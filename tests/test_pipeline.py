from pathlib import Path

from api_evidence_mapper.config import load_config
from api_evidence_mapper.discovery import parse_har, parse_postman, scan_repository
from api_evidence_mapper.pipeline import run_all
from api_evidence_mapper.reconcile import reconcile

ROOT = Path(__file__).resolve().parents[1]


def test_repository_and_postman_discovery():
    cfg = load_config(ROOT / "fixtures/project.fixture.toml")
    evidence = []
    for repo in cfg.repositories:
        evidence.extend(scan_repository(repo))
    postman, _ = parse_postman(ROOT / "fixtures/partial.postman_collection.json")
    evidence.extend(postman)
    har, report = parse_har(ROOT / "fixtures/qc4-sanitized.har")
    evidence.extend(har)
    assert any(item.path == "/mobile2api/v1/plans" and item.method == "GET" for item in evidence)
    assert any(item.path.endswith("/{{observedId1}}") for item in har)
    assert report
    endpoints = reconcile(evidence)
    assert len(endpoints) >= 2


def test_end_to_end_fixture_generation(tmp_path):
    cfg_path = ROOT / "fixtures/project.fixture.toml"
    cfg = load_config(cfg_path)
    cfg.raw["output_root"] = str(tmp_path)
    result = run_all(cfg)
    output = Path(result["output"])
    assert (output / "mapping/endpoint_migration_matrix.csv").exists()
    assert (output / "mapping/endpoint_migration_matrix.xlsx").exists()
    assert (output / "postman/fixture-mobile.postman_collection.json").exists()
    assert (output / "reports/FINAL-SUMMARY.md").exists()
