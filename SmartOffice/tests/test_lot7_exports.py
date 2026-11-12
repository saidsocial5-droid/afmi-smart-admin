"""Lot 7 — exports Word, PDF, Excel et dossier annuel."""
import hashlib
import io
import re
import zipfile
from pathlib import Path

import pytest
from docx import Document
from docx.oxml.ns import qn
from openpyxl import load_workbook

from backend.core import unified_db
from backend.tools.editor import documents
from backend.tools.exports import docx_writer, html_writer, naming, pdf, resolve, xlsx_writer
from backend.tools.reports import finance
from backend.tools.reports.context import layout, period, scope
from tests.test_lot5_reports import unified  # noqa: F401  (fixture : scénario partagé avec .NET)

HAS_BROWSER = bool(pdf.engines()["browser"])
HAS_SOFFICE = bool(pdf.engines()["libreoffice"])


def _doc(language="fr"):
    content = {"type": "doc", "content": [
        {"type": "heading", "attrs": {"level": 1}, "content": [{"type": "text", "text": "Rapport de test"}]},
        {"type": "tableOfContents"},
        {"type": "paragraph", "content": [
            {"type": "text", "text": "Projet "}, {"type": "field", "attrs": {"name": "project_name"}},
            {"type": "text", "text": " gras", "marks": [{"type": "bold"}]},
            {"type": "footnote", "attrs": {"text": "Source : comptes validés."}},
            {"type": "text", "text": " supprimé", "marks": [{"type": "deletion", "attrs": {"author": "a"}}]},
            {"type": "text", "text": " ajouté", "marks": [{"type": "insertion", "attrs": {"author": "a"}}]}]},
        {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "Compte d'emploi"}]},
        {"type": "dynamicBlock", "attrs": {"kind": "annual", "table": "cer", "year": 2026, "scopeType": "association", "lang": language}},
        {"type": "orderedList", "content": [{"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Un"}]}]}]},
        {"type": "orderedList", "content": [{"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Encore un"}]}]}]},
        {"type": "table", "content": [
            {"type": "tableRow", "content": [{"type": "tableHeader", "attrs": {"colspan": 2}, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Fusion"}]}]}]},
            {"type": "tableRow", "content": [{"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "a"}]}]},
                                             {"type": "tableCell", "attrs": {"backgroundColor": "#fde68a"}, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "b"}]}]}]}]},
        {"type": "paragraph", "attrs": {"dir": "rtl"}, "content": [{"type": "text", "text": "نص عربي"}]},
        {"type": "dynamicBlock", "attrs": {"kind": "gallery", "projectId": None}},
        {"type": "pageBreak"},
        {"type": "dynamicBlock", "attrs": {"kind": "annual", "table": "inconnu", "year": 2026}},
    ]}
    layout_ = {"header": {"text": "{association}", "first_page_text": "", "even_text": "Pages paires"},
               "footer": {"text": "Pied", "page_numbers": True, "first_page_different": True, "odd_even_different": True}}
    d = documents.create_document({"title": "Rapport: test/2026", "language": language, "project_id": 1, "content": content})
    return documents.save_document(d["id"], {"layout": layout_})


# --- Préparation ---------------------------------------------------------------------------------------------

def test_prepare_resolves_blocks_fields_and_final_version(unified):
    p = resolve.prepare(_doc()["id"])
    types = [n["type"] for n in p["content"]]
    assert "dynamicBlock" not in types and "x-table" in types and "x-gallery" in types
    assert any(n["type"] == "x-note" and "Données indisponibles" in n["text"] for n in p["content"])   # bloc en erreur signalé
    para = next(n for n in p["content"] if n["type"] == "paragraph")
    texts = [c.get("text") for c in para["content"] if c["type"] == "text"]
    assert "Projet 1" in texts and " supprimé" not in texts and " ajouté" in texts                       # version finale
    assert [h["text"] for h in p["headings"]] == ["Rapport de test", "Compte d'emploi"]
    cer = next(n for n in p["content"] if n["type"] == "x-table")["data"]
    assert cer["total"][1] == 589511 - 95001                                                              # mêmes chiffres que le rapport


def test_number_formatting_matches_editor():
    assert resolve.fmt_number(123456789, "money") == "1 234 567,89"
    assert resolve.fmt_number(12.5, "percent") == "12,5 %" and resolve.fmt_number(None, "percent") == "—"
    assert resolve.split_label("    **Total**") == ("Total", 4, True)


def test_external_images_are_never_downloaded(tmp_path):
    assert resolve.image_path("https://example.org/x.png", tmp_path) is None
    png = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    assert resolve.image_path(png, tmp_path).exists()


# --- Word ----------------------------------------------------------------------------------------------------

def _docx(language="fr", tmp_path=None):
    return Document(io.BytesIO(docx_writer.render(resolve.prepare(_doc(language)["id"]), tmp_path)))


def test_docx_structure(unified, tmp_path):
    d = _docx("fr", tmp_path)
    styles = [p.style.name for p in d.paragraphs]
    assert "Heading 1" in styles and "Heading 2" in styles
    body = d.element.body.xml
    assert 'TOC \\o "1-3"' in body                                            # table des matières Word (champ)
    assert "<w:footnoteReference" in body
    footnotes = next(r.target_part for r in d.part.rels.values() if r.reltype.endswith("/footnotes"))
    assert "Source : comptes validés." in footnotes.blob.decode()             # vraie note de bas de page
    sec = d.sections[0]
    assert sec.different_first_page_header_footer and d.settings.odd_and_even_pages_header_footer
    assert "PAGE" in sec.footer._element.xml and "NUMPAGES" in sec.footer._element.xml
    assert "PAGE" not in sec.first_page_footer._element.xml                    # pas de numéro sur la première page
    assert "Pages paires" in sec.even_page_header._element.xml
    assert "Association Forêt Modèle" in sec.header._element.xml               # champ {association} rempli
    # deux listes numérotées : deux instances de numérotation (chacune repart à 1)
    nums = {p._p.pPr.numPr.numId.val for p in d.paragraphs if p._p.pPr is not None and p._p.pPr.numPr is not None}
    assert len(nums) == 2
    # tableau fusionné et trame
    merged = [t for t in d.tables if "Fusion" in t._tbl.xml][0]
    assert 'w:gridSpan w:val="2"' in merged._tbl.xml and "FDE68A" in merged._tbl.xml
    # tableau du CER : en-tête répété, montants au format français
    cer = [t for t in d.tables if "Total emplois" in t._tbl.xml][0]
    assert "<w:tblHeader/>" in cer._tbl.xml and "4 945,10" in cer._tbl.xml
    assert any(p.text == "نص عربي" and p._p.pPr.find(qn("w:bidi")) is not None for p in d.paragraphs)


def test_docx_properties_follow_schema_order(unified, tmp_path):
    d = _docx("fr", tmp_path)
    order = docx_writer._ORDER["pPr"].split()
    for ppr in d.element.body.iter(qn("w:pPr")):
        names = [c.tag.split("}")[1] for c in ppr]
        ranks = [order.index(n) for n in names if n in order]
        assert ranks == sorted(ranks), names


def test_docx_arabic_document_is_rtl(unified, tmp_path):
    d = _docx("ar", tmp_path)
    assert d.sections[0]._sectPr.find(qn("w:bidi")) is not None
    assert all(t._tbl.tblPr.find(qn("w:bidiVisual")) is not None for t in d.tables)
    assert d.core_properties.language == "ar-MA"


@pytest.mark.skipif(not HAS_SOFFICE, reason="LibreOffice absent")
def test_docx_opens_in_libreoffice(unified, tmp_path):
    data = docx_writer.render(resolve.prepare(_doc()["id"]), tmp_path)
    out = pdf.docx_to_pdf(data, tmp_path)
    import pymupdf
    doc = pymupdf.open(stream=out, filetype="pdf")
    assert doc.page_count >= 2 and "Source : comptes validés." in "".join(p.get_text() for p in doc)


# --- HTML et PDF --------------------------------------------------------------------------------------------

def test_html_is_self_contained(unified, tmp_path):
    html = html_writer.render(resolve.prepare(_doc("ar")["id"]), tmp_path)
    assert 'dir="rtl"' in html and "@page :first" in html and "@page :left" in html
    assert 'href="http' not in html.replace('href="https://', "") and "src=\"http" not in html
    assert "Source : comptes validés." in html and 'class="footnotes"' in html


@pytest.mark.skipif(not HAS_BROWSER, reason="Aucun navigateur pour imprimer en PDF")
def test_pdf_has_bookmarks_metadata_and_embedded_fonts(unified):
    import pymupdf
    data = pdf.to_pdf(resolve.prepare(_doc()["id"]))
    doc = pymupdf.open(stream=data, filetype="pdf")
    assert [t[1] for t in doc.get_toc()] == ["Rapport de test", "Compte d'emploi"]
    assert doc.metadata["title"] == "Rapport: test/2026"
    assert "fr-FR" in doc.xref_get_key(doc.pdf_catalog(), "Lang")[1]
    fonts = [f for p in doc for f in p.get_fonts()]
    assert fonts and all(f[1] != "n/a" for f in fonts)                     # polices intégrées


def test_pdfa_requires_libreoffice(unified, monkeypatch):
    monkeypatch.setattr(pdf, "engines", lambda: {"browser": "x", "libreoffice": None})
    with pytest.raises(pdf.PdfError, match="LibreOffice"):
        pdf.to_pdf(resolve.prepare(_doc()["id"]), pdfa=True)


@pytest.mark.skipif(not HAS_SOFFICE, reason="LibreOffice absent")
def test_pdfa_declares_conformance(unified):
    import pymupdf
    doc = pymupdf.open(stream=pdf.to_pdf(resolve.prepare(_doc()["id"]), pdfa=True), filetype="pdf")
    xmp = doc.get_xml_metadata()
    assert "pdfaid:part" in xmp and doc.get_toc()


# --- Excel ---------------------------------------------------------------------------------------------------

_REF = re.compile(r"(?:'?([^'!]+)'?!)?\$?([A-Z]+)\$?(\d+)")


def _evaluate(wb, sheet, formula, depth=0):
    """Évaluateur minimal des formules produites (SUM, +, -, SUMIFS, IF) pour vérifier les résultats sans tableur."""
    from openpyxl.utils import column_index_from_string

    def value(sh, col, row):
        v = wb[sh].cell(row=int(row), column=column_index_from_string(col)).value
        if isinstance(v, str) and v.startswith("="):
            return _evaluate(wb, sh, v, depth + 1)
        return v or 0

    expr = formula[1:]
    if expr.startswith("IF("):
        return None
    def sumifs(m):
        args = [a.strip() for a in m.group(1).split(",")]
        sum_rng, crit_rng, crit = args[0], args[1], args[2].strip('"')
        sh = sum_rng.split("!")[0].strip("'") if "!" in sum_rng else sheet
        (c1, r1), (c2, r2) = [_REF.search(x).groups()[1:] for x in sum_rng.split("!")[-1].split(":")]
        cc = crit_rng.split("!")[-1].split(":")[0].replace("$", "")
        ccol = re.match(r"[A-Z]+", cc).group(0)
        total = 0
        for r in range(int(r1), int(r2) + 1):
            if wb[sh].cell(row=r, column=column_index_from_string(ccol)).value == crit:
                total += value(sh, c1, r)
        return str(total)
    expr = re.sub(r"SUMIFS\(([^)]*)\)", sumifs, expr)
    def rng(m):
        sh = m.group(1) or sheet
        from openpyxl.utils import get_column_letter
        c1, r1, c2, r2 = column_index_from_string(m.group(2)), int(m.group(3)), column_index_from_string(m.group(4)), int(m.group(5))
        cells = [str(value(sh, get_column_letter(c), r)) for r in range(r1, r2 + 1) for c in range(c1, c2 + 1)]
        return "(" + "+".join(cells) + ")"
    expr = re.sub(r"SUM\((?:'?([^'!(]+)'?!)?\$?([A-Z]+)\$?(\d+):\$?([A-Z]+)\$?(\d+)\)", rng, expr)
    expr = _REF.sub(lambda m: str(value(m.group(1) or sheet, m.group(2), m.group(3))), expr)
    return eval(expr, {"__builtins__": {}})  # noqa: S307 — expression arithmétique produite par le test


def test_financial_workbook_formulas_reproduce_the_report(unified):
    wb = load_workbook(io.BytesIO(xlsx_writer.financial_workbook(2026)))
    assert {"CER", "Recettes-Dépenses", "Budget par projet", "Trésorerie", "Comparaison", "Ventilations", "Contrôles"} <= set(wb.sheetnames)
    formulas = 0
    for ws in wb:
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value, str) and c.value.startswith("=") and not c.value.startswith("=IF("):
                    formulas += 1
                    assert _evaluate(wb, ws.title, c.value) is not None
    assert formulas >= 20
    cer = wb["CER"]
    result = next(r for r in cer.iter_rows() if r[0].value and str(r[0].value).startswith("Résultat") and isinstance(r[1].value, str))
    assert result[1].value.startswith("=")                                       # résultat = formule
    assert abs(_evaluate(wb, "CER", result[1].value) - (589511 - 95001) / 100) < 1e-6
    for row in wb["Contrôles"].iter_rows(min_row=5):
        if row[3].value:
            assert abs(_evaluate(wb, "Contrôles", row[3].value)) < 1e-6            # écarts nuls
    with unified_db.connect() as conn:
        bp = finance.budget_execution(conn, period(conn, 2026), scope(conn, "association", None))
    ws = wb["Budget par projet"]
    total = next(r for r in ws.iter_rows() if r[0].value == "Total")
    assert abs(_evaluate(wb, ws.title, total[2].value) - bp["total"][2] / 100) < 1e-6


def test_formula_kept_only_when_exact():
    data = {"rows": [["**Groupe**", 100, 50], ["    a", 60, 20], ["    b", 30, 30]], "formats": ["text", "money", "money"]}
    plan = xlsx_writer.FormulaPlanner(data, "x", 5).plan()
    assert (0, 1) not in plan                       # 60 + 30 ≠ 100 : la valeur de l'application est conservée
    assert plan[(0, 2)] == "=SUM(C6:C7)"


def test_operations_workbook_running_balance(unified):
    wb = load_workbook(io.BytesIO(xlsx_writer.operations_workbook()))
    with unified_db.connect() as conn:
        expected = {r["Title"]: finance.book_balance(conn, r["Id"], "9999-12-31") for r in conn.execute("SELECT * FROM BankAccounts")}
    for ws in wb:
        last = ws.max_row
        closing = ws.cell(row=last, column=11).value
        assert closing.startswith("=")
        title = ws.cell(row=1, column=1).value.split(" — ")[0]
        assert abs(_evaluate(wb, ws.title, closing) - expected[title] / 100) < 1e-6


def test_reconciliation_workbook_difference(unified):
    with unified_db.connect() as conn:
        sid = conn.execute("SELECT Id FROM BankStatements").fetchone()[0]
        rec = finance.reconciliation_status(conn, 1, "2026-12-31")
    wb = load_workbook(io.BytesIO(xlsx_writer.reconciliation_workbook(sid)))
    ws = wb["État de rapprochement"]
    gap = next(r for r in ws.iter_rows() if r[0].value == "Écart (doit être nul)")
    assert abs(_evaluate(wb, ws.title, gap[1].value) - rec["difference"] / 100) < 1e-6


# --- Nommage, API, dossier annuel ---------------------------------------------------------------------------

def test_naming_patterns(unified):
    assert naming.file_name("pdf", "financial", 2026, "fr") == "AFMI_RapportFinancier_2026_FR.pdf"
    assert naming.file_name("docx", "document", title='Rapport: S1 / "final"', pattern="{org}_{title}") == "AFMI_Rapport_S1_final.docx"
    unified_db.set_setting("exports.naming.report", "{year}-{type}-{lang}")
    assert naming.file_name("xlsx", "statements", 2025, "ar") == "2025-EtatsFinanciers-AR.xlsx"


def test_document_export_api(client, unified):
    doc = _doc()
    r = client.get(f"/api/exports/document/{doc['id']}?format=docx")
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/vnd.openxmlformats")
    assert "filename*=UTF-8''AFMI_Rapport" in r.headers["content-disposition"]
    assert client.get(f"/api/exports/document/{doc['id']}?format=odt").status_code == 400
    with unified_db.connect() as conn:
        audit = conn.execute("SELECT * FROM AuditEntries WHERE EntityType = 'Export' ORDER BY Id DESC").fetchone()
    assert audit["EntityId"] == f"EditorDocument:{doc['id']}" and hashlib.sha256(r.content).hexdigest() in audit["ChangesJson"]


@pytest.mark.skipif(not HAS_BROWSER and not HAS_SOFFICE, reason="Aucun moteur PDF")
def test_annual_package(client, unified, tmp_path):
    from backend.config.settings import settings
    annex = tmp_path / "convention.pdf"
    import pymupdf
    a = pymupdf.open()
    a.new_page().insert_text((72, 72), "Convention signée")
    annex.write_bytes(a.tobytes())
    with unified_db.connect() as conn:
        aid = unified_db.insert(conn, "Documents", "Document", {
            "ProjectId": 1, "Title": "Convention", "Category": "Convention", "DocumentPhase": "", "Tags": "", "IsKeyReference": 0,
            "DocumentVersion": "", "DonorName": "", "DocumentReference": "", "ApprovedGrantAmount": "0", "FilePath": str(annex),
            "OriginalFileName": "convention.pdf", "FileExtension": ".pdf", "FileSize": annex.stat().st_size, "Notes": "",
            "ExtractedSummary": "", "FullExtractedText": "", "KeyInsights": "", "UploadedDate": unified_db.now_ef(),
            "DocType": "Convention", "LifecyclePhase": "Instruction", "ClassificationConfidence": 1, "MetadataJson": "{}",
            "Language": "fr", "IsDeleted": 0})
    r = client.post("/api/exports/annual-package", json={"year": 2026, "annex_ids": [aid], "formats": ["pdf", "xlsx"]})
    assert r.status_code == 200, r.text
    z = zipfile.ZipFile(io.BytesIO(r.content))
    names = z.namelist()
    assert {"AFMI_RapportAnnuel_2026_FR.pdf", "AFMI_RapportMoral_2026_FR.pdf", "AFMI_RapportFinancier_2026_FR.pdf",
            "AFMI_EtatsFinanciers_2026_FR.xlsx", "Annexes/Convention.pdf"} <= set(names)
    manifest = z.read("LISEZMOI_empreintes_SHA256.txt").decode()
    for n in names:
        if n != "LISEZMOI_empreintes_SHA256.txt":
            assert f"{hashlib.sha256(z.read(n)).hexdigest()}  {n}" in manifest
    merged = pymupdf.open(stream=z.read("AFMI_RapportAnnuel_2026_FR.pdf"), filetype="pdf")
    top = [t[1] for t in merged.get_toc() if t[0] == 1]
    assert top == ["Rapport moral", "Rapport financier", "Annexes"]
    assert "Convention signée" in merged[-1].get_text()
