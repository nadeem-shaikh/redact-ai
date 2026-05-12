"""HTTP routes (BUILD_SPEC §8)."""

from __future__ import annotations

import base64
import hashlib
import uuid
from importlib.resources import files
from typing import Any

from fastapi import APIRouter, Cookie, File, Form, Header, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, Response

from redact_ai.config import get_settings
from redact_ai.errors import (
    RedactError,
    csrf_error,
    input_format_error,
    input_too_large_error,
    policy_error,
)
from redact_ai.logging import get_logger
from redact_ai.models.manifest import Manifest
from redact_ai.pipeline import redact as run_pipeline
from redact_ai.pipeline.ingest import SUPPORTED_INPUT_MIMES
from redact_ai.policy.loader import builtin_policies, load_default_policy
from redact_ai.policy.schema import (
    BlockStyle,
    BlurStyle,
    LabelStyle,
    PixelateStyle,
    Policy,
)
from redact_ai.server.csrf import (
    COOKIE_NAME,
    META_NAME,
    generate_token,
    token_matches,
)
from redact_ai.version import __version__

log = get_logger("server")

router = APIRouter()

# Hard cap for inline manifest in response headers. 6 KB stays comfortably
# under the typical 8 KB header-size ceiling enforced by reverse proxies
# and the default uvicorn/h11 limit.
_MANIFEST_HEADER_LIMIT: int = 6 * 1024


@router.get("/healthz", response_class=JSONResponse)
async def healthz() -> JSONResponse:
    from redact_ai.pipeline.ocr.tesseract import TesseractAdapter

    engine = TesseractAdapter().engine_id()
    return JSONResponse({"status": "ok", "version": __version__, "ocr_engine": engine})


@router.get("/policies", response_class=JSONResponse)
async def list_policies() -> JSONResponse:
    out: list[dict[str, str]] = []
    for policy in builtin_policies():
        out.append(
            {
                "id": policy.id,
                "version": policy.version,
                "description": policy.description,
            }
        )
    return JSONResponse(out)


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    html = files("redact_ai.server.static").joinpath("index.html").read_text(encoding="utf-8")
    token = request.cookies.get(COOKIE_NAME) or generate_token()
    html = html.replace("{{ csrf_token }}", token).replace("{{ csrf_meta_name }}", META_NAME)
    response = HTMLResponse(html)
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        samesite="strict",
        path="/",
    )
    return response


@router.get("/static/{file_path:path}")
async def static_file(file_path: str) -> Response:
    safe = file_path.replace("..", "").lstrip("/")
    try:
        data = files("redact_ai.server.static").joinpath(safe).read_bytes()
    except FileNotFoundError:
        return JSONResponse({"error": "not found"}, status_code=404)
    mime = "application/octet-stream"
    if safe.endswith(".js"):
        mime = "application/javascript"
    elif safe.endswith(".css"):
        mime = "text/css"
    elif safe.endswith(".html"):
        mime = "text/html"
    return Response(data, media_type=mime)


@router.post("/redact")
async def post_redact(
    request: Request,
    image: UploadFile = File(...),
    policy_id: str = Form("default"),
    style: str | None = Form(None),
    verbose_report: str | None = Form(None),
    accept: str = Header("image/*"),
    x_redact_csrf: str | None = Header(None),
    rai_csrf: str | None = Cookie(None),
) -> Response:
    request_id = uuid.uuid4().hex
    settings = get_settings()
    if not token_matches(rai_csrf, x_redact_csrf):
        err = csrf_error()
        return JSONResponse({"error": err.to_dict()}, status_code=err.http_status)
    # Strip RFC 7231 media-type parameters (e.g. ``image/jpeg; charset=binary``)
    # before the allowlist check so well-formed uploads aren't rejected.
    mime = (image.content_type or "").split(";", 1)[0].strip().lower()
    if mime not in SUPPORTED_INPUT_MIMES:
        err = input_format_error(mime or "<unknown>")
        return JSONResponse({"error": err.to_dict()}, status_code=err.http_status)
    data = await image.read()
    if len(data) == 0:
        err = input_format_error(mime)
        return JSONResponse({"error": err.to_dict()}, status_code=err.http_status)
    if len(data) > settings.max_upload_bytes:
        err = input_too_large_error(len(data), settings.max_upload_bytes)
        return JSONResponse({"error": err.to_dict()}, status_code=err.http_status)

    try:
        policy = _resolve_policy(policy_id, style, verbose_report)
    except RedactError as exc:
        return JSONResponse({"error": exc.to_dict()}, status_code=exc.http_status)

    try:
        result = run_pipeline(data, mime, policy, request_id=request_id)
    except RedactError as exc:
        log.warning(
            "pipeline_error",
            extra={"stage": "http", "request_id": request_id, "fields": {"code": exc.code}},
        )
        return JSONResponse({"error": exc.to_dict()}, status_code=exc.http_status)

    accept_header = (accept or "").lower()
    manifest_dict = _manifest_to_dict(result.manifest)
    manifest_json = _stable_json(manifest_dict)
    manifest_b64 = base64.urlsafe_b64encode(manifest_json.encode("utf-8")).decode("ascii")
    manifest_sha = hashlib.sha256(manifest_json.encode("utf-8")).hexdigest()

    log.info(
        "redact_ok",
        extra={
            "stage": "http",
            "request_id": request_id,
            "fields": {
                "policy_id": policy.id,
                "findings": result.manifest.stats.redactions_total,
                "warnings": len(result.warnings),
                "mime": mime,
            },
        },
    )

    if "application/json" in accept_header:
        body: dict[str, Any] = {
            "image": {
                "mime_type": result.image.mime_type,
                "bytes_b64": base64.b64encode(result.image.bytes).decode("ascii"),
            },
            "manifest": manifest_dict,
            "warnings": [w.model_dump() for w in result.warnings],
        }
        return JSONResponse(body)

    by_category = result.manifest.stats.by_category
    stats_header = (
        f"redactions={result.manifest.stats.redactions_total};" f"categories={len(by_category)}"
    )
    headers: dict[str, str] = {
        "X-Redaction-Manifest-Sha256": manifest_sha,
        "X-Redaction-Stats": stats_header,
    }
    # Common proxy / framework header-size limits sit around 8 KB. Keep
    # the hash + stats unconditional, and only attach the full manifest
    # when it comfortably fits — large manifests will need the JSON
    # envelope branch (Accept: application/json) anyway.
    if len(manifest_b64) <= _MANIFEST_HEADER_LIMIT:
        headers["X-Redaction-Manifest"] = manifest_b64
    return Response(
        content=result.image.bytes,
        media_type=result.image.mime_type,
        headers=headers,
    )


def _resolve_policy(policy_id: str, style: str | None, verbose_report: str | None) -> Policy:
    if policy_id != "default":
        raise policy_error(policy_id, "only the 'default' policy is shipped in v0.1")
    base = load_default_policy()
    overrides: dict[str, Any] = {}
    if style is not None:
        overrides["redaction_style"] = _coerce_style(base.redaction_style, style)
    if verbose_report is not None and verbose_report.lower() == "true":
        overrides["verbose_report"] = True
    if not overrides:
        return base
    return base.model_copy(update=overrides)


def _coerce_style(
    current: BlockStyle | BlurStyle | PixelateStyle | LabelStyle,
    requested: str,
) -> BlockStyle | BlurStyle | PixelateStyle | LabelStyle:
    requested = requested.lower()
    if requested == "block":
        return BlockStyle(color=getattr(current, "color", "#000000"))
    if requested == "blur":
        return BlurStyle(color=getattr(current, "color", "#000000"))
    if requested == "pixelate":
        return PixelateStyle()
    if requested == "label":
        return LabelStyle()
    raise policy_error("override", f"unknown redaction style: {requested}")


def _manifest_to_dict(manifest: Manifest) -> dict[str, Any]:
    data: dict[str, Any] = manifest.model_dump(mode="json")
    return data


def _stable_json(obj: Any) -> str:
    import json

    return json.dumps(obj, separators=(",", ":"), sort_keys=False)
