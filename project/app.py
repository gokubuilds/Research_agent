import streamlit as st
import time
import sys
import os
import html

# Import the compiled graph from research_agent.py
from research_agent import graph

# -------------------------------------------------
# Page config
# -------------------------------------------------
st.set_page_config(
    page_title="Research Agent",
    page_icon="📚",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# -------------------------------------------------
# Styling — warm paper/editorial theme (light, calm, readable)
# -------------------------------------------------
st.markdown("""
    <style>
    .stApp {
        background-color: #faf7f2;
        color: #2b2620;
    }

    /* Header */
    .header-wrap {
        text-align: center;
        padding: 2.2rem 0 0.6rem 0;
        border-bottom: 2px solid #e8dfd0;
        margin-bottom: 1.6rem;
    }
    .header-title {
        font-family: 'Georgia', 'Times New Roman', serif;
        font-size: 2.4rem;
        font-weight: 700;
        color: #2b2620;
        letter-spacing: -0.5px;
        margin-bottom: 0.2rem;
    }
    .header-sub {
        font-family: 'Trebuchet MS', sans-serif;
        color: #8a7d68;
        font-size: 1rem;
        font-style: italic;
        margin-bottom: 1.4rem;
    }

    /* Input box */
    .stTextInput input {
        background-color: #ffffff;
        border: 1.5px solid #d8cbb0;
        border-radius: 6px;
        padding: 0.7rem;
        font-size: 1rem;
        color: #2b2620;
    }
    .stTextInput input:focus {
        border-color: #b5824a;
        box-shadow: 0 0 0 1px #b5824a;
    }

    /* Button */
    div.stButton > button {
        background-color: #a8632f;
        color: #fff8ef;
        border: none;
        border-radius: 6px;
        padding: 0.6rem 1.4rem;
        font-weight: 600;
        font-family: 'Trebuchet MS', sans-serif;
        letter-spacing: 0.3px;
        transition: background-color 0.2s ease;
    }
    div.stButton > button:hover {
        background-color: #8a4f24;
        color: #fff8ef;
    }

    /* Status card */
    .status-card {
        background-color: #fffaf2;
        border-left: 4px solid #b5824a;
        border-radius: 4px;
        padding: 0.8rem 1rem;
        margin: 1rem 0;
        font-family: 'Trebuchet MS', sans-serif;
        color: #5c4b32;
    }

    /* Section heading inside tabs */
    .section-heading {
        font-family: 'Georgia', serif;
        font-size: 1.3rem;
        color: #2b2620;
        border-bottom: 1px solid #e8dfd0;
        padding-bottom: 0.4rem;
        margin-bottom: 1rem;
    }

    /* Fact row */
    .fact-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        background-color: #ffffff;
        border: 1px solid #ece3d3;
        border-left: 4px solid #b5824a;
        border-radius: 6px;
        padding: 0.75rem 1rem;
        margin: 0.55rem 0;
        font-family: 'Trebuchet MS', sans-serif;
        color: #3a3226;
    }
    .fact-text {
        flex: 1;
        line-height: 1.4;
    }
    .confidence-badge {
        border-radius: 20px;
        padding: 0.2rem 0.75rem;
        font-size: 0.78rem;
        font-weight: 700;
        white-space: nowrap;
        font-family: 'Trebuchet MS', sans-serif;
    }

    /* Source tag */
    .source-tag {
        display: flex;
        align-items: center;
        gap: 0.55rem;
        background-color: #ffffff;
        border: 1px solid #e8dfd0;
        border-left: 4px solid #6b8f71;
        border-radius: 6px;
        color: #3a3226;
        padding: 0.6rem 1rem;
        margin: 0.5rem 0;
        font-family: 'Trebuchet MS', sans-serif;
        font-size: 0.92rem;
        transition: background-color 0.15s ease;
    }
    .source-tag .source-icon {
        flex: 0 0 auto;
        line-height: 1;
    }
    .source-tag a {
        color: #0068c9;
        line-height: 1.35;
        overflow-wrap: anywhere;
        text-decoration: underline;
    }
    .source-tag:hover {
        background-color: #f3f0e8;
    }

    /* Sidebar log */
    .log-line {
        font-family: 'Consolas', monospace;
        font-size: 0.82rem;
        color: #6b5f4d;
        padding: 0.15rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# Header
# -------------------------------------------------
st.markdown(
    '<div class="header-wrap">'
    '<div class="header-title">📚 Research Agent</div>'
    '<div class="header-sub">Ask a question — the agent fetches, extracts, verifies, and summarizes it for you</div>'
    '</div>',
    unsafe_allow_html=True
)

# -------------------------------------------------
# Input section
# -------------------------------------------------
topic = st.text_input(
    label="What would you like to research today?",
    placeholder="e.g., How does quantum computing affect modern encryption algorithms?",
    help="Enter a research topic, question, or concept you want to investigate."
)

col1, col2, col3 = st.columns([2, 1, 2])
with col2:
    start_btn = st.button("Generate Report", use_container_width=True, type="primary")

# -------------------------------------------------
# Confidence badge helper
# -------------------------------------------------
def render_fact(fact):
    if isinstance(fact, dict):
        text = fact.get("text", "")
        confidence = fact.get("confidence", fact.get("confidence_score", None))
    else:
        text = fact
        confidence = None

    if confidence is not None:
        if confidence >= 0.75:
            color, bg = "#3f7a3f", "rgba(63, 122, 63, 0.12)"
        elif confidence >= 0.5:
            color, bg = "#a37a1f", "rgba(163, 122, 31, 0.12)"
        else:
            color, bg = "#a3402f", "rgba(163, 64, 47, 0.12)"

        pct = int(confidence * 100)
        st.markdown(f'''
            <div class="fact-row">
                <span class="fact-text">{text}</span>
                <span class="confidence-badge" style="background-color:{bg}; color:{color}; border:1px solid {color};">{pct}%</span>
            </div>
        ''', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="fact-row"><span class="fact-text">{text}</span></div>', unsafe_allow_html=True)


# -------------------------------------------------
# Run the agent
# -------------------------------------------------
if start_btn:
    if not topic.strip():
        st.warning("Please enter a valid topic to search.")
    else:
        status_placeholder = st.empty()
        debug_expander = st.sidebar.expander("Agent Execution Log", expanded=True)

        with st.spinner("Initializing research agent..."):
            try:
                inputs = {
                    "topic": topic.strip(),
                    "fetch_attempts": 0,
                    "max_fetch_attempts": 3
                }

                final_state = None

                for event in graph.stream(inputs):
                    for node_name, output in event.items():
                        debug_expander.markdown(f'<div class="log-line">⚙ {node_name} completed</div>', unsafe_allow_html=True)

                        if node_name == "validate_topic":
                            status = output.get("status")
                            if status == "invalid":
                                status_placeholder.markdown(
                                    f'<div class="status-card">❌ {output.get("final_report")}</div>',
                                    unsafe_allow_html=True
                                )
                                break
                            else:
                                status_placeholder.markdown(
                                    '<div class="status-card">✔ Topic validated — starting web search...</div>',
                                    unsafe_allow_html=True
                                )

                        elif node_name == "web_search":
                            status_placeholder.markdown(
                                f'<div class="status-card">🌐 Searching the web (attempt {output.get("fetch_attempts")})...</div>',
                                unsafe_allow_html=True
                            )

                        elif node_name == "content_classifier":
                            status_placeholder.markdown(
                                '<div class="status-card">🧠 Extracting facts from search results...</div>',
                                unsafe_allow_html=True
                            )

                        elif node_name == "fact_checker":
                            status_placeholder.markdown(
                                '<div class="status-card">🔎 Re-checking low-confidence facts...</div>',
                                unsafe_allow_html=True
                            )

                        elif node_name == "content_categorizer":
                            status_placeholder.markdown(
                                '<div class="status-card">🗂 Grouping facts into categories...</div>',
                                unsafe_allow_html=True
                            )

                        elif node_name == "summarizer":
                            status_placeholder.markdown(
                                '<div class="status-card">📝 Writing the final report...</div>',
                                unsafe_allow_html=True
                            )

                        final_state = output

            except Exception as e:
                st.error(f"An error occurred during execution: {e}")
                final_state = None

        with st.spinner("Compiling results..."):
            try:
                result = graph.invoke({
                    "topic": topic.strip(),
                    "fetch_attempts": 0,
                    "max_fetch_attempts": 3
                })

                status_placeholder.empty()

                if result.get("status") == "invalid":
                    st.markdown(f'<div class="status-card">❌ {result.get("final_report")}</div>', unsafe_allow_html=True)
                else:
                    st.success("Research complete.")

                    tab1, tab2, tab3 = st.tabs(["📄 Report", "📌 Facts", "🔗 Sources"])

                    with tab1:
                        st.markdown('<div class="section-heading">Executive Summary</div>', unsafe_allow_html=True)
                        st.markdown(result.get("final_report", "No report generated."))

                    with tab2:
                        st.markdown('<div class="section-heading">Extracted Facts</div>', unsafe_allow_html=True)
                        st.caption("Facts below 50% confidence were automatically re-verified with a follow-up search.")
                        facts = result.get("fact", [])
                        if facts:
                            for fact in facts:
                                render_fact(fact)
                        else:
                            st.write("No specific facts were extracted.")

                    with tab3:
                        st.markdown('<div class="section-heading">References & Sources</div>', unsafe_allow_html=True)
                        sources = result.get("sources", [])
                        if sources:
                            for src in sources:
                                safe_src = html.escape(str(src), quote=True)
                                st.markdown(
                                    f'''
                                    <div class="source-tag">
                                        <span class="source-icon">🔗</span>
                                        <a href="{safe_src}" target="_blank" rel="noopener noreferrer">{safe_src}</a>
                                    </div>
                                    ''',
                                    unsafe_allow_html=True
                                )
                        else:
                            st.write("No sources cited.")

            except Exception as e:
                st.error(f"An error occurred while compiling results: {e}")
