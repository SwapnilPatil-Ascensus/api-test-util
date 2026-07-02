import json
from pathlib import Path

from api_evidence_mapper.config import configuration_issues, load_config
from api_evidence_mapper.discovery import parse_code_file, parse_postman_environment
from api_evidence_mapper.pipeline import run_all

ROOT = Path(__file__).resolve().parents[1]


def test_postman_environment_values_are_sanitized():
    values, report = parse_postman_environment(ROOT / "fixtures/partial-qc4.postman_environment.json")
    by_key = {item["key"]: item for item in values}
    assert by_key["accessToken"]["value"] == ""
    assert by_key["accessToken"]["sensitive"] is True
    assert by_key["memberId"]["value"] == ""
    assert by_key["brand"]["value"] == "hawaii"
    assert report


def test_custom_pattern_support(tmp_path):
    source = tmp_path / "route.custom"
    source.write_text('@CustomRoute("PATCH", "/api/v2/items/{itemId}")', encoding="utf-8")
    patterns = [{
        "name": "custom-route",
        "extensions": [".custom"],
        "regex": r'@CustomRoute\("(GET|POST|PUT|PATCH|DELETE)",\s*"([^"]+)"\)',
        "method_group": 1,
        "path_group": 2,
    }]
    evidence = parse_code_file(source, "custom-repo", "service_source", "custom-service", patterns)
    assert len(evidence) == 1
    assert evidence[0].method == "PATCH"
    assert evidence[0].path == "/api/v2/items/{itemId}"


def test_generated_collection_parameterizes_route_and_secrets(tmp_path):
    cfg = load_config(ROOT / "fixtures/project.fixture.toml")
    cfg.raw["output_root"] = str(tmp_path)
    result = run_all(cfg)
    output = Path(result["output"])
    collection = json.loads((output / "postman/fixture-mobile.postman_collection.json").read_text(encoding="utf-8"))
    environment = json.loads((output / "postman/fixture-mobile-qc4.postman_environment.json").read_text(encoding="utf-8"))
    urls = []
    for folder in collection["item"]:
        urls.extend(item["request"]["url"]["raw"] for item in folder["item"])
    assert "{{baseUrl}}/mobile2api/v1/plans/{{planId}}" in urls
    secret_values = [item["value"] for item in environment["values"] if item.get("type") == "secret"]
    assert all(value == "" for value in secret_values)


def test_stage1_is_rejected_in_strict_qc4_mode(tmp_path):
    config_path = tmp_path / "project.toml"
    config_path.write_text('project_id="x"\nstrict_qc4_only=true\n[qc4]\ndefault_base_url="https://stage1.example"\n', encoding="utf-8")
    issues = configuration_issues(load_config(config_path))
    assert any("Stage1" in issue for issue in issues)


def test_postman_raw_json_body_is_templated(tmp_path):
    collection_path = tmp_path / "body.postman_collection.json"
    collection_path.write_text(
        json.dumps({
            "info": {"name": "Body fixture"},
            "item": [{
                "name": "Create member",
                "request": {
                    "method": "POST",
                    "url": "https://qc4.example.invalid/members/123?email=user@example.com",
                    "header": [{"key": "x-member-id", "value": "123"}],
                    "body": {"mode": "raw", "raw": json.dumps({"memberId": "123", "email": "user@example.com", "active": True})},
                },
            }],
        }),
        encoding="utf-8",
    )
    from api_evidence_mapper.discovery import parse_postman

    evidence, report = parse_postman(collection_path)
    item = evidence[0]
    assert item.path == "/members/{{observedId1}}"
    assert item.query == {"email": "{{email}}"}
    assert item.headers["x-member-id"] == "{{x_member_id}}"
    assert "123" not in item.body["raw"]
    assert "user@example.com" not in item.body["raw"]
    assert "{{memberId}}" in item.body["raw"]
    assert report


def test_postman_collection_with_utf8_bom_parses(tmp_path):
    collection_path = tmp_path / "bom.postman_collection.json"
    collection_path.write_text(
        json.dumps({
            "info": {"name": "BOM fixture"},
            "item": [{
                "name": "Health",
                "request": {"method": "GET", "url": "https://qc4.example.invalid/health"},
            }],
        }),
        encoding="utf-8-sig",
    )
    from api_evidence_mapper.discovery import parse_postman

    evidence, _ = parse_postman(collection_path)
    assert len(evidence) == 1
    assert evidence[0].method == "GET"
    assert evidence[0].path == "/health"
