import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional

from backend.config.settings import settings
from backend.core.llm_router import llm_router
from backend.core import dpapi, privacy, unified_db

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
    key_persisted = None
    if req.gemini_key is not None:
        llm_router.set_gemini_key(req.gemini_key)
        key_persisted = persist_gemini_key(req.gemini_key)
    if req.gemini_model is not None:
        llm_router.gemini_model = req.gemini_model
    if req.ollama_url is not None:
        llm_router.set_ollama_url(req.ollama_url)
    if req.ollama_model is not None:
        llm_router.ollama_model = req.ollama_model
    if req.provider:
        settings.default_provider = req.provider

    message = "Paramètres LLM mis à jour avec succès."
    if key_persisted is False:
        message += " La clé n'est conservée que jusqu'à la fermeture (stockage chiffré indisponible)."
    return {"status": "success", "message": message, "key_persisted": key_persisted}


GEMINI_KEY_SETTING = "ai.gemini.api_key"


def persist_gemini_key(key: str) -> bool:
    """Clé chiffrée par DPAPI dans la base unique ; jamais en clair sur disque."""
    if not (dpapi.is_available() and unified_db.is_available()):
        return False
    unified_db.set_setting(GEMINI_KEY_SETTING, key, secret=True)
    return True


def load_persisted_gemini_key() -> None:
    if llm_router.gemini_key:
        return  # une clé fournie par l'environnement reste prioritaire
    key = unified_db.get_setting(GEMINI_KEY_SETTING, "") if unified_db.is_available() else ""
    if key:
        llm_router.set_gemini_key(key)


class PrivacyRequest(BaseModel):
    offline_mode: Optional[bool] = None
    mask_sensitive_data: Optional[bool] = None


@router.get("/privacy")
def get_privacy():
    return {
        "offline_mode": privacy.get(privacy.OFFLINE_KEY),
        "mask_sensitive_data": privacy.get(privacy.MASK_KEY),
        "secure_key_storage": dpapi.is_available() and unified_db.is_available(),
        "unified_database": unified_db.is_available(),
    }


@router.put("/privacy")
def update_privacy(req: PrivacyRequest):
    if req.offline_mode is not None:
        privacy.set_value(privacy.OFFLINE_KEY, req.offline_mode)
    if req.mask_sensitive_data is not None:
        privacy.set_value(privacy.MASK_KEY, req.mask_sensitive_data)
    return get_privacy()

@router.post("/llm-test")
async def test_llm_connection(req: LLMTestRequest):
    res = await llm_router.test_provider(
        provider=req.provider,
        api_key=req.api_key,
        url=req.url
    )
    return res
