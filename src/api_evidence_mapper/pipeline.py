from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from .config import ProjectConfig, configuration_issues
from .discovery import parse_har, parse_openapi, parse_postman, parse_postman_environment, scan_repository
from .generate import ensure_output_dirs, write_curl, write_inventory, write_mapping, write_postman, write_reports
from .models import Evidence
from .reconcile import apply_overrides, reconcile


def git_status(path: str) -> str:
    try:
        result = subprocess.run(["git", "-C", path, "status", "--porcelain"], check=False, capture_output=True, text=True, timeout=20)
        if result.returncode != 0:
            return f"<not-a-git-repository-or-status-failed: {result.stderr.strip()}>"
        return result.stdout.strip()
    except Exception as exc:
        return f"<git-status-unavailable: {exc}>"


def collect_evidence(config: ProjectConfig) -> tuple[list[Evidence], list[str], dict[str, str], list[dict[str, Any]]]:
    evidence: list[Evidence] = []
    sanitization: list[str] = []
    repo_status: dict[str, str] = {}
    environment_values: list[dict[str, Any]] = []
    max_file_size = int(config.scan.get("max_file_size_bytes", 2_000_000))

    before_status: dict[str, str] = {}
    for repo in config.repositories:
        path = str(repo.get("path", ""))
        if not Path(path).exists():
            continue
        name = str(repo.get("name", path))
        before_status[name] = git_status(path)
        repo_status[f"before:{name}"] = before_status[name]
        evidence.extend(scan_repository(repo, max_file_size=max_file_size, custom_patterns=config.custom_patterns))

    for path in config.inputs.get("partial_postman_collections", []):
        if Path(str(path)).exists():
            parsed, report = parse_postman(path)
            evidence.extend(parsed)
            sanitization.extend(report)

    for path in config.inputs.get("partial_postman_environments", []):
        if Path(str(path)).exists():
            values, report = parse_postman_environment(path)
            environment_values.extend(values)
            sanitization.extend(report)

    for path in config.inputs.get("har_files", []):
        if Path(str(path)).exists():
            parsed, report = parse_har(path, include_sensitive_headers=bool(config.scan.get("include_sensitive_har_headers", False)))
            evidence.extend(parsed)
            sanitization.extend(report)

    for path in config.inputs.get("openapi_files", []):
        if Path(str(path)).exists():
            evidence.extend(parse_openapi(path))

    for repo in config.repositories:
        path = str(repo.get("path", ""))
        if not Path(path).exists():
            continue
        name = str(repo.get("name", path))
        after = git_status(path)
        repo_status[f"after:{name}"] = after
        if before_status.get(name) != after:
            raise RuntimeError(f"Source repository changed during scan: {name}. Before and after git status differ.")

    return evidence, sanitization, repo_status, environment_values


def run_all(config: ProjectConfig) -> dict:
    issues = configuration_issues(config)
    evidence, sanitization, repo_status, environment_values = collect_evidence(config)
    endpoints = reconcile(evidence, config.normalization)
    override_audit = apply_overrides(endpoints, config.inputs.get("endpoint_overrides_csv"), config.normalization)
    root = config.output_dir
    if root.exists():
        shutil.rmtree(root)
    ensure_output_dirs(root)
    write_inventory(root, evidence)
    write_mapping(root, endpoints)
    collection_path, env_path = write_postman(root, config, endpoints, environment_values)
    write_curl(root, config, endpoints)
    write_reports(root, config, evidence, endpoints, sanitization, issues, override_audit)
    log_lines = ["# Execution Log", "", "## Repository status snapshots", ""]
    for key, value in repo_status.items():
        log_lines.append(f"### {key}\n\n```text\n{value or '<clean>'}\n```")
    if override_audit:
        log_lines.extend(["", "## Manual override audit", ""] + [f"- {item}" for item in override_audit])
    (root / "reports/EXECUTION-LOG.md").write_text("\n\n".join(log_lines) + "\n", encoding="utf-8")
    return {
        "project": config.project_id,
        "output": str(root),
        "evidence_count": len(evidence),
        "endpoint_count": len(endpoints),
        "collection": str(collection_path),
        "environment": str(env_path),
        "configuration_issues": issues,
        "environment_variables_imported": len(environment_values),
        "overrides_applied_or_reported": len(override_audit),
    }
