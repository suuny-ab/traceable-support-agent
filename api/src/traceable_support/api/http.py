"""Hardened HTTP boundary for the public portfolio API.

The shell runs on FastAPI + uvicorn and keeps the exact public contract of
the previous standard-library implementation; every business decision stays
in ``runs.PublicRunService``. Caddy is the public TLS endpoint; this process
is bound to the container network and never owns certificates or public ports.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from .runs import PublicApiError, PublicRunService, _parse_bool


MAX_REQUEST_BYTES = 16 * 1024
RUN_ID = re.compile(r"^[A-Za-z0-9_-]{20,100}$")

_JSON_CONTENT_TYPE = "application/json; charset=utf-8"
_ALLOW_METHODS = "GET, HEAD, POST, OPTIONS"
_PREFLIGHT_HEADERS = {
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "600",
}
_BROWSER_COOKIE = "__Host-traceable-browser"
_SERVER_HEADER = "TraceableSupportAPI"


class _DuplicateKey(ValueError):
    pass


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise _DuplicateKey("duplicate_json_key")
        value[key] = item
    return value


def _reject_constant(_: str) -> None:
    raise ValueError("non_finite_json_number")


def _json_response(
    status: int,
    value: dict[str, Any],
    *,
    cookie_token: str | None = None,
    retry_after_seconds: int | None = None,
    close_connection: bool = False,
) -> Response:
    body = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    headers = {
        "Content-Type": _JSON_CONTENT_TYPE,
        "Content-Length": str(len(body)),
    }
    if cookie_token is not None:
        headers["Set-Cookie"] = (
            _BROWSER_COOKIE
            + "="
            + cookie_token
            + "; Path=/; Secure; HttpOnly; SameSite=Lax; Max-Age=31536000"
        )
    if retry_after_seconds is not None:
        headers["Retry-After"] = str(retry_after_seconds)
    if close_connection:
        headers["Connection"] = "close"
    return Response(content=body, status_code=status, headers=headers)


def _error_response(error: PublicApiError) -> Response:
    return _json_response(
        error.status_code,
        {
            "error": {
                "code": error.code,
                "replay_available": error.replay_available,
            }
        },
        retry_after_seconds=error.retry_after_seconds,
        close_connection=True,
    )


def _empty_response(status: int, headers: dict[str, str] | None = None) -> Response:
    merged = dict(headers or {})
    merged["Content-Length"] = "0"
    return Response(status_code=status, headers=merged)


class _SecurityHeadersMiddleware:
    """Outermost ASGI wrapper adding the fixed headers to every response."""

    def __init__(self, app: Any, allowed_origin: str) -> None:
        self.app = app
        self.allowed_origin = allowed_origin

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        origin: str | None = None
        for name, value in scope["headers"]:
            if name == b"origin":
                origin = value.decode("latin-1")
                break

        async def send_with_security_headers(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                raw = message.setdefault("headers", [])
                raw.extend(
                    [
                        (b"cache-control", b"no-store"),
                        (b"x-content-type-options", b"nosniff"),
                        (b"x-frame-options", b"DENY"),
                        (b"referrer-policy", b"no-referrer"),
                        (b"cross-origin-resource-policy", b"same-origin"),
                        (b"vary", b"Origin"),
                        (b"server", _SERVER_HEADER.encode("latin-1")),
                    ]
                )
                if origin == self.allowed_origin:
                    raw.append(
                        (
                            b"access-control-allow-origin",
                            self.allowed_origin.encode("latin-1"),
                        )
                    )
            await send(message)

        await self.app(scope, receive, send_with_security_headers)


def create_app(service: PublicRunService) -> FastAPI:
    app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None, redirect_slashes=False)

    def _require_mutation_origin(request: Request) -> None:
        if request.headers.get("origin") != service.allowed_origin:
            raise PublicApiError(403, "origin_not_allowed")

    def _browser_token(request: Request) -> str | None:
        raw = request.headers.get("cookie")
        if raw is None or len(raw) > 4096:
            return None
        cookie = SimpleCookie()
        try:
            cookie.load(raw)
        except Exception:
            return None
        item = cookie.get(_BROWSER_COOKIE)
        return None if item is None else item.value

    async def _read_json(request: Request) -> dict[str, Any]:
        if request.headers.get("transfer-encoding") is not None:
            raise PublicApiError(400, "transfer_encoding_not_allowed")
        content_type = request.headers.get("content-type", "")
        media_type = content_type.split(";", 1)[0].strip().lower()
        if media_type != "application/json":
            raise PublicApiError(415, "content_type_invalid")
        raw_length = request.headers.get("content-length")
        if raw_length is None or not raw_length.isdigit():
            raise PublicApiError(411, "content_length_required")
        length = int(raw_length)
        if length < 2 or length > MAX_REQUEST_BYTES:
            raise PublicApiError(413, "request_body_too_large")
        raw = await request.body()
        if len(raw) != length:
            raise PublicApiError(400, "request_body_incomplete")
        try:
            value = json.loads(
                raw.decode("utf-8", errors="strict"),
                object_pairs_hook=_object_without_duplicates,
                parse_constant=_reject_constant,
            )
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            raise PublicApiError(400, "json_invalid") from None
        if type(value) is not dict:
            raise PublicApiError(400, "json_object_required")
        return value

    async def health(_: Request) -> Response:
        return _json_response(200, service.health())

    async def get_run(request: Request) -> Response:
        if RUN_ID.fullmatch(request.path_params["run_id"]) is None:
            raise PublicApiError(404, "route_not_found")
        return _json_response(200, service.get_run(request.path_params["run_id"]))

    async def submit(request: Request) -> Response:
        _require_mutation_origin(request)
        submission = service.submit(
            await _read_json(request), browser_token=_browser_token(request)
        )
        return _json_response(
            202,
            {
                "run_id": submission.run_id,
                "status": "queued",
                "estimated_wait_seconds": submission.estimated_wait_seconds,
            },
            cookie_token=submission.browser_token,
        )

    async def decide(request: Request) -> Response:
        _require_mutation_origin(request)
        if RUN_ID.fullmatch(request.path_params["run_id"]) is None:
            raise PublicApiError(404, "route_not_found")
        return _json_response(
            200,
            service.decide(request.path_params["run_id"], await _read_json(request)),
        )

    async def preflight_runs(request: Request) -> Response:
        _require_mutation_origin(request)
        return _empty_response(204, _PREFLIGHT_HEADERS)

    async def preflight_decision(request: Request) -> Response:
        _require_mutation_origin(request)
        if RUN_ID.fullmatch(request.path_params["run_id"]) is None:
            raise PublicApiError(404, "route_not_found")
        return _empty_response(204, _PREFLIGHT_HEADERS)

    async def post_fallback(request: Request) -> Response:
        _require_mutation_origin(request)
        raise PublicApiError(404, "route_not_found")

    async def options_fallback(request: Request) -> Response:
        _require_mutation_origin(request)
        raise PublicApiError(404, "route_not_found")

    async def get_fallback(_: Request) -> Response:
        raise PublicApiError(404, "route_not_found")

    async def method_not_allowed(_: Request) -> Response:
        return _empty_response(405, {"Allow": _ALLOW_METHODS})

    async def _on_public_api_error(_: Request, error: PublicApiError) -> Response:
        return _error_response(error)

    async def _on_http_exception(_: Request, error: StarletteHTTPException) -> Response:
        if error.status_code == 405:
            return _empty_response(405, {"Allow": _ALLOW_METHODS})
        return _error_response(PublicApiError(404, "route_not_found"))

    app.add_route("/api/v1/health", health, methods=["GET"])
    app.add_route("/api/v1/runs/{run_id}", get_run, methods=["GET"])
    app.add_route("/api/v1/runs", submit, methods=["POST"])
    app.add_route("/api/v1/runs/{run_id}/decision", decide, methods=["POST"])
    app.add_route("/api/v1/runs", preflight_runs, methods=["OPTIONS"])
    app.add_route("/api/v1/runs/{run_id}/decision", preflight_decision, methods=["OPTIONS"])
    app.add_route("/{path:path}", post_fallback, methods=["POST"])
    app.add_route("/{path:path}", options_fallback, methods=["OPTIONS"])
    app.add_route("/{path:path}", get_fallback, methods=["GET"])
    app.add_route("/{path:path}", method_not_allowed, methods=["PUT", "PATCH", "DELETE"])
    app.add_exception_handler(PublicApiError, _on_public_api_error)
    app.add_exception_handler(StarletteHTTPException, _on_http_exception)
    return app


def _bind_socket(host: str, port: int) -> socket.socket:
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    sock = socket.socket(family=family)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    sock.listen(2048)
    sock.set_inheritable(True)
    return sock


class PublicApiHttpServer:
    """uvicorn runner with the stdlib server's lifecycle surface.

    The listen socket is bound at construction so an ephemeral port is known
    before ``serve_forever`` starts; ``shutdown`` asks uvicorn to drain.
    """

    def __init__(
        self,
        host: str,
        port: int,
        service: PublicRunService,
    ) -> None:
        self.service = service
        app = _SecurityHeadersMiddleware(create_app(service), service.allowed_origin)
        self._config = uvicorn.Config(
            app,
            host=host,
            port=port,
            access_log=False,
            log_level="warning",
            server_header=False,
        )
        self._socket = _bind_socket(host, port)
        self._server = uvicorn.Server(self._config)
        self.server_port = self._socket.getsockname()[1]

    def serve_forever(self) -> None:
        self._server.run(sockets=[self._socket])

    def shutdown(self) -> None:
        self._server.should_exit = True

    def server_close(self) -> None:
        self._socket.close()


def create_server(
    *,
    host: str,
    port: int,
    service: PublicRunService,
) -> PublicApiHttpServer:
    return PublicApiHttpServer(host, port, service)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Traceable Support public API")
    parser.add_argument("--host", default=os.environ.get("TRACEABLE_PUBLIC_HOST", "0.0.0.0"))
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("TRACEABLE_PUBLIC_PORT", "8000"))
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=Path(
            os.environ.get("TRACEABLE_PUBLIC_DB", "/var/lib/traceable/public.sqlite3")
        ),
    )
    parser.add_argument(
        "--origin",
        default=os.environ.get("TRACEABLE_PUBLIC_ORIGIN", "https://127.0.0.1"),
    )
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    product_runner = None
    if _parse_bool(os.environ.get("TRACEABLE_PUBLIC_LIVE_ENABLED")):
        # Lazy import keeps the replay-only image free of live dependencies.
        from .live_assembly import assemble_product_runner

        product_runner = assemble_product_runner()
    service = PublicRunService(
        args.database, allowed_origin=args.origin, product_runner=product_runner
    )
    server = create_server(host=args.host, port=args.port, service=service)
    try:
        # uvicorn owns SIGINT/SIGTERM in the main thread and drains on signal.
        server.serve_forever()
    finally:
        server.server_close()
        service.shutdown(wait=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["MAX_REQUEST_BYTES", "PublicApiHttpServer", "create_app", "create_server", "main"]
