# Start Here in Cursor

Open this extracted utility folder in Cursor. Do not open Cursor at the root of any source repository for this task.

1. Copy `config/project.example.toml` to `config/project.toml`.
2. Put the three local repository paths, partial Postman paths, and HAR paths into `config/project.toml`.
3. Run the bootstrap script, then paste the prompt from `CURSOR-MASTER-PROMPT.md` into Cursor Agent mode.
4. Allow Cursor to inspect and edit only this utility folder. Source repositories are read-only evidence.
5. Do not provide credentials in chat. Put local values into `config/local.secrets.env` only after artifact generation is complete.

Expected finish condition:

- offline scan succeeds,
- unit tests pass,
- collection structural validation passes,
- mapping CSV/XLSX and documentation are created,
- all source conflicts and missing runtime values are explicitly reported,
- no source repository changed,
- no network execution occurred unless you explicitly supplied `--allow-network`.
