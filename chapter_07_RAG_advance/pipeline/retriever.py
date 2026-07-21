"""Hybrid retriever — dense + sparse search with RRF fusion."""

import logging
from typing import Any

from qdrant_client.models import ScoredPoint

import config
from pipeline import embedder, indexer

logger = logging.getLogger(__name__)


def rrf_fuse(dense_results: list[ScoredPoint],
             sparse_results: list[ScoredPoint],
             k: int = None) -> list[ScoredPoint]:
    """Reciprocal Rank Fusion.

    Each result point gets score = 1/(k + rank) from each ranked list.
    Scores are summed per point, then re-sorted descending.
    """
    k = k or config.RRF_K
    scores: dict[str, float] = {}
    for rank, point in enumerate(dense_results):
        scores[point.id] = scores.get(point.id, 0.0) + 1.0 / (k + rank + 1)
    for rank, point in enumerate(sparse_results):
        scores[point.id] = scores.get(point.id, 0.0) + 1.0 / (k + rank + 1)

    all_points = {}
    for p in dense_results:
        all_points[p.id] = p
    for p in sparse_results:
        if p.id not in all_points:
            all_points[p.id] = p

    sorted_ids = sorted(scores, key=scores.get, reverse=True)
    result = [all_points[pid] for pid in sorted_ids]
    logger.info("RRF fused %d dense + %d sparse -> %d candidates",
                len(dense_results), len(sparse_results), len(result))
    return result


def search_hybrid(query_text: str) -> dict[str, Any]:
    """Run hybrid search: embed query, search dense + sparse, RRF fuse.

    Returns dict with keys:
        dense_results, sparse_results, rrf_results,
        dense_vector, sparse_vector
    """
    # 1. Encode query
    dense_vec = embedder.encode_dense([query_text])[0]
    sparse_vec = embedder.encode_sparse([query_text])[0]

    # 2. Search
    dense_results = indexer.search_dense(dense_vec)
    sparse_results = indexer.search_sparse(sparse_vec)

    # 3. Fuse
    fused = rrf_fuse(dense_results, sparse_results)

    return {
        "dense_results": dense_results,
        "sparse_results": sparse_results,
        "rrf_results": fused,
        "dense_vector": dense_vec,
        "sparse_vector": sparse_vec,
    }
