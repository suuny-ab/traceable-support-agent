"""Small hardened HTTP boundary for the public portfolio API.

The server intentionally uses only the Python standard library. Caddy is the
public TLS endpoint; this process is bound to the container network and never
owns certificates or public ports.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import threading
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .runs import PublicApiError, PublicRunService, _parse_bool


MAX_REQUEST_BYTES = 16 * 1024
RUN_PATH = re.compile(r"^/api/v1/runs/([A-Za-z0-9_-]{20,100})$")
DECISION_PATH = re.compile(
    r"^/api/v1/runs/([A-Za-z0-9_-]{20,100})/decision$"
)


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


class PublicApiHttpServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        service: PublicRunService,
    ) -> None:
        self.service = service
        super().__init__(server_address, PublicApiHandler)


class PublicApiHandler(BaseHTTPRequestHandler):
    server: PublicApiHttpServer
    server_version = "TraceableSupportAPI"
    sys_version = ""
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        # Do not emit request paths, query strings, source addresses, or bodies.
        return

    def version_string(self) -> str:
        return self.server_version

    def _origin_allowed(self) -> bool:
        return self.headers.get("Origin") == self.server.service.allowed_origin

    def _require_mutation_origin(self) -> None:
        if not self._origin_allowed():
            raise PublicApiError(403, "origin_not_allowed")

    def _browser_token(self) -> str | None:
        raw = self.headers.get("Cookie")
        if raw is None or len(raw) > 4096:
            return None
        cookie = SimpleCookie()
        try:
            cookie.load(raw)
        except Exception:
            return None
        item = cookie.get("__Host-traceable-browser")
        return None if item is None else item.value

    def _read_json(self) -> dict[str, Any]:
        if self.headers.get("Transfer-Encoding") is not None:
            raise PublicApiError(400, "transfer_encoding_not_allowed")
        content_type = self.headers.get("Content-Type", "")
        media_type = content_type.split(";", 1)[0].strip().lower()
        if media_type != "application/json":
            raise PublicApiError(415, "content_type_invalid")
        raw_length = self.headers.get("Content-Length")
        if raw_length is None or not raw_length.isdigit():
            raise PublicApiError(411, "content_length_required")
        length = int(raw_length)
        if length < 2 or length > MAX_REQUEST_BYTES:
            raise PublicApiError(413, "request_body_too_large")
        raw = self.rfile.read(length)
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

    def _security_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Vary", "Origin")
        if self._origin_allowed():
            self.send_header(
                "Access-Control-Allow-Origin", self.server.service.allowed_origin
            )

    def _send_json(
        self,
        status: int,
        value: dict[str, Any],
        *,
        cookie_token: str | None = None,
        retry_after_seconds: int | None = None,
        close_connection: bool = False,
    ) -> None:
        body = json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        self.send_response(status)
        self._security_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if cookie_token is not None:
            self.send_header(
                "Set-Cookie",
                "__Host-traceable-browser="
                + cookie_token
                + "; Path=/; Secure; HttpOnly; SameSite=Lax; Max-Age=31536000",
            )
        if retry_after_seconds is not None:
            self.send_header("Retry-After", str(retry_after_seconds))
        if close_connection:
            self.close_connection = True
            self.send_header("Connection", "close")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _send_error(self, error: PublicApiError) -> None:
        self._send_json(
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

    def do_OPTIONS(self) -> None:  # noqa: N802
        try:
            self._require_mutation_origin()
            if self.path != "/api/v1/runs" and DECISION_PATH.fullmatch(self.path) is None:
                raise PublicApiError(404, "route_not_found")
            self.send_response(HTTPStatus.NO_CONTENT)
            self._security_headers()
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Max-Age", "600")
            self.send_header("Content-Length", "0")
            self.end_headers()
        except PublicApiError as error:
            self._send_error(error)

    def do_GET(self) -> None:  # noqa: N802
        try:
            if self.path == "/api/v1/health":
                self._send_json(HTTPStatus.OK, self.server.service.health())
                return
            match = RUN_PATH.fullmatch(self.path)
            if match is None:
                raise PublicApiError(404, "route_not_found")
            self._send_json(HTTPStatus.OK, self.server.service.get_run(match.group(1)))
        except PublicApiError as error:
            self._send_error(error)

    def do_POST(self) -> None:  # noqa: N802
        try:
            self._require_mutation_origin()
            if self.path == "/api/v1/runs":
                submission = self.server.service.submit(
                    self._read_json(), browser_token=self._browser_token()
                )
                self._send_json(
                    HTTPStatus.ACCEPTED,
                    {
                        "run_id": submission.run_id,
                        "status": "queued",
                        "estimated_wait_seconds": submission.estimated_wait_seconds,
                    },
                    cookie_token=submission.browser_token,
                )
                return
            match = DECISION_PATH.fullmatch(self.path)
            if match is None:
                raise PublicApiError(404, "route_not_found")
            self._send_json(
                HTTPStatus.OK,
                self.server.service.decide(match.group(1), self._read_json()),
            )
        except PublicApiError as error:
            self._send_error(error)

    def do_HEAD(self) -> None:  # noqa: N802
        self.do_GET()

    def _method_not_allowed(self, allow: str) -> None:
        self.send_response(HTTPStatus.METHOD_NOT_ALLOWED)
        self._security_headers()
        self.send_header("Allow", allow)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_PUT(self) -> None:  # noqa: N802
        self._method_not_allowed("GET, HEAD, POST, OPTIONS")

    do_PATCH = do_PUT
    do_DELETE = do_PUT


def create_server(
    *,
    host: str,
    port: int,
    service: PublicRunService,
) -> PublicApiHttpServer:
    return PublicApiHttpServer((host, port), service)


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
    stop_once = threading.Event()

    def stop(_signum: int, _frame: Any) -> None:
        if not stop_once.is_set():
            stop_once.set()
            threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        server.serve_forever(poll_interval=0.25)
    finally:
        server.server_close()
        service.shutdown(wait=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["MAX_REQUEST_BYTES", "PublicApiHttpServer", "create_server", "main"]
