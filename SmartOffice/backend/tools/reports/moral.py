"""Données du rapport moral : projets de l'exercice, activités, indicateurs GAR, bénéficiaires, partenaires,
faits marquants, difficultés, perspectives. Tout provient de la base ; rien n'est rédigé sans source."""
import json
from collections import defaultdict
from typing import Any, Dict, List, Optional

from backend.config.settings import settings
from .context import Period, Scope
from .i18n import t


def projects(conn, period: Period, scope: Scope) -> List[Dict[str, Any]]:
    rows = conn.execute("SELECT p.*, f.Name AS FunderName FROM Projects p LEFT JOIN Funders f ON f.Id = p.FunderId "
                        "WHERE p.IsDeleted = 0 ORDER BY p.Code").fetchall()
    out = []
    for p in rows:
        if scope.project_ids is not None and p["Id"] not in scope.project_ids:
            continue
        start, end = str(p["TargetStartDate"] or "")[:10], str(p["TargetEndDate"] or "")[:10]
        overlaps = (not start or start <= period.end) and (not end or end >= period.start)
        active = conn.execute(
            "SELECT 1 FROM ActivityReports r JOIN Tasks t ON t.Id = r.ProjectTaskId WHERE t.ProjectId = ? AND date(r.ActivityDate) BETWEEN ? AND ? "
            "UNION SELECT 1 FROM OperationAllocations a JOIN Operations o ON o.Id = a.OperationId WHERE a.ProjectId = ? AND o.Status = 'Validated' "
            "AND o.IsDeleted = 0 AND o.OperationDate BETWEEN ? AND ? LIMIT 1",
            (p["Id"], period.start, period.end, p["Id"], period.start, period.end)).fetchone()
        if not (overlaps or active):
            continue
        progress = conn.execute("SELECT AVG(ProgressPercentage) FROM Tasks WHERE ProjectId = ? AND ParentTaskId IS NULL", (p["Id"],)).fetchone()[0]
        out.append({"id": p["Id"], "code": p["Code"], "name": p["Name"], "description": p["Description"], "status": p["Status"],
                    "funder": p["FunderName"], "start": start, "end": end, "progress": round(progress, 0) if progress is not None else None,
                    "lessons": p["LessonsLearned"], "parent_id": p["ParentProjectId"]})
    return out


def activities(conn, period: Period, scope: Scope) -> List[Dict[str, Any]]:
    rows = conn.execute(
        "SELECT r.*, t.ProjectId, p.Code AS ProjCode FROM ActivityReports r JOIN Tasks t ON t.Id = r.ProjectTaskId "
        "JOIN Projects p ON p.Id = t.ProjectId WHERE p.IsDeleted = 0 AND date(r.ActivityDate) BETWEEN ? AND ? ORDER BY r.ActivityDate",
        (period.start, period.end)).fetchall()
    return [{"id": r["Id"], "project_id": r["ProjectId"], "project": r["ProjCode"], "date": str(r["ActivityDate"])[:10], "title": r["Title"],
             "location": r["Location"], "participants": r["ParticipantsCount"] or 0, "narrative": r["Narrative"], "difficulties": r["Difficulties"],
             "recommendations": r["Recommendations"], "status": r["Status"]}
            for r in rows if scope.project_ids is None or r["ProjectId"] in scope.project_ids]


def _aggregate(values: List[Dict[str, Any]], how: str) -> Optional[float]:
    if not values:
        return None
    totals = [v for v in values if not (v["Sex"] or v["AgeGroup"] or v["Zone"])]
    use = totals or values
    if how == "Dernière":
        last = max(v["PeriodEnd"] for v in use)
        return sum(v["Value"] for v in use if v["PeriodEnd"] == last)
    return sum(v["Value"] for v in use)


def indicators(conn, period: Period, scope: Scope) -> List[Dict[str, Any]]:
    out = []
    for i in conn.execute("SELECT i.*, p.Code AS ProjCode FROM Indicators i JOIN Projects p ON p.Id = i.ProjectId WHERE p.IsDeleted = 0 "
                          "ORDER BY p.Code, i.Name"):
        if scope.project_ids is not None and i["ProjectId"] not in scope.project_ids:
            continue
        meas = [dict(m) for m in conn.execute("SELECT * FROM IndicatorMeasurements WHERE IndicatorId = ? AND PeriodEnd BETWEEN ? AND ?",
                                              (i["Id"], period.start, period.end))]
        value = _aggregate(meas, i["Aggregation"] or "Somme")
        out.append({"id": i["Id"], "project_id": i["ProjectId"], "project": i["ProjCode"], "name": i["Name"], "unit": i["Unit"],
                    "level": i["Level"] or "Extrant", "baseline": i["BaselineValue"], "target": i["TargetValue"],
                    "value": value if value is not None else i["CurrentValue"], "measured": value is not None,
                    "rate": round(100 * (value if value is not None else i["CurrentValue"]) / i["TargetValue"], 1) if i["TargetValue"] else None,
                    "measurements": meas})
    return out


def beneficiaries(inds: List[Dict[str, Any]], lang: str) -> Dict[str, Dict[str, float]]:
    """Ventilations par sexe, âge et zone, à partir des mesures désagrégées de l'exercice."""
    out = {"sex": defaultdict(float), "age": defaultdict(float), "zone": defaultdict(float)}
    labels = {"F": t(lang, "women"), "M": t(lang, "men")}
    for ind in inds:
        for m in ind["measurements"]:
            if m["Sex"]:
                out["sex"][labels[m["Sex"]]] += m["Value"]
            if m["AgeGroup"]:
                out["age"][m["AgeGroup"]] += m["Value"]
            if m["Zone"]:
                out["zone"][m["Zone"]] += m["Value"]
    return {k: dict(v) for k, v in out.items()}


def partners(conn, projs: List[Dict[str, Any]]) -> List[str]:
    names = [p["funder"] for p in projs if p["funder"]]
    ids = [p["id"] for p in projs]
    if ids:
        names += [r[0] for r in conn.execute(
            f"SELECT DISTINCT f.Name FROM FundingAgreements a JOIN Funders f ON f.Id = a.FunderId WHERE a.IsDeleted = 0 AND a.ProjectId IN ({','.join('?' * len(ids))})", ids)]
    try:
        profile = json.loads((settings.ngo_profile_path).read_text(encoding="utf-8"))
        names += [p for p in profile.get("partners", []) if isinstance(p, str)]
    except (OSError, ValueError):
        pass
    return list(dict.fromkeys(names))


def facts(conn, period: Period, scope: Scope, fin_totals: Dict[str, int], lang: str = "fr") -> Dict[str, Any]:
    """Faits chiffrés de l'exercice : seule matière autorisée pour la synthèse (et pour l'IA, si elle est utilisée)."""
    projs = projects(conn, period, scope)
    acts = activities(conn, period, scope)
    inds = indicators(conn, period, scope)
    return {
        "exercice": period.year, "periode": [period.start, period.end], "perimetre": scope.label,
        "projets": [{"code": p["code"], "nom": p["name"], "bailleur": p["funder"], "avancement_pct": p["progress"]} for p in projs],
        "nombre_projets": len(projs), "nombre_activites": len(acts), "participants": sum(a["participants"] for a in acts),
        "ressources_mad": round(fin_totals["income"] / 100, 2), "emplois_mad": round(fin_totals["expense"] / 100, 2),
        "resultat_mad": round(fin_totals["result"] / 100, 2),
        "indicateurs": [{"projet": i["project"], "indicateur": i["name"], "cible": i["target"], "realise": i["value"], "unite": i["unit"],
                         "taux_pct": i["rate"]} for i in inds],
        "beneficiaires": beneficiaries(inds, lang),
    }


def _n(x) -> str:
    return f"{x:,.2f}".replace(",", " ").replace(".", ",") if isinstance(x, float) and not x.is_integer() else f"{int(x):,}".replace(",", " ")


def synthesis(f: Dict[str, Any], lang: str) -> List[str]:
    """Synthèse déterministe, entièrement tirée des faits (toujours traçable)."""
    codes = ", ".join(p["code"] for p in f["projets"]) or "—"
    top = [i for i in f["indicateurs"] if i["taux_pct"] is not None][:3]
    if lang == "ar":
        out = [f"خلال السنة المالية {f['exercice']}، أنجزت الجمعية {f['nombre_projets']} مشروعاً ({codes}) و{f['nombre_activites']} نشاطاً بمشاركة {_n(f['participants'])} مشاركاً.",
               f"بلغت موارد السنة {_n(f['ressources_mad'])} درهم والاستعمالات {_n(f['emplois_mad'])} درهم، أي نتيجة قدرها {_n(f['resultat_mad'])} درهم."]
        out += [f"المؤشر «{i['indicateur']}» ({i['projet']}): {_n(i['realise'])} من أصل {_n(i['cible'])} {i['unite']} ({_n(i['taux_pct'])}٪)." for i in top]
    elif lang == "en":
        out = [f"During the {f['exercice']} financial year, the association ran {f['nombre_projets']} project(s) ({codes}) and carried out {f['nombre_activites']} activit(ies) with {_n(f['participants'])} participants.",
               f"Resources for the year amount to MAD {_n(f['ressources_mad'])} and uses to MAD {_n(f['emplois_mad'])}, a result of MAD {_n(f['resultat_mad'])}."]
        out += [f"Indicator “{i['indicateur']}” ({i['projet']}): {_n(i['realise'])} out of {_n(i['cible'])} {i['unite']} ({_n(i['taux_pct'])} %)." for i in top]
    else:
        out = [f"Au cours de l'exercice {f['exercice']}, l'association a conduit {f['nombre_projets']} projet(s) ({codes}) et réalisé {f['nombre_activites']} activité(s) réunissant {_n(f['participants'])} participant(s).",
               f"Les ressources de l'exercice s'élèvent à {_n(f['ressources_mad'])} MAD et les emplois à {_n(f['emplois_mad'])} MAD, soit un résultat de {_n(f['resultat_mad'])} MAD."]
        out += [f"Indicateur « {i['indicateur']} » ({i['projet']}) : {_n(i['realise'])} sur {_n(i['cible'])} {i['unite']} visés ({_n(i['taux_pct'])} %)." for i in top]
    return out


def table_activities(conn, period, scope, lang):
    acts = activities(conn, period, scope)
    rows = [[a["date"], a["project"], a["title"], a["location"], a["participants"]] for a in acts]
    return {"title": t(lang, "activities"), "columns": ["Date", "Projet", t(lang, "activities"), "Lieu", "Participants"], "rows": rows,
            "total": [t(lang, "total"), None, None, None, sum(a["participants"] for a in acts)], "notes": [], "source": "Rapports d'activité", "chart": None,
            "formats": ["text", "text", "text", "text", "number"]}


def table_indicators(conn, period, scope, lang):
    inds = indicators(conn, period, scope)
    rows = [[i["project"], i["name"], i["level"], i["baseline"], i["target"], i["value"], i["rate"],
             "" if i["measured"] else "valeur courante (non datée)"] for i in inds]
    return {"title": t(lang, "indicators"), "columns": ["Projet", t(lang, "indicator"), t(lang, "level"), t(lang, "baseline"), t(lang, "target"),
                                                       t(lang, "value", year=period.year), t(lang, "rate"), "Note"],
            "rows": rows, "total": None, "notes": [], "source": "Indicateurs et mesures de l'exercice", "chart": None,
            "formats": ["text", "text", "text", "number", "number", "number", "percent", "text"]}


def table_beneficiaries(conn, period, scope, lang):
    b = beneficiaries(indicators(conn, period, scope), lang)
    rows = []
    for key, label in (("sex", "Sexe"), ("age", t(lang, "age")), ("zone", t(lang, "zone"))):
        if b[key]:
            rows.append([f"**{label}**", None])
            rows += [[f"    {k}", v] for k, v in sorted(b[key].items())]
    notes = [] if rows else [t(lang, "no_data") + " Saisissez des mesures désagrégées (sexe, âge, zone) dans « Indicateurs »."]
    return {"title": t(lang, "beneficiaries"), "columns": ["", "Nombre"], "rows": rows, "total": None, "notes": notes,
            "source": "Mesures désagrégées des indicateurs", "chart": None, "formats": ["text", "number"]}


def table_meetings(conn, period, scope, lang):
    """Réunions et instances de l'exercice (comptes rendus validés, Lot 9), par type, avec les décisions."""
    from backend.tools.meetings import service as meetings
    summary = meetings.summary_for_year(conn, period.year, scope.project_ids)
    rows = [[f"**{meetings.KINDS.get(k, {}).get('label', k)}**", n] for k, n in sorted(summary["by_kind"].items())]
    for m in summary["meetings"]:
        rows.append([f"    {m['date']} — {m['title']}", None])
    notes = [f"Décision du {d['date']} ({d['meeting']}) : {d['text']}" for d in summary["decisions"][:20]]
    if not rows:
        notes = [t(lang, "no_data") + " Les comptes rendus validés de l'exercice apparaissent ici (menu « Comptes rendus & PV »)."]
    return {"title": "Réunions et instances", "columns": ["", "Nombre"], "rows": rows, "total": ["Total", summary["count"]] if rows else None,
            "notes": notes, "source": "Comptes rendus et PV validés", "chart": None, "formats": ["text", "number"]}
