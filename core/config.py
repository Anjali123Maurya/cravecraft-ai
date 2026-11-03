"""Application settings, read from environment variables / the .env file.

Nothing is hardcoded in other modules: they call get_settings() instead.
"""
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    ollama_host: str
    ollama_model: str
    llm_temperature: float
    llm_num_ctx: int
    llm_num_predict: int
    db_path: Path
    log_level: str
    default_diet: str
    unit_system: str  # "household" (cups + grams) or "metric"


@lru_cache
def get_settings() -> Settings:
    return Settings(
        ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b"),
        llm_temperature=_float("LLM_TEMPERATURE", 0.3),
        llm_num_ctx=_int("LLM_NUM_CTX", 4096),
        llm_num_predict=_int("LLM_NUM_PREDICT", 1200),
        db_path=PROJECT_ROOT / os.getenv("DB_PATH", "data/cravecraft.db"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        default_diet=os.getenv("DEFAULT_DIET", "vegetarian"),
        unit_system=os.getenv("UNIT_SYSTEM", "household"),
    )