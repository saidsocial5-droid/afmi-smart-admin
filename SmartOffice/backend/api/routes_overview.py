"""Liaisons entre les modules (Lot 9) : vue 360° d'un projet, recherche unifiée."""
from fastapi import APIRouter, HTTPException

from backend.core import unified_db
from backend.tools import overview

router = APIRouter(tags=["Vue d'ensemble"])


@router.get("/api/overview/project/{project_id}")
def project_overview(project_id: int):
    try:
        return overview.project_overview(project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except unified_db.UnifiedDbUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/api/search")
def search(q: str):
    try:
        return overview.search(q)
    except unified_db.UnifiedDbUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
