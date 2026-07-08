import streamlit as st
import time
import sys
import os

# Import the compiled graph from research_agent.py
from research_agent import graph

# Page config
st.set_page_config(
    page_title="Deep Research Agent",
    page_icon="🔬",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom Styling to make it look extremely premium
st.markdown("""
    <style>
    /* Main container styling */
    .main {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
        color: #f8fafc;
    }
    
    /* Title styling */
    .title-container {
        text-align: center;
        padding: 2rem 0 1rem 0;
    }
    .title-main {
        font-family: 'Outfit', 'Inter', sans-serif;
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(to right, #38bdf8, #818cf8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .subtitle-main {
        font-family: 'Inter', sans-serif;
        color: #94a3b8;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    
    /* Card/Status block styling */
    .status-card {
        background-color: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(148, 163, 184, 0.1);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        backdrop-filter: blur(10px);
    }
    
    /* Sources style */
    .source-tag {
        display: inline-block;
        background-color: rgba(56, 189, 248, 0.15);
        color: #38bdf8;
        border: 1px solid rgba(56, 189, 248, 0.3);
        border-radius: 20px;
        padding: 0.2rem 0.8rem;
        margin: 0.3rem;
        font-size: 0.85rem;
        text-decoration: none;
        transition: all 0.2s ease;
    }
    .source-tag:hover {
        background-color: rgba(56, 189, 248, 0.3);
        border-color: #38bdf8;
    }
    
    /* Fact list styling */
    .fact-item {
        border-left: 3px solid #818cf8;
        padding-left: 1rem;
        margin: 0.8rem 0;
        color: #cbd5e1;
    }
    </style>
""", unsafe_allow_html=True)

# App Header
st.markdown('<div class="title-container"><h1 class="title-main">🔬 Deep Research Assistant</h1><p class="subtitle-main">An autonomous research agent powered by LangGraph, Groq, and Tavily</p></div>', unsafe_allow_html=True)

# Search Input Section
topic = st.text_input(
    label="What would you like to research today?",
    placeholder="e.g., How does quantum computing affect modern encryption algorithms?",
    help="Enter a research topic, question, or concept you want to investigate."
)

col1, col2, col3 = st.columns([2, 1, 2])
with col2:
    start_btn = st.button("Generate Report", use_container_width=True, type="primary")

if start_btn:
    if not topic.strip():
        st.warning("Please enter a valid topic to search.")
    else:
        # Status box that updates dynamically
        status_placeholder = st.empty()
        
        # Container for intermediate results
        debug_expander = st.sidebar.expander("Agent Execution Logs", expanded=True)
        
        with st.spinner("Initializing Research Agent..."):
            try:
                # Initialize state inputs
                inputs = {
                    "topic": topic.strip(),
                    "fetch_attempts": 0,
                    "max_fetch_attempts": 3
                }
                
                # We will stream the graph execution to update the user in real-time
                final_state = None
                
                # Run the graph and stream events
                for event in graph.stream(inputs):
                    for node_name, output in event.items():
                        debug_expander.write(f"⚙️ Node `{node_name}` completed execution.")
                        
                        if node_name == "validate_topic":
                            status = output.get("status")
                            if status == "invalid":
                                status_placeholder.error(f"❌ Validation Failed: {output.get('final_report')}")
                                break
                            else:
                                status_placeholder.info("🔍 Topic validated! Initiating web search...")
                                
                        elif node_name == "web_search":
                            status_placeholder.info(f"🌐 Searching the web (Attempt {output.get('fetch_attempts')})...")
                            
                        elif node_name == "content_classifier":
                            status_placeholder.info("🧠 Classifying search results & extracting facts...")
                            
                        elif node_name == "content_categorizer":
                            status_placeholder.info("🗂️ Categorizing and grouping facts...")
                            
                        elif node_name == "summarizer":
                            status_placeholder.info("📝 Writing final markdown report...")
                        
                        # Store the latest output state
                        final_state = output
                
            except Exception as e:
                st.error(f"An error occurred during execution: {e}")
                final_state = None
        
        # Pull final results using invoke
        with st.spinner("Compiling results..."):
            try:
                result = graph.invoke({
                    "topic": topic.strip(),
                    "fetch_attempts": 0,
                    "max_fetch_attempts": 3
                })
                
                status_placeholder.empty()
                
                if result.get("status") == "invalid":
                    st.error(result.get("final_report"))
                else:
                    st.success("✨ Research Complete!")
                    
                    # Display layout in tabs
                    tab1, tab2, tab3 = st.tabs(["📄 Final Report", "📌 Key Facts", "🔗 Sources"])
                    
                    with tab1:
                        st.markdown("### Executive Summary")
                        st.markdown(result.get("final_report", "No report generated."))
                        
                    with tab2:
                        st.markdown("### Extracted Facts")
                        facts = result.get("fact", [])
                        if facts:
                            for fact in facts:
                                st.markdown(f'<div class="fact-item">{fact}</div>', unsafe_allow_html=True)
                        else:
                            st.write("No specific facts were extracted.")
                            
                    with tab3:
                        st.markdown("### References & Sources")
                        sources = result.get("sources", [])
                        if sources:
                            for src in sources:
                                st.markdown(f'<a href="{src}" target="_blank" class="source-tag">🔗 {src}</a>', unsafe_allow_html=True)
                        else:
                            st.write("No sources cited.")
            except Exception as e:
                st.error(f"An error occurred while compiling results: {e}")
