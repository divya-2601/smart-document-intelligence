"""
ui_pages/Settings.py — Platform Settings & RAG Configurations
"""

import os
import pathlib
import streamlit as st

# ---------------------------------------------------------------------------
# Database Connectivity
# ---------------------------------------------------------------------------
DB_PATH = pathlib.Path(__file__).parent.parent / "doc_intel.db"

# ---------------------------------------------------------------------------
# Main Page Body
# ---------------------------------------------------------------------------
st.markdown("<h2 style='margin-bottom: 0.5rem; font-weight: 700; color: #f0f6fc;'>Settings</h2>", unsafe_allow_html=True)
st.markdown("<p style='font-size: 0.9rem; color: #8b949e; margin-bottom: 1.5rem;'>Configure retrieval criteria, query thresholds, and inspect connection status parameters.</p>", unsafe_allow_html=True)

st.markdown("### 🎛️ RAG Retrieval Configurations")

# Settings defaults in session state
if "settings_top_k" not in st.session_state:
    st.session_state["settings_top_k"] = 6
if "settings_min_score" not in st.session_state:
    st.session_state["settings_min_score"] = 0.30

# Adjusters
top_k = st.slider("Top K Chunks to Retrieve", min_value=1, max_value=12, value=st.session_state["settings_top_k"], help="The number of highest-similarity chunks pulled for Gemini context construction.")
min_score = st.slider("Similarity Threshold (Minimum Score)", min_value=0.0, max_value=1.0, value=st.session_state["settings_min_score"], step=0.05, help="Cosine similarity score cut-off. Chunks below this are discarded.")

if st.button("💾 Save Settings", use_container_width=True):
    st.session_state["settings_top_k"] = top_k
    st.session_state["settings_min_score"] = min_score
    st.toast("✅ Settings saved successfully!")

st.markdown("---")

st.markdown("### 🔌 Connections & Infrastructure")

db_size_str = "0 B"
if DB_PATH.exists():
    try:
        db_size_str = f"{(DB_PATH.stat().st_size / 1024):.1f} KB"
    except Exception:
        pass

st.markdown(
    f"""
    <div style="background: #161b22; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 1rem; line-height: 1.6;">
        <span style="color:#8b949e;">🗄️ SQLite Database File Path:</span> <code style="color:#f0f6fc;">{DB_PATH.absolute()}</code><br>
        <span style="color:#8b949e;">📏 Database File Size:</span> <strong style="color:#f0f6fc;">{db_size_str}</strong><br>
        <span style="color:#8b949e;">🌲 Pinecone Index:</span> <code style="color:#f0f6fc;">{os.getenv("PINECONE_INDEX_NAME", "doc-intel-index")}</code><br>
        <span style="color:#8b949e;">🧠 Embedding Model:</span> <code style="color:#f0f6fc;">text-embedding-004</code><br>
        <span style="color:#8b949e;">💬 Answer Synthesis Model:</span> <code style="color:#f0f6fc;">gemini-2.5-flash</code>
    </div>
    """,
    unsafe_allow_html=True
)
