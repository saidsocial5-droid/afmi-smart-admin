"""Fichiers de configuration modifiables depuis les paramètres (Lot 7).

Le fichier livré avec l'application (backend/config) n'est jamais modifié : la version personnalisée est écrite dans
le dossier de données de l'utilisateur (config/<nom>.json), qui est déjà lu en priorité par les modules
(rapports, GED, relevés). « Restaurer » supprime la version personnalisée (une copie datée est conservée).
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from backend.config.settings import BUNDLED_CONFIG_DIR, settings
from backend.core import unified_db

NAMES = ("financial_report_layout", "lifecycle_config", "bank_templates")
LEVELS = ("blocking", "warning", "ignore")


def _user(name: str) -> Path:
    return settings.data_dir / "config" / f"{name}.json"


def _check(name: str) -> None:
    if name not in NAMES:
        raise ValueError(f"Fichier de configuration inconnu : {name}.")


def is_customized(name: str) -> bool:
    _check(name)
    return _user(name).exists()


def read(name: str) -> Dict[str, Any]:
    _check(name)
    path = _user(name) if _user(name).exists() else BUNDLED_CONFIG_DIR / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def default(name: str) -> Dict[str, Any]:
    _check(name)
    return json.loads((BUNDLED_CONFIG_DIR / f"{name}.json").read_text(encoding="utf-8"))


def validate(name: str, data: Any) -> None:
    """Contrôle de structure : une erreur ici évite qu'un fichier mal formé casse les rapports, la GED ou l'OCR."""
    _check(name)
    if not isinstance(data, dict):
        raise ValueError(f"{name} : objet JSON attendu.")
    if name == "financial_report_layout":
        cer = data.get("cer") or {}
        if not isinstance(cer.get("uses"), list) or not isinstance(cer.get("resources"), list):
            raise ValueError("financial_report_layout : sections « cer.uses » et « cer.resources » obligatoires.")
        for s in cer["uses"]:
            if s.get("source") not in ("projects", "operating") or not s.get("label"):
                raise ValueError("financial_report_layout : chaque emploi a un libellé et une source « projects » ou « operating ».")
        for s in cer["resources"]:
            if not s.get("label") or not isinstance(s.get("categories"), list):
                raise ValueError("financial_report_layout : chaque ressource a un libellé et une liste de catégories.")
        for code, level in (data.get("checks") or {}).items():
            if level not in LEVELS:
                raise ValueError(f"financial_report_layout : niveau « {level} » du contrôle {code} (blocking, warning ou ignore).")
        if "receipt_threshold_mad" in data and not isinstance(data["receipt_threshold_mad"], (int, float)):
            raise ValueError("financial_report_layout : receipt_threshold_mad doit être un nombre.")
    elif name == "lifecycle_config":
        phases = data.get("phases")
        if not isinstance(phases, list) or not phases or not isinstance(data.get("types"), dict):
            raise ValueError("lifecycle_config : « phases » (liste) et « types » (objet) obligatoires.")
        for phase, expected in (data.get("expected") or {}).items():
            if phase not in phases:
                raise ValueError(f"lifecycle_config : phase inconnue « {phase} » dans « expected ».")
            unknown = [t for t in expected if t not in data["types"]]
            if unknown:
                raise ValueError(f"lifecycle_config : type(s) inconnu(s) {', '.join(unknown)} attendu(s) en phase {phase}.")
        for t, spec in data["types"].items():
            if spec.get("phase") and spec["phase"] not in phases:
                raise ValueError(f"lifecycle_config : le type {t} renvoie à une phase inconnue.")
    elif name == "bank_templates":
        templates = data.get("templates")
        if not isinstance(templates, list) or not any(t.get("id") == "generique" for t in templates):
            raise ValueError("bank_templates : liste « templates » avec le gabarit « generique » obligatoire.")
        ids = [t.get("id") for t in templates]
        if len(ids) != len(set(ids)) or not all(ids):
            raise ValueError("bank_templates : chaque gabarit a un identifiant unique.")


def write(name: str, data: Dict[str, Any]) -> None:
    validate(name, data)
    path = _user(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.replace(path.with_name(f"{name}.{datetime.now():%Y%m%d_%H%M%S}.bak.json"))
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    if unified_db.is_available():
        with unified_db.connect() as conn:
            unified_db.append_audit(conn, "ConfigFile", name, unified_db.ACTION_UPDATE, {"file": path.name})


def restore(name: str) -> None:
    _check(name)
    path = _user(name)
    if path.exists():
        path.replace(path.with_name(f"{name}.{datetime.now():%Y%m%d_%H%M%S}.bak.json"))
        if unified_db.is_available():
            with unified_db.connect() as conn:
                unified_db.append_audit(conn, "ConfigFile", name, unified_db.ACTION_DELETE, {"reset": "fichier livré"})
