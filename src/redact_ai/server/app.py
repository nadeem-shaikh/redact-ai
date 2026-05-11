"""FastAPI application factory (BUILD_SPEC §8, §14)."""

from __future__ import annotations

import socket
import threading
import webbrowser

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from redact_ai.config import get_settings
from redact_ai.errors import RedactError, input_too_large_error
from redact_ai.logging import configure as configure_logging
from redact_ai.logging import get_logger
from redact_ai.server.middleware import LoopbackOnlyMiddleware
from redact_ai.server.routes import router
from redact_ai.version import __version__

log = get_logger("server.app")


def build_app(*, port: int) -> FastAPI:
    """Construct the FastAPI app with all middleware and routes mounted."""
    settings = get_settings()
    app = FastAPI(
        title="redact-ai",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url="/openapi.json",
    )
    app.state.port = port
    app.state.max_upload_bytes = settings.max_upload_bytes
    app.add_middleware(LoopbackOnlyMiddleware, port=port)
    app.include_router(router)

    @app.exception_handler(RedactError)
    async def _redact_error_handler(_: object, exc: RedactError) -> JSONResponse:
        return JSONResponse({"error": exc.to_dict()}, status_code=exc.http_status)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error_handler(
        _: object, exc: StarletteHTTPException
    ) -> JSONResponse:
        if exc.status_code == 413:
            err = input_too_large_error(settings.max_upload_bytes + 1, settings.max_upload_bytes)
            return JSONResponse({"error": err.to_dict()}, status_code=err.http_status)
        return JSONResponse({"error": {"code": "E_HTTP", "message": str(exc.detail), "hint": ""}}, status_code=exc.status_code)

    return app


def _claim_ephemeral_port() -> int:
    """Bind to an ephemeral port, read it back, then immediately release it."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]
    finally:
        sock.close()


def serve() -> None:
    """Bind to ``127.0.0.1`` on an ephemeral port and open the browser (BUILD_SPEC §14.1)."""
    configure_logging()
    port = _claim_ephemeral_port()
    app = build_app(port=port)
    url = f"http://127.0.0.1:{port}"
    log.info(
        "server_listening",
        extra={"stage": "http", "fields": {"url": url}},
    )
    settings = get_settings()
    if settings.open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
        access_log=False,
    )
