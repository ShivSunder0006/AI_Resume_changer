"""
Groq LLM client wrapper with retry logic.
"""

import time
from loguru import logger
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage

from src.config.settings import get_settings


class GroqClient:
    """Wrapper around ChatGroq with exponential backoff."""

    def __init__(self):
        settings = get_settings()
        self.model_name = settings.GROQ_MODEL
        self.max_retries = settings.MAX_RETRIES
        self.llm = ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model=self.model_name,
            temperature=0.3,
            max_tokens=4096,
        )
        logger.info(f"GroqClient initialised with model={self.model_name}")

    def invoke(self, messages: list[BaseMessage]) -> BaseMessage:
        """Call Groq with retries + exponential backoff."""
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(f"Groq attempt {attempt}/{self.max_retries}")
                response = self.llm.invoke(messages)
                logger.info("Groq call succeeded")
                return response
            except Exception as exc:
                last_error = exc
                wait = 2 ** attempt
                logger.warning(
                    f"Groq attempt {attempt} failed: {exc}. "
                    f"Retrying in {wait}s..."
                )
                time.sleep(wait)

        raise RuntimeError(
            f"Groq failed after {self.max_retries} attempts: {last_error}"
        )

    def invoke_structured(
        self,
        messages: list[BaseMessage],
        schema: type,
    ):
        """Call Groq with structured (JSON) output."""
        structured_llm = self.llm.with_structured_output(schema)
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                response = structured_llm.invoke(messages)
                return response
            except Exception as exc:
                last_error = exc
                wait = 2 ** attempt
                logger.warning(f"Groq structured attempt {attempt} failed: {exc}")
                time.sleep(wait)

        raise RuntimeError(
            f"Groq structured call failed after {self.max_retries} attempts: {last_error}"
        )
