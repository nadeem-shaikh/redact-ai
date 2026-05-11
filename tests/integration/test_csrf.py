"""CSRF token enforcement (BUILD_SPEC §14.2, BS-16.5)."""

from __future__ import annotations

import io

from fastapi.testclient import TestClient
from PIL import Image

from redact_ai.server.app import build_app
from redact_ai.server.csrf import COOKIE_NAME


def _png_bytes() -> bytes:
    img = Image.new("RGB", (200, 60), "white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _client() -> TestClient:
    app = build_app(port=12345)
    return TestClient(app, base_url="http://127.0.0.1:12345")


def test_missing_csrf_rejected() -> None:
    client = _client()
    response = client.post(
        "/redact",
        files={"image": ("x.png", _png_bytes(), "image/png")},
        data={"policy_id": "default"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "E_CSRF"


def test_mismatched_csrf_rejected() -> None:
    client = _client()
    client.cookies.set(COOKIE_NAME, "expected")
    response = client.post(
        "/redact",
        files={"image": ("x.png", _png_bytes(), "image/png")},
        headers={"X-Redact-CSRF": "wrong"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "E_CSRF"


def test_index_sets_csrf_cookie_and_meta() -> None:
    client = _client()
    response = client.get("/")
    assert response.status_code == 200
    assert COOKIE_NAME in response.cookies
    assert 'meta name="rai-csrf"' in response.text


def test_csrf_round_trip_allows_upload() -> None:
    client = _client()
    client.get("/")
    token = client.cookies.get(COOKIE_NAME)
    response = client.post(
        "/redact",
        files={"image": ("x.png", _png_bytes(), "image/png")},
        headers={"X-Redact-CSRF": token or ""},
    )
    # Accept either a redacted image or a JSON envelope. The point is
    # not 403/E_CSRF.
    assert response.status_code != 403
