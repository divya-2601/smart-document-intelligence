"""
vector_store.py — Pinecone vector database integration.
Handles index connection, upsert, query, and stats.
Uses the new pinecone SDK (pinecone v9+).
"""

import os
import time
from typing import List, Dict, Any, Optional
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX   = os.getenv("PINECONE_INDEX")

if not PINECONE_API_KEY:
    raise EnvironmentError("PINECONE_API_KEY not found in environment / .env file.")
if not PINECONE_INDEX:
    raise EnvironmentError("PINECONE_INDEX not found in environment / .env file.")

EMBED_DIM    = 3072   # must match Gemini text-embedding-2 / text-embedding-004
UPSERT_BATCH = 100   # vectors per upsert call


# ---------------------------------------------------------------------------
# Singleton client
# ---------------------------------------------------------------------------
_pc: Optional[Pinecone] = None
_index = None


def _get_client() -> Pinecone:
    global _pc
    if _pc is None:
        _pc = Pinecone(api_key=PINECONE_API_KEY)
    return _pc


def get_index():
    """Return (and lazily create) the Pinecone index."""
    global _index
    if _index is not None:
        return _index
        
    pc = _get_client()
    # Check if index exists, create if not
    if PINECONE_INDEX not in [idx.name for idx in pc.list_indexes()]:
        pc.create_index(
            name=PINECONE_INDEX,
            dimension=EMBED_DIM,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        # Wait for index to be ready
        while not pc.describe_index(PINECONE_INDEX).status.ready:
            time.sleep(1)
            
    _index = pc.Index(PINECONE_INDEX)
    return _index


def upsert_chunks(chunks: List[Dict[str, Any]], embeddings: List[List[float]]) -> int:
    """
    Upsert list of chunks and their corresponding embeddings to Pinecone index.
    """
    index = get_index()
    vectors = []
    for chunk, emb in zip(chunks, embeddings):
        vectors.append({
            "id": chunk["chunk_id"],
            "values": emb,
            "metadata": {
                "text": chunk["text"],
                "page": chunk["page"],
                "filename": chunk["filename"],
            },
        })

    total = 0
    for i in range(0, len(vectors), UPSERT_BATCH):
        batch = vectors[i : i + UPSERT_BATCH]
        resp  = index.upsert(vectors=batch)
        total += resp.upserted_count
    return total


def query_index(
    query_vec: List[float],
    top_k: int = 6,
    filter_dict: Optional[Dict] = None,
) -> List[Dict[str, Any]]:
    """
    Query the Pinecone index and return top-k matching chunks.

    Returns a list of dicts:
        { "text", "page", "filename", "score" }
    """
    index = get_index()
    kwargs: Dict[str, Any] = {
        "vector":           query_vec,
        "top_k":            top_k,
        "include_metadata": True,
    }
    if filter_dict:
        kwargs["filter"] = filter_dict

    result = index.query(**kwargs)
    matches = []
    for match in result.matches:
        meta = match.metadata or {}
        matches.append({
            "text":     meta.get("text", ""),
            "page":     meta.get("page", "?"),
            "filename": meta.get("filename", "Unknown"),
            "score":    round(match.score, 4),
        })
    return matches


def get_index_stats() -> Dict[str, Any]:
    """Return index statistics (total vectors, dimension, etc.)."""
    index = get_index()
    stats = index.describe_index_stats()
    return {
        "total_vectors": stats.total_vector_count,
        "dimension":     stats.dimension,
        "namespaces":    dict(stats.namespaces) if stats.namespaces else {},
    }


def delete_all_vectors() -> None:
    """Delete all vectors in the index (clears the knowledge base)."""
    index = get_index()
    index.delete(delete_all=True)
