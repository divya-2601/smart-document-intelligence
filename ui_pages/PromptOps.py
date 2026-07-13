"""
ui_pages/PromptOps.py — Prompt Lifecycle Console
"""

import sqlite3
import pathlib
import datetime
import time
import logging
import pandas as pd
import streamlit as st

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PromptOps")

# ---------------------------------------------------------------------------
# Database Connectivity
# ---------------------------------------------------------------------------
DB_PATH = pathlib.Path(__file__).parent.parent / "doc_intel.db"

def get_prompts():
    try:
        conn = sqlite3.connect(str(DB_PATH))
        df = pd.read_sql_query("SELECT * FROM prompts", conn)
        conn.close()
        return df.to_dict('records')
    except Exception as e:
        logger.error(f"Error fetching prompts: {e}")
        st.error(f"Database error: Unable to retrieve prompt templates. ({e})")
        return []

def set_active_prompt(prompt_id: int):
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("UPDATE prompts SET is_active = 0")
        cursor.execute("UPDATE prompts SET is_active = 1 WHERE id = ?", (prompt_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error setting active prompt: {e}")
        st.error(f"Database error: Unable to update active prompt. ({e})")
        return False

def add_or_update_prompt_db(name: str, version: str, description: str, template: str, tags: str):
    now = datetime.datetime.now().isoformat()
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        # Ensure table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                version TEXT,
                description TEXT,
                template TEXT,
                tags TEXT,
                is_active INTEGER,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        cursor.execute("SELECT id FROM prompts WHERE name = ? AND version = ?", (name, version))
        row = cursor.fetchone()
        if row:
            # Edit / Save Prompt
            cursor.execute("""
                UPDATE prompts 
                SET description = ?, template = ?, tags = ?, updated_at = ?
                WHERE id = ?
            """, (description, template, tags, now, row[0]))
            conn.commit()
            conn.close()
            logger.info(f"Updated prompt template: {name} ({version})")
            return True, "updated"
        else:
            # Create / Version Prompt
            cursor.execute("""
                INSERT INTO prompts (name, version, description, template, tags, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 0, ?, ?)
            """, (name, version, description, template, tags, now, now))
            conn.commit()
            conn.close()
            logger.info(f"Inserted new prompt template: {name} ({version})")
            return True, "created"
    except Exception as e:
        logger.error(f"Error saving prompt to database: {e}")
        st.error(f"Database error: Unable to save prompt template. ({e})")
        return False, str(e)

# ---------------------------------------------------------------------------
# Main Page Body
# ---------------------------------------------------------------------------
st.markdown("<h2 style='margin-bottom: 0.5rem; font-weight: 700; color: #f0f6fc;'>PromptOps Console</h2>", unsafe_allow_html=True)
st.markdown("<p style='font-size: 0.9rem; color: #8b949e; margin-bottom: 1.5rem;'>Manage template presets, edit formatting instructions, and configure active templates.</p>", unsafe_allow_html=True)

prompts = get_prompts()

active_prompt = next((p for p in prompts if p.get("is_active") == 1), None)
active_name = active_prompt["name"] if active_prompt else "None"
active_version = active_prompt["version"] if active_prompt else ""

col_meta1, col_meta2 = st.columns(2)
with col_meta1:
    st.markdown(f"**🧠 Active Prompt:** `{active_name}` (`{active_version}`)")
with col_meta2:
    st.markdown(f"**📁 Library Size:** `{len(prompts)} templates`")

st.markdown("---")

col_left, col_right = st.columns(2)

with col_left:
    st.markdown("### 📁 Prompt Library & Activation")
    
    # Search input for filtering prompts
    search_query = st.text_input("🔍 Search Prompt Library (by name, template, or tags)", value="")
    
    filtered_prompts = prompts
    if search_query:
        filtered_prompts = [
            p for p in prompts
            if search_query.lower() in p.get("name", "").lower() or
               search_query.lower() in p.get("tags", "").lower() or
               search_query.lower() in p.get("template", "").lower() or
               search_query.lower() in p.get("version", "").lower()
        ]
        
    if not filtered_prompts:
        if not prompts:
            st.info("No prompts available in the database. Use the form on the right to create one.")
        else:
            st.warning("No prompts match your search query.")
    else:
        prompt_options = [f"{p['name']} ({p['version']})" for p in filtered_prompts]
        selected_option = st.selectbox("Select Prompt to inspect/activate", options=prompt_options)
        
        selected_p = None
        if selected_option:
            idx = prompt_options.index(selected_option)
            selected_p = filtered_prompts[idx]
            
        if selected_p:
            st.text_input("Name", value=selected_p["name"], disabled=True, key="insp_name")
            st.text_input("Version", value=selected_p["version"], disabled=True, key="insp_ver")
            st.text_area("Template Text", value=selected_p["template"], height=160, disabled=True, key="insp_temp")
            
            col_act, col_load = st.columns(2)
            with col_act:
                if st.button("🟢 Activate Selected Prompt", use_container_width=True):
                    try:
                        if set_active_prompt(selected_p["id"]):
                            st.toast(f"✅ '{selected_p['name']}' activated successfully!")
                            time.sleep(0.5)
                            st.rerun()
                    except Exception as e:
                        st.error(f"Failed to activate prompt: {e}")
            with col_load:
                if st.button("📝 Load to Edit/Version", use_container_width=True):
                    st.session_state["edit_prompt_name"] = selected_p["name"]
                    st.session_state["edit_prompt_version"] = selected_p["version"]
                    st.session_state["edit_prompt_description"] = selected_p["description"]
                    st.session_state["edit_prompt_template"] = selected_p["template"]
                    st.session_state["edit_prompt_tags"] = selected_p["tags"]
                    st.toast(f"Loaded '{selected_p['name']}' ({selected_p['version']}) into form!")
                    time.sleep(0.5)
                    st.rerun()

with col_right:
    st.markdown("### 📝 Create Version / Edit Prompt")
    
    # Retrieve default values from session state if loaded for editing, else defaults
    default_name = st.session_state.get("edit_prompt_name", "")
    default_ver = st.session_state.get("edit_prompt_version", "v1.0.0")
    default_desc = st.session_state.get("edit_prompt_description", "")
    default_temp = st.session_state.get("edit_prompt_template", "Context:\n{context}\n\nQuery:\n{query}")
    default_tags = st.session_state.get("edit_prompt_tags", "RAG, Custom")
    
    with st.form("create_prompt_form"):
        new_name = st.text_input("Template Name (e.g. Concise)", value=default_name)
        new_ver = st.text_input("Version String (e.g. v1.1.0)", value=default_ver)
        new_desc = st.text_input("Short Description", value=default_desc)
        new_temp = st.text_area("Template Content (must contain {context} and {query})", value=default_temp, height=160)
        new_tags = st.text_input("Tags (comma separated)", value=default_tags)
        
        submit_btn = st.form_submit_button("💾 Save to Library")
        if submit_btn:
            if not new_name.strip() or not new_temp.strip():
                st.error("Name and Template content cannot be empty.")
            elif "{context}" not in new_temp or ("{query}" not in new_temp and "{question}" not in new_temp):
                st.error("Template Content must contain {context} and {query} (or {question}) placeholders.")
            else:
                try:
                    success, op = add_or_update_prompt_db(new_name, new_ver, new_desc, new_temp, new_tags)
                    if success:
                        st.toast(f"✅ Prompt template {op} successfully!")
                        # Clear loaded edit state upon successful save
                        st.session_state.pop("edit_prompt_name", None)
                        st.session_state.pop("edit_prompt_version", None)
                        st.session_state.pop("edit_prompt_description", None)
                        st.session_state.pop("edit_prompt_template", None)
                        st.session_state.pop("edit_prompt_tags", None)
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(f"Error saving to database: {op}")
                except Exception as e:
                    st.error(f"Unexpected error: {e}")
                    
    # Optional clear/reset button for the form if session state was populated
    if "edit_prompt_name" in st.session_state:
        if st.button("🧹 Clear/Reset Edit Form", use_container_width=True):
            st.session_state.pop("edit_prompt_name", None)
            st.session_state.pop("edit_prompt_version", None)
            st.session_state.pop("edit_prompt_description", None)
            st.session_state.pop("edit_prompt_template", None)
            st.session_state.pop("edit_prompt_tags", None)
            st.toast("Form cleared.")
            time.sleep(0.5)
            st.rerun()

st.markdown("---")

st.markdown("### 🔗 Platform Integrations")
col_int1, col_int2 = st.columns(2)
with col_int1:
    if st.button("⚖️ Open Prompt Comparison Console", use_container_width=True):
        st.switch_page("ui_pages/Prompt_Comparison.py")
with col_int2:
    if st.button("📊 Open Analytics Dashboard", use_container_width=True):
        st.switch_page("ui_pages/Analytics.py")

st.markdown("---")

# Prompt History (logs)
st.markdown("### 📋 Evaluation Logs & Sentiment History")
feedbacks_df = pd.DataFrame()
try:
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='feedbacks'")
    if cursor.fetchone():
        feedbacks_df = pd.read_sql_query("SELECT timestamp, prompt_version, response_time, feedback FROM feedbacks", conn)
    conn.close()
except Exception as e:
    logger.error(f"Error loading feedbacks: {e}")
    st.warning("Could not load feedback logs from database.")

if feedbacks_df.empty:
    st.info("No feedback metrics have been recorded yet.")
else:
    try:
        df_logs = feedbacks_df.copy()
        df_logs.columns = ["Timestamp", "Prompt Version", "Latency", "User Rating"]
        df_logs["Latency"] = df_logs["Latency"].map(lambda x: f"{float(x):.1f} ms" if x is not None and not pd.isna(x) else "N/A")
        st.dataframe(df_logs.sort_values("Timestamp", ascending=False), use_container_width=True, hide_index=True)
    except Exception as e:
        logger.error(f"Error displaying feedbacks table: {e}")
        st.error("Error formatting evaluation logs table.")
