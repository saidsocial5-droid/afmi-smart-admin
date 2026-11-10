from fastapi import APIRouter
from pathlib import Path
from backend.config.settings import settings
from backend.core.agent_registry import agent_registry

router = APIRouter(prefix="/api/plugins", tags=["Plugins & Extensibility"])

@router.get("")
def list_plugins():
    plugins = []
    p_dir = settings.plugins_dir
    for p_file in p_dir.glob("*.py"):
        if p_file.name.startswith("__"):
            continue
        plugins.append({
            "filename": p_file.name,
            "path": str(p_file),
            "size_bytes": p_file.stat().st_size,
            "status": "Loaded & Active"
        })
    return {
        "plugins": plugins,
        "total_active": len(plugins)
    }

@router.post("/reload")
def reload_plugins():
    agent_registry.load_plugins()
    return {"status": "success", "message": "Plugins rechargés dynamiquement avec succès."}
