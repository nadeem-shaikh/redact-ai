"""Loopback / Host / Origin enforcement (BUILD_SPEC §14.3)."""

from __future__ import annotations

from typing import Awaitable, Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from redact_ai.errors import origin_error


def _allowed_set(port: int) -> frozenset[str]:
    return frozenset(
        {
            "127.0.0.1",
            f"127.0.0.1:{port}",
            "localhost",
            f"localhost:{port}",
        }
    )


def _allowed_origins(port: int) -> frozenset[str]:
    return frozenset(
        {
            f"http://127.0.0.1:{port}",
            f"http://localhost:{port}",
        }
    )


class LoopbackOnlyMiddleware(BaseHTTPMiddleware):
    """Reject any request whose ``Host`` or ``Origin`` header is not loopback."""

    def __init__(self, app: ASGIApp, *, port: int) -> None:
        super().__init__(app)
        self._port = port

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable["Response"]],  # type: ignore[name-defined]
    ):
        allowed_hosts = _allowed_set(self._port)
        allowed_origins = _allowed_origins(self._port)

        host = request.headers.get("host", "")
        if host not in allowed_hosts and host.split(":", 1)[0] not in {"127.0.0.1", "localhost"}:
            return _origin_response()

        origin = request.headers.get("origin")
        if origin is not None and origin not in allowed_origins:
            return _origin_response()

        # Also defend against a malicious browser handing us a path like
        # ``//evil.example/foo`` — Starlette resolves this to ``request.url.hostname``.
        client = request.client
        if client is not None and client.host not in {"127.0.0.1", "::1"}:
            return _origin_response()
        return await call_next(request)


def _origin_response() -> JSONResponse:
    err = origin_error()
    return JSONResponse(status_code=err.http_status, content={"error": err.to_dict()})
