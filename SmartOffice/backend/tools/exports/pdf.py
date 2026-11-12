"""Production des PDF.

Deux moteurs, choisis par le paramètre ``exports.pdf_engine`` (« auto » par défaut) :

- **navigateur** : le HTML imprimable (html_writer) est imprimé par Microsoft Edge (présent sur tout Windows 10/11),
  Chrome ou Chromium, sans interface. Polices intégrées (sous-ensembles), signets tirés des titres, en-têtes et pieds
  de page de la charte. Les notes de bas de page sont regroupées en fin de document (limite des navigateurs) ;
- **LibreOffice** (s'il est installé) : le fichier Word exporté est converti en PDF. Notes en bas de page, signets,
  polices intégrées, et seul moteur proposant le **PDF/A-2b** (archivage).

En « auto » : navigateur, sauf PDF/A demandé (LibreOffice). Aucun moteur n'est téléchargé ni appelé sur Internet.
Après production, le PDF reçoit ses métadonnées (titre, auteur, langue) et, s'il n'en a pas, ses signets.
"""
import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import pymupdf

from backend.core import unified_db


class PdfError(RuntimeError):
    pass


LANG_TAGS = {"fr": "fr-FR", "ar": "ar-MA", "en": "en-GB"}


def _candidates_browser() -> List[str]:
    env = os.getenv("AFMI_PDF_BROWSER")
    out = [env] if env else []
    if platform.system() == "Windows":
        for base in (os.getenv("ProgramFiles(x86)"), os.getenv("ProgramFiles"), os.getenv("LOCALAPPDATA")):
            if base:
                out += [f"{base}\\Microsoft\\Edge\\Application\\msedge.exe", f"{base}\\Google\\Chrome\\Application\\chrome.exe"]
    else:
        out += [str(p) for p in sorted(Path("/opt/pw-browsers").glob("chromium_headless_shell-*/chrome-headless-shell-*/chrome-headless-shell"))]
        out += [str(p) for p in sorted(Path("/opt/pw-browsers").glob("chromium-*/chrome-linux*/chrome"))]
        out += [shutil.which(n) or "" for n in ("chromium", "chromium-browser", "google-chrome", "microsoft-edge", "msedge")]
    return [c for c in out if c and Path(c).is_file()]


def _candidates_soffice() -> List[str]:
    env = os.getenv("AFMI_SOFFICE")
    out = [env] if env else []
    if platform.system() == "Windows":
        for base in (os.getenv("ProgramFiles"), os.getenv("ProgramFiles(x86)")):
            if base:
                out.append(f"{base}\\LibreOffice\\program\\soffice.exe")
    out += [shutil.which("soffice") or "", shutil.which("libreoffice") or ""]
    return [c for c in out if c and Path(c).is_file()]


def engines() -> Dict[str, Optional[str]]:
    """Moteurs détectés sur le poste (affichés dans les paramètres)."""
    b, s = _candidates_browser(), _candidates_soffice()
    return {"browser": b[0] if b else None, "libreoffice": s[0] if s else None}


def _engine(pdfa: bool) -> str:
    choice = unified_db.get_setting("exports.pdf_engine", "auto") if unified_db.is_available() else "auto"
    found = engines()
    if pdfa:
        if not found["libreoffice"]:
            raise PdfError("Le PDF/A nécessite LibreOffice (gratuit), non détecté sur ce poste. Installez-le ou indiquez son "
                           "chemin (variable AFMI_SOFFICE), ou exportez en PDF standard.")
        return "libreoffice"
    if choice == "libreoffice" and found["libreoffice"]:
        return "libreoffice"
    if found["browser"]:
        return "browser"
    if found["libreoffice"]:
        return "libreoffice"
    raise PdfError("Aucun moteur PDF détecté : Microsoft Edge, Chrome/Chromium ou LibreOffice est nécessaire.")


def html_to_pdf(html: str, work: Path) -> bytes:
    browser = engines()["browser"]
    if not browser:
        raise PdfError("Aucun navigateur (Edge, Chrome, Chromium) détecté pour produire le PDF.")
    src, out = work / "document.html", work / "document.pdf"
    src.write_text(html, encoding="utf-8")
    headless = [] if "headless-shell" in Path(browser).name else ["--headless=new"]
    args = [browser, *headless, "--disable-gpu", "--disable-background-networking", "--disable-component-update", "--disable-sync", "--no-first-run", "--no-default-browser-check", "--disable-extensions",
            "--no-pdf-header-footer", "--generate-pdf-document-outline", "--virtual-time-budget=10000",
            f"--user-data-dir={work / 'profile'}", f"--print-to-pdf={out}", src.resolve().as_uri()]
    if platform.system() != "Windows" and os.geteuid() == 0:
        args.insert(1, "--no-sandbox")                    # conteneur de développement exécuté en root
    try:
        subprocess.run(args, capture_output=True, timeout=180, check=False)
    except subprocess.TimeoutExpired as e:
        raise PdfError("Le navigateur n'a pas produit le PDF dans le délai imparti.") from e
    if not out.exists() or out.stat().st_size == 0:
        raise PdfError("Le navigateur n'a pas produit de PDF.")
    return out.read_bytes()


def docx_to_pdf(docx: bytes, work: Path, pdfa: bool = False) -> bytes:
    soffice = engines()["libreoffice"]
    if not soffice:
        raise PdfError("LibreOffice n'est pas installé sur ce poste.")
    src = work / "document.docx"
    src.write_bytes(docx)
    options = '{"ExportBookmarks":{"type":"boolean","value":"true"},"UseTaggedPDF":{"type":"boolean","value":"true"}'
    if pdfa:
        options += ',"SelectPdfVersion":{"type":"long","value":"2"}'
    options += "}"
    args = [soffice, "--headless", "--norestore", f"-env:UserInstallation={(work / 'lo-profile').resolve().as_uri()}",
            "--convert-to", f"pdf:writer_pdf_Export:{options}", "--outdir", str(work), str(src)]
    try:
        subprocess.run(args, capture_output=True, timeout=240, check=False)
    except subprocess.TimeoutExpired as e:
        raise PdfError("LibreOffice n'a pas produit le PDF dans le délai imparti.") from e
    out = work / "document.pdf"
    if not out.exists() or out.stat().st_size == 0:
        raise PdfError("LibreOffice n'a pas produit de PDF.")
    return out.read_bytes()


def finalize(pdf: bytes, title: str, language: str, headings: List[Dict[str, Any]], author: str, pdfa: bool = False) -> bytes:
    """Métadonnées et signets. Un PDF/A n'est pas réécrit (sa conformité vient de LibreOffice)."""
    if pdfa:
        return pdf
    doc = pymupdf.open(stream=pdf, filetype="pdf")
    meta = doc.metadata or {}
    meta.update({"title": title, "author": author, "subject": title, "creator": "AFMI Smart Admin", "producer": meta.get("producer") or ""})
    doc.set_metadata(meta)
    doc.xref_set_key(doc.pdf_catalog(), "Lang", pymupdf.get_pdf_str(LANG_TAGS.get(language, "fr-FR")))
    existing = doc.get_toc()
    if existing and len(existing) == len([h for h in headings if h["text"].strip()]):
        # signets du navigateur : pages exactes, mais le texte arabe peut y être stocké dans l'ordre visuel ;
        # on reprend le texte des titres du document (ordre logique)
        texts = [h["text"] for h in headings if h["text"].strip()]
        doc.set_toc([[lvl, texts[i], page] for i, (lvl, _t, page, *_rest) in enumerate(existing)])
    elif not existing and headings:
        toc, page = [], 0
        last_level = 0
        for h in headings:
            needle = " ".join(h["text"].split())[:50]
            if not needle:
                continue
            found = None
            for p in range(page, doc.page_count):
                if doc[p].search_for(needle):
                    found = p
                    break
            if found is None:
                continue
            page = found
            level = min(h["level"], last_level + 1)        # un signet ne peut pas sauter un niveau
            toc.append([level, h["text"], found + 1])
            last_level = level
        if toc:
            doc.set_toc(toc)
    out = doc.tobytes(garbage=3, deflate=True)
    doc.close()
    return out


def to_pdf(prepared: Dict[str, Any], pdfa: bool = False) -> bytes:
    """PDF d'un document préparé (resolve.prepare)."""
    from . import docx_writer, html_writer
    with tempfile.TemporaryDirectory(prefix="afmi_pdf_") as tmp:
        work = Path(tmp)
        engine = _engine(pdfa)
        if engine == "libreoffice":
            pdf = docx_to_pdf(docx_writer.render(prepared, work), work, pdfa)
        else:
            pdf = html_to_pdf(html_writer.render(prepared, work), work)
    return finalize(pdf, prepared["title"], prepared["language"], prepared["headings"],
                    prepared["fields"].get("association") or "AFMI", pdfa)
