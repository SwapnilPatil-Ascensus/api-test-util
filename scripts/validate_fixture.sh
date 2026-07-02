#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON="python3"
if [[ -x .venv/bin/python ]]; then PYTHON=".venv/bin/python"; fi
"$PYTHON" -m ruff check src tests scripts
"$PYTHON" -m pytest -q
rm -rf outputs/fixture-mobile
"$PYTHON" -m api_evidence_mapper all --config fixtures/project.fixture.toml
"$PYTHON" scripts/validate_distribution.py --config fixtures/project.fixture.toml
npm run validate:collection -- --config fixtures/project.fixture.toml
printf 'Fixture validation passed. No network requests were made.\n'
