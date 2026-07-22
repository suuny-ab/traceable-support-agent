"""Stable internal product execution contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol, runtime_checkable

StageCallback = Callable[[str, str], None]


@dataclass(frozen=True)
class RunInput:
    """The minimum data the product runner may receive from the public API."""

    run_id: str
    task_type: str
    text: str
    product_model: str
    reserved_cny_nanos: int


@dataclass(frozen=True)
class ExecutionResult:
    """A validated internal package and its observed Provider call count."""

    package: dict[str, Any]
    provider_call_count: int


@runtime_checkable
class ProductRunner(Protocol):
    """Product execution boundary consumed by the public control plane."""

    @property
    def is_ready(self) -> bool:
        """Return true only when every live dependency is assembled."""

    def execute(
        self,
        run_input: RunInput,
        on_stage: StageCallback,
    ) -> ExecutionResult:
        """Execute one bounded QA or ticket run."""
