"""Questions en langage naturel sur les documents d'un projet : réponse appuyée sur des passages cités."""
from typing import Any, Dict, Optional

from backend.core import ai_config, unified_db
from backend.core.llm_router import llm_router
from . import index


async def ask(question: str, project_id: Optional[int]) -> Dict[str, Any]:
    if not (question or "").strip():
        raise ValueError("Posez une question.")
    with unified_db.connect() as conn:
        passages, mode = await index.hybrid(conn, question, project_id, 6)
    sources = [{"n": i + 1, "document_id": p["DocumentId"], "title": p["Title"], "page": p["Page"], "excerpt": p["Text"][:700]}
               for i, p in enumerate(passages)]
    if not sources:
        return {"answer": "Aucun passage des documents indexés ne répond à cette question.", "sources": [], "engine": "aucun", "search": mode}
    context = "\n\n".join(f"[{s['n']}] {s['title']} (p. {s['page']}) :\n{s['excerpt']}" for s in sources)
    prompt = (f"Question : {question}\n\nPassages des documents du projet :\n{context}\n\n"
              "Réponds en français, uniquement à partir de ces passages, en citant la source entre crochets [n] après chaque "
              "affirmation. Si les passages ne permettent pas de répondre, dis-le.")
    text, engine = await llm_router.generate_with_meta(prompt, system_prompt=ai_config.prompt("ged.qa"), temperature=0.1, task="qa")
    if engine == "heuristic":
        # Pas de modèle disponible : réponse extractive (les passages les plus pertinents, tels quels).
        text = "Passages les plus pertinents (aucun modèle d'IA disponible pour rédiger une réponse) :\n" + \
               "\n".join(f"[{s['n']}] {s['excerpt'][:300]}…" for s in sources[:3])
    return {"answer": text.strip(), "sources": sources, "engine": engine, "search": mode}
