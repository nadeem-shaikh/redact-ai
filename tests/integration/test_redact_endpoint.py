"""End-to-end POST /redact tests (BUILD_SPEC §8.1)."""

from __future__ import annotations

import base64
import io
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from redact_ai.server.app import build_app
from redact_ai.server.csrf import COOKIE_NAME

TC_001 = Path(__file__).resolve().parents[1] / "golden" / "inputs" / "TC-001.png"


def _client() -> TestClient:
    app = build_app(port=33333)
    return TestClient(app, base_url="http://127.0.0.1:33333")


def _csrf(client: TestClient) -> str:
    client.get("/")
    return client.cookies.get(COOKIE_NAME) or ""


def test_image_response_default_content_type() -> None:
    client = _client()
    token = _csrf(client)
    response = client.post(
        "/redact",
        files={"image": ("tc-001.png", TC_001.read_bytes(), "image/png")},
        headers={"X-Redact-CSRF": token},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/png")
    assert response.headers["X-Redaction-Manifest"]
    manifest = response.headers["X-Redaction-Manifest"]
    # Base64-url-decode the manifest header and ensure it parses as JSON.
    import json

    raw = base64.urlsafe_b64decode(manifest.encode("ascii"))
    payload = json.loads(raw)
    assert payload["schema_version"] == "1"


def test_json_response_returns_image_and_manifest() -> None:
    client = _client()
    token = _csrf(client)
    response = client.post(
        "/redact",
        files={"image": ("tc-001.png", TC_001.read_bytes(), "image/png")},
        headers={
            "X-Redact-CSRF": token,
            "Accept": "application/json",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["image"]["mime_type"] == "image/png"
    image_bytes = base64.b64decode(body["image"]["bytes_b64"])
    Image.open(io.BytesIO(image_bytes))
    assert body["manifest"]["stats"]["redactions_total"] >= 1


def test_unsupported_mime_returns_415() -> None:
    client = _client()
    token = _csrf(client)
    response = client.post(
        "/redact",
        files={"image": ("x.bmp", b"BM", "image/bmp")},
        headers={"X-Redact-CSRF": token},
    )
    assert response.status_code == 415
    err = response.json()["error"]
    assert err["code"] == "E_INPUT_FORMAT"
    assert err["hint"]


def test_blur_style_downgrades_to_block() -> None:
    client = _client()
    token = _csrf(client)
    response = client.post(
        "/redact",
        files={"image": ("tc-001.png", TC_001.read_bytes(), "image/png")},
        data={"style": "blur"},
        headers={"X-Redact-CSRF": token, "Accept": "application/json"},
    )
    assert response.status_code == 200
    codes = {w["code"] for w in response.json()["warnings"]}
    assert "W_STYLE_DOWNGRADED_TO_BLOCK" in codes


def test_verbose_report_includes_matched_text_and_warning() -> None:
    client = _client()
    token = _csrf(client)
    response = client.post(
        "/redact",
        files={"image": ("tc-001.png", TC_001.read_bytes(), "image/png")},
        data={"verbose_report": "true"},
        headers={"X-Redact-CSRF": token, "Accept": "application/json"},
    )
    body = response.json()
    codes = {w["code"] for w in body["warnings"]}
    assert "W_VERBOSE_REPORT_ENABLED" in codes
    assert any(f.get("matched_text") for f in body["manifest"]["findings"])


def test_healthz() -> None:
    client = _client()
    response = client.get("/healthz")
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"]
    assert body["ocr_engine"].startswith("tesseract")


def test_policies_endpoint_lists_default() -> None:
    client = _client()
    response = client.get("/policies")
    assert response.status_code == 200
    ids = [p["id"] for p in response.json()]
    assert "default" in ids


def test_no_request_bytes_written_to_disk(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """BS-DoD — verify the redact request path does not touch the tempdir."""
    sentinel = tmp_path / "isolated"
    sentinel.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(sentinel))
    # Snapshot existing entries before the request.
    before = sorted(sentinel.iterdir())
    client = _client()
    token = _csrf(client)
    response = client.post(
        "/redact",
        files={"image": ("tc-001.png", TC_001.read_bytes(), "image/png")},
        headers={"X-Redact-CSRF": token, "Accept": "application/json"},
    )
    assert response.status_code == 200
    after = sorted(sentinel.iterdir())
    # The pipeline must not create any new entries in the tempdir.
    assert before == after, f"unexpected files in tempdir: {set(after) - set(before)}"
