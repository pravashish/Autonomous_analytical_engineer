"""
prompts.py — all Claude prompt templates live here.
Separated from logic so prompts can be tuned without touching business code.
Each function takes structured inputs and returns a ready-to-send string.
"""

import json


def query_analysis_prompt(sql: str, schema_context: str = "") -> str:
    """
    Prompt for the Query Analyzer tab.
    Asks Claude to return structured sections so the UI can parse them cleanly.
    """
    schema_section = f"\n\nSchema context:\n{schema_context}" if schema_context else ""

    return f"""You are a senior Snowflake data engineer reviewing a SQL query for performance issues.

Analyze the query below and respond in EXACTLY this format with these section headers:

## Query Intent
One sentence describing what this query does.

## Issues Found
Bullet list of specific problems found (e.g. SELECT *, missing filters, cartesian join risk).
If none found, write "No major issues detected."

## Performance Risks
Bullet list of performance risks ranked by severity (High / Medium / Low).

## Recommendations
Numbered list of concrete changes to make, most impactful first.

## Optimized SQL
The rewritten SQL with your recommendations applied. Include comments explaining key changes.

## Confidence
One of: High / Medium / Low — how confident you are in this analysis.
{schema_section}

SQL to analyze:
```sql
{sql}
```"""


def metadata_explanation_prompt(metadata: dict) -> str:
    """
    Prompt for the Table Explainer tab.
    Sends column names, types, and sample rows. Asks for business interpretation.
    """
    columns_text = "\n".join([
        f"  - {col['COLUMN_NAME']} ({col['DATA_TYPE']}, nullable={col['IS_NULLABLE']})"
        for col in metadata["columns"]
    ])

    sample_text = json.dumps(metadata["sample_rows"], indent=2, default=str)

    return f"""You are a data engineer analyzing a Snowflake table to understand its business purpose.

Table: {metadata['database']}.{metadata['schema']}.{metadata['table']}
Row count: {metadata['row_count']:,}

Columns:
{columns_text}

Sample rows (up to 5):
{sample_text}

Respond in EXACTLY this format:

## Likely Purpose
One paragraph describing what this table probably represents in the business.

## Probable Grain
One sentence: "One row represents..."

## Key Dimensions
Bullet list of columns that are categorical/descriptive (who, what, where).

## Key Metrics
Bullet list of columns that are numeric measures.

## Candidate Primary Key
The column(s) that likely uniquely identify each row.

## Likely Foreign Keys
Columns that look like they join to other tables (e.g. _sk, _id suffixes).

## Suggested dbt Tests
YAML snippet of recommended dbt tests for this table's most important columns."""


def dbt_generation_prompt(source_table: str, business_logic: str, columns: list) -> str:
    """
    Prompt for the dbt Generator tab.
    Takes a source table name, the user's business logic description, and column list.
    Returns model SQL + schema.yml + assumptions.
    """
    columns_text = "\n".join([
        f"  - {col['COLUMN_NAME']} ({col['DATA_TYPE']})"
        for col in columns
    ])

    return f"""You are a senior dbt developer. Generate a production-ready dbt model based on the inputs below.

Source table: {source_table}

Available columns:
{columns_text}

Business logic requested:
{business_logic}

Respond in EXACTLY this format:

## Model SQL
A complete dbt model SQL file using CTE style.
Use {{ source() }} or {{ ref() }} — never hardcode database names.
Include comments explaining each CTE.

## schema.yml
A complete dbt schema.yml for this model with:
- model description
- column descriptions
- data_tests (not_null, unique, accepted_values where appropriate)

## Assumptions Made
Bullet list of assumptions you made about business logic or data.

## Suggested Downstream Models
Bullet list of models that could logically be built on top of this one."""
