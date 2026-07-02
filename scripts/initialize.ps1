$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
if (-not (Test-Path "config\project.toml")) {
  Copy-Item "config\project.example.toml" "config\project.toml"
  Write-Host "Created config\project.toml from the example."
}
Write-Host "Initialization complete. Replace the path and QC4 placeholders before scanning real evidence. Create local.secrets.env only for an authorized live run."
