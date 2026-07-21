"""BGE-M3 hybrid embeddings: one encode() pass returns dense + lexical sparse.

The model loads lazily on first use so the Flask server boots instantly and
only pays the download/warm cost when you ingest or chat.
"""
from .. import config as C

_embedder = None


def get_embedder():
    global _embedder
    if _embedder is None:
        from FlagEmbedding import BGEM3FlagModel
        _embedder = BGEM3FlagModel(C.EMBED_MODEL, use_fp16=C.USE_FP16)
    return _embedder


def embed(texts, batch_size=16):
    """Return (dense_list, sparse_list). dense: list[list[float]];
    sparse: list[{'indices': [int], 'values': [float]}] from bge-m3 lexical weights."""
    model = get_embedder()
    out = model.encode(texts, batch_size=batch_size, max_length=1024,
                       return_dense=True, return_sparse=True, return_colbert_vecs=False)
    dense = [list(map(float, v)) for v in out["dense_vecs"]]
    sparse = []
    for lw in out["lexical_weights"]:
        idx, val = [], []
        for k, v in lw.items():
            idx.append(int(k))
            val.append(float(v))
        sparse.append({"indices": idx, "values": val})
    return dense, sparse


def sparse_top_tokens(sparse, n=5):
    """Human-readable top-n sparse tokens (token text + weight) for the UI."""
    pairs = sorted(zip(sparse["indices"], sparse["values"]), key=lambda p: -p[1])[:n]
    try:
        tok = get_embedder().tokenizer
        return [{"token": tok.decode([i]).strip(), "weight": round(w, 3)} for i, w in pairs]
    except Exception:
        return [{"token": str(i), "weight": round(w, 3)} for i, w in pairs]
