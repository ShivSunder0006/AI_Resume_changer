"""
Tests for the LLM Router (Groq → Gemini fallback).
"""

import pytest
from unittest.mock import patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage


class TestLLMRouter:
    """Test the fallback routing logic."""

    @patch("src.llm.router.GroqClient")
    @patch("src.llm.router.GeminiClient")
    def test_groq_success_no_fallback(self, MockGemini, MockGroq):
        """When Groq succeeds, Gemini should not be called."""
        mock_groq = MockGroq.return_value
        mock_gemini = MockGemini.return_value

        mock_groq.invoke.return_value = AIMessage(content="Groq response")

        from src.llm.router import LLMRouter
        router = LLMRouter()
        result = router.invoke([HumanMessage(content="Hello")])

        assert result.content == "Groq response"
        assert router.last_provider == "groq"
        mock_gemini.invoke.assert_not_called()

    @patch("src.llm.router.GroqClient")
    @patch("src.llm.router.GeminiClient")
    def test_groq_fails_gemini_fallback(self, MockGemini, MockGroq):
        """When Groq fails, should fall back to Gemini."""
        mock_groq = MockGroq.return_value
        mock_gemini = MockGemini.return_value

        mock_groq.invoke.side_effect = RuntimeError("Groq rate limit")
        mock_gemini.invoke.return_value = AIMessage(content="Gemini response")

        from src.llm.router import LLMRouter
        router = LLMRouter()
        result = router.invoke([HumanMessage(content="Hello")])

        assert result.content == "Gemini response"
        assert router.last_provider == "gemini"

    @patch("src.llm.router.GroqClient")
    @patch("src.llm.router.GeminiClient")
    def test_both_fail_raises(self, MockGemini, MockGroq):
        """When both providers fail, should raise RuntimeError."""
        mock_groq = MockGroq.return_value
        mock_gemini = MockGemini.return_value

        mock_groq.invoke.side_effect = RuntimeError("Groq down")
        mock_gemini.invoke.side_effect = RuntimeError("Gemini down")

        from src.llm.router import LLMRouter
        router = LLMRouter()

        with pytest.raises(RuntimeError, match="All LLM providers failed"):
            router.invoke([HumanMessage(content="Hello")])

    @patch("src.llm.router.GroqClient")
    @patch("src.llm.router.GeminiClient")
    def test_structured_groq_success(self, MockGemini, MockGroq):
        """Structured output should work with Groq."""
        mock_groq = MockGroq.return_value
        mock_gemini = MockGemini.return_value

        mock_groq.invoke_structured.return_value = {"key": "value"}

        from src.llm.router import LLMRouter
        router = LLMRouter()
        result = router.invoke_structured([HumanMessage(content="Hello")], dict)

        assert result == {"key": "value"}
        assert router.last_provider == "groq"
