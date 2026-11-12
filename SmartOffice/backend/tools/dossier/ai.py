"""Lecture d'un dossier par l'IA choisie dans les paramètres (tâche « dossier »), avec garde-fous :
- local d'abord : rien ne sort du poste si l'IA externe n'est pas autorisée (le routeur applique la règle) ;
- masquage des RIB, CIN, salaires avant envoi (routeur) ;
- chaque montant, pourcentage ou cible proposé par l'IA doit se retrouver dans le texte des documents,
  sinon il est marqué « non retrouvé » et signalé ; l'IA ne remplace jamais une valeur lue par les règles.
"""
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from . import normalize as N
from .sources import Source

SCHEMA = {
    "project": {"code": "str", "title": "str", "donor": "str", "start": "AAAA-MM-JJ", "end": "AAAA-MM-JJ", "duration_months": "int",
                "manager": "str", "location": "str", "objective": "str", "partners": ["str"]},
    "funding": {"grant": {"amount": "nombre", "currency": "MAD|USD|EUR"}, "grant_mad": {"amount": "nombre", "currency": "MAD"},
                "cofinancing": {"amount": "nombre", "currency": "str"}, "total_cost": {"amount": "nombre", "currency": "str"},
                "exchange_rate": "nombre", "signature_date": "AAAA-MM-JJ"},
    "tranches": [{"label": "str", "percent": "nombre", "amount": "nombre", "currency": "str", "date": "AAAA-MM-JJ", "condition": "str"}],
    "budget": {"currency": "str", "lines": [{"code": "str", "category": "str", "label": "str", "total": "nombre", "by_source": {"source": "nombre"}}]},
    "activities": [{"code": "str", "title": "str", "responsible": "str", "start": "AAAA-MM-JJ", "end": "AAAA-MM-JJ"}],
    "logframe": [{"level": "Objectif global|Objectif spécifique|Résultat|Produit", "code": "str", "statement": "str", "parent_code": "str"}],
    "indicators": [{"code": "str", "result_code": "str", "name": "str", "target": "nombre", "unit": "str", "baseline": "nombre", "verification": "str"}],
    "reports": [{"title": "str", "kind": "str", "due": "AAAA-MM-JJ"}],
    "risks": [{"description": "str", "probability": "Faible|Moyen|Élevé", "impact": "Faible|Moyen|Élevé", "mitigation": "str"}],
    "rules": [{"kind": "IndirectCostsMaxPercent|CofinancingMinPercent|GrantMaxShareOfIncomePercent|GrantMaxAmount|Other", "value": "nombre", "text": "str"}],
}
KEYWORDS = re.compile(r"budget|montant|subvention|tranche|activit|indicateur|r[ée]sultat|objectif|risque|rapport|p[ée]riode|dur[ée]e|"
                      r"grant|amount|activity|indicator|risk|report|period|duration|deliverable|component", re.I)
MAX_CHARS = 110_000


def _corpus(sources: List[Source]) -> str:
    """Pages des documents, les plus utiles d'abord si le dossier dépasse la taille admise."""
    pages: List[Tuple[int, str, str, int]] = []
    for s in sources:
        for no, text in s.pages:
            t = re.sub(r"[ \t]{3,}", "   ", text)
            pages.append((len(KEYWORDS.findall(t)) + (100 if no <= 2 else 0), s.name, t, no))
    total = sum(len(p[2]) for p in pages)
    keep = pages if total <= MAX_CHARS else sorted(pages, key=lambda p: -p[0])
    out, size = [], 0
    for score, name, t, no in keep:
        block = f"\n=== Fichier : {name} — page {no} ===\n{t}"
        if size + len(block) > MAX_CHARS:
            continue
        out.append((name, no, block))
        size += len(block)
    order = {(s.name, no): i for i, s in enumerate(sources) for no, _ in s.pages}
    out.sort(key=lambda x: order.get((x[0], x[1]), 0))
    return "".join(b for _, _, b in out)


def _parse_json(text: str) -> Optional[Dict[str, Any]]:
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    a, b = text.find("{"), text.rfind("}")
    if a < 0 or b <= a:
        return None
    try:
        return json.loads(text[a:b + 1])
    except json.JSONDecodeError:
        return None


def _known_numbers(sources: List[Source]) -> set:
    keys = set()
    for s in sources:
        for _, raw, _ in N.amounts_in(s.text):
            v = N.parse_amount(raw)
            if v is not None:
                keys.add(N.digits_key(v))
        for sh in s.sheets:
            for r in sh.rows:
                for v in r:
                    if isinstance(v, (int, float)):
                        keys.add(N.digits_key(float(v)))
    return keys


def _verify(value: Any, known: set) -> bool:
    if value is None or value == "":
        return True
    try:
        return N.digits_key(float(value)) in known
    except (TypeError, ValueError):
        return True


async def extract(sources: List[Source]) -> Tuple[Optional[Dict[str, Any]], str, str]:
    """(proposition de l'IA ou None, moteur, message). None si l'IA n'est pas disponible ou a refusé."""
    from backend.core.llm_router import llm_router
    from backend.core import ai_config
    corpus = _corpus(sources)
    prompt = ("Schéma JSON attendu (types indicatifs) :\n" + json.dumps(SCHEMA, ensure_ascii=False) +
              "\nPour chaque élément de liste, ajoute \"src\": {\"file\": nom du fichier, \"page\": numéro}.\n"
              "Dates au format AAAA-MM-JJ. Montants en nombres sans séparateur de milliers. Les trimestres T1…T8 ou « mois 1 à 3 » "
              "restent écrits tels quels dans un champ \"period\" si aucune date n'est donnée.\n\nDocuments :" + corpus)
    try:
        text, engine = await llm_router.generate_with_meta(prompt, ai_config.prompt("dossier.extract"), temperature=0.0,
                                                           response_json=True, task="dossier")
    except Exception as e:  # noqa: BLE001
        return None, "", f"IA indisponible : {e}"
    if engine == "heuristic":
        return None, "", "Aucune IA disponible pour la lecture des dossiers (paramètres › IA, tâche « Lecture des dossiers de projet »)."
    data = _parse_json(text)
    if not isinstance(data, dict):
        return None, engine, "Réponse de l'IA illisible : seules les règles locales sont utilisées."
    return data, engine, ""


def _src(item: Dict[str, Any], engine: str) -> Optional[Dict[str, Any]]:
    s = item.get("src") if isinstance(item, dict) else None
    if isinstance(s, dict):
        return {"file": s.get("file") or "", "page": s.get("page") or "", "excerpt": f"lu par {engine}"}
    return {"file": "", "page": "", "excerpt": f"lu par {engine}"}


def merge(rules_res: Dict[str, Any], ai_res: Dict[str, Any], engine: str, sources: List[Source]) -> List[Dict[str, Any]]:
    """Complète la proposition des règles avec celle de l'IA (sur place). Retourne les alertes de vérification."""
    known = _known_numbers(sources)
    issues: List[Dict[str, Any]] = []
    tag = f"IA ({engine})"

    def scalar(section: str, key: str, value: Any, numeric: bool = False):
        if value in (None, "", [], {}):
            return
        cur = rules_res.setdefault(section, {}).get(key)
        if numeric:
            amt = value.get("amount") if isinstance(value, dict) else value
            if not _verify(amt, known):
                issues.append({"level": "attention", "code": "ai_unverified", "source": None,
                               "message": f"L'IA propose {section}.{key} = {amt}, valeur introuvable dans les documents : ignorée."})
                return
        if cur is None:
            rules_res[section][key] = {"value": value, "source": {"file": "", "page": "", "excerpt": f"lu par {engine}"}, "engine": tag}
        elif str(cur.get("value")).strip().lower() != str(value).strip().lower() and not numeric:
            cur.setdefault("alternatives", []).append({"value": value, "engine": tag})
        elif numeric and isinstance(value, dict) and isinstance(cur.get("value"), dict) and cur["value"].get("amount") != value.get("amount"):
            cur.setdefault("alternatives", []).append({"value": value, "engine": tag})
            issues.append({"level": "attention", "code": "ai_conflict", "source": cur.get("source"),
                           "message": f"{key} : les règles lisent {cur['value'].get('amount')}, l'IA lit {value.get('amount')}. À vérifier."})

    for k, v in (ai_res.get("project") or {}).items():
        scalar("project", k, v)
    for k, v in (ai_res.get("funding") or {}).items():
        scalar("funding", k, v, numeric=k in ("grant", "grant_mad", "cofinancing", "total_cost", "exchange_rate"))

    def items(key: str, numeric_fields: Tuple[str, ...]):
        got = ai_res.get(key) or []
        if not isinstance(got, list) or rules_res.get(key):
            return
        out = []
        for it in got:
            if not isinstance(it, dict):
                continue
            bad = [f for f in numeric_fields if not _verify(it.get(f), known)]
            it["source"] = _src(it, engine)
            it.pop("src", None)
            it["engine"] = tag
            if bad:
                it["unverified"] = bad
            out.append(it)
        if out:
            rules_res[key] = out
            unver = sum(1 for i in out if i.get("unverified"))
            if unver:
                issues.append({"level": "attention", "code": "ai_unverified", "source": None,
                               "message": f"{unver} élément(s) « {key} » proposés par l'IA contiennent un chiffre introuvable dans les documents (marqués)."})

    items("tranches", ("amount", "percent"))
    items("activities", ())
    items("logframe", ())
    items("indicators", ("target", "baseline"))
    items("reports", ())
    items("risks", ())
    items("rules", ("value",))
    b = ai_res.get("budget") or {}
    if not (rules_res.get("budget") or {}).get("lines") and isinstance(b, dict) and b.get("lines"):
        lines = []
        for l in b["lines"]:
            if isinstance(l, dict) and l.get("total") is not None:
                l["source"] = _src(l, engine)
                l.pop("src", None)
                l.setdefault("by_source", {})
                l.setdefault("activity_code", "")
                l.setdefault("category", "")
                if not _verify(l.get("total"), known):
                    l["unverified"] = ["total"]
                lines.append(l)
        if lines:
            rules_res["budget"] = {"currency": b.get("currency") or "", "total_column": "Total", "sources": sorted({k for l in lines for k in l["by_source"]}),
                                   "lines": lines, "declared_total": None, "origin": tag, "alternatives": []}
    return issues
