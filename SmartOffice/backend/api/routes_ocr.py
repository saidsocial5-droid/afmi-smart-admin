import os
import re
import shutil
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.tools.ocr_engine import ocr_engine
from backend.core.database import get_db, FinancialTransactionModel
from backend.config.settings import settings

router = APIRouter(prefix="/api/ocr", tags=["OCR & Vision"])

ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}

def sanitize_upload_filename(filename: Optional[str]) -> str:
    """Keep only the base name (no directories, no '..') and restrict to supported document types."""
    base = Path((filename or "").replace("\\", "/")).name
    stem = re.sub(r"[^\w\-.]", "_", Path(base).stem, flags=re.UNICODE).strip("._") or "document"
    ext = Path(base).suffix.lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Type de fichier non pris en charge. Formats acceptés : {', '.join(sorted(ALLOWED_UPLOAD_EXTENSIONS))}"
        )
    return f"{stem[:80]}_{uuid.uuid4().hex[:8]}{ext}"

class BatchSaveTransactionsRequest(BaseModel):
    source_file: str
    file_type: str = "bank_statement"
    transactions: List[Dict[str, Any]]

@router.post("/upload-and-parse")
async def upload_and_parse_document(
    file: UploadFile = File(...),
    doc_type: str = Form("auto"),  # bank_statement, invoice, auto
    provider: Optional[str] = Form(None)
):
    """Uploads a PDF or Image, extracts text & tables, and executes Vision AI analysis."""
    safe_name = sanitize_upload_filename(file.filename)
    target_path = settings.uploads_dir / safe_name

    # Save uploaded file
    with open(target_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        extraction_result = await ocr_engine.process_document(
            file_path=str(target_path),
            doc_hint=doc_type,
            provider=provider
        )
        extraction_result["filename"] = safe_name
        extraction_result["file_size_kb"] = round(os.path.getsize(target_path) / 1024, 2)
        return extraction_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'extraction OCR : {str(e)}")

@router.post("/batch-save")
def batch_save_transactions(req: BatchSaveTransactionsRequest, db: Session = Depends(get_db)):
    """Persist verified OCR transactions directly to database."""
    created_records = []
    for tx in req.transactions:
        record = FinancialTransactionModel(
            source_file=req.source_file,
            file_type=req.file_type,
            tx_date=tx.get("date", tx.get("tx_date", "")),
            reference=tx.get("reference", ""),
            label=tx.get("description", tx.get("label", "Opération")),
            beneficiary_or_emitter=tx.get("beneficiary", tx.get("beneficiary_or_emitter", "")),
            debit=float(tx.get("debit", 0.0) or 0.0),
            credit=float(tx.get("credit", 0.0) or 0.0),
            balance=float(tx.get("balance", 0.0) or 0.0),
            category=tx.get("category", "Divers"),
            strategic_axis=tx.get("strategic_axis", "Forest ecosystems conservation and biodiversity monitoring in the Middle Atlas"),
            status=tx.get("status", "Validated")
        )
        db.add(record)
        created_records.append(record)

    db.commit()
    return {
        "status": "success",
        "saved_count": len(created_records),
        "message": f"{len(created_records)} transactions comptables enregistrées avec succès."
    }

@router.get("/sample-documents")
def get_sample_documents():
    """Provides instant sample documents for immediate testing."""
    return [
        {
            "id": "sample_releve_bp",
            "name": "Relevé Bancaire Banque Populaire - Août 2026",
            "type": "bank_statement",
            "description": "Extrait de compte officiel comportant 4 opérations (virements bailleurs, achats matériel, appui coopératives)."
        },
        {
            "id": "sample_facture_hydrotech",
            "name": "Facture HydroTech Maroc N° 2026-089",
            "type": "invoice",
            "description": "Facture d'achat de sondes de prélèvement d'eau avec mentions fiscales marocaines (ICE, TVA 20%)."
        }
    ]
