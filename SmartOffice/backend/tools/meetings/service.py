"""Comptes rendus et procès-verbaux (Lot 9).

Un compte rendu relie : le projet (ou la vie associative), l'activité du projet, le texte rédigé dans l'éditeur, les
participants, les décisions et les actions. Les actions sont suivies (tâche du projet, alerte d'échéance, rappel dans
le compte rendu suivant) ; un compte rendu validé est archivé dans la GED et, pour une activité, met à jour le rapport
d'activité qui alimente les indicateurs et le rapport annuel.
"""
import json
import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from backend.core import unified_db
from backend.tools.editor import documents

KINDS = {
    "Réunion": {"label": "Réunion de travail", "doc": "Procès-verbal", "pv": True},
    "COPIL": {"label": "Comité de pilotage", "doc": "Procès-verbal", "pv": True},
    "AG": {"label": "Assemblée générale", "doc": "Procès-verbal", "pv": True},
    "CA": {"label": "Conseil d'administration", "doc": "Procès-verbal", "pv": True},
    "Rencontre": {"label": "Rencontre (partenaire, autorité, bailleur)", "doc": "Procès-verbal", "pv": True},
    "Visite": {"label": "Visite de terrain", "doc": "Rapport narratif", "pv": False},
    "Activité": {"label": "Compte rendu d'activité (atelier, formation, sensibilisation…)", "doc": "Rapport narratif", "pv": False},
}
STATUSES = ("Brouillon", "Validé", "Diffusé")
ACTION_STATUSES = ("À faire", "En cours", "Fait", "Abandonné")
GOVERNANCE_CODE = "ASSO-GOUV"


class MeetingError(ValueError):
    pass


# --- Lecture ---------------------------------------------------------------------------------------------------

def _meeting(conn, r) -> Dict[str, Any]:
    mid = r["Id"]
    project = conn.execute("SELECT Code, Name FROM Projects WHERE Id = ?", (r["ProjectId"],)).fetchone() if r["ProjectId"] else None
    participants = [dict(id=p["Id"], name=p["Name"], organization=p["Organization"], role=p["Role"], sex=p["Sex"], present=bool(p["Present"]))
                    for p in conn.execute("SELECT * FROM MeetingParticipants WHERE MeetingId = ? ORDER BY Id", (mid,))]
    decisions = [dict(id=d["Id"], number=d["Number"], text=d["Text"], responsible=d["Responsible"])
                 for d in conn.execute("SELECT * FROM MeetingResolutions WHERE MeetingId = ? ORDER BY Number, Id", (mid,))]
    actions = [_action(a) for a in conn.execute("SELECT * FROM MeetingActions WHERE MeetingId = ? ORDER BY Id", (mid,))]
    present = [p for p in participants if p["present"]]
    return {"id": mid, "kind": r["Kind"], "kind_label": KINDS.get(r["Kind"], {}).get("label", r["Kind"]), "title": r["Title"],
            "date": r["Date"], "start_time": r["StartTime"], "location": r["Location"], "project_id": r["ProjectId"],
            "project": f"{project['Code']} — {project['Name']}" if project else "Vie associative", "task_id": r["ProjectTaskId"],
            "activity_report_id": r["ActivityReportId"], "editor_document_id": r["EditorDocumentId"], "archived_document_id": r["ArchivedDocumentId"],
            "organizer": r["Organizer"], "secretary": r["Secretary"], "agenda": r["Agenda"], "summary": r["Summary"], "status": r["Status"],
            "participants": participants, "decisions": decisions, "actions": actions,
            "attendance": {"present": len(present), "women": sum(p["sex"] == "F" for p in present), "men": sum(p["sex"] == "M" for p in present),
                           "excused": len(participants) - len(present)},
            "updated_at": r["UpdatedAtUtc"]}


def _action(a) -> Dict[str, Any]:
    late = a["Status"] in ("À faire", "En cours") and a["DueDate"] and a["DueDate"] < date.today().isoformat()
    return {"id": a["Id"], "meeting_id": a["MeetingId"], "text": a["Text"], "responsible": a["Responsible"], "due_date": a["DueDate"],
            "status": a["Status"], "done_date": a["DoneDate"], "task_id": a["ProjectTaskId"], "late": bool(late)}


def list_meetings(project_id: Optional[int] = None, year: Optional[int] = None, kind: Optional[str] = None,
                  governance: bool = False) -> List[Dict[str, Any]]:
    sql, args = "SELECT * FROM Meetings WHERE IsDeleted = 0", []
    if governance:
        sql += " AND ProjectId IS NULL"
    elif project_id:
        sql += " AND ProjectId = ?"
        args.append(project_id)
    if year:
        sql += " AND substr(Date, 1, 4) = ?"
        args.append(str(year))
    if kind:
        sql += " AND Kind = ?"
        args.append(kind)
    with unified_db.connect() as conn:
        return [_meeting(conn, r) for r in conn.execute(sql + " ORDER BY Date DESC, Id DESC", args)]


def get(meeting_id: int) -> Dict[str, Any]:
    with unified_db.connect() as conn:
        r = conn.execute("SELECT * FROM Meetings WHERE Id = ? AND IsDeleted = 0", (meeting_id,)).fetchone()
        if r is None:
            raise MeetingError("Compte rendu introuvable.")
        return _meeting(conn, r)


def open_actions(project_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Actions non terminées (suivi, alertes, compte rendu suivant)."""
    sql = ("SELECT a.*, m.Title AS MeetingTitle, m.Date AS MeetingDate, m.ProjectId FROM MeetingActions a JOIN Meetings m ON m.Id = a.MeetingId "
           "WHERE m.IsDeleted = 0 AND a.Status IN ('À faire', 'En cours')")
    args: List[Any] = []
    if project_id:
        sql += " AND m.ProjectId = ?"
        args.append(project_id)
    with unified_db.connect() as conn:
        return [{**_action(a), "meeting": a["MeetingTitle"], "meeting_date": a["MeetingDate"], "project_id": a["ProjectId"]}
                for a in conn.execute(sql + " ORDER BY COALESCE(a.DueDate, '9999') , a.Id", args)]


# --- Écriture --------------------------------------------------------------------------------------------------

def _check(data: Dict[str, Any]) -> None:
    if data.get("kind") not in KINDS:
        raise MeetingError("Type de compte rendu inconnu.")
    if not (data.get("title") or "").strip():
        raise MeetingError("Titre obligatoire.")
    try:
        date.fromisoformat(data.get("date") or "")
    except ValueError as e:
        raise MeetingError("Date invalide (AAAA-MM-JJ).") from e
    if data.get("status", "Brouillon") not in STATUSES:
        raise MeetingError("Statut inconnu.")
    for p in data.get("participants") or []:
        if p.get("sex", "") not in ("", "F", "M"):
            raise MeetingError("Sexe d'un participant : F, M ou vide.")
    for a in data.get("actions") or []:
        if a.get("status", "À faire") not in ACTION_STATUSES:
            raise MeetingError("Statut d'action inconnu.")
        if a.get("due_date"):
            date.fromisoformat(a["due_date"])
    if data.get("kind") == "Activité" and not data.get("project_id"):
        raise MeetingError("Un compte rendu d'activité se rattache à un projet.")


def save(data: Dict[str, Any]) -> Dict[str, Any]:
    _check(data)
    now = unified_db.now_ef()
    values = {"Kind": data["kind"], "Title": data["title"].strip()[:250], "Date": data["date"], "StartTime": (data.get("start_time") or "")[:10],
              "Location": (data.get("location") or "")[:200], "ProjectId": data.get("project_id") or None,
              "ProjectTaskId": data.get("task_id") or None, "Organizer": (data.get("organizer") or "")[:150],
              "Secretary": (data.get("secretary") or "")[:150], "Agenda": data.get("agenda") or "", "Summary": data.get("summary") or "",
              "Status": data.get("status") or "Brouillon", "UpdatedAtUtc": now}
    with unified_db.connect() as conn:
        if data.get("id"):
            current = conn.execute("SELECT * FROM Meetings WHERE Id = ? AND IsDeleted = 0", (data["id"],)).fetchone()
            if current is None:
                raise MeetingError("Compte rendu introuvable.")
            unified_db.update(conn, "Meetings", "Meeting", data["id"], values)
            mid = data["id"]
        else:
            mid = unified_db.insert(conn, "Meetings", "Meeting", {**values, "CreatedBy": unified_db.current_user(), "CreatedAtUtc": now,
                                                                  "EditorDocumentId": None, "ActivityReportId": None, "ArchivedDocumentId": None,
                                                                  "IsDeleted": 0})
        if "participants" in data:
            _replace(conn, "MeetingParticipants", "MeetingParticipant", mid, [
                {"Name": (p.get("name") or "").strip()[:150], "Organization": (p.get("organization") or "")[:150], "Role": (p.get("role") or "")[:100],
                 "Sex": p.get("sex") or "", "Present": int(p.get("present", True))} for p in data["participants"] if (p.get("name") or "").strip()])
        if "decisions" in data:
            _replace(conn, "MeetingResolutions", "MeetingResolution", mid, [
                {"Number": i + 1, "Text": d["text"].strip(), "Responsible": (d.get("responsible") or "")[:150]}
                for i, d in enumerate(x for x in data["decisions"] if (x.get("text") or "").strip())])
        if "actions" in data:
            _save_actions(conn, mid, data["actions"])
    return get(mid)


def _replace(conn, table: str, entity: str, meeting_id: int, rows: List[Dict[str, Any]]) -> None:
    for r in conn.execute(f"SELECT Id FROM {table} WHERE MeetingId = ?", (meeting_id,)).fetchall():
        unified_db.hard_delete(conn, table, entity, r["Id"])
    for row in rows:
        unified_db.insert(conn, table, entity, {"MeetingId": meeting_id, **row})


def _save_actions(conn, meeting_id: int, actions: List[Dict[str, Any]]) -> None:
    """Actions mises à jour par identifiant : la tâche liée et la date de réalisation sont conservées."""
    keep = set()
    for a in actions:
        if not (a.get("text") or "").strip():
            continue
        status = a.get("status") or "À faire"
        values = {"Text": a["text"].strip(), "Responsible": (a.get("responsible") or "")[:150], "DueDate": a.get("due_date") or None, "Status": status}
        if a.get("id"):
            old = conn.execute("SELECT * FROM MeetingActions WHERE Id = ? AND MeetingId = ?", (a["id"], meeting_id)).fetchone()
            if old is None:
                continue
            if status == "Fait" and old["Status"] != "Fait":
                values["DoneDate"] = date.today().isoformat()
            unified_db.update(conn, "MeetingActions", "MeetingAction", a["id"], values)
            keep.add(a["id"])
        else:
            keep.add(unified_db.insert(conn, "MeetingActions", "MeetingAction", {"MeetingId": meeting_id, **values, "ProjectTaskId": None,
                                                                                 "DoneDate": date.today().isoformat() if status == "Fait" else None}))
    for r in conn.execute("SELECT Id FROM MeetingActions WHERE MeetingId = ?", (meeting_id,)).fetchall():
        if r["Id"] not in keep:
            unified_db.hard_delete(conn, "MeetingActions", "MeetingAction", r["Id"])


def set_action_status(action_id: int, status: str) -> Dict[str, Any]:
    if status not in ACTION_STATUSES:
        raise MeetingError("Statut d'action inconnu.")
    with unified_db.connect() as conn:
        a = conn.execute("SELECT * FROM MeetingActions WHERE Id = ?", (action_id,)).fetchone()
        if a is None:
            raise MeetingError("Action introuvable.")
        values = {"Status": status, "DoneDate": date.today().isoformat() if status == "Fait" else None}
        unified_db.update(conn, "MeetingActions", "MeetingAction", action_id, values)
        if a["ProjectTaskId"] and status == "Fait":           # la tâche du projet suit l'action
            unified_db.update(conn, "Tasks", "ProjectTask", a["ProjectTaskId"], {"Status": "Terminé", "ProgressPercentage": 100.0,
                                                                                 "ActualEndDate": f"{date.today().isoformat()} 00:00:00"})
        return _action(conn.execute("SELECT * FROM MeetingActions WHERE Id = ?", (action_id,)).fetchone())


def delete(meeting_id: int) -> None:
    with unified_db.connect() as conn:
        unified_db.soft_delete(conn, "Meetings", "Meeting", meeting_id)


def create_task(action_id: int) -> Dict[str, Any]:
    """Action → tâche du projet (planning, Gantt, échéances de l'application de bureau)."""
    with unified_db.connect() as conn:
        a = conn.execute("SELECT a.*, m.ProjectId, m.Title AS MeetingTitle, m.Date AS MeetingDate FROM MeetingActions a "
                         "JOIN Meetings m ON m.Id = a.MeetingId WHERE a.Id = ?", (action_id,)).fetchone()
        if a is None:
            raise MeetingError("Action introuvable.")
        if a["ProjectTaskId"]:
            return {"task_id": a["ProjectTaskId"], "created": False}
        if not a["ProjectId"]:
            raise MeetingError("Compte rendu sans projet : l'action ne peut pas devenir une tâche de projet.")
        task = unified_db.insert(conn, "Tasks", "ProjectTask", {
            "ProjectId": a["ProjectId"], "ParentTaskId": None, "Name": a["Text"][:200],
            "Description": f"Action décidée lors de « {a['MeetingTitle']} » du {a['MeetingDate']}.", "Assignee": a["Responsible"],
            "TargetStartDate": f"{date.today().isoformat()} 00:00:00", "TargetEndDate": f"{a['DueDate']} 00:00:00" if a["DueDate"] else None,
            "ActualStartDate": None, "ActualEndDate": None, "ProgressPercentage": 0.0, "Status": "À faire", "Budget": "0", "Cost": "0",
            "Predecessors": ""})
        unified_db.update(conn, "MeetingActions", "MeetingAction", action_id, {"ProjectTaskId": task, "Status": "En cours" if a["Status"] == "À faire" else a["Status"]})
    return {"task_id": task, "created": True}


# --- Rédaction dans l'éditeur ----------------------------------------------------------------------------------

def _t(text: str, bold: bool = False) -> Dict[str, Any]:
    n = {"type": "text", "text": text}
    if bold:
        n["marks"] = [{"type": "bold"}]
    return n


def _p(*parts) -> Dict[str, Any]:
    content = [x if isinstance(x, dict) else _t(x) for x in parts if x]
    return {"type": "paragraph", "content": content} if content else {"type": "paragraph"}


def _h(level: int, text: str) -> Dict[str, Any]:
    return {"type": "heading", "attrs": {"level": level}, "content": [_t(text)]}


def _table(header: List[str], rows: List[List[str]]) -> Dict[str, Any]:
    def cell(kind, text, bold=False):
        return {"type": kind, "content": [_p(_t(text, bold)) if text else _p()]}
    return {"type": "table", "content": [{"type": "tableRow", "content": [cell("tableHeader", h, True) for h in header]}] +
            [{"type": "tableRow", "content": [cell("tableCell", c) for c in r]} for r in rows]}


def _fr(day: Optional[str]) -> str:
    return datetime.strptime(day, "%Y-%m-%d").strftime("%d/%m/%Y") if day else ""


def _template(m: Dict[str, Any], previous_actions: List[Dict[str, Any]]) -> Dict[str, Any]:
    kind = KINDS[m["kind"]]
    d = datetime.strptime(m["date"], "%Y-%m-%d").strftime("%d/%m/%Y")
    title = ("Procès-verbal — " if kind["pv"] else "Compte rendu — ") + m["title"]
    content: List[Dict[str, Any]] = [_h(1, title), _table(["Rubrique", "Information"], [
        ["Type", kind["label"]], ["Date et heure", f"{d} {m['start_time']}".strip()], ["Lieu", m["location"] or "[à compléter]"],
        ["Projet", m["project"]], ["Organisateur", m["organizer"] or "[à compléter]"], ["Secrétaire de séance", m["secretary"] or "[à compléter]"],
        ["Participants", f"{m['attendance']['present']} présents ({m['attendance']['women']} femmes, {m['attendance']['men']} hommes), "
                         f"{m['attendance']['excused']} excusés"]])]
    if m["participants"]:
        content += [_h(2, "Participants"), _table(["Nom", "Structure", "Fonction", "Présence"],
                                                  [[p["name"], p["organization"], p["role"], "Présent" if p["present"] else "Excusé"] for p in m["participants"]])]
    if previous_actions:
        content += [_h(2, "Suivi des actions des réunions précédentes"),
                    _table(["Action", "Responsable", "Échéance", "Statut"],
                           [[a["text"], a["responsible"], _fr(a["due_date"]), a["status"] + (" (en retard)" if a["late"] else "")] for a in previous_actions])]
    agenda = [x.strip(" -•\t") for x in (m["agenda"] or "").splitlines() if x.strip()]
    content.append(_h(2, "Ordre du jour" if kind["pv"] else "Objectifs de l'activité"))
    content.append({"type": "orderedList", "content": [{"type": "listItem", "content": [_p(a)]} for a in agenda]} if agenda else _p("[à compléter]"))
    content += [_h(2, "Déroulement et échanges" if kind["pv"] else "Déroulement et résultats"), _p(m["summary"] or "[à compléter]")]
    if kind["pv"]:
        content += [_h(2, "Décisions"), {"type": "orderedList", "content": [{"type": "listItem", "content": [_p(x["text"])]} for x in m["decisions"]]}
                    if m["decisions"] else _p("Décision 1 : [à compléter]")]
    else:
        content += [_h(2, "Difficultés rencontrées"), _p("[à compléter]"), _h(2, "Recommandations"), _p("[à compléter]")]
        if m["project_id"]:
            content += [_h(2, "Photos de l'activité"), {"type": "dynamicBlock", "attrs": {"kind": "gallery", "projectId": m["project_id"],
                                                                                           "dateFrom": m["date"], "dateTo": m["date"], "limit": 4}}]
    content += [_h(2, "Actions à mener"), _table(["Action", "Responsable", "Échéance"],
                                                 [[a["text"], a["responsible"], _fr(a["due_date"])] for a in m["actions"]] or [["Action : [à compléter]", "", ""]])]
    if kind["pv"]:
        content += [_p(), _p(_t("Fait à "), _t(m["location"] or "[lieu]"), _t(f", le {d}.")),
                    _table(["Le président de séance", "Le secrétaire de séance"], [[m["organizer"] or "", m["secretary"] or ""]])]
    return {"type": "doc", "content": content}


def write_document(meeting_id: int) -> Dict[str, Any]:
    """Crée (ou rouvre) le texte du compte rendu dans l'éditeur, pré-rempli selon le type."""
    m = get(meeting_id)
    if m["editor_document_id"]:
        return {"editor_document_id": m["editor_document_id"], "created": False}
    previous = [a for a in open_actions(m["project_id"]) if a["meeting_id"] != meeting_id and a["meeting_date"] <= m["date"]] if m["project_id"] else []
    with unified_db.connect() as conn:
        funder = conn.execute("SELECT FunderId FROM Projects WHERE Id = ?", (m["project_id"],)).fetchone() if m["project_id"] else None
    doc = documents.create_document({"title": ("PV — " if KINDS[m["kind"]]["pv"] else "CR — ") + m["title"], "project_id": m["project_id"],
                                     "funder_id": funder["FunderId"] if funder else None, "language": "fr", "content": _template(m, previous)})
    with unified_db.connect() as conn:
        unified_db.update(conn, "Meetings", "Meeting", meeting_id, {"EditorDocumentId": doc["id"], "UpdatedAtUtc": unified_db.now_ef()})
    return {"editor_document_id": doc["id"], "created": True}


# --- Extraction des décisions et des actions -------------------------------------------------------------------

_DATE = re.compile(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b")
_DECISION = re.compile(r"^d[ée]cision\s*(?:n°\s*)?\d*\s*[:.\-–]\s*(.+)$", re.I)          # « Décision 2 : … » : libellé retiré
_DECISION_SENTENCE = re.compile(r"\b(il est d[ée]cid[ée]|d[ée]cide|valide|approuve|adopte)\b", re.I)   # phrase gardée entière
_ACTION = re.compile(r"^(?:action\s*(?:n°\s*)?\d*\s*[:.\-–]\s*|\[ \]\s*|à faire\s*:\s*)(.+)$", re.I)
_RESP = re.compile(r"\((?:resp(?:onsable)?\.?\s*:?\s*)?([^()]{2,60}?)\)|responsable\s*:\s*([^,;.]{2,60})|(?:est\s+)?charg[ée]e?\s+de\s+\w+.*?$", re.I)


def _plain_lines(doc_json: Dict[str, Any]) -> List[str]:
    lines: List[str] = []

    def walk(node):
        if node.get("type") in ("paragraph", "heading"):
            lines.append("".join(c.get("text", "") for c in node.get("content") or [] if c.get("type") == "text").strip())
            return
        if node.get("type") == "tableRow":
            cells = ["".join(t.get("text", "") for p in c.get("content") or [] for t in p.get("content") or []).strip() for c in node.get("content") or []]
            lines.append(" | ".join(cells))
            return
        for child in node.get("content") or []:
            walk(child)
    walk(doc_json)
    return [l for l in lines if l]


def extract_from_text(lines: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    """Décisions et actions repérées dans le texte (formulations usuelles des PV) ; à vérifier par l'utilisateur."""
    decisions, actions, section = [], [], ""
    for line in lines:
        low = line.lower()
        if low in ("décisions", "decisions"):
            section = "d"
            continue
        if low.startswith("actions à mener") or low == "actions":
            section = "a"
            continue
        if low.startswith(("participants", "ordre du jour", "déroulement", "suivi des actions", "difficultés", "recommandations", "photos")):
            section = ""
            continue
        if "[à compléter]" in low or low.startswith(("action | responsable", "rubrique |")):
            continue
        m = _DECISION.match(line)
        if m or (section == "d" and len(line) > 8 and "|" not in line) or (section == "" and _DECISION_SENTENCE.search(line) and len(line) < 300):
            decisions.append({"text": (m.group(1) if m else line).strip()})
            continue
        if "|" in line and section == "a":
            parts = [p.strip() for p in line.split("|")]
            due = _DATE.search(parts[2]) if len(parts) > 2 else None
            actions.append({"text": parts[0], "responsible": parts[1] if len(parts) > 1 else "",
                            "due_date": f"{due.group(3)}-{int(due.group(2)):02d}-{int(due.group(1)):02d}" if due else None})
            continue
        m = _ACTION.match(line)
        if m:
            text = m.group(1).strip()
            due = _DATE.search(text)
            resp = re.search(r"responsable\s*:\s*([^,;.()]{2,60})|\(([^()]{2,60})\)", text, re.I)
            cleaned = _DATE.sub("", re.sub(r"\s*(responsable\s*:[^,;.()]*|\([^()]*\))", "", text, flags=re.I))
            cleaned = re.sub(r"\s*(avant le|au plus tard le|pour le|d'ici le)\s*$", "", cleaned.strip(), flags=re.I).strip(" ,;–-")
            actions.append({"text": cleaned,
                            "responsible": re.sub(r"^resp(?:onsable)?\.?\s*:\s*", "", (resp.group(1) or resp.group(2)).strip(), flags=re.I) if resp else "",
                            "due_date": f"{due.group(3)}-{int(due.group(2)):02d}-{int(due.group(1)):02d}" if due else None})
    return {"decisions": decisions, "actions": actions}


def extract(meeting_id: int) -> Dict[str, Any]:
    m = get(meeting_id)
    if not m["editor_document_id"]:
        raise MeetingError("Rédigez d'abord le compte rendu dans l'éditeur.")
    doc = documents.get_document(m["editor_document_id"])
    found = extract_from_text(_plain_lines(doc["content"]))
    known_d = {d["text"].lower() for d in m["decisions"]}
    known_a = {a["text"].lower() for a in m["actions"]}
    return {"decisions": [d for d in found["decisions"] if d["text"].lower() not in known_d],
            "actions": [a for a in found["actions"] if a["text"] and a["text"].lower() not in known_a]}


# --- Validation : rapport d'activité, archivage dans la GED -----------------------------------------------------

def governance_project(conn) -> int:
    """Projet technique « Association — gouvernance » qui reçoit les PV de la vie associative dans la GED."""
    r = conn.execute("SELECT Id FROM Projects WHERE Code = ? AND IsDeleted = 0", (GOVERNANCE_CODE,)).fetchone()
    if r:
        return r["Id"]
    return unified_db.insert(conn, "Projects", "Project", {
        "Name": "Association — gouvernance et vie associative", "Code": GOVERNANCE_CODE,
        "Description": "Dossier permanent : PV d'assemblée générale et de conseil d'administration, statuts, rapports institutionnels.",
        "Manager": "", "Owner": "", "Client": "", "Department": "", "Status": "Exécution", "Priority": "Moyenne", "BudgetGlobal": 0,
        "LessonsLearned": "", "LocalFolderPath": "", "Currency": "MAD", "IsDeleted": 0})


def _upsert_activity_report(conn, m: Dict[str, Any]) -> Optional[int]:
    if m["kind"] not in ("Activité", "Visite") or not m["task_id"]:
        return None
    values = {"Title": m["title"][:250], "ActivityDate": f"{m['date']} {m['start_time'] or '09:00'}:00"[:19], "Location": m["location"],
              "ParticipantsCount": m["attendance"]["present"], "Narrative": m["summary"], "Status": "Validé", "ProjectTaskId": m["task_id"]}
    if m["activity_report_id"]:
        unified_db.update(conn, "ActivityReports", "ActivityReport", m["activity_report_id"], values)
        return m["activity_report_id"]
    rid = unified_db.insert(conn, "ActivityReports", "ActivityReport", {**values, "Difficulties": "", "Recommendations": "", "IndicatorId": None})
    unified_db.update(conn, "Meetings", "Meeting", m["id"], {"ActivityReportId": rid})
    return rid


async def validate(meeting_id: int) -> Dict[str, Any]:
    """Validation : rapport d'activité mis à jour, document exporté et archivé dans la GED (type PV ou rapport)."""
    from backend.tools.exports import service as exports
    from backend.tools.ged import service as ged
    import asyncio
    m = get(meeting_id)
    with unified_db.connect() as conn:
        report_id = _upsert_activity_report(conn, m)
        target_project = m["project_id"] or governance_project(conn)
        unified_db.update(conn, "Meetings", "Meeting", meeting_id, {"Status": "Validé", "UpdatedAtUtc": unified_db.now_ef()})
    archived, note = None, ""
    if m["editor_document_id"]:
        try:
            data, name = await asyncio.to_thread(exports.document, m["editor_document_id"], "pdf")
        except Exception as e:                                  # pas de moteur PDF : archivage au format Word
            data, name = await asyncio.to_thread(exports.document, m["editor_document_id"], "docx")
            note = f"PDF indisponible ({e}) : archivé au format Word."
        try:
            res = await ged.import_document(target_project, data, name, title=m["title"], doc_type=KINDS[m["kind"]]["doc"])
            archived = res["document"]["id"]
        except ged.GedError as e:                               # document identique déjà archivé
            archived, note = m["archived_document_id"], f"{note} {e}".strip()
        if archived:
            with unified_db.connect() as conn:
                unified_db.update(conn, "Meetings", "Meeting", meeting_id, {"ArchivedDocumentId": archived})
    return {"meeting": get(meeting_id), "activity_report_id": report_id, "archived_document_id": archived, "note": note}


# --- Synthèses pour les autres modules ---------------------------------------------------------------------------

def summary_for_year(conn, year: int, project_ids: Optional[List[int]] = None) -> Dict[str, Any]:
    """Réunions et instances de l'exercice (rapport moral)."""
    rows = conn.execute("SELECT * FROM Meetings WHERE IsDeleted = 0 AND Status <> 'Brouillon' AND substr(Date, 1, 4) = ? ORDER BY Date",
                        (str(year),)).fetchall()
    if project_ids is not None:
        rows = [r for r in rows if r["ProjectId"] in project_ids]
    by_kind: Dict[str, int] = {}
    for r in rows:
        by_kind[r["Kind"]] = by_kind.get(r["Kind"], 0) + 1
    decisions = conn.execute(
        f"SELECT d.Text, m.Title, m.Date FROM MeetingResolutions d JOIN Meetings m ON m.Id = d.MeetingId WHERE m.Id IN ({','.join(str(r['Id']) for r in rows) or '0'}) "
        "ORDER BY m.Date, d.Number").fetchall()
    return {"count": len(rows), "by_kind": by_kind, "meetings": [dict(date=r["Date"], kind=r["Kind"], title=r["Title"]) for r in rows],
            "decisions": [dict(text=d["Text"], meeting=d["Title"], date=d["Date"]) for d in decisions]}
