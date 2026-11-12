"""Montants, devises, dates et périodes tels qu'ils sont écrits dans les documents des bailleurs (FR, EN, formats mixtes)."""
import re
from calendar import monthrange
from datetime import date, timedelta
from typing import Optional, Tuple

MONTHS = {
    "janvier": 1, "janv": 1, "january": 1, "jan": 1, "février": 2, "fevrier": 2, "févr": 2, "fevr": 2, "february": 2, "feb": 2,
    "mars": 3, "march": 3, "mar": 3, "avril": 4, "avr": 4, "april": 4, "apr": 4, "mai": 5, "may": 5,
    "juin": 6, "june": 6, "jun": 6, "juillet": 7, "juil": 7, "july": 7, "jul": 7, "août": 8, "aout": 8, "august": 8, "aug": 8,
    "septembre": 9, "sept": 9, "september": 9, "sep": 9, "octobre": 10, "oct": 10, "october": 10,
    "novembre": 11, "nov": 11, "november": 11, "décembre": 12, "decembre": 12, "déc": 12, "dec": 12, "december": 12,
}
_MONTH_RE = "|".join(sorted(MONTHS, key=len, reverse=True))

CURRENCIES = {
    "MAD": ("MAD", "DH", "DHS", "DIRHAM", "DIRHAMS"), "USD": ("USD", "US$", "$", "DOLLAR", "DOLLARS"),
    "EUR": ("EUR", "€", "EURO", "EUROS"), "CAD": ("CAD", "CA$"), "GBP": ("GBP", "£"), "CHF": ("CHF",), "JPY": ("JPY", "YEN", "¥"),
}

# Nombre : 465 000,00 · 50.000 · 50.000,00 · $117,930.00 · 139882.0049 · 1 234 567 · 50. 000,00 (coquille fréquente)
NUMBER_RE = re.compile(r"(?<![\w/])-?\d{1,3}(?:[   .,]\s?\d{3})+(?:[.,]\d{1,4})?(?!\d)|(?<![\w/.,])-?\d+(?:[.,]\d{1,4})?(?![\d/])")


def parse_amount(text: str) -> Optional[float]:
    """Interprète un montant écrit à la française, à l'anglaise ou mixte. None si ce n'est pas un nombre."""
    if text is None:
        return None
    if isinstance(text, (int, float)):
        return float(text)
    s = str(text).strip().replace(" ", " ").replace(" ", " ")
    s = re.sub(r"[^\d,.\- ]", "", s).strip()
    if not s or not re.search(r"\d", s):
        return None
    neg = s.startswith("-")
    s = s.lstrip("-").strip()
    s = re.sub(r"(?<=[.,])\s+(?=\d)", "", s)                 # « 50. 000,00 »
    s = s.replace(" ", "")
    last_dot, last_comma = s.rfind("."), s.rfind(",")
    if last_dot >= 0 and last_comma >= 0:                     # les deux : le dernier est le séparateur décimal
        dec = "." if last_dot > last_comma else ","
        thou = "," if dec == "." else "."
        s = s.replace(thou, "").replace(dec, ".")
    elif last_comma >= 0:
        parts = s.split(",")
        if len(parts) == 2 and len(parts[1]) != 3:
            s = s.replace(",", ".")                           # 465000,5 ou 9,30
        elif len(parts) == 2 and len(parts[0]) > 3:
            s = s.replace(",", ".")                           # 1000,500 : décimal
        else:
            s = s.replace(",", "")                            # 117,930 : milliers
    elif last_dot >= 0:
        parts = s.split(".")
        if len(parts) > 2 or (len(parts) == 2 and len(parts[1]) == 3 and len(parts[0]) <= 3 and parts[0] != "0"):
            s = s.replace(".", "")                            # 50.000 ou 1.234.567 : milliers
    try:
        v = float(s)
    except ValueError:
        return None
    return -v if neg else v


def round_money(v: Optional[float]) -> Optional[float]:
    return None if v is None else round(v + 0.0, 2)


def detect_currency(text: str, default: str = "") -> str:
    up = f" {text.upper()} "
    for code, marks in CURRENCIES.items():
        for m in marks:
            if m in ("$", "€", "£", "¥"):
                if m in up:
                    return code
            elif re.search(rf"(?<![A-Z]){re.escape(m)}(?![A-Z])", up):
                return code
    return default


def amounts_in(text: str):
    """Montants d'une ligne, dans l'ordre (ignore les années isolées et les pourcentages)."""
    out = []
    for m in NUMBER_RE.finditer(text):
        raw = m.group(0)
        tail = text[m.end():m.end() + 2]
        if tail.strip().startswith("%"):
            continue
        v = parse_amount(raw)
        if v is None:
            continue
        out.append((v, raw, m.start()))
    return out


def _mk(y: int, m: int, d: int) -> Optional[date]:
    try:
        return date(y, m, d)
    except ValueError:
        return None


def parse_date(text: str, us: bool = False) -> Optional[date]:
    """1er octobre 2026 · 30 juin 2027 · 12/09/2026 · 5/1/2020 (us=True) · 2026-10-01 · June 1, 2020 · Juillet 2020 (1er du mois)."""
    if not text:
        return None
    s = str(text).strip().lower().replace("1er", "1").replace("1st", "1")
    m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if m:
        return _mk(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.search(r"(\d{1,2})\s*[/.\-]\s*(\d{1,2})\s*[/.\-]\s*(\d{2,4})", s)
    if m:
        a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        y = y + 2000 if y < 100 else y
        if a > 12:
            us = False
        elif b > 12:
            us = True
        return _mk(y, a, b) if us else _mk(y, b, a)
    m = re.search(rf"(\d{{1,2}})\s*(?:er|e)?\s+({_MONTH_RE})\.?\s+(\d{{4}})", s)
    if m:
        return _mk(int(m.group(3)), MONTHS[m.group(2)], int(m.group(1)))
    m = re.search(rf"({_MONTH_RE})\.?\s+(\d{{1,2}}),?\s+(\d{{4}})", s)
    if m:
        return _mk(int(m.group(3)), MONTHS[m.group(1)], int(m.group(2)))
    m = re.search(rf"({_MONTH_RE})\.?\s+(\d{{4}})", s)
    if m:
        return _mk(int(m.group(2)), MONTHS[m.group(1)], 1)
    return None


def dates_in(text: str, us: bool = False):
    pat = re.compile(rf"\d{{4}}-\d{{1,2}}-\d{{1,2}}|\d{{1,2}}\s*/\s*\d{{1,2}}\s*/\s*\d{{2,4}}|\d{{1,2}}\s*(?:er|e)?\s+(?:{_MONTH_RE})\.?\s+\d{{4}}|"
                     rf"(?:{_MONTH_RE})\.?\s+\d{{1,2}},?\s+\d{{4}}", re.I)
    out = []
    for m in pat.finditer(text):
        d = parse_date(m.group(0), us)
        if d:
            out.append((d, m.group(0), m.start()))
    return out


def add_months(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    y, m = d.year + y, m + 1
    return date(y, m, min(d.day, monthrange(y, m)[1]))


def quarter_span(start: date, q_from: int, q_to: Optional[int] = None) -> Tuple[date, date]:
    """Trimestres du projet (T1 = trois premiers mois à partir de la date de début)."""
    q_to = q_to or q_from
    return add_months(start, 3 * (q_from - 1)), add_months(start, 3 * q_to) - timedelta(days=1)


def month_span(start: date, m_from: int, m_to: Optional[int] = None) -> Tuple[date, date]:
    m_to = m_to or m_from
    return add_months(start, m_from - 1), add_months(start, m_to) - timedelta(days=1)


def months_between(a: date, b: date) -> int:
    """Durée en mois pleins entre deux dates incluses (1/10/2026 → 30/9/2028 = 24)."""
    end = b + timedelta(days=1)
    return (end.year - a.year) * 12 + end.month - a.month


def relative_period(text: str) -> Optional[Tuple[str, int, int]]:
    """« T3 », « T2 à T5 », « Mois 1 à 3 », « M4-M6 », « Année 2 » → (unité, début, fin)."""
    s = text.lower()
    m = re.search(r"mois\s*(\d{1,2})\s*(?:à|a|-|–|au)\s*(?:mois\s*)?(\d{1,2})", s) or re.search(r"\bm(\d{1,2})\s*[-–à]\s*m(\d{1,2})\b", s)
    if m:
        return ("mois", int(m.group(1)), int(m.group(2)))
    m = re.search(r"\bmois\s*(\d{1,2})\b", s)
    if m:
        return ("mois", int(m.group(1)), int(m.group(1)))
    m = re.search(r"\bt(\d)\s*(?:à|a|-|–|au)\s*t(\d)\b", s)
    if m:
        return ("trimestre", int(m.group(1)), int(m.group(2)))
    m = re.search(r"(?:année|annee|year)\s*(\d)", s)
    if m:
        n = int(m.group(1))
        return ("mois", 12 * (n - 1) + 1, 12 * n)
    return None


def digits_key(v: float) -> str:
    """Clé de comparaison d'un montant avec le texte source (sans séparateurs, sans décimales nulles)."""
    if v is None:
        return ""
    v = round(abs(v), 2)
    return str(int(v)) if v == int(v) else f"{v:.2f}".rstrip("0").replace(".", "")
