#!/usr/bin/env bash
# Start PatternLoop UI from repo root. First Gradio load can take 1-3 minutes.
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
pip install -U pip setuptools wheel -q
pip install -e ".[dev]" -q
echo "Loading UI (first start may take 1-3 minutes — do not press Ctrl+C)..."
exec python -m patternloop ui --port 7860
