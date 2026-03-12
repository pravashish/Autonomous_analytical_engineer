"""
config.py — loads all environment variables and project-wide constants.
Every other file imports from here. Nothing reads .env directly.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Snowflake ──────────────────────────────────────────────────────────────────
SNOWFLAKE_ACCOUNT    = os.getenv("SNOWFLAKE_ACCOUNT")
SNOWFLAKE_USER       = os.getenv("SNOWFLAKE_USER")
SNOWFLAKE_PASSWORD   = os.getenv("SNOWFLAKE_PASSWORD")
SNOWFLAKE_ROLE       = os.getenv("SNOWFLAKE_ROLE",      "ACCOUNTADMIN")
SNOWFLAKE_WAREHOUSE  = os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH")
SNOWFLAKE_DATABASE   = os.getenv("SNOWFLAKE_DATABASE",  "ANALYTICS_DEMO")
SNOWFLAKE_SCHEMA     = os.getenv("SNOWFLAKE_SCHEMA",    "MARTS")

# ── Ollama (local LLM — completely free, no API key needed) ───────────────────
OLLAMA_BASE_URL = "http://localhost:11434/v1"   # Ollama's OpenAI-compatible endpoint
OLLAMA_API_KEY  = "ollama"                      # placeholder — Ollama ignores this value

# ── Model routing ──────────────────────────────────────────────────────────────
# GPU available  → keep qwen2.5-coder:7b  (fast, high quality)
# CPU only       → switch to qwen2.5-coder:1.5b (4x faster, still decent for SQL)
# Check which you have: run `ollama ps` while a request is in flight
#   PROCESSOR = 100% GPU → fast, keep 7b
#   PROCESSOR = 100% CPU → slow, switch to 1.5b below
MODEL_FAST  = "qwen2.5-coder:1.5b"   # lightweight — labels, quick classifications
MODEL_SMART = "qwen2.5-coder:1.5b"   # change back to 7b if you have GPU

# ── Token caps ────────────────────────────────────────────────────────────────
MAX_TOKENS_QUERY_ANALYSIS  = 800    # reduced from 1200 — faster on CPU
MAX_TOKENS_METADATA        = 600    # reduced from 800
MAX_TOKENS_DBT_GENERATION  = 1000   # reduced from 1500

# ── Snowflake query limits ─────────────────────────────────────────────────────
QUERY_HISTORY_LIMIT  = 20
SAMPLE_ROWS_LIMIT    = 5
MAX_COLUMNS_TO_SEND  = 20

# ── Output paths ──────────────────────────────────────────────────────────────
OUTPUT_SQL_DIR    = "outputs/generated_sql"
OUTPUT_YAML_DIR   = "outputs/generated_yaml"
OUTPUT_REPORT_DIR = "outputs/reports"
