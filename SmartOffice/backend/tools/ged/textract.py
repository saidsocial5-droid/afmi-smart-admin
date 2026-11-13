"""Extraction du texte d'un document, page par page quand c'est possible (PDF natif ou scanné, Word, Excel, texte, image)."""
import io
from pathlib import Path
from typing import List, Tuple

import numpy as np

try:
    import pymupdf as fitz
except ImportError:
    import fitz

SUPPORTED = {".pdf", ".docx", ".xlsx", ".xlsm", ".txt", ".md", ".csv", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}


class ExtractionError(ValueError):
    pass


def _ocr_gray(gray: np.ndarray) -> str:
    """OCR local d'une page numérisée, colonnes des tableaux conservées (voir dossier.sources.layout_words)."""
    from backend.tools.dossier.sources import ocr_layout
    return ocr_layout(gray)


def extract(data: bytes, filename: str) -> Tuple[List[Tuple[int, str]], str]:
    """Retourne [(numéro de page à partir de 1, texte)] et le moteur utilisé."""
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED:
        raise ExtractionError(f"Format non pris en charge pour l'analyse : {ext or 'inconnu'} (PDF, Word .docx, Excel, texte, image).")
    if ext == ".pdf":
        pages, engine = [], "pdf-natif"
        doc = fitz.open(stream=data, filetype="pdf")
        for i, page in enumerate(doc):
            text = page.get_text("text")
            if len(text.strip()) < 40:  # page scannée : OCR
                pix = page.get_pixmap(dpi=300, colorspace=fitz.csGRAY)
                gray = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width).copy()
                text, engine = _ocr_gray(gray), "pdf+ocr"
            pages.append((i + 1, text))
        doc.close()
        return pages, engine
    if ext == ".docx":
        from docx import Document
        d = Document(io.BytesIO(data))
        parts = [p.text for p in d.paragraphs]
        for table in d.tables:
            for row in table.rows:
                parts.append(" | ".join(c.text for c in row.cells))
        return [(1, "\n".join(parts))], "docx"
    if ext in (".xlsx", ".xlsm"):
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        pages = []
        for i, ws in enumerate(wb.worksheets):
            rows = [" | ".join(str(v) for v in row if v is not None) for row in ws.iter_rows(values_only=True)]
            pages.append((i + 1, f"[{ws.title}]\n" + "\n".join(r for r in rows if r)))
        return pages, "xlsx"
    if ext in (".txt", ".md", ".csv"):
        try:
            return [(1, data.decode("utf-8-sig"))], "texte"
        except UnicodeDecodeError:
            return [(1, data.decode("cp1252"))], "texte"
    from backend.tools.statements.preprocess import load_image
    return [(1, _ocr_gray(load_image(data)))], "ocr"
