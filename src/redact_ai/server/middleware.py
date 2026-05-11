"""Loopback / Host / Origin enforcement (BUILD_SPEC §14.3)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from redact_ai.errors import origin_error


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
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        allowed_origins = _allowed_origins(self._port)

        host = request.headers.get("host", "")
        host_name = host.split(":", 1)[0]
        if host_name not in {"127.0.0.1", "localhost"}:
            return _origin_response()

        origin = request.headers.get("origin")
        if origin is not None and origin not in allowed_origins:
            return _origin_response()
        return await call_next(request)


def _origin_response() -> JSONResponse:
    err = origin_error()
    return JSONResponse(status_code=err.http_status, content={"error": err.to_dict()})
