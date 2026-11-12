import json
from pathlib import Path

import pytest

from backend.tools.statements import ocr
from backend.tools.statements.extract import clean_numeric, parse_amount, parse_date
from backend.tools.statements.model import ExtractedLine, ExtractedStatement
from backend.tools.statements.pipeline import process, second_pass_fix
from backend.tools.statements.tabular import read as read_tabular
from tests.tools import statement_accuracy, statement_fixtures

REAL_DIR = Path(__file__).resolve().parents[1] / "backend" / "tests" / "fixtures" / "releves"
needs_tesseract = pytest.mark.skipif(ocr.find_tesseract() is None, reason="Tesseract non installé sur ce poste")


@pytest.fixture(scope="session")
def synthetic_dir(tmp_path_factory):
    folder = tmp_path_factory.mktemp("releves_synthetiques")
    statement_fixtures.generate(folder)
    return folder


@pytest.mark.parametrize("text, expected", [
    ("1 234,56", 123456), ("14 185,73", 1418573), ("79,21", 7921), ("1.234,56", 123456),
    ("12O,5O", 12050), ("1 234,56-", -123456), ("12,5", None), ("9864766", None), ("03/2026", None),
])
def test_parse_amount(text, expected):
    assert parse_amount(text) == expected


@pytest.mark.parametrize("text, expected", [
    ("04/03/2026", "2026-03-04"), ("4.3.26", "2026-03-04"), ("O4/O3/2O26", "2026-03-04"),
    ("31/02/2026", None), ("FRAIS", None),
])
def test_parse_date(text, expected):
    assert parse_date(text) == expected


def test_clean_numeric_leaves_words_alone():
    assert clean_numeric("SOLDE") == "SOLDE"
    assert clean_numeric("l2,5O") == "12,50"


def test_native_pdf_is_read_exactly_without_ocr(synthetic_dir):
    truth = json.loads((synthetic_dir / "synth_cih_66.truth.json").read_text(encoding="utf-8"))
    result = process((synthetic_dir / truth["files"]["native_pdf"]).read_bytes(), "releve.pdf")
    st = result.statement
    assert st.engine == "pdf-natif"
    assert st.bank_id == "cih" and st.rib == truth["rib"]
    assert (st.period_start, st.period_end) == (truth["period_start"], truth["period_end"])
    assert (st.opening, st.closing) == (truth["opening"], truth["closing"])
    assert st.balance_ok() is True
    assert len(st.lines) == len(truth["lines"]) == 40        # deux pages, en-tête répété ignoré
    assert all(l.confidence["date"] == 100 for l in st.lines)
    assert len(result.page_images) == 2


@needs_tesseract
def test_extraction_accuracy_on_synthetic_statements_is_at_least_95_percent(synthetic_dir):
    totals = statement_accuracy.evaluate(synthetic_dir)
    assert totals["documents"] == 15                         # 6 PDF natifs, 6 scans, 3 photos difficiles
    assert totals["accuracy"] >= 0.95, totals
    assert totals["headers_ok"] == totals["documents"]


@needs_tesseract
def test_real_anonymised_statements_when_provided():
    if not list(REAL_DIR.glob("*.truth.json")):
        pytest.skip("Aucun relevé réel anonymisé déposé dans backend/tests/fixtures/releves/")
    totals = statement_accuracy.evaluate(REAL_DIR)
    assert totals["accuracy"] >= 0.95, f"{totals['correct']}/{totals['expected']} lignes correctes"


@needs_tesseract
def test_scan_gives_page_images_and_positions(synthetic_dir):
    result = process((synthetic_dir / "synth_bp_11_scan_p1.jpg").read_bytes(), "scan.jpg")
    st = result.statement
    assert st.engine == "tesseract" and st.bank_id == "bp"
    assert result.page_images and result.page_images[0][:4] == b"\x89PNG"
    assert all(0 < l.y < 1 for l in st.lines)
    assert all(set(l.confidence) >= {"date", "label", "debit", "credit"} for l in st.lines)


def _statement(amounts):
    st = ExtractedStatement(opening=10_000, closing=10_000 - sum(amounts))
    st.lines = [ExtractedLine(f"2026-03-0{i + 1}", None, "x", "", a, 0, {"debit": 95}) for i, a in enumerate(amounts)]
    return st


def test_second_pass_fixes_only_a_single_unambiguous_misread():
    primary = _statement([3_952, 1_000])
    primary.lines[0].debit = 8_952                 # « 3 » lu « 8 »
    secondary = _statement([3_952, 1_000])
    fixed = second_pass_fix(primary, secondary)
    assert fixed.balance_ok() is True
    assert fixed.lines[0].debit == 3_952 and fixed.lines[0].confidence["debit"] == 50.0
    assert any("seconde lecture" in w for w in fixed.warnings)

    # Deux corrections possibles : rien n'est changé.
    p2 = _statement([1_000, 1_000]); p2.lines[0].debit = p2.lines[1].debit = 1_500; p2.closing = 10_000 - 2_500
    s2 = _statement([1_000, 1_000])
    assert second_pass_fix(p2, s2).lines[0].debit == 1_500


def test_csv_and_excel_exports_are_read():
    csv_data = "Date opération;Libellé;Débit;Crédit\n05/03/2026;PRLV LOYER;2 000,00;\n10/03/2026;VIR RECU;;15 250,50\n".encode("cp1252")
    st = read_tabular(csv_data, ".csv")
    assert [(l.date, l.debit, l.credit) for l in st.lines] == [("2026-03-05", 200_000, 0), ("2026-03-10", 0, 1_525_050)]

    from io import BytesIO
    from openpyxl import Workbook
    from datetime import datetime
    wb = Workbook()
    ws = wb.active
    ws.append(["Relevé AFMI"])
    ws.append(["Date", "Libellé", "Montant"])
    ws.append([datetime(2026, 3, 5), "Loyer", -2000.0])
    ws.append([datetime(2026, 3, 6), "Don", 125.5])
    buf = BytesIO()
    wb.save(buf)
    st = read_tabular(buf.getvalue(), ".xlsx")
    assert [(l.debit, l.credit) for l in st.lines] == [(200_000, 0), (0, 12_550)]


def test_unsupported_format_is_refused():
    with pytest.raises(ValueError):
        process(b"x", "releve.docx")
