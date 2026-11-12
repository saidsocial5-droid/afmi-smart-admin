"""Exports Word, PDF et Excel (Lot 7)."""
import sqlite3
from typing import Any, Dict, Optional
from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from backend.core import unified_db
from backend.tools.editor.documents import EditorError
from backend.tools.ged.service import GedError
from backend.tools.exports import naming, pdf, service
from backend.tools.exports.resolve import ExportError

router = APIRouter(prefix="/api/exports", tags=["Exports"])


def _file(data: bytes, name: str) -> Response:
    ext = name.rsplit(".", 1)[-1]
    ascii_name = name.encode("ascii", "ignore").decode() or f"export.{ext}"
    return Response(content=data, media_type=service.MIME.get(ext, "application/octet-stream"),
                    headers={"Content-Disposition": f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(name)}",
                             "X-AFMI-Filename": quote(name)})


def _guard(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except pdf.PdfError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except (EditorError, GedError, ExportError, ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e).strip("'"))
    except unified_db.UnifiedDbUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Erreur de base de données : {e}")


@router.get("/engines")
def engines():
    """Moteurs PDF détectés et modèles de nommage (pour l'écran des paramètres)."""
    found = pdf.engines()
    return {"pdf": {"browser": bool(found["browser"]), "libreoffice": bool(found["libreoffice"]), "pdfa": bool(found["libreoffice"]),
                    "browser_path": found["browser"], "libreoffice_path": found["libreoffice"]},
            "naming": {k: unified_db.get_setting(k, v) if unified_db.is_available() else v for k, v in naming.DEFAULTS.items()},
            "examples": {"report": naming.file_name("pdf", "financial", 2026, "fr"),
                         "document": naming.file_name("docx", "document", title="Rapport narratif S1")}}


@router.get("/naming-preview")
def naming_preview(pattern: str, kind: str = "financial"):
    return {"name": naming.file_name("pdf", kind, 2026, "fr", title="Rapport narratif S1", project="P-CEDRE", pattern=pattern)}


@router.get("/document/{doc_id}")
def export_document(doc_id: int, format: str = "docx", pdfa: bool = False):
    return _file(*_guard(service.document, doc_id, format, pdfa))


@router.get("/statements")
def export_statements(year: int, scope_type: str = "association", scope_id: Optional[int] = None, lang: str = "fr"):
    return _file(*_guard(service.statements, year, scope_type, scope_id, lang))


@router.get("/operations")
def export_operations(account_id: Optional[int] = None, date_from: Optional[str] = None, date_to: Optional[str] = None):
    return _file(*_guard(service.operations, account_id, date_from, date_to))


@router.get("/reconciliation/{statement_id}")
def export_reconciliation(statement_id: int):
    return _file(*_guard(service.reconciliation, statement_id))


@router.post("/annual-package")
async def export_annual_package(data: Dict[str, Any]):
    try:
        content, name = await service.annual_package(
            int(data["year"]), data.get("scope_type") or "association", data.get("scope_id"), data.get("language") or "fr",
            data.get("moral_document_id"), data.get("financial_document_id"), data.get("annex_ids") or [],
            data.get("formats") or ["pdf", "docx", "xlsx"], bool(data.get("pdfa")))
    except pdf.PdfError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except (EditorError, GedError, ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e).strip("'"))
    except unified_db.UnifiedDbUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    return _file(content, name)
