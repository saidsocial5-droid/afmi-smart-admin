"""Découpage en passages, index plein texte (FTS5 par déclencheurs) et vecteurs sémantiques éventuels."""
import re
from typing import List, Optional, Tuple

import numpy as np

from backend.core import unified_db
from backend.core.llm_router import llm_router

CHUNK = 900
OVERLAP = 150


def chunk_pages(pages: List[Tuple[int, str]]) -> List[Tuple[int, str]]:
    """Passages d'environ 900 caractères, coupés en fin de phrase, avec recouvrement, page par page."""
    out = []
    for page, text in pages:
        text = re.sub(r"[ \t]+", " ", text).strip()
        i = 0
        while i < len(text):
            end = min(len(text), i + CHUNK)
            if end < len(text):
                cut = max(text.rfind(". ", i, end), text.rfind("\n", i, end))
                if cut > i + CHUNK // 2:
                    end = cut + 1
            piece = text[i:end].strip()
            if len(piece) > 20:
                out.append((page, piece))
            if end >= len(text):
                break
            i = max(end - OVERLAP, i + 1)
    return out


async def index_document(doc_id: int, pages: List[Tuple[int, str]]) -> dict:
    chunks = chunk_pages(pages)
    vectors, engine = (await llm_router.embed([c[1] for c in chunks])) if chunks else (None, "none")
    with unified_db.connect() as conn:
        conn.execute("DELETE FROM DocumentChunks WHERE DocumentId = ?", (doc_id,))
        for i, (page, text) in enumerate(chunks):
            blob = np.asarray(vectors[i], dtype=np.float32).tobytes() if vectors else None
            conn.execute("INSERT INTO DocumentChunks (DocumentId, Ordinal, Page, Text, Embedding, EmbeddingModel) VALUES (?, ?, ?, ?, ?, ?)",
                         (doc_id, i, page, text, blob, engine if vectors else ""))
        conn.execute("UPDATE Documents SET IndexedAtUtc = ? WHERE Id = ?", (unified_db.now_ef(), doc_id))
    return {"chunks": len(chunks), "embeddings": engine if vectors else None}


def _fts_query(question: str, mode: str = "AND") -> Optional[str]:
    words = [w for w in re.findall(r"[\w؀-ۿ]{3,}", question.lower()) if w not in STOP]
    if not words:
        return None
    return f" {mode} ".join(f'"{w}"*' for w in words[:12])


STOP = {"les", "des", "une", "pour", "dans", "est", "sont", "quel", "quelle", "quels", "quelles", "que", "qui", "quoi", "avec", "sur", "par",
        "aux", "the", "and", "what", "when", "comment", "combien", "doit", "elle", "ils", "nous", "vous", "leur", "cette", "ces", "son", "ses"}


def search_fts(conn, question: str, project_id: Optional[int], limit: int = 8) -> List[dict]:
    for mode in ("AND", "OR"):
        q = _fts_query(question, mode)
        if not q:
            return []
        sql = ("SELECT c.Id, c.DocumentId, c.Page, c.Text, d.Title, d.DocType, d.ProjectId, bm25(DocumentChunksFts) AS score, "
               "snippet(DocumentChunksFts, 0, '[', ']', '…', 18) AS snip FROM DocumentChunksFts JOIN DocumentChunks c ON c.Id = DocumentChunksFts.rowid "
               "JOIN Documents d ON d.Id = c.DocumentId WHERE DocumentChunksFts MATCH ? AND d.IsDeleted = 0")
        args = [q]
        if project_id:
            sql += " AND d.ProjectId = ?"
            args.append(project_id)
        rows = conn.execute(sql + " ORDER BY score LIMIT ?", (*args, limit)).fetchall()
        if rows:
            return [dict(r) for r in rows]
    return []


async def search_semantic(conn, question: str, project_id: Optional[int], limit: int = 8) -> Tuple[List[dict], str]:
    sql = ("SELECT c.Id, c.DocumentId, c.Page, c.Text, c.Embedding, c.EmbeddingModel, d.Title, d.DocType, d.ProjectId FROM DocumentChunks c "
           "JOIN Documents d ON d.Id = c.DocumentId WHERE d.IsDeleted = 0 AND c.Embedding IS NOT NULL")
    args = []
    if project_id:
        sql += " AND d.ProjectId = ?"
        args.append(project_id)
    rows = conn.execute(sql, args).fetchall()
    if not rows:
        return [], "none"
    vec, engine = await llm_router.embed([question])
    if not vec:
        return [], "none"
    q = np.asarray(vec[0], dtype=np.float32)
    usable = [r for r in rows if r["EmbeddingModel"] == engine]
    if not usable:
        return [], "none"
    mat = np.stack([np.frombuffer(r["Embedding"], dtype=np.float32) for r in usable])
    sims = mat @ q / (np.linalg.norm(mat, axis=1) * np.linalg.norm(q) + 1e-9)
    order = np.argsort(-sims)[:limit]
    return [{**{k: usable[i][k] for k in ("Id", "DocumentId", "Page", "Text", "Title", "DocType", "ProjectId")}, "score": float(sims[i]),
             "snip": usable[i]["Text"][:240]} for i in order], engine


async def hybrid(conn, question: str, project_id: Optional[int], limit: int = 6) -> Tuple[List[dict], str]:
    """Fusion par rang réciproque (RRF) du plein texte et du sémantique."""
    fts = search_fts(conn, question, project_id, 12)
    sem, engine = await search_semantic(conn, question, project_id, 12)
    ranks = {}
    for lst in (fts, sem):
        for rank, r in enumerate(lst):
            entry = ranks.setdefault(r["Id"], {"row": r, "score": 0.0})
            entry["score"] += 1 / (60 + rank)
    merged = sorted(ranks.values(), key=lambda e: -e["score"])[:limit]
    return [e["row"] for e in merged], ("hybride" if sem else "plein texte") + (f" ({engine})" if sem else "")
