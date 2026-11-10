import json
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from backend.core.database import get_db, AgentConfigModel, AdminDocumentModel
from backend.core.agent_registry import agent_registry
from backend.tools.exporters import export_to_docx

router = APIRouter(prefix="/api/agents", tags=["Agents"])

class AgentRunRequest(BaseModel):
    message: str
    context_data: Optional[Dict[str, Any]] = None
    images_b64: Optional[List[str]] = None
    language: Optional[str] = "ar"

class AgentConfigUpdateRequest(BaseModel):
    system_prompt: Optional[str] = None
    temperature: Optional[float] = None
    model_provider: Optional[str] = None
    model_name: Optional[str] = None
    active_tools: Optional[List[str]] = None
    custom_instructions: Optional[str] = None
    is_active: Optional[bool] = None

class ToolExecutionRequest(BaseModel):
    tool_name: str
    parameters: Dict[str, Any] = {}

class DocExportRequest(BaseModel):
    title: str
    content: str
    doc_type: Optional[str] = "Document Institutionnel AFMI"
    agent_id: Optional[str] = "agent_grant_writer"

@router.get("")
def list_agents():
    """List all agents with their current configs and dynamic tools."""
    return agent_registry.list_agents()

@router.get("/{agent_id}")
def get_agent_details(agent_id: str):
    agent = agent_registry.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent non trouvé.")
    return {
        "id": agent.agent_id,
        "name_ar": agent.name_ar,
        "name_fr": agent.name_fr,
        "role_ar": agent.role_ar,
        "role_fr": agent.role_fr,
        "description": agent.description,
        "system_prompt": agent.system_prompt,
        "temperature": agent.temperature,
        "model_provider": agent.model_provider,
        "model_name": agent.model_name,
        "active_tools": agent.active_tools,
        "registered_tools": [
            {"name": name, "description": data["description"]}
            for name, data in agent.tools.items()
        ],
        "custom_instructions": agent.custom_instructions,
        "is_active": agent.is_active
    }

@router.post("/{agent_id}/run")
async def run_agent(agent_id: str, req: AgentRunRequest):
    agent = agent_registry.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent non trouvé.")
    
    result = await agent.run(
        user_message=req.message,
        context_data=req.context_data,
        images_b64=req.images_b64,
        language=req.language or "ar"
    )
    return result

@router.put("/{agent_id}/config")
def update_agent_config(agent_id: str, req: AgentConfigUpdateRequest, db: Session = Depends(get_db)):
    cfg = db.query(AgentConfigModel).filter(AgentConfigModel.id == agent_id).first()
    if not cfg:
        raise HTTPException(status_code=404, detail="Configuration d'agent introuvable.")

    if req.system_prompt is not None:
        cfg.system_prompt = req.system_prompt
    if req.temperature is not None:
        cfg.temperature = req.temperature
    if req.model_provider is not None:
        cfg.model_provider = req.model_provider
    if req.model_name is not None:
        cfg.model_name = req.model_name
    if req.active_tools is not None:
        cfg.active_tools = json.dumps(req.active_tools)
    if req.custom_instructions is not None:
        cfg.custom_instructions = req.custom_instructions
    if req.is_active is not None:
        cfg.is_active = req.is_active

    db.commit()
    db.refresh(cfg)

    # Reload agent in memory
    agent = agent_registry.get_agent(agent_id)
    if agent:
        agent.load_config()

    return {"status": "success", "message": "Configuration mise à jour avec succès."}

@router.post("/{agent_id}/execute-tool")
async def execute_agent_tool(agent_id: str, req: ToolExecutionRequest):
    agent = agent_registry.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent non trouvé.")

    try:
        res = await agent.execute_tool(req.tool_name, **req.parameters)
        return {"status": "success", "result": res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/export-doc")
def export_document_docx(req: DocExportRequest, db: Session = Depends(get_db)):
    agent = agent_registry.get_agent(req.agent_id or "agent_grant_writer")
    agent_name = agent.name_fr if agent else "AFMI AI Agent"
    
    sections = [{"title": req.title, "content": req.content}]
    file_path = export_to_docx(
        title=req.title,
        sections=sections,
        doc_type=req.doc_type or "Document Technique",
        agent_name=agent_name
    )
    
    # Save to AdminDocuments
    admin_doc = AdminDocumentModel(
        title=req.title,
        doc_type="rapport_technique",
        language="bilingual",
        content=req.content,
        agent_id=req.agent_id,
        file_path=file_path
    )
    db.add(admin_doc)
    db.commit()

    return {
        "status": "success",
        "file_path": file_path,
        "filename": file_path.split("\\")[-1].split("/")[-1],
        "message": "Fichier Word (.docx) généré avec succès avec la charte AFMI."
    }
