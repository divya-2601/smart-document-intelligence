"""
ui_pages/Analytics.py — Analytics & Performance Evaluation Dashboard
"""

import sqlite3
import pathlib
import json
import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Database Connectivity (Chat-specific metrics only)
# ---------------------------------------------------------------------------
DB_PATH = pathlib.Path(__file__).parent.parent / "doc_intel.db"

def load_chat_analytics():
    if not DB_PATH.exists():
        return None, False
        
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        tables = [t[0] for t in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        if "chat_messages" not in tables or "conversations" not in tables or "documents" not in tables:
            conn.close()
            return None, False
            
        # Get total questions
        cursor.execute("SELECT COUNT(*) FROM chat_messages WHERE role = 'user'")
        total_questions = cursor.fetchone()[0]
        
        # Get total chats
        cursor.execute("SELECT COUNT(*) FROM conversations")
        total_chats = cursor.fetchone()[0]
        
        # Get total documents
        cursor.execute("SELECT COUNT(*) FROM documents")
        total_documents = cursor.fetchone()[0]
        
        # Get total prompt usage
        cursor.execute("SELECT COUNT(*) FROM chat_messages WHERE role = 'assistant' AND version IS NOT NULL AND version != ''")
        total_prompt_usage = cursor.fetchone()[0]
        
        # Get average response time (latency)
        cursor.execute("SELECT AVG(latency) FROM chat_messages WHERE role = 'assistant' AND latency IS NOT NULL")
        avg_latency = cursor.fetchone()[0]
        if avg_latency is None:
            avg_latency = 0.0
            
        # Get most used prompt
        cursor.execute("""
            SELECT version, COUNT(*) as count 
            FROM chat_messages 
            WHERE role = 'assistant' AND version IS NOT NULL AND version != '' 
            GROUP BY version 
            ORDER BY count DESC 
            LIMIT 1
        """)
        row_most_used = cursor.fetchone()
        most_used_prompt = row_most_used[0] if row_most_used else "N/A"
        
        # Get responses for charts
        df_responses = pd.read_sql_query("""
            SELECT id, latency as response_time, version as prompt_version, timestamp, citations
            FROM chat_messages 
            WHERE role = 'assistant'
        """, conn)
        
        conn.close()
        return {
            "total_questions": total_questions,
            "total_chats": total_chats,
            "total_documents": total_documents,
            "total_prompt_usage": total_prompt_usage,
            "avg_latency": avg_latency,
            "most_used_prompt": most_used_prompt,
            "df_responses": df_responses
        }, True
    except Exception:
        return None, False

# ---------------------------------------------------------------------------
# Main Page Body
# ---------------------------------------------------------------------------
st.markdown("<h2 style='margin-bottom: 0.5rem; font-weight: 700; color: #f0f6fc;'>Analytics Dashboard</h2>", unsafe_allow_html=True)
st.markdown("<p style='font-size: 0.9rem; color: #8b949e; margin-bottom: 1.5rem;'>Real-time operational metrics, response latencies, and prompt usage trends gathered from chat sessions.</p>", unsafe_allow_html=True)

data, db_ok = load_chat_analytics()

# Check fallback or empty state
if not db_ok or data is None or data["df_responses"].empty:
    total_questions = data["total_questions"] if (db_ok and data) else 0
    total_chats = data["total_chats"] if (db_ok and data) else 0
    total_docs = data["total_documents"] if (db_ok and data) else 0
    total_prompt_usage = data["total_prompt_usage"] if (db_ok and data) else 0
    avg_latency = data["avg_latency"] if (db_ok and data) else 0.0
    most_used_prompt = data["most_used_prompt"] if (db_ok and data) else "N/A"

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.metric("Total Questions", total_questions)
    with col2:
        st.metric("Total Chats", total_chats)
    with col3:
        st.metric("Total Documents", total_docs)
    with col4:
        st.metric("Total Prompt Usage", total_prompt_usage)
    with col5:
        st.metric("Average Response Time (ms)", f"{avg_latency:.0f}" if avg_latency > 0 else "0")
    with col6:
        st.metric("Most Used Prompt", most_used_prompt)
        
    st.markdown("---")
    st.info("📊 **Operational Analytics Dashboard**\n\nNo operational logs or user feedback data found from your Chat history yet. Ask questions on the Chat page to populate real-time analytics graphs dynamically.")
    st.stop()

# Regular Dashboard calculations
df_resp = data["df_responses"]

total_questions = data["total_questions"]
total_chats = data["total_chats"]
total_docs = data["total_documents"]
total_prompt_usage = data["total_prompt_usage"]
avg_latency = data["avg_latency"]
most_used_prompt = data["most_used_prompt"]

# Render metrics
col1, col2, col3, col4, col5, col6 = st.columns(6)
with col1:
    st.metric("Total Questions", total_questions)
with col2:
    st.metric("Total Chats", total_chats)
with col3:
    st.metric("Total Documents", total_docs)
with col4:
    st.metric("Total Prompt Usage", total_prompt_usage)
with col5:
    st.metric("Average Response Time (ms)", f"{avg_latency:.0f}" if avg_latency > 0 else "0")
with col6:
    st.metric("Most Used Prompt", most_used_prompt)

st.markdown("---")

# Prepare counts and scores from citations column
doc_counts = {}
scores = []
for _, row in df_resp.iterrows():
    c_str = row["citations"]
    if c_str:
        try:
            c_list = json.loads(c_str)
            if isinstance(c_list, list):
                seen_in_row = set()
                for item in c_list:
                    if isinstance(item, dict) and "filename" in item:
                        seen_in_row.add(item["filename"])
                    if isinstance(item, dict) and "score" in item:
                        scores.append(float(item["score"]))
                for fname in seen_in_row:
                    doc_counts[fname] = doc_counts.get(fname, 0) + 1
        except Exception:
            pass

# Row 1 Visualizations: Prompt Usage & Citation Frequency
col_row1_left, col_row1_right = st.columns(2)

with col_row1_left:
    st.subheader("📊 Prompt Usage Distribution")
    df_prompt_usage = df_resp[df_resp["prompt_version"].notna() & (df_resp["prompt_version"] != "") & (df_resp["prompt_version"] != "N/A")]
    if df_prompt_usage.empty:
        st.info("No prompt version usage data recorded yet.")
    else:
        try:
            import plotly.express as px
            usage_grouped = df_prompt_usage["prompt_version"].value_counts().reset_index()
            usage_grouped.columns = ["prompt_version", "usage_count"]
            fig_usage = px.bar(
                usage_grouped,
                x='prompt_version',
                y='usage_count',
                labels={'prompt_version': 'Prompt Version', 'usage_count': 'Executions'},
                color='prompt_version',
                color_discrete_sequence=['#a855f7', '#6366f1', '#34d399'],
                template="plotly_dark"
            )
            fig_usage.update_layout(
                margin=dict(t=20, b=20, l=20, r=20),
                height=280,
                showlegend=False,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_usage, use_container_width=True)
        except Exception:
            st.bar_chart(df_prompt_usage['prompt_version'].value_counts())

with col_row1_right:
    st.subheader("📄 Citation Frequency")
    if not doc_counts:
        st.info("No documents have been cited in queries yet.")
    else:
        try:
            import plotly.express as px
            doc_counts_df = pd.DataFrame(list(doc_counts.items()), columns=["Document", "Query Count"])
            doc_counts_df = doc_counts_df.sort_values(by="Query Count", ascending=True)
            fig_docs = px.bar(
                doc_counts_df,
                x="Query Count",
                y="Document",
                orientation="h",
                labels={"Query Count": "Retrieval Count", "Document": "Document"},
                color="Document",
                color_discrete_sequence=['#34d399', '#6366f1', '#a855f7'],
                template="plotly_dark"
            )
            fig_docs.update_layout(
                margin=dict(t=20, b=20, l=20, r=20),
                height=280,
                showlegend=False,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_docs, use_container_width=True)
        except Exception:
            st.bar_chart(pd.Series(doc_counts))

# Row 2 Visualizations: Response Time Distribution & Retrieval Confidence Distribution
row2_charts = []

# 1. Response Time Distribution
latencies = df_resp["response_time"].dropna()
if not latencies.empty:
    bin_counts = {"0-2s": 0, "2-4s": 0, "4-6s": 0, "6s+": 0}
    for lat in latencies:
        lat_s = lat / 1000.0
        if lat_s < 2.0:
            bin_counts["0-2s"] += 1
        elif lat_s < 4.0:
            bin_counts["2-4s"] += 1
        elif lat_s < 6.0:
            bin_counts["4-6s"] += 1
        else:
            bin_counts["6s+"] += 1
            
    try:
        import plotly.express as px
        latency_df = pd.DataFrame(list(bin_counts.items()), columns=["Latency Range", "Count"])
        fig_latency = px.bar(
            latency_df,
            x="Latency Range",
            y="Count",
            labels={"Latency Range": "Response Latency Range", "Count": "Responses"},
            color="Latency Range",
            color_discrete_sequence=['#34d399', '#6366f1', '#a855f7', '#06b6d4'],
            template="plotly_dark"
        )
        fig_latency.update_layout(
            margin=dict(t=20, b=20, l=20, r=20),
            height=280,
            showlegend=False,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        row2_charts.append(("Response Time Distribution", fig_latency, '⚡'))
    except Exception:
        pass

# 2. Retrieval Confidence Distribution
if scores:
    score_bins = {
        "0.60–0.70": 0,
        "0.70–0.80": 0,
        "0.80–0.90": 0,
        "0.90–1.00": 0
    }
    for s in scores:
        if 0.60 <= s < 0.70:
            score_bins["0.60–0.70"] += 1
        elif 0.70 <= s < 0.80:
            score_bins["0.70–0.80"] += 1
        elif 0.80 <= s < 0.90:
            score_bins["0.80–0.90"] += 1
        elif 0.90 <= s <= 1.00:
            score_bins["0.90–1.00"] += 1
            
    try:
        import plotly.express as px
        score_df = pd.DataFrame(list(score_bins.items()), columns=["Confidence Range", "Chunk Count"])
        fig_score = px.bar(
            score_df,
            x="Confidence Range",
            y="Chunk Count",
            labels={"Confidence Range": "Retrieval Confidence Score Range", "Chunk Count": "Retrieved Chunks"},
            color="Confidence Range",
            color_discrete_sequence=['#06b6d4', '#6366f1', '#a855f7', '#10b981'],
            template="plotly_dark"
        )
        fig_score.update_layout(
            margin=dict(t=20, b=20, l=20, r=20),
            height=280,
            showlegend=False,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        row2_charts.append(("Retrieval Confidence Distribution", fig_score, '🎯'))
    except Exception:
        pass

if row2_charts:
    st.markdown("---")
    if len(row2_charts) == 2:
        col_row2_left, col_row2_right = st.columns(2)
        with col_row2_left:
            st.subheader(f"{row2_charts[0][2]} {row2_charts[0][0]}")
            st.plotly_chart(row2_charts[0][1], use_container_width=True)
        with col_row2_right:
            st.subheader(f"{row2_charts[1][2]} {row2_charts[1][0]}")
            st.plotly_chart(row2_charts[1][1], use_container_width=True)
    else:
        st.subheader(f"{row2_charts[0][2]} {row2_charts[0][0]}")
        st.plotly_chart(row2_charts[0][1], use_container_width=True)

# Conditional Daily Query Count line chart
df_resp['date'] = pd.to_datetime(df_resp['timestamp']).dt.date
if df_resp['date'].nunique() >= 3:
    st.markdown("---")
    st.subheader("📈 Daily Query Count")
    try:
        import plotly.express as px
        daily_queries = df_resp.groupby('date').size().reset_index(name='Queries')
        fig_line = px.line(
            daily_queries,
            x='date',
            y='Queries',
            markers=True,
            labels={'date': 'Date', 'Queries': 'Queries Executed'},
            template="plotly_dark"
        )
        fig_line.update_traces(line_color='#6366f1')
        fig_line.update_layout(
            margin=dict(t=20, b=20, l=20, r=20),
            height=260,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_line, use_container_width=True)
    except Exception:
        st.line_chart(df_resp.groupby('date').size())


