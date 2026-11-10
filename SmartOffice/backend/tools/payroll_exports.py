"""
Payroll documents: livre de paie, récapitulatifs IR / CNSS, état 9421 (Excel) and bulletin de paie (Word).

The official EDI XML of SIMPL-IR (état 9421) and the e-BDS file of Damancom follow schemas published by the DGI
and the CNSS to registered employers; they are not reproduced here. These workbooks carry every field those
declarations require, for entry on the portals (EFI mode) or conversion by the employer's EDI tool.
"""
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import docx
import openpyxl
from docx.shared import Pt, RGBColor
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from backend.config.settings import settings

GREEN = "1B4332"
MONEY = '#,##0.00'

LINE_LABELS = [
    ("salaire_base", "Salaire de base"),
    ("heures_supplementaires", "Heures supplémentaires"),
    ("prime_anciennete", "Prime d'ancienneté"),
    ("primes_imposables", "Primes et indemnités imposables"),
    ("avantages_en_nature", "Avantages en nature"),
    ("salaire_brut_imposable", "Salaire brut imposable"),
    ("indemnites_exonerees", "Indemnités exonérées"),
    ("salaire_brut_global", "Salaire brut global"),
    ("cnss_salarie", "CNSS (prestations sociales)"),
    ("amo_salarie", "AMO"),
    ("retraite_complementaire_salarie", "Retraite complémentaire"),
    ("frais_professionnels", "Frais professionnels"),
    ("interets_logement", "Intérêts prêt logement"),
    ("salaire_net_imposable", "Salaire net imposable"),
    ("ir_brut", "IR brut"),
    ("reduction_charges_famille", "Réduction charges de famille"),
    ("ir_net", "IR retenu à la source"),
    ("total_retenues", "Total retenues"),
    ("net_a_payer", "NET À PAYER"),
    ("cnss_patronal", "CNSS patronale"),
    ("allocations_familiales", "Allocations familiales"),
    ("taxe_formation_professionnelle", "Taxe de formation professionnelle"),
    ("amo_patronal", "AMO patronale"),
    ("charges_patronales", "Total charges patronales"),
    ("cout_total_employeur", "Coût total employeur"),
]


def _employer_header(profile: Dict[str, Any]) -> str:
    org = profile.get("organization", {})
    return (f"{org.get('name_fr', 'AFMI')} — IF {org.get('identifiant_fiscal', '…')} — ICE {org.get('ice', '…')} — "
            f"{org.get('headquarters', '')}")


def _write_table(title: str, subtitle: str, headers: Sequence[str], rows: List[Sequence[Any]],
                 money_cols: Sequence[int], filename: str, totals: bool = True) -> str:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = title[:31]
    side = Side(border_style="thin", color="CBD5E1")
    border = Border(left=side, right=side, top=side, bottom=side)
    last_col = get_column_letter(len(headers))

    ws.merge_cells(f"A1:{last_col}1")
    ws["A1"] = title
    ws["A1"].font = Font(size=14, bold=True, color=GREEN)
    ws.merge_cells(f"A2:{last_col}2")
    ws["A2"] = subtitle
    ws["A2"].font = Font(size=9, italic=True, color="64748B")

    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=4, column=c, value=h)
        cell.fill = PatternFill(start_color=GREEN, end_color=GREEN, fill_type="solid")
        cell.font = Font(bold=True, color="FFFFFF")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border
        ws.column_dimensions[get_column_letter(c)].width = max(12, min(34, len(h) + 4))
    ws.row_dimensions[4].height = 32

    r = 5
    for row in rows:
        for c, value in enumerate(row, start=1):
            cell = ws.cell(row=r, column=c, value=value)
            cell.border = border
            if c - 1 in money_cols:
                cell.number_format = MONEY
        r += 1
    if totals and rows:
        ws.cell(row=r, column=1, value="TOTAL").font = Font(bold=True)
        for c in money_cols:
            col = get_column_letter(c + 1)
            cell = ws.cell(row=r, column=c + 1, value=f"=SUM({col}5:{col}{r - 1})")
            cell.number_format = MONEY
            cell.font = Font(bold=True)
    ws.freeze_panes = "A5"

    path = Path(settings.exports_dir) / filename
    wb.save(path)
    return str(path)


def export_payroll_ledger(period: str, payslips: List[Dict[str, Any]], profile: Dict[str, Any]) -> str:
    keys = ["salaire_brut_global", "salaire_brut_imposable", "cnss_salarie", "amo_salarie",
            "frais_professionnels", "salaire_net_imposable", "ir_net", "net_a_payer",
            "charges_patronales", "cout_total_employeur"]
    headers = ["Matricule", "Nom et prénom", "N° CNSS", "Pers. à charge"] + [dict(LINE_LABELS)[k] for k in keys] + ["Statut"]
    rows = [[p["matricule"], p["full_name"], p.get("cnss_number") or "", p.get("dependents", 0)]
            + [p["lines"].get(k, 0) for k in keys] + [p["status"]] for p in payslips]
    return _write_table(f"Livre de paie {period}", _employer_header(profile), headers, rows,
                        money_cols=list(range(4, 4 + len(keys))),
                        filename=f"AFMI_LivrePaie_{period}_{datetime.now():%H%M%S}.xlsx")


def export_cnss_recap(period: str, payslips: List[Dict[str, Any]], profile: Dict[str, Any]) -> str:
    headers = ["N° CNSS", "Nom et prénom", "CIN", "Salaire brut imposable", "Salaire plafonné (6 000)",
               "CNSS salarié", "CNSS patronal", "Allocations familiales", "TFP", "AMO salarié", "AMO patronal"]
    rows = []
    for p in payslips:
        l = p["lines"]
        rows.append([p.get("cnss_number") or "À compléter", p["full_name"], p.get("cin") or "",
                     l.get("salaire_brut_imposable", 0), min(l.get("salaire_brut_imposable", 0), 6000.0),
                     l.get("cnss_salarie", 0), l.get("cnss_patronal", 0), l.get("allocations_familiales", 0),
                     l.get("taxe_formation_professionnelle", 0), l.get("amo_salarie", 0), l.get("amo_patronal", 0)])
    return _write_table(f"Récapitulatif CNSS {period}",
                        _employer_header(profile) + " — à reporter sur Damancom (BDS)",
                        headers, rows, money_cols=list(range(3, 11)),
                        filename=f"AFMI_CNSS_{period}_{datetime.now():%H%M%S}.xlsx")


def export_ir_monthly(period: str, payslips: List[Dict[str, Any]], profile: Dict[str, Any]) -> str:
    headers = ["Matricule", "Nom et prénom", "CIN", "Salaire brut imposable", "Salaire net imposable", "IR retenu"]
    rows = [[p["matricule"], p["full_name"], p.get("cin") or "", p["lines"].get("salaire_brut_imposable", 0),
             p["lines"].get("salaire_net_imposable", 0), p["lines"].get("ir_net", 0)] for p in payslips]
    return _write_table(f"IR retenu à la source {period}",
                        _employer_header(profile) + " — versement via SIMPL-IR", headers, rows,
                        money_cols=[3, 4, 5], filename=f"AFMI_IR_{period}_{datetime.now():%H%M%S}.xlsx")


def export_etat_9421(year: int, employees: List[Dict[str, Any]], profile: Dict[str, Any]) -> str:
    """One row per employee with the annual totals required by the état 9421 (CGI art. 79)."""
    headers = ["Nom et prénom", "Adresse", "CIN", "N° CNSS", "Période (mois payés)", "Salaire brut global",
               "Avantages en nature", "Indemnités exonérées", "Revenu brut imposable", "Frais professionnels",
               "Cotisations CNSS + AMO", "Retraite complémentaire", "Intérêts prêt logement",
               "Revenu net imposable", "Personnes à charge", "IR retenu"]
    rows = [[e["full_name"], e.get("address") or "", e.get("cin") or "À compléter", e.get("cnss_number") or "",
             e["months"], e["salaire_brut_global"], e["avantages_en_nature"], e["indemnites_exonerees"],
             e["salaire_brut_imposable"], e["frais_professionnels"], e["cotisations_sociales"],
             e["retraite_complementaire_salarie"], e["interets_logement"], e["salaire_net_imposable"],
             e["dependents"], e["ir_net"]] for e in employees]
    return _write_table(f"État 9421 — Traitements et salaires {year}",
                        _employer_header(profile) + " — à télédéclarer sur SIMPL-IR avant le 1er mars",
                        headers, rows, money_cols=[5, 6, 7, 8, 9, 10, 11, 12, 13, 15],
                        filename=f"AFMI_Etat9421_{year}_{datetime.now():%H%M%S}.xlsx")


def export_payslip_docx(payslip: Dict[str, Any], employee: Dict[str, Any], profile: Dict[str, Any]) -> str:
    d = docx.Document()
    style = d.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10)

    title = d.add_heading(f"BULLETIN DE PAIE — {payslip['period']}", level=1)
    title.runs[0].font.color.rgb = RGBColor(0x1B, 0x43, 0x32)
    d.add_paragraph(_employer_header(profile))
    info = d.add_table(rows=0, cols=4)
    info.style = "Light Grid Accent 1"
    pairs = [("Salarié", employee["full_name"]), ("Matricule", employee["matricule"]),
             ("CIN", employee.get("cin") or ""), ("N° CNSS", employee.get("cnss_number") or ""),
             ("Fonction", employee.get("position") or ""), ("Date d'embauche", employee.get("hire_date") or ""),
             ("Personnes à charge", str(employee.get("dependents", 0))), ("Règles appliquées", payslip["rules_version"])]
    for i in range(0, len(pairs), 2):
        cells = info.add_row().cells
        cells[0].text, cells[1].text = pairs[i]
        cells[2].text, cells[3].text = pairs[i + 1]

    d.add_paragraph()
    table = d.add_table(rows=1, cols=2)
    table.style = "Light List Accent 1"
    table.rows[0].cells[0].text = "Rubrique"
    table.rows[0].cells[1].text = "Montant (DH)"
    for key, label in LINE_LABELS:
        value = payslip["lines"].get(key)
        if value is None or (value == 0 and key not in ("ir_net", "net_a_payer")):
            continue
        cells = table.add_row().cells
        cells[0].text = label
        cells[1].text = f"{value:,.2f}".replace(",", " ")
        if key in ("net_a_payer", "salaire_brut_imposable", "ir_net"):
            for c in cells:
                for run in c.paragraphs[0].runs:
                    run.bold = True
    for w in payslip.get("warnings", []):
        d.add_paragraph(f"⚠ {w}")
    d.add_paragraph("Bulletin établi selon le Code du travail et le Code général des impôts (art. 59, 73, 74), "
                    f"règles {payslip['rules_version']}.").runs[0].font.size = Pt(8)

    path = Path(settings.exports_dir) / f"AFMI_Bulletin_{employee['matricule']}_{payslip['period']}.docx"
    d.save(path)
    return str(path)
