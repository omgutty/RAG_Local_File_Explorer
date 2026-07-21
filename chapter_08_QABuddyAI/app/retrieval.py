"""Ask pipeline: condense -> rewrite -> hybrid search -> RRF -> rerank -> cited answer."""
import re
import time

from . import config as C
from . import llm, prompts
from .core.embedder import embed
from .core.fusion import rrf_fuse
from .core.reranker import rerank
from .core.store import Store

_store = None


def store():
    global _store
    if _store is None:
        _store = Store()
    return _store


# ---- modes -----------------------------------------------------------------

MODE_PATTERNS = [
    ("generate", re.compile(r"\b(create|generate|write|draft|design|add)\b.{0,60}\b(test ?cases?|tests?|scenarios?|test ?plan)\b", re.I)),
    ("rca", re.compile(r"\b(root ?cause|rca|why\s+(is|did|does|was).{0,60}(fail|flaky|break)|analy[sz]e.{0,40}(failure|log|build))\b", re.I)),
    ("review", re.compile(r"\b(review|missing|gaps?|coverage|critique|what.{0,20}not covered)\b", re.I)),
]


def detect_mode(q):
    for mode, rx in MODE_PATTERNS:
        if rx.search(q or ""):
            return mode
    return "answer"


# ---- query shaping ---------------------------------------------------------


def condense_question(question, history):
    """Rewrite a follow-up into a standalone question using recent turns."""
    if not history:
        return question
    turns = history[-2 * C.cfg("retrieval.history_turns", 3):]
    convo = "\n".join(f"{h.get('role')}: {str(h.get('content'))[:400]}" for h in turns)
    try:
        out = llm.chat([
            {"role": "system", "content":
             "Rewrite the user's last message as ONE standalone search question, resolving "
             "pronouns from the conversation. Return only the question."},
            {"role": "user", "content": f"Conversation:\n{convo}\n\nLast message: {question}"},
        ], temperature=0.0, max_tokens=120)
        return out.strip() or question
    except Exception:
        return question


def rewrite_query(query, n=3):
    try:
        out = llm.chat([
            {"role": "system", "content":
             "You rewrite a search query into alternate phrasings for retrieval. "
             f"Return exactly {n} rewrites, one per line, no numbering, no extra text."},
            {"role": "user", "content": query},
        ], temperature=0.4, max_tokens=200)
        lines = [re.sub(r"^\s*[-*\d.]+\s*", "", l).strip() for l in out.splitlines() if l.strip()]
        return lines[:n] if lines else []
    except Exception:
        return []


# ---- retrieval -------------------------------------------------------------


def retrieve(question, source_types=None, rewrites=None):
    top_n = C.cfg("retrieval.top_n_hybrid", 20)
    rrf_k = C.cfg("retrieval.rrf_k", 60)
    n_cand = C.cfg("retrieval.rerank_candidates", 12)
    top_k = C.cfg("retrieval.top_k", 6)

    t0 = time.time()
    if rewrites is None:
        rewrites = rewrite_query(question, C.cfg("retrieval.rewrite_n", 3)) \
            if C.cfg("retrieval.rewrite_enabled", True) else []
    queries = [question] + [r for r in rewrites if r and r != question]
    t_rewrite = time.time() - t0

    dense_all, sparse_all = {}, {}
    for qv in queries:
        d, s = embed([qv], batch_size=1)
        for h in store().dense_search(d[0], top_n, source_types):
            dense_all.setdefault(h["id"], h)
        for h in store().sparse_search(s[0], top_n, source_types):
            sparse_all.setdefault(h["id"], h)
    dense_hits = list(dense_all.values())[:top_n]
    sparse_hits = list(sparse_all.values())[:top_n]
    t_search = time.time() - t0 - t_rewrite

    fused = rrf_fuse(dense_hits, sparse_hits, rrf_k, limit=n_cand)
    reranked = rerank(question, [dict(f) for f in fused], top_k)
    return {
        "candidates": reranked, "fused": fused,
        "dense": dense_hits, "sparse": sparse_hits, "rewrites": rewrites,
        "timings": {"rewrite": round(t_rewrite, 2), "search": round(t_search, 2),
                    "rerank": round(time.time() - t0 - t_rewrite - t_search, 2)},
    }


# ---- citations -------------------------------------------------------------

SOURCE_LABELS = {
    "selenium_framework": "Selenium repo", "playwright_framework": "Playwright repo",
    "test_cases": "Test case", "jira_tickets": "JIRA", "company_docs": "Doc",
    "meeting_notes": "Meeting", "lucid_charts": "Lucid", "prd_docs": "PRD",
    "jenkins_logs": "Jenkins", "figma_designs": "Figma",
}


def build_citation(n, cand):
    p = cand["payload"]
    return {
        "n": n,
        "source_type": p.get("source_type"),
        "label": SOURCE_LABELS.get(p.get("source_type"), p.get("source_type")),
        "ref": prompts.chunk_label(p),
        "path": p.get("path"),
        "url": p.get("url"),
        "rerank": round(cand.get("rerank", 0.0), 3),
        "rrf": cand.get("rrf"),
        "snippet": (p.get("text") or "")[:500],
    }


# ---- ask (streaming event generator) --------------------------------------

NO_ANSWER = ("This is not in the QABuddy knowledge base yet (best match scored below the "
             "confidence threshold). Try rephrasing with exact ids (ticket key, test case id, "
             "file name), widening the source filter, or ingest the missing document.")


def ask_events(question, sources=None, mode=None, history=None):
    """Yields: meta -> citations -> token* -> done | error."""
    t0 = time.time()
    try:
        q = condense_question(question, history)
        mode = mode if mode in prompts.MODE_SYS else detect_mode(q)
        yield {"type": "meta", "mode": mode, "question": q}

        r = retrieve(q, source_types=sources or None)
        cands = r["candidates"]
        citations = [build_citation(i + 1, c) for i, c in enumerate(cands)]
        yield {"type": "citations", "items": citations, "rewrites": r["rewrites"],
               "timings": r["timings"]}

        best = max((c.get("rerank", 0.0) for c in cands), default=0.0)
        threshold = C.cfg("retrieval.relevance_threshold", 0.22)
        if not cands or best < threshold:
            yield {"type": "token", "text": NO_ANSWER}
            yield {"type": "done", "answer": NO_ANSWER, "no_answer": True,
                   "elapsed": round(time.time() - t0, 2)}
            return

        messages = prompts.build_messages(mode, q, cands, history)
        answer = ""
        try:
            for delta in llm.chat_stream(messages):
                answer += delta
                yield {"type": "token", "text": delta}
        except Exception:
            answer = llm.chat(messages)  # streaming unsupported -> one shot
            yield {"type": "token", "text": answer}
        yield {"type": "done", "answer": answer, "elapsed": round(time.time() - t0, 2)}
    except Exception as e:
        yield {"type": "error", "message": str(e)}


def ask(question, sources=None, mode=None, history=None):
    """Non-streaming wrapper: returns {answer, citations, mode, ...}."""
    out = {"question": question, "citations": [], "answer": "", "mode": None}
    for ev in ask_events(question, sources=sources, mode=mode, history=history):
        if ev["type"] == "meta":
            out["mode"] = ev["mode"]
        elif ev["type"] == "citations":
            out["citations"] = ev["items"]
            out["rewrites"] = ev.get("rewrites")
            out["timings"] = ev.get("timings")
        elif ev["type"] == "done":
            out["answer"] = ev["answer"]
            out["elapsed"] = ev["elapsed"]
            out["no_answer"] = ev.get("no_answer", False)
        elif ev["type"] == "error":
            out["error"] = ev["message"]
    return out
