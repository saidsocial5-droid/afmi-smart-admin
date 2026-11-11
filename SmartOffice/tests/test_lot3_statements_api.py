import json
import sqlite3

import pytest

from backend.config.settings import settings
from backend.core import unified_db
from backend.tools.statements import ocr
from tests.tools import statement_fixtures
from tests.unified_db_fixture import create_unified_db


@pytest.fixture()
def unified(tmp_path, monkeypatch):
    path = create_unified_db(tmp_path / "database.db")
    monkeypatch.setenv(unified_db.DESKTOP_DB_ENV, str(path))
    monkeypatch.setattr(settings, "data_dir", tmp_path / "data")
    conn = sqlite3.connect(str(path))
    conn.executescript("""
        INSERT INTO Projects (Id, Name, Code, Description, Manager, Owner, Client, Department, Status, Priority, BudgetGlobal,
                              LessonsLearned, LocalFolderPath, Currency, IsDeleted)
        VALUES (1, 'Reboisement', 'P1', '', '', '', '', '', 'Exécution', 'Haute', 0, '', '', 'MAD', 0);
        INSERT INTO BankAccounts (Id, Kind, Purpose, BankName, Branch, Title, Rib, Currency, OpeningBalanceMinor, OpeningDate,
                                  Status, Notes, IsDeleted)
        VALUES (1, 'Bank', 'Operating', 'Banque Populaire', 'Azrou', 'Fonctionnement', NULL, 'MAD', 0, '2026-01-01', 'Active', '', 0);
        INSERT INTO BudgetLines (Id, ProjectId, Code, Label, CategoryId, PlannedMinor, Currency, IsDeleted)
        VALUES (1, NULL, 'F7', 'Frais bancaires', 12, 10000, 'MAD', 0);
    """)
    conn.commit()
    conn.close()
    return path


@pytest.fixture(scope="module")
def synthetic(tmp_path_factory):
    folder = tmp_path_factory.mktemp("releves_api")
    statement_fixtures.generate(folder)
    return folder


def _upload(client, folder, name, **form):
    data = {"account_id": "1", **form}
    with open(folder / name, "rb") as f:
        return client.post("/api/statements/upload", data=data, files={"files": (name, f.read())}).json()


def _db(path):
    c = sqlite3.connect(str(path))
    c.row_factory = sqlite3.Row
    return c


def test_native_statement_is_imported_as_draft_with_suggestions_and_archive(client, unified, synthetic):
    r = _upload(client, synthetic, "synth_bp_11.pdf")["results"][0]
    assert r["balance_ok"] is True and r["engine"] == "pdf-natif" and r["lines"] == 14
    st = client.get(f"/api/statements/{r['statement_id']}").json()
    assert st["status"] == "Draft" and st["source"] == "Ocr" and st["bank"] == "bp"
    assert st["blocking"] == []
    fees = [l for l in st["lines"] if "FRAIS" in l["label"] or "COMMISSION" in l["label"] or "AGIOS" in l["label"]]
    assert fees and all(l["category_id"] == 12 and l["budget_line_id"] == 1 for l in fees)   # règle de base + ligne unique
    assert all(l["project_id"] is None for l in st["lines"])                                  # compte de fonctionnement non lié
    assert client.get(f"/api/statements/{r['statement_id']}/pages/1").headers["content-type"] == "image/png"

    db = _db(unified)
    stored = db.execute("SELECT * FROM StoredFiles").fetchone()
    assert (settings.data_dir / stored["RelativePath"]).exists()
    assert db.execute("SELECT COUNT(*) FROM Operations").fetchone()[0] == 0                   # rien d'intégré
    assert unified_db.find_first_tampered_audit_entry(db) is None
    assert db.execute("SELECT COUNT(*) FROM AuditEntries WHERE EntityType = 'StatementLine'").fetchone()[0] == 14

    again = _upload(client, synthetic, "synth_bp_11.pdf")["results"][0]
    assert "déjà été importé" in again["error"]


def test_anomalies_over_budget_and_missing_receipts(client, unified, synthetic):
    st = client.get(f"/api/statements/{_upload(client, synthetic, 'synth_bp_11.pdf')['results'][0]['statement_id']}").json()
    codes = {a["code"] for a in st["anomalies"]}
    assert "OVER_BUDGET" in codes          # 100 MAD prévus pour les frais bancaires
    assert "NO_RECEIPT" in codes           # grosses dépenses sans opération ni justificatif


def test_corrections_learning_validation_and_integration(client, unified, synthetic):
    sid = _upload(client, synthetic, "synth_awb_55.pdf")["results"][0]["statement_id"]
    st = client.get(f"/api/statements/{sid}").json()
    lines = st["lines"]

    # Erreur de lecture simulée : l'équilibre est rompu, la validation est refusée.
    broken = dict(lines[0]); broken["debit"], broken["credit"] = (lines[0]["debit"] + 100, 0) if lines[0]["debit"] else (0, lines[0]["credit"] + 100)
    st2 = client.put(f"/api/statements/{sid}", json={"lines": [broken]}).json()
    assert [b["code"] for b in st2["blocking"]] == ["BALANCE"]
    assert client.post(f"/api/statements/{sid}/validate").status_code == 400
    client.put(f"/api/statements/{sid}", json={"lines": [lines[0]]})

    # Correction de catégorie → règle apprise, réutilisée sur un autre relevé.
    target = next(l for l in lines if l["debit"] > 0)
    corrected = dict(target, category_id=11, project_id=1, budget_line_id=None)
    res = client.put(f"/api/statements/{sid}", json={"lines": [corrected]}).json()
    assert res["learned_rules"] == 1
    db = _db(unified)
    rule = db.execute("SELECT * FROM CategorizationRules").fetchone()
    assert rule["Source"] == "Learned" and rule["CategoryId"] == 11 and rule["ProjectId"] == 1

    assert client.post(f"/api/statements/{sid}/integrate").status_code == 400   # pas encore validé
    assert client.post(f"/api/statements/{sid}/validate").json()["status"] == "Validated"
    assert client.put(f"/api/statements/{sid}", json={"opening": 1}).status_code == 400  # plus modifiable

    # Une opération existe déjà pour une ligne : elle n'est pas dupliquée.
    other = next(l for l in lines if l["id"] != target["id"])
    db.execute("INSERT INTO Operations (BankAccountId, OperationDate, Label, Reference, ThirdParty, Direction, Nature, AmountMinor, "
               "Currency, AmountMadMinor, Status, ValidatedBy, Notes, IsDeleted) VALUES (1, ?, 'Saisie manuelle', 'M1', '', ?, ?, ?, 'MAD', ?, "
               "'Validated', 'x', '', 0)",
               (other["date"], "Credit" if other["credit"] else "Debit", "Income" if other["credit"] else "Expense",
                other["credit"] or other["debit"], other["credit"] or other["debit"]))
    db.commit()
    out = client.post(f"/api/statements/{sid}/integrate").json()
    assert out == {"created": len(lines) - 1, "skipped_existing": 1, "already_integrated": 0}
    ops = db.execute("SELECT * FROM Operations WHERE Reference LIKE 'REL-%'").fetchall()
    assert all(o["Status"] == "Draft" for o in ops)
    assert client.post(f"/api/statements/{sid}/integrate").json()["already_integrated"] == len(lines) - 1

    # La règle apprise s'applique au relevé suivant contenant le même libellé.
    sid2 = _upload(client, synthetic, "synth_awb_22.pdf")["results"][0]["statement_id"]
    pattern = rule["Pattern"]
    from backend.tools.statements.templates import normalize
    same = [l for l in client.get(f"/api/statements/{sid2}").json()["lines"] if pattern in normalize(l["label"]) and l["debit"] > 0]
    assert all(l["category_id"] == 11 and l["project_id"] == 1 and l["suggestion_source"] == "apprise" for l in same)


def test_bad_inputs_are_refused(client, unified, synthetic):
    r = client.post("/api/statements/upload", data={"account_id": "1"}, files={"files": ("x.exe", b"MZ")})
    assert r.status_code == 400
    r = client.post("/api/statements/upload", data={"account_id": "999"}, files={"files": ("a.pdf", (synthetic / "synth_bp_44.pdf").read_bytes())}).json()
    assert "Compte introuvable" in r["results"][0]["error"]
    sid = _upload(client, synthetic, "synth_bp_44.pdf")["results"][0]["statement_id"]
    bad = dict(client.get(f"/api/statements/{sid}").json()["lines"][0], debit=100, credit=100)
    assert client.put(f"/api/statements/{sid}", json={"lines": [bad]}).status_code == 400
    assert client.delete(f"/api/statements/{sid}").json() == {"status": "deleted"}
    assert client.get(f"/api/statements/{sid}").status_code == 400


@pytest.mark.skipif(ocr.find_tesseract() is None, reason="Tesseract non installé")
def test_photographed_pages_of_one_statement(client, unified, synthetic):
    truth = json.loads((synthetic / "synth_cih_66.truth.json").read_text(encoding="utf-8"))
    files = [("files", (n, (synthetic / n).read_bytes())) for n in truth["files"]["scan_pages"]]
    r = client.post("/api/statements/upload", data={"account_id": "1", "mode": "pages"}, files=files).json()["results"]
    assert len(r) == 1 and r[0]["lines"] == 40 and r[0]["balance_ok"] is True
    st = client.get(f"/api/statements/{r[0]['statement_id']}").json()
    assert st["meta"]["pages"] == 2 and {l["page"] for l in st["lines"]} == {0, 1}


def test_unusual_fee_duplicate_line_and_continuity(client, unified, synthetic):
    sid = _upload(client, synthetic, "synth_bp_44.pdf")["results"][0]["statement_id"]
    st = client.get(f"/api/statements/{sid}").json()
    fee = next(l for l in st["lines"] if l["category_id"] == 12)
    copy = {k: v for k, v in fee.items() if k != "id"} | {"debit": 250_000, "credit": 0}
    st = client.put(f"/api/statements/{sid}", json={"lines": [dict(fee, debit=250_000, credit=0), copy]}).json()
    codes = {a["code"] for a in st["anomalies"]}
    assert {"UNUSUAL_FEE", "DUPLICATE_LINE"} <= codes
    assert "BALANCE" in {b["code"] for b in st["blocking"]}

    # Relevé suivant dont le solde initial ne suit pas : contrôle de continuité bloquant.
    sid2 = _upload(client, synthetic, "synth_awb_55.pdf")["results"][0]["statement_id"]   # juillet, après juin
    assert "CONTINUITY" in {b["code"] for b in client.get(f"/api/statements/{sid2}").json()["blocking"]}
