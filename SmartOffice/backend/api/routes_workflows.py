from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core.agent_registry import agent_registry
from backend.core import orchestrator
from backend.tools.exporters import export_to_docx

router = APIRouter(prefix="/api/workflows", tags=["Multi-Agent Workflows"])


class WorkflowRunRequest(BaseModel):
    inputs: Dict[str, Any] = {}
    language: Optional[str] = "fr"


@router.get("")
def list_workflows():
    """Available multi-agent workflows with their inputs and step chain."""
    return [w.to_public() for w in orchestrator.WORKFLOWS.values()]


@router.post("/{workflow_id}/runs")
async def start_workflow(workflow_id: str, req: WorkflowRunRequest):
    workflow = orchestrator.WORKFLOWS.get(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Chaîne d'agents introuvable.")
    missing = orchestrator.validate_inputs(workflow, req.inputs)
    if missing:
        raise HTTPException(status_code=400, detail=f"Champs obligatoires manquants : {', '.join(missing)}")
    language = req.language if req.language in ("ar", "fr", "en") else "fr"

    run_id = orchestrator.create_run(workflow_id, req.inputs, language)
    orchestrator.start_run_in_background(run_id, agent_registry.get_agent)
    return orchestrator.get_run(run_id)


@router.get("/runs")
def list_workflow_runs(limit: int = 30):
    return orchestrator.list_runs(limit=max(1, min(limit, 200)))


@router.get("/runs/{run_id}")
def get_workflow_run(run_id: str):
    run = orchestrator.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Exécution introuvable.")
    return run


@router.post("/runs/{run_id}/export-docx")
def export_workflow_run(run_id: str):
    run = orchestrator.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Exécution introuvable.")
    sections = [{"title": s["title_fr"], "content": s["output"]} for s in run["steps"] if s["status"] == "completed"]
    if not sections:
        raise HTTPException(status_code=400, detail="Aucune étape terminée à exporter.")
    workflow = orchestrator.WORKFLOWS.get(run["workflow_id"])
    file_path = export_to_docx(
        title=run["title"],
        sections=sections,
        doc_type=workflow.name_fr if workflow else "Dossier multi-agents",
        agent_name="Chaîne d'agents AFMI (Rédaction · Suivi · Finance · Communication)",
    )
    return {"status": "success", "file_path": file_path, "filename": Path(file_path).name}
