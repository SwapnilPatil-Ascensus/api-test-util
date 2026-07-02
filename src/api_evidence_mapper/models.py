from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Evidence:
    source_type: str
    source_name: str
    location: str
    method: str
    path: str
    description: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    query: dict[str, str] = field(default_factory=dict)
    body: Any = None
    auth_type: str = "unknown"
    service: str = "unclassified"
    operation_name: str = ""
    raw_url: str = ""
    line: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CanonicalEndpoint:
    endpoint_id: str
    method: str
    path: str
    match_path: str
    service: str
    name: str
    description: str
    auth_type: str
    headers: dict[str, str]
    query: dict[str, str]
    body: Any
    source_types: list[str]
    evidence: list[Evidence]
    status: str
    confidence: str
    conflicts: list[str] = field(default_factory=list)
    required_variables: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["evidence"] = [item.to_dict() for item in self.evidence]
        return result
