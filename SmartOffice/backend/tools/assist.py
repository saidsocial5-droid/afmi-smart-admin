"""Assistant de rédaction de tous les champs de saisie (Lot 11) : corriger, reformuler, enrichir, générer, résumer, traduire.

Utilisé par Smart Office (barre ✨ de chaque champ) et par l'application de bureau (menu contextuel des zones de texte).
L'IA choisie pour la tâche « Rédaction » est utilisée, avec les règles habituelles : local d'abord, IA externe seulement
si elle est autorisée, masquage des RIB, CIN et salaires. Sans IA disponible, le texte n'est jamais remplacé par une
réponse de secours : l'utilisateur est invité à configurer une IA (Ollama en local, ou une IA en ligne autorisée).
"""
import re
from typing import Any, Dict

from backend.core import ai_config
from backend.core.llm_router import llm_router

ACTIONS = ("corriger", "reformuler", "enrichir", "generer", "resumer", "traduire")
LANG = {"fr": "français", "ar": "arabe standard (فصحى)", "en": "anglais"}
MAX_CHARS = 12_000


class AssistError(ValueError):
    pass


def detect_language(text: str) -> str:
    arabic = len(re.findall(r"[؀-ۿ]", text or ""))
    latin = len(re.findall(r"[A-Za-zÀ-ÿ]", text or ""))
    return "ar" if arabic > latin else "fr"


def _clean(answer: str, original: str) -> str:
    """Retire les guillemets ou préambules que certains modèles ajoutent (« Voici le texte corrigé : … »)."""
    t = (answer or "").strip()
    t = re.sub(r"^(?:voici|here is|ci-dessous)[^:\n]{0,80}:\s*", "", t, flags=re.I)
    if len(t) > 2 and t[0] in "«\"“'" and t[-1] in "»\"”'" and not (original.strip()[:1] in "«\"“'"):
        t = t[1:-1].strip()
    return t


async def run(action: str, text: str = "", field: str = "", context: str = "", language: str = "", target: str = "") -> Dict[str, Any]:
    if action not in ACTIONS:
        raise AssistError("Action inconnue : " + ", ".join(ACTIONS) + ".")
    text = (text or "").strip()
    if len(text) > MAX_CHARS:
        raise AssistError(f"Texte trop long pour l'assistant ({len(text)} caractères, {MAX_CHARS} au plus).")
    if action != "generer" and not text:
        raise AssistError("Le champ est vide : écrivez d'abord un texte, ou choisissez « Générer ».")
    lang_code = language if language in LANG else detect_language(text or context)
    lang = LANG[lang_code]
    if action == "traduire":
        tgt = target if target in LANG else ("fr" if lang_code == "ar" else "ar")
        system = ai_config.prompt("assist.traduire", lang=LANG[tgt])
        prompt = text
    elif action == "generer":
        system = ai_config.prompt("assist.generer", champ=field or "texte", lang=lang)
        prompt = (f"Indications de l'utilisateur : {text}\n" if text else "") + (f"Contexte de l'écran : {context[:2000]}" if context else "")
        if not prompt.strip():
            prompt = f"Rédige un contenu type pour le champ « {field or 'texte'} »."
    else:
        system = ai_config.prompt(f"assist.{action}")
        prompt = text
    answer, engine = await llm_router.generate_with_meta(prompt, system_prompt=system, temperature=0.2 if action == "corriger" else 0.4,
                                                         task="redaction")
    if engine == "heuristic":
        raise AssistError("Aucune IA disponible pour la rédaction. Activez-en une dans Paramètres › IA "
                          "(Ollama sur ce poste, ou Gemini / Claude / ChatGPT si l'IA en ligne est autorisée).")
    result = _clean(answer, text)
    if not result:
        raise AssistError("L'IA n'a rien renvoyé : réessayez.")
    return {"text": result, "engine": engine, "action": action, "language": lang_code}
