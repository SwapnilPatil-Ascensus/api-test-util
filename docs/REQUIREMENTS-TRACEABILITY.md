# Requirements Traceability

| Requested capability | Implementation | Verification |
|---|---|---|
| Read three local repositories | TOML `[[repositories]]` roles and read-only scanning | before/after Git status snapshots; hard failure on change |
| Discover endpoints, methods, auth, payload clues | built-in code/test parsers, OpenAPI parser, Postman importer, HAR importer, custom regex profiles | fixture unit tests and endpoint inventory provenance |
| Merge old code, partial Postman, target framework, and HAR | canonical method/path reconciliation with source weighting, conflicts, and manual overrides | migration matrix and evidence count checks |
| Handle QC4, not Stage1 | `strict_qc4_only`, environment sanitization, Stage1 distribution gate | distribution validator |
| Produce a comprehensive manual Postman baseline | Postman Collection v2.1, QC4 environment, descriptions, variables, cURL previews | Postman Collection SDK validation |
| Support BFF/gateway path differences | configurable prefix stripping and path aliases | normalization unit test |
| Produce mapping documentation | CSV and formatted XLSX plus Markdown reports | required-artifact and count gates |
| Avoid keys and secrets in the project | blank secret placeholders, HAR/Postman sanitization, ignored local secret file | secret scans and environment-value gate |
| Work for other API projects | generic config, parser extension guide, custom patterns, no Unite-specific parser logic | reusable fixture project |
| No automated test cases in this phase | collection generation excludes new assertions; scripts are summarized only | collection inspection and scope documents |
| Validate locally without network calls | fixture validation script and guarded Newman runner | fixture evidence and explicit `--allow-network` requirement |
| One Cursor execution prompt with roles | `docs/CURSOR-MASTER-PROMPT.md` and role/gate matrix | required closeout summary |
