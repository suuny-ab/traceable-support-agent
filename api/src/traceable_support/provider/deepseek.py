"""Transport boundary with explicit offline and future-authorized modes.

The authorized class is a sealed, zero-retry wrapper around one exact POST to
the official endpoint. Merely importing or constructing either class never
reads ``DEEPSEEK_API_KEY`` and never opens a socket.
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
import time
import urllib.error
import urllib.request
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable

from .contract import (
    ENDPOINT_URL,
    MAX_REQUEST_BYTES,
    MAX_RESPONSE_BYTES,
    canonical_json_bytes,
    strict_json_loads,
)
from .response import TransportResponse


TRANSPORT_SCHEMA_VERSION = "tg07c0-safe-transport-v1"
OBSERVATION_SCHEMA_VERSION = "tg07c0-safe-transport-observation-v1"
MODE_OFFLINE = "offline_injected"
MODE_AUTHORIZED_REAL = "authorized_real"
KIND_OFFLINE = "local_injected"
KIND_AUTHORIZED_REAL = "official_https"


class Tg07c0TransportError(RuntimeError):
    """Detached fixed-code error; never carries headers, body, or exception text."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)
        self.__cause__ = None
        self.__context__ = None


def _fail(code: str) -> None:
    raise Tg07c0TransportError(code) from None


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _validate_call(*, url: Any, body: Any, timeout_ms: Any) -> tuple[bytes, int]:
    if url != ENDPOINT_URL:
        _fail("tg07c0_transport_target_invalid")
    if type(body) is not bytes or not body or len(body) > MAX_REQUEST_BYTES:
        _fail("tg07c0_transport_request_invalid")
    if type(timeout_ms) is not int or not 1 <= timeout_ms <= 180_000:
        _fail("tg07c0_transport_timeout_invalid")
    return body, timeout_ms


def _observation(
    *,
    sequence: int,
    mode: str,
    transport_kind: str,
    body: bytes,
    timeout_ms: int,
    outcome: str,
    failure_code: str | None,
    http_status: int | None,
    response_received: bool,
    response_body: bytes | None,
    final_url_verified: bool | None,
    content_type_is_json: bool | None,
    latency_ms: int,
    credential_read_attempted: bool,
    credential_value_obtained: bool,
    network_attempted: bool,
    dns_attempted: bool,
) -> dict[str, Any]:
    offline = mode == MODE_OFFLINE
    value: dict[str, Any] = {
        "schema_version": OBSERVATION_SCHEMA_VERSION,
        "sequence": sequence,
        "execution_mode": mode,
        "transport_kind": transport_kind,
        "url": ENDPOINT_URL,
        "method": "POST",
        "request_bytes": len(body),
        "request_sha256": _sha256(body),
        "timeout_ms": timeout_ms,
        "automatic_retry_count": 0,
        "transport_attempted": True,
        "credential_read_attempted": credential_read_attempted,
        "credential_value_obtained": credential_value_obtained,
        "network_attempted": network_attempted,
        "dns_attempted": dns_attempted,
        "provider_call_attempted": network_attempted,
        "http_status": http_status,
        "provider_response_received": response_received,
        "response_bytes": len(response_body) if response_body is not None else None,
        "response_sha256": _sha256(response_body) if response_body is not None else None,
        "final_url_verified": final_url_verified,
        "content_type_is_application_json": content_type_is_json,
        "latency_ms": latency_ms,
        "outcome": outcome,
        "failure_code": failure_code,
        "paid_call_performed": False if offline else None,
        "actual_billed_cost_cny_nanos": None,
        "billing_status": (
            "offline_no_external_call"
            if offline
            else ("unknown_after_network_attempt" if network_attempted else "no_network_attempt")
        ),
    }
    unsigned = deepcopy(value)
    value["observation_sha256"] = _sha256(canonical_json_bytes(unsigned))
    return value


def validate_transport_observation(
    value: Any,
    *,
    expected_request_body: bytes | None = None,
    expected_timeout: int | None = None,
    expected_ordinal: int | None = None,
    expected_mode: str | None = None,
) -> dict[str, Any]:
    """Strictly validate a persisted safe observation.

    Optional trusted arguments bind readback to the caller's rebuilt request,
    ordinal, timeout, and execution mode.  They are never inferred from the
    observation itself.
    """

    keys = {
        "schema_version", "sequence", "execution_mode", "transport_kind", "url",
        "method", "request_bytes", "request_sha256", "timeout_ms",
        "automatic_retry_count", "transport_attempted", "credential_read_attempted",
        "credential_value_obtained", "network_attempted", "dns_attempted",
        "provider_call_attempted", "http_status", "provider_response_received",
        "response_bytes", "response_sha256", "final_url_verified",
        "content_type_is_application_json",
        "latency_ms", "outcome", "failure_code", "paid_call_performed",
        "actual_billed_cost_cny_nanos", "billing_status", "observation_sha256",
    }
    if type(value) is not dict or set(value) != keys:
        _fail("tg07c0_transport_observation_invalid")
    item = deepcopy(value)
    if (
        item["schema_version"] != OBSERVATION_SCHEMA_VERSION
        or type(item["sequence"]) is not int
        or item["sequence"] < 1
        or item["url"] != ENDPOINT_URL
        or item["method"] != "POST"
        or type(item["request_bytes"]) is not int
        or not 0 < item["request_bytes"] <= MAX_REQUEST_BYTES
        or type(item["request_sha256"]) is not str
        or len(item["request_sha256"]) != 64
        or any(character not in "0123456789abcdef" for character in item["request_sha256"])
        or type(item["timeout_ms"]) is not int
        or not 1 <= item["timeout_ms"] <= 180_000
        or type(item["automatic_retry_count"]) is not int
        or item["automatic_retry_count"] != 0
        or item["transport_attempted"] is not True
        or any(
            type(item[name]) is not bool
            for name in (
                "credential_read_attempted", "credential_value_obtained",
                "network_attempted", "dns_attempted", "provider_call_attempted",
                "provider_response_received",
            )
        )
        or item["provider_call_attempted"] is not item["network_attempted"]
        or type(item["latency_ms"]) is not int
        or item["latency_ms"] < 0
        or type(item["outcome"]) is not str
        or item["outcome"] not in {"succeeded", "failed"}
        or (item["failure_code"] is not None and type(item["failure_code"]) is not str)
        or type(item["observation_sha256"]) is not str
        or len(item["observation_sha256"]) != 64
    ):
        _fail("tg07c0_transport_observation_invalid")
    if item["http_status"] is not None and (
        type(item["http_status"]) is not int or not 100 <= item["http_status"] <= 599
    ):
        _fail("tg07c0_transport_observation_invalid")
    if item["response_bytes"] is not None and (
        type(item["response_bytes"]) is not int
        or not 0 <= item["response_bytes"] <= MAX_RESPONSE_BYTES
    ):
        _fail("tg07c0_transport_observation_invalid")
    if item["response_sha256"] is not None and (
        type(item["response_sha256"]) is not str
        or len(item["response_sha256"]) != 64
        or any(character not in "0123456789abcdef" for character in item["response_sha256"])
    ):
        _fail("tg07c0_transport_observation_invalid")
    if (item["response_bytes"] is None) != (item["response_sha256"] is None):
        _fail("tg07c0_transport_observation_invalid")
    if item["final_url_verified"] is not None and type(item["final_url_verified"]) is not bool:
        _fail("tg07c0_transport_observation_invalid")
    if (
        item["content_type_is_application_json"] is not None
        and type(item["content_type_is_application_json"]) is not bool
    ):
        _fail("tg07c0_transport_observation_invalid")
    if item["outcome"] == "succeeded":
        if (
            item["failure_code"] is not None
            or item["provider_response_received"] is not True
            or item["response_bytes"] is None
            or item["response_sha256"] is None
            or item["final_url_verified"] is not True
        ):
            _fail("tg07c0_transport_observation_invalid")
    elif type(item["failure_code"]) is not str or not item["failure_code"]:
        _fail("tg07c0_transport_observation_invalid")
    if item["execution_mode"] == MODE_OFFLINE:
        if (
            item["transport_kind"] != KIND_OFFLINE
            or any(
                item[name] is not False
                for name in (
                    "credential_read_attempted", "credential_value_obtained",
                    "network_attempted", "dns_attempted", "provider_call_attempted",
                )
            )
            or item["paid_call_performed"] is not False
            or item["actual_billed_cost_cny_nanos"] is not None
            or item["billing_status"] != "offline_no_external_call"
        ):
            _fail("tg07c0_transport_observation_invalid")
    elif item["execution_mode"] == MODE_AUTHORIZED_REAL:
        if (
            item["transport_kind"] != KIND_AUTHORIZED_REAL
            or item["credential_read_attempted"] is not True
            or item["paid_call_performed"] is not None
            or item["actual_billed_cost_cny_nanos"] is not None
            or type(item["billing_status"]) is not str
            or item["billing_status"]
            not in {"no_network_attempt", "unknown_after_network_attempt"}
        ):
            _fail("tg07c0_transport_observation_invalid")
    else:
        _fail("tg07c0_transport_observation_invalid")
    unsigned = {key: deepcopy(item[key]) for key in item if key != "observation_sha256"}
    if item["observation_sha256"] != _sha256(canonical_json_bytes(unsigned)):
        _fail("tg07c0_transport_observation_invalid")
    if expected_request_body is not None:
        if (
            type(expected_request_body) is not bytes
            or item["request_bytes"] != len(expected_request_body)
            or item["request_sha256"] != _sha256(expected_request_body)
        ):
            _fail("tg07c0_transport_observation_invalid")
    if expected_timeout is not None and (
        type(expected_timeout) is not int or item["timeout_ms"] != expected_timeout
    ):
        _fail("tg07c0_transport_observation_invalid")
    if expected_ordinal is not None and (
        type(expected_ordinal) is not int or item["sequence"] != expected_ordinal
    ):
        _fail("tg07c0_transport_observation_invalid")
    if expected_mode is not None and (
        type(expected_mode) is not str or item["execution_mode"] != expected_mode
    ):
        _fail("tg07c0_transport_observation_invalid")
    return item


class OfflineInjectedTransport:
    """Deterministic response source; never reads credentials or opens sockets."""

    __slots__ = ("_steps", "_observations", "_clock_ns")

    def __init__(
        self,
        steps: list[dict[str, Any]],
        *,
        clock_ns: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        if type(steps) is not list or not steps or not callable(clock_ns):
            _fail("tg07c0_offline_fixture_invalid")
        checked: list[dict[str, Any]] = []
        for step in steps:
            if type(step) is not dict or type(step.get("kind")) is not str:
                _fail("tg07c0_offline_fixture_invalid")
            kind = step["kind"]
            if kind == "response":
                allowed_shapes = (
                    {"kind", "status_code", "body"},
                    {"kind", "status_code", "body", "final_url"},
                    {"kind", "status_code", "body", "content_type"},
                    {"kind", "status_code", "body", "final_url", "content_type"},
                )
                if (
                    set(step) not in allowed_shapes
                    or type(step["status_code"]) is not int
                    or type(step["body"]) is not bytes
                ):
                    _fail("tg07c0_offline_fixture_invalid")
                if not 100 <= step["status_code"] <= 599 or len(step["body"]) > MAX_RESPONSE_BYTES:
                    _fail("tg07c0_offline_fixture_invalid")
                if "final_url" in step and type(step["final_url"]) is not str:
                    _fail("tg07c0_offline_fixture_invalid")
                if "content_type" in step and step["content_type"] is not None and type(step["content_type"]) is not str:
                    _fail("tg07c0_offline_fixture_invalid")
            elif kind in {"timeout", "transport_error"}:
                if set(step) not in ({"kind"}, {"kind", "unsafe_message"}):
                    _fail("tg07c0_offline_fixture_invalid")
                if "unsafe_message" in step and (
                    type(step["unsafe_message"]) is not str
                    or not step["unsafe_message"]
                    or len(step["unsafe_message"]) > 512
                ):
                    _fail("tg07c0_offline_fixture_invalid")
            elif kind == "sensitive_reflection":
                if (
                    set(step) != {"kind", "unsafe_message"}
                    or type(step["unsafe_message"]) is not str
                    or not step["unsafe_message"]
                    or len(step["unsafe_message"]) > 512
                ):
                    _fail("tg07c0_offline_fixture_invalid")
            else:
                _fail("tg07c0_offline_fixture_invalid")
            checked.append(deepcopy(step))
        self._steps = checked
        self._observations: list[dict[str, Any]] = []
        self._clock_ns = clock_ns

    @property
    def execution_mode(self) -> str:
        return MODE_OFFLINE

    @property
    def transport_kind(self) -> str:
        return KIND_OFFLINE

    def post_json(self, *, url: str, body: bytes, timeout_ms: int) -> TransportResponse:
        body, timeout_ms = _validate_call(url=url, body=body, timeout_ms=timeout_ms)
        if not self._steps:
            _fail("tg07c0_offline_fixture_exhausted")
        sequence = len(self._observations) + 1
        started = self._clock_ns()
        step = self._steps.pop(0)
        kind = step["kind"]
        status = step.get("status_code") if kind == "response" else None
        response_received = kind == "response"
        response_body = step.get("body") if kind == "response" else None
        final_url = step.get("final_url", ENDPOINT_URL) if kind == "response" else None
        content_type = step.get("content_type", "application/json") if kind == "response" else None
        failure = None
        outcome = "succeeded"
        if kind == "timeout":
            failure = "tg07c0_timeout"
            outcome = "failed"
        elif kind == "transport_error":
            failure = "tg07c0_transport_error"
            outcome = "failed"
        elif kind == "sensitive_reflection":
            failure = "tg07c0_sensitive_reflection"
            outcome = "failed"
        elif final_url != ENDPOINT_URL:
            failure = "tg07c0_redirect_rejected"
            outcome = "failed"
            response_body = None
        finished = self._clock_ns()
        observation = _observation(
            sequence=sequence,
            mode=MODE_OFFLINE,
            transport_kind=KIND_OFFLINE,
            body=body,
            timeout_ms=timeout_ms,
            outcome=outcome,
            failure_code=failure,
            http_status=status,
            response_received=response_received,
            response_body=response_body,
            final_url_verified=(final_url == ENDPOINT_URL) if response_received else None,
            content_type_is_json=(
                type(content_type) is str
                and content_type.split(";", 1)[0].strip().lower() == "application/json"
            ) if response_received else None,
            latency_ms=max(0, (finished - started) // 1_000_000),
            credential_read_attempted=False,
            credential_value_obtained=False,
            network_attempted=False,
            dns_attempted=False,
        )
        self._observations.append(validate_transport_observation(observation))
        if failure is not None:
            # Do not retain an injected canary or arbitrary failure text in a
            # traceback frame or the transport object.
            step.clear()
            _fail(failure)
        response = TransportResponse(
            status_code=status,
            body=step["body"],
            final_url=final_url,
            content_type=content_type,
        )
        step.clear()
        return response

    @property
    def call_count(self) -> int:
        return len(self._observations)

    def safe_observations(self) -> list[dict[str, Any]]:
        return deepcopy(self._observations)


class _RejectRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        return None


@dataclass(frozen=True)
class _AuthorizedRoundtrip:
    kind: str
    response: TransportResponse | None
    credential_value_obtained: bool
    network_attempted: bool
    dns_attempted: bool


def _authorized_roundtrip(body: bytes, timeout_ms: int) -> _AuthorizedRoundtrip:
    """Keep secret/header/raw-response aliases inside a fully caught frame."""

    secret: str | None = None
    headers: dict[str, str] = {}
    request: urllib.request.Request | None = None
    response: Any = None
    raw: bytes | None = None
    network_attempted = False
    try:
        secret = os.environ.get("DEEPSEEK_API_KEY")
        if type(secret) is not str or not secret:
            return _AuthorizedRoundtrip("credential_missing", None, False, False, False)
        if secret.encode("utf-8") in body:
            return _AuthorizedRoundtrip("sensitive_reflection", None, True, False, False)
        headers = {
            "Authorization": "Bearer " + secret,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        request = urllib.request.Request(ENDPOINT_URL, data=body, headers=headers, method="POST")
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _RejectRedirects())
        network_attempted = True
        response = opener.open(request, timeout=timeout_ms / 1000)
        final_url = response.geturl()
        status = response.getcode()
        content_type = response.getheader("Content-Type")
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        if final_url != ENDPOINT_URL:
            return _AuthorizedRoundtrip("redirect", None, True, True, True)
        if len(raw) > MAX_RESPONSE_BYTES:
            return _AuthorizedRoundtrip("response_too_large", None, True, True, True)
        normalized: bytes | None = None
        try:
            normalized = canonical_json_bytes(strict_json_loads(raw))
        except BaseException:
            normalized = None
        if secret.encode("utf-8") in raw or (
            normalized is not None and secret.encode("utf-8") in normalized
        ):
            return _AuthorizedRoundtrip("sensitive_reflection", None, True, True, True)
        return _AuthorizedRoundtrip(
            "ok",
            TransportResponse(
                status_code=status,
                body=raw,
                final_url=final_url,
                content_type=content_type,
            ),
            True,
            True,
            True,
        )
    except urllib.error.HTTPError as exc:
        status = exc.code if type(exc.code) is int else 599
        return _AuthorizedRoundtrip(
            "redirect" if 300 <= status <= 399 else f"http_{status}",
            TransportResponse(status_code=status, body=b"", content_type=None),
            secret is not None,
            network_attempted,
            network_attempted,
        )
    except (TimeoutError, socket.timeout):
        return _AuthorizedRoundtrip("timeout", None, secret is not None, network_attempted, network_attempted)
    except BaseException:
        return _AuthorizedRoundtrip("transport", None, secret is not None, network_attempted, network_attempted)
    finally:
        if response is not None:
            try:
                response.close()
            except BaseException:
                pass
        headers.clear()
        secret = None
        request = None
        response = None
        raw = None


class AuthorizedRealTransport:
    """Future authorized official HTTPS transport; construction is inert."""

    __slots__ = ("_observations", "_clock_ns")

    def __init__(self, *, clock_ns: Callable[[], int] = time.monotonic_ns) -> None:
        if not callable(clock_ns):
            _fail("tg07c0_transport_clock_invalid")
        self._observations: list[dict[str, Any]] = []
        self._clock_ns = clock_ns

    @property
    def execution_mode(self) -> str:
        return MODE_AUTHORIZED_REAL

    @property
    def transport_kind(self) -> str:
        return KIND_AUTHORIZED_REAL

    def post_json(self, *, url: str, body: bytes, timeout_ms: int) -> TransportResponse:
        body, timeout_ms = _validate_call(url=url, body=body, timeout_ms=timeout_ms)
        sequence = len(self._observations) + 1
        started = self._clock_ns()
        result = _authorized_roundtrip(body, timeout_ms)
        finished = self._clock_ns()
        code: str | None = None
        if result.kind != "ok":
            code = {
                "credential_missing": "provider_credential_missing",
                "sensitive_reflection": "provider_sensitive_reflection",
                "redirect": "provider_redirect_rejected",
                "timeout": "provider_timeout",
                "transport": "provider_transport_error",
                "response_too_large": "provider_response_too_large",
            }.get(result.kind, "provider_http_status_invalid" if result.kind.startswith("http_") else "provider_transport_error")
        status = result.response.status_code if result.response is not None else None
        observation = _observation(
            sequence=sequence,
            mode=MODE_AUTHORIZED_REAL,
            transport_kind=KIND_AUTHORIZED_REAL,
            body=body,
            timeout_ms=timeout_ms,
            outcome="succeeded" if code is None else "failed",
            failure_code=code,
            http_status=status,
            response_received=result.response is not None,
            response_body=(result.response.body if code is None and result.response is not None else None),
            final_url_verified=(result.response.final_url == ENDPOINT_URL if result.response is not None else None),
            content_type_is_json=(
                type(result.response.content_type) is str
                and result.response.content_type.split(";", 1)[0].strip().lower() == "application/json"
            ) if result.response is not None else None,
            latency_ms=max(0, (finished - started) // 1_000_000),
            credential_read_attempted=True,
            credential_value_obtained=result.credential_value_obtained,
            network_attempted=result.network_attempted,
            dns_attempted=result.dns_attempted,
        )
        self._observations.append(validate_transport_observation(observation))
        if code is not None or result.response is None:
            _fail(code or "provider_transport_error")
        return result.response

    @property
    def call_count(self) -> int:
        return len(self._observations)

    def safe_observations(self) -> list[dict[str, Any]]:
        return deepcopy(self._observations)


# Public name used by the fixed real-execution entry.  The alias does not
# create a second implementation or a weaker subclass boundary.
AuthorizedOfficialHTTPSTransport = AuthorizedRealTransport


def transport_identity(value: Any) -> dict[str, str]:
    if type(value) is OfflineInjectedTransport:
        mode, kind = MODE_OFFLINE, KIND_OFFLINE
    elif type(value) is AuthorizedRealTransport:
        mode, kind = MODE_AUTHORIZED_REAL, KIND_AUTHORIZED_REAL
    else:
        _fail("tg07c0_transport_identity_invalid")
    return {
        "schema_version": TRANSPORT_SCHEMA_VERSION,
        "execution_mode": mode,
        "transport_kind": kind,
        "endpoint": ENDPOINT_URL,
        "automatic_retry_count": 0,
    }


__all__ = [
    "AuthorizedRealTransport",
    "AuthorizedOfficialHTTPSTransport",
    "KIND_AUTHORIZED_REAL",
    "KIND_OFFLINE",
    "MODE_AUTHORIZED_REAL",
    "MODE_OFFLINE",
    "OfflineInjectedTransport",
    "Tg07c0TransportError",
    "transport_identity",
    "validate_transport_observation",
]
