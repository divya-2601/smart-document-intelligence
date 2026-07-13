"""
pdf_processor.py — PDF parsing and chunking with PyMuPDF.
Uses RecursiveCharacterTextSplitter for semantic chunking.
"""

import fitz  # PyMuPDF
import hashlib
from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CHUNK_SIZE = 800        # characters per chunk
CHUNK_OVERLAP = 150     # overlap between chunks


def _file_hash(file_bytes: bytes) -> str:
    """Return a short SHA-256 hex digest of the file bytes."""
    return hashlib.sha256(file_bytes).hexdigest()[:12]


def extract_text_from_pdf(file_bytes: bytes, filename: str) -> List[Dict[str, Any]]:
    """
    Open a PDF from bytes and extract text page-by-page.

    Returns a list of dicts:
        {
            "text":     str,          # raw page text
            "page":     int,          # 1-indexed page number
            "filename": str,          # original filename
        }
    """
    pages: List[Dict[str, Any]] = []
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text").strip()
            if text:                  # skip blank pages
                pages.append({
                    "text": text,
                    "page": page_num + 1,
                    "filename": filename,
                })
        doc.close()
    except Exception as exc:
        raise RuntimeError(f"Failed to parse '{filename}': {exc}") from exc
    return pages


def chunk_pages(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Split page-level text into smaller, overlapping chunks.

    Each chunk dict:
        {
            "text":       str,   # chunk text
            "page":       int,   # source page number
            "filename":   str,   # source filename
            "chunk_id":   str,   # stable unique ID (sha256 of content)
        }
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks: List[Dict[str, Any]] = []
    for page in pages:
        sub_texts = splitter.split_text(page["text"])
        for sub_text in sub_texts:
            chunk_id = hashlib.sha256(
                f"{page['filename']}_{page['page']}_{sub_text}".encode()
            ).hexdigest()[:20]
            chunks.append({
                "text": sub_text.strip(),
                "page": page["page"],
                "filename": page["filename"],
                "chunk_id": chunk_id,
            })
    return chunks


def process_pdf(file_bytes: bytes, filename: str) -> List[Dict[str, Any]]:
    """
    End-to-end: bytes → parsed pages → chunks.
    Returns a list of chunk dicts ready for embedding.
    """
    pages = extract_text_from_pdf(file_bytes, filename)
    if not pages:
        raise ValueError(f"No text could be extracted from '{filename}'.")
    chunks = chunk_pages(pages)
    return chunks
