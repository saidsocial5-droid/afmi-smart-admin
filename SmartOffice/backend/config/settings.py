import os
import shutil
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
BUNDLED_CONFIG_DIR = BASE_DIR / "config"
PLUGINS_DIR = BASE_DIR / "plugins"

# Installed app: the install folder is read-only, so AFMI_DATA_DIR (set by the desktop host to
# %LocalAppData%\AFMI Smart Admin\SmartOffice) holds the database, uploads, exports and editable config.
# Development: everything stays under backend/ as before.
_data_dir_env = os.getenv("AFMI_DATA_DIR", "").strip()
if _data_dir_env:
    DATA_DIR = Path(_data_dir_env)
    CONFIG_DIR = DATA_DIR / "config"
else:
    DATA_DIR = BASE_DIR / "data"
    CONFIG_DIR = BUNDLED_CONFIG_DIR
UPLOADS_DIR = DATA_DIR / "uploads"
EXPORTS_DIR = DATA_DIR / "exports"
# Official DGI EDI schemas (.xsd) are dropped here by the user; exports are validated against them
EDI_SCHEMAS_DIR = DATA_DIR / "edi_schemas"

# Ensure runtime directories exist
for _d in (DATA_DIR, CONFIG_DIR, UPLOADS_DIR, EXPORTS_DIR, EDI_SCHEMAS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# First run with an external data dir: seed the editable config files from the bundled defaults
if CONFIG_DIR != BUNDLED_CONFIG_DIR:
    for _name in ("ngo_profile.json", "rss_feeds.json", "edi_9421_config.json"):
        if not (CONFIG_DIR / _name).exists() and (BUNDLED_CONFIG_DIR / _name).exists():
            shutil.copy2(BUNDLED_CONFIG_DIR / _name, CONFIG_DIR / _name)

_frontend_env = os.getenv("AFMI_FRONTEND_DIST", "").strip()
FRONTEND_DIST_DIR = Path(_frontend_env) if _frontend_env else BASE_DIR.parent / "frontend" / "dist"

class AppSettings(BaseModel):
    app_name: str = "AFMI-SmartOffice"
    app_title_ar: str = "المكتب الذكي للجمعية - إفران"
    version: str = "1.3.0"
    db_url: str = f"sqlite:///{DATA_DIR / 'afmi_smartoffice.db'}"

    # LLM Settings
    default_provider: str = os.getenv("LLM_PROVIDER", "gemini")  # "gemini" or "ollama"
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.1")
    ollama_vision_model: str = os.getenv("OLLAMA_VISION_MODEL", "llama3.2-vision")

    # Paths
    base_dir: Path = BASE_DIR
    data_dir: Path = DATA_DIR
    ngo_profile_path: Path = CONFIG_DIR / "ngo_profile.json"
    rss_feeds_path: Path = CONFIG_DIR / "rss_feeds.json"
    # Legal rules ship with the app (read-only) so a new version always brings the latest finance-law rules
    payroll_rules_path: Path = BUNDLED_CONFIG_DIR / "payroll_rules_ma.json"
    edi_9421_config_path: Path = CONFIG_DIR / "edi_9421_config.json"
    edi_schemas_dir: Path = EDI_SCHEMAS_DIR
    uploads_dir: Path = UPLOADS_DIR
    exports_dir: Path = EXPORTS_DIR
    plugins_dir: Path = PLUGINS_DIR
    frontend_dist_dir: Path = FRONTEND_DIST_DIR

settings = AppSettings()
