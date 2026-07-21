"""Advanced RAG Explorer — Configuration & Tunables."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ──
BASE_DIR   = Path(__file__).resolve().parent
DATA_DIR   = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
QDRANT_DIR = DATA_DIR / "qdrant_data"

# ── API (Openrouter) ──
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE    = "https://openrouter.ai/api/v1"
GENERATE_MODEL     = "deepseek/deepseek-chat"
REWRITE_MODEL      = "openai/gpt-4o-mini"

# ── Embedding ──
EMBED_MODEL_NAME   = "BAAI/bge-m3"
EMBED_DIM          = 1024
BGE_USE_FP16       = True
INGEST_BATCH       = 16

# ── Reranker ──
RERANKER_MODEL_NAME = "BAAI/bge-reranker-v2-m3"

# ── Chunking ──
CHUNK_SIZE         = 1000
CHUNK_OVERLAP      = 150

# ── Retrieval ──
TOP_N_HYBRID       = 20
TOP_K_RERANK       = 4
RRF_K              = 60

# ── Flags ──
REWRITE_ENABLED    = True
PORT               = int(os.getenv("PORT", 5050))
DEBUG              = os.getenv("DEBUG", "0") == "1"

# ── CSV generator ──
NUM_TEST_CASES     = 5000
