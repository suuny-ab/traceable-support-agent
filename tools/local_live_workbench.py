"""Local-only live-chain acceptance server; never used by production.

This tool starts the real ``PublicRunService`` with a runner that mirrors
``DefaultProductRunner`` but injects deterministic offline transports derived
from the actual local retrieval result. It performs no Provider call, reads no
credential, and opens no socket beyond the loopback HTTP listener. Its purpose
is to let a developer verify the live-first workbench end to end (POST run,
status polling, projection, decision) without Provider authorization.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
API_SRC = REPO_ROOT / "api" / "src"
if str(API_SRC) not in sys.path:
    sys.path.insert(0, str(API_SRC))

from traceable_support.api.http import create_server  # noqa: E402
from traceable_support.api.runs import PublicRunService  # noqa: E402
from traceable_support.generation.checklist import build_clause_inventory  # noqa: E402
from traceable_support.product.boundaries import (  # noqa: E402
    build_boundary_handoff_package,
    evaluate_generation_boundary,
)
from traceable_support.product.qa import run_qa  # noqa: E402
from traceable_support.product.ticket import run_ticket  # noqa: E402
from traceable_support.product.types import ExecutionResult, RunInput  # noqa: E402
from traceable_support.provider.deepseek import (  # noqa: E402
    MODE_OFFLINE,
    OfflineInjectedTransport,
)
from traceable_support.provider.response import json_response  # noqa: E402
from traceable_support.retrieval.hybrid import (  # noqa: E402
    BusinessRetrievalRequest,
    ModelAwareRrfPipeline,
)

USAGE = {
    "prompt_tokens": 100,
    "completion_tokens": 100,
    "total_tokens": 200,
    "prompt_cache_hit_tokens": 0,
    "prompt_cache_miss_tokens": 100,
}


def _scripted_transport(task_type: str, text: str, product_model: str) -> OfflineInjectedTransport:
    """Build a two-step offline fixture bound to the real retrieval output."""

    result = ModelAwareRrfPipeline(unit_strategy="native_section", delivery_k=5).retrieve(
        BusinessRetrievalRequest(
            query_text=text,
            known_product_model=product_model,
            channel="qa",
            candidate_pool_limit=10,
            delivery_limit=5,
        )
    )
    evidence = [
        {"evidence_id": candidate.unit.unit_id, "text": candidate.unit.text}
        for candidate in result.candidate_hits
    ]
    inventory = build_clause_inventory(evidence)
    selected = inventory[0]
    first = selected["text"] if len(selected["text"]) <= 60 else selected["text"][:60]
    checklist = {
        "schema_version": "obligation-checklist-v4",
        "obligations": [
            {
                "obligation_id": "o1",
                "description": "覆盖检索到的首要来源 clause",
                "clause_ids": [selected["clause_id"]],
            }
        ],
        "ignored_clause_ids": [entry["clause_id"] for entry in inventory[1:]],
    }
    if task_type == "qa":
        step2 = {
            "schema_version": "retrieved-top10-qa-result-v4",
            "task_type": "qa",
            "content": {
                "kind": "qa_answer",
                "answer": {"text": f"本地离线验收答复。{first}"},
                "claims": [
                    {
                        "claim_id": "c1",
                        "exact_span_text": selected["text"],
                        "customer_visible_span_text": first,
                        "evidence_ids": [selected["evidence_id"]],
                        "obligation_ids": ["o1"],
                    }
                ],
                "insufficient_evidence": False,
            },
        }
    else:
        step2 = {
            "schema_version": "ticket-proposal-result-v3",
            "task_type": "ticket",
            "content": {
                "kind": "ticket_proposal",
                "action_steps": ["核对设备型号与故障现象", "按来源步骤处理并复核结果"],
                "draft_reply": f"本地离线验收答复。{first}",
                "claims": [
                    {
                        "claim_id": "c1",
                        "exact_span_text": selected["text"],
                        "customer_visible_span_text": first,
                        "evidence_ids": [selected["evidence_id"]],
                        "obligation_ids": ["o1"],
                    }
                ],
                "insufficient_evidence": False,
            },
        }
    return OfflineInjectedTransport(
        [
            {"kind": "response", "status_code": 200,
             "body": json_response(checklist, usage=USAGE, response_id="local-1")},
            {"kind": "response", "status_code": 200,
             "body": json_response(step2, usage=USAGE, response_id="local-2")},
        ]
    )


class ScriptedOfflineRunner:
    """Mirror DefaultProductRunner with per-input offline scripted transports."""

    is_ready = True

    def execute(self, run_input: RunInput, on_stage: Any) -> ExecutionResult:
        boundary = evaluate_generation_boundary(run_input.text, run_input.product_model)
        if boundary is not None:
            on_stage("preflight", "failed")
            ticket_input = None
            if run_input.task_type == "ticket":
                ticket_input = {
                    "ticket_id": "PUB-"
                    + hashlib.sha256(run_input.run_id.encode("utf-8")).hexdigest()[:24].upper(),
                    "product_model": run_input.product_model,
                    "issue_description": run_input.text,
                }
            package = build_boundary_handoff_package(
                task_type=run_input.task_type,
                text=run_input.text,
                product_model=run_input.product_model,
                run_id=run_input.run_id,
                decision=boundary,
                ticket=ticket_input,
            )
            return ExecutionResult(package=package, provider_call_count=0)
        transport = _scripted_transport(
            run_input.task_type, run_input.text, run_input.product_model
        )
        if run_input.task_type == "qa":
            package = run_qa(
                question=run_input.text,
                product_model=run_input.product_model,
                transport=transport,
                mode=MODE_OFFLINE,
                run_id=run_input.run_id,
                worst_cost_limit_cny_nanos=run_input.reserved_cny_nanos,
                on_stage=on_stage,
            )
        elif run_input.task_type == "ticket":
            from traceable_support.product.ticket_tools import CategoryTool, PriorityTool

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
                mode=MODE_OFFLINE,
                run_id=run_input.run_id,
                worst_cost_limit_cny_nanos=run_input.reserved_cny_nanos,
                on_stage=on_stage,
            )
        else:
            raise ValueError("product_task_type_invalid")
        return ExecutionResult(
            package=package, provider_call_count=transport.call_count
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--origin", default="http://localhost:3000")
    parser.add_argument(
        "--database",
        type=Path,
        default=Path(tempfile.gettempdir()) / "traceable-local-live.sqlite3",
    )
    args = parser.parse_args()
    service = PublicRunService(
        args.database,
        allowed_origin=args.origin,
        live_enabled=True,
        product_runner=ScriptedOfflineRunner(),
    )
    server = create_server(host=args.host, port=args.port, service=service)
    print(
        f"local live acceptance api on http://{args.host}:{args.port} "
        f"(origin {args.origin}, offline scripted transport, no Provider calls)"
    )
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        service.shutdown(wait=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
