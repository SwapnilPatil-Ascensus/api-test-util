# Architecture

## Design goal

Build one local utility that can reconstruct a manual-testing Postman collection from incomplete API evidence without changing the source repositories or requiring cloud credentials.

## Modules

| Module | Responsibility |
|---|---|
| `config.py` | TOML loading, path resolution, QC4-only checks, custom parser configuration |
| `discovery.py` | Repository, Postman, Postman environment, HAR, and OpenAPI extraction |
| `sanitize.py` | Token/header redaction, HAR payload templating, environment-value safety |
| `normalize.py` | URL splitting, route-parameter normalization, Postman/cURL variable conversion |
| `reconcile.py` | Canonical endpoint grouping, source precedence, confidence/status calculation, approved overrides |
| `generate.py` | CSV/XLSX mapping, Collection v2.1, QC4 environment, cURL previews, Markdown reports |
| `pipeline.py` | Read-only orchestration and source-repository before/after Git checks |
| `tools/validate_collection.js` | Structural validation with the official Postman Collection SDK |
| `scripts/run_newman_safe.py` | Explicitly gated live execution with local secret injection |

## Data flow

1. Load project configuration.
2. Snapshot source repository Git status.
3. Extract endpoint evidence from every configured source.
4. Sanitize observed runtime values before they enter the evidence model.
5. Normalize method/path pairs and retain field-level provenance.
6. Reconcile evidence without silently discarding unmatched or contradictory records.
7. Apply only documented CSV overrides.
8. Generate mapping, collection, environment, cURL, and manual-testing documentation.
9. Recheck source repository Git status and fail on any change.
10. Run offline structural, count, secret, and QC4-only validation.
11. Permit live Newman execution only through the guarded wrapper and explicit `--allow-network`.

## Evidence precedence

Precedence is field-specific:

- Method/path and request schema: OpenAPI or service route definitions.
- Known request construction: legacy integration tests.
- Actual gateway/BFF route and client behavior: sanitized QC4 HAR.
- Reusable descriptions, variables, and working examples: partial Postman collection.
- Operator decision: documented override CSV with a reason.

A higher-ranked source does not erase lower-ranked evidence. Every source remains visible in the mapping.

## Status model

- `READY`: Postman plus at least one corroborating source and no conflict.
- `PARTIAL`: useful multi-source evidence exists, but the final request still needs review.
- `CODE_ONLY`: found only in code/spec/test evidence.
- `POSTMAN_ONLY`: found only in Postman.
- `HAR_ONLY`: observed only in runtime traffic.
- `CONFLICT`: material evidence disagrees.
- `BLOCKED`: operator-defined status for a request that cannot yet be executed.

These are migration-readiness statuses, not source-code coverage percentages.
