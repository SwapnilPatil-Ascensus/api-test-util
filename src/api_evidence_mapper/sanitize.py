from __future__ import annotations

import copy
import re
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

SENSITIVE_HEADER_NAMES = {"authorization", "cookie", "set-cookie", "proxy-authorization", "x-api-key"}
SENSITIVE_KEY_RE = re.compile(
    r"password|passwd|token|secret|api[-_]?key|session|ssn|account(?:[-_ ]?(?:number|no|id))?|routing(?:[-_ ]?(?:number|no))?|email|phone|address|dob|birth|member[-_ ]?id|user[-_ ]?id|customer[-_ ]?id",
    re.I,
)
IDENTIFIER_KEY_RE = re.compile(r"(?:^|[_-])(id|ids)$|Id$|ID$", re.I)
SAFE_ENV_KEY_RE = re.compile(r"url|uri|host|base|version|environment|env|brand|state|locale|language|content[-_]?type", re.I)
BEARER_RE = re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+\-/]+=*")
JWT_RE = re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
PRIVATE_KEY_RE = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")


def sanitize_scalar(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    value = BEARER_RE.sub("Bearer <REDACTED>", value)
    value = JWT_RE.sub("<REDACTED_JWT>", value)
    if PRIVATE_KEY_RE.search(value):
        return "<REDACTED_PRIVATE_KEY>"
    return value


def sanitize_object(value: Any, report: list[str], path: str = "$") -> Any:
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if SENSITIVE_KEY_RE.search(str(key)) or IDENTIFIER_KEY_RE.search(str(key)):
                result[key] = f"{{{{{variable_name(str(key))}}}}}"
                report.append(f"Parameterised sensitive or identifier key at {path}.{key}")
            else:
                result[key] = sanitize_object(item, report, f"{path}.{key}")
        return result
    if isinstance(value, list):
        return [sanitize_object(item, report, f"{path}[{index}]") for index, item in enumerate(value)]
    clean = sanitize_scalar(value)
    if clean != value:
        report.append(f"Redacted token-like value at {path}")
    return clean


def variable_name(key_hint: str | None) -> str:
    if not key_hint:
        return "value"
    clean = re.sub(r"[^A-Za-z0-9_]+", "_", key_hint).strip("_") or "value"
    return clean[0].lower() + clean[1:]


def template_payload(value: Any, report: list[str], path: str = "$", key_hint: str | None = None) -> Any:
    """Convert observed HAR payload values into a non-sensitive variable template while preserving shape."""
    if isinstance(value, dict):
        return {key: template_payload(item, report, f"{path}.{key}", str(key)) for key, item in value.items()}
    if isinstance(value, list):
        if not value:
            return []
        report.append(f"Collapsed observed array to one template item at {path}")
        return [template_payload(value[0], report, f"{path}[0]", key_hint)]
    if value is None or isinstance(value, bool):
        return value
    clean = sanitize_scalar(value)
    if clean != value:
        report.append(f"Redacted token-like payload value at {path}")
        return clean
    variable = variable_name(key_hint)
    report.append(f"Replaced observed payload value with {{{{{variable}}}}} at {path}")
    return f"{{{{{variable}}}}}"


def sanitize_url_query(url: str, report: list[str], source: str) -> tuple[str, dict[str, str]]:
    parsed = urlsplit(url)
    query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
    templated: dict[str, str] = {}
    for key, _ in query_pairs:
        variable = variable_name(key)
        templated[key] = f"{{{{{variable}}}}}"
        report.append(f"Replaced observed query value with {{{{{variable}}}}} in {source}")
    safe_url = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(templated, doseq=False), ""))
    return safe_url, templated


def sanitize_environment_value(key: str, value: Any, declared_type: str = "") -> tuple[str, bool, str | None]:
    text = "" if value is None else str(value)
    lower = text.lower()
    if declared_type.lower() == "secret" or SENSITIVE_KEY_RE.search(key) or IDENTIFIER_KEY_RE.search(key):
        return "", True, "sensitive-or-identifier"
    if BEARER_RE.search(text) or JWT_RE.search(text) or PRIVATE_KEY_RE.search(text):
        return "", True, "token-like"
    if any(token in lower for token in ("stage1", "stage-1", "stage_1")):
        return "", False, "stage1-prohibited"
    if SAFE_ENV_KEY_RE.search(key):
        return sanitize_scalar(text), False, None
    if text.lower() in {"true", "false"} or (0 < len(text) <= 32 and re.fullmatch(r"[A-Za-z0-9_.-]+", text or "")):
        return text, False, None
    return "", False, "value-blanked-by-default"


def sanitize_har_entry(entry: dict[str, Any], include_sensitive_headers: bool = False) -> tuple[dict[str, Any], list[str]]:
    clone = copy.deepcopy(entry)
    report: list[str] = []
    request = clone.get("request", {})
    headers = request.get("headers", [])
    clean_headers = []
    for header in headers:
        name = str(header.get("name", ""))
        if name.lower() in SENSITIVE_HEADER_NAMES and not include_sensitive_headers:
            clean_headers.append({"name": name, "value": "<REDACTED>"})
            report.append(f"Redacted request header: {name}")
        else:
            clean_headers.append({"name": name, "value": sanitize_scalar(header.get("value", ""))})
    request["headers"] = clean_headers
    if "postData" in request:
        request["postData"] = sanitize_object(request["postData"], report, "$.request.postData")
    clone["request"] = request
    if "response" in clone:
        clone["response"] = {"status": clone["response"].get("status"), "statusText": clone["response"].get("statusText", "")}
    return clone, report
