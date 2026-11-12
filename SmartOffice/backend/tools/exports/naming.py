"""Nommage configurable des fichiers exportés.

Deux modèles (paramètres) : ``exports.naming.report`` pour les rapports et états, par défaut
``{org}_{type}_{year}_{lang}`` → ``AFMI_RapportFinancier_2026_FR.pdf`` ; ``exports.naming.document`` pour les documents
de l'éditeur, par défaut ``{org}_{title}_{date}``. Variables : {org} sigle de l'association, {type}, {year}, {lang},
{title}, {project} (code), {date} (AAAAMMJJ). Les caractères interdits par Windows sont retirés.
"""
import re
import unicodedata
from datetime import date
from typing import Optional

from backend.core import unified_db

DEFAULTS = {"exports.naming.report": "{org}_{type}_{year}_{lang}", "exports.naming.document": "{org}_{title}_{date}"}
TYPES = {"moral": "RapportMoral", "financial": "RapportFinancier", "both": "RapportAnnuel", "statements": "EtatsFinanciers",
         "operations": "OperationsBancaires", "reconciliation": "Rapprochement", "package": "DossierAnnuel", "document": "Document"}
_FORBIDDEN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _setting(key: str) -> str:
    value = unified_db.get_setting(key, None) if unified_db.is_available() else None
    return value or DEFAULTS[key]


def _slug(text: str, limit: int = 60) -> str:
    text = unicodedata.normalize("NFC", text or "").strip()
    text = _FORBIDDEN.sub("", text)
    text = re.sub(r"\s+", "_", text)
    return text[:limit].strip("._") or "Document"


def file_name(ext: str, kind: str = "document", year: Optional[int] = None, lang: str = "fr", title: str = "",
              project: str = "", pattern: Optional[str] = None) -> str:
    org = unified_db.get_setting("association.acronym", "AFMI") if unified_db.is_available() else "AFMI"
    pattern = pattern or _setting("exports.naming.document" if kind == "document" else "exports.naming.report")
    values = {"org": org or "AFMI", "type": TYPES.get(kind, kind), "year": str(year or date.today().year), "lang": (lang or "fr").upper(),
              "title": _slug(title, 50), "project": project or "", "date": date.today().strftime("%Y%m%d")}
    name = re.sub(r"\{(\w+)\}", lambda m: values.get(m.group(1), m.group(0)), pattern)
    name = re.sub(r"_+", "_", _slug(name, 120))
    return f"{name}.{ext.lstrip('.')}"
