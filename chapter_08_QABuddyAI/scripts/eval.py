#!/usr/bin/env python3
"""Retrieval hit-rate eval on eval/golden_questions.yaml (no LLM calls).

    .venv/bin/python scripts/eval.py [--rewrites]

A question is a HIT when any top-k chunk matches the expected source_type
(and the expected substring, when given, appears in some top chunk).
"""
import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import retrieval  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rewrites", action="store_true",
                    help="use LLM query rewriting (costs LLM calls)")
    args = ap.parse_args()

    golden = yaml.safe_load((Path(__file__).resolve().parent.parent / "eval" /
                             "golden_questions.yaml").read_text())["questions"]
    hits = 0
    print(f"{'HIT':4} {'best':6} question")
    for g in golden:
        r = retrieval.retrieve(g["q"], rewrites=None if args.rewrites else [])
        cands = r["candidates"]
        types = [c["payload"].get("source_type") for c in cands]
        blob = " ".join((c["payload"].get("text") or "") + " " +
                        retrieval.prompts.chunk_label(c["payload"]) for c in cands)
        exp = g.get("expect", {})
        ok_type = any(t in exp.get("source_type", types) for t in types)
        ok_sub = (exp.get("contains") or "") in blob
        ok = ok_type and ok_sub
        hits += ok
        best = max((c.get("rerank", 0) for c in cands), default=0)
        print(f"{'YES' if ok else 'no ':4} {best:0.3f}  {g['q'][:70]}"
              + ("" if ok else f"   [got: {', '.join(sorted(set(t for t in types if t)))or 'nothing'}]"))
    rate = hits / max(len(golden), 1)
    print(f"\nhit rate: {hits}/{len(golden)} = {rate:.0%}")
    return 0 if rate >= 0.7 else 1


if __name__ == "__main__":
    sys.exit(main())
