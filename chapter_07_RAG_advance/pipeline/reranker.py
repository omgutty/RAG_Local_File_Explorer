"""Cross-encoder re-ranker using BAAI/bge-reranker-v2-m3."""

import logging
from typing import Any

from qdrant_client.models import ScoredPoint

import config
from models.loader import get_reranker

logger = logging.getLogger(__name__)


def rerank(query: str, candidates: list[ScoredPoint],
           top_k: int = None) -> dict[str, Any]:
    """Re-rank candidate chunks using the cross-encoder.

    Args:
        query: Original (or rewritten) user query.
        candidates: List of ScoredPoint from RRF fusion.
        top_k: Number of chunks to keep after re-ranking.

    Returns dict::
        {
            "reranked": [ScoredPoint, ...],   # sorted by cross-encoder score
            "scores": {point_id: cross_encoder_score, ...},
            "before": {point_id: rrf_score, ...},
        }
    """
    top_k = top_k or config.TOP_K_RERANK

    if not candidates:
        return {"reranked": [], "scores": {}, "before": {}}

    model = get_reranker()

    # Build query + text pairs
    texts = []
    for p in candidates:
        text = p.payload.get("text", "")
        texts.append(text)

    pairs = [[query, t] for t in texts]

    # Compute cross-encoder scores
    scores = model.compute_score(pairs, normalize=True)
    if isinstance(scores, list) and len(scores) > 0 and isinstance(scores[0], list):
        scores = [s[0] for s in scores]

    # Before re-ranking scores (the RRF scores)
    before = {}
    for p in candidates:
        before[p.id] = p.score

    # Attach scores to points and sort descending
    scored = list(zip(candidates, scores))
    scored.sort(key=lambda x: x[1], reverse=True)

    reranked = []
    score_map = {}
    for p, s in scored:
        p.score = s  # Override score with re-ranker score
        reranked.append(p)
        score_map[p.id] = s

    result = {
        "reranked": reranked[:top_k],
        "scores": score_map,
        "before": before,
    }
    logger.info("Reranked %d candidates -> top %d (best score: %.4f)",
                len(candidates), top_k, scores[0] if scores else 0)
    return result
