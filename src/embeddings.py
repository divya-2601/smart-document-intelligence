"""
embeddings.py — Gemini text-embedding wrapper.
Uses gemini-embedding-2 via the google-genai SDK (v1 API).
"""

import os
import time
from typing import List
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Init — force v1 (stable) API
# ---------------------------------------------------------------------------
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise EnvironmentError("GOOGLE_API_KEY not found in environment / .env file.")

_client = genai.Client(
    api_key=GOOGLE_API_KEY,
    http_options=types.HttpOptions(api_version="v1"),
)

EMBEDDING_MODEL    = "gemini-embedding-2"
EMBED_DIM          = 3072  # we request 3072 dims to match our Pinecone index
BATCH_SIZE         = 100   # larger batch size to reduce total requests
RETRY_DELAY        = 3


def embed_texts(texts: List[str], task_type: str = "RETRIEVAL_DOCUMENT") -> List[List[float]]:
    """
    Embed a list of strings using gemini-embedding-2.

    Args:
        texts:      List of strings to embed.
        task_type:  'RETRIEVAL_DOCUMENT' for indexing, 'RETRIEVAL_QUERY' for queries.

    Returns:
        List of embedding vectors (each a list of floats, length EMBED_DIM).
    """
    all_embeddings: List[List[float]] = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        for attempt in range(5):
            try:
                result = _client.models.embed_content(
                    model=EMBEDDING_MODEL,
                    contents=batch,
                    config=types.EmbedContentConfig(
                        task_type=task_type,
                        output_dimensionality=EMBED_DIM,
                    ),
                )
                vecs = [emb.values for emb in result.embeddings]
                all_embeddings.extend(vecs)
                break
            except Exception as exc:
                if attempt == 4:
                    raise RuntimeError(f"Embedding failed after 5 attempts: {exc}") from exc
                
                # Double/triple sleep delay if we hit a rate limit (429) or quota exceeded error
                is_rate_limit = "429" in str(exc) or "quota" in str(exc).lower()
                sleep_time = (RETRY_DELAY * (attempt + 1)) * 5 if is_rate_limit else (RETRY_DELAY * (attempt + 1))
                time.sleep(sleep_time)

        # Pause between successful batches to respect Free Tier RPM limits
        if i + BATCH_SIZE < len(texts):
            time.sleep(2.5)

    return all_embeddings


def embed_query(query: str) -> List[float]:
    """Embed a single query string for retrieval."""
    results = embed_texts([query], task_type="RETRIEVAL_QUERY")
    return results[0]
