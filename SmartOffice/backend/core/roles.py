"""Rôles des utilisateurs (Lot 7) : contrôle des écritures de l'API Smart Office.

Liste vide (Paramètres › Utilisateurs) : poste mono-utilisateur, tous les droits (comportement de la 1.3.0).
Sinon, l'utilisateur courant (compte Windows transmis par l'application de bureau) est cherché dans la liste ;
absent ou inactif, il n'a qu'un accès en lecture. Les lectures et les exports restent ouverts à tous.
"""
from typing import Optional

from backend.core import unified_db

AREAS = [
    ("/api/settings", "settings"),
    ("/api/statements", "finance"), ("/api/finance", "finance"), ("/api/payroll", "finance"), ("/api/ocr", "finance"),
    ("/api/exports", "read"),
    ("/api/documents", "projects"), ("/api/templates", "projects"), ("/api/charts", "projects"), ("/api/photos", "projects"),
    ("/api/editor", "projects"), ("/api/meetings", "projects"), ("/api/folders", "projects"), ("/api/ged", "projects"), ("/api/indicators", "projects"), ("/api/projects", "projects"),
    ("/api/grants", "projects"), ("/api/reports", "projects"), ("/api/files", "projects"), ("/api/funders", "projects"),
    ("/api/agents", "ai"), ("/api/workflows", "ai"), ("/api/plugins", "ai"), ("/api/rss", "ai"),
]
ALLOWED = {
    "Administrateur": {"settings", "finance", "projects", "ai", "read", "other"},
    "Comptable": {"finance", "projects", "ai", "read", "other"},
    "Chargé de projet": {"projects", "ai", "read", "other"},
    "Lecteur": {"read"},
}
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def area(path: str) -> str:
    for prefix, name in AREAS:
        if path == prefix or path.startswith(prefix + "/"):
            return name
    return "other"


def current_role() -> Optional[str]:
    """Rôle de l'utilisateur courant ; None = aucun utilisateur déclaré (tous les droits)."""
    if not unified_db.is_available():
        return None
    users = unified_db.get_setting("security.users", []) or []
    if not users:
        return None
    me = unified_db.current_user().lower()
    for u in users:
        if u.get("login", "").lower() == me and u.get("active", True):
            return u.get("role") or "Lecteur"
    return "Lecteur"


def check(method: str, path: str) -> Optional[str]:
    """Message de refus, ou None si l'action est permise."""
    if method.upper() not in WRITE_METHODS or not path.startswith("/api/"):
        return None
    role = current_role()
    if role is None:
        return None
    needed = area(path)
    if needed in ALLOWED.get(role, {"read"}):
        return None
    return f"Action réservée : votre rôle ({role}) ne permet pas de modifier cette partie de l'application."
