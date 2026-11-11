"""Modèles, documents, versions et commentaires de l'éditeur."""
import json
import uuid
from typing import Any, Dict, List, Optional

from backend.core import unified_db

EMPTY_DOC = {"type": "doc", "content": [{"type": "paragraph"}]}


class EditorError(ValueError):
    pass


def _json(value: Any, default: Any) -> str:
    if value is None:
        value = default
    if isinstance(value, str):
        json.loads(value)  # valide
        return value
    return json.dumps(value, ensure_ascii=False)


# --- Modèles ---------------------------------------------------------------------------------------------

def _template(r) -> Dict[str, Any]:
    return {"id": r["Id"], "name": r["Name"], "description": r["Description"], "kind": r["Kind"], "is_shared": bool(r["IsShared"]),
            "content": json.loads(r["ContentJson"] or "{}"), "layout": json.loads(r["LayoutJson"] or "{}"),
            "created_by": r["CreatedBy"], "updated_at": r["UpdatedAtUtc"]}


def list_templates() -> List[Dict[str, Any]]:
    with unified_db.connect() as conn:
        return [{k: v for k, v in _template(r).items() if k != "content"}
                for r in conn.execute("SELECT * FROM DocumentTemplates WHERE IsDeleted = 0 ORDER BY Kind, Name")]


def get_template(template_id: int) -> Dict[str, Any]:
    with unified_db.connect() as conn:
        r = conn.execute("SELECT * FROM DocumentTemplates WHERE Id = ? AND IsDeleted = 0", (template_id,)).fetchone()
        if r is None:
            raise EditorError("Modèle introuvable.")
        return _template(r)


def save_template(data: Dict[str, Any]) -> Dict[str, Any]:
    if not (data.get("name") or "").strip():
        raise EditorError("Nom du modèle obligatoire.")
    values = {"Name": data["name"].strip()[:200], "Description": data.get("description", ""), "Kind": (data.get("kind") or "")[:50],
              "ContentJson": _json(data.get("content"), EMPTY_DOC), "LayoutJson": _json(data.get("layout"), {}),
              "IsShared": int(bool(data.get("is_shared", True))), "UpdatedAtUtc": unified_db.now_ef()}
    with unified_db.connect() as conn:
        if data.get("id"):
            unified_db.update(conn, "DocumentTemplates", "DocumentTemplate", data["id"], values)
            tid = data["id"]
        else:
            tid = unified_db.insert(conn, "DocumentTemplates", "DocumentTemplate",
                                    {**values, "CreatedBy": unified_db.current_user(), "IsDeleted": 0})
    return get_template(tid)


def duplicate_template(template_id: int) -> Dict[str, Any]:
    t = get_template(template_id)
    return save_template({**t, "id": None, "name": f"{t['name']} (copie)"})


def delete_template(template_id: int) -> None:
    with unified_db.connect() as conn:
        unified_db.soft_delete(conn, "DocumentTemplates", "DocumentTemplate", template_id)


# --- Documents -------------------------------------------------------------------------------------------

def _document(r) -> Dict[str, Any]:
    return {"id": r["Id"], "title": r["Title"], "project_id": r["ProjectId"], "funder_id": r["FunderId"], "template_id": r["TemplateId"],
            "language": r["Language"], "content": json.loads(r["ContentJson"] or "{}"), "layout": json.loads(r["LayoutJson"] or "{}"),
            "version": r["CurrentVersion"], "status": r["Status"], "created_by": r["CreatedBy"], "updated_at": r["UpdatedAtUtc"]}


def list_documents(project_id: Optional[int] = None) -> List[Dict[str, Any]]:
    with unified_db.connect() as conn:
        sql = "SELECT * FROM EditorDocuments WHERE IsDeleted = 0"
        args: tuple = ()
        if project_id:
            sql += " AND ProjectId = ?"
            args = (project_id,)
        return [{k: v for k, v in _document(r).items() if k not in ("content",)}
                for r in conn.execute(sql + " ORDER BY UpdatedAtUtc DESC", args)]


def get_document(doc_id: int) -> Dict[str, Any]:
    with unified_db.connect() as conn:
        r = conn.execute("SELECT * FROM EditorDocuments WHERE Id = ? AND IsDeleted = 0", (doc_id,)).fetchone()
        if r is None:
            raise EditorError("Document introuvable.")
        return _document(r)


def create_document(data: Dict[str, Any]) -> Dict[str, Any]:
    """Nouveau document, vierge ou à partir d'un modèle (contenu et mise en page copiés)."""
    content, layout = EMPTY_DOC, {}
    if data.get("template_id"):
        t = get_template(data["template_id"])
        content, layout = t["content"], t["layout"]
    if data.get("content"):
        content = data["content"]
    language = data.get("language", "fr")
    if language not in ("fr", "ar", "en"):
        raise EditorError("Langue : fr, ar ou en.")
    now = unified_db.now_ef()
    with unified_db.connect() as conn:
        doc_id = unified_db.insert(conn, "EditorDocuments", "EditorDocument", {
            "Title": (data.get("title") or "Document sans titre").strip()[:250], "ProjectId": data.get("project_id"),
            "FunderId": data.get("funder_id"), "TemplateId": data.get("template_id"), "Language": language,
            "ContentJson": _json(content, EMPTY_DOC), "LayoutJson": _json(layout, {}), "CurrentVersion": 0,
            "Status": "Brouillon", "CreatedBy": unified_db.current_user(), "CreatedAtUtc": now, "UpdatedAtUtc": now, "IsDeleted": 0})
    return get_document(doc_id)


def save_document(doc_id: int, data: Dict[str, Any], version_note: Optional[str] = None) -> Dict[str, Any]:
    """Enregistre le document ; avec une note, crée aussi une version (instantané restaurable)."""
    current = get_document(doc_id)
    values = {"UpdatedAtUtc": unified_db.now_ef()}
    for key, col in (("title", "Title"), ("project_id", "ProjectId"), ("funder_id", "FunderId"), ("language", "Language"), ("status", "Status")):
        if key in data:
            values[col] = data[key]
    if "content" in data:
        values["ContentJson"] = _json(data["content"], EMPTY_DOC)
    if "layout" in data:
        values["LayoutJson"] = _json(data["layout"], {})
    with unified_db.connect() as conn:
        if version_note is not None:
            number = current["version"] + 1
            unified_db.insert(conn, "DocumentVersions", "DocumentVersion", {
                "EditorDocumentId": doc_id, "Number": number,
                "ContentJson": values.get("ContentJson", json.dumps(current["content"], ensure_ascii=False)),
                "LayoutJson": values.get("LayoutJson", json.dumps(current["layout"], ensure_ascii=False)),
                "Note": version_note[:300], "CreatedBy": unified_db.current_user(), "CreatedAtUtc": unified_db.now_ef()})
            values["CurrentVersion"] = number
        unified_db.update(conn, "EditorDocuments", "EditorDocument", doc_id, values)
    return get_document(doc_id)


def list_versions(doc_id: int) -> List[Dict[str, Any]]:
    with unified_db.connect() as conn:
        return [{"id": r["Id"], "number": r["Number"], "note": r["Note"], "created_by": r["CreatedBy"], "created_at": r["CreatedAtUtc"]}
                for r in conn.execute("SELECT * FROM DocumentVersions WHERE EditorDocumentId = ? ORDER BY Number DESC", (doc_id,))]


def restore_version(doc_id: int, version_id: int) -> Dict[str, Any]:
    """Restaure une version : l'état courant est d'abord conservé comme nouvelle version (rien n'est perdu)."""
    with unified_db.connect() as conn:
        v = conn.execute("SELECT * FROM DocumentVersions WHERE Id = ? AND EditorDocumentId = ?", (version_id, doc_id)).fetchone()
        if v is None:
            raise EditorError("Version introuvable.")
    save_document(doc_id, {}, version_note=f"Avant restauration de la version {v['Number']}")
    return save_document(doc_id, {"content": json.loads(v["ContentJson"]), "layout": json.loads(v["LayoutJson"])},
                         version_note=f"Restauration de la version {v['Number']}")


def delete_document(doc_id: int) -> None:
    with unified_db.connect() as conn:
        unified_db.soft_delete(conn, "EditorDocuments", "EditorDocument", doc_id)


# --- Commentaires ----------------------------------------------------------------------------------------

def _comment(r) -> Dict[str, Any]:
    return {"id": r["Id"], "anchor_id": r["AnchorId"], "parent_id": r["ParentId"], "text": r["Text"], "quoted": r["QuotedText"],
            "author": r["Author"], "created_at": r["CreatedAtUtc"], "resolved": r["ResolvedAtUtc"] is not None}


def list_comments(doc_id: int) -> List[Dict[str, Any]]:
    with unified_db.connect() as conn:
        return [_comment(r) for r in conn.execute("SELECT * FROM DocumentComments WHERE EditorDocumentId = ? ORDER BY Id", (doc_id,))]


def add_comment(doc_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    if not (data.get("text") or "").strip():
        raise EditorError("Commentaire vide.")
    get_document(doc_id)
    with unified_db.connect() as conn:
        cid = unified_db.insert(conn, "DocumentComments", "DocumentComment", {
            "EditorDocumentId": doc_id, "AnchorId": (data.get("anchor_id") or uuid.uuid4().hex[:12])[:40], "ParentId": data.get("parent_id"),
            "Text": data["text"].strip(), "QuotedText": (data.get("quoted") or "")[:300], "Author": unified_db.current_user(),
            "CreatedAtUtc": unified_db.now_ef(), "ResolvedAtUtc": None})
        return _comment(conn.execute("SELECT * FROM DocumentComments WHERE Id = ?", (cid,)).fetchone())


def resolve_comment(doc_id: int, comment_id: int, resolved: bool = True) -> Dict[str, Any]:
    with unified_db.connect() as conn:
        unified_db.update(conn, "DocumentComments", "DocumentComment", comment_id, {"ResolvedAtUtc": unified_db.now_ef() if resolved else None})
        return _comment(conn.execute("SELECT * FROM DocumentComments WHERE Id = ? AND EditorDocumentId = ?", (comment_id, doc_id)).fetchone())
