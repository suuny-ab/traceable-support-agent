"""Explicit live-runner assembly for the public API process.

The public service stays ``replay_only`` unless every gate is satisfied in the
same process: the operator sets ``TRACEABLE_PUBLIC_LIVE_ENABLED``, the frozen
embedding model inventory validates, the synthetic corpus is complete, the
retrieval dependency imports, and a provider credential placeholder exists.
Only the presence of the credential variable is checked here; the value is
never read, logged, or persisted by the assembly path.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

from ..product.qa import default_qa_transport
from ..product.runner import DefaultProductRunner
from ..provider.deepseek import MODE_AUTHORIZED_REAL
from ..retrieval.candidates import (
    load_local_model_manifest,
    validate_local_model_files,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
KNOWLEDGE_DIR = REPOSITORY_ROOT / "data" / "knowledge" / "synthetic-kb-v1"
EXPECTED_KNOWLEDGE_FILES = frozenset(
    {
        "after-sales-policy.md",
        "common-faq.md",
        "customer-service-sop.json",
        "fault-codes.json",
        "manual-cz-r1.md",
        "manual-cz-r2.md",
    }
)
CREDENTIAL_ENV = "DEEPSEEK_API_KEY"


def live_dependencies_ready() -> bool:
    """Return True only when every local live dependency verifies cleanly."""

    try:
        validate_local_model_files(load_local_model_manifest())
    except (OSError, ValueError):
        return False
    if not KNOWLEDGE_DIR.is_dir():
        return False
    present = {path.name for path in KNOWLEDGE_DIR.iterdir() if path.is_file()}
    if not EXPECTED_KNOWLEDGE_FILES.issubset(present):
        return False
    if importlib.util.find_spec("fastembed") is None:
        return False
    return CREDENTIAL_ENV in os.environ


def assemble_product_runner() -> DefaultProductRunner:
    """Build the runner; ``is_ready`` stays False until the gate passes."""

    return DefaultProductRunner(
        transport_factory=default_qa_transport,
        transport_mode=MODE_AUTHORIZED_REAL,
        dependencies_ready=live_dependencies_ready(),
    )


__all__ = [
    "CREDENTIAL_ENV",
    "EXPECTED_KNOWLEDGE_FILES",
    "KNOWLEDGE_DIR",
    "assemble_product_runner",
    "live_dependencies_ready",
]
