"""Pipeline orchestrators — IngestPipeline and ChatPipeline.

Each is a generator that yields SSE-friendly event dicts for real-time streaming."""

import json
import logging
import time
from typing import Any, Generator, Optional
from pathlib import Path

import pandas as pd
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue

import config
from pipeline import chunker, embedder, indexer, rewriter, retriever, reranker, generator as gen_mod
from models.loader import warm_models

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
#  Ingest Pipeline
# ──────────────────────────────────────────────

class IngestPipeline:
    """Ingest CSV/XLSX → rows → docs → chunks → embed → Qdrant.

    Usage::

        for event in IngestPipeline().run("data/file.csv", text_cols, meta_cols):
            yield event  # SSE stream
    """

    def run(self, filepath: str,
            text_cols: list[str],
            meta_cols: list[str]) -> Generator[dict[str, Any], None, None]:
        # ── 0. Warm models ──
        yield {"type": "stage", "stage": "warm", "message": "Warming AI models..."}
        warm_models()
        yield {"type": "progress", "stage": "warm", "status": "done"}

        # ── 1. Read ──
        yield {"type": "stage", "stage": "read", "message": "Reading file..."}
        df = self._read_file(filepath)
        total_rows = len(df)
        yield {
            "type": "progress",
            "stage": "read",
            "status": "done",
            "rows": total_rows,
            "columns": list(df.columns),
            "dtypes": {c: str(dt) for c, dt in df.dtypes.items()},
            "sample": json.loads(df.head(5).to_json(orient="records", force_ascii=False)),
        }

        # ── 2. Build docs ──
        yield {"type": "stage", "stage": "build", "message": "Assembling documents..."}
        docs, meta_rows = self._build_docs(df, text_cols, meta_cols)
        yield {"type": "progress", "stage": "build", "status": "done", "doc_count": len(docs)}

        # ── 3. Chunk ──
        yield {"type": "stage", "stage": "chunk", "message": "Chunking documents..."}
        all_chunks = chunker.chunk_all(docs)
        chunk_lengths = [len(c["text"]) for c in all_chunks]
        yield {
            "type": "progress",
            "stage": "chunk",
            "status": "done",
            "total_chunks": len(all_chunks),
            "avg_chars": round(sum(chunk_lengths) / len(chunk_lengths), 1) if chunk_lengths else 0,
            "min_chars": min(chunk_lengths) if chunk_lengths else 0,
            "max_chars": max(chunk_lengths) if chunk_lengths else 0,
            "histogram": self._histogram(chunk_lengths, 10),
            "samples": [
                {
                    "index": c["index"],
                    "doc_index": c.get("doc_index"),
                    "start_char": c["start_char"],
                    "end_char": c["end_char"],
                    "text": c["text"][:200] + ("..." if len(c["text"]) > 200 else ""),
                }
                for c in all_chunks[:5]
            ],
        }

        # ── 4. Embed ──
        yield {"type": "stage", "stage": "embed", "message": "Embedding chunks (bge-m3)..."}
        chunk_texts = [c["text"] for c in all_chunks]
        batch_size = config.INGEST_BATCH
        dense_vectors = []
        sparse_vectors = []

        for i in range(0, len(chunk_texts), batch_size):
            batch = chunk_texts[i:i + batch_size]
            dense_batch = embedder.encode_dense(batch)
            sparse_batch = embedder.encode_sparse(batch)
            dense_vectors.extend(dense_batch)
            sparse_vectors.extend(sparse_batch)

            yield {
                "type": "progress",
                "stage": "embed",
                "current": min(i + batch_size, len(chunk_texts)),
                "total": len(chunk_texts),
                "status": "embedding",
            }

        # Show previews from first chunk
        dv = dense_vectors[0]
        sv = sparse_vectors[0]
        top_sparse = sorted(sv.items(), key=lambda x: x[1], reverse=True)[:5]
        yield {
            "type": "progress",
            "stage": "embed",
            "status": "done",
            "dense_dim": len(dv),
            "dense_preview": dv[:8],
            "sparse_top5": [{"token_id": int(k), "weight": round(v, 4)} for k, v in top_sparse],
        }

        # ── 5. Index ──
        yield {"type": "stage", "stage": "index", "message": "Indexing into Qdrant..."}
        indexer.create_collection(force=True)

        points = []
        for i in range(len(all_chunks)):
            chunk = all_chunks[i]
            meta = meta_rows[chunk["doc_index"]].copy() if chunk.get("doc_index") is not None else {}

            payload = {
                "text": chunk["text"],
                "_chunk_id": f"VWO-{i}",
                "_doc_index": chunk.get("doc_index", 0),
                "_chunk_index": chunk["index"],
                "start_char": chunk["start_char"],
                "end_char": chunk["end_char"],
            }
            payload.update({k: meta.get(k, "") for k in meta})

            point = PointStruct(
                id=i,
                vector={
                    "": dense_vectors[i],
                    "sparse": {
                        "indices": list(sparse_vectors[i].keys()),
                        "values": list(sparse_vectors[i].values()),
                    },
                },
                payload=payload,
            )
            points.append(point)

            if len(points) >= 100:
                indexer.upsert_points(points)
                points = []

        if points:
            indexer.upsert_points(points)

        total_indexed = indexer.count_points()
        yield {
            "type": "progress",
            "stage": "index",
            "status": "done",
            "collection": "vwo_test_cases",
            "points_count": total_indexed,
        }

        yield {"type": "complete", "message": f"Ingested {total_indexed} chunks into Qdrant."}

    # ── Helpers ──

    def _read_file(self, filepath: str) -> pd.DataFrame:
        path = Path(filepath)
        if path.suffix == ".csv":
            return pd.read_csv(path)
        elif path.suffix in (".xls", ".xlsx"):
            return pd.read_excel(path)
        else:
            raise ValueError(f"Unsupported file type: {path.suffix}")

    def _build_docs(self, df: pd.DataFrame,
                    text_cols: list[str],
                    meta_cols: list[str]) -> tuple[list[str], list[dict]]:
        docs = []
        meta_rows = []
        for _, row in df.iterrows():
            text_parts = []
            for col in text_cols:
                val = row.get(col, "")
                if pd.notna(val):
                    text_parts.append(f"{col}: {val}")
            docs.append("\n\n".join(text_parts))

            meta = {}
            for col in meta_cols:
                val = row.get(col, "")
                meta[col] = str(val) if pd.notna(val) else ""
            meta_rows.append(meta)

        return docs, meta_rows

    @staticmethod
    def _histogram(values: list[int], bins: int) -> list[dict]:
        if not values:
            return []
        mn, mx = min(values), max(values)
        if mx == mn:
            return [{"bin_start": mn, "bin_end": mx + 1, "count": len(values)}]
        step = (mx - mn) / bins
        hist = []
        for i in range(bins):
            lo = mn + i * step
            hi = lo + step
            cnt = sum(1 for v in values if lo <= v < hi)
            hist.append({"bin_start": round(lo, 1), "bin_end": round(hi, 1), "count": cnt})
        return hist


# ──────────────────────────────────────────────
#  Chat Pipeline
# ──────────────────────────────────────────────

class ChatPipeline:
    """Full chat pipeline: rewrite → embed → search → rerank → generate.

    Usage::

        for event in ChatPipeline().run("user query", history):
            yield event
    """

    def run(self, user_query: str,
            history: list[dict] = None) -> Generator[dict[str, Any], None, None]:
        history = history or []

        # ── 1. Rewrite ──
        yield {"type": "stage", "stage": "rewrite", "message": "Rewriting query..."}
        rewrites = rewriter.rewrite_query(user_query)
        queries = [user_query] + rewrites  # original + alternates
        yield {
            "type": "progress",
            "stage": "rewrite",
            "status": "done",
            "original": user_query,
            "rewrites": rewrites,
            "total_queries": len(queries),
        }

        # ── 2. Embed queries ──
        yield {"type": "stage", "stage": "embed_query", "message": "Embedding queries..."}
        all_dense = embedder.encode_dense(queries)
        all_sparse = embedder.encode_sparse(queries)
        yield {"type": "progress", "stage": "embed_query", "status": "done"}

        # ── 3. Hybrid search for each query, RRF fuse ──
        yield {"type": "stage", "stage": "search", "message": "Searching knowledge base..."}
        all_dense_results = []
        all_sparse_results = []

        for i, (dvec, svec) in enumerate(zip(all_dense, all_sparse)):
            dr = indexer.search_dense(dvec)
            sr = indexer.search_sparse(svec)
            all_dense_results.extend(dr)
            all_sparse_results.extend(sr)

        # Deduplicate before RRF: merge scores for same point id
        dense_dedup: dict = {}
        for p in all_dense_results:
            if p.id not in dense_dedup or p.score > dense_dedup[p.id].score:
                dense_dedup[p.id] = p
        sparse_dedup: dict = {}
        for p in all_sparse_results:
            if p.id not in sparse_dedup or p.score > sparse_dedup[p.id].score:
                sparse_dedup[p.id] = p

        # RRF fuse
        from pipeline.retriever import rrf_fuse
        fused = rrf_fuse(
            sorted(dense_dedup.values(), key=lambda x: x.score, reverse=True)[:config.TOP_N_HYBRID],
            sorted(sparse_dedup.values(), key=lambda x: x.score, reverse=True)[:config.TOP_N_HYBRID],
        )

        yield {
            "type": "progress",
            "stage": "search",
            "status": "done",
            "dense_count": len(dense_dedup),
            "sparse_count": len(sparse_dedup),
            "fused_count": len(fused),
            "dense_top5": [{"id": p.id, "score": round(p.score, 4)} for p in list(dense_dedup.values())[:5]],
            "sparse_top5": [{"id": p.id, "score": round(p.score, 4)} for p in list(sparse_dedup.values())[:5]],
            "rrf_top5": [{"id": p.id, "score": round(p.score, 4)} for p in fused[:5]],
        }

        # ── 4. Re-rank ──
        yield {"type": "stage", "stage": "rerank", "message": "Re-ranking candidates..."}
        rerank_result = reranker.rerank(user_query, fused[:config.TOP_N_HYBRID])
        reranked = rerank_result["reranked"]
        yield {
            "type": "progress",
            "stage": "rerank",
            "status": "done",
            "before": {str(k): round(v, 4) for k, v in rerank_result["before"].items()},
            "after": {str(k): round(v, 4) for k, v in rerank_result["scores"].items()},
            "top_chunks": [
                {
                    "id": p.id,
                    "score": round(p.score, 4),
                    "text_preview": (p.payload.get("text", "")[:200] + "..."),
                }
                for p in reranked
            ],
        }

        # ── 5. Generate ──
        mode = gen_mod.detect_mode(user_query)
        stage_label = "generate_test_case" if mode == "generate" else "generate_answer"
        yield {
            "type": "stage",
            "stage": stage_label,
            "message": "Generating response with AI..." if mode == "answer" else "Generating test case...",
        }

        answer = gen_mod.generate(user_query, reranked, mode=mode, history=history)
        yield {
            "type": "progress",
            "stage": stage_label,
            "status": "done",
            "mode": answer["mode"],
        }

        yield {
            "type": "answer",
            "content": answer["content"],
            "citations": answer["citations"],
            "mode": answer["mode"],
        }
