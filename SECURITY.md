# Security and Data Handling

This utility is intended for local use with internal code and QC4 evidence.

Do not commit or share:

- `config/local.secrets.env`,
- raw or sensitive HAR files,
- populated Postman environments,
- bearer tokens, cookies, passwords, API keys, private keys,
- member, account, user, or customer identifiers,
- unredacted request or response bodies containing PII.

The generated collection is a template, not a secure secret store. Runtime values are injected only by the guarded Newman wrapper. Review `SANITIZATION-REPORT.md` after every evidence refresh.

A report that says structural validation passed does not prove that an endpoint is authorized, safe to execute, or functionally correct in QC4. Live execution requires explicit operator approval and `--allow-network`.
