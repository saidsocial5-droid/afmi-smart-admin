"""Export Word (.docx) fidèle à l'éditeur.

Entrée : le document préparé par ``resolve.prepare`` (contenu TipTap aux blocs dynamiques résolus, charte effective).
Ce que le fichier contient :

- styles Word natifs (Normal, Titre 1 à 3, Citation, Liste à puces / numérotée) aux polices et couleurs de la charte,
  ce qui garde le volet de navigation et la table des matières de Word ;
- en-têtes et pieds de page : première page distincte, pages paires et impaires si la charte le demande, logos,
  mentions obligatoires, numéros « Page X / Y » en champs Word (PAGE, NUMPAGES) ;
- table des matières en champ TOC (Word propose de la mettre à jour à l'ouverture ; elle est pré-remplie) ;
- vraies notes de bas de page Word (partie footnotes.xml), numérotées par Word ;
- tableaux (en-tête répété à chaque page, trames, cellules fusionnées), images, graphiques, galeries légendées ;
- arabe : paragraphes et tableaux de droite à gauche (w:bidi, w:rtl, w:bidiVisual), langue ar-MA.
"""
import io
from pathlib import Path
from typing import Any, Dict, List, Optional
from xml.sax.saxutils import escape

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.opc.packuri import PackURI
from docx.opc.part import Part
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Mm, Pt, RGBColor
from PIL import Image

from . import graphics
from .resolve import fmt_number, logo_path, image_path, split_label

LANG_TAGS = {"fr": "fr-FR", "ar": "ar-MA", "en": "en-GB"}
ALIGN = {"left": WD_ALIGN_PARAGRAPH.LEFT, "center": WD_ALIGN_PARAGRAPH.CENTER, "right": WD_ALIGN_PARAGRAPH.RIGHT,
         "justify": WD_ALIGN_PARAGRAPH.JUSTIFY}
FOOTNOTES_CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml"
HEADING_SIZES = {1: 18, 2: 14, 3: 12}


def _hex(color: Optional[str], default: str = "1F2937") -> str:
    c = (color or "").strip().lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    if len(c) != 6 or any(ch not in "0123456789abcdefABCDEF" for ch in c):
        return default
    return c.upper()


def _css_color(value: Optional[str]) -> Optional[str]:
    """Couleur d'une marque TipTap : #rrggbb ou rgb(r, g, b)."""
    if not value:
        return None
    v = value.strip()
    if v.startswith("rgb"):
        try:
            parts = [int(float(x)) for x in v[v.index("(") + 1:v.index(")")].split(",")[:3]]
            return "".join(f"{p:02X}" for p in parts)
        except ValueError:
            return None
    h = _hex(v, "")
    return h or None


def _el(tag: str, **attrs) -> Any:
    e = OxmlElement(tag)
    for k, v in attrs.items():
        e.set(qn(k.replace("_", ":", 1)), str(v))
    return e


class DocxWriter:
    def __init__(self, prepared: Dict[str, Any], tmp_dir: Path):
        self.p = prepared
        self.style = prepared["style"]
        self.lang = prepared["language"]
        self.rtl_doc = self.lang == "ar"
        self.tmp = tmp_dir
        self.doc = Document()
        self.footnotes: List[str] = []
        self.photo_no = 0
        self.heading_no = [0, 0, 0]
        m = self.style.get("margins_mm") or {}
        self.margins = {k: float(m.get(k) or d) for k, d in (("top", 25), ("bottom", 22), ("left", 20), ("right", 20))}
        self.content_width_mm = 210 - self.margins["left"] - self.margins["right"]
        self.cs_font = (self.style.get("fonts") or {}).get("arabic") or "Arial"

    # --- Mise en place ---------------------------------------------------------------------------------------

    def _setup(self) -> None:
        s = self.doc.sections[0]
        s.page_width, s.page_height = Mm(210), Mm(297)
        s.top_margin, s.bottom_margin = Mm(self.margins["top"]), Mm(self.margins["bottom"])
        s.left_margin, s.right_margin = Mm(self.margins["left"]), Mm(self.margins["right"])
        s.header_distance, s.footer_distance = Mm(10), Mm(9)
        if self.rtl_doc:
            s._sectPr.append(_el("w:bidi"))
        colors, fonts = self.style.get("colors") or {}, self.style.get("fonts") or {}
        body, headings = fonts.get("body") or "Calibri", fonts.get("headings") or fonts.get("body") or "Calibri"
        normal = self.doc.styles["Normal"]
        normal.font.name = body
        normal.font.size = Pt(float(fonts.get("size_pt") or 11))
        normal.font.color.rgb = RGBColor.from_string(_hex(colors.get("text")))
        self._fonts(normal.element, body)
        normal.paragraph_format.space_after = Pt(6)
        normal.paragraph_format.line_spacing = 1.15
        rpr = normal.element.get_or_add_rPr()
        rpr.append(_el("w:lang", w_val=LANG_TAGS.get(self.lang, "fr-FR"), w_bidi="ar-MA"))
        for level in (1, 2, 3):
            h = self.doc.styles[f"Heading {level}"]
            h.font.name = headings
            h.font.size = Pt(HEADING_SIZES[level])
            h.font.bold = True
            h.font.color.rgb = RGBColor.from_string(_hex(colors.get("primary"), "1B4332"))
            self._fonts(h.element, headings)
            h.paragraph_format.space_before = Pt({1: 14, 2: 12, 3: 10}[level])
            h.paragraph_format.space_after = Pt({1: 8, 2: 6, 3: 4}[level])
            h.paragraph_format.keep_with_next = True
        styles = self.doc.styles
        if "Footnote Text" not in [x.name for x in styles]:
            ft = styles.add_style("Footnote Text", WD_STYLE_TYPE.PARAGRAPH)
            ft.base_style = styles["Normal"]
            ft.font.size = Pt(8.5)
            ft.paragraph_format.space_after = Pt(0)
            fr = styles.add_style("Footnote Reference", WD_STYLE_TYPE.CHARACTER)
            fr.font.superscript = True
        cap = styles["Caption"]
        cap.font.size = Pt(8.5)
        cap.font.italic = False
        cap.font.color.rgb = RGBColor.from_string("374151")
        self._settings_insert(_el("w:updateFields", w_val="true"))   # Word met à jour la table des matières à l'ouverture
        core = self.doc.core_properties
        core.title = self.p["title"]
        core.language = LANG_TAGS.get(self.lang, "fr-FR")
        core.author = self.p["fields"].get("association") or "AFMI"

    def _fonts(self, style_el, font: str) -> None:
        rpr = style_el.get_or_add_rPr()
        rf = rpr.find(qn("w:rFonts"))
        if rf is None:
            rf = _el("w:rFonts")
            rpr.insert(0, rf)
        for a in ("w:ascii", "w:hAnsi", "w:eastAsia"):
            rf.set(qn(a), font)
        rf.set(qn("w:cs"), self.cs_font)
        for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
            rf.attrib.pop(qn(a), None)

    # --- Paragraphes et texte --------------------------------------------------------------------------------

    def _para(self, container, node: Dict[str, Any], style: Optional[str] = None):
        attrs = node.get("attrs") or {}
        para = container.add_paragraph(style=style)
        rtl = attrs.get("dir") == "rtl" or (self.rtl_doc and attrs.get("dir") != "ltr")
        if rtl:
            para._p.get_or_add_pPr().append(_el("w:bidi"))
        if attrs.get("textAlign") in ALIGN and attrs.get("textAlign") != "left":
            para.alignment = ALIGN[attrs["textAlign"]]
        self._inline(para, node.get("content") or [], rtl)
        return para

    def _inline(self, para, nodes: List[Dict[str, Any]], rtl: bool) -> None:
        for n in nodes:
            t = n.get("type")
            if t == "text":
                self._run(para, n.get("text", ""), n.get("marks") or [], rtl)
            elif t == "hardBreak":
                para.add_run().add_break()
            elif t == "footnote":
                self._footnote_ref(para, (n.get("attrs") or {}).get("text") or "")
            elif t == "x-field":
                self._field(para, "PAGE" if n["name"] == "page" else "NUMPAGES")
            elif t == "image":
                self._image_run(para, n.get("attrs") or {})

    def _run(self, para, text: str, marks: List[Dict[str, Any]], rtl: bool):
        link = next((m for m in marks if m.get("type") == "link"), None)
        target = para
        if link and (link.get("attrs") or {}).get("href"):
            r_id = para.part.relate_to(link["attrs"]["href"], RT.HYPERLINK, is_external=True)
            hl = _el("w:hyperlink", r_id=r_id)
            para._p.append(hl)
            target = None
        run = para.add_run(text) if target is not None else None
        if run is None:
            r = _el("w:r")
            t = _el("w:t")
            t.text = text
            t.set(qn("xml:space"), "preserve")
            r.append(t)
            hl.append(r)
            from docx.text.run import Run
            run = Run(r, para)
            run.font.color.rgb = RGBColor.from_string("1D4ED8")
            run.font.underline = True
        for m in marks:
            mt, a = m.get("type"), m.get("attrs") or {}
            if mt == "bold":
                run.bold = True
            elif mt == "italic":
                run.italic = True
            elif mt == "underline":
                run.underline = True
            elif mt == "strike":
                run.font.strike = True
            elif mt == "subscript":
                run.font.subscript = True
            elif mt == "superscript":
                run.font.superscript = True
            elif mt == "code":
                run.font.name = "Consolas"
            elif mt == "textStyle":
                c = _css_color(a.get("color"))
                if c:
                    run.font.color.rgb = RGBColor.from_string(c)
                if a.get("fontFamily"):
                    run.font.name = a["fontFamily"].split(",")[0].strip().strip("'\"")
                size = str(a.get("fontSize") or "")
                if size.endswith("pt"):
                    run.font.size = Pt(float(size[:-2]))
                elif size.endswith("px"):
                    run.font.size = Pt(float(size[:-2]) * 0.75)
            elif mt == "highlight":
                c = _css_color(a.get("color")) or "FEF08A"
                run._r.get_or_add_rPr().append(_el("w:shd", w_val="clear", w_color="auto", w_fill=c))
        if rtl:
            run._r.get_or_add_rPr().append(_el("w:rtl"))
        return run

    def _field(self, para, instr: str, placeholder: str = "1") -> None:
        fld = _el("w:fldSimple", w_instr=f" {instr} ")
        r = _el("w:r")
        t = _el("w:t")
        t.text = placeholder
        r.append(t)
        fld.append(r)
        para._p.append(fld)

    def _footnote_ref(self, para, text: str) -> None:
        self.footnotes.append(text)
        fid = len(self.footnotes)              # 0 et -1 réservés aux séparateurs (ids 1.. ici décalés plus bas)
        r = _el("w:r")
        rpr = _el("w:rPr")
        rpr.append(_el("w:rStyle", w_val="FootnoteReference"))
        r.append(rpr)
        r.append(_el("w:footnoteReference", w_id=fid + 1))
        para._p.append(r)

    def _footnotes_part(self) -> None:
        if not self.footnotes:
            return
        notes = ['<w:footnote w:type="separator" w:id="-1"><w:p><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr>'
                 '<w:r><w:separator/></w:r></w:p></w:footnote>',
                 '<w:footnote w:type="continuationSeparator" w:id="0"><w:p><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr>'
                 '<w:r><w:continuationSeparator/></w:r></w:p></w:footnote>']
        bidi = "<w:bidi/>" if self.rtl_doc else ""
        for i, text in enumerate(self.footnotes, start=1):
            notes.append(f'<w:footnote w:id="{i + 1}"><w:p><w:pPr><w:pStyle w:val="FootnoteText"/>{bidi}</w:pPr>'
                         f'<w:r><w:rPr><w:rStyle w:val="FootnoteReference"/></w:rPr><w:footnoteRef/></w:r>'
                         f'<w:r><w:t xml:space="preserve"> {escape(text)}</w:t></w:r></w:p></w:footnote>')
        xml = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:footnotes {nsdecls("w", "r")}>' + "".join(notes) + "</w:footnotes>")
        part = Part(PackURI("/word/footnotes.xml"), FOOTNOTES_CT, xml.encode("utf-8"), self.doc.part.package)
        self.doc.part.relate_to(part, RT.FOOTNOTES)
        self._settings_insert(parse_xml(f'<w:footnotePr {nsdecls("w")}><w:footnote w:id="-1"/><w:footnote w:id="0"/></w:footnotePr>'))

    def _settings_insert(self, element) -> None:
        """Insère avant w:compat (ordre imposé par le schéma : updateFields, footnotePr, …, compat)."""
        settings = self.doc.settings.element
        anchor = next((settings.find(qn(t)) for t in ("w:endnotePr", "w:compat", "w:docVars", "w:rsids") if settings.find(qn(t)) is not None), None)
        if anchor is None:
            settings.append(element)
        else:
            anchor.addprevious(element)

    # --- Images ----------------------------------------------------------------------------------------------

    def _fit_width(self, path: Path, max_mm: float) -> float:
        try:
            with Image.open(path) as im:
                w = im.width / ((im.info.get("dpi") or (96, 96))[0] or 96) * 25.4
        except OSError:
            return max_mm
        return min(w, max_mm)

    def _image_run(self, para, attrs: Dict[str, Any], max_mm: Optional[float] = None) -> bool:
        path = image_path(attrs.get("src") or "", self.tmp)
        if path is None:
            para.add_run(f"[Image non disponible{' : ' + attrs['alt'] if attrs.get('alt') else ''}]").italic = True
            return False
        width = self._fit_width(path, max_mm or self.content_width_mm)
        para.add_run().add_picture(str(path), width=Mm(width))
        self._alt(para, attrs.get("alt") or attrs.get("title") or "")
        return True

    @staticmethod
    def _alt(para, text: str) -> None:
        """Texte de remplacement (accessibilité) sur la dernière image insérée."""
        props = para._p.findall(".//" + qn("wp:docPr"))
        if props and text:
            props[-1].set("descr", text)

    def _picture_bytes(self, container, data: bytes, width_mm: float, align_center: bool = True):
        para = container.add_paragraph()
        if align_center:
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        para.add_run().add_picture(io.BytesIO(data), width=Mm(width_mm))
        return para

    # --- Tableaux --------------------------------------------------------------------------------------------

    def _cell_shading(self, cell, fill: Optional[str]) -> None:
        if not fill:
            return
        tcpr = cell._tc.get_or_add_tcPr()
        tcpr.append(_el("w:shd", w_val="clear", w_color="auto", w_fill=fill))

    def _table_common(self, table, header_rows: int = 1) -> None:
        table.style = self.doc.styles["Table Grid"]
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        tblpr = table._tbl.tblPr
        if self.rtl_doc:
            tblpr.append(_el("w:bidiVisual"))
        border = _hex((self.style.get("table") or {}).get("border_color"), "CBD5E1")
        borders = _el("w:tblBorders")
        for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
            borders.append(_el(f"w:{side}", w_val="single", w_sz=4, w_space=0, w_color=border))
        tblpr.append(borders)
        for row in table.rows[:header_rows]:
            trpr = row._tr.get_or_add_trPr()
            trpr.append(_el("w:tblHeader"))                       # en-tête répété sur chaque page
        for row in table.rows:
            row._tr.get_or_add_trPr().append(_el("w:cantSplit"))

    def _cell_text(self, cell, text: str, bold: bool = False, align: Optional[str] = None, color: Optional[str] = None,
                   indent_mm: float = 0, size: float = 9.5) -> None:
        para = cell.paragraphs[0]
        para.paragraph_format.space_after = Pt(0)
        if self.rtl_doc:
            para._p.get_or_add_pPr().append(_el("w:bidi"))
        if align:
            para._p.get_or_add_pPr().append(_el("w:jc", w_val=align))
        if indent_mm:
            para.paragraph_format.first_line_indent = None
            ind = _el("w:ind", w_start=int(indent_mm * 56.7))  # retrait logique (côté début, à droite en arabe)
            para._p.get_or_add_pPr().append(ind)
        run = para.add_run(text)
        run.font.size = Pt(size)
        run.bold = bold or None
        if color:
            run.font.color.rgb = RGBColor.from_string(color)
        if self.rtl_doc:
            run._r.get_or_add_rPr().append(_el("w:rtl"))

    def _widths(self, table, weights: List[float], total_mm: Optional[float] = None) -> None:
        """Largeurs de colonnes proportionnelles (grille et cellules : Word et LibreOffice lisent l'une ou l'autre)."""
        total_mm = total_mm or self.content_width_mm
        s = sum(weights) or 1
        mm = [total_mm * w / s for w in weights]
        table.autofit = False
        grid = table._tbl.tblGrid
        for col, w in zip(grid.findall(qn("w:gridCol")), mm):
            col.set(qn("w:w"), str(int(w * 56.7)))
        for row in table.rows:
            for cell, w in zip(row.cells, mm):
                cell.width = Mm(w)

    def _generic_table(self, container, data: Dict[str, Any]) -> None:
        """Tableau des rapports (formats par colonne), comme GenericTable dans l'éditeur."""
        cols, rows, total = data.get("columns") or [], data.get("rows") or [], data.get("total")
        formats = data.get("formats") or ["text"] * len(cols)
        tstyle = self.style.get("table") or {}
        if not rows:
            self._note(container, "Aucune donnée.")
        else:
            table = container.add_table(rows=1 + len(rows) + (1 if total else 0), cols=len(cols))
            hbg, hcolor = _hex(tstyle.get("header_bg"), "1B4332"), _hex(tstyle.get("header_color"), "FFFFFF")
            for j, c in enumerate(cols):
                cell = table.rows[0].cells[j]
                self._cell_shading(cell, hbg)
                self._cell_text(cell, str(c), bold=True, color=hcolor, align="end" if formats[j] != "text" else None)
            stripe = _hex(tstyle.get("stripe"), "F8F9FA")
            for i, r in enumerate(rows, start=1):
                label, indent, bold = split_label(r[0])
                for j, v in enumerate(r):
                    cell = table.rows[i].cells[j]
                    if bold:
                        self._cell_shading(cell, "F1F5F9")
                    elif i % 2 == 0:
                        self._cell_shading(cell, stripe)
                    if j == 0:
                        self._cell_text(cell, label, bold=bold, indent_mm=indent * 2)
                    else:
                        self._cell_text(cell, fmt_number(v, formats[j] if j < len(formats) else "text"), bold=bold,
                                        align="end" if formats[j] != "text" else None)
            if total:
                for j, v in enumerate(total):
                    cell = table.rows[-1].cells[j]
                    self._cell_text(cell, str(v) if j == 0 else fmt_number(v, formats[j]), bold=True,
                                    align="end" if j and formats[j] != "text" else None)
            text_cols = [j for j, f in enumerate(formats) if f == "text"]
            widths = []
            for j, f in enumerate(formats):
                widths.append(2.2 if j == 0 else (1.4 if f == "text" else 1.0))
            self._widths(table, widths)
            self._table_common(table)
        for n in data.get("notes") or []:
            self._note(container, n)

    def _editor_table(self, container, node: Dict[str, Any]) -> None:
        """Tableau saisi dans l'éditeur : cellules fusionnées (colspan, rowspan), trames, cellules d'en-tête."""
        rows = [r for r in node.get("content") or [] if r.get("type") == "tableRow"]
        if not rows:
            return
        grid: Dict[tuple, Any] = {}
        placements = []
        ncols = 0
        for i, row in enumerate(rows):
            j = 0
            for cell in row.get("content") or []:
                while (i, j) in grid:
                    j += 1
                a = cell.get("attrs") or {}
                cs, rs = int(a.get("colspan") or 1), int(a.get("rowspan") or 1)
                for di in range(rs):
                    for dj in range(cs):
                        grid[(i + di, j + dj)] = True
                placements.append((i, j, cs, rs, cell))
                j += cs
            ncols = max(ncols, j)
        nrows = max([i for i, _ in grid] + [len(rows) - 1]) + 1
        table = container.add_table(rows=nrows, cols=max(ncols, 1))
        tstyle = self.style.get("table") or {}
        header_rows = 0
        for i, j, cs, rs, cell in placements:
            target = table.cell(i, j)
            if cs > 1 or rs > 1:
                target = target.merge(table.cell(min(i + rs - 1, nrows - 1), min(j + cs - 1, ncols - 1)))
            a = cell.get("attrs") or {}
            is_header = cell.get("type") == "tableHeader"
            fill = _css_color(a.get("backgroundColor")) or (_hex(tstyle.get("header_bg"), "1B4332") if is_header else None)
            self._cell_shading(target, fill)
            if is_header and i == header_rows:
                header_rows = i + 1 if all(c.get("type") == "tableHeader" for c in rows[i].get("content") or []) else header_rows
            first = True
            for child in cell.get("content") or []:
                if first:
                    para = target.paragraphs[0]
                    first = False
                    rtl = (child.get("attrs") or {}).get("dir") == "rtl" or self.rtl_doc
                    if rtl:
                        para._p.get_or_add_pPr().append(_el("w:bidi"))
                    self._inline(para, child.get("content") or [], rtl)
                    if is_header and not a.get("backgroundColor"):
                        for run in para.runs:
                            run.bold = True
                            run.font.color.rgb = RGBColor.from_string(_hex(tstyle.get("header_color"), "FFFFFF"))
                else:
                    self._blocks(target, [child])
        self._table_common(table, header_rows)

    # --- Blocs -----------------------------------------------------------------------------------------------

    def _note(self, container, text: str) -> None:
        para = container.add_paragraph()
        if self.rtl_doc:
            para._p.get_or_add_pPr().append(_el("w:bidi"))
        run = para.add_run(text)
        run.italic = True
        run.font.size = Pt(8)
        run.font.color.rgb = RGBColor.from_string("6B7280")

    def _title(self, container, text: str) -> None:
        if not text:
            return
        para = container.add_paragraph()
        para.paragraph_format.keep_with_next = True
        if self.rtl_doc:
            para._p.get_or_add_pPr().append(_el("w:bidi"))
        run = para.add_run(text)
        run.bold = True
        run.font.size = Pt(10)

    def _toc(self) -> None:
        """Champ TOC pré-rempli avec les titres (Word recalcule les numéros de page à l'ouverture)."""
        para = self.doc.add_paragraph()
        if self.rtl_doc:
            para._p.get_or_add_pPr().append(_el("w:bidi"))
        run = para.add_run("Sommaire" if self.lang == "fr" else ("الفهرس" if self.lang == "ar" else "Contents"))
        run.bold = True
        run.font.size = Pt(13)
        heads = self.p["headings"] or [{"level": 1, "text": "(Mettre à jour la table des matières : F9)"}]
        first = self.doc.add_paragraph()
        r = first.add_run()
        r._r.append(_el("w:fldChar", w_fldCharType="begin"))
        r2 = first.add_run()
        instr = _el("w:instrText")
        instr.set(qn("xml:space"), "preserve")
        instr.text = ' TOC \\o "1-3" \\h \\z \\u '
        r2._r.append(instr)
        first.add_run()._r.append(_el("w:fldChar", w_fldCharType="separate"))
        for k, h in enumerate(heads):
            para = first if k == 0 else self.doc.add_paragraph()
            para._p.get_or_add_pPr().append(_el("w:ind", w_start=int(6 * 56.7 * (h["level"] - 1))))
            para.paragraph_format.space_after = Pt(2)
            if self.rtl_doc:
                para._p.get_or_add_pPr().append(_el("w:bidi"))
            para.add_run(h["text"])
        self.doc.paragraphs[-1].add_run()._r.append(_el("w:fldChar", w_fldCharType="end"))

    def _heading(self, container, node: Dict[str, Any]) -> None:
        level = min(max(int((node.get("attrs") or {}).get("level") or 1), 1), 3)
        para = self._para(container, {**node, "content": []}, style=f"Heading {level}")
        if self.style.get("heading_numbering"):
            self.heading_no[level - 1] += 1
            for k in range(level, 3):
                self.heading_no[k] = 0
            number = ".".join(str(x) for x in self.heading_no[:level])
            para.add_run(f"{number}{'.' if level == 1 else ''} ")
        rtl = bool(para._p.pPr is not None and para._p.pPr.find(qn("w:bidi")) is not None)
        self._inline(para, node.get("content") or [], rtl)

    def _list(self, container, node: Dict[str, Any], depth: int = 0) -> None:
        ordered = node.get("type") == "orderedList"
        base = "List Number" if ordered else "List Bullet"
        style = base if depth == 0 else f"{base} {min(depth + 1, 3)}"
        num_id = self._restart_numbering(style, (node.get("attrs") or {}).get("start") or 1) if ordered else None
        for item in node.get("content") or []:
            first = True
            for child in item.get("content") or []:
                if child.get("type") in ("bulletList", "orderedList"):
                    self._list(container, child, depth + 1)
                elif first and child.get("type") == "paragraph":
                    para = self._para(container, child, style=style)
                    if num_id:
                        numpr = para._p.get_or_add_pPr().get_or_add_numPr()
                        numpr.get_or_add_ilvl().val = 0
                        numpr.get_or_add_numId().val = num_id
                    first = False
                else:
                    self._blocks(container, [child])

    def _restart_numbering(self, style_name: str, start: int) -> int:
        """Chaque liste numérotée repart de son premier numéro (nouvelle instance de la numérotation du style)."""
        numbering = self.doc.part.numbering_part.element
        style_num = self.doc.styles[style_name].element.xpath(".//w:numPr/w:numId/@w:val")[0]
        abstract = next(n.find(qn("w:abstractNumId")).get(qn("w:val")) for n in numbering.findall(qn("w:num"))
                        if n.get(qn("w:numId")) == style_num)
        new_id = max(int(n.get(qn("w:numId"))) for n in numbering.findall(qn("w:num"))) + 1
        num = parse_xml(f'<w:num {nsdecls("w")} w:numId="{new_id}"><w:abstractNumId w:val="{abstract}"/>'
                        f'<w:lvlOverride w:ilvl="0"><w:startOverride w:val="{int(start)}"/></w:lvlOverride></w:num>')
        numbering.append(num)
        return new_id

    def _columns(self, node: Dict[str, Any]) -> None:
        count = int((node.get("attrs") or {}).get("count") or 2)
        self.doc.add_section(WD_SECTION.CONTINUOUS)
        self._set_cols(self.doc.sections[-2], 1)
        self._blocks(self.doc, node.get("content") or [])
        self.doc.add_section(WD_SECTION.CONTINUOUS)
        self._set_cols(self.doc.sections[-2], count)
        self._set_cols(self.doc.sections[-1], 1)

    @staticmethod
    def _set_cols(section, count: int) -> None:
        sp = section._sectPr
        for old in sp.findall(qn("w:cols")):
            sp.remove(old)
        sp.append(_el("w:cols", w_num=count, w_space=int(8 * 56.7)))

    def _gallery(self, container, data: Dict[str, Any]) -> None:
        self._title(container, data.get("title") or "")
        items = data.get("photos") or []
        if not items:
            self._note(container, "Aucune photo avec consentement pour ce projet et cette période.")
            return
        per_row = int(data.get("per_row") or (self.style.get("photo_grid") or {}).get("per_row") or 2)
        nrows = (len(items) + per_row - 1) // per_row
        table = container.add_table(rows=nrows, cols=per_row)
        width = (self.content_width_mm - 4 * (per_row - 1)) / per_row - 3
        for k, ph in enumerate(items):
            cell = table.cell(k // per_row, k % per_row)
            para = cell.paragraphs[0]
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            para.add_run().add_picture(ph["path"], width=Mm(width))
            self._alt(para, ph["caption"] or "Photo d'activité")
            self.photo_no += 1
            cap = cell.add_paragraph(style="Caption")
            if self.rtl_doc:
                cap._p.get_or_add_pPr().append(_el("w:bidi"))
            label = {"ar": "صورة رقم", "en": "Photo"}.get(self.lang, "Photo n°")
            cap.add_run(f"{label} {self.photo_no} : ").bold = True
            cap.add_run(ph["caption"] or "Légende à saisir")
            if ph["credit"]:
                cr = cap.add_run(f" — © {ph['credit']}")
                cr.font.color.rgb = RGBColor.from_string("6B7280")
        tbl = table._tbl
        borders = _el("w:tblBorders")
        for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
            borders.append(_el(f"w:{side}", w_val="nil"))
        tbl.tblPr.append(borders)
        for row in table.rows:
            row._tr.get_or_add_trPr().append(_el("w:cantSplit"))

    def _blocks(self, container, nodes: List[Dict[str, Any]]) -> None:
        colors = self.style.get("colors") or {}
        for node in nodes:
            t = node.get("type")
            if t == "paragraph":
                self._para(container, node)
            elif t == "heading":
                self._heading(container, node)
            elif t in ("bulletList", "orderedList"):
                self._list(container, node)
            elif t == "blockquote":
                for child in node.get("content") or []:
                    self._para(container, child, style="Quote") if child.get("type") == "paragraph" else self._blocks(container, [child])
            elif t == "codeBlock":
                para = container.add_paragraph()
                text = "".join(c.get("text", "") for c in node.get("content") or [])
                for k, line in enumerate(text.split("\n")):
                    if k:
                        para.add_run().add_break()
                    run = para.add_run(line)
                    run.font.name = "Consolas"
                    run.font.size = Pt(9)
            elif t == "horizontalRule":
                para = container.add_paragraph()
                pbdr = _el("w:pBdr")
                pbdr.append(_el("w:bottom", w_val="single", w_sz=6, w_space=1, w_color="CBD5E1"))
                para._p.get_or_add_pPr().append(pbdr)
            elif t == "image":
                para = container.add_paragraph()
                para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                self._image_run(para, node.get("attrs") or {})
            elif t == "table":
                self._editor_table(container, node)
                container.add_paragraph().paragraph_format.space_after = Pt(0)
            elif t == "pageBreak":
                container.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
            elif t == "tableOfContents" and container is self.doc:
                self._toc()
            elif t == "columns" and container is self.doc:
                self._columns(node)
            elif t == "columns":
                self._blocks(container, node.get("content") or [])
            elif t == "x-table":
                self._generic_table(container, node["data"])
            elif t == "x-bars":
                d = node["data"]
                self._title(container, d.get("title") or "")
                png = graphics.bars_png(d.get("series") or [], colors, d.get("unit") or "", d.get("legend"), self.rtl_doc)
                if png:
                    self._picture_bytes(container, png, min(self.content_width_mm, 165))
                else:
                    self._note(container, "Aucune donnée à représenter.")
            elif t == "x-pies":
                for pie in node["data"].get("pies") or []:
                    self._title(container, pie["title"])
                    png = graphics.pie_png(pie["slices"], colors)
                    if not png:
                        self._note(container, f"{pie['title']} : aucune donnée.")
                        continue
                    self._picture_bytes(container, png, 45)
                    legend = graphics.pie_legend(pie["slices"])
                    pal = graphics.palette(colors)
                    table = container.add_table(rows=len(legend), cols=4)
                    for i, (label, value, share) in enumerate(legend):
                        self._cell_shading(table.cell(i, 0), pal[i % len(pal)].lstrip("#"))
                        self._cell_text(table.cell(i, 1), label, size=8.5)
                        self._cell_text(table.cell(i, 2), value, align="end", size=8.5)
                        self._cell_text(table.cell(i, 3), share, align="end", size=8.5)
                    self._widths(table, [5, 80, 40, 20], 145)
                    self._table_common(table, 0)
            elif t == "x-gallery":
                self._gallery(container, node["data"])
            elif t == "x-note":
                self._note(container, node.get("text") or "")

    # --- En-têtes et pieds de page ----------------------------------------------------------------------------

    def _fill(self, text: str) -> str:
        out = str(text or "")
        for k, v in self.p["fields"].items():
            out = out.replace("{" + k + "}", str(v))
        return out

    def _hf_paragraph(self, part, left: List, center: List, right: List, size: float = 8.5) -> None:
        """Paragraphe à trois zones (gauche, centre, droite) par taquets de tabulation."""
        para = part.paragraphs[0] if part.paragraphs else part.add_paragraph()
        for r in list(para.runs):
            r._r.getparent().remove(r._r)
        width_tw = int(self.content_width_mm * 56.7)
        ppr = para._p.get_or_add_pPr()
        for old in ppr.findall(qn("w:tabs")):
            ppr.remove(old)
        tabs = _el("w:tabs")
        for pos in (4680, 9360):                            # taquets du style En-tête/Pied de page de Word, neutralisés
            if pos not in (width_tw // 2, width_tw):
                tabs.append(_el("w:tab", w_val="clear", w_pos=pos))
        tabs.append(_el("w:tab", w_val="center", w_pos=width_tw // 2))
        tabs.append(_el("w:tab", w_val="right", w_pos=width_tw))
        ppr.append(tabs)
        for k, zone in enumerate((left, center, right)):
            if k:
                para.add_run("\t")
            for item in zone:
                kind, value = item
                if kind == "text":
                    run = para.add_run(value)
                    run.font.size = Pt(size)
                    run.font.color.rgb = RGBColor.from_string("6B7280")
                elif kind == "logo":
                    path, height = value
                    para.add_run().add_picture(str(path), height=Mm(height))
                elif kind == "pages":
                    for piece in ("Page ", "PAGE", " / ", "NUMPAGES"):
                        if piece in ("PAGE", "NUMPAGES"):
                            self._field(para, piece)
                        else:
                            run = para.add_run(piece)
                            run.font.size = Pt(size)
                            run.font.color.rgb = RGBColor.from_string("6B7280")

    def _headers_footers(self) -> None:
        s = self.style
        h, ft = s.get("header") or {}, s.get("footer") or {}
        logos: Dict[str, Any] = {}
        for logo in s.get("logos") or []:
            path = logo_path(logo, self.tmp)
            if path is not None and logo.get("position") != "cover":
                logos[logo["position"]] = ("logo", (path, float(logo.get("height_mm") or 14)))
        footer_text = " — ".join(self._fill(x) for x in [ft.get("text"), *(s.get("mentions") or [])] if x)
        odd_even = bool(ft.get("odd_even_different"))
        even_text = h.get("even_text") or ""
        first_text = h.get("first_page_text")
        sec = self.doc.sections[0]
        sec.different_first_page_header_footer = True     # comme l'aperçu : la première page a son propre en-tête
        if odd_even or even_text:
            self.doc.settings.odd_and_even_pages_header_footer = True

        def header(part, text):
            zone = lambda pos: [logos[pos]] if pos in logos else []
            center = zone("header-center") + ([("text", self._fill(text))] if text else [])
            self._hf_paragraph(part, zone("header-left"), center, zone("header-right"))

        def footer(part, numbers_at: Optional[str]):
            zone = lambda pos: [logos[pos]] if pos in logos else []
            left, right = zone("footer-left"), zone("footer-right")
            if numbers_at == "left":
                left = left + [("pages", None)]
            elif numbers_at == "right":
                right = right + [("pages", None)]
            self._hf_paragraph(part, left, zone("footer-center") + ([("text", footer_text)] if footer_text else []), right, size=7.5)

        numbers = ft.get("page_numbers", True) is not False
        header(sec.header, h.get("text"))
        footer(sec.footer, "right" if numbers else None)
        header(sec.first_page_header, first_text if first_text is not None else h.get("text"))
        footer(sec.first_page_footer, "right" if numbers and not ft.get("first_page_different") else None)
        if odd_even or even_text:
            header(sec.even_page_header, even_text or h.get("text"))
            footer(sec.even_page_footer, ("left" if odd_even else "right") if numbers else None)
        for later in self.doc.sections[1:]:                 # sections de colonnes : mêmes en-têtes, pas de « première page »
            later.different_first_page_header_footer = False
            for part in (later.header, later.footer, later.even_page_header, later.even_page_footer):
                part.is_linked_to_previous = True

    # --- Rendu -----------------------------------------------------------------------------------------------

    def render(self) -> bytes:
        self._setup()
        body = self.doc.element.body
        for p in list(body.iterchildren(qn("w:p"))):      # le modèle vierge contient un paragraphe vide
            body.remove(p)
        cover = next((l for l in self.style.get("logos") or [] if l.get("position") == "cover"), None)
        if cover:
            path = logo_path(cover, self.tmp)
            if path:
                para = self.doc.add_paragraph()
                para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                para.add_run().add_picture(str(path), height=Mm(float(cover.get("height_mm") or 30)))
        self._blocks(self.doc, self.p["content"])
        if not self.doc.paragraphs:
            self.doc.add_paragraph()
        self._headers_footers()
        self._footnotes_part()
        normalize(self.doc.element)
        for rel in self.doc.part.rels.values():
            if rel.reltype in (RT.HEADER, RT.FOOTER):
                normalize(rel.target_part.element)
        normalize(self.doc.styles.element)
        buf = io.BytesIO()
        self.doc.save(buf)
        return buf.getvalue()


_ORDER = {
    "pPr": "pStyle keepNext keepLines pageBreakBefore framePr widowControl numPr suppressLineNumbers pBdr shd tabs suppressAutoHyphens "
           "kinsoku wordWrap overflowPunct topLinePunct autoSpaceDE autoSpaceDN bidi adjustRightInd snapToGrid spacing ind contextualSpacing "
           "mirrorIndents suppressOverlap jc textDirection textAlignment textboxTightWrap outlineLvl divId cnfStyle rPr sectPr pPrChange",
    "rPr": "rStyle rFonts b bCs i iCs caps smallCaps strike dstrike outline shadow emboss imprint noProof snapToGrid vanish webHidden color "
           "spacing w kern position sz szCs highlight u effect bdr shd fitText vertAlign rtl cs em lang eastAsianLayout specVanish oMath",
    "tblPr": "tblStyle tblpPr tblOverlap bidiVisual tblStyleRowBandSize tblStyleColBandSize tblW jc tblCellSpacing tblInd tblBorders shd "
             "tblLayout tblCellMar tblLook tblCaption tblDescription",
    "trPr": "cnfStyle divId gridBefore gridAfter wBefore wAfter cantSplit trHeight tblHeader tblCellSpacing jc hidden",
    "tcPr": "cnfStyle tcW gridSpan hMerge vMerge tcBorders shd noWrap tcMar textDirection tcFitText vAlign hideMark",
    "sectPr": "headerReference footerReference footnotePr endnotePr type pgSz pgMar paperSrc pgBorders lnNumType pgNumType cols formProt "
              "vAlign noEndnote titlePg textDirection bidi rtlGutter docGrid printerSettings sectPrChange",
}


def normalize(root) -> None:
    """Remet les enfants des propriétés dans l'ordre du schéma OOXML (Word refuse un ordre incorrect) ; un doublon
    d'élément unique garde la dernière valeur."""
    for tag, order in _ORDER.items():
        rank = {qn("w:" + name): i for i, name in enumerate(order.split())}
        repeatable = {qn("w:headerReference"), qn("w:footerReference")}
        for props in root.iter(qn("w:" + tag)):
            children = list(props)
            seen: Dict[str, Any] = {}
            kept = []
            for child in children:
                if child.tag in rank and child.tag not in repeatable:
                    if child.tag in seen:
                        kept.remove(seen[child.tag])
                    seen[child.tag] = child
                kept.append(child)
            for child in children:
                props.remove(child)
            for child in sorted(kept, key=lambda c: rank.get(c.tag, len(rank))):
                props.append(child)


def render(prepared: Dict[str, Any], tmp_dir: Path) -> bytes:
    return DocxWriter(prepared, tmp_dir).render()
