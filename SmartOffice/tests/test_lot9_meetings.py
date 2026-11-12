"""Lot 9 — comptes rendus et PV : enregistrement, rédaction, extraction, suivi des actions, liens avec les autres modules."""
import asyncio
from datetime import date, timedelta

import pytest

from backend.core import unified_db
from backend.tools.editor import documents
from backend.tools.meetings import service as meetings
from tests.test_lot5_reports import unified  # noqa: F401  (scénario partagé)


def _copil(**over):
    data = {"kind": "COPIL", "title": "Comité de pilotage n° 1", "date": "2026-03-12", "start_time": "10:00", "location": "Ifrane",
            "project_id": 1, "organizer": "La présidente", "secretary": "Le chargé de projet", "agenda": "Bilan du trimestre\nPlan d'action",
            "summary": "Échanges sur l'avancement.",
            "participants": [{"name": "Amina", "organization": "AFMI", "sex": "F"}, {"name": "Karim", "organization": "Bailleur", "sex": "M"},
                             {"name": "Excusé", "sex": "M", "present": False}],
            "decisions": [{"text": "Valider le plan de plantation."}],
            "actions": [{"text": "Commander les plants", "responsible": "Karim", "due_date": (date.today() - timedelta(days=3)).isoformat()}]}
    data.update(over)
    return meetings.save(data)


def test_meeting_is_saved_with_attendance(unified):
    m = _copil()
    assert m["attendance"] == {"present": 2, "women": 1, "men": 1, "excused": 1}
    assert m["decisions"][0]["number"] == 1 and m["actions"][0]["late"] is True
    with pytest.raises(meetings.MeetingError, match="projet"):
        meetings.save({**_copil(), "id": None, "kind": "Activité", "project_id": None})
    with pytest.raises(meetings.MeetingError):
        meetings.save({"kind": "Inconnu", "title": "x", "date": "2026-01-01"})
    # mise à jour : l'action garde son identifiant (et sa tâche)
    updated = meetings.save({**m, "actions": [{**m["actions"][0], "status": "En cours"}], "participants": m["participants"]})
    assert updated["actions"][0]["id"] == m["actions"][0]["id"] and updated["actions"][0]["status"] == "En cours"


def test_document_template_and_extraction(unified):
    first = _copil()
    second = _copil(title="Comité de pilotage n° 2", date="2026-06-12", decisions=[], actions=[])
    res = meetings.write_document(second["id"])
    doc = documents.get_document(res["editor_document_id"])
    text = str(doc["content"])
    assert "Suivi des actions des réunions précédentes" in text and "Commander les plants" in text   # rappel des actions ouvertes
    assert doc["title"].startswith("PV — ") and doc["project_id"] == 1
    assert meetings.write_document(second["id"])["created"] is False                                   # pas de doublon
    lines = ["Décisions", "Le comité décide de reporter la deuxième tranche.", "Décision 2 : recruter un animateur.",
             "Actions à mener", "Préparer le rapport | Amina | 30/06/2026", "Action : relancer la mairie (responsable : Karim) avant le 15/07/2026"]
    found = meetings.extract_from_text(lines)
    assert [d["text"] for d in found["decisions"]] == ["Le comité décide de reporter la deuxième tranche.", "recruter un animateur."]
    assert found["actions"][0] == {"text": "Préparer le rapport", "responsible": "Amina", "due_date": "2026-06-30"}
    assert found["actions"][1]["responsible"] == "Karim" and found["actions"][1]["due_date"] == "2026-07-15"
    assert "relancer la mairie" in found["actions"][1]["text"]


def test_action_becomes_task_and_alerts(unified):
    from backend.tools.ged import lifecycle
    m = _copil()
    action = m["actions"][0]
    res = meetings.create_task(action["id"])
    assert res["created"] and meetings.create_task(action["id"])["created"] is False
    with unified_db.connect() as conn:
        task = conn.execute("SELECT * FROM Tasks WHERE Id = ?", (res["task_id"],)).fetchone()
    assert task["Name"] == "Commander les plants" and task["Assignee"] == "Karim" and task["ProjectId"] == 1
    assert any(a["code"] == "MEETING_ACTION_LATE" for a in lifecycle.alerts(1))
    meetings.set_action_status(action["id"], "Fait")
    with unified_db.connect() as conn:
        assert conn.execute("SELECT Status FROM Tasks WHERE Id = ?", (res["task_id"],)).fetchone()[0] == "Terminé"
    assert not any(a["code"] == "MEETING_ACTION_LATE" for a in lifecycle.alerts(1))


def test_validation_archives_and_feeds_reports(unified):
    from backend.tools.reports import generator
    with unified_db.connect() as conn:
        task = unified_db.insert(conn, "Tasks", "ProjectTask", {"ProjectId": 1, "ParentTaskId": None, "Name": "Ateliers", "Description": "",
                                                                "Assignee": "", "ProgressPercentage": 0.0, "Status": "En cours", "Budget": "0",
                                                                "Cost": "0", "Predecessors": ""})
    act = meetings.save({"kind": "Activité", "title": "Atelier pépinière", "date": "2026-04-02", "location": "Azrou", "project_id": 1,
                         "task_id": task, "summary": "22 pépiniéristes formés.",
                         "participants": [{"name": f"P{i}", "sex": "F" if i % 2 else "M"} for i in range(22)]})
    meetings.write_document(act["id"])
    res = asyncio.run(meetings.validate(act["id"]))
    assert res["meeting"]["status"] == "Validé" and res["activity_report_id"]
    with unified_db.connect() as conn:
        report = conn.execute("SELECT * FROM ActivityReports WHERE Id = ?", (res["activity_report_id"],)).fetchone()
        assert report["ParticipantsCount"] == 22 and report["Status"] == "Validé"
        if res["archived_document_id"]:
            doc = conn.execute("SELECT DocType, ProjectId FROM Documents WHERE Id = ?", (res["archived_document_id"],)).fetchone()
            assert doc["DocType"] == "Rapport narratif" and doc["ProjectId"] == 1
    # Vie associative (AG sans projet) : archivée dans le dossier « gouvernance »
    ag = meetings.save({"kind": "AG", "title": "Assemblée générale ordinaire 2026", "date": "2026-05-20", "decisions": [{"text": "Approuver les comptes."}]})
    meetings.write_document(ag["id"])
    asyncio.run(meetings.validate(ag["id"]))
    with unified_db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM Projects WHERE Code = ?", (meetings.GOVERNANCE_CODE,)).fetchone()[0] == 1
    table = generator.table("meetings", 2026, "association", None)
    labels = [r[0] for r in table["rows"]]
    assert any("Assemblée générale" in l for l in labels) and table["total"][1] == 2
    assert any("Approuver les comptes." in n for n in table["notes"])


def test_meetings_api(client, unified):
    r = client.post("/api/meetings", json={"kind": "Rencontre", "title": "Rencontre avec la commune", "date": "2026-02-10", "project_id": 1})
    assert r.status_code == 200
    mid = r.json()["id"]
    assert client.get("/api/meetings?project_id=1").json()[0]["id"] == mid
    assert client.post(f"/api/meetings/{mid}/document").json()["created"] is True
    assert client.get("/api/meetings/context").json()["kinds"]["COPIL"]["label"] == "Comité de pilotage"
    assert client.delete(f"/api/meetings/{mid}").status_code == 200
    assert client.get(f"/api/meetings/{mid}").status_code == 400
