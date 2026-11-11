"""API des relevés bancaires (Lot 3) : import, écran de validation, intégration en brouillons."""
import sqlite3
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from backend.core import unified_db
from backend.tools.statements import ocr, store
from backend.tools.statements.ai_extract import extract_with_ai
from backend.tools.statements.pipeline import process, process_pages

router = APIRouter(prefix="/api/statements", tags=["Relevés bancaires"])

MAX_FILE_BYTES = 25 * 1024 * 1024
ALLOWED = {".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp", ".csv", ".txt", ".xlsx", ".xlsm"}


def _guard(func, *args):
    try:
        return func(*args)
    except store.StatementError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except unified_db.UnifiedDbUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=f"Enregistrement refusé par la base : {e}")


@router.get("/context")
def get_context():
    data = _guard(store.context)
    data["ocr_available"] = ocr.find_tesseract() is not None
    return data


@router.get("")
def list_statements(account_id: Optional[int] = None):
    return _guard(store.list_statements, account_id)


@router.post("/upload")
async def upload(account_id: int = Form(...), mode: str = Form("documents"), use_ai: bool = Form(False),
                 files: List[UploadFile] = File(...)):
    """mode « documents » : chaque fichier est un relevé ; « pages » : les images sont les pages d'un même relevé."""
    blobs = []
    for f in files:
        name = (f.filename or "releve").replace("\\", "/").split("/")[-1]
        ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if ext not in ALLOWED:
            raise HTTPException(status_code=400, detail=f"« {name} » : format non pris en charge (PDF, JPG, PNG, TIFF, CSV, XLSX).")
        data = await f.read()
        if len(data) > MAX_FILE_BYTES:
            raise HTTPException(status_code=400, detail=f"« {name} » dépasse 25 Mo.")
        blobs.append((data, name))

    groups = [blobs] if mode == "pages" and len(blobs) > 1 else [[b] for b in blobs]
    results: List[Dict[str, Any]] = []
    for group in groups:
        name = group[0][1] if len(group) == 1 else f"{group[0][1]} (+{len(group) - 1} page(s))"
        try:
            result = process(*group[0]) if len(group) == 1 else process_pages(group)
            if use_ai and result.statement.balance_ok() is False and result.page_images:
                text = "\n".join(f"{l.date} {l.label} {l.debit / 100:.2f} {l.credit / 100:.2f}" for l in result.statement.lines)
                ai = await extract_with_ai(text, result.page_images, result.statement)
                if ai is not None:
                    for a, o in zip(ai.lines, result.statement.lines):
                        a.page, a.y = o.page, o.y
                    result.statement = ai
            data = b"".join(d for d, _ in group)
            statement_id = _guard(store.save_extraction, account_id, result, data, group[0][1])
            results.append({"file": name, "statement_id": statement_id, "lines": len(result.statement.lines),
                            "engine": result.statement.engine, "balance_ok": result.statement.balance_ok(),
                            "warnings": result.statement.warnings})
        except HTTPException as e:
            results.append({"file": name, "error": e.detail})
        except (ValueError, ocr.OcrUnavailable) as e:
            results.append({"file": name, "error": str(e)})
    return {"results": results}


@router.get("/{statement_id}")
def get_statement(statement_id: int):
    return _guard(store.get_statement, statement_id)


@router.get("/{statement_id}/pages/{page}")
def get_page(statement_id: int, page: int):
    path = _guard(store.page_image, statement_id, page)
    return FileResponse(path, media_type="image/png")


@router.put("/{statement_id}")
def save(statement_id: int, payload: Dict[str, Any]):
    return _guard(store.save_corrections, statement_id, payload)


@router.post("/{statement_id}/validate")
def validate(statement_id: int):
    return _guard(store.validate, statement_id)


@router.post("/{statement_id}/integrate")
def integrate(statement_id: int):
    return _guard(store.integrate, statement_id)


@router.delete("/{statement_id}")
def delete(statement_id: int):
    _guard(store.delete, statement_id)
    return {"status": "deleted"}
