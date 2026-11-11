"""Lot 8 — parcours de bout en bout sur la base de démonstration (construite par le vrai pipeline), alertes par
e-mail et performance sur un volume de plusieurs années."""
import io
import json
import os
import sqlite3
import time
import zipfile
from pathlib import Path

import pytest
from openpyxl import load_workbook

from backend.config.settings import settings
from backend.core import notifications, smtp, unified_db


@pytest.fixture(scope="module")
def demo(tmp_path_factory):
    saved = {k: os.environ.get(k) for k in ("AFMI_DESKTOP_DB", "AFMI_DATA_DIR", "AFMI_AUDIT_USER", "OLLAMA_URL")}
    saved_dir = settings.data_dir
    from demo.build_demo import build
    out = tmp_path_factory.mktemp("demo") / "paquet"
    manifest = build(out)
    yield out, manifest
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    settings.data_dir = saved_dir


@pytest.fixture()
def demo_env(demo, monkeypatch):
    out, manifest = demo
    monkeypatch.setenv("AFMI_DESKTOP_DB", str(out / "database.db"))
    monkeypatch.setattr(settings, "data_dir", out / "data")
    return out, manifest


def test_demo_content(demo_env):
    out, manifest = demo_env
    assert (manifest["projects"], manifest["accounts"], len(manifest["statements"])) == (3, 3, 12)
    assert json.loads((out / "demo.json").read_text(encoding="utf-8"))["year"] == 2026
    with unified_db.connect() as c:
        q = lambda sql: c.execute(sql).fetchone()[0]
        assert q("SELECT COUNT(*) FROM BankStatements WHERE Status = 'Validated'") == 11      # un relevé laissé « à vérifier »
        assert q("SELECT COUNT(*) FROM Operations WHERE Status = 'Draft'") == 2
        assert q("SELECT COUNT(*) FROM ReconciliationMatches") == q("SELECT COUNT(*) FROM Operations WHERE Status = 'Validated'")
        # Toute opération validée est ventilée intégralement sur une ligne budgétaire (règle de la source unique)
        assert q("SELECT COUNT(*) FROM Operations o WHERE o.Status = 'Validated' AND o.AmountMinor <> "
                 "(SELECT COALESCE(SUM(AmountMinor), 0) FROM OperationAllocations a WHERE a.OperationId = o.Id AND a.BudgetLineId IS NOT NULL)") == 0
        assert {r[0] for r in c.execute("SELECT DocType FROM Documents")} == {"Convention", "Rapport narratif", "Procès-verbal"}
        assert q("SELECT COUNT(*) FROM ReportingObligations") >= 3 and q("SELECT COUNT(*) FROM Photos WHERE ConsentGiven = 1") == 10
        assert unified_db.find_first_tampered_audit_entry(c) is None                         # journal d'audit intact
    from backend.tools.reports import finance
    with unified_db.connect() as c:
        for a in c.execute("SELECT Id, Title FROM BankAccounts WHERE Currency = 'MAD'"):
            assert finance.reconciliation_status(c, a["Id"], "2026-12-31")["difference"] == 0


def test_end_to_end_reports_and_exports(client, demo_env):
    checks = client.post("/api/reports/checks", json={"year": 2026, "scope_type": "association"}).json()
    assert {c["code"] for c in checks["checks"]} >= {"DRAFT_OPERATIONS"}                     # les brouillons sont signalés
    doc_id = demo_env[1]["annual_report_document"]
    docx = client.get(f"/api/exports/document/{doc_id}?format=docx")
    assert docx.status_code == 200 and "ACA_Rapport_annuel" in docx.headers["X-AFMI-Filename"]
    wb = load_workbook(io.BytesIO(client.get("/api/exports/statements?year=2026").content))
    assert "Contrôles" in wb.sheetnames
    search = client.get("/api/ged/search", params={"q": "rapport semestriel", "project_id": 1}).json()
    assert search["results"] and search["results"][0]["title"].startswith("Convention")
    ops = load_workbook(io.BytesIO(client.get("/api/exports/operations").content))
    assert len(ops.sheetnames) == 3


def test_annual_package_on_demo(client, demo_env):
    from backend.tools.exports import pdf
    if not (pdf.engines()["browser"] or pdf.engines()["libreoffice"]):
        pytest.skip("Aucun moteur PDF")
    with unified_db.connect() as c:
        convention = c.execute("SELECT Id FROM Documents WHERE DocType = 'Convention'").fetchone()[0]
    r = client.post("/api/exports/annual-package", json={"year": 2026, "annex_ids": [convention], "formats": ["pdf", "xlsx"]})
    # Rapport financier refusé : opérations en brouillon (contrôle bloquant) — comportement attendu, message explicite
    assert r.status_code == 400 and "brouillon" in r.json()["detail"]
    doc_id = demo_env[1]["annual_report_document"]
    r = client.post("/api/exports/annual-package", json={"year": 2026, "moral_document_id": doc_id, "financial_document_id": doc_id,
                                                         "annex_ids": [convention], "formats": ["pdf"]})
    assert r.status_code == 200
    names = zipfile.ZipFile(io.BytesIO(r.content)).namelist()
    assert "ACA_RapportAnnuel_2026_FR.pdf" in names and "Annexes/Convention_FV-2026-07.pdf" in names


# --- Alertes par e-mail ---------------------------------------------------------------------------------------

def test_alert_digest_sent_once_then_reminded(demo_env, monkeypatch):
    sent = []
    monkeypatch.setattr(smtp, "send", lambda subject, body, recipients: sent.append((subject, body, recipients)))
    unified_db.set_setting("notifications.recipients", "da@example.org")
    alerts = notifications.collect()
    assert any(a["kind"] == "Trésorerie" and "Compte de fonctionnement" in a["message"] for a in alerts)   # sous le seuil d'alerte
    r = notifications.run()
    assert r["sent"] and sent[0][2] == ["da@example.org"] and "[nouveau]" in sent[0][1]
    assert notifications.run()["sent"] is False                                     # rien de nouveau : pas de second message
    from datetime import datetime, timedelta
    assert notifications.run(now=datetime.now() + timedelta(days=8))["sent"] is True  # rappel après 7 jours
    monkeypatch.setenv("AFMI_DEMO", "1")
    assert notifications.run(force=True)["sent"] is False                          # jamais depuis une démonstration
    with unified_db.connect() as c:
        assert c.execute("SELECT COUNT(*) FROM AuditEntries WHERE EntityType = 'Notification'").fetchone()[0] == 2


def test_alerts_follow_preferences(demo_env):
    unified_db.set_setting("notifications.events", {"obligations": False, "treasury": False, "reconciliation": True, "backup_failure": True})
    unified_db.set_setting("backup.last_error", "11/11/2026 09:00 — disque plein")
    kinds = {a["kind"] for a in notifications.collect()}
    assert "Trésorerie" not in kinds and "Sauvegardes" in kinds and "Rapprochement" in kinds
    unified_db.set_setting("notifications.events", {"obligations": True, "treasury": True, "reconciliation": False, "backup_failure": True})


# --- Performance ----------------------------------------------------------------------------------------------

def test_performance_on_five_years_of_operations(tmp_path, monkeypatch):
    """~15 000 opérations ventilées sur 5 ans, 3 comptes : états du rapport annuel et classeur Excel en quelques secondes."""
    from tests.unified_db_fixture import create_unified_db
    from backend.tools.exports import xlsx_writer
    from backend.tools.reports import generator
    path = create_unified_db(tmp_path / "database.db")
    monkeypatch.setenv("AFMI_DESKTOP_DB", str(path))
    conn = sqlite3.connect(str(path))
    conn.executescript("""
        INSERT INTO Projects (Id, Name, Code, Description, Manager, Owner, Client, Department, Status, Priority, BudgetGlobal, LessonsLearned,
                              LocalFolderPath, Currency, IsDeleted) VALUES (1, 'A', 'PA', '', '', '', '', '', 'Exécution', 'Haute', 0, '', '', 'MAD', 0),
               (2, 'B', 'PB', '', '', '', '', '', 'Exécution', 'Haute', 0, '', '', 'MAD', 0);
        INSERT INTO BudgetLines (Id, ProjectId, Code, Label, CategoryId, PlannedMinor, Currency, IsDeleted) VALUES
               (1, 1, 'A1', 'A', 7, 900000000, 'MAD', 0), (2, 2, 'B1', 'B', 8, 900000000, 'MAD', 0), (3, NULL, 'F', 'F', 10, 900000000, 'MAD', 0);
    """)
    for acc in (1, 2, 3):
        conn.execute("INSERT INTO BankAccounts (Id, Kind, Purpose, BankName, Branch, Title, Currency, OpeningBalanceMinor, OpeningDate, Status, Notes, IsDeleted) "
                     "VALUES (?, 'Bank', 'Operating', 'B', '', ?, 'MAD', 0, '2022-01-01', 'Active', '', 0)", (acc, f"Compte {acc}"))
    import random
    rnd = random.Random(1)
    ops, allocs = [], []
    for i in range(1, 15_001):
        day = f"{2022 + i % 5}-{1 + i % 12:02d}-{1 + i % 28:02d}"
        income = i % 7 == 0
        amount = rnd.randint(1_000, 5_000_000)
        ops.append((i, 1 + i % 3, day, f"Op {i}", "Credit" if income else "Debit", "Income" if income else "Expense", amount, amount))
        if i % 3 == 0:                       # ventilation multiple
            half = amount // 2
            allocs += [(i, 1, 1, 1 if income else 7, half), (i, 2, 2, 1 if income else 8, amount - half)]
        else:
            allocs.append((i, None, 3, 2 if income else 10, amount))
    conn.executemany("INSERT INTO Operations (Id, BankAccountId, OperationDate, Label, Reference, ThirdParty, Direction, Nature, AmountMinor, Currency, "
                     "AmountMadMinor, Status, ValidatedBy, Notes, IsDeleted) VALUES (?, ?, ?, ?, '', '', ?, ?, ?, 'MAD', ?, 'Validated', 't', '', 0)", ops)
    conn.executemany("INSERT INTO OperationAllocations (OperationId, ProjectId, BudgetLineId, CategoryId, AmountMinor) VALUES (?, ?, ?, ?, ?)", allocs)
    conn.commit()
    conn.close()
    t = time.perf_counter()
    for name in ("cer", "income_expense", "budget_project", "treasury", "comparison", "charts"):
        generator.table(name, 2025, "association", None)
    tables = time.perf_counter() - t
    t = time.perf_counter()
    wb = load_workbook(io.BytesIO(xlsx_writer.financial_workbook(2025)))
    workbook = time.perf_counter() - t
    assert wb["Ventilations"].max_row > 3000
    print(f"\n[perf] états : {tables:.2f} s ; classeur Excel : {workbook:.2f} s")
    assert tables < 15 and workbook < 30


def test_packaging_ships_every_configuration_file():
    """Le backend compilé (PyInstaller) doit embarquer tous les fichiers de configuration et les modèles de python-docx."""
    script = (Path(__file__).resolve().parents[1] / "build_backend.bat").read_text(encoding="utf-8")
    assert r"backend\config\*.json;backend\config" in script and "--collect-data docx" in script
    iss = (Path(__file__).resolve().parents[2] / "installer" / "AFMI_Smart_Admin.iss").read_text(encoding="utf-8-sig")
    assert '#define AppVersion "2.0.1"' in iss and "Amiri-Regular.ttf" in iss


def test_frontend_assets_have_browser_mime_types(client, monkeypatch):
    """Page blanche sous Windows si .js est servi en text/plain (registre) : les types sont imposés au démarrage."""
    import mimetypes
    assert mimetypes.guess_type("index-abc.js")[0] == "application/javascript"
    assert mimetypes.guess_type("index-abc.css")[0] == "text/css"
