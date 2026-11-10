"""Confidentialité des envois vers une IA externe.

- L'IA externe (cloud) est désactivée par défaut : il faut l'activer dans les paramètres (ai.offline_mode = false).
- Si ai.mask_sensitive_data est activé (par défaut), RIB, IBAN, ICE, IF, CIN, n° CNSS et montants de salaire
  sont remplacés par des marqueurs avant tout envoi. Une image (relevé scanné) ne pouvant pas être masquée,
  elle n'est alors jamais envoyée à l'extérieur.
Les paramètres sont lus dans la base unique ; sans elle (mode web de développement), dans config/privacy.json.
"""
import json
import re
from typing import Any, Dict, Tuple

from backend.config.settings import settings
from backend.core import unified_db

OFFLINE_KEY = "ai.offline_mode"
MASK_KEY = "ai.mask_sensitive_data"
DEFAULTS = {OFFLINE_KEY: True, MASK_KEY: True}

_PATTERNS = [
    # IBAN marocain : MA + 2 chiffres de contrôle + 24 chiffres (espaces tolérés)
    ("IBAN", re.compile(r"\bMA\s?\d{2}(?:\s?\d){24}\b", re.IGNORECASE)),
    # RIB : 24 chiffres, éventuellement groupés 3 / 3 / 16 / 2 ou par blocs
    ("RIB", re.compile(r"(?<!\d)\d{3}[\s.-]?\d{3}[\s.-]?(?:\d[\s.-]?){15}\d[\s.-]?\d{2}(?!\d)")),
    # ICE : 15 chiffres
    ("ICE", re.compile(r"(?<!\d)\d{15}(?!\d)")),
    # Identifiant fiscal, n° CNSS : uniquement précédés de leur libellé
    ("IF", re.compile(r"(\b(?:IF|I\.F\.|identifiant\s+fiscal)\s*(?:n°|no|:)?\s*)\d{6,10}\b", re.IGNORECASE)),
    ("CNSS", re.compile(r"(\b(?:CNSS|immatriculation)\s*(?:n°|no|:)?\s*)\d{7,10}\b", re.IGNORECASE)),
    # CIN : 1 ou 2 lettres suivies de 3 à 6 chiffres, avec libellé, ou forme standard 2 lettres + 5-6 chiffres
    ("CIN", re.compile(r"(\b(?:CIN|C\.I\.N\.|carte\s+nationale)\s*(?:n°|no|:)?\s*)[A-Z]{1,2}\s?\d{3,6}\b", re.IGNORECASE)),
    ("CIN", re.compile(r"\b[A-Z]{2}\d{5,6}\b")),
    # Salaire nominatif : le montant qui suit le mot « salaire » ou « net à payer »
    ("SALAIRE", re.compile(r"(\b(?:salaire|net\s+à\s+payer|rémunération)\b[^\d\n]{0,25})\d[\d\s.,]*\d", re.IGNORECASE)),
]


def mask_sensitive(text: str) -> Tuple[str, Dict[str, int]]:
    """Retourne le texte masqué et le nombre de remplacements par type."""
    if not text:
        return text, {}
    counts: Dict[str, int] = {}
    for label, pattern in _PATTERNS:
        def repl(m: re.Match, label=label) -> str:
            counts[label] = counts.get(label, 0) + 1
            prefix = m.group(1) if m.re.groups else ""
            return f"{prefix}[{label} MASQUÉ]"
        text = pattern.sub(repl, text)
    return text, counts


def _fallback_path():
    return settings.data_dir / "config" / "privacy.json"


def _load_fallback() -> Dict[str, Any]:
    try:
        return json.loads(_fallback_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def get(key: str) -> bool:
    default = DEFAULTS[key]
    if unified_db.is_available():
        return bool(unified_db.get_setting(key, default))
    return bool(_load_fallback().get(key, default))


def set_value(key: str, value: bool) -> None:
    if key not in DEFAULTS:
        raise KeyError(key)
    if unified_db.is_available():
        unified_db.set_setting(key, bool(value))
        return
    data = _load_fallback()
    data[key] = bool(value)
    path = _fallback_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def external_ai_allowed() -> bool:
    return not get(OFFLINE_KEY)


def mask_enabled() -> bool:
    return get(MASK_KEY)
