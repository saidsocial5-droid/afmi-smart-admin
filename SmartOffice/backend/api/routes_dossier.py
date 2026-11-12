"""Import intelligent d'un dossier de projet (Lot 10) et suivi du cofinancement."""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend.core import unified_db
from backend.tools.dossier import service

router = APIRouter(prefix="/api/dossier", tags=["Dossier de projet"])
MAX_BYTES = 40 * 1024 * 1024


def _guard(fn, *a, **kw):
    try:
        return fn(*a, **kw)
    except service.DossierError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except unified_db.UnifiedDbUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/analyze")
async def analyze(files: List[UploadFile] = File(...), project_id: Optional[int] = Form(None), use_ai: bool = Form(True)):
    data = []
    for f in files:
        content = await f.read()
        if len(content) > MAX_BYTES:
            raise HTTPException(status_code=413, detail=f"{f.filename} dépasse 40 Mo.")
        data.append((f.filename or "document", content))
    try:
        return await service.analyze(data, project_id, use_ai)
    except service.DossierError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except unified_db.UnifiedDbUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/imports")
def imports(project_id: Optional[int] = None):
    return _guard(service.list_imports, project_id)


@router.get("/imports/{import_id}")
def get_import(import_id: int):
    return _guard(service.get, import_id)


@router.put("/imports/{import_id}")
def save_import(import_id: int, body: Dict[str, Any]):
    return _guard(service.save, import_id, body.get("result") or {}, body.get("project_id"))


@router.post("/imports/{import_id}/apply")
async def apply_import(import_id: int, body: Dict[str, Any]):
    try:
        return await service.apply(import_id, body or {})
    except service.DossierError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except unified_db.UnifiedDbUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/projects")
def projects():
    with unified_db.connect() as conn:
        return [dict(id=r["Id"], code=r["Code"], name=r["Name"]) for r in
                conn.execute("SELECT Id, Code, Name FROM Projects WHERE IsDeleted = 0 ORDER BY Code")]


@router.get("/cofinancing/{project_id}")
def cofinancing(project_id: int):
    return _guard(service.cofinancing, project_id)


@router.post("/cofinancing/contributions/{contribution_id}/entries")
def add_entry(contribution_id: int, body: Dict[str, Any]):
    return _guard(service.add_cofinancing_entry, contribution_id, body or {})


@router.get("/cofinancing/{project_id}/journal")
def journal(project_id: int):
    return _guard(service.in_kind_journal, project_id)
