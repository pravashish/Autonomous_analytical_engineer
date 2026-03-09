"""
config.py — loads all environment variables and project-wide constants.
Every other file imports from here. Nothing reads .env directly.
"""

import os
from dotenv import load_dotenv

load_dotenv()  # reads .env file into os.environ

# ── Snowflake ──────────────────────────────────────────────────────────────────
SNOWFLAKE_ACCOUNT    = os.getenv("SNOWFLAKE_ACCOUNT")
SNOWFLAKE_USER       = os.getenv("SNOWFLAKE_USER")
SNOWFLAKE_PASSWORD   = os.getenv("SNOWFLAKE_PASSWORD")
SNOWFLAKE_ROLE       = os.getenv("SNOWFLAKE_ROLE",      "ACCOUNTADMIN")
SNOWFLAKE_WAREHOUSE  = os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH")
SNOWFLAKE_DATABASE   = os.getenv("SNOWFLAKE_DATABASE",  "ANALYTICS_DEMO")
SNOWFLAKE_SCHEMA     = os.getenv("SNOWFLAKE_SCHEMA",    "MARTS")

# ── Claude API ─────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY    = os.getenv("ANTHROPIC_API_KEY")

# ── Model routing (token budget strategy) ─────────────────────────────────────
# Haiku  = fast + cheap  → use for simple tasks (rule labeling, short summaries)
# Sonnet = smart + slower → use for deep analysis (SQL optimization, dbt generation)
MODEL_FAST   = "claude-3-5-haiku-20241022"   # ~25x cheaper than Sonnet
MODEL_SMART  = "claude-sonnet-4-5"          # use only when complexity demands it

# ── Token caps per call (hard limits to protect your budget) ──────────────────
MAX_TOKENS_QUERY_ANALYSIS  = 1200   # query analyzer response
MAX_TOKENS_METADATA        = 800    # table explainer response
MAX_TOKENS_DBT_GENERATION  = 1500   # dbt model + yaml + tests

# ── Snowflake query limits ─────────────────────────────────────────────────────
QUERY_HISTORY_LIMIT  = 20   # max recent queries to fetch
SAMPLE_ROWS_LIMIT    = 5    # max sample rows to send to Claude
MAX_COLUMNS_TO_SEND  = 20   # cap columns sent in metadata prompts

# ── Output paths ──────────────────────────────────────────────────────────────
OUTPUT_SQL_DIR   = "outputs/generated_sql"
OUTPUT_YAML_DIR  = "outputs/generated_yaml"
OUTPUT_REPORT_DIR = "outputs/reports"
