"""Extraction sans IA : règles de lecture des dossiers de bailleurs (conventions, formulaires, budgets Excel, avenants).

Chaque valeur proposée garde sa source (fichier, page, extrait) pour être vérifiée dans l'écran de revue. Ce moteur
fonctionne hors ligne ; l'IA (module ai.py), si elle est autorisée, complète ce qu'il ne sait pas lire et ses chiffres
sont confrontés au texte des documents.
"""
import re
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from . import normalize as N
from .sources import Source

# Bailleurs connus : expression → nom affiché (l'ordre compte : le plus précis d'abord)
DONORS = [
    (r"ICCA[- ]GSI", "PNUD — PMF/FEM (ICCA-GSI)"),
    (r"Programme de micro-?financements du FEM|PMF[ /-]FEM|GEF SGP|Small Grants Programme|\bSGP\b", "PNUD — PMF/FEM"),
    (r"Programme des Nations Unies pour le D[ée]veloppement|\bPNUD\b|\bUNDP\b", "PNUD"),
    (r"\bCEPF\b|Critical Ecosystem Partnership Fund", "CEPF (Conservation International)"),
    (r"Conservation International", "Conservation International"),
    (r"Ambassade de France|\bSCAC\b", "Ambassade de France — SCAC"),
    (r"\bIKI\b|Internationale Klimaschutzinitiative|International Climate Initiative", "IKI"),
    (r"\bMMFN\b|Mediterranean Model Forest Network|R[ée]seau M[ée]diterran[ée]en des For[êe]ts Mod[èe]les", "RMFM / MMFN"),
    (r"Union europ[ée]enne|European Union|\bUE\b", "Union européenne"),
    (r"\bAFD\b|Agence fran[çc]aise de d[ée]veloppement", "AFD"),
    (r"\bFFEM\b|Fonds fran[çc]ais pour l'environnement mondial", "FFEM"),
    (r"\bGIZ\b", "GIZ"), (r"\bUSAID\b", "USAID"), (r"\bJICA\b", "JICA"), (r"Kusanone|Ambassade du Japon", "Ambassade du Japon (Kusanone)"),
    (r"\bFAO\b", "FAO"), (r"\bMCA\b|Millennium Challenge", "MCA"), (r"\bINDH\b", "INDH"),
]


@dataclass
class Line:
    src: int
    page: int
    text: str


def _ref(sources: List[Source], ln: Line, excerpt: Optional[str] = None) -> Dict[str, Any]:
    return {"file": sources[ln.src].name, "page": ln.page, "excerpt": (excerpt or ln.text).strip()[:240]}


def _lines(sources: List[Source]) -> List[Line]:
    out = []
    for i, s in enumerate(sources):
        for page, text in s.pages:
            for t in text.splitlines():
                out.append(Line(i, page, t))
    return out


def _us_dates(src: Source) -> bool:
    """Le document écrit-il ses dates au format américain (mois/jour/année) ?"""
    us = fr = 0
    for a, b in re.findall(r"\b(\d{1,2})/(\d{1,2})/\d{2,4}", src.text):
        a, b = int(a), int(b)
        us += b > 12 >= a
        fr += a > 12 >= b
    return us > fr or (us == fr == 0 and _is_english(src))


def _search_joined(sources: List[Source], pattern: str, flags=re.I):
    """Recherche sur le texte complet d'un document (lignes jointes) : phrases coupées par la mise en page."""
    rx = re.compile(pattern, flags)
    for i, s in enumerate(sources):
        for page, text in s.pages:
            joined = re.sub(r"\s+", " ", text)
            m = rx.search(joined)
            if m:
                return {"file": s.name, "page": page, "excerpt": joined[max(0, m.start() - 20):m.end() + 20].strip()[:240]}, m
    return None


def _is_english(src: Source) -> bool:
    t = src.text[:20000].lower()
    en = sum(t.count(w) for w in (" the ", " and ", " of ", " shall ", " grant "))
    fr = sum(t.count(w) for w in (" le ", " les ", " des ", " et ", " du "))
    return en > fr


def _clean(v: str) -> str:
    v = re.sub(r"\s{2,}", " ", v or "").strip(" :;,-–|\t")
    return v.strip()


def _field(value: Any, ref: Optional[Dict[str, Any]], engine: str = "règles") -> Dict[str, Any]:
    return {"value": value, "source": ref, "engine": engine}


# ---------------------------------------------------------------- champs de la fiche
def _first(lines: List[Line], pattern: str, flags=re.I) -> Optional[Tuple[Line, re.Match, int]]:
    rx = re.compile(pattern, flags)
    for k, ln in enumerate(lines):
        m = rx.search(ln.text)
        if m:
            return ln, m, k
    return None


def _continuation(lines: List[Line], k: int, start_col: int, stop: str, max_lines: int = 5) -> str:
    """Suite d'un libellé sur les lignes suivantes (même source, même colonne ou plus à droite)."""
    parts = []
    for ln in lines[k + 1:k + 1 + max_lines]:
        if ln.src != lines[k].src:
            break
        t = ln.text
        if not t.strip() or re.search(stop, t, re.I):
            break
        indent = len(t) - len(t.lstrip())
        if indent < start_col - 4:
            break
        parts.append(t.strip())
    return " ".join(parts)


def extract_fields(sources: List[Source], lines: List[Line]) -> Dict[str, Any]:
    f: Dict[str, Any] = {}
    # Référence / code
    hit = _first(lines, r"(?:N[o°º]\.?\s*de\s*r[ée]f[ée]rence|Num[ée]ro du projet|R[ée]f[ée]rence de la convention|Record Number|Grant (?:No|Number))\s*:?\s*([A-Z][A-Z0-9/_.\-]{4,})")
    if hit:
        f["code"] = _field(hit[1].group(1).rstrip("."), _ref(sources, hit[0]))
    else:
        hit = _first(lines, r"\b(CEPF-\d{4,})\b")
        if hit:
            f["code"] = _field(hit[1].group(1), _ref(sources, hit[0]))

    # Intitulé
    title = None
    hit = _first(lines, r"Num[ée]ro et intitul[ée] du projet\s*:\s*(.+)")
    if hit:
        ln, m, k = hit
        t = m.group(1) + " " + _continuation(lines, k, len(ln.text) - len(ln.text.lstrip()), r"^\s*\d+\.\s+\w")
        t = re.sub(r"^[A-Z0-9/_.\-]+\s*[-–]\s*", "", _clean(t))
        title = (t, _ref(sources, ln))
    if not title:
        hit = _first(lines, r"(?:Titre du projet|Intitul[ée] du projet|Project Title)\s*\d?\s*[:|]?\s{0,}(.*)")
        if hit:
            ln, m, k = hit
            col = m.start(1) if m.group(1).strip() else len(ln.text)
            stop = r"(?:Date de soumission|R[ée]sum[ée]|Organisation|Amendment|Record|^\s*[A-Z]\.\s|\d+\s*[-–]\s*\w+\s*:|\w+\s*:\s|^\s*\d+\s*[-–])"
            t = m.group(1) + " " + _continuation(lines, k, max(col - 8, 0), stop)
            if not re.search(r"[.)]\s*$", m.group(1)) and len(t.strip()) == len(m.group(1).strip()):
                nxt = lines[k + 1] if k + 1 < len(lines) else None
                if nxt and nxt.src == ln.src and nxt.text.strip() and not re.search(stop, nxt.text, re.I) and len(nxt.text.strip()) < 120:
                    t += " " + nxt.text.strip()
            t = re.sub(r"^\d\s+", "", _clean(re.sub(r"^\d+\s{2,}", "", t)))
            title = (t, _ref(sources, ln))
    if title and len(title[0]) > 8:
        f["title"] = _field(title[0][:400], title[1])

    # Bailleur : le plus cité dans les premières pages des documents
    scores: Dict[str, Tuple[int, Line]] = {}
    weight = {1: 6, 2: 2, 3: 1}
    for ln in lines:
        if ln.page > 3:
            continue
        for rx, name in DONORS:
            if re.search(rx, ln.text, re.I):
                n, first = scores.get(name, (0, ln))
                scores[name] = (n + weight[ln.page], first)
                break
    if scores:
        name, (n, ln) = max(scores.items(), key=lambda kv: kv[1][0])
        f["donor"] = _field(name, _ref(sources, ln))

    # Période
    rx_period = re.compile(rf"\bdu\s+(\d{{1,2}}(?:er)?\s+\w+\.?\s+\d{{4}}|\d{{1,2}}/\d{{1,2}}/\d{{4}})\s+au\s+(\d{{1,2}}(?:er)?\s+\w+\.?\s+\d{{4}}|\d{{1,2}}/\d{{1,2}}/\d{{4}})", re.I)
    for ln in lines:
        m = rx_period.search(ln.text)
        if m and ("période" in ln.text.lower() or "durée" in ln.text.lower() or "mise en" in ln.text.lower() or "projet" in ln.text.lower()):
            a, b = N.parse_date(m.group(1)), N.parse_date(m.group(2))
            if a and b and b > a:
                f.setdefault("start", _field(a.isoformat(), _ref(sources, ln)))
                f.setdefault("end", _field(b.isoformat(), _ref(sources, ln)))
                break
    if "start" not in f:
        # date d'effet de la convention d'abord (elle prime sur la date proposée dans le formulaire)
        hit = _search_joined(sources, r"effective\s+(\w+\s+\d{1,2},\s*\d{4})|prend effet (?:le|à compter du)\s+(\d{1,2}(?:er)?\s+\w+\s+\d{4})")
        if hit:
            d = N.parse_date(next(g for g in hit[1].groups() if g))
            if d:
                f["start"] = _field(d.isoformat(), hit[0])
    if "start" not in f:
        hit = _first(lines, r"(?:Date de d[ée]but(?: propos[ée]e)?|Project Start Date|Start Date)\s*:?\s*(.+)")
        if hit:
            d = N.parse_date(hit[1].group(1))
            if d:
                f["start"] = _field(d.isoformat(), _ref(sources, hit[0]))
    # Prolongation (avenant) : la nouvelle date de fin l'emporte
    hit = _search_joined(sources, r"extended from\s+(\w+\s+\d{1,2},\s*\d{4})\s+to\s+(\w+\s+\d{1,2},\s*\d{4})|prolong[ée]e?\s+du\s+(\d.+?\d{4})\s+au\s+(\d.+?\d{4})")
    if hit:
        ref, mm = hit
        g = [x for x in mm.groups() if x]
        old, new = N.parse_date(g[0]), N.parse_date(g[1])
        if new:
            f["end"] = _field(new.isoformat(), ref)
            f["_extension"] = {"old_end": old.isoformat() if old else None, "new_end": new.isoformat(), "source": ref}
    hit = _first(lines, r"(?:Dur[ée]e du projet[^\n\d]{0,30}|Project Duration\s*:?|dur[ée]e de projet est de)\s*(\d{1,3})\s*(?:mois|months)")
    if hit:
        f["duration_months"] = _field(int(hit[1].group(1)), _ref(sources, hit[0]))
    if "end" not in f and "start" in f and "duration_months" in f:
        s = date.fromisoformat(f["start"]["value"])
        e = N.add_months(s, f["duration_months"]["value"]) - __import__("datetime").timedelta(days=1)
        f["end"] = _field(e.isoformat(), f["duration_months"]["source"], "calcul (début + durée)")

    # Responsable
    for pat in (r"Project Director is\s+([A-Z][\w'’\- ]+?)[.,\n]", r"Contacts? du responsable du projet[^\n]*?\s{2,}([A-ZÉ][\w'’\-]+(?: [A-ZÉ][\w'’\-]+){1,3})",
                r"(?:Responsable|Coordinat(?:eur|rice)|Chef) du projet\s*:\s*([A-ZÉ][\w'’\-]+(?: [A-ZÉ][\w'’\-]+){1,3})"):
        hit = _first(lines, pat, 0)
        if hit:
            f["manager"] = _field(hit[1].group(1).strip(), _ref(sources, hit[0]))
            break
    if "manager" not in f:
        hit = _first(lines, r"Contacts? du responsable du projet", re.I)
        if hit:
            ln, _, k = hit
            for near in lines[max(0, k - 3):k + 3]:
                m = re.search(r"\s{3,}([A-ZÉ][a-zéèë'’\-]+ [A-ZÉ][a-zéèë'’\-]+)\s*;", near.text)
                if m:
                    f["manager"] = _field(m.group(1), _ref(sources, near))
                    break

    # Lieu
    hit = _first(lines, r"Commune(?: rurale| urbaine)? de\s+([A-ZÉ][\w'’\- ]+)")
    loc = []
    if hit:
        loc.append(hit[1].group(1).strip())
    hit2 = _first(lines, r"Province d['’]\s?([A-ZÉ][\w'’\-]+)|Province de\s+([A-ZÉ][\w'’\-]+)")
    if hit2:
        loc.append("Province " + (hit2[1].group(1) or hit2[1].group(2)))
    if loc:
        f["location"] = _field(", ".join(dict.fromkeys(loc)), _ref(sources, (hit or hit2)[0]))
    hit = _first(lines, r"Objectif (?:du projet|g[ée]n[ée]ral)\s*:\s*(.+)")
    if hit:
        ln, m, k = hit
        t = m.group(1) + " " + _continuation(lines, k, len(ln.text) - len(ln.text.lstrip()), r"R[ée]sultats|Objectifs? sp[ée]cifique")
        f["objective"] = _field(_clean(t)[:600], _ref(sources, ln))
    return f


# ---------------------------------------------------------------- financement
def extract_funding(sources: List[Source], lines: List[Line], fields: Dict[str, Any]) -> Dict[str, Any]:
    fund: Dict[str, Any] = {}

    def grab(pattern: str, key: str, idx: int = 0, currency: Optional[str] = None):
        if key in fund:
            return
        rx = re.compile(pattern, re.I)
        for ln in lines:
            if rx.search(ln.text):
                vals = [a for a in N.amounts_in(ln.text[rx.search(ln.text).end():]) if a[0] >= 100]
                if len(vals) > idx:
                    cur = currency or N.detect_currency(ln.text, "")
                    fund[key] = _field({"amount": N.round_money(vals[idx][0]), "currency": cur}, _ref(sources, ln))
                    return

    # Avenant : « Grant funds are increased by $X from $A to $B »
    hit = _first(lines, r"increased by\s*\$?([\d,.\s]+?)\s+from\s*\$?([\d,.\s]+?)\s+to\s*\$?([\d,.\s]+\d)")
    if hit:
        a, b, c = (N.parse_amount(x) for x in hit[1].groups())
        fund["grant"] = _field({"amount": c, "currency": "USD"}, _ref(sources, hit[0]))
        fund["_amendment"] = {"increase": a, "old": b, "new": c, "source": _ref(sources, hit[0])}
    # Formulaire PMF : colonnes MAD | USD
    rx_pmf = re.compile(r"Total du fonds sollicit[ée]", re.I)
    for ln in lines:
        if rx_pmf.search(ln.text):
            vals = [a[0] for a in N.amounts_in(ln.text) if a[0] >= 100]
            if len(vals) >= 2:
                fund.setdefault("grant", _field({"amount": vals[1], "currency": "USD"}, _ref(sources, ln)))
                fund["grant_mad"] = _field({"amount": vals[0], "currency": "MAD"}, _ref(sources, ln))
            break
    grab(r"^\s*\d*\.?\s*Budget\s*:", "grant")
    grab(r"Total New Budget", "grant", 0, "USD")
    grab(r"Budget pr[ée]vu \(MAD\)", "grant", 0, "MAD")
    grab(r"^\s*Total USD", "grant", 0, "USD")
    grab(r"Subvention demand[ée]e", "requested", 0, "MAD")
    if "grant" not in fund and "requested" in fund:
        fund["grant"] = fund["requested"]
    for ln in lines:
        if re.search(r"Total du fonds du cofinancement", ln.text, re.I):
            vals = [a[0] for a in N.amounts_in(ln.text) if a[0] >= 100]
            if vals:
                fund["cofinancing"] = _field({"amount": vals[0], "currency": "MAD"}, _ref(sources, ln))
        if re.search(r"^\s*Co[ûu]t total du projet\s{2,}", ln.text, re.I) and "total_cost" not in fund:
            vals = [a[0] for a in N.amounts_in(ln.text) if a[0] >= 100]
            if vals:
                fund["total_cost"] = _field({"amount": vals[0], "currency": "MAD"}, _ref(sources, ln))
        m = re.search(r"Taux de change[^\d]{0,90}(\d{1,3}[.,]\d{1,4})|\(taux\s*(\d{1,3}[.,]\d{1,4})\)", ln.text, re.I)
        if m and "exchange_rate" not in fund:
            fund["exchange_rate"] = _field(N.parse_amount(m.group(1) or m.group(2)), _ref(sources, ln))
    if "grant" in fund and not fund["grant"]["value"]["currency"]:
        fund["grant"]["value"]["currency"] = "MAD"
    hit = _first(lines, r"Date\s*:\s*(\d{1,2}/\d{1,2}/\d{4})")
    if hit:
        d = N.parse_date(hit[1].group(1), _is_english(sources[hit[0].src]))
        if d:
            fund["signature_date"] = _field(d.isoformat(), _ref(sources, hit[0]))
    return fund


def extract_tranches(sources: List[Source], lines: List[Line], grant_currency: str) -> List[Dict[str, Any]]:
    out = []
    idx = [k for k, ln in enumerate(lines) if re.search(r"^\s*Tranche\s*\d", ln.text, re.I)]
    for n, k in enumerate(idx):
        end = idx[n + 1] if n + 1 < len(idx) else k + 4
        block = [lines[k]]
        for ln in lines[k + 1:end]:
            if ln.src != lines[k].src or ln.page != lines[k].page or re.match(r"^\s*\d{1,2}\.\s+[A-ZÉ]", ln.text):
                break                                  # rubrique suivante de la convention
            block.append(ln)
        text = " ".join(l.text.strip() for l in block)
        pct = re.search(r"\((\d{1,3})\s*%\)", text)
        amounts = [a[0] for a in N.amounts_in(re.sub(r"n°\s*\d+|\(\d{1,3}\s*%\)", "", text))
                   if a[0] >= 100 and not (1900 < a[0] < 2100 and re.fullmatch(r"\d{4}", a[1]))]      # « 2027 » = année, « 2 000 » = montant
        dts = N.dates_in(text)
        label = re.search(r"Tranche\s*\d+", text, re.I).group(0)
        text_nc = re.split(r"\s\d{1,2}\.\s+[A-ZÉ]", text)[0]                     # s'arrête à la rubrique suivante (« 7. Informations… »)
        cond = re.split(r"[-–]\s*(?=[ÀA]\s?l[a'’]|[ÀA] |Upon|On |Apr[èe]s|D[èe]s|Sur )", text_nc, maxsplit=1)
        condition = cond[1] if len(cond) > 1 else ""
        for a in sorted(N.amounts_in(condition), key=lambda a: -a[2]):
            if a[0] >= 100 and not (1900 < a[0] < 2100 and re.fullmatch(r"\d{4}", a[1])):
                condition = condition[:a[2]] + condition[a[2] + len(a[1]):]
        condition = _clean(condition)
        out.append({"label": label, "percent": float(pct.group(1)) if pct else None, "amount": amounts[-1] if amounts else None,
                    "currency": grant_currency, "date": dts[0][0].isoformat() if dts else None,
                    "condition": condition[:250], "source": _ref(sources, lines[k], text)})
    return out


# ---------------------------------------------------------------- budget
TOTAL_HEADS = [r"total new budget", r"amended budget", r"budget r[ée]vis[ée]", r"co[ûu]t total", r"total approved", r"budget pr[ée]visionnel",
               r"^budget$", r"montant", r"amount", r"total"]
SOURCE_HEADS = r"subvention|cofinancement|contribution|communaut|apport|bailleur|donateur|grant|fonds propres|afmi|association"
SUBTOTAL = re.compile(r"^\s*(sous[- ]?total|subtotal|total|grand total|co[ûu]t total)\b", re.I)


def _budget_from_rows(rows: List[List[Any]], src: Source, sheet: str) -> Optional[Dict[str, Any]]:
    """Budget lu dans un tableau (Excel ou Word) : ligne d'en-tête, colonne du montant prévu, colonnes de financement.
    Les colonnes de libellé et de montant sont reconnues par leur contenu (texte ou nombres), les cellules fusionnées
    (activité, site) sont reportées sur les lignes suivantes."""
    width = max((len(r) for r in rows), default=0)
    rows = [list(r) + [None] * (width - len(r)) for r in rows]
    header_idx = None
    for i, r in enumerate(rows[:40]):
        cells = [str(c).strip().lower() if c is not None else "" for c in r]
        texts = [c for c in cells if c and not re.fullmatch(r"[\d.,\s-]+", c)]
        if len(texts) >= 2 and any(re.search(r"budget|total|montant|amount|co[ûu]t", c) for c in cells):
            numeric_rows = sum(1 for rr in rows[i + 1:i + 10] if sum(isinstance(v, (int, float)) for v in rr) >= 1)
            if numeric_rows >= 2:
                header_idx = i
                break
    if header_idx is None:
        return None
    header = [str(c).strip() if c is not None else "" for c in rows[header_idx]]
    low = [h.lower() for h in header]
    body = rows[header_idx + 1:]
    num_count = [sum(isinstance(r[j], (int, float)) for r in body) for j in range(width)]
    str_count = [sum(isinstance(r[j], str) and bool(r[j].strip()) and not re.fullmatch(r"[\d.,\s-]+", r[j]) for r in body) for j in range(width)]
    numeric_cols = [j for j in range(width) if num_count[j] >= 2 and num_count[j] >= str_count[j]]
    total_col = None
    for h in [r"total new budget", r"amended budget", r"budget r[ée]vis[ée]", r"^total\b", r"co[ûu]t total", r"total approved",
              r"budget pr[ée]visionnel", r"^budget", r"montant", r"amount", r"total"]:
        cand = [j for j in numeric_cols if re.search(h, low[j])]
        if cand:
            total_col = cand[-1] if h in (r"total new budget", r"^total\b") else cand[0]
            break
    if total_col is None:
        return None
    first_num = min(numeric_cols) if numeric_cols else total_col
    text_cols = [j for j in range(first_num) if str_count[j] >= 1 and num_count[j] == 0]
    source_cols = [j for j in numeric_cols if j != total_col and re.search(SOURCE_HEADS, low[j])]
    lines_out, section, declared = [], "", None
    carry: Dict[int, str] = {}
    for r in body:
        texts = {}
        for j in text_cols:
            v = r[j]
            if isinstance(v, str) and v.strip():
                carry[j] = v.strip()
                texts[j] = v.strip()
        any_text = next((str(v).strip() for v in r if isinstance(v, str) and v.strip() and not re.fullmatch(r"[\d.,\s-]+", v)), "")
        nums = {j: float(r[j]) for j in numeric_cols if isinstance(r[j], (int, float))}
        if not any_text and not nums:
            continue
        if any_text and SUBTOTAL.match(any_text):
            if total_col in nums and re.search(r"grand total|^total$|co[ûu]t total|^total (?:usd|mad|eur)|^total g[ée]n[ée]ral", any_text, re.I):
                declared = nums[total_col]
            continue
        if total_col not in nums:
            if any_text and not re.fullmatch(r"\s*(\d+(\.\d+)*)?\s*", any_text):
                section = any_text
            continue
        own = [j for j in text_cols if j in texts]
        if own:
            label = texts[own[-1]]
            parents = [carry.get(j, "") for j in text_cols if j < own[-1]] if own[-1] != text_cols[0] else []
            category = next((n for n in reversed(parents) if n and n != label), section) or section
        else:
            label = any_text or (carry.get(text_cols[-1], "") if text_cols else "") or section
            category = section
        code_m = re.match(r"^\s*(\d+(?:\.\d+)*|[A-Z]\d+(?:\.\d+)*)[.)]?\s+(.*)", label)
        code, lab = (code_m.group(1), code_m.group(2)) if code_m else ("", label)
        lines_out.append({"code": code, "category": category if category != lab else "", "activity_code": _activity_code(category),
                          "label": lab[:250], "total": N.round_money(nums[total_col]),
                          "by_source": {header[j]: N.round_money(nums.get(j, 0.0)) for j in source_cols},
                          "source": {"file": src.name, "page": sheet, "excerpt": " | ".join(str(v) for v in r if v not in (None, ""))[:240]}})
    if len(lines_out) < 2:
        return None
    extra = {}
    for j in numeric_cols:
        if re.search(r"taux|rate", low[j]):
            vals = [float(r[j]) for r in body if isinstance(r[j], (int, float)) and isinstance(r[total_col], (int, float))]
            if vals and 0.97 <= sum(v for v in vals if v < 1) <= 1.03 and all(v <= 1 for v in vals):
                extra["share_column"] = header[j]
    return {"currency": "", "total_column": header[total_col], "sources": [header[j] for j in source_cols],
            "lines": lines_out, "declared_total": declared, "origin": f"{src.name} › {sheet}", **extra}


def _activity_code(section: str) -> str:
    m = re.match(r"^\s*(?:Activit[ée]|Activity|A)\s*(\d+(?:\.\d+)*)", section or "", re.I)
    return m.group(1) if m else ""


def _budget_from_layout(src: Source, lines: List[Line], si: int) -> Optional[Dict[str, Any]]:
    """Budget lu dans un PDF mis en page : section « Budget », montants rattachés aux colonnes de l'en-tête."""
    mine = [ln for ln in lines if ln.src == si]
    start = next((k for k, ln in enumerate(mine) if re.search(r"Tableau\s*\d*\s*:\s*Budget|^\s*\d+\s*[-–]\s*Budget\s*$|Budget Category|Cat[ée]gorie de d[ée]penses", ln.text, re.I)), None)
    if start is None:
        return None
    rows: List[Tuple[Line, List[Tuple[float, str, int]], str]] = []
    pending: List[str] = []
    code_pending = ""
    category = ""
    header_lines: List[str] = []
    declared = None
    for ln in mine[start:start + 260]:
        t = ln.text
        if re.search(r"^\s*(?:\d+\.\s*)?Cofinancement\s*$|Tableau\s*4|18-\s*Additional", t, re.I) and rows:
            break
        amounts = [a for a in N.amounts_in(t) if not (len(a[1]) == 4 and 1900 < a[0] < 2100 and "," not in a[1])]
        tail = re.search(r"(?:\s{2,}[$€]?\s?-?\d[\d\s.,\u00a0]*[$€]?)+\s*$", t)   # colonnes numériques en fin de ligne
        textpart = _clean(t[:tail.start()] if tail else re.sub(N.NUMBER_RE, " ", t))
        textpart = re.sub(r"\s+\d[\d\s.,]*$", "", textpart) if tail else textpart
        tabular = len(amounts) >= 2 and re.search(r"\d\s{3,}[$€]?-?\d", t) or (amounts and "$" in t and len(textpart) < 60)
        if tabular and len(textpart) < 70:
            if SUBTOTAL.match(textpart) or re.match(r"^(Co[ûu]t total|Subtotal|Grand Total|Total)", textpart, re.I):
                if re.search(r"grand total|co[ûu]t total du projet en mad|^total$|co[ûu]t total du projet$", textpart, re.I) and declared is None:
                    declared = amounts[0][0]
                pending, code_pending = [], ""
                continue
            tot = next((i for i, x in enumerate(pending) if SUBTOTAL.match(x) or re.match(r"^\s*Co[ûu]t total", x, re.I)), None)
            if tot is not None and not textpart:
                # libellé « Coût total … » écrit au-dessus de ses montants
                if rows and tot > 0 and declared is None:
                    rows[-1] = (rows[-1][0], rows[-1][1], _clean(rows[-1][2] + " " + " ".join(pending[:tot])))
                if declared is None and not re.search(r"\bUSD\b|\bEUR\b", " ".join(pending[tot:]) + t):
                    declared = amounts[0][0]
                pending = []
                continue
            if re.match(r"^\d+\.\d+\s", textpart) and pending and rows:
                # la ligne porte son propre code : les lignes en attente terminaient le libellé précédent
                rows[-1] = (rows[-1][0], rows[-1][1], _clean(rows[-1][2] + " " + " ".join(pending)))
                pending = []
            label = " ".join(pending + ([textpart] if textpart else []))
            rows.append((ln, amounts, _clean(label)))
            pending = []
            continue
        if not t.strip():
            continue
        m_cat = re.match(r"^\s*(\d+)\.\s+([A-ZÉ].+)", t)
        m_line = re.match(r"^\s*(\d+\.\d+)\s+(.+)", t)
        if m_line:
            if pending and rows:
                rows[-1] = (rows[-1][0], rows[-1][1], _clean(rows[-1][2] + " " + " ".join(pending)))
            pending = [m_line.group(1) + " " + m_line.group(2).strip()]
        elif m_cat and not rows or (m_cat and len(t.strip()) < 70):
            if pending and rows:
                rows[-1] = (rows[-1][0], rows[-1][1], _clean(rows[-1][2] + " " + " ".join(pending)))
            category, pending = _clean(m_cat.group(2)), []
            rows.append((ln, [], "__cat__" + category))
        elif not rows and not pending:
            if not re.match(r"^\s*\d+\s+[A-ZÉ][a-zé]", t) and (re.search(r"\S\s{3,}\S", t) or len(t.strip()) < 45):
                header_lines.append(t)
        else:
            pending.append(t.strip())
    data = [(ln, am, lab) for ln, am, lab in rows]
    if sum(1 for _, am, _ in data if am) < 3:
        return None
    # colonnes : positions des montants
    positions = sorted({a[2] for _, am, _ in data for a in am})
    cols: List[int] = []
    for p in positions:
        if not cols or p - cols[-1] > 8:
            cols.append(p)
    def col_of(p: int) -> int:
        return min(range(len(cols)), key=lambda i: abs(cols[i] - p))
    head_txt = header_lines[-8:]
    heads = []
    for ci, c in enumerate(cols):
        lo = c - 6
        hi = cols[ci + 1] - 3 if ci + 1 < len(cols) else c + 30
        words = [h[max(lo, 0):hi].strip() for h in head_txt]
        h = _clean(" ".join(w for w in words if w))
        if h.count("(") != h.count(")"):
            h = h.replace("(", "").replace(")", "")
        heads.append(_clean(h) or f"Colonne {ci + 1}")
    total_ci = 0
    for h in TOTAL_HEADS:
        found = [i for i, x in enumerate(heads) if re.search(h, x.lower())]
        if found:
            total_ci = found[-1] if h in (r"total new budget",) else found[0]
            break
    source_cis = [i for i, x in enumerate(heads) if i != total_ci and re.search(SOURCE_HEADS, x.lower())]
    out, cat = [], ""
    for ln, am, lab in data:
        if lab.startswith("__cat__"):
            cat = lab[7:]
            continue
        vals = {col_of(a[2]): a[0] for a in am}
        if total_ci not in vals:
            continue
        code_m = re.match(r"^(\d+(?:\.\d+)+)\s+(.*)", lab)
        code, label = (code_m.group(1), code_m.group(2)) if code_m else ("", lab)
        out.append({"code": code, "category": cat, "activity_code": "", "label": label[:250] or cat, "total": N.round_money(vals[total_ci]),
                    "by_source": {heads[i]: N.round_money(vals.get(i, 0.0)) for i in source_cis},
                    "source": _ref([src], Line(0, ln.page, ln.text))})
    if len(out) < 3:
        return None
    return {"currency": "", "total_column": heads[total_ci], "sources": [heads[i] for i in source_cis], "lines": out,
            "declared_total": declared, "origin": src.name}


def extract_budget(sources: List[Source], lines: List[Line]) -> Optional[Dict[str, Any]]:
    candidates = []
    for si, s in enumerate(sources):
        for sh in s.sheets:
            b = _budget_from_rows(sh.rows, s, sh.name)
            if b:
                b["currency"] = N.detect_currency(" ".join(str(c) for r in sh.rows[:12] for c in r if c), "")
                b["_rank"] = (1, len(b["lines"]))
                candidates.append(b)
        if s.kind == "pdf":
            b = _budget_from_layout(s, lines, si)
            if b:
                hdr = (b["total_column"] + " " + " ".join(b["sources"])).upper()
                b["currency"] = N.detect_currency(hdr, "") or N.detect_currency(" ".join(l["source"]["excerpt"] for l in b["lines"][:5]), "")
                b["_rank"] = (0, len(b["lines"]))
                candidates.append(b)
    if not candidates:
        return None
    # Avenant le plus récent ou budget le plus détaillé ; les autres restent consultables
    best = max(candidates, key=lambda b: (("total new budget" in b["total_column"].lower()), b["_rank"]))
    others = [{"origin": c["origin"], "lines": len(c["lines"]), "total": sum(l["total"] for l in c["lines"])} for c in candidates if c is not best]
    best.pop("_rank", None)
    best["alternatives"] = others
    return best


# ---------------------------------------------------------------- activités et cadre logique
ACT_RX = re.compile(r"^\s*(?:Activit[ée]|Activity)\s*(\d+(?:\.\d+){0,2})\s*[:\-–]?\s*(.*)|^\s*A(\d+(?:\.\d+){1,2})\s*:\s*(.*)", re.I)


def _cut(text: str, a: int, b: Optional[int]) -> str:
    """Tranche de colonne [a, b) sans couper un mot à cheval sur la limite (le mot va à la colonne où il commence)."""
    n = len(text)
    a = max(0, min(a, n))
    while 0 < a < n and text[a - 1].isalnum() and text[a].isalnum():
        a += 1
    if b is None or b >= n:
        return text[a:]
    b = max(a, b)
    while b < n and b > 0 and text[b - 1].isalnum() and text[b].isalnum():
        b += 1
    return text[a:b]


def _quarter_header(mine: List[Line]) -> Dict[int, Tuple[int, int]]:
    """Positions des colonnes T1…T8 (ou Q1…) d'un calendrier par trimestres."""
    for ln in mine:
        ms = list(re.finditer(r"\b[TQ]([1-9]|1[0-2])\b", ln.text))
        if len(ms) >= 4 and [int(m.group(1)) for m in ms] == list(range(1, len(ms) + 1)):
            return {int(m.group(1)): (m.start(), m.end()) for m in ms}
    return {}


def _grid_tables(mine: List[Line]) -> List[Dict[str, Any]]:
    """Tableaux « Composante / Livrable / Activité / Du / Au » (CEPF, UE…) : lignes reconstruites par colonnes.
    Les cellules écrites sur plusieurs lignes sont recollées ; les dates coupées (« 5/31/202 » + « 0 ») aussi."""
    rows: List[Dict[str, Any]] = []
    starts: List[int] = []
    names: List[str] = []
    cur: Optional[Dict[str, Any]] = None
    for k, ln in enumerate(mine):
        t = ln.text
        low = t.lower()
        if ("activit" in low and ("deliverable" in low or "livrable" in low or "component" in low or "composante" in low)
                and len(re.findall(r"\S+(?: \S+)*", t)) >= 4):
            cells = []
            for m in re.finditer(r"\S+(?: \S+)*", t):
                # « Activity Activity Description » : un mot-clé d'en-tête ouvre une nouvelle colonne
                for w in re.finditer(r"\S+", m.group(0)):
                    is_head = re.fullmatch(r"(?:Comp|Component|Del|Deliverable|Activity|Activit[ée]|Composante|Livrable|Produit|R[ée]sultat)", w.group(0), re.I)
                    if not cells or (is_head and cells[-1][0] < m.start()) or (is_head and m.start() + w.start() > cells[-1][0] + len(cells[-1][1]) - 1 and cells[-1][0] >= m.start()):
                        cells.append((m.start() + w.start(), w.group(0)))
                    else:
                        cells[-1] = (cells[-1][0], cells[-1][1] + " " + w.group(0))
            nxt = mine[k + 1].text if k + 1 < len(mine) else ""
            starts = [c[0] for c in cells]
            names = []
            for i, (pos, name) in enumerate(cells):
                end = starts[i + 1] if i + 1 < len(starts) else pos + 30
                sub = _cut(nxt, max(pos - 2, 0), end - 1).strip()
                names.append(_clean(f"{name} {sub}"))
            cur = None
            continue
        if not starts or re.search(r"Page \d+ of \d+|^\s*#\s", t) or not t.strip():
            continue
        if re.match(r"^\s*\d+\s*[-–]\s+[A-Z]", t):           # rubrique suivante (« 10- Expected Results »)
            starts, cur = [], None
            continue
        date_i = next((i for i, n in enumerate(names) if re.search(r"\b(?:from|du|d[ée]but)\b", n.lower())), None)
        limit = len(starts) if date_i is None else date_i
        segs = []
        for i, a in enumerate(starts[:limit]):
            b = starts[i + 1] if i + 1 < len(starts) else None
            segs.append(_cut(t, max(a - 2, 0), (b - 2) if b else None).strip())
        dtoks = [(m.start(), m.group(0)) for m in re.finditer(r"[\d/.\-]+", t[starts[date_i] - 4:]) if re.search(r"\d", m.group(0))] \
            if date_i is not None and len(t) > starts[date_i] - 4 else []
        if segs and segs[0] and re.match(r"^\d+$", segs[0]):
            cur = {"names": names, "cells": [[x] for x in segs], "line": ln, "dates": [list(x) for x in dtoks], "date_i": date_i}
            rows.append(cur)
        elif cur:
            for i, x in enumerate(segs):
                if x:
                    cur["cells"][i].append(x)
            for pos, tok in dtoks:                          # suite d'une date coupée : rattachée à la date la plus proche
                if cur["dates"]:
                    near = min(cur["dates"], key=lambda d: abs(d[0] - pos))
                    if not re.search(r"/\d{4}$", near[1]):
                        near[1] += tok
    out = []
    for r in rows:
        cells = {}
        for name, parts in zip(r["names"], r["cells"]):
            cells[name] = _clean(" ".join(parts))
        if r["date_i"] is not None:
            ds = [d[1] for d in r["dates"] if re.search(r"\d", d[1])]
            for j, name in enumerate(r["names"][r["date_i"]:r["date_i"] + 2]):
                cells[name] = ds[j] if j < len(ds) else ""
        out.append({"cells": cells, "line": r["line"]})
    return out


def _grid_col(cells: Dict[str, str], *pats: str) -> str:
    for p in pats:
        for k, v in cells.items():
            if re.fullmatch(p, k, re.I):
                return v
    return ""


def extract_activities(sources: List[Source], lines: List[Line], start: Optional[date]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen = set()
    for si, s in enumerate(sources):
        if s.kind == "xlsx":
            continue                                   # les classeurs donnent les activités par leur budget (voir extract)
        mine = [ln for ln in lines if ln.src == si]
        qcols = _quarter_header(mine)
        first_q = min(v[0] for v in qcols.values()) if qcols else None
        resp_col = ind_col = None
        if qcols:
            hk = next(k for k, l in enumerate(mine) if _quarter_header([l]))
            for l in mine[max(0, hk - 3):hk + 3]:
                if resp_col is None and re.search(r"Responsab", l.text):
                    resp_col = l.text.find(re.search(r"Responsab", l.text).group(0))
                if ind_col is None and re.search(r"Indicateur", l.text):
                    ind_col = l.text.find("Indicateur")
        us = _us_dates(s)
        grid = _grid_tables(mine)
        if grid:
            for g in grid:
                c = g["cells"]
                code = _grid_col(c, r"activity #", r"activit[ée] (?:#|n°)")
                title = _grid_col(c, r"activity description", r"description de l'activit[ée]", r"activit[ée] description")
                d1 = N.parse_date(_grid_col(c, r"activity from", r"activit[ée] du", r"from"), us)
                d2 = N.parse_date(_grid_col(c, r"activity to", r"activit[ée] au", r"to"), us)
                comp = _grid_col(c, r"comp #", r"composante #")
                if code and title and code not in {a["code"] for a in out}:
                    out.append({"code": code, "component": comp, "title": title[:300], "responsible": "",
                                "start": d1.isoformat() if d1 else None, "end": d2.isoformat() if d2 else None,
                                "deliverable": _grid_col(c, r"del #", r"livrable #"),
                                "component_label": _grid_col(c, r"component description", r"composante description"),
                                "deliverable_label": _grid_col(c, r"deliverable description", r"livrable description"),
                                "source": _ref(sources, g["line"])})
            continue
        k = 0
        while k < len(mine):
            ln = mine[k]
            m = ACT_RX.match(ln.text)
            if m and not qcols and (len(ln.text) - len(ln.text.lstrip())) > 30:
                m = None                                   # code d'activité au milieu d'un tableau large : illisible sans colonnes
            cepf = None
            if not m and not cepf:
                k += 1
                continue
            if cepf:
                code = cepf.group(3)
                desc_col = ln.text.find(code) + len(code)
                block = [mine[j] for j in range(k, min(k + 6, len(mine))) if j == k or not re.match(r"^\s*\d+\s{2,}\S", mine[j].text)]
                desc, dates_txt = [], []
                for b in block:
                    seg = b.text[desc_col:]
                    parts = re.split(r"\s{2,}", seg.strip(), maxsplit=1)
                    desc.append(parts[0] if parts else "")
                    dates_txt.append(seg)
                joined = " ".join(dates_txt)
                raw = re.findall(r"\d{1,2}/\d{1,2}/\d{2,4}", re.sub(r"(\d/\d{1,2}/\d{2,3})\s{2,}[\s\S]*?(\d)\b", r"\1\2", joined))
                dts = [N.parse_date(x, us) for x in raw]
                title = _clean(re.sub(r"\d{1,2}/\d{1,2}/\d{2,4}", "", " ".join(desc)))
                comp = cepf.group(1)
                period = (dts[0], dts[1]) if len(dts) >= 2 and dts[0] and dts[1] else (None, None)
                k += 1
            else:
                code = m.group(1) or m.group(3)
                title_parts = [(m.group(2) or m.group(4) or "")]
                col_end = first_q - 2 if first_q else None
                cut = None
                for j in range(k + 1, min(k + 8, len(mine))):
                    nxt = mine[j].text
                    if ACT_RX.match(nxt) or re.match(r"^\s*Composante|^\s*Component|^\s*R[ée]sultat|^\s*OS\d|^\s*R\d", nxt, re.I):
                        break
                    cut = j
                responsible = ""
                if resp_col:
                    # tableau à colonnes connues : titre = colonne 1, responsable = colonne 2
                    c1, c2 = resp_col - 1, (ind_col or first_q) - 2
                    title_parts = [_cut(ln.text, m.end(1) if m.group(1) else m.end(3), c1).strip(" :")]
                    resp = [_cut(ln.text, c1, c2).strip()]
                    for j in range(k + 1, (cut or k) + 1):
                        seg = mine[j].text
                        title_parts.append(_cut(seg, 0, c1).strip())
                        resp.append(_cut(seg, c1, c2).strip())
                    responsible = _clean(" ".join(x for x in resp if x))
                else:
                    head_seg = re.split(r"\s{3,}", title_parts[0].strip())[0]
                    title_parts[0] = head_seg
                    for j in range(k + 1, (cut or k) + 1):
                        seg = mine[j].text
                        lead = re.split(r"\s{3,}", seg.strip())[0] if (len(seg) - len(seg.lstrip())) < (len(ln.text) - len(ln.text.lstrip())) + 4 else ""
                        if lead and not lead.startswith("-") and not re.match(r"^(AFMI|ONG|Expert|Consultant)\b", lead):
                            title_parts.append(lead)
                title = _clean(" ".join(title_parts))
                comp = code.split(".")[0]
                period = (None, None)
                block_text = " ".join(mine[j].text for j in range(k, (cut or k) + 1))
                if qcols and start:
                    qs = set()
                    for j in range(k, (cut or k) + 1):
                        t = mine[j].text
                        for q, (a, b) in qcols.items():
                            if re.search(r"[xX✓✔■●]", t[max(a - 2, 0):b + 2]):
                                qs.add(q)
                    if qs:
                        period = N.quarter_span(start, min(qs), max(qs))
                rp = N.relative_period(block_text)
                if rp and start and period == (None, None):
                    period = N.month_span(start, rp[1], rp[2]) if rp[0] == "mois" else N.quarter_span(start, rp[1], rp[2])
                k = (cut or k) + 1
            key = (code, title[:30])
            if code in {a["code"] for a in out} or key in seen or not title:
                continue
            seen.add(key)
            out.append({"code": code, "component": comp, "title": title[:300], "responsible": locals().get("responsible", "") if not cepf else "",
                        "start": period[0].isoformat() if period[0] else None, "end": period[1].isoformat() if period[1] else None,
                        "source": _ref(sources, ln)})
    # Activités d'un budget par activité (Excel) quand le document n'en décrit pas
    return out


def extract_logframe(sources: List[Source], lines: List[Line]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    nodes: List[Dict[str, Any]] = []
    indicators: List[Dict[str, Any]] = []
    hit = None
    for k0, ln0 in enumerate(lines):
        if re.search(r"R[ée]sultats\s+(?:du\s+projet|attendus)\s*:\s*$", ln0.text, re.I):
            nxt0 = next((x for x in lines[k0 + 1:k0 + 4] if x.text.strip()), None)
            if nxt0 and re.match(r"^\s*1\.\s", nxt0.text):
                hit = (ln0, None, k0)
                break
    if hit:
        ln, _, k = hit
        cur = None
        for nxt in lines[k + 1:k + 40]:
            if nxt.src != ln.src:
                break
            t = nxt.text
            m = re.match(r"^\s*(\d)\.\s+(.+)", t)
            if m:
                seg = re.split(r"\s{4,}", m.group(2).strip())[0]
                cur = {"level": "Résultat", "code": f"R{m.group(1)}", "statement": seg, "parent_code": "", "source": _ref(sources, nxt)}
                nodes.append(cur)
            elif cur and t.strip() and (len(t) - len(t.lstrip())) > 8 and not re.search(r"Responsabl|Cadre du projet|Indicateur", t):
                cur["statement"] += " " + re.split(r"\s{4,}", t.strip())[0]
            elif re.search(r"Responsabl|Cadre du projet", t):
                break
        for n in nodes:
            n["statement"] = _clean(n["statement"])[:400]
    # Composantes et livrables (tableaux CEPF / UE)
    for si, s_ in enumerate(sources):
        for g in _grid_tables([ln for ln in lines if ln.src == si]):
            c = g["cells"]
            comp, comp_l = _grid_col(c, r"comp #", r"composante #"), _grid_col(c, r"component description", r"composante description")
            dl, dl_l = _grid_col(c, r"del #", r"livrable #"), _grid_col(c, r"deliverable description", r"livrable description")
            if comp and comp_l and f"C{comp}" not in {n["code"] for n in nodes}:
                nodes.append({"level": "Résultat", "code": f"C{comp}", "statement": comp_l[:400], "parent_code": "", "source": _ref(sources, g["line"])})
            if dl and dl_l and dl not in {n["code"] for n in nodes}:
                nodes.append({"level": "Produit", "code": dl, "statement": dl_l[:400], "parent_code": f"C{comp}" if comp else "", "source": _ref(sources, g["line"])})
    hit = _first(lines, r"^\s*\d+\s*[-–]\s*Portfolio Indicators")
    if hit:
        ln, _, k = hit
        cur = None
        for nxt in lines[k + 1:k + 60]:
            if nxt.src != ln.src or re.match(r"^\s*\d+\s*[-–]\s+[A-Z]", nxt.text):
                break
            m = re.match(r"^\s*(\d+\.\d+)\s{2,}(.+)", nxt.text)
            if m:
                parts = re.split(r"\s{3,}", m.group(2).strip())
                target = N.parse_amount(parts[1]) if len(parts) > 1 else None
                cur = {"code": m.group(1), "result_code": "", "name": parts[0], "target": target, "unit": "", "baseline": None,
                       "verification": "", "source": _ref(sources, nxt)}
                indicators.append(cur)
            elif cur and nxt.text.strip() and not re.search(r"Number|Short Name|Expected|Numeric|Contributio|^\s*n\s*$|Page \d+", nxt.text):
                cur["name"] = _clean(cur["name"] + " " + re.split(r"\s{3,}", nxt.text.strip())[0])
    # Objectifs codés OG / OS / R (formulaires « cadre logique »)
    for ln in lines:
        for m in re.finditer(r"\b(OG|OS\d|R\d)\s*:\s*([^:]{8,}?)(?=\s{3,}|\s(?:OS\d|R\d|A\d)\s*:|$)", ln.text):
            code = m.group(1)
            level = "Objectif global" if code == "OG" else "Objectif spécifique" if code.startswith("OS") else "Résultat"
            if code not in {n["code"] for n in nodes}:
                nodes.append({"level": level, "code": code, "statement": _clean(m.group(2))[:400], "parent_code": "", "source": _ref(sources, ln)})
    # Indicateurs : puces chiffrées sous « Indicateurs : » d'une composante / d'un produit
    for k, ln in enumerate(lines):
        if not re.search(r"^\s*Indicateurs?\s*:\s*$", ln.text):
            continue
        comp = ""
        for near in lines[k + 1:k + 6]:
            mc = re.search(r"(?:Composante|Component)\s*(\d+)", near.text, re.I)
            if mc:
                comp = mc.group(1)
                break
        if not comp:
            for near in reversed(lines[max(0, k - 30):k]):
                mc = re.search(r"(?:Composante|Component)\s*(\d+)", near.text, re.I)
                if mc:
                    comp = mc.group(1)
                    break
        if not comp:
            continue
        col = ln.text.find("Indicateur")
        cur = None
        for nxt in lines[k + 1:k + 16]:
            if nxt.src != ln.src or re.search(r"Activit[ée]\s*\d", nxt.text[:col + 6], re.I):
                break
            seg = nxt.text[max(col - 4, 0):max(col - 4, 0) + 34].rstrip()
            if re.search(r"Moyens de v[ée]rification", seg, re.I):
                break
            mm = re.match(r"\s*-\s*(\d[\d\s,.]*)\s*(.+)", seg)
            if mm:
                target = N.parse_amount(mm.group(1))
                name = _clean(mm.group(1).strip() + " " + mm.group(2))       # libellé du document, cible comprise
                cur = {"code": f"I{comp}.{sum(1 for i in indicators if i['result_code'] == f'R{comp}') + 1}",
                       "result_code": f"R{comp}", "name": name[:200], "target": target, "unit": _clean(mm.group(2)).split(" ")[0][:20],
                       "baseline": None, "verification": "", "source": _ref(sources, nxt)}
                indicators.append(cur)
            elif re.match(r"\s*-\s*\D", seg):
                cur = None
            elif cur and seg.strip() and not seg.strip().startswith("-"):
                cur["name"] = _clean(cur["name"] + " " + seg.strip())[:200]
    return nodes, indicators


def extract_rules(sources: List[Source], lines: List[Line]) -> List[Dict[str, Any]]:
    pats = [
        (r"frais indirects[^.]{0,60}?(?:ne (?:devront|doivent) pas d[ée]passer|≤|inf[ée]rieurs? [àa])\s*(\d{1,2}(?:[.,]\d)?)\s*%", "IndirectCostsMaxPercent"),
        (r"subvention[^.]{0,80}?ne peut pas exc[ée]der\s*(\d{1,3})\s*%", "GrantMaxShareOfIncomePercent"),
        (r"cofinancement d['’]un montant [ée]gal ou sup[ée]rieur", "CofinancingMinPercent"),
        (r"ne doivent pas d[ée]passer\s+[a-zé\-\s]*\(?([\d\s.,]+)\s*(USD|MAD|EUR|\$)", "GrantMaxAmount"),
        (r"(?:au minimum|au moins)\s*(\d{1,3})\s*%\s*des recettes", "CofinancingMinPercentOfIncome"),
        (r"budget[^.]{0,40}doit [êe]tre [ée]quilibr[ée]", "BalancedBudget"),
        (r"monitoring budget[^.]{0,40}up to\s*(\d{1,2})\s*%|budget de suivi[^.]{0,40}(\d{1,2})\s*%", "MonitoringMaxPercent"),
    ]
    out, seen = [], set()
    for ln in lines:
        for pat, kind in pats:
            m = re.search(pat, ln.text, re.I)
            if m and kind not in seen:
                seen.add(kind)
                val = None
                if m.groups():
                    raw = next((g for g in m.groups() if g), None)
                    val = N.parse_amount(raw) if raw else None
                if kind == "CofinancingMinPercent":
                    val = 100.0
                out.append({"kind": kind, "value": val, "text": _clean(ln.text)[:300], "source": _ref(sources, ln)})
    return out


def extract_reports(sources: List[Source], lines: List[Line], tranches: List[Dict[str, Any]], end: Optional[str]) -> List[Dict[str, Any]]:
    out = []
    for t in tranches:
        m = re.search(r"rapports?\s+([\w\s]+?)\s+n[°o]\s*(\d+)", t.get("condition") or "", re.I)
        if m:
            out.append({"title": f"Rapport {m.group(1).strip()} n° {m.group(2)}", "kind": "Rapport narratif et financier",
                        "due": t.get("date"), "note": f"Conditionne {t['label']}", "source": t.get("source")})
    hit = _first(lines, r"rapport (?:financier et descriptif|narratif et financier|technique et financier) final|final (?:narrative|financial) report")
    if hit:
        out.append({"title": "Rapport final narratif et financier", "kind": "Rapport final", "due": end, "note": "Date limite à confirmer dans la convention",
                    "source": _ref(sources, hit[0])})
    hit = _first(lines, r"Rapport financier\s*-\s*trimestre|rapports? trimestriels?|quarterly reports?")
    if hit:
        out.append({"title": "Rapports financiers trimestriels", "kind": "Rapport financier", "due": None, "note": "Périodicité trimestrielle",
                    "source": _ref(sources, hit[0])})
    return out


def extract_amendments(sources: List[Source], lines: List[Line], fields: Dict[str, Any], funding: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    num = _first(lines, r"Amendment Number:\s*(\d+)|Avenant\s*n[°o]\s*(\d+)")
    a = funding.get("_amendment")
    ext = fields.get("_extension")
    if a or ext or num:
        out.append({"number": (num[1].group(1) or num[1].group(2)) if num else "", "old_amount": a and a["old"], "new_amount": a and a["new"],
                    "increase": a and a["increase"], "old_end": ext and ext["old_end"], "new_end": ext and ext["new_end"],
                    "source": (a or ext or {"source": _ref(sources, num[0])})["source"]})
    for s in sources:
        for sh in s.sheets:
            flat = {str(r[0]).strip().lower(): r for r in sh.rows if r and isinstance(r[0], str)}
            cur = next((r for k, r in flat.items() if k.startswith("current budget amount")), None)
            new = next((r for k, r in flat.items() if k.startswith("total new budget")), None)
            add = next((r for k, r in flat.items() if k.startswith("additional amount")), None)
            if cur and new:
                val = lambda r: next((float(v) for v in r[1:] if isinstance(v, (int, float))), None)
                out.append({"number": "", "old_amount": val(cur), "new_amount": N.round_money(val(new)), "increase": add and val(add),
                            "old_end": None, "new_end": None, "source": {"file": s.name, "page": sh.name, "excerpt": "Current Budget Amount / Total New Budget"}})
    return out


def extract(sources: List[Source]) -> Dict[str, Any]:
    lines = _lines(sources)
    fields = extract_fields(sources, lines)
    funding = extract_funding(sources, lines, fields)
    grant_cur = (funding.get("grant") or {}).get("value", {}).get("currency") or "MAD"
    tranches = extract_tranches(sources, lines, grant_cur)
    budget = extract_budget(sources, lines)
    start = date.fromisoformat(fields["start"]["value"]) if "start" in fields else None
    activities = extract_activities(sources, lines, start)
    nodes, indicators = extract_logframe(sources, lines)
    rules = extract_rules(sources, lines)
    reports = extract_reports(sources, lines, tranches, (fields.get("end") or {}).get("value"))
    amendments = extract_amendments(sources, lines, fields, funding)
    if amendments:
        last = amendments[-1]
        if last.get("new_amount") and (not funding.get("grant") or "Total New Budget" not in (funding["grant"]["source"] or {}).get("excerpt", "")):
            funding["grant"] = _field({"amount": last["new_amount"], "currency": grant_cur}, last["source"], "règles (dernier avenant)")
    if budget:
        known = {a["code"] for a in activities}
        for l in budget["lines"]:
            code = l.get("activity_code")
            if code and code not in known:
                known.add(code)
                title = re.sub(r"^\s*(?:Activit[ée]|Activity|A)\s*\d+(?:\.\d+)*\s*[:\-–]?\s*", "", l.get("category") or "")
                activities.append({"code": code, "component": code.split(".")[0], "title": _clean(title)[:300], "responsible": "",
                                   "start": None, "end": None, "source": l["source"]})
    cofin = []
    if budget and budget.get("sources"):
        grant_like = [s for s in budget["sources"] if re.search(r"subvention|grant|pmf|bailleur principal", s, re.I)]
        for col in budget["sources"]:
            if col in grant_like:
                continue
            total = sum((l["by_source"].get(col) or 0) for l in budget["lines"])
            if total > 0:
                low = col.lower()
                stype = "Communauté" if "communaut" in low else "Autre bailleur" if re.search(r"donateur|bailleur|partenaire", low) else "Association"
                cofin.append({"source_type": stype, "source_name": col, "nature": "Nature" if "nature" in low and "esp" not in low else "Espèces et nature",
                              "amount": N.round_money(total), "currency": budget.get("currency") or "MAD", "commitment": "Prévu",
                              "description": f"Colonne « {col} » du budget", "source": {"file": budget["origin"], "page": "", "excerpt": col}})
    return {"project": {k: v for k, v in fields.items() if not k.startswith("_")}, "funding": {k: v for k, v in funding.items() if not k.startswith("_")},
            "tranches": tranches, "budget": budget, "activities": activities, "logframe": nodes, "indicators": indicators,
            "reports": reports, "rules": rules, "risks": [], "cofinancing": cofin, "amendments": amendments}
