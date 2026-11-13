import json
import os
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


# --- Panneau de paramètres avancé (Lot 7) ---------------------------------------------------------------------
import sqlite3 as _sqlite3

from fastapi.responses import JSONResponse

from backend.core import ai_config, ai_providers, backups, config_files, roles, settings_registry, smtp


def _guard(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except (settings_registry.SettingsError, backups.BackupError, smtp.SmtpError, ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e).strip("'"))
    except unified_db.UnifiedDbUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    except _sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Erreur de base de données : {e}")


@router.get("/registry")
def registry():
    return _guard(settings_registry.snapshot)


@router.get("/me")
def me():
    role = roles.current_role()
    return {"user": unified_db.current_user(), "role": role or "Administrateur", "single_user": role is None}


@router.put("/values")
def save_values(data: Dict[str, Any]):
    return {"saved": _guard(settings_registry.save, data.get("values") or {})}


@router.post("/reset")
def reset(data: Dict[str, Any]):
    if data.get("all"):
        keys = [f.key for f in settings_registry.FIELDS]
    elif data.get("section"):
        keys = settings_registry.section_keys(data["section"])
        if not keys:
            raise HTTPException(status_code=400, detail="Section inconnue.")
    else:
        keys = data.get("keys") or []
    return {"reset": _guard(settings_registry.reset, keys)}


@router.put("/secret")
def save_secret(data: Dict[str, Any]):
    _guard(settings_registry.set_secret, data.get("key", ""), data.get("value", ""))
    return {"configured": bool((data.get("value") or "").strip())}


@router.get("/export")
def export_settings():
    payload = _guard(settings_registry.export_json)
    return JSONResponse(payload, headers={"Content-Disposition": 'attachment; filename="AFMI_parametres.json"',
                                          "X-AFMI-Filename": "AFMI_parametres.json"})


@router.post("/import")
def import_settings(data: Dict[str, Any]):
    return _guard(settings_registry.import_json, data.get("data"), bool(data.get("dry_run")))


@router.get("/files/{name}")
def get_config_file(name: str):
    return _guard(lambda: {"name": name, "description": settings_registry.CONFIG_FILES.get(name, ""), "content": config_files.read(name),
                           "customized": config_files.is_customized(name), "default": config_files.default(name)})


@router.put("/files/{name}")
def save_config_file(name: str, data: Dict[str, Any]):
    _guard(config_files.write, name, data.get("content"))
    return get_config_file(name)


@router.delete("/files/{name}")
def restore_config_file(name: str):
    _guard(config_files.restore, name)
    return get_config_file(name)


@router.post("/ai/test")
async def ai_test(data: Dict[str, Any]):
    return await ai_providers.test(data.get("provider", ""), data.get("api_key"), data.get("base_url"))


@router.get("/ai/catalog")
def ai_catalog():
    return {"providers": ai_config.PROVIDERS, "tasks": ai_config.TASKS, "prompts": ai_config.PROMPTS, "usage": ai_config.usage()}


@router.get("/backups")
def list_backups():
    return _guard(lambda: {"folder": str(backups.folder()), "items": backups.list_backups(), "pending": backups.pending()})


@router.post("/backups")
def create_backup():
    return _guard(backups.create, "manuel")


@router.post("/backups/restore")
def schedule_restore(data: Dict[str, Any]):
    return _guard(backups.schedule_restore, data.get("name", ""))


@router.delete("/backups/restore")
def cancel_restore():
    _guard(backups.cancel_restore)
    return {"pending": None}


@router.get("/smtp")
def get_smtp():
    return _guard(smtp.get)


@router.put("/smtp")
def save_smtp(data: Dict[str, Any]):
    return _guard(smtp.save, data)


@router.post("/smtp/test")
def test_smtp(data: Dict[str, Any]):
    return {"sent_to": _guard(smtp.send_test, data.get("to", ""))}


@router.post("/notifications/send")
def send_notifications():
    from backend.core import notifications
    return _guard(notifications.run, True)


@router.get("/notifications/preview")
def preview_notifications():
    from backend.core import notifications
    return {"alerts": _guard(notifications.collect)}


APP_VERSION = "2.4.0"


@router.get("/header")
def header_info():
    """En-tête de Smart Office : identité, version, état réel de l'IA, trésorerie et budget de la base unique."""
    from datetime import date as _date
    from decimal import Decimal
    info = {"version": APP_VERSION, "demo": os.getenv("AFMI_DEMO") == "1", "offline": privacy.get(privacy.OFFLINE_KEY),
            "association": None, "acronym": None, "treasury_mad": None, "budget_mad": None}
    if not unified_db.is_available():
        return info
    from backend.tools.reports import finance
    info["association"] = unified_db.get_setting("association.name", "Association Forêt Modèle d'Ifrane")
    info["acronym"] = unified_db.get_setting("association.acronym", "AFMI")
    today = _date.today().isoformat()
    with unified_db.connect() as conn:
        total = 0
        for a in conn.execute("SELECT Id, Currency FROM BankAccounts WHERE IsDeleted = 0 AND Status = 'Active'"):
            rate = finance._rate(conn, a["Currency"], today)
            if rate is not None:
                total += int(Decimal(finance.book_balance(conn, a["Id"], today)) * rate)
        info["treasury_mad"] = total
        budget = 0
        for l in conn.execute("SELECT PlannedMinor, Currency FROM BudgetLines WHERE IsDeleted = 0"):
            rate = finance._rate(conn, l["Currency"], today)
            if rate is not None:
                budget += int(Decimal(l["PlannedMinor"]) * rate)
        info["budget_mad"] = budget
    return info
