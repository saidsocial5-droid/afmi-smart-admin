"""Assistant de rédaction des champs de saisie (Lot 11)."""
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from backend.tools import assist

router = APIRouter(prefix="/api/assist", tags=["Assistant de rédaction"])


@router.post("/text")
async def text(body: Dict[str, Any]):
    try:
        return await assist.run(body.get("action", ""), body.get("text", ""), body.get("field", ""), body.get("context", ""),
                                body.get("language", ""), body.get("target", ""))
    except assist.AssistError as e:
        raise HTTPException(status_code=400, detail=str(e))
