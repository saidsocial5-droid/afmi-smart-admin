"""Liaisons entre les modules (Lot 9) : vue 360° d'un projet et recherche unifiée.

Tout ce qui concerne un projet, réuni en un seul endroit et calculé depuis la base unique : budget et réalisé,
trésorerie des comptes liés, indicateurs, activités et comptes rendus, actions en cours, documents par type,
échéances des bailleurs, photos, documents de l'éditeur et alertes. Chaque élément renvoie vers son module.
"""
from datetime import date
from typing import Any, Dict, List

from backend.core import unified_db


def project_overview(project_id: int) -> Dict[str, Any]:
    from backend.tools.editor import blocks
    from backend.tools.ged import lifecycle
    from backend.tools.meetings import service as meetings
    from backend.tools.reports import finance
    with unified_db.connect() as conn:
        p = conn.execute("SELECT p.*, f.Name AS FunderName FROM Projects p LEFT JOIN Funders f ON f.Id = p.FunderId WHERE p.Id = ? AND p.IsDeleted = 0",
                         (project_id,)).fetchone()
        if p is None:
            raise ValueError("Projet introuvable.")
        today = date.today().isoformat()
        accounts = []
        for a in conn.execute("SELECT DISTINCT b.* FROM BankAccounts b JOIN AccountProjectLinks l ON l.BankAccountId = b.Id "
                              "WHERE l.ProjectId = ? AND l.IsDeleted = 0 AND b.IsDeleted = 0", (project_id,)):
            accounts.append({"id": a["Id"], "title": a["Title"], "currency": a["Currency"], "balance": finance.book_balance(conn, a["Id"], today),
                             "reconciliation": finance.reconciliation_status(conn, a["Id"], today)["status"]})
        agreements = [dict(reference=r["Reference"], amount=r["AmountMinor"], currency=r["Currency"], end=r["EndDate"],
                           received=conn.execute("SELECT COALESCE(SUM(AmountMinor), 0) FROM FundingTranches WHERE FundingAgreementId = ? "
                                                 "AND ReceivedOperationId IS NOT NULL AND IsDeleted = 0", (r["Id"],)).fetchone()[0])
                      for r in conn.execute("SELECT * FROM FundingAgreements WHERE ProjectId = ? AND IsDeleted = 0", (project_id,))]
        docs_by_type = {r["DocType"] or "Autre": r["n"] for r in conn.execute(
            "SELECT DocType, COUNT(*) AS n FROM Documents WHERE ProjectId = ? AND IsDeleted = 0 GROUP BY DocType", (project_id,))}
        obligations = [dict(title=r["Title"], due=r["DueDate"], status=r["Status"]) for r in conn.execute(
            "SELECT * FROM ReportingObligations WHERE ProjectId = ? AND IsDeleted = 0 AND Status IN ('À venir', 'Proposée') ORDER BY DueDate LIMIT 5",
            (project_id,))]
        photos = conn.execute("SELECT COUNT(*) FROM Photos WHERE ProjectId = ? AND IsDeleted = 0", (project_id,)).fetchone()[0]
        editor_docs = [dict(id=r["Id"], title=r["Title"], updated=r["UpdatedAtUtc"]) for r in conn.execute(
            "SELECT Id, Title, UpdatedAtUtc FROM EditorDocuments WHERE ProjectId = ? AND IsDeleted = 0 ORDER BY UpdatedAtUtc DESC LIMIT 6", (project_id,))]
        draft_ops = conn.execute(
            "SELECT COUNT(DISTINCT o.Id) FROM Operations o JOIN OperationAllocations a ON a.OperationId = o.Id "
            "WHERE a.ProjectId = ? AND o.Status = 'Draft' AND o.IsDeleted = 0", (project_id,)).fetchone()[0]
        tasks = conn.execute("SELECT COUNT(*), SUM(Status = 'Terminé'), AVG(ProgressPercentage) FROM Tasks WHERE ProjectId = ?", (project_id,)).fetchone()
    budget = blocks.budget_table(project_id)
    inds = blocks.indicators(project_id)["rows"]
    acts = blocks.activities(project_id)
    meeting_list = meetings.list_meetings(project_id)
    return {
        "project": {"id": p["Id"], "code": p["Code"], "name": p["Name"], "status": p["Status"], "manager": p["Manager"], "funder": p["FunderName"],
                    "start": str(p["TargetStartDate"] or "")[:10], "end": str(p["TargetEndDate"] or "")[:10], "local_folder": p["LocalFolderPath"]},
        "budget": {"planned": budget["total"]["planned"], "realized": budget["total"]["realized_mad"], "rate": budget["total"]["rate"],
                   "lines": len(budget["rows"]), "draft_operations": draft_ops},
        "treasury": accounts, "agreements": agreements,
        "indicators": [{"name": i["name"], "rate": i["rate"], "current": i["current"], "target": i["target"], "unit": i["unit"]} for i in inds],
        "activities": {"count": len(acts["rows"]), "participants": acts["total_participants"], "last": acts["rows"][-3:]},
        "tasks": {"count": tasks[0] or 0, "done": int(tasks[1] or 0), "progress": round(tasks[2] or 0, 1)},
        "meetings": {"count": len(meeting_list), "last": [dict(id=m["id"], title=m["title"], date=m["date"], kind=m["kind_label"], status=m["status"])
                                                          for m in meeting_list[:4]],
                     "open_actions": meetings.open_actions(project_id)[:6]},
        "documents": {"total": sum(docs_by_type.values()), "by_type": docs_by_type, "obligations": obligations},
        "photos": photos, "editor_documents": editor_docs,
        "alerts": lifecycle.alerts(project_id)[:8],
    }


def search(q: str, limit: int = 8) -> Dict[str, List[Dict[str, Any]]]:
    """Recherche dans tous les modules : projets, documents (plein texte), comptes rendus, opérations, documents de l'éditeur."""
    q = (q or "").strip()
    if len(q) < 2:
        return {"projects": [], "documents": [], "meetings": [], "operations": [], "editor": []}
    like = f"%{q}%"
    out: Dict[str, List[Dict[str, Any]]] = {}
    with unified_db.connect() as conn:
        out["projects"] = [dict(id=r["Id"], title=f"{r['Code']} — {r['Name']}", tab="ged") for r in conn.execute(
            "SELECT Id, Code, Name FROM Projects WHERE IsDeleted = 0 AND (Name LIKE ? OR Code LIKE ? OR Description LIKE ?) LIMIT ?", (like, like, like, limit))]
        out["meetings"] = [dict(id=r["Id"], title=r["Title"], subtitle=f"{r['Date']} · {r['Kind']}", tab="meetings") for r in conn.execute(
            "SELECT DISTINCT m.Id, m.Title, m.Date, m.Kind FROM Meetings m LEFT JOIN MeetingResolutions d ON d.MeetingId = m.Id "
            "LEFT JOIN MeetingActions a ON a.MeetingId = m.Id WHERE m.IsDeleted = 0 AND (m.Title LIKE ? OR m.Summary LIKE ? OR m.Agenda LIKE ? "
            "OR d.Text LIKE ? OR a.Text LIKE ?) ORDER BY m.Date DESC LIMIT ?", (like, like, like, like, like, limit))]
        out["operations"] = [dict(id=r["Id"], title=r["Label"], subtitle=f"{r['OperationDate']} · {r['AmountMinor'] / 100:,.2f} {r['Currency']}".replace(",", " "),
                                  tab="statements") for r in conn.execute(
            "SELECT Id, Label, OperationDate, AmountMinor, Currency FROM Operations WHERE IsDeleted = 0 AND (Label LIKE ? OR Reference LIKE ? OR ThirdParty LIKE ?) "
            "ORDER BY OperationDate DESC LIMIT ?", (like, like, like, limit))]
        out["editor"] = [dict(id=r["Id"], title=r["Title"], tab="editor") for r in conn.execute(
            "SELECT Id, Title FROM EditorDocuments WHERE IsDeleted = 0 AND (Title LIKE ? OR ContentJson LIKE ?) ORDER BY UpdatedAtUtc DESC LIMIT ?",
            (like, like, limit))]
        try:
            from backend.tools.ged import index
            hits = index.search_fts(conn, q, None, limit)
            seen, docs = set(), []
            for h in hits:
                if h["DocumentId"] not in seen:
                    seen.add(h["DocumentId"])
                    docs.append(dict(id=h["DocumentId"], title=h["Title"], subtitle=f"p. {h['Page']}" if h.get("Page") else "", tab="ged"))
            out["documents"] = docs
        except Exception:                                   # requête plein texte invalide (caractères spéciaux)
            out["documents"] = [dict(id=r["Id"], title=r["Title"], tab="ged") for r in conn.execute(
                "SELECT Id, Title FROM Documents WHERE IsDeleted = 0 AND Title LIKE ? LIMIT ?", (like, limit))]
    return out
