from __future__ import annotations

import hashlib
import json
import re
from urllib.parse import parse_qsl, urlsplit

UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$")
INTEGER_RE = re.compile(r"^\d+$")
PATH_VAR_RE = re.compile(r"(?:\{\{?[^/{}]+\}\}?|:[A-Za-z_][A-Za-z0-9_]*)")
SECRET_KEY_RE = re.compile(r"authorization|cookie|token|password|secret|api[-_]?key|session", re.I)


def split_url(value: str) -> tuple[str, dict[str, str]]:
    if not value:
        return "/", {}
    expanded = value.replace("{{baseUrl}}", "https://placeholder.invalid")
    if expanded.startswith("/"):
        expanded = "https://placeholder.invalid" + expanded
    parsed = urlsplit(expanded)
    path = parsed.path or "/"
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    return path, query


def canonicalize_path(
    path: str,
    strip_prefixes: list[str] | tuple[str, ...] | None = None,
    path_aliases: list[dict[str, str]] | None = None,
) -> str:
    """Apply configured gateway/BFF aliases without changing the source evidence."""
    result = "/" + path.lstrip("/")
    for alias in sorted(path_aliases or [], key=lambda item: len(str(item.get("from", ""))), reverse=True):
        source = "/" + str(alias.get("from", "")).strip("/")
        target = "/" + str(alias.get("to", "")).strip("/")
        if source == "/" or not str(alias.get("from", "")).strip():
            continue
        if result == source or result.startswith(source + "/"):
            suffix = result[len(source):]
            result = (target.rstrip("/") + suffix) or "/"
            break
    for prefix_value in sorted(strip_prefixes or [], key=len, reverse=True):
        prefix = "/" + str(prefix_value).strip("/")
        if prefix == "/":
            continue
        if result == prefix:
            result = "/"
            break
        if result.startswith(prefix + "/"):
            result = result[len(prefix):] or "/"
            break
    return "/" + result.lstrip("/")


def normalize_match_path(
    path: str,
    strip_prefixes: list[str] | tuple[str, ...] | None = None,
    path_aliases: list[dict[str, str]] | None = None,
) -> str:
    path = canonicalize_path(path, strip_prefixes, path_aliases)
    parts = []
    for segment in path.split("/"):
        if not segment:
            continue
        if PATH_VAR_RE.fullmatch(segment):
            parts.append("{param}")
        elif UUID_RE.fullmatch(segment):
            parts.append("{param}")
        elif INTEGER_RE.fullmatch(segment):
            parts.append("{param}")
        else:
            parts.append(segment)
    return "/" + "/".join(parts)


def endpoint_id(method: str, match_path: str) -> str:
    digest = hashlib.sha1(f"{method.upper()} {match_path}".encode("utf-8")).hexdigest()[:10]
    return f"EP-{digest.upper()}"


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in headers.items():
        result[key] = "<REDACTED>" if SECRET_KEY_RE.search(key) else value
    return result


def detect_required_variables(value: object) -> list[str]:
    text = json.dumps(value, default=str)
    found = re.findall(r"\{\{\s*([A-Za-z_][A-Za-z0-9_.-]*)\s*\}\}", text)
    return sorted(set(found))


def safe_json_loads(value: str):
    try:
        return json.loads(value)
    except Exception:
        return value


def extract_path_variables(path: str) -> list[str]:
    variables: list[str] = []
    for match in re.finditer(r"\{\{?([A-Za-z_][A-Za-z0-9_.-]*)\}\}?|:([A-Za-z_][A-Za-z0-9_]*)", path):
        variables.append(match.group(1) or match.group(2))
    return sorted(set(variables))


def postmanize_path(path: str) -> str:
    path = re.sub(r"\{\{?([A-Za-z_][A-Za-z0-9_.-]*)\}\}?", r"{{\1}}", path)
    path = re.sub(r":([A-Za-z_][A-Za-z0-9_]*)", r"{{\1}}", path)
    return path


def sanitize_concrete_path(path: str) -> str:
    parts = []
    counter = 1
    for segment in path.split("/"):
        if UUID_RE.fullmatch(segment) or INTEGER_RE.fullmatch(segment):
            parts.append(f"{{{{observedId{counter}}}}}")
            counter += 1
        else:
            parts.append(segment)
    return "/".join(parts) or "/"
