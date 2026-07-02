from api_evidence_mapper.normalize import canonicalize_path, normalize_match_path, split_url


def test_path_normalization():
    assert normalize_match_path("/plans/{planId}") == "/plans/{param}"
    assert normalize_match_path("/plans/123") == "/plans/{param}"


def test_split_url():
    path, query = split_url("{{baseUrl}}/plans?active=true")
    assert path == "/plans"
    assert query == {"active": "true"}


def test_gateway_alias_and_prefix_normalization():
    aliases = [{"from": "/mobile-bff/api", "to": "/mobile2api"}]
    assert canonicalize_path("/mobile-bff/api/v1/plans/42", path_aliases=aliases) == "/mobile2api/v1/plans/42"
    assert normalize_match_path("/gateway/mobile2api/v1/plans/42", ["/gateway"], []) == "/mobile2api/v1/plans/{param}"
