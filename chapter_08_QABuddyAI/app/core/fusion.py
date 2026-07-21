"""Reciprocal Rank Fusion of dense + sparse result lists."""


def rrf_fuse(dense_hits, sparse_hits, k=60, limit=None):
    scores, meta = {}, {}
    for rank, h in enumerate(dense_hits):
        scores[h["id"]] = scores.get(h["id"], 0.0) + 1.0 / (k + rank + 1)
        meta[h["id"]] = h
    for rank, h in enumerate(sparse_hits):
        scores[h["id"]] = scores.get(h["id"], 0.0) + 1.0 / (k + rank + 1)
        meta.setdefault(h["id"], h)
    fused = sorted(scores.items(), key=lambda kv: -kv[1])
    out = [{"id": pid, "rrf": round(s, 5), "payload": meta[pid]["payload"]} for pid, s in fused]
    return out[:limit] if limit else out
