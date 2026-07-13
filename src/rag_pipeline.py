"""
rag_pipeline.py — RAG orchestration using Gemini 2.5 Flash.
Uses the new google-genai SDK.
Retrieves relevant chunks from Pinecone and generates grounded answers.
"""

import os
import sqlite3
import pathlib
from typing import List, Dict, Any, Generator
from google import genai
from google.genai import types
from dotenv import load_dotenv

from src.embeddings  import embed_query
from src.vector_store import query_index

load_dotenv()

# ---------------------------------------------------------------------------
# Gemini LLM config
# ---------------------------------------------------------------------------
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise EnvironmentError("GOOGLE_API_KEY not found in environment / .env file.")

_client = genai.Client(api_key=GOOGLE_API_KEY)

LLM_MODEL  = "gemini-2.5-flash"
TOP_K      = 6       # retrieved chunks per query
MIN_SCORE  = 0.30    # minimum cosine similarity threshold


# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------
SYSTEM_INSTRUCTION = """You are an expert Document Intelligence Assistant.
Your role is to answer questions accurately based ONLY on the provided document context.

Guidelines:
- Answer directly and concisely using ONLY information from the context.
- If the context doesn't contain enough information, say: "I couldn't find enough information in the provided context to answer your question." Do NOT make up answers or use outside knowledge.
- If you use information from a document chunk, cite it correctly.
"""


def _get_active_prompt() -> str | None:
    """Fetch the active prompt template from SQLite."""
    db_path = pathlib.Path(__file__).parent.parent / "doc_intel.db"
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT template FROM prompts WHERE is_active = 1 LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        if row:
            return row[0]
    except Exception:
        pass
    return None


def retrieve_chunks(question: str) -> List[Dict[str, Any]]:
    """Retrieve relevant chunks from Pinecone, filtered by score."""
    import streamlit as st
    top_k = st.session_state.get("settings_top_k", TOP_K)
    min_score = st.session_state.get("settings_min_score", MIN_SCORE)
    
    query_vec = embed_query(question)
    matches = query_index(query_vec, top_k=top_k)
    return [m for m in matches if m.get("score", 0) >= min_score]



def _build_context_block(chunks: List[Dict[str, Any]]) -> str:
    """Build the context block to pass to the model."""
    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(
            f"--- Document Chunk {i} ---\n"
            f"Source File: {chunk['filename']}\n"
            f"Page: {chunk['page']}\n"
            f"Content: {chunk['text']}\n"
        )
    return "\n\n".join(parts)


def _build_prompt(question: str, context: str) -> str:
    """Build the user prompt with context and question."""
    return (
        f"Answer the question based only on the context below.\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {question}\n\n"
        f"Answer:"
    )


def _build_history(chat_history: List[Dict[str, str]] | None) -> List[types.Content]:
    """Convert chat history to google-genai types.Content objects."""
    history = []
    if chat_history:
        for msg in chat_history:
            role = "user" if msg["role"] == "user" else "model"
            history.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg["content"])]
                )
            )
    return history


def _format_citations(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Format chunks into citations metadata."""
    citations = []
    for chunk in chunks:
        # Generate a short preview of the text
        preview = chunk["text"][:150]
        if len(chunk["text"]) > 150:
            preview += "..."
        citations.append({
            "filename": chunk["filename"],
            "page": chunk["page"],
            "score": chunk["score"],
            "preview": preview,
        })
    return citations


def stream_answer(
    question: str,
    chat_history: List[Dict[str, str]] | None = None,
) -> Generator[str | Dict, None, None]:
    """
    Streaming RAG pipeline. Yields text chunks, then a final metadata dict.
    """
    chunks      = retrieve_chunks(question)
    has_context = bool(chunks)

    if not has_context:
        yield (
            "I couldn't find relevant information in the uploaded documents "
            "to answer your question. Please make sure the relevant PDFs have "
            "been processed, or try rephrasing your question."
        )
        yield {"citations": [], "chunks_used": 0, "has_context": False}
        return

    context_block = _build_context_block(chunks)
    
    active_template = _get_active_prompt()
    if active_template:
        try:
            # Format active template using context_block and question (support both {query} and {question})
            user_prompt = active_template.format(context=context_block, query=question, question=question)
        except Exception:
            user_prompt = _build_prompt(question, context_block)
    else:
        user_prompt = _build_prompt(question, context_block)

    history = _build_history(chat_history)
    chat    = _client.chats.create(
        model=LLM_MODEL,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION),
        history=history,
    )

    for resp_chunk in chat.send_message_stream(user_prompt):
        if resp_chunk.text:
            yield resp_chunk.text

    citations = _format_citations(chunks)
    yield {"citations": citations, "chunks_used": len(chunks), "has_context": True}


def query_context(question: str) -> tuple[str, List[Dict[str, Any]]]:
    """Retrieve context block and citations metadata in a single call."""
    chunks = retrieve_chunks(question)
    context_str = _build_context_block(chunks)
    citations = _format_citations(chunks)
    return context_str, citations


def get_client() -> genai.Client:
    """Return the initialized GenAI Client instance."""
    return _client

