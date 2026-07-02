from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ProjectConfig:
    raw: dict[str, Any]
    path: Path

    @property
    def project_id(self) -> str:
        return str(self.raw.get("project_id", "api-project"))

    @property
    def project_name(self) -> str:
        return str(self.raw.get("project_name", self.project_id))

    @property
    def output_dir(self) -> Path:
        root = Path(str(self.raw.get("output_root", "outputs")))
        if not root.is_absolute():
            root = (self.path.parent.parent / root).resolve()
        return root / self.project_id

    def resolve_path(self, value: str | Path) -> Path:
        candidate = Path(value)
        if candidate.is_absolute():
            return candidate.resolve()
        return (self.path.parent.parent / candidate).resolve()

    @property
    def repositories(self) -> list[dict[str, Any]]:
        resolved: list[dict[str, Any]] = []
        for repo in self.raw.get("repositories", []):
            item = dict(repo)
            if item.get("path"):
                item["path"] = str(self.resolve_path(str(item["path"])))
            resolved.append(item)
        return resolved

    @property
    def inputs(self) -> dict[str, Any]:
        raw_inputs = dict(self.raw.get("inputs", {}))
        for key in ("partial_postman_collections", "partial_postman_environments", "har_files", "openapi_files"):
            raw_inputs[key] = [str(self.resolve_path(str(item))) for item in raw_inputs.get(key, [])]
        if raw_inputs.get("endpoint_overrides_csv"):
            raw_inputs["endpoint_overrides_csv"] = str(self.resolve_path(str(raw_inputs["endpoint_overrides_csv"])))
        return raw_inputs

    @property
    def qc4(self) -> dict[str, Any]:
        return dict(self.raw.get("qc4", {}))

    @property
    def auth(self) -> dict[str, Any]:
        return dict(self.raw.get("auth", {}))

    @property
    def scan(self) -> dict[str, Any]:
        return dict(self.raw.get("scan", {}))

    @property
    def normalization(self) -> dict[str, Any]:
        return dict(self.raw.get("normalization", {}))

    @property
    def custom_patterns(self) -> list[dict[str, Any]]:
        return list(self.raw.get("custom_patterns", []))


def load_config(path: str | Path) -> ProjectConfig:
    config_path = Path(path).resolve()
    with config_path.open("rb") as handle:
        raw = tomllib.load(handle)
    return ProjectConfig(raw=raw, path=config_path)


def is_placeholder(value: str) -> bool:
    upper = value.upper()
    return "REPLACE" in upper or "TODO" in upper or not value.strip()


def configuration_issues(config: ProjectConfig) -> list[str]:
    issues: list[str] = []
    for repo in config.repositories:
        path = str(repo.get("path", ""))
        if is_placeholder(path):
            issues.append(f"Repository path not configured: {repo.get('name', repo.get('role', 'unknown'))}")
        elif not Path(path).exists():
            issues.append(f"Repository path does not exist: {path}")
    for key in ("partial_postman_collections", "partial_postman_environments", "har_files", "openapi_files"):
        for item in config.inputs.get(key, []):
            if is_placeholder(str(item)):
                issues.append(f"Input path not configured: {key} -> {item}")
            elif not Path(str(item)).exists():
                issues.append(f"Input path does not exist: {item}")
    base_url = str(config.qc4.get("default_base_url", ""))
    if is_placeholder(base_url):
        issues.append("QC4 default_base_url is not configured")
    if config.raw.get("strict_qc4_only", False) and any(token in base_url.lower() for token in ("stage1", "stage-1", "stage_1")):
        issues.append("Stage1 base URL is prohibited when strict_qc4_only=true")
    return issues
