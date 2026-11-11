"""Extraction de secours par un modèle d'IA (option), utilisée seulement si la lecture OCR ne s'équilibre pas.

Les règles de confidentialité du routeur s'appliquent : IA externe seulement si autorisée, données masquées si
le masquage est actif, images jamais envoyées à l'extérieur quand le masquage est actif (Ollama local possible).
Le résultat n'est retenu que s'il équilibre les soldes ; il reste un brouillon à valider par l'utilisateur.
"""
import base64
import json
import re
from typing import List, Optional

from backend.core import ai_config
from backend.core.llm_router import llm_router
from .extract import parse_date
from .model import ExtractedLine, ExtractedStatement

PROMPT = ai_config.PROMPTS["statements.extract"]["text"]     # modifiable dans Paramètres › IA


def _cents(value) -> Optional[int]:
    if value in (None, ""):
        return 0
    t = re.sub(r"[^\d,.\-]", "", str(value))
    if not t:
        return 0
    t = t.replace(" ", "")
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    try:
        return int(round(float(t) * 100))
    except ValueError:
        return None


async def extract_with_ai(ocr_text: str, page_images: List[bytes], base: ExtractedStatement) -> Optional[ExtractedStatement]:
    images = [base64.b64encode(p).decode("ascii") for p in page_images[:4]]
    text, engine = await llm_router.generate_with_meta(ai_config.prompt("statements.extract") + ocr_text[:12000], images_b64=images or None,
                                                         response_json=True, temperature=0.0, task="extraction")
    if engine == "heuristic":
        return None  # aucun modèle disponible : on ne fabrique pas de relevé
    try:
        data = json.loads(text[text.index("{"): text.rindex("}") + 1])
    except (ValueError, json.JSONDecodeError):
        return None
    st = ExtractedStatement(bank_id=base.bank_id, bank_name=base.bank_name, rib=base.rib, period_start=base.period_start,
                            period_end=base.period_end, engine=f"ia:{engine}", pages=base.pages)
    st.opening, st.closing = _cents(data.get("opening")), _cents(data.get("closing"))
    for item in data.get("lines", []):
        d = parse_date(str(item.get("date", "")).strip())
        debit, credit = _cents(item.get("debit")), _cents(item.get("credit"))
        if not d or debit is None or credit is None or (debit > 0) == (credit > 0):
            continue
        st.lines.append(ExtractedLine(d, parse_date(str(item.get("value_date") or "")), str(item.get("label", ""))[:500], "",
                                      abs(debit), abs(credit), {"date": 60.0, "label": 60.0, "debit": 60.0, "credit": 60.0}))
    if st.balance_ok() is not True:
        return None
    st.warnings.append(f"Lu par l'IA ({engine}) car la lecture OCR ne s'équilibrait pas : vérifiez chaque ligne.")
    return st
