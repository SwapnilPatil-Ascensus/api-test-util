# Operating Model

## Phase A — Offline baseline

Run repository, Postman, environment, OpenAPI, and available HAR discovery. Generate the first mapping and collection. No QC4 calls occur.

## Phase B — Runtime evidence enrichment

Traverse mobile screens in coherent flows and export sanitized HAR files. Re-run the utility. Review newly discovered `HAR_ONLY` endpoints, gateway-prefix differences, query parameters, and payload shapes.

## Phase C — Conflict closure

Resolve contradictions through code-owner confirmation or a documented override. Do not use an override merely to make the report green.

## Phase D — Manual execution readiness

Populate local environment values, import the collection, execute prerequisite/auth flows, and manually validate business requests. Keep results outside source repositories and shared collection files when they contain sensitive data.

## Phase E — Later test design

Formal manual test cases and automated endpoint assertions are explicitly outside the current scope. They should be generated only after the endpoint inventory and runtime prerequisites are stable.

## Definition of done for this utility run

- every evidence record is represented in inventory or mapping,
- every generated request traces to evidence or a documented override,
- no source repository changed,
- no secret/runtime identifier exists in generated artifacts,
- QC4-only validation passes,
- unresolved endpoints remain visible,
- the collection is structurally valid and importable,
- live execution is not claimed successful without actual QC4 results.
