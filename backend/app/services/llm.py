"""Optional narration. The model only receives numbers this app already calculated."""

from __future__ import annotations

import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


def explain(question: str, facts: dict) -> tuple[str | None, str | None, str]:
    """Return (narrative, provider, note).

    Narrative is None when no key is configured or the provider call fails.
    The note is safe to show to the user.
    """

    settings = get_settings()
    provider = _provider(settings)
    if provider is None:
        return None, None, "No Gemini or OpenRouter API key is configured, so this answer uses the calculated metrics only."

    prompt = (
        "You explain small-business analytics. Use only the JSON facts. "
        "Do not invent numbers, customers, products, or dates. "
        "If a metric is null or a section says data is unavailable, say that plainly. "
        "Write 2 short paragraphs.\n\n"
        f"Question: {question}\n\nFacts: {facts}"
    )
    try:
        if provider == "gemini":
            text = _gemini(settings.gemini_api_key, settings.gemini_model, prompt)
            return text, "gemini", "Explanation generated from the metrics above."
        text = _openrouter(settings.openrouter_api_key, settings.openrouter_model, prompt)
        return text, "openrouter", "Explanation generated from the metrics above."
    except Exception:
        logger.exception("LLM explanation failed")
        return None, provider, "The AI service did not respond. The answer below is the calculated metrics only."


def _provider(settings) -> str | None:
    choice = (settings.llm_provider or "auto").lower()
    if choice == "none":
        return None
    if choice == "gemini":
        return "gemini" if settings.gemini_api_key else None
    if choice == "openrouter":
        return "openrouter" if settings.openrouter_api_key else None
    if settings.gemini_api_key:
        return "gemini"
    if settings.openrouter_api_key:
        return "openrouter"
    return None


def _gemini(api_key: str, model: str, prompt: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    response = httpx.post(
        url,
        params={"key": api_key},
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    parts = data["candidates"][0]["content"]["parts"]
    text = "".join(part.get("text", "") for part in parts).strip()
    if not text:
        raise ValueError("Empty model response")
    return text


def _openrouter(api_key: str, model: str, prompt: str) -> str:
    response = httpx.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": model, "messages": [{"role": "user", "content": prompt}]},
        timeout=30,
    )
    response.raise_for_status()
    text = response.json()["choices"][0]["message"]["content"]
    if not text or not str(text).strip():
        raise ValueError("Empty model response")
    return str(text).strip()
