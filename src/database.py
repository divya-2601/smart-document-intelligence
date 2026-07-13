"""
src/database.py — Shared SQLite Database Helper Operations
Handles schema initialization, feedback saving, chat conversation history, and document indexing records.
"""

import sqlite3
import datetime
import pathlib
import json
import pandas as pd

DB_PATH = pathlib.Path(__file__).parent.parent / "doc_intel.db"

def init_db() -> None:
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        # 1. feedbacks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedbacks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                user_question TEXT,
                prompt_version TEXT,
                response TEXT UNIQUE,
                response_time REAL,
                feedback TEXT,
                source_document TEXT,
                page_number TEXT
            )
        """)
        
        # 2. documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT UNIQUE,
                file_hash TEXT UNIQUE,
                upload_date TEXT,
                chunk_count INTEGER,
                file_size TEXT
            )
        """)
        
        # 3. conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT,
                created_at TEXT
            )
        """)
        
        # 4. chat_messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT,
                role TEXT,
                content TEXT,
                citations TEXT,
                latency REAL,
                version TEXT,
                timestamp TEXT,
                user_question TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        """)
        
        conn.commit()
        conn.close()
    except Exception:
        pass

# --- Feedback helpers ---
def save_feedback(user_question, prompt_version, response, response_time, feedback, source_document, page_number):
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        # Prevent duplicate feedbacks for the same response
        cursor.execute("SELECT id FROM feedbacks WHERE response = ?", (response,))
        if cursor.fetchone():
            conn.close()
            return False
            
        timestamp = datetime.datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO feedbacks (timestamp, user_question, prompt_version, response, response_time, feedback, source_document, page_number)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (timestamp, user_question, prompt_version, response, response_time, feedback, source_document, page_number))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False

# --- Conversation helpers ---
def load_conversations():
    try:
        conn = sqlite3.connect(str(DB_PATH))
        df = pd.read_sql_query("SELECT * FROM conversations ORDER BY created_at DESC", conn)
        conn.close()
        return df.to_dict('records')
    except Exception:
        return []

def save_conversation(conv_id, title):
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM conversations WHERE id = ?", (conv_id,))
        if cursor.fetchone():
            cursor.execute("UPDATE conversations SET title = ? WHERE id = ?", (title, conv_id))
        else:
            now = datetime.datetime.now().isoformat()
            cursor.execute("INSERT INTO conversations (id, title, created_at) VALUES (?, ?, ?)", (conv_id, title, now))
        conn.commit()
        conn.close()
    except Exception:
        pass

def delete_conversation(conv_id):
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
        cursor.execute("DELETE FROM chat_messages WHERE conversation_id = ?", (conv_id,))
        conn.commit()
        conn.close()
    except Exception:
        pass

def rename_conversation(conv_id, new_title):
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("UPDATE conversations SET title = ? WHERE id = ?", (new_title, conv_id))
        conn.commit()
        conn.close()
    except Exception:
        pass

def load_messages(conv_id):
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("SELECT role, content, citations, latency, version, user_question FROM chat_messages WHERE conversation_id = ? ORDER BY id ASC", (conv_id,))
        rows = cursor.fetchall()
        conn.close()
        messages = []
        for row in rows:
            role, content, citations_str, latency, version, question = row
            citations = json.loads(citations_str) if citations_str else []
            messages.append({
                "role": role,
                "content": content,
                "citations": citations,
                "latency": latency,
                "version": version,
                "question": question
            })
        return messages
    except Exception:
        return []

def save_message(conv_id, role, content, citations, latency, version, question="N/A"):
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        citations_str = json.dumps(citations)
        now = datetime.datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO chat_messages (conversation_id, role, content, citations, latency, version, timestamp, user_question)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (conv_id, role, content, citations_str, latency, version, now, question))
        conn.commit()
        conn.close()
    except Exception:
        pass

# --- Document helpers ---
def save_document(file_name, file_hash, chunk_count, file_size):
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        now = datetime.datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO documents (file_name, file_hash, upload_date, chunk_count, file_size)
            VALUES (?, ?, ?, ?, ?)
        """, (file_name, file_hash, now, chunk_count, file_size))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False
    except Exception:
        return False

def delete_document_from_db(file_name):
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("DELETE FROM documents WHERE file_name = ?", (file_name,))
        conn.commit()
        conn.close()
    except Exception:
        pass

def clear_all_documents_from_db():
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("DELETE FROM documents")
        conn.commit()
        conn.close()
    except Exception:
        pass

def load_processed_docs_from_db():
    try:
        conn = sqlite3.connect(str(DB_PATH))
        df = pd.read_sql_query("SELECT * FROM documents", conn)
        conn.close()
        docs = []
        for _, row in df.iterrows():
            docs.append({
                "name": row["file_name"],
                "chunks": row["chunk_count"],
                "size_str": row["file_size"],
                "upload_date": row["upload_date"]
            })
        return docs
    except Exception:
        return []
