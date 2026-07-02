from __future__ import annotations

import fnmatch
import json
import re
from pathlib import Path
from typing import Any, Iterable

from .models import Evidence
from .normalize import safe_json_loads, sanitize_concrete_path, split_url
from .sanitize import (
    IDENTIFIER_KEY_RE,
    SENSITIVE_HEADER_NAMES,
    SENSITIVE_KEY_RE,
    sanitize_environment_value,
    sanitize_har_entry,
    sanitize_object,
    sanitize_scalar,
    sanitize_url_query,
    template_payload,
    variable_name,
)

HTTP_METHODS = "GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS"


def _line_number(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def _clean_literal(value: str) -> str:
    return value.strip().strip('"\'`')


def _join_paths(base: str, child: str) -> str:
    if child.startswith("http://") or child.startswith("https://") or child.startswith("{{"):
        path, _ = split_url(child)
        return path
    return "/" + "/".join(part.strip("/") for part in (base, child) if part and part != "/")


def _operation_after(text: str, index: int) -> str:
    tail = text[index:index + 1200]
    match = re.search(r"(?:public|private|protected|internal)?\s*(?:static\s+)?[A-Za-z0-9_$.<>?,\[\] ]+\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", tail)
    return match.group(1) if match else ""


def _java_spring(text: str, source_name: str, service_name: str, location: str, role: str) -> list[Evidence]:
    results: list[Evidence] = []
    class_base = ""
    class_match = re.search(r"@RequestMapping\s*\(\s*(?:value\s*=\s*|path\s*=\s*)?[\"']([^\"']+)[\"']", text)
    if class_match:
        class_base = class_match.group(1)
    pattern = re.compile(
        r"@(Get|Post|Put|Patch|Delete)Mapping(?:\s*\(\s*(?:value\s*=\s*|path\s*=\s*)?(?:\{\s*)?[\"']([^\"']*)[\"'](?:\s*\})?\s*\))?",
        re.I,
    )
    for match in pattern.finditer(text):
        method = match.group(1).upper()
        child = _clean_literal(match.group(2) or "")
        tail = text[match.end():match.end() + 1400]
        body_match = re.search(r"@RequestBody(?:\s*\([^)]*\))?\s+([A-Za-z0-9_$.<>?,\[\]]+)\s+([A-Za-z_][A-Za-z0-9_]*)", tail)
        metadata: dict[str, Any] = {"parser": "java-spring"}
        if body_match:
            metadata["request_body_type"] = body_match.group(1)
            metadata["request_body_variable"] = body_match.group(2)
        operation = _operation_after(text, match.end()) or f"{method} {child or class_base}"
        results.append(
            Evidence(
                source_type=role,
                source_name=source_name,
                location=location,
                line=_line_number(text, match.start()),
                method=method,
                path=_join_paths(class_base, child),
                operation_name=operation,
                description="Spring route definition",
                service=service_name,
                metadata=metadata,
            )
        )
    return results


def _jax_rs(text: str, source_name: str, service_name: str, location: str, role: str) -> list[Evidence]:
    results: list[Evidence] = []
    base = ""
    class_match = re.search(r"@Path\s*\(\s*[\"']([^\"']+)[\"']\s*\)\s*(?:public\s+)?class", text, re.S)
    if class_match:
        base = class_match.group(1)
    pattern = re.compile(rf"@({HTTP_METHODS})\b(?:(?!@(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)).)*?@Path\s*\(\s*[\"']([^\"']+)[\"']\s*\)", re.S | re.I)
    for match in pattern.finditer(text):
        method = match.group(1).upper()
        child = match.group(3)
        results.append(Evidence(source_type=role, source_name=source_name, location=location, line=_line_number(text, match.start()), method=method, path=_join_paths(base, child), operation_name=_operation_after(text, match.end()) or f"{method} {child}", description="JAX-RS route definition", service=service_name, metadata={"parser": "jax-rs"}))
    return results


def _python_routes(text: str, source_name: str, service_name: str, location: str, role: str) -> list[Evidence]:
    results: list[Evidence] = []
    pattern = re.compile(r"@(?:app|router|bp)\.(get|post|put|patch|delete|head|options)\s*\(\s*[\"']([^\"']+)[\"']", re.I)
    for match in pattern.finditer(text):
        results.append(Evidence(source_type=role, source_name=source_name, location=location, line=_line_number(text, match.start()), method=match.group(1).upper(), path=match.group(2), operation_name=_operation_after(text, match.end()), description="Python web route definition", service=service_name, metadata={"parser": "python-route"}))
    return results


def _javascript_routes(text: str, source_name: str, service_name: str, location: str, role: str) -> list[Evidence]:
    results: list[Evidence] = []
    pattern = re.compile(r"(?:app|router|server)\.(get|post|put|patch|delete|head|options)\s*\(\s*[\"'`]([^\"'`]+)[\"'`]", re.I)
    for match in pattern.finditer(text):
        results.append(Evidence(source_type=role, source_name=source_name, location=location, line=_line_number(text, match.start()), method=match.group(1).upper(), path=match.group(2), description="JavaScript/TypeScript route definition", service=service_name, metadata={"parser": "js-route"}))
    return results


def _dotnet_routes(text: str, source_name: str, service_name: str, location: str, role: str) -> list[Evidence]:
    results: list[Evidence] = []
    class_base = ""
    route = re.search(r"\[Route\(\s*[\"']([^\"']+)[\"']\s*\)\]", text)
    if route:
        class_base = route.group(1).replace("[controller]", "")
    pattern = re.compile(r"\[Http(Get|Post|Put|Patch|Delete|Head|Options)(?:\(\s*[\"']([^\"']*)[\"']\s*\))?\]", re.I)
    for match in pattern.finditer(text):
        method = match.group(1).upper()
        child = match.group(2) or ""
        results.append(Evidence(source_type=role, source_name=source_name, location=location, line=_line_number(text, match.start()), method=method, path=_join_paths(class_base, child), operation_name=_operation_after(text, match.end()), description="ASP.NET route definition", service=service_name, metadata={"parser": "dotnet-route"}))
    return results


def _client_calls(text: str, source_name: str, service_name: str, location: str, role: str) -> list[Evidence]:
    results: list[Evidence] = []
    patterns = [
        re.compile(r"\.(get|post|put|patch|delete|head|options)\s*\(\s*[\"'`]([^\"'`]+)[\"'`]", re.I),
        re.compile(r"fetch\s*\(\s*[\"'`]([^\"'`]+)[\"'`](?:\s*,\s*\{(?:(?!\}\s*\)).)*?method\s*:\s*[\"'](GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)[\"'])?", re.I | re.S),
    ]
    seen = set()
    for pattern in patterns:
        for match in pattern.finditer(text):
            if pattern.pattern.startswith("fetch"):
                url = match.group(1)
                method = (match.group(2) or "GET").upper()
            else:
                method = match.group(1).upper()
                url = match.group(2)
            if not (url.startswith("/") or url.startswith("http") or "{{" in url):
                continue
            path, query = split_url(url)
            path = sanitize_concrete_path(path)
            safe_query = {}
            for query_key, query_value in query.items():
                if "{{" in str(query_value):
                    safe_query[query_key] = str(query_value)
                else:
                    safe_query[query_key] = f"{{{{{variable_name(query_key)}}}}}"
            query = safe_query
            key = (method, path, match.start())
            if key in seen:
                continue
            seen.add(key)
            context = text[max(0, match.start() - 1600):match.end() + 500]
            auth_type = "bearer" if re.search(r"Authorization|Bearer", context, re.I) else "unknown"
            method_name = ""
            before = text[max(0, match.start() - 700):match.start()]
            method_match = list(re.finditer(r"(?:public|private|protected)?\s*(?:void|[A-Za-z0-9_<>?,\[\] ]+)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\([^)]*\)\s*\{", before))
            if method_match:
                method_name = method_match[-1].group(1)
            metadata: dict[str, Any] = {"parser": "generic-client-call"}
            body_matches = list(re.finditer(r"\.body\s*\(\s*([^\n;]+?)\s*\)", context, re.S))
            if body_matches:
                expression = body_matches[-1].group(1).strip()
                metadata["request_body_expression"] = "inline literal (redacted)" if expression.startswith(("\"", "'")) else sanitize_scalar(expression)[:300]
            results.append(Evidence(source_type=role, source_name=source_name, location=location, line=_line_number(text, match.start()), method=method, path=path, raw_url=path, query=query, description="HTTP client/test call", auth_type=auth_type, service=service_name, operation_name=method_name, metadata=metadata))
    return results



def _custom_pattern_evidence(text: str, source_name: str, service_name: str, location: str, role: str, suffix: str, patterns: list[dict[str, Any]]) -> list[Evidence]:
    results: list[Evidence] = []
    for pattern in patterns:
        extensions = {str(item).lower() for item in pattern.get("extensions", [])}
        if extensions and suffix not in extensions:
            continue
        expression = str(pattern.get("regex", ""))
        if not expression:
            continue
        try:
            compiled = re.compile(expression, re.I | re.M)
        except re.error:
            continue
        method_group = int(pattern.get("method_group", 1))
        path_group = int(pattern.get("path_group", 2))
        fixed_method = str(pattern.get("fixed_method", "")).upper()
        for match in compiled.finditer(text):
            try:
                method = fixed_method or str(match.group(method_group)).upper()
                path_value = str(match.group(path_group))
            except (IndexError, TypeError):
                continue
            if method not in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}:
                continue
            results.append(Evidence(source_type=role, source_name=source_name, location=location, line=_line_number(text, match.start()), method=method, path=path_value, operation_name=str(pattern.get("name", "custom route")), description=str(pattern.get("description", "Custom configured route pattern")), service=str(pattern.get("service", service_name)), metadata={"parser": f"custom:{pattern.get('name', 'unnamed')}"}))
    return results

def parse_code_file(path: Path, repo_name: str, role: str, service_name: str | None = None, custom_patterns: list[dict[str, Any]] | None = None) -> list[Evidence]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    location = str(path)
    suffix = path.suffix.lower()
    service = service_name or repo_name
    results: list[Evidence] = []
    if suffix in {".java", ".kt"}:
        results.extend(_java_spring(text, repo_name, service, location, role))
        results.extend(_jax_rs(text, repo_name, service, location, role))
    if suffix == ".py":
        results.extend(_python_routes(text, repo_name, service, location, role))
    if suffix in {".js", ".ts", ".jsx", ".tsx"}:
        results.extend(_javascript_routes(text, repo_name, service, location, role))
    if suffix == ".cs":
        results.extend(_dotnet_routes(text, repo_name, service, location, role))
    results.extend(_client_calls(text, repo_name, service, location, role))
    results.extend(_custom_pattern_evidence(text, repo_name, service, location, role, suffix, custom_patterns or []))
    return results


def _matches(path: Path, root: Path, includes: list[str], excludes: list[str]) -> bool:
    relative = path.relative_to(root).as_posix()
    if excludes and any(fnmatch.fnmatch(relative, pattern) for pattern in excludes):
        return False
    return not includes or any(fnmatch.fnmatch(relative, pattern) for pattern in includes)


def _infer_service(root: Path, path: Path, repo_name: str) -> str:
    parts = path.relative_to(root).parts
    if "src" in parts:
        index = parts.index("src")
        if index > 0:
            candidate = parts[index - 1]
            if candidate.lower() not in {"main", "test", "java", "python"}:
                return candidate
    for marker in ("services", "microservices", "modules", "apps"):
        if marker in parts:
            index = parts.index(marker)
            if index + 1 < len(parts):
                return parts[index + 1]
    return repo_name


def scan_repository(repo: dict, max_file_size: int = 2_000_000, custom_patterns: list[dict[str, Any]] | None = None) -> list[Evidence]:
    root = Path(str(repo["path"])).resolve()
    includes = list(repo.get("include", []))
    excludes = list(repo.get("exclude", []))
    repo_name = str(repo.get("name", root.name))
    role = str(repo.get("role", "repository"))
    results: list[Evidence] = []
    ignored_parts = {".git", ".venv", "node_modules", "target", "build", "dist", "vendor", "coverage", "generated"}
    for path in root.rglob("*"):
        if ignored_parts.intersection(path.relative_to(root).parts):
            continue
        if not path.is_file() or not _matches(path, root, includes, excludes):
            continue
        try:
            if path.stat().st_size > max_file_size:
                continue
        except OSError:
            continue
        results.extend(parse_code_file(path, repo_name, role, _infer_service(root, path, repo_name), custom_patterns))
    return results


def _safe_query_from_postman(query_items: list[dict], report: list[str], location: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in query_items:
        if item.get("disabled"):
            continue
        key = str(item.get("key", ""))
        value = str(item.get("value", ""))
        if "{{" in value:
            result[key] = value
        else:
            result[key] = f"{{{{{variable_name(key)}}}}}"
            report.append(f"Parameterised concrete Postman query value for {key} at {location}")
    return result



def _sanitize_postman_body(body: dict[str, Any], report: list[str], location: str) -> dict[str, Any]:
    clean = dict(body)
    mode = str(clean.get("mode", ""))
    if mode == "raw":
        raw = str(clean.get("raw", ""))
        parsed = safe_json_loads(raw)
        if isinstance(parsed, (dict, list)):
            templated = template_payload(parsed, report, f"postman:{location}.body")
            clean["raw"] = json.dumps(templated, indent=2)
        elif raw and "{{" not in raw:
            clean["raw"] = "{{rawRequestBody}}"
            report.append(f"Replaced non-JSON Postman raw body with variable at {location}")
    elif mode in {"urlencoded", "formdata"}:
        entries = []
        for entry in clean.get(mode, []):
            item = dict(entry)
            key = str(item.get("key", "field"))
            if item.get("type") == "file":
                item.pop("src", None)
                item["src"] = "{{requestFilePath}}"
            elif "{{" not in str(item.get("value", "")):
                item["value"] = f"{{{{{variable_name(key)}}}}}"
            entries.append(item)
        clean[mode] = entries
    else:
        clean = sanitize_object(clean, report, f"postman:{location}.body")
    return clean


def _summarize_postman_events(events: list[dict]) -> dict[str, Any]:
    scripts: list[str] = []
    for event in events or []:
        script = event.get("script", {}) if isinstance(event, dict) else {}
        executable = script.get("exec", []) if isinstance(script, dict) else []
        if isinstance(executable, str):
            scripts.append(executable)
        else:
            scripts.extend(str(line) for line in executable)
    text = "\n".join(scripts)
    sets = sorted(set(re.findall(r"pm\.(?:environment|collectionVariables|variables)\.set\(\s*[\"']([^\"']+)", text)))
    reads = sorted(set(re.findall(r"pm\.(?:environment|collectionVariables|variables)\.get\(\s*[\"']([^\"']+)", text)))
    return {"script_count": len(events or []), "script_sets": sets, "script_reads": reads}

def _flatten_postman_items(items: list[dict], source_name: str, sanitization: list[str], prefix: str = "") -> Iterable[Evidence]:
    for item in items:
        name = str(item.get("name", "Unnamed request"))
        folder = f"{prefix}/{name}".strip("/")
        if "item" in item:
            yield from _flatten_postman_items(item.get("item", []), source_name, sanitization, folder)
            continue
        request = item.get("request", {})
        method = str(request.get("method", "GET")).upper()
        url = request.get("url", {})
        raw_url = url.get("raw", "") if isinstance(url, dict) else str(url)
        path, query = split_url(raw_url)
        path = sanitize_concrete_path(path)
        if isinstance(url, dict):
            query = _safe_query_from_postman(url.get("query", []), sanitization, folder)
        else:
            query = {
                key: value if "{{" in str(value) else f"{{{{{variable_name(key)}}}}}"
                for key, value in query.items()
            }
            if query:
                sanitization.append(f"Parameterised concrete Postman query values at {folder}")
        headers = {}
        for header in request.get("header", []):
            if header.get("disabled"):
                continue
            key = str(header.get("key", ""))
            value = str(header.get("value", ""))
            if key.lower() in SENSITIVE_HEADER_NAMES:
                headers[key] = "<REDACTED>"
                sanitization.append(f"Redacted Postman header {key} at {folder}")
            elif SENSITIVE_KEY_RE.search(key) or IDENTIFIER_KEY_RE.search(key):
                headers[key] = f"{{{{{variable_name(key)}}}}}"
                sanitization.append(f"Parameterised Postman header {key} at {folder}")
            else:
                headers[key] = sanitize_scalar(value)
        body = request.get("body")
        if body:
            body_report: list[str] = []
            body = _sanitize_postman_body(body, body_report, folder)
            sanitization.extend(body_report)
        description = request.get("description", item.get("description", ""))
        if isinstance(description, dict):
            description = description.get("content", "")
        auth = request.get("auth", {}) or {}
        auth_type = str(auth.get("type", "unknown"))
        yield Evidence(source_type="postman", source_name=source_name, location=folder, method=method, path=path, raw_url=path, query=query, headers=headers, body=body, auth_type=auth_type, operation_name=name, description=str(description), service=prefix.split("/")[0] if prefix else "postman", metadata=_summarize_postman_events(item.get("event", [])))


def _read_json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def parse_postman(path: str | Path) -> tuple[list[Evidence], list[str]]:
    file_path = Path(path)
    data = _read_json_file(file_path)
    source_name = str(data.get("info", {}).get("name", file_path.name))
    sanitization: list[str] = []
    return list(_flatten_postman_items(data.get("item", []), source_name, sanitization)), sanitization


def parse_postman_environment(path: str | Path) -> tuple[list[dict[str, Any]], list[str]]:
    file_path = Path(path)
    data = _read_json_file(file_path)
    values: list[dict[str, Any]] = []
    report: list[str] = []
    for item in data.get("values", []):
        if item.get("enabled") is False:
            continue
        key = str(item.get("key", ""))
        value, sensitive, reason = sanitize_environment_value(key, item.get("value", ""), str(item.get("type", "")))
        values.append({"key": key, "value": value, "sensitive": sensitive, "source": file_path.name})
        if reason:
            report.append(f"Environment {file_path.name}: {key} -> {reason}")
    return values, report


def parse_har(path: str | Path, include_sensitive_headers: bool = False) -> tuple[list[Evidence], list[str]]:
    file_path = Path(path)
    data = _read_json_file(file_path)
    results: list[Evidence] = []
    sanitization: list[str] = []
    for index, original in enumerate(data.get("log", {}).get("entries", [])):
        entry, report = sanitize_har_entry(original, include_sensitive_headers)
        request = entry.get("request", {})
        method = str(request.get("method", "GET")).upper()
        original_url = str(request.get("url", ""))
        safe_url, query = sanitize_url_query(original_url, report, f"{file_path.name} entry {index}")
        path_value, _ = split_url(safe_url)
        path_value = sanitize_concrete_path(path_value)
        headers = {str(h.get("name")): str(h.get("value", "")) for h in request.get("headers", [])}
        post_data = request.get("postData", {})
        body = None
        if post_data:
            parsed = safe_json_loads(str(post_data.get("text", "")))
            body = template_payload(parsed, report, f"{file_path.name}.entry[{index}].request.body")
        sanitization.extend(f"{file_path.name} entry {index}: {line}" for line in report)
        safe_raw_url = path_value
        if query:
            safe_raw_url += "?" + "&".join(f"{key}={value}" for key, value in sorted(query.items()))
        results.append(Evidence(source_type="har", source_name=file_path.name, location=f"entry[{index}]", method=method, path=path_value, raw_url=safe_raw_url, query=query, headers=headers, body=body, auth_type="bearer" if any(k.lower() == "authorization" for k in headers) else "unknown", operation_name=f"{method} {path_value}", description="Observed client request from sanitized HAR", metadata={"status": entry.get("response", {}).get("status")}))
    return results, sanitization


def parse_openapi(path: str | Path) -> list[Evidence]:
    import yaml

    file_path = Path(path)
    data = yaml.safe_load(file_path.read_text(encoding="utf-8"))
    results: list[Evidence] = []
    for api_path, operations in (data.get("paths", {}) or {}).items():
        for method, operation in (operations or {}).items():
            if method.upper() not in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}:
                continue
            operation = operation or {}
            results.append(Evidence(source_type="openapi", source_name=file_path.name, location=f"paths.{api_path}.{method}", method=method.upper(), path=str(api_path), operation_name=str(operation.get("operationId", "")), description=str(operation.get("summary", operation.get("description", ""))), service=(operation.get("tags") or ["openapi"])[0], auth_type="configured" if operation.get("security") else "unknown", metadata={"parameters": operation.get("parameters", []), "requestBody": operation.get("requestBody")}))
    return results
