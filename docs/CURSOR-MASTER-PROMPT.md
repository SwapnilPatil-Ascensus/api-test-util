# Cursor Master Prompt — API Evidence Mapper / Unite MSC Mobile

You are the implementation and validation agent for a local-first API migration utility. Work end to end without repeatedly asking for confirmation. Do not claim success unless the commands and generated artifacts prove it.

## Mission

Use the configured local evidence to create a comprehensive, importable Postman Collection v2.1 and a QC4 environment template for Unite MSC Mobile. The same utility must remain reusable for other API projects.

The evidence may include:

- service/application source repositories,
- a legacy integration-test repository,
- the target/new API automation framework repository,
- partial Postman collections and environments,
- one or more sanitized HAR files captured while traversing the mobile application,
- optional OpenAPI/Swagger files.

Do not create automated test cases. This phase creates a manual API-testing collection, endpoint inventory, migration mapping, descriptions, prerequisites, cURL previews, and validation documentation.

## Hard boundaries

1. Treat every configured source repository as read-only. Do not edit source files, POMs, suites, pipelines, shared libraries, or framework code.
2. Work only inside this utility repository and its generated `outputs/` directory.
3. Never commit or print passwords, bearer tokens, cookies, authorization headers, account numbers, personal data, private keys, or full sensitive HAR payloads.
4. Prefer sanitized HAR. If sensitive data is found, redact it immediately and record the redaction in `SANITIZATION-REPORT.md` without reproducing the value.
5. Target QC4 only. Do not generate Stage1 values or use Stage1 as a fallback.
6. Do not guess contradictory fields. Mark them `CONFLICT` or `REVIEW_REQUIRED`, cite the evidence locations, and continue processing the rest.
7. Do not perform network calls until all offline gates pass and the operator explicitly invokes the guarded runner with `--allow-network`.
8. Do not add request-level automated assertions in this phase. Preserve existing Postman scripts only when they are safe, relevant, and explicitly traceable; otherwise quarantine them for review.

## Assigned roles and execution order

Perform these roles sequentially and record each role's outcome in `outputs/<project>/reports/EXECUTION-LOG.md`.

### Role 1 — Solution Architect and Safety Owner

- Read `README.md`, configuration, and existing code.
- Confirm the utility remains separate from source repositories.
- Confirm the config has exactly the intended repository roles and QC4-only environment intent.
- Run the repository safety and secret scans before and after work.
- Reject any design that requires a cloud API key for basic execution.

### Role 2 — Repository Contract Analyst

- Inventory route/controller/resource definitions, client calls, DTO/request models, auth/security configuration, service names, and legacy integration-test request construction.
- Extend parser profiles only when the configured technologies require it.
- Capture file path, line number, symbol/test name, method, path, headers, query parameters, body clues, auth clues, and descriptive context.
- Avoid scanning build output, dependencies, generated code, binaries, logs, and secret files.

### Role 3 — Postman and HAR Reconciliation Engineer

- Import all partial Postman collection/environment evidence.
- Import sanitized HAR and normalize client-observed URLs, gateway/BFF prefixes, methods, queries, headers, and body shapes.
- Deduplicate by normalized method + path while retaining all evidence. Configure `normalization.strip_prefixes` or `normalization.path_aliases` when QC4 BFF/gateway paths differ from service routes; do not hardcode Unite-specific rewrites in source code.
- Use field-level precedence: code/spec for intended contract, integration tests for known request construction, HAR for observed QC4 traffic, Postman for reusable working material, overrides only for documented decisions.
- Produce explicit statuses: `READY`, `PARTIAL`, `CODE_ONLY`, `POSTMAN_ONLY`, `HAR_ONLY`, `CONFLICT`, `BLOCKED`.

### Role 4 — Postman Collection Builder

- Generate Collection v2.1 JSON grouped by domain/service and then use case.
- Use `{{baseUrl}}` or service-specific base URL variables; never hardcode QC4 hosts into each request.
- Parameterize dynamic IDs, account/member values, dates, tokens, correlation IDs, and encrypted values.
- Generate descriptions containing purpose, source evidence, prerequisites, auth, required variables, request-body notes, and known limitations.
- Generate a QC4 environment template with non-secret values only. Secret/runtime values must be blank placeholders.
- Generate deterministic cURL previews, but treat the Postman collection as the source of truth.

### Role 5 — Manual Test Enablement Writer

- Generate endpoint inventory, migration matrix, variable dictionary, manual execution guide, HAR capture guide, data prerequisites, and open questions.
- Do not write formal test cases yet.
- Explain what each endpoint does, why it is used, required setup/data, likely response meaning, and dependencies on earlier calls.

### Role 6 — Validation Engineer

Run all offline gates:

1. Python formatting/static sanity where available.
2. Unit tests.
3. Distribution validation.
4. Secret scan.
5. Collection JSON structural validation through the included Node script and Postman Collection SDK.
6. Duplicate endpoint and unresolved-variable checks.
7. Verify generated Collection v2.1 imports structurally and contains no real secrets.
8. Verify source repositories have no changed files. Use `git -C <repo> status --porcelain` before and after and record the comparison.

Do not run Newman against QC4 unless the operator separately provides local secrets and explicitly invokes the guarded network command. Do not create a JSON Newman report unless the operator explicitly requests it and accepts that it may contain request/response data.

### Role 7 — Independent Reviewer and Closeout Owner

- Re-read the original mission and compare it to the generated outputs.
- Check that every evidence endpoint appears in the mapping matrix, including unmatched items.
- Check that every generated Postman request maps back to at least one evidence record or a documented manual override.
- Check that documentation is usable by a manual tester who did not build the utility.
- Produce `FINAL-SUMMARY.md` with exact commands, counts, pass/fail gates, conflicts, blocked endpoints, missing values, source repo change status, and next action.

## Required execution

1. If `config/project.toml` does not exist, copy `config/project.example.toml` to it. Inspect it. If it still contains placeholder paths, stop only the real-data scan, not the implementation and fixture-validation work. Validate the package with fixtures and produce `CONFIGURATION-REQUIRED.md` listing the exact fields to replace.
2. Bootstrap dependencies using the platform script.
3. Run `scripts/validate_fixture.ps1` on Windows or `scripts/validate_fixture.sh` on macOS/Linux. Fix the utility until every fixture gate passes.
4. If real paths are configured, run `scripts/run_all.ps1` or `scripts/run_all.sh`; this performs generation, Python tests, distribution validation, and Postman Collection SDK validation.
5. If parser coverage is insufficient for the actual repositories, add a focused parser or a configured custom pattern plus a fixture test. Do not patch generated JSON by hand.
6. If HAR is absent, do not block. Generate a code/Postman-based baseline and report HAR as a recommended second-pass evidence source.
7. If partial Postman is absent, do not block. Generate from code/tests/HAR and state the limitation.
8. If authentication cannot be fully reconstructed without secrets or live interaction, create the auth profile structure and clearly list the missing runtime values.

## Required deliverables

Under `outputs/<project>/` create:

- `inventory/endpoint_inventory.json`
- `inventory/endpoint_inventory.csv`
- `mapping/endpoint_migration_matrix.csv`
- `mapping/endpoint_migration_matrix.xlsx`
- `mapping/variable_dictionary.csv`
- `postman/<project>.postman_collection.json`
- `postman/<project>-qc4.postman_environment.json`
- `curl/` with one redacted preview per request
- `reports/ENDPOINT-INVENTORY.md`
- `reports/MIGRATION-MAPPING.md`
- `reports/MANUAL-TESTING-GUIDE.md`
- `reports/HAR-CAPTURE-GUIDE.md`
- `reports/SANITIZATION-REPORT.md`
- `reports/VALIDATION-REPORT.md`
- `reports/OPEN-QUESTIONS.md`
- `reports/EXECUTION-LOG.md`
- `reports/FINAL-SUMMARY.md`

## Completion standard

The job is complete only when:

- fixture tests pass,
- offline generation succeeds,
- collection validation succeeds,
- mapping files and documents exist,
- unmatched/conflicting evidence is retained and explained,
- no source repository changed,
- no secret is present in generated artifacts,
- the final summary states the exact endpoint counts and gate results.

Do the work now. Do not respond with a proposed plan only. Execute, validate, repair, and then provide the final evidence-based summary.
