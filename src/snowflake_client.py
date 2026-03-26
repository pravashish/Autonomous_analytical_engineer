"""
snowflake_client.py — all Snowflake interactions live here.
The rest of the app never imports snowflake-connector directly.
Uses st.cache_data to avoid repeat API calls (saves cost + latency).
"""

import streamlit as st
import snowflake.connector
import pandas as pd
from src.config import (
    SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD,
    SNOWFLAKE_ROLE, SNOWFLAKE_WAREHOUSE, SNOWFLAKE_DATABASE,
    SNOWFLAKE_SCHEMA, QUERY_HISTORY_LIMIT, SAMPLE_ROWS_LIMIT,
    MAX_COLUMNS_TO_SEND
)


# ── Connection ─────────────────────────────────────────────────────────────────

@st.cache_resource                          # one connection per session
def get_connection():
    """
    Creates and caches a Snowflake connection for the whole Streamlit session.
    cache_resource means it is created once and reused — not recreated on every rerun.
    """
    return snowflake.connector.connect(
        account   = SNOWFLAKE_ACCOUNT,
        user      = SNOWFLAKE_USER,
        password  = SNOWFLAKE_PASSWORD,
        role      = SNOWFLAKE_ROLE,
        warehouse = SNOWFLAKE_WAREHOUSE,
        database  = SNOWFLAKE_DATABASE,
        schema    = SNOWFLAKE_SCHEMA,
    )


def run_query(sql: str) -> pd.DataFrame:
    """
    Runs any SQL and returns a pandas DataFrame.
    Used internally by all fetch functions below.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(sql)
    cols = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    return pd.DataFrame(rows, columns=cols)


# ── Schema navigation ──────────────────────────────────────────────────────────

@st.cache_data(ttl=300)                     # cache for 5 minutes
def get_databases() -> list[str]:
    """Returns list of all databases the user can see."""
    df = run_query("SHOW DATABASES")
    return df["name"].tolist()


@st.cache_data(ttl=300)
def get_schemas(database: str) -> list[str]:
    """Returns list of schemas in a given database."""
    df = run_query(f"SHOW SCHEMAS IN DATABASE {database}")
    # exclude Snowflake system schemas
    system = {"INFORMATION_SCHEMA", "PUBLIC"}
    return [s for s in df["name"].tolist() if s not in system]


@st.cache_data(ttl=300)
def get_tables(database: str, schema: str) -> list[str]:
    """Returns list of tables and views in a given schema."""
    df = run_query(f"SHOW TABLES IN SCHEMA {database}.{schema}")
    return df["name"].tolist()


# ── Table metadata ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def get_columns(database: str, schema: str, table: str) -> pd.DataFrame:
    """
    Fetches column names, data types, and nullability from INFORMATION_SCHEMA.
    This is what the Table Explainer tab uses.
    """
    sql = f"""
        SELECT
            COLUMN_NAME,
            DATA_TYPE,
            IS_NULLABLE,
            CHARACTER_MAXIMUM_LENGTH,
            NUMERIC_PRECISION,
            COLUMN_DEFAULT,
            ORDINAL_POSITION
        FROM {database}.INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = '{schema}'
          AND TABLE_NAME   = '{table}'
        ORDER BY ORDINAL_POSITION
    """
    return run_query(sql)


@st.cache_data(ttl=300)
def get_sample_rows(database: str, schema: str, table: str) -> pd.DataFrame:
    """
    Fetches a small sample of rows for context.
    Capped at SAMPLE_ROWS_LIMIT to control tokens sent to Claude.
    """
    sql = f"SELECT * FROM {database}.{schema}.{table} LIMIT {SAMPLE_ROWS_LIMIT}"
    return run_query(sql)


@st.cache_data(ttl=600)
def get_row_count(database: str, schema: str, table: str) -> int:
    """Returns approximate row count using Snowflake metadata — no full scan."""
    sql = f"""
        SELECT ROW_COUNT
        FROM {database}.INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = '{schema}'
          AND TABLE_NAME   = '{table}'
    """
    df = run_query(sql)
    if df.empty or df["ROW_COUNT"].iloc[0] is None:
        return 0
    return int(df["ROW_COUNT"].iloc[0])


def get_table_metadata(database: str, schema: str, table: str) -> dict:
    """
    Bundles columns, sample rows, and row count into one dict.
    This is what gets passed to Claude for metadata explanation.
    Caps columns at MAX_COLUMNS_TO_SEND to control token usage.
    """
    cols_df   = get_columns(database, schema, table)
    sample_df = get_sample_rows(database, schema, table)
    row_count = get_row_count(database, schema, table)

    # cap columns to avoid sending huge schemas to Claude
    cols_capped = cols_df.head(MAX_COLUMNS_TO_SEND)

    return {
        "database"   : database,
        "schema"     : schema,
        "table"      : table,
        "row_count"  : row_count,
        "columns"    : cols_capped.to_dict(orient="records"),
        "sample_rows": sample_df.to_dict(orient="records"),
    }


# ── Query history ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=120)                     # refresh every 2 min
def get_query_history() -> pd.DataFrame:
    """
    Fetches the most recent slow/expensive queries from QUERY_HISTORY.
    Ordered by execution time descending (slowest first).
    Only returns SELECT queries to avoid showing DDL/admin noise.
    """
    sql = f"""
        SELECT
            QUERY_ID,
            QUERY_TEXT,
            DATABASE_NAME,
            SCHEMA_NAME,
            EXECUTION_STATUS,
            ROUND(TOTAL_ELAPSED_TIME / 1000, 2)   AS ELAPSED_SECONDS,
            ROUND(BYTES_SCANNED / 1024 / 1024, 2) AS MB_SCANNED,
            ROWS_PRODUCED,
            ROUND(COMPILATION_TIME / 1000, 2)      AS COMPILATION_SECONDS,
            ROUND(EXECUTION_TIME / 1000, 2)        AS EXECUTION_SECONDS,
            START_TIME,
            USER_NAME,
            WAREHOUSE_NAME
        FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY(
            RESULT_LIMIT => {QUERY_HISTORY_LIMIT}
        ))
        WHERE QUERY_TYPE = 'SELECT'
          AND EXECUTION_STATUS = 'SUCCESS'
        ORDER BY TOTAL_ELAPSED_TIME DESC
    """
    return run_query(sql)
