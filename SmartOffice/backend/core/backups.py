"""Sauvegardes depuis les paramètres (Lot 7), compatibles avec BackupService (.NET) : même dossier, même nommage
(afmi_AAAAMMJJ_HHMMSS_motif.db), copie cohérente par l'API de sauvegarde SQLite.

La restauration n'est jamais faite à chaud : elle est programmée (fichier restore.pending à côté de la base) et
appliquée par l'application de bureau à son prochain démarrage, après une sauvegarde de sécurité.
"""
import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.core import unified_db

PREFIX = "afmi_"
PENDING = "restore.pending"
_NAME = re.compile(r"^afmi_(\d{8}_\d{6})_([a-z_]+?)(?:_\d+)?\.db$")


class BackupError(ValueError):
    pass


def _db() -> Path:
    path = unified_db.database_path()
    if path is None or not path.exists():
        raise BackupError("Base introuvable.")
    return path


def folder() -> Path:
    configured = unified_db.get_setting("backup.folder", "") or ""
    return Path(configured).resolve() if configured else _db().parent / "backups"


def list_backups() -> List[Dict[str, Any]]:
    d = folder()
    out = []
    if d.exists():
        for f in d.glob(f"{PREFIX}*.db"):
            m = _NAME.match(f.name)
            created = datetime.strptime(m.group(1), "%Y%m%d_%H%M%S") if m else datetime.fromtimestamp(f.stat().st_mtime)
            out.append({"name": f.name, "created_at": created.isoformat(timespec="seconds"), "size": f.stat().st_size,
                        "reason": m.group(2) if m else ""})
    return sorted(out, key=lambda b: (b["created_at"], b["name"]), reverse=True)


def create(reason: str = "manuel") -> Dict[str, Any]:
    d = folder()
    d.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = d / f"{PREFIX}{stamp}_{reason}.db"
    k = 2
    while target.exists():
        target = d / f"{PREFIX}{stamp}_{reason}_{k}.db"
        k += 1
    src = sqlite3.connect(f"file:{_db()}?mode=ro", uri=True)
    dst = sqlite3.connect(str(target))
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    keep = int(unified_db.get_setting("backup.retention", 30) or 30)
    removed = 0
    for old in [b for b in list_backups() if b["reason"] in ("auto", "manuel")][keep:]:
        (d / old["name"]).unlink(missing_ok=True)
        removed += 1
    with unified_db.connect() as conn:
        unified_db.append_audit(conn, "Backup", target.name, unified_db.ACTION_CREATE, {"folder": str(d), "removed": removed})
    return {"name": target.name, "folder": str(d), "removed": removed}


def _resolve(name: str) -> Path:
    if not _NAME.match(name or ""):
        raise BackupError("Nom de sauvegarde invalide.")
    path = (folder() / name).resolve()
    if path.parent != folder().resolve() or not path.exists():
        raise BackupError("Sauvegarde introuvable dans le dossier des sauvegardes.")
    return path


def schedule_restore(name: str) -> Dict[str, Any]:
    path = _resolve(name)
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise BackupError("Cette sauvegarde est endommagée.")
    finally:
        conn.close()
    flag = _db().parent / PENDING
    flag.write_text(json.dumps({"path": str(path), "requested_by": unified_db.current_user(),
                                "requested_at": datetime.now().isoformat(timespec="seconds")}), encoding="utf-8")
    with unified_db.connect() as c:
        unified_db.append_audit(c, "Backup", name, "Restauration programmée", {"path": str(path)})
    return pending() or {}


def pending() -> Optional[Dict[str, Any]]:
    flag = _db().parent / PENDING
    if not flag.exists():
        return None
    try:
        data = json.loads(flag.read_text(encoding="utf-8"))
    except ValueError:
        return None
    return {"name": Path(data.get("path", "")).name, "requested_by": data.get("requested_by"), "requested_at": data.get("requested_at")}


def cancel_restore() -> None:
    flag = _db().parent / PENDING
    if flag.exists():
        flag.unlink()
        with unified_db.connect() as c:
            unified_db.append_audit(c, "Backup", "restore.pending", "Restauration annulée", {})
