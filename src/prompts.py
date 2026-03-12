"""
prompts.py — LLM prompt templates. Kept concise to reduce CPU processing time.
"""

import json


def query_analysis_prompt(sql: str, schema_context: str = "") -> str:
    schema_section = f"\nSchema:\n{schema_context}" if schema_context else ""
    return f"""You are a Snowflake SQL performance expert. Analyze this SQL query.

Respond using ONLY these exact headers:

## Query Intent
One sentence.

## Issues Found
Bullet list of problems (SELECT *, missing filters, bad joins, etc). Write "None" if clean.

## Performance Risks
Bullet list: [High/Medium/Low] risk and why.

## Recommendations
Numbered list, most impactful first.

## Optimized SQL
Rewritten SQL with inline comments on key changes.

## Confidence
High / Medium / Low
{schema_section}

SQL:
```sql
{sql}
```"""


def metadata_explanation_prompt(metadata: dict) -> str:
    cols = "\n".join(
        f"  {c['COLUMN_NAME']} {c['DATA_TYPE']} nullable={c['IS_NULLABLE']}"
        for c in metadata["columns"]
    )
    sample = json.dumps(metadata["sample_rows"], indent=2, default=str)

    return f"""You are a data engineer. Explain this Snowflake table.

Table: {metadata['database']}.{metadata['schema']}.{metadata['table']}
Rows: {metadata['row_count']:,}

Columns:
{cols}

Sample (5 rows):
{sample}

Respond using ONLY these exact headers:

## Likely Purpose
One paragraph.

## Probable Grain
One sentence starting with "One row represents..."

## Key Dimensions
Bullet list of categorical columns.

## Key Metrics
Bullet list of numeric measure columns.

## Candidate Primary Key
Column(s) that uniquely identify each row.

## Likely Foreign Keys
Columns that join to other tables (_sk, _id suffixes).

## Suggested dbt Tests
Short YAML snippet for the most important columns only."""


def dbt_generation_prompt(source_table: str, business_logic: str, columns: list) -> str:
    cols = "\n".join(
        f"  {c['COLUMN_NAME']} ({c['DATA_TYPE']})"
        for c in columns
    )
    return f"""You are a dbt developer. Generate a dbt model for this request.

Source: {source_table}
Columns:
{cols}

Request: {business_logic}

Respond using ONLY these exact headers:

## Model SQL
Complete dbt SQL using CTEs. Use {{{{ source() }}}} or {{{{ ref() }}}}. Add brief comments per CTE.

## schema.yml
Complete schema.yml with description, column descriptions, and data_tests.

## Assumptions Made
Bullet list.

## Suggested Downstream Models
Bullet list."""
