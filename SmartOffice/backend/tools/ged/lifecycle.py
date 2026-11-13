"""Cycle de vie d'un projet : phase atteinte, documents attendus et reçus, frise, alertes."""
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from backend.core import unified_db
from .config import load


def current_phase(conn, project) -> str:
    """Phase atteinte, déduite du statut, des dates et des documents (sans saisie supplémentaire)."""
    cfg = load()
    phases = cfg["phases"]
    status = (project["Status"] or "").lower()
    today = date.today().isoformat()
    types = {r[0] for r in conn.execute("SELECT DocType FROM Documents WHERE ProjectId = ? AND IsDeleted = 0", (project["Id"],))}
    if "rapport d'évaluation" in {t.lower() for t in types}:
        return "Évaluation"
    if "clôture" in status or "archiv" in status or "Rapport final" in types:
        return "Clôture"
    start = str(project["ActualStartDate"] or project["TargetStartDate"] or "")[:10]
    has_agreement = "Convention" in types or conn.execute("SELECT 1 FROM FundingAgreements WHERE ProjectId = ? AND IsDeleted = 0", (project["Id"],)).fetchone()
    if has_agreement and start and start <= today:
        return "Suivi" if any(t in types for t in ("Rapport narratif", "Rapport financier")) else "Mise en œuvre"
    if has_agreement:
        return "Contractualisation"
    if any(t in types for t in ("Document de projet", "Budget", "Cadre logique")):
        return "Formulation"
    return phases[0]


def expected_documents(conn, project) -> List[Dict[str, Any]]:
    cfg = load()
    phase = current_phase(conn, project)
    reached = cfg["phases"][: cfg["phases"].index(phase) + 1]
    counts = {}
    for r in conn.execute("SELECT DocType, COUNT(*) FROM Documents WHERE ProjectId = ? AND IsDeleted = 0 GROUP BY DocType", (project["Id"],)):
        counts[r[0]] = r[1]
    # Document de projet unique (formulaire PNUD/PMF…) : le budget et le cadre logique y figurent. S'ils ont été repris dans
    # l'application (import du dossier), ces pièces sont considérées comme fournies, sans exiger un fichier séparé.
    covered = {}
    if counts.get("Document de projet") or counts.get("Convention"):
        pid = project["Id"]
        if conn.execute("SELECT 1 FROM BudgetLines WHERE ProjectId = ? AND IsDeleted = 0 LIMIT 1", (pid,)).fetchone():
            covered["Budget"] = "Document de projet (budget repris dans l'application)"
        if conn.execute("SELECT 1 FROM LogframeNodes WHERE ProjectId = ? AND IsDeleted = 0 LIMIT 1", (pid,)).fetchone():
            covered["Cadre logique"] = "Document de projet (cadre logique repris dans l'application)"
    out = []
    for ph in cfg["phases"]:
        for t in cfg["expected"].get(ph, []):
            n = counts.get(t, 0)
            item = {"phase": ph, "doc_type": t, "count": n, "reached": ph in reached}
            if n == 0 and t in covered:
                item.update(count=1, covered_by=covered[t])
            out.append(item)
    return out


def timeline(project_id: int) -> Dict[str, Any]:
    with unified_db.connect() as conn:
        p = conn.execute("SELECT * FROM Projects WHERE Id = ? AND IsDeleted = 0", (project_id,)).fetchone()
        if p is None:
            raise ValueError("Projet introuvable.")
        items: List[Dict[str, Any]] = []
        for label, value in (("Début prévu", p["TargetStartDate"]), ("Fin prévue", p["TargetEndDate"]), ("Début réel", p["ActualStartDate"]), ("Fin réelle", p["ActualEndDate"])):
            if value:
                items.append({"date": str(value)[:10], "lane": "Projet", "label": label, "status": "info"})
        for m in conn.execute("SELECT * FROM ProjectMilestones WHERE ProjectId = ? AND IsDeleted = 0", (project_id,)):
            items.append({"date": m["Date"], "lane": "Jalons", "label": m["Title"], "status": "done" if m["Done"] else "todo", "id": m["Id"], "phase": m["Phase"]})
        today = date.today().isoformat()
        for o in conn.execute("SELECT * FROM ReportingObligations WHERE ProjectId = ? AND IsDeleted = 0", (project_id,)):
            st = "done" if o["Status"] == "Remise" else "proposed" if o["Status"] == "Proposée" else ("late" if o["DueDate"] < today else "todo")
            items.append({"date": o["DueDate"], "lane": "Rapports dus", "label": o["Title"], "status": st, "id": o["Id"]})
        for t in conn.execute("SELECT t.*, a.Reference, a.Currency FROM FundingTranches t JOIN FundingAgreements a ON a.Id = t.FundingAgreementId "
                              "WHERE a.ProjectId = ? AND t.IsDeleted = 0 AND a.IsDeleted = 0", (project_id,)):
            st = "done" if t["ReceivedOperationId"] else ("late" if t["ExpectedDate"] < today else "todo")
            items.append({"date": t["ExpectedDate"], "lane": "Tranches", "label": f"{t['Label']} ({t['AmountMinor'] / 100:,.0f} {t['Currency']})".replace(",", " "), "status": st})
        for a in conn.execute("SELECT * FROM FundingAgreements WHERE ProjectId = ? AND IsDeleted = 0", (project_id,)):
            if a["EndDate"]:
                items.append({"date": a["EndDate"], "lane": "Tranches", "label": f"Fin de la convention {a['Reference']}", "status": "info"})
        for d in conn.execute("SELECT * FROM Documents WHERE ProjectId = ? AND IsDeleted = 0", (project_id,)):
            items.append({"date": str(d["SignatureDate"] or d["UploadedDate"])[:10], "lane": "Documents", "label": f"{d['DocType'] or d['Category']} : {d['Title']}",
                          "status": "done", "id": d["Id"], "phase": d["LifecyclePhase"]})
        phase = current_phase(conn, p)
        expected = expected_documents(conn, p)
    items = [i for i in items if i["date"]]
    items.sort(key=lambda i: i["date"])
    return {"project": {"id": p["Id"], "code": p["Code"], "name": p["Name"]}, "phase": phase, "phases": load()["phases"], "items": items, "expected": expected}


def alerts(project_id: Optional[int] = None) -> List[Dict[str, Any]]:
    cfg = load()
    days_report, days_end = cfg["alerts"]["report_due_days"], cfg["alerts"]["agreement_end_days"]
    today = date.today()
    out: List[Dict[str, Any]] = []
    with unified_db.connect() as conn:
        projects = conn.execute("SELECT * FROM Projects WHERE IsDeleted = 0" + (" AND Id = ?" if project_id else ""), ((project_id,) if project_id else ())).fetchall()
        for p in projects:
            for o in conn.execute("SELECT * FROM ReportingObligations WHERE ProjectId = ? AND IsDeleted = 0 AND Status = 'À venir'", (p["Id"],)):
                due = date.fromisoformat(o["DueDate"])
                if due < today:
                    out.append({"level": "critical", "code": "REPORT_LATE", "project": p["Code"], "date": o["DueDate"],
                                "message": f"{p['Code']} : « {o['Title']} » en retard (dû le {due:%d/%m/%Y})."})
                elif due <= today + timedelta(days=days_report):
                    out.append({"level": "warning", "code": "REPORT_DUE", "project": p["Code"], "date": o["DueDate"],
                                "message": f"{p['Code']} : « {o['Title']} » à remettre le {due:%d/%m/%Y} (dans {(due - today).days} jours)."})
            n_prop = conn.execute("SELECT COUNT(*) FROM ReportingObligations WHERE ProjectId = ? AND IsDeleted = 0 AND Status = 'Proposée'", (p["Id"],)).fetchone()[0]
            if n_prop:
                out.append({"level": "info", "code": "OBLIGATIONS_TO_CONFIRM", "project": p["Code"], "date": "",
                            "message": f"{p['Code']} : {n_prop} échéance(s) de rapport proposée(s) d'après une convention, à confirmer."})
            for e in expected_documents(conn, p):
                if e["reached"] and e["count"] == 0:
                    out.append({"level": "warning", "code": "MISSING_DOCUMENT", "project": p["Code"], "date": "",
                                "message": f"{p['Code']} : document attendu en phase « {e['phase']} » absent : {e['doc_type']}."})
            ends = [(a["EndDate"], f"convention {a['Reference']}") for a in conn.execute("SELECT * FROM FundingAgreements WHERE ProjectId = ? AND IsDeleted = 0 AND EndDate IS NOT NULL", (p["Id"],))]
            ends += [(str(d["ContractualEndDate"])[:10], f"« {d['Title']} »") for d in conn.execute(
                "SELECT * FROM Documents WHERE ProjectId = ? AND IsDeleted = 0 AND ContractualEndDate IS NOT NULL AND DocType IN ('Convention', 'Avenant', 'Contrat')", (p["Id"],))]
            for end, what in ends:
                d = date.fromisoformat(end)
                if today <= d <= today + timedelta(days=days_end):
                    out.append({"level": "warning", "code": "AGREEMENT_ENDING", "project": p["Code"], "date": end,
                                "message": f"{p['Code']} : {what} arrive à échéance le {d:%d/%m/%Y}."})
        # Actions décidées en réunion (comptes rendus, Lot 9) : en retard ou à échéance proche
        meeting_sql = ("SELECT a.Text, a.DueDate, a.Responsible, m.Title, m.ProjectId FROM MeetingActions a JOIN Meetings m ON m.Id = a.MeetingId "
                       "WHERE m.IsDeleted = 0 AND a.Status IN ('À faire', 'En cours') AND a.DueDate IS NOT NULL")
        codes = {p["Id"]: p["Code"] for p in projects}
        for a in conn.execute(meeting_sql):
            if project_id and a["ProjectId"] != project_id:
                continue
            due = date.fromisoformat(a["DueDate"])
            who = f" ({a['Responsible']})" if a["Responsible"] else ""
            label = codes.get(a["ProjectId"], "Association")
            if due < today:
                out.append({"level": "critical", "code": "MEETING_ACTION_LATE", "project": label, "date": a["DueDate"],
                            "message": f"{label} : action « {a['Text'][:80]} »{who} décidée en « {a['Title']} », en retard (due le {due:%d/%m/%Y})."})
            elif due <= today + timedelta(days=days_report):
                out.append({"level": "warning", "code": "MEETING_ACTION_DUE", "project": label, "date": a["DueDate"],
                            "message": f"{label} : action « {a['Text'][:80]} »{who} à réaliser avant le {due:%d/%m/%Y}."})
    order = {"critical": 0, "warning": 1, "info": 2}
    return sorted(out, key=lambda a: (order[a["level"]], a["date"] or "9999"))
