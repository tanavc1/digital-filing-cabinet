"""
Document chunking with overlap and boundary detection.
"""
import re
from typing import List, Dict

from core.utils import infer_chunk_type


def chunk_text_with_overlap(
    text: str,
    chunk_size_chars: int,
    overlap_ratio: float,
    boundary_window: int = 250
) -> List[Dict]:
    """
    Split text into overlapping chunks with intelligent boundary detection.

    Prefers splitting at:
    1. Markdown headings
    2. Paragraph breaks
    3. Sentence boundaries

    Returns list of dicts with: chunk_index, start_char, end_char, text, chunk_type
    """
    if chunk_size_chars < 200:
        raise ValueError("chunk_size_chars too small; use >= 200")
    if not (0.0 <= overlap_ratio < 1.0):
        raise ValueError("overlap_ratio must be in [0.0, 1.0)")
    overlap_chars = int(chunk_size_chars * overlap_ratio)
    if overlap_chars >= chunk_size_chars:
        overlap_chars = max(0, chunk_size_chars - 1)

    n = len(text)
    chunks = []
    start = 0
    idx = 0

    while start < n:
        raw_end = min(start + chunk_size_chars, n)
        end = raw_end

        # Prefer ending before a markdown heading if nearby
        back_start = max(start + 200, raw_end - boundary_window)
        back_window = text[back_start:raw_end]
        heading_pos = back_window.rfind("\n#")
        if heading_pos != -1:
            candidate_end = back_start + heading_pos
            if candidate_end - start >= int(0.6 * chunk_size_chars):
                end = candidate_end

        # Otherwise extend forward to natural boundary
        if end == raw_end and raw_end < n:
            window_end = min(n, raw_end + boundary_window)
            window = text[raw_end:window_end]
            candidates = []
            for pat in ["\n\n", "\n", ". ", "? ", "! ", "; ", ": "]:
                pos = window.find(pat)
                if pos != -1:
                    candidates.append(raw_end + pos + len(pat))
            if candidates:
                end = min(candidates)

        if end <= start:
            end = min(start + chunk_size_chars, n)

        chunk = text[start:end]
        chunks.append({
            "chunk_index": idx,
            "start_char": start,
            "end_char": end,
            "text": chunk,
            "chunk_type": infer_chunk_type(chunk),
        })
        idx += 1

        if end >= n:
            break
        start = max(0, end - overlap_chars)

    return chunks
