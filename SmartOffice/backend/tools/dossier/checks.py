"""Contrôles de cohérence d'un dossier extrait : totaux, tranches, taux de change, dates, règles du bailleur,
valeurs contradictoires entre documents. Ils ne corrigent rien : ils signalent, l'utilisateur tranche."""
import re
from collections import Counter
from datetime import date
from typing import Any, Dict, List, Optional

from . import normalize as N
from .sources import Source


def _issue(level: str, code: str, message: str, source: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {"level": level, "code": code, "message": message, "source": source}


def _v(d: Dict[str, Any], key: str):
    x = d.get(key)
    return x.get("value") if isinstance(x, dict) and "value" in x else x


def _fmt(v: Optional[float], cur: str = "") -> str:
    if v is None:
        return "—"
    s = f"{v:,.2f}".replace(",", " ").replace(".", ",").replace(",00", "")
    return f"{s} {cur}".strip()


def _close(a: float, b: float, tol: float = 1.0) -> bool:
    return abs(a - b) <= max(tol, abs(b) * 0.0005)


def run(result: Dict[str, Any], sources: List[Source]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    p, f = result.get("project", {}), result.get("funding", {})
    budget = result.get("budget") or {}
    grant = _v(f, "grant") or {}
    grant_mad = (_v(f, "grant_mad") or {}).get("amount")
    rate = _v(f, "exchange_rate")
    cur = budget.get("currency") or grant.get("currency") or "MAD"

    # Essentiels
    for key, label in (("title", "l'intitulé"), ("start", "la date de début"), ("end", "la date de fin")):
        if not _v(p, key):
            issues.append(_issue("attention", "missing", f"Les documents ne donnent pas {label} du projet : à saisir."))
    if not grant.get("amount"):
        issues.append(_issue("attention", "missing", "Montant de la subvention non trouvé : à saisir."))
    if not budget.get("lines"):
        issues.append(_issue("attention", "missing", "Aucun tableau de budget reconnu dans les documents."))

    # Budget : total des lignes et total déclaré
    lines = budget.get("lines") or []
    if lines:
        s = sum(l.get("total") or 0 for l in lines)
        decl = budget.get("declared_total")
        if decl is not None and not _close(s, decl):
            issues.append(_issue("erreur", "budget_total", f"La somme des lignes du budget ({_fmt(s, cur)}) diffère du total écrit "
                                 f"dans le tableau ({_fmt(decl, cur)}) : écart de {_fmt(s - decl, cur)}.", {"file": budget.get("origin"), "page": "", "excerpt": "Total"}))
        if decl is not None and abs(decl - round(decl, 2)) > 1e-6:
            issues.append(_issue("info", "rounding", f"Le total du classeur contient des décimales parasites ({decl}) : il sera arrondi à {_fmt(round(decl, 2), cur)}."))
        if budget.get("sources"):
            for l in lines:
                parts = sum(v or 0 for v in l["by_source"].values())
                if parts and not _close(parts, l["total"]):
                    issues.append(_issue("erreur", "budget_line_sources", f"Ligne {l.get('code') or l['label'][:40]} : la somme des financements "
                                         f"({_fmt(parts, cur)}) ne fait pas le total de la ligne ({_fmt(l['total'], cur)}).", l.get("source")))
            gcol = next((c for c in budget["sources"] if re.search(r"subvention|grant|pmf", c, re.I)), None)
            if gcol and grant_mad:
                g = sum(l["by_source"].get(gcol) or 0 for l in lines)
                if not _close(g, grant_mad):
                    issues.append(_issue("erreur", "budget_grant", f"La colonne « {gcol} » totalise {_fmt(g, 'MAD')} alors que la subvention "
                                         f"demandée est de {_fmt(grant_mad, 'MAD')}."))
        tc = _v(f, "total_cost") or {}
        if tc.get("amount") and not _close(s, tc["amount"]) and (budget.get("currency") or "MAD") == (tc.get("currency") or "MAD"):
            issues.append(_issue("attention", "budget_vs_cost", f"Le budget détaillé ({_fmt(s, cur)}) ne correspond pas au coût total annoncé ({_fmt(tc['amount'], tc.get('currency'))})."))
        codes = [l["code"] for l in lines if l.get("code")]
        for c, n in Counter(codes).items():
            if n > 1:
                issues.append(_issue("attention", "dup_code", f"Le code budgétaire {c} apparaît {n} fois."))
        if budget.get("share_column"):
            issues.append(_issue("info", "share_column", f"La colonne « {budget['share_column']} » contient la part de chaque ligne dans le total "
                                 "(0,16 = 16 %), pas un taux unitaire : elle n'est pas reprise."))
        if budget.get("alternatives"):
            for a in budget["alternatives"]:
                if not _close(a["total"], s):
                    issues.append(_issue("info", "budget_versions", f"Autre version du budget trouvée ({a['origin']}, {a['lines']} lignes, "
                                         f"{_fmt(a['total'])}) : la version retenue est {budget.get('origin')} ({_fmt(s, cur)})."))

    # Taux de change
    if grant.get("amount") and grant_mad and rate and grant.get("currency") != "MAD":
        if not _close(grant["amount"] * rate, grant_mad, 2):
            issues.append(_issue("erreur", "rate", f"{_fmt(grant['amount'], grant.get('currency'))} × {rate} = {_fmt(grant['amount'] * rate, 'MAD')}, "
                                 f"mais le document indique {_fmt(grant_mad, 'MAD')}."))
    # Cofinancement
    cof = _v(f, "cofinancing") or {}
    cof_lines = sum(c.get("amount") or 0 for c in result.get("cofinancing") or [])
    if cof.get("amount") and cof_lines and not _close(cof["amount"], cof_lines):
        issues.append(_issue("attention", "cofinancing", f"Le cofinancement annoncé ({_fmt(cof['amount'], 'MAD')}) diffère de la somme des colonnes "
                             f"de cofinancement du budget ({_fmt(cof_lines, 'MAD')})."))

    # Tranches
    tr = result.get("tranches") or []
    if tr:
        pct = [t["percent"] for t in tr if t.get("percent") is not None]
        if pct and len(pct) == len(tr) and not _close(sum(pct), 100, 0.01):
            issues.append(_issue("erreur", "tranches_pct", f"Les pourcentages des tranches font {sum(pct):g} % au lieu de 100 %."))
        amts = [t["amount"] for t in tr if t.get("amount") is not None]
        if grant.get("amount") and amts and len(amts) == len(tr) and not _close(sum(amts), grant["amount"]):
            issues.append(_issue("erreur", "tranches_sum", f"Les tranches totalisent {_fmt(sum(amts), grant.get('currency'))} pour une subvention de "
                                 f"{_fmt(grant['amount'], grant.get('currency'))}."))
        for t in tr:
            if t.get("percent") is not None and t.get("amount") and grant.get("amount") and not _close(t["amount"], grant["amount"] * t["percent"] / 100):
                issues.append(_issue("attention", "tranche_pct_amount", f"{t['label']} : {t['percent']:g} % de la subvention ferait "
                                     f"{_fmt(grant['amount'] * t['percent'] / 100)}, le document indique {_fmt(t['amount'])}.", t.get("source")))
            if not t.get("date"):
                issues.append(_issue("info", "tranche_date", f"{t['label']} : pas de date fixe ({t.get('condition') or 'condition non précisée'}). "
                                     "La date de signature ou de début sera proposée.", t.get("source")))

    # Dates
    try:
        start = date.fromisoformat(_v(p, "start")) if _v(p, "start") else None
        end = date.fromisoformat(_v(p, "end")) if _v(p, "end") else None
    except ValueError:
        start = end = None
    if start and end:
        if end <= start:
            issues.append(_issue("erreur", "dates", "La date de fin précède la date de début."))
        dm = _v(p, "duration_months")
        if dm and abs(N.months_between(start, end) - dm) > 1 and not result.get("amendments"):
            issues.append(_issue("attention", "duration", f"La période {start:%d/%m/%Y} → {end:%d/%m/%Y} fait {N.months_between(start, end)} mois, "
                                 f"le document annonce {dm} mois."))
        outside = []
        for a in result.get("activities") or []:
            try:
                a1 = date.fromisoformat(a["start"]) if a.get("start") else None
                a2 = date.fromisoformat(a["end"]) if a.get("end") else None
            except ValueError:
                continue
            if (a1 and a1 < start) or (a2 and a2 > end):
                outside.append(f"{a['code']} ({(a1 or start):%d/%m/%Y} → {(a2 or end):%d/%m/%Y})")
        if outside:
            issues.append(_issue("attention", "activity_dates", f"{len(outside)} activité(s) hors de la période du projet "
                                 f"{start:%d/%m/%Y} → {end:%d/%m/%Y} : {', '.join(outside[:6])}{'…' if len(outside) > 6 else ''}."))
    missing_dates = [a["code"] for a in result.get("activities") or [] if not a.get("start")]
    if missing_dates:
        issues.append(_issue("info", "activity_no_dates", f"{len(missing_dates)} activité(s) sans calendrier dans les documents "
                             f"({', '.join(missing_dates[:8])}{'…' if len(missing_dates) > 8 else ''}) : dates à compléter dans le planning."))

    # Valeurs contradictoires d'un document à l'autre (ou dans le même document)
    text_all = "\n".join(s.text for s in sources)
    durations = {int(x) for x in re.findall(r"(?:Duration|Dur[ée]e)[^\n\d]{0,40}?(\d{1,3})\s*(?:months|mois)", text_all, re.I)}
    durations |= {int(x) for x in re.findall(r"^\s*(\d{1,3})\s+(?:Months|mois)\s{2,}", text_all, re.I | re.M)}
    if len(durations) > 1:
        issues.append(_issue("attention", "conflict_duration", f"Durées différentes selon les passages : {', '.join(f'{d} mois' for d in sorted(durations))}."))
    amendments = result.get("amendments") or []
    news = set()
    for m in re.finditer(r"Total New Budget\s+\$?\s*([\d,.\s]+\d)", text_all, re.I):
        v = N.parse_amount(m.group(1))
        if v and v > 1000:
            news.add(round(v, 2))
    official = {round(a["new_amount"], 2) for a in amendments if a.get("new_amount")}
    for v in sorted(news - official):
        if official:
            issues.append(_issue("erreur", "conflict_amount", f"Le document indique aussi un « Total New Budget » de {_fmt(v, 'USD')}, "
                                 f"différent du montant de l'avenant ({', '.join(_fmt(o, 'USD') for o in sorted(official))})."))
    for i in range(1, len(amendments)):
        prev, cur_a = amendments[i - 1], amendments[i]
        if prev.get("new_amount") and cur_a.get("old_amount") and not _close(prev["new_amount"], cur_a["old_amount"]):
            issues.append(_issue("erreur", "amendment_chain", f"L'avenant suivant part de {_fmt(cur_a['old_amount'])} alors que le précédent "
                                 f"portait la subvention à {_fmt(prev['new_amount'])}."))
    req = _v(f, "requested") or {}
    if req.get("amount") and grant.get("amount") and not _close(req["amount"], grant["amount"]):
        issues.append(_issue("attention", "requested_vs_budget", f"Montant demandé dans le formulaire : {_fmt(req['amount'], req.get('currency'))} ; "
                             f"budget retenu : {_fmt(grant['amount'], grant.get('currency'))}. Vérifiez le montant accordé."))
    for s in sources:
        for sh in s.sheets:
            labels = [str(r[0]).strip().lower() for r in sh.rows if r and isinstance(r[0], str) and re.match(r"\s*total activit", str(r[0]), re.I)]
            for lab, n in Counter(labels).items():
                if n > 1:
                    issues.append(_issue("info", "dup_subtotal", f"« {lab} » apparaît {n} fois dans {s.name} › {sh.name} (libellé de sous-total recopié)."))

    # Règles du bailleur
    for r in result.get("rules") or []:
        k, val = r.get("kind"), r.get("value")
        if k == "IndirectCostsMaxPercent" and val and lines:
            ind = sum(l["total"] for l in lines if re.search(r"indirect|frais de gestion|overhead|management support|frais administratifs", l["label"] + " " + l.get("category", ""), re.I))
            direct = sum(l["total"] for l in lines) - ind
            if direct and ind / direct * 100 > val + 0.01:
                issues.append(_issue("erreur", "rule_indirect", f"Frais indirects : {_fmt(ind, cur)}, soit {ind / direct * 100:.2f} % des frais directs "
                                     f"({_fmt(direct, cur)}) ; le bailleur plafonne à {val:g} % ({_fmt(direct * val / 100, cur)}).", r.get("source")))
        if k == "CofinancingMinPercent" and grant_mad and cof.get("amount"):
            if cof["amount"] < grant_mad * (val or 100) / 100:
                issues.append(_issue("erreur", "rule_cofinancing", f"Cofinancement ({_fmt(cof['amount'], 'MAD')}) inférieur au minimum exigé "
                                     f"({val:g} % de la subvention, soit {_fmt(grant_mad * (val or 100) / 100, 'MAD')}).", r.get("source")))
            else:
                issues.append(_issue("info", "rule_ok", f"Règle respectée : cofinancement {_fmt(cof['amount'], 'MAD')} ≥ {val:g} % de la subvention.", r.get("source")))

    # Données sensibles
    if re.search(r"\b(?:IBAN|RIB)\b|\b\d{24}\b|\bMA\d{2}(?:\s?\d){20,}", text_all):
        issues.append(_issue("info", "sensitive", "Coordonnées bancaires détectées dans les documents : elles restent sur ce poste et sont masquées "
                             "avant tout envoi à une IA en ligne."))
    order = {"erreur": 0, "attention": 1, "info": 2}
    return sorted(issues, key=lambda i: order.get(i["level"], 3))
