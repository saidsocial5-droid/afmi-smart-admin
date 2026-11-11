"""Classification et extraction des métadonnées d'un document de projet (sans IA : règles explicites, traçables).

- Type : score des mots-clés de config/lifecycle_config.json (titre ×3, texte) ; confiance = part du meilleur score.
- Métadonnées : dates, montants et devises, parties, durée, début et fin, signature.
- Obligations de reporting : phrases parlant de rapport et d'échéance ; dates explicites ou périodicité (trimestriel,
  semestriel, annuel) + délai (« dans les 30 jours ») appliqués à la période de la convention. Toujours « proposées »,
  avec la phrase source, jusqu'à confirmation par l'utilisateur.
"""
import re
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from backend.tools.statements.templates import normalize
from .config import load

MONTHS = {"janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6, "juillet": 7, "aout": 8, "septembre": 9,
          "octobre": 10, "novembre": 11, "decembre": 12}
NUM_DATE = re.compile(r"\b(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})\b|\b(\d{4})-(\d{2})-(\d{2})\b")
TEXT_DATE = re.compile(r"\b(\d{1,2})(?:er)?\s+(janvier|f[ée]vrier|mars|avril|mai|juin|juillet|ao[uû]t|septembre|octobre|novembre|d[ée]cembre)\s+(\d{4})\b",
                       re.IGNORECASE)
AMOUNT = re.compile(r"(\d{1,3}(?:[ .  ]\d{3})+|\d+)(?:,(\d{1,2}))?\s*(MAD|DH|dirhams?|EUR|€|euros?|USD|\$|dollars?)", re.IGNORECASE)
PARTY = re.compile(r"([A-ZÉÈÀ][^,;\n]{2,90}?),?\s*ci-apr[eè]s\s+d[ée]nomm[ée]e?s?\s*[«\"“]?\s*([^»\"”\n,;]{2,40})", re.IGNORECASE)
CURRENCY = {"mad": "MAD", "dh": "MAD", "dirham": "MAD", "dirhams": "MAD", "eur": "EUR", "€": "EUR", "euro": "EUR", "euros": "EUR",
            "usd": "USD", "$": "USD", "dollar": "USD", "dollars": "USD"}
FREQ = {"trimestriel": 3, "trimestriels": 3, "trimestrielle": 3, "trimestre": 3, "semestriel": 6, "semestriels": 6, "semestrielle": 6,
        "semestre": 6, "annuel": 12, "annuels": 12, "annuelle": 12, "chaque annee": 12, "mensuel": 1, "mensuelle": 1}


def _safe(y: int, m: int, d: int) -> Optional[str]:
    try:
        return date(y, m, d).isoformat()
    except ValueError:
        return None


def dates_in(text: str) -> List[str]:
    """Dates du texte, dans leur ordre d'apparition (numériques ou en toutes lettres)."""
    found = []
    for m in NUM_DATE.finditer(text):
        iso = _safe(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m.group(1) else _safe(int(m.group(4)), int(m.group(5)), int(m.group(6)))
        if iso:
            found.append((m.start(), iso))
    for m in TEXT_DATE.finditer(text):
        iso = _safe(int(m.group(3)), MONTHS[normalize(m.group(2))], int(m.group(1)))
        if iso:
            found.append((m.start(), iso))
    return [iso for _, iso in sorted(found)]


def _first_date_after(text: str, *markers: str) -> Optional[str]:
    norm = normalize(text)
    for marker in markers:
        i = norm.find(marker)
        if i >= 0:
            found = dates_in(norm[i:i + 120].replace(" ", " "))
            # normalize() retire la ponctuation des dates numériques : on relit le texte brut autour du repère
            if not found:
                raw_i = text.lower().find(marker.split()[0])
                found = dates_in(text[raw_i:raw_i + 160]) if raw_i >= 0 else []
            if found:
                return found[0]
    return None


def classify(title: str, text: str) -> Tuple[str, float, Dict[str, float]]:
    cfg = load()
    t, body = " " + normalize(title) + " ", " " + normalize(text[:6000]) + " "
    scores: Dict[str, float] = {}
    for name, spec in cfg["types"].items():
        score = 0.0
        for kw in spec["keywords"]:
            k = normalize(kw)
            if not k:
                continue
            weight = 1 + len(k.split()) * 0.5        # une expression précise pèse plus qu'un mot isolé
            score += 3 * weight * t.count(f" {k} ") + weight * min(body.count(f" {k} "), 5)
        if score:
            scores[name] = round(score, 1)
    if not scores:
        return "Autre", 0.0, {}
    best = max(scores, key=scores.get)
    confidence = round(100 * scores[best] / sum(scores.values()), 1)
    return best, confidence, scores


def metadata(text: str) -> Dict[str, Any]:
    amounts = []
    for m in AMOUNT.finditer(text):
        value = float(re.sub(r"[ .  ]", "", m.group(1)) + "." + (m.group(2) or "0"))
        cur = CURRENCY.get(m.group(3).lower().rstrip("s") if m.group(3).lower() not in CURRENCY else m.group(3).lower(), "MAD")
        if value >= 1:
            amounts.append({"value": value, "currency": cur, "text": m.group(0).strip()})
    parties = list(dict.fromkeys(f"{m.group(1).strip()} (« {m.group(2).strip()} »)" for m in PARTY.finditer(text)))[:6]
    norm = normalize(text)
    duration = re.search(r"duree\s+(?:totale\s+)?(?:de\s+)?(\d{1,3})\s+mois", norm)
    start = _first_date_after(text, "a compter du", "debute le", "date de debut", "prend effet le", "du ")
    end = _first_date_after(text, "jusqu au", "prend fin le", "date de fin", "au plus tard le 31", "se termine le")
    signature = _first_date_after(text, "signe le", "fait a")
    months = int(duration.group(1)) if duration else None
    if start and not end and months:
        end = (_shift(date.fromisoformat(start), months) - timedelta(days=1)).isoformat()
    return {"dates": sorted(set(dates_in(text)))[:30], "amounts": amounts[:20], "max_amount": max(amounts, key=lambda a: a["value"]) if amounts else None,
            "parties": parties, "duration_months": months, "start": start, "end": end, "signature": signature}


def _shift(d: date, months: int) -> date:
    """d + n mois (jour ramené au dernier jour du mois si besoin)."""
    y, m = divmod(d.month - 1 + months, 12)
    year, month = d.year + y, m + 1
    last = (date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)).day
    return date(year, month, min(d.day, last))


def obligations(text: str, start: Optional[str], end: Optional[str]) -> List[Dict[str, Any]]:
    """Échéances de rapports proposées (jamais enregistrées sans confirmation)."""
    sentences = [s.strip() for s in re.split(r"(?<=[.;])\s+|\n{1,}", text) if s.strip()]
    out: List[Dict[str, Any]] = []
    for sent in sentences:
        n = " " + normalize(sent) + " "
        if " rapport" not in n or not any(k in n for k in (" au plus tard", " avant le", " dans un delai", " dans les ", " remettre", " soumettre",
                                                             " transmettre", " fournir", " produire", " presenter", *[f" {f} " for f in FREQ])):
            continue
        kind = "Rapport final" if " final" in n else "Rapport financier" if " financier" in n else "Rapport narratif"
        if " financier" in n and " narratif" in n:
            kind = "Rapports narratif et financier"
        delay = re.search(r"(\d{1,3})\s+jours", n)
        delay_days = int(delay.group(1)) if delay else 0
        explicit = dates_in(sent)
        freq = next((v for k, v in FREQ.items() if f" {k} " in n), None)
        excerpt = sent[:300]
        if explicit:
            for d in explicit[:4]:
                out.append({"kind": kind, "title": kind, "due": d, "excerpt": excerpt})
        elif freq and start and end:
            s, e = date.fromisoformat(start), date.fromisoformat(end)
            k = 1
            period_end = _shift(s, freq) - timedelta(days=1)          # fin de la 1re période (ex. 01/01 + 6 mois − 1 jour = 30/06)
            while period_end <= e and k <= 12:
                out.append({"kind": kind, "title": f"{kind} n° {k}", "due": (period_end + timedelta(days=delay_days)).isoformat(), "excerpt": excerpt})
                k += 1
                period_end = _shift(s, freq * k) - timedelta(days=1)
            if " final" in n or kind == "Rapport final":
                out.append({"kind": "Rapport final", "title": "Rapport final", "due": (e + timedelta(days=delay_days)).isoformat(), "excerpt": excerpt})
        elif kind == "Rapport final" and end:
            out.append({"kind": kind, "title": kind, "due": (date.fromisoformat(end) + timedelta(days=delay_days)).isoformat(), "excerpt": excerpt})
    seen, unique = set(), []
    for o in out:
        key = (o["kind"], o["due"])
        if key not in seen:
            seen.add(key)
            unique.append(o)
    return sorted(unique, key=lambda o: o["due"])[:24]


def language(text: str) -> str:
    letters = [c for c in text[:4000] if c.isalpha()]
    if not letters:
        return ""
    arabic = sum(1 for c in letters if "؀" <= c <= "ۿ")
    return "ar" if arabic / len(letters) > 0.3 else ("en" if re.search(r"\b(the|and|of|report)\b", text[:4000].lower()) and not re.search(r"\b(le|la|les|des)\b", text[:4000].lower()) else "fr")
