"""Import intelligent d'un dossier de projet : analyse, revue, application à la base unique (écritures auditées).

Principes : rien n'est écrit sans validation ; aucune donnée existante n'est supprimée (les éléments déjà présents
— même code, même référence — sont mis à jour, les autres ajoutés) ; chaque import garde ses fichiers et sa proposition.
"""
import hashlib
import json
import re
import shutil
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.core import unified_db
from . import ai, checks, rules, sources as S

SECTIONS = ["project", "funding", "budget", "activities", "logframe", "indicators", "reports", "risks", "rules", "cofinancing", "documents"]


class DossierError(ValueError):
    pass


def _dir(import_id: int) -> Path:
    from backend.config.settings import settings
    d = settings.data_dir / "imports" / f"dossier_{import_id}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _value(x: Any) -> Any:
    return x.get("value") if isinstance(x, dict) and "value" in x else x


async def analyze(files: List[Tuple[str, bytes]], project_id: Optional[int] = None, use_ai: bool = True) -> Dict[str, Any]:
    if not files:
        raise DossierError("Aucun fichier reçu.")
    srcs, info, errors = [], [], []
    for name, data in files:
        try:
            src = S.read(data, name)
            srcs.append(src)
            info.append({"name": name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest(), "pages": len(src.pages),
                         "kind": src.kind, "engine": src.engine})
        except Exception as e:  # noqa: BLE001 — un fichier illisible n'empêche pas d'analyser les autres
            errors.append({"name": name, "error": str(e)})
    if not srcs:
        raise DossierError("Aucun des fichiers n'a pu être lu : " + "; ".join(e["error"] for e in errors))
    result = rules.extract(srcs)
    engine, ai_msg, ai_issues = "règles", "", []
    if use_ai:
        proposal, eng, ai_msg = await ai.extract(srcs)
        if proposal:
            ai_issues = ai.merge(result, proposal, eng, srcs)
            engine = f"règles + {eng}"
    result["issues"] = checks.run(result, srcs) + ai_issues
    if ai_msg:
        result["issues"].append({"level": "info", "code": "ai", "message": ai_msg, "source": None})
    for e in errors:
        result["issues"].insert(0, {"level": "erreur", "code": "file", "message": f"{e['name']} : {e['error']}", "source": None})
    result["defaults"] = _defaults(result)
    with unified_db.connect() as conn:
        imp_id = unified_db.insert(conn, "ProjectImports", "ProjectImport", {
            "ProjectId": project_id, "CreatedAtUtc": unified_db.now_ef(), "CreatedBy": unified_db.current_user(),
            "FilesJson": json.dumps(info, ensure_ascii=False), "ResultJson": json.dumps(result, ensure_ascii=False, default=str),
            "Engine": engine[:80], "Status": "Brouillon", "AppliedAtUtc": None, "AppliedSummary": ""})
    d = _dir(imp_id)
    for name, data in files:
        (d / Path(name).name).write_bytes(data)
    return get(imp_id)


def _defaults(r: Dict[str, Any]) -> Dict[str, Any]:
    """Valeurs proposées pour la création du projet et le traitement des contributions en nature."""
    p, f = r.get("project", {}), r.get("funding", {})
    title = _value(p.get("title")) or ""
    short = re.split(r"\s*[:–—-]\s+", title)[0][:120] if title else ""
    return {"code": _value(p.get("code")) or "", "name": short or title[:120], "funder": _value(p.get("donor")) or "", "in_kind": "Suivi"}


def get(import_id: int) -> Dict[str, Any]:
    with unified_db.connect() as conn:
        row = conn.execute("SELECT * FROM ProjectImports WHERE Id = ?", (import_id,)).fetchone()
        if row is None:
            raise DossierError("Import introuvable.")
        project = None
        if row["ProjectId"]:
            p = conn.execute("SELECT Id, Code, Name, Description, Manager, TargetStartDate, TargetEndDate, BudgetGlobal, Currency, FunderId "
                             "FROM Projects WHERE Id = ?", (row["ProjectId"],)).fetchone()
            project = dict(p) if p else None
    return {"id": row["Id"], "project_id": row["ProjectId"], "project": project, "created": row["CreatedAtUtc"], "engine": row["Engine"],
            "status": row["Status"], "files": json.loads(row["FilesJson"] or "[]"), "result": json.loads(row["ResultJson"] or "{}"),
            "applied_summary": row["AppliedSummary"]}


def list_imports(project_id: Optional[int] = None) -> List[Dict[str, Any]]:
    with unified_db.connect() as conn:
        q = "SELECT Id, ProjectId, CreatedAtUtc, Engine, Status, FilesJson, AppliedSummary FROM ProjectImports"
        rows = conn.execute(q + (" WHERE ProjectId = ?" if project_id else "") + " ORDER BY Id DESC LIMIT 50",
                            (project_id,) if project_id else ()).fetchall()
    return [{"id": r["Id"], "project_id": r["ProjectId"], "created": r["CreatedAtUtc"], "engine": r["Engine"], "status": r["Status"],
             "files": [f["name"] for f in json.loads(r["FilesJson"] or "[]")], "summary": r["AppliedSummary"]} for r in rows]


def save(import_id: int, result: Dict[str, Any], project_id: Optional[int] = None) -> Dict[str, Any]:
    """Corrections de l'utilisateur pendant la revue (proposition complète renvoyée par l'écran)."""
    with unified_db.connect() as conn:
        row = conn.execute("SELECT Status FROM ProjectImports WHERE Id = ?", (import_id,)).fetchone()
        if row is None:
            raise DossierError("Import introuvable.")
        if row["Status"] == "Appliqué":
            raise DossierError("Cet import a déjà été appliqué : relancez une analyse pour le modifier.")
        values = {"ResultJson": json.dumps(result, ensure_ascii=False, default=str)}
        if project_id is not None:
            values["ProjectId"] = project_id or None
        unified_db.update(conn, "ProjectImports", "ProjectImport", import_id, values)
    return get(import_id)


# ---------------------------------------------------------------- application
def _minor(v: Any) -> int:
    try:
        return int(round(float(v) * 100))
    except (TypeError, ValueError):
        return 0


def _ef_dt(d: Optional[str]) -> Optional[str]:
    return f"{d[:10]} 00:00:00" if d else None


def _funder(conn, name: str, in_kind: str) -> Optional[int]:
    if not name:
        return None
    row = conn.execute("SELECT Id, InKindTreatment FROM Funders WHERE lower(Name) = lower(?)", (name,)).fetchone()
    if row:
        if in_kind and row["InKindTreatment"] != in_kind:
            unified_db.update(conn, "Funders", "Funder", row["Id"], {"InKindTreatment": in_kind})
        return row["Id"]
    return unified_db.insert(conn, "Funders", "Funder", {"Name": name[:200], "PrimaryColor": "#1B4332", "LogoPath": "", "LegalMentions": "",
                                                        "HeaderText": "", "FooterText": "", "InKindTreatment": in_kind or "Suivi"})


async def apply(import_id: int, options: Dict[str, Any]) -> Dict[str, Any]:
    """options : project_id (ou create: {code, name}), sections [...], project_fields [...], in_kind ('Suivi'|'Comptabilité')."""
    imp = get(import_id)
    if imp["status"] == "Appliqué":
        raise DossierError("Cet import a déjà été appliqué.")
    r = imp["result"]
    sections = set(options.get("sections") or SECTIONS)
    in_kind = options.get("in_kind")                  # None : le réglage du bailleur reste tel quel
    if in_kind not in (None, "Suivi", "Comptabilité"):
        raise DossierError("Traitement des contributions en nature : « Suivi » ou « Comptabilité ».")
    p, f = r.get("project", {}), r.get("funding", {})
    summary: Dict[str, int] = {}
    budget = r.get("budget") or {}
    b_cur = (budget.get("currency") or (_value(f.get("grant")) or {}).get("currency") or "MAD").upper()[:3]

    def count(k: str, n: int = 1):
        summary[k] = summary.get(k, 0) + n

    with unified_db.connect() as conn:
        funder_id = _funder(conn, (options.get("funder") or _value(p.get("donor")) or "").strip(), in_kind)
        project_id = options.get("project_id") or imp["project_id"]
        if not project_id:
            create = options.get("create") or {}
            code = (create.get("code") or _value(p.get("code")) or "").strip()
            name = (create.get("name") or _value(p.get("title")) or "").strip()
            if not code or not name:
                raise DossierError("Code et nom du projet requis pour le créer.")
            if conn.execute("SELECT 1 FROM Projects WHERE Code = ? AND IsDeleted = 0", (code,)).fetchone():
                raise DossierError(f"Un projet porte déjà le code {code} : choisissez-le dans la liste au lieu d'en créer un.")
            project_id = unified_db.insert(conn, "Projects", "Project", {
                "Name": name[:250], "Code": code[:60], "Description": "", "Manager": "", "Owner": "", "Client": "", "Department": "",
                "FunderId": funder_id, "Status": "Initiation", "Priority": "Moyenne", "BudgetGlobal": "0", "ParentProjectId": None,
                "LessonsLearned": "", "LocalFolderPath": "", "Currency": b_cur, "IsDeleted": 0,
                "TargetStartDate": None, "TargetEndDate": None, "ActualStartDate": None, "ActualEndDate": None})
            count("projet créé")
        proj = conn.execute("SELECT * FROM Projects WHERE Id = ? AND IsDeleted = 0", (project_id,)).fetchone()
        if proj is None:
            raise DossierError("Projet introuvable.")

        # Fiche du projet : seulement les champs cochés pendant la revue
        if "project" in sections:
            fields = set(options.get("project_fields") or ["title", "description", "manager", "start", "end", "budget_global", "funder"])
            values: Dict[str, Any] = {}
            title = _value(p.get("title"))
            if "title" in fields and title and options.get("rename", False):
                values["Name"] = title[:250]
            desc = " ".join(x for x in [_value(p.get("objective")) or "", f"Lieu : {_value(p.get('location'))}." if _value(p.get("location")) else "",
                                         f"Intitulé complet : {title}." if title and title != proj["Name"] else ""] if x)
            if "description" in fields and desc and not (proj["Description"] or "").strip():
                values["Description"] = desc[:4000]
            if "manager" in fields and _value(p.get("manager")):
                values["Manager"] = _value(p.get("manager"))[:150]
            if "start" in fields and _value(p.get("start")):
                values["TargetStartDate"] = _ef_dt(_value(p.get("start")))
            if "end" in fields and _value(p.get("end")):
                values["TargetEndDate"] = _ef_dt(_value(p.get("end")))
            if "funder" in fields and funder_id:
                values["FunderId"] = funder_id
            if "budget_global" in fields and budget.get("lines"):
                values["BudgetGlobal"] = str(round(sum(float(l.get("total") or 0) for l in budget["lines"]), 2))
                values["Currency"] = b_cur
            if values:
                unified_db.update(conn, "Projects", "Project", project_id, values)
                count("champs de la fiche", len(values))

        # Convention, tranches, règles
        agreement_id = None
        grant = _value(f.get("grant")) or {}
        if ("funding" in sections or "rules" in sections) and funder_id and grant.get("amount"):
            ref = (_value(p.get("code")) or proj["Code"])[:100]
            row = conn.execute("SELECT Id FROM FundingAgreements WHERE ProjectId = ? AND Reference = ? AND IsDeleted = 0", (project_id, ref)).fetchone()
            rate = _value(f.get("exchange_rate"))
            vals = {"FunderId": funder_id, "ProjectId": project_id, "Reference": ref, "Title": (_value(p.get("title")) or proj["Name"])[:250],
                    "AmountMinor": _minor(grant["amount"]), "Currency": (grant.get("currency") or "MAD")[:3],
                    "ContractualRateToMad": str(rate) if rate and (grant.get("currency") or "MAD") != "MAD" else None,
                    "SignatureDate": (_value(f.get("signature_date")) or None), "StartDate": _value(p.get("start")), "EndDate": _value(p.get("end")),
                    "Notes": f"Importé du dossier (import n° {import_id})."}
            if row:
                agreement_id = row["Id"]
                unified_db.update(conn, "FundingAgreements", "FundingAgreement", agreement_id, vals)
                count("convention mise à jour")
            else:
                agreement_id = unified_db.insert(conn, "FundingAgreements", "FundingAgreement", {**vals, "IsDeleted": 0})
                count("convention")
            if "funding" in sections:
                fallback = _value(f.get("signature_date")) or _value(p.get("start")) or date.today().isoformat()
                for t in r.get("tranches") or []:
                    if not t.get("amount"):
                        continue
                    tv = {"FundingAgreementId": agreement_id, "Label": (t.get("label") or "Tranche")[:100], "ExpectedDate": (t.get("date") or fallback)[:10],
                          "AmountMinor": _minor(t["amount"]), "Percent": str(t["percent"]) if t.get("percent") is not None else None,
                          "Condition": (t.get("condition") or "")[:500]}
                    ex = conn.execute("SELECT Id FROM FundingTranches WHERE FundingAgreementId = ? AND Label = ? AND IsDeleted = 0",
                                      (agreement_id, tv["Label"])).fetchone()
                    if ex:
                        unified_db.update(conn, "FundingTranches", "FundingTranche", ex["Id"], tv)
                    else:
                        unified_db.insert(conn, "FundingTranches", "FundingTranche", {**tv, "ReceivedOperationId": None, "IsDeleted": 0})
                    count("tranches")
            if "rules" in sections:
                for rule in r.get("rules") or []:
                    ex = conn.execute("SELECT Id FROM DonorRules WHERE FundingAgreementId = ? AND Kind = ? AND IsDeleted = 0",
                                      (agreement_id, rule.get("kind") or "Other")).fetchone()
                    rv = {"FundingAgreementId": agreement_id, "Kind": (rule.get("kind") or "Other")[:40],
                          "Value": str(rule["value"]) if rule.get("value") is not None else None, "Text": (rule.get("text") or "")[:1000],
                          "SourceExcerpt": ((rule.get("source") or {}).get("excerpt") or "")[:500]}
                    if ex:
                        unified_db.update(conn, "DonorRules", "DonorRule", ex["Id"], rv)
                    else:
                        unified_db.insert(conn, "DonorRules", "DonorRule", {**rv, "IsDeleted": 0})
                    count("règles du bailleur")

        # Budget (dans la devise du bailleur, codes et rubriques du bailleur)
        line_ids: Dict[int, int] = {}
        if "budget" in sections and budget.get("lines"):
            for i, l in enumerate(budget["lines"]):
                code = (l.get("code") or f"L{i + 1:02d}")[:30]
                lv = {"ProjectId": project_id, "FundingAgreementId": agreement_id, "FiscalYearId": None, "Code": code, "Label": (l.get("label") or "")[:250],
                      "CategoryId": None, "PlannedMinor": max(0, _minor(l.get("total"))), "Currency": b_cur,
                      "DonorCategory": (l.get("category") or "")[:150], "ActivityCode": (l.get("activity_code") or "")[:30], "SortOrder": i + 1}
                ex = conn.execute("SELECT Id FROM BudgetLines WHERE ProjectId = ? AND Code = ? AND Label = ? AND IsDeleted = 0",
                                  (project_id, code, lv["Label"])).fetchone()
                if ex:
                    unified_db.update(conn, "BudgetLines", "BudgetLine", ex["Id"], lv)
                    line_ids[i] = ex["Id"]
                else:
                    line_ids[i] = unified_db.insert(conn, "BudgetLines", "BudgetLine", {**lv, "IsDeleted": 0})
                count("lignes budgétaires")

        # Cofinancement : une contribution par ligne et par cofinanceur
        if "cofinancing" in sections and budget.get("lines") and budget.get("sources"):
            grant_cols = [c for c in budget["sources"] if re.search(r"subvention|grant|pmf|bailleur principal", c, re.I)]
            types = {c.get("source_name"): c for c in r.get("cofinancing") or []}
            for i, l in enumerate(budget["lines"]):
                for col, amount in (l.get("by_source") or {}).items():
                    if col in grant_cols or not amount:
                        continue
                    meta = types.get(col, {})
                    nature = meta.get("nature") if meta.get("nature") in ("Espèces", "Nature") else ("Nature" if re.search(r"nature", col, re.I) else "Espèces")
                    cv = {"ProjectId": project_id, "FundingAgreementId": agreement_id, "BudgetLineId": line_ids.get(i),
                          "SourceType": (meta.get("source_type") or "Association")[:30], "SourceName": col[:150], "Nature": nature,
                          "Description": f"{l.get('code') or ''} {l.get('label') or ''}".strip()[:500], "PlannedMinor": _minor(amount),
                          "Currency": b_cur, "Commitment": (meta.get("commitment") or "Prévu")[:10]}
                    ex = conn.execute("SELECT Id FROM CofinancingContributions WHERE ProjectId = ? AND SourceName = ? AND BudgetLineId IS ? AND IsDeleted = 0",
                                      (project_id, cv["SourceName"], cv["BudgetLineId"])).fetchone()
                    if ex:
                        unified_db.update(conn, "CofinancingContributions", "CofinancingContribution", ex["Id"], cv)
                    else:
                        unified_db.insert(conn, "CofinancingContributions", "CofinancingContribution", {**cv, "IsDeleted": 0})
                    count("contributions de cofinancement")

        # Activités → tâches du planning (code du bailleur conservé)
        if "activities" in sections:
            act_budget: Dict[str, float] = {}
            for l in budget.get("lines") or []:
                if l.get("activity_code"):
                    act_budget[l["activity_code"]] = act_budget.get(l["activity_code"], 0) + float(l.get("total") or 0)
            for a in r.get("activities") or []:
                if not a.get("title"):
                    continue
                code = (a.get("code") or "")[:30]
                tv = {"ProjectId": project_id, "Code": code, "Name": f"{code} — {a['title']}"[:250] if code else a["title"][:250],
                      "Description": "", "Assignee": (a.get("responsible") or "")[:150],
                      "TargetStartDate": _ef_dt(a.get("start")), "TargetEndDate": _ef_dt(a.get("end")),
                      "Budget": str(round(act_budget.get(code, 0.0), 2))}
                ex = conn.execute("SELECT Id FROM Tasks WHERE ProjectId = ? AND Code = ? AND Code <> ''", (project_id, code)).fetchone() if code else None
                if ex:
                    unified_db.update(conn, "Tasks", "ProjectTask", ex["Id"], tv)
                else:
                    unified_db.insert(conn, "Tasks", "ProjectTask", {**tv, "ParentTaskId": None, "ActualStartDate": None, "ActualEndDate": None,
                                                                     "ProgressPercentage": 0.0, "Status": "À faire", "Cost": "0", "Predecessors": ""})
                count("activités")

        # Cadre logique et indicateurs
        node_ids: Dict[str, int] = {}
        if "logframe" in sections:
            levels = {"Objectif global", "Objectif spécifique", "Résultat", "Produit"}
            for i, n in enumerate(r.get("logframe") or []):
                if not n.get("statement") or n.get("level") not in levels:
                    continue
                parent = node_ids.get(n.get("parent_code") or "")
                nv = {"ProjectId": project_id, "ParentId": parent, "Level": n["level"], "Code": (n.get("code") or "")[:30],
                      "Statement": n["statement"][:2000], "SortOrder": i + 1}
                ex = conn.execute("SELECT Id FROM LogframeNodes WHERE ProjectId = ? AND Code = ? AND IsDeleted = 0", (project_id, nv["Code"])).fetchone() if nv["Code"] else None
                if ex:
                    unified_db.update(conn, "LogframeNodes", "LogframeNode", ex["Id"], nv)
                    node_ids[nv["Code"]] = ex["Id"]
                else:
                    node_ids[nv["Code"]] = unified_db.insert(conn, "LogframeNodes", "LogframeNode", {**nv, "IsDeleted": 0})
                count("éléments du cadre logique")
        else:
            for row in conn.execute("SELECT Id, Code FROM LogframeNodes WHERE ProjectId = ? AND IsDeleted = 0", (project_id,)):
                node_ids[row["Code"]] = row["Id"]
        if "indicators" in sections:
            for ind in r.get("indicators") or []:
                if not ind.get("name"):
                    continue
                node = node_ids.get(ind.get("result_code") or "")
                level = "Effet" if (ind.get("result_code") or "").startswith(("R", "C", "OS")) else "Extrant"
                iv = {"Name": ind["name"][:250], "Description": "", "TargetValue": float(ind.get("target") or 0), "Unit": (ind.get("unit") or "")[:50],
                      "ProjectId": project_id, "BaselineValue": ind.get("baseline"), "Level": level, "Code": (ind.get("code") or "")[:30],
                      "MeansOfVerification": (ind.get("verification") or "")[:1000], "LogframeNodeId": node}
                ex = conn.execute("SELECT Id FROM Indicators WHERE ProjectId = ? AND (Name = ? OR (Code = ? AND Code <> ''))",
                                  (project_id, iv["Name"], iv["Code"])).fetchone()
                if ex:
                    unified_db.update(conn, "Indicators", "Indicator", ex["Id"], iv)
                else:
                    unified_db.insert(conn, "Indicators", "Indicator", {**iv, "CurrentValue": 0.0, "Aggregation": "Somme"})
                count("indicateurs")

        # Rapports dus au bailleur → obligations (alertes, frise de la GED)
        if "reports" in sections:
            for rep in r.get("reports") or []:
                if not rep.get("title"):
                    continue
                due = (rep.get("due") or _value(p.get("end")) or date.today().isoformat())[:10]
                ex = conn.execute("SELECT Id FROM ReportingObligations WHERE ProjectId = ? AND Title = ? AND IsDeleted = 0", (project_id, rep["title"][:250])).fetchone()
                ov = {"ProjectId": project_id, "FundingAgreementId": agreement_id, "Title": rep["title"][:250], "Kind": (rep.get("kind") or "Rapport")[:50],
                      "DueDate": due, "Notes": (rep.get("note") or "")[:500], "SourceExcerpt": ((rep.get("source") or {}).get("excerpt") or "")[:500]}
                if ex:
                    unified_db.update(conn, "ReportingObligations", "ReportingObligation", ex["Id"], ov)
                else:
                    unified_db.insert(conn, "ReportingObligations", "ReportingObligation", {**ov, "Status": "À venir", "DeliveredDocumentId": None,
                                                                                            "SourceDocumentId": None, "IsDeleted": 0})
                count("rapports à remettre")

        if "risks" in sections:
            for rk in r.get("risks") or []:
                if not rk.get("description"):
                    continue
                ex = conn.execute("SELECT Id FROM ProjectRisks WHERE ProjectId = ? AND Description = ? AND IsDeleted = 0", (project_id, rk["description"][:2000])).fetchone()
                rv = {"ProjectId": project_id, "Description": rk["description"][:2000], "Probability": (rk.get("probability") or "")[:20],
                      "Impact": (rk.get("impact") or "")[:20], "Mitigation": (rk.get("mitigation") or "")[:2000], "Owner": "", "Status": "Ouvert"}
                if ex:
                    unified_db.update(conn, "ProjectRisks", "ProjectRisk", ex["Id"], rv)
                else:
                    unified_db.insert(conn, "ProjectRisks", "ProjectRisk", {**rv, "IsDeleted": 0})
                count("risques")

    # Pièces du dossier → GED du projet (et dossiers locaux), sans doublon (empreinte)
    if "documents" in sections:
        from backend.tools.ged import service as ged
        d = _dir(import_id)
        for fi in imp["files"]:
            path = d / Path(fi["name"]).name
            if not path.exists():
                continue
            n = fi["name"]
            dtype = ("Avenant" if re.search(r"amendment|avenant", n, re.I) else "Convention" if re.search(r"accord|convention|agreement|\bloa\b|lgv", n, re.I)
                     else "Budget" if re.search(r"budget", n, re.I) or n.lower().endswith((".xlsx", ".xlsm")) else "Document de projet")
            try:
                res = await ged.import_document(project_id, path.read_bytes(), n, doc_type=dtype)
                doc = res.get("document") or {}
                if doc.get("id"):
                    count("documents archivés")
                    if "reports" in sections:
                        # les échéances viennent déjà du dossier : pas de propositions en double
                        with unified_db.connect() as conn:
                            for o in conn.execute("SELECT Id FROM ReportingObligations WHERE SourceDocumentId = ? AND Status = 'Proposée' AND IsDeleted = 0",
                                                  (doc["id"],)).fetchall():
                                unified_db.soft_delete(conn, "ReportingObligations", "ReportingObligation", o["Id"])
            except Exception as e:  # noqa: BLE001 — doublon déjà archivé, format non indexable…
                if "déjà" in str(e).lower():
                    count("documents déjà archivés")
    text = ", ".join(f"{n} {k}" for k, n in summary.items()) or "rien à appliquer"
    with unified_db.connect() as conn:
        unified_db.update(conn, "ProjectImports", "ProjectImport", import_id, {"Status": "Appliqué", "AppliedAtUtc": unified_db.now_ef(),
                                                                               "AppliedSummary": text[:1000], "ProjectId": project_id})
    return {"project_id": project_id, "summary": summary, "text": text}


def cofinancing(project_id: int) -> Dict[str, Any]:
    """Tableau de suivi du cofinancement : prévu, réalisé, par cofinanceur et par nature ; traitement du bailleur."""
    with unified_db.connect() as conn:
        rows = conn.execute(
            "SELECT c.*, b.Code AS LineCode, b.Label AS LineLabel, COALESCE((SELECT SUM(AmountMinor) FROM CofinancingEntries e "
            "WHERE e.ContributionId = c.Id AND e.IsDeleted = 0), 0) AS RealizedMinor FROM CofinancingContributions c "
            "LEFT JOIN BudgetLines b ON b.Id = c.BudgetLineId WHERE c.ProjectId = ? AND c.IsDeleted = 0 ORDER BY c.SourceName, b.SortOrder",
            (project_id,)).fetchall()
        treat = conn.execute("SELECT f.Name, f.InKindTreatment FROM Projects p LEFT JOIN Funders f ON f.Id = p.FunderId WHERE p.Id = ?",
                             (project_id,)).fetchone()
    by_source: Dict[str, Dict[str, Any]] = {}
    items = []
    for c in rows:
        it = {"id": c["Id"], "source_type": c["SourceType"], "source_name": c["SourceName"], "nature": c["Nature"], "line": f"{c['LineCode'] or ''} {c['LineLabel'] or ''}".strip(),
              "planned": c["PlannedMinor"] / 100, "realized": c["RealizedMinor"] / 100, "currency": c["Currency"], "commitment": c["Commitment"]}
        items.append(it)
        s = by_source.setdefault(c["SourceName"], {"source_name": c["SourceName"], "source_type": c["SourceType"], "planned": 0.0, "realized": 0.0, "currency": c["Currency"]})
        s["planned"] += it["planned"]
        s["realized"] += it["realized"]
    return {"items": items, "by_source": list(by_source.values()), "funder": treat["Name"] if treat else None,
            "in_kind_treatment": (treat["InKindTreatment"] if treat and treat["InKindTreatment"] else "Suivi")}


def add_cofinancing_entry(contribution_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """Réalisation d'une contribution. En mode « Comptabilité », un justificatif est exigé (écriture de valorisation)."""
    amount = float(data.get("amount") or 0)
    if amount <= 0:
        raise DossierError("Montant positif requis.")
    try:
        day = date.fromisoformat(str(data.get("date"))[:10])
    except ValueError:
        raise DossierError("Date invalide (AAAA-MM-JJ).")
    with unified_db.connect() as conn:
        c = conn.execute("SELECT c.*, f.InKindTreatment FROM CofinancingContributions c JOIN Projects p ON p.Id = c.ProjectId "
                         "LEFT JOIN Funders f ON f.Id = p.FunderId WHERE c.Id = ? AND c.IsDeleted = 0", (contribution_id,)).fetchone()
        if c is None:
            raise DossierError("Contribution introuvable.")
        if c["Nature"] == "Nature" and (c["InKindTreatment"] or "Suivi") == "Comptabilité" and not (data.get("evidence") or "").strip():
            raise DossierError("Ce bailleur demande la comptabilisation des contributions en nature : indiquez le justificatif "
                               "(feuille de présence, attestation, convention de mise à disposition…).")
        eid = unified_db.insert(conn, "CofinancingEntries", "CofinancingEntry", {
            "ContributionId": contribution_id, "Date": day.isoformat(), "AmountMinor": _minor(amount),
            "Description": (data.get("description") or "")[:1000], "Evidence": (data.get("evidence") or "")[:1000],
            "CreatedBy": unified_db.current_user(), "CreatedAtUtc": unified_db.now_ef(), "IsDeleted": 0})
    return {"id": eid}


def in_kind_journal(project_id: int) -> List[Dict[str, Any]]:
    """Écritures de valorisation des contributions en nature (bailleurs en mode « Comptabilité ») : une ligne d'emploi
    et une ligne de ressource de même montant, sans effet sur le résultat ni sur la trésorerie. Les numéros de comptes
    sont ceux des paramètres (à confirmer par le comptable)."""
    acc_use = unified_db.get_setting("cofinancing.account_use", "86 — Emplois des contributions volontaires en nature")
    acc_src = unified_db.get_setting("cofinancing.account_source", "87 — Contributions volontaires en nature")
    with unified_db.connect() as conn:
        rows = conn.execute(
            "SELECT e.*, c.SourceName, c.Currency, b.Code AS LineCode FROM CofinancingEntries e JOIN CofinancingContributions c ON c.Id = e.ContributionId "
            "JOIN Projects p ON p.Id = c.ProjectId LEFT JOIN Funders f ON f.Id = p.FunderId LEFT JOIN BudgetLines b ON b.Id = c.BudgetLineId "
            "WHERE c.ProjectId = ? AND c.Nature = 'Nature' AND COALESCE(f.InKindTreatment, 'Suivi') = 'Comptabilité' "
            "AND e.IsDeleted = 0 AND c.IsDeleted = 0 ORDER BY e.Date", (project_id,)).fetchall()
    out = []
    for e in rows:
        label = f"{e['SourceName']} — {e['Description']}".strip(" —")
        out.append({"date": e["Date"], "account": acc_use, "label": label, "debit": e["AmountMinor"] / 100, "credit": 0, "line": e["LineCode"], "evidence": e["Evidence"]})
        out.append({"date": e["Date"], "account": acc_src, "label": label, "debit": 0, "credit": e["AmountMinor"] / 100, "line": e["LineCode"], "evidence": e["Evidence"]})
    return out
