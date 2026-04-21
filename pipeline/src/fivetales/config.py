"""Centralized configuration loaded from environment variables."""
from dotenv import load_dotenv
import os

load_dotenv()

HF_TOKEN: str = os.getenv("HF_TOKEN", "")
NLM_API_KEY: str = os.getenv("NLM_API_KEY", "")

MODEL_PRIMARY: str = "Qwen/Qwen3-32B:cerebras"
MODEL_FALLBACK: str = "Qwen/Qwen3-32B"
MODEL_BASELINE: str = "Qwen/Qwen3-8B"

TEMPERATURE: float = 0.3
TEMPERATURE_BASELINE: float = 0.7
MAX_TOKENS: int = 1024
HTTP_TIMEOUT: int = 10
MAX_LLM_RETRIES: int = 2
