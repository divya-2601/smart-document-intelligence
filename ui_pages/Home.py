"""
ui_pages/Home.py — Minimal SaaS Landing Page
"""

import streamlit as st

st.markdown(
    """
    <div style="text-align: center; padding: 5rem 2rem;">
        <h1 style="font-size: 3rem; font-weight: 800; background: linear-gradient(90deg, #6366f1, #a855f7); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 1rem;">
            Smart Document Intelligence
        </h1>
        <p style="font-size: 1.2rem; color: #8b949e; max-width: 600px; margin: 0 auto 2.5rem; line-height: 1.6;">
            Multi-PDF Semantic Retrieval and grounded answer synthesis engine. Upload documents, customize prompt instructions, and evaluate execution latencies.
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

col_c, _ = st.columns([1, 2])
with col_c:
    if st.button("🚀 Get Started", type="primary", use_container_width=True):
        st.switch_page("ui_pages/Workspace.py")

