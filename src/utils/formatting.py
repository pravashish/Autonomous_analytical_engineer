"""
formatting.py — helpers to render Claude output and rule flags in Streamlit.
Keeps all st.markdown / st.write calls out of the main app.py.
"""

import streamlit as st
from src.rules import RuleFlag


SEVERITY_COLOR = {
    "HIGH"   : "🔴",
    "MEDIUM" : "🟡",
    "LOW"    : "🟢",
}


def render_rule_flags(flags: list[RuleFlag]):
    """Renders deterministic rule flags as colored cards in Streamlit."""
    if not flags:
        st.success("✅ No rule-based issues detected.")
        return

    st.markdown("### 🔍 Rule-Based Checks")
    for flag in flags:
        icon = SEVERITY_COLOR.get(flag.severity, "⚪")
        with st.expander(f"{icon} [{flag.severity}] {flag.rule}"):
            st.write(flag.message)


def render_claude_output(text: str):
    """
    Renders Claude's structured markdown response.
    Claude is prompted to use ## headers — Streamlit renders these natively.
    """
    st.markdown("### 🤖 AI Analysis")
    st.markdown(text)


def render_sql_block(sql: str, label: str = "SQL"):
    """Renders a SQL code block with a copy button."""
    st.markdown(f"**{label}**")
    st.code(sql, language="sql")


def render_yaml_block(yaml_text: str, label: str = "schema.yml"):
    """Renders a YAML block with syntax highlighting."""
    st.markdown(f"**{label}**")
    st.code(yaml_text, language="yaml")


def render_severity_badge(score: int):
    """Renders a colored severity score badge (0-100)."""
    if score >= 60:
        st.error(f"Severity Score: {score}/100 — High Risk")
    elif score >= 30:
        st.warning(f"Severity Score: {score}/100 — Medium Risk")
    else:
        st.success(f"Severity Score: {score}/100 — Low Risk")
