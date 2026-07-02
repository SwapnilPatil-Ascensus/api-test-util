# Unite MSC Starter Configuration

Use the three repository roles consistently:

1. `service_source`: microservice/application implementation containing controllers, routes, DTOs, and security configuration.
2. `legacy_api_tests`: old integration/API automation implementation containing known request construction and data dependencies.
3. `target_framework`: new API framework containing conventions, utilities, and any already migrated endpoints.

Recommended Unite MSC settings:

- `project_id = "unite-msc-mobile"`
- `environment_name = "QC4"`
- `strict_qc4_only = true`
- partial collection paths from Nate/Luis or other known sources,
- sanitized HAR files grouped by mobile flow,
- separate service base URL variables when the BFF, auth server, or downstream service hosts differ.

Keep this utility outside the canonical `mobile/` automation source tree. Do not edit `jsonapi-core`, shared HTTP clients, POMs, TestNG suites, pipeline files, or JaCoCo configuration while building the manual Postman baseline.

## BFF and gateway route differences

When a mobile HAR shows a BFF path that differs from the service controller path, first record the difference in the mapping report. Then configure either:

- `normalization.strip_prefixes` for a simple gateway-only prefix, or
- `[[normalization.path_aliases]]` with explicit `from` and `to` prefixes.

This changes reconciliation only. It does not rewrite source repositories or silently discard either path; both evidence locations remain in the endpoint inventory.
