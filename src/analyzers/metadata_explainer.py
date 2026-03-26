"""
metadata_explainer.py — fetches table metadata from Snowflake and explains it via LLM.
"""

import logging
from dataclasses import dataclass
from src.snowflake_client import get_table_metadata
from src.claude_client    import explain_metadata
from src.prompts          import metadata_explanation_prompt

logger = logging.getLogger("llm")


@dataclass
class MetadataResult:
    """Everything the UI needs to render a table explanation."""
    database       : str
    schema         : str
    table          : str
    row_count      : int
    column_count   : int
    columns        : list        # raw column dicts for the dataframe view
    sample_rows    : list        # raw sample rows for the dataframe view
    llm_response   : str = ""
    llm_error      : str = ""
    success        : bool = True


def run(database: str, schema: str, table: str) -> MetadataResult:
    """
    Full metadata explanation pipeline:
      1. Fetch columns, sample rows, row count from Snowflake
      2. Build prompt
      3. Send to LLM
      4. Return combined result
    """
    logger.info(f"metadata_explainer.run() called for {database}.{schema}.{table}")

    # step 1 — fetch from Snowflake
    try:
        metadata = get_table_metadata(database, schema, table)
    except Exception as e:
        logger.error(f"metadata fetch failed: {e}")
        return MetadataResult(
            database     = database,
            schema       = schema,
            table        = table,
            row_count    = 0,
            column_count = 0,
            columns      = [],
            sample_rows  = [],
            llm_error    = f"Could not fetch metadata from Snowflake: {e}",
            success      = False,
        )

    # step 2 — LLM
    prompt = metadata_explanation_prompt(metadata)

    try:
        response = explain_metadata(prompt)
        return MetadataResult(
            database     = database,
            schema       = schema,
            table        = table,
            row_count    = metadata["row_count"],
            column_count = len(metadata["columns"]),
            columns      = metadata["columns"],
            sample_rows  = metadata["sample_rows"],
            llm_response = response,
            success      = True,
        )
    except Exception as e:
        logger.error(f"metadata_explainer LLM call failed: {e}")
        return MetadataResult(
            database     = database,
            schema       = schema,
            table        = table,
            row_count    = metadata["row_count"],
            column_count = len(metadata["columns"]),
            columns      = metadata["columns"],
            sample_rows  = metadata["sample_rows"],
            llm_error    = str(e),
            success      = False,
        )
