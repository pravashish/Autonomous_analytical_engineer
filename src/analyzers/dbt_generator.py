"""
dbt_generator.py — generates dbt model SQL + schema.yml from a source table and prompt.
Also saves outputs to the outputs/ directory.
"""

import os
import re
import logging
from datetime import datetime
from dataclasses import dataclass
from src.snowflake_client import get_table_metadata
from src.claude_client    import generate_dbt
from src.prompts          import dbt_generation_prompt
from src.config           import OUTPUT_SQL_DIR, OUTPUT_YAML_DIR

logger = logging.getLogger("llm")


@dataclass
class DbtGenerationResult:
    """Everything the UI needs to render and download the generated dbt artifacts."""
    source_table   : str
    llm_response   : str = ""
    model_sql      : str = ""       # extracted model SQL block
    schema_yaml    : str = ""       # extracted schema.yml block
    saved_sql_path : str = ""
    saved_yml_path : str = ""
    llm_error      : str = ""
    success        : bool = True


def _extract_block(text: str, header: str) -> str:
    """
    Pulls the content between a ## header and the next ## header.
    Used to split Claude's structured response into individual sections.
    """
    pattern = rf"## {re.escape(header)}\s*(.*?)(?=\n## |\Z)"
    match   = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _extract_code_block(text: str) -> str:
    """Strips ```sql or ```yaml fences if present, returns raw code."""
    text  = text.strip()
    clean = re.sub(r"^```[a-z]*\n?", "", text)
    clean = re.sub(r"\n?```$", "", clean)
    return clean.strip()


def _save(content: str, directory: str, filename: str) -> str:
    """Saves content to a file, returns the path."""
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def run(database: str, schema: str, table: str, business_logic: str) -> DbtGenerationResult:
    """
    Full dbt generation pipeline:
      1. Fetch columns from Snowflake
      2. Build prompt
      3. Send to LLM
      4. Extract model SQL and schema.yml from response
      5. Save both to outputs/
      6. Return result
    """
    source_ref = f"{database}.{schema}.{table}"
    logger.info(f"dbt_generator.run() called for {source_ref}")

    # step 1 — fetch columns
    try:
        metadata = get_table_metadata(database, schema, table)
        columns  = metadata["columns"]
    except Exception as e:
        logger.error(f"column fetch failed: {e}")
        return DbtGenerationResult(
            source_table = source_ref,
            llm_error    = f"Could not fetch columns from Snowflake: {e}",
            success      = False,
        )

    # step 2 — LLM
    prompt = dbt_generation_prompt(source_ref, business_logic, columns)

    try:
        response = generate_dbt(prompt)
    except Exception as e:
        logger.error(f"dbt_generator LLM call failed: {e}")
        return DbtGenerationResult(
            source_table = source_ref,
            llm_error    = str(e),
            success      = False,
        )

    # step 3 — extract sections from structured response
    model_raw  = _extract_block(response, "Model SQL")
    schema_raw = _extract_block(response, "schema.yml")
    model_sql  = _extract_code_block(model_raw)  if model_raw  else ""
    schema_yml = _extract_code_block(schema_raw) if schema_raw else ""

    # step 4 — save to files
    ts        = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = table.lower().replace(" ", "_")

    sql_path = _save(
        model_sql or response,
        OUTPUT_SQL_DIR,
        f"{safe_name}_{ts}.sql",
    )
    yml_path = _save(
        schema_yml or "",
        OUTPUT_YAML_DIR,
        f"{safe_name}_{ts}.yml",
    )

    logger.info(f"dbt artifacts saved: {sql_path}, {yml_path}")

    return DbtGenerationResult(
        source_table   = source_ref,
        llm_response   = response,
        model_sql      = model_sql,
        schema_yaml    = schema_yml,
        saved_sql_path = sql_path,
        saved_yml_path = yml_path,
        success        = True,
    )
