"""Base unique jetable créée par le script des migrations EF Core (tests/fixtures/unified_schema.sql)."""
import sqlite3
from pathlib import Path

SCHEMA = Path(__file__).parent / "fixtures" / "unified_schema.sql"


def create_unified_db(path: Path) -> Path:
    conn = sqlite3.connect(str(path))
    try:
        # Fonction utilisée par la migration DecryptLegacyAmounts (aucune ligne à traiter sur une base neuve).
        conn.create_function("afmi_legacy_amount", 1, lambda v: float(v or 0))
        conn.executescript(SCHEMA.read_text(encoding="utf-8-sig"))
    finally:
        conn.close()
    return path
