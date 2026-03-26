"""
app.py — Autonomous Analytics Engineer
Streamlit entry point. 3 tabs, each backed by an analyzer module.
"""

import time
import pandas as pd
import streamlit as st
from openai import OpenAI

from src.snowflake_client import get_databases, get_schemas, get_tables, get_query_history
from src.analyzers.query_analyzer    import run as analyze_sql
from src.analyzers.metadata_explainer import run as explain_table
from src.analyzers.dbt_generator      import run as generate_dbt_model
from src.utils.formatting import render_rule_flags, render_claude_output, render_severity_badge
from src.utils.sql_utils  import format_sql
from src.config import MODEL_SMART

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title = "Autonomous Analytics Engineer",
    page_icon  = "🤖",
    layout     = "wide",
)

# ── Sidebar: live status ───────────────────────────────────────────────────────
with st.sidebar:
    st.header("System Status")
    try:
        _c = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
        _t = time.perf_counter()
        _c.models.list()
        st.success(f"Ollama  ✅  {int((time.perf_counter()-_t)*1000)}ms")
    except Exception as _e:
        st.error(f"Ollama  ❌  not running")
    st.caption(f"Model: `{MODEL_SMART}`")
    st.caption("Logs → `logs/llm.log`")

# ── Header ─────────────────────────────────────────────────────────────────────
st.title("🤖 Autonomous Analytics Engineer")
st.caption("SQL analysis · table documentation · dbt generation — runs locally with Ollama.")
st.divider()

tab1, tab2, tab3 = st.tabs(["🔍 Query Analyzer", "📋 Table Explainer", "🛠 dbt Generator"])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — QUERY ANALYZER
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.header("Query Analyzer")

    input_mode = st.radio(
        "Input method",
        ["Paste SQL manually", "Load from Snowflake query history"],
        horizontal=True,
    )

    sql_input = ""

    if input_mode == "Paste SQL manually":
        sql_input = st.text_area(
            "SQL",
            height=200,
            placeholder="SELECT * FROM arr_program_fact WHERE ...",
        )
    else:
        with st.spinner("Loading query history from Snowflake..."):
            try:
                history_df = get_query_history()
                if history_df.empty:
                    st.info("No recent SELECT queries found.")
                else:
                    idx = st.selectbox(
                        "Select a query (sorted by slowest first)",
                        range(len(history_df)),
                        format_func=lambda i: (
                            f"[{history_df.iloc[i]['ELAPSED_SECONDS']}s] "
                            f"{str(history_df.iloc[i]['QUERY_TEXT'])[:80]}..."
                        ),
                    )
                    row      = history_df.iloc[idx]
                    sql_input = row["QUERY_TEXT"]

                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Total Elapsed",   f"{row['ELAPSED_SECONDS']}s")
                    c2.metric("MB Scanned",      f"{row['MB_SCANNED']} MB")
                    c3.metric("Rows Produced",   f"{int(row['ROWS_PRODUCED']):,}")
                    c4.metric("Warehouse",       row['WAREHOUSE_NAME'])

                    with st.expander("View full query"):
                        st.code(format_sql(sql_input), language="sql")
            except Exception as e:
                st.error(f"Could not load query history: {e}")

    if st.button("🔍 Analyze", type="primary", disabled=not sql_input.strip(), key="btn_analyze"):
        with st.spinner("Running rule checks + AI analysis..."):
            result = analyze_sql(sql_input)

        # ── Results layout ─────────────────────────────────────────────────
        col_left, col_right = st.columns([1, 2])

        with col_left:
            render_severity_badge(result.severity)
            st.divider()
            render_rule_flags(result.flags)

        with col_right:
            if result.success:
                render_claude_output(result.llm_response)
                st.divider()
                st.download_button(
                    label     = "⬇ Download analysis",
                    data      = result.llm_response,
                    file_name = "query_analysis.md",
                    mime      = "text/markdown",
                )
            else:
                st.error(f"AI analysis failed: {result.llm_error}")
                st.info("Rule-based checks above still ran successfully.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — TABLE EXPLAINER
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.header("Table Explainer")
    st.caption("Select a table to understand its purpose, grain, and suggested tests.")

    c1, c2, c3 = st.columns(3)

    with c1:
        try:
            selected_db = st.selectbox("Database", get_databases(), key="exp_db")
        except Exception as e:
            st.error(f"Cannot load databases: {e}")
            selected_db = None

    with c2:
        selected_schema = None
        if selected_db:
            try:
                selected_schema = st.selectbox("Schema", get_schemas(selected_db), key="exp_schema")
            except Exception as e:
                st.error(f"Cannot load schemas: {e}")

    with c3:
        selected_table = None
        if selected_db and selected_schema:
            try:
                selected_table = st.selectbox("Table", get_tables(selected_db, selected_schema), key="exp_table")
            except Exception as e:
                st.error(f"Cannot load tables: {e}")

    if st.button("📋 Explain Table", type="primary",
                 disabled=not (selected_db and selected_schema and selected_table),
                 key="btn_explain"):

        with st.spinner(f"Fetching {selected_table} metadata + running AI analysis..."):
            result = explain_table(selected_db, selected_schema, selected_table)

        if not result.success and not result.columns:
            st.error(f"Failed to fetch metadata: {result.llm_error}")
        else:
            # ── Table stats ────────────────────────────────────────────────
            m1, m2 = st.columns(2)
            m1.metric("Rows",    f"{result.row_count:,}")
            m2.metric("Columns", result.column_count)

            col_left, col_right = st.columns([1, 1])

            with col_left:
                with st.expander("Column list", expanded=True):
                    st.dataframe(
                        pd.DataFrame(result.columns),
                        use_container_width=True,
                        hide_index=True,
                    )
                with st.expander("Sample rows"):
                    st.dataframe(
                        pd.DataFrame(result.sample_rows),
                        use_container_width=True,
                        hide_index=True,
                    )

            with col_right:
                if result.success:
                    render_claude_output(result.llm_response)
                    st.divider()
                    st.download_button(
                        label     = "⬇ Download explanation",
                        data      = result.llm_response,
                        file_name = f"{result.table}_explanation.md",
                        mime      = "text/markdown",
                    )
                else:
                    st.error(f"AI explanation failed: {result.llm_error}")
                    st.info("Metadata above was fetched successfully.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — dbt GENERATOR
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.header("dbt Generator")
    st.caption("Describe what you want. Get back model SQL, schema.yml, and tests.")

    # ── Source table ───────────────────────────────────────────────────────────
    st.subheader("1. Pick a source table")
    c1, c2, c3 = st.columns(3)

    with c1:
        try:
            dbt_db = st.selectbox("Database", get_databases(), key="dbt_db")
        except:
            dbt_db = None

    with c2:
        dbt_schema = None
        if dbt_db:
            try:
                dbt_schema = st.selectbox("Schema", get_schemas(dbt_db), key="dbt_schema")
            except:
                pass

    with c3:
        dbt_table = None
        if dbt_db and dbt_schema:
            try:
                dbt_table = st.selectbox("Table", get_tables(dbt_db, dbt_schema), key="dbt_table")
            except:
                pass

    # ── Business logic ─────────────────────────────────────────────────────────
    st.subheader("2. Describe what you want to build")
    business_logic = st.text_area(
        "Business logic",
        height=100,
        placeholder=(
            "e.g. Monthly ARR by program and region. "
            "Include total ARR, count of programs, flag churned rows."
        ),
    )

    ready = bool(dbt_db and dbt_schema and dbt_table and business_logic.strip())

    if st.button("🛠 Generate dbt Model", type="primary", disabled=not ready, key="btn_dbt"):
        with st.spinner("Fetching columns + generating dbt artifacts..."):
            result = generate_dbt_model(dbt_db, dbt_schema, dbt_table, business_logic)

        if not result.success:
            st.error(f"Generation failed: {result.llm_error}")
        else:
            st.success(f"Generated for `{result.source_table}`")

            col_left, col_right = st.columns(2)

            with col_left:
                st.markdown("#### Model SQL")
                if result.model_sql:
                    st.code(result.model_sql, language="sql")
                    st.download_button(
                        label     = "⬇ Download model SQL",
                        data      = result.model_sql,
                        file_name = f"{dbt_table.lower()}.sql",
                        mime      = "text/plain",
                        key       = "dl_sql",
                    )
                else:
                    st.markdown(result.llm_response)

            with col_right:
                st.markdown("#### schema.yml")
                if result.schema_yaml:
                    st.code(result.schema_yaml, language="yaml")
                    st.download_button(
                        label     = "⬇ Download schema.yml",
                        data      = result.schema_yaml,
                        file_name = f"{dbt_table.lower()}_schema.yml",
                        mime      = "text/plain",
                        key       = "dl_yml",
                    )

            if result.saved_sql_path:
                st.caption(f"Saved to `{result.saved_sql_path}` and `{result.saved_yml_path}`")
