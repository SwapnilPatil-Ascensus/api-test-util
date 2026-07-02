$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Python = if (Test-Path ".venv\Scripts\python.exe") { ".venv\Scripts\python.exe" } else { "python" }
& $Python -m ruff check src tests scripts
& $Python -m pytest -q
& $Python -m api_evidence_mapper all --config config/project.toml
& $Python scripts/validate_distribution.py --config config/project.toml
npm run validate:collection -- --config config/project.toml
