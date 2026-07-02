from __future__ import annotations

import argparse
import csv
import json
import re
from urllib.parse import urlsplit

from api_evidence_mapper.config import load_config
from api_evidence_mapper.normalize import normalize_match_path

SECRET_PATTERNS = [
    re.compile(r"Bearer\s+eyJ[A-Za-z0-9_-]+\.", re.I),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]
VARIABLE_RE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_.-]*)\s*\}\}")


def walk_requests(items: list[dict]) -> list[dict]:
    requests: list[dict] = []
    for item in items:
        if "item" in item:
            requests.extend(walk_requests(item.get("item", [])))
        elif "request" in item:
            requests.append(item)
    return requests


def request_key(item: dict) -> tuple[str, str]:
    request = item.get("request", {})
    method = str(request.get("method", "")).upper()
    url = request.get("url", {})
    raw = str(url.get("raw", "")) if isinstance(url, dict) else str(url)
    raw_without_base = re.sub(r"^\{\{[^}]+\}\}", "", raw)
    path = urlsplit("https://placeholder.invalid" + raw_without_base).path
    return method, normalize_match_path(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate generated offline distribution artifacts")
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    cfg = load_config(args.config)
    root = cfg.output_dir
    required = [
        root / "inventory/endpoint_inventory.json",
        root / "inventory/endpoint_inventory.csv",
        root / "mapping/endpoint_migration_matrix.csv",
        root / "mapping/endpoint_migration_matrix.xlsx",
        root / "mapping/variable_dictionary.csv",
        root / f"postman/{cfg.project_id}.postman_collection.json",
        root / f"postman/{cfg.project_id}-qc4.postman_environment.json",
        root / "reports/VALIDATION-REPORT.md",
        root / "reports/FINAL-SUMMARY.md",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit("Missing required artifacts:\n" + "\n".join(missing))

    collection_path = root / f"postman/{cfg.project_id}.postman_collection.json"
    environment_path = root / f"postman/{cfg.project_id}-qc4.postman_environment.json"
    collection_text = collection_path.read_text(encoding="utf-8")
    environment_text = environment_path.read_text(encoding="utf-8")
    collection = json.loads(collection_text)
    environment = json.loads(environment_text)

    if cfg.raw.get("strict_qc4_only", False):
        combined = (collection_text + environment_text).lower()
        if any(token in combined for token in ("stage1", "stage-1", "stage_1")):
            raise SystemExit("Stage1 reference detected while strict_qc4_only=true")
        if "qc4" not in str(environment.get("name", "")).lower():
            raise SystemExit("Generated environment is not explicitly named QC4")

    environment_keys: set[str] = set()
    for item in environment.get("values", []):
        key = str(item.get("key", "")).strip()
        value = str(item.get("value", ""))
        if not key:
            raise SystemExit("Environment contains a blank variable key")
        if key in environment_keys:
            raise SystemExit(f"Duplicate environment variable: {key}")
        environment_keys.add(key)
        if item.get("type") == "secret" and value:
            raise SystemExit(f"Secret environment variable contains a value: {key}")
        if "REPLACE" in value.upper() or "TODO" in value.upper():
            raise SystemExit(f"Environment variable still contains a configuration placeholder: {key}")

    if "/v2.1.0/" not in collection.get("info", {}).get("schema", ""):
        raise SystemExit("Collection schema is not v2.1")

    collection_keys = {str(item.get("key", "")) for item in collection.get("variable", []) if item.get("key")}
    available_variables = environment_keys | collection_keys
    requests = walk_requests(collection.get("item", []))
    if not requests:
        raise SystemExit("Collection contains no requests")

    seen: set[tuple[str, str]] = set()
    duplicate_keys: list[str] = []
    for item in requests:
        key = request_key(item)
        if key in seen:
            duplicate_keys.append(f"{key[0]} {key[1]}")
        seen.add(key)
        request = item.get("request", {})
        if not str(request.get("description", "")).strip():
            raise SystemExit(f"Request has no description: {item.get('name', '<unnamed>')}")
        if "Evidence:" not in str(request.get("description", "")):
            raise SystemExit(f"Request description lacks evidence provenance: {item.get('name', '<unnamed>')}")
    if duplicate_keys:
        raise SystemExit("Duplicate normalized requests detected:\n" + "\n".join(sorted(set(duplicate_keys))))

    referenced_variables = set(VARIABLE_RE.findall(collection_text))
    unresolved = sorted(referenced_variables - available_variables)
    if unresolved:
        raise SystemExit("Variables referenced by collection but absent from collection/environment scopes: " + ", ".join(unresolved))

    mapping_path = root / "mapping/endpoint_migration_matrix.csv"
    with mapping_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(requests) != len(rows):
        raise SystemExit(f"Mapping/collection count mismatch: mapping={len(rows)} collection={len(requests)}")
    if any(not row.get("evidence_locations", "").strip() for row in rows):
        raise SystemExit("One or more mapping rows lack evidence locations")

    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() in {".xlsx", ".png", ".pdf"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                raise SystemExit(f"Possible secret detected in {path}: {pattern.pattern}")

    print(
        json.dumps(
            {
                "valid": True,
                "root": str(root),
                "endpoint_count": len(rows),
                "request_count": len(requests),
                "referenced_variable_count": len(referenced_variables),
                "required_artifacts": len(required),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
