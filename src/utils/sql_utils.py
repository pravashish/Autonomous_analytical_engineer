"""
sql_utils.py — SQL cleaning and trimming utilities.
Goal: reduce token count before sending SQL to Claude without losing meaning.
"""

import re
import sqlparse


def clean_sql(sql: str) -> str:
    """
    Removes comments and collapses whitespace.
    Always run this before sending SQL to Claude.
    """
    # remove single-line comments (-- ...)
    sql = re.sub(r'--[^\n]*', '', sql)

    # remove multi-line comments (/* ... */)
    sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)

    # collapse multiple whitespace/newlines into single space
    sql = re.sub(r'\s+', ' ', sql).strip()

    return sql


def format_sql(sql: str) -> str:
    """
    Pretty-prints SQL using sqlparse. Used for display in the UI.
    Not used before sending to Claude (use clean_sql for that).
    """
    return sqlparse.format(
        sql,
        reindent    = True,
        keyword_case= "upper",
        indent_width= 4,
    )


def trim_sql(sql: str, max_chars: int = 3000) -> str:
    """
    Hard-trims SQL to max_chars to stay within token budget.
    Appends a note if truncated so Claude knows the SQL is incomplete.
    """
    sql = clean_sql(sql)
    if len(sql) <= max_chars:
        return sql
    return sql[:max_chars] + "\n-- [SQL TRUNCATED FOR ANALYSIS — showing first 3000 chars]"


def extract_table_names(sql: str) -> list[str]:
    """
    Roughly extracts table names from a SQL string using regex.
    Not perfect — use for display hints only, not logic.
    Finds identifiers after FROM and JOIN keywords.
    """
    sql_upper = sql.upper()
    pattern   = r'(?:FROM|JOIN)\s+([\w.]+)'
    matches   = re.findall(pattern, sql_upper)

    # deduplicate and exclude CTEs (usually short names without dots)
    tables = list({m for m in matches if "." in m or len(m) > 4})
    return tables
