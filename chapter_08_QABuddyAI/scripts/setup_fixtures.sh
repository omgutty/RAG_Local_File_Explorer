#!/usr/bin/env bash
# Copy demo data from chapter_07 into the data folders (gitignored copies).
set -euo pipefail
cd "$(dirname "$0")/.."

cp -f ../chapter_07_RAG/Advance_RAG/testcase/vwo_5000_test_cases.csv data/03_test_cases/ 2>/dev/null \
  && echo "copied vwo_5000_test_cases.csv -> data/03_test_cases/" || echo "ch07 CSV not found (skip)"
cp -f "../chapter_07_RAG/Basic_RAG/data/Product Requirements Document_(PRD)_VWO.com.pdf" data/09_prd_srs_brd_frd/ 2>/dev/null \
  && echo "copied VWO PRD -> data/09_prd_srs_brd_frd/" || echo "ch07 PRD not found (skip)"
