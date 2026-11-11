"""Façade des exports : un document de l'éditeur, les états financiers, les opérations, un rapprochement,
le dossier annuel complet. Chaque export est tracé dans le journal d'audit (qui, quand, quoi)."""
import hashlib
import io
import json
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pymupdf
from PIL import Image

from backend.core import unified_db
from backend.tools.editor import documents
from backend.tools.ged import service as ged
from backend.tools.reports import generator
from . import docx_writer, naming, pdf as pdf_mod, resolve, xlsx_writer

MIME = {"pdf": "application/pdf", "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "zip": "application/zip"}


def _audit(what: str, details: Dict[str, Any]) -> None:
    if not unified_db.is_available():
        return
    with unified_db.connect() as conn:
        unified_db.append_audit(conn, "Export", what, "Export", details)


def document(doc_id: int, fmt: str, pdfa: bool = False) -> Tuple[bytes, str]:
    if fmt not in ("docx", "pdf"):
        raise ValueError("Format : docx ou pdf.")
    prepared = resolve.prepare(doc_id)
    if fmt == "docx":
        with tempfile.TemporaryDirectory(prefix="afmi_docx_") as tmp:
            data = docx_writer.render(prepared, Path(tmp))
    else:
        data = pdf_mod.to_pdf(prepared, pdfa)
    name = naming.file_name(fmt, "document", lang=prepared["language"], title=prepared["title"])
    _audit(f"EditorDocument:{doc_id}", {"format": fmt, "pdfa": pdfa, "file": name, "sha256": hashlib.sha256(data).hexdigest()})
    return data, name


def statements(year: int, scope_type: str, scope_id: Optional[int], lang: str = "fr") -> Tuple[bytes, str]:
    data = xlsx_writer.financial_workbook(year, scope_type, scope_id, lang)
    name = naming.file_name("xlsx", "statements", year, lang)
    _audit(f"Statements:{year}:{scope_type}:{scope_id or ''}", {"format": "xlsx", "file": name})
    return data, name


def operations(account_id: Optional[int], date_from: Optional[str], date_to: Optional[str]) -> Tuple[bytes, str]:
    data = xlsx_writer.operations_workbook(account_id, date_from, date_to)
    year = int((date_to or date_from or str(datetime.now().year))[:4])
    name = naming.file_name("xlsx", "operations", year)
    _audit(f"Operations:{account_id or 'all'}", {"format": "xlsx", "from": date_from, "to": date_to, "file": name})
    return data, name


def reconciliation(statement_id: int) -> Tuple[bytes, str]:
    data = xlsx_writer.reconciliation_workbook(statement_id)
    name = naming.file_name("xlsx", "reconciliation", title=str(statement_id))
    _audit(f"BankStatement:{statement_id}", {"format": "xlsx", "file": name})
    return data, name


# --- Dossier annuel ------------------------------------------------------------------------------------------

def _annex_pdf(path: Path, work: Path) -> Optional[bytes]:
    """Annexe convertie en PDF pour le document fusionné : PDF tel quel, image sur une page A4, Word/Excel via
    LibreOffice s'il est installé ; sinon None (l'annexe reste jointe au dossier dans son format d'origine)."""
    ext = path.suffix.lower()
    if ext == ".pdf":
        return path.read_bytes()
    if ext in (".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"):
        img = Image.open(path).convert("RGB")
        buf = io.BytesIO()
        img.save(buf, "PDF", resolution=150)
        return buf.getvalue()
    soffice = pdf_mod.engines()["libreoffice"]
    if soffice and ext in (".docx", ".doc", ".odt", ".xlsx", ".xls", ".ods", ".pptx", ".rtf"):
        import shutil
        import subprocess
        src = work / f"annexe{ext}"
        shutil.copy(path, src)
        subprocess.run([soffice, "--headless", "--norestore", f"-env:UserInstallation={(work / 'lo').resolve().as_uri()}",
                        "--convert-to", "pdf", "--outdir", str(work), str(src)], capture_output=True, timeout=240)
        out = work / "annexe.pdf"
        if out.exists():
            data = out.read_bytes()
            out.unlink()
            return data
    return None


async def annual_package(year: int, scope_type: str = "association", scope_id: Optional[int] = None, language: str = "fr",
                               moral_document_id: Optional[int] = None, financial_document_id: Optional[int] = None,
                         annex_ids: Optional[List[int]] = None, formats: Optional[List[str]] = None, pdfa: bool = False) -> Tuple[bytes, str]:
    """Dossier annuel (ZIP) : rapport moral, rapport financier, états financiers Excel, annexes de la GED, et un PDF
    unique « rapport annuel complet » (moral + financier + annexes) avec signets par partie.

    Un rapport non désigné est généré depuis les données (comme l'assistant) : il apparaît alors dans l'éditeur,
    où il reste modifiable."""
    ids: Dict[str, int] = {}
    for kind, given in (("moral", moral_document_id), ("financial", financial_document_id)):
        if given:
            documents.get_document(given)
            ids[kind] = given
        else:
            res = await generator.generate(year, scope_type, scope_id, language, kind)
            if not res.get("document"):
                raise ValueError("Rapport non généré : " + "; ".join(c["message"] for c in res.get("blocking") or []))
            ids[kind] = res["document"]["id"]
    import asyncio
    return await asyncio.to_thread(_build_package, year, scope_type, scope_id, language, ids, annex_ids or [],
                                   formats or ["pdf", "docx", "xlsx"], pdfa, [])


def _build_package(year, scope_type, scope_id, language, ids, annex_ids, formats, pdfa, notes) -> Tuple[bytes, str]:
    files: List[Tuple[str, bytes]] = []
    parts: List[Tuple[str, bytes]] = []
    labels = {"fr": ("Rapport moral", "Rapport financier", "Annexes"), "en": ("Narrative report", "Financial report", "Annexes"),
              "ar": ("التقرير الأدبي", "التقرير المالي", "الملاحق")}[language if language in ("fr", "en", "ar") else "fr"]
    with tempfile.TemporaryDirectory(prefix="afmi_pack_") as tmp:
        work = Path(tmp)
        for (kind, label) in (("moral", labels[0]), ("financial", labels[1])):
            if kind not in ids:
                continue
            prepared = resolve.prepare(ids[kind])
            if "docx" in formats:
                files.append((naming.file_name("docx", kind, year, language), docx_writer.render(prepared, work)))
            pdf_bytes = pdf_mod.to_pdf(prepared, pdfa)        # toujours produit : il entre dans le PDF complet
            if "pdf" in formats:
                files.append((naming.file_name("pdf", kind, year, language), pdf_bytes))
            parts.append((label, pdf_bytes))
        if "xlsx" in formats:
            files.append((naming.file_name("xlsx", "statements", year, language), xlsx_writer.financial_workbook(year, scope_type, scope_id, language)))
        annex_parts: List[Tuple[str, bytes]] = []
        for aid in annex_ids:
            try:
                meta = ged.get(aid)
                path = ged.file_path(aid)
            except Exception as e:
                notes.append(f"Annexe {aid} ignorée : {e}")
                continue
            title = meta.get("title") or path.stem
            files.append((f"Annexes/{naming._slug(title, 80)}{path.suffix.lower()}", path.read_bytes()))
            converted = _annex_pdf(path, work)
            if converted:
                annex_parts.append((title, converted))
            else:
                notes.append(f"Annexe « {title} » jointe au dossier mais non intégrée au PDF complet (format {path.suffix} : installez LibreOffice).")
        # PDF unique : parties + annexes, signets par partie (les signets internes sont conservés en sous-niveau)
        merged = pymupdf.open()
        toc: List[List[Any]] = []
        for label, data in parts:
            src = pymupdf.open(stream=data, filetype="pdf")
            start = merged.page_count
            merged.insert_pdf(src)
            toc.append([1, label, start + 1])
            toc += [[lvl + 1, title, page + start] for lvl, title, page, *_ in src.get_toc()]
        if annex_parts:
            toc.append([1, labels[2], merged.page_count + 1])
            for title, data in annex_parts:
                try:
                    src = pymupdf.open(stream=data, filetype="pdf")
                except Exception:
                    notes.append(f"Annexe « {title} » illisible en PDF.")
                    continue
                toc.append([2, title, merged.page_count + 1])
                merged.insert_pdf(src)
        if merged.page_count:
            merged.set_toc([e for e in toc if e[2] >= 1])
            merged.set_metadata({"title": f"{naming.TYPES['both']} {year}", "author": "AFMI Smart Admin", "creator": "AFMI Smart Admin"})
            files.insert(0, (naming.file_name("pdf", "both", year, language), merged.tobytes(garbage=3, deflate=True)))
        merged.close()
    manifest = [f"Dossier annuel {year} — généré le {datetime.now():%d/%m/%Y %H:%M} par {unified_db.current_user()}", ""]
    manifest += [f"{hashlib.sha256(data).hexdigest()}  {name}" for name, data in files]
    if notes:
        manifest += ["", "Remarques :"] + [f"- {n}" for n in notes]
    if pdfa:
        manifest.append("Les PDF des rapports sont au format PDF/A-2b ; le PDF complet fusionné ne l'est pas.")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files:
            z.writestr(name, data)
        z.writestr("LISEZMOI_empreintes_SHA256.txt", "\n".join(manifest) + "\n")
    name = naming.file_name("zip", "package", year, language)
    _audit(f"AnnualPackage:{year}:{scope_type}:{scope_id or ''}", {"files": [n for n, _ in files], "documents": ids, "annexes": annex_ids})
    return buf.getvalue(), name
