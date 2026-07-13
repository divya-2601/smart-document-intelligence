"""
app.py — Smart Document Intelligence Platform
SaaS-style multi-page navigation routing.
"""

import pathlib
import streamlit as st

st.set_page_config(
    page_title="Smart Document Intelligence",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)
from dotenv import load_dotenv

# Load environment configs
load_dotenv()

# Injection of custom CSS
CSS_PATH = pathlib.Path(__file__).parent / "assets" / "style.css"
if CSS_PATH.exists():
    with open(CSS_PATH, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Custom sidebar CSS style injection to remove excess logo/branding space
st.markdown(
    """
    <style>
    /* Hide top Streamlit padding/header */
    [data-testid="stHeader"] {
        background-color: transparent !important;
    }
    .main .block-container {
        padding-top: 2rem !important;
    }
    /* Compact sidebar navigation spacing */
    [data-testid="stSidebarNav"] {
        padding-top: 1rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------------------------------------------------------------------
# Database Schema Initialization
# ---------------------------------------------------------------------------
from src.database import init_db
init_db()

# ---------------------------------------------------------------------------
# Multi-Page SaaS Navigation Routing
# ---------------------------------------------------------------------------
pages = {
    "DocIntel Platform": [
        st.Page("ui_pages/Home.py", title="Home", icon="🏠", default=True),
        st.Page("ui_pages/Workspace.py", title="Workspace", icon="💼"),
        st.Page("ui_pages/Analytics.py", title="Analytics", icon="📊"),
        st.Page("ui_pages/PromptOps.py", title="PromptOps", icon="🧠"),
        st.Page("ui_pages/Prompt_Comparison.py", title="Prompt Comparison", icon="⚖️"),
        st.Page("ui_pages/Settings.py", title="Settings", icon="⚙️"),
    ]
}

pg = st.navigation(pages)
pg.run()