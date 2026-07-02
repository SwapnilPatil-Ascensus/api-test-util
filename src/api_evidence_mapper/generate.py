from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from .config import ProjectConfig
from .models import CanonicalEndpoint, Evidence
from .normalize import postmanize_path, redact_headers


def ensure_output_dirs(root: Path) -> None:
    for name in ("inventory", "mapping", "postman", "curl", "reports", "validation"):
        (root / name).mkdir(parents=True, exist_ok=True)


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def write_inventory(root: Path, evidence: list[Evidence]) -> None:
    write_json(root / "inventory/endpoint_inventory.json", [item.to_dict() for item in evidence])
    headers = ["source_type", "source_name", "location", "line", "method", "path", "operation_name", "description", "auth_type", "service", "raw_url"]
    with (root / "inventory/endpoint_inventory.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for item in evidence:
            row = item.to_dict()
            writer.writerow({key: row.get(key, "") for key in headers})


def mapping_rows(endpoints: list[CanonicalEndpoint]) -> list[dict[str, Any]]:
    rows = []
    for ep in endpoints:
        payload_clues = []
        observed_statuses = []
        for item in ep.evidence:
            if item.metadata.get("request_body_type"):
                payload_clues.append(f"{item.source_type}:type={item.metadata['request_body_type']}")
            if item.metadata.get("request_body_expression"):
                payload_clues.append(f"{item.source_type}:expression={item.metadata['request_body_expression']}")
            if item.metadata.get("requestBody"):
                payload_clues.append(f"{item.source_type}:OpenAPI requestBody present")
            if item.metadata.get("status") is not None:
                observed_statuses.append(str(item.metadata["status"]))
        prerequisites = []
        if ep.auth_type not in {"", "unknown", "noauth"}:
            prerequisites.append(f"auth={ep.auth_type}")
        if ep.required_variables:
            prerequisites.append("variables=" + ", ".join(ep.required_variables))
        rows.append({
            "endpoint_id": ep.endpoint_id,
            "status": ep.status,
            "confidence": ep.confidence,
            "service": ep.service,
            "method": ep.method,
            "canonical_path": ep.path,
            "normalized_match_path": ep.match_path,
            "name": ep.name,
            "use_case_description": ep.description,
            "prerequisites": " | ".join(prerequisites),
            "auth_type": ep.auth_type,
            "required_variables": ", ".join(ep.required_variables),
            "payload_clues": " | ".join(sorted(set(payload_clues))),
            "observed_status_codes": ", ".join(sorted(set(observed_statuses))),
            "source_types": ", ".join(ep.source_types),
            "evidence_count": len(ep.evidence),
            "conflicts": " | ".join(ep.conflicts),
            "evidence_locations": " | ".join(f"{e.source_type}:{e.location}:{e.line or ''}" for e in ep.evidence),
        })
    return rows


def write_mapping(root: Path, endpoints: list[CanonicalEndpoint]) -> None:
    rows = mapping_rows(endpoints)
    headers = list(rows[0].keys()) if rows else ["endpoint_id", "status", "confidence", "service", "method", "canonical_path", "normalized_match_path", "name", "use_case_description", "prerequisites", "auth_type", "required_variables", "payload_clues", "observed_status_codes", "source_types", "evidence_count", "conflicts", "evidence_locations"]
    csv_path = root / "mapping/endpoint_migration_matrix.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    variable_rows = []
    seen = set()
    for ep in endpoints:
        for variable in ep.required_variables:
            if variable in seen:
                continue
            seen.add(variable)
            variable_rows.append({"variable": variable, "value": "", "scope": "environment", "sensitive": "review", "description": "Discovered from endpoint evidence", "used_by": ep.endpoint_id})
    with (root / "mapping/variable_dictionary.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["variable", "value", "scope", "sensitive", "description", "used_by"])
        writer.writeheader()
        writer.writerows(variable_rows)
    try:
        import xlsxwriter
        workbook = xlsxwriter.Workbook(root / "mapping/endpoint_migration_matrix.xlsx")
        ws = workbook.add_worksheet("Endpoint Mapping")
        header_fmt = workbook.add_format({"bold": True, "bg_color": "#1F4E78", "font_color": "#FFFFFF", "border": 1, "text_wrap": True})
        body_fmt = workbook.add_format({"border": 1, "text_wrap": True, "valign": "top"})
        conflict_fmt = workbook.add_format({"border": 1, "text_wrap": True, "valign": "top", "bg_color": "#FCE4D6"})
        for col, header in enumerate(headers):
            ws.write(0, col, header, header_fmt)
        for row_index, row in enumerate(rows, 1):
            fmt = conflict_fmt if row.get("status") == "CONFLICT" else body_fmt
            for col, header in enumerate(headers):
                ws.write(row_index, col, row.get(header, ""), fmt)
        ws.freeze_panes(1, 0)
        ws.autofilter(0, 0, max(len(rows), 1), len(headers) - 1)
        widths = {0: 16, 1: 14, 2: 12, 3: 22, 4: 10, 5: 42, 6: 42, 7: 34, 8: 55, 9: 45, 10: 16, 11: 30, 12: 55, 13: 20, 14: 32, 15: 14, 16: 50, 17: 70}
        for col, width in widths.items():
            ws.set_column(col, col, width)
        summary = workbook.add_worksheet("Summary")
        summary.write_row(0, 0, ["Metric", "Count"], header_fmt)
        metrics = defaultdict(int)
        for row in rows:
            metrics[row["status"]] += 1
        summary.write_row(1, 0, ["Total endpoints", len(rows)], body_fmt)
        cursor = 2
        for key in sorted(metrics):
            summary.write_row(cursor, 0, [key, metrics[key]], body_fmt)
            cursor += 1
        workbook.close()
    except Exception as exc:
        (root / "reports/XLSX-GENERATION-WARNING.md").write_text(f"# XLSX Generation Warning\n\n{exc}\n", encoding="utf-8")


def _postman_url(base_var: str, path: str, query: dict[str, str]) -> dict[str, Any]:
    path = postmanize_path(path)
    raw = f"{{{{{base_var}}}}}{path}"
    query_list = []
    if query:
        query_list = [{"key": key, "value": value} for key, value in sorted(query.items())]
        raw += "?" + "&".join(f"{key}={value}" for key, value in sorted(query.items()))
    return {"raw": raw, "host": [f"{{{{{base_var}}}}}"], "path": [part for part in path.strip("/").split("/") if part], "query": query_list}


def _postman_body(body: Any) -> dict[str, Any] | None:
    if body in (None, "", {}, []):
        return None
    if isinstance(body, dict) and "mode" in body:
        clean = dict(body)
        return clean
    if isinstance(body, (dict, list)):
        return {"mode": "raw", "raw": json.dumps(body, indent=2), "options": {"raw": {"language": "json"}}}
    return {"mode": "raw", "raw": str(body)}


def _request_description(ep: CanonicalEndpoint) -> str:
    evidence = "\n".join(f"- {e.source_type}: {e.location}{':' + str(e.line) if e.line else ''}" for e in ep.evidence)
    conflicts = "\n".join(f"- {item}" for item in ep.conflicts) or "- None detected"
    body_clues = []
    for item in ep.evidence:
        if item.metadata.get("request_body_type"):
            body_clues.append(f"- {item.source_type}: request type {item.metadata['request_body_type']}")
        if item.metadata.get("request_body_expression"):
            body_clues.append(f"- {item.source_type}: body expression {item.metadata['request_body_expression']}")
    body_notes = "\n".join(body_clues) or "- No code-level payload clue detected"
    return f"""Purpose: {ep.description or ep.name}

Migration status: {ep.status}
Confidence: {ep.confidence}
Authentication: {ep.auth_type}
Required variables: {', '.join(ep.required_variables) or 'None discovered'}

Payload clues:
{body_notes}

Evidence:
{evidence}

Known conflicts/limitations:
{conflicts}

This request was generated for manual validation. No new automated test assertions were added.
"""


def build_postman_collection(config: ProjectConfig, endpoints: list[CanonicalEndpoint]) -> dict[str, Any]:
    base_var = str(config.qc4.get("base_url_variable", "baseUrl"))
    folders: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for ep in endpoints:
        headers = [{"key": key, "value": value, "type": "text"} for key, value in sorted(redact_headers(ep.headers).items()) if key.lower() not in {"authorization", "cookie", "set-cookie"}]
        request: dict[str, Any] = {"method": ep.method, "header": headers, "url": _postman_url(base_var, ep.path, ep.query), "description": _request_description(ep)}
        body = _postman_body(ep.body)
        if body:
            request["body"] = body
        if ep.auth_type in {"bearer", "oauth2"}:
            request["auth"] = {"type": "bearer", "bearer": [{"key": "token", "value": "{{accessToken}}", "type": "string"}]}
        elif ep.auth_type == "basic":
            request["auth"] = {"type": "basic", "basic": [{"key": "username", "value": "{{username}}", "type": "string"}, {"key": "password", "value": "{{password}}", "type": "string"}]}
        elif ep.auth_type == "apikey":
            request["auth"] = {"type": "apikey", "apikey": [{"key": "key", "value": "x-api-key", "type": "string"}, {"key": "value", "value": "{{apiKey}}", "type": "string"}, {"key": "in", "value": "header", "type": "string"}]}
        item = {"name": ep.name, "request": request}
        folders[ep.service or "unclassified"].append(item)
    return {
        "info": {"name": f"{config.project_name} - QC4 Manual Validation", "description": "Generated by API Evidence Mapper from repository, Postman, HAR, and specification evidence. No new automated test cases are included.", "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"},
        "item": [{"name": service, "item": sorted(items, key=lambda item: item["name"])} for service, items in sorted(folders.items())],
        "variable": [{"key": base_var, "value": "", "type": "string"}],
    }


def build_environment(config: ProjectConfig, endpoints: list[CanonicalEndpoint], imported_values: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    values = []
    base_var = str(config.qc4.get("base_url_variable", "baseUrl"))
    values.append({"key": base_var, "value": str(config.qc4.get("default_base_url", "")), "type": "default", "enabled": True})
    for key, value in sorted(dict(config.qc4.get("service_base_urls", {})).items()):
        values.append({"key": key, "value": value, "type": "default", "enabled": True})
    known = {item["key"] for item in values}
    for item in imported_values or []:
        key = str(item.get("key", "")).strip()
        if not key or key in known:
            continue
        values.append({"key": key, "value": str(item.get("value", "")), "type": "secret" if item.get("sensitive") else "default", "enabled": True})
        known.add(key)
    auth = config.auth
    for key in (str(auth.get("token_variable", "accessToken")), str(auth.get("username_variable", "username")), str(auth.get("password_variable", "password")), str(auth.get("api_key_variable", "apiKey"))):
        if key not in known:
            values.append({"key": key, "value": "", "type": "secret", "enabled": True})
            known.add(key)
    for ep in endpoints:
        for variable in ep.required_variables:
            if variable not in known:
                values.append({"key": variable, "value": "", "type": "default", "enabled": True})
                known.add(variable)
    return {"name": f"{config.project_name} - QC4", "values": values, "_postman_variable_scope": "environment", "_postman_exported_using": "API Evidence Mapper"}


def write_postman(root: Path, config: ProjectConfig, endpoints: list[CanonicalEndpoint], imported_values: list[dict[str, Any]] | None = None) -> tuple[Path, Path]:
    collection_path = root / f"postman/{config.project_id}.postman_collection.json"
    env_path = root / f"postman/{config.project_id}-qc4.postman_environment.json"
    write_json(collection_path, build_postman_collection(config, endpoints))
    write_json(env_path, build_environment(config, endpoints, imported_values))
    return collection_path, env_path


def _safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-")[:120] or "request"


def write_curl(root: Path, config: ProjectConfig, endpoints: list[CanonicalEndpoint]) -> None:
    base_var = str(config.qc4.get("base_url_variable", "baseUrl"))
    for ep in endpoints:
        curl_path = re.sub(r"\{\{?([A-Za-z_][A-Za-z0-9_.-]*)\}\}?", r"${\1}", ep.path)
        curl_path = re.sub(r":([A-Za-z_][A-Za-z0-9_]*)", r"${\1}", curl_path)
        if ep.query:
            query_parts = []
            for key, value in sorted(ep.query.items()):
                shell_value = re.sub(r"\{\{\s*([A-Za-z_][A-Za-z0-9_.-]*)\s*\}\}", r"${\1}", str(value))
                query_parts.append(f"{key}={shell_value}")
            curl_path += "?" + "&".join(query_parts)
        args = [f"curl --request {ep.method}", f'--url "${{{base_var}}}{curl_path}"']
        if ep.auth_type in {"bearer", "oauth2"}:
            args.append('--header "Authorization: Bearer ${accessToken}"')
        for key, value in sorted(redact_headers(ep.headers).items()):
            if key.lower() in {"authorization", "cookie", "set-cookie"}:
                continue
            args.append(f'--header "{key}: {value}"')
        body_block = ""
        if ep.body not in (None, "", {}, []):
            raw = ep.body.get("raw") if isinstance(ep.body, dict) and ep.body.get("mode") == "raw" else json.dumps(ep.body, default=str)
            args.append("--data-raw @-")
            body_block = " <<'JSON'\n" + str(raw) + "\nJSON"
        command = (" \\\n  ".join(args)) + body_block + "\n"
        name = _safe_filename(f"{ep.endpoint_id}-{ep.method}-{ep.path}") + ".sh"
        (root / "curl" / name).write_text(command, encoding="utf-8")


def write_reports(root: Path, config: ProjectConfig, evidence: list[Evidence], endpoints: list[CanonicalEndpoint], sanitization: list[str], config_issues: list[str], override_audit: list[str] | None = None) -> None:
    statuses = defaultdict(int)
    for ep in endpoints:
        statuses[ep.status] += 1
    inventory_lines = [f"# Endpoint Inventory — {config.project_name}", "", f"Evidence records: {len(evidence)}", f"Canonical endpoints: {len(endpoints)}", "", "| ID | Status | Method | Path | Sources |", "|---|---|---|---|---|"]
    for ep in endpoints:
        inventory_lines.append(f"| {ep.endpoint_id} | {ep.status} | {ep.method} | `{ep.path}` | {', '.join(ep.source_types)} |")
    (root / "reports/ENDPOINT-INVENTORY.md").write_text("\n".join(inventory_lines) + "\n", encoding="utf-8")
    mapping_lines = [f"# Migration Mapping — {config.project_name}", "", "Status counts:", ""] + [f"- {key}: {value}" for key, value in sorted(statuses.items())]
    mapping_lines += ["", "Detailed evidence is in `mapping/endpoint_migration_matrix.xlsx` and `.csv`."]
    (root / "reports/MIGRATION-MAPPING.md").write_text("\n".join(mapping_lines) + "\n", encoding="utf-8")
    (root / "reports/MANUAL-TESTING-GUIDE.md").write_text(f"""# Manual Testing Guide — {config.project_name}

1. Import the generated collection and QC4 environment into Postman.
2. Fill only the local QC4 variables required for the flow. Do not save secrets in shared files.
3. Start with prerequisite/authentication folders before dependent business requests.
4. Read each request description for evidence, required variables, and conflicts.
5. Do not execute requests marked `CONFLICT` or `BLOCKED` until the mapping issue is resolved.
6. Record manual results outside the collection in the agreed evidence location.
7. Use the guarded Newman wrapper only after offline validation and only with `--allow-network`.

This phase does not contain newly generated test assertions or formal manual test cases.
""", encoding="utf-8")
    (root / "reports/HAR-CAPTURE-GUIDE.md").write_text((Path(__file__).resolve().parents[2] / "docs/HAR-CAPTURE-INSTRUCTIONS.md").read_text(encoding="utf-8"), encoding="utf-8")
    sanitize_lines = ["# Sanitization Report", "", f"Redaction events: {len(sanitization)}", ""] + [f"- {item}" for item in sanitization]
    if not sanitization:
        sanitize_lines.append("- No token-like or sensitive HAR values were retained by the parser.")
    (root / "reports/SANITIZATION-REPORT.md").write_text("\n".join(sanitize_lines) + "\n", encoding="utf-8")
    open_questions = ["# Open Questions", ""]
    for issue in config_issues:
        open_questions.append(f"- CONFIGURATION: {issue}")
    for ep in endpoints:
        if ep.status in {"CONFLICT", "CODE_ONLY", "POSTMAN_ONLY", "HAR_ONLY", "PARTIAL", "BLOCKED"}:
            open_questions.append(f"- {ep.endpoint_id} {ep.method} {ep.path}: status={ep.status}; {'; '.join(ep.conflicts) or 'additional evidence or review required'}")
    if override_audit:
        open_questions.append("")
        open_questions.append("## Manual override audit")
        open_questions.extend(f"- {item}" for item in override_audit)
    if len(open_questions) == 2:
        open_questions.append("- None generated.")
    (root / "reports/OPEN-QUESTIONS.md").write_text("\n".join(open_questions) + "\n", encoding="utf-8")
    validation = ["# Validation Report", "", "## Offline generation", "", "- Endpoint evidence scanned: " + str(len(evidence)), "- Canonical endpoints produced: " + str(len(endpoints)), "- Network calls performed: 0", "", "## Status counts", ""] + [f"- {key}: {value}" for key, value in sorted(statuses.items())]
    validation += ["", "## Offline gates to record", "", "- Python unit tests.", "- `scripts/validate_distribution.py`.", "- Postman Collection SDK validation.", "- Source repository before/after Git status comparison."]
    (root / "reports/VALIDATION-REPORT.md").write_text("\n".join(validation) + "\n", encoding="utf-8")
    summary = [f"# Final Summary — {config.project_name}", "", f"- Evidence records: {len(evidence)}", f"- Canonical endpoints: {len(endpoints)}", f"- Collection: `postman/{config.project_id}.postman_collection.json`", f"- QC4 environment: `postman/{config.project_id}-qc4.postman_environment.json`", "- New automated test cases created: 0", "- Network calls performed during generation: 0", "", "Review `VALIDATION-REPORT.md` and `OPEN-QUESTIONS.md` before live execution."]
    (root / "reports/FINAL-SUMMARY.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
