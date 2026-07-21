"""Recursive character text splitter with configurable overlap."""

from typing import Any

import config


def chunk_text(doc_text: str,
               chunk_size: int = None,
               chunk_overlap: int = None) -> list[dict[str, Any]]:
    """Split a single document into overlapping chunks.

    Uses recursive character splitting on paragraph boundaries first,
    then sentence boundaries, then character boundaries.

    Returns a list of dicts::
        [{"index": 0, "text": "...", "start_char": 0, "end_char": 312}, ...]
    """
    chunk_size = chunk_size or config.CHUNK_SIZE
    chunk_overlap = chunk_overlap or config.CHUNK_OVERLAP

    if len(doc_text) <= chunk_size:
        return [{"index": 0, "text": doc_text, "start_char": 0, "end_char": len(doc_text)}]

    separators = ["\n\n", "\n", ". ", "! ", "? ", ", ", " "]

    chunks = []
    start = 0

    while start < len(doc_text):
        end = min(start + chunk_size, len(doc_text))

        if end < len(doc_text):
            # Try to break at a separator
            best_break = -1
            for sep in separators:
                break_pos = doc_text.rfind(sep, start + chunk_size // 2, end)
                if break_pos > best_break:
                    best_break = break_pos
            if best_break > 0:
                end = best_break + len(sep) if best_break + len(sep) <= len(doc_text) else best_break

        text = doc_text[start:end]
        if text.strip():
            chunks.append({
                "index": len(chunks),
                "text": text,
                "start_char": start,
                "end_char": end,
            })

        # Advance start, accounting for overlap
        start = end - chunk_overlap if end < len(doc_text) else len(doc_text)

    return chunks


def chunk_all(docs: list[str],
              chunk_size: int = None,
              chunk_overlap: int = None) -> list[dict[str, Any]]:
    """Chunk multiple documents. Returns flat list with doc_index."""
    all_chunks = []
    for doc_index, text in enumerate(docs):
        doc_chunks = chunk_text(text, chunk_size, chunk_overlap)
        for c in doc_chunks:
            c["doc_index"] = doc_index
        all_chunks.extend(doc_chunks)
    return all_chunks
