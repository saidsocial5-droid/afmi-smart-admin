"""Comptes rendus et procès-verbaux (Lot 9)."""
import sqlite3
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

from backend.core import unified_db
from backend.tools.editor.documents import EditorError
from backend.tools.meetings import service

router = APIRouter(prefix="/api/meetings", tags=["Comptes rendus et PV"])


def _guard(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except (service.MeetingError, EditorError, ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e).strip("'"))
    except unified_db.UnifiedDbUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Erreur de base de données : {e}")


@router.get("/context")
def context():
    def load():
        with unified_db.connect() as conn:
            return {"kinds": service.KINDS, "statuses": service.STATUSES, "action_statuses": service.ACTION_STATUSES,
                    "projects": [dict(id=r["Id"], code=r["Code"], name=r["Name"]) for r in conn.execute(
                        "SELECT Id, Code, Name FROM Projects WHERE IsDeleted = 0 AND Code <> ? ORDER BY Code", (service.GOVERNANCE_CODE,))],
                    "tasks": [dict(id=r["Id"], project_id=r["ProjectId"], name=r["Name"]) for r in conn.execute("SELECT Id, ProjectId, Name FROM Tasks ORDER BY Name")]}
    return _guard(load)


@router.get("")
def list_meetings(project_id: Optional[int] = None, year: Optional[int] = None, kind: Optional[str] = None, governance: bool = False):
    return _guard(service.list_meetings, project_id, year, kind, governance)


@router.get("/actions/open")
def open_actions(project_id: Optional[int] = None):
    return _guard(service.open_actions, project_id)


@router.put("/actions/{action_id}/status")
def action_status(action_id: int, data: Dict[str, Any]):
    return _guard(service.set_action_status, action_id, data.get("status", ""))


@router.post("/actions/{action_id}/task")
def action_task(action_id: int):
    return _guard(service.create_task, action_id)


@router.get("/{meeting_id}")
def get_meeting(meeting_id: int):
    return _guard(service.get, meeting_id)


@router.post("")
def save_meeting(data: Dict[str, Any]):
    return _guard(service.save, data)


@router.delete("/{meeting_id}")
def delete_meeting(meeting_id: int):
    _guard(service.delete, meeting_id)
    return {"deleted": meeting_id}


@router.post("/{meeting_id}/document")
def write_document(meeting_id: int):
    return _guard(service.write_document, meeting_id)


@router.post("/{meeting_id}/extract")
def extract(meeting_id: int):
    return _guard(service.extract, meeting_id)


@router.post("/{meeting_id}/validate")
async def validate(meeting_id: int):
    try:
        return await service.validate(meeting_id)
    except (service.MeetingError, EditorError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
