"""Lot 7 — panneau de paramètres avancé : registre, secrets, import/export, IA par tâche, rôles, sauvegardes, SMTP."""
import asyncio
import base64
import json
import sqlite3

import pytest

from backend.config.settings import settings
from backend.core import ai_config, ai_providers, backups, config_files, dpapi, privacy, roles, settings_registry as reg, smtp, unified_db
from backend.core.llm_router import llm_router
from tests.unified_db_fixture import create_unified_db


@pytest.fixture()
def db(tmp_path, monkeypatch):
    path = create_unified_db(tmp_path / "database.db")
    monkeypatch.setenv(unified_db.DESKTOP_DB_ENV, str(path))
    monkeypatch.setenv("AFMI_AUDIT_USER", "admin.afmi")
    monkeypatch.setattr(settings, "data_dir", tmp_path / "data")
    return path


@pytest.fixture()
def fake_dpapi(monkeypatch):
    """DPAPI n'existe que sous Windows : chiffrement simulé (préfixe identique) pour tester le parcours des secrets."""
    monkeypatch.setattr(dpapi, "is_available", lambda: True)
    monkeypatch.setattr(dpapi, "protect", lambda v: "dpapi:" + base64.b64encode(v[::-1].encode()).decode())
    monkeypatch.setattr(dpapi, "unprotect", lambda v: base64.b64decode(v[6:]).decode()[::-1] if v.startswith("dpapi:") else v)


def _rows(sql, *args):
    with unified_db.connect() as conn:
        return conn.execute(sql, args).fetchall()


# --- Registre -------------------------------------------------------------------------------------------------

def test_snapshot_lists_sections_with_defaults(db):
    snap = reg.snapshot()
    ids = [s["id"] for s in snap["sections"]]
    assert ids[:3] == ["association", "comptabilite", "banques"] and "ia" in ids and "sauvegardes" in ids
    fields = {f["key"]: f for s in snap["sections"] for f in s["fields"]}
    assert fields["bank.reconciliation_tolerance_days"]["value"] == 3 and fields["bank.reconciliation_tolerance_days"]["is_default"]
    assert fields["ai.offline_mode"]["value"] is True                       # local-first par défaut
    assert fields["ai.keys.anthropic"]["configured"] is False and fields["ai.keys.anthropic"]["value"] is None
    assert "ai.keys.ollama" not in fields                                   # fournisseur local : pas de clé


def test_save_is_validated_and_atomic(db):
    with pytest.raises(reg.SettingsError) as e:
        reg.save({"bank.reconciliation_tolerance_days": 45, "association.acronym": "AFM"})
    assert "maximum 30" in str(e.value)
    assert reg.get("association.acronym") == "AFMI"                         # rien n'a été écrit
    reg.save({"bank.reconciliation_tolerance_days": 5, "ui.primary_color": "#123456",
              "ai.tasks.qa": {"provider": "ollama", "model": "llama3.1", "temperature": "0.2", "max_tokens": "800"}})
    assert reg.get("bank.reconciliation_tolerance_days") == 5
    assert reg.get("ai.tasks.qa") == {"provider": "ollama", "model": "llama3.1", "temperature": 0.2, "max_tokens": 800}
    for bad in ({"ui.primary_color": "vert"}, {"ai.tasks.qa": {"provider": "inconnu"}}, {"backup.frequency": "horaire"},
                {"ai.providers.anthropic": {"base_url": "http://api.anthropic.com"}}, {"inconnu.cle": 1}):
        with pytest.raises(reg.SettingsError):
            reg.save(bad)


def test_reset_restores_default_and_is_audited(db):
    reg.save({"association.acronym": "FMI"})
    assert reg.reset(["association.acronym"]) == 1
    assert reg.get("association.acronym") == "AFMI"
    audit = _rows("SELECT * FROM AuditEntries WHERE EntityType = 'AppSetting' AND EntityId = 'association.acronym' ORDER BY Id")
    assert [a["Action"] for a in audit] == ["Création", "Suppression"]
    with unified_db.connect() as conn:
        assert unified_db.find_first_tampered_audit_entry(conn) is None       # chaîne d'empreintes intacte


def test_secrets_are_encrypted_never_exported_nor_logged(db, fake_dpapi):
    reg.set_secret("ai.keys.anthropic", "sk-ant-SECRET")
    stored = _rows("SELECT ValueJson, IsSecret FROM AppSettings WHERE Key = 'ai.keys.anthropic'")[0]
    assert stored["IsSecret"] == 1 and "sk-ant-SECRET" not in stored["ValueJson"]
    assert ai_config.api_key("anthropic") == "sk-ant-SECRET"
    assert "sk-ant-SECRET" not in json.dumps(reg.export_json())
    assert all("sk-ant-SECRET" not in r["ChangesJson"] for r in _rows("SELECT ChangesJson FROM AuditEntries"))
    reg.set_secret("ai.keys.anthropic", "")                                  # vider = supprimer
    assert ai_config.api_key("anthropic") == ""


def test_secret_refused_without_dpapi(db, monkeypatch):
    monkeypatch.setattr(dpapi, "is_available", lambda: False)
    with pytest.raises(reg.SettingsError, match="DPAPI"):
        reg.set_secret("ai.keys.openai", "sk-x")


def test_export_import_roundtrip(db, fake_dpapi):
    reg.save({"association.acronym": "FMI", "backup.retention": 12})
    reg.set_secret("ai.keys.mistral", "m-key")
    layout = config_files.read("financial_report_layout")
    layout["checks"]["MISSING_RECEIPT"] = "ignore"
    config_files.write("financial_report_layout", layout)
    exported = reg.export_json()
    assert exported["values"]["association.acronym"] == "FMI" and "ai.keys.mistral" not in exported["values"]
    assert "financial_report_layout" in exported["files"]
    reg.reset(["association.acronym", "backup.retention"])
    config_files.restore("financial_report_layout")
    bad = json.loads(json.dumps(exported))
    bad["values"]["backup.retention"] = 0
    with pytest.raises(reg.SettingsError, match="rien n'a été modifié"):
        reg.import_json(bad)
    assert reg.get("association.acronym") == "AFMI"
    exported["values"]["ai.keys.mistral"] = "injecté"                        # un secret importé est ignoré
    res = reg.import_json(exported)
    assert res["secrets_skipped"] == ["ai.keys.mistral"] and ai_config.api_key("mistral") == "m-key"
    assert reg.get("backup.retention") == 12
    assert config_files.read("financial_report_layout")["checks"]["MISSING_RECEIPT"] == "ignore"


def test_config_files_are_validated_and_used(db):
    from backend.tools.reports.context import layout
    lay = config_files.read("financial_report_layout")
    lay["checks"]["DRAFT_OPERATIONS"] = "fatal"
    with pytest.raises(ValueError, match="fatal"):
        config_files.write("financial_report_layout", lay)
    lay["checks"]["DRAFT_OPERATIONS"] = "warning"
    config_files.write("financial_report_layout", lay)
    assert layout()["checks"]["DRAFT_OPERATIONS"] == "warning"
    life = config_files.read("lifecycle_config")
    life["expected"][life["phases"][0]] = ["TypeInexistant"]
    with pytest.raises(ValueError, match="TypeInexistant"):
        config_files.write("lifecycle_config", life)
    config_files.restore("financial_report_layout")
    assert layout()["checks"]["DRAFT_OPERATIONS"] == "blocking"
    assert list((settings.data_dir / "config").glob("financial_report_layout.*.bak.json"))   # copie conservée


def test_thresholds_follow_settings(db):
    from backend.tools.statements import store
    assert (store.receipt_threshold(), store.fee_threshold(), store.match_days()) == (100_000, 50_000, 3)
    reg.save({"accounting.receipt_threshold_mad": 2500, "bank.fee_alert_min_mad": 120.5, "bank.reconciliation_tolerance_days": 6})
    assert (store.receipt_threshold(), store.fee_threshold(), store.match_days()) == (250_000, 12_050, 6)


# --- IA par tâche ---------------------------------------------------------------------------------------------

class FakeHttp:
    def __init__(self, response):
        self.response, self.calls = response, []

    async def __call__(self, url, payload, headers, timeout=90.0):
        self.calls.append({"url": url, "payload": payload, "headers": headers})
        return self.response


ANTHROPIC_OK = {"content": [{"type": "text", "text": "Réponse Claude"}], "usage": {"input_tokens": 1000, "output_tokens": 500}}


def _anthropic_task(fake_dpapi_fixture=None):
    reg.set_secret("ai.keys.anthropic", "sk-ant")
    reg.save({"ai.tasks.redaction": {"provider": "anthropic", "model": "claude-sonnet-5-5", "temperature": 0.1, "max_tokens": 300},
              "ai.providers.anthropic": {"base_url": "https://api.anthropic.com", "model": "", "price_in": 3, "price_out": 15}})


def test_task_routing_respects_offline_mode(db, fake_dpapi, monkeypatch):
    _anthropic_task()
    fake = FakeHttp(ANTHROPIC_OK)
    monkeypatch.setattr(ai_providers, "_post", fake)
    monkeypatch.setattr(llm_router, "_call_ollama", _fail)
    text, engine = asyncio.run(llm_router.generate_with_meta("Bonjour", task="redaction"))
    assert fake.calls == [] and engine == "heuristic"                         # mode hors ligne par défaut : aucun envoi


async def _fail(*a, **k):
    raise RuntimeError("Ollama absent")


def test_task_routing_masks_and_records_usage(db, fake_dpapi, monkeypatch):
    _anthropic_task()
    privacy.set_value(privacy.OFFLINE_KEY, False)
    fake = FakeHttp(ANTHROPIC_OK)
    monkeypatch.setattr(ai_providers, "_post", fake)
    text, engine = asyncio.run(llm_router.generate_with_meta("RIB 011 780 0000123456789012 34 à vérifier", system_prompt="Sys",
                                                             task="redaction"))
    assert (text, engine) == ("Réponse Claude", "anthropic:claude-sonnet-5-5")
    call = fake.calls[0]
    assert call["url"] == "https://api.anthropic.com/v1/messages" and call["headers"]["x-api-key"] == "sk-ant"
    body = call["payload"]
    assert "0000123456789012" not in json.dumps(body) and "MASQUÉ" in body["messages"][0]["content"][-1]["text"]
    assert (body["model"], body["max_tokens"], body["temperature"], body["system"]) == ("claude-sonnet-5-5", 300, 0.1, "Sys")
    u = ai_config.usage()
    assert u["providers"]["anthropic"]["in"] == 1000 and abs(u["cost"] - (1000 * 3 + 500 * 15) / 1e6) < 1e-9
    # image + masquage : jamais envoyée
    fake.calls.clear()
    monkeypatch.setattr(llm_router, "_call_ollama", _fail)
    asyncio.run(llm_router.generate_with_meta("légende", images_b64=["aGVsbG8="], task="redaction"))
    assert fake.calls == []


def test_monthly_cost_cap_stops_external_calls(db, fake_dpapi, monkeypatch):
    _anthropic_task()
    privacy.set_value(privacy.OFFLINE_KEY, False)
    reg.save({"ai.cost.monthly_cap": 0.01})
    fake = FakeHttp(ANTHROPIC_OK)
    monkeypatch.setattr(ai_providers, "_post", fake)
    monkeypatch.setattr(llm_router, "_call_ollama", _fail)
    asyncio.run(llm_router.generate_with_meta("a", task="redaction"))       # 0,0105 USD : plafond atteint après cet appel
    asyncio.run(llm_router.generate_with_meta("b", task="redaction"))
    assert len(fake.calls) == 1 and ai_config.cap_reached()


def test_local_only_task_and_provider_payloads(db, fake_dpapi, monkeypatch):
    reg.save({"ai.tasks.qa": {"provider": "heuristic"}})
    fake = FakeHttp({})
    monkeypatch.setattr(ai_providers, "_post", fake)
    assert asyncio.run(llm_router.generate_with_meta("q", task="qa"))[1] == "heuristic" and fake.calls == []
    # Formats des autres fournisseurs
    privacy.set_value(privacy.OFFLINE_KEY, False)
    privacy.set_value(privacy.MASK_KEY, False)
    reg.set_secret("ai.keys.openai", "sk-o")
    fake = FakeHttp({"choices": [{"message": {"content": "ok"}}], "usage": {"prompt_tokens": 3, "completion_tokens": 2}})
    monkeypatch.setattr(ai_providers, "_post", fake)
    out = asyncio.run(ai_providers.call("openai", "gpt-x", "p", "s", 0.2, 50, ["aW1n"], True))
    assert out == ("ok", 3, 2)
    body = fake.calls[0]["payload"]
    assert body["max_completion_tokens"] == 50 and body["response_format"] == {"type": "json_object"}
    assert fake.calls[0]["headers"]["Authorization"] == "Bearer sk-o" and body["messages"][1]["content"][1]["type"] == "image_url"
    reg.save({"ai.providers.openai_compatible": {"base_url": "http://localhost:1234/v1", "model": "local-model"}})
    assert not ai_config.is_external("openai_compatible", "http://localhost:1234/v1")
    assert ai_config.is_external("openai_compatible", "https://llm.example.org/v1")
    fake = FakeHttp({"candidates": [{"content": {"parts": [{"text": "g"}]}}], "usageMetadata": {"promptTokenCount": 1, "candidatesTokenCount": 1}})
    monkeypatch.setattr(ai_providers, "_post", fake)
    reg.set_secret("ai.keys.gemini", "g-key")
    assert asyncio.run(ai_providers.call("gemini", "gemini-2.5-flash", "p", "", 0.1, None, None, False))[0] == "g"
    assert fake.calls[0]["url"].endswith("/models/gemini-2.5-flash:generateContent") and fake.calls[0]["headers"]["x-goog-api-key"] == "g-key"


def test_connection_test_refused_offline(db):
    res = asyncio.run(ai_providers.test("anthropic", "sk"))
    assert res["ok"] is False and "hors ligne" in res["message"]


def test_prompts_are_editable_with_default(db):
    assert ai_config.prompt("editor.translate", lang="arabe").endswith("en arabe, sans rien ajouter.")
    reg.save({"ai.prompts.editor.translate": "Traduis en {lang} (style AFMI)."})
    assert ai_config.prompt("editor.translate", lang="anglais") == "Traduis en anglais (style AFMI)."
    reg.save({"ai.prompts.editor.translate": "Accolade {inconnue}"})          # gabarit invalide : prompt par défaut
    assert "Traduis fidèlement" in ai_config.prompt("editor.translate", lang="anglais")
    reg.reset(["ai.prompts.editor.translate"])
    assert "Traduis fidèlement" in ai_config.prompt("editor.translate", lang="anglais")


# --- Rôles ----------------------------------------------------------------------------------------------------

def test_roles_guard_writes(client, db, monkeypatch):
    assert roles.check("POST", "/api/editor/documents") is None              # aucun utilisateur déclaré : tous les droits
    with pytest.raises(reg.SettingsError, match="votre propre compte"):
        reg.save({"security.users": [{"login": "autre", "role": "Administrateur"}]})
    with pytest.raises(reg.SettingsError, match="administrateur"):
        reg.save({"security.users": [{"login": "admin.afmi", "role": "Lecteur"}]})
    reg.save({"security.users": [{"login": "admin.afmi", "role": "Administrateur"}, {"login": "compta", "role": "Comptable"},
                                 {"login": "projet", "role": "Chargé de projet"}]})
    monkeypatch.setenv("AFMI_AUDIT_USER", "compta")
    assert roles.check("POST", "/api/statements/upload") is None
    assert "Comptable" in roles.check("PUT", "/api/settings/values")
    assert roles.check("GET", "/api/settings/registry") is None              # lecture libre
    r = client.put("/api/settings/values", json={"values": {"association.acronym": "X"}})
    assert r.status_code == 403
    monkeypatch.setenv("AFMI_AUDIT_USER", "projet")
    assert roles.check("POST", "/api/statements/upload") is not None and roles.check("POST", "/api/ged/documents") is None
    monkeypatch.setenv("AFMI_AUDIT_USER", "inconnu")
    assert roles.current_role() == "Lecteur" and roles.check("POST", "/api/exports/annual-package") is None
    assert roles.check("DELETE", "/api/editor/documents/1") is not None


# --- Sauvegardes ----------------------------------------------------------------------------------------------

def test_backups_create_list_and_schedule_restore(db, tmp_path):
    reg.save({"backup.retention": 2, "association.acronym": "AVANT"})
    for _ in range(3):
        backups.create("manuel")
    items = backups.list_backups()
    assert len(items) == 2 and all(i["reason"] == "manuel" for i in items)  # conservation appliquée
    copy = sqlite3.connect(str(backups.folder() / items[0]["name"]))
    assert copy.execute("SELECT ValueJson FROM AppSettings WHERE Key = 'association.acronym'").fetchone()[0] == '"AVANT"'
    copy.close()
    with pytest.raises(backups.BackupError):
        backups.schedule_restore("../database.db")
    pending = backups.schedule_restore(items[-1]["name"])
    flag = json.loads((db.parent / backups.PENDING).read_text(encoding="utf-8"))
    assert pending["name"] == items[-1]["name"] and flag["path"].endswith(items[-1]["name"])   # lu par BackupService (.NET)
    backups.cancel_restore()
    assert backups.pending() is None


def test_backup_api_requires_admin(client, db, monkeypatch):
    reg.save({"security.users": [{"login": "admin.afmi", "role": "Administrateur"}, {"login": "lecteur", "role": "Lecteur"}]})
    assert client.post("/api/settings/backups").status_code == 200
    monkeypatch.setenv("AFMI_AUDIT_USER", "lecteur")
    assert client.post("/api/settings/backups").status_code == 403
    assert client.get("/api/settings/backups").status_code == 200


# --- SMTP -----------------------------------------------------------------------------------------------------

def test_smtp_password_encrypted_and_masked_in_audit(db, fake_dpapi):
    smtp.save({"server": "smtp.example.org", "port": 587, "username": "afmi@example.org", "password": "MotDePasse!", "recipient": "da@example.org"})
    row = _rows("SELECT Password FROM SmtpSettings")[0]
    assert row["Password"].startswith("dpapi:") and "MotDePasse" not in row["Password"]
    assert smtp.get()["password_configured"] is True
    assert all("MotDePasse" not in r["ChangesJson"] and "dpapi:" not in r["ChangesJson"]
               for r in _rows("SELECT ChangesJson FROM AuditEntries WHERE EntityType = 'SmtpSettings'"))
    with pytest.raises(smtp.SmtpError):
        smtp.save({"server": "x", "port": 70000})


def test_settings_api_roundtrip(client, db):
    r = client.get("/api/settings/registry")
    assert r.status_code == 200 and r.json()["current_user"] == "admin.afmi"
    assert client.put("/api/settings/values", json={"values": {"ui.font_scale": 200}}).status_code == 400
    assert client.put("/api/settings/values", json={"values": {"ui.font_scale": 110}}).status_code == 200
    exported = client.get("/api/settings/export")
    assert exported.json()["values"]["ui.font_scale"] == 110
    assert client.post("/api/settings/reset", json={"section": "apparence"}).json()["reset"] == 1
    assert client.post("/api/settings/import", json={"data": exported.json(), "dry_run": True}).json()["dry_run"] is True
    assert reg.get("ui.font_scale") == 100
    f = client.get("/api/settings/files/lifecycle_config").json()
    assert f["customized"] is False and f["content"] == f["default"]
    assert client.get("/api/settings/files/../../secret").status_code in (400, 404)
