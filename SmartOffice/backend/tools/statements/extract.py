"""Reconstruction d'un relevé à partir des mots positionnés (PDF natif ou OCR).

1. Regroupement des mots en lignes (par ordonnée).
2. Repérage de la ligne d'en-tête des colonnes (date, libellé, valeur, débit, crédit…) et de leurs positions.
3. Une opération commence par une date ; les lignes sans date prolongent le libellé précédent.
4. Les montants (avec 2 décimales, milliers séparés par des espaces recollés) sont rangés dans la colonne débit ou
   crédit la plus proche ; soldes initial et final repérés par les libellés du gabarit de la banque.
Chaque champ porte une confiance (celle de l'OCR, 0 si la valeur est illisible).
"""
import re
from datetime import date
from statistics import median
from typing import Dict, List, Optional, Tuple

from backend.tools import rib as rib_tools

from .model import ExtractedLine, ExtractedStatement, Word
from .templates import BankTemplate, detect, normalize

DATE_RE = re.compile(r"^(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2}|\d{4})$")
AMOUNT_RE = re.compile(r"^[-+]?\d{1,3}(?:[ .  ]?\d{3})*[,.]\d{2}-?$")
GROUP_RE = re.compile(r"^\d{1,3}$")
PERIOD_RE = re.compile(r"(\d{1,2}[/.]\d{1,2}[/.]\d{2,4})\s*(?:au|a|à|-|–|jusqu)\s*(\d{1,2}[/.]\d{1,2}[/.]\d{2,4})", re.IGNORECASE)
_DIGIT_FIX = str.maketrans({"O": "0", "o": "0", "D": "0", "Q": "0", "l": "1", "I": "1", "|": "1", "i": "1", "S": "5", "s": "5", "B": "8", "Z": "2"})


def clean_numeric(token: str) -> str:
    """Corrige les confusions OCR classiques (O/0, l/1, S/5…) dans un jeton surtout numérique."""
    digits = sum(c.isdigit() for c in token)
    if digits == 0 or digits < 0.5 * len([c for c in token if c.isalnum()]):
        return token
    return token.translate(_DIGIT_FIX).rstrip(".:;")


def parse_date(token: str, default_year: Optional[int] = None) -> Optional[str]:
    m = DATE_RE.match(clean_numeric(token))
    if not m:
        return None
    d, mo, y = (int(g) for g in m.groups())
    if y < 100:
        y += 2000
    try:
        return date(y, mo, d).isoformat()
    except ValueError:
        return None


def parse_amount(text: str) -> Optional[int]:
    t = clean_numeric(text.replace(" ", " ").replace(" ", " ")).strip()
    negative = t.startswith("-") or t.endswith("-")
    t = t.strip("-+")
    if not AMOUNT_RE.match(t):
        return None
    t = t.replace(" ", "")
    int_part, dec = t[:-3], t[-2:]
    int_part = int_part.replace(".", "").replace(",", "")
    if not int_part.isdigit():
        return None
    value = int(int_part) * 100 + int(dec)
    return -value if negative else value


def group_lines(words: List[Word]) -> List[List[Word]]:
    if not words:
        return []
    h = median(w.h for w in words)
    lines: List[List[Word]] = []
    for w in sorted(words, key=lambda w: (w.page, w.yc)):
        if lines and lines[-1][0].page == w.page and abs(w.yc - sum(x.yc for x in lines[-1]) / len(lines[-1])) < 0.55 * h:
            lines[-1].append(w)
        else:
            lines.append([w])
    return [sorted(l, key=lambda w: w.x0) for l in lines]


def merge_amounts(line: List[Word]) -> List[Tuple[Word, int]]:
    """Recolle « 14 » « 185,73 » en un montant ; retourne (mot fusionné, centimes)."""
    out: List[Tuple[Word, int]] = []
    used = set()
    h = median(w.h for w in line) if line else 10
    for i in range(len(line) - 1, -1, -1):
        if i in used:
            continue
        w = line[i]
        if parse_amount(w.text) is None:
            continue
        parts, j = [w], i - 1
        while j >= 0 and GROUP_RE.match(clean_numeric(line[j].text)) and parts[0].x0 - line[j].x1 < 1.6 * h:
            parts.insert(0, line[j])
            j -= 1
        text = " ".join(p.text for p in parts)
        value = parse_amount(text)
        if value is None:
            parts, value = [w], parse_amount(w.text)
        used.update(range(j + 1, i + 1) if len(parts) > 1 else [i])
        merged = Word(text, parts[0].x0, min(p.y0 for p in parts), parts[-1].x1, max(p.y1 for p in parts),
                      min(p.conf for p in parts), w.page)
        out.append((merged, value))
    return list(reversed(out))


def _lev(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _fuzzy(token: str, word: str) -> str:
    """Mot d'en-tête mal lu par l'OCR (« degir » pour « debit ») : rapproché si la différence est minime."""
    if token == word or len(word) < 5 or len(token) < 4:
        return token
    return word if _lev(token, word) <= (1 if len(word) < 5 else 2) else token


def find_header(line: List[Word], columns: Dict[str, List[str]]) -> Optional[Dict[str, Word]]:
    """Positions des colonnes si la ligne est un en-tête (au moins une date et un montant)."""
    vocab = {w for ps in columns.values() for p in ps for w in p.split()}
    tokens = []
    for w in line:
        t = normalize(w.text)
        tokens.append(next((v for v in vocab if _fuzzy(t, v) == v), t) if t and t not in vocab else t)
    anchors: Dict[str, Word] = {}
    i = 0
    phrases = sorted(((k, p.split()) for k, ps in columns.items() for p in ps), key=lambda kp: -len(kp[1]))
    while i < len(tokens):
        for key, words in phrases:
            n = len(words)
            if tokens[i:i + n] == words and key not in anchors:
                span = line[i:i + n]
                anchors[key] = Word(" ".join(w.text for w in span), span[0].x0, span[0].y0, span[-1].x1, span[-1].y1, min(w.conf for w in span), span[0].page)
                i += n
                break
        else:
            i += 1
    if "date" in anchors and ({"debit", "credit", "amount"} & anchors.keys()) and len(anchors) >= 3:
        return anchors
    return None


DAY_MONTH_YEAR_RE = re.compile(r"(?<!\d)(\d{1,2})[\s/.\-]+(\d{1,2})[\s/.\-]+(\d{4}|\d{2})(?!\d)")


def _column_text(line: List[Word], x_from: float, x_to: float) -> str:
    return " ".join(w.text for w in line if w.xc >= x_from and w.xc < x_to)


def _date_words(line: List[Word], anchors: Dict[str, Word]) -> List[Word]:
    """Jetons de tête qui portent le code et la date (avant le libellé) : ceux qui contiennent des chiffres."""
    label = anchors.get("label")
    out = []
    for w in line[:4]:
        if not re.search(r"\d", w.text) or (label is not None and w.xc >= label.xc):
            break
        out.append(w)
    return out


def _date_in_columns(line: List[Word], anchors: Dict[str, Word], year: Optional[int]) -> Optional[str]:
    """Date d'opération lue dans les colonnes avant le libellé, quand elle n'est pas un jeton jj/mm/aaaa :
    « 0016PV|13 07| » (code d'opération collé au jour, jour et mois sans année) → 13/07 de l'année du relevé."""
    label = anchors.get("label")
    if label is None:
        return None
    pre = _date_words(line, anchors)
    if not pre:
        return None
    text = " ".join(w.text for w in pre)
    m = DAY_MONTH_YEAR_RE.search(text.replace("|", " ").replace("]", " "))
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        y = y + 2000 if y < 100 else y
    else:
        pieces = re.findall(r"\d+", text)
        if len(pieces) < 2 or year is None:
            return None
        d, mo, y = int(pieces[-2][-2:]), int(pieces[-1][-2:]), year
    try:
        return date(y, mo, d).isoformat()
    except ValueError:
        return None


def _value_date_in_columns(line: List[Word], anchors: Dict[str, Word], zone: float) -> Optional[str]:
    """Date de valeur écrite en trois groupes (« 11 07 2026 ») dans sa colonne."""
    v = anchors.get("value_date")
    if v is None:
        return None
    lo = v.x0 - 2 * v.h
    m = DAY_MONTH_YEAR_RE.search(_column_text(line, lo, zone).replace("|", " "))
    if not m:
        return None
    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        return date(y + 2000 if y < 100 else y, mo, d).isoformat()
    except ValueError:
        return None


def _header_words(line: List[Word], columns: Dict[str, List[str]]) -> Dict[str, Word]:
    """Mots d'en-tête isolés d'une ligne voisine (un seul mot par colonne : « VALEUR », « DEBIT »…)."""
    out: Dict[str, Word] = {}
    single = {p: k for k, ps in columns.items() for p in ps if " " not in p}
    for w in line:
        t = normalize(w.text)
        for p, k in single.items():
            if _fuzzy(t, p) == p and k not in out and len(t) >= 4:
                out[k] = w
    return out


def _amount_column(word: Word, anchors: Dict[str, Word]) -> Optional[str]:
    candidates = [k for k in ("debit", "credit", "amount") if k in anchors]
    if not candidates:
        return None

    def dist(k: str) -> float:
        a = anchors[k]
        return min(abs(word.x0 - a.x0), abs(word.x1 - a.x1), abs(word.xc - a.xc))
    return min(candidates, key=dist)


def _amount_zone_start(anchors: Dict[str, Word]) -> float:
    amount_x = min(anchors[k].x0 for k in ("debit", "credit", "amount") if k in anchors)
    previous = [a.x0 for k, a in anchors.items() if k not in ("debit", "credit", "amount") and a.x0 < amount_x]
    prev_x = max(previous) if previous else 0
    return amount_x - 0.25 * (amount_x - prev_x)


def _balance_near(lines: List[List[Word]], idx: int) -> Tuple[Optional[int], float]:
    """Montant du solde : sur la même ligne, sinon sur la ligne suivante si elle ne contient qu'un montant."""
    for k in (idx, idx + 1):
        if k >= len(lines):
            break
        amounts = merge_amounts(lines[k])
        if amounts and (k == idx or len(amounts) == len(lines[k]) or all(parse_amount(w.text) is not None or GROUP_RE.match(w.text) for w in lines[k])):
            word, value = amounts[-1]
            text = normalize(" ".join(w.text for w in lines[k]))
            if " debiteur" in f" {text}" or text.endswith(" d"):
                value = -abs(value)
            return value, word.conf
    return None, 0.0


def extract(words: List[Word], templates: List[BankTemplate], columns: Dict[str, List[str]], engine: str,
            page_heights: Optional[Dict[int, float]] = None) -> ExtractedStatement:
    lines = group_lines(words)
    full_text = "\n".join(" ".join(w.text for w in l) for l in lines)
    template = detect(full_text, templates)
    st = ExtractedStatement(bank_id=template.id, bank_name=template.name, engine=engine,
                            pages=len({w.page for w in words}) if words else 0)

    # Période et RIB
    m = PERIOD_RE.search(full_text)
    if m:
        st.period_start, st.period_end = parse_date(m.group(1)), parse_date(m.group(2))
    for l in lines:
        compact = re.sub(r"[^\d]", "", " ".join(clean_numeric(w.text) for w in l if any(c.isdigit() for c in w.text)))
        for start in range(0, max(0, len(compact) - 23)):
            check = rib_tools.check(compact[start:start + 24])
            if check.is_valid:
                st.rib = check.normalized
                break
        if st.rib:
            break
    if not st.rib:
        st.warnings.append("RIB non trouvé ou clé RIB invalide sur le relevé.")

    # Soldes
    opening_idx = closing_idx = None
    for i, l in enumerate(lines):
        text = " " + normalize(" ".join(w.text for w in l)) + " "
        if opening_idx is None and any(f" {p} " in text for p in template.opening):
            opening_idx = i
        if any(f" {p} " in text for p in template.closing):
            closing_idx = i
    if opening_idx is not None:
        st.opening, st.confidence["opening"] = _balance_near(lines, opening_idx)
    if closing_idx is not None:
        st.closing, st.confidence["closing"] = _balance_near(lines, closing_idx)
    if st.opening is None:
        st.warnings.append("Solde initial non trouvé : saisissez-le.")
    if st.closing is None:
        st.warnings.append("Solde final non trouvé : saisissez-le.")

    # Opérations
    anchors: Optional[Dict[str, Word]] = None
    current: Optional[ExtractedLine] = None
    headers = {i: h for i, l in enumerate(lines) if (h := find_header(l, columns))}
    for i, h in headers.items():                      # en-tête sur deux lignes (« VALEUR » au-dessus, libellés arabes…)
        for k in (i - 1, i + 1):
            if 0 <= k < len(lines) and k not in headers:
                extra = find_header(lines[k] + [h["date"]], columns) or {}
                lone = _header_words(lines[k], columns)
                for key, w in {**lone, **extra}.items():
                    h.setdefault(key, w)
    year_hint = None
    for d in (st.period_end, st.period_start):
        if d:
            year_hint = int(d[:4])
            break
    if year_hint is None:
        ym = re.findall(r"(?<!\d)(20\d{2})(?!\d)", full_text)
        year_hint = int(max(set(ym), key=ym.count)) if ym else None
    first_header_on_page = {}
    for i in headers:
        first_header_on_page.setdefault(lines[i][0].page, i)
    page = -1
    for i, l in enumerate(lines):
        if l[0].page != page:
            page, current = l[0].page, None   # une opération ne se prolonge jamais sur la page suivante
        if i in (opening_idx, closing_idx):
            current = None
            continue
        if i in headers:
            anchors, current = headers[i], None
            continue
        # En-tête répété en haut de page (banque, RIB, période…) : ignoré jusqu'à l'en-tête des colonnes de la page.
        if anchors is None or i < first_header_on_page.get(page, -1):
            continue
        text_norm = normalize(" ".join(w.text for w in l))
        if text_norm.startswith(("total", "totaux", "page", "report", "a reporter")):
            current = None
            continue

        first_date = parse_date(l[0].text)
        zone = _amount_zone_start(anchors)
        pre_ids = set()
        if first_date is None and not text_norm.startswith(("solde", "nous avons")):
            first_date = _date_in_columns(l, anchors, year_hint)
            if first_date:
                pre_ids = {id(w) for w in _date_words(l, anchors)}
        amounts = [(w, v) for w, v in merge_amounts(l) if w.x1 > zone]
        amount_ids = {id(x) for w, _ in amounts for x in l if x.x0 >= w.x0 - 0.5 and x.x1 <= w.x1 + 0.5}

        if first_date is None:
            # Suite du libellé de l'opération précédente
            if current is not None and not amounts:
                extra = " ".join(w.text for w in l if w.x1 <= zone)
                if extra:
                    current.label = (current.label + " " + extra).strip()
                    current.confidence["label"] = min(current.confidence.get("label", 100), sum(w.conf for w in l) / len(l))
            continue

        conf: Dict[str, float] = {"date": l[0].conf}
        value_date = None
        label_words, ref_words = [], []
        if pre_ids:
            code = re.split(r"[|\]]", l[0].text)[0]
            if code and not code.isdigit() or len(code) > 2:
                ref_words.append(Word((re.sub(r"[|\]I]?\d{1,2}$", "", code) or code).strip("/|-"), l[0].x0, l[0].y0, l[0].x1, l[0].y1, l[0].conf, l[0].page))
            vd = _value_date_in_columns(l, anchors, zone)
            if vd:
                value_date, conf["value_date"] = vd, l[0].conf
        if pre_ids:                                   # « 07|PRELEVEMENT » : la fin du jeton de date ouvre le libellé
            for w in l:
                if id(w) in pre_ids:
                    tail = re.split(r"[|\]]", w.text, maxsplit=1)
                    if len(tail) == 2 and re.match(r"[A-Za-zÀ-ÿ]{2,}", tail[1]):
                        label_words.append(Word(tail[1], w.x0, w.y0, w.x1, w.y1, w.conf, w.page))
        for w in (l if pre_ids else l[1:]):
            if id(w) in amount_ids or id(w) in pre_ids:
                continue
            if pre_ids and value_date and "value_date" in anchors and w.xc >= anchors["value_date"].x0 - 2 * anchors["value_date"].h and w.x1 <= zone:
                continue
            d = parse_date(w.text)
            if d and "value_date" in anchors and abs(w.x0 - anchors["value_date"].x0) < abs(w.x0 - anchors.get("label", anchors["date"]).x0):
                value_date, conf["value_date"] = d, w.conf
                continue
            if "reference" in anchors and "label" in anchors and abs(w.x0 - anchors["reference"].x0) < abs(w.x0 - anchors["label"].x0) and not label_words:
                ref_words.append(w)
            else:
                label_words.append(w)

        debit = credit = 0
        for w, v in amounts:
            col = _amount_column(w, anchors)
            if col == "amount":
                debit, credit = (-v, 0) if v < 0 else (0, v)
                conf["debit"] = conf["credit"] = w.conf
            elif col == "debit":
                debit, conf["debit"] = abs(v), w.conf
            elif col == "credit":
                credit, conf["credit"] = abs(v), w.conf
        if amounts:  # la colonne restée vide est aussi sûre que le montant lu sur la ligne
            found = max(conf.get("debit", 0), conf.get("credit", 0))
            conf.setdefault("debit", found)
            conf.setdefault("credit", found)
        else:
            conf["debit"] = conf["credit"] = 0.0
            st.warnings.append(f"Opération du {first_date} sans montant lisible.")
        # Libellé : confiance moyenne (un mot isolé peu sûr n'en fait pas un libellé faux) ; dates et montants : minimum.
        conf["label"] = sum(w.conf for w in label_words) / len(label_words) if label_words else 0.0

        height = (page_heights or {}).get(l[0].page)
        current = ExtractedLine(
            date=first_date, value_date=value_date,
            label=" ".join(w.text for w in label_words), reference=" ".join(w.text for w in ref_words),
            debit=debit, credit=credit, confidence={k: round(v, 1) for k, v in conf.items()},
            page=l[0].page, y=round(l[0].yc / height, 4) if height else 0.0,
        )
        st.lines.append(current)

    if st.lines and not st.period_start:
        st.period_start = min(l.date for l in st.lines if l.date)
        st.period_end = max(l.date for l in st.lines if l.date)
    if anchors is None:
        st.warnings.append("En-tête des colonnes (Date, Libellé, Débit, Crédit) non reconnu : aucune opération extraite.")
    ok = st.balance_ok()
    if ok is False:
        st.warnings.append("Solde initial + mouvements ≠ solde final : une ligne est probablement mal lue, vérifiez les montants surlignés.")
    return st
