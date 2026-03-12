"""
app.py — Autonomous Analytics Engineer
Main Streamlit entry point. 3 tabs:
  1. Query Analyzer   — paste SQL, get analysis + optimized rewrite
  2. Table Explainer  — select a table, get business meaning + dbt tests
  3. dbt Generator    — describe what you want, get model SQL + schema.yml
"""

import time
import streamlit as st
from openai import OpenAI
from src.snowflake_client import (
    get_databases, get_schemas, get_tables,
    get_table_metadata, get_query_history,
)
from src.claude_client    import analyze_query, explain_metadata, generate_dbt
from src.prompts          import query_analysis_prompt, metadata_explanation_prompt, dbt_generation_prompt
from src.rules            import check_query, severity_score
from src.utils.sql_utils  import clean_sql, format_sql, trim_sql
from src.utils.formatting import (
    render_rule_flags, render_claude_output,
    render_sql_block, render_yaml_block, render_severity_badge,
)

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title = "Autonomous Analytics Engineer",
    page_icon  = "🤖",
    layout     = "wide",
)

st.title("🤖 Autonomous Analytics Engineer")
st.caption("AI-powered SQL analysis, metadata explanation, and dbt generation for Snowflake.")
st.divider()

# ── Sidebar: live connection status ───────────────────────────────────────────
with st.sidebar:
    st.header("System Status")

    # Ollama ping
    try:
        _ping_client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
        _t0 = time.perf_counter()
        _ping_client.models.list()          # lightweight call — just lists available models
        _ping_ms = int((time.perf_counter() - _t0) * 1000)
        st.success(f"Ollama  ✅  {_ping_ms}ms")
    except Exception as _e:
        st.error(f"Ollama  ❌  {_e}")

    from src.config import MODEL_SMART
    st.caption(f"Model: `{MODEL_SMART}`")
    st.caption("Logs: `logs/llm.log`")
    st.divider()
    st.caption("Each request is timed and logged to the terminal and log file.")

# ── 3 Tabs ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs([
    "🔍 Query Analyzer",
    "📋 Table Explainer",
    "🛠 dbt Generator",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — QUERY ANALYZER
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.header("Query Analyzer")
    st.write("Paste a SQL query or load one from your Snowflake query history.")

    # ── Input method toggle ────────────────────────────────────────────────────
    input_mode = st.radio(
        "Input method",
        ["Paste SQL manually", "Load from query history"],
        horizontal = True,
    )

    sql_input = ""

    if input_mode == "Paste SQL manually":
        sql_input = st.text_area(
            "Paste your SQL here",
            height      = 200,
            placeholder = "SELECT * FROM arr_program_fact WHERE ...",
        )

    else:
        # ── Load from Snowflake query history ──────────────────────────────────
        with st.spinner("Loading recent queries from Snowflake..."):
            try:
                history_df = get_query_history()
                if history_df.empty:
                    st.info("No recent SELECT queries found in query history.")
                else:
                    # let user pick from the dropdown
                    selected_idx = st.selectbox(
                        "Select a query",
                        options = range(len(history_df)),
                        format_func = lambda i: (
                            f"[{history_df.iloc[i]['ELAPSED_SECONDS']}s] "
                            f"{history_df.iloc[i]['QUERY_TEXT'][:80]}..."
                        ),
                    )
                    selected_row = history_df.iloc[selected_idx]
                    sql_input    = selected_row["QUERY_TEXT"]
                    st.caption(
                        f"⏱ {selected_row['ELAPSED_SECONDS']}s elapsed  |  "
                        f"💾 {selected_row['MB_SCANNED']} MB scanned  |  "
                        f"🗂 {selected_row['PARTITIONS_SCANNED']} / "
                        f"{selected_row['PARTITIONS_TOTAL']} partitions"
                    )
                    render_sql_block(format_sql(sql_input), "Selected Query")
            except Exception as e:
                st.error(f"Could not load query history: {e}")

    # ── Analysis ───────────────────────────────────────────────────────────────
    if st.button("🔍 Analyze Query", type="primary", disabled=not sql_input.strip()):
        with st.spinner("Running rule checks..."):
            clean   = clean_sql(sql_input)
            flags   = check_query(clean)
            score   = severity_score(flags)

        col1, col2 = st.columns([1, 2])

        with col1:
            render_severity_badge(score)
            render_rule_flags(flags)

        with col2:
            with st.spinner("Analyzing with AI..."):
                try:
                    trimmed  = trim_sql(clean)
                    prompt   = query_analysis_prompt(trimmed)
                    response = analyze_query(prompt)
                    render_claude_output(response)
                except Exception as e:
                    st.error(f"Claude API error: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — TABLE EXPLAINER
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.header("Table Explainer")
    st.write("Select a table to understand its business purpose, grain, and suggested tests.")

    # ── Cascading selectors: database → schema → table ─────────────────────────
    col1, col2, col3 = st.columns(3)

    with col1:
        try:
            databases = get_databases()
            selected_db = st.selectbox("Database", databases)
        except Exception as e:
            st.error(f"Cannot load databases: {e}")
            selected_db = None

    with col2:
        if selected_db:
            try:
                schemas = get_schemas(selected_db)
                selected_schema = st.selectbox("Schema", schemas)
            except Exception as e:
                st.error(f"Cannot load schemas: {e}")
                selected_schema = None
        else:
            selected_schema = None

    with col3:
        if selected_db and selected_schema:
            try:
                tables = get_tables(selected_db, selected_schema)
                selected_table = st.selectbox("Table", tables)
            except Exception as e:
                st.error(f"Cannot load tables: {e}")
                selected_table = None
        else:
            selected_table = None

    # ── Fetch metadata and explain ─────────────────────────────────────────────
    if st.button("📋 Explain Table", type="primary",
                 disabled=not (selected_db and selected_schema and selected_table)):

        with st.spinner("Fetching metadata from Snowflake..."):
            try:
                metadata = get_table_metadata(selected_db, selected_schema, selected_table)
            except Exception as e:
                st.error(f"Cannot fetch metadata: {e}")
                metadata = None

        if metadata:
            st.caption(
                f"📊 {metadata['row_count']:,} rows  |  "
                f"📐 {len(metadata['columns'])} columns"
            )

            # show columns as a table
            with st.expander("View column list"):
                import pandas as pd
                st.dataframe(pd.DataFrame(metadata["columns"]), use_container_width=True)

            # show sample rows
            with st.expander("View sample rows"):
                st.dataframe(pd.DataFrame(metadata["sample_rows"]), use_container_width=True)

            with st.spinner("Explaining with AI..."):
                try:
                    prompt   = metadata_explanation_prompt(metadata)
                    response = explain_metadata(prompt)
                    render_claude_output(response)
                except Exception as e:
                    st.error(f"Claude API error: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — dbt GENERATOR
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.header("dbt Generator")
    st.write("Describe what you want to build. The agent generates model SQL, schema.yml, and tests.")

    # ── Source table selection ─────────────────────────────────────────────────
    st.subheader("1. Pick a source table")
    col1, col2, col3 = st.columns(3)

    with col1:
        try:
            dbs_dbt = get_databases()
            dbt_db  = st.selectbox("Database", dbs_dbt, key="dbt_db")
        except:
            dbt_db = None

    with col2:
        if dbt_db:
            try:
                schemas_dbt = get_schemas(dbt_db)
                dbt_schema  = st.selectbox("Schema", schemas_dbt, key="dbt_schema")
            except:
                dbt_schema = None
        else:
            dbt_schema = None

    with col3:
        if dbt_db and dbt_schema:
            try:
                tables_dbt = get_tables(dbt_db, dbt_schema)
                dbt_table  = st.selectbox("Table", tables_dbt, key="dbt_table")
            except:
                dbt_table = None
        else:
            dbt_table = None

    # ── Business logic prompt ──────────────────────────────────────────────────
    st.subheader("2. Describe what you want to build")
    business_logic = st.text_area(
        "Business logic",
        height      = 120,
        placeholder = (
            "Example: Build a monthly ARR summary by program and region. "
            "Include total ARR, count of new deals, and flag churned programs."
        ),
    )

    # ── Generate ───────────────────────────────────────────────────────────────
    can_generate = bool(dbt_db and dbt_schema and dbt_table and business_logic.strip())

    if st.button("🛠 Generate dbt Model", type="primary", disabled=not can_generate):
        with st.spinner("Fetching columns from Snowflake..."):
            try:
                meta = get_table_metadata(dbt_db, dbt_schema, dbt_table)
                columns = meta["columns"]
            except Exception as e:
                st.error(f"Cannot fetch columns: {e}")
                columns = []

        if columns:
            with st.spinner("Generating dbt model with AI..."):
                try:
                    source_ref = f"{dbt_db}.{dbt_schema}.{dbt_table}"
                    prompt     = dbt_generation_prompt(source_ref, business_logic, columns)
                    response   = generate_dbt(prompt)
                    render_claude_output(response)

                    # ── Save outputs to files ──────────────────────────────────
                    import os, datetime
                    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_path = f"outputs/generated_sql/{dbt_table}_{ts}.md"
                    os.makedirs("outputs/generated_sql", exist_ok=True)
                    with open(output_path, "w") as f:
                        f.write(f"# Generated dbt model for {source_ref}\n\n")
                        f.write(response)
                    st.success(f"✅ Saved to `{output_path}`")

                except Exception as e:
                    st.error(f"Claude API error: {e}")
