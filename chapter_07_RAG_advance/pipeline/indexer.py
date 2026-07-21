"""Qdrant client wrapper — embedded file store (no Docker needed).

Manages collection lifecycle, upsert, search (dense + sparse), and scroll."""

import logging
import json
from typing import Any, Optional

from qdrant_client import QdrantClient, models
from qdrant_client.models import (
    Filter, FieldCondition, MatchValue, Range,
    PointStruct, VectorParams, SparseVectorParams, SparseIndexParams,
    ScoredPoint,
)

import config

logger = logging.getLogger(__name__)

_COLLECTION = "vwo_test_cases"
_client: Optional[QdrantClient] = None


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        config.QDRANT_DIR.mkdir(parents=True, exist_ok=True)
        _client = QdrantClient(path=str(config.QDRANT_DIR))
        logger.info("Qdrant client initialised (embedded @ %s)", config.QDRANT_DIR)
    return _client


def collection_exists() -> bool:
    client = get_client()
    collections = [c.name for c in client.get_collections().collections]
    return _COLLECTION in collections


def create_collection(force: bool = False):
    """Create the '' collection with dense + sparse vector config."""
    client = get_client()
    if force:
        try:
            client.delete_collection(_COLLECTION)
        except Exception:
            pass

    if collection_exists():
        return

    client.create_collection(
        collection_name=_COLLECTION,
        vectors_config=VectorParams(
            size=config.EMBED_DIM,
            distance=models.Distance.COSINE,
        ),
        sparse_vectors_config={
            "sparse": SparseVectorParams(
                index=SparseIndexParams(on_disk=True),
            ),
        },
    )
    logger.info("Created collection '%s'", _COLLECTION)


def upsert_points(points: list[PointStruct]):
    """Insert or update points into the collection."""
    client = get_client()
    client.upsert(collection_name=_COLLECTION, points=points)
    logger.info("Upserted %d points", len(points))


def search_dense(vector: list[float],
                 top_n: int = None,
                 payload_filter: Optional[Filter] = None) -> list[ScoredPoint]:
    """Dense vector search."""
    top_n = top_n or config.TOP_N_HYBRID
    client = get_client()
    results = client.search(
        collection_name=_COLLECTION,
        query_vector=vector,
        limit=top_n,
        query_filter=payload_filter,
        with_payload=True,
        with_vectors=True,
    )
    return results


def search_sparse(vector: dict[int, float],
                  top_n: int = None,
                  payload_filter: Optional[Filter] = None) -> list[ScoredPoint]:
    """Sparse vector search."""
    top_n = top_n or config.TOP_N_HYBRID
    client = get_client()
    sparse_vec = models.SparseVector(
        indices=list(vector.keys()),
        values=list(vector.values()),
    )
    results = client.search(
        collection_name=_COLLECTION,
        query_vector=models.NamedSparseVector(name="sparse", vector=sparse_vec),
        limit=top_n,
        query_filter=payload_filter,
        with_payload=True,
        with_vectors=True,
    )
    return results


def scroll_points(limit: int = 50,
                  offset: int = 0,
                  payload_filter: Optional[Filter] = None,
                  with_vectors: bool = True):
    """Scroll through points with optional filter."""
    client = get_client()
    results, next_offset = client.scroll(
        collection_name=_COLLECTION,
        limit=limit,
        offset=offset if offset else None,
        filter=payload_filter,
        with_payload=True,
        with_vectors=with_vectors,
    )
    return results, next_offset


def count_points(payload_filter: Optional[Filter] = None) -> int:
    client = get_client()
    result = client.count(
        collection_name=_COLLECTION,
        count_filter=payload_filter,
    )
    return result.count


def delete_collection():
    client = get_client()
    try:
        client.delete_collection(_COLLECTION)
    except Exception:
        pass
