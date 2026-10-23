"""
ai/provider.py — LLM provider adapter for HackMate AI module.

Supports:
  - Google Gemini via `google-genai` SDK (free-tier compatible, recommended)
  - Deterministic fallback (when no key is configured — clearly labelled)

Environment variables (read from .env via python-dotenv):
  GEMINI_API_KEY   — Google Gemini API key (get free at aistudio.google.com)
  AI_MODEL         — Model name override. Defaults to 'gemini-2.0-flash'
                     Set to 'mock' to force the deterministic fallback.
"""

from __future__ import annotations

import asyncio
import logging
import os
from abc import ABC, abstractmethod
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_MAX_RETRIES = 2
_RETRY_DELAY = 2.0
_DEFAULT_GEMINI_MODEL = "gemini-3.5-flash"
_BACKUP_GEMINI_MODELS = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]


class ProviderError(Exception):
    """Raised when the AI provider returns an unrecoverable error."""


class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, prompt: str) -> str: ...

    @property
    @abstractmethod
    def name(self) -> str: ...


# ---------------------------------------------------------------------------
# Google Gemini provider (uses google-genai SDK)
# ---------------------------------------------------------------------------

class GeminiProvider(LLMProvider):
    """Async wrapper around the google-genai SDK.

    Uses 'gemini-2.0-flash' by default (free-tier compatible).
    """

    def __init__(self, api_key: str, model: str = _DEFAULT_GEMINI_MODEL):
        try:
            from google import genai  # type: ignore
            from google.genai import types  # type: ignore
        except ImportError as exc:
            raise ProviderError(
                "google-genai is not installed. Run: pip install google-genai"
            ) from exc

        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=45000),
        )
        self._model_name = model

    @property
    def name(self) -> str:
        return f"Gemini ({self._model_name})"

    async def complete(self, prompt: str) -> str:
        """Call Gemini asynchronously with bounded retries and model failover."""
        models_to_try = [self._model_name] + [
            m for m in _BACKUP_GEMINI_MODELS if m != self._model_name
        ]

        last_exc: Optional[Exception] = None
        for current_model in models_to_try:
            for attempt in range(1, _MAX_RETRIES + 2):
                try:
                    loop = asyncio.get_running_loop()
                    response = await loop.run_in_executor(
                        None,
                        lambda m=current_model: self._client.models.generate_content(
                            model=m,
                            contents=prompt,
                        ),
                    )
                    text = response.text
                    if not text or not text.strip():
                        raise ProviderError(f"Gemini ({current_model}) returned an empty response.")
                    return text.strip()
                except ProviderError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    last_exc = exc
                    err_str = str(exc)
                    # If high demand / 503 / 429, try next attempt or failover model
                    is_transient = "503" in err_str or "UNAVAILABLE" in err_str or "429" in err_str
                    if attempt <= _MAX_RETRIES and is_transient:
                        logger.warning(
                            "Gemini (%s) attempt %d/%d failed: %s — retrying in %.1fs",
                            current_model, attempt, _MAX_RETRIES + 1, exc, _RETRY_DELAY,
                        )
                        await asyncio.sleep(_RETRY_DELAY)
                    elif is_transient:
                        logger.warning(
                            "Gemini (%s) unavailable. Failing over to backup model if available...",
                            current_model,
                        )
                        break
                    else:
                        logger.error("Gemini (%s) call error: %s", current_model, exc)
                        break

        raise ProviderError(
            f"All Gemini models exhausted. Last error: {last_exc}"
        )


# ---------------------------------------------------------------------------
# Deterministic fallback provider
# ---------------------------------------------------------------------------

class FallbackProvider(LLMProvider):
    """Deterministic stub used when no API key is configured.

    IMPORTANT: This is NOT an LLM. Responses are tagged with [FALLBACK].
    """

    @property
    def name(self) -> str:
        return "Fallback (deterministic — no LLM key configured)"

    async def complete(self, prompt: str) -> str:
        return _FALLBACK_SENTINEL


_FALLBACK_SENTINEL = "__HACKMATE_FALLBACK__"


# ---------------------------------------------------------------------------
# Provider factory
# ---------------------------------------------------------------------------

def get_provider() -> LLMProvider:
    """Return the best available LLM provider.

    Priority:
      1. FallbackProvider  — if AI_MODEL=mock
      2. GeminiProvider    — if GEMINI_API_KEY is set
      3. FallbackProvider  — default (no key)
    """
    ai_model = os.getenv("AI_MODEL", "").strip().lower()
    if ai_model == "mock":
        logger.info("AI_MODEL=mock — using deterministic fallback provider.")
        return FallbackProvider()

    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    if gemini_key:
        model_name = (
            ai_model
            if ai_model and ai_model not in ("mock", "mock-v1")
            else _DEFAULT_GEMINI_MODEL
        )
        logger.info("Using Gemini provider with model '%s'.", model_name)
        return GeminiProvider(api_key=gemini_key, model=model_name)

    logger.warning(
        "No AI provider key found. Using deterministic fallback. "
        "Set GEMINI_API_KEY in .env to enable real AI generation."
    )
    return FallbackProvider()
