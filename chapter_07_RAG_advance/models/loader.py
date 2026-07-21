"""Singleton model loaders — bge-m3 (dense+sparse) and bge-reranker-v2-m3.

Models are loaded lazily on first call, not at import time.
This keeps the Flask app responsive at startup (~2.3 GB + ~570 MB memory)."""

import logging

import config

logger = logging.getLogger(__name__)

_MODELS = {}  # type: dict[str, object]


def get_embedder():
    """Return the lazy-loaded BAAI/bge-m3 model instance."""
    if "bge_m3" not in _MODELS:
        logger.info("Loading bge-m3 embedder (%.1f GB in FP16)...", 2.3)
        from FlagEmbedding import BGEM3FlagModel
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info("Using device: %s", device)
        _MODELS["bge_m3"] = BGEM3FlagModel(
            config.EMBED_MODEL_NAME,
            use_fp16=config.BGE_USE_FP16,
            device=device,
        )
        logger.info("bge-m3 loaded successfully.")
    return _MODELS["bge_m3"]


def get_reranker():
    """Return the lazy-loaded BAAI/bge-reranker-v2-m3 model instance."""
    if "reranker" not in _MODELS:
        logger.info("Loading bge-reranker-v2-m3 (%.0f MB)...", 570)
        from FlagEmbedding import FlagReranker
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info("Using device: %s", device)
        _MODELS["reranker"] = FlagReranker(
            config.RERANKER_MODEL_NAME,
            use_fp16=config.BGE_USE_FP16,
            device=device,
        )
        logger.info("Reranker loaded successfully.")
    return _MODELS["reranker"]


def warm_models():
    """Pre-warm both models (called on first /ingest or /chat)."""
    get_embedder()
    get_reranker()
