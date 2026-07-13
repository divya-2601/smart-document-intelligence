"""
ui_pages/Prompt_Comparison.py — Prompt Comparison Split-Screen
"""

import time
import sqlite3
import pathlib
import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Database Connectivity
# ---------------------------------------------------------------------------
DB_PATH = pathlib.Path(__file__).parent.parent / "doc_intel.db"

try:
    from src.rag_pipeline import query_context, get_client
    PIPELINE_OK = True
except Exception as _err:
    PIPELINE_OK = False
    PIPELINE_ERROR = str(_err)

def get_prompts():
    try:
        conn = sqlite3.connect(str(DB_PATH))
        df = pd.read_sql_query("SELECT * FROM prompts", conn)
        conn.close()
        return df.to_dict('records')
    except Exception:
        return []

# ---------------------------------------------------------------------------
# Main Page Body
# ---------------------------------------------------------------------------
st.markdown("<h2 style='margin-bottom: 0.5rem; font-weight: 700; color: #f0f6fc;'>Prompt Comparison</h2>", unsafe_allow_html=True)
st.markdown("<p style='font-size: 0.9rem; color: #8b949e; margin-bottom: 1.5rem;'>Execute side-by-side RAG evaluations using different system configurations on the same context payload.</p>", unsafe_allow_html=True)

prompts = get_prompts()
if not prompts:
    st.info("⚖️ No prompt templates found in the database. Add templates in PromptOps first.")
    st.stop()

prompt_names = [p.get("name", "Unnamed") for p in prompts if isinstance(p, dict)]

if not PIPELINE_OK:
    st.error(f"❌ Pipeline initialization failed: `{PIPELINE_ERROR}`")
    st.stop()

# Selectors
col_sel_a, col_sel_b = st.columns(2)
with col_sel_a:
    prompt_a_name = st.selectbox("Select Prompt A", options=prompt_names, index=0)
    prompt_a = next((p for p in prompts if p.get("name") == prompt_a_name), None)
with col_sel_b:
    prompt_b_name = st.selectbox("Select Prompt B", options=prompt_names, index=min(1, len(prompt_names)-1))
    prompt_b = next((p for p in prompts if p.get("name") == prompt_b_name), None)

st.markdown("---")

user_query = st.text_input("Enter Question for evaluation", value="Summarize the core financial or operational highlights.")

if st.button("⚖️ Compare Side-by-Side", use_container_width=True):
    if not user_query.strip():
        st.warning("Please enter a question.")
    else:
        with st.spinner("Retrieving context and running models..."):
            try:
                # Retrieve context once
                context_str, citations = query_context(user_query)
                client = get_client()
                
                # Run A
                prompt_a_filled = prompt_a.get("template", "").format(context=context_str, query=user_query)
                start_a = time.time()
                res_a = client.models.generate_content(model="gemini-2.5-flash", contents=prompt_a_filled)
                latency_a = (time.time() - start_a) * 1000
                st.session_state["comp_a_res"] = res_a.text
                st.session_state["comp_a_lat"] = latency_a
                
                # Run B
                prompt_b_filled = prompt_b.get("template", "").format(context=context_str, query=user_query)
                start_b = time.time()
                res_b = client.models.generate_content(model="gemini-2.5-flash", contents=prompt_b_filled)
                latency_b = (time.time() - start_b) * 1000
                st.session_state["comp_b_res"] = res_b.text
                st.session_state["comp_b_lat"] = latency_b
                
            except Exception as e:
                st.error(f"Error during comparison: {e}")

# Render side-by-side results
if "comp_a_res" in st.session_state and "comp_b_res" in st.session_state:
    col_out_a, col_out_b = st.columns(2)
    
    with col_out_a:
        st.markdown(f"#### Model Output (Prompt A - {prompt_a.get('name')})")
        st.info(st.session_state["comp_a_res"])
        
        # Token estimation & response time
        tokens_a = len(st.session_state["comp_a_res"]) / 4
        st.markdown(
            f"""
            <div style="font-size: 0.8rem; color: #8b949e; background: #161b22; border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 6px 10px;">
                ⏱️ Latency: <strong>{st.session_state['comp_a_lat']:.0f} ms</strong> &nbsp;·&nbsp; 
                🪙 Estimated Tokens: <strong>{tokens_a:.0f}</strong>
            </div>
            """,
            unsafe_allow_html=True
        )
        
    with col_out_b:
        st.markdown(f"#### Model Output (Prompt B - {prompt_b.get('name')})")
        st.info(st.session_state["comp_b_res"])
        
        # Token estimation & response time
        tokens_b = len(st.session_state["comp_b_res"]) / 4
        st.markdown(
            f"""
            <div style="font-size: 0.8rem; color: #8b949e; background: #161b22; border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 6px 10px;">
                ⏱️ Latency: <strong>{st.session_state['comp_b_lat']:.0f} ms</strong> &nbsp;·&nbsp; 
                🪙 Estimated Tokens: <strong>{tokens_b:.0f}</strong>
            </div>
            """,
            unsafe_allow_html=True
        )
