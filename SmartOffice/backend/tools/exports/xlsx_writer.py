"""Exports Excel avec de vraies formules.

- **États financiers** : une feuille par état du rapport annuel (CER, recettes et dépenses, exécution budgétaire,
  trésorerie, reports, comparaison). Les montants de détail sont des valeurs ; sous-totaux, totaux, écarts, taux,
  totaux de ligne et résultats sont des **formules**. Une formule n'est écrite que si elle redonne exactement le
  montant calculé par l'application (sinon la valeur est conservée) : le classeur ne peut pas contredire le rapport.
  Une feuille « Ventilations » détaille les opérations validées et une feuille « Contrôles » recalcule les totaux
  par SOMME.SI.ENS sur ce détail (écart attendu : 0).
- **Opérations bancaires** : une feuille par compte, solde progressif en formule à partir du solde d'ouverture.
- **Rapprochement** : relevé, opérations, éléments non rapprochés et état de rapprochement en formules.

Mise en forme selon la charte (couleurs d'en-tête, police), feuilles de droite à gauche en arabe, impression
paysage ajustée à la largeur, volets figés sous l'en-tête.
"""
import io
import re
from typing import Any, Dict, List, Optional, Tuple

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from backend.core import unified_db
from backend.tools.editor import charts
from backend.tools.reports import finance
from backend.tools.reports.context import layout as report_layout, period as get_period, scope as get_scope
from backend.tools.reports.generator import TABLES, scope_label
from backend.tools.reports.i18n import t as tr
from .resolve import split_label

MONEY = '#,##0.00;[Red]-#,##0.00'
NUMBER = '#,##0.##'
PERCENT = '0.0%'
SHEETS = [("cer", "CER"), ("income_expense", "Recettes-Dépenses"), ("budget_project", "Budget par projet"),
          ("budget_funder", "Budget par bailleur"), ("treasury", "Trésorerie"), ("carry_forward", "Reports"),
          ("comparison", "Comparaison")]
# Colonnes calculées : écart = a - b ; taux = num / den (indices de colonnes du tableau)
DERIVED = {
    "budget_project": {"diff": (3, 1, 2), "ratio": (4, 2, 1)},
    "budget_funder": {"diff": (3, 1, 2), "ratio": (4, 2, 1)},
    "comparison": {"diff": (3, 2, 1), "ratio": (4, 3, 1)},
    "carry_forward": {"diff": (5, 3, 4)},
}


def _hex(c: Optional[str], default: str) -> str:
    c = (c or "").lstrip("#")
    return c.upper() if re.fullmatch(r"[0-9a-fA-F]{6}", c) else default


class Styler:
    def __init__(self, style: Dict[str, Any], rtl: bool):
        tbl, colors, fonts = style.get("table") or {}, style.get("colors") or {}, style.get("fonts") or {}
        self.font = fonts.get("body") or "Calibri"
        self.head_fill = PatternFill("solid", fgColor=_hex(tbl.get("header_bg"), "1B4332"))
        self.head_font = Font(name=self.font, bold=True, color=_hex(tbl.get("header_color"), "FFFFFF"))
        self.title_font = Font(name=self.font, bold=True, size=14, color=_hex(colors.get("primary"), "1B4332"))
        self.sub_fill = PatternFill("solid", fgColor="F1F5F9")
        self.border = Border(*(Side(style="thin", color=_hex(tbl.get("border_color"), "CBD5E1")),) * 4)
        self.rtl = rtl

    def sheet(self, ws: Worksheet, title: str, subtitle: str = "") -> int:
        ws.sheet_view.rightToLeft = self.rtl
        ws["A1"] = title
        ws["A1"].font = self.title_font
        row = 2
        if subtitle:
            ws["A2"] = subtitle
            ws["A2"].font = Font(name=self.font, italic=True, color="6B7280")
            row = 3
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.print_options.horizontalCentered = True
        ws.oddFooter.center.text = "&P / &N"
        return row + 1

    def header(self, ws: Worksheet, row: int, columns: List[str], numeric: List[bool]) -> None:
        for j, c in enumerate(columns, start=1):
            cell = ws.cell(row=row, column=j, value=c)
            cell.fill, cell.font, cell.border = self.head_fill, self.head_font, self.border
            cell.alignment = Alignment(horizontal="right" if numeric[j - 1] else "left", vertical="center", wrap_text=True)
        ws.freeze_panes = ws.cell(row=row + 1, column=2)
        ws.print_title_rows = f"{row}:{row}"

    def body(self, cell, bold: bool = False, sub: bool = False, fmt: Optional[str] = None, indent: int = 0) -> None:
        cell.border = self.border
        cell.font = Font(name=self.font, bold=bold)
        if sub:
            cell.fill = self.sub_fill
        if fmt:
            cell.number_format = fmt
        if indent:
            cell.alignment = Alignment(indent=indent)

    @staticmethod
    def widths(ws: Worksheet, widths: List[float]) -> None:
        for j, w in enumerate(widths, start=1):
            ws.column_dimensions[get_column_letter(j)].width = w


def _excel_value(v: Any, fmt: str) -> Any:
    if v is None or isinstance(v, str):
        return v
    if fmt == "money":
        return v / 100
    if fmt == "percent":
        return v / 100
    return v


def _cell_fmt(fmt: str) -> Optional[str]:
    return {"money": MONEY, "number": NUMBER, "percent": PERCENT}.get(fmt)


class FormulaPlanner:
    """Décide, cellule par cellule, si une formule reproduit exactement le montant de l'application."""

    def __init__(self, data: Dict[str, Any], name: str, first_row: int):
        self.data, self.name, self.r0 = data, name, first_row
        self.rows = data.get("rows") or []
        self.formats = data.get("formats") or []
        self.formulas: Dict[Tuple[int, int], str] = {}
        self.kinds = [self._kind(r) for r in self.rows]

    def _kind(self, r: List[Any]) -> str:
        label, indent, bold = split_label(r[0])
        has_values = any(isinstance(v, (int, float)) for v in r[1:])
        if indent:
            return "detail"
        if bold and not has_values:
            return "header"
        if bold:
            return "bold"
        return "plain"

    def xl_row(self, i: int) -> int:
        return self.r0 + i

    @staticmethod
    def _col(j: int) -> str:
        return get_column_letter(j + 1)

    def _try(self, i: int, j: int, refs: List[int], expected: Any, sign: Optional[List[int]] = None) -> None:
        """Somme (signée) des lignes refs, colonne j ; formule retenue si elle redonne exactement la valeur."""
        if not isinstance(expected, (int, float)) or not refs:
            return
        sign = sign or [1] * len(refs)
        values = [self.rows[k][j] if k >= 0 else None for k in refs]
        if any(not isinstance(v, (int, float)) for v in values):
            return
        if sum(s * v for s, v in zip(sign, values)) != expected:
            return
        col = self._col(j)
        if all(s == 1 for s in sign) and refs == list(range(refs[0], refs[-1] + 1)) and len(refs) > 1:
            self.formulas[(i, j)] = f"=SUM({col}{self.xl_row(refs[0])}:{col}{self.xl_row(refs[-1])})"
        else:
            terms = "".join(("+" if s > 0 else "-") + f"{col}{self.xl_row(k)}" for s, k in zip(sign, refs))
            self.formulas[(i, j)] = "=" + terms.lstrip("+")

    def plan(self) -> Dict[Tuple[int, int], str]:
        n = len(self.rows)
        money_cols = [j for j, f in enumerate(self.formats) if f in ("money", "number") and j > 0]
        derived = DERIVED.get(self.name, {})
        skip = {derived["diff"][0]} if "diff" in derived else set()
        skip |= {derived["ratio"][0]} if "ratio" in derived else set()
        for i, kind in enumerate(self.kinds):
            following = []
            k = i + 1
            while k < n and self.kinds[k] == "detail":
                following.append(k)
                k += 1
            for j in money_cols:
                if j in skip:
                    continue
                if kind in ("bold", "plain") and following:
                    self._try(i, j, following, self.rows[i][j])          # groupe = somme de son détail
                elif kind == "bold" and not following:
                    start = i - 1                                         # « Total … » = somme depuis l'intertitre
                    while start >= 0 and self.kinds[start] != "header":
                        start -= 1
                    refs = [k for k in range(start + 1, i) if self.kinds[k] in ("plain", "bold")]
                    self._try(i, j, refs, self.rows[i][j])
        # Total de ligne (dernière colonne « Total » de la matrice recettes/dépenses)
        if self.name == "income_expense" and len(money_cols) > 1:
            last = money_cols[-1]
            for i, r in enumerate(self.rows):
                vals = [r[j] for j in money_cols[:-1]]
                if all(isinstance(v, (int, float)) for v in vals) and isinstance(r[last], (int, float)) and sum(vals) == r[last]:
                    self.formulas[(i, last)] = f"=SUM({self._col(money_cols[0])}{self.xl_row(i)}:{self._col(money_cols[-2])}{self.xl_row(i)})"
        # Écarts et taux de chaque ligne
        if "diff" in derived:
            d, a, b = derived["diff"]
            for i, r in enumerate(self.rows):
                if isinstance(r[d], (int, float)) and isinstance(r[a], (int, float)) and isinstance(r[b], (int, float)) and r[a] - r[b] == r[d]:
                    self.formulas[(i, d)] = f"={self._col(a)}{self.xl_row(i)}-{self._col(b)}{self.xl_row(i)}"
        if "ratio" in derived:
            q, num, den = derived["ratio"]
            for i, r in enumerate(self.rows):
                if r[q] is not None and isinstance(r[num], (int, float)) and isinstance(r[den], (int, float)):
                    self.formulas[(i, q)] = f'=IF({self._col(den)}{self.xl_row(i)}=0,"",{self._col(num)}{self.xl_row(i)}/{self._col(den)}{self.xl_row(i)})'
        return self.formulas

    def total_formulas(self, total: List[Any]) -> Dict[int, str]:
        """Ligne de total/résultat du tableau."""
        out: Dict[int, str] = {}
        if not total:
            return out
        n = len(self.rows)
        trow = self.xl_row(n)
        totals_rows = [i for i, k in enumerate(self.kinds) if k == "bold" and "total" in split_label(self.rows[i][0])[0].lower()]
        for j, expected in enumerate(total):
            if j == 0 or not isinstance(expected, (int, float)) or self.formats[j] not in ("money", "number"):
                continue
            col = self._col(j)
            if self.name in ("cer", "income_expense") and len(totals_rows) == 2:
                # Résultat = total des ressources − total des emplois (l'ordre des sections dépend de l'état)
                res_i, use_i = (totals_rows[0], totals_rows[1]) if self.name == "income_expense" else (totals_rows[1], totals_rows[0])
                rv, uv = self.rows[res_i][j], self.rows[use_i][j]
                if isinstance(rv, (int, float)) and isinstance(uv, (int, float)) and rv - uv == expected:
                    out[j] = f"={col}{self.xl_row(res_i)}-{col}{self.xl_row(use_i)}"
                continue
            if self.name == "comparison":
                continue                                            # résultat recalculé par l'application (hors tableau)
            top = [i for i, k in enumerate(self.kinds) if k in ("bold", "plain")]
            if self.name.startswith("budget"):
                top = [i for i, k in enumerate(self.kinds) if k == "bold"]
            vals = [self.rows[i][j] for i in top]
            if top and all(isinstance(v, (int, float)) for v in vals) and sum(vals) == expected:
                if top == list(range(top[0], top[-1] + 1)):
                    out[j] = f"=SUM({col}{self.xl_row(top[0])}:{col}{self.xl_row(top[-1])})"
                else:
                    out[j] = "=" + "+".join(f"{col}{self.xl_row(i)}" for i in top)
        derived = DERIVED.get(self.name, {})
        if "diff" in derived:
            d, a, b = derived["diff"]
            if isinstance(total[d], (int, float)) and isinstance(total[a], (int, float)) and isinstance(total[b], (int, float)) and total[a] - total[b] == total[d]:
                out[d] = f"={self._col(a)}{trow}-{self._col(b)}{trow}"
        if "ratio" in derived:
            q, num, den = derived["ratio"]
            if total[q] is not None:
                out[q] = f'=IF({self._col(den)}{trow}=0,"",{self._col(num)}{trow}/{self._col(den)}{trow})'
        return out


def write_table(ws: Worksheet, st: Styler, data: Dict[str, Any], name: str, start_row: int) -> Dict[str, Any]:
    """Écrit un tableau des rapports ; retourne la position des lignes (pour la feuille Contrôles)."""
    cols = data.get("columns") or []
    formats = data.get("formats") or ["text"] * len(cols)
    numeric = [f != "text" for f in formats]
    st.header(ws, start_row, cols, numeric)
    r0 = start_row + 1
    plan = FormulaPlanner(data, name, r0)
    formulas = plan.plan()
    positions: Dict[str, int] = {}
    for i, r in enumerate(data.get("rows") or []):
        label, indent, bold = split_label(r[0])
        kind = plan.kinds[i]
        positions[label] = r0 + i
        for j, v in enumerate(r):
            cell = ws.cell(row=r0 + i, column=j + 1)
            if j == 0:
                cell.value = label
            else:
                cell.value = formulas.get((i, j), _excel_value(v, formats[j] if j < len(formats) else "text"))
            st.body(cell, bold=bold, sub=kind in ("bold", "header"), fmt=_cell_fmt(formats[j]) if j else None, indent=indent // 2 if j == 0 else 0)
    n = len(data.get("rows") or [])
    total = data.get("total")
    if total:
        tf = plan.total_formulas(total)
        for j, v in enumerate(total):
            cell = ws.cell(row=r0 + n, column=j + 1, value=tf.get(j, v if j == 0 else _excel_value(v, formats[j])))
            st.body(cell, bold=True, sub=True, fmt=_cell_fmt(formats[j]) if j else None)
        positions["__total__"] = r0 + n
    row = r0 + n + (2 if total else 1)
    for note in data.get("notes") or []:
        ws.cell(row=row, column=1, value=note).font = Font(name=st.font, italic=True, size=9, color="6B7280")
        row += 1
    if data.get("source"):
        ws.cell(row=row, column=1, value=f"Source : {data['source']}").font = Font(name=st.font, italic=True, size=9, color="6B7280")
    st.widths(ws, [46] + [16 if numeric[j] else 24 for j in range(1, len(cols))])
    return positions


def financial_workbook(year: int, scope_type: str = "association", scope_id: Optional[int] = None, lang: str = "fr") -> bytes:
    lay = report_layout()
    with unified_db.connect() as conn:
        p, s = get_period(conn, year), get_scope(conn, scope_type, scope_id)
        tables = {name: TABLES[name](conn, p, s, lay, lang) for name, _ in SHEETS}
        allocs = finance.allocations(conn, p.start, p.end, s)
        accounts = {r["Id"]: r["Title"] for r in conn.execute("SELECT Id, Title FROM BankAccounts")}
        lines = {r["Id"]: f"{r['Code']} {r['Label']}".strip() for r in conn.execute("SELECT Id, Code, Label FROM BudgetLines")}
        funders = {r["Id"]: r["Name"] for r in conn.execute("SELECT Id, Name FROM Funders")}
        project_id = scope_id if scope_type in ("project", "programme") else None
    style = charts.effective(project_id)["style"]
    st = Styler(style, lang == "ar")
    wb = Workbook()
    wb.remove(wb.active)
    label = scope_label(s, lang)
    subtitle = f"{label} — {tr(lang, 'period', start=p.start, end=p.end)}. {lay.get('status_note', '')}".strip()
    positions: Dict[str, Dict[str, int]] = {}
    for name, sheet in SHEETS:
        ws = wb.create_sheet(sheet)
        row = st.sheet(ws, tables[name]["title"], subtitle)
        positions[name] = write_table(ws, st, tables[name], name, row)

    # Détail des ventilations (base des contrôles)
    ws = wb.create_sheet("Ventilations")
    row = st.sheet(ws, "Ventilations des opérations validées", subtitle)
    cols = ["Date", "Opération", "Nature", "Compte", "Projet", "Ligne budgétaire", "Catégorie", "Bailleur", "Montant MAD"]
    st.header(ws, row, cols, [False] * 8 + [True])
    nature_label = {"Income": tr(lang, "resources"), "Expense": tr(lang, "uses")}
    first = row + 1
    for k, a in enumerate(allocs):
        values = [a["OperationDate"], a["OpId"], nature_label.get(a["Nature"], a["Nature"]), accounts.get(a["BankAccountId"], ""),
                  a["ProjCode"] or tr(lang, "operating"), lines.get(a["BudgetLineId"], ""), a["CatLabel"] or "",
                  funders.get(a["funder_id"], ""), a["mad"] / 100]
        for j, v in enumerate(values, start=1):
            cell = ws.cell(row=first + k, column=j, value=v)
            st.body(cell, fmt=MONEY if j == 9 else None)
    last = first + max(len(allocs), 1) - 1
    if allocs:
        ws.auto_filter.ref = f"A{row}:I{last}"
    st.widths(ws, [12, 10, 14, 26, 14, 30, 28, 22, 16])

    # Contrôles : totaux du CER recalculés par SOMME.SI.ENS sur les ventilations
    ws = wb.create_sheet("Contrôles")
    row = st.sheet(ws, "Contrôles de cohérence", "Chaque écart doit être nul : les états sont recalculés à partir du détail des ventilations.")
    st.header(ws, row, ["Contrôle", "Selon l'état", "Selon le détail", "Écart"], [False, True, True, True])
    cer_pos = positions["cer"]
    rng_n, rng_v = f"Ventilations!$C${first}:$C${last}", f"Ventilations!$I${first}:$I${last}"
    checks = []
    for key, nat in (("uses", "Expense"), ("resources", "Income")):
        label_total = f"{tr(lang, 'total')} {tr(lang, key).lower()}"
        r = cer_pos.get(label_total)
        if r:
            checks.append((f"CER — {label_total}", f"=CER!B{r}", f'=SUMIFS({rng_v},{rng_n},"{nature_label[nat]}")'))
    if "__total__" in cer_pos:
        checks.append((f"CER — {tr(lang, 'result')}", f"=CER!B{cer_pos['__total__']}",
                       f'=SUMIFS({rng_v},{rng_n},"{nature_label["Income"]}")-SUMIFS({rng_v},{rng_n},"{nature_label["Expense"]}")'))
    ie_pos = positions["income_expense"]
    ie_cols = len(tables["income_expense"]["columns"])
    if "__total__" in ie_pos and ie_cols > 1:
        col = get_column_letter(ie_cols)
        checks.append((f"{tables['income_expense']['title']} — {tr(lang, 'result')}", f"='Recettes-Dépenses'!{col}{ie_pos['__total__']}",
                       f"=CER!B{cer_pos['__total__']}" if "__total__" in cer_pos else "=0"))
    for k, (label_c, a, b) in enumerate(checks):
        rr = row + 1 + k
        for j, v in enumerate((label_c, a, b, f"=B{rr}-C{rr}"), start=1):
            cell = ws.cell(row=rr, column=j, value=v)
            st.body(cell, bold=j == 4, fmt=MONEY if j > 1 else None)
    st.widths(ws, [58, 18, 18, 14])
    buf = io.BytesIO()
    wb.properties.title = f"États financiers {year}"
    wb.properties.creator = "AFMI Smart Admin"
    wb.save(buf)
    return buf.getvalue()


# --- Opérations bancaires et rapprochement -----------------------------------------------------------------

def _sheet_name(title: str, used: set) -> str:
    base = re.sub(r"[\[\]\*\?/\\:]", " ", title).strip()[:28] or "Compte"
    name, k = base, 2
    while name in used:
        name, k = f"{base[:25]} ({k})", k + 1
    used.add(name)
    return name


def operations_workbook(account_id: Optional[int] = None, date_from: Optional[str] = None, date_to: Optional[str] = None) -> bytes:
    """Une feuille par compte : solde d'ouverture, opérations validées et en attente, solde progressif en formule."""
    with unified_db.connect() as conn:
        accounts = conn.execute("SELECT * FROM BankAccounts WHERE IsDeleted = 0" + (" AND Id = ?" if account_id else "") + " ORDER BY Title",
                                (account_id,) if account_id else ()).fetchall()
        style = charts.effective()["style"]
        st = Styler(style, False)
        wb = Workbook()
        wb.remove(wb.active)
        used: set = set()
        for acc in accounts:
            start = date_from or acc["OpeningDate"]
            ops = conn.execute(
                "SELECT o.*, (SELECT GROUP_CONCAT(DISTINCT p.Code) FROM OperationAllocations a LEFT JOIN Projects p ON p.Id = a.ProjectId "
                "  WHERE a.OperationId = o.Id) AS Projects, "
                "(SELECT GROUP_CONCAT(DISTINCT l.Code) FROM OperationAllocations a LEFT JOIN BudgetLines l ON l.Id = a.BudgetLineId "
                "  WHERE a.OperationId = o.Id) AS Lines, "
                "EXISTS (SELECT 1 FROM ReconciliationMatches m WHERE m.OperationId = o.Id) AS Matched "
                "FROM Operations o WHERE o.BankAccountId = ? AND o.IsDeleted = 0 AND o.OperationDate >= ? AND o.OperationDate <= ? "
                "ORDER BY o.OperationDate, o.Id", (acc["Id"], start, date_to or "9999-12-31")).fetchall()
            opening = finance.book_balance(conn, acc["Id"], _day_before(start)) if start > acc["OpeningDate"] else acc["OpeningBalanceMinor"]
            ws = wb.create_sheet(_sheet_name(acc["Title"], used))
            row = st.sheet(ws, f"{acc['Title']} — {acc['BankName']}", f"Devise : {acc['Currency']}. Du {start} au {date_to or 'à ce jour'}. "
                           "Le solde progressif ne retient que les opérations validées.")
            cols = ["Date", "Libellé", "Référence", "Tiers", "Statut", "Projets", "Lignes", "Rapprochée", "Débit", "Crédit", "Solde"]
            st.header(ws, row, cols, [False] * 8 + [True] * 3)
            r = row + 1
            ws.cell(row=r, column=2, value="Solde d'ouverture")
            ws.cell(row=r, column=11, value=opening / 100)
            for j in range(1, 12):
                st.body(ws.cell(row=r, column=j), bold=True, sub=True, fmt=MONEY if j >= 9 else None)
            first = r + 1
            for k, o in enumerate(ops):
                rr = first + k
                debit = o["AmountMinor"] / 100 if o["Direction"] == "Debit" else None
                credit = o["AmountMinor"] / 100 if o["Direction"] == "Credit" else None
                values = [o["OperationDate"], o["Label"], o["Reference"], o["ThirdParty"],
                          {"Validated": "Validée", "Draft": "Brouillon", "Pending": "En attente"}.get(o["Status"], o["Status"]),
                          o["Projects"] or "", o["Lines"] or "", "oui" if o["Matched"] else "non", debit, credit,
                          f'=K{rr - 1}+IF(E{rr}="Validée",N(J{rr})-N(I{rr}),0)']
                for j, v in enumerate(values, start=1):
                    st.body(ws.cell(row=rr, column=j, value=v), fmt=MONEY if j >= 9 else None)
            last = first + len(ops) - 1
            tr_ = last + 1
            ws.cell(row=tr_, column=2, value="Totaux (opérations validées) et solde de clôture")
            ws.cell(row=tr_, column=9, value=f'=SUMIFS(I{first}:I{max(last, first)},E{first}:E{max(last, first)},"Validée")' if ops else 0)
            ws.cell(row=tr_, column=10, value=f'=SUMIFS(J{first}:J{max(last, first)},E{first}:E{max(last, first)},"Validée")' if ops else 0)
            ws.cell(row=tr_, column=11, value=f"=K{row + 1}+J{tr_}-I{tr_}")
            for j in range(1, 12):
                st.body(ws.cell(row=tr_, column=j), bold=True, sub=True, fmt=MONEY if j >= 9 else None)
            if ops:
                ws.auto_filter.ref = f"A{row}:K{last}"
            st.widths(ws, [12, 40, 16, 22, 11, 12, 12, 11, 14, 14, 15])
    if not wb.sheetnames:
        wb.create_sheet("Aucun compte")
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _day_before(day: str) -> str:
    from datetime import date, timedelta
    return (date.fromisoformat(day) - timedelta(days=1)).isoformat()


def reconciliation_workbook(statement_id: int) -> bytes:
    """État de rapprochement d'un relevé (même formule que ReconciliationService) : solde du relevé
    + opérations non encore au relevé − lignes du relevé non comptabilisées = solde comptable ; écart en formule."""
    with unified_db.connect() as conn:
        st_row = conn.execute("SELECT * FROM BankStatements WHERE Id = ? AND IsDeleted = 0", (statement_id,)).fetchone()
        if st_row is None:
            raise ValueError("Relevé introuvable.")
        acc = conn.execute("SELECT * FROM BankAccounts WHERE Id = ?", (st_row["BankAccountId"],)).fetchone()
        first_start = conn.execute("SELECT MIN(PeriodStart) FROM BankStatements WHERE BankAccountId = ? AND IsDeleted = 0 AND PeriodEnd <= ?",
                                   (acc["Id"], st_row["PeriodEnd"])).fetchone()[0]
        lines = conn.execute(
            "SELECT l.*, m.OperationId, m.Mode, m.Score FROM StatementLines l LEFT JOIN ReconciliationMatches m ON m.StatementLineId = l.Id "
            "WHERE l.BankStatementId = ? ORDER BY l.OperationDate, l.Id", (statement_id,)).fetchall()
        open_lines = conn.execute(
            "SELECT l.* FROM StatementLines l JOIN BankStatements b ON b.Id = l.BankStatementId WHERE b.BankAccountId = ? AND b.IsDeleted = 0 "
            "AND b.PeriodEnd <= ? AND NOT EXISTS (SELECT 1 FROM ReconciliationMatches m WHERE m.StatementLineId = l.Id) ORDER BY l.OperationDate",
            (acc["Id"], st_row["PeriodEnd"])).fetchall()
        open_ops = conn.execute(
            "SELECT * FROM Operations o WHERE o.BankAccountId = ? AND o.Status = 'Validated' AND o.IsDeleted = 0 AND o.OperationDate >= ? "
            "AND o.OperationDate <= ? AND NOT EXISTS (SELECT 1 FROM ReconciliationMatches m WHERE m.OperationId = o.Id) ORDER BY o.OperationDate",
            (acc["Id"], first_start, st_row["PeriodEnd"])).fetchall()
        book = finance.book_balance(conn, acc["Id"], st_row["PeriodEnd"])
        ops_by_id = {r["Id"]: r for r in conn.execute("SELECT Id, Label, OperationDate FROM Operations WHERE BankAccountId = ?", (acc["Id"],))}
    st = Styler(charts.effective()["style"], False)
    wb = Workbook()
    ws = wb.active
    ws.title = "État de rapprochement"
    row = st.sheet(ws, f"Rapprochement — {acc['Title']}", f"Relevé du {st_row['PeriodStart']} au {st_row['PeriodEnd']} (n° {statement_id}).")

    def section(ws_, title, items, r):
        ws_.cell(row=r, column=1, value=title).font = Font(name=st.font, bold=True)
        st.header(ws_, r + 1, ["Date", "Libellé", "Référence", "Montant (signé)"], [False, False, False, True])
        first_ = r + 2
        for k, (d, label, ref, amount) in enumerate(items):
            for j, v in enumerate((d, label, ref, amount), start=1):
                st.body(ws_.cell(row=first_ + k, column=j, value=v), fmt=MONEY if j == 4 else None)
        last_ = first_ + len(items) - 1
        total_cell = f"SUM(D{first_}:D{last_})" if items else "0"
        return last_ + 2, total_cell

    ws.freeze_panes = None
    r = row
    summary_row = r
    r += 7
    r, ops_total = section(ws, "Opérations comptabilisées absentes du relevé", [
        (o["OperationDate"], o["Label"], o["Reference"], (o["AmountMinor"] if o["Direction"] == "Credit" else -o["AmountMinor"]) / 100) for o in open_ops], r)
    r, lines_total = section(ws, "Lignes du relevé non comptabilisées", [
        (l["OperationDate"], l["Label"], l["Reference"], (l["CreditMinor"] - l["DebitMinor"]) / 100) for l in open_lines], r)
    summary = [("Solde de clôture du relevé", st_row["ClosingBalanceMinor"] / 100),
               ("+ Opérations comptabilisées absentes du relevé", f"={ops_total}"),
               ("− Lignes du relevé non comptabilisées", f"={lines_total}"),
               ("= Solde rapproché", f"=B{summary_row}+B{summary_row + 1}-B{summary_row + 2}"),
               ("Solde comptable (opérations validées)", book / 100),
               ("Écart (doit être nul)", f"=B{summary_row + 4}-B{summary_row + 3}")]
    for k, (label, v) in enumerate(summary):
        for j, val in enumerate((label, v), start=1):
            st.body(ws.cell(row=summary_row + k, column=j, value=val), bold=k in (3, 5), sub=k in (3, 5), fmt=MONEY if j == 2 else None)
    st.widths(ws, [46, 40, 18, 16])

    ws2 = wb.create_sheet("Lignes du relevé")
    row2 = st.sheet(ws2, "Lignes du relevé et opérations rapprochées", "")
    st.header(ws2, row2, ["Date", "Libellé", "Référence", "Débit", "Crédit", "Opération rapprochée", "Mode", "Score"],
              [False, False, False, True, True, False, False, True])
    for k, l in enumerate(lines):
        op = ops_by_id.get(l["OperationId"]) if l["OperationId"] else None
        values = [l["OperationDate"], l["Label"], l["Reference"], l["DebitMinor"] / 100 or None, l["CreditMinor"] / 100 or None,
                  f"{op['OperationDate']} — {op['Label']}" if op else "non rapprochée", l["Mode"] or "", l["Score"]]
        for j, v in enumerate(values, start=1):
            st.body(ws2.cell(row=row2 + 1 + k, column=j, value=v), fmt=MONEY if j in (4, 5) else ("0.00" if j == 8 else None))
    last2 = row2 + len(lines)
    tr2 = last2 + 1
    ws2.cell(row=tr2, column=3, value="Totaux")
    ws2.cell(row=tr2, column=4, value=f"=SUM(D{row2 + 1}:D{last2})" if lines else 0)
    ws2.cell(row=tr2, column=5, value=f"=SUM(E{row2 + 1}:E{last2})" if lines else 0)
    ws2.cell(row=tr2 + 1, column=3, value="Contrôle : ouverture + crédits − débits − clôture")
    ws2.cell(row=tr2 + 1, column=4, value=f"={st_row['OpeningBalanceMinor'] / 100}+E{tr2}-D{tr2}-{st_row['ClosingBalanceMinor'] / 100}")
    for c in (3, 4, 5):
        for rr in (tr2, tr2 + 1):
            st.body(ws2.cell(row=rr, column=c), bold=True, sub=True, fmt=MONEY if c > 3 else None)
    st.widths(ws2, [12, 40, 16, 14, 14, 40, 12, 8])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
