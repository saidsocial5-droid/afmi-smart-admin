"""Hand-checked payslips (see comments for the arithmetic)."""
import pytest

from backend.tools.payroll_ma import PayInput, compute_payslip, rules_for_period, seniority_rate, deadlines_for_period


def L(**kw):
    return compute_payslip(PayInput(**kw)).lines


def test_rules_selected_by_period():
    assert rules_for_period("2017-06")["id"] == "LF2017"
    assert rules_for_period("2022-12")["id"] == "LF2017"
    assert rules_for_period("2023-01")["id"] == "LF2023"
    assert rules_for_period("2025-07")["id"] == "LF2025"
    assert rules_for_period("2026-11")["id"] == "LF2026"
    assert rules_for_period("2026-11", "LF2017")["id"] == "LF2017"
    with pytest.raises(ValueError):
        rules_for_period("2016-12")


def test_lf2017_example():
    # 5 000 brut, 2 personnes à charge, juin 2017
    # CNSS 4,48 % x 5 000 = 224 ; AMO 2,26 % = 113 ; FP 20 % = 1 000 (plafond 2 500/mois)
    # SNI = 3 663 -> annuel 43 956 : 10 % - 3 000 -> 1 395,60 /12 = 116,30 ; famille 360x2/12 = 60 -> IR 56,30
    l = L(period="2017-06", base_salary=5000, dependents=2)
    assert l["cnss_salarie"] == 224
    assert l["amo_salarie"] == 113
    assert l["frais_professionnels"] == 1000
    assert float(l["salaire_net_imposable"]) == 3663
    assert float(l["ir_brut"]) == 116.30
    assert float(l["ir_net"]) == 56.30
    assert float(l["net_a_payer"]) == 4606.70


def test_lf2026_example_and_employer_cost():
    # 10 000 brut, janvier 2026, 0 personne à charge
    # CNSS 4,48 % x 6 000 (plafond) = 268,80 ; AMO 226 ; FP 25 % (120 000 > 78 000) = 2 500
    # SNI 7 005,20 -> annuel 84 062,40 : 30 % - 18 000 = 7 218,72 /12 = 601,56
    l = L(period="2026-01", base_salary=10000)
    assert float(l["cnss_salarie"]) == 268.80
    assert float(l["frais_professionnels"]) == 2500
    assert float(l["salaire_net_imposable"]) == 7005.20
    assert float(l["ir_net"]) == 601.56
    assert float(l["net_a_payer"]) == 8903.64
    # Patronal : 8,98 % x 6 000 = 538,80 ; AF 640 ; TFP 160 ; AMO 411 -> 1 749,80
    assert float(l["charges_patronales"]) == 1749.80
    assert float(l["cout_total_employeur"]) == 11749.80


def test_family_reduction_follows_finance_law():
    assert float(L(period="2026-01", base_salary=10000, dependents=2)["reduction_charges_famille"]) == 100.00  # 600x2/12
    assert float(L(period="2025-01", base_salary=10000, dependents=2)["reduction_charges_famille"]) == 83.33   # 500x2/12
    capped = compute_payslip(PayInput(period="2026-01", base_salary=10000, dependents=8))
    assert float(capped.lines["reduction_charges_famille"]) == 300.00  # 6 personnes max
    assert capped.warnings


def test_family_reduction_never_makes_ir_negative():
    l = L(period="2026-01", base_salary=3500, dependents=6)
    assert l["ir_net"] >= 0


def test_low_income_professional_expenses_rate_and_cap():
    # 2024, 6 000 brut -> 72 000/an <= 78 000 : 35 % = 2 100 (plafond mensuel 2 916,67)
    assert float(L(period="2024-03", base_salary=6000)["frais_professionnels"]) == 2100
    # 2017, 20 000 brut : 20 % = 4 000 > plafond 30 000/12 = 2 500
    assert float(L(period="2017-03", base_salary=20000)["frais_professionnels"]) == 2500


def test_seniority_and_overtime():
    assert float(seniority_rate("2019-01-15", "2026-01")) == 0.10   # 6 ans révolus
    assert float(seniority_rate("2024-06-01", "2026-01")) == 0.0    # < 2 ans
    assert float(seniority_rate("2000-01-01", "2026-01")) == 0.25
    # 191 h -> taux horaire 9 550/191 = 50 ; 10 h à +25 % = 625
    l = L(period="2026-01", base_salary=9550, overtime_hours_25=10)
    assert float(l["heures_supplementaires"]) == 625


def test_exempt_allowances_are_paid_but_not_taxed():
    a = L(period="2026-01", base_salary=8000)
    b = L(period="2026-01", base_salary=8000, exempt_allowances=500)
    assert a["ir_net"] == b["ir_net"]
    assert b["net_a_payer"] - a["net_a_payer"] == 500


def test_deadlines():
    d = deadlines_for_period("2026-12")
    assert d["ir_versement"] == "2027-01-31"
    assert d["cnss_bds"] == "2027-01-10"
    assert deadlines_for_period("2027-05")["etat_9421"] == "2028-02-29"
