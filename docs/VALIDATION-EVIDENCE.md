# Package Validation Evidence

Validation date: 2026-07-02

## Fixture validation (synthetic)

Validated gates:

- Python Ruff static check: pass
- Python tests: 10 passed
- Offline fixture scan and generation: pass
- Synthetic evidence records: 6
- Reconciled canonical endpoints: 2
- Required artifact validation: pass
- Postman Collection SDK parse: pass
- Generated Postman requests: 2
- Collection/mapping count match: pass
- Secret and Stage1 checks: pass
- Concrete fixture identifier/token scan: pass
- Network requests made during validation: 0

## Unite MSC Mobile offline generation (local evidence)

Configured with local `config/project.toml` (git-ignored). Source repositories were read-only and unchanged.

Validated gates:

- Python Ruff static check: pass
- Python tests: 10 passed
- Offline evidence scan and generation: pass
- Evidence records scanned: 406
- Reconciled canonical endpoints: 349
- Postman Collection v2.1 requests: 349
- Postman Collection SDK validation: pass
- Distribution artifact validation: pass
- Environment variables imported (sanitized): 64
- Sanitization events recorded: 55
- Network requests made during generation: 0
- New automated test cases created: 0

Endpoint status mix:

- READY: 27
- POSTMAN_ONLY: 38
- CODE_ONLY: 284

HAR evidence was not supplied for this run. A sanitized HAR second pass is recommended to reconcile BFF-observed traffic with service-contract routes.

Real-project QC4 execution requires copying `config/local.secrets.env.example` to `config/local.secrets.env`, reviewing `outputs/unite-msc-mobile/reports/OPEN-QUESTIONS.md`, and invoking the guarded Newman wrapper with `--allow-network` only after explicit operator authorization.
