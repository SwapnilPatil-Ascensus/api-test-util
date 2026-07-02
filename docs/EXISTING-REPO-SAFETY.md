# Existing Repository Safety

The utility must be extracted as a sibling folder, not inside `mobile/`, the legacy API repository, or the target automation repository.

Source repositories are evidence only. The utility captures `git status --porcelain` before and after scanning. Any change is a hard failure.

If corporate policy forces temporary placement inside an existing repository, do not change the repository `.gitignore`. Add the utility's runtime folders only to that repository's local `.git/info/exclude`, then remove the utility after use.

Never commit:

- HAR files,
- Postman environments containing values,
- tokens, cookies, auth headers, or passwords,
- member/account identifiers or PII,
- raw response bodies,
- generated QC4 run reports containing request/response data.
