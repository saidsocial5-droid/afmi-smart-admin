"""Rendu HTML imprimable d'un document préparé (même présentation que l'aperçu de l'éditeur, print.js).

Sert à produire le PDF côté serveur (navigateur sans interface), y compris pour l'export par lot où aucun éditeur
n'est ouvert. Les images sont intégrées en data URI : le fichier est autonome, aucune requête réseau n'est faite.
"""
import base64
import mimetypes
from html import escape
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import graphics
from .resolve import fmt_number, image_path, logo_path, split_label

MARK_TAGS = {"bold": "strong", "italic": "em", "underline": "u", "strike": "s", "code": "code", "subscript": "sub", "superscript": "sup"}


def _data_uri(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def _css_str(s: str) -> str:
    return str(s or "").replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


class HtmlWriter:
    def __init__(self, prepared: Dict[str, Any], tmp_dir: Path):
        self.p = prepared
        self.style = prepared["style"]
        self.lang = prepared["language"]
        self.tmp = tmp_dir
        self.notes: List[str] = []
        self.heading_index = 0

    # --- Contenu ---------------------------------------------------------------------------------------------

    def _attrs(self, node: Dict[str, Any]) -> str:
        a = node.get("attrs") or {}
        out = []
        if a.get("dir"):
            out.append(f' dir="{escape(a["dir"])}"')
        if a.get("textAlign") and a["textAlign"] != "left":
            out.append(f' style="text-align:{escape(a["textAlign"])}"')
        return "".join(out)

    def _inline(self, nodes: List[Dict[str, Any]]) -> str:
        out = []
        for n in nodes or []:
            t = n.get("type")
            if t == "text":
                html = escape(n.get("text", ""))
                for m in n.get("marks") or []:
                    mt, a = m.get("type"), m.get("attrs") or {}
                    if mt in MARK_TAGS:
                        html = f"<{MARK_TAGS[mt]}>{html}</{MARK_TAGS[mt]}>"
                    elif mt == "link" and a.get("href"):
                        html = f'<a href="{escape(a["href"])}">{html}</a>'
                    elif mt == "textStyle":
                        css = []
                        if a.get("color"):
                            css.append(f"color:{escape(a['color'])}")
                        if a.get("fontFamily"):
                            css.append(f"font-family:{escape(a['fontFamily'])}")
                        if a.get("fontSize"):
                            css.append(f"font-size:{escape(str(a['fontSize']))}")
                        if css:
                            html = f'<span style="{";".join(css)}">{html}</span>'
                    elif mt == "highlight":
                        html = f'<mark style="background:{escape(a.get("color") or "#FEF08A")}">{html}</mark>'
                out.append(html)
            elif t == "hardBreak":
                out.append("<br/>")
            elif t == "footnote":
                self.notes.append((n.get("attrs") or {}).get("text") or "")
                out.append(f'<sup class="footnote-ref">{len(self.notes)}</sup>')
            elif t == "image":
                out.append(self._image(n.get("attrs") or {}))
            # x-field page/pages : sans objet dans le corps d'un PDF (les numéros sont dans le pied de page)
        return "".join(out)

    def _image(self, a: Dict[str, Any]) -> str:
        path = image_path(a.get("src") or "", self.tmp)
        if path is None:
            return f'<em class="block-empty">[Image non disponible{escape(" : " + a["alt"]) if a.get("alt") else ""}]</em>'
        return f'<img src="{_data_uri(path)}" alt="{escape(a.get("alt") or "")}"/>'

    def _cell(self, value: Any, fmt: str) -> str:
        return escape(fmt_number(value, fmt))

    def _generic_table(self, data: Dict[str, Any]) -> str:
        cols, rows, total = data.get("columns") or [], data.get("rows") or [], data.get("total")
        formats = data.get("formats") or ["text"] * len(cols)
        notes = "".join(f'<div class="table-note">{escape(n)}</div>' for n in data.get("notes") or [])
        if not rows:
            return f'<div class="block-empty">Aucune donnée.</div>{notes}'
        num = lambda j: ' class="num"' if j < len(formats) and formats[j] != "text" else ""
        head = "".join(f"<th{num(j)}>{escape(str(c))}</th>" for j, c in enumerate(cols))
        body = []
        for r in rows:
            label, indent, bold = split_label(r[0])
            cells = [f'<td><span style="padding-inline-start:{indent * 2}mm;{"font-weight:700" if bold else ""}">{escape(label)}</span></td>']
            cells += [f"<td{num(j)}>{self._cell(v, formats[j] if j < len(formats) else 'text')}</td>" for j, v in enumerate(r) if j]
            body.append(f'<tr{" class=subtotal" if bold else ""}>{"".join(cells)}</tr>')
        if total:
            cells = [f"<td{num(j) if j else ''}>{escape(str(v)) if j == 0 else self._cell(v, formats[j])}</td>" for j, v in enumerate(total)]
            body.append(f'<tr class="total">{"".join(cells)}</tr>')
        return f'<table class="data-table"><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table>{notes}'

    def _editor_table(self, node: Dict[str, Any]) -> str:
        rows = []
        for row in node.get("content") or []:
            cells = []
            for cell in row.get("content") or []:
                a = cell.get("attrs") or {}
                tag = "th" if cell.get("type") == "tableHeader" else "td"
                span = "".join(f' {k}="{int(a[k])}"' for k in ("colspan", "rowspan") if a.get(k) and int(a[k]) > 1)
                bg = f' style="background:{escape(a["backgroundColor"])}"' if a.get("backgroundColor") else ""
                cells.append(f"<{tag}{span}{bg}>{self._blocks(cell.get('content') or [])}</{tag}>")
            rows.append(f"<tr>{''.join(cells)}</tr>")
        return f"<table>{''.join(rows)}</table>"

    def _gallery(self, data: Dict[str, Any]) -> str:
        items = data.get("photos") or []
        title = f'<div class="chart-title">{escape(data["title"])}</div>' if data.get("title") else ""
        if not items:
            return f'{title}<div class="block-empty">Aucune photo avec consentement pour ce projet et cette période.</div>'
        per_row = int(data.get("per_row") or (self.style.get("photo_grid") or {}).get("per_row") or 2)
        label = {"ar": "صورة رقم", "en": "Photo"}.get(self.lang, "Photo n°")
        figs = []
        for ph in items:
            credit = f'<span class="photo-credit"> — © {escape(ph["credit"])}</span>' if ph["credit"] else ""
            figs.append(f'<figure class="photo-figure"><img src="{_data_uri(Path(ph["path"]))}" alt="{escape(ph["caption"] or "Photo")}"/>'
                        f'<figcaption><span class="photo-num" data-label="{escape(label)}"></span>{escape(ph["caption"] or "Légende à saisir")}{credit}</figcaption></figure>')
        return f'{title}<div class="photo-grid" style="grid-template-columns:repeat({per_row}, 1fr)">{"".join(figs)}</div>'

    def _pies(self, data: Dict[str, Any]) -> str:
        colors = self.style.get("colors") or {}
        pal = graphics.palette(colors)
        out = []
        for pie in data.get("pies") or []:
            svg = graphics.pie_svg(pie["slices"], colors)
            if not svg:
                out.append(f'<div class="block-empty">{escape(pie["title"])} : aucune donnée.</div>')
                continue
            legend = "".join(f'<tr><td><span class="pie-swatch" style="background:{pal[i % len(pal)]}"></span></td><td>{escape(l)}</td>'
                             f'<td class="num">{escape(v)}</td><td class="num">{escape(s)}</td></tr>'
                             for i, (l, v, s) in enumerate(graphics.pie_legend(pie["slices"])))
            out.append(f'<figure class="pie-figure"><figcaption class="chart-title">{escape(pie["title"])}</figcaption>'
                       f'<div class="pie-row">{svg}<table class="pie-legend"><tbody>{legend}</tbody></table></div></figure>')
        return f'<div class="pies">{"".join(out)}</div>'

    def _toc(self) -> str:
        title = {"ar": "الفهرس", "en": "Contents"}.get(self.lang, "Sommaire")
        items = "".join(f'<li class="toc-l{h["level"]}"><a href="#h{i}">{escape(h["text"])}</a></li>' for i, h in enumerate(self.p["headings"]))
        return f'<nav class="toc"><div class="toc-title">{title}</div><ul class="toc-list">{items}</ul></nav>'

    def _blocks(self, nodes: List[Dict[str, Any]]) -> str:
        colors = self.style.get("colors") or {}
        out = []
        for n in nodes or []:
            t = n.get("type")
            if t == "paragraph":
                out.append(f"<p{self._attrs(n)}>{self._inline(n.get('content')) or '&#8203;'}</p>")
            elif t == "heading":
                level = min(max(int((n.get("attrs") or {}).get("level") or 1), 1), 3)
                out.append(f'<h{level} id="h{self.heading_index}"{self._attrs(n)}>{self._inline(n.get("content"))}</h{level}>')
                self.heading_index += 1
            elif t == "bulletList":
                out.append(f"<ul>{self._blocks(n.get('content'))}</ul>")
            elif t == "orderedList":
                start = (n.get("attrs") or {}).get("start") or 1
                out.append(f'<ol start="{int(start)}">{self._blocks(n.get("content"))}</ol>')
            elif t == "listItem":
                out.append(f"<li>{self._blocks(n.get('content'))}</li>")
            elif t == "blockquote":
                out.append(f"<blockquote>{self._blocks(n.get('content'))}</blockquote>")
            elif t == "codeBlock":
                out.append(f"<pre>{escape(''.join(c.get('text', '') for c in n.get('content') or []))}</pre>")
            elif t == "horizontalRule":
                out.append("<hr/>")
            elif t == "image":
                out.append(f'<p style="text-align:center">{self._image(n.get("attrs") or {})}</p>')
            elif t == "table":
                out.append(self._editor_table(n))
            elif t == "pageBreak":
                out.append('<div class="page-break"></div>')
            elif t == "tableOfContents":
                out.append(self._toc())
            elif t == "columns":
                count = int((n.get("attrs") or {}).get("count") or 2)
                out.append(f'<div class="columns-{count}">{self._blocks(n.get("content"))}</div>')
            elif t == "x-table":
                out.append(self._generic_table(n["data"]))
            elif t == "x-bars":
                d = n["data"]
                title = f'<figcaption class="chart-title">{escape(d["title"])}</figcaption>' if d.get("title") else ""
                out.append(f'<figure class="chart-figure">{title}{graphics.bars_svg(d.get("series") or [], colors, d.get("unit") or "", d.get("legend"))}</figure>')
            elif t == "x-pies":
                out.append(self._pies(n["data"]))
            elif t == "x-gallery":
                out.append(self._gallery(n["data"]))
            elif t == "x-note":
                out.append(f'<div class="block-empty">{escape(n.get("text") or "")}</div>')
        return "".join(out)

    # --- Page ------------------------------------------------------------------------------------------------

    def _fill(self, text: str) -> str:
        out = str(text or "")
        for k, v in self.p["fields"].items():
            out = out.replace("{" + k + "}", str(v))
        return out

    def _margin_boxes(self, variant: str, logos: Dict[str, str]) -> str:
        """Boîtes de marge CSS @page, comme print.js (première page, pages paires, numéros)."""
        h, ft = self.style.get("header") or {}, self.style.get("footer") or {}
        boxes: Dict[str, str] = {}
        if variant == "first":
            text = h.get("first_page_text") if h.get("first_page_text") is not None else h.get("text")
        elif variant == "left":
            text = h.get("even_text") or h.get("text")
        else:
            text = h.get("text")
        if text:
            boxes["top-center"] = f'content: "{_css_str(self._fill(text))}"; font-size: 8.5pt; color: #6B7280;'
        for pos, uri in logos.items():
            box = pos.replace("header", "top").replace("footer", "bottom")
            boxes[box] = f'content: ""; background: url("{uri}") no-repeat center / contain; height: {logos_h(self.style, pos)}mm; width: 45mm;'
        show = ft.get("page_numbers", True) is not False and not (variant == "first" and ft.get("first_page_different"))
        number_box = "bottom-left" if variant == "left" and ft.get("odd_even_different") else "bottom-right"
        boxes.setdefault("bottom-right", "content: none;")
        if variant in ("left", "first"):
            boxes.setdefault("bottom-left", "content: none;")
        if show:
            word = {"ar": "صفحة", "en": "Page"}.get(self.lang, "Page")
            boxes[number_box] = f'content: "{word} " counter(page) " / " counter(pages); font-size: 8.5pt; color: #6B7280;'
        footer = " — ".join(self._fill(x) for x in [ft.get("text"), *(self.style.get("mentions") or [])] if x)
        if footer:
            boxes["bottom-center"] = f'content: "{_css_str(footer)}"; font-size: 7.5pt; color: #6B7280;'
        return "\n".join(f"@{k} {{ {v} }}" for k, v in boxes.items())

    def render(self) -> str:
        s = self.style
        c, f, t = s.get("colors") or {}, s.get("fonts") or {}, s.get("table") or {}
        m = s.get("margins_mm") or {}
        logos: Dict[str, str] = {}
        cover = ""
        for logo in s.get("logos") or []:
            path = logo_path(logo, self.tmp)
            if path is None:
                continue
            if logo.get("position") == "cover":
                cover = f'<p style="text-align:center"><img src="{_data_uri(path)}" style="height:{logo.get("height_mm") or 30}mm"/></p>'
            else:
                logos[logo["position"]] = _data_uri(path)
        body = self._blocks(self.p["content"])
        notes = ""
        if self.notes:
            notes = '<section class="footnotes"><hr/><ol>' + "".join(f"<li>{escape(n)}</li>" for n in self.notes) + "</ol></section>"
        direction = "rtl" if self.lang == "ar" else "ltr"
        numbering = """
.doc-body { counter-reset: h1; } .doc-body h1 { counter-reset: h2; } .doc-body h2 { counter-reset: h3; }
.doc-body h1::before { counter-increment: h1; content: counter(h1) ". "; }
.doc-body h2::before { counter-increment: h2; content: counter(h1) "." counter(h2) " "; }
.doc-body h3::before { counter-increment: h3; content: counter(h1) "." counter(h2) "." counter(h3) " "; }""" if s.get("heading_numbering") else ""
        body_font = _css_str(f.get("body") or "Calibri")
        head_font = _css_str(f.get("headings") or f.get("body") or "Calibri")
        return f"""<!doctype html><html lang="{self.lang}" dir="{direction}"><head><meta charset="utf-8"><title>{escape(self.p['title'])}</title>
<style>
@page {{ size: A4; margin: {m.get('top') or 25}mm {m.get('right') or 20}mm {m.get('bottom') or 22}mm {m.get('left') or 20}mm; {self._margin_boxes('right', logos)} }}
@page :left {{ {self._margin_boxes('left', logos)} }}
@page :first {{ {self._margin_boxes('first', logos)} }}
html, body {{ margin: 0; background: white; }}
.doc-body {{ font-family: "{body_font}", Calibri, Carlito, Arial, "DejaVu Sans", sans-serif; font-size: {f.get('size_pt') or 11}pt; color: {c.get('text') or '#1F2937'}; line-height: 1.45; }}
.doc-body h1, .doc-body h2, .doc-body h3 {{ font-family: "{head_font}", Calibri, Carlito, Arial, sans-serif; color: {c.get('primary') or '#1B4332'}; break-after: avoid; }}
.doc-body h1 {{ font-size: 18pt; margin: 14pt 0 8pt; }} .doc-body h2 {{ font-size: 14pt; margin: 12pt 0 6pt; }} .doc-body h3 {{ font-size: 12pt; margin: 10pt 0 4pt; }}
.doc-body p {{ margin: 0 0 6pt; }}
.doc-body table {{ border-collapse: collapse; width: 100%; margin: 6pt 0; font-size: 9.5pt; }}
.doc-body td, .doc-body th {{ padding: 3pt 5pt; vertical-align: top; border: 1px solid {t.get('border_color') or '#CBD5E1'}; }}
.doc-body th, .doc-body .data-table thead tr {{ background: {t.get('header_bg') or '#1B4332'}; color: {t.get('header_color') or '#FFFFFF'}; }}
.doc-body thead {{ display: table-header-group; }} .doc-body tr {{ break-inside: avoid; }}
.doc-body .data-table tbody tr:nth-child(even) {{ background: {t.get('stripe') or '#F8F9FA'}; }}
.doc-body .data-table .subtotal td {{ background: #f1f5f9; }}
.doc-body .num {{ text-align: end; white-space: nowrap; }} .doc-body .total {{ font-weight: bold; }}
.doc-body .table-note {{ font-size: 8pt; color: #6b7280; font-style: italic; }}
.doc-body .page-break {{ break-after: page; height: 0; }}
.doc-body .columns-2 {{ column-count: 2; column-gap: 8mm; }} .doc-body .columns-3 {{ column-count: 3; column-gap: 6mm; }}
.doc-body img {{ max-width: 100%; }}
.doc-body blockquote {{ border-inline-start: 3px solid {c.get('secondary') or '#D4A373'}; margin: 6pt 0; padding-inline-start: 4mm; color: #374151; }}
.doc-body .photo-grid {{ display: grid; gap: 4mm; }}
.doc-body .photo-figure {{ margin: 0; break-inside: avoid; }}
.doc-body .photo-figure img {{ width: 100%; height: 55mm; object-fit: cover; }}
.doc-body .photo-figure figcaption {{ font-size: 8.5pt; color: #374151; margin-top: 1mm; }}
.doc-body {{ counter-reset: photo; }}
.doc-body .photo-num::before {{ counter-increment: photo; content: attr(data-label) " " counter(photo) " : "; font-weight: bold; }}
.doc-body .photo-credit {{ color: #6B7280; }}
.doc-body .toc-title {{ font-weight: bold; font-size: 13pt; margin-bottom: 4pt; }}
.doc-body .toc-list {{ list-style: none; padding: 0; }} .doc-body .toc-list a {{ color: inherit; text-decoration: none; }}
.doc-body .toc-l2 {{ padding-inline-start: 6mm; }} .doc-body .toc-l3 {{ padding-inline-start: 12mm; }}
.doc-body .bar-chart {{ width: 100%; max-height: 110mm; }}
.doc-body .chart-title {{ font-weight: bold; font-size: 10pt; }}
.doc-body .chart-figure, .doc-body .pie-figure {{ margin: 4pt 0; break-inside: avoid; }}
.doc-body .block-empty {{ color: #6B7280; font-style: italic; }}
.doc-body .pies {{ display: grid; grid-template-columns: 1fr 1fr; gap: 6mm; }}
.doc-body .pie-row {{ display: flex; gap: 4mm; align-items: center; }} .doc-body .pie-svg {{ width: 38mm; height: 38mm; flex: none; }}
.doc-body .pie-legend {{ font-size: 8pt; width: auto; }} .doc-body .pie-legend td {{ padding: 1px 3px; border: 0; }}
.doc-body .pie-swatch {{ display: inline-block; width: 9px; height: 9px; }}
.doc-body sup.footnote-ref {{ font-size: 7pt; }}
.footnotes {{ font-size: 8.5pt; margin-top: 10mm; }}
{numbering}
</style></head><body><main class="doc-body">{cover}{body}{notes}</main></body></html>"""


def logos_h(style: Dict[str, Any], position: str) -> float:
    for logo in style.get("logos") or []:
        if logo.get("position") == position:
            return float(logo.get("height_mm") or 14)
    return 14.0


def render(prepared: Dict[str, Any], tmp_dir: Path) -> str:
    return HtmlWriter(prepared, tmp_dir).render()
