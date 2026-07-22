"""Concrete product runner assembled explicitly by the live target."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from typing import Any

from .qa import run_qa
from .ticket import run_ticket
from .ticket_tools import CategoryTool, PriorityTool
from .types import ExecutionResult, RunInput, StageCallback


class DefaultProductRunner:
    """Execute the inherited two-stage product chain through an injected transport.

    Construction alone does not make a runner ready. The assembler must provide a
    transport factory and explicitly assert that its dependencies and credential
    boundary were checked. This prevents an API key alone from enabling live mode.
    """

    def __init__(
        self,
        *,
        transport_factory: Callable[[], Any] | None,
        transport_mode: str,
        dependencies_ready: bool = False,
    ) -> None:
        self._transport_factory = transport_factory
        self._transport_mode = transport_mode
        self._dependencies_ready = bool(dependencies_ready)

    @property
    def is_ready(self) -> bool:
        return self._dependencies_ready and self._transport_factory is not None

    def execute(
        self,
        run_input: RunInput,
        on_stage: StageCallback,
    ) -> ExecutionResult:
        if not self.is_ready or self._transport_factory is None:
            raise RuntimeError("product_runner_not_ready")
        transport = self._transport_factory()
        if run_input.task_type == "qa":
            package = run_qa(
                question=run_input.text,
                product_model=run_input.product_model,
                transport=transport,
                mode=self._transport_mode,
                run_id=run_input.run_id,
                worst_cost_limit_cny_nanos=run_input.reserved_cny_nanos,
                on_stage=on_stage,
            )
        elif run_input.task_type == "ticket":
            ticket_input = {
                "ticket_id": "PUB-"
                + hashlib.sha256(run_input.run_id.encode("utf-8")).hexdigest()[:24].upper(),
                "product_model": run_input.product_model,
                "issue_description": run_input.text,
            }
            ticket = {
                **ticket_input,
                "category": CategoryTool().execute(ticket_input)["category"],
                "priority": PriorityTool().execute(ticket_input)["priority"],
            }
            package = run_ticket(
                ticket=ticket,
                transport=transport,
                mode=self._transport_mode,
                run_id=run_input.run_id,
                worst_cost_limit_cny_nanos=run_input.reserved_cny_nanos,
                on_stage=on_stage,
            )
        else:
            raise ValueError("product_task_type_invalid")
        call_count = getattr(transport, "call_count", 0)
        return ExecutionResult(
            package=package,
            provider_call_count=call_count if type(call_count) is int else 0,
        )


__all__ = ["DefaultProductRunner"]
