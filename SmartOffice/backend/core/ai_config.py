"""Configuration de l'IA par tâche (Lot 7) : fournisseur, modèle, température, limite de jetons, prompts système,
plafond de coût mensuel et suivi de la consommation.

Tout est stocké dans la table AppSettings de la base unique ; les clés d'API sont des secrets chiffrés par DPAPI
(``ai.keys.<fournisseur>``), jamais exportés ni journalisés. Une tâche en « auto » garde le comportement d'origine
(fournisseur par défaut, puis Ollama local, puis moteur heuristique).
"""
from datetime import date
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from backend.core import unified_db

PROVIDERS: Dict[str, Dict[str, Any]] = {
    "anthropic": {"label": "Anthropic (Claude)", "external": True, "base_url": "https://api.anthropic.com", "model": "claude-sonnet-5-5"},
    "openai": {"label": "OpenAI", "external": True, "base_url": "https://api.openai.com/v1", "model": ""},
    "gemini": {"label": "Google Gemini", "external": True, "base_url": "https://generativelanguage.googleapis.com/v1beta", "model": "gemini-2.5-flash"},
    "mistral": {"label": "Mistral AI", "external": True, "base_url": "https://api.mistral.ai/v1", "model": ""},
    "ollama": {"label": "Ollama (local)", "external": False, "base_url": "http://localhost:11434", "model": "llama3.1"},
    "openai_compatible": {"label": "Serveur compatible OpenAI (LM Studio, vLLM…)", "external": None, "base_url": "http://localhost:1234/v1", "model": ""},
    "heuristic": {"label": "Moteur local sans IA (règles)", "external": False, "base_url": "", "model": ""},
}

TASKS: Dict[str, Dict[str, Any]] = {
    "redaction": {"label": "Rédaction (assistant de l'éditeur)", "vision": False},
    "reports": {"label": "Synthèse des rapports annuels", "vision": False},
    "extraction": {"label": "Lecture des relevés et pièces (secours de l'OCR)", "vision": True},
    "qa": {"label": "Questions sur les documents (GED)", "vision": False},
    "captions": {"label": "Légendes des photos", "vision": True},
}
TASK_DEFAULT = {"provider": "auto", "model": "", "temperature": None, "max_tokens": None}

PROMPTS: Dict[str, Dict[str, str]] = {
    "editor.reformulate": {"label": "Éditeur — reformuler",
                           "text": "Reformule le texte suivant dans un style institutionnel clair et précis, sans changer le sens ni les chiffres."},
    "editor.summarize": {"label": "Éditeur — résumer", "text": "Résume le texte suivant en quelques phrases, en conservant les chiffres exacts."},
    "editor.translate": {"label": "Éditeur — traduire ({lang} = langue cible)", "text": "Traduis fidèlement le texte suivant en {lang}, sans rien ajouter."},
    "editor.complete": {"label": "Éditeur — compléter une section ({lang} = langue)",
                        "text": "Rédige la section demandée pour un rapport d'activité d'association, en {lang}. N'utilise QUE les faits fournis ; "
                                "n'invente aucun chiffre, nom ou date ; si une information manque, écris [à compléter]."},
    "reports.synthesis": {"label": "Rapports annuels — synthèse ({lang} = langue)",
                          "text": "Rédige la synthèse de l'exercice d'une association, en {lang}, à partir des seuls faits fournis. "
                                  "N'invente aucun chiffre, nom ou date ; si une information manque, écris [à compléter]."},
    "statements.extract": {"label": "Relevés — extraction des lignes",
                           "text": "Tu lis un relevé bancaire marocain. Réponds UNIQUEMENT par un objet JSON :\n"
                                   '{"opening": "solde initial", "closing": "solde final", "lines": [{"date": "jj/mm/aaaa", "value_date": "jj/mm/aaaa ou vide",\n'
                                   '"label": "libellé", "debit": "montant ou vide", "credit": "montant ou vide"}]}\n'
                                   "Recopie les montants exactement (virgule décimale). N'invente aucune ligne.\n"
                                   "Texte lu par OCR (peut contenir des erreurs) :\n"},
    "ged.qa": {"label": "GED — questions sur les documents",
               "text": "Tu es l'assistant documentaire de l'association. Tu ne réponds qu'avec les documents fournis."},
    "photos.caption": {"label": "Photos — légende",
                       "text": "Décris cette photo d'activité d'une association de gestion forestière en UNE phrase factuelle de légende "
                               "(moins de 25 mots), en français, sans inventer de nom de personne ni de lieu."},
}


def _get(key: str, default: Any) -> Any:
    if not unified_db.is_available():
        return default
    value = unified_db.get_setting(key, None)
    return default if value is None else value


def prompt(name: str, **fmt: str) -> str:
    """Prompt système en vigueur (modifié dans les paramètres, ou celui par défaut)."""
    text = _get(f"ai.prompts.{name}", None) or PROMPTS[name]["text"]
    try:
        return text.format(**fmt) if fmt else text
    except (KeyError, IndexError, ValueError):
        return PROMPTS[name]["text"].format(**fmt) if fmt else PROMPTS[name]["text"]


def task_config(task: Optional[str]) -> Dict[str, Any]:
    if not task or task not in TASKS:
        return dict(TASK_DEFAULT)
    return {**TASK_DEFAULT, **(_get(f"ai.tasks.{task}", {}) or {})}


def provider_config(provider: str) -> Dict[str, Any]:
    base = PROVIDERS[provider]
    stored = _get(f"ai.providers.{provider}", {}) or {}
    return {"base_url": stored.get("base_url") or base["base_url"], "model": stored.get("model") or base["model"],
            "price_in": float(stored.get("price_in") or 0), "price_out": float(stored.get("price_out") or 0)}


def api_key(provider: str) -> str:
    key = _get(f"ai.keys.{provider}", "") or ""
    if not key and provider == "gemini":
        key = _get("ai.gemini.api_key", "") or ""            # clé enregistrée avant le Lot 7
    return key


def is_external(provider: str, base_url: str = "") -> bool:
    ext = PROVIDERS[provider]["external"]
    if ext is None:                                           # serveur compatible : externe sauf s'il tourne sur le poste
        host = (urlparse(base_url).hostname or "").lower()
        return host not in ("localhost", "127.0.0.1", "::1")
    return bool(ext)


# --- Consommation et plafond --------------------------------------------------------------------------------

def _month_key(day: Optional[date] = None) -> str:
    return f"ai.usage.{(day or date.today()):%Y-%m}"


def usage(day: Optional[date] = None) -> Dict[str, Any]:
    data = _get(_month_key(day), {}) or {}
    return {"month": f"{(day or date.today()):%Y-%m}", "providers": data, "cost": round(sum(p.get("cost", 0) for p in data.values()), 4),
            "cap": float(_get("ai.cost.monthly_cap", 0) or 0)}


def cap_reached() -> bool:
    u = usage()
    return u["cap"] > 0 and u["cost"] >= u["cap"]


def record(provider: str, tokens_in: int, tokens_out: int) -> float:
    """Ajoute un appel à la consommation du mois ; retourne son coût estimé (prix saisis dans les paramètres, par million de jetons)."""
    cfg = provider_config(provider)
    cost = (tokens_in * cfg["price_in"] + tokens_out * cfg["price_out"]) / 1_000_000
    if unified_db.is_available():
        key = _month_key()
        data = _get(key, {}) or {}
        p = data.setdefault(provider, {"calls": 0, "in": 0, "out": 0, "cost": 0.0})
        p["calls"] += 1
        p["in"] += int(tokens_in or 0)
        p["out"] += int(tokens_out or 0)
        p["cost"] = round(p["cost"] + cost, 6)
        unified_db.set_setting(key, data)
    return cost
