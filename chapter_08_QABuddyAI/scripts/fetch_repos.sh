#!/usr/bin/env bash
# Clone or update the two framework repos into data/01 and data/02.
set -euo pipefail
cd "$(dirname "$0")/.."

fetch() {
  local dir="$1" url="$2"
  if [ -d "$dir/.git" ]; then
    echo "pull $dir"
    git -C "$dir" pull --ff-only
  else
    echo "clone $url"
    git clone --depth 1 "$url" "$dir"
  fi
}

fetch data/01_selenium_framework https://github.com/PramodDutta/ATB13xSeleniumAdvanceFramework.git
fetch data/02_playwright_framework https://github.com/PramodDutta/Advance-Playwright-Framework.git
echo "done. next: .venv/bin/python -m app.ingestion.cli ingest --source 01 (and 02)"
