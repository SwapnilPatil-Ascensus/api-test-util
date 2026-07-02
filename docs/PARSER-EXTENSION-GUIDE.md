# Parser Extension Guide

The built-in scanner recognizes common patterns from:

- Spring MVC and Kotlin/Java annotations,
- JAX-RS,
- FastAPI/Flask-style Python decorators,
- Express-style JavaScript/TypeScript routes,
- ASP.NET attributes,
- common HTTP client/test calls including REST Assured-like `.get()` and `.post()` calls,
- Postman Collection v2.x,
- Postman environments,
- HAR 1.2 request entries,
- OpenAPI/Swagger YAML or JSON.

## Add a project-specific regex without changing Python

Add an array entry to `config/project.toml`:

```toml
[[custom_patterns]]
name = "company-http-annotation"
extensions = [".java"]
regex = '''@HttpEndpoint\(method\s*=\s*"(GET|POST|PUT|PATCH|DELETE)",\s*path\s*=\s*"([^"]+)"'''
method_group = 1
path_group = 2
description = "Company-specific endpoint annotation"
```

Use `fixed_method = "GET"` when the regex captures only a path. Add `service = "service-name"` only when path-based service inference is wrong.

## When code changes are justified

Change the parser code only when the project uses a structured framework that cannot be represented reliably by one regex. Add a focused parser and fixture, then run all tests. Do not add broad regexes that interpret arbitrary strings as endpoints.

## Required parser fixture

Every new parser must include:

1. one positive endpoint,
2. one non-endpoint string that must not be detected,
3. a parameterized path,
4. auth or payload clue when applicable,
5. a unit test showing the expected canonical endpoint count.
