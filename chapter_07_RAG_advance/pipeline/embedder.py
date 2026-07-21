"""Wraps bge-m3: encode_dense() and encode_sparse() with batched inference."""

import logging
import numpy as np

import config
from models.loader import get_embedder

logger = logging.getLogger(__name__)


def encode_dense(texts: list[str], batch_size: int = None) -> list[list[float]]:
    """Encode texts into dense 1024-dim vectors.

    Returns list of lists (nested Python floats) for JSON serialization.
    """
    batch_size = batch_size or config.INGEST_BATCH
    model = get_embedder()
    output = model.encode(
        texts,
        return_dense=True,
        return_sparse=False,
        batch_size=batch_size,
    )
    dense = output["dense_vecs"]
    if isinstance(dense, np.ndarray):
        return dense.tolist()
    return [v.tolist() if hasattr(v, "tolist") else list(v) for v in dense]


def encode_sparse(texts: list[str], batch_size: int = None) -> list[dict[int, float]]:
    """Encode texts into sparse lexical weight dicts.

    Returns list of {token_id: weight} dicts.
    """
    batch_size = batch_size or config.INGEST_BATCH
    model = get_embedder()
    output = model.encode(
        texts,
        return_dense=False,
        return_sparse=True,
        batch_size=batch_size,
    )
    lexical = output["lexical_weights"]
    result = []
    for lw in lexical:
        if hasattr(lw, "export"):
            result.append(dict(lw.export()))
        elif isinstance(lw, dict):
            result.append(lw)
        else:
            result.append(dict(lw))
    return result
