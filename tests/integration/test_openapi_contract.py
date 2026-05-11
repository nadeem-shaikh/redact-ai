"""OpenAPI contract test (BUILD_SPEC §8.5)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from redact_ai.server.app import build_app


def test_openapi_paths() -> None:
    client = TestClient(build_app(port=44444), base_url="http://127.0.0.1:44444")
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    paths = spec["paths"]
    assert "/redact" in paths
    assert "post" in paths["/redact"]
    assert "/healthz" in paths
    assert "/policies" in paths


def test_openapi_redact_accepts_multipart() -> None:
    client = TestClient(build_app(port=44445), base_url="http://127.0.0.1:44445")
    spec = client.get("/openapi.json").json()
    post = spec["paths"]["/redact"]["post"]
    request_body = post["requestBody"]["content"]
    assert "multipart/form-data" in request_body
