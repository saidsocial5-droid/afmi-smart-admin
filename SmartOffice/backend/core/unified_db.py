"""Accès du backend à la base unique du poste (database.db du Desktop).

Le schéma appartient aux migrations EF Core (Core/Data/Migrations) : ce module ne crée ni ne modifie
aucune table. Toute écriture est journalisée dans AuditEntries, dans la même transaction, avec la même
chaîne d'empreintes que AppDbContext (voir compute_audit_hash).
"""
import getpass
import hashlib
import json
import os
import platform
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

from backend.core import dpapi

DESKTOP_DB_ENV = "AFMI_DESKTOP_DB"
REQUIRED_MIGRATION_SUFFIX = "_DocumentManagement"   # dernière migration dont dépend le backend (Lot 6)

ACTION_CREATE = "Création"
ACTION_UPDATE = "Modification"
ACTION_DELETE = "Suppression"


class UnifiedDbUnavailable(RuntimeError):
    pass


def database_path() -> Optional[Path]:
    env = os.getenv(DESKTOP_DB_ENV, "").strip()
    if env:
        return Path(env)
    local = os.getenv("LOCALAPPDATA")
    if local:
        candidate = Path(local) / "AFMIGestionProjet" / "database.db"
        if candidate.exists():
            return candidate
    return None


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    """Connexion transactionnelle : validée en sortie normale, annulée sur exception."""
    path = database_path()
    if path is None or not path.exists():
        raise UnifiedDbUnavailable("Base AFMI introuvable : lancez l'application de bureau au moins une fois.")
    conn = sqlite3.connect(str(path), timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        applied = {r[0] for r in conn.execute("SELECT MigrationId FROM __EFMigrationsHistory")}
        if not any(m.endswith(REQUIRED_MIGRATION_SUFFIX) for m in applied):
            raise UnifiedDbUnavailable("Base AFMI non migrée : ouvrez l'application de bureau pour la mettre à jour.")
        yield conn
        conn.commit()
    except sqlite3.OperationalError as e:
        conn.rollback()
        if "no such table: __EFMigrationsHistory" in str(e):
            raise UnifiedDbUnavailable("Base AFMI non migrée.") from e
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def is_available() -> bool:
    try:
        with connect():
            return True
    except (UnifiedDbUnavailable, sqlite3.Error):
        return False


# --- Journal d'audit -------------------------------------------------------------------------------------

def _ef_datetime(dt: datetime) -> str:
    """Format de stockage d'EF Core SQLite (yyyy-MM-dd HH:mm:ss.FFFFFFF)."""
    text = f"{dt:%Y-%m-%d %H:%M:%S}.{dt.microsecond:06d}0".rstrip("0")
    return text.rstrip(".")


def _hash_datetime(dt: datetime) -> str:
    """Format utilisé dans l'empreinte (yyyy-MM-ddTHH:mm:ss.fffffff), identique à AppDbContext."""
    return f"{dt:%Y-%m-%dT%H:%M:%S}.{dt.microsecond:06d}0"


def compute_audit_hash(previous_hash: str, timestamp_canonical: str, user: str, machine: str,
                       entity_type: str, entity_id: str, action: str, changes_json: str) -> str:
    canonical = "\x1f".join([previous_hash, timestamp_canonical, user, machine, entity_type, entity_id, action, changes_json])
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def current_user() -> str:
    return os.getenv("AFMI_AUDIT_USER") or getpass.getuser()


def append_audit(conn: sqlite3.Connection, entity_type: str, entity_id: str, action: str,
                 changes: Dict[str, Any], now: Optional[datetime] = None) -> str:
    now = (now or datetime.now(timezone.utc)).replace(tzinfo=None)
    row = conn.execute("SELECT Hash FROM AuditEntries ORDER BY Id DESC LIMIT 1").fetchone()
    previous = row[0] if row else ""
    user, machine = current_user(), platform.node()
    changes_json = json.dumps(changes, ensure_ascii=False, separators=(",", ":"))
    digest = compute_audit_hash(previous, _hash_datetime(now), user, machine, entity_type, entity_id, action, changes_json)
    conn.execute(
        "INSERT INTO AuditEntries (TimestampUtc, User, Machine, EntityType, EntityId, Action, ChangesJson, PreviousHash, Hash) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (_ef_datetime(now), user, machine, entity_type, entity_id, action, changes_json, previous, digest),
    )
    return digest


def find_first_tampered_audit_entry(conn: sqlite3.Connection) -> Optional[int]:
    previous = ""
    for r in conn.execute("SELECT * FROM AuditEntries ORDER BY Id"):
        ts = datetime.fromisoformat(r["TimestampUtc"])
        expected = compute_audit_hash(previous, _hash_datetime(ts), r["User"], r["Machine"], r["EntityType"],
                                      r["EntityId"], r["Action"], r["ChangesJson"])
        if r["PreviousHash"] != previous or r["Hash"] != expected:
            return r["Id"]
        previous = r["Hash"]
    return None


# --- Écritures journalisées -------------------------------------------------------------------------------

def now_ef() -> str:
    """Horodatage UTC au format de stockage d'EF Core."""
    return _ef_datetime(datetime.now(timezone.utc).replace(tzinfo=None))


MAX_AUDITED_TEXT = 2000
# Colonnes secrètes : jamais recopiées dans le journal (comme AppDbContext.Audit côté .NET)
SECRET_COLUMNS = {("SmtpSettings", "Password"), ("AiSettings", "CloudApiKey")}


def _audit_value(v: Any) -> Any:
    """Comme AppDbContext : les textes longs (contenu de document, image) sont résumés dans le journal."""
    if v is None:
        return None
    if isinstance(v, (bytes, bytearray)):
        return f"[données binaires de {len(v)} octets]"
    text = str(v)
    return text if len(text) <= MAX_AUDITED_TEXT else f"[texte de {len(text)} caractères]"


def insert(conn: sqlite3.Connection, table: str, entity_type: str, values: Dict[str, Any]) -> int:
    """INSERT + entrée d'audit « Création » (même format que AppDbContext : {"Champ": {"new": "…"}})."""
    cols = ", ".join(values)
    marks = ", ".join("?" for _ in values)
    cur = conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({marks})", tuple(values.values()))
    new_id = cur.lastrowid
    append_audit(conn, entity_type, str(new_id), ACTION_CREATE,
                 {k: {"new": "***" if (table, k) in SECRET_COLUMNS else _audit_value(v)} for k, v in values.items()})
    return new_id


def update(conn: sqlite3.Connection, table: str, entity_type: str, row_id: int, values: Dict[str, Any]) -> bool:
    """UPDATE des seuls champs modifiés + entrée d'audit « Modification ». Retourne False si rien n'a changé."""
    old = conn.execute(f"SELECT * FROM {table} WHERE Id = ?", (row_id,)).fetchone()
    if old is None:
        raise KeyError(f"{entity_type} {row_id} introuvable.")
    changes = {k: v for k, v in values.items() if old[k] != v}
    if not changes:
        return False
    sets = ", ".join(f"{k} = ?" for k in changes)
    conn.execute(f"UPDATE {table} SET {sets} WHERE Id = ?", (*changes.values(), row_id))
    append_audit(conn, entity_type, str(row_id), ACTION_UPDATE,
                 {k: ({"old": "***", "new": "***"} if (table, k) in SECRET_COLUMNS else {"old": _audit_value(old[k]), "new": _audit_value(v)})
                  for k, v in changes.items()})
    return True


def soft_delete(conn: sqlite3.Connection, table: str, entity_type: str, row_id: int) -> None:
    conn.execute(f"UPDATE {table} SET IsDeleted = 1, DeletedAtUtc = ? WHERE Id = ?", (now_ef(), row_id))
    append_audit(conn, entity_type, str(row_id), "Suppression", {"IsDeleted": {"old": "False", "new": "True"}})


def hard_delete(conn: sqlite3.Connection, table: str, entity_type: str, row_id: int) -> None:
    old = conn.execute(f"SELECT * FROM {table} WHERE Id = ?", (row_id,)).fetchone()
    conn.execute(f"DELETE FROM {table} WHERE Id = ?", (row_id,))
    if old is not None:
        append_audit(conn, entity_type, str(row_id), "Suppression définitive", {k: {"old": _audit_value(old[k])} for k in old.keys()})


# --- Paramètres (table AppSettings, partagée avec SettingsService côté Desktop) ----------------------------

def get_setting(key: str, default: Any = None) -> Any:
    try:
        with connect() as conn:
            row = conn.execute("SELECT ValueJson, IsSecret FROM AppSettings WHERE Key = ?", (key,)).fetchone()
    except (UnifiedDbUnavailable, sqlite3.Error):
        return default
    if row is None:
        return default
    value = json.loads(row["ValueJson"])
    return dpapi.unprotect(value) if row["IsSecret"] else value


def set_setting(key: str, value: Any, secret: bool = False) -> None:
    stored = json.dumps(dpapi.protect(value) if secret else value, ensure_ascii=False)
    with connect() as conn:
        old = conn.execute("SELECT ValueJson, IsSecret FROM AppSettings WHERE Key = ?", (key,)).fetchone()
        now = _ef_datetime(datetime.now(timezone.utc).replace(tzinfo=None))
        if old is None:
            conn.execute("INSERT INTO AppSettings (Key, ValueJson, IsSecret, UpdatedAtUtc) VALUES (?, ?, ?, ?)",
                         (key, stored, int(secret), now))
            action, changes = ACTION_CREATE, {"ValueJson": {"new": "***" if secret else stored}}
        else:
            conn.execute("UPDATE AppSettings SET ValueJson = ?, IsSecret = ?, UpdatedAtUtc = ? WHERE Key = ?",
                         (stored, int(secret), now, key))
            hidden = secret or bool(old["IsSecret"])
            action, changes = ACTION_UPDATE, {"ValueJson": {"old": "***" if hidden else old["ValueJson"],
                                                           "new": "***" if hidden else stored}}
        append_audit(conn, "AppSetting", key, action, changes)
