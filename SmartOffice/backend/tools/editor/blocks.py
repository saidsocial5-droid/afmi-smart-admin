"""Données des blocs dynamiques de l'éditeur. Chaque bloc enregistre ses paramètres dans le document et se recalcule
depuis la base à l'ouverture ou sur « Actualiser » : les chiffres affichés viennent toujours des données."""
from datetime import date
from typing import Any, Dict, List, Optional

from backend.core import unified_db


def _project(conn, project_id: Optional[int]):
    if not project_id:
        return None
    return conn.execute("SELECT * FROM Projects WHERE Id = ? AND IsDeleted = 0", (project_id,)).fetchone()


def budget_table(project_id: Optional[int]) -> Dict[str, Any]:
    """Exécution budgétaire : prévu, réalisé (dépenses validées nettes des avoirs, quote-part MAD), écart, taux."""
    with unified_db.connect() as conn:
        lines = conn.execute("SELECT * FROM BudgetLines WHERE IsDeleted = 0 AND ProjectId IS ? ORDER BY Code", (project_id,)).fetchall()
        rows = []
        for l in lines:
            realized = 0
            for a in conn.execute(
                    "SELECT a.AmountMinor, o.AmountMinor AS OpAmount, o.AmountMadMinor, o.Direction FROM OperationAllocations a "
                    "JOIN Operations o ON o.Id = a.OperationId WHERE a.BudgetLineId = ? AND o.Status = 'Validated' "
                    "AND o.IsDeleted = 0 AND o.Nature = 'Expense'", (l["Id"],)):
                mad = round(a["AmountMinor"] * a["AmountMadMinor"] / a["OpAmount"]) if a["OpAmount"] else 0
                realized += mad if a["Direction"] == "Debit" else -mad
            planned = l["PlannedMinor"] if l["Currency"] == "MAD" else None
            rows.append({"code": l["Code"], "label": l["Label"], "planned": l["PlannedMinor"], "currency": l["Currency"],
                         "realized_mad": realized, "gap": None if planned is None else planned - realized,
                         "rate": None if not planned else round(100 * realized / planned, 1)})
        project = _project(conn, project_id)
    total_planned = sum(r["planned"] for r in rows if r["currency"] == "MAD")
    total_realized = sum(r["realized_mad"] for r in rows)
    return {"project": project["Name"] if project else "Fonctionnement général", "rows": rows,
            "total": {"planned": total_planned, "realized_mad": total_realized, "gap": total_planned - total_realized,
                      "rate": round(100 * total_realized / total_planned, 1) if total_planned else None},
            "source": "Lignes budgétaires et opérations validées (Trésorerie)"}


def indicators(project_id: Optional[int]) -> Dict[str, Any]:
    with unified_db.connect() as conn:
        rows = conn.execute("SELECT * FROM Indicators WHERE ProjectId = ? ORDER BY Name", (project_id,)).fetchall() if project_id else []
    return {"rows": [{"name": r["Name"], "unit": r["Unit"], "target": r["TargetValue"], "current": r["CurrentValue"],
                      "rate": round(100 * r["CurrentValue"] / r["TargetValue"], 1) if r["TargetValue"] else None} for r in rows],
            "source": "Indicateurs du projet"}


def activities(project_id: Optional[int], date_from: Optional[str] = None, date_to: Optional[str] = None) -> Dict[str, Any]:
    with unified_db.connect() as conn:
        sql = ("SELECT r.*, t.Name AS TaskName FROM ActivityReports r JOIN Tasks t ON t.Id = r.ProjectTaskId "
               "WHERE t.ProjectId = ?")
        args: List[Any] = [project_id]
        if date_from:
            sql += " AND date(r.ActivityDate) >= date(?)"
            args.append(date_from)
        if date_to:
            sql += " AND date(r.ActivityDate) <= date(?)"
            args.append(date_to)
        rows = conn.execute(sql + " ORDER BY r.ActivityDate", args).fetchall() if project_id else []
    return {"rows": [{"date": str(r["ActivityDate"])[:10], "title": r["Title"], "task": r["TaskName"], "location": r["Location"],
                      "participants": r["ParticipantsCount"], "status": r["Status"]} for r in rows],
            "total_participants": sum(r["ParticipantsCount"] or 0 for r in rows), "source": "Rapports d'activité"}


def chart(project_id: Optional[int], kind: str = "budget") -> Dict[str, Any]:
    """Séries pour un graphique : exécution budgétaire par ligne, ou réalisé des indicateurs."""
    if kind == "indicators":
        data = indicators(project_id)
        series = [{"label": r["name"], "planned": r["target"], "actual": r["current"]} for r in data["rows"]]
        return {"kind": kind, "title": "Indicateurs : cible et réalisé", "series": series, "unit": "", "source": data["source"]}
    data = budget_table(project_id)
    series = [{"label": f"{r['code']} {r['label']}".strip(), "planned": r["planned"] / 100, "actual": r["realized_mad"] / 100}
              for r in data["rows"] if r["currency"] == "MAD"]
    return {"kind": "budget", "title": "Exécution budgétaire (MAD)", "series": series, "unit": "MAD", "source": data["source"]}


def fields(project_id: Optional[int], funder_id: Optional[int]) -> Dict[str, str]:
    """Valeurs des champs dynamiques (date du jour, projet, bailleur, association)."""
    with unified_db.connect() as conn:
        project = _project(conn, project_id)
        fid = funder_id or (project["FunderId"] if project else None)
        funder = conn.execute("SELECT Name FROM Funders WHERE Id = ?", (fid,)).fetchone() if fid else None
        assoc = conn.execute("SELECT ValueJson FROM AppSettings WHERE Key = 'association.name'").fetchone()
    import json
    return {"date": date.today().strftime("%d/%m/%Y"), "project_name": project["Name"] if project else "",
            "project_code": project["Code"] if project else "", "funder_name": funder["Name"] if funder else "",
            "association": json.loads(assoc["ValueJson"]) if assoc else "Association Forêt Modèle d'Ifrane"}
