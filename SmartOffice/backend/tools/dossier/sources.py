"""Lecture des pièces d'un dossier de projet en texte « mis en page » (colonnes conservées) et en tableaux.

Les tableaux des bailleurs (budget, cadre logique, calendrier par trimestre) se lisent par la position des colonnes :
le texte de chaque page PDF est donc reconstruit à partir des mots et de leur abscisse, comme « pdftotext -layout ».
Les classeurs Excel gardent leurs cellules (lignes et colonnes) en plus du texte.
"""
import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional, Tuple

try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover
    import fitz

SUPPORTED = {".pdf", ".docx", ".xlsx", ".xlsm", ".txt", ".md", ".csv", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}
IMAGES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}


@dataclass
class Sheet:
    name: str
    rows: List[List[Any]]


@dataclass
class Source:
    name: str
    kind: str                                   # pdf, docx, xlsx, texte
    pages: List[Tuple[int, str]] = field(default_factory=list)
    sheets: List[Sheet] = field(default_factory=list)
    engine: str = ""

    @property
    def text(self) -> str:
        return "\n".join(t for _, t in self.pages)

    def page_of(self, offset: int) -> int:
        """Numéro de page d'une position dans self.text."""
        pos = 0
        for no, t in self.pages:
            pos += len(t) + 1
            if offset < pos:
                return no
        return self.pages[-1][0] if self.pages else 1


def _layout_page(page) -> str:
    """Texte d'une page avec l'alignement des colonnes (un caractère ≈ la largeur moyenne d'un caractère de la page)."""
    return layout_words(page.get_text("words"))          # x0, y0, x1, y1, mot, …


def layout_words(words) -> str:
    """Reconstruit un texte « mis en page » (colonnes conservées) à partir de mots positionnés (PDF ou OCR)."""
    words = [w for w in words if str(w[4]).strip()]
    if not words:
        return ""
    widths = [(w[2] - w[0]) / max(1, len(w[4])) for w in words if w[4].strip()]
    cw = sorted(widths)[len(widths) // 2] if widths else 5.0
    cw = max(cw * 0.92, 2.0)
    heights = sorted(w[3] - w[1] for w in words)
    lh = heights[len(heights) // 2] if heights else 10.0
    words = sorted(words, key=lambda w: ((w[1] + w[3]) / 2, w[0]))
    lines: List[List[Any]] = []
    for w in words:
        yc = (w[1] + w[3]) / 2
        if lines and abs(lines[-1][0] - yc) <= lh * 0.45:
            lines[-1][1].append(w)
        else:
            lines.append([yc, [w]])
    out = []
    for _, ws in lines:
        ws.sort(key=lambda w: w[0])
        s, prev_x1 = "", None
        for w in ws:
            col = int(round(w[0] / cw))
            if prev_x1 is not None and w[0] - prev_x1 < 2.2 * cw:
                s += " "                       # espace entre deux mots d'une même cellule (texte justifié)
            elif len(s) < col:
                s += " " * (col - len(s))      # saut de colonne : on respecte l'abscisse
            elif s:
                s += "   "
            s += w[4]
            prev_x1 = w[2]
        out.append(s.rstrip())
    return "\n".join(out)


def ocr_layout(gray) -> str:
    """Page numérisée : OCR local (Tesseract, français + arabe + anglais) puis texte à colonnes, pour lire les tableaux
    (budgets, calendriers, relevés) comme dans un PDF natif. Aucune IA."""
    from backend.tools.statements.ocr import ocr_image, OcrUnavailable
    from backend.tools.statements.preprocess import preprocess
    img, _ = preprocess(gray)
    try:
        # psm 6 (bloc uniforme) : lit les tableaux ligne à ligne ; mesuré sur un relevé Attijariwafa numérisé :
        # 8 montants et dates sur 8, contre 3 sur 8 en mode automatique (psm 3).
        words = ocr_image(img, languages="fra+ara+eng", psm=6)
    except OcrUnavailable:
        return ""
    return layout_words([(w.x0, w.y0, w.x1, w.y1, w.text) for w in words])


def _ocr_page(page) -> str:
    import numpy as np
    pix = page.get_pixmap(dpi=300, colorspace=fitz.csGRAY)
    gray = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width).copy()
    return ocr_layout(gray)


def read(data: bytes, filename: str) -> Source:
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED:
        raise ValueError(f"Format non pris en charge : {ext or 'inconnu'} (PDF, image, Word .docx, Excel .xlsx, texte).")
    src = Source(name=filename, kind=ext.lstrip("."))
    if ext == ".pdf":
        doc = fitz.open(stream=data, filetype="pdf")
        src.kind, src.engine = "pdf", "pdf-natif"
        for i, page in enumerate(doc):
            text = _layout_page(page)
            if len(text.strip()) < 40:
                text, src.engine = _ocr_page(page), "pdf+ocr"
            src.pages.append((i + 1, text))
        doc.close()
    elif ext == ".docx":
        from docx import Document
        d = Document(io.BytesIO(data))
        parts = [p.text for p in d.paragraphs]
        for t in d.tables:
            rows = [[c.text.strip() for c in r.cells] for r in t.rows]
            src.sheets.append(Sheet(f"Tableau {len(src.sheets) + 1}", rows))
            parts.extend("   ".join(r) for r in rows)
        src.pages, src.engine = [(1, "\n".join(parts))], "docx"
    elif ext in (".xlsx", ".xlsm"):
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(data), data_only=True)
        for i, ws in enumerate(wb.worksheets):
            rows = [list(r) for r in ws.iter_rows(values_only=True)]
            while rows and all(v in (None, "") for v in rows[-1]):
                rows.pop()
            src.sheets.append(Sheet(ws.title, rows))
            lines = ["   ".join(_cell(v) for v in r if v not in (None, "")) for r in rows]
            src.pages.append((i + 1, f"[Feuille {ws.title}]\n" + "\n".join(l for l in lines if l)))
        src.kind, src.engine = "xlsx", "xlsx"
    elif ext in IMAGES:
        from backend.tools.statements.preprocess import load_image
        src.pages, src.kind, src.engine = [(1, ocr_layout(load_image(data)))], "image", "ocr"
    else:
        try:
            txt = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            txt = data.decode("cp1252")
        src.pages, src.kind, src.engine = [(1, txt)], "texte", "texte"
    return src


def _cell(v: Any) -> str:
    if isinstance(v, float):
        return f"{v:.2f}".rstrip("0").rstrip(".") if abs(v - round(v)) > 1e-9 else str(int(round(v)))
    return str(v).strip()


def read_path(path: str, name: Optional[str] = None) -> Source:
    p = Path(path)
    return read(p.read_bytes(), name or p.name)
