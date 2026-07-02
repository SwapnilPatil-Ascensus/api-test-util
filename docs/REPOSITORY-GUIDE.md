# Repository Guide — API Evidence Mapper

This document is the canonical map of **what lives where**, **how to run it**, and **what was consolidated** in this repository.

---

## Which utility is main?

| Location | Status |
|---|---|
| **`C:\Workspace\GitLab\api-test-util`** (repo root) | **Canonical — use this** |
| `api-evidence-mapper-email-safe/` | **Removed / obsolete** — was an email-transport wrapper that duplicated the repo payload. Do not open it in Cursor. |

There is **one** Python package (`src/api_evidence_mapper/`), **one** `pyproject.toml`, and **one** `package.json` — all at repo root.

If you still see `api-evidence-mapper-email-safe/` on disk, close any editor or terminal using it and delete the folder manually. It is not part of the maintained utility.

---

## Top-level layout

```
api-test-util/
├── config/                 Local project configuration
├── docs/                   All documentation (including Cursor onboarding)
├── fixtures/               Synthetic offline evidence + fixture config
├── scripts/                Bootstrap, validation, Newman wrapper
├── src/api_evidence_mapper/  Core Python package
├── templates/              Operator CSV overrides and mapping template
├── tests/                  pytest suite
├── tools/                  Node Postman Collection SDK validator
├── README.md               Project overview and quick start
├── pyproject.toml          Python package metadata and dev deps
├── package.json            Node deps (Postman SDK, Newman)
└── LICENSE, SECURITY.md    Legal and security policy
```

**Git-ignored at runtime (created locally, never committed):**

| Path | Purpose |
|---|---|
| `config/project.toml` | Your real repository paths and inputs |
| `config/local.paths.toml` | Workstation path registry |
| `config/local.secrets.env` | QC4 credentials for guarded Newman runs |
| `outputs/` | Generated Postman collections, reports, mappings |
| `inputs/` | Optional drop zone for user-supplied evidence |
| `runtime/` | Scratch space |
| `.venv/` | Python virtual environment |
| `node_modules/` | Node dependencies |

**Tracked sanitized fixtures (safe to commit):**

| Path | Purpose |
|---|---|
| `fixtures/qc4-sanitized.har` | Synthetic HAR for offline tests |
| `fixtures/partial-qc4.postman_environment.json` | Synthetic Postman env for offline tests |

All other `*.har` and `*.postman_environment.json` files remain git-ignored.

---

## Python package (`src/api_evidence_mapper/`)

| Module | Responsibility |
|---|---|
| `cli.py` / `__main__.py` | CLI entry: `python -m api_evidence_mapper all --config <toml>` |
| `config.py` | Load and resolve TOML configuration paths |
| `discovery.py` | Scan repos, Postman, HAR, OpenAPI for evidence |
| `sanitize.py` | Redact secrets; template HAR values |
| `normalize.py` | Path aliases, parameter normalization |
| `reconcile.py` | Merge evidence into canonical endpoints |
| `generate.py` | Postman v2.1, CSV/XLSX, cURL, reports |
| `pipeline.py` | Orchestrate scan → reconcile → generate |
| `models.py` | Data models |

Console script (after `pip install -e .`): `api-evidence-mapper`

---

## Scripts (`scripts/`)

| Script | Platform | Purpose |
|---|---|---|
| `bootstrap.ps1` / `bootstrap.sh` | Win / Unix | Create `.venv`, `pip install -e ".[dev]"`, `npm ci` |
| `initialize.ps1` / `initialize.sh` | Win / Unix | Copy `config/project.example.toml` → `config/project.toml` |
| `validate_fixture.ps1` / `.sh` | Win / Unix | **Offline proof gate** — ruff, pytest, fixture generate, validate |
| `run_all.ps1` / `.sh` | Win / Unix | Full gate using `config/project.toml` |
| `validate_distribution.py` | Cross | Validate generated artifact set, counts, secret scans |
| `run_newman_safe.py` | Cross | Guarded Newman; requires explicit `--allow-network` |

---

## Configuration (`config/`)

| File | Tracked | Purpose |
|---|---|---|
| `project.example.toml` | Yes | Template — copy to `project.toml` and edit |
| `local.secrets.env.example` | Yes | Template for live QC4 secrets |
| `project.toml` | No | Your real paths (git-ignored) |
| `local.secrets.env` | No | Live credentials (git-ignored) |

**Fixture config** (for offline validation only): `fixtures/project.fixture.toml`

---

## Documentation (`docs/`)

| Document | When to read |
|---|---|
| **REPOSITORY-GUIDE.md** (this file) | Orientation — what is where |
| **START-HERE-CURSOR.md** | First time in Cursor |
| **EXECUTION-PLAYBOOK.md** | Step-by-step runbook |
| **CURSOR-MASTER-PROMPT.md** | Full agent prompt for end-to-end execution |
| **ARCHITECTURE.md** | Module design and data flow |
| **OPERATING-MODEL.md** | Phases A–E (offline → live QC4) |
| **UNITE-MSC-STARTER-CONFIG.md** | Unite MSC Mobile-specific settings |
| **PARSER-EXTENSION-GUIDE.md** | Adding custom route parsers |
| **EXISTING-REPO-SAFETY.md** | Read-only evidence guarantees |
| **HAR-CAPTURE-INSTRUCTIONS.md** | How to capture sanitized HAR |
| **ROLE-AND-GATE-MATRIX.md** | Validation gates and roles |
| **REQUIREMENTS-TRACEABILITY.md** | Feature → artifact mapping |
| **VALIDATION-EVIDENCE.md** | Recorded validation results |
| **MANIFEST.md** | Feature checklist |
| **RESEARCH-AND-DESIGN-DECISIONS.md** | Design rationale |

---

## Generated outputs (`outputs/<project_id>/`)

After a successful run, expect:

```
outputs/<project_id>/
├── postman/                  Postman Collection v2.1 + QC4 env template
├── inventory/                Endpoint inventory (JSON + CSV)
├── mapping/                  Migration matrix (CSV + Excel)
├── curl/                     Redacted cURL previews
└── reports/                  Validation, sanitization, open questions
```

Review `reports/VALIDATION-REPORT.md` and `reports/OPEN-QUESTIONS.md` before any live QC4 call.

---

## How to get fully functional

### First-time setup

1. **Open repo root in Cursor:** `C:\Workspace\GitLab\api-test-util`
2. **Bootstrap dependencies:**
   ```powershell
   .\scripts\bootstrap.ps1
   ```
3. **Create local config** (if `config/project.toml` does not exist):
   ```powershell
   Copy-Item config\project.example.toml config\project.toml
   ```
   Edit paths in `config/project.toml` for your service source, legacy tests, target framework, and partial Postman files.
4. **Prove the package offline** (no real evidence required):
   ```powershell
   .\scripts\validate_fixture.ps1
   ```
   Expected: ruff pass, 10 pytest pass, fixture generation pass, SDK validation pass.

### Generate real artifacts

5. **Run full offline pipeline:**
   ```powershell
   .\scripts\run_all.ps1
   ```
6. **Review outputs** under `outputs/<project_id>/reports/`.

### Optional live QC4 execution

7. Copy `config/local.secrets.env.example` → `config/local.secrets.env` and fill values locally.
8. Run Newman only after explicit authorization:
   ```powershell
   python scripts/run_newman_safe.py --allow-network --config config/project.toml
   ```

---

## Consolidation changes (2026-07-02)

Removed or relocated to eliminate redundancy:

| Removed / moved | Reason |
|---|---|
| `api-evidence-mapper-email-safe/` | Obsolete email-transport wrapper — duplicate of repo root |
| `PACKAGE-FILES-SHA256.txt` | One-time transport integrity manifest |
| `TRANSPORT-RECONSTRUCTION-REPORT.txt` | One-time reconstruction log |
| `archive/` | Historical transport note — no longer needed |
| Root-level Cursor/design docs | Moved to `docs/` for a cleaner root |

Root now contains only: runtime code, config templates, scripts, tests, and `README.md`.

---

## Primary commands (cheat sheet)

```powershell
# Bootstrap (once)
.\scripts\bootstrap.ps1

# Offline proof (synthetic fixtures)
.\scripts\validate_fixture.ps1

# Real project generation
.\scripts\run_all.ps1

# Direct CLI
python -m api_evidence_mapper all --config config/project.toml

# Lint + test only
python -m ruff check src tests scripts
python -m pytest -q

# Postman SDK validation (after generation)
npm run validate:collection -- --config config/project.toml
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Two copies of the utility visible | Close Cursor workspace pointing at `api-evidence-mapper-email-safe`; open repo root only |
| `validate_fixture.ps1` fails on missing HAR/env | Ensure `fixtures/qc4-sanitized.har` and `fixtures/partial-qc4.postman_environment.json` exist (tracked in git) |
| `run_all.ps1` fails on paths | Edit `config/project.toml` — paths must exist on your machine |
| Tests pass but generation empty | Check `[inputs]` and `[[repositories]]` sections in your TOML |
| Cannot delete `api-evidence-mapper-email-safe` | Close Cursor/terminal holding the folder, then delete manually |

---

## What you need to do

- [ ] Open **`C:\Workspace\GitLab\api-test-util`** (not email-safe wrapper)
- [ ] Delete `api-evidence-mapper-email-safe/` if it still exists locally
- [ ] Run `.\scripts\bootstrap.ps1`
- [ ] Ensure `config/project.toml` has your local repository paths
- [ ] Run `.\scripts\validate_fixture.ps1` — must pass before real work
- [ ] Run `.\scripts\run_all.ps1` when paths are configured
- [ ] Review `outputs/<project>/reports/` before live QC4
