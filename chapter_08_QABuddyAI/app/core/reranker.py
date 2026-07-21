"""bge-reranker-v2-m3 as a cross-encoder, via transformers directly.

We avoid FlagEmbedding's FlagReranker: in 1.4.0 its compute_score calls
tokenizer.prepare_for_model, which the loaded XLM-R tokenizer doesn't expose.
Running the sequence-classification head ourselves is version-robust.
(See learnings/2026-07-12-flagembedding-reranker-bypass.md.)
"""
from .. import config as C

_reranker = None


def get_reranker():
    global _reranker
    if _reranker is None:
        import torch
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        tok = AutoTokenizer.from_pretrained(C.RERANK_MODEL, use_fast=True)
        model = AutoModelForSequenceClassification.from_pretrained(C.RERANK_MODEL)
        model.eval()
        _reranker = (tok, model, torch)
    return _reranker


def rerank(query, candidates, top_k=6):
    """Score (query, chunk) pairs with the cross-encoder; sigmoid to 0..1."""
    if not candidates:
        return []
    tok, model, torch = get_reranker()
    pairs = [[query, c["payload"].get("text", "")] for c in candidates]
    with torch.no_grad():
        inputs = tok(pairs, padding=True, truncation=True, max_length=512, return_tensors="pt")
        logits = model(**inputs).logits.view(-1).float()
        scores = torch.sigmoid(logits).tolist()
    for c, s in zip(candidates, scores):
        c["rerank"] = float(s)
    ranked = sorted(candidates, key=lambda c: -c["rerank"])
    return ranked[:top_k]
