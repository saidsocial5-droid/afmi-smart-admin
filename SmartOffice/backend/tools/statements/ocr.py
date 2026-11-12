"""OCR local par Tesseract (exécutable, sortie TSV avec boîtes et confiance par mot)."""
import csv
import io
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

import numpy as np

from .model import Word
from .preprocess import to_png


class OcrUnavailable(RuntimeError):
    pass


def find_tesseract() -> Optional[str]:
    """AFMI_TESSERACT, puis Tesseract livré avec l'application, puis le PATH."""
    candidates = [os.getenv("AFMI_TESSERACT", "")]
    base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[3]
    candidates += [str(base / "tesseract" / "tesseract.exe"), str(base / "tesseract" / "tesseract")]
    if sys.platform == "win32":
        candidates.append(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    for c in candidates:
        if c and Path(c).is_file():
            return c
    return shutil.which("tesseract")


def available_languages(binary: str) -> List[str]:
    try:
        out = subprocess.run([binary, "--list-langs"], capture_output=True, text=True, timeout=20).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    return [l.strip() for l in out.splitlines()[1:] if l.strip()]


def ocr_image(img: np.ndarray, page: int = 0, languages: str = "fra", psm: int = 6) -> List[Word]:
    binary = find_tesseract()
    if binary is None:
        raise OcrUnavailable("OCR local indisponible : Tesseract n'est pas installé (voir docs/v2/ARCHITECTURE.md).")
    langs = [l for l in languages.split("+") if l in available_languages(binary)] or ["eng"]
    with tempfile.TemporaryDirectory(prefix="afmi_ocr_") as tmp:
        src = Path(tmp) / "page.png"
        src.write_bytes(to_png(img))
        proc = subprocess.run(
            [binary, str(src), "stdout", "-l", "+".join(langs), "--psm", str(psm), "-c", "preserve_interword_spaces=1", "tsv"],
            capture_output=True, timeout=180,
        )
    if proc.returncode != 0:
        raise OcrUnavailable("Échec de Tesseract : " + proc.stderr.decode("utf-8", "replace")[:300])
    words: List[Word] = []
    reader = csv.DictReader(io.StringIO(proc.stdout.decode("utf-8", "replace")), delimiter="\t", quoting=csv.QUOTE_NONE)
    for row in reader:
        text = (row.get("text") or "").strip()
        if not text or row.get("level") != "5":
            continue
        try:
            x, y, w, h, conf = (float(row[k]) for k in ("left", "top", "width", "height", "conf"))
        except (TypeError, ValueError):
            continue
        words.append(Word(text, x, y, x + w, y + h, max(conf, 0.0), page))
    return words
