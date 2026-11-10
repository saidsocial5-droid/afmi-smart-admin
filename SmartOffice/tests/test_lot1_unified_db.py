import sqlite3

import pytest

from backend.core import dpapi, privacy, unified_db
from tests.unified_db_fixture import create_unified_db


@pytest.fixture()
def unified(tmp_path, monkeypatch):
    path = create_unified_db(tmp_path / "database.db")
    monkeypatch.setenv(unified_db.DESKTOP_DB_ENV, str(path))
    monkeypatch.setenv("AFMI_AUDIT_USER", "comptable")
    return path


def test_unavailable_without_desktop_database(tmp_path, monkeypatch):
    monkeypatch.setenv(unified_db.DESKTOP_DB_ENV, str(tmp_path / "absente.db"))
    assert unified_db.is_available() is False
    assert unified_db.get_setting("ai.offline_mode", True) is True


def test_unmigrated_database_is_refused(tmp_path, monkeypatch):
    path = tmp_path / "vide.db"
    sqlite3.connect(str(path)).close()
    monkeypatch.setenv(unified_db.DESKTOP_DB_ENV, str(path))
    assert unified_db.is_available() is False


def test_settings_are_shared_and_audited(unified):
    assert unified_db.is_available()
    unified_db.set_setting("ai.offline_mode", False)
    unified_db.set_setting("ai.offline_mode", True)
    assert unified_db.get_setting("ai.offline_mode") is True

    conn = sqlite3.connect(str(unified))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM AuditEntries ORDER BY Id").fetchall()
    assert [r["Action"] for r in rows] == ["Création", "Modification"]
    assert rows[0]["User"] == "comptable" and rows[0]["EntityType"] == "AppSetting"
    assert rows[1]["PreviousHash"] == rows[0]["Hash"]
    assert unified_db.find_first_tampered_audit_entry(conn) is None

    # Le journal est en ajout seul, y compris pour le backend.
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM AuditEntries")
    conn.close()


def test_privacy_settings_use_the_unified_database(unified):
    privacy.set_value(privacy.OFFLINE_KEY, False)
    assert privacy.external_ai_allowed() is True
    assert unified_db.get_setting(privacy.OFFLINE_KEY) is False


def test_failed_write_leaves_no_trace(unified):
    with pytest.raises(sqlite3.IntegrityError):
        with unified_db.connect() as conn:
            unified_db.append_audit(conn, "Test", "1", "Création", {})
            conn.execute("INSERT INTO Operations (BankAccountId, OperationDate, Label, Reference, ThirdParty, Direction, Nature, "
                         "AmountMinor, Currency, AmountMadMinor, Status, ValidatedBy, Notes, IsDeleted) "
                         "VALUES (999, '2026-01-01', '', '', '', 'Debit', 'Expense', 100, 'MAD', 100, 'Draft', '', '', 0)")
    conn = sqlite3.connect(str(unified))
    assert conn.execute("SELECT COUNT(*) FROM AuditEntries").fetchone()[0] == 0
    conn.close()


def test_secrets_require_dpapi(unified):
    if dpapi.is_available():
        unified_db.set_setting("ai.gemini.api_key", "AIza-secret", secret=True)
        assert unified_db.get_setting("ai.gemini.api_key") == "AIza-secret"
        raw = sqlite3.connect(str(unified)).execute("SELECT ValueJson FROM AppSettings WHERE Key='ai.gemini.api_key'").fetchone()[0]
        assert "AIza-secret" not in raw
    else:
        with pytest.raises(dpapi.DpapiUnavailable):
            unified_db.set_setting("ai.gemini.api_key", "AIza-secret", secret=True)
        assert unified_db.get_setting("ai.gemini.api_key") is None
