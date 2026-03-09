"""
rules.py — deterministic SQL rule checks.
These run WITHOUT calling Claude (zero token cost).
They catch obvious anti-patterns before Claude even sees the query.
The results are merged with Claude's output in the UI.
"""

import re
from dataclasses import dataclass


@dataclass
class RuleFlag:
    """A single rule violation found in the SQL."""
    severity : str   # "HIGH" | "MEDIUM" | "LOW"
    rule     : str   # short rule name
    message  : str   # human-readable explanation


def check_query(sql: str) -> list[RuleFlag]:
    """
    Runs all rules against a SQL string.
    Returns a list of RuleFlag objects (empty list = no issues found).
    """
    sql_upper = sql.upper()
    flags: list[RuleFlag] = []

    # ── HIGH severity ──────────────────────────────────────────────────────────

    if re.search(r'\bSELECT\s+\*', sql_upper):
        flags.append(RuleFlag(
            severity = "HIGH",
            rule     = "SELECT *",
            message  = "SELECT * fetches all columns including unused ones. "
                       "Project only the columns you need to reduce data scanned."
        ))

    # count number of JOINs
    join_count = len(re.findall(r'\bJOIN\b', sql_upper))
    if join_count >= 5:
        flags.append(RuleFlag(
            severity = "HIGH",
            rule     = "Too many JOINs",
            message  = f"Found {join_count} JOINs. Queries with 5+ joins are hard to "
                       "maintain and likely to cause row explosion. Consider pre-aggregating."
        ))

    # cartesian join (cross join or join with no ON clause)
    if re.search(r'\bCROSS\s+JOIN\b', sql_upper):
        flags.append(RuleFlag(
            severity = "HIGH",
            rule     = "CROSS JOIN detected",
            message  = "CROSS JOIN multiplies every row from both tables. "
                       "Confirm this is intentional — it can create billions of rows."
        ))

    # no WHERE clause on a large fact-like query
    if "WHERE" not in sql_upper and join_count >= 1:
        flags.append(RuleFlag(
            severity = "HIGH",
            rule     = "No WHERE filter",
            message  = "No WHERE clause found on a multi-table query. "
                       "Without filters, Snowflake scans the entire table. "
                       "Add a date range or partition filter."
        ))

    # ── MEDIUM severity ────────────────────────────────────────────────────────

    # function on a filter/join column disables micro-partition pruning
    if re.search(r'(TO_DATE|DATE_TRUNC|YEAR|MONTH|CAST)\s*\(', sql_upper):
        if "WHERE" in sql_upper or "ON" in sql_upper:
            flags.append(RuleFlag(
                severity = "MEDIUM",
                rule     = "Function on filter column",
                message  = "Applying a function (TO_DATE, DATE_TRUNC, CAST) inside "
                           "a WHERE or JOIN ON clause prevents Snowflake from using "
                           "micro-partition pruning. Move the function to the other side."
            ))

    # repeated subqueries (same subquery appears more than once)
    subqueries = re.findall(r'\(SELECT[^)]+\)', sql_upper)
    if len(subqueries) > 1:
        unique_sq = set(subqueries)
        if len(unique_sq) < len(subqueries):
            flags.append(RuleFlag(
                severity = "MEDIUM",
                rule     = "Repeated subquery",
                message  = "The same subquery appears multiple times. "
                           "Extract it into a CTE (WITH clause) to avoid re-scanning."
            ))

    # no date filter but date column appears to exist
    date_cols = re.findall(r'\b\w*(DATE|PERIOD|MONTH|YEAR)\w*\b', sql_upper)
    if date_cols and "WHERE" in sql_upper:
        has_date_filter = any(
            col in sql_upper
            for col in ["DATE", "PERIOD", "MONTH", "YEAR"]
            if col in sql_upper.split("WHERE", 1)[-1]
        )
        if not has_date_filter:
            flags.append(RuleFlag(
                severity = "MEDIUM",
                rule     = "No date filter",
                message  = "Date-like columns found but no date filter in WHERE clause. "
                           "On large fact tables, always filter by date to limit partition scans."
            ))

    # ── LOW severity ──────────────────────────────────────────────────────────

    # ambiguous aliases (single-letter aliases like a, b, c)
    ambiguous = re.findall(r'\bAS\s+[A-Z]\b', sql_upper)
    if len(ambiguous) >= 3:
        flags.append(RuleFlag(
            severity = "LOW",
            rule     = "Ambiguous aliases",
            message  = f"Found {len(ambiguous)} single-letter aliases. "
                       "Use descriptive aliases (e.g. 'arr' instead of 'a') "
                       "to improve readability."
        ))

    # DISTINCT without GROUP BY (often a workaround for duplicates)
    if "DISTINCT" in sql_upper and "GROUP BY" not in sql_upper:
        flags.append(RuleFlag(
            severity = "LOW",
            rule     = "DISTINCT without GROUP BY",
            message  = "DISTINCT is used to remove duplicates but GROUP BY with "
                       "aggregation is usually more explicit and efficient."
        ))

    return flags


def severity_score(flags: list[RuleFlag]) -> int:
    """
    Returns a numeric severity score (0-100) for sorting queries by urgency.
    Used in the query history loader to rank worst queries first.
    """
    weights = {"HIGH": 30, "MEDIUM": 10, "LOW": 3}
    score = sum(weights.get(f.severity, 0) for f in flags)
    return min(score, 100)       # cap at 100
