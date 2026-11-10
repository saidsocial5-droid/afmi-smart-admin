import asyncio
import time
from types import SimpleNamespace

from backend.core import orchestrator
from backend.core.database import init_db


class FakeAgent:
    def __init__(self, agent_id, fail=False, calls=None):
        self.agent_id = agent_id
        self.fail = fail
        self.calls = calls if calls is not None else []

    async def run(self, user_message, language="fr", **kwargs):
        self.calls.append((self.agent_id, user_message))
        if self.fail:
            raise RuntimeError("LLM indisponible")
        return {"response": f"SORTIE<{self.agent_id}>", "model_used": "fake:test"}


def _run(workflow_id, inputs, failing=()):
    init_db()
    calls = []
    agents = {a: FakeAgent(a, fail=a in failing, calls=calls) for a in
              ("agent_grant_writer", "agent_project_manager", "agent_finance_auditor", "agent_communications")}
    run_id = orchestrator.create_run(workflow_id, inputs, "fr")
    result = asyncio.run(orchestrator.execute_run(run_id, agents.get))
    return result, calls


def test_workflow_dependencies_reference_previous_steps():
    for wf in orchestrator.WORKFLOWS.values():
        seen = set()
        for step in wf.steps:
            assert set(step.depends_on) <= seen, f"{wf.id}.{step.id} depends on a later step"
            assert set(step.context) <= set(orchestrator.CONTEXT_PROVIDERS)
            seen.add(step.id)


def test_full_chain_hands_off_outputs():
    result, calls = _run("montage_proposition", {"opportunity": "Appel FEM", "idea": "Reboisement cèdre"})
    assert result["status"] == "completed"
    assert all(s["status"] == "completed" for s in result["steps"])
    # The concept note step must receive eligibility, logframe and budget outputs as isolated data blocks
    note_prompt = calls[3][1]
    assert "SORTIE<agent_grant_writer>" in note_prompt
    assert "SORTIE<agent_project_manager>" in note_prompt
    assert "SORTIE<agent_finance_auditor>" in note_prompt
    assert "<<<UNTRUSTED_DOCUMENT_DATA" in note_prompt
    assert "Reboisement cèdre" in calls[0][1]


def test_failed_step_skips_dependents_and_reports_partial():
    result, calls = _run("montage_proposition", {"opportunity": "Appel", "idea": "Idée"},
                         failing=("agent_finance_auditor",))
    by_id = {s["id"]: s for s in result["steps"]}
    assert by_id["budget"]["status"] == "failed"
    assert by_id["budget"]["attempts"] == 2  # retried once
    assert by_id["note_conceptuelle"]["status"] == "skipped"
    assert by_id["communication"]["status"] == "skipped"
    assert by_id["eligibilite"]["status"] == "completed"
    assert result["status"] == "partial"


def test_all_failed_is_failed():
    result, _ = _run("audit_depenses", {}, failing=("agent_finance_auditor",))
    assert result["status"] == "failed"


def test_audit_rules():
    tx = lambda **k: SimpleNamespace(**{"id": 1, "debit": 0.0, "label": "x", "tax_id_ice": "", "category": "Matériel",
                                        "reference": "", **k})
    findings = orchestrator.run_expense_audit_checks([
        tx(id=1, debit=600000.0, tax_id_ice="001894235000088", reference="A"),
        tx(id=2, debit=8000.0, reference="A"),
        tx(id=3, debit=100.0, tax_id_ice="123"),
        tx(id=4, debit=50.0, category="Divers"),
    ])
    rules = [f["rule"] for f in findings]
    assert rules[0] == "seuil_bon_de_commande"
    assert {"ice_manquant", "doublon_reference", "ice_invalide", "non_categorise"} <= set(rules)


def test_api_lists_and_validates(client):
    workflows = client.get("/api/workflows").json()
    assert {w["id"] for w in workflows} >= {"montage_proposition", "rapport_bailleur", "audit_depenses"}
    r = client.post("/api/workflows/montage_proposition/runs", json={"inputs": {}})
    assert r.status_code == 400
    assert client.post("/api/workflows/inconnu/runs", json={"inputs": {}}).status_code == 404


def test_api_runs_workflow_end_to_end_with_offline_engine(client):
    # No API key and no Ollama: the heuristic engine answers, so the chain must still complete.
    r = client.post("/api/workflows/audit_depenses/runs", json={"inputs": {"scope": "T3"}, "language": "fr"})
    assert r.status_code == 200
    run_id = r.json()["id"]
    deadline = time.time() + 60
    while time.time() < deadline:
        run = client.get(f"/api/workflows/runs/{run_id}").json()
        if run["status"] not in ("pending", "running"):
            break
        time.sleep(0.3)
    assert run["status"] == "completed", run
    # No key and no Ollama: the UI must show the engine that really answered
    assert all(s["model_used"] == "heuristic" for s in run["steps"])
    exported = client.post(f"/api/workflows/runs/{run_id}/export-docx").json()
    assert exported["filename"].endswith(".docx")
    assert any(r["id"] == run_id for r in client.get("/api/workflows/runs").json())
