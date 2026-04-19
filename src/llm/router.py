"""
LLM Router — Groq (primary) → Gemini (fallback).

Transparently routes requests; logs which provider was used.
"""

from loguru import logger
from langchain_core.messages import BaseMessage

from src.llm.groq_client import GroqClient
from src.llm.gemini_client import GeminiClient


class LLMRouter:
    """
    Tries Groq first. If all retries fail, falls back to Gemini.
    Exposes a unified `.invoke()` / `.invoke_structured()` interface.
    """

    def __init__(self):
        self.groq = GroqClient()
        self.gemini = GeminiClient()
        self._last_provider: str = ""
        logger.info("LLMRouter ready (Groq → Gemini fallback)")

    @property
    def last_provider(self) -> str:
        return self._last_provider

    # ── Plain text call ───────────────────────────────────
    def invoke(self, messages: list[BaseMessage]) -> BaseMessage:
        try:
            result = self.groq.invoke(messages)
            self._last_provider = "groq"
            return result
        except Exception as groq_err:
            logger.error(f"Groq exhausted, falling back to Gemini: {groq_err}")
            try:
                result = self.gemini.invoke(messages)
                self._last_provider = "gemini"
                return result
            except Exception as gemini_err:
                logger.critical(f"Both LLMs failed. Groq: {groq_err} | Gemini: {gemini_err}")
                raise RuntimeError(
                    f"All LLM providers failed.\n"
                    f"  Groq: {groq_err}\n"
                    f"  Gemini: {gemini_err}"
                )

    # ── Structured (JSON) call ────────────────────────────
    def invoke_structured(
        self,
        messages: list[BaseMessage],
        schema: type,
    ):
        try:
            result = self.groq.invoke_structured(messages, schema)
            self._last_provider = "groq"
            return result
        except Exception as groq_err:
            logger.error(f"Groq structured exhausted, falling back to Gemini: {groq_err}")
            try:
                result = self.gemini.invoke_structured(messages, schema)
                self._last_provider = "gemini"
                return result
            except Exception as gemini_err:
                logger.critical(f"Both structured LLMs failed.")
                raise RuntimeError(
                    f"All LLM providers failed (structured).\n"
                    f"  Groq: {groq_err}\n"
                    f"  Gemini: {gemini_err}"
                )
