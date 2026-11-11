"""Appels aux fournisseurs d'IA configurés par tâche (Lot 7).

Règles appliquées avant tout appel externe (fournisseur en ligne ou serveur compatible distant) :
1. l'IA externe doit être autorisée (mode hors ligne désactivé) ;
2. le plafond de coût mensuel ne doit pas être atteint ;
3. si le masquage est actif, RIB, CIN, salaires… sont masqués dans le prompt et le prompt système, et une image
   (non masquable) n'est jamais envoyée ;
4. la clé d'API vient du stockage chiffré (DPAPI) ; elle n'est jamais écrite dans un journal ni renvoyée à l'interface.
Un refus ou une erreur rend la main au routeur, qui se replie sur le moteur local.
"""
import json
from typing import Any, Dict, List, Optional, Tuple

import httpx

from backend.core import ai_config, privacy


class ProviderError(RuntimeError):
    pass


async def _post(url: str, payload: Dict[str, Any], headers: Dict[str, str], timeout: float = 90.0) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(url, json=payload, headers=headers)
    if r.status_code >= 400:
        # Le corps d'erreur ne contient pas la clé (envoyée en en-tête) ; on le tronque.
        raise ProviderError(f"{r.status_code} : {r.text[:300]}")
    return r.json()


async def _get(url: str, headers: Dict[str, str], timeout: float = 15.0) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.get(url, headers=headers)
    if r.status_code >= 400:
        raise ProviderError(f"{r.status_code} : {r.text[:300]}")
    return r.json()


def _clean_b64(b64: str) -> str:
    return b64.split(",")[-1] if "," in b64 else b64


async def call(provider: str, model: str, prompt: str, system: str, temperature: float, max_tokens: Optional[int],
               images_b64: Optional[List[str]], response_json: bool) -> Tuple[str, int, int]:
    """Appel brut : (texte, jetons en entrée, jetons en sortie)."""
    cfg = ai_config.provider_config(provider)
    base = cfg["base_url"].rstrip("/")
    key = ai_config.api_key(provider)
    max_tokens = int(max_tokens or 2048)
    if ai_config.PROVIDERS[provider]["external"] and not key:
        raise ProviderError("clé d'API non configurée")
    if provider == "anthropic":
        content: List[Dict[str, Any]] = [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": _clean_b64(i)}}
                                         for i in images_b64 or []]
        content.append({"type": "text", "text": prompt + ("\n\nRéponds uniquement par du JSON valide." if response_json else "")})
        payload: Dict[str, Any] = {"model": model, "max_tokens": max_tokens, "temperature": temperature,
                                   "messages": [{"role": "user", "content": content}]}
        if system:
            payload["system"] = system
        data = await _post(f"{base}/v1/messages", payload, {"x-api-key": key, "anthropic-version": "2023-06-01"})
        text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        u = data.get("usage") or {}
        return text, int(u.get("input_tokens") or 0), int(u.get("output_tokens") or 0)
    if provider in ("openai", "mistral", "openai_compatible"):
        messages: List[Dict[str, Any]] = [{"role": "system", "content": system}] if system else []
        if images_b64:
            parts: List[Dict[str, Any]] = [{"type": "text", "text": prompt}]
            parts += [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_clean_b64(i)}"}} for i in images_b64]
            messages.append({"role": "user", "content": parts})
        else:
            messages.append({"role": "user", "content": prompt})
        payload = {"model": model, "messages": messages, "temperature": temperature}
        payload["max_completion_tokens" if provider == "openai" else "max_tokens"] = max_tokens
        if response_json:
            payload["response_format"] = {"type": "json_object"}
        headers = {"Authorization": f"Bearer {key}"} if key else {}
        data = await _post(f"{base}/chat/completions", payload, headers)
        text = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
        u = data.get("usage") or {}
        return text, int(u.get("prompt_tokens") or 0), int(u.get("completion_tokens") or 0)
    if provider == "gemini":
        parts = [{"text": prompt}] + [{"inline_data": {"mime_type": "image/jpeg", "data": _clean_b64(i)}} for i in images_b64 or []]
        payload = {"contents": [{"role": "user", "parts": parts}],
                   "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens}}
        if system:
            payload["system_instruction"] = {"parts": [{"text": system}]}
        if response_json:
            payload["generationConfig"]["response_mime_type"] = "application/json"
        data = await _post(f"{base}/models/{model}:generateContent", payload, {"x-goog-api-key": key})
        cand = (data.get("candidates") or [{}])[0]
        text = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))
        u = data.get("usageMetadata") or {}
        return text, int(u.get("promptTokenCount") or 0), int(u.get("candidatesTokenCount") or 0)
    if provider == "ollama":
        messages = [{"role": "system", "content": system}] if system else []
        user: Dict[str, Any] = {"role": "user", "content": prompt}
        if images_b64:
            user["images"] = [_clean_b64(i) for i in images_b64]
        messages.append(user)
        payload = {"model": model, "messages": messages, "stream": False, "options": {"temperature": temperature, "num_predict": max_tokens}}
        if response_json:
            payload["format"] = "json"
        data = await _post(f"{base}/api/chat", payload, {})
        return data.get("message", {}).get("content", ""), int(data.get("prompt_eval_count") or 0), int(data.get("eval_count") or 0)
    raise ProviderError(f"fournisseur inconnu : {provider}")


async def run_task(task: str, prompt: str, system: str, temperature: float, images_b64: Optional[List[str]],
                   response_json: bool) -> Optional[Tuple[str, str]]:
    """Exécute une tâche avec le fournisseur choisi ; None = repli sur le moteur local (refus ou erreur)."""
    cfg = ai_config.task_config(task)
    provider = cfg["provider"]
    if provider in ("auto", "", None) or provider not in ai_config.PROVIDERS:
        return None
    if provider == "heuristic":
        return None
    pcfg = ai_config.provider_config(provider)
    model = cfg.get("model") or pcfg["model"]
    if not model:
        print(f"[IA] Tâche {task} : aucun modèle choisi pour {provider} ; moteur local utilisé.")
        return None
    temp = cfg["temperature"] if cfg.get("temperature") is not None else temperature
    if ai_config.is_external(provider, pcfg["base_url"]):
        if not privacy.external_ai_allowed():
            return None
        if ai_config.cap_reached():
            print(f"[IA] Plafond de coût mensuel atteint : tâche {task} traitée localement.")
            return None
        if privacy.mask_enabled():
            if images_b64:
                print("[IA] Masquage actif : image non envoyée à l'IA externe, moteur local utilisé.")
                return None
            prompt, _ = privacy.mask_sensitive(prompt)
            system, _ = privacy.mask_sensitive(system)
    try:
        text, tin, tout = await call(provider, model, prompt, system, float(temp), cfg.get("max_tokens"), images_b64, response_json)
    except Exception as e:  # noqa: BLE001 — toute erreur réseau ou d'API : repli local
        print(f"[IA] {provider} indisponible pour la tâche {task} : {e}")
        return None
    ai_config.record(provider, tin, tout)
    return text, f"{provider}:{model}"


async def test(provider: str, api_key: Optional[str] = None, base_url: Optional[str] = None) -> Dict[str, Any]:
    """« Tester la connexion » : liste des modèles disponibles (aucune donnée de l'association n'est envoyée)."""
    if provider not in ai_config.PROVIDERS or provider == "heuristic":
        return {"ok": True, "message": "Moteur local : aucune connexion nécessaire.", "models": []}
    cfg = ai_config.provider_config(provider)
    base = (base_url or cfg["base_url"]).rstrip("/")
    if ai_config.is_external(provider, base) and not privacy.external_ai_allowed():
        return {"ok": False, "message": "Mode hors ligne actif : désactivez-le (section IA) pour tester un fournisseur en ligne.", "models": []}
    key = api_key or ai_config.api_key(provider)
    try:
        if provider == "anthropic":
            data = await _get(f"{base}/v1/models", {"x-api-key": key, "anthropic-version": "2023-06-01"})
            models = [m["id"] for m in data.get("data", [])]
        elif provider == "gemini":
            data = await _get(f"{base}/models", {"x-goog-api-key": key})
            models = [m["name"].split("/")[-1] for m in data.get("models", []) if "generateContent" in m.get("supportedGenerationMethods", [])]
        elif provider == "ollama":
            data = await _get(f"{base}/api/tags", {})
            models = [m["name"] for m in data.get("models", [])]
        else:
            data = await _get(f"{base}/models", {"Authorization": f"Bearer {key}"} if key else {})
            models = [m["id"] for m in data.get("data", [])]
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "message": f"Connexion impossible : {e}", "models": []}
    return {"ok": True, "message": f"Connexion réussie : {len(models)} modèle(s) disponible(s).", "models": sorted(models)}
