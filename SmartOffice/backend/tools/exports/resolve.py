"""Préparation d'un document de l'éditeur pour l'export.

Le JSON TipTap est parcouru et chaque bloc dynamique est recalculé depuis la base (comme « Actualiser » dans
l'éditeur), puis remplacé par un nœud neutre que les rendus Word et HTML savent dessiner :

- ``x-table`` : tableau générique (colonnes, lignes, total, formats par colonne : text, money, number, percent) ;
- ``x-bars`` / ``x-pies`` : séries d'un graphique en barres ou de camemberts ;
- ``x-gallery`` : photos (fichier local, légende, crédit) ;
- ``x-note`` : message (données indisponibles…).

Les champs (date, projet, bailleur…) sont remplacés par leur valeur, sauf ``page`` et ``pages`` qui deviennent des
champs de mise en page. La version exportée est la version finale : suppressions en révision retirées, ajouts
acceptés, commentaires retirés (comme l'impression).
"""
import base64
import copy
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.config.settings import settings
from backend.core import unified_db
from backend.tools.editor import blocks, charts, documents, photos
from backend.tools.reports import generator


class ExportError(ValueError):
    pass


def _money_table(title: str, columns: List[str], rows: List[List[Any]], total: Optional[List[Any]], formats: List[str],
                 source: str = "", notes: Optional[List[str]] = None) -> Dict[str, Any]:
    return {"type": "x-table", "data": {"title": title, "columns": columns, "rows": rows, "total": total, "formats": formats,
                                         "notes": notes or [], "source": source}}


def _block(attrs: Dict[str, Any], doc_project: Optional[int]) -> List[Dict[str, Any]]:
    kind = attrs.get("kind") or "budget"
    project_id = attrs.get("projectId") or doc_project
    if kind == "annual":
        data = generator.table(attrs.get("table"), int(attrs.get("year")), attrs.get("scopeType") or "association",
                               attrs.get("scopeId"), attrs.get("lang") or "fr")
        if data.get("pies") is not None:
            return [{"type": "x-pies", "data": data}]
        out = [{"type": "x-table", "data": data}]
        if (data.get("chart") or {}).get("type") == "bars":
            out.append({"type": "x-bars", "data": {"title": "", "series": data["chart"]["series"],
                                                   "legend": data["chart"].get("legend"), "unit": "MAD"}})
        return out
    if kind == "budget":
        d = blocks.budget_table(project_id)
        rows = [[f"{r['code']} {r['label']}".strip() + ("" if r["currency"] == "MAD" else f" ({r['currency']})"),
                 r["planned"], r["realized_mad"], r["gap"], r["rate"]] for r in d["rows"]]
        t = d["total"]
        return [_money_table(f"Exécution budgétaire — {d['project']}", ["Ligne", "Prévu", "Réalisé (MAD)", "Écart", "Taux"], rows,
                             ["Total", t["planned"], t["realized_mad"], t["gap"], t["rate"]], ["text", "money", "money", "money", "percent"],
                             d["source"])]
    if kind == "indicators":
        d = blocks.indicators(project_id)
        rows = [[r["name"] + (f" ({r['unit']})" if r["unit"] else ""), r["target"], r["current"], r["rate"]] for r in d["rows"]]
        return [_money_table("Indicateurs", ["Indicateur", "Cible", "Réalisé", "Taux"], rows, None,
                             ["text", "number", "number", "percent"], d["source"])]
    if kind == "activities":
        d = blocks.activities(project_id, attrs.get("dateFrom"), attrs.get("dateTo"))
        rows = [[r["date"], r["title"], r["location"], r["participants"]] for r in d["rows"]]
        return [_money_table("Activités", ["Date", "Activité", "Lieu", "Participants"], rows,
                             ["Total des participants", None, None, d["total_participants"]], ["text", "text", "text", "number"], d["source"])]
    if kind == "chart":
        d = blocks.chart(project_id, attrs.get("chart") or "budget")
        return [{"type": "x-bars", "data": {"title": attrs.get("title") or d["title"], "series": d["series"], "unit": d["unit"]}}]
    if kind == "gallery":
        ids = attrs.get("photoIds") or []
        if ids:
            chosen = [p for p in photos.list_photos(project_id) if p["id"] in ids]
            chosen.sort(key=lambda p: ids.index(p["id"]))
        elif project_id:
            chosen = photos.select_for_report(project_id, attrs.get("dateFrom"), attrs.get("dateTo"), None,
                                              max(1, min(int(attrs.get("limit") or 6), 24)))
        else:
            chosen = []
        items = []
        for p in chosen:
            try:
                path = photos.web_version(p["id"])
            except Exception:
                continue
            items.append({"path": str(path), "caption": p["caption"] or "", "credit": p["credit"] or "", "width": p["width"], "height": p["height"]})
        return [{"type": "x-gallery", "data": {"title": attrs.get("title") or "", "photos": items, "per_row": attrs.get("perRow")}}]
    return [{"type": "x-note", "text": f"Bloc inconnu : {kind}."}]


_FILE_URL = re.compile(r"/api/files/(\d+)/image")
_PHOTO_URL = re.compile(r"/api/photos/(\d+)/image")
_FUNDER_URL = re.compile(r"/api/funders/(\d+)/logo")


def image_path(src: str, tmp_dir: Path) -> Optional[Path]:
    """Fichier local d'une image de l'éditeur. Aucun téléchargement externe (local-first) : une image distante est ignorée."""
    if not src:
        return None
    if src.startswith("data:image/"):
        header, _, data = src.partition(",")
        ext = header.split("/")[1].split(";")[0].replace("jpeg", "jpg")
        target = tmp_dir / f"inline_{abs(hash(data)) % 10**10}.{ext}"
        target.write_bytes(base64.b64decode(data))
        return target
    m = _FILE_URL.search(src)
    if m:
        with unified_db.connect() as conn:
            r = conn.execute("SELECT RelativePath, MimeType FROM StoredFiles WHERE Id = ?", (int(m.group(1)),)).fetchone()
        if r is None or not str(r["MimeType"]).startswith("image/"):
            return None
        p = (settings.data_dir / r["RelativePath"]).resolve()
        return p if p.is_relative_to(settings.data_dir.resolve()) and p.exists() else None
    m = _PHOTO_URL.search(src)
    if m:
        try:
            return photos.web_version(int(m.group(1)))
        except Exception:
            return None
    m = _FUNDER_URL.search(src)
    if m:
        with unified_db.connect() as conn:
            r = conn.execute("SELECT LogoPath FROM Funders WHERE Id = ?", (int(m.group(1)),)).fetchone()
        p = Path(r["LogoPath"]) if r and r["LogoPath"] else None
        return p if p and p.is_file() else None
    return None


def logo_path(logo: Dict[str, Any], tmp_dir: Path) -> Optional[Path]:
    if logo.get("funder_logo"):
        return image_path(f"/api/funders/{logo['funder_logo']}/logo", tmp_dir)
    if logo.get("file_id") is not None:
        return image_path(f"/api/files/{logo['file_id']}/image", tmp_dir)
    return None


def _final_text(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for n in nodes:
        marks = n.get("marks") or []
        if any(m.get("type") == "deletion" for m in marks):
            continue
        n = dict(n)
        if marks:
            n["marks"] = [m for m in marks if m.get("type") not in ("insertion", "comment")]
        out.append(n)
    return out


def _walk(nodes: List[Dict[str, Any]], ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for node in nodes or []:
        t = node.get("type")
        if t == "dynamicBlock":
            try:
                out += _block(node.get("attrs") or {}, ctx["project_id"])
            except Exception as e:  # un bloc en erreur ne bloque pas l'export : il est signalé dans le document
                out.append({"type": "x-note", "text": f"Données indisponibles : {e}"})
            continue
        if t == "field":
            name = (node.get("attrs") or {}).get("name") or "date"
            if name in ("page", "pages"):
                out.append({"type": "x-field", "name": name})
            else:
                out.append({"type": "text", "text": str(ctx["fields"].get(name, "")), "marks": node.get("marks") or []})
            continue
        if t == "heading":
            text = "".join(c.get("text", "") for c in _final_text(node.get("content") or []) if c.get("type") == "text")
            ctx["headings"].append({"level": (node.get("attrs") or {}).get("level", 1), "text": text})
        node = dict(node)
        if "content" in node:
            children = _final_text(node["content"]) if t in ("paragraph", "heading") else node["content"]
            node["content"] = _walk(children, ctx)
        out.append(node)
    return out


def prepare(doc_id: int) -> Dict[str, Any]:
    """Document prêt à rendre : contenu résolu, charte effective fusionnée avec la mise en page, champs, titres."""
    doc = documents.get_document(doc_id)
    return prepare_content(doc)


def prepare_content(doc: Dict[str, Any]) -> Dict[str, Any]:
    eff = charts.effective(doc.get("project_id"), doc.get("funder_id"))
    style = charts.merge(eff["style"], doc.get("layout") or {})
    fields = blocks.fields(doc.get("project_id"), doc.get("funder_id"))
    ctx = {"project_id": doc.get("project_id"), "fields": fields, "headings": []}
    content = _walk(copy.deepcopy((doc.get("content") or {}).get("content") or []), ctx)
    return {"id": doc.get("id"), "title": doc.get("title") or "Document", "language": doc.get("language") or "fr",
            "project_id": doc.get("project_id"), "style": style, "fields": fields, "content": content, "headings": ctx["headings"],
            "chain": eff["chain"]}


def fmt_number(value: Any, fmt: str) -> str:
    """Mise en forme française des cellules (comme GenericTable) : 1 234,56 ; 12,5 %."""
    if value is None:
        return "—" if fmt == "percent" else ""
    if isinstance(value, str):
        return value
    if fmt == "money":
        s = f"{value / 100:,.2f}"
    elif fmt == "percent":
        s = f"{value:,.1f}".rstrip("0").rstrip(".") + " %"
    else:
        s = f"{value:,.2f}".rstrip("0").rstrip(".") if isinstance(value, float) else f"{value:,}"
    return s.replace(",", " ").replace(".", ",")


def split_label(text: Any) -> tuple:
    """(libellé, retrait, gras) d'une cellule de libellé (« **sous-total** », détail indenté)."""
    if not isinstance(text, str):
        return ("" if text is None else str(text)), 0, False
    indent = len(text) - len(text.lstrip())
    clean = text.strip()
    bold = clean.startswith("**") and clean.endswith("**") and len(clean) >= 4
    return (clean[2:-2] if bold else clean), indent, bold
