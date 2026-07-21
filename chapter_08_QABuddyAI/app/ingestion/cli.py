"""CLI: python -m app.ingestion.cli ingest --all | --source 03 [--limit N] [--force]"""
import argparse
import sys
import time

from .. import config as C
from ..core.store import Store
from .pipeline import SOURCES, SOURCE_TYPES, ingest_source, ingest_all


def _print_progress(stage, source=None, **info):
    if stage == "load" and info.get("status") == "start":
        print(f"[{source}] loading {info.get('label', '')} ...")
    elif stage == "load":
        print(f"[{source}] loaded {info.get('docs', 0)} chunks from {info.get('files', 0)} files")
    elif stage == "diff":
        print(f"[{source}] changed={info['changed']} unchanged={info['unchanged']} removed={info['removed']}")
    elif stage == "embed":
        print(f"[{source}] embedded {info['done']}/{info['total']}", end="\r")
    elif stage == "done":
        print(f"\n[{source}] done: {info.get('chunks', 0)} chunks ({info.get('embedded', 0)} embedded)")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="qabuddy")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_ing = sub.add_parser("ingest", help="ingest one source or all")
    p_ing.add_argument("--source", choices=list(SOURCES), help="source number, e.g. 03")
    p_ing.add_argument("--all", action="store_true")
    p_ing.add_argument("--limit", type=int, default=None, help="cap chunks (demo runs; manifest untouched)")
    p_ing.add_argument("--force", action="store_true", help="re-embed even if unchanged")

    sub.add_parser("stats", help="chunk counts per source")
    p_reset = sub.add_parser("reset", help="drop and recreate the collection")
    p_reset.add_argument("--yes", action="store_true")

    args = ap.parse_args(argv)

    if args.cmd == "ingest":
        t0 = time.time()
        if args.all or not args.source:
            results = ingest_all(limit=args.limit, force=args.force, progress=_print_progress)
        else:
            results = [ingest_source(args.source, limit=args.limit, force=args.force,
                                     progress=_print_progress)]
        print(f"\nTotal {round(time.time() - t0, 1)}s")
        for r in results:
            if "skipped" not in r:
                print(f"  {r['source']} {r['label']}: files={r['files']} chunks={r['chunks']} embedded={r['embedded']}")
    elif args.cmd == "stats":
        s = Store()
        st = s.stats(SOURCE_TYPES)
        print(f"collection={st['collection']} total={st['total']}")
        for num, spec in SOURCES.items():
            if spec["loader"]:
                print(f"  {num} {spec['label']}: {st['by_source'].get(spec['source_type'], 0)}")
    elif args.cmd == "reset":
        if not args.yes:
            confirm = input(f"Drop collection '{C.COLLECTION}'? [y/N] ")
            if confirm.lower() != "y":
                print("aborted")
                return 1
        Store().reset()
        print("collection reset")
    return 0


if __name__ == "__main__":
    sys.exit(main())
