import json
from typing import Any, Dict

from backend.config.settings import BUNDLED_CONFIG_DIR, settings


def load() -> Dict[str, Any]:
    user = settings.data_dir / "config" / "lifecycle_config.json"
    path = user if user.exists() else BUNDLED_CONFIG_DIR / "lifecycle_config.json"
    return json.loads(path.read_text(encoding="utf-8"))
