"""
claude_client.py — single wrapper around the Anthropic API.
All Claude calls go through here. Token budget enforced centrally.

Token strategy:
  - MODEL_FAST  (haiku)  → classifications, short labels, rule summaries
  - MODEL_SMART (sonnet) → SQL analysis, metadata explanation, dbt generation
"""

import anthropic
from src.config import (
    ANTHROPIC_API_KEY,
    MODEL_FAST,
    MODEL_SMART,
    MAX_TOKENS_QUERY_ANALYSIS,
    MAX_TOKENS_METADATA,
    MAX_TOKENS_DBT_GENERATION,
)

# single shared client — instantiated once at import time
_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def _call(model: str, prompt: str, max_tokens: int) -> str:
    """
    Internal function — makes the actual API call.
    Returns the response text as a string.
    All other functions in this file call this one.
    """
    message = _client.messages.create(
        model      = model,
        max_tokens = max_tokens,
        messages   = [{"role": "user", "content": prompt}],
    )
    return message.content[0].text


# ── Public functions — one per feature ────────────────────────────────────────

def analyze_query(prompt: str) -> str:
    """
    Used by: Query Analyzer tab
    Model: Sonnet (complex SQL reasoning)
    """
    return _call(
        model      = MODEL_SMART,
        prompt     = prompt,
        max_tokens = MAX_TOKENS_QUERY_ANALYSIS,
    )


def explain_metadata(prompt: str) -> str:
    """
    Used by: Table Explainer tab
    Model: Sonnet (business context inference)
    """
    return _call(
        model      = MODEL_SMART,
        prompt     = prompt,
        max_tokens = MAX_TOKENS_METADATA,
    )


def generate_dbt(prompt: str) -> str:
    """
    Used by: dbt Generator tab
    Model: Sonnet (code generation)
    """
    return _call(
        model      = MODEL_SMART,
        prompt     = prompt,
        max_tokens = MAX_TOKENS_DBT_GENERATION,
    )


def quick_label(prompt: str) -> str:
    """
    Used by: any feature that needs a fast, cheap classification.
    Example: "Is this a fact table or dimension table? Reply in one word."
    Model: Haiku (simple yes/no or short labels)
    """
    return _call(
        model      = MODEL_FAST,
        prompt     = prompt,
        max_tokens = 100,                   # very small cap for labeling
    )
