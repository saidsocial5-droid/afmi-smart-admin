import asyncio

import pytest

from backend.core import privacy
from backend.core.llm_router import llm_router


@pytest.mark.parametrize("text, label", [
    ("Virement sur le RIB 022 330 0001234567890123 45 de l'association", "RIB"),
    ("RIB : 022330000123456789012345", "RIB"),
    ("IBAN MA64 0223 3000 0123 4567 8901 2345", "IBAN"),
    ("ICE 001894235000088", "ICE"),
    ("Identifiant fiscal : 40291845", "IF"),
    ("N° CNSS 123456789", "CNSS"),
    ("CIN : D123456", "CIN"),
    ("Titulaire AB123456", "CIN"),
    ("Salaire net de M. Alaoui : 8 450,00 DH", "SALAIRE"),
])
def test_sensitive_data_is_masked(text, label):
    masked, counts = privacy.mask_sensitive(text)
    assert counts.get(label, 0) >= 1, masked
    assert f"[{label} MASQUÉ]" in masked


def test_ordinary_figures_are_kept():
    text = "Budget de 150 000 MAD, 320 bénéficiaires, atelier du 12/03/2026, tél. 0535561240"
    masked, counts = privacy.mask_sensitive(text)
    assert masked == text
    assert counts == {}


def test_profile_identifiers_never_leave_unmasked():
    masked, _ = privacy.mask_sensitive("ICE 001894235000088 | IF 40291845 | RIB 022 330 0001234567890123 45")
    for secret in ("001894235000088", "40291845", "0001234567890123"):
        assert secret not in masked


class _Recorder:
    def __init__(self):
        self.calls = []

    async def __call__(self, prompt, system_prompt, model, temperature, images_b64=None, response_json=False):
        self.calls.append({"prompt": prompt, "system": system_prompt, "images": images_b64})
        return "réponse externe"


@pytest.fixture()
def gemini(monkeypatch):
    recorder = _Recorder()
    monkeypatch.setattr(llm_router, "_call_gemini", recorder)
    monkeypatch.setattr(llm_router, "gemini_key", "test-key")
    return recorder


def _settings(monkeypatch, offline, mask):
    values = {privacy.OFFLINE_KEY: offline, privacy.MASK_KEY: mask}
    monkeypatch.setattr(privacy, "get", lambda key: values[key])


def _run(**kwargs):
    return asyncio.run(llm_router.generate_with_meta(provider="gemini", **kwargs))


def test_external_ai_is_off_by_default(gemini, monkeypatch, tmp_path):
    monkeypatch.setattr(privacy, "_fallback_path", lambda: tmp_path / "privacy.json")
    monkeypatch.setattr(privacy.unified_db, "is_available", lambda: False)
    assert privacy.external_ai_allowed() is False
    _text, engine = _run(prompt="Rédige une note")
    assert gemini.calls == []
    assert not engine.startswith("gemini")


def test_enabled_external_ai_receives_masked_prompt(gemini, monkeypatch):
    _settings(monkeypatch, offline=False, mask=True)
    _text, engine = _run(prompt="Payer sur RIB 022330000123456789012345", system_prompt="ICE 001894235000088")
    assert engine.startswith("gemini")
    assert "022330000123456789012345" not in gemini.calls[0]["prompt"]
    assert "001894235000088" not in gemini.calls[0]["system"]


def test_images_never_leave_when_masking_is_on(gemini, monkeypatch):
    _settings(monkeypatch, offline=False, mask=True)
    _run(prompt="Lis ce relevé", images_b64=["aGVsbG8="])
    assert gemini.calls == []


def test_masking_can_be_disabled(gemini, monkeypatch):
    _settings(monkeypatch, offline=False, mask=False)
    _run(prompt="RIB 022330000123456789012345", images_b64=["aGVsbG8="])
    assert "022330000123456789012345" in gemini.calls[0]["prompt"]
    assert gemini.calls[0]["images"] == ["aGVsbG8="]


def test_privacy_settings_api_round_trip(client, monkeypatch, tmp_path):
    monkeypatch.setattr(privacy, "_fallback_path", lambda: tmp_path / "privacy.json")
    monkeypatch.setattr(privacy.unified_db, "is_available", lambda: False)
    r = client.get("/api/settings/privacy").json()
    assert r["offline_mode"] is True and r["mask_sensitive_data"] is True
    r = client.put("/api/settings/privacy", json={"offline_mode": False}).json()
    assert r["offline_mode"] is False and r["mask_sensitive_data"] is True
    assert client.get("/api/settings/privacy").json()["offline_mode"] is False
