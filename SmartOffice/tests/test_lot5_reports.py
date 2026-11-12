import json
import sqlite3
from pathlib import Path

import pytest
from PIL import Image

from backend.config.settings import settings
from backend.core import unified_db
from backend.tools.reports import checks, finance, moral
from backend.tools.reports.context import layout, period, scope
from tests.unified_db_fixture import create_unified_db

SCENARIO = json.loads((Path(__file__).resolve().parents[2] / "SharedTestCases" / "annual_scenario.json").read_text(encoding="utf-8"))


def _load_scenario(conn):
    """Même scénario que AnnualScenarioTests (.NET), inséré directement (opérations déjà validées)."""
    conn.executescript("""
        INSERT INTO Funders (Id, Name, PrimaryColor, LogoPath, LegalMentions, HeaderText, FooterText) VALUES (1, 'Fonds Vert', '#0055A4', '', '', '', '');
        INSERT INTO Projects (Id, Name, Code, Description, Manager, Owner, Client, Department, Status, Priority, BudgetGlobal, LessonsLearned,
                              LocalFolderPath, Currency, IsDeleted, FunderId, TargetStartDate, TargetEndDate)
        VALUES (1, 'Projet 1', 'P1', 'Restaurer 50 ha de cédraie.', '', '', '', '', 'Exécution', 'Haute', 0, 'Retards de livraison des plants.', '', 'MAD', 0, 1,
                '2026-01-01 00:00:00', '2027-06-30 00:00:00'),
               (2, 'Sous-projet école', 'P1-E', '', '', '', '', '', 'Exécution', 'Haute', 0, '', '', 'MAD', 0, NULL, NULL, NULL),
               (3, 'Ancien projet', 'P0', '', '', '', '', '', 'Clôture', 'Basse', 0, '', '', 'MAD', 0, NULL, '2020-01-01 00:00:00', '2021-12-31 00:00:00');
        UPDATE Projects SET ParentProjectId = 1 WHERE Id = 2;
        INSERT INTO BudgetLines (Id, ProjectId, Code, Label, CategoryId, PlannedMinor, Currency, IsDeleted) VALUES (1, 1, '1', 'Projet', 7, 200000, 'MAD', 0),
               (2, NULL, 'F', 'Fonctionnement', 10, 100000, 'MAD', 0);
    """)
    ids = {}
    for r in SCENARIO["rates"]:
        conn.execute("INSERT INTO CurrencyRates (Currency, Date, RateToMad, Source) VALUES (?, ?, ?, 'test')", (r["currency"], r["date"], r["rate"]))
    for i, a in enumerate(SCENARIO["accounts"], start=1):
        conn.execute("INSERT INTO BankAccounts (Id, Kind, Purpose, BankName, Branch, Title, Rib, Currency, OpeningBalanceMinor, OpeningDate, Status, Notes, IsDeleted) "
                     "VALUES (?, 'Bank', 'Operating', 'BP', '', ?, NULL, ?, ?, ?, 'Active', '', 0)", (i, a["title"], a["currency"], a["opening"], a["opening_date"]))
        ids[a["key"]] = i
    conn.execute("INSERT INTO AccountProjectLinks (BankAccountId, ProjectId, ValidFrom, AllocationMode, IsDeleted) VALUES (1, 1, '2026-01-01', 'None', 0)")
    ops = {}
    for o in SCENARIO["operations"]:
        acc = next(a for a in SCENARIO["accounts"] if a["key"] == o["account"])
        mad = o["amount"] if acc["currency"] == "MAD" else int((__import__("decimal").Decimal(o["amount"]) * __import__("decimal").Decimal("10.95")).quantize(1, rounding="ROUND_HALF_UP"))
        cur = conn.execute("INSERT INTO Operations (BankAccountId, OperationDate, Label, Reference, ThirdParty, Direction, Nature, AmountMinor, Currency, RateToMad, "
                           "AmountMadMinor, Status, ValidatedBy, Notes, IsDeleted) VALUES (?, ?, ?, '', '', ?, ?, ?, ?, ?, ?, 'Validated', 't', '', 0)",
                           (ids[o["account"]], o["date"], o["label"], o["direction"], o["nature"], o["amount"], acc["currency"],
                            None if acc["currency"] == "MAD" else "10.95", mad))
        ops[o["key"]] = cur.lastrowid
        cat = {"Income": 1 if o["label"].startswith("Subvention") else 3, "Expense": 7}[o["nature"]]
        for al in o["allocations"]:
            conn.execute("INSERT INTO OperationAllocations (OperationId, ProjectId, BudgetLineId, CategoryId, AmountMinor) VALUES (?, ?, ?, ?, ?)",
                         (ops[o["key"]], 1 if al["project"] else None, 1 if al["project"] else 2, cat, al["amount"]))
    tr = SCENARIO["transfer"]
    g = "11111111-2222-3333-4444-555555555555"
    for acc, direction, amount, mad in ((tr["from"], "Debit", tr["amount"], tr["amount"]), (tr["to"], "Credit", tr["received"], 9997)):
        cur = conn.execute("INSERT INTO Operations (BankAccountId, OperationDate, Label, Reference, ThirdParty, Direction, Nature, AmountMinor, Currency, "
                           "AmountMadMinor, TransferGroupId, Status, ValidatedBy, Notes, IsDeleted) VALUES (?, ?, 'Virement', '', '', ?, 'InternalTransfer', ?, ?, ?, ?, "
                           "'Validated', 't', '', 0)", (ids[acc], tr["date"], direction, amount, "MAD" if acc == "A" else "EUR", mad, g))
        if direction == "Debit":
            ops["transfer_debit"] = cur.lastrowid
    st = SCENARIO["statement"]
    sid = conn.execute("INSERT INTO BankStatements (BankAccountId, PeriodStart, PeriodEnd, OpeningBalanceMinor, ClosingBalanceMinor, Source, Template, Status, "
                       "ImportedAtUtc, Notes, IsDeleted) VALUES (?, ?, ?, ?, ?, 'Csv', '', 'Validated', '2026-04-01', '', 0)",
                       (ids[st["account"]], st["start"], st["end"], st["opening"], st["closing"])).lastrowid
    for l in st["lines"]:
        lid = conn.execute("INSERT INTO StatementLines (BankStatementId, OperationDate, Label, Reference, DebitMinor, CreditMinor, ConfidenceJson) "
                           "VALUES (?, ?, 'x', '', ?, ?, '{}')", (sid, l["date"], max(0, -l["signed"]), max(0, l["signed"]))).lastrowid
        if l["match"]:
            conn.execute("INSERT INTO ReconciliationMatches (StatementLineId, OperationId, Mode, Score, MatchedAtUtc, MatchedBy) VALUES (?, ?, 'Manual', 1, '2026-04-01', 't')",
                         (lid, ops[l["match"]]))
    return ids, ops


@pytest.fixture()
def unified(tmp_path, monkeypatch):
    path = create_unified_db(tmp_path / "database.db")
    monkeypatch.setenv(unified_db.DESKTOP_DB_ENV, str(path))
    monkeypatch.setattr(settings, "data_dir", tmp_path / "data")
    conn = sqlite3.connect(str(path))
    _load_scenario(conn)
    conn.commit()
    conn.close()
    return path


def _conn():
    cm = unified_db.connect()
    return cm, cm.__enter__()


def test_shared_scenario_matches_dotnet(unified):
    exp = SCENARIO["expected"]
    with unified_db.connect() as conn:
        p = period(conn, SCENARIO["year"])
        assert (p.start, p.end) == ("2026-01-01", "2026-12-31")
        tot = finance.totals(conn, p, scope(conn, "association", None))
        assert (tot["income"], tot["expense"]) == (exp["income_mad"], exp["expense_mad"])
        assert finance.book_balance(conn, 1, "2026-03-31") == exp["balance_A_2026-03-31"]
        rec = finance.reconciliation_status(conn, 1, "2026-12-31")
        assert rec["difference"] == exp["reconciliation_difference"] and rec["unmatched_lines"] == exp["unmatched_lines"]
        p1 = finance.totals(conn, p, scope(conn, "project", 1))
        assert (p1["income"], p1["expense"]) == (exp["python_project_P1"]["income_mad"], exp["python_project_P1"]["expense_mad"])


def test_split_minor_matches_shared_vectors():
    vectors = json.loads((Path(__file__).resolve().parents[2] / "SharedTestCases" / "allocation_split.json").read_text(encoding="utf-8"))["cases"]
    from decimal import Decimal
    for c in vectors:
        # Le module Python ne reçoit que des poids entiers (montants) : on ramène les poids décimaux à l'échelle.
        weights = [int(Decimal(str(w)) * 100) for w in c["weights"]]
        assert finance.split_minor(c["total"], weights) == c["expected"]


def test_financial_statements_are_consistent(unified):
    with unified_db.connect() as conn:
        p, s, lay = period(conn, 2026), scope(conn, "association", None), layout()
        cer = finance.cer(conn, p, s, lay)
        assert cer["total"][1] == 589511 - 95001                       # résultat = ressources − emplois
        labels = [r[0] for r in cer["rows"]]
        assert "Subventions" in labels and "    Fonds Vert" in labels      # subventions détaillées par bailleur
        ie = finance.income_expense(conn, p, s)
        assert ie["total"][-1] == 589511 - 95001
        assert ie["columns"][1:-1] == ["P1", "Fonctionnement"]
        bud = finance.budget_execution(conn, p, s, "project")
        assert bud["total"][1:3] == [300000, 66667 + 33334 - 5000]
        tre = finance.treasury(conn, p, s)
        assert [r[2] for r in tre["rows"]] == [474999, 10001 + 913] and tre["rows"][1][3] == 119508   # 10 914 EUR × 10,95
        cmp_ = finance.comparison(conn, p, s, lay)
        assert cmp_["total"][1] == 0 and cmp_["total"][2] == 589511 - 95001
        pies = finance.charts(conn, p, s, lay)["pies"]
        assert sum(x["value"] for x in pies[0]["slices"]) == pytest.approx(5895.11)


def test_project_and_programme_scopes(unified):
    with unified_db.connect() as conn:
        assert scope(conn, "programme", 1).project_ids == [1, 2]
        assert scope(conn, "project", 1).account_ids == [1]
        assert scope(conn, "funder", 1).project_ids == [1]
        cer = finance.cer(conn, period(conn, 2026), scope(conn, "project", 1), layout())
        assert not any("fonctionnement" in r[0].lower() for r in cer["rows"])     # pas de frais de fonctionnement pour un projet
        assert [p["code"] for p in moral.projects(conn, period(conn, 2026), scope(conn, "association", None))] == ["P1", "P1-E"]
        with pytest.raises(ValueError):
            scope(conn, "galaxie", None)


def test_checks_and_generation(client, unified):
    db = sqlite3.connect(str(unified))
    db.execute("INSERT INTO Operations (BankAccountId, OperationDate, Label, Reference, ThirdParty, Direction, Nature, AmountMinor, Currency, "
               "AmountMadMinor, Status, ValidatedBy, Notes, IsDeleted) VALUES (1, '2026-05-01', 'Brouillon oublié', '', '', 'Debit', 'Expense', 100, 'MAD', 100, 'Draft', '', '', 0)")
    db.commit()
    r = client.post("/api/reports/checks", json={"year": 2026}).json()
    codes = {c["code"]: c["level"] for c in r["checks"]}
    assert codes["DRAFT_OPERATIONS"] == "blocking" and r["blocking"] is True
    assert codes["UNRECONCILED_ACCOUNT"] == "warning"                       # relevé arrêté au 31/03, ligne de frais non comptabilisée
    assert codes["MISSING_RECEIPT"] == "warning"
    gen = client.post("/api/reports/generate", json={"year": 2026, "kind": "both"})
    assert gen.status_code == 409 and gen.json()["detail"]["checks"]

    db.execute("UPDATE Operations SET IsDeleted = 1 WHERE Label = 'Brouillon oublié'")
    db.commit()
    res = client.post("/api/reports/generate", json={"year": 2026, "kind": "both", "language": "fr"}).json()
    doc = client.get(f"/api/documents/{res['document']['id']}").json()
    text = json.dumps(doc["content"], ensure_ascii=False)
    assert doc["title"] == "Rapport annuel 2026"
    for table in ("cer", "income_expense", "budget_project", "budget_funder", "treasury", "carry_forward", "comparison", "charts",
                  "activities", "indicators", "beneficiaries"):
        assert f'"table": "{table}"' in text
    assert "5 895,11 MAD" in text and "950,01 MAD" in text                 # synthèse chiffrée, tirée des données
    assert "Retards de livraison des plants." in text                        # difficultés : leçons apprises du projet
    assert "Fonds Vert" in text                                              # partenaires

    ar = client.post("/api/reports/generate", json={"year": 2026, "kind": "moral", "language": "ar", "scope_type": "project", "scope_id": 1}).json()
    ar_doc = client.get(f"/api/documents/{ar['document']['id']}").json()
    assert ar_doc["language"] == "ar" and ar_doc["project_id"] == 1 and ar_doc["funder_id"] == 1
    assert ar_doc["content"]["content"][0]["attrs"]["dir"] == "rtl" and "التقرير الأدبي" in ar_doc["title"]

    table = client.get("/api/reports/table/cer?year=2026&lang=en").json()
    assert table["title"] == "Statement of use of resources" and table["total"][1] == 494510
    assert client.get("/api/reports/table/inconnu?year=2026").status_code == 400


def test_indicators_measurements_and_beneficiaries(client, unified):
    ind = client.post("/api/indicators", json={"project_id": 1, "name": "Élèves sensibilisés", "unit": "élèves", "target": 300,
                                               "level": "Effet", "baseline": 0, "aggregation": "Somme"}).json()
    for m in [{"period_end": "2026-03-31", "value": 120}, {"period_end": "2026-03-31", "value": 70, "sex": "F", "age_group": "6-12 ans", "zone": "Azrou"},
              {"period_end": "2026-03-31", "value": 50, "sex": "M", "age_group": "6-12 ans", "zone": "Ifrane"},
              {"period_end": "2026-06-30", "value": 90}, {"period_end": "2025-12-31", "value": 999}]:
        assert client.post(f"/api/indicators/{ind['id']}/measurements", json=m).status_code == 200
    assert client.post(f"/api/indicators/{ind['id']}/measurements", json={"period_end": "2026-01-01", "value": 1, "sex": "X"}).status_code == 400
    rows = client.get("/api/reports/table/indicators?year=2026").json()["rows"]
    row = next(r for r in rows if r[1] == "Élèves sensibilisés")
    assert row[5] == 210 and row[6] == 70.0                              # mesures non désagrégées de 2026 seulement (120 + 90)
    ben = client.get("/api/reports/table/beneficiaries?year=2026").json()["rows"]
    assert ["    Femmes", 70] in ben and ["    Hommes", 50] in ben and ["    Azrou", 70] in ben
    listed = client.get("/api/indicators?project_id=1").json()[0]
    assert listed["current"] == 120 + 90 + 999 and len(listed["measurements"]) == 5
    assert client.post("/api/indicators", json={"project_id": 1, "name": "X", "level": "Galaxie"}).status_code == 400


def test_legacy_activity_photos_are_imported_once(client, unified, tmp_path):
    img = tmp_path / "ancienne.jpg"
    Image.new("RGB", (300, 200), "green").save(img)
    db = sqlite3.connect(str(unified))
    db.executescript(f"""
        INSERT INTO Tasks (Id, ProjectId, Name, Description, Assignee, ProgressPercentage, Status, Budget, Cost, Predecessors) VALUES (1, 1, 'T', '', '', 0, '', 0, 0, '');
        INSERT INTO ActivityReports (Id, Title, ActivityDate, Location, ParticipantsCount, Narrative, Difficulties, Recommendations, Status, ProjectTaskId)
        VALUES (1, 'Atelier', '2026-03-12 00:00:00', 'Azrou', 20, '', '', '', 'Validé', 1);
        INSERT INTO ActivityReportPhotos (LocalFilePath, Caption, ActivityReportId) VALUES ('{img}', 'Atelier avec les femmes', 1), ('C:/absent.jpg', '', 1);
    """)
    db.commit()
    r = client.post("/api/photos/import-legacy").json()
    assert r["imported"] == 1 and r["missing_count"] == 1
    p = client.get("/api/photos?project_id=1").json()[0]
    assert p["caption"] == "Atelier avec les femmes" and p["caption_validated"] and not p["consent"] and p["taken_at"].startswith("2026-03-12")
    assert client.post("/api/photos/import-legacy").json()["imported"] == 0
