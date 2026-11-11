"""Rapport de projet (application de bureau) → document de l'éditeur (Lot 9).

Le texte produit par l'onglet Projet › Rapports (sections « === TITRE === », puces, lignes « Clé : valeur ») devient un
vrai document mis en forme, ouvert dans l'éditeur de type Word, avec en plus les blocs de données du projet (budget,
indicateurs, activités, graphique) selon le type de rapport. Régénérer le même rapport crée une nouvelle version du
document existant (l'ancienne reste restaurable) au lieu d'un doublon.
"""
import re
from typing import Any, Dict, List, Optional

from backend.core import unified_db
from . import documents

BLOCKS = {
    "Rapport d'Avancement": [("Indicateurs du projet", {"kind": "indicators"}), ("Activités réalisées", {"kind": "activities"}),
                             ("Exécution budgétaire", {"kind": "budget"})],
    "Rapport Financier": [("Exécution budgétaire", {"kind": "budget"}), ("Graphique prévu / réalisé", {"kind": "chart", "chart": "budget"})],
    "Bilan Final de Clôture": [("Indicateurs du projet", {"kind": "indicators"}), ("Activités réalisées", {"kind": "activities"}),
                               ("Exécution budgétaire", {"kind": "budget"}), ("Photos des activités", {"kind": "gallery", "limit": 6})],
    "Rapport de Conformité Bailleur": [("Exécution budgétaire", {"kind": "budget"})],
}
KNOWN_ACRONYMS = {"WBS", "EVM", "CPI", "SPI", "ONG", "AFMI", "GAR", "COPIL", "PV", "MAD", "TVA", "CNSS"}
_INLINE_BOLD = re.compile(r"\*\*(.+?)\*\*")


def _inline(text: str) -> List[Dict[str, Any]]:
    out, pos = [], 0
    for m in _INLINE_BOLD.finditer(text):
        if m.start() > pos:
            out.append({"type": "text", "text": text[pos:m.start()]})
        out.append({"type": "text", "text": m.group(1), "marks": [{"type": "bold"}]})
        pos = m.end()
    if pos < len(text):
        out.append({"type": "text", "text": text[pos:]})
    return [n for n in out if n["text"]]


def _para(text: str) -> Dict[str, Any]:
    content = _inline(text)
    return {"type": "paragraph", "content": content} if content else {"type": "paragraph"}


def _heading(level: int, text: str) -> Dict[str, Any]:
    return {"type": "heading", "attrs": {"level": level}, "content": [{"type": "text", "text": text}]}


def _pretty(title: str) -> str:
    """« SYNTHÈSE DE PERFORMANCE » → « Synthèse de performance »."""
    t = title.strip().strip("=").strip()
    if not t.isupper():
        return t
    out = t[:1].upper() + t[1:].lower()
    # Sigles conservés : ceux entre parenthèses, et les sigles usuels des rapports
    sigles = set(re.findall(r"\(([A-Z0-9]{2,8})\)", t)) | {w for w in re.findall(r"\b[A-Z]{2,6}\b", t) if w in KNOWN_ACRONYMS}
    for acronym in sigles:
        out = re.sub(rf"\b{acronym.lower()}\b", acronym, out)
    return out


def text_to_content(text: str, title: str) -> List[Dict[str, Any]]:
    nodes: List[Dict[str, Any]] = [_heading(1, title)]
    bullets: List[str] = []
    fields: List[tuple] = []

    def flush():
        nonlocal bullets, fields
        if bullets:
            nodes.append({"type": "bulletList", "content": [{"type": "listItem", "content": [_para(b)]} for b in bullets]})
            bullets = []
        if fields:
            rows = [{"type": "tableRow", "content": [
                {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": k, "marks": [{"type": "bold"}]}]}]},
                {"type": "tableCell", "content": [_para(v)]}]} for k, v in fields]
            nodes.append({"type": "table", "content": rows})
            fields = []

    lines = (text or "").replace("\r\n", "\n").split("\n")
    for i, raw in enumerate(lines):
        line = raw.strip()
        if not line or re.fullmatch(r"[-=_]{3,}", line):
            flush()
            continue
        if i == 0 and line.isupper() and len(line) < 120:
            continue                                         # titre déjà repris en Titre 1
        m = re.fullmatch(r"=+\s*(.+?)\s*=+", line)
        if m:
            flush()
            nodes.append(_heading(2, _pretty(m.group(1))))
            continue
        m = re.match(r"^[•\-\*]\s+(.*)$", line)
        if m:
            if fields:
                flush()
            bullets.append(m.group(1))
            continue
        m = re.match(r"^([^:]{2,40}?)\s+:\s+(.+)$", line)
        if m and not bullets and len(line) < 140:
            fields.append((m.group(1).strip(), m.group(2).strip()))
            continue
        flush()
        nodes.append(_para(line))
    flush()
    return nodes


def create_or_update(project_id: int, report_type: str, title: str, text: str) -> Dict[str, Any]:
    with unified_db.connect() as conn:
        project = conn.execute("SELECT Id, FunderId FROM Projects WHERE Id = ? AND IsDeleted = 0", (project_id,)).fetchone()
        if project is None:
            raise documents.EditorError("Projet introuvable.")
        existing = conn.execute("SELECT Id FROM EditorDocuments WHERE ProjectId = ? AND Title = ? AND IsDeleted = 0 ORDER BY UpdatedAtUtc DESC LIMIT 1",
                                (project_id, title)).fetchone()
    content = text_to_content(text, title)
    blocks = BLOCKS.get(report_type, [])
    if blocks:
        content.append(_heading(2, "Données du projet (mises à jour automatiquement)"))
        for label, attrs in blocks:
            content.append(_heading(3, label))
            content.append({"type": "dynamicBlock", "attrs": {**attrs, "projectId": project_id}})
    doc = {"type": "doc", "content": content}
    if existing:
        result = documents.save_document(existing["Id"], {"content": doc}, version_note=f"Régénéré depuis Projet › Rapports ({report_type})")
    else:
        result = documents.create_document({"title": title, "project_id": project_id, "funder_id": project["FunderId"], "language": "fr",
                                            "content": doc})
    return {"id": result["id"], "title": result["title"], "version": result["version"], "created": existing is None}
