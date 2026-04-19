"""
Google Gemini LLM client wrapper — used as fallback.
"""

import time
from loguru import logger
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage

from src.config.settings import get_settings


class GeminiClient:
    """Wrapper around ChatGoogleGenerativeAI with retry logic."""

    def __init__(self):
        settings = get_settings()
        self.model_name = settings.GEMINI_MODEL
        self.max_retries = settings.MAX_RETRIES
        self.llm = ChatGoogleGenerativeAI(
            google_api_key=settings.GEMINI_API_KEY,
            model=self.model_name,
            temperature=0.3,
            max_output_tokens=4096,
        )
        logger.info(f"GeminiClient initialised with model={self.model_name}")

    def invoke(self, messages: list[BaseMessage]) -> BaseMessage:
        """Call Gemini with retries."""
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(f"Gemini attempt {attempt}/{self.max_retries}")
                response = self.llm.invoke(messages)
                logger.info("Gemini call succeeded")
                return response
            except Exception as exc:
                last_error = exc
                wait = 2 ** attempt
                logger.warning(
                    f"Gemini attempt {attempt} failed: {exc}. "
                    f"Retrying in {wait}s..."
                )
                time.sleep(wait)

        raise RuntimeError(
            f"Gemini failed after {self.max_retries} attempts: {last_error}"
        )

    def invoke_structured(
        self,
        messages: list[BaseMessage],
        schema: type,
    ):
        """Call Gemini with structured (JSON) output."""
        structured_llm = self.llm.with_structured_output(schema)
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                response = structured_llm.invoke(messages)
                return response
            except Exception as exc:
                last_error = exc
                wait = 2 ** attempt
                logger.warning(f"Gemini structured attempt {attempt} failed: {exc}")
                time.sleep(wait)

        raise RuntimeError(
            f"Gemini structured call failed after {self.max_retries} attempts: {last_error}"
        )
