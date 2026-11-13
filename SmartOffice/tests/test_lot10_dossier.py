"""Lot 10 — import intelligent d'un dossier de projet : lecture (PDF mis en page, Excel), contrôles, IA vérifiée, application.

Les pièces sont fictives et générées ici (aucun document réel ni coordonnée bancaire dans le dépôt). Elles reprennent les
formes rencontrées : convention PNUD/PMF (tranches conditionnées), formulaire avec cadre logique et calendrier T1…T8,
budget à colonnes de cofinancement, avenant CEPF (Total New Budget), budget par activité (SCAC), budget IKI (colonne « Taux »).
"""
import asyncio
import io
from datetime import date

import pytest

from backend.tools.dossier import ai, checks, normalize as N, rules, service, sources as S
from tests.test_lot5_reports import unified  # noqa: F401

try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover
    import fitz


def _row(*cells):
    """Ligne mise en page : [(colonne, texte), …]."""
    s = ""
    for col, txt in cells:
        s = s.ljust(col) + txt
    return s


T = [64 + 5 * i for i in range(8)]
PAGES = [
    [
        "                ACCORD DE SUBVENTION DE FAIBLE VALEUR",
        "   Conclu entre le Programme des Nations Unies pour le Développement et Association Test",
        "                       No de référence : MOR/TEST/2026/01",
        "1.    Pays : Maroc",
        "3.    Numéro et intitulé du projet : MOR/TEST/2026/01 - Restauration des parcours :",
        "      gestion communautaire durable à Tizguit",
        "4.    Période de mise en œuvre : Du 1er octobre 2026 au 30 septembre 2028",
        "5.    Budget : 20.000 USD - vingt mille dollars américains",
        "6.    Calendrier de versement des fonds :",
        "Tranche 1 (50%) – À la signature de l'accord                                  10 000",
        "Tranche 2 (40%) – 30 juin 2027 - À l'approbation du rapport narratif et financier n° 2      8 000",
        "Tranche 3 (10%) – 30 juin 2028 - À l'approbation du rapport narratif et financier n° 4      2 000",
        "7.    Informations bancaires : voir annexe",
    ],
    [
        _row((1, "Contacts du responsable du projet"), (45, "Amina Test ; Coordinatrice ;")),
        _row((1, "Total du fonds sollicité auprès du PMF du FEM"), (52, "186 000,00"), (70, "20 000,00")),
        _row((1, "Total du fonds du cofinancement (en espèces"), (52, "200 000,00"), (70, "21 505,38")),
        _row((1, "Coût total du projet"), (52, "386 000,00"), (70, "41 505,38")),
        _row((1, "Taux de change UN (réservé au PMF)"), (60, "9,30")),
        "Un cofinancement d'un montant égal ou supérieur à celui de la subvention du PMF est requis.",
        "Objectif du projet : Restaurer les parcours de Tizguit avec la communauté.",
        "Résultats du projet :",
        "   1.  Les parcours sont restaurés sur 500 ha.",
        "   2.  Une coopérative est équipée.",
        _row((28, "Responsable"), (37, "Indicateur"), *[(T[i], f"T{i + 1}") for i in range(8)]),
        _row((37, "Indicateurs :")),
        _row((0, "Composante 1/Produit 1"), (37, "- 500 ha restaurés")),
        _row((0, "Activité 1.1 : Diagnostic"), (28, "AFMI"), (37, "- 1 carte validée"), (T[0], "X"), (T[1], "X")),
        _row((0, "participatif")),
        _row((0, "Activité 1.2 : Mise en"), (28, "AFMI"), (T[2], "X"), (T[3], "X"), (T[4], "X")),
        _row((0, "défens des parcours")),
        _row((37, "Indicateurs :")),
        _row((0, "Composante 2/Produit 2"), (37, "- 1 coopérative équipée")),
        _row((0, "Activité 2.1 : Achat de"), (28, "AFMI"), (T[4], "X"), (T[5], "X")),
        _row((0, "matériel")),
    ],
    [
        "Tableau 3 : Budget du projet",
        _row((25, "Coût total du"), (44, "Subvention"), (62, "Cofinancement")),
        _row((1, "Catégorie de dépenses"), (25, "projet en MAD"), (44, "PMF en MAD"), (62, "communauté en MAD")),
        _row((1, "1. Personnel")),
        _row((1, "1.1 Coordination"), (25, "150 000,00"), (44, "100 000,00"), (62, "50 000,00")),
        _row((1, "1.2 Main-d'œuvre locale"), (25, "236 000,00"), (44, "86 000,00"), (62, "150 000,00")),
        _row((1, "2. Équipement")),
        _row((1, "2.1 Matériel de clôture"), (25, "0,00"), (44, "0,00"), (62, "0,00")),
        _row((1, "Coût total du projet en")),
        _row((25, "386 000,00"), (44, "186 000,00"), (62, "200 000,00")),
    ],
]


def _pdf(pages=PAGES) -> bytes:
    doc = fitz.open()
    for lines in pages:
        page = doc.new_page(width=842, height=595)
        for i, line in enumerate(lines):
            page.insert_text((20, 30 + 14 * i), line, fontname="cour", fontsize=8.5)
    return doc.tobytes()


def _xlsx(rows, title="Budget") -> bytes:
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = title
    for r in rows:
        ws.append(list(r))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_amounts_dates_and_periods_as_written_by_donors():
    assert [N.parse_amount(x) for x in ("465 000,00", "50.000", "$117,930.00", "50. 000,00", "9,30", "1.234.567")] == \
        [465000, 50000, 117930, 50000, 9.3, 1234567]
    assert N.parse_date("1er octobre 2026") == date(2026, 10, 1)
    assert N.parse_date("5/31/2020") == date(2020, 5, 31) and N.parse_date("12/09/2026") == date(2026, 9, 12)
    assert N.parse_date("June 1, 2020") == date(2020, 6, 1) and N.parse_date("Juillet 2020") == date(2020, 7, 1)
    assert N.quarter_span(date(2026, 10, 1), 2, 3) == (date(2027, 1, 1), date(2027, 6, 30))
    assert N.relative_period("Mois 1 à 3") == ("mois", 1, 3) and N.months_between(date(2026, 10, 1), date(2028, 9, 30)) == 24


def test_agreement_and_project_form_are_read_with_sources():
    r = rules.extract([S.read(_pdf(), "Formulaire_test.pdf")])
    p, f = r["project"], r["funding"]
    assert p["code"]["value"] == "MOR/TEST/2026/01"
    assert p["title"]["value"].startswith("Restauration des parcours") and "Tizguit" in p["title"]["value"]
    assert p["donor"]["value"].startswith("PNUD")
    assert (p["start"]["value"], p["end"]["value"]) == ("2026-10-01", "2028-09-30")
    assert p["manager"]["value"] == "Amina Test" and p["code"]["source"]["page"] == 1
    assert f["grant"]["value"] == {"amount": 20000, "currency": "USD"} and f["grant_mad"]["value"]["amount"] == 186000
    assert f["exchange_rate"]["value"] == 9.3 and f["cofinancing"]["value"]["amount"] == 200000
    tr = r["tranches"]
    assert [(t["percent"], t["amount"], t["date"]) for t in tr] == [(50, 10000, None), (40, 8000, "2027-06-30"), (10, 2000, "2028-06-30")]
    assert tr[1]["condition"].endswith("n° 2") and "8 000" not in tr[1]["condition"]
    assert [x["title"] for x in r["reports"]][:2] == ["Rapport narratif et financier n° 2", "Rapport narratif et financier n° 4"]
    # calendrier T1…T8 → dates réelles, titres sans la colonne « Responsable »
    acts = {a["code"]: a for a in r["activities"]}
    assert acts["1.1"]["title"] == "Diagnostic participatif" and acts["1.1"]["responsible"] == "AFMI"
    assert (acts["1.1"]["start"], acts["1.1"]["end"]) == ("2026-10-01", "2027-03-31")
    assert (acts["1.2"]["start"], acts["1.2"]["end"]) == ("2027-04-01", "2027-12-31")
    assert [n["code"] for n in r["logframe"]] == ["R1", "R2"]
    inds = {i["code"]: i for i in r["indicators"]}
    assert inds["I1.1"]["target"] == 500 and inds["I1.1"]["unit"] == "ha" and inds["I2.1"]["result_code"] == "R2"
    b = r["budget"]
    assert b["currency"] == "MAD" and b["declared_total"] == 386000 and len(b["lines"]) == 3
    assert b["lines"][1]["category"] == "Personnel" and b["lines"][1]["by_source"]["Cofinancement communauté en MAD"] == 150000
    assert r["cofinancing"][0]["source_type"] == "Communauté" and r["cofinancing"][0]["amount"] == 200000
    assert r["rules"][0]["kind"] == "CofinancingMinPercent"


def test_checks_find_inconsistencies_but_accept_a_coherent_file():
    src = S.read(_pdf(), "f.pdf")
    r = rules.extract([src])
    levels = [i["level"] for i in checks.run(r, [src])]
    assert "erreur" not in levels
    bad = [list(p) for p in PAGES]
    bad[2][5] = _row((1, "1.2 Main-d'œuvre locale"), (25, "236 000,00"), (44, "96 000,00"), (62, "150 000,00"))    # 96 000 au lieu de 86 000
    bad[0][11] = "Tranche 3 (15%) – 30 juin 2028 - À l'approbation du rapport narratif et financier n° 4      2 000"
    src2 = S.read(_pdf(bad), "f.pdf")
    msgs = " | ".join(i["message"] for i in checks.run(rules.extract([src2]), [src2]) if i["level"] == "erreur")
    assert "1.2" in msgs and "ne fait pas le total" in msgs
    assert "105 %" in msgs
    assert "PMF en MAD" in msgs                                   # colonne subvention ≠ subvention demandée


def test_amendment_workbook_uses_total_new_budget_and_flags_rounding():
    wb = _xlsx([
        ("Grantee Name", "Association Test"), ("Current Budget Amount", 100000), ("Total New Budget", 104000.0049),
        ("Additional Amount for this amendment", 4000), (),
        ("Grantee Budget Category", "Total Approved Budget", "Expenditures", "Amended Budget", "Total New Budget"),
        ("Salaries and Benefits", 60000, 20000, 42000, 62000), ("Furniture and Equipment", 40000, 5000, 37000.0049, 42000.0049),
        ("Grand Total", 100000, 25000, 79000.0049, 104000.0049),
    ], "Summary Budget")
    src = S.read(wb, "Budget_Amendment.xlsx")
    r = rules.extract([src])
    assert r["budget"]["total_column"] == "Total New Budget" and [l["total"] for l in r["budget"]["lines"]] == [62000, 42000]
    assert r["amendments"][0]["old_amount"] == 100000 and r["amendments"][0]["new_amount"] == 104000
    assert r["funding"]["grant"]["value"]["amount"] == 104000
    assert any(i["code"] == "rounding" for i in checks.run(r, [src]))


def test_budget_by_activity_and_donor_rule_on_indirect_costs():
    wb = _xlsx([
        ("Rapport financier",), ("Budget prévu (MAD)", 41000), (),
        ("Dépenses", "Dates", "Nature de la dépense", "Budget prévisionnel", "Dépenses effectives", "Balance"),
        ("Activité 1: Rencontre de lancement",), ("Restauration", None, None, 6000, 0, 6000), ("Outils de communication", None, None, 2000, 0, 2000),
        ("Activité 2: Analyses au laboratoire",), ("Consommables", None, None, 30000, 0, 30000),
        ("Frais indirects (7%)",), ("Frais administratifs et de coordination", None, None, 3000, 0, 3000),
    ])
    rule = "Frais indirects : les frais indirects ne devront pas dépasser 7% des frais directs du budget global demandé.".encode()
    srcs = [S.read(wb, "Budget.xlsx"), S.read(rule, "Formulaire.txt")]
    r = rules.extract(srcs)
    assert [(a["code"], a["title"]) for a in r["activities"]] == [("1", "Rencontre de lancement"), ("2", "Analyses au laboratoire")]
    assert r["budget"]["lines"][0]["activity_code"] == "1" and r["budget"]["lines"][0]["category"].startswith("Activité 1")
    issue = next(i for i in checks.run(r, srcs) if i["code"] == "rule_indirect")
    assert "7.89 %" in issue["message"] and issue["level"] == "erreur"   # 3 000 / 38 000


def test_share_column_is_recognised_and_not_used_as_a_rate():
    wb = _xlsx([
        ("Site", "Activité", "Détail", "Jours", "Taux", "Sous-total ($)", "TOTAL USD"),
        ("Ifrane", "Reboisement", "Préparation du sol", 500, 0.6, 6000, 6000), (None, None, "Plantation", 250, 0.4, 4000, 4000),
        (None, None, None, None, 1.0, None, None), (None, None, None, None, "Total USD", None, 10000),
    ])
    src = S.read(wb, "Budget_LoA.xlsx")
    r = rules.extract([src])
    b = r["budget"]
    assert b["total_column"] == "TOTAL USD" and b["declared_total"] == 10000 and b["share_column"] == "Taux"
    assert [(l["category"], l["label"]) for l in b["lines"]] == [("Reboisement", "Préparation du sol"), ("Reboisement", "Plantation")]


def test_ai_numbers_must_exist_in_the_documents():
    src = S.read(_pdf(), "f.pdf")
    r = rules.extract([src])
    proposal = {"project": {"partners": ["Commune de Tizguit"]}, "funding": {"total_cost": {"amount": 999999, "currency": "MAD"}},
                "risks": [{"description": "Sécheresse prolongée", "mitigation": "Semences locales", "src": {"file": "f.pdf", "page": 2}}],
                "indicators": [{"name": "Hectares", "target": 123456}]}
    issues = ai.merge(r, proposal, "test:modele", [src])
    assert r["risks"][0]["description"] == "Sécheresse prolongée" and r["risks"][0]["engine"] == "IA (test:modele)"
    assert r["funding"]["total_cost"]["value"]["amount"] == 386000           # chiffre inventé ignoré, valeur lue conservée
    assert any("999999" in i["message"] for i in issues)
    assert r["indicators"][0]["code"] == "I1.1"                             # les règles ont déjà des indicateurs : pas de remplacement
    assert r["project"]["partners"]["value"] == ["Commune de Tizguit"]


def test_analyze_and_apply_create_a_complete_project_without_duplicates(unified):
    files = [("Formulaire_test.pdf", _pdf())]
    imp = asyncio.run(service.analyze(files, None, use_ai=False))
    assert imp["status"] == "Brouillon" and imp["result"]["defaults"]["code"] == "MOR/TEST/2026/01"
    out = asyncio.run(service.apply(imp["id"], {"create": {"code": "MOR/TEST/2026/01", "name": "Parcours de Tizguit"}, "in_kind": "Comptabilité"}))
    pid = out["project_id"]
    from backend.core import unified_db
    with unified_db.connect() as c:
        p = c.execute("SELECT * FROM Projects WHERE Id = ?", (pid,)).fetchone()
        assert (p["Manager"], p["TargetStartDate"][:10], float(p["BudgetGlobal"]), p["Currency"]) == ("Amina Test", "2026-10-01", 386000.0, "MAD")
        assert c.execute("SELECT InKindTreatment FROM Funders WHERE Id = ?", (p["FunderId"],)).fetchone()[0] == "Comptabilité"
        ag = c.execute("SELECT * FROM FundingAgreements WHERE ProjectId = ?", (pid,)).fetchone()
        assert (ag["AmountMinor"], ag["Currency"], ag["ContractualRateToMad"]) == (2_000_000, "USD", "9.3")
        assert c.execute("SELECT COUNT(*), SUM(AmountMinor) FROM FundingTranches WHERE FundingAgreementId = ?", (ag["Id"],)).fetchone()[:] == (3, 2_000_000)
        assert c.execute("SELECT ExpectedDate FROM FundingTranches WHERE Label = 'Tranche 1'").fetchone()[0] == "2026-10-01"
        assert c.execute("SELECT COUNT(*), SUM(PlannedMinor) FROM BudgetLines WHERE ProjectId = ? AND Code <> 'REC'", (pid,)).fetchone()[:] == (3, 38_600_000)
        assert c.execute("SELECT PlannedMinor FROM BudgetLines WHERE ProjectId = ? AND Code = 'REC'", (pid,)).fetchone()[0] == 0
        assert c.execute("SELECT COUNT(*) FROM Tasks WHERE ProjectId = ? AND Code IN ('1.1', '1.2', '2.1')", (pid,)).fetchone()[0] == 3
        assert c.execute("SELECT COUNT(*) FROM Indicators WHERE ProjectId = ? AND LogframeNodeId IS NOT NULL", (pid,)).fetchone()[0] == 2
        assert c.execute("SELECT COUNT(*) FROM ReportingObligations WHERE ProjectId = ? AND Status = 'À venir' AND IsDeleted = 0", (pid,)).fetchone()[0] == 2
        assert c.execute("SELECT SUM(PlannedMinor) FROM CofinancingContributions WHERE ProjectId = ?", (pid,)).fetchone()[0] == 20_000_000
        assert c.execute("SELECT COUNT(*) FROM Documents WHERE ProjectId = ? AND IsDeleted = 0", (pid,)).fetchone()[0] == 1
        assert c.execute("SELECT COUNT(*) FROM AuditEntries WHERE EntityType = 'BudgetLine'").fetchone()[0] >= 3
    with pytest.raises(service.DossierError, match="déjà été appliqué"):
        asyncio.run(service.apply(imp["id"], {}))
    # le budget et le cadre logique contenus dans le document de projet ne sont plus signalés comme pièces manquantes
    from backend.tools.ged import lifecycle
    msgs = " ".join(a["message"] for a in lifecycle.alerts(pid) if a["code"] == "MISSING_DOCUMENT")
    assert "absent : Budget" not in msgs and "absent : Cadre logique" not in msgs
    # second import du même dossier sur le même projet : mises à jour, aucun doublon
    imp2 = asyncio.run(service.analyze(files, pid, use_ai=False))
    asyncio.run(service.apply(imp2["id"], {"project_id": pid, "sections": [s for s in service.SECTIONS if s != "documents"]}))
    with unified_db.connect() as c:
        assert c.execute("SELECT COUNT(*) FROM BudgetLines WHERE ProjectId = ?", (pid,)).fetchone()[0] == 4
        assert c.execute("SELECT COUNT(*) FROM Tasks WHERE ProjectId = ?", (pid,)).fetchone()[0] == 3
        assert c.execute("SELECT COUNT(*) FROM FundingTranches").fetchone()[0] >= 3
        assert c.execute("SELECT COUNT(*) FROM FundingAgreements WHERE ProjectId = ?", (pid,)).fetchone()[0] == 1
    # cofinancement en nature, bailleur en mode « Comptabilité » : justificatif obligatoire, écriture équilibrée
    contrib = service.cofinancing(pid)["items"][0]["id"]
    with unified_db.connect() as c:
        c.execute("UPDATE CofinancingContributions SET Nature = 'Nature' WHERE Id = ?", (contrib,))
    with pytest.raises(service.DossierError, match="justificatif"):
        service.add_cofinancing_entry(contrib, {"date": "2026-11-30", "amount": 4500})
    service.add_cofinancing_entry(contrib, {"date": "2026-11-30", "amount": 4500, "evidence": "Feuille de présence novembre"})
    j = service.in_kind_journal(pid)
    assert len(j) == 2 and sum(x["debit"] for x in j) == sum(x["credit"] for x in j) == 4500
    assert service.cofinancing(pid)["by_source"][0]["realized"] == 4500
