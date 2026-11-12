"""Relevés exportés par la banque en CSV ou Excel (mêmes règles de colonnes que les gabarits)."""
import csv
import io
from typing import List

from .extract import parse_amount, parse_date
from .model import ExtractedLine, ExtractedStatement
from .templates import load, normalize


def _rows(data: bytes, ext: str) -> List[List[str]]:
    if ext in (".xlsx", ".xlsm"):
        from openpyxl import load_workbook
        ws = load_workbook(io.BytesIO(data), read_only=True, data_only=True).active
        out = []
        for row in ws.iter_rows(values_only=True):
            cells = []
            for v in row:
                if v is None:
                    cells.append("")
                elif hasattr(v, "strftime"):
                    cells.append(v.strftime("%d/%m/%Y"))
                elif isinstance(v, float):
                    cells.append(f"{v:.2f}")
                else:
                    cells.append(str(v))
            out.append(cells)
        return out
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("cp1252")
    first = text.splitlines()[0] if text else ""
    sep = max([";", "\t", ","], key=first.count)
    return [r for r in csv.reader(io.StringIO(text), delimiter=sep)]


def _money(cell: str):
    c = cell.strip().replace("MAD", "").replace("DH", "").strip()
    if not c:
        return 0
    if "," not in c and "." not in c:
        c += ",00"
    elif c.count(".") == 1 and "," not in c and len(c.split(".")[1]) == 1:
        c += "0"
    return parse_amount(c)


def read(data: bytes, ext: str) -> ExtractedStatement:
    _, columns = load()
    rows = [r for r in _rows(data, ext) if any(c.strip() for c in r)]
    st = ExtractedStatement(engine="tableur", pages=1)
    header_idx, mapping = None, {}
    for i, row in enumerate(rows[:15]):
        norm = [normalize(c) for c in row]
        found = {}
        for key, phrases in columns.items():
            for j, cell in enumerate(norm):
                if cell in phrases and key not in found and j not in found.values():
                    found[key] = j
        if "date" in found and ({"debit", "credit", "amount"} & found.keys()):
            header_idx, mapping = i, found
            break
    if header_idx is None:
        st.warnings.append("En-têtes non reconnus : il faut au moins Date et Débit/Crédit (ou Montant).")
        return st
    for row in rows[header_idx + 1:]:
        cell = lambda k: row[mapping[k]] if k in mapping and mapping[k] < len(row) else ""
        d = parse_date(cell("date").strip()[:10])
        if not d:
            continue
        if "amount" in mapping and not ({"debit", "credit"} <= mapping.keys()):
            v = _money(cell("amount"))
            debit, credit = (abs(v), 0) if v is not None and v < 0 else (0, v or 0)
        else:
            debit, credit = abs(_money(cell("debit")) or 0), abs(_money(cell("credit")) or 0)
        if debit == 0 and credit == 0:
            continue
        st.lines.append(ExtractedLine(d, parse_date(cell("value_date").strip()[:10]) if cell("value_date") else None,
                                      cell("label").strip(), cell("reference").strip(), debit, credit,
                                      {"date": 100.0, "label": 100.0, "debit": 100.0, "credit": 100.0}))
    if st.lines:
        st.period_start = min(l.date for l in st.lines)
        st.period_end = max(l.date for l in st.lines)
    st.warnings.append("Fichier tableur : saisissez les soldes initial et final du relevé.")
    return st
