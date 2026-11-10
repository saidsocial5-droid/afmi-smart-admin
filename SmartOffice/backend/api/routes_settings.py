import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional

from backend.config.settings import settings
from backend.core.llm_router import llm_router

router = APIRouter(prefix="/api/settings", tags=["Settings & Memory"])

class LLMConfigRequest(BaseModel):
    provider: str
    gemini_key: Optional[str] = None
    gemini_model: Optional[str] = None
    ollama_url: Optional[str] = None
    ollama_model: Optional[str] = None

class LLMTestRequest(BaseModel):
    provider: str
    api_key: Optional[str] = None
    url: Optional[str] = None

@router.get("/ngo-profile")
def get_ngo_profile():
    try:
        with open(settings.ngo_profile_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/ngo-profile")
def update_ngo_profile(data: Dict[str, Any]):
    try:
        with open(settings.ngo_profile_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return {"status": "success", "message": "Mémoire institutionnelle mise à jour."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/llm-config")
def get_llm_config():
    return {
        "current_provider": settings.default_provider,
        "gemini_configured": bool(llm_router.gemini_key),
        "gemini_model": llm_router.gemini_model,
        "ollama_url": llm_router.ollama_url,
        "ollama_model": llm_router.ollama_model,
        "ollama_vision_model": llm_router.ollama_vision_model
    }

@router.post("/llm-config")
def update_llm_config(req: LLMConfigRequest):
    if req.gemini_key is not None:
        llm_router.set_gemini_key(req.gemini_key)
    if req.gemini_model is not None:
        llm_router.gemini_model = req.gemini_model
    if req.ollama_url is not None:
        llm_router.set_ollama_url(req.ollama_url)
    if req.ollama_model is not None:
        llm_router.ollama_model = req.ollama_model
    if req.provider:
        settings.default_provider = req.provider

    return {"status": "success", "message": "Paramètres LLM mis à jour avec succès."}

@router.post("/llm-test")
async def test_llm_connection(req: LLMTestRequest):
    res = await llm_router.test_provider(
        provider=req.provider,
        api_key=req.api_key,
        url=req.url
    )
    return res
