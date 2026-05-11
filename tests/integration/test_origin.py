"""Loopback / Host / Origin enforcement (BUILD_SPEC §14.3, BS-16.5)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from redact_ai.server.app import build_app


def _client() -> TestClient:
    app = build_app(port=22222)
    return TestClient(app, base_url="http://127.0.0.1:22222")


def test_host_loopback_allowed() -> None:
    client = _client()
    response = client.get("/healthz", headers={"Host": "127.0.0.1:22222"})
    assert response.status_code == 200


def test_host_evil_rejected() -> None:
    client = _client()
    response = client.get("/healthz", headers={"Host": "evil.example"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "E_ORIGIN"


def test_origin_evil_rejected() -> None:
    client = _client()
    response = client.get(
        "/healthz",
        headers={
            "Host": "127.0.0.1:22222",
            "Origin": "http://attacker.example",
        },
    )
    assert response.status_code == 403


def test_origin_localhost_allowed() -> None:
    client = _client()
    response = client.get(
        "/healthz",
        headers={
            "Host": "127.0.0.1:22222",
            "Origin": "http://127.0.0.1:22222",
        },
    )
    assert response.status_code == 200
