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
    seen = "\n".join(f"{l.date} {l.value_date} {l.reference!r} {l.label!r} D={l.debit} C={l.credit}" for l in st.lines)
    from backend.tools.statements.extract import group_lines
    from backend.tools.statements.preprocess import load_image
    raw_words, _, _ = pipeline._ocr_page(load_image(scan), 0, "fra")
    raw = "\n".join(" | ".join(f"{w.text}@{int(w.x0)}" for w in l) for l in group_lines(raw_words)
                     if any(k in " ".join(w.text for w in l) for k in ("PREL", "RETRAIT", "ARRETE", "SOLDE", "DATE", "VALEUR")))
    diag = f"\nsoldes {st.opening} → {st.closing}\n{seen}\n{st.warnings}\nOCR :\n{raw}"
    assert st.bank_id == "awb", diag
    assert (st.opening, st.closing) == (1_294_382, 83_139), diag
    assert st.balance_ok() is True, diag
    assert [(l.date, l.value_date, l.debit) for l in st.lines] == [  # noqa: E501
        ("2026-07-13", "2026-07-11", 150_297), ("2026-07-13", "2026-07-11", 155_006),
        ("2026-07-14", "2026-07-01", 5_940), ("2026-07-23", "2026-07-22", 900_000)]
    assert st.lines[0].label == "PRELEVEMENT EN FAV. CNSS" and st.lines[0].reference == "0016PV"


# Lecture réelle du Tesseract Windows livré (diagnostic du poste de build) : « 59, » « 40 » séparés, code « 062411|23 ».
WINDOWS_OCR = [
    "SOLDE@659 DEPART@792 AU@949 30@1019 06@1087 2026@1154 12@1702 943,82@1770 CREDITEUR@1924",
    "VALEUR@1198",
    "CODE@179 DATE@313 LIBELLE@494 DEBIT@1470 CAPITAUX@1699 CREDIT@2116",
    "0016PV|13@160 07|PRELEVEMENT@385 EN@719 FAV.@786 CNSS@899 11@1160 07@1227 2026@1294 1@1605 502,97@1649",
    "0016PV|13@160 07|PRELEVEMENT@385 EN@719 FAV.@786 CNSS@899 11@1160 07@1227 2026@1294 1@1605 550,06@1649",
    "0016GG|14@160 07|ARRETE@385 DU@606 COMPTE@674 2E@833 TRIM.@900 2026@1035 01@1160 07@1227 2026@1294 59,@1672 40@1741",
    "062411|23@160 07|RETRAIT@385 ESPECES@629 CHO@809 100575@901 22@1159 07@1227 2026@1294 9@1606 000,00@1650",
    "SOLDE@659 FINAL@792 AU@926 31@997 07@1065 2026@1131 831,39@1576 —@1742 CREDITEUR@1777",
]


def test_attijariwafa_tokens_read_by_windows_tesseract():
    from backend.tools.statements.extract import extract
    from backend.tools.statements.model import Word
    from backend.tools.statements.templates import load
    words = []
    for i, line in enumerate(["Attijariwafa@500 bank@800", "RELEVE@300 D'IDENTITE@450 BANCAIRE@700 007@300 425@380 0006243000302148@460 76@900"] + WINDOWS_OCR):
        y = 100 + 40 * i
        for tok in line.split():
            text, x = tok.rsplit("@", 1)
            x = float(x)
            words.append(Word(text, x, y, x + 21 * len(text), y + 24, 90.0, 0))
    st = extract(words, *load(), "tesseract", {0: 3500})
    assert (st.opening, st.closing) == (1_294_382, 83_139) and st.balance_ok() is True, st.warnings
    assert [l.debit for l in st.lines] == [150_297, 155_006, 5_940, 900_000]
    assert [l.reference for l in st.lines] == ["0016PV", "0016PV", "0016GG", "062411"]
    assert st.lines[2].label == "ARRETE DU COMPTE 2E TRIM. 2026"
