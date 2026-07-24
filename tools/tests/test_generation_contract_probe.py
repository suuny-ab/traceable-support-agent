from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from tools import generation_contract_probe

    _IMPORT_ERROR: ModuleNotFoundError | None = None
except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
    generation_contract_probe = None
    _IMPORT_ERROR = exc


@unittest.skipUnless(
    generation_contract_probe is not None,
    f"live retrieval dependencies unavailable: {_IMPORT_ERROR}",
)
class GenerationContractProbeTest(unittest.TestCase):
    def _steps(self, case: dict) -> list[dict]:
        from traceable_support.generation.checklist import build_clause_inventory
        from traceable_support.retrieval.hybrid import (
            BusinessRetrievalRequest,
            ModelAwareRrfPipeline,
        )

        result = ModelAwareRrfPipeline(
            unit_strategy="native_section",
            delivery_k=5,
        ).retrieve(
            BusinessRetrievalRequest(
                query_text=case["input"],
                known_product_model=case["product_model"],
                channel="qa",
                candidate_pool_limit=10,
                delivery_limit=5,
            )
        )
        evidence = [
            {
                "evidence_id": hit.unit.unit_id,
                "document_id": hit.unit.document_id,
                "section_id": hit.unit.section_id,
                "text": hit.unit.text,
            }
            for hit in result.candidate_hits
        ]
        inventory = build_clause_inventory(evidence)
        expected_sections = set(case["expected"]["source_sections"])
        selected_evidence_ids = [
            entry["evidence_id"]
            for entry in evidence
            if f"{entry['document_id']}/{entry['section_id']}" in expected_sections
        ]
        self.assertTrue(selected_evidence_ids)
        obligations = []
        selected_clause_ids: set[str] = set()
        key_elements: list[str] = []
        claims = []
        for index, evidence_id in enumerate(selected_evidence_ids, start=1):
            clauses = [
                entry for entry in inventory if entry["evidence_id"] == evidence_id
            ]
            self.assertTrue(clauses)
            clause_ids = [entry["clause_id"] for entry in clauses]
            selected_clause_ids.update(clause_ids)
            key_element = clauses[0]["text"][:60]
            key_elements.append(key_element)
            obligation_id = f"o{index}"
            obligations.append(
                {
                    "obligation_id": obligation_id,
                    "description": f"覆盖来源 {evidence_id}",
                    "clause_ids": clause_ids,
                    "key_elements": [key_element],
                }
            )
            evidence_text = next(
                entry["text"]
                for entry in evidence
                if entry["evidence_id"] == evidence_id
            )
            claims.append(
                {
                    "claim_id": f"c{index}",
                    "exact_span_text": evidence_text,
                    "evidence_ids": [evidence_id],
                    "obligation_ids": [obligation_id],
                }
            )
        checklist = {
            "schema_version": "obligation-checklist-v3",
            "obligations": obligations,
            "ignored_clause_ids": [
                entry["clause_id"]
                for entry in inventory
                if entry["clause_id"] not in selected_clause_ids
            ],
        }
        visible = "；".join(
            case["expected"].get("required_facts", []) + key_elements
        )
        if case["task_type"] == "qa":
            generated = {
                "schema_version": "retrieved-top10-qa-result-v3",
                "task_type": "qa",
                "content": {
                    "kind": "qa_answer",
                    "answer": {"text": visible},
                    "claims": claims,
                    "insufficient_evidence": False,
                },
            }
        else:
            generated = {
                "schema_version": "ticket-proposal-result-v2",
                "task_type": "ticket",
                "content": {
                    "kind": "ticket_proposal",
                    "action_steps": [visible],
                    "draft_reply": visible,
                    "claims": claims,
                    "insufficient_evidence": False,
                },
            }
        return [
            {"kind": "response", "json": checklist},
            {"kind": "response", "json": generated},
        ]

    def _write_responses(self, path: Path, *, break_first: bool = False) -> None:
        cases = generation_contract_probe.load_cases()
        responses = {
            case["case_id"]: self._steps(case)
            for case in cases
        }
        if break_first:
            responses[cases[0]["case_id"]] = [
                {"kind": "response", "json": {"schema_version": "wrong"}}
            ]
        path.write_text(
            json.dumps(
                {
                    "schema_version": "generation-contract-probe-offline-v1",
                    "cases": responses,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def _run(self, name: str, *, break_first: bool = False) -> tuple[int, dict, dict]:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            responses = root / "responses.json"
            self._write_responses(responses, break_first=break_first)
            out = root / "private"
            report_path = root / "report.json"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = generation_contract_probe.main(
                    [
                        "--mode",
                        "offline",
                        "--offline-responses",
                        str(responses),
                        "--out",
                        str(out),
                        "--report",
                        str(report_path),
                        "--git-sha",
                        "0" * 40,
                    ]
                )
            report = json.loads(report_path.read_text(encoding="utf-8"))
            raw = json.loads(
                (out / "generation-contract-probe-raw.json").read_text(
                    encoding="utf-8"
                )
            )
            return code, report, raw

    def test_fixed_public_probe_passes_with_eight_injected_calls(self) -> None:
        code, report, raw = self._run("pass")

        self.assertEqual(code, 0)
        self.assertEqual(
            report["schema_version"],
            "generation-contract-probe-report-v1",
        )
        self.assertEqual(
            report["envelope"]["case_ids"],
            list(generation_contract_probe.CASE_IDS),
        )
        self.assertEqual(report["totals"]["cases_executed"], 4)
        self.assertEqual(report["totals"]["provider_calls"], 8)
        self.assertTrue(report["totals"]["passed"])
        self.assertEqual(report["generation_failures"]["failures"], 0)
        self.assertEqual(raw["schema_version"], "generation-contract-probe-raw-v1")
        self.assertTrue(all(case["passed"] for case in report["cases"]))

    def test_contract_failure_is_classified_without_false_success(self) -> None:
        code, report, _ = self._run("failure", break_first=True)

        self.assertEqual(code, 1)
        self.assertFalse(report["totals"]["passed"])
        self.assertEqual(report["generation_failures"]["failures"], 1)
        self.assertEqual(
            report["generation_failures"]["families"],
            {"checklist_shape": 1},
        )
        self.assertEqual(report["cases"][0]["observed_outcome"], "handoff")

    def test_lower_cost_cap_stops_before_first_reserved_call(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            responses = root / "responses.json"
            self._write_responses(responses)
            report_path = root / "report.json"
            code = generation_contract_probe.main(
                [
                    "--mode",
                    "offline",
                    "--offline-responses",
                    str(responses),
                    "--out",
                    str(root / "private"),
                    "--report",
                    str(report_path),
                    "--git-sha",
                    "0" * 40,
                    "--max-cost-cny",
                    "0.69",
                ]
            )
            report = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(code, 1)
        self.assertEqual(report["totals"]["cases_executed"], 0)
        self.assertEqual(report["totals"]["provider_calls"], 0)
        self.assertEqual(report["totals"]["reserved_cost_cny_nanos"], 0)
        self.assertEqual(report["totals"]["stop_code"], "cost_envelope_exceeded")


if __name__ == "__main__":
    unittest.main()
