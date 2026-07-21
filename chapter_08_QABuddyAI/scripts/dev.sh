#!/usr/bin/env bash
# Run the QABuddy server locally.
set -euo pipefail
cd "$(dirname "$0")/.."
exec .venv/bin/python -m app.server.app
