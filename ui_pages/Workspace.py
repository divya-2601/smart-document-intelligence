"""
ui_pages/Workspace.py — NotebookLM-style Workspace Page
Integrates Document Management (Left Panel) and Semantic Chat (Right Panel) into a single workspace view.
"""

import time
import datetime
import sqlite3
import pathlib
import hashlib
import streamlit as st

# ---------------------------------------------------------------------------
# Lazy Imports for RAG & Database Logic
# ---------------------------------------------------------------------------
try:
    from src.rag_pipeline  import stream_answer
    from src.pdf_processor import process_pdf
    from src.embeddings    import embed_texts
    from src.vector_store  import upsert_chunks, delete_all_vectors, get_index, get_index_stats
    from src.utils         import score_to_percentage  # noqa: F401 — available for future use
    from src.database      import (
        load_conversations, save_conversation, delete_conversation,
        rename_conversation, load_messages, save_message, save_feedback,
        load_processed_docs_from_db, save_document, delete_document_from_db,
        clear_all_documents_from_db, DB_PATH
    )
    IMPORTS_OK = True
except Exception as _err:
    IMPORTS_OK = False
    IMPORT_ERROR = str(_err)

# ---------------------------------------------------------------------------
# Pinecone helper: delete vectors by file_name
# ---------------------------------------------------------------------------
def delete_pdf_vectors_from_pinecone(file_name):
    try:
        idx = get_index()
        idx.delete(filter={"filename": file_name})
        return True
    except Exception as e:
        st.error(f"Failed to delete Pinecone vectors: {e}")
        return False

def format_file_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.1f} KB"
    else:
        return f"{size_bytes/(1024*1024):.1f} MB"

# ---------------------------------------------------------------------------
# Initialize session states
# ---------------------------------------------------------------------------
def _init_state() -> None:
    db_docs = load_processed_docs_from_db() if IMPORTS_OK else []
    total_vects = 0
    if IMPORTS_OK:
        try:
            total_vects = get_index_stats().get("total_vectors", 0)
        except Exception:
            pass
            
    defaults = {
        "chat_history":   [],
        "processed_docs": db_docs,
        "total_vectors":  total_vects,
        "active_conversation_id": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

_init_state()

# ---------------------------------------------------------------------------
# Main Page Body
# ---------------------------------------------------------------------------
if not IMPORTS_OK:
    st.error(f"❌ Initialization failed: `{IMPORT_ERROR}`")
    st.stop()

# Get active prompt version
active_version = "v1.0.0"
try:
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("SELECT version FROM prompts WHERE is_active = 1 LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        active_version = row[0]
except Exception:
    pass

total_chunks = sum(d["chunks"] for d in st.session_state["processed_docs"])

# Layout: Split screen 25% Left Panel, 57% Right Panel (proportions relative to screen width)
col_left, col_right = st.columns([25, 57])

# ===========================================================================
# LEFT PANEL (Document Indexer & Sources Inventory)
# ===========================================================================
with col_left:
    st.markdown("<h3 style='margin: 0 0 10px 0; font-size: 1.15rem; font-weight: 700; color: #f0f6fc;'>📚 Sources</h3>", unsafe_allow_html=True)
    
    # Small Summary Dashboard
    st.markdown(
        f"""
        <div style="background: #161b22; border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; 
                    padding: 0.5rem 0.8rem; margin-bottom: 1rem; font-size: 0.8rem; line-height: 1.5;">
            <div style="display:flex; justify-content:space-between;"><span style="color:#8b949e;">Files Indexed:</span> <strong style="color:#f0f6fc;">{len(st.session_state['processed_docs'])}</strong></div>
            <div style="display:flex; justify-content:space-between;"><span style="color:#8b949e;">Total Chunks:</span> <strong style="color:#f0f6fc;">{total_chunks}</strong></div>
            <div style="display:flex; justify-content:space-between;"><span style="color:#8b949e;">Prompt Mode:</span> <strong style="color:#a855f7;">{active_version}</strong></div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Upload PDF Form
    uploaded_files = st.file_uploader(
        "Upload sources",
        type=["pdf"],
        accept_multiple_files=True,
        key="workspace_upload",
        label_visibility="collapsed"
    )
    
    if uploaded_files:
        if st.button("⚡ Process & Index Chunks", use_container_width=True, key="process_index_workspace"):
            pipeline_placeholder = st.empty()
            with pipeline_placeholder.container():
                progress_bar = st.progress(0, text="Indexing file bytes...")
                status_text = st.empty()
                all_chunks_buf = []
                new_docs = []
                
                try:
                    for idx, file in enumerate(uploaded_files):
                        file_bytes = file.read()
                        file_size_formatted = format_file_size(len(file_bytes))
                        file_hash = hashlib.sha256(file_bytes).hexdigest()
                        
                        # Prevent duplicates via hash check
                        conn = sqlite3.connect(str(DB_PATH))
                        cursor = conn.cursor()
                        cursor.execute("SELECT file_name FROM documents WHERE file_hash = ?", (file_hash,))
                        dup = cursor.fetchone()
                        conn.close()
                        
                        if dup:
                            st.toast(f"⚠️ Skip '{file.name}': Already uploaded as '{dup[0]}'.")
                            continue
                            
                        status_text.markdown(f"Parsing `{file.name}` with PyMuPDF...")
                        progress_bar.progress(int((idx+1)/len(uploaded_files) * 25), text=f"Parsing {file.name}...")
                        
                        chunks = process_pdf(file_bytes, file.name)
                        all_chunks_buf.extend(chunks)
                        new_docs.append({
                            "name": file.name,
                            "chunks": len(chunks),
                            "size_str": file_size_formatted,
                            "hash": file_hash
                        })
                        
                    if all_chunks_buf:
                        progress_bar.progress(50, text="Generating Gemini Embeddings...")
                        status_text.markdown(f"Generating vectors for {len(all_chunks_buf)} text segments...")
                        
                        texts = [c["text"] for c in all_chunks_buf]
                        embeddings = embed_texts(texts, task_type="RETRIEVAL_DOCUMENT")
                        
                        progress_bar.progress(75, text="Indexing in Pinecone...")
                        status_text.markdown("Upserting similarity vectors to vector store index...")
                        upsert_chunks(all_chunks_buf, embeddings)
                        
                        progress_bar.progress(90, text="Writing metadata to database...")
                        for doc in new_docs:
                            save_document(
                                file_name=doc["name"],
                                file_hash=doc["hash"],
                                chunk_count=doc["chunks"],
                                file_size=doc["size_str"]
                            )
                            
                        progress_bar.progress(100, text="Finished successfully!")
                        st.toast("✅ Indexing completed successfully!")
                        
                        # Sync state
                        st.session_state["processed_docs"] = load_processed_docs_from_db()
                        try:
                            st.session_state["total_vectors"] = get_index_stats().get("total_vectors", 0)
                        except Exception:
                            pass
                        time.sleep(1.0)
                        st.rerun()
                    else:
                        st.warning("No new unique documents to index.")
                        
                except Exception as e:
                    st.error(f"Failed to process: {e}")
                    
    # Indexed Documents List Table
    st.markdown("<p style='font-size: 0.85rem; font-weight: 600; color: #8b949e; text-transform: uppercase; margin-top:1rem;'>Indexed Documents</p>", unsafe_allow_html=True)
    docs_list = load_processed_docs_from_db()
    if not docs_list:
        st.info("No sources uploaded yet.")
    else:
        # Simple metadata presentation list
        for doc in docs_list:
            st.markdown(
                f"""
                <div style="font-size: 0.82rem; background: rgba(255,255,255,0.03); 
                            border:1px solid rgba(255,255,255,0.06); border-radius: 4px; 
                            padding: 4px 8px; margin-bottom: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                    📄 {doc['name']} <span style="font-size: 0.72rem; color: #8b949e; float: right;">{doc['size_str']}</span>
                </div>
                """,
                unsafe_allow_html=True
            )
            
        st.markdown("<p style='font-size: 0.85rem; font-weight: 600; color: #8b949e; margin-top:1rem; margin-bottom: 0.2rem;'>Manage Sources</p>", unsafe_allow_html=True)
        doc_to_delete = st.selectbox("Delete PDF", options=[d["name"] for d in docs_list], label_visibility="collapsed")
        if st.button("🗑️ Delete Selected PDF", use_container_width=True, key="del_pdf_btn"):
            with st.spinner("Deleting..."):
                pc_deleted = delete_pdf_vectors_from_pinecone(doc_to_delete)
                if pc_deleted:
                    delete_document_from_db(doc_to_delete)
                    st.toast(f"Deleted '{doc_to_delete}'")
                    st.session_state["processed_docs"] = [d for d in st.session_state["processed_docs"] if d["name"] != doc_to_delete]
                    try:
                        st.session_state["total_vectors"] = get_index_stats().get("total_vectors", 0)
                    except Exception:
                        pass
                    time.sleep(1.0)
                    st.rerun()
        if st.button("🚨 Wipe Knowledge Base", use_container_width=True, help="Wipe Pinecone & SQLite metadata", key="wipe_kb_btn"):
            with st.spinner("Wiping..."):
                try:
                    delete_all_vectors()
                    clear_all_documents_from_db()
                    st.session_state["processed_docs"] = []
                    st.session_state["total_vectors"] = 0
                    st.toast("Wiped index completely")
                    time.sleep(1.0)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

# ===========================================================================
# RIGHT PANEL (Dialogue workspace)
# ===========================================================================
with col_right:
    # Top Control Bar (New Chat / Chat list Selector)
    col_cb1, col_cb2 = st.columns([1, 2.5])
    
    with col_cb1:
        if st.button("➕ New Chat", key="workspace_new_chat", use_container_width=True):
            new_id = f"conv_{int(time.time())}"
            title = f"Chat on {datetime.datetime.now().strftime('%m-%d %H:%M')}"
            save_conversation(new_id, title)
            st.session_state["active_conversation_id"] = new_id
            st.session_state["chat_history"] = []
            st.rerun()
            
    with col_cb2:
        convs = load_conversations()
        if not st.session_state["active_conversation_id"]:
            if convs:
                st.session_state["active_conversation_id"] = convs[0]["id"]
                st.session_state["chat_history"] = load_messages(convs[0]["id"])
            else:
                new_id = f"conv_{int(time.time())}"
                title = f"Chat on {datetime.datetime.now().strftime('%m-%d %H:%M')}"
                save_conversation(new_id, title)
                st.session_state["active_conversation_id"] = new_id
                st.session_state["chat_history"] = []
                
        # Dropdown selection of conversation threads
        conv_titles = {c["id"]: c["title"] for c in convs}
        conv_ids = [c["id"] for c in convs]
        
        # Safe lookup in case session conversation ID gets deleted
        if st.session_state["active_conversation_id"] not in conv_ids and conv_ids:
            st.session_state["active_conversation_id"] = conv_ids[0]
            st.session_state["chat_history"] = load_messages(conv_ids[0])
            
        selected_id = st.selectbox(
            "Select Conversation History",
            options=conv_ids,
            format_func=lambda x: conv_titles.get(x, "Untitled"),
            index=conv_ids.index(st.session_state["active_conversation_id"]) if st.session_state["active_conversation_id"] in conv_ids else 0,
            label_visibility="collapsed"
        )
        if selected_id != st.session_state["active_conversation_id"]:
            st.session_state["active_conversation_id"] = selected_id
            st.session_state["chat_history"] = load_messages(selected_id)
            st.rerun()

    st.markdown("<hr style='margin: 0.5rem 0 1rem; border-color: rgba(255,255,255,0.06);'>", unsafe_allow_html=True)

    # Empty State Alert if Knowledge Base has no sources
    if len(st.session_state["processed_docs"]) == 0:
        st.markdown(
            """
            <div style="text-align: center; padding: 4rem 1rem; color: #8b949e;">
                <h4>No documents indexed.</h4>
                <p>Please upload PDF files in the Left Panel and click 'Process & Index Chunks' to begin chatting.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        # Chat dialogue stream
        chat_workspace = st.container()
        with chat_workspace:
            for msg in st.session_state["chat_history"]:
                with st.chat_message(msg["role"], avatar="🧑" if msg["role"] == "user" else "🧠"):
                    st.markdown(msg["content"])
                    if msg["role"] == "assistant":
                        citations = msg.get("citations", [])
                        if citations:
                            cite_tags = []
                            for c in citations:
                                cite_tags.append(f"📄 {c['filename']} (Pg. {c['page']})")
                            st.markdown(
                                f"<p style='font-size:0.75rem; color:#8b949e; margin-top: 4px; font-weight: 500;'>Sources: {', '.join(cite_tags)}</p>",
                                unsafe_allow_html=True
                            )
                        
                        # Feedback controls
                        if "feedback_submitted" not in st.session_state:
                            st.session_state["feedback_submitted"] = set()
                        
                        response_text = msg["content"]
                        if response_text in st.session_state["feedback_submitted"]:
                            st.markdown("<small style='color:#3fb950; font-weight:bold; font-size:0.72rem;'>✓ Feedback saved</small>", unsafe_allow_html=True)
                        else:
                            col_f1, col_f2, _ = st.columns([0.16, 0.20, 0.64])
                            with col_f1:
                                if st.button("👍 Helpful", key=f"fb_up_{hash(response_text)}", use_container_width=True):
                                    docs = ", ".join(list(set([c["filename"] for c in citations]))) if citations else "None"
                                    pages = ", ".join(list(set([str(c["page"]) for c in citations]))) if citations else "None"
                                    success = save_feedback(
                                        user_question=msg.get("question", "N/A"),
                                        prompt_version=msg.get("version", "v1.0.0"),
                                        response=response_text,
                                        response_time=msg.get("latency", 0.0),
                                        feedback="Helpful",
                                        source_document=docs,
                                        page_number=pages
                                    )
                                    if success:
                                        st.session_state["feedback_submitted"].add(response_text)
                                        st.rerun()
                            with col_f2:
                                if st.button("👎 Not Helpful", key=f"fb_down_{hash(response_text)}", use_container_width=True):
                                    docs = ", ".join(list(set([c["filename"] for c in citations]))) if citations else "None"
                                    pages = ", ".join(list(set([str(c["page"]) for c in citations]))) if citations else "None"
                                    success = save_feedback(
                                        user_question=msg.get("question", "N/A"),
                                        prompt_version=msg.get("version", "v1.0.0"),
                                        response=response_text,
                                        response_time=msg.get("latency", 0.0),
                                        feedback="Not Helpful",
                                        source_document=docs,
                                        page_number=pages
                                    )
                                    if success:
                                        st.session_state["feedback_submitted"].add(response_text)
                                        st.rerun()

        # Fixed Chat Input Box
        user_query = st.chat_input(
            placeholder="Ask anything about your documents...",
            key="workspace_chat_input",
        )

        if user_query and user_query.strip():
            with st.chat_message("user", avatar="🧑"):
                st.markdown(user_query)

            st.session_state["chat_history"].append({
                "role":      "user",
                "content":   user_query,
                "citations": [],
            })
            
            save_message(
                conv_id=st.session_state["active_conversation_id"],
                role="user",
                content=user_query,
                citations=[],
                latency=0.0,
                version=""
            )

            with st.chat_message("assistant", avatar="🧠"):
                response_placeholder = st.empty()
                full_response        = ""
                final_meta           = {}

                start_time = time.time()
                with st.spinner("Thinking..."):
                    try:
                        chat_hist_for_rag = [
                            {"role": m["role"], "content": m["content"]}
                            for m in st.session_state["chat_history"][:-1]
                        ]
                        for chunk in stream_answer(user_query, chat_hist_for_rag):
                            if isinstance(chunk, dict):
                                final_meta = chunk
                            else:
                                full_response += chunk
                                response_placeholder.markdown(full_response + "▌")
                        response_placeholder.markdown(full_response)
                    except Exception as exc:
                        full_response = f"❌ Error: {exc}"
                        response_placeholder.error(full_response)

                latency = (time.time() - start_time) * 1000
                citations = final_meta.get("citations", [])
                if citations:
                    cite_tags = []
                    for c in citations:
                        cite_tags.append(f"📄 {c['filename']} (Pg. {c['page']})")
                    st.markdown(
                        f"<p style='font-size:0.75rem; color:#8b949e; margin-top: 4px; font-weight: 500;'>Sources: {', '.join(cite_tags)}</p>",
                        unsafe_allow_html=True
                    )

            # Persist in history
            st.session_state["chat_history"].append({
                "role":      "assistant",
                "content":   full_response,
                "citations": citations,
                "latency":   latency,
                "version":   active_version,
                "question":  user_query
            })
            
            save_message(
                conv_id=st.session_state["active_conversation_id"],
                role="assistant",
                content=full_response,
                citations=citations,
                latency=latency,
                version=active_version,
                question=user_query
            )
            
            # Auto-rename if default title
            current_conv = next((c for c in convs if c["id"] == st.session_state["active_conversation_id"]), None)
            if current_conv and current_conv["title"].startswith("Chat on"):
                new_title = user_query[:25] + "..." if len(user_query) > 25 else user_query
                rename_conversation(st.session_state["active_conversation_id"], new_title)
                st.rerun()
