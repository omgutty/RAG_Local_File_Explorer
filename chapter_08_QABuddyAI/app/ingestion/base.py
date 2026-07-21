"""Shared ingestion primitives: Doc, stable uids, safe file walking."""
import hashlib
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

EXCLUDE_DIRS = {".git", "node_modules", "target", "build", "dist", ".venv", "venv",
                "__pycache__", "test-results", "playwright-report", "allure-results",
                "allure-report", "reports", "site", ".idea", ".vscode", "out",
                ".github", "coverage"}
SKIP_FILES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", ".DS_Store"}
MAX_FILE_BYTES = 1_500_000


@dataclass
class Doc:
    uid: str
    text: str
    payload: dict


def make_uid(source_type: str, path: str, text: str) -> str:
    h = hashlib.sha256(f"{source_type}|{path}|{text}".encode("utf-8", "replace"))
    return h.hexdigest()[:40]


def new_doc(source_type: str, path: str, text: str, **extra) -> Doc:
    payload = {"source_type": source_type, "path": path}
    payload.update({k: v for k, v in extra.items() if v is not None})
    return Doc(uid=make_uid(source_type, path, text), text=text, payload=payload)


def normalize(text: str) -> str:
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = "".join(ch for ch in text if ch == "\n" or ch == "\t" or ord(ch) >= 32)
    return text.strip()


def file_date(p: Path) -> str:
    try:
        return datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d")
    except OSError:
        return None


def iter_files(root: Path, exts=None, skip_readme=False, max_bytes=MAX_FILE_BYTES):
    """Yield files under root, pruning vendored/generated dirs and oversized files."""
    root = Path(root)
    if not root.exists():
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDE_DIRS and not d.startswith("."))
        for fn in sorted(filenames):
            if fn in SKIP_FILES or fn.startswith("."):
                continue
            if skip_readme and fn.lower() == "readme.md":
                continue
            p = Path(dirpath) / fn
            if exts and p.suffix.lower() not in exts:
                continue
            try:
                if p.stat().st_size > max_bytes:
                    continue
            except OSError:
                continue
            yield p


def read_text(p: Path) -> str:
    try:
        return normalize(p.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return ""


def rel(root: Path, p: Path) -> str:
    return str(Path(p).relative_to(root))
