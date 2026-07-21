"""Ingestion pipeline: load -> diff vs manifest -> embed -> idempotent upsert.

data/ folders are the source of truth; Qdrant is a disposable derived index.
Per-file signatures make re-ingest cheap: unchanged files are skipped, changed
files are delete+reinserted, removed files are deleted. Phase 2's hourly cron
just calls ingest_all() on a schedule.
"""
import hashlib
import json
from collections import defaultdict

from .. import config as C
from ..core.embedder import embed
from ..core.store import Store
from . import loaders

SOURCES = {
    "01": dict(folder="01_selenium_framework", source_type="selenium_framework",
               label="Selenium framework", loader="code", repo="ATB13xSeleniumAdvanceFramework",
               git="https://github.com/PramodDutta/ATB13xSeleniumAdvanceFramework.git"),
    "02": dict(folder="02_playwright_framework", source_type="playwright_framework",
               label="Playwright framework", loader="code", repo="Advance-Playwright-Framework",
               git="https://github.com/PramodDutta/Advance-Playwright-Framework.git"),
    "03": dict(folder="03_test_cases", source_type="test_cases",
               label="Test cases", loader="testcases"),
    "04": dict(folder="04_jira_tickets", source_type="jira_tickets",
               label="JIRA tickets", loader="jira"),
    "05": dict(folder="05_company_docs", source_type="company_docs",
               label="Company docs", loader="docs"),
    "06": dict(folder="06_figma_designs", source_type="figma_designs",
               label="Figma designs (Phase 2)", loader=None),
    "07": dict(folder="07_meeting_notes", source_type="meeting_notes",
               label="Meeting notes", loader="transcripts"),
    "08": dict(folder="08_lucid_charts", source_type="lucid_charts",
               label="Lucid charts", loader="docs"),
    "09": dict(folder="09_prd_srs_brd_frd", source_type="prd_docs",
               label="PRD / SRS / BRD / FRD", loader="docs"),
    "10": dict(folder="10_jenkins_logs", source_type="jenkins_logs",
               label="Jenkins logs", loader="jenkins"),
}

SOURCE_TYPES = [s["source_type"] for s in SOURCES.values() if s["loader"]]


def load_source(num):
    spec = SOURCES[num]
    if not spec["loader"]:
        return []
    root = C.DATA_DIR / spec["folder"]
    fn = getattr(loaders, f"load_{spec['loader']}")
    if spec["loader"] == "code":
        return fn(root, spec["source_type"], spec["repo"])
    return fn(root, spec["source_type"])


def _load_manifest():
    try:
        return json.loads(C.MANIFEST_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _save_manifest(m):
    C.MANIFEST_PATH.write_text(json.dumps(m, indent=1, sort_keys=True))


def _sig(docs):
    h = hashlib.sha256("".join(sorted(d.uid for d in docs)).encode())
    return h.hexdigest()[:16]


def ingest_source(num, limit=None, force=False, progress=None, store=None, batch_size=16):
    """Returns stats dict. progress(stage=str, **info) is called along the way."""
    def report(stage, **info):
        if progress:
            progress(stage=stage, source=num, **info)

    spec = SOURCES[num]
    if not spec["loader"]:
        report("skipped", reason="phase 2 source")
        return {"source": num, "skipped": "phase 2"}

    store = store or Store()
    store.ensure_collection()

    report("load", status="start", label=spec["label"])
    docs = load_source(num)
    if limit:
        docs = docs[:limit]
    by_path = defaultdict(list)
    for d in docs:
        by_path[d.payload["path"]].append(d)
    report("load", status="done", docs=len(docs), files=len(by_path))

    manifest = _load_manifest()
    src_man = manifest.get(num, {})
    changed = {p: ds for p, ds in by_path.items()
               if force or src_man.get(p) != _sig(ds)}
    removed = [p for p in src_man if p not in by_path]
    unchanged = len(by_path) - len(changed)
    report("diff", changed=len(changed), unchanged=unchanged, removed=len(removed))

    for p in removed:
        store.delete_where(source_type=spec["source_type"], path=p)
    for p in changed:
        store.delete_where(source_type=spec["source_type"], path=p)

    todo = [d for p in sorted(changed) for d in changed[p]]
    done = 0
    for b in range(0, len(todo), batch_size):
        batch = todo[b:b + batch_size]
        dense, sparse = embed([d.text for d in batch], batch_size=batch_size)
        store.upsert_docs(batch, dense, sparse)
        done += len(batch)
        report("embed", done=done, total=len(todo))

    if not limit:  # a limited demo run must not poison the manifest
        for p in removed:
            src_man.pop(p, None)
        for p, ds in changed.items():
            src_man[p] = _sig(ds)
        manifest[num] = src_man
        _save_manifest(manifest)

    stats = {"label": spec["label"], "files": len(by_path),
             "chunks": len(docs), "embedded": len(todo), "unchanged_files": unchanged,
             "removed_files": len(removed)}
    report("done", **stats)
    stats["source"] = num
    return stats


def ingest_all(limit=None, force=False, progress=None, store=None):
    store = store or Store()
    out = []
    for num in SOURCES:
        if SOURCES[num]["loader"]:
            out.append(ingest_source(num, limit=limit, force=force, progress=progress, store=store))
    return out
