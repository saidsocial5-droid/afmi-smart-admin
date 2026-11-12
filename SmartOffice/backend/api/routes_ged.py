"""API de la GED des projets (Lot 6) : documents, obligations de reporting, jalons, frise, alertes, recherche, questions."""
import sqlite3
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from backend.core import unified_db
from backend.tools.ged import index, lifecycle, qa, service, textract
from backend.tools.ged.config import load

router = APIRouter(prefix="/api/ged", tags=["GED et cycle de vie"])
MAX_BYTES = 40 * 1024 * 1024


def _guard(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except (service.GedError, textract.ExtractionError, ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e).strip("'"))
    except unified_db.UnifiedDbUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=f"Enregistrement refusé par la base : {e}")


async def _aguard(coro):
    try:
        return await coro
    except (service.GedError, textract.ExtractionError, ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e).strip("'"))
    except unified_db.UnifiedDbUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/config")
def config():
    cfg = load()
    return {"phases": cfg["phases"], "types": list(cfg["types"]) + ["Autre"], "expected": cfg["expected"]}


@router.get("/documents")
def list_documents(project_id: Optional[int] = None):
    return _guard(service.list_documents, project_id)


@router.post("/documents")
async def upload(project_id: int = Form(...), doc_type: Optional[str] = Form(None), phase: Optional[str] = Form(None),
                 files: List[UploadFile] = File(...)):
    results = []
    for f in files:
        name = (f.filename or "document").replace("\\", "/").split("/")[-1]
        data = await f.read()
        if len(data) > MAX_BYTES:
            results.append({"file": name, "error": "Fichier de plus de 40 Mo."})
            continue
        try:
            results.append({"file": name, **await service.import_document(project_id, data, name, None, doc_type or None, phase or None)})
        except (service.GedError, textract.ExtractionError, ValueError) as e:
            results.append({"file": name, "error": str(e)})
        except unified_db.UnifiedDbUnavailable as e:
            raise HTTPException(status_code=503, detail=str(e))
    return {"results": results}


@router.get("/documents/{doc_id}")
def get_document(doc_id: int):
    return _guard(service.get, doc_id)


@router.get("/documents/{doc_id}/file")
def get_file(doc_id: int):
    path = _guard(service.file_path, doc_id)
    return FileResponse(path, filename=path.name)


@router.put("/documents/{doc_id}")
def update_document(doc_id: int, data: Dict[str, Any]):
    return _guard(service.update, doc_id, data)


@router.delete("/documents/{doc_id}")
def delete_document(doc_id: int):
    _guard(service.delete, doc_id)
    return {"status": "deleted"}


@router.post("/reindex")
async def reindex(project_id: Optional[int] = None):
    return await _aguard(service.reindex_existing(project_id))


@router.get("/obligations")
def obligations(project_id: int):
    return _guard(service.list_obligations, project_id)


@router.post("/obligations")
def save_obligation(data: Dict[str, Any]):
    return _guard(service.save_obligation, data)


@router.delete("/obligations/{obligation_id}")
def delete_obligation(obligation_id: int):
    _guard(service.delete_obligation, obligation_id)
    return {"status": "deleted"}


@router.post("/milestones")
def save_milestone(data: Dict[str, Any]):
    return _guard(service.save_milestone, data)


@router.delete("/milestones/{milestone_id}")
def delete_milestone(milestone_id: int):
    _guard(service.delete_milestone, milestone_id)
    return {"status": "deleted"}


@router.get("/timeline/{project_id}")
def timeline(project_id: int):
    return _guard(lifecycle.timeline, project_id)


@router.get("/alerts")
def alerts(project_id: Optional[int] = None):
    return _guard(lifecycle.alerts, project_id)


@router.get("/search")
async def search(q: str, project_id: Optional[int] = None):
    async def run():
        with unified_db.connect() as conn:
            rows, mode = await index.hybrid(conn, q, project_id, 10)
        return {"mode": mode, "results": [{"document_id": r["DocumentId"], "title": r["Title"], "doc_type": r["DocType"], "page": r["Page"],
                                           "snippet": r.get("snip") or r["Text"][:240]} for r in rows]}
    return await _aguard(run())


@router.post("/ask")
async def ask(data: Dict[str, Any]):
    return await _aguard(qa.ask(data.get("question", ""), data.get("project_id")))


# --- Classement : arborescence et dossiers (Lot 9) ----------------------------------------------------------------
from backend.tools.ged import folders as _folders


def _fguard(func, *args):
    try:
        return func(*args)
    except (_folders.FolderError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except unified_db.UnifiedDbUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/tree")
def folder_tree():
    return _fguard(_folders.tree)


@router.get("/tree/documents")
def tree_documents(year: Optional[str] = None, project_id: Optional[int] = None, doc_type: Optional[str] = None, folder_id: Optional[int] = None):
    return _fguard(_folders.documents, year, project_id, doc_type, folder_id)


@router.post("/folders")
def create_folder(data: Dict[str, Any]):
    return _fguard(_folders.create_folder, data)


@router.put("/folders/{folder_id}")
def rename_folder(folder_id: int, data: Dict[str, Any]):
    _fguard(_folders.rename_folder, folder_id, data.get("name", ""))
    return {"id": folder_id}


@router.delete("/folders/{folder_id}")
def delete_folder(folder_id: int):
    _fguard(_folders.delete_folder, folder_id)
    return {"deleted": folder_id}


@router.post("/documents/{doc_id}/local-copy")
def local_copy(doc_id: int):
    return {"path": _fguard(_folders.mirror_document, doc_id)}
