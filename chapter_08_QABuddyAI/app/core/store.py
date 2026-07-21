"""Qdrant store: named dense + sparse vectors, stable IDs, per-source filters.

Embedded mode (QDRANT_PATH) for local dev, server mode (QDRANT_URL) on the
droplet; both come from env, no code change.
"""
import uuid

from .. import config as C

INDEXED_FIELDS = ("source_type", "repo", "path", "language",
                  "ticket_key", "ticket_status", "tc_id", "module")


def point_id(uid: str) -> str:
    """Stable UUID from a chunk uid (sha of source|path|content) -> idempotent upserts."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, uid))


class Store:
    def __init__(self):
        from qdrant_client import QdrantClient
        if C.QDRANT_URL:
            self.client = QdrantClient(url=C.QDRANT_URL)
        else:
            self.client = QdrantClient(path=C.QDRANT_PATH)

    # ---- lifecycle --------------------------------------------------------
    def ensure_collection(self):
        from qdrant_client import models
        if not self.client.collection_exists(C.COLLECTION):
            self.client.create_collection(
                C.COLLECTION,
                vectors_config={"dense": models.VectorParams(size=C.DENSE_DIM, distance=models.Distance.COSINE)},
                sparse_vectors_config={"sparse": models.SparseVectorParams()},
            )
            for field in INDEXED_FIELDS:
                try:
                    self.client.create_payload_index(C.COLLECTION, field_name=field,
                                                     field_schema=models.PayloadSchemaType.KEYWORD)
                except Exception:
                    pass

    def reset(self):
        try:
            self.client.delete_collection(C.COLLECTION)
        except Exception:
            pass
        self.ensure_collection()

    # ---- write ------------------------------------------------------------
    def upsert_docs(self, docs, dense, sparse):
        from qdrant_client import models
        points = []
        for j, doc in enumerate(docs):
            payload = dict(doc.payload)
            payload["text"] = doc.text
            points.append(models.PointStruct(
                id=point_id(doc.uid),
                vector={
                    "dense": dense[j],
                    "sparse": models.SparseVector(indices=sparse[j]["indices"], values=sparse[j]["values"]),
                },
                payload=payload,
            ))
        self.client.upsert(C.COLLECTION, points=points)

    def delete_where(self, source_type=None, path=None):
        from qdrant_client import models
        must = []
        if source_type:
            must.append(models.FieldCondition(key="source_type", match=models.MatchValue(value=source_type)))
        if path:
            must.append(models.FieldCondition(key="path", match=models.MatchValue(value=path)))
        if not must:
            return
        self.client.delete(C.COLLECTION,
                           points_selector=models.FilterSelector(filter=models.Filter(must=must)))

    # ---- read -------------------------------------------------------------
    def _filter(self, source_types=None):
        from qdrant_client import models
        if not source_types:
            return None
        return models.Filter(must=[models.FieldCondition(
            key="source_type", match=models.MatchAny(any=list(source_types)))])

    def dense_search(self, dense_vec, limit, source_types=None):
        res = self.client.query_points(C.COLLECTION, query=dense_vec, using="dense",
                                       limit=limit, with_payload=True,
                                       query_filter=self._filter(source_types)).points
        return [{"id": str(p.id), "score": float(p.score), "payload": p.payload} for p in res]

    def sparse_search(self, sparse_vec, limit, source_types=None):
        from qdrant_client import models
        q = models.SparseVector(indices=sparse_vec["indices"], values=sparse_vec["values"])
        res = self.client.query_points(C.COLLECTION, query=q, using="sparse",
                                       limit=limit, with_payload=True,
                                       query_filter=self._filter(source_types)).points
        return [{"id": str(p.id), "score": float(p.score), "payload": p.payload} for p in res]

    # ---- stats ------------------------------------------------------------
    def count(self, source_type=None):
        from qdrant_client import models
        try:
            flt = None
            if source_type:
                flt = models.Filter(must=[models.FieldCondition(
                    key="source_type", match=models.MatchValue(value=source_type))])
            return self.client.count(C.COLLECTION, count_filter=flt, exact=True).count
        except Exception:
            return 0

    def stats(self, source_types):
        return {
            "collection": C.COLLECTION,
            "total": self.count(),
            "by_source": {st: self.count(st) for st in source_types},
        }

    def info(self):
        try:
            c = self.client.get_collection(C.COLLECTION)
            return {"points": c.points_count, "status": str(c.status), "collection": C.COLLECTION}
        except Exception as e:
            return {"points": 0, "status": "missing", "collection": C.COLLECTION, "error": str(e)}
