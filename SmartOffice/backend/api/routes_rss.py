from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.tools.rss_processor import rss_processor
from backend.core.database import get_db, GrantPipelineModel

router = APIRouter(prefix="/api/rss", tags=["RSS Project Radar"])

class RssSearchRequest(BaseModel):
    keywords: Optional[str] = ""
    donor: Optional[str] = "all"
    axis: Optional[str] = "all"
    min_score: Optional[int] = 5
    force_refresh: Optional[bool] = False

class RssFeedCreateRequest(BaseModel):
    name: str
    url: str
    category: Optional[str] = "international"
    focus: Optional[str] = ""
    name_ar: Optional[str] = ""

class RssImportRequest(BaseModel):
    title: str
    donor: str
    link: Optional[str] = ""
    amount_mad: Optional[float] = 500000.0
    currency: Optional[str] = "MAD"
    deadline: Optional[str] = "2026-12-31"
    strategic_axis: Optional[str] = "حماية النظم الإيكولوجية الغابوية ورصد التنوع البيولوجي"
    summary_ar: Optional[str] = ""
    summary_fr: Optional[str] = ""
    action_recommendation: Optional[str] = ""

@router.get("/search")
async def search_projects_get(
    keywords: str = "",
    donor: str = "all",
    axis: str = "all",
    min_score: int = 5,
    force_refresh: bool = False
):
    """Search opportunities via RSS feeds using GET query parameters."""
    try:
        results = await rss_processor.fetch_and_analyze(
            keywords=keywords,
            donor_filter=donor,
            axis_filter=axis,
            min_score=min_score,
            force_refresh=force_refresh
        )
        return {
            "status": "success",
            "count": len(results),
            "projects": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RSS search failed: {str(e)}")

@router.post("/search")
async def search_projects_post(req: RssSearchRequest):
    """Search opportunities via RSS feeds using POST body."""
    try:
        results = await rss_processor.fetch_and_analyze(
            keywords=req.keywords or "",
            donor_filter=req.donor or "all",
            axis_filter=req.axis or "all",
            min_score=req.min_score or 5,
            force_refresh=req.force_refresh or False
        )
        return {
            "status": "success",
            "count": len(results),
            "projects": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RSS scan failed: {str(e)}")

@router.get("/feeds")
async def list_rss_feeds():
    """Return all configured RSS feeds with active status."""
    return {
        "status": "success",
        "count": len(rss_processor.get_feeds()),
        "feeds": rss_processor.get_feeds()
    }

@router.get("/config")
async def get_rss_config():
    """Backward compatibility endpoint for feed configurations."""
    feeds = rss_processor.get_feeds()
    return {
        "status": "success",
        "feeds": {f.get("name", f.get("id")): f.get("url") for f in feeds}
    }

@router.post("/feeds")
async def add_rss_feed(feed_req: RssFeedCreateRequest):
    """Add a new RSS feed to monitor."""
    if not feed_req.name or not feed_req.url:
        raise HTTPException(status_code=400, detail="Name and URL are required.")
    
    new_feed = rss_processor.add_feed(
        name=feed_req.name,
        url=feed_req.url,
        category=feed_req.category or "international",
        focus=feed_req.focus or "",
        name_ar=feed_req.name_ar or ""
    )
    return {
        "status": "success",
        "message": f"Flux RSS '{new_feed['name']}' ajouté avec succès.",
        "feed": new_feed
    }

@router.delete("/feeds/{feed_id}")
async def delete_rss_feed(feed_id: str):
    """Remove a monitored RSS feed."""
    removed = rss_processor.remove_feed(feed_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Feed not found.")
    return {
        "status": "success",
        "message": "Flux RSS supprimé."
    }

@router.post("/feeds/{feed_id}/toggle")
async def toggle_rss_feed(feed_id: str):
    """Toggle feed active/inactive."""
    new_state = rss_processor.toggle_feed(feed_id)
    if new_state is None:
        raise HTTPException(status_code=404, detail="Feed not found.")
    return {
        "status": "success",
        "is_active": new_state
    }

@router.post("/import")
async def import_rss_opportunity(req: RssImportRequest, db: Session = Depends(get_db)):
    """
    Import an opportunity detected via RSS directly into AFMI's Grants Pipeline (SQLite).
    """
    try:
        combined_summary = req.summary_ar or req.summary_fr or ""
        if req.action_recommendation:
            combined_summary += f"\n\n[نصيحة الإيداع]: {req.action_recommendation}"
        if req.link:
            combined_summary += f"\n[الرابط الأصلي للخلاصة]: {req.link}"

        new_grant = GrantPipelineModel(
            title=req.title,
            donor=req.donor,
            funding_program="Opportunité détectée via Flux RSS",
            amount_requested=float(req.amount_mad or 500000.0),
            currency=req.currency or "MAD",
            strategic_axis=req.strategic_axis or "حماية النظم الإيكولوجية الغابوية ورصد التنوع البيولوجي",
            status="Draft",
            deadline=req.deadline or "2026-12-31",
            focal_point="Responsable Montage Projets AFMI",
            summary=combined_summary
        )
        db.add(new_grant)
        db.commit()
        db.refresh(new_grant)

        return {
            "status": "success",
            "message": f"L'appel à projets '{new_grant.title}' a été importé dans le pipeline AFMI.",
            "grant_id": new_grant.id
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Échec de l'importation: {str(e)}")
