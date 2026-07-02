# Start Here in Cursor

Open **`C:\Workspace\GitLab\api-test-util`** in Cursor — the repository root. Do not open a source repository (UniteMSC, api-test-automation) as the workspace for this work.

## Quick path

1. Run `scripts/bootstrap.ps1`
2. Copy `config/project.example.toml` → `config/project.toml` and set local paths
3. Run `scripts/validate_fixture.ps1` (proves the package offline)
4. Run `scripts/run_all.ps1` (generates real artifacts when paths are configured)
5. Review `outputs/<project>/reports/` before any live QC4 call

Full step-by-step instructions: **[docs/EXECUTION-PLAYBOOK.md](docs/EXECUTION-PLAYBOOK.md)**

## Cursor agent mode

For end-to-end agent execution, paste the contents of **[CURSOR-MASTER-PROMPT.md](CURSOR-MASTER-PROMPT.md)** into Cursor Agent.

## Rules

- Source repositories are **read-only** evidence
- Do not put credentials in chat
- Put runtime values in `config/local.secrets.env` only (git-ignored)
- Live QC4 requires explicit `--allow-network` on the Newman wrapper

## Done when

- [ ] Fixture validation passes
- [ ] Offline generation succeeds
- [ ] Collection SDK validation passes
- [ ] Mapping CSV/XLSX and reports exist
- [ ] Source repositories unchanged
- [ ] No network execution unless explicitly authorized
