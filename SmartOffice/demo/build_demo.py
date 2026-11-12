"""Construction de la base de DÉMONSTRATION d'AFMI Smart Admin (Lot 8).

Association fictive, 3 projets, 3 comptes bancaires (dont un en euros), 12 relevés mensuels (janvier à avril 2026),
conventions, budgets, indicateurs, activités, photos, documents de la GED et rapport annuel.

Les données passent par les mêmes traitements que dans l'application : chaque relevé est un PDF lu par le pipeline
des relevés, corrigé (imputation), validé, intégré en opérations, puis les opérations sont validées et rapprochées ;
les documents de la GED sont analysés ; le rapport annuel est généré par l'assistant. La démonstration montre donc
le comportement réel, et sa construction sert de test de bout en bout.

Rien n'est écrit ailleurs que dans le dossier de sortie (jamais dans la base réelle du poste).

Usage : python -m demo.build_demo <dossier_de_sortie>
"""
import asyncio
import io
import json
import os
import random
import sqlite3
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "tests" / "fixtures" / "unified_schema.sql"     # script des migrations EF Core (contrôlé par Core.Tests)

YEAR = 2026
MONTHS = [1, 2, 3, 4]
ASSOCIATION = "Association des Cèdres de l'Atlas (démonstration)"


def _prepare(out: Path) -> Path:
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"Le dossier {out} n'est pas vide : choisissez un dossier neuf.")
    out.mkdir(parents=True, exist_ok=True)
    db = out / "database.db"
    conn = sqlite3.connect(str(db))
    conn.create_function("afmi_legacy_amount", 1, lambda v: float(v or 0))
    conn.executescript(SCHEMA.read_text(encoding="utf-8-sig"))
    conn.close()
    os.environ["AFMI_DESKTOP_DB"] = str(db)
    os.environ["AFMI_DATA_DIR"] = str(out / "data")
    os.environ["AFMI_AUDIT_USER"] = "demonstration"
    os.environ["LLM_PROVIDER"] = "heuristic"
    os.environ["GEMINI_API_KEY"] = ""
    os.environ["OLLAMA_URL"] = "http://127.0.0.1:9"     # aucun appel à une IA pendant la construction
    return db


# --- Référentiel ----------------------------------------------------------------------------------------------

FUNDERS = [
    {"key": "FV", "Name": "Fonds Vert pour les Forêts (fictif)", "PrimaryColor": "#0B6E4F", "HeaderText": "Projet cofinancé par le Fonds Vert pour les Forêts",
     "LegalMentions": "Le contenu de ce document relève de la seule responsabilité de l'association."},
    {"key": "FA", "Name": "Fondation Atlas pour l'Eau (fictive)", "PrimaryColor": "#1D4E89", "HeaderText": "", "LegalMentions": "Avec le soutien de la Fondation Atlas pour l'Eau."},
]
PROJECTS = [
    {"Code": "P-CEDRE", "Name": "Restauration de la cédraie d'Azrou", "funder": "FV", "Status": "Exécution", "start": "2026-01-01", "end": "2027-12-31",
     "Description": "Restaurer 60 ha de cédraie dégradée avec les coopératives et les écoles riveraines.", "Manager": "Salma Idrissi (fictive)",
     "LessonsLearned": "Les livraisons de plants doivent être commandées trois mois à l'avance."},
    {"Code": "P-EAU", "Name": "Gestion durable de l'eau à Tizguit", "funder": "FA", "Status": "Exécution", "start": "2026-02-01", "end": "2027-07-31",
     "Description": "Équiper 3 douars de systèmes d'irrigation économes et former les usagers.", "Manager": "Youssef Alaoui (fictif)", "LessonsLearned": ""},
    {"Code": "P-EDU", "Name": "Éducation à l'environnement", "funder": None, "Status": "Exécution", "start": "2026-01-01", "end": "2026-12-31",
     "Description": "Sensibiliser 400 élèves aux écosystèmes du Moyen Atlas (fonds propres).", "Manager": "Nadia Bennani (fictive)", "LessonsLearned": ""},
]
# (code, libellé, catégorie, prévu en unités, devise, projet, convention)
BUDGET = [
    ("F-LOY", "Loyer du siège", "LOC", 54_000, "MAD", None, None),
    ("F-PERS", "Personnel permanent", "PERS", 260_000, "MAD", None, None),
    ("F-BQ", "Frais bancaires", "FBQ", 1_500, "MAD", None, None),
    ("F-REC", "Recettes de fonctionnement (cotisations, dons, prestations)", None, 0, "MAD", None, None),
    ("E-SUP", "Supports pédagogiques", "ACH", 8_000, "MAD", "P-EDU", None),
    ("E-ANIM", "Animation des ateliers", "HONO", 20_000, "MAD", "P-EDU", None),
    ("C-PLANTS", "Plants et plantation", "ACH", 350_000, "MAD", "P-CEDRE", "FV"),
    ("C-TRANS", "Transport et logistique", "DEPL", 60_000, "MAD", "P-CEDRE", "FV"),
    ("C-COOP", "Contrats des coopératives", "HONO", 120_000, "MAD", "P-CEDRE", "FV"),
    ("C-FRAIS", "Frais bancaires du projet", "FBQ", 2_000, "MAD", "P-CEDRE", "FV"),
    ("C-REC", "Subvention du Fonds Vert (recette)", None, 0, "MAD", "P-CEDRE", "FV"),
    ("W-ETUDE", "Études hydrauliques", "HONO", 20_000, "EUR", "P-EAU", "FA"),
    ("W-EQP", "Matériel d'irrigation", "EQP", 15_000, "EUR", "P-EAU", "FA"),
    ("W-FRAIS", "Frais bancaires du projet", "FBQ", 500, "EUR", "P-EAU", "FA"),
    ("W-REC", "Subvention de la Fondation Atlas (recette)", None, 0, "EUR", "P-EAU", "FA"),
]
ACCOUNTS = [
    {"key": "FCT", "Title": "Compte de fonctionnement", "BankName": "Banque Populaire", "Branch": "Azrou", "Currency": "MAD", "Purpose": "Operating",
     "layout": "bp", "opening": 85_000_00, "opening_date": "2026-01-01", "low": 20_000_00, "rib22": "1902101234567890123456"},
    {"key": "CED", "Title": "Compte projet Cèdre", "BankName": "Attijariwafa Bank", "Branch": "Ifrane", "Currency": "MAD", "Purpose": "Project",
     "layout": "awb", "opening": 0, "opening_date": "2026-01-01", "low": None, "rib22": "0073301234500012345678", "project": "P-CEDRE"},
    {"key": "EUR", "Title": "Compte Fondation Atlas (EUR)", "BankName": "CIH Bank", "Branch": "Meknès", "Currency": "EUR", "Purpose": "Project",
     "layout": "cih", "opening": 0, "opening_date": "2026-01-01", "low": None, "rib22": "2304501234567890987654", "project": "P-EAU"},
]
EUR_RATES = {"2026-01-01": "10.86", "2026-02-01": "10.91", "2026-03-01": "10.95", "2026-04-01": "10.89"}

# Lignes des relevés : (jour, libellé, sens, montant en unités, catégorie, ligne budgétaire)
D, C = "D", "C"
STATEMENTS = {
    "FCT": {
        1: [(5, "PRLV LOYER SIEGE AZROU", D, 4_500, "LOC", "F-LOY"), (10, "VIR EMIS SALAIRES 01/2026", D, 18_000, "PERS", "F-PERS"),
            (12, "PRLV CNSS 01/2026", D, 2_300, "PERS", "F-PERS"), (15, "VERSEMENT ESPECES COTISATIONS", C, 6_000, "COTIS", "F-REC"),
            (20, "PAIEMENT TPE PAPETERIE ATLAS", D, 650, "ACH", "E-SUP"), (30, "FRAIS TENUE DE COMPTE", D, 45, "FBQ", "F-BQ")],
        2: [(5, "PRLV LOYER SIEGE AZROU", D, 4_500, "LOC", "F-LOY"), (10, "VIR EMIS SALAIRES 02/2026", D, 18_000, "PERS", "F-PERS"),
            (12, "PRLV CNSS 02/2026", D, 2_300, "PERS", "F-PERS"), (18, "VIR RECU DON ASSOCIATION AMIS", C, 10_000, "DONS", "F-REC"),
            (25, "VIR EMIS ATELIERS ECOLES NATURE", D, 3_200, "HONO", "E-ANIM"), (27, "FRAIS TENUE DE COMPTE", D, 45, "FBQ", "F-BQ")],
        3: [(5, "PRLV LOYER SIEGE AZROU", D, 4_500, "LOC", "F-LOY"), (10, "VIR EMIS SALAIRES 03/2026", D, 18_000, "PERS", "F-PERS"),
            (12, "PRLV CNSS 03/2026", D, 2_300, "PERS", "F-PERS"), (16, "VERSEMENT ESPECES COTISATIONS", C, 1_500, "COTIS", "F-REC"),
            (22, "VIR RECU PRESTATION FORMATION", C, 7_500, "PREST", "F-REC"), (24, "PAIEMENT TPE PAPETERIE ATLAS", D, 1_240, "ACH", "E-SUP"),
            (31, "FRAIS TENUE DE COMPTE", D, 45, "FBQ", "F-BQ")],
        4: [(6, "PRLV LOYER SIEGE AZROU", D, 4_500, "LOC", "F-LOY"), (10, "VIR EMIS SALAIRES 04/2026", D, 18_000, "PERS", "F-PERS"),
            (13, "PRLV CNSS 04/2026", D, 2_300, "PERS", "F-PERS"), (22, "VIR EMIS ATELIERS ECOLES NATURE", D, 3_200, "HONO", "E-ANIM"),
            (30, "FRAIS TENUE DE COMPTE", D, 45, "FBQ", "F-BQ")],
    },
    "CED": {
        1: [(8, "VIR RECU FONDS VERT CONVENTION FV-2026-07", C, 300_000, "SUBV", "C-REC"), (19, "VIR EMIS PEPINIERE MOYEN ATLAS", D, 45_000, "ACH", "C-PLANTS"),
            (19, "COMMISSION SUR VIREMENT", D, 30, "FBQ", "C-FRAIS")],
        2: [(9, "VIR EMIS PEPINIERE MOYEN ATLAS", D, 38_000, "ACH", "C-PLANTS"), (9, "COMMISSION SUR VIREMENT", D, 30, "FBQ", "C-FRAIS"),
            (21, "CHQ 4410021 TRANSPORT PLANTS", D, 6_500, "DEPL", "C-TRANS")],
        3: [(4, "VIR EMIS PEPINIERE MOYEN ATLAS", D, 52_000, "ACH", "C-PLANTS"), (4, "COMMISSION SUR VIREMENT", D, 30, "FBQ", "C-FRAIS"),
            (14, "VIR EMIS COOPERATIVE TIMAHDITE", D, 12_000, "HONO", "C-COOP"), (14, "COMMISSION SUR VIREMENT", D, 30, "FBQ", "C-FRAIS"),
            (26, "CHQ 4410022 TRANSPORT PLANTS", D, 8_200, "DEPL", "C-TRANS")],
        4: [(8, "VIR EMIS PEPINIERE MOYEN ATLAS", D, 30_000, "ACH", "C-PLANTS"), (8, "COMMISSION SUR VIREMENT", D, 30, "FBQ", "C-FRAIS"),
            (15, "VIR EMIS COOPERATIVE TIMAHDITE", D, 12_000, "HONO", "C-COOP"), (15, "COMMISSION SUR VIREMENT", D, 30, "FBQ", "C-FRAIS")],
    },
    "EUR": {
        1: [(20, "FRAIS OUVERTURE DE COMPTE", D, 25, "FBQ", "W-FRAIS")],
        2: [(3, "VIR RECU FONDATION ATLAS TRANCHE 1", C, 20_000, "SUBV", "W-REC"), (17, "VIR EMIS BUREAU ETUDES HYDRO", D, 3_500, "HONO", "W-ETUDE"),
            (28, "FRAIS TENUE DE COMPTE", D, 8, "FBQ", "W-FRAIS")],
        3: [(12, "VIR EMIS BUREAU ETUDES HYDRO", D, 2_800, "HONO", "W-ETUDE"), (19, "PAIEMENT MATERIEL IRRIGATION", D, 5_200, "EQP", "W-EQP"),
            (31, "FRAIS TENUE DE COMPTE", D, 8, "FBQ", "W-FRAIS")],
        4: [(16, "VIR EMIS BUREAU ETUDES HYDRO", D, 4_100, "HONO", "W-ETUDE"), (30, "FRAIS TENUE DE COMPTE", D, 8, "FBQ", "W-FRAIS")],
    },
}
LEFT_TO_REVIEW = ("EUR", 4)                 # dernier relevé laissé « à vérifier » pour montrer l'écran de validation


def _month_end(m: int) -> date:
    return (date(YEAR, m + 1, 1) if m < 12 else date(YEAR + 1, 1, 1)) - timedelta(days=1)


def _rib(first22: str) -> str:
    return first22 + f"{97 - (int(first22) * 100) % 97:02d}"


# --- Construction ---------------------------------------------------------------------------------------------

def build(out: Path) -> dict:
    db = _prepare(out)
    sys.path.insert(0, str(ROOT))
    from backend.config.settings import settings
    settings.data_dir = out / "data"            # même si le backend a déjà été importé (tests)
    from backend.core import unified_db
    from backend.tools.ged import service as ged
    from backend.tools.editor import charts, photos
    from backend.tools.reports import generator
    from backend.tools.statements import pipeline, store
    from tests.tools.statement_fixtures import render_pdf

    ids = {"funders": {}, "projects": {}, "lines": {}, "accounts": {}, "agreements": {}, "tasks": {}, "categories": {}}
    with unified_db.connect() as conn:
        ids["categories"] = {r["Code"]: r["Id"] for r in conn.execute("SELECT Id, Code FROM Categories")}
    for key, value in (("association.name", ASSOCIATION), ("association.acronym", "ACA"),
                       ("association.address", "12, avenue des Cèdres, Azrou (adresse fictive)")):
        unified_db.set_setting(key, value)

    logo_dir = out / "data" / "logos"
    logo_dir.mkdir(parents=True, exist_ok=True)
    with unified_db.connect() as conn:
        for f in FUNDERS:
            logo = logo_dir / f"{f['key']}.png"
            _logo(f["Name"].split(" (")[0], f["PrimaryColor"]).save(logo)
            ids["funders"][f["key"]] = unified_db.insert(conn, "Funders", "Funder", {
                "Name": f["Name"], "PrimaryColor": f["PrimaryColor"], "LogoPath": str(logo), "LegalMentions": f["LegalMentions"],
                "HeaderText": f["HeaderText"], "FooterText": ""})
        for p in PROJECTS:
            ids["projects"][p["Code"]] = unified_db.insert(conn, "Projects", "Project", {
                "Name": p["Name"], "Code": p["Code"], "Description": p["Description"], "Manager": p["Manager"], "Owner": "", "Client": "",
                "Department": "", "Status": p["Status"], "Priority": "Haute", "BudgetGlobal": 0, "LessonsLearned": p["LessonsLearned"],
                "LocalFolderPath": "", "Currency": "MAD", "IsDeleted": 0, "FunderId": ids["funders"].get(p["funder"]),
                "TargetStartDate": f"{p['start']} 00:00:00", "TargetEndDate": f"{p['end']} 00:00:00", "ActualStartDate": f"{p['start']} 00:00:00"})
        unified_db.insert(conn, "FiscalYears", "FiscalYear", {"Year": YEAR, "StartDate": f"{YEAR}-01-01", "EndDate": f"{YEAR}-12-31", "Status": "Open"})
        for day, rate in EUR_RATES.items():
            unified_db.insert(conn, "CurrencyRates", "CurrencyRate", {"Currency": "EUR", "Date": day, "RateToMad": rate, "Source": "Bank Al-Maghrib (valeur de démonstration)"})
        ids["agreements"]["FV"] = unified_db.insert(conn, "FundingAgreements", "FundingAgreement", {
            "FunderId": ids["funders"]["FV"], "ProjectId": ids["projects"]["P-CEDRE"], "Reference": "FV-2026-07", "Title": "Restauration de la cédraie d'Azrou",
            "AmountMinor": 600_000_00, "Currency": "MAD", "ContractualRateToMad": None, "SignatureDate": "2025-12-15", "StartDate": "2026-01-01",
            "EndDate": "2027-12-31", "Notes": "", "IsDeleted": 0})
        ids["agreements"]["FA"] = unified_db.insert(conn, "FundingAgreements", "FundingAgreement", {
            "FunderId": ids["funders"]["FA"], "ProjectId": ids["projects"]["P-EAU"], "Reference": "FA-EAU-2026", "Title": "Eau et irrigation économe à Tizguit",
            "AmountMinor": 40_000_00, "Currency": "EUR", "ContractualRateToMad": "10.90", "SignatureDate": "2026-01-20", "StartDate": "2026-02-01",
            "EndDate": "2027-07-31", "Notes": "", "IsDeleted": 0})
        tranches = {}
        for ag, label, day, amount in (("FV", "Tranche 1 (50 %)", "2026-01-10", 300_000_00), ("FV", "Tranche 2 (50 %)", "2026-09-30", 300_000_00),
                                       ("FA", "Tranche 1", "2026-02-05", 20_000_00), ("FA", "Tranche 2", "2026-10-15", 20_000_00)):
            tranches[(ag, label)] = unified_db.insert(conn, "FundingTranches", "FundingTranche", {
                "FundingAgreementId": ids["agreements"][ag], "Label": label, "ExpectedDate": day, "AmountMinor": amount, "ReceivedOperationId": None, "IsDeleted": 0})
        fy = conn.execute("SELECT Id FROM FiscalYears WHERE Year = ?", (YEAR,)).fetchone()[0]
        for code, label, cat, planned, cur, project, ag in BUDGET:
            ids["lines"][code] = unified_db.insert(conn, "BudgetLines", "BudgetLine", {
                "ProjectId": ids["projects"].get(project), "FundingAgreementId": ids["agreements"].get(ag), "FiscalYearId": None if project else fy,
                "Code": code, "Label": label, "CategoryId": ids["categories"].get(cat), "PlannedMinor": planned * 100, "Currency": cur, "IsDeleted": 0})
        for a in ACCOUNTS:
            ids["accounts"][a["key"]] = unified_db.insert(conn, "BankAccounts", "BankAccount", {
                "Kind": "Bank", "Purpose": a["Purpose"], "BankName": a["BankName"], "Branch": a["Branch"], "Title": a["Title"], "Rib": _rib(a["rib22"]),
                "Currency": a["Currency"], "OpeningBalanceMinor": a["opening"], "OpeningDate": a["opening_date"], "Status": "Active",
                "ClosedDate": None, "Notes": "Compte fictif (démonstration).", "IsDeleted": 0, "LowBalanceThresholdMinor": a["low"]})
            if a.get("project"):
                unified_db.insert(conn, "AccountProjectLinks", "AccountProjectLink", {
                    "BankAccountId": ids["accounts"][a["key"]], "ProjectId": ids["projects"][a["project"]], "ValidFrom": a["opening_date"],
                    "ValidTo": None, "AllocationMode": "None", "AllocationPercent": None, "AllocationAmountMinor": None, "IsDeleted": 0})

    # Charte du Fonds Vert : logo en en-tête
    charts.save_chart({"name": "Charte Fonds Vert", "scope": "Funder", "funder_id": ids["funders"]["FV"],
                       "style": {"colors": {"primary": "#0B6E4F", "secondary": "#C9A227"}, "footer": {"page_numbers": True, "first_page_different": True}}})

    # --- 12 relevés : PDF → pipeline → imputation → validation → intégration → validation des opérations → rapprochement
    statements = []
    for a in ACCOUNTS:
        balance = a["opening"]
        for m in MONTHS:
            rows = STATEMENTS[a["key"]][m]
            lines = []
            for day, label, sense, amount, cat, line in rows:
                d = date(YEAR, m, day).isoformat()
                lines.append({"date": d, "value_date": d, "label": label, "debit": amount * 100 if sense == D else 0, "credit": amount * 100 if sense == C else 0})
            closing = balance + sum(l["credit"] - l["debit"] for l in lines)
            truth = {"layout": a["layout"], "bank": a["BankName"].upper(), "rib": _rib(a["rib22"]), "period_start": date(YEAR, m, 1).isoformat(),
                     "period_end": _month_end(m).isoformat(), "opening": balance, "closing": closing, "lines": lines}
            pdf = render_pdf(truth)
            name = f"Releve_{a['key']}_{YEAR}-{m:02d}.pdf"
            (out / "releves").mkdir(exist_ok=True)
            (out / "releves" / name).write_bytes(pdf)
            result = pipeline.process(pdf, name)
            sid = store.save_extraction(ids["accounts"][a["key"]], result, pdf, name)
            st = store.get_statement(sid)
            if len(st["lines"]) != len(rows):
                raise RuntimeError(f"{name} : {len(st['lines'])} lignes lues pour {len(rows)} attendues.")
            corrections = []
            for line, (day, label, sense, amount, cat, bline) in zip(sorted(st["lines"], key=lambda l: (l["date"], l["id"])), rows):
                if line["debit"] + line["credit"] != amount * 100:
                    raise RuntimeError(f"{name} : montant lu {line['debit'] + line['credit']} pour {amount * 100} ({label}).")
                project = next((p for c, _, _, _, _, p, _ in BUDGET if c == bline), None)
                corrections.append({**{k: line[k] for k in ("id", "date", "value_date", "label", "reference", "debit", "credit")},
                                    "category_id": ids["categories"][cat], "project_id": ids["projects"].get(project), "budget_line_id": ids["lines"][bline]})
            store.save_corrections(sid, {"lines": corrections})
            statements.append({"file": name, "id": sid, "lines": len(rows)})
            balance = closing
            if (a["key"], m) == LEFT_TO_REVIEW:
                continue
            store.validate(sid)
            store.integrate(sid)
            with unified_db.connect() as conn:
                for l in conn.execute("SELECT * FROM StatementLines WHERE BankStatementId = ?", (sid,)).fetchall():
                    op = conn.execute("SELECT * FROM Operations WHERE Reference = ?", (f"REL-{l['Id']}",)).fetchone()
                    unified_db.update(conn, "Operations", "Operation", op["Id"], {"Status": "Validated", "ValidatedAtUtc": unified_db.now_ef(), "ValidatedBy": "demonstration"})
                    unified_db.insert(conn, "ReconciliationMatches", "ReconciliationMatch", {
                        "StatementLineId": l["Id"], "OperationId": op["Id"], "Mode": "Auto", "Score": 1.0, "MatchedAtUtc": unified_db.now_ef(), "MatchedBy": "demonstration"})
                    if "FONDS VERT" in l["Label"]:
                        unified_db.update(conn, "FundingTranches", "FundingTranche", tranches[("FV", "Tranche 1 (50 %)")], {"ReceivedOperationId": op["Id"]})
                    if "FONDATION ATLAS" in l["Label"]:
                        unified_db.update(conn, "FundingTranches", "FundingTranche", tranches[("FA", "Tranche 1")], {"ReceivedOperationId": op["Id"]})

    # --- Activités, indicateurs, photos
    rnd = random.Random(2026)
    activities = [
        ("P-CEDRE", "Plantations", "2026-02-14", "Journée de plantation avec les écoles", "Azrou", 64, "2 400 jeunes cèdres plantés sur la parcelle 4.", "Sol gelé le matin.", "Prévoir les plantations après la mi-mars."),
        ("P-CEDRE", "Formation des coopératives", "2026-03-18", "Atelier pépinière avec la coopérative de Timahdite", "Timahdite", 22, "Formation de 22 pépiniéristes au semis du cèdre.", "", "Organiser une session de suivi en juin."),
        ("P-EAU", "Diagnostic des douars", "2026-03-05", "Diagnostic participatif de l'irrigation", "Tizguit", 41, "Cartographie des séguias et des besoins de 3 douars.", "Accès difficile après les pluies.", ""),
        ("P-EDU", "Ateliers scolaires", "2026-02-25", "Atelier « La forêt et l'eau »", "Ifrane", 58, "Deux classes de primaire sensibilisées au cycle de l'eau.", "", "Étendre aux collèges à la rentrée."),
        ("P-EDU", "Ateliers scolaires", "2026-04-22", "Sortie nature au parc national", "Ifrane", 47, "Observation de la faune et de la flore avec un écoguide.", "Transport à mutualiser.", ""),
    ]
    with unified_db.connect() as conn:
        task_ids = {}
        for code, task, *_ in activities:
            if (code, task) not in task_ids:
                task_ids[(code, task)] = unified_db.insert(conn, "Tasks", "ProjectTask", {
                    "Name": task, "Description": "", "Assignee": "", "Budget": 0, "Cost": 0, "Predecessors": "", "ProgressPercentage": rnd.choice([30, 50, 70]),
                    "ProjectId": ids["projects"][code], "Status": "En cours", "TargetStartDate": f"{YEAR}-01-15 00:00:00", "TargetEndDate": f"{YEAR}-11-30 00:00:00"})
        report_ids = []
        for code, task, day, title, place, n, narrative, diff, reco in activities:
            report_ids.append((code, day, unified_db.insert(conn, "ActivityReports", "ActivityReport", {
                "Title": title, "ActivityDate": f"{day} 09:00:00", "Location": place, "ParticipantsCount": n, "Narrative": narrative,
                "Difficulties": diff, "Recommendations": reco, "Status": "Validé", "ProjectTaskId": task_ids[(code, task)], "IndicatorId": None})))
        indicators = [("P-CEDRE", "Plants mis en terre", "plants", 0, 24_000, "Extrant", "Somme"), ("P-CEDRE", "Surface restaurée", "ha", 0, 60, "Effet", "Dernière valeur"),
                      ("P-EAU", "Ménages équipés en irrigation économe", "ménages", 0, 120, "Effet", "Somme"),
                      ("P-EDU", "Élèves sensibilisés", "élèves", 0, 400, "Extrant", "Somme")]
        ind_ids = {}
        for code, name, unit, base, target, level, agg in indicators:
            ind_ids[name] = unified_db.insert(conn, "Indicators", "Indicator", {
                "Name": name, "Description": "", "TargetValue": target, "CurrentValue": 0, "Unit": unit, "ProjectId": ids["projects"][code],
                "Aggregation": agg, "BaselineValue": base, "Level": level})
        measures = [("Plants mis en terre", "2026-02-28", 2400, "", "", "Azrou"), ("Plants mis en terre", "2026-03-31", 3100, "", "", "Azrou"),
                    ("Plants mis en terre", "2026-04-30", 2600, "", "", "Ain Leuh"), ("Surface restaurée", "2026-04-30", 14, "", "", ""),
                    ("Ménages équipés en irrigation économe", "2026-04-30", 18, "", "", "Tizguit"),
                    ("Élèves sensibilisés", "2026-02-28", 31, "F", "6-12 ans", "Ifrane"), ("Élèves sensibilisés", "2026-02-28", 27, "M", "6-12 ans", "Ifrane"),
                    ("Élèves sensibilisés", "2026-04-30", 25, "F", "6-12 ans", "Ifrane"), ("Élèves sensibilisés", "2026-04-30", 22, "M", "6-12 ans", "Ifrane")]
        for name, day, value, sex, age, zone in measures:
            unified_db.insert(conn, "IndicatorMeasurements", "IndicatorMeasurement", {
                "IndicatorId": ind_ids[name], "PeriodEnd": day, "Value": value, "Sex": sex, "AgeGroup": age, "Zone": zone,
                "Source": "Fiches de suivi (démonstration)", "Notes": "", "CreatedAtUtc": unified_db.now_ef()})
        for name, total in (("Plants mis en terre", 8100), ("Surface restaurée", 14), ("Ménages équipés en irrigation économe", 18), ("Élèves sensibilisés", 105)):
            unified_db.update(conn, "Indicators", "Indicator", ind_ids[name], {"CurrentValue": total})
    for k, (code, day, rid) in enumerate(report_ids):
        imgs = [(_photo(rnd, k * 2 + j), f"photo_{code}_{day}_{j}.jpg") for j in range(2)]
        for j, res in enumerate(photos.upload(imgs, ids["projects"][code], activity_report_id=rid, credit="ACA (démonstration)", consent=True)):
            if "error" in res:
                raise RuntimeError(f"Photo {res['file']} : {res['error']}")
            photos.update(res["photo"]["id"], {"caption": f"{activities[k][3]} — {activities[k][4]}, {day[8:]}/{day[5:7]}/{day[:4]}",
                                     "caption_validated": True, "taken_at": f"{day} 10:{15 * j:02d}:00", "location": activities[k][4]})

    # --- GED : convention, rapport narratif, procès-verbal
    docs = [("P-CEDRE", "Convention_FV-2026-07.pdf", _convention_pdf()), ("P-CEDRE", "Rapport_narratif_T1_2026.docx", _report_docx()),
            ("P-EAU", "PV_comite_pilotage_mars_2026.pdf", _pv_pdf())]
    for code, name, data in docs:
        asyncio.run(ged.import_document(ids["projects"][code], data, name))

    # --- Comptes rendus et PV (Lot 9) : COPIL avec décisions et actions, atelier (compte rendu d'activité), AG
    from backend.tools.meetings import service as meetings
    with unified_db.connect() as conn:
        atelier_task = conn.execute("SELECT Id FROM Tasks WHERE ProjectId = ? AND Name = 'Formation des coopératives'", (ids["projects"]["P-CEDRE"],)).fetchone()[0]
    copil = meetings.save({
        "kind": "COPIL", "title": "Comité de pilotage n° 1 — P-CEDRE", "date": "2026-03-10", "start_time": "10:00", "location": "Azrou",
        "project_id": ids["projects"]["P-CEDRE"], "organizer": "Salma Idrissi (fictive)", "secretary": "Youssef Alaoui (fictif)",
        "agenda": "Bilan des plantations du trimestre\nAvancement financier\nProgramme du printemps",
        "summary": "Le comité constate l'avancement des plantations (5 500 plants) et le retard de livraison de la pépinière.",
        "participants": [{"name": "Salma Idrissi", "organization": "ACA", "role": "Cheffe de projet", "sex": "F"},
                         {"name": "Représentant du Fonds Vert", "organization": "Fonds Vert (fictif)", "role": "Chargé de portefeuille", "sex": "M"},
                         {"name": "Présidente de la coopérative", "organization": "Coopérative de Timahdite", "sex": "F"},
                         {"name": "Agent des Eaux et Forêts", "organization": "DREF", "sex": "M", "present": False}],
        "decisions": [{"text": "Valider le programme de plantation du printemps (6 000 plants)."},
                      {"text": "Commander les plants trois mois à l'avance auprès de la pépinière."}],
        "actions": [{"text": "Passer la commande de plants du printemps", "responsible": "Salma Idrissi", "due_date": "2026-04-15", "status": "Fait"},
                    {"text": "Transmettre le rapport semestriel au Fonds Vert", "responsible": "Youssef Alaoui", "due_date": "2026-07-30"},
                    {"text": "Organiser une visite de terrain avec la DREF", "responsible": "Salma Idrissi", "due_date": "2026-05-31"}]})
    meetings.write_document(copil["id"])
    asyncio.run(meetings.validate(copil["id"]))
    meetings.create_task(copil["actions"][1]["id"])
    atelier = meetings.save({
        "kind": "Activité", "title": "Atelier pépinière avec la coopérative", "date": "2026-03-18", "location": "Timahdite",
        "project_id": ids["projects"]["P-CEDRE"], "task_id": atelier_task, "organizer": "Salma Idrissi (fictive)",
        "agenda": "Former les pépiniéristes au semis du cèdre\nPréparer la production de 6 000 plants",
        "summary": "22 pépiniéristes formés au semis du cèdre ; un calendrier de production a été établi.",
        "participants": [{"name": f"Pépiniériste {i + 1}", "organization": "Coopérative de Timahdite", "sex": "F" if i % 3 else "M"} for i in range(22)]})
    meetings.write_document(atelier["id"])
    asyncio.run(meetings.validate(atelier["id"]))
    ag = meetings.save({
        "kind": "AG", "title": "Assemblée générale ordinaire 2026", "date": "2026-04-25", "start_time": "15:00", "location": "Siège, Azrou",
        "organizer": "Présidente de l'association (fictive)", "secretary": "Secrétaire général (fictif)",
        "agenda": "Rapport moral 2025\nRapport financier 2025\nQuitus au bureau\nProgramme 2026",
        "summary": "L'assemblée a approuvé les rapports de l'exercice 2025 et le programme 2026.",
        "participants": [{"name": f"Membre {i + 1}", "sex": "F" if i % 2 else "M"} for i in range(31)],
        "decisions": [{"text": "Approuver le rapport moral 2025."}, {"text": "Approuver les comptes 2025 et donner quitus au bureau."},
                      {"text": "Fixer la cotisation annuelle à 200 MAD (valeur de démonstration)."}],
        "actions": [{"text": "Déposer le PV de l'AG auprès des autorités", "responsible": "Secrétaire général", "due_date": "2026-05-25"}]})
    meetings.write_document(ag["id"])
    asyncio.run(meetings.validate(ag["id"]))

    # --- Rapport annuel (moral + financier) généré par l'assistant, ouvert dans l'éditeur
    report = asyncio.run(generator.generate(YEAR, "association", None, "fr", "both"))

    # Deux opérations saisies et non encore validées : les contrôles des rapports les signalent (démonstration)
    with unified_db.connect() as conn:
        for label, amount, line in (("Achat de petits outils (à justifier)", 1_850_00, "C-PLANTS"), ("Remboursement de frais de mission", 620_00, "C-TRANS")):
            op = unified_db.insert(conn, "Operations", "Operation", {
                "BankAccountId": ids["accounts"]["CED"], "OperationDate": "2026-04-28", "ValueDate": None, "Label": label, "Reference": "", "ThirdParty": "",
                "Direction": "Debit", "Nature": "Expense", "AmountMinor": amount, "Currency": "MAD", "RateToMad": None, "AmountMadMinor": amount,
                "TransferGroupId": None, "Status": "Draft", "ValidatedAtUtc": None, "ValidatedBy": "", "Notes": "Saisie de démonstration : à valider.", "IsDeleted": 0})
            unified_db.insert(conn, "OperationAllocations", "OperationAllocation", {
                "OperationId": op, "ProjectId": ids["projects"]["P-CEDRE"], "BudgetLineId": ids["lines"][line],
                "CategoryId": ids["categories"]["ACH" if line == "C-PLANTS" else "DEPL"], "AmountMinor": amount})

    manifest = {"association": ASSOCIATION, "year": YEAR, "build_data_dir": str((out / "data").resolve()), "projects": len(PROJECTS),
                "accounts": len(ACCOUNTS), "statements": statements, "annual_report_document": (report.get("document") or {}).get("id"),
                "warning": "Données entièrement fictives. Ne pas saisir de données réelles dans la base de démonstration."}
    (out / "demo.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


# --- Fichiers fictifs -----------------------------------------------------------------------------------------

def _logo(text: str, color: str):
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (480, 120), "white")
    d = ImageDraw.Draw(img)
    d.ellipse((10, 10, 110, 110), fill=color)
    d.text((130, 45), text, fill=color, font=_font(26))
    return img


def _font(size: int):
    from PIL import ImageFont
    for name in ("DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def _photo(rnd: random.Random, seed: int) -> bytes:
    """Paysage stylisé (ciel, montagnes, cèdres) : aucune photo réelle de personne."""
    from PIL import Image, ImageDraw
    w, h = 1600, 1066
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)], fill=(int(140 + 80 * t), int(190 + 30 * t), int(235 - 60 * t)))
    for k in range(3):
        base = int(h * (0.45 + 0.1 * k))
        pts = [(0, h)] + [(x, base - rnd.randint(0, 160 - 40 * k)) for x in range(0, w + 200, 200)] + [(w, h)]
        d.polygon(pts, fill=(60 + 30 * k, 90 + 25 * k, 70 + 10 * k))
    for _ in range(18):
        x, y = rnd.randint(0, w), rnd.randint(int(h * 0.6), h)
        s = rnd.randint(40, 110)
        d.polygon([(x, y - s * 2), (x - s, y), (x + s, y)], fill=(20, 70 + seed % 30, 40))
        d.rectangle([x - 6, y, x + 6, y + s // 2], fill=(90, 60, 30))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=82)
    return buf.getvalue()


def _text_pdf(title: str, paragraphs: list) -> bytes:
    import pymupdf
    doc = pymupdf.open()
    page = doc.new_page()
    y = 60
    page.insert_text((60, y), title, fontsize=15, fontname="hebo")
    y += 30
    for para in paragraphs:
        rect = pymupdf.Rect(60, y, 535, y + 200)
        page.insert_textbox(rect, para, fontsize=10.5)
        y += 14 * (1 + len(para) // 85) + 10
        if y > 760:
            page = doc.new_page()
            y = 60
    data = doc.tobytes()
    doc.close()
    return data


def _convention_pdf() -> bytes:
    return _text_pdf("CONVENTION DE FINANCEMENT N° FV-2026-07 (DOCUMENT FICTIF)", [
        "Entre le Fonds Vert pour les Forêts, ci-après dénommé « le Bailleur », et l'Association des Cèdres de l'Atlas, "
        "ci-après dénommée « l'Association », les parties conviennent de ce qui suit.",
        "Article 1 — Objet. La présente convention de financement a pour objet le projet « Restauration de la cédraie d'Azrou ».",
        "Article 2 — Montant. Le Bailleur accorde une subvention de 600 000 MAD, versée en deux tranches de 300 000 MAD.",
        "Article 3 — Durée. La convention prend effet le 1er janvier 2026 et se termine le 31 décembre 2027.",
        "Article 4 — Rapports. L'Association remet un rapport narratif et financier semestriel dans les 30 jours suivant "
        "la fin de chaque semestre, ainsi qu'un rapport final au plus tard le 31 mars 2028.",
        "Fait à Ifrane, le 15 décembre 2025, en deux exemplaires originaux.",
    ])


def _pv_pdf() -> bytes:
    return _text_pdf("PROCÈS-VERBAL DU COMITÉ DE PILOTAGE — 12 MARS 2026 (FICTIF)", [
        "Le comité de pilotage du projet « Gestion durable de l'eau à Tizguit » s'est réuni le 12 mars 2026 à Tizguit.",
        "Présents : représentants des trois douars, de l'Association et de la Fondation Atlas pour l'Eau.",
        "Décisions : validation du diagnostic participatif ; lancement de l'achat du matériel d'irrigation ; "
        "prochaine réunion en septembre 2026.",
    ])


def _report_docx() -> bytes:
    from docx import Document
    doc = Document()
    doc.add_heading("Rapport narratif du premier trimestre 2026 — Restauration de la cédraie (fictif)", 1)
    doc.add_paragraph("Au cours du premier trimestre 2026, l'association a planté 5 500 jeunes cèdres sur les parcelles 3 et 4, "
                      "avec la participation de 64 élèves et de la coopérative de Timahdite.")
    doc.add_paragraph("Difficultés : le gel tardif a retardé deux journées de plantation. Perspectives : plantation de 6 000 plants au printemps.")
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    result = build(Path(sys.argv[1]).resolve())
    print(json.dumps({k: v for k, v in result.items() if k != "statements"}, ensure_ascii=False, indent=2))
    print(f"{len(result['statements'])} relevés importés.")
