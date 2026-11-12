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
        while j >= 0 and GROUP_RE.match(clean_numeric(line[j].text)) and parts[0].x0 - line[j].x1 < 1.2 * h:
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


def find_header(line: List[Word], columns: Dict[str, List[str]]) -> Optional[Dict[str, Word]]:
    """Positions des colonnes si la ligne est un en-tête (au moins une date et un montant)."""
    tokens = [normalize(w.text) for w in line]
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
        for w in l[1:]:
            if id(w) in amount_ids:
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
