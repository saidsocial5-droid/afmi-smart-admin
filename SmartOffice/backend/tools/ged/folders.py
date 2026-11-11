"""Classement des documents (Lot 9) : arborescence Année › Projet › Type, dossiers personnalisés, copie dans les dossiers
locaux du projet (structure « Dossiers Locaux » de l'application de bureau : Année › Trimestre › catégorie).

L'archive de la GED reste la référence (empreinte, index, liens) ; la copie dans les dossiers locaux sert à parcourir
les documents depuis l'explorateur Windows. Elle n'est jamais faite depuis la démonstration.
"""
import os
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.core import unified_db

GENERAL = "Documents Généraux & Conventions"
QUARTERS = ["T1 - Premier Trimestre (Janvier à Mars)", "T2 - Deuxième Trimestre (Avril à Juin)",
            "T3 - Troisième Trimestre (Juillet à Septembre)", "T4 - Quatrième Trimestre (Octobre à Décembre)"]
# Type de document (GED) → sous-dossier du trimestre (mêmes noms que ProjectFolderService côté bureau)
QUARTER_CATEGORY = {
    "Procès-verbal": "Comptes Rendus (CR)", "Liste de présence": "Comptes Rendus (CR)",
    "Rapport narratif": "Rapports d'Avancement", "Rapport final": "Rapports d'Avancement", "Rapport d'évaluation": "Rapports d'Avancement",
    "Rapport financier": "Rapports Financiers", "Facture": "Rapports Financiers",
}
GENERAL_TYPES = {"Convention", "Avenant", "Budget", "Cadre logique", "Termes de référence", "Document de projet", "Contrat", "Étude ou diagnostic"}
_FORBIDDEN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


class FolderError(ValueError):
    pass


def _year(r) -> str:
    return str(r["SignatureDate"] or r["UploadedDate"] or "")[:4] or "Sans date"


# --- Arborescence --------------------------------------------------------------------------------------------------

def tree() -> Dict[str, Any]:
    """Années › projets › types (avec nombres de documents) et dossiers personnalisés."""
    with unified_db.connect() as conn:
        projects = {r["Id"]: dict(id=r["Id"], code=r["Code"], name=r["Name"]) for r in conn.execute("SELECT Id, Code, Name FROM Projects WHERE IsDeleted = 0")}
        docs = conn.execute("SELECT Id, ProjectId, DocType, FolderId, SignatureDate, UploadedDate FROM Documents WHERE IsDeleted = 0").fetchall()
        folders = [dict(id=f["Id"], parent_id=f["ParentId"], project_id=f["ProjectId"], year=f["Year"], name=f["Name"])
                   for f in conn.execute("SELECT * FROM DocumentFolders WHERE IsDeleted = 0 ORDER BY Name")]
    counts: Dict[str, Dict[int, Dict[str, int]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    folder_counts: Dict[int, int] = defaultdict(int)
    for d in docs:
        counts[_year(d)][d["ProjectId"]][d["DocType"] or "Autre"] += 1
        if d["FolderId"]:
            folder_counts[d["FolderId"]] += 1
    years = []
    for year in sorted(counts, reverse=True):
        plist = []
        for pid, types in sorted(counts[year].items(), key=lambda kv: projects.get(kv[0], {}).get("code", "")):
            p = projects.get(pid, {"id": pid, "code": "?", "name": "Projet supprimé"})
            custom = [{**f, "count": folder_counts[f["id"]]} for f in folders if f["project_id"] == pid and str(f["year"] or "") in (year, "")]
            plist.append({**p, "count": sum(types.values()), "types": [{"name": t, "count": n} for t, n in sorted(types.items())], "folders": custom})
        years.append({"year": year, "count": sum(p["count"] for p in plist), "projects": plist})
    # Dossiers personnalisés encore vides : visibles sous leur année (ou l'année en cours)
    return {"years": years, "folders": [{**f, "count": folder_counts[f["id"]]} for f in folders]}


def documents(year: Optional[str] = None, project_id: Optional[int] = None, doc_type: Optional[str] = None,
              folder_id: Optional[int] = None) -> List[Dict[str, Any]]:
    from . import service
    out = []
    for d in service.list_documents(project_id):
        with unified_db.connect() as conn:
            r = conn.execute("SELECT FolderId, SignatureDate, UploadedDate FROM Documents WHERE Id = ?", (d["id"],)).fetchone()
        if year and _year(r) != str(year):
            continue
        if doc_type and d["doc_type"] != doc_type:
            continue
        if folder_id and r["FolderId"] != folder_id:
            continue
        out.append({**d, "folder_id": r["FolderId"], "year": _year(r)})
    return out


def create_folder(data: Dict[str, Any]) -> Dict[str, Any]:
    name = _FORBIDDEN.sub("", (data.get("name") or "").strip())[:150]
    if not name:
        raise FolderError("Nom du dossier obligatoire.")
    with unified_db.connect() as conn:
        if data.get("parent_id") and conn.execute("SELECT 1 FROM DocumentFolders WHERE Id = ? AND IsDeleted = 0", (data["parent_id"],)).fetchone() is None:
            raise FolderError("Dossier parent introuvable.")
        fid = unified_db.insert(conn, "DocumentFolders", "DocumentFolder", {
            "ParentId": data.get("parent_id"), "ProjectId": data.get("project_id"), "Year": data.get("year"), "Name": name, "IsDeleted": 0})
        r = conn.execute("SELECT * FROM DocumentFolders WHERE Id = ?", (fid,)).fetchone()
    return dict(id=r["Id"], parent_id=r["ParentId"], project_id=r["ProjectId"], year=r["Year"], name=r["Name"])


def rename_folder(folder_id: int, name: str) -> None:
    name = _FORBIDDEN.sub("", (name or "").strip())[:150]
    if not name:
        raise FolderError("Nom du dossier obligatoire.")
    with unified_db.connect() as conn:
        unified_db.update(conn, "DocumentFolders", "DocumentFolder", folder_id, {"Name": name})


def delete_folder(folder_id: int) -> None:
    """Suppression logique ; ses documents reviennent dans le classement automatique (rien n'est supprimé)."""
    with unified_db.connect() as conn:
        for d in conn.execute("SELECT Id FROM Documents WHERE FolderId = ?", (folder_id,)).fetchall():
            unified_db.update(conn, "Documents", "ProjectDocument", d["Id"], {"FolderId": None})
        unified_db.soft_delete(conn, "DocumentFolders", "DocumentFolder", folder_id)


def move_document(doc_id: int, folder_id: Optional[int]) -> None:
    with unified_db.connect() as conn:
        if folder_id is not None:
            f = conn.execute("SELECT ProjectId FROM DocumentFolders WHERE Id = ? AND IsDeleted = 0", (folder_id,)).fetchone()
            d = conn.execute("SELECT ProjectId FROM Documents WHERE Id = ?", (doc_id,)).fetchone()
            if f is None or d is None:
                raise FolderError("Dossier ou document introuvable.")
            if f["ProjectId"] and f["ProjectId"] != d["ProjectId"]:
                raise FolderError("Ce dossier appartient à un autre projet.")
        unified_db.update(conn, "Documents", "ProjectDocument", doc_id, {"FolderId": folder_id})


# --- Copie dans les dossiers locaux du projet --------------------------------------------------------------------

def local_root() -> Optional[Path]:
    configured = unified_db.get_setting("ged.local_root", "") or ""
    if configured:
        return Path(configured)
    if sys.platform == "win32":
        return Path.home() / "Documents" / "AFMI_Projets"
    return None


def local_subfolder(doc_type: str, day: str) -> Path:
    """Chemin relatif au dossier du projet, selon la structure créée par « Créer Dossiers » (bureau)."""
    if doc_type in GENERAL_TYPES:
        return Path(GENERAL)
    year, month = (int(day[:4]), int(day[5:7])) if re.match(r"\d{4}-\d{2}", day or "") else (None, None)
    if year is None:
        return Path(GENERAL)
    quarter = Path(f"Année {year}") / QUARTERS[(month - 1) // 3]
    category = QUARTER_CATEGORY.get(doc_type)
    return quarter / category if category else quarter


def mirror_document(doc_id: int) -> Optional[str]:
    """Copie le fichier du document dans le dossier local du projet (créé au besoin). Retourne le chemin copié."""
    if os.getenv("AFMI_DEMO") == "1" or not unified_db.get_setting("ged.mirror_local", True):
        return None
    with unified_db.connect() as conn:
        d = conn.execute("SELECT d.*, p.Code, p.Name, p.LocalFolderPath FROM Documents d JOIN Projects p ON p.Id = d.ProjectId WHERE d.Id = ?",
                         (doc_id,)).fetchone()
        if d is None or not d["FilePath"] or not Path(d["FilePath"]).is_file():
            return None
        root = Path(d["LocalFolderPath"]) if d["LocalFolderPath"] else None
        if root is None:
            base = local_root()
            if base is None:
                return None
            root = base / _FORBIDDEN.sub("", f"{d['Code']} - {d['Name']}".strip())[:120]
            unified_db.update(conn, "Projects", "Project", d["ProjectId"], {"LocalFolderPath": str(root)})
    day = str(d["SignatureDate"] or d["UploadedDate"] or "")[:10]
    target_dir = root / local_subfolder(d["DocType"] or "", day)
    target_dir.mkdir(parents=True, exist_ok=True)
    stem = _FORBIDDEN.sub("", d["Title"] or "document").strip()[:100] or "document"
    ext = Path(d["FilePath"]).suffix
    target = target_dir / f"{stem}{ext}"
    if target.exists():
        import hashlib
        if hashlib.sha256(target.read_bytes()).hexdigest() == hashlib.sha256(Path(d["FilePath"]).read_bytes()).hexdigest():
            return str(target)                                   # déjà copié
        k = 2
        while (target_dir / f"{stem} ({k}){ext}").exists():
            k += 1
        target = target_dir / f"{stem} ({k}){ext}"
    shutil.copy2(d["FilePath"], target)
    return str(target)
