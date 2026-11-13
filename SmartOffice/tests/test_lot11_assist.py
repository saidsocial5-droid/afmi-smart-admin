"""Lot 11 — assistant de rédaction des champs : prompts par action, langue, refus sans IA, nettoyage de la réponse."""
import asyncio

import pytest

from backend.core.llm_router import llm_router
from backend.tools import assist


def _fake(monkeypatch, answer="Texte amélioré.", engine="ollama:test"):
    calls = []

    async def gen(prompt, system_prompt="", **kw):
        calls.append({"prompt": prompt, "system": system_prompt, **kw})
        return answer, engine
    monkeypatch.setattr(llm_router, "generate_with_meta", gen)
    return calls


def test_each_action_uses_its_prompt_and_the_redaction_task(monkeypatch):
    calls = _fake(monkeypatch)
    for action in ("corriger", "reformuler", "enrichir", "resumer"):
        out = asyncio.run(assist.run(action, "La reunion a eu lieu a Azrou."))
        assert out["text"] == "Texte amélioré." and out["engine"] == "ollama:test"
    assert "orthographe" in calls[0]["system"] and "Reformule" in calls[1]["system"] and "[à compléter]" in calls[2]["system"]
    assert all(c["task"] == "redaction" for c in calls)


def test_translation_targets_the_other_language_and_generation_uses_field_context(monkeypatch):
    calls = _fake(monkeypatch)
    asyncio.run(assist.run("traduire", "اجتماع اللجنة"))
    assert "français" in calls[-1]["system"]
    asyncio.run(assist.run("traduire", "Réunion du comité"))
    assert "arabe" in calls[-1]["system"]
    asyncio.run(assist.run("generer", "", field="Description du projet", context="Projet APAC Timahdite"))
    assert "Description du projet" in calls[-1]["system"] and "APAC Timahdite" in calls[-1]["prompt"]


def test_no_ai_never_replaces_the_text(monkeypatch):
    _fake(monkeypatch, answer="réponse de secours", engine="heuristic")
    with pytest.raises(assist.AssistError, match="Aucune IA"):
        asyncio.run(assist.run("corriger", "texte"))
    with pytest.raises(assist.AssistError, match="vide"):
        asyncio.run(assist.run("corriger", "  "))


def test_answer_is_cleaned(monkeypatch):
    _fake(monkeypatch, answer="Voici le texte corrigé : « La réunion a eu lieu à Azrou. »")
    assert asyncio.run(assist.run("corriger", "La reunion a eu lieu a Azrou."))["text"] == "La réunion a eu lieu à Azrou."


def test_api_route(client, monkeypatch):
    _fake(monkeypatch)
    r = client.post("/api/assist/text", json={"action": "reformuler", "text": "abc"})
    assert r.status_code == 200 and r.json()["text"] == "Texte amélioré."
    assert client.post("/api/assist/text", json={"action": "inconnue", "text": "abc"}).status_code == 400
