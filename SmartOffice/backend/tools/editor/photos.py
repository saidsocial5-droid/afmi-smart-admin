"""Photos d'activités : import par lot (EXIF), consentement, légende (proposition IA à valider), sélection pour un rapport.

Le fichier d'origine est archivé tel quel (SHA-256) ; une version allégée (2000 px, JPEG 85) est servie à l'éditeur
et aux rapports. Une photo sans consentement au droit à l'image n'est jamais sélectionnée automatiquement.
"""
import base64
import hashlib
import io
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from PIL import Image, ImageOps, UnidentifiedImageError

from backend.config.settings import settings
from backend.core import unified_db
from backend.core.llm_router import llm_router

ARCHIVE_DIR = "archives/photos"
WEB_MAX = 2000
EXT = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".heic"}


class PhotoError(ValueError):
    pass


def _dir() -> Path:
    d = settings.data_dir / ARCHIVE_DIR
    (d / "web").mkdir(parents=True, exist_ok=True)
    return d


def _gps(exif) -> tuple[Optional[float], Optional[float]]:
    try:
        gps = exif.get_ifd(0x8825)
    except Exception:
        return None, None
    if not gps or 2 not in gps or 4 not in gps:
        return None, None

    def to_deg(v, ref):
        d, m, s = (float(x) for x in v)
        deg = d + m / 60 + s / 3600
        return -deg if ref in ("S", "W") else deg
    try:
        return round(to_deg(gps[2], gps.get(1, "N")), 6), round(to_deg(gps[4], gps.get(3, "E")), 6)
    except (TypeError, ValueError, ZeroDivisionError):
        return None, None


def read_metadata(data: bytes) -> Dict[str, Any]:
    try:
        img = Image.open(io.BytesIO(data))
    except UnidentifiedImageError:
        raise PhotoError("Image illisible.")
    exif = img.getexif()
    taken = None
    raw = None
    try:
        raw = exif.get_ifd(0x8769).get(36867)  # DateTimeOriginal
    except Exception:
        raw = None
    raw = raw or exif.get(306)                  # DateTime
    if raw:
        try:
            taken = datetime.strptime(str(raw).strip(), "%Y:%m:%d %H:%M:%S")
        except ValueError:
            taken = None
    lat, lon = _gps(exif)
    w, h = ImageOps.exif_transpose(img).size
    return {"taken_at": taken, "latitude": lat, "longitude": lon, "width": w, "height": h}


def web_version(photo_id: int) -> Path:
    """Version allégée (orientation EXIF appliquée), créée à la demande et mise en cache."""
    with unified_db.connect() as conn:
        r = conn.execute("SELECT f.RelativePath FROM Photos p JOIN StoredFiles f ON f.Id = p.StoredFileId WHERE p.Id = ? AND p.IsDeleted = 0",
                         (photo_id,)).fetchone()
    if r is None:
        raise PhotoError("Photo introuvable.")
    target = _dir() / "web" / f"{photo_id}.jpg"
    if not target.exists():
        img = ImageOps.exif_transpose(Image.open(settings.data_dir / r["RelativePath"]))
        img.thumbnail((WEB_MAX, WEB_MAX))
        img.convert("RGB").save(target, "JPEG", quality=85, optimize=True)
    return target


def _row(r) -> Dict[str, Any]:
    return {"id": r["Id"], "project_id": r["ProjectId"], "task_id": r["ProjectTaskId"], "activity_report_id": r["ActivityReportId"],
            "taken_at": r["TakenAt"], "location": r["Location"], "latitude": r["Latitude"], "longitude": r["Longitude"],
            "caption": r["Caption"], "suggested_caption": r["SuggestedCaption"], "caption_validated": bool(r["CaptionValidated"]),
            "credit": r["Credit"], "consent": bool(r["ConsentGiven"]), "width": r["Width"], "height": r["Height"],
            "url": f"/api/photos/{r['Id']}/image"}


def upload(files: List[tuple[bytes, str]], project_id: Optional[int], task_id: Optional[int] = None,
           activity_report_id: Optional[int] = None, credit: str = "", consent: bool = False) -> List[Dict[str, Any]]:
    results = []
    for data, name in files:
        ext = Path(name).suffix.lower()
        if ext not in EXT:
            results.append({"file": name, "error": "Format non pris en charge (JPG, PNG, WEBP, TIFF)."})
            continue
        try:
            meta = read_metadata(data)
        except PhotoError as e:
            results.append({"file": name, "error": str(e)})
            continue
        sha = hashlib.sha256(data).hexdigest()
        with unified_db.connect() as conn:
            f = conn.execute("SELECT Id FROM StoredFiles WHERE Sha256 = ?", (sha,)).fetchone()
            if f and conn.execute("SELECT 1 FROM Photos WHERE StoredFileId = ? AND IsDeleted = 0", (f["Id"],)).fetchone():
                results.append({"file": name, "error": "Photo déjà importée."})
                continue
            if f:
                file_id = f["Id"]
            else:
                (_dir() / f"{sha}{ext}").write_bytes(data)
                file_id = unified_db.insert(conn, "StoredFiles", "StoredFile", {
                    "Sha256": sha, "RelativePath": f"{ARCHIVE_DIR}/{sha}{ext}", "OriginalName": Path(name).name[:255],
                    "MimeType": mimetypes.guess_type(name)[0] or "image/jpeg", "SizeBytes": len(data), "ImportedAtUtc": unified_db.now_ef()})
            pid = unified_db.insert(conn, "Photos", "Photo", {
                "StoredFileId": file_id, "ProjectId": project_id, "ProjectTaskId": task_id, "ActivityReportId": activity_report_id,
                "TakenAt": meta["taken_at"].strftime("%Y-%m-%d %H:%M:%S") if meta["taken_at"] else None, "Location": "",
                "Latitude": meta["latitude"], "Longitude": meta["longitude"], "Caption": "", "SuggestedCaption": "",
                "CaptionValidated": 0, "Credit": credit[:150], "ConsentGiven": int(bool(consent)), "Width": meta["width"],
                "Height": meta["height"], "ImportedAtUtc": unified_db.now_ef(), "IsDeleted": 0})
            results.append({"file": name, "photo": _row(conn.execute("SELECT * FROM Photos WHERE Id = ?", (pid,)).fetchone())})
    return results


def list_photos(project_id: Optional[int] = None, task_id: Optional[int] = None, date_from: Optional[str] = None,
                date_to: Optional[str] = None, consent_only: bool = False) -> List[Dict[str, Any]]:
    sql, args = "SELECT * FROM Photos WHERE IsDeleted = 0", []
    for cond, val in (("ProjectId = ?", project_id), ("ProjectTaskId = ?", task_id),
                      ("date(COALESCE(TakenAt, ImportedAtUtc)) >= date(?)", date_from),
                      ("date(COALESCE(TakenAt, ImportedAtUtc)) <= date(?)", date_to)):
        if val:
            sql += f" AND {cond}"
            args.append(val)
    if consent_only:
        sql += " AND ConsentGiven = 1"
    with unified_db.connect() as conn:
        return [_row(r) for r in conn.execute(sql + " ORDER BY COALESCE(TakenAt, ImportedAtUtc)", args)]


def update(photo_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    values = {}
    for key, col, conv in (("caption", "Caption", lambda v: (v or "")[:500]), ("credit", "Credit", lambda v: (v or "")[:150]),
                           ("location", "Location", lambda v: (v or "")[:200]), ("consent", "ConsentGiven", lambda v: int(bool(v))),
                           ("caption_validated", "CaptionValidated", lambda v: int(bool(v))), ("project_id", "ProjectId", lambda v: v),
                           ("task_id", "ProjectTaskId", lambda v: v), ("taken_at", "TakenAt", lambda v: v)):
        if key in data:
            values[col] = conv(data[key])
    if "caption" in data and "caption_validated" not in data:
        values["CaptionValidated"] = int(bool(values["Caption"]))  # une légende saisie par l'utilisateur est validée
    with unified_db.connect() as conn:
        unified_db.update(conn, "Photos", "Photo", photo_id, values)
        return _row(conn.execute("SELECT * FROM Photos WHERE Id = ?", (photo_id,)).fetchone())


def delete(photo_id: int) -> None:
    with unified_db.connect() as conn:
        unified_db.soft_delete(conn, "Photos", "Photo", photo_id)


async def suggest_caption(photo_id: int) -> Dict[str, Any]:
    """Légende proposée par un modèle de vision (local, ou externe si autorisé et sans masquage). Toujours à valider."""
    with unified_db.connect() as conn:
        r = conn.execute("SELECT p.*, pr.Name AS ProjectName FROM Photos p LEFT JOIN Projects pr ON pr.Id = p.ProjectId WHERE p.Id = ?",
                         (photo_id,)).fetchone()
    if r is None:
        raise PhotoError("Photo introuvable.")
    img = Image.open(web_version(photo_id))
    img.thumbnail((1024, 1024))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=80)
    from backend.core import ai_config
    prompt = ai_config.prompt("photos.caption")
    if r["ProjectName"]:
        prompt += f" Projet : {r['ProjectName']}."
    text, engine = await llm_router.generate_with_meta(prompt, images_b64=[base64.b64encode(buf.getvalue()).decode()], temperature=0.2,
                                                         task="captions")
    if engine == "heuristic":
        return {"photo": _row(r), "engine": engine,
                "message": "Aucun modèle de vision disponible (activez Ollama avec un modèle de vision, ou l'IA externe) : saisissez la légende."}
    caption = " ".join(text.strip().strip('"').split())[:500]
    return {"photo": _apply_suggestion(photo_id, caption), "engine": engine}


def _apply_suggestion(photo_id: int, caption: str) -> Dict[str, Any]:
    with unified_db.connect() as conn:
        unified_db.update(conn, "Photos", "Photo", photo_id, {"SuggestedCaption": caption})
        return _row(conn.execute("SELECT * FROM Photos WHERE Id = ?", (photo_id,)).fetchone())


def select_for_report(project_id: int, date_from: Optional[str], date_to: Optional[str], task_id: Optional[int] = None,
                      limit: int = 6) -> List[Dict[str, Any]]:
    """Sélection automatique : consentement obligatoire, puis légendes validées, puis photos les mieux définies,
    réparties sur la période (pas toutes du même jour)."""
    candidates = list_photos(project_id, task_id, date_from, date_to, consent_only=True)
    candidates.sort(key=lambda p: (not p["caption_validated"], -(p["width"] * p["height"])))
    chosen, days = [], set()
    for p in candidates:                                   # 1er passage : un jour différent par photo
        day = (p["taken_at"] or "")[:10]
        if day not in days:
            chosen.append(p)
            days.add(day)
        if len(chosen) == limit:
            break
    for p in candidates:                                   # 2e passage : compléter
        if len(chosen) >= limit:
            break
        if p not in chosen:
            chosen.append(p)
    return sorted(chosen, key=lambda p: p["taken_at"] or "")


def import_legacy_activity_photos() -> Dict[str, Any]:
    """
    Reprise des photos des rapports d'activité de l'application de bureau (table ActivityReportPhotos, chemins locaux).
    Le consentement n'étant pas connu, il est à confirmer : ces photos ne sont pas sélectionnées automatiquement avant.
    Relancer la reprise ne crée pas de doublon (empreinte SHA-256).
    """
    imported, skipped, missing = 0, 0, []
    with unified_db.connect() as conn:
        rows = conn.execute("SELECT ph.*, r.ActivityDate, r.Location, t.ProjectId, t.Id AS TaskId FROM ActivityReportPhotos ph "
                            "JOIN ActivityReports r ON r.Id = ph.ActivityReportId JOIN Tasks t ON t.Id = r.ProjectTaskId").fetchall()
    for r in rows:
        path = Path(r["LocalFilePath"] or "")
        if not path.is_file() or path.suffix.lower() not in EXT:
            missing.append(str(path))
            continue
        result = upload([(path.read_bytes(), path.name)], r["ProjectId"], r["TaskId"], r["ActivityReportId"], "", False)[0]
        if "error" in result:
            skipped += 1
            continue
        update(result["photo"]["id"], {"caption": r["Caption"] or "", "location": r["Location"] or "",
                                       "caption_validated": bool(r["Caption"]),
                                       **({} if result["photo"]["taken_at"] else {"taken_at": str(r["ActivityDate"])[:19]})})
        imported += 1
    return {"imported": imported, "skipped": skipped, "missing": missing[:20], "missing_count": len(missing)}
