"""
query_analyzer.py — combines the rule engine and LLM into one result object.
app.py calls run() and gets back everything it needs to render.
"""

import logging
from dataclasses import dataclass, field
from src.rules           import check_query, severity_score, RuleFlag
from src.claude_client   import analyze_query
from src.prompts         import query_analysis_prompt
from src.utils.sql_utils import clean_sql, trim_sql

logger = logging.getLogger("llm")


@dataclass
class QueryAnalysisResult:
    """Everything the UI needs to render a query analysis."""
    sql_cleaned    : str
    flags          : list[RuleFlag]
    severity       : int                  # 0-100, from rule engine only
    llm_response   : str = ""
    llm_error      : str = ""
    success        : bool = True


def run(sql: str, schema_context: str = "") -> QueryAnalysisResult:
    """
    Full analysis pipeline:
      1. Clean the SQL
      2. Run deterministic rule checks
      3. Send to LLM for deeper analysis
      4. Return combined result

    Never raises — errors are captured in the result object so the UI
    can show partial results even if the LLM call fails.
    """
    logger.info("query_analyzer.run() called")

    # step 1 — clean
    cleaned = clean_sql(sql)

    # step 2 — rules (zero cost, always runs)
    flags  = check_query(cleaned)
    score  = severity_score(flags)
    logger.info(f"rule engine: {len(flags)} flags, severity={score}")

    # step 3 — LLM
    trimmed = trim_sql(cleaned)
    prompt  = query_analysis_prompt(trimmed, schema_context)

    try:
        response = analyze_query(prompt)
        return QueryAnalysisResult(
            sql_cleaned  = cleaned,
            flags        = flags,
            severity     = score,
            llm_response = response,
            success      = True,
        )
    except Exception as e:
        logger.error(f"query_analyzer LLM call failed: {e}")
        return QueryAnalysisResult(
            sql_cleaned = cleaned,
            flags       = flags,
            severity    = score,
            llm_error   = str(e),
            success     = False,
        )
