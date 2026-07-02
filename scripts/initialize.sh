#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
[[ -f config/project.toml ]] || cp config/project.example.toml config/project.toml
printf 'Initialization complete. Replace the path and QC4 placeholders before scanning real evidence. Create local.secrets.env only for an authorized live run.\n'
