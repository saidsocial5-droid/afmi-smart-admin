from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from backend.core.database import get_db, GrantPipelineModel
from backend.tools.grant_scanner import grant_scanner, OFFICIAL_DONOR_PORTALS

router = APIRouter(prefix="/api/grants", tags=["Grants Pipeline"])

class GrantCreateRequest(BaseModel):
    title: str
    donor: str
    funding_program: Optional[str] = ""
    amount_requested: float = 0.0
    currency: Optional[str] = "MAD"
    strategic_axis: Optional[str] = "Forest ecosystems conservation and biodiversity monitoring in the Middle Atlas"
    status: Optional[str] = "Draft"
    deadline: Optional[str] = ""
    submission_date: Optional[str] = ""
    focal_point: Optional[str] = ""
    summary: Optional[str] = ""

class InternetGrantSearchRequest(BaseModel):
    keywords: Optional[str] = ""
    category: Optional[str] = "all"  # all, national, international, marches_publics
    theme: Optional[str] = "all"
    provider: Optional[str] = None

class ImportOpportunityRequest(BaseModel):
    title: str
    donor: str
    portal_url: Optional[str] = ""
    amount_mad: Optional[float] = 0.0
    currency: Optional[str] = "MAD"
    deadline: Optional[str] = ""
    strategic_axis: Optional[str] = "Forest ecosystems conservation and biodiversity monitoring in the Middle Atlas"
    eligibility_summary: Optional[str] = ""
    action_recommendation: Optional[str] = ""

@router.get("")
def list_grants(db: Session = Depends(get_db)):
    return db.query(GrantPipelineModel).order_by(GrantPipelineModel.id.desc()).all()

@router.post("")
def create_grant(req: GrantCreateRequest, db: Session = Depends(get_db)):
    grant = GrantPipelineModel(**req.dict())
    db.add(grant)
    db.commit()
    db.refresh(grant)
    return grant

@router.put("/{grant_id}")
def update_grant(grant_id: int, req: GrantCreateRequest, db: Session = Depends(get_db)):
    grant = db.query(GrantPipelineModel).filter(GrantPipelineModel.id == grant_id).first()
    if not grant:
        raise HTTPException(status_code=404, detail="Subvention non trouvée.")
    for k, v in req.dict().items():
        setattr(grant, k, v)
    db.commit()
    db.refresh(grant)
    return grant

@router.delete("/{grant_id}")
def delete_grant(grant_id: int, db: Session = Depends(get_db)):
    grant = db.query(GrantPipelineModel).filter(GrantPipelineModel.id == grant_id).first()
    if not grant:
        raise HTTPException(status_code=404, detail="Subvention non trouvée.")
    db.delete(grant)
    db.commit()
    return {"status": "success", "message": "Opportunité supprimée."}

@router.post("/search-internet")
async def search_internet_grants(req: InternetGrantSearchRequest):
    """Scan internet portals & synthesize live grant opportunities for AFMI."""
    try:
        opportunities = await grant_scanner.search_live_opportunities(
            keywords=req.keywords or "",
            category=req.category or "all",
            theme=req.theme or "all",
            provider=req.provider
        )
        return {
            "status": "success",
            "query": req.keywords,
            "count": len(opportunities),
            "opportunities": opportunities
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur de recherche d'opportunités : {str(e)}")

@router.post("/import-opportunity")
def import_opportunity(req: ImportOpportunityRequest, db: Session = Depends(get_db)):
    """Directly save a discovered online grant opportunity into the AFMI Grants Pipeline."""
    summary_text = f"{req.eligibility_summary}\n\nRecommandation stratégique : {req.action_recommendation}"
    if req.portal_url:
        summary_text += f"\nLien officiel du portail : {req.portal_url}"

    grant = GrantPipelineModel(
        title=req.title,
        donor=req.donor,
        funding_program=f"Portail : {req.portal_url[:50]}..." if req.portal_url else "Appel Web Détecté",
        amount_requested=req.amount_mad or 0.0,
        currency=req.currency or "MAD",
        strategic_axis=req.strategic_axis,
        status="Draft",
        deadline=req.deadline,
        focal_point="Chargé de Mobilisation des Ressources AFMI",
        summary=summary_text
    )
    db.add(grant)
    db.commit()
    db.refresh(grant)
    return {
        "status": "success",
        "message": f"L'opportunité '{req.title}' a été importée dans le pipeline de subventions.",
        "grant": grant
    }

@router.get("/donor-portals")
def get_donor_portals():
    """List curated Moroccan and international donor portals with direct links."""
    return OFFICIAL_DONOR_PORTALS
