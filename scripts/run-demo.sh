#!/usr/bin/env bash
# CLI demo against bundled sample notes (no browser UI).
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
pip install -U pip setuptools wheel -q
pip install -e ".[dev]" -q
patternloop init 2>/dev/null || true
patternloop agents install research_digest --yes
patternloop run research_digest "Summarize themes; cite filenames." --workdir examples/demo_notes
