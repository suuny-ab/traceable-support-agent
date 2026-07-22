"""Offline-verifiable DeepSeek response adapter and local fixture transport."""

from __future__ import annotations

import os
import socket
import time
import urllib.error
import urllib.request
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable

from .contract import (
    BASE_URL,
    CONTENT_PROMPT_VERSION,
    ENDPOINT_URL,
    FAILURE_CODES,
    MAX_REQUEST_BYTES,
    MAX_RESPONSE_BYTES,
    MODEL,
    PLAN_PROMPT_VERSION,
    PROVIDER,
    STAGE_CONTENT,
    STAGE_PLAN,
    STAGES,
    Tg07aContractError,
    build_attempt_record,
    build_chat_request,
    build_manifest,
    canonical_json_bytes,
    finalize_transcript,
    parse_chat_completion,
    sha256_bytes,
    strict_json_loads,
    validate_stage_result,
)


@dataclass(frozen=True)
class TransportResponse:
    status_code: int
    body: bytes
    final_url: str = ENDPOINT_URL
    content_type: str | None = "application/json"


class TransportTimeout(Exception):
    pass


class TransportFailure(Exception):
    pass


class TransportRedirect(Exception):
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        super().__init__()


class TransportSensitiveReflection(Exception):
    def __init__(self, status_code: int | None) -> None:
        self.status_code = status_code
        super().__init__()


class LocalInjectedTransport:
    """A deterministic, header-free local transport for contract tests."""

    __slots__ = ("_steps", "_safe_calls")

    def __init__(self, steps: list[dict[str, Any]]) -> None:
        if type(steps) is not list or not steps:
            raise Tg07aContractError("injected_transport_invalid")
        checked: list[dict[str, Any]] = []
        for step in steps:
            if type(step) is not dict or type(step.get("kind")) is not str:
                raise Tg07aContractError("injected_transport_invalid")
            kind = step["kind"]
            if kind == "response":
                if set(step) not in (
                    {"kind", "status_code", "body"},
                    {"kind", "status_code", "body", "final_url"},
                    {"kind", "status_code", "body", "content_type"},
                    {"kind", "status_code", "body", "final_url", "content_type"},
                ):
                    raise Tg07aContractError("injected_transport_invalid")
                if type(step["status_code"]) is not int or not 100 <= step["status_code"] <= 599:
                    raise Tg07aContractError("injected_transport_invalid")
                if type(step["body"]) is not bytes:
                    raise Tg07aContractError("injected_transport_invalid")
                if "final_url" in step and type(step["final_url"]) is not str:
                    raise Tg07aContractError("injected_transport_invalid")
                if "content_type" in step and type(step["content_type"]) is not str:
                    raise Tg07aContractError("injected_transport_invalid")
            elif kind == "timeout":
                if set(step) != {"kind"}:
                    raise Tg07aContractError("injected_transport_invalid")
            elif kind == "exception":
                if set(step) not in ({"kind"}, {"kind", "unsafe_message"}):
                    raise Tg07aContractError("injected_transport_invalid")
                if "unsafe_message" in step and (
                    type(step["unsafe_message"]) is not str
                    or not step["unsafe_message"]
                    or len(step["unsafe_message"]) > 512
                ):
                    raise Tg07aContractError("injected_transport_invalid")
            else:
                raise Tg07aContractError("injected_transport_invalid")
            checked.append(deepcopy(step))
        self._steps = checked
        self._safe_calls: list[dict[str, Any]] = []

    def post_json(self, *, url: str, body: bytes, timeout_ms: int) -> TransportResponse:
        if url != ENDPOINT_URL or type(body) is not bytes or type(timeout_ms) is not int:
            raise TransportFailure() from None
        ordinal = len(self._safe_calls) + 1
        self._safe_calls.append(
            {
                "ordinal": ordinal,
                "url": ENDPOINT_URL,
                "method": "POST",
                "request_bytes": len(body),
                "request_sha256": sha256_bytes(body),
                "timeout_ms": timeout_ms,
                "authorization_present": False,
                "automatic_retry_count": 0,
            }
        )
        if not self._steps:
            raise TransportFailure() from None
        step = self._steps.pop(0)
        if step["kind"] == "timeout":
            raise TransportTimeout() from None
        if step["kind"] == "exception":
            unsafe_message: str | None = step.get("unsafe_message")
            try:
                raise RuntimeError(unsafe_message or "injected transport failure")
            except BaseException:
                raise TransportFailure() from None
            finally:
                unsafe_message = None
        return TransportResponse(
            status_code=step["status_code"],
            body=step["body"],
            final_url=step.get("final_url", ENDPOINT_URL),
            content_type=step.get("content_type", "application/json"),
        )

    @property
    def call_count(self) -> int:
        return len(self._safe_calls)

    def safe_calls(self) -> list[dict[str, Any]]:
        return deepcopy(self._safe_calls)


class _RejectRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        return None


def _real_http_roundtrip(body: bytes, timeout_ms: int) -> tuple[str, TransportResponse | None]:
    """Keep every secret alias inside a frame that returns only a safe outcome."""

    secret: str | None = None
    headers: dict[str, str] = {}
    request: urllib.request.Request | None = None
    response: Any = None
    try:
        secret = os.environ.get("DEEPSEEK_API_KEY")
        if type(secret) is not str or not secret:
            return "credential_missing", None
        if secret.encode("utf-8") in body:
            return "sensitive_reflection", None
        headers = {
            "Authorization": "Bearer " + secret,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        request = urllib.request.Request(
            ENDPOINT_URL,
            data=body,
            headers=headers,
            method="POST",
        )
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            _RejectRedirects(),
        )
        response = opener.open(request, timeout=timeout_ms / 1000)
        final_url = response.geturl()
        status_code = response.getcode()
        content_type = response.getheader("Content-Type")
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        if final_url != ENDPOINT_URL:
            return "redirect", TransportResponse(status_code=status_code, body=b"", final_url=ENDPOINT_URL)
        normalized: bytes | None = None
        try:
            normalized = canonical_json_bytes(strict_json_loads(raw))
        except Tg07aContractError:
            normalized = None
        if secret.encode("utf-8") in raw or (
            normalized is not None and secret.encode("utf-8") in normalized
        ):
            return "sensitive_reflection", TransportResponse(status_code=status_code, body=b"", final_url=ENDPOINT_URL)
        return "ok", TransportResponse(
            status_code=status_code,
            body=raw,
            final_url=final_url,
            content_type=content_type,
        )
    except urllib.error.HTTPError as exc:
        code = exc.code if type(exc.code) is int else 599
        if 300 <= code <= 399:
            return "redirect", TransportResponse(status_code=code, body=b"", final_url=ENDPOINT_URL)
        return "ok", TransportResponse(
            status_code=code,
            body=b"",
            final_url=ENDPOINT_URL,
            content_type=None,
        )
    except (TimeoutError, socket.timeout):
        return "timeout", None
    except BaseException:
        return "transport", None
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


class OfficialDeepSeekHTTPSTransport:
    """Exact official endpoint, no proxy, no redirect, no retry."""

    __slots__ = ()

    def post_json(self, *, url: str, body: bytes, timeout_ms: int) -> TransportResponse:
        if (
            url != ENDPOINT_URL
            or not url.startswith(BASE_URL + "/")
            or type(body) is not bytes
            or len(body) > MAX_REQUEST_BYTES
            or type(timeout_ms) is not int
            or not 1 <= timeout_ms <= 180_000
        ):
            raise TransportFailure() from None
        kind, response = _real_http_roundtrip(body, timeout_ms)
        if kind == "ok" and response is not None:
            return response
        if kind == "timeout":
            raise TransportTimeout() from None
        if kind == "redirect":
            raise TransportRedirect(response.status_code if response is not None else 599) from None
        if kind == "sensitive_reflection":
            raise TransportSensitiveReflection(response.status_code if response is not None else None) from None
        raise TransportFailure() from None


def json_response(
    content: dict[str, Any],
    *,
    usage: dict[str, int] | None = None,
    model: str = MODEL,
    response_id: str = "chatcmpl-tg07a",
) -> bytes:
    """Build a deterministic local fixture response; never used for real I/O."""

    envelope: dict[str, Any] = {
        "id": response_id,
        "object": "chat.completion",
        "created": 1,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": canonical_json_bytes(content).decode("utf-8"),
                    "reasoning_content": None,
                },
                "finish_reason": "stop",
                "logprobs": None,
            }
        ],
        "system_fingerprint": "fp_tg07a_local_fixture",
    }
    if usage is not None:
        envelope["usage"] = deepcopy(usage)
    return canonical_json_bytes(envelope)


class DeepSeekContentAdapter:
    """One isolated two-stage session with strict hash-chained safe records."""

    __slots__ = ("transport", "object_id", "run_id", "_records", "_terminal", "_clock_ns")

    def __init__(
        self,
        *,
        transport: LocalInjectedTransport,
        object_id: str,
        run_id: str,
        clock_ns: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        if type(transport) is not LocalInjectedTransport:
            raise Tg07aContractError("provider_transport_invalid")
        if type(object_id) is not str or not object_id or len(object_id) > 128:
            raise Tg07aContractError("provider_binding_invalid")
        if type(run_id) is not str or not run_id or len(run_id) > 128:
            raise Tg07aContractError("provider_binding_invalid")
        if not callable(clock_ns):
            raise Tg07aContractError("provider_clock_invalid")
        self.transport = transport
        self.object_id = object_id
        self.run_id = run_id
        self._records: list[dict[str, Any]] = []
        self._terminal = False
        self._clock_ns = clock_ns

    def _expected_stage(self) -> str:
        return STAGES[len(self._records)] if len(self._records) < len(STAGES) else "complete"

    def _record(
        self,
        *,
        status: str,
        prepared: Any,
        transport_attempted: bool,
        http_status: int | None,
        response_received: bool,
        latency_ms: int,
        response_projection: dict[str, Any] | None,
        result: dict[str, Any] | None,
        usage: dict[str, int] | None,
        cost: dict[str, Any] | None,
        failure_code: str | None,
    ) -> dict[str, Any]:
        manifest = build_manifest()
        record = build_attempt_record(
            status=status,
            provider=PROVIDER,
            model=MODEL,
            config_sha256=manifest["manifest_sha256"],
            prompt_version=PLAN_PROMPT_VERSION if prepared.stage == STAGE_PLAN else CONTENT_PROMPT_VERSION,
            output_schema_version=manifest["output_schema_versions"][prepared.stage],
            stage=prepared.stage,
            object_id=self.object_id,
            run_id=self.run_id,
            sequence=len(self._records) + 1,
            transport_attempted=transport_attempted,
            automatic_retry_count=0,
            timeout_ms=prepared.safe_projection["timeout_ms"],
            http_status=http_status,
            provider_response_received=response_received,
            latency_ms=latency_ms,
            request_safe_projection=prepared.safe_projection,
            response_safe_projection=deepcopy(response_projection),
            structured_result=deepcopy(result),
            structured_result_sha256=(sha256_bytes(canonical_json_bytes(result)) if result is not None else None),
            usage=deepcopy(usage),
            cost=deepcopy(cost),
            failure_code=failure_code,
            execution_mode="offline_injected",
            transport_kind="local_injected",
            network_attempted=False,
            dns_attempted=False,
            credential_read_attempted=False,
            paid_call_performed=False,
            actual_paid_cost_cny_nanos=0,
            cost_semantics=("usage_pricing_estimate_not_invoice" if cost is not None else None),
            previous_record_sha256=(self._records[-1]["record_sha256"] if self._records else None),
        )
        self._records.append(record)
        if status == "failed" or len(self._records) == len(STAGES):
            self._terminal = True
        return deepcopy(record)

    def invoke(
        self,
        *,
        stage: str,
        stage_input: dict[str, Any],
        timeout_ms: int = 30_000,
        sensitive_values: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        if self._terminal:
            raise Tg07aContractError("provider_session_terminal")
        if stage != self._expected_stage():
            raise Tg07aContractError("provider_stage_order_invalid")
        prepared = build_chat_request(
            stage=stage,
            object_id=self.object_id,
            run_id=self.run_id,
            stage_input=stage_input,
            timeout_ms=timeout_ms,
        )
        if len(prepared.body) > MAX_REQUEST_BYTES:
            record = self._record(
                status="failed", prepared=prepared, transport_attempted=False,
                http_status=None, response_received=False, latency_ms=0,
                response_projection=None, result=None, usage=None, cost=None,
                failure_code="provider_request_too_large",
            )
            return {"status": "failed", "failure_code": record["failure_code"], "result": None, "record": record}
        for secret in sensitive_values:
            if type(secret) is str and secret and secret.encode("utf-8") in prepared.body:
                record = self._record(
                    status="failed", prepared=prepared, transport_attempted=False,
                    http_status=None, response_received=False, latency_ms=0,
                    response_projection=None, result=None, usage=None, cost=None,
                    failure_code="provider_sensitive_reflection",
                )
                return {
                    "status": "failed",
                    "failure_code": record["failure_code"],
                    "result": None,
                    "record": record,
                }

        start = self._clock_ns()
        response: TransportResponse | None = None
        transport_attempted = True
        response_projection: dict[str, Any] | None = None
        usage: dict[str, int] | None = None
        cost: dict[str, Any] | None = None
        safe_failure_status: int | None = None
        try:
            response = self.transport.post_json(url=ENDPOINT_URL, body=prepared.body, timeout_ms=timeout_ms)
            elapsed = max(0, (self._clock_ns() - start) // 1_000_000)
            if type(response) is not TransportResponse:
                raise TransportFailure() from None
            if response.final_url != ENDPOINT_URL:
                raise Tg07aContractError("provider_redirect_rejected")
            if type(response.status_code) is not int or not 100 <= response.status_code <= 599:
                raise Tg07aContractError("provider_http_status_invalid")
            if response.status_code != 200:
                raise Tg07aContractError("provider_http_status_invalid")
            if (
                type(response.content_type) is not str
                or response.content_type.split(";", 1)[0].strip().lower() != "application/json"
                or len(response.content_type) > 128
            ):
                raise Tg07aContractError("provider_content_type_invalid")
            parsed = parse_chat_completion(response.body, sensitive_values=sensitive_values)
            response_projection = parsed["response_safe_projection"]
            usage = parsed["usage"]
            cost = parsed["cost"]
            try:
                content_value = strict_json_loads(parsed["content"].encode("utf-8"))
                result = validate_stage_result(stage, content_value)
            except Tg07aContractError:
                raise Tg07aContractError("provider_content_invalid") from None
            record = self._record(
                status="succeeded", prepared=prepared, transport_attempted=True,
                http_status=200, response_received=True, latency_ms=elapsed,
                response_projection=response_projection, result=result, usage=usage,
                cost=cost, failure_code=None,
            )
            return {"status": "succeeded", "failure_code": None, "result": deepcopy(result), "record": record}
        except TransportTimeout:
            code = "provider_timeout"
        except TransportRedirect as exc:
            code = "provider_redirect_rejected"
            safe_failure_status = exc.status_code
        except TransportSensitiveReflection as exc:
            code = "provider_sensitive_reflection"
            safe_failure_status = exc.status_code
        except TransportFailure:
            code = "provider_transport_error"
        except Tg07aContractError as exc:
            code = exc.code if exc.code in FAILURE_CODES else "provider_transport_error"
        except BaseException:
            code = "provider_transport_error"
        elapsed = max(0, (self._clock_ns() - start) // 1_000_000)
        http_status = response.status_code if type(response) is TransportResponse and type(response.status_code) is int else safe_failure_status
        response_received = type(response) is TransportResponse or safe_failure_status is not None
        record = self._record(
            status="failed", prepared=prepared, transport_attempted=transport_attempted,
            http_status=http_status, response_received=response_received, latency_ms=elapsed,
            response_projection=response_projection, result=None, usage=usage, cost=cost,
            failure_code=code,
        )
        response = None
        return {"status": "failed", "failure_code": code, "result": None, "record": record}

    def transcript(self) -> dict[str, Any]:
        return finalize_transcript(object_id=self.object_id, run_id=self.run_id, records=self._records)
