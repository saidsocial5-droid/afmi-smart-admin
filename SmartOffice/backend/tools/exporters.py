import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from backend.config.settings import settings

AFMI_GREEN = RGBColor(27, 67, 50)      # #1B4332
AFMI_GOLD = RGBColor(212, 163, 115)    # #D4A373
AFMI_GREY = RGBColor(100, 116, 139)

def set_cell_background(cell, fill_hex):
    """Set background color of a docx table cell."""
    tcPr = cell._element.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def export_to_docx(
    title: str,
    sections: List[Dict[str, Any]],
    output_filename: Optional[str] = None,
    doc_type: str = "Proposition de Projet / Rapport Technique",
    agent_name: str = "AFMI-SmartOffice AI Agent"
) -> str:
    """Generate professional DOCX document with AFMI branding."""
    doc = docx.Document()
    
    # Page setup
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)
        
        # Header
        header = section.header
        hp = header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hrun = hp.add_run("Association Forêt Modèle d'Ifrane (AFMI) | جمعية الغابة النموذجية إفران")
        hrun.font.name = "Calibri"
        hrun.font.size = Pt(8.5)
        hrun.font.color.rgb = AFMI_GREY
        
        # Footer
        footer = section.footer
        fp = footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        frun = fp.add_run(f"AFMI-SmartOffice © {datetime.now().year} — Siège : Azrou / Province d'Ifrane, Région Fès-Meknès, Maroc")
        frun.font.name = "Calibri"
        frun.font.size = Pt(8)
        frun.font.color.rgb = AFMI_GREY

    # Institution Title Banner
    top_p = doc.add_paragraph()
    top_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sub = top_p.add_run("ROYAUME DU MAROC\nASSOCIATION FORÊT MODÈLE D'IFRANE (AFMI)\nجمعية الغابة النموذجية إفران\n")
    r_sub.font.name = "Georgia"
    r_sub.font.size = Pt(11)
    r_sub.font.bold = True
    r_sub.font.color.rgb = AFMI_GREEN
    
    # Document Type Pill / Subtitle
    type_p = doc.add_paragraph()
    type_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_type = type_p.add_run(f"— {doc_type.upper()} —\n")
    r_type.font.name = "Calibri"
    r_type.font.size = Pt(10)
    r_type.font.bold = True
    r_type.font.color.rgb = AFMI_GOLD

    # Document Main Title
    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title = title_p.add_run(title)
    r_title.font.name = "Georgia"
    r_title.font.size = Pt(18)
    r_title.font.bold = True
    r_title.font.color.rgb = AFMI_GREEN

    # Meta Table
    meta_table = doc.add_table(rows=2, cols=2)
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    meta_table.autofit = False
    
    meta_cells = meta_table.rows[0].cells
    meta_cells[0].paragraphs[0].add_run(f"Date d'émission: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    meta_cells[1].paragraphs[0].add_run(f"Agent Rédacteur: {agent_name}")
    
    meta_cells_2 = meta_table.rows[1].cells
    meta_cells_2[0].paragraphs[0].add_run("Zone d'action: Moyen Atlas (Azrou, Ifrane, Timahdite)")
    meta_cells_2[1].paragraphs[0].add_run("Statut: Document Officiel / Draft Validé")

    for row in meta_table.rows:
        for cell in row.cells:
            set_cell_background(cell, "F1F5F9")
            for p in cell.paragraphs:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                for run in p.runs:
                    run.font.size = Pt(8.5)
                    run.font.color.rgb = AFMI_GREY

    doc.add_paragraph()  # Spacer

    # Sections Rendering
    for sec in sections:
        sec_title = sec.get("title", "")
        sec_content = sec.get("content", "")
        
        if sec_title:
            h = doc.add_heading(level=1)
            hrun = h.add_run(sec_title)
            hrun.font.name = "Georgia"
            hrun.font.size = Pt(13)
            hrun.font.bold = True
            hrun.font.color.rgb = AFMI_GREEN
        
        # Split lines for paragraphs & bullets
        lines = sec_content.split("\n")
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("- ") or stripped.startswith("* ") or stripped.startswith("• "):
                bp = doc.add_paragraph(style='List Bullet')
                brun = bp.add_run(stripped[2:])
                brun.font.name = "Calibri"
                brun.font.size = Pt(10.5)
            else:
                p = doc.add_paragraph()
                prun = p.add_run(stripped)
                prun.font.name = "Calibri"
                prun.font.size = Pt(10.5)

    if not output_filename:
        safe_title = "".join(c for c in title[:30] if c.isalnum() or c in (' ', '_', '-')).strip()
        output_filename = f"AFMI_Doc_{safe_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
    
    output_path = settings.exports_dir / output_filename
    doc.save(str(output_path))
    return str(output_path)


def export_to_excel(
    transactions: List[Dict[str, Any]],
    output_filename: Optional[str] = None,
    sheet_title: str = "Grand Livre & Rapprochement"
) -> str:
    """Generate professional Excel workbook with AFMI financial layout."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_title
    ws.sheet_view.showGridLines = True

    # AFMI Excel Palette
    green_header_fill = PatternFill(start_color="1B4332", end_color="1B4332", fill_type="solid")
    gold_fill = PatternFill(start_color="D4A373", end_color="D4A373", fill_type="solid")
    subtotal_fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")
    alt_row_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")

    font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_title = Font(name="Calibri", size=15, bold=True, color="1B4332")
    font_bold = Font(name="Calibri", size=10.5, bold=True)
    font_normal = Font(name="Calibri", size=10)
    
    thin_border_side = Side(border_style="thin", color="CBD5E1")
    border_cell = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)

    # Title Banner
    ws.merge_cells("A1:K1")
    title_cell = ws["A1"]
    title_cell.value = "ASSOCIATION FORÊT MODÈLE D'IFRANE (AFMI) — ÉTAT FINANCIER & GRAND LIVRE"
    title_cell.font = font_title
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 32

    ws.merge_cells("A2:K2")
    sub_cell = ws["A2"]
    sub_cell.value = f"Extraction Automatisée OCR & Audit Intelligent | Date d'export : {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    sub_cell.font = Font(name="Calibri", size=10, italic=True, color="64748B")
    sub_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 18

    # Headers Row
    headers = [
        "N°", "Date Opération", "N° Référence", "Libellé de l'Opération", 
        "Tiers / Bénéficiaire", "Débit (DH)", "Crédit (DH)", "Solde (DH)", 
        "Catégorie Budgétaire", "Axe Stratégique AFMI", "Statut Audit"
    ]
    
    header_row = 4
    ws.row_dimensions[header_row].height = 25
    for col_idx, h_text in enumerate(headers, start=1):
        cell = ws.cell(row=header_row, column=col_idx, value=h_text)
        cell.fill = green_header_fill
        cell.font = font_header
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border_cell

    # Populate Data
    start_data_row = 5
    current_row = start_data_row

    total_debit = 0.0
    total_credit = 0.0

    for idx, tx in enumerate(transactions, start=1):
        debit_val = float(tx.get("debit", 0.0) or 0.0)
        credit_val = float(tx.get("credit", 0.0) or 0.0)
        balance_val = float(tx.get("balance", 0.0) or 0.0)
        
        total_debit += debit_val
        total_credit += credit_val

        ws.cell(row=current_row, column=1, value=idx).alignment = Alignment(horizontal="center")
        ws.cell(row=current_row, column=2, value=tx.get("tx_date", tx.get("date", ""))).alignment = Alignment(horizontal="center")
        ws.cell(row=current_row, column=3, value=tx.get("reference", "")).alignment = Alignment(horizontal="center")
        ws.cell(row=current_row, column=4, value=tx.get("label", tx.get("description", ""))).alignment = Alignment(horizontal="left")
        ws.cell(row=current_row, column=5, value=tx.get("beneficiary_or_emitter", tx.get("beneficiary", ""))).alignment = Alignment(horizontal="left")
        
        # Debits & Credits
        c_deb = ws.cell(row=current_row, column=6, value=debit_val if debit_val > 0 else "")
        c_deb.number_format = '#,##0.00 "DH"'
        c_deb.alignment = Alignment(horizontal="right")
        
        c_crd = ws.cell(row=current_row, column=7, value=credit_val if credit_val > 0 else "")
        c_crd.number_format = '#,##0.00 "DH"'
        c_crd.alignment = Alignment(horizontal="right")
        
        c_bal = ws.cell(row=current_row, column=8, value=balance_val)
        c_bal.number_format = '#,##0.00 "DH"'
        c_bal.alignment = Alignment(horizontal="right")

        ws.cell(row=current_row, column=9, value=tx.get("category", "Divers")).alignment = Alignment(horizontal="left")
        ws.cell(row=current_row, column=10, value=tx.get("strategic_axis", "Non Assigné")).alignment = Alignment(horizontal="left")
        
        c_status = ws.cell(row=current_row, column=11, value=tx.get("status", "Validated"))
        c_status.alignment = Alignment(horizontal="center")

        # Styling
        is_even = (current_row % 2 == 0)
        for col_idx in range(1, 12):
            cell = ws.cell(row=current_row, column=col_idx)
            cell.font = font_normal
            cell.border = border_cell
            if is_even:
                cell.fill = alt_row_fill

        current_row += 1

    # Totals Row
    ws.row_dimensions[current_row].height = 24
    ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=5)
    tot_label = ws.cell(row=current_row, column=1, value="TOTAUX GÉNÉRAUX (MAD)")
    tot_label.font = font_bold
    tot_label.alignment = Alignment(horizontal="right", vertical="center")

    tot_deb = ws.cell(row=current_row, column=6, value=f"=SUM(F{start_data_row}:F{current_row-1})")
    tot_deb.font = font_bold
    tot_deb.number_format = '#,##0.00 "DH"'
    tot_deb.alignment = Alignment(horizontal="right", vertical="center")

    tot_crd = ws.cell(row=current_row, column=7, value=f"=SUM(G{start_data_row}:G{current_row-1})")
    tot_crd.font = font_bold
    tot_crd.number_format = '#,##0.00 "DH"'
    tot_crd.alignment = Alignment(horizontal="right", vertical="center")

    for col_idx in range(1, 12):
        c = ws.cell(row=current_row, column=col_idx)
        c.fill = subtotal_fill
        c.border = border_cell

    # Auto-adjust column widths
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            # ignore merged rows 1 & 2 for width calculation
            if cell.row in [1, 2]:
                continue
            val_str = str(cell.value or "")
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    # Specific comfortable widths
    ws.column_dimensions["D"].width = 38
    ws.column_dimensions["E"].width = 28
    ws.column_dimensions["J"].width = 32

    if not output_filename:
        output_filename = f"AFMI_GrandLivre_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
    output_path = settings.exports_dir / output_filename
    wb.save(str(output_path))
    return str(output_path)
