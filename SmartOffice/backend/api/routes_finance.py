from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from pathlib import Path

from backend.core.database import get_db, FinancialTransactionModel
from backend.tools.exporters import export_to_excel

router = APIRouter(prefix="/api/finance", tags=["Finance & Ledger"])

class TransactionCreateRequest(BaseModel):
    source_file: Optional[str] = "Saisie Manuelle"
    file_type: Optional[str] = "manual"
    tx_date: str
    reference: Optional[str] = ""
    label: str
    beneficiary_or_emitter: Optional[str] = ""
    debit: float = 0.0
    credit: float = 0.0
    balance: float = 0.0
    category: str = "Divers"
    strategic_axis: str = "Forest ecosystems conservation and biodiversity monitoring in the Middle Atlas"
    status: str = "Validated"

@router.get("/transactions")
def list_transactions(
    status: Optional[str] = None,
    axis: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(FinancialTransactionModel)
    if status:
        query = query.filter(FinancialTransactionModel.status == status)
    if axis:
        query = query.filter(FinancialTransactionModel.strategic_axis == axis)
    
    records = query.order_by(FinancialTransactionModel.tx_date.desc(), FinancialTransactionModel.id.desc()).all()
    return records

@router.post("/transactions")
def create_transaction(req: TransactionCreateRequest, db: Session = Depends(get_db)):
    tx = FinancialTransactionModel(**req.dict())
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx

@router.put("/transactions/{tx_id}")
def update_transaction(tx_id: int, req: TransactionCreateRequest, db: Session = Depends(get_db)):
    tx = db.query(FinancialTransactionModel).filter(FinancialTransactionModel.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction non trouvée.")
    for k, v in req.dict().items():
        setattr(tx, k, v)
    db.commit()
    db.refresh(tx)
    return tx

@router.delete("/transactions/{tx_id}")
def delete_transaction(tx_id: int, db: Session = Depends(get_db)):
    tx = db.query(FinancialTransactionModel).filter(FinancialTransactionModel.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction non trouvée.")
    db.delete(tx)
    db.commit()
    return {"status": "success", "message": "Transaction supprimée."}

@router.get("/summary")
def get_financial_summary(db: Session = Depends(get_db)):
    transactions = db.query(FinancialTransactionModel).all()
    total_income = sum(t.credit for t in transactions)
    total_expenses = sum(t.debit for t in transactions)
    current_balance = total_income - total_expenses

    # Breakdown by strategic axis
    axis_breakdown = {}
    for t in transactions:
        axis = t.strategic_axis or "Non Classifié"
        if axis not in axis_breakdown:
            axis_breakdown[axis] = {"income": 0.0, "expense": 0.0}
        axis_breakdown[axis]["income"] += t.credit
        axis_breakdown[axis]["expense"] += t.debit

    # Breakdown by category
    cat_breakdown = {}
    for t in transactions:
        cat = t.category or "Divers"
        cat_breakdown[cat] = cat_breakdown.get(cat, 0.0) + t.debit

    return {
        "total_income": round(total_income, 2),
        "total_expenses": round(total_expenses, 2),
        "current_balance": round(current_balance, 2),
        "transaction_count": len(transactions),
        "axis_breakdown": axis_breakdown,
        "category_breakdown": cat_breakdown
    }

@router.get("/export-excel")
def export_transactions_excel(db: Session = Depends(get_db)):
    records = db.query(FinancialTransactionModel).order_by(FinancialTransactionModel.tx_date.asc()).all()
    tx_list = [
        {
            "tx_date": r.tx_date,
            "reference": r.reference,
            "label": r.label,
            "beneficiary_or_emitter": r.beneficiary_or_emitter,
            "debit": r.debit,
            "credit": r.credit,
            "balance": r.balance,
            "category": r.category,
            "strategic_axis": r.strategic_axis,
            "status": r.status
        }
        for r in records
    ]
    file_path = export_to_excel(tx_list)
    return FileResponse(
        path=file_path,
        filename=Path(file_path).name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
