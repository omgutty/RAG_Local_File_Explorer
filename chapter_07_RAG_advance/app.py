"""Advanced RAG Explorer — Flask application entry point.

Routes:
    /              → redirect to /upload
    /upload        → file picker + column selector
    /ingest        → SSE streaming pipeline for ingestion
    /chunks        → paginated chunk viewer
    /chat          → interactive Q&A with pipeline stage tracking
    /chat/ask      → SSE endpoint for chat queries
"""

import json
import logging
import os
import uuid
from pathlib import Path
from functools import wraps

from flask import (Flask, render_template, request, redirect, url_for,
                   flash, Response, stream_with_context, jsonify, session)
import pandas as pd

import config
from pipeline.orchestrator import IngestPipeline, ChatPipeline
from pipeline import indexer

# ── Logging ──
logging.basicConfig(
    level=logging.DEBUG if config.DEBUG else logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── App ──
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "rag-explorer-secret-2026")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB

# Ensure directories exist
config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
config.QDRANT_DIR.mkdir(parents=True, exist_ok=True)

# ── Helpers ──

def _get_available_modules():
    """Return distinct module values from Qdrant (cached per request)."""
    try:
        if not indexer.collection_exists():
            return []
        # Scroll a limited set to extract distinct modules
        results, _ = indexer.scroll_points(limit=200, with_vectors=False)
        modules = set()
        for p in results:
            val = p.payload.get("module", "")
            if val:
                modules.add(val)
        return sorted(modules)
    except Exception:
        return []


def _sse_stream(events):
    """Yield SSE-formatted lines from an event generator.

    Each event dict uses 'type' as the SSE event name (stage, progress,
    complete, answer, etc.) — this maps directly to JS addEventListener.
    """
    for event in events:
        event_type = event.get("type", "message") if isinstance(event, dict) else "message"
        yield f"event: {event_type}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"


# ── Routes ──

@app.route("/")
def index():
    return redirect(url_for("upload"))


@app.route("/upload", methods=["GET", "POST"])
def upload():
    preview = None

    if request.method == "POST":
        file = request.files.get("file")
        if not file or file.filename == "":
            flash("No file selected.", "error")
            return render_template("upload.html", active_stage="upload", preview=None)

        # Save file
        ext = Path(file.filename).suffix.lower()
        if ext not in (".csv", ".xls", ".xlsx"):
            flash("Unsupported file type. Please upload .csv, .xls, or .xlsx.", "error")
            return render_template("upload.html", active_stage="upload", preview=None)

        save_name = f"{uuid.uuid4().hex}{ext}"
        save_path = config.UPLOAD_DIR / save_name
        file.save(str(save_path))

        # Read preview
        try:
            if ext == ".csv":
                df = pd.read_csv(save_path)
            else:
                df = pd.read_excel(save_path)

            columns = list(df.columns)
            suggested_text = [c for c in columns if c.lower() in
                              ("title", "description", "steps", "preconditions", "expected", "tags", "test")]
            suggested_meta = [c for c in columns if c.lower() in
                              ("id", "jira_id", "priority", "module", "created_date", "jira")]

            if not suggested_text:
                suggested_text = columns[:3]
            if not suggested_meta:
                suggested_meta = [c for c in columns if c not in suggested_text]

            preview = {
                "filename": save_name,
                "rows": len(df),
                "columns": columns,
                "dtypes": {c: str(dt) for c, dt in df.dtypes.items()},
                "sample": json.loads(df.head(5).to_json(orient="records", force_ascii=False)),
                "suggested_text": suggested_text,
                "suggested_meta": suggested_meta,
            }

        except Exception as e:
            flash(f"Error reading file: {e}", "error")
            return render_template("upload.html", active_stage="upload", preview=None)

    return render_template("upload.html", active_stage="upload", preview=preview)


@app.route("/ingest", methods=["POST"])
def start_ingest():
    """POST to start ingestion; redirects to SSE monitoring page."""
    filename = request.form.get("filename")
    text_cols = request.form.getlist("text_cols")
    meta_cols = request.form.getlist("meta_cols")

    if not filename or not text_cols:
        flash("Missing filename or text columns.", "error")
        return redirect(url_for("upload"))

    filepath = str(config.UPLOAD_DIR / filename)
    if not Path(filepath).exists():
        flash("Uploaded file not found. Please re-upload.", "error")
        return redirect(url_for("upload"))

    # Store ingest params in session
    session["ingest_filepath"] = filepath
    session["ingest_text_cols"] = text_cols
    session["ingest_meta_cols"] = meta_cols

    return render_template("ingest.html",
                           active_stage="ingest",
                           ingest_url=url_for("ingest_stream"))


@app.route("/ingest/stream")
def ingest_stream():
    """SSE endpoint: runs the ingest pipeline and streams events."""
    filepath = session.get("ingest_filepath")
    text_cols = session.get("ingest_text_cols", [])
    meta_cols = session.get("ingest_meta_cols", [])

    if not filepath or not Path(filepath).exists():
        def error_gen():
            yield {"type": "error", "message": "No file to ingest."}
        return Response(_sse_stream(error_gen()), mimetype="text/event-stream")

    pipeline = IngestPipeline()

    def generate():
        for event in pipeline.run(filepath, text_cols, meta_cols):
            yield event
        # Clean up session
        session.pop("ingest_filepath", None)
        session.pop("ingest_text_cols", None)
        session.pop("ingest_meta_cols", None)

    return Response(
        stream_with_context(_sse_stream(generate())),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.route("/chunks")
def chunks():
    """Paginated chunk viewer with filters."""
    page = request.args.get("page", 1, type=int)
    per_page = 50
    search = request.args.get("search", "")
    priority = request.args.get("priority", "")
    module = request.args.get("module", "")

    # Build Qdrant filter
    filter_conditions = []
    if priority:
        filter_conditions.append(
            {"key": "priority", "match": {"value": priority}}
        )
    if module:
        filter_conditions.append(
            {"key": "module", "match": {"value": module}}
        )

    try:
        if not indexer.collection_exists():
            return render_template("chunks.html", active_stage="chunks",
                                   chunks=[], total=0, page=1, total_pages=1,
                                   search=search, filters={"priority": priority, "module": module},
                                   modules=[], referenced=[])

        total = indexer.count_points()
        total_pages = max(1, (total + per_page - 1) // per_page)

        offset = (page - 1) * per_page
        results, _ = indexer.scroll_points(
            limit=per_page,
            offset=offset,
            with_vectors=True,
        )

        # Post-filter by substring search
        if search:
            results = [p for p in results if search.lower() in p.payload.get("text", "").lower()]

        # Get available modules for filter dropdown
        modules = _get_available_modules()

        # Referenced chunks from last chat (stored in session)
        referenced = session.get("last_citations", [])

        # Truncate vectors for display
        for p in results:
            vec = p.vector
            if vec and isinstance(vec, dict) and "" in vec:
                p.vector = vec[""][:8]  # First 8 dims only

        return render_template("chunks.html", active_stage="chunks",
                               chunks=results, total=total, page=page,
                               total_pages=total_pages, search=search,
                               filters={"priority": priority, "module": module},
                               modules=modules, referenced=referenced)

    except Exception as e:
        logger.error("Chunks error: %s", e)
        flash(f"Error loading chunks: {e}", "error")
        return render_template("chunks.html", active_stage="chunks",
                               chunks=[], total=0, page=1, total_pages=1,
                               search=search, filters={"priority": priority, "module": module},
                               modules=[], referenced=[])


@app.route("/chat")
def chat():
    """Chat interface."""
    return render_template("chat.html", active_stage="chat")


@app.route("/chat/ask", methods=["POST"])
def chat_ask():
    """SSE endpoint for chat queries — streams pipeline stages + final answer."""
    data = request.get_json()
    query = data.get("query", "").strip()
    history = data.get("history", [])

    if not query:
        return jsonify({"error": "Query is required"}), 400

    pipeline = ChatPipeline()

    def generate():
        for event in pipeline.run(query, history):
            if event.get("type") == "answer":
                session["last_citations"] = event.get("citations", [])
            yield event

    return Response(
        stream_with_context(_sse_stream(generate())),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── Entry ──

if __name__ == "__main__":
    logger.info("Starting Advanced RAG Explorer on port %d", config.PORT)
    app.run(host="0.0.0.0", port=config.PORT, debug=config.DEBUG, threaded=True)
