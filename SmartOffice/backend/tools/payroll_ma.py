"""
Moroccan payroll engine: gross-to-net, CNSS/AMO, professional expenses, IR withheld at source (CGI art. 73-74),
employer charges. Pure functions (no DB, no LLM) so results are deterministic and testable.

Rules are dated (backend/config/payroll_rules_ma.json): the version whose period covers the pay month is used,
unless a version is forced (e.g. recomputing 2017 payslips under LF 2017). Monetary amounts use Decimal and are
rounded half-up to the centime at each line of the payslip, as on a paper bulletin.
"""
import json
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from functools import lru_cache
from typing import Any, Dict, List, Optional

from backend.config.settings import settings

CENT = Decimal("0.01")


def _d(value: Any) -> Decimal:
    return Decimal(str(value or 0))


def _round(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


@lru_cache(maxsize=1)
def load_rules() -> Dict[str, Any]:
    with open(settings.payroll_rules_path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_period(period: str) -> date:
    """'YYYY-MM' -> first day of month. Raises ValueError on bad input."""
    year, month = period.split("-")
    return date(int(year), int(month), 1)


def rules_for_period(period: str, version_id: Optional[str] = None) -> Dict[str, Any]:
    rules = load_rules()
    if version_id:
        for v in rules["versions"]:
            if v["id"] == version_id:
                return v
        raise ValueError(f"Version de règles inconnue : {version_id}")
    parse_period(period)  # validates format
    for v in rules["versions"]:
        if v["valid_from"] <= period and (v["valid_to"] is None or period <= v["valid_to"]):
            return v
    raise ValueError(f"Aucune règle de paie disponible pour la période {period} (couverture : 2017-01 et après).")


def seniority_rate(hire_date: Optional[str], period: str) -> Decimal:
    """Prime d'ancienneté rate from completed years of service at the pay month (Code du travail art. 350)."""
    if not hire_date:
        return Decimal("0")
    start = date.fromisoformat(hire_date[:10])
    month = parse_period(period)
    years = month.year - start.year - ((month.month, 1) < (start.month, start.day))
    for bracket in load_rules()["common"]["seniority_brackets"]:
        if years >= bracket["min_years"]:
            return _d(bracket["rate"])
    return Decimal("0")


def annual_ir(net_taxable_annual: Decimal, brackets: List[Dict[str, Any]]) -> Decimal:
    for b in brackets:
        if b["upto"] is None or net_taxable_annual <= _d(b["upto"]):
            return max(Decimal("0"), net_taxable_annual * _d(b["rate"]) - _d(b["deduction"]))
    raise ValueError("Barème IR invalide (dernière tranche sans plafond manquante).")


@dataclass
class PayInput:
    period: str                                  # "YYYY-MM"
    base_salary: float                           # salaire de base mensuel
    hire_date: Optional[str] = None              # "YYYY-MM-DD" (prime d'ancienneté)
    dependents: int = 0                          # personnes à charge (conjoint + enfants), CGI art. 74
    overtime_hours_25: float = 0.0
    overtime_hours_50: float = 0.0
    overtime_hours_100: float = 0.0
    taxable_bonuses: float = 0.0                 # primes et indemnités imposables
    exempt_allowances: float = 0.0               # indemnités exonérées (transport, panier… dans les limites légales)
    benefits_in_kind: float = 0.0                # avantages en nature imposables
    pension_employee_rate: float = 0.0           # retraite complémentaire (CIMR…) part salariale, ex. 0.06
    housing_loan_interest: float = 0.0           # intérêts prêt logement principal déductibles (mensuel)
    cnss_affiliated: bool = True
    rules_version: Optional[str] = None


@dataclass
class PayResult:
    period: str
    rules_version: str
    lines: Dict[str, Decimal] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"period": self.period, "rules_version": self.rules_version,
                "lines": {k: float(v) for k, v in self.lines.items()}, "warnings": self.warnings}


def compute_payslip(inp: PayInput) -> PayResult:
    rules = rules_for_period(inp.period, inp.rules_version)
    common = load_rules()["common"]
    social = common["social"]
    res = PayResult(period=inp.period, rules_version=rules["id"])
    L = res.lines

    if inp.base_salary < 0 or inp.dependents < 0:
        raise ValueError("Le salaire de base et le nombre de personnes à charge doivent être positifs.")

    base = _round(_d(inp.base_salary))
    hourly = _d(inp.base_salary) / _d(common["monthly_legal_hours"])
    ot = common["overtime_rates"]
    overtime = _round(
        hourly * _d(inp.overtime_hours_25) * (1 + _d(ot["h25"]))
        + hourly * _d(inp.overtime_hours_50) * (1 + _d(ot["h50"]))
        + hourly * _d(inp.overtime_hours_100) * (1 + _d(ot["h100"]))
    )
    seniority = _round((base + overtime) * seniority_rate(inp.hire_date, inp.period))

    L["salaire_base"] = base
    L["heures_supplementaires"] = overtime
    L["prime_anciennete"] = seniority
    L["primes_imposables"] = _round(_d(inp.taxable_bonuses))
    L["avantages_en_nature"] = _round(_d(inp.benefits_in_kind))
    gross_taxable = base + overtime + seniority + L["primes_imposables"] + L["avantages_en_nature"]
    L["salaire_brut_imposable"] = gross_taxable
    L["indemnites_exonerees"] = _round(_d(inp.exempt_allowances))
    L["salaire_brut_global"] = gross_taxable + L["indemnites_exonerees"]

    # Employee social contributions
    ceiling = _d(social["cnss_ceiling_monthly"])
    emp = social["employee"]
    if inp.cnss_affiliated:
        L["cnss_salarie"] = _round(min(gross_taxable, ceiling) * _d(emp["cnss_prestations"]))
        L["amo_salarie"] = _round(gross_taxable * _d(emp["amo"]))
    else:
        L["cnss_salarie"] = Decimal("0.00")
        L["amo_salarie"] = Decimal("0.00")
        res.warnings.append("Salarié non affilié à la CNSS : aucune cotisation sociale calculée.")
    L["retraite_complementaire_salarie"] = _round(gross_taxable * _d(inp.pension_employee_rate))

    # Professional expenses (CGI art. 59): rate depends on annual gross taxable income, annual cap
    gross_annual = gross_taxable * 12
    fp_rate = next(_d(t["rate"]) for t in rules["professional_expenses"]
                   if t["max_gross_annual"] is None or gross_annual <= _d(t["max_gross_annual"]))
    fp_cap_monthly = _d(rules["professional_expenses_cap_annual"]) / 12
    L["frais_professionnels"] = _round(min(gross_taxable * fp_rate, fp_cap_monthly))

    L["interets_logement"] = _round(_d(inp.housing_loan_interest))
    net_taxable = max(Decimal("0"), gross_taxable - L["frais_professionnels"] - L["cnss_salarie"]
                      - L["amo_salarie"] - L["retraite_complementaire_salarie"] - L["interets_logement"])
    L["salaire_net_imposable"] = _round(net_taxable)

    # IR: annual barème applied to the annualised monthly base, then family reduction (art. 74), never < 0
    ir_gross = _round(annual_ir(net_taxable * 12, rules["ir_brackets"]) / 12)
    persons = min(inp.dependents, rules["family_max_persons"])
    if inp.dependents > rules["family_max_persons"]:
        res.warnings.append(f"Charges de famille plafonnées à {rules['family_max_persons']} personnes.")
    family = _round(_d(rules["family_reduction_per_person_annual"]) * persons / 12)
    L["ir_brut"] = ir_gross
    L["reduction_charges_famille"] = min(family, ir_gross)
    L["ir_net"] = ir_gross - L["reduction_charges_famille"]

    L["total_retenues"] = (L["cnss_salarie"] + L["amo_salarie"] + L["retraite_complementaire_salarie"]
                           + L["ir_net"])
    L["net_a_payer"] = L["salaire_brut_global"] - L["avantages_en_nature"] - L["total_retenues"]

    # Employer charges
    er = social["employer"]
    if inp.cnss_affiliated:
        L["cnss_patronal"] = _round(min(gross_taxable, ceiling) * _d(er["cnss_prestations"]))
        L["allocations_familiales"] = _round(gross_taxable * _d(er["allocations_familiales"]))
        L["taxe_formation_professionnelle"] = _round(gross_taxable * _d(er["taxe_formation_professionnelle"]))
        L["amo_patronal"] = _round(gross_taxable * _d(er["amo"]))
    else:
        for k in ("cnss_patronal", "allocations_familiales", "taxe_formation_professionnelle", "amo_patronal"):
            L[k] = Decimal("0.00")
    L["charges_patronales"] = (L["cnss_patronal"] + L["allocations_familiales"]
                               + L["taxe_formation_professionnelle"] + L["amo_patronal"])
    L["cout_total_employeur"] = L["salaire_brut_global"] + L["charges_patronales"]

    if L["net_a_payer"] < 0:
        res.warnings.append("Net à payer négatif : vérifier les retenues et avantages en nature.")
    return res


def deadlines_for_period(period: str) -> Dict[str, str]:
    """Filing deadlines for salaries paid in `period`."""
    month = parse_period(period)
    nxt = date(month.year + (month.month // 12), month.month % 12 + 1, 1)
    after = date(nxt.year + (nxt.month // 12), nxt.month % 12 + 1, 1)
    last_day_next = date.fromordinal(after.toordinal() - 1)
    return {
        "ir_versement": last_day_next.isoformat(),
        "cnss_bds": date(nxt.year, nxt.month, 10).isoformat(),
        "etat_9421": date.fromordinal(date(month.year + 1, 3, 1).toordinal() - 1).isoformat(),  # before 1 March
    }
