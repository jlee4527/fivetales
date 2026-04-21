"""Hugging Face InferenceClient wrapper for Qwen3 model calls."""
import re
import logging
from huggingface_hub import InferenceClient
from fivetales.config import (
    HF_TOKEN,
    MODEL_PRIMARY,
    TEMPERATURE,
    MAX_TOKENS,
    HTTP_TIMEOUT,
)
from fivetales.schema import get_llm_schema

logger = logging.getLogger(__name__)

_THINK_PATTERN = re.compile(r"<think>.*?</think>", re.DOTALL)
_THINK_OPEN_PATTERN = re.compile(r"<think>.*", re.DOTALL)
_CODE_FENCE_PATTERN = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


class LLMCallError(Exception):
    """Raised when all LLM call attempts fail."""


def _strip_think_blocks(text: str) -> str:
    """Remove <think>...</think> blocks; handles unclosed blocks from token truncation."""
    cleaned = _THINK_PATTERN.sub("", text)
    # If <think> opened but never closed (truncated), strip from opening tag to end
    if "<think>" in cleaned:
        cleaned = _THINK_OPEN_PATTERN.sub("", cleaned)
    return cleaned.strip()


def _strip_code_fences(text: str) -> str:
    match = _CODE_FENCE_PATTERN.search(text)
    if match:
        return match.group(1).strip()
    return text.strip()


def _clean_response(text: str) -> str:
    text = _strip_think_blocks(text)
    text = _strip_code_fences(text)
    return text


def call_llm(
    messages: list[dict],
    temperature: float = TEMPERATURE,
    max_tokens: int = MAX_TOKENS,
    model: str | None = None,
    response_format: dict | None = None,
) -> str:
    """
    Call the Hugging Face InferenceClient with three-tier structured output fallback:
      1. json_schema strict mode (Cerebras)
      2. json_object mode (auto-routed)
      3. plain text generation (prompt-only)

    Returns cleaned response string with think blocks and code fences removed.
    Raises LLMCallError if all attempts fail.
    """
    effective_model = model or MODEL_PRIMARY
    client = InferenceClient(token=HF_TOKEN, timeout=HTTP_TIMEOUT)

    # Tier 1: json_schema strict mode
    rf = response_format or {
        "type": "json_schema",
        "json_schema": {"name": "character_card", "schema": get_llm_schema(), "strict": True},
    }
    attempts = [
        (effective_model, rf),
        (effective_model, {"type": "json_object"}),
        (effective_model, None),
    ]

    last_exc: Exception | None = None
    for attempt_model, attempt_rf in attempts:
        try:
            kwargs: dict = {
                "model": attempt_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if attempt_rf is not None:
                kwargs["response_format"] = attempt_rf

            completion = client.chat.completions.create(**kwargs)
            raw = completion.choices[0].message.content or ""

            usage = getattr(completion, "usage", None)
            if usage:
                logger.info(
                    "LLM usage — model=%s prompt=%s completion=%s",
                    attempt_model,
                    getattr(usage, "prompt_tokens", "?"),
                    getattr(usage, "completion_tokens", "?"),
                )

            return _clean_response(raw)
        except Exception as exc:
            logger.warning("LLM attempt failed (model=%s rf=%s): %s", attempt_model, attempt_rf, exc)
            last_exc = exc

    raise LLMCallError(f"All LLM call attempts failed: {last_exc}") from last_exc
