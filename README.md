# API Evidence Mapper

API Evidence Mapper is a local-first utility for reconstructing and validating a complete Postman collection from incomplete and conflicting evidence.

It reads, but does not modify:

- service/application source repositories,
- legacy API integration-test repositories,
- a target/new API framework repository,
- partial Postman collections and environments,
- sanitized browser or mobile WebView HAR captures,
- optional OpenAPI/Swagger definitions.

It produces:

- a canonical endpoint inventory,
- an evidence-to-endpoint migration matrix in CSV and Excel,
- a Postman Collection v2.1 JSON file,
- a QC4 environment template with placeholders only,
- one cURL preview per endpoint,
- manual-testing guidance,
- conflict, gap, and unresolved-value reports,
- local validation commands and Newman reports.

## What this utility does not do

It does not create automated test cases. It does not commit secrets. It does not modify any source repository. It does not infer credentials, account numbers, tokens, PII, or production data. It does not silently resolve contradictory evidence.

## Why the output uses Postman Collection v2.1

The default execution path is fully local and does not require a Postman API key or cloud login. Newman runs Collection v2.1 JSON locally. The utility therefore generates v2.1 as the compatibility baseline. A later migration to Postman v3 can be done separately if Native Git/Postman cloud features are required.

## Fast start

1. Extract this folder outside the three source repositories.
2. Run `scripts/initialize.ps1` on Windows or `scripts/initialize.sh` on macOS/Linux.
3. Replace the path placeholders and QC4 non-secret host values in `config/project.toml`.
4. Run `scripts/bootstrap.ps1` on Windows or `scripts/bootstrap.sh` on macOS/Linux.
5. Run `scripts/validate_fixture.ps1` or `scripts/validate_fixture.sh`. This proves the package without touching QC4.
6. Run `scripts/run_all.ps1` or `scripts/run_all.sh` against the configured local evidence.
7. Review `outputs/<project>/reports/VALIDATION-REPORT.md` before running any QC4 request.
8. Copy `config/local.secrets.env.example` to `config/local.secrets.env` only for a live run, keep values local, and invoke the guarded Newman wrapper with `--allow-network`.

The complete Cursor execution instruction is in `START-HERE-CURSOR.md` and `CURSOR-MASTER-PROMPT.md`.

## Primary command

```powershell
python -m api_evidence_mapper all --config config/project.toml
```

This command is offline. It scans local evidence and generates artifacts; it does not call QC4.

## Guarded QC4 execution

```powershell
python scripts/run_newman_safe.py `
  --collection outputs/unite-msc-mobile/postman/unite-msc-mobile.postman_collection.json `
  --environment outputs/unite-msc-mobile/postman/unite-msc-mobile-qc4.postman_environment.json `
  --secrets config/local.secrets.env `
  --allow-network
```

The wrapper refuses to run without the explicit `--allow-network` flag. It merges secrets into a restricted temporary environment file, removes that file after execution, and does not place secret values on the Newman command line. JSON reports are disabled unless an explicit `--json-report` path is supplied because those reports may contain request or response data.

## Recommended evidence precedence

Evidence is resolved field by field, not file by file:

1. Server route definitions and API specifications establish intended method/path and contract.
2. Existing integration tests establish known request construction, variables, and expected usage.
3. Sanitized HAR establishes what the client actually called in QC4 and exposes gateway/BFF rewrites.
4. Partial Postman content contributes known working requests, descriptions, variables, and scripts, but is not assumed complete.
5. Manual override files resolve only documented conflicts.

Every final field retains evidence references and a confidence level. Configurable `strip_prefixes` and `path_aliases` reconcile BFF/gateway routes with service-contract routes without adding Unite-specific logic to the parser.

## Detailed documentation

- `docs/ARCHITECTURE.md`
- `docs/OPERATING-MODEL.md`
- `docs/PARSER-EXTENSION-GUIDE.md`
- `docs/UNITE-MSC-STARTER-CONFIG.md`
- `docs/ROLE-AND-GATE-MATRIX.md`
