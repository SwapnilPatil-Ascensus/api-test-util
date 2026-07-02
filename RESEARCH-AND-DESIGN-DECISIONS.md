# Research and Design Decisions

## 1. Collection format and local execution

The baseline output is Postman Collection v2.1 JSON because it remains the stable portable schema for Newman. Newman can run exported collections locally without a Postman API key. Postman v3/Native Git support is a separate concern and should not be forced into this local utility.

Sources:

- https://learning.postman.com/docs/reference/newman-cli/migrate-to-postman-cli/
- https://schema.postman.com/collection/json/v2.1.0/draft-07/docs/index.html
- https://github.com/postmanlabs/newman
- https://github.com/postmanlabs/postman-collection

## 2. HAR handling

Chrome DevTools can export sanitized HAR that omits sensitive headers such as Authorization and Cookie. Sanitized HAR is the required default. Sensitive HAR should not be committed and should be deleted or redacted after extraction.

Source:

- https://developer.chrome.com/docs/devtools/network/reference

## 3. Evidence reconciliation

No single source is complete:

- code may show intended routes but not deployed gateway rewrites,
- tests may contain known request construction but stale paths,
- Postman may be partially working but incomplete,
- HAR shows observed client traffic but may contain concrete data and only exercised flows.

The utility therefore uses a canonical evidence model, field-level provenance, confidence scores, conflict statuses, and explicit manual overrides.

## 4. No automatic test-case generation in this phase

Postman supports request scripts and response tests, but the present scope is manual-test enablement and migration completeness. The collection is generated without new automated assertions. Formal test-case generation is a later controlled phase.

Source:

- https://learning.postman.com/docs/tests-and-scripts/write-scripts/test-scripts

## 5. cURL generation

cURL is generated as a review and troubleshooting preview. Collection JSON is authoritative. The implementation avoids depending on cURL output for migration decisions because code generators may have edge cases around auth and escaping.

Source:

- https://github.com/postmanlabs/postman-code-generators
