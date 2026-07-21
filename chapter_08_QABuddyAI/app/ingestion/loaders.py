"""Source loaders: each returns list[Doc] with citation-ready payloads."""
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from .. import config as C
from ..core import chunking as ck
from .base import Doc, new_doc, iter_files, read_text, rel, file_date

# ---- source 01/02: code repos ---------------------------------------------

CODE_LANGS = {".java": "java", ".ts": "ts", ".tsx": "ts", ".mts": "ts",
              ".js": "js", ".mjs": "js", ".cjs": "js"}
REPO_DOC_EXTS = {".md", ".txt", ".properties", ".xml", ".yml", ".yaml",
                 ".json", ".feature", ".gradle", ".cfg", ".conf", ".html"}
REPO_SKIP_HTML = True  # playwright HTML reports are noise


def load_code(root, source_type, repo):
    cfg = C.cfg("chunking.code", {})
    docs = []
    for p in iter_files(root, exts=set(CODE_LANGS) | REPO_DOC_EXTS):
        r = rel(root, p)
        text = read_text(p)
        if not text:
            continue
        lang = CODE_LANGS.get(p.suffix.lower())
        date = file_date(p)
        if lang:
            units = ck.split_code(text, "java" if lang == "java" else "ts",
                                  max_chars=cfg.get("max_chars", 2000),
                                  min_chars=cfg.get("min_chars", 250),
                                  fallback_size=cfg.get("fallback_size", 1600),
                                  fallback_overlap=cfg.get("fallback_overlap", 200))
            for u in units:
                crumb = f"[{repo}] {r}" + (f" > {u['name']}" if u.get("name") else "")
                docs.append(new_doc(source_type, r, f"{crumb}\n{u['text']}",
                                    repo=repo, language=lang, unit=u.get("name"),
                                    line_start=u["line_start"], line_end=u["line_end"],
                                    title=r, date=date))
        else:
            if p.suffix.lower() == ".html" and REPO_SKIP_HTML:
                continue
            for i, piece in enumerate(ck.chunk_doc(text, cfg.get("fallback_size", 1600),
                                                   cfg.get("fallback_overlap", 200))):
                docs.append(new_doc(source_type, r, f"[{repo}] {r}\n{piece['text']}",
                                    repo=repo, heading=piece.get("heading") or None,
                                    chunk_index=i, title=r, date=date))
    return docs


# ---- source 03: test case spreadsheets ------------------------------------

ID_COL = re.compile(r"(?i)^(issue.?key|test.?case.?id|tc.?id|id|key)$")
MODULE_COL = re.compile(r"(?i)^(component|module|feature|suite)$")


def load_testcases(root, source_type):
    size = C.cfg("chunking.testcases.size", 1400)
    docs = []
    for p in iter_files(root, exts={".csv", ".xlsx", ".xls"}, max_bytes=50_000_000):
        r = rel(root, p)
        try:
            df = pd.read_excel(p) if p.suffix.lower() in (".xlsx", ".xls") else pd.read_csv(p)
        except Exception:
            continue
        df = df.astype(object).where(pd.notna(df), None)
        cols = [str(c).strip() for c in df.columns]
        df.columns = cols
        id_col = next((c for c in cols if ID_COL.match(c)), None)
        mod_col = next((c for c in cols if MODULE_COL.match(c)), None)
        date = file_date(p)
        for i, row in enumerate(df.to_dict(orient="records")):
            text = "\n".join(f"{c}: {row[c]}" for c in cols if row.get(c) is not None and str(row[c]).strip())
            if not text:
                continue
            tc_id = str(row.get(id_col)).strip() if id_col and row.get(id_col) is not None else f"{p.stem}#row{i+1}"
            pieces = ck.chunk_text(text, size, 0) or [text]
            for j, piece in enumerate(pieces):
                docs.append(new_doc(source_type, r, f"[test case {tc_id}]\n{piece}",
                                    tc_id=tc_id, module=(row.get(mod_col) if mod_col else None),
                                    priority=row.get("Priority"), status=row.get("Status"),
                                    title=row.get("Summary") or tc_id, row=i + 1,
                                    chunk_index=j if len(pieces) > 1 else None, date=date))
    return docs


# ---- source 04: JIRA JSON dumps -------------------------------------------


def _ticket_text(t):
    head = [f"JIRA {t.get('key')} [{t.get('type', 'Issue')}] {t.get('summary', '')}".strip()]
    meta = []
    for label, k in (("Status", "status"), ("Priority", "priority")):
        if t.get(k):
            meta.append(f"{label}: {t[k]}")
    if t.get("components"):
        meta.append("Components: " + ", ".join(map(str, t["components"])))
    if t.get("labels"):
        meta.append("Labels: " + ", ".join(map(str, t["labels"])))
    if t.get("created") or t.get("updated"):
        meta.append(f"Created: {t.get('created', '?')}  Updated: {t.get('updated', '?')}")
    body = (t.get("description") or "").strip()
    comments = t.get("comments") or []
    lines = ["  ".join(meta)] if meta else []
    return head[0] + "\n" + "\n".join(lines) + ("\n\n" + body if body else ""), comments


def load_jira(root, source_type):
    size = C.cfg("chunking.jira.size", 4800)
    docs = []
    for p in iter_files(root, exts={".json"}):
        r = rel(root, p)
        try:
            data = json.loads(read_text(p))
        except Exception:
            continue
        tickets = data.get("tickets") if isinstance(data, dict) else data
        if not isinstance(tickets, list):
            continue
        date = file_date(p)
        for t in tickets:
            if not isinstance(t, dict) or not t.get("key"):
                continue
            key = str(t["key"])
            main, comments = _ticket_text(t)
            ctext = "\n".join(
                f"- {c.get('author', '?')} ({c.get('created', '?')}): {c.get('body', '')}"
                if isinstance(c, dict) else f"- {c}" for c in comments)
            full = main + ("\n\nComments:\n" + ctext if ctext else "")
            common = dict(ticket_key=key, ticket_status=t.get("status"),
                          priority=t.get("priority"), url=t.get("url"),
                          title=t.get("summary"), date=t.get("updated") or date)
            if len(full) <= size:
                docs.append(new_doc(source_type, r, full, **common))
            else:
                for j, piece in enumerate(ck.chunk_text(main, size, 0)):
                    docs.append(new_doc(source_type, r, piece, chunk_index=j, **common))
                for j, piece in enumerate(ck.chunk_text("Comments on JIRA " + key + ":\n" + ctext, size, 0)):
                    docs.append(new_doc(source_type, r, piece, chunk_index=100 + j, **common))
    return docs


# ---- sources 05/08/09: docs (PDF / MD / TXT) ------------------------------


def load_docs(root, source_type):
    size = C.cfg("chunking.docs.size", 2048)
    overlap = C.cfg("chunking.docs.overlap", 300)
    docs = []
    for p in iter_files(root, exts={".pdf", ".md", ".txt"}, skip_readme=True):
        r = rel(root, p)
        date = file_date(p)
        if p.suffix.lower() == ".pdf":
            try:
                import fitz
                with fitz.open(p) as pdf:
                    for pno, page in enumerate(pdf, start=1):
                        ptext = (page.get_text() or "").strip()
                        for i, piece in enumerate(ck.chunk_text(ptext, size, overlap)):
                            docs.append(new_doc(source_type, r, f"[{p.name} p.{pno}]\n{piece}",
                                                page=pno, chunk_index=i, title=p.name, date=date))
            except Exception:
                continue
        else:
            for i, piece in enumerate(ck.chunk_doc(read_text(p), size, overlap)):
                docs.append(new_doc(source_type, r, f"[{p.name}]\n{piece['text']}",
                                    heading=piece.get("heading") or None,
                                    chunk_index=i, title=p.name, date=date))
    return docs


# ---- source 07: transcripts ------------------------------------------------


def load_transcripts(root, source_type):
    size = C.cfg("chunking.transcripts.size", 3600)
    overlap = C.cfg("chunking.transcripts.overlap", 480)
    docs = []
    for p in iter_files(root, exts={".txt", ".md", ".vtt"}, skip_readme=True):
        r = rel(root, p)
        text = read_text(p)
        if p.suffix.lower() == ".vtt":
            text = re.sub(r"^WEBVTT.*?\n\n", "", text, flags=re.S)
            text = re.sub(r"^\d+\n(?=\d{2}:)", "", text, flags=re.M)
        for i, piece in enumerate(ck.split_transcript(text, size, overlap)):
            docs.append(new_doc(source_type, r, f"[meeting: {p.stem}]\n{piece}",
                                chunk_index=i, title=p.stem, date=file_date(p)))
    return docs


# ---- source 10: Jenkins logs + JUnit XML ----------------------------------

BUILD_RE = re.compile(r"(?:build[_\-. ]?#?|#)(\d{1,7})", re.I)


def _too_old(p, retention_days):
    if not retention_days:
        return False
    try:
        return datetime.fromtimestamp(p.stat().st_mtime) < datetime.now() - timedelta(days=retention_days)
    except OSError:
        return False


def load_jenkins(root, source_type):
    lcfg = C.cfg("chunking.logs", {})
    retention = lcfg.get("retention_days", 90)
    docs = []
    for p in iter_files(root, exts={".log", ".txt", ".out", ".xml"}, skip_readme=True):
        if _too_old(p, retention):
            continue
        r = rel(root, p)
        date = file_date(p)
        m = BUILD_RE.search(p.name)
        build_id = m.group(1) if m else None
        if p.suffix.lower() == ".xml":
            tag = f"jenkins build #{build_id}" if build_id else f"jenkins log {p.stem}"
            try:
                tree = ET.parse(p)
            except ET.ParseError:
                continue
            for tc in tree.iter("testcase"):
                fail = tc.find("failure")
                err = tc.find("error")
                node = fail if fail is not None else err
                if node is None:
                    continue
                name = f"{tc.get('classname', '')}.{tc.get('name', '')}".strip(".")
                text = (f"[{tag}] JUnit failure: {name}\n"
                        f"{node.get('message', '')}\n{(node.text or '').strip()}")
                docs.append(new_doc(source_type, r, text[:lcfg.get('max_block_chars', 2400)],
                                    test_name=name, build_id=build_id,
                                    exception=node.get("type"), title=p.name, date=date))
        else:
            text = read_text(p)
            if not build_id:
                m2 = BUILD_RE.search("\n".join(text.splitlines()[:30]))
                build_id = m2.group(1) if m2 else None
            tag = f"jenkins build #{build_id}" if build_id else f"jenkins log {p.stem}"
            parsed = ck.split_log_failures(text,
                                           max_block_chars=lcfg.get("max_block_chars", 2400),
                                           context_lines=lcfg.get("context_lines", 12))
            for f in parsed["failures"]:
                crumb = f"[{tag}] failure" + (f": {f['test_name']}" if f.get("test_name") else "")
                docs.append(new_doc(source_type, r, f"{crumb}\n{f['text']}",
                                    test_name=f.get("test_name"), exception=f.get("exception"),
                                    build_id=build_id, line_start=f["line_start"],
                                    line_end=f["line_end"], title=p.name, date=date))
            if parsed["summary"]:
                docs.append(new_doc(source_type, r, f"[{tag}] build summary\n{parsed['summary']}",
                                    build_id=build_id, title=p.name, date=date, unit="summary"))
    return docs
