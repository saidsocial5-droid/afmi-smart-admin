"""API de l'éditeur (Lot 4) : chartes, logos, modèles, documents, versions, commentaires, blocs, photos, assistant."""
import hashlib
import mimetypes
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from backend.config.settings import settings
from backend.core import unified_db
from backend.tools.editor import assistant, blocks, charts, documents, from_report, photos

router = APIRouter(tags=["Éditeur de documents"])
IMAGE_TYPES = {".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif"}
MAX_IMAGE = 15 * 1024 * 1024


def _guard(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except (documents.EditorError, photos.PhotoError, ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e).strip("'"))
    except unified_db.UnifiedDbUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=f"Enregistrement refusé par la base : {e}")


async def _aguard(coro):
    try:
        return await coro
    except (documents.EditorError, photos.PhotoError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except unified_db.UnifiedDbUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))


# --- Chartes et logos ----------------------------------------------------------------------------------------

@router.get("/api/charts")
def list_charts():
    return _guard(charts.list_charts)


@router.post("/api/charts")
def save_chart(data: Dict[str, Any]):
    return _guard(charts.save_chart, data)


@router.delete("/api/charts/{chart_id}")
def delete_chart(chart_id: int):
    _guard(charts.delete_chart, chart_id)
    return {"status": "deleted"}


@router.get("/api/charts/effective")
def effective_chart(project_id: Optional[int] = None, funder_id: Optional[int] = None):
    return _guard(charts.effective, project_id, funder_id)


@router.post("/api/files/images")
async def upload_image(file: UploadFile = File(...)):
    """Logo ou image insérée dans un document : archivé (SHA-256), renvoie l'identifiant du fichier."""
    name = (file.filename or "image.png").replace("\\", "/").split("/")[-1]
    ext = Path(name).suffix.lower()
    if ext not in IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Image attendue (PNG, JPG, WEBP, SVG, GIF).")
    data = await file.read()
    if len(data) > MAX_IMAGE:
        raise HTTPException(status_code=400, detail="Image trop lourde (15 Mo au plus).")
    sha = hashlib.sha256(data).hexdigest()

    def store():
        with unified_db.connect() as conn:
            row = conn.execute("SELECT Id FROM StoredFiles WHERE Sha256 = ?", (sha,)).fetchone()
            if row:
                return row["Id"]
            folder = settings.data_dir / "archives" / "images"
            folder.mkdir(parents=True, exist_ok=True)
            (folder / f"{sha}{ext}").write_bytes(data)
            return unified_db.insert(conn, "StoredFiles", "StoredFile", {
                "Sha256": sha, "RelativePath": f"archives/images/{sha}{ext}", "OriginalName": name[:255],
                "MimeType": mimetypes.guess_type(name)[0] or "image/png", "SizeBytes": len(data), "ImportedAtUtc": unified_db.now_ef()})
    file_id = _guard(store)
    return {"file_id": file_id, "url": f"/api/files/{file_id}/image"}


@router.get("/api/files/{file_id}/image")
def get_image(file_id: int):
    """Seuls les fichiers archivés de type image sont servis (jamais un chemin arbitraire)."""
    with unified_db.connect() as conn:
        row = conn.execute("SELECT * FROM StoredFiles WHERE Id = ?", (file_id,)).fetchone()
    if row is None or not str(row["MimeType"]).startswith("image/"):
        raise HTTPException(status_code=404, detail="Image introuvable.")
    path = (settings.data_dir / row["RelativePath"]).resolve()
    if not path.is_relative_to(settings.data_dir.resolve()) or not path.exists():
        raise HTTPException(status_code=404, detail="Image introuvable.")
    return FileResponse(path, media_type=row["MimeType"])


@router.get("/api/funders/{funder_id}/logo")
def funder_logo(funder_id: int):
    """Logo saisi sur la fiche du bailleur (application de bureau) : servi seulement si c'est une image existante."""
    with unified_db.connect() as conn:
        row = conn.execute("SELECT LogoPath FROM Funders WHERE Id = ?", (funder_id,)).fetchone()
    path = Path(row["LogoPath"]) if row and row["LogoPath"] else None
    if path is None or path.suffix.lower() not in IMAGE_TYPES or not path.is_file():
        raise HTTPException(status_code=404, detail="Logo introuvable.")
    return FileResponse(path, media_type=mimetypes.guess_type(path.name)[0] or "image/png")


# --- Modèles ----------------------------------------------------------------------------------------------

@router.get("/api/templates")
def list_templates():
    return _guard(documents.list_templates)


@router.get("/api/templates/{template_id}")
def get_template(template_id: int):
    return _guard(documents.get_template, template_id)


@router.post("/api/templates")
def save_template(data: Dict[str, Any]):
    return _guard(documents.save_template, data)


@router.post("/api/templates/{template_id}/duplicate")
def duplicate_template(template_id: int):
    return _guard(documents.duplicate_template, template_id)


@router.delete("/api/templates/{template_id}")
def delete_template(template_id: int):
    _guard(documents.delete_template, template_id)
    return {"status": "deleted"}


# --- Documents, versions, commentaires ------------------------------------------------------------------

@router.get("/api/documents")
def list_documents(project_id: Optional[int] = None):
    return _guard(documents.list_documents, project_id)


@router.post("/api/documents")
def create_document(data: Dict[str, Any]):
    return _guard(documents.create_document, data)


@router.get("/api/documents/{doc_id}")
def get_document(doc_id: int):
    return _guard(documents.get_document, doc_id)


@router.put("/api/documents/{doc_id}")
def save_document(doc_id: int, data: Dict[str, Any]):
    note = data.pop("version_note", None)
    return _guard(documents.save_document, doc_id, data, note)


@router.delete("/api/documents/{doc_id}")
def delete_document(doc_id: int):
    _guard(documents.delete_document, doc_id)
    return {"status": "deleted"}


@router.get("/api/documents/{doc_id}/versions")
def list_versions(doc_id: int):
    return _guard(documents.list_versions, doc_id)


@router.post("/api/documents/{doc_id}/versions/{version_id}/restore")
def restore_version(doc_id: int, version_id: int):
    return _guard(documents.restore_version, doc_id, version_id)


@router.get("/api/documents/{doc_id}/comments")
def list_comments(doc_id: int):
    return _guard(documents.list_comments, doc_id)


@router.post("/api/documents/{doc_id}/comments")
def add_comment(doc_id: int, data: Dict[str, Any]):
    return _guard(documents.add_comment, doc_id, data)


@router.post("/api/documents/{doc_id}/comments/{comment_id}/resolve")
def resolve_comment(doc_id: int, comment_id: int, data: Optional[Dict[str, Any]] = None):
    return _guard(documents.resolve_comment, doc_id, comment_id, (data or {}).get("resolved", True))


# --- Blocs dynamiques et champs ----------------------------------------------------------------------------

@router.get("/api/editor/blocks/{kind}")
def block_data(kind: str, project_id: Optional[int] = None, date_from: Optional[str] = None, date_to: Optional[str] = None,
               chart: str = "budget", task_id: Optional[int] = None, photo_ids: Optional[str] = None, limit: int = 6):
    if kind == "budget":
        return _guard(blocks.budget_table, project_id)
    if kind == "indicators":
        return _guard(blocks.indicators, project_id)
    if kind == "activities":
        return _guard(blocks.activities, project_id, date_from, date_to)
    if kind == "chart":
        return _guard(blocks.chart, project_id, chart)
    if kind == "gallery":
        if photo_ids:
            ids = [int(i) for i in photo_ids.split(",") if i.strip().isdigit()]
            selected = [p for p in _guard(photos.list_photos, project_id) if p["id"] in ids]
            selected.sort(key=lambda p: ids.index(p["id"]))
            return {"photos": selected}
        if not project_id:
            return {"photos": []}
        return {"photos": _guard(photos.select_for_report, project_id, date_from, date_to, task_id, max(1, min(limit, 24)))}
    raise HTTPException(status_code=404, detail="Bloc inconnu.")


@router.get("/api/editor/fields")
def field_values(project_id: Optional[int] = None, funder_id: Optional[int] = None):
    return _guard(blocks.fields, project_id, funder_id)


@router.get("/api/editor/context")
def editor_context():
    def load():
        with unified_db.connect() as conn:
            return {
                "projects": [dict(id=r["Id"], code=r["Code"], name=r["Name"], funder_id=r["FunderId"])
                             for r in conn.execute("SELECT Id, Code, Name, FunderId FROM Projects WHERE IsDeleted = 0 ORDER BY Code")],
                "funders": [dict(id=r["Id"], name=r["Name"]) for r in conn.execute("SELECT Id, Name FROM Funders ORDER BY Name")],
                "tasks": [dict(id=r["Id"], project_id=r["ProjectId"], name=r["Name"]) for r in conn.execute("SELECT Id, ProjectId, Name FROM Tasks ORDER BY Name")],
                "user": unified_db.current_user(),
            }
    return _guard(load)


@router.post("/api/editor/assistant")
async def run_assistant(data: Dict[str, Any]):
    return await _aguard(assistant.run(data.get("action", ""), data.get("text", ""), data.get("language", "fr"),
                                       data.get("project_id"), data.get("instruction", "")))


# --- Photos -------------------------------------------------------------------------------------------------

@router.get("/api/photos")
def list_photos(project_id: Optional[int] = None, task_id: Optional[int] = None, date_from: Optional[str] = None,
                date_to: Optional[str] = None, consent_only: bool = False):
    return _guard(photos.list_photos, project_id, task_id, date_from, date_to, consent_only)


@router.post("/api/photos/upload")
async def upload_photos(project_id: Optional[int] = Form(None), task_id: Optional[int] = Form(None), credit: str = Form(""),
                        consent: bool = Form(False), files: List[UploadFile] = File(...)):
    blobs = []
    for f in files:
        data = await f.read()
        if len(data) > MAX_IMAGE * 2:
            raise HTTPException(status_code=400, detail=f"« {f.filename} » dépasse 30 Mo.")
        blobs.append((data, (f.filename or "photo.jpg").replace("\\", "/").split("/")[-1]))
    return {"results": _guard(photos.upload, blobs, project_id, task_id, None, credit, consent)}


@router.get("/api/photos/{photo_id}/image")
def photo_image(photo_id: int):
    return FileResponse(_guard(photos.web_version, photo_id), media_type="image/jpeg")


@router.put("/api/photos/{photo_id}")
def update_photo(photo_id: int, data: Dict[str, Any]):
    return _guard(photos.update, photo_id, data)


@router.delete("/api/photos/{photo_id}")
def delete_photo(photo_id: int):
    _guard(photos.delete, photo_id)
    return {"status": "deleted"}


@router.post("/api/photos/{photo_id}/suggest-caption")
async def suggest_caption(photo_id: int):
    return await _aguard(photos.suggest_caption(photo_id))


@router.post("/api/editor/documents/from-report")
def document_from_report(data: Dict[str, Any]):
    """Rapport généré par l'application de bureau (Projet › Rapports) → document de l'éditeur, nouvelle version si existant."""
    return _guard(from_report.create_or_update, int(data["project_id"]), data.get("report_type") or "", (data.get("title") or "Rapport").strip()[:250],
                  data.get("text") or "")
