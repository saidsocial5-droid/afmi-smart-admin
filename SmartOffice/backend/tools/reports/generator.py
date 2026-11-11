"""Génération du rapport annuel (moral, financier ou complet) sous forme de document de l'éditeur.

Les tableaux sont des blocs dynamiques (paramètres : exercice, périmètre, langue) : ils restent à jour tant que le
document est ouvert dans l'éditeur. Les textes (synthèse, faits marquants…) sont tirés des données ; la synthèse IA
est facultative et ses chiffres absents des données sont signalés dans le document.
"""
from datetime import date
from typing import Any, Dict, List, Optional

from backend.core import ai_config, unified_db
from backend.core.llm_router import llm_router
from backend.tools.editor import assistant, documents
from . import checks as checks_mod, finance, moral
from .context import layout, period as get_period, scope as get_scope
from .i18n import t

TABLES = {
    "cer": lambda c, p, s, lay, lang: finance.cer(c, p, s, lay, lang),
    "income_expense": lambda c, p, s, lay, lang: finance.income_expense(c, p, s, lang),
    "budget_project": lambda c, p, s, lay, lang: finance.budget_execution(c, p, s, "project", lang),
    "budget_funder": lambda c, p, s, lay, lang: finance.budget_execution(c, p, s, "funder", lang),
    "treasury": lambda c, p, s, lay, lang: finance.treasury(c, p, s, lang),
    "carry_forward": lambda c, p, s, lay, lang: finance.carry_forward(c, p, s, lang),
    "comparison": lambda c, p, s, lay, lang: finance.comparison(c, p, s, lay, lang),
    "charts": lambda c, p, s, lay, lang: finance.charts(c, p, s, lay, lang),
    "activities": lambda c, p, s, lay, lang: moral.table_activities(c, p, s, lang),
    "indicators": lambda c, p, s, lay, lang: moral.table_indicators(c, p, s, lang),
    "beneficiaries": lambda c, p, s, lay, lang: moral.table_beneficiaries(c, p, s, lang),
}


def table(name: str, year: int, scope_type: str, scope_id: Optional[int], lang: str = "fr") -> Dict[str, Any]:
    if name not in TABLES:
        raise ValueError(f"Tableau inconnu : {name}.")
    with unified_db.connect() as conn:
        return TABLES[name](conn, get_period(conn, year), get_scope(conn, scope_type, scope_id), layout(), lang)


def run_checks(year: int, scope_type: str, scope_id: Optional[int]) -> Dict[str, Any]:
    with unified_db.connect() as conn:
        p, s = get_period(conn, year), get_scope(conn, scope_type, scope_id)
        result = checks_mod.run(conn, p, s, layout())
        result.update({"period": {"start": p.start, "end": p.end}, "scope": s.label})
        return result


def scope_label(s, lang: str) -> str:
    """Libellé du périmètre dans la langue du rapport (le nom du projet ou du bailleur reste tel quel)."""
    if s.type == "association":
        return t(lang, "scope_association")
    name = s.label.split(" : ", 1)[1] if " : " in s.label else s.label
    return f"{t(lang, 'scope_' + s.type)} : {name}"


# --- Construction du document (JSON TipTap) ------------------------------------------------------------------

def _text(s: str, bold: bool = False) -> Dict[str, Any]:
    node = {"type": "text", "text": s}
    if bold:
        node["marks"] = [{"type": "bold"}]
    return node


def _p(s: str, italic: bool = False) -> Dict[str, Any]:
    node = {"type": "paragraph", "content": [{"type": "text", "text": s, **({"marks": [{"type": "italic"}]} if italic else {})}]} if s else {"type": "paragraph"}
    return node


def _h(level: int, s: str) -> Dict[str, Any]:
    return {"type": "heading", "attrs": {"level": level}, "content": [_text(s)]}


def _bullets(items: List[str]) -> Dict[str, Any]:
    return {"type": "bulletList", "content": [{"type": "listItem", "content": [_p(i)]} for i in items]}


def _block(name: str, year: int, scope_type: str, scope_id: Optional[int], lang: str) -> Dict[str, Any]:
    return {"type": "dynamicBlock", "attrs": {"kind": "annual", "table": name, "year": year, "scopeType": scope_type,
                                              "scopeId": scope_id, "lang": lang}}


def _with_dir(content: List[Dict[str, Any]], lang: str) -> List[Dict[str, Any]]:
    if lang != "ar":
        return content
    for n in content:
        if n["type"] in ("paragraph", "heading"):
            n.setdefault("attrs", {})["dir"] = "rtl"
    return content


async def _ai_synthesis(f: Dict[str, Any], lang: str) -> Optional[Dict[str, Any]]:
    """Synthèse rédigée par l'IA à partir des seuls faits ; None si aucun modèle n'est disponible."""
    text, engine = await llm_router.generate_with_meta(
        f"Rédige en 2 paragraphes la synthèse de l'exercice, en {assistant.LANG.get(lang, 'français')}, à partir de ces faits "
        f"UNIQUEMENT (n'invente aucun chiffre, nom ou date) :\n{f}", system_prompt=ai_config.prompt("reports.synthesis", lang=assistant.LANG.get(lang, "français")),
        temperature=0.2, task="reports")
    if engine == "heuristic":
        return None
    return {"text": text.strip(), "engine": engine, "unverified": assistant.numbers_not_in_facts(text, f)}


async def generate(year: int, scope_type: str, scope_id: Optional[int], language: str = "fr", kind: str = "both",
                   template_id: Optional[int] = None, use_ai: bool = False, accept_warnings: bool = True) -> Dict[str, Any]:
    if kind not in ("moral", "financial", "both"):
        raise ValueError("Type de rapport : moral, financial ou both.")
    if language not in ("fr", "ar", "en"):
        raise ValueError("Langue : fr, ar ou en.")
    lay = layout()
    with unified_db.connect() as conn:
        p, s = get_period(conn, year), get_scope(conn, scope_type, scope_id)
        check = checks_mod.run(conn, p, s, lay)
        if check["blocking"]:
            return {"document": None, **check}
        if not accept_warnings and check["checks"]:
            return {"document": None, **check}
        totals = finance.totals(conn, p, s)
        facts = moral.facts(conn, p, s, totals, language)
        projs = moral.projects(conn, p, s)
        acts = moral.activities(conn, p, s)
        partners = moral.partners(conn, projs)
        project_row = conn.execute("SELECT FunderId FROM Projects WHERE Id = ?", (scope_id,)).fetchone() if scope_type in ("project", "programme") else None

    s.label = scope_label(s, language)
    title_key = {"moral": "moral_title", "financial": "financial_title", "both": "annual_title"}[kind]
    title = t(language, title_key, year=year) + ("" if scope_type == "association" else f" — {s.label}")
    content: List[Dict[str, Any]] = [
        _h(1, title),
        _p(f"{t(language, 'scope')} : {s.label}. {t(language, 'period', start=p.start, end=p.end)}."),
        _p(t(language, "generated", date=date.today().strftime("%d/%m/%Y")), italic=True),
        {"type": "tableOfContents"},
    ]
    blk = lambda name: _block(name, year, scope_type, scope_id, language)

    if kind in ("moral", "both"):
        if kind == "both":
            content.append(_h(1, t(language, "moral_title", year=year)))
        content.append(_h(2, t(language, "summary")))
        content += [_p(x) for x in moral.synthesis(facts, language)]
        if use_ai:
            ai = await _ai_synthesis(facts, language)
            if ai:
                content += [_p(x) for x in ai["text"].split("\n\n") if x.strip()]
                content.append(_p(f"(Synthèse rédigée par l'IA — {ai['engine']} — à relire.)", italic=True))
                if ai["unverified"]:
                    content.append(_p(t(language, "verify", numbers=", ".join(ai["unverified"]))))
            else:
                content.append(_p("(Aucun modèle d'IA disponible : synthèse établie automatiquement à partir des données.)", italic=True))
        content.append(_h(2, t(language, "projects")))
        for pr in projs:
            content.append(_h(3, f"{pr['code']} — {pr['name']}"))
            meta = [x for x in [f"{t(language, 'funder')} : {pr['funder']}" if pr["funder"] else "", f"{t(language, 'status')} : {pr['status']}",
                                f"{pr['start']} → {pr['end']}" if pr["start"] or pr["end"] else "",
                                f"Avancement : {int(pr['progress'])} %" if pr["progress"] is not None else ""] if x]
            content.append(_p(" · ".join(meta)))
            if pr["description"]:
                content.append(_p(f"{t(language, 'objectives')} : {pr['description']}"))
        if not projs:
            content.append(_p(t(language, "no_data")))
        content += [_h(2, t(language, "activities")), blk("activities"), _h(2, t(language, "indicators")), blk("indicators"),
                    _h(2, t(language, "beneficiaries")), blk("beneficiaries")]
        content += [_h(2, t(language, "partners")), _bullets(partners) if partners else _p(t(language, "no_data"))]
        highlights = [f"{a['date']} — {a['title']} ({a['location']}, {a['participants']} participants)" + (f" : {a['narrative'].split('.')[0]}." if a["narrative"] else "")
                      for a in sorted(acts, key=lambda a: -a["participants"])[:8]]
        content += [_h(2, t(language, "highlights")), _bullets(highlights) if highlights else _p(t(language, "no_data"))]
        diffs = [f"{a['title']} : {a['difficulties']}" for a in acts if a["difficulties"]] + [f"{pr['code']} : {pr['lessons']}" for pr in projs if pr["lessons"]]
        content += [_h(2, t(language, "difficulties")), _bullets(diffs) if diffs else _p("[À compléter]")]
        persp = [f"{a['title']} : {a['recommendations']}" for a in acts if a["recommendations"]] + \
                [f"{pr['code']} — {pr['name']} : se poursuit jusqu'au {pr['end']}." for pr in projs if pr["end"] and pr["end"] > p.end]
        content += [_h(2, t(language, "perspectives")), _bullets(persp) if persp else _p("[À compléter]")]
        content.append(_h(2, t(language, "photos")))
        for pr in projs[:6]:
            content.append({"type": "dynamicBlock", "attrs": {"kind": "gallery", "projectId": pr["id"], "dateFrom": p.start, "dateTo": p.end, "limit": 4,
                                                              "title": pr["code"]}})

    if kind in ("financial", "both"):
        if kind == "both":
            content.append({"type": "pageBreak"})
            content.append(_h(1, t(language, "financial_title", year=year)))
        content.append(_p(lay.get("status_note", t(language, "provisional")), italic=True))
        for key, name in (("cer", "cer"), ("income_expense", "income_expense"), (None, "budget_project"), (None, "budget_funder"),
                          (None, "treasury"), ("carry", "carry_forward"), (None, "comparison"), ("charts", "charts")):
            heading = {"budget_project": f"{t(language, 'budget_exec')} {t(language, 'by_project')}",
                       "budget_funder": f"{t(language, 'budget_exec')} {t(language, 'by_funder')}",
                       "treasury": t(language, "treasury", end=p.end), "comparison": t(language, "comparison", prev=year - 1)}.get(name) or t(language, key)
            content += [_h(2, heading), blk(name)]
        if check["checks"]:
            content.append(_h(2, "Contrôles de cohérence"))
            content.append(_bullets([f"{c['message']} ({c['count']})" for c in check["checks"]]))

    doc = documents.create_document({
        "title": title, "language": language, "template_id": None,
        "project_id": scope_id if scope_type in ("project", "programme") else None,
        "funder_id": scope_id if scope_type == "funder" else (project_row["FunderId"] if project_row else None),
        "content": {"type": "doc", "content": _with_dir(content, language)},
    })
    if template_id:  # modèle de mise en page : on reprend sa mise en page (marges, en-têtes…), le contenu reste généré
        doc = documents.save_document(doc["id"], {"layout": documents.get_template(template_id)["layout"]})
    return {"document": {"id": doc["id"], "title": doc["title"]}, **check}
