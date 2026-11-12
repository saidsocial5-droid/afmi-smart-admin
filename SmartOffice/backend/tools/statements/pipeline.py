"""Point d'entrée : un fichier (PDF natif ou scanné, JPG/PNG, CSV/XLSX) → relevé extrait + images des pages."""
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import numpy as np

from . import ocr, tabular
from .extract import extract
from .model import ExtractedStatement, Word
from .preprocess import load_image, preprocess, rotate, estimate_skew, to_png
from .templates import load

try:
    import pymupdf as fitz
except ImportError:  # anciennes versions de PyMuPDF
    import fitz

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}
NATIVE_MIN_WORDS = 15
DISPLAY_DPI = 150


@dataclass
class PipelineResult:
    statement: ExtractedStatement
    page_images: List[bytes] = field(default_factory=list)   # PNG des pages (redressées) pour l'écran de validation
    sha256: str = ""


def _ocr_page(gray: np.ndarray, page: int, languages: str, mode: str = "gray"):
    binary, angle = preprocess(gray, mode)
    words = ocr.ocr_image(binary, page=page, languages=languages)
    display = rotate(gray, angle)
    scale = display.shape[1] / binary.shape[1]
    for w in words:  # coordonnées ramenées à l'image affichée
        w.x0, w.x1, w.y0, w.y1 = w.x0 * scale, w.x1 * scale, w.y0 * scale, w.y1 * scale
    return words, display, angle


def second_pass_fix(primary: ExtractedStatement, secondary: ExtractedStatement) -> ExtractedStatement:
    """
    L'équilibre des soldes échoue : si une seule substitution de montant issue de la seconde lecture le rétablit,
    elle est appliquée et surlignée (confiance 50) pour vérification ; sinon rien n'est changé.
    """
    if primary.balance_ok() is not False or len(secondary.lines) != len(primary.lines):
        return primary
    gap = primary.closing - primary.opening - primary.movement
    fixes = []
    for i, (a, b) in enumerate(zip(primary.lines, secondary.lines)):
        if a.date != b.date:
            return primary
        for field in ("debit", "credit"):
            va, vb = getattr(a, field), getattr(b, field)
            delta = (vb - va) if field == "credit" else (va - vb)
            if va != vb and delta == gap:
                fixes.append((i, field, vb))
    if len(fixes) != 1:
        return primary
    i, field, value = fixes[0]
    line = primary.lines[i]
    old = getattr(line, field)
    setattr(line, field, value)
    line.confidence[field] = 50.0
    primary.warnings = [w for w in primary.warnings if not w.startswith("Solde initial + mouvements")]
    primary.warnings.append(f"Montant du {line.date} corrigé par une seconde lecture ({old / 100:.2f} → {value / 100:.2f}) : à vérifier.")
    return primary


def process(data: bytes, filename: str, languages: str = "fra") -> PipelineResult:
    ext = Path(filename).suffix.lower()
    templates, columns = load()
    sha = hashlib.sha256(data).hexdigest()

    if ext in (".csv", ".txt", ".xlsx", ".xlsm"):
        return PipelineResult(tabular.read(data, ext), [], sha)

    words: List[Word] = []
    images: List[bytes] = []
    heights = {}
    engines = set()
    scanned_pages = []   # (page, image en niveaux de gris) pour une éventuelle seconde lecture
    native_words: List[Word] = []
    if ext == ".pdf":
        doc = fitz.open(stream=data, filetype="pdf")
        for p, page in enumerate(doc):
            native = page.get_text("words")
            zoom = DISPLAY_DPI / 72
            if len(native) >= NATIVE_MIN_WORDS:
                engines.add("pdf-natif")
                for x0, y0, x1, y1, text, *_ in native:
                    w = Word(text, x0 * zoom, y0 * zoom, x1 * zoom, y1 * zoom, 100.0, p)
                    words.append(w)
                    native_words.append(w)
                pix = page.get_pixmap(dpi=DISPLAY_DPI)
                images.append(pix.tobytes("png"))
                heights[p] = pix.height
            else:
                engines.add("tesseract")
                pix = page.get_pixmap(dpi=300, colorspace=fitz.csGRAY)
                gray = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width).copy()
                page_words, display, _ = _ocr_page(gray, p, languages)
                scanned_pages.append((p, gray))
                words += page_words
                images.append(to_png(display))
                heights[p] = display.shape[0]
        doc.close()
    elif ext in IMAGE_EXT:
        engines.add("tesseract")
        gray = load_image(data)
        scanned_pages.append((0, gray))
        page_words, display, _ = _ocr_page(gray, 0, languages)
        words += page_words
        images.append(to_png(display))
        heights[0] = display.shape[0]
    else:
        raise ValueError(f"Format non pris en charge : {ext or 'inconnu'} (PDF, JPG, PNG, TIFF, CSV, XLSX).")

    statement = extract(words, templates, columns, "+".join(sorted(engines)), heights)
    if scanned_pages and statement.balance_ok() is False:
        alt_words = list(native_words)
        for p, gray in scanned_pages:
            alt_words += _ocr_page(gray, p, languages, mode="binary")[0]
        statement = second_pass_fix(statement, extract(alt_words, templates, columns, statement.engine, heights))
    return PipelineResult(statement, images, sha)


def process_pages(files: List[tuple[bytes, str]], languages: str = "fra") -> PipelineResult:
    """Plusieurs images (photos page par page) d'un même relevé : traitées comme un seul document."""
    templates, columns = load()
    words: List[Word] = []
    images: List[bytes] = []
    heights = {}
    digest = hashlib.sha256()
    for p, (data, _name) in enumerate(files):
        digest.update(data)
        page_words, display, _ = _ocr_page(load_image(data), p, languages)
        words += page_words
        images.append(to_png(display))
        heights[p] = display.shape[0]
    statement = extract(words, templates, columns, "tesseract", heights)
    if statement.balance_ok() is False:
        alt = [w for p, (data, _n) in enumerate(files) for w in _ocr_page(load_image(data), p, languages, mode="binary")[0]]
        statement = second_pass_fix(statement, extract(alt, templates, columns, "tesseract", heights))
    return PipelineResult(statement, images, digest.hexdigest())
