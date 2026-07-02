# Execution Playbook

Simple step-by-step runbook for **API Evidence Mapper**. All steps are offline unless Step 8 is explicitly authorized.

---

## Before you start

- [ ] Clone or open `api-test-util` at `C:\Workspace\GitLab\api-test-util`
- [ ] Do **not** open a source repository (UniteMSC, api-test-automation) as the Cursor workspace root
- [ ] Have local paths ready for service source, legacy tests, target framework, and partial Postman files
- [ ] Do **not** put credentials in chat or in committed files

---

## Step 1 — Bootstrap dependencies

**Windows**

```powershell
cd C:\Workspace\GitLab\api-test-util
.\scripts\bootstrap.ps1
```

**macOS / Linux**

```bash
cd /path/to/api-test-util
./scripts/bootstrap.sh
```

**Expected:** `.venv` created, Python package installed editable, `node_modules` present.

---

## Step 2 — Create local configuration

```powershell
Copy-Item config\project.example.toml config\project.toml
```

Edit `config/project.toml`:

| Section | What to set |
|---|---|
| `[[repositories]]` | Absolute paths to service source, legacy tests, target framework |
| `[inputs]` | Partial Postman collection/environment paths; optional HAR/OpenAPI |
| `[qc4]` | QC4 base URL (non-secret only) |
| `[normalization]` | BFF/gateway `path_aliases` if routes differ between HAR and service code |

Optional: copy paths into `config/local.paths.toml` as a workstation registry (git-ignored).

---

## Step 3 — Prove the package (fixture gate)

```powershell
.\scripts\validate_fixture.ps1
```

**Pass criteria**

- Ruff: no errors
- Pytest: all tests green
- Fixture generation: 2 endpoints, collection validates
- No network calls

If this fails, fix the utility before scanning real repositories.

---

## Step 4 — Generate artifacts (offline)

```powershell
.\scripts\run_all.ps1
```

Or directly:

```powershell
.venv\Scripts\python.exe -m api_evidence_mapper all --config config/project.toml
```

**Outputs** (under `outputs/<project_id>/`):

| Path | Purpose |
|---|---|
| `inventory/endpoint_inventory.csv` | All evidence records |
| `mapping/endpoint_migration_matrix.xlsx` | Migration matrix with status |
| `postman/<project>.postman_collection.json` | Import into Postman |
| `postman/<project>-qc4.postman_environment.json` | QC4 template (no secrets) |
| `curl/` | One redacted cURL per request |
| `reports/MANUAL-TESTING-GUIDE.md` | How to run manually |
| `reports/OPEN-QUESTIONS.md` | Gaps and review items |
| `reports/VALIDATION-REPORT.md` | Gate results |

---

## Step 5 — Review before any live call

1. Open `reports/VALIDATION-REPORT.md` — confirm status counts
2. Open `reports/SANITIZATION-REPORT.md` — confirm secrets were redacted
3. Open `reports/OPEN-QUESTIONS.md` — triage `CODE_ONLY` / `POSTMAN_ONLY` rows
4. Import the collection + environment into Postman locally
5. Focus manual testing on `READY` endpoints first

---

## Step 6 — Optional HAR second pass

If HAR was not configured in Step 2:

1. Capture sanitized QC4 traffic per `docs/HAR-CAPTURE-INSTRUCTIONS.md`
2. Add HAR paths to `config/project.toml`
3. Re-run Step 4
4. Compare new `HAR_ONLY` and reconciled rows in the migration matrix

---

## Step 7 — Prepare secrets (local only)

```powershell
Copy-Item config\local.secrets.env.example config\local.secrets.env
# Fill in runtime values locally — never commit this file
```

---

## Step 8 — Live QC4 execution (explicit authorization only)

```powershell
.venv\Scripts\python.exe scripts\run_newman_safe.py `
  --collection outputs\unite-msc-mobile\postman\unite-msc-mobile.postman_collection.json `
  --environment outputs\unite-msc-mobile\postman\unite-msc-mobile-qc4.postman_environment.json `
  --secrets config\local.secrets.env `
  --allow-network
```

**Requirements**

- `--allow-network` flag is mandatory; without it the wrapper refuses to run
- Secrets are merged into a temporary file and deleted after execution
- Do not add `--json-report` unless you accept request/response data in the report file

---

## Step 9 — Verify source repos unchanged

After every generation run, confirm evidence repositories were not modified:

```powershell
git -C C:\Workspace\GitLab\MobileAutomation\UniteMSC\unite-mobile2 status --porcelain
git -C C:\Workspace\GitLab\api-test-automation\mobile status --porcelain
```

The utility also records before/after snapshots in `outputs/<project>/reports/EXECUTION-LOG.md`.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `JSONDecodeError: UTF-8 BOM` on Postman import | Re-export collection without BOM, or ensure you are on latest `discovery.py` (handles `utf-8-sig`) |
| `postman-collection` module not found | Run `npm install` in repo root; verify `node -e "require('postman-collection')"` |
| Source repository changed during scan | Abort; investigate what modified the repo; re-run from clean state |
| 284 `CODE_ONLY` endpoints | Expected when scanning all UniteMSC microservices; filter matrix to mobile BFF scope |
| Collection validation duplicate errors | Check `OPEN-QUESTIONS.md`; add overrides in `templates/endpoint_overrides.csv` |

---

## One-page checklist

```
[ ] bootstrap.ps1
[ ] config/project.toml configured
[ ] validate_fixture.ps1 PASS
[ ] run_all.ps1 PASS
[ ] reports reviewed
[ ] collection imported to Postman
[ ] source repos git-clean
[ ] (optional) live QC4 with --allow-network
```
