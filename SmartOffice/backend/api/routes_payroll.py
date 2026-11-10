import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.config.settings import settings
from backend.core.database import EmployeeModel, IrPaymentModel, PayslipModel, get_db
from backend.tools import edi_9421, payroll_exports
from backend.tools.payroll_ma import PayInput, compute_payslip, deadlines_for_period, load_rules, parse_period

router = APIRouter(prefix="/api/payroll", tags=["Paie & Déclarations"])

PERIOD_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"


class EmployeeRequest(BaseModel):
    matricule: str = Field(min_length=1, max_length=30)
    full_name: str = Field(min_length=1, max_length=150)
    cin: Optional[str] = ""
    cnss_number: Optional[str] = ""
    address: Optional[str] = ""
    position: Optional[str] = ""
    hire_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    dependents: int = Field(default=0, ge=0, le=20)
    marital_status: str = Field(default="celibataire", pattern=r"^(celibataire|marie|divorce|veuf)$")
    base_salary: float = Field(default=0.0, ge=0)
    pension_employee_rate: float = Field(default=0.0, ge=0, le=0.2)
    cnss_affiliated: bool = True
    rib: Optional[str] = ""
    active: bool = True


class PayVariables(BaseModel):
    overtime_hours_25: float = Field(default=0.0, ge=0)
    overtime_hours_50: float = Field(default=0.0, ge=0)
    overtime_hours_100: float = Field(default=0.0, ge=0)
    taxable_bonuses: float = Field(default=0.0, ge=0)
    exempt_allowances: float = Field(default=0.0, ge=0)
    benefits_in_kind: float = Field(default=0.0, ge=0)
    housing_loan_interest: float = Field(default=0.0, ge=0)


class SimulationRequest(PayVariables):
    period: str = Field(pattern=PERIOD_PATTERN)
    base_salary: float = Field(ge=0)
    hire_date: Optional[str] = None
    dependents: int = Field(default=0, ge=0, le=20)
    pension_employee_rate: float = Field(default=0.0, ge=0, le=0.2)
    cnss_affiliated: bool = True
    rules_version: Optional[str] = None


class PayrollRunRequest(BaseModel):
    variables: Dict[int, PayVariables] = {}   # employee_id -> variables du mois
    rules_version: Optional[str] = None


def _employee_dict(e: EmployeeModel) -> Dict[str, Any]:
    return {c.name: getattr(e, c.name) for c in EmployeeModel.__table__.columns if c.name != "created_at"}


def _payslip_dict(p: PayslipModel, e: Optional[EmployeeModel]) -> Dict[str, Any]:
    return {
        "id": p.id, "employee_id": p.employee_id, "period": p.period, "rules_version": p.rules_version,
        "status": p.status, "lines": json.loads(p.lines_json or "{}"), "warnings": json.loads(p.warnings_json or "[]"),
        "inputs": json.loads(p.inputs_json or "{}"),
        "matricule": e.matricule if e else "?", "full_name": e.full_name if e else "Salarié supprimé",
        "cin": e.cin if e else "", "cnss_number": e.cnss_number if e else "", "dependents": e.dependents if e else 0,
    }


def _profile() -> Dict[str, Any]:
    try:
        with open(settings.ngo_profile_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _export_response(path: str) -> Dict[str, str]:
    return {"status": "success", "filename": Path(path).name, "file_path": path}


# --- Rules -----------------------------------------------------------------

@router.get("/rules")
def get_rules():
    rules = load_rules()
    return {"versions": [{k: v[k] for k in ("id", "label", "valid_from", "valid_to", "legal_ref")}
                         for v in rules["versions"]],
            "deadlines": rules["common"]["deadlines"], "portals": rules["common"]["portals"]}


# --- Employees -------------------------------------------------------------

@router.get("/employees")
def list_employees(db: Session = Depends(get_db)):
    return [_employee_dict(e) for e in db.query(EmployeeModel).order_by(EmployeeModel.full_name).all()]


@router.post("/employees")
def create_employee(req: EmployeeRequest, db: Session = Depends(get_db)):
    if db.query(EmployeeModel).filter(EmployeeModel.matricule == req.matricule).first():
        raise HTTPException(status_code=400, detail="Un salarié avec ce matricule existe déjà.")
    e = EmployeeModel(**req.model_dump())
    db.add(e)
    db.commit()
    db.refresh(e)
    return _employee_dict(e)


@router.put("/employees/{employee_id}")
def update_employee(employee_id: int, req: EmployeeRequest, db: Session = Depends(get_db)):
    e = db.query(EmployeeModel).filter(EmployeeModel.id == employee_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Salarié introuvable.")
    clash = db.query(EmployeeModel).filter(EmployeeModel.matricule == req.matricule, EmployeeModel.id != employee_id).first()
    if clash:
        raise HTTPException(status_code=400, detail="Ce matricule est déjà utilisé.")
    for k, v in req.model_dump().items():
        setattr(e, k, v)
    db.commit()
    return _employee_dict(e)


@router.delete("/employees/{employee_id}")
def delete_employee(employee_id: int, db: Session = Depends(get_db)):
    e = db.query(EmployeeModel).filter(EmployeeModel.id == employee_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Salarié introuvable.")
    if db.query(PayslipModel).filter(PayslipModel.employee_id == employee_id).count():
        # Payslips must stay traceable for the état 9421 and audits: deactivate instead of deleting.
        e.active = False
        db.commit()
        return {"status": "success", "message": "Salarié désactivé (des bulletins existent, il ne peut être supprimé)."}
    db.delete(e)
    db.commit()
    return {"status": "success", "message": "Salarié supprimé."}


# --- Payroll ---------------------------------------------------------------

@router.post("/simulate")
def simulate(req: SimulationRequest):
    try:
        return compute_payslip(PayInput(**req.model_dump())).to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/runs/{period}")
def run_payroll(period: str, req: PayrollRunRequest, db: Session = Depends(get_db)):
    """Computes (or recomputes) draft payslips of every active employee. Validated payslips are never overwritten."""
    try:
        parse_period(period)
    except ValueError:
        raise HTTPException(status_code=400, detail="Période invalide (format AAAA-MM).")
    employees = db.query(EmployeeModel).filter(EmployeeModel.active == True).all()  # noqa: E712
    if not employees:
        raise HTTPException(status_code=400, detail="Aucun salarié actif.")

    computed, locked, errors = 0, 0, []
    for e in employees:
        existing = db.query(PayslipModel).filter(PayslipModel.employee_id == e.id, PayslipModel.period == period).first()
        if existing and existing.status == "validated":
            locked += 1
            continue
        variables = req.variables.get(e.id, PayVariables())
        inp = PayInput(period=period, base_salary=e.base_salary or 0.0, hire_date=e.hire_date,
                       dependents=e.dependents or 0, pension_employee_rate=e.pension_employee_rate or 0.0,
                       cnss_affiliated=bool(e.cnss_affiliated), rules_version=req.rules_version,
                       **variables.model_dump())
        try:
            result = compute_payslip(inp)
        except ValueError as ex:
            errors.append(f"{e.full_name} : {ex}")
            continue
        lines = result.to_dict()["lines"]
        p = existing or PayslipModel(employee_id=e.id, period=period)
        p.rules_version = result.rules_version
        p.inputs_json = json.dumps(variables.model_dump())
        p.lines_json = json.dumps(lines)
        p.warnings_json = json.dumps(result.warnings, ensure_ascii=False)
        p.gross_taxable = lines["salaire_brut_imposable"]
        p.net_taxable = lines["salaire_net_imposable"]
        p.ir_withheld = lines["ir_net"]
        p.net_pay = lines["net_a_payer"]
        p.status = "draft"
        if not existing:
            db.add(p)
        computed += 1
    db.commit()
    return {"status": "success", "computed": computed, "locked": locked, "errors": errors}


@router.get("/payslips")
def list_payslips(period: str, db: Session = Depends(get_db)):
    employees = {e.id: e for e in db.query(EmployeeModel).all()}
    slips = db.query(PayslipModel).filter(PayslipModel.period == period).all()
    return sorted((_payslip_dict(p, employees.get(p.employee_id)) for p in slips), key=lambda x: x["full_name"])


@router.post("/payslips/{payslip_id}/validate")
def validate_payslip(payslip_id: int, db: Session = Depends(get_db)):
    p = db.query(PayslipModel).filter(PayslipModel.id == payslip_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Bulletin introuvable.")
    p.status = "validated"
    db.commit()
    return {"status": "success"}


@router.post("/periods/{period}/validate")
def validate_period(period: str, db: Session = Depends(get_db)):
    n = db.query(PayslipModel).filter(PayslipModel.period == period, PayslipModel.status == "draft") \
          .update({PayslipModel.status: "validated"})
    db.commit()
    return {"status": "success", "validated": n}


@router.post("/payslips/{payslip_id}/export-docx")
def export_payslip(payslip_id: int, db: Session = Depends(get_db)):
    p = db.query(PayslipModel).filter(PayslipModel.id == payslip_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Bulletin introuvable.")
    e = db.query(EmployeeModel).filter(EmployeeModel.id == p.employee_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Salarié introuvable.")
    return _export_response(payroll_exports.export_payslip_docx(_payslip_dict(p, e), _employee_dict(e), _profile()))


# --- Declarations ----------------------------------------------------------

def _period_slips(period: str, db: Session) -> List[Dict[str, Any]]:
    return list_payslips(period, db)


@router.get("/declarations/monthly/{period}")
def monthly_declaration(period: str, db: Session = Depends(get_db)):
    try:
        deadlines = deadlines_for_period(period)
    except ValueError:
        raise HTTPException(status_code=400, detail="Période invalide (format AAAA-MM).")
    slips = _period_slips(period, db)
    total = lambda key: round(sum(s["lines"].get(key, 0) for s in slips), 2)
    rules = load_rules()["common"]
    missing = [s["full_name"] for s in slips if not s.get("cnss_number")]
    return {
        "period": period,
        "payslips": len(slips),
        "drafts": sum(1 for s in slips if s["status"] != "validated"),
        "ir": {"total_withheld": total("ir_net"), "taxable_base": total("salaire_brut_imposable"),
               "deadline": deadlines["ir_versement"], "portal": rules["portals"]["dgi_simpl"],
               "rule": rules["deadlines"]["ir_monthly"]},
        "cnss": {"employee": total("cnss_salarie"), "employer": total("cnss_patronal"),
                 "allocations_familiales": total("allocations_familiales"),
                 "tfp": total("taxe_formation_professionnelle"),
                 "amo": round(total("amo_salarie") + total("amo_patronal"), 2),
                 "total_due": round(total("cnss_salarie") + total("cnss_patronal") + total("allocations_familiales")
                                    + total("taxe_formation_professionnelle") + total("amo_salarie")
                                    + total("amo_patronal"), 2),
                 "deadline": deadlines["cnss_bds"], "portal": rules["portals"]["cnss_damancom"],
                 "rule": rules["deadlines"]["cnss_monthly"], "missing_cnss_numbers": missing},
        "net_to_pay": total("net_a_payer"),
    }


@router.post("/declarations/monthly/{period}/export")
def export_monthly(period: str, kind: str = "ledger", db: Session = Depends(get_db)):
    slips = _period_slips(period, db)
    if not slips:
        raise HTTPException(status_code=400, detail="Aucun bulletin pour cette période.")
    exporters = {"ledger": payroll_exports.export_payroll_ledger, "cnss": payroll_exports.export_cnss_recap,
                 "ir": payroll_exports.export_ir_monthly}
    if kind not in exporters:
        raise HTTPException(status_code=400, detail="Type d'export inconnu (ledger, cnss, ir).")
    return _export_response(exporters[kind](period, slips, _profile()))


def _annual_rows(year: int, db: Session) -> List[Dict[str, Any]]:
    slips = db.query(PayslipModel).filter(PayslipModel.period.like(f"{year}-%")).all()
    employees = {e.id: e for e in db.query(EmployeeModel).all()}
    keys = ["salaire_brut_global", "avantages_en_nature", "indemnites_exonerees", "salaire_brut_imposable",
            "frais_professionnels", "retraite_complementaire_salarie", "interets_logement",
            "salaire_net_imposable", "ir_net"]
    agg: Dict[int, Dict[str, Any]] = {}
    for p in slips:
        e = employees.get(p.employee_id)
        lines = json.loads(p.lines_json or "{}")
        row = agg.setdefault(p.employee_id, {
            "employee_id": p.employee_id, "full_name": e.full_name if e else "?", "address": e.address if e else "",
            "cin": e.cin if e else "", "cnss_number": e.cnss_number if e else "",
            "matricule": e.matricule if e else "", "marital_status": (e.marital_status if e else None) or "celibataire",
            "dependents": e.dependents if e else 0, "months": 0, "cotisations_sociales": 0.0, "drafts": 0,
            "ir_by_month": {}, **{k: 0.0 for k in keys}})
        row["months"] += 1
        row["drafts"] += 1 if p.status != "validated" else 0
        row["ir_by_month"][p.period] = lines.get("ir_net", 0)
        for k in keys:
            row[k] = round(row[k] + lines.get(k, 0), 2)
        row["cotisations_sociales"] = round(row["cotisations_sociales"] + lines.get("cnss_salarie", 0)
                                            + lines.get("amo_salarie", 0), 2)
    return sorted(agg.values(), key=lambda r: r["full_name"])


@router.get("/declarations/9421/{year}")
def etat_9421(year: int, db: Session = Depends(get_db)):
    rows = _annual_rows(year, db)
    rules = load_rules()["common"]
    checks = []
    for r in rows:
        if not r["cin"]:
            checks.append(f"{r['full_name']} : CIN manquante (obligatoire dans l'état 9421).")
        if r["drafts"]:
            checks.append(f"{r['full_name']} : {r['drafts']} bulletin(s) non validé(s).")
    return {"year": year, "employees": rows, "total_ir": round(sum(r["ir_net"] for r in rows), 2),
            "deadline": deadlines_for_period(f"{year}-12")["etat_9421"], "portal": rules["portals"]["dgi_simpl"],
            "rule": rules["deadlines"]["etat_9421_annual"], "checks": checks}


@router.post("/declarations/9421/{year}/export")
def export_9421(year: int, db: Session = Depends(get_db)):
    rows = _annual_rows(year, db)
    if not rows:
        raise HTTPException(status_code=400, detail="Aucun bulletin pour cette année.")
    return _export_response(payroll_exports.export_etat_9421(year, rows, _profile()))


# --- IR payments (listVersements) ------------------------------------------

class IrPaymentRequest(BaseModel):
    period: str = Field(pattern=PERIOD_PATTERN)
    amount: float = Field(gt=0)
    principal: Optional[float] = Field(default=None, ge=0)
    penalty: float = Field(default=0.0, ge=0)
    surcharge: float = Field(default=0.0, ge=0)
    payment_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    reference: Optional[str] = ""
    receipt_number: Optional[str] = ""
    payment_method: str = Field(default="teleservice", pattern=r"^(especes|cheque|virement|teleservice)$")


def _payment_dict(p: IrPaymentModel) -> Dict[str, Any]:
    return {c.name: getattr(p, c.name) for c in IrPaymentModel.__table__.columns if c.name != "created_at"}


@router.get("/ir-payments")
def list_ir_payments(year: int, db: Session = Depends(get_db)):
    rows = db.query(IrPaymentModel).filter(IrPaymentModel.period.like(f"{year}-%")) \
             .order_by(IrPaymentModel.period, IrPaymentModel.payment_date).all()
    return [_payment_dict(p) for p in rows]


@router.post("/ir-payments")
def add_ir_payment(req: IrPaymentRequest, db: Session = Depends(get_db)):
    data = req.model_dump()
    data["principal"] = data["principal"] if data["principal"] is not None else data["amount"] - data["penalty"] - data["surcharge"]
    p = IrPaymentModel(**data)
    db.add(p)
    db.commit()
    db.refresh(p)
    return _payment_dict(p)


@router.delete("/ir-payments/{payment_id}")
def delete_ir_payment(payment_id: int, db: Session = Depends(get_db)):
    p = db.query(IrPaymentModel).filter(IrPaymentModel.id == payment_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Versement introuvable.")
    db.delete(p)
    db.commit()
    return {"status": "success"}


# --- EDI 9421 (Simpl-IR) ---------------------------------------------------

@router.get("/edi/config")
def get_edi_config():
    cfg = edi_9421.load_config()
    schema = edi_9421.find_schema()
    return {"config": cfg, "employer_effective": edi_9421.employer_values(cfg, _profile()),
            "schema_file": schema.name if schema else None, "schemas_dir": str(settings.edi_schemas_dir)}


@router.put("/edi/config")
def put_edi_config(data: Dict[str, Any]):
    current = edi_9421.load_config()
    for section in ("employer", "codes", "options"):
        if section in data and not isinstance(data[section], dict):
            raise HTTPException(status_code=400, detail=f"Section « {section} » invalide.")
    merged = {**current, **{k: data[k] for k in ("employer", "codes", "options") if k in data}}
    edi_9421.save_config(merged)
    return {"status": "success"}


def _edi_inputs(year: int, db: Session):
    rows = _annual_rows(year, db)
    payments = list_ir_payments(year, db)
    return rows, payments, edi_9421.load_config(), _profile()


@router.get("/declarations/9421/{year}/edi/preflight")
def edi_preflight(year: int, db: Session = Depends(get_db)):
    rows, payments, cfg, profile = _edi_inputs(year, db)
    result = edi_9421.preflight(year, rows, payments, cfg, profile)
    schema = edi_9421.find_schema()
    result["schema_file"] = schema.name if schema else None
    result["spec_version"] = cfg.get("spec_version")
    return result


@router.post("/declarations/9421/{year}/edi")
def edi_export(year: int, db: Session = Depends(get_db)):
    rows, payments, cfg, profile = _edi_inputs(year, db)
    check = edi_9421.preflight(year, rows, payments, cfg, profile)
    if check["errors"]:
        raise HTTPException(status_code=400, detail="Export bloqué : " + " | ".join(check["errors"]))
    xml_bytes = edi_9421.build_xml(year, rows, payments, cfg, profile)
    validation = edi_9421.validate_against_schema(xml_bytes)
    if validation["schema"] and not validation["validated"]:
        raise HTTPException(status_code=400, detail="Fichier non conforme au schéma "
                            f"{validation['schema']} : " + " | ".join(validation["errors"][:10]))
    try:
        path = edi_9421.package(year, xml_bytes, edi_9421.employer_values(cfg, profile)["identifiant_fiscal"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {**_export_response(path), "schema_validated": validation["validated"],
            "schema_file": validation["schema"], "warnings": check["warnings"]}
