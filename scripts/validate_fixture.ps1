$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Python = if (Test-Path ".venv\Scripts\python.exe") { ".venv\Scripts\python.exe" } else { "python" }
& $Python -m ruff check src tests scripts
& $Python -m pytest -q
if (Test-Path "outputs\fixture-mobile") { Remove-Item -Recurse -Force "outputs\fixture-mobile" }
& $Python -m api_evidence_mapper all --config fixtures/project.fixture.toml
& $Python scripts/validate_distribution.py --config fixtures/project.fixture.toml
npm run validate:collection -- --config fixtures/project.fixture.toml
Write-Host "Fixture validation passed. No network requests were made."
