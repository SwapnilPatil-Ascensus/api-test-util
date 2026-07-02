# API Evidence Mapper

Local-first utility that reconstructs a **Postman Collection v2.1**, QC4 environment template, endpoint inventory, and migration mapping from incomplete API evidence — without modifying source repositories or requiring cloud credentials.

Built for **Unite MSC Mobile** API migration; reusable for other API projects via `config/project.toml`.

---

## What it does

| Input (read-only) | Output (local `outputs/<project>/`) |
|---|---|
| Service/application source repos | Canonical endpoint inventory (JSON + CSV) |
| Legacy integration-test repos | Migration matrix (CSV + Excel) |
| Target API automation framework | Postman Collection v2.1 |
| Partial Postman collections/environments | QC4 environment template (placeholders only) |
| Sanitized HAR captures | Redacted cURL preview per endpoint |
| Optional OpenAPI/Swagger | Manual-testing guides and validation reports |

## What it does not do

- Create automated test cases
- Commit secrets, tokens, or PII
- Modify any source repository
- Call QC4 unless you explicitly run the guarded Newman wrapper with `--allow-network`

---

## Repository layout

```
api-test-util/
├── config/           # Example config + local secrets template (project.toml is git-ignored)
├── docs/             # Architecture, operating model, execution playbook
├── fixtures/         # Synthetic evidence for offline validation
├── scripts/          # Bootstrap, validation, and run-all entry points
├── src/              # Python package (api_evidence_mapper)
├── templates/        # Override CSV and mapping templates
├── tests/            # Unit tests
├── tools/            # Node Postman Collection SDK validator
├── archive/          # Historical transport notes
├── CURSOR-MASTER-PROMPT.md   # Full Cursor agent instruction set
└── START-HERE-CURSOR.md      # Quick Cursor onboarding
```

Generated artifacts land in `outputs/<project_id>/` (git-ignored).

---

## Quick start

### 1. Prerequisites

- Python 3.11+
- Node.js 18+ (for collection structural validation)
- Git

### 2. Bootstrap

```powershell
cd C:\Workspace\GitLab\api-test-util
.\scripts\bootstrap.ps1
```

### 3. Configure local paths

```powershell
Copy-Item config\project.example.toml config\project.toml
# Edit config\project.toml — set repository paths, Postman files, QC4 base URL
```

See `config/project.example.toml` for all fields. Local path registry: `config/local.paths.toml` (git-ignored).

### 4. Validate with fixtures (no real evidence needed)

```powershell
.\scripts\validate_fixture.ps1
```

### 5. Generate against real evidence

```powershell
.\scripts\run_all.ps1
```

Review `outputs/<project>/reports/VALIDATION-REPORT.md` before any live QC4 run.

---

## Primary commands

| Command | Purpose |
|---|---|
| `python -m api_evidence_mapper all --config config/project.toml` | Offline scan + generate |
| `.\scripts\validate_fixture.ps1` | Prove package with synthetic data |
| `.\scripts\run_all.ps1` | Full gate: lint, test, generate, validate |
| `python scripts/run_newman_safe.py --allow-network ...` | Guarded live QC4 execution |

---

## Documentation

| Document | Contents |
|---|---|
| [docs/EXECUTION-PLAYBOOK.md](docs/EXECUTION-PLAYBOOK.md) | Step-by-step runbook |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Modules, data flow, diagrams |
| [docs/OPERATING-MODEL.md](docs/OPERATING-MODEL.md) | Phases A–E (offline → live) |
| [docs/UNITE-MSC-STARTER-CONFIG.md](docs/UNITE-MSC-STARTER-CONFIG.md) | Unite MSC-specific settings |
| [docs/PARSER-EXTENSION-GUIDE.md](docs/PARSER-EXTENSION-GUIDE.md) | Adding custom route parsers |
| [VALIDATION-EVIDENCE.md](VALIDATION-EVIDENCE.md) | Recorded validation results |

---

## Evidence precedence

Resolved **field by field**, not file by file:

1. OpenAPI / service route definitions → intended contract
2. Legacy integration tests → known request construction
3. Sanitized HAR → observed QC4 client traffic
4. Partial Postman → working examples and variables
5. Documented CSV overrides → operator decisions

Statuses: `READY`, `PARTIAL`, `CODE_ONLY`, `POSTMAN_ONLY`, `HAR_ONLY`, `CONFLICT`, `BLOCKED`.

---

## Cursor usage

1. Open **`C:\Workspace\GitLab\api-test-util`** in Cursor (not a source repository).
2. Follow [START-HERE-CURSOR.md](START-HERE-CURSOR.md).
3. For full agent execution, paste [CURSOR-MASTER-PROMPT.md](CURSOR-MASTER-PROMPT.md).

---

## License

See [LICENSE](LICENSE).
