"""Import, classement, métadonnées et obligations des documents de projet (table Documents, partagée avec le bureau)."""
import hashlib
import json
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.config.settings import settings
from backend.core import unified_db
from . import analyze, index, textract
from .config import load

ARCHIVE = "archives/documents"


class GedError(ValueError):
    pass


def _row(r) -> Dict[str, Any]:
    meta = json.loads(r["MetadataJson"] or "{}")
    return {"id": r["Id"], "project_id": r["ProjectId"], "title": r["Title"], "doc_type": r["DocType"], "phase": r["LifecyclePhase"],
            "confidence": r["ClassificationConfidence"], "metadata": meta, "file_name": r["OriginalFileName"], "size": r["FileSize"],
            "uploaded": str(r["UploadedDate"])[:19], "signature_date": str(r["SignatureDate"] or "")[:10], "end_date": str(r["ContractualEndDate"] or "")[:10],
            "summary": r["ExtractedSummary"], "language": r["Language"], "indexed": r["IndexedAtUtc"] is not None, "key": bool(r["IsKeyReference"]),
            "has_file": bool(r["FilePath"]) and Path(r["FilePath"]).is_file()}


def list_documents(project_id: Optional[int]) -> List[Dict[str, Any]]:
    with unified_db.connect() as conn:
        sql, args = "SELECT * FROM Documents WHERE IsDeleted = 0", []
        if project_id:
            sql += " AND ProjectId = ?"
            args.append(project_id)
        return [_row(r) for r in conn.execute(sql + " ORDER BY COALESCE(SignatureDate, UploadedDate) DESC", args)]


def _summary(pages) -> str:
    text = " ".join(t for _, t in pages)
    text = " ".join(text.split())
    return text[:600] + ("…" if len(text) > 600 else "")


async def import_document(project_id: int, data: bytes, filename: str, title: Optional[str] = None,
                          doc_type: Optional[str] = None, phase: Optional[str] = None) -> Dict[str, Any]:
    cfg = load()
    name = Path(filename).name
    pages, engine = textract.extract(data, name)
    full = "\n".join(t for _, t in pages)
    title = (title or Path(name).stem.replace("_", " ")).strip()[:250]
    guessed, confidence, scores = analyze.classify(title, full)
    if doc_type:
        if doc_type not in cfg["types"] and doc_type != "Autre":
            raise GedError(f"Type inconnu : {doc_type}.")
        guessed, confidence = doc_type, 100.0
    phase = phase or cfg["types"].get(guessed, {}).get("phase", "Mise en œuvre")
    if phase not in cfg["phases"]:
        raise GedError(f"Phase inconnue : {phase}.")
    meta = analyze.metadata(full)
    meta.update({"engine": engine, "scores": scores, "pages": len(pages)})
    sha = hashlib.sha256(data).hexdigest()
    folder = settings.data_dir / ARCHIVE
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{sha}{Path(name).suffix.lower()}"

    with unified_db.connect() as conn:
        if conn.execute("SELECT 1 FROM Projects WHERE Id = ? AND IsDeleted = 0", (project_id,)).fetchone() is None:
            raise GedError("Projet introuvable.")
        dup = conn.execute("SELECT d.Title FROM Documents d JOIN StoredFiles f ON f.Id = d.StoredFileId WHERE f.Sha256 = ? AND d.ProjectId = ? "
                           "AND d.IsDeleted = 0", (sha, project_id)).fetchone()
        if dup:
            raise GedError(f"Ce fichier est déjà dans la GED du projet (« {dup['Title']} »).")
        f = conn.execute("SELECT Id FROM StoredFiles WHERE Sha256 = ?", (sha,)).fetchone()
        if not path.exists():
            path.write_bytes(data)
        file_id = f["Id"] if f else unified_db.insert(conn, "StoredFiles", "StoredFile", {
            "Sha256": sha, "RelativePath": f"{ARCHIVE}/{path.name}", "OriginalName": name[:255],
            "MimeType": mimetypes.guess_type(name)[0] or "application/octet-stream", "SizeBytes": len(data), "ImportedAtUtc": unified_db.now_ef()})
        amount = meta["max_amount"]["value"] if guessed in ("Convention", "Avenant") and meta["max_amount"] else 0.0
        doc_id = unified_db.insert(conn, "Documents", "ProjectDocument", {
            "ProjectId": project_id, "Title": title, "Category": guessed, "DocumentPhase": phase, "Tags": "", "IsKeyReference": int(guessed in ("Convention", "Rapport final", "Rapport d'évaluation")),
            "DocumentVersion": "", "DonorName": "", "DocumentReference": "", "SignatureDate": f"{meta['signature']} 00:00:00" if meta["signature"] else None,
            "ContractualEndDate": f"{meta['end']} 00:00:00" if meta["end"] and guessed in ("Convention", "Avenant", "Contrat") else None,
            "ApprovedGrantAmount": amount, "FilePath": str(path), "OriginalFileName": name[:255], "FileExtension": path.suffix, "FileSize": len(data),
            "Notes": "", "ExtractedSummary": _summary(pages), "FullExtractedText": full, "KeyInsights": "", "AnalyzedDate": unified_db.now_ef(),
            "UploadedDate": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "DocType": guessed, "LifecyclePhase": phase, "ClassificationConfidence": confidence,
            "MetadataJson": json.dumps(meta, ensure_ascii=False), "StoredFileId": file_id, "Language": analyze.language(full), "IsDeleted": 0})

        proposals = []
        if guessed in ("Convention", "Avenant", "Termes de référence", "Contrat"):
            for o in analyze.obligations(full, meta["start"], meta["end"]):
                exists = conn.execute("SELECT 1 FROM ReportingObligations WHERE ProjectId = ? AND DueDate = ? AND Kind = ? AND IsDeleted = 0",
                                      (project_id, o["due"], o["kind"][:50])).fetchone()
                if exists:
                    continue
                unified_db.insert(conn, "ReportingObligations", "ReportingObligation", {
                    "ProjectId": project_id, "FundingAgreementId": None, "Title": o["title"][:250], "Kind": o["kind"][:50], "DueDate": o["due"],
                    "Status": "Proposée", "DeliveredDocumentId": None, "SourceDocumentId": doc_id, "SourceExcerpt": o["excerpt"], "Notes": "", "IsDeleted": 0})
                proposals.append(o)
    indexed = await index.index_document(doc_id, pages)
    if guessed.startswith("Rapport") and not doc_type:
        mark_delivered(project_id, doc_id, guessed)
    # Copie dans les dossiers locaux du projet (Année › Trimestre › catégorie), pour l'explorateur Windows
    from . import folders
    try:
        local_copy = folders.mirror_document(doc_id)
    except OSError as e:
        local_copy = None
        print(f"[GED] Copie locale impossible : {e}")
    return {"document": get(doc_id), "proposed_obligations": proposals, "index": indexed, "local_copy": local_copy}


def get(doc_id: int) -> Dict[str, Any]:
    with unified_db.connect() as conn:
        r = conn.execute("SELECT * FROM Documents WHERE Id = ? AND IsDeleted = 0", (doc_id,)).fetchone()
        if r is None:
            raise GedError("Document introuvable.")
        return _row(r)


def update(doc_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    cfg = load()
    values = {}
    if "title" in data:
        values["Title"] = (data["title"] or "").strip()[:250]
    if "doc_type" in data:
        if data["doc_type"] not in cfg["types"] and data["doc_type"] != "Autre":
            raise GedError("Type inconnu.")
        values.update({"DocType": data["doc_type"], "Category": data["doc_type"], "ClassificationConfidence": 100.0})
    if "phase" in data:
        if data["phase"] not in cfg["phases"]:
            raise GedError("Phase inconnue.")
        values.update({"LifecyclePhase": data["phase"], "DocumentPhase": data["phase"]})
    if "signature_date" in data:
        values["SignatureDate"] = f"{data['signature_date']} 00:00:00" if data["signature_date"] else None
    if "end_date" in data:
        values["ContractualEndDate"] = f"{data['end_date']} 00:00:00" if data["end_date"] else None
    if "key" in data:
        values["IsKeyReference"] = int(bool(data["key"]))
    if "folder_id" in data:
        from . import folders
        folders.move_document(doc_id, data["folder_id"])
    with unified_db.connect() as conn:
        unified_db.update(conn, "Documents", "ProjectDocument", doc_id, values)
    return get(doc_id)


def delete(doc_id: int) -> None:
    with unified_db.connect() as conn:
        unified_db.soft_delete(conn, "Documents", "ProjectDocument", doc_id)


def file_path(doc_id: int) -> Path:
    d = get(doc_id)
    with unified_db.connect() as conn:
        p = Path(conn.execute("SELECT FilePath FROM Documents WHERE Id = ?", (doc_id,)).fetchone()[0] or "")
    if not p.is_file():
        raise GedError("Fichier introuvable sur ce poste.")
    return p


async def reindex_existing(project_id: Optional[int] = None) -> Dict[str, Any]:
    """Documents importés avant le Lot 6 (application de bureau) : texte relu, classé si besoin, indexé."""
    done, skipped = 0, []
    with unified_db.connect() as conn:
        sql, args = "SELECT * FROM Documents WHERE IsDeleted = 0 AND IndexedAtUtc IS NULL", []
        if project_id:
            sql += " AND ProjectId = ?"
            args.append(project_id)
        rows = [dict(r) for r in conn.execute(sql, args)]
    for r in rows:
        pages = None
        path = Path(r["FilePath"] or "")
        if path.is_file():
            try:
                pages, _ = textract.extract(path.read_bytes(), path.name)
            except textract.ExtractionError:
                pages = None
        if pages is None and r["FullExtractedText"]:
            pages = [(1, r["FullExtractedText"])]
        if not pages:
            skipped.append(r["Title"])
            continue
        full = "\n".join(t for _, t in pages)
        if not r["DocType"] or r["DocType"] == "Autre":
            guessed, conf, _ = analyze.classify(r["Title"], full)
            if conf >= 60:
                update(r["Id"], {"doc_type": guessed})
        with unified_db.connect() as conn:
            unified_db.update(conn, "Documents", "ProjectDocument", r["Id"], {
                "MetadataJson": json.dumps(analyze.metadata(full), ensure_ascii=False), "Language": analyze.language(full)})
        await index.index_document(r["Id"], pages)
        done += 1
    return {"indexed": done, "skipped": skipped}


# --- Obligations et jalons -----------------------------------------------------------------------------------

def mark_delivered(project_id: int, doc_id: int, doc_type: str) -> Optional[int]:
    """Un rapport importé solde la prochaine obligation confirmée du même genre non encore remise."""
    kind_word = "financier" if "financier" in doc_type.lower() else "final" if "final" in doc_type.lower() else "narratif"
    with unified_db.connect() as conn:
        o = conn.execute("SELECT * FROM ReportingObligations WHERE ProjectId = ? AND IsDeleted = 0 AND Status = 'À venir' "
                         "AND lower(Kind) LIKE ? ORDER BY DueDate LIMIT 1", (project_id, f"%{kind_word}%")).fetchone()
        if o is None:
            return None
        unified_db.update(conn, "ReportingObligations", "ReportingObligation", o["Id"], {"Status": "Remise", "DeliveredDocumentId": doc_id})
        return o["Id"]


def _obl(r) -> Dict[str, Any]:
    return {"id": r["Id"], "project_id": r["ProjectId"], "title": r["Title"], "kind": r["Kind"], "due": r["DueDate"], "status": r["Status"],
            "delivered_document_id": r["DeliveredDocumentId"], "source_document_id": r["SourceDocumentId"], "excerpt": r["SourceExcerpt"]}


def list_obligations(project_id: int) -> List[Dict[str, Any]]:
    with unified_db.connect() as conn:
        return [_obl(r) for r in conn.execute("SELECT * FROM ReportingObligations WHERE ProjectId = ? AND IsDeleted = 0 ORDER BY DueDate", (project_id,))]


def save_obligation(data: Dict[str, Any]) -> Dict[str, Any]:
    if data.get("status", "À venir") not in ("Proposée", "À venir", "Remise"):
        raise GedError("Statut : Proposée, À venir ou Remise.")
    fields = {"title": "Title", "kind": "Kind", "due": "DueDate", "status": "Status", "delivered_document_id": "DeliveredDocumentId"}
    values = {col: data[key] for key, col in fields.items() if key in data}
    with unified_db.connect() as conn:
        if data.get("id"):
            unified_db.update(conn, "ReportingObligations", "ReportingObligation", data["id"], values)
            oid = data["id"]
        else:
            if not data.get("title") or not data.get("due"):
                raise GedError("Titre et échéance obligatoires.")
            oid = unified_db.insert(conn, "ReportingObligations", "ReportingObligation", {
                "ProjectId": int(data["project_id"]), "FundingAgreementId": None, "Title": data["title"][:250], "Kind": (data.get("kind") or "Rapport narratif")[:50],
                "DueDate": data["due"], "Status": data.get("status", "À venir"), "DeliveredDocumentId": None, "SourceDocumentId": None,
                "SourceExcerpt": "", "Notes": "", "IsDeleted": 0})
        return _obl(conn.execute("SELECT * FROM ReportingObligations WHERE Id = ?", (oid,)).fetchone())


def delete_obligation(obligation_id: int) -> None:
    with unified_db.connect() as conn:
        unified_db.soft_delete(conn, "ReportingObligations", "ReportingObligation", obligation_id)


def save_milestone(data: Dict[str, Any]) -> Dict[str, Any]:
    if data.get("phase") and data["phase"] not in load()["phases"]:
        raise GedError("Phase inconnue.")
    with unified_db.connect() as conn:
        values = {"Title": (data.get("title") or "").strip()[:250], "Date": data.get("date"), "Phase": data.get("phase", ""), "Done": int(bool(data.get("done")))}
        if not values["Title"] or not values["Date"]:
            raise GedError("Titre et date du jalon obligatoires.")
        if data.get("id"):
            unified_db.update(conn, "ProjectMilestones", "ProjectMilestone", data["id"], values)
            mid = data["id"]
        else:
            mid = unified_db.insert(conn, "ProjectMilestones", "ProjectMilestone", {**values, "ProjectId": int(data["project_id"]), "SourceDocumentId": None, "IsDeleted": 0})
        r = conn.execute("SELECT * FROM ProjectMilestones WHERE Id = ?", (mid,)).fetchone()
        return {"id": r["Id"], "title": r["Title"], "date": r["Date"], "phase": r["Phase"], "done": bool(r["Done"])}


def delete_milestone(milestone_id: int) -> None:
    with unified_db.connect() as conn:
        unified_db.soft_delete(conn, "ProjectMilestones", "ProjectMilestone", milestone_id)
