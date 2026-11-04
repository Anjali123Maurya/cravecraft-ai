"""Thin wrapper around the local Ollama server.

All Ollama problems (server not running, model missing, timeout) are turned
into one exception, LLMUnavailable, so the rest of the app can fall back
gracefully instead of crashing.
"""
import logging
from typing import Any

import ollama

from core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class LLMUnavailable(Exception):
    """Raised when the local model cannot be reached or fails."""


class LLMClient:
    def __init__(self, client: Any | None = None, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._client = client or ollama.Client(host=self.settings.ollama_host,
                                               timeout=180)

    def generate_json(self, system: str, user: str, schema: dict,
                      temperature: float | None = None) -> str:
        """Ask the model for JSON that follows `schema`; return the raw text."""
        try:
            response = self._client.chat(
                model=self.settings.ollama_model,
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": user}],
                format=schema,
                options={
                    "temperature": (self.settings.llm_temperature
                                    if temperature is None else temperature),
                    "num_ctx": self.settings.llm_num_ctx,
                    "num_predict": self.settings.llm_num_predict,
                },
            )
        except Exception as exc:
            logger.error("Ollama call failed: %s", exc)
            raise LLMUnavailable(f"{type(exc).__name__}: {exc}") from exc
        return response.message.content or ""