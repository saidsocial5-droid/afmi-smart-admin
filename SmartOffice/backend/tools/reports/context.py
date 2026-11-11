"""Exercice, périmètre et configuration des rapports annuels."""
import json
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from backend.config.settings import BUNDLED_CONFIG_DIR, settings
from backend.core import unified_db

SCOPES = ("association", "programme", "project", "funder")


@dataclass
class Period:
    year: int
    start: str
    end: str

    def previous(self) -> "Period":
        s, e = date.fromisoformat(self.start), date.fromisoformat(self.end)
        ps = s.replace(year=s.year - 1)
        return Period(self.year - 1, ps.isoformat(), (s - timedelta(days=1)).isoformat())


@dataclass
class Scope:
    type: str
    id: Optional[int]
    label: str
    project_ids: Optional[List[int]] = None     # None = association entière (tous les projets + fonctionnement)
    funder_id: Optional[int] = None
    include_operating: bool = True
    account_ids: Optional[List[int]] = None      # comptes concernés (None = tous)
    meta: Dict[str, Any] = field(default_factory=dict)


def layout() -> Dict[str, Any]:
    user = settings.data_dir / "config" / "financial_report_layout.json"
    path = user if user.exists() else BUNDLED_CONFIG_DIR / "financial_report_layout.json"
    return json.loads(path.read_text(encoding="utf-8"))


def period(conn, year: int) -> Period:
    """Exercice : table FiscalYears si renseignée, sinon mois de début du paramètre association (janvier par défaut)."""
    row = conn.execute("SELECT StartDate, EndDate FROM FiscalYears WHERE Year = ?", (year,)).fetchone()
    if row:
        return Period(year, row["StartDate"], row["EndDate"])
    setting = conn.execute("SELECT ValueJson FROM AppSettings WHERE Key = 'association.fiscal_year_start_month'").fetchone()
    month = int(json.loads(setting["ValueJson"])) if setting else 1
    start = date(year, month, 1)
    end = date(year + (1 if month > 1 else 0), month - 1 if month > 1 else 12, 1)
    end = (end.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    return Period(year, start.isoformat(), end.isoformat())


def scope(conn, scope_type: str, scope_id: Optional[int]) -> Scope:
    if scope_type not in SCOPES:
        raise ValueError(f"Périmètre inconnu : {scope_type}.")
    if scope_type == "association":
        return Scope("association", None, "Association (tous projets et fonctionnement)")
    if scope_type == "funder":
        f = conn.execute("SELECT * FROM Funders WHERE Id = ?", (scope_id,)).fetchone()
        if f is None:
            raise ValueError("Bailleur introuvable.")
        ids = {r[0] for r in conn.execute("SELECT Id FROM Projects WHERE FunderId = ? AND IsDeleted = 0", (scope_id,))}
        ids |= {r[0] for r in conn.execute("SELECT ProjectId FROM FundingAgreements WHERE FunderId = ? AND IsDeleted = 0", (scope_id,))}
        sc = Scope("funder", scope_id, f"Bailleur : {f['Name']}", sorted(ids), scope_id, include_operating=False)
    else:
        p = conn.execute("SELECT * FROM Projects WHERE Id = ? AND IsDeleted = 0", (scope_id,)).fetchone()
        if p is None:
            raise ValueError("Projet introuvable.")
        ids = [p["Id"]]
        if scope_type == "programme":  # le programme et tous ses sous-projets
            frontier = [p["Id"]]
            while frontier:
                children = [r[0] for r in conn.execute(
                    f"SELECT Id FROM Projects WHERE IsDeleted = 0 AND ParentProjectId IN ({','.join('?' * len(frontier))})", frontier)]
                frontier = [c for c in children if c not in ids]
                ids += frontier
        label = ("Programme : " if scope_type == "programme" else "Projet : ") + f"{p['Code']} — {p['Name']}"
        sc = Scope(scope_type, scope_id, label, ids, p["FunderId"], include_operating=False)
    if sc.project_ids:
        marks = ",".join("?" * len(sc.project_ids))
        sc.account_ids = [r[0] for r in conn.execute(
            f"SELECT DISTINCT BankAccountId FROM AccountProjectLinks WHERE IsDeleted = 0 AND ProjectId IN ({marks})", sc.project_ids)]
    else:
        sc.account_ids = []
    return sc
