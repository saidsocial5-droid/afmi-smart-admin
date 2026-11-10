import os

from backend.config.settings import settings


def _employee(client, matricule, **kw):
    body = {"matricule": matricule, "full_name": f"Salarié {matricule}", "cin": "D123456", "cnss_number": "123456789",
            "hire_date": "2019-01-15", "dependents": 2, "base_salary": 10000, **kw}
    r = client.post("/api/payroll/employees", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def test_payroll_month_to_declarations(client):
    e1 = _employee(client, "P001")
    _employee(client, "P002", base_salary=5000, dependents=0, hire_date="2025-06-01", cin="")
    assert client.post("/api/payroll/employees", json={"matricule": "P001", "full_name": "x"}).status_code == 400

    # Other tests share the database: count every active employee
    n = sum(1 for e in client.get("/api/payroll/employees").json() if e["active"])
    r = client.post("/api/payroll/runs/2026-01", json={"variables": {str(e1["id"]): {"taxable_bonuses": 1000}}})
    assert r.json()["computed"] == n

    slips = client.get("/api/payroll/payslips", params={"period": "2026-01"}).json()
    s1 = next(s for s in slips if s["matricule"] == "P001")
    assert s1["rules_version"] == "LF2026"
    assert s1["lines"]["prime_anciennete"] > 0          # 7 ans -> 10 %
    assert s1["lines"]["primes_imposables"] == 1000

    decl = client.get("/api/payroll/declarations/monthly/2026-01").json()
    assert decl["ir"]["total_withheld"] == round(sum(s["lines"]["ir_net"] for s in slips), 2)
    assert decl["ir"]["deadline"] == "2026-02-28"
    assert decl["cnss"]["deadline"] == "2026-02-10"
    assert decl["drafts"] == n

    # Validated payslips are locked against recomputation
    client.post("/api/payroll/periods/2026-01/validate")
    assert client.post("/api/payroll/runs/2026-01", json={}).json()["locked"] == n

    for kind in ("ledger", "cnss", "ir"):
        out = client.post(f"/api/payroll/declarations/monthly/2026-01/export", params={"kind": kind}).json()
        assert os.path.exists(os.path.join(settings.exports_dir, out["filename"]))
    doc = client.post(f"/api/payroll/payslips/{s1['id']}/export-docx").json()
    assert doc["filename"].endswith(".docx")

    etat = client.get("/api/payroll/declarations/9421/2026").json()
    assert len(etat["employees"]) == n
    assert etat["deadline"] == "2027-02-28"
    assert any("CIN manquante" in c for c in etat["checks"])
    assert client.post("/api/payroll/declarations/9421/2026/export").json()["filename"].endswith(".xlsx")


def test_historic_period_uses_lf2017(client):
    r = client.post("/api/payroll/simulate", json={"period": "2017-06", "base_salary": 5000, "dependents": 2})
    assert r.json()["rules_version"] == "LF2017"
    assert r.json()["lines"]["net_a_payer"] == 4606.70
    assert client.post("/api/payroll/simulate", json={"period": "2016-05", "base_salary": 5000}).status_code == 400
    assert client.post("/api/payroll/simulate", json={"period": "2026-13", "base_salary": 5000}).status_code == 422


def test_employee_with_payslips_is_deactivated_not_deleted(client):
    e = _employee(client, "P900")
    client.post("/api/payroll/runs/2026-02", json={})
    r = client.delete(f"/api/payroll/employees/{e['id']}")
    assert "désactivé" in r.json()["message"]
    assert any(x["id"] == e["id"] and not x["active"] for x in client.get("/api/payroll/employees").json())


def test_finance_agent_can_compute_payslip(client):
    from backend.core.agent_registry import agent_registry
    import asyncio
    agent = agent_registry.get_agent("agent_finance_auditor")
    res = asyncio.run(agent.execute_tool("calculate_payslip_ma", period="2026-01", base_salary=10000))
    assert res["lines"]["ir_net"] == 601.56
