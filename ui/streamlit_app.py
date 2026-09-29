"""Launch with: streamlit run ui/streamlit_app.py"""
from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from app.adapters import EXAMPLES
from app.contracts import STEPS
from app.pipeline_service import MODE_DEMO, create_service
from ui.theme import CSS, notice, page_header, pipeline_html, schema_row

st.set_page_config(page_title="ERP Intelligence — Text to SQL", page_icon="▦", layout="wide",
                   initial_sidebar_state="collapsed")
st.markdown(CSS, unsafe_allow_html=True)

MODE = os.getenv("ERP_APP_MODE", MODE_DEMO).strip().lower()


@st.cache_resource(show_spinner=False)
def cached_service(mode):
    return create_service(mode)


service = cached_service(MODE)


def clear_query():
    st.session_state.question = ""
    st.session_state.response = None
    st.session_state.example = "Choose an example…"


def choose_example():
    selected = st.session_state.example
    if selected in EXAMPLES:
        st.session_state.question = EXAMPLES[selected]


def fmt_seconds(value):
    return "—" if value is None else f"{value * 1000:.1f} ms"


st.session_state.setdefault("question", "")
st.session_state.setdefault("response", None)
st.session_state.setdefault("example", "Choose an example…")
st.markdown(page_header(MODE), unsafe_allow_html=True)

st.markdown('<div class="section-kicker">Report request</div><div class="section-title">Ask an English ERP question</div>',
            unsafe_allow_html=True)
left, right = st.columns([3.4, 1.3], gap="large")
with left:
    st.text_area("Question", key="question", height=118, label_visibility="collapsed",
                 placeholder="Example: Show monthly sales totals by region for the current fiscal year.",
                 max_chars=2000)
with right:
    st.selectbox("Example scenario", ["Choose an example…", *EXAMPLES], key="example",
                 on_change=choose_example)
    generate = st.button("Generate & Run", type="primary", width="stretch")
    st.button("Clear", on_click=clear_query, width="stretch",
              disabled=not st.session_state.question and st.session_state.response is None)

status_slot = st.empty()
current = st.session_state.response
status_slot.markdown(pipeline_html(current.steps if current else dict.fromkeys(STEPS, "waiting")),
                     unsafe_allow_html=True)

if generate:
    def progress(steps):
        status_slot.markdown(pipeline_html(steps), unsafe_allow_html=True)

    with st.spinner("Preparing the report…"):
        st.session_state.response = service.run(st.session_state.question, on_progress=progress)
    current = st.session_state.response
    status_slot.markdown(pipeline_html(current.steps), unsafe_allow_html=True)

st.markdown('<div class="section-kicker">Analysis output</div><div class="section-title">Report workspace</div>',
            unsafe_allow_html=True)
result_tab, sql_tab, schema_tab, details_tab = st.tabs(
    ["Result", "Generated SQL", "Retrieved Schema", "Execution Details"])

with result_tab:
    if current is None:
        st.markdown(notice("Choose a synthetic scenario or enter a question to inspect the pipeline."), unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="metric-strip"><div class="mini-metric"><div class="mini-label">Status</div>'
                    f'<div class="mini-value">{current.status.replace("_", " ").title()}</div></div>'
                    f'<div class="mini-metric"><div class="mini-label">Returned rows</div><div class="mini-value">{current.row_count:,}</div></div>'
                    f'<div class="mini-metric"><div class="mini-label">Total latency</div><div class="mini-value">{fmt_seconds(current.timings.get("total"))}</div></div></div>',
                    unsafe_allow_html=True)
        if current.status == "SUCCESS":
            if current.rows:
                # Object dtype keeps Persian/Unicode values intact and avoids unwanted numeric coercion.
                frame = pd.DataFrame(current.rows, columns=current.columns, dtype=object)
                st.dataframe(frame, width="stretch", hide_index=True)
            else:
                st.markdown(notice("The query completed successfully and returned no matching rows.", "success"), unsafe_allow_html=True)
        elif current.status == "VALIDATION_REJECTED":
            st.markdown(notice(current.validation_message, "error"), unsafe_allow_html=True)
        elif current.status == "INSUFFICIENT_SCHEMA":
            st.markdown(notice("The available schema context was insufficient to generate a safe query."), unsafe_allow_html=True)
        else:
            st.markdown(notice(current.error or "The request could not be completed.", "error"), unsafe_allow_html=True)

with sql_tab:
    validation = current.validation_status if current else "waiting"
    st.caption(f"Validation: {validation.replace('_', ' ').title()}  ·  Read-only execution")
    if current and current.generated_sql:
        st.code(current.generated_sql, language="sql", line_numbers=True)
    else:
        st.markdown(notice("Generated T-SQL will appear here. SQL is view-only."), unsafe_allow_html=True)

with schema_tab:
    if current and current.retrieved_tables:
        st.caption("Final order provided by the pipeline. Scores appear only when supplied by the adapter.")
        for table in current.retrieved_tables:
            st.markdown(schema_row(table.rank, table.name, table.summary, table.score), unsafe_allow_html=True)
    else:
        st.markdown(notice("No schema context is available for this request."), unsafe_allow_html=True)

with details_tab:
    if current:
        timing_rows = [{"Stage": name.title(), "Latency": fmt_seconds(current.timings.get(name))}
                       for name in (*STEPS, "total")]
        st.dataframe(timing_rows, width="stretch", hide_index=True)
        a, b, c = st.columns(3)
        a.metric("Validation", current.validation_status.replace("_", " ").title())
        b.metric("Execution", current.execution_status.replace("_", " ").title())
        c.metric("Rows", current.row_count)
        st.caption("Operational details are intentionally sanitized. Credentials, connection strings, and benchmark provenance are never shown.")
    else:
        st.markdown(notice("Timing and operational metadata will appear after a run."), unsafe_allow_html=True)
