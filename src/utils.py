"""
utils.py — Shared helper utilities.
"""

import re
from typing import List, Dict, Any


def format_file_size(num_bytes: int) -> str:
    """Return a human-readable file size string."""
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"


def truncate_text(text: str, max_len: int = 120) -> str:
    """Truncate text to max_len chars with ellipsis."""
    return text[:max_len].rstrip() + "…" if len(text) > max_len else text


def score_to_percentage(score: float) -> str:
    """Convert a cosine similarity score (0–1) to a % string."""
    return f"{score * 100:.1f}%"


def deduplicate_by_key(items: List[Dict[str, Any]], key: str) -> List[Dict[str, Any]]:
    """Remove duplicate dicts by a given key, preserving order."""
    seen = set()
    out  = []
    for item in items:
        val = item.get(key)
        if val not in seen:
            seen.add(val)
            out.append(item)
    return out


def sanitize_filename(name: str) -> str:
    """Strip dangerous characters from a filename."""
    return re.sub(r"[^\w\s\-.]", "", name).strip()
