"""
claude_client.py — LLM wrapper using Ollama (local, free).
Logs every request and response to terminal + logs/llm.log for debugging.
"""

import time
import logging
import os
from openai import OpenAI
from src.config import (
    OLLAMA_BASE_URL,
    OLLAMA_API_KEY,
    MODEL_FAST,
    MODEL_SMART,
    MAX_TOKENS_QUERY_ANALYSIS,
    MAX_TOKENS_METADATA,
    MAX_TOKENS_DBT_GENERATION,
)

# ── Logger setup ───────────────────────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)

logger = logging.getLogger("llm")
logger.setLevel(logging.DEBUG)

# format: timestamp | level | message
_fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s", datefmt="%H:%M:%S")

# handler 1 — terminal (you see this in the streamlit console)
_console = logging.StreamHandler()
_console.setFormatter(_fmt)

# handler 2 — file (persists across restarts)
_file = logging.FileHandler("logs/llm.log", encoding="utf-8")
_file.setFormatter(_fmt)

logger.addHandler(_console)
logger.addHandler(_file)

# ── Ollama client ──────────────────────────────────────────────────────────────
logger.info(f"Connecting to Ollama at {OLLAMA_BASE_URL}")
_client = OpenAI(
    base_url = OLLAMA_BASE_URL,
    api_key  = OLLAMA_API_KEY,
)
logger.info("Ollama client ready")


# ── Core call function ─────────────────────────────────────────────────────────
def _call(model: str, prompt: str, max_tokens: int, caller: str = "unknown") -> str:
    """
    Makes the actual call to Ollama. Logs everything:
      - what function triggered it
      - model used
      - prompt size
      - how long it took
      - first 120 chars of response (to confirm it came back)
    """
    prompt_chars = len(prompt)
    prompt_preview = prompt[:80].replace("\n", " ")

    logger.info(f"─── REQUEST ── caller={caller} model={model} max_tokens={max_tokens}")
    logger.debug(f"  prompt_chars : {prompt_chars}")
    logger.debug(f"  prompt_start : {prompt_preview!r}...")

    start = time.perf_counter()

    try:
        response = _client.chat.completions.create(
            model      = model,
            max_tokens = max_tokens,
            messages   = [{"role": "user", "content": prompt}],
        )
        elapsed = time.perf_counter() - start
        text    = response.choices[0].message.content

        logger.info(f"─── RESPONSE ─ caller={caller} elapsed={elapsed:.2f}s response_chars={len(text)}")
        logger.debug(f"  response_start : {text[:120].replace(chr(10), ' ')!r}...")

        return text

    except Exception as e:
        elapsed = time.perf_counter() - start
        logger.error(f"─── ERROR ──── caller={caller} elapsed={elapsed:.2f}s error={e}")
        raise


# ── Public functions ───────────────────────────────────────────────────────────

def analyze_query(prompt: str) -> str:
    return _call(MODEL_SMART, prompt, MAX_TOKENS_QUERY_ANALYSIS, caller="analyze_query")


def explain_metadata(prompt: str) -> str:
    return _call(MODEL_SMART, prompt, MAX_TOKENS_METADATA, caller="explain_metadata")


def generate_dbt(prompt: str) -> str:
    return _call(MODEL_SMART, prompt, MAX_TOKENS_DBT_GENERATION, caller="generate_dbt")


def quick_label(prompt: str) -> str:
    return _call(MODEL_FAST, prompt, 100, caller="quick_label")
