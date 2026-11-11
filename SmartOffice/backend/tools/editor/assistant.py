"""Assistant IA de l'éditeur : reformuler, résumer, traduire, compléter une section à partir des données du projet.

Les règles de confidentialité du routeur s'appliquent (IA externe seulement si autorisée, masquage). Pour « compléter »,
les seules données chiffrées fournies au modèle sont celles de la base ; elles sont renvoyées avec la réponse pour
que l'utilisateur vérifie que chaque chiffre du texte en provient.
"""
import json
import re
from typing import Any, Dict, Optional

from backend.core.llm_router import llm_router
from . import blocks

LANG = {"fr": "français", "ar": "arabe standard (فصحى)", "en": "anglais"}
ACTIONS = {
    "reformulate": "Reformule le texte suivant dans un style institutionnel clair et précis, sans changer le sens ni les chiffres.",
    "summarize": "Résume le texte suivant en quelques phrases, en conservant les chiffres exacts.",
    "translate": "Traduis fidèlement le texte suivant en {lang}, sans rien ajouter.",
    "complete": "Rédige la section demandée pour un rapport d'activité d'association, en {lang}. N'utilise QUE les faits fournis ; "
                "n'invente aucun chiffre, nom ou date ; si une information manque, écris [à compléter].",
}


def project_facts(project_id: Optional[int]) -> Dict[str, Any]:
    if not project_id:
        return {}
    budget = blocks.budget_table(project_id)
    return {
        "projet": budget["project"],
        "budget": [{"ligne": f"{r['code']} {r['label']}", "prevu_mad": r["planned"] / 100, "realise_mad": r["realized_mad"] / 100}
                   for r in budget["rows"]],
        "indicateurs": blocks.indicators(project_id)["rows"],
        "activites": blocks.activities(project_id)["rows"],
    }


def _canonical(number: str) -> str:
    """« 6 500 », « 6500,0 » et « 6500 » → « 6500 »."""
    value = float(re.sub(r"[\s\u00a0]", "", number).replace(",", "."))
    return ("%.4f" % value).rstrip("0").rstrip(".")


def numbers_not_in_facts(text: str, facts: Dict[str, Any]) -> list[str]:
    """Nombres du texte généré absents des faits fournis : à vérifier par l'utilisateur."""
    known = {_canonical(n) for n in re.findall(r"\d+(?:\.\d+)?", json.dumps(facts, ensure_ascii=False))}
    out = []
    for n in re.findall(r"\d{1,3}(?:[\s\u00a0]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?", text):
        if _canonical(n) not in known:
            out.append(n.strip())
    return sorted(set(out))


async def run(action: str, text: str, language: str = "fr", project_id: Optional[int] = None, instruction: str = "") -> Dict[str, Any]:
    if action not in ACTIONS:
        raise ValueError("Action inconnue : reformulate, summarize, translate ou complete.")
    lang = LANG.get(language, "français")
    system = ACTIONS[action].format(lang=lang)
    facts = project_facts(project_id) if action == "complete" else {}
    prompt = (text or "").strip()
    if action == "complete":
        prompt = f"Section à rédiger : {instruction or prompt}\nFaits disponibles (JSON) :\n{json.dumps(facts, ensure_ascii=False)}"
    if not prompt:
        raise ValueError("Sélectionnez un texte ou décrivez la section à rédiger.")
    result, engine = await llm_router.generate_with_meta(prompt, system_prompt=system, temperature=0.3)
    return {"text": result.strip(), "engine": engine, "facts": facts,
            "unverified_numbers": numbers_not_in_facts(result, facts) if action == "complete" else [],
            "offline": engine == "heuristic"}
