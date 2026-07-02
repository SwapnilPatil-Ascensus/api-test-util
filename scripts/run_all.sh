#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON="python3"
if [[ -x .venv/bin/python ]]; then PYTHON=".venv/bin/python"; fi
"$PYTHON" -m ruff check src tests scripts
"$PYTHON" -m pytest -q
"$PYTHON" -m api_evidence_mapper all --config config/project.toml
"$PYTHON" scripts/validate_distribution.py --config config/project.toml
npm run validate:collection -- --config config/project.toml
