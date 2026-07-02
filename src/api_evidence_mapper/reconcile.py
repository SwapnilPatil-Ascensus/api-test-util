from __future__ import annotations

import json
from collections import defaultdict
from typing import Iterable

from .models import CanonicalEndpoint, Evidence
from .normalize import detect_required_variables, endpoint_id, extract_path_variables, normalize_match_path

SOURCE_WEIGHT = {
    "openapi": 100,
    "service_source": 90,
    "legacy_api_tests": 75,
    "target_framework": 65,
    "har": 80,
    "postman": 60,
}

GENERIC_DESCRIPTIONS = {
    "Spring route definition",
    "JAX-RS route definition",
    "Python web route definition",
    "JavaScript/TypeScript route definition",
    "ASP.NET route definition",
    "HTTP client/test call",
    "Observed client request from sanitized HAR",
}


def _humanize(value: str) -> str:
    import re
    value = value or ""
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    value = value.replace("_", " ").replace("-", " ")
    value = re.sub(r"\s+", " ", value).strip()
    return value[:1].upper() + value[1:] if value else ""


def _best_description(items: list[Evidence], fallback_name: str) -> str:
    source_bonus = {"openapi": 100, "postman": 90, "service_source": 70, "har": 50, "legacy_api_tests": 40, "target_framework": 35}
    candidates = [item for item in items if item.description]
    if candidates:
        best = max(candidates, key=lambda item: source_bonus.get(item.source_type, 20) + min(len(item.description), 200) - (200 if item.description in GENERIC_DESCRIPTIONS else 0))
        if best.description not in GENERIC_DESCRIPTIONS:
            return best.description.strip()
    return _humanize(fallback_name) or "Manual API request"


def _best(items: list[Evidence], field: str):
    candidates = [item for item in items if getattr(item, field)]
    if not candidates:
        return None
    return max(candidates, key=lambda item: SOURCE_WEIGHT.get(item.source_type, 50))


def _json_signature(value) -> str:
    if value in (None, "", {}, []):
        return ""
    try:
        return json.dumps(value, sort_keys=True, default=str)
    except Exception:
        return str(value)


def reconcile(evidence: Iterable[Evidence], normalization: dict | None = None) -> list[CanonicalEndpoint]:
    normalization = normalization or {}
    strip_prefixes = list(normalization.get("strip_prefixes", []))
    path_aliases = list(normalization.get("path_aliases", []))
    ignore_query_keys = {str(item).lower() for item in normalization.get("ignore_query_keys", [])}
    groups: dict[tuple[str, str], list[Evidence]] = defaultdict(list)
    for item in evidence:
        if not item.method or not item.path:
            continue
        groups[(item.method.upper(), normalize_match_path(item.path, strip_prefixes, path_aliases))].append(item)

    endpoints: list[CanonicalEndpoint] = []
    for (method, match_path), items in sorted(groups.items()):
        path_item = _best(items, "path") or items[0]
        auth_item = _best([item for item in items if item.auth_type not in {"", "unknown"}], "auth_type")
        body_item = _best([item for item in items if item.body not in (None, "", {}, [])], "body")
        service_item = _best([item for item in items if item.service not in {"", "unclassified"}], "service")
        name_item = _best([item for item in items if item.operation_name], "operation_name")
        resolved_name = name_item.operation_name if name_item else f"{method} {path_item.path}"
        resolved_description = _best_description(items, resolved_name)
        sources = sorted(set(item.source_type for item in items))
        conflicts: list[str] = []
        auth_types = sorted(set(item.auth_type for item in items if item.auth_type not in {"", "unknown"}))
        if len(auth_types) > 1:
            conflicts.append("Authentication evidence differs: " + " | ".join(auth_types))
        bodies = sorted(set(_json_signature(item.body) for item in items if _json_signature(item.body)))
        if len(bodies) > 1:
            conflicts.append("Request body evidence differs across sources")
        source_set = set(sources)
        if conflicts:
            status = "CONFLICT"
        elif "postman" in source_set and ("service_source" in source_set or "openapi" in source_set or "har" in source_set or "legacy_api_tests" in source_set):
            status = "READY"
        elif source_set == {"postman"}:
            status = "POSTMAN_ONLY"
        elif source_set == {"har"}:
            status = "HAR_ONLY"
        elif source_set <= {"service_source", "openapi", "legacy_api_tests", "target_framework"}:
            status = "CODE_ONLY"
        else:
            status = "PARTIAL"
        if len(source_set) >= 3 and not conflicts:
            confidence = "HIGH"
        elif len(source_set) >= 2 and not conflicts:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"
        merged_headers: dict[str, str] = {}
        merged_query: dict[str, str] = {}
        for item in sorted(items, key=lambda item: SOURCE_WEIGHT.get(item.source_type, 50)):
            merged_headers.update(item.headers)
            merged_query.update({key: value for key, value in item.query.items() if key.lower() not in ignore_query_keys})
        auth_type = auth_item.auth_type if auth_item else "unknown"
        required = sorted(set(extract_path_variables(path_item.path) + detect_required_variables({"path": path_item.path, "headers": merged_headers, "query": merged_query, "body": body_item.body if body_item else None})))
        endpoints.append(CanonicalEndpoint(endpoint_id=endpoint_id(method, match_path), method=method, path=path_item.path, match_path=match_path, service=service_item.service if service_item else "unclassified", name=resolved_name, description=resolved_description, auth_type=auth_type, headers=merged_headers, query=merged_query, body=body_item.body if body_item else None, source_types=sources, evidence=items, status=status, confidence=confidence, conflicts=conflicts, required_variables=required))
    return endpoints


def apply_overrides(endpoints: list[CanonicalEndpoint], csv_path: str | None, normalization: dict | None = None) -> list[str]:
    """Apply explicit operator-approved field overrides. Returns audit log entries."""
    if not csv_path:
        return []
    from pathlib import Path
    import csv

    path = Path(csv_path)
    if not path.exists():
        return []
    normalization = normalization or {}
    strip_prefixes = list(normalization.get("strip_prefixes", []))
    path_aliases = list(normalization.get("path_aliases", []))
    index = {(ep.method.upper(), ep.match_path): ep for ep in endpoints}
    audit: list[str] = []
    allowed = {"path", "service", "name", "description", "auth_type", "status", "confidence"}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row_number, row in enumerate(csv.DictReader(handle), 2):
            method = str(row.get("method", "")).upper().strip()
            raw_path = str(row.get("normalized_path", "")).strip()
            field = str(row.get("field", "")).strip()
            value = str(row.get("value", "")).strip()
            reason = str(row.get("reason", "")).strip()
            if not method or not raw_path or not field or method.startswith("#"):
                continue
            key = (method, normalize_match_path(raw_path, strip_prefixes, path_aliases))
            endpoint = index.get(key)
            if endpoint is None:
                audit.append(f"Override row {row_number} did not match an endpoint: {method} {raw_path}")
                continue
            if field not in allowed:
                audit.append(f"Override row {row_number} ignored unsupported field: {field}")
                continue
            if not reason:
                audit.append(f"Override row {row_number} ignored because reason is blank")
                continue
            setattr(endpoint, field, value)
            if field == "auth_type":
                endpoint.conflicts = [item for item in endpoint.conflicts if not item.startswith("Authentication evidence differs")]
            if not endpoint.conflicts and endpoint.status == "CONFLICT":
                endpoint.status = "PARTIAL"
            audit.append(f"Applied override row {row_number}: {endpoint.endpoint_id}.{field}={value} ({reason})")
    return audit
