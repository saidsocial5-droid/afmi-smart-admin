"""Gabarits de banques (config/bank_templates.json, copiable dans le dossier de configuration de l'utilisateur)."""
import json
import unicodedata
from dataclasses import dataclass
from typing import Dict, List

from backend.config.settings import BUNDLED_CONFIG_DIR, settings


@dataclass
class BankTemplate:
    id: str
    name: str
    detect: List[str]
    opening: List[str]
    closing: List[str]


def normalize(text: str) -> str:
    """Minuscules, sans accents ni ponctuation : « Libellé de l'opération » → « libelle de l operation »."""
    t = unicodedata.normalize("NFD", text.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = "".join(c if c.isalnum() else " " for c in t)
    return " ".join(t.split())


def load() -> tuple[List[BankTemplate], Dict[str, List[str]]]:
    user_file = settings.data_dir / "config" / "bank_templates.json"
    path = user_file if user_file.exists() else BUNDLED_CONFIG_DIR / "bank_templates.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    templates = [BankTemplate(t["id"], t["name"], [normalize(d) for d in t["detect"]],
                              [normalize(o) for o in t["opening"]], [normalize(c) for c in t["closing"]])
                 for t in data["templates"]]
    columns = {k: [normalize(v) for v in vals] for k, vals in data["columns"].items()}
    return templates, columns


def detect(full_text: str, templates: List[BankTemplate]) -> BankTemplate:
    text = " " + normalize(full_text) + " "
    for t in templates:
        if any(f" {d} " in text for d in t.detect):
            return t
    return next(t for t in templates if t.id == "generique")
