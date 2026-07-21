"""QABuddy.ai Flask server: chat (SSE), ingest (SSE), search, stats, health.

Run locally:  .venv/bin/python -m app.server.app   (http://127.0.0.1:5080)
Droplet:      gunicorn -w 1 --threads 8 -b 0.0.0.0:5080 app.server.app:app
"""
import json
import queue
import threading

from flask import Flask, Response, jsonify, render_template, request, stream_with_context

from .. import config as C
from .. import retrieval
from ..ingestion.pipeline import SOURCES, SOURCE_TYPES, ingest_source, ingest_all

app = Flask(__name__)

# one Store per process: embedded Qdrant allows a single client instance
store = retrieval.store


def sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


# ---- pages -----------------------------------------------------------------


@app.route("/")
def index():
    sources = [{"num": num, "label": s["label"], "source_type": s["source_type"],
                "active": bool(s["loader"])} for num, s in SOURCES.items()]
    return render_template("index.html", sources=sources,
                           llm_model=C.LLM_MODEL, embed_model=C.EMBED_MODEL)


# ---- api -------------------------------------------------------------------


@app.route("/api/health")
def health():
    return jsonify({"ok": True, "llm_key": bool(C.LLM_API_KEY), "llm": C.LLM_MODEL,
                    "embed": C.EMBED_MODEL, "rerank": C.RERANK_MODEL,
                    "qdrant": "server" if C.QDRANT_URL else "embedded",
                    "collection": store().info()})


@app.route("/api/stats")
def stats():
    st = store().stats(SOURCE_TYPES)
    st["labels"] = {s["source_type"]: s["label"] for s in SOURCES.values()}
    return jsonify(st)


@app.route("/api/chat", methods=["POST"])
def chat():
    body = request.get_json(force=True)
    question = (body.get("question") or "").strip()
    if not question:
        return jsonify({"error": "question is required"}), 400
    if store().count() == 0:
        return jsonify({"error": "Knowledge base is empty. Run an ingest first (left panel)."}), 400
    sources = [s for s in (body.get("sources") or []) if s in SOURCE_TYPES] or None
    mode = body.get("mode") or None
    history = body.get("history") or []

    @stream_with_context
    def gen():
        for ev in retrieval.ask_events(question, sources=sources, mode=mode, history=history):
            yield sse(ev)

    return Response(gen(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/api/search", methods=["POST"])
def search():
    """Debug endpoint: retrieval only, no LLM."""
    body = request.get_json(force=True)
    question = (body.get("question") or "").strip()
    if not question:
        return jsonify({"error": "question is required"}), 400
    sources = [s for s in (body.get("sources") or []) if s in SOURCE_TYPES] or None
    r = retrieval.retrieve(question, source_types=sources,
                           rewrites=[] if body.get("no_rewrites") else None)
    return jsonify({
        "question": question,
        "rewrites": r["rewrites"],
        "timings": r["timings"],
        "results": [retrieval.build_citation(i + 1, c) for i, c in enumerate(r["candidates"])],
    })


@app.route("/api/ingest")
def ingest():
    source = request.args.get("source")
    limit = request.args.get("limit", type=int)
    force = request.args.get("force") == "1"
    if source and source not in SOURCES:
        return jsonify({"error": f"unknown source {source}"}), 400

    q: "queue.Queue[dict|None]" = queue.Queue()

    def progress(**ev):
        q.put(ev)

    def run():
        try:
            if source:
                ingest_source(source, limit=limit, force=force, progress=progress, store=store())
            else:
                ingest_all(limit=limit, force=force, progress=progress, store=store())
        except Exception as e:
            q.put({"stage": "error", "message": str(e)})
        finally:
            q.put(None)

    threading.Thread(target=run, daemon=True).start()

    @stream_with_context
    def gen():
        while True:
            ev = q.get()
            if ev is None:
                break
            yield sse(ev)

    return Response(gen(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


if __name__ == "__main__":
    print(f"QABuddy.ai on http://127.0.0.1:{C.PORT}")
    print(f"  embed={C.EMBED_MODEL}  rerank={C.RERANK_MODEL}  llm={C.LLM_MODEL}  "
          f"key={'set' if C.LLM_API_KEY else 'MISSING'}  "
          f"qdrant={'server ' + C.QDRANT_URL if C.QDRANT_URL else 'embedded ' + C.QDRANT_PATH}")
    app.run(host="127.0.0.1", port=C.PORT, threaded=True, debug=False)
