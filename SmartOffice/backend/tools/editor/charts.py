"""Chartes graphiques et leur héritage : association ← bailleur ← projet.

Une charte ne contient que ce qu'elle change. La charte effective d'un document est la fusion, dans l'ordre :
valeurs par défaut, charte de l'association, réglages saisis sur la fiche du bailleur (couleur, mentions, en-tête,
pied de page), charte du bailleur, charte du projet. Dictionnaires : fusion clé par clé ; logos : remplacés position
par position ; mentions obligatoires : cumulées sans doublon.
"""
import copy
import json
from typing import Any, Dict, List, Optional

from backend.core import unified_db

DEFAULT_STYLE: Dict[str, Any] = {
    "colors": {"primary": "#1B4332", "secondary": "#D4A373", "text": "#1F2937", "muted": "#6B7280"},
    "fonts": {"body": "Calibri", "headings": "Calibri", "size_pt": 11, "arabic": "Amiri"},   # Amiri : installée avec l'application
    "margins_mm": {"top": 25, "bottom": 22, "left": 20, "right": 20},
    "logos": [],                       # [{"file_id": 3, "position": "header-left", "height_mm": 14}]
    "header": {"text": "", "first_page_text": "", "even_text": ""},
    "footer": {"text": "", "page_numbers": True, "first_page_different": True, "odd_even_different": False},
    "mentions": [],
    "table": {"header_bg": "#1B4332", "header_color": "#FFFFFF", "border_color": "#CBD5E1", "stripe": "#F8F9FA"},
    "photo_grid": {"per_row": 2},
    "heading_numbering": False,
}
LOGO_POSITIONS = ["header-left", "header-center", "header-right", "footer-left", "footer-center", "footer-right", "cover"]


def merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if value is None or value == "":
            continue
        if key == "logos":
            by_pos = {l.get("position"): l for l in out.get("logos", [])}
            for logo in value:
                by_pos[logo.get("position")] = logo
            out["logos"] = [l for l in by_pos.values() if l.get("file_id") is not None]
        elif key == "mentions":
            out["mentions"] = list(dict.fromkeys([*out.get("mentions", []), *[m for m in value if m]]))
        elif isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = merge(out[key], value)
        else:
            out[key] = value
    return out


def _row(r) -> Dict[str, Any]:
    return {"id": r["Id"], "name": r["Name"], "scope": r["Scope"], "funder_id": r["FunderId"], "project_id": r["ProjectId"],
            "style": json.loads(r["StyleJson"] or "{}"), "updated_at": r["UpdatedAtUtc"]}


def ensure_association_chart(conn) -> int:
    row = conn.execute("SELECT Id FROM GraphicCharts WHERE Scope = 'Association' AND IsDeleted = 0 ORDER BY Id LIMIT 1").fetchone()
    if row:
        return row["Id"]
    return unified_db.insert(conn, "GraphicCharts", "GraphicChart", {
        "Name": "Charte AFMI", "Scope": "Association", "FunderId": None, "ProjectId": None,
        "StyleJson": json.dumps({"colors": DEFAULT_STYLE["colors"]}), "UpdatedAtUtc": unified_db.now_ef(), "IsDeleted": 0})


def list_charts() -> List[Dict[str, Any]]:
    with unified_db.connect() as conn:
        ensure_association_chart(conn)
        return [_row(r) for r in conn.execute(
            "SELECT * FROM GraphicCharts WHERE IsDeleted = 0 ORDER BY CASE Scope WHEN 'Association' THEN 0 WHEN 'Funder' THEN 1 ELSE 2 END, Name")]


def save_chart(data: Dict[str, Any]) -> Dict[str, Any]:
    scope = data.get("scope", "Project")
    if scope not in ("Association", "Funder", "Project"):
        raise ValueError("Portée de charte inconnue.")
    values = {
        "Name": (data.get("name") or "Charte").strip()[:150], "Scope": scope,
        "FunderId": data.get("funder_id") if scope == "Funder" else None,
        "ProjectId": data.get("project_id") if scope == "Project" else None,
        "StyleJson": json.dumps(data.get("style") or {}, ensure_ascii=False), "UpdatedAtUtc": unified_db.now_ef(),
    }
    for logo in (data.get("style") or {}).get("logos", []):
        if logo.get("position") not in LOGO_POSITIONS:
            raise ValueError(f"Position de logo inconnue : {logo.get('position')}.")
    with unified_db.connect() as conn:
        if scope != "Association":
            column = "FunderId" if scope == "Funder" else "ProjectId"
            clash = conn.execute(f"SELECT Id FROM GraphicCharts WHERE Scope = ? AND {column} = ? AND IsDeleted = 0 AND Id <> ?",
                                 (scope, values[column], data.get("id") or 0)).fetchone()
            if clash:
                raise ValueError("Une charte existe déjà pour ce bailleur ou ce projet : modifiez-la.")
        if data.get("id"):
            unified_db.update(conn, "GraphicCharts", "GraphicChart", data["id"], values)
            chart_id = data["id"]
        else:
            chart_id = unified_db.insert(conn, "GraphicCharts", "GraphicChart", {**values, "IsDeleted": 0})
        return _row(conn.execute("SELECT * FROM GraphicCharts WHERE Id = ?", (chart_id,)).fetchone())


def delete_chart(chart_id: int) -> None:
    with unified_db.connect() as conn:
        row = conn.execute("SELECT Scope FROM GraphicCharts WHERE Id = ?", (chart_id,)).fetchone()
        if row and row["Scope"] == "Association":
            raise ValueError("La charte de l'association ne peut pas être supprimée (c'est la charte par défaut).")
        unified_db.soft_delete(conn, "GraphicCharts", "GraphicChart", chart_id)


def _funder_card(funder) -> Dict[str, Any]:
    """Réglages saisis sur la fiche du bailleur (application de bureau), traduits en charte."""
    style: Dict[str, Any] = {}
    if funder["PrimaryColor"] and funder["PrimaryColor"] != "#000000":
        style["colors"] = {"primary": funder["PrimaryColor"]}
    if funder["LegalMentions"]:
        style["mentions"] = [funder["LegalMentions"]]
    if funder["HeaderText"]:
        style["header"] = {"text": funder["HeaderText"]}
    if funder["FooterText"]:
        style["footer"] = {"text": funder["FooterText"]}
    if funder["LogoPath"]:
        style["logos"] = [{"funder_logo": funder["Id"], "file_id": f"funder:{funder['Id']}", "position": "header-right", "height_mm": 14}]
    return style


def effective(project_id: Optional[int] = None, funder_id: Optional[int] = None) -> Dict[str, Any]:
    """Charte effective et chaîne d'héritage appliquée (pour l'afficher à l'utilisateur)."""
    with unified_db.connect() as conn:
        ensure_association_chart(conn)
        chain = ["Valeurs par défaut"]
        style = copy.deepcopy(DEFAULT_STYLE)
        assoc = conn.execute("SELECT * FROM GraphicCharts WHERE Scope = 'Association' AND IsDeleted = 0 ORDER BY Id LIMIT 1").fetchone()
        style = merge(style, json.loads(assoc["StyleJson"] or "{}"))
        chain.append(assoc["Name"])
        project = None
        if project_id:
            project = conn.execute("SELECT * FROM Projects WHERE Id = ?", (project_id,)).fetchone()
            if project is not None and not funder_id:
                funder_id = project["FunderId"]
        if funder_id:
            funder = conn.execute("SELECT * FROM Funders WHERE Id = ?", (funder_id,)).fetchone()
            if funder is not None:
                style = merge(style, _funder_card(funder))
                chain.append(f"Fiche bailleur : {funder['Name']}")
                fc = conn.execute("SELECT * FROM GraphicCharts WHERE Scope = 'Funder' AND FunderId = ? AND IsDeleted = 0", (funder_id,)).fetchone()
                if fc:
                    style = merge(style, json.loads(fc["StyleJson"] or "{}"))
                    chain.append(fc["Name"])
        if project is not None:
            pc = conn.execute("SELECT * FROM GraphicCharts WHERE Scope = 'Project' AND ProjectId = ? AND IsDeleted = 0", (project_id,)).fetchone()
            if pc:
                style = merge(style, json.loads(pc["StyleJson"] or "{}"))
                chain.append(pc["Name"])
        return {"style": style, "chain": chain}
