"""Relevé Attijariwafa scanné (forme réelle, données fictives) : lecture locale sans IA.

Particularités reproduites d'un vrai relevé AWB numérisé (copieur) : solde « SOLDE DEPART AU jj mm aaaa … CREDITEUR »,
code d'opération collé au jour (« 0016PV|13 07| »), date d'opération sans année, date de valeur en trois groupes
(« 11 07 2026 »), en-tête sur deux lignes (« VALEUR » au-dessus), montants à milliers séparés par une espace.
"""
import fitz
import pytest

from backend.tools.statements import pipeline
from backend.tools.statements import ocr
from tests.tools.statement_fixtures import degrade_to_scan

ROWS = [("0016PV", "13 07", "PRELEVEMENT EN FAV. CNSS", "11 07 2026", "1 502,97"),
        ("0016PV", "13 07", "PRELEVEMENT EN FAV. CNSS", "11 07 2026", "1 550,06"),
        ("0016GG", "14 07", "ARRETE DU COMPTE 2E TRIM. 2026", "01 07 2026", "59,40"),
        ("062411", "23 07", "RETRAIT ESPECES CHQ 100575", "22 07 2026", "9 000,00")]


def _awb_pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    put = lambda x, y, t, s=9: page.insert_text((x, y), t, fontsize=s, fontname="cour")
    put(60, 80, "Attijariwafa bank", 14)
    put(300, 150, "RELEVE DE COMPTE BANCAIRE", 11)
    put(30, 190, "AGENCE : AGENCE AWB AZROU")
    put(330, 190, "ASSOCIATION FICTIVE DES CEDRES")
    put(30, 210, "DEVISE : DIRHAM")
    put(330, 240, "RELEVE D'IDENTITE BANCAIRE")
    put(330, 255, "007 425 0006243000302148 76")
    put(150, 300, "SOLDE DEPART AU 30 06 2026")
    put(400, 300, "12 943,82 CREDITEUR")
    put(280, 322, "VALEUR")
    put(35, 336, "CODE  DATE    LIBELLE")
    put(345, 336, "DEBIT")
    put(400, 336, "CAPITAUX")
    put(500, 336, "CREDIT")
    page.draw_line((30, 342), (565, 342), width=0.6)
    y = 360
    for code, d, lab, vd, amount in ROWS:
        put(30, y, f"{code}|{d}|")
        put(100, y, lab)
        put(270, y, vd)
        put(420 - 5.4 * len(amount), y, amount)
        y += 14
    put(150, y + 10, "TOTAL MOUVEMENTS")
    put(355, y + 10, "12 112,43")
    put(520, y + 10, "0,00")
    put(150, y + 60, "SOLDE FINAL AU 31 07 2026")
    put(370, y + 60, "831,39   CREDITEUR")
    data = doc.tobytes()
    doc.close()
    return data


@pytest.mark.skipif(ocr.find_tesseract() is None, reason="Tesseract non installé")
def test_scanned_attijariwafa_statement_is_read_without_ai():
    scan = degrade_to_scan(_awb_pdf(), seed=7, dpi=300)
    st = pipeline.process(scan, "releve_juillet.jpg").statement
    assert st.bank_id == "awb"
    assert (st.opening, st.closing) == (1_294_382, 83_139)
    assert st.balance_ok() is True
    assert [(l.date, l.value_date, l.debit) for l in st.lines] == [
        ("2026-07-13", "2026-07-11", 150_297), ("2026-07-13", "2026-07-11", 155_006),
        ("2026-07-14", "2026-07-01", 5_940), ("2026-07-23", "2026-07-22", 900_000)]
    assert st.lines[0].label == "PRELEVEMENT EN FAV. CNSS" and st.lines[0].reference == "0016PV"
