import json
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from backend.core.database import get_db, ProjectModel

router = APIRouter(prefix="/api/projects", tags=["Projects"])

class ProjectCreateRequest(BaseModel):
    code: str
    title: str
    donor: str
    total_budget: float = 0.0
    spent_budget: float = 0.0
    currency: Optional[str] = "MAD"
    start_date: Optional[str] = ""
    end_date: Optional[str] = ""
    status: Optional[str] = "In Progress"
    location: Optional[str] = ""
    beneficiaries: Optional[str] = ""
    strategic_axis: Optional[str] = "Forest ecosystems conservation and biodiversity monitoring in the Middle Atlas"
    kpis: Optional[List[Dict[str, Any]]] = []

@router.get("")
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(ProjectModel).order_by(ProjectModel.id.desc()).all()
    out = []
    for p in projects:
        try:
            kpi_data = json.loads(p.kpis_json) if p.kpis_json else []
        except Exception:
            kpi_data = []
        out.append({
            "id": p.id,
            "code": p.code,
            "title": p.title,
            "donor": p.donor,
            "total_budget": p.total_budget,
            "spent_budget": p.spent_budget,
            "burn_rate": round((p.spent_budget / p.total_budget * 100), 1) if p.total_budget > 0 else 0,
            "currency": p.currency,
            "start_date": p.start_date,
            "end_date": p.end_date,
            "status": p.status,
            "location": p.location,
            "beneficiaries": p.beneficiaries,
            "strategic_axis": p.strategic_axis,
            "kpis": kpi_data
        })
    return out

@router.post("")
def create_project(req: ProjectCreateRequest, db: Session = Depends(get_db)):
    existing = db.query(ProjectModel).filter(ProjectModel.code == req.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Un projet avec ce code existe déjà.")

    p = ProjectModel(
        code=req.code,
        title=req.title,
        donor=req.donor,
        total_budget=req.total_budget,
        spent_budget=req.spent_budget,
        currency=req.currency,
        start_date=req.start_date,
        end_date=req.end_date,
        status=req.status,
        location=req.location,
        beneficiaries=req.beneficiaries,
        strategic_axis=req.strategic_axis,
        kpis_json=json.dumps(req.kpis or [])
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p

@router.put("/{project_id}")
def update_project(project_id: int, req: ProjectCreateRequest, db: Session = Depends(get_db)):
    p = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Projet non trouvé.")
    
    p.code = req.code
    p.title = req.title
    p.donor = req.donor
    p.total_budget = req.total_budget
    p.spent_budget = req.spent_budget
    p.currency = req.currency
    p.start_date = req.start_date
    p.end_date = req.end_date
    p.status = req.status
    p.location = req.location
    p.beneficiaries = req.beneficiaries
    p.strategic_axis = req.strategic_axis
    p.kpis_json = json.dumps(req.kpis or [])
    
    db.commit()
    db.refresh(p)
    return p

@router.delete("/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    p = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Projet non trouvé.")
    db.delete(p)
    db.commit()
    return {"status": "success", "message": "Projet supprimé."}
