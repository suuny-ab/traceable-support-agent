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
        visible_spans: list[str] = []
        claims = []
        for index, evidence_id in enumerate(selected_evidence_ids, start=1):
            clauses = [
                entry for entry in inventory if entry["evidence_id"] == evidence_id
            ]
            self.assertTrue(clauses)
            clause_ids = [entry["clause_id"] for entry in clauses]
            selected_clause_ids.update(clause_ids)
            visible_span = clauses[0]["text"][:60]
            visible_spans.append(visible_span)
            obligation_id = f"o{index}"
            obligations.append(
                {
                    "obligation_id": obligation_id,
                    "description": f"覆盖来源 {evidence_id}",
                    "clause_ids": clause_ids,
                }
            )
            claims.append(
                {
                    "claim_id": f"c{index}",
                    "exact_span_text": clauses[0]["text"],
                    "customer_visible_span_text": visible_span,
                    "evidence_ids": [evidence_id],
                    "obligation_ids": [obligation_id],
                }
            )
        checklist = {
            "schema_version": "obligation-checklist-v4",
            "obligations": obligations,
            "ignored_clause_ids": [
                entry["clause_id"]
                for entry in inventory
                if entry["clause_id"] not in selected_clause_ids
            ],
        }
        visible = "；".join(
            case["expected"].get("required_facts", []) + visible_spans
        )
        if case["task_type"] == "qa":
            generated = {
                "schema_version": "retrieved-top10-qa-result-v4",
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
                "schema_version": "ticket-proposal-result-v3",
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

    def _run(
        self,
        name: str,
        *,
        break_first: bool = False,
        profile: str = "full",
    ) -> tuple[int, dict, dict]:
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
                        "--profile",
                        profile,
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
            "generation-contract-probe-report-v4",
        )
        self.assertEqual(
            report["envelope"]["case_ids"],
            list(generation_contract_probe.CASE_IDS),
        )
        self.assertEqual(report["totals"]["cases_executed"], 4)
        self.assertEqual(report["totals"]["provider_calls"], 8)
        self.assertEqual(report["totals"]["usage_priced_calls"], 8)
        self.assertEqual(report["totals"]["unpriced_provider_calls"], 0)
        self.assertGreaterEqual(report["totals"]["provider_latency_ms"], 0)
        self.assertTrue(report["totals"]["passed"])
        self.assertEqual(report["generation_failures"]["failures"], 0)
        self.assertEqual(raw["schema_version"], "generation-contract-probe-raw-v4")
        self.assertEqual(
            report["identity"]["request_config"],
            {
                "step1_max_output_tokens": 16384,
                "step2_max_output_tokens": 16384,
                "timeout_ms": 180_000,
            },
        )
        self.assertTrue(
            all(len(case["provider_observations"]) == 2 for case in report["cases"])
        )
        self.assertTrue(
            all(
                observation["response_received"] is True
                and observation["timeout_ms"] == 180_000
                for case in report["cases"]
                for observation in case["provider_observations"]
            )
        )
        self.assertTrue(
            all(
                case["used_source_sections"]
                == raw_case["scoring"]["used_source_sections"]
                for case, raw_case in zip(report["cases"], raw["cases"], strict=True)
            )
        )
        self.assertTrue(all(case["passed"] for case in report["cases"]))

    def test_scoring_normalizes_nfkc_punctuation_without_semantic_model(self) -> None:
        self.assertEqual(
            generation_contract_probe._score_text("断电，检查。"),
            generation_contract_probe._score_text("断电,检查。"),
        )

    def test_diagnostic_profile_is_fixed_to_two_failed_cases(self) -> None:
        code, report, _ = self._run("diagnostic", profile="diagnostic-v2")

        self.assertEqual(code, 0)
        self.assertEqual(report["profile"], "diagnostic-v2")
        self.assertEqual(
            report["envelope"]["case_ids"],
            list(generation_contract_probe.DIAGNOSTIC_CASE_IDS),
        )
        self.assertEqual(report["envelope"]["max_cases"], 2)
        self.assertEqual(report["envelope"]["max_calls"], 4)
        self.assertEqual(report["envelope"]["max_cost_cny_nanos"], 1_400_000_000)
        self.assertEqual(report["totals"]["provider_calls"], 4)

    def test_finish_reason_profile_is_fixed_to_ticket_case(self) -> None:
        code, report, _ = self._run(
            "finish-reason",
            profile="finish-reason-v3",
        )

        self.assertEqual(code, 0)
        self.assertEqual(report["profile"], "finish-reason-v3")
        self.assertEqual(
            report["envelope"]["case_ids"],
            list(generation_contract_probe.FINISH_REASON_CASE_IDS),
        )
        self.assertEqual(report["envelope"]["max_cases"], 1)
        self.assertEqual(report["envelope"]["max_calls"], 2)
        self.assertEqual(report["envelope"]["max_cost_cny_nanos"], 700_000_000)
        self.assertEqual(report["totals"]["provider_calls"], 2)

    def test_length_recovery_profile_is_fixed_to_same_ticket_case(self) -> None:
        code, report, _ = self._run(
            "length-recovery",
            profile="length-recovery-v4",
        )

        self.assertEqual(code, 0)
        self.assertEqual(report["profile"], "length-recovery-v4")
        self.assertEqual(
            report["envelope"]["case_ids"],
            list(generation_contract_probe.LENGTH_RECOVERY_CASE_IDS),
        )
        self.assertEqual(report["envelope"]["max_cases"], 1)
        self.assertEqual(report["envelope"]["max_calls"], 2)
        self.assertEqual(report["envelope"]["max_cost_cny_nanos"], 700_000_000)
        self.assertEqual(report["totals"]["provider_calls"], 2)

    def test_obligation_count_profile_is_fixed_to_same_ticket_case(self) -> None:
        code, report, _ = self._run(
            "obligation-count",
            profile="obligation-count-v5",
        )

        self.assertEqual(code, 0)
        self.assertEqual(report["profile"], "obligation-count-v5")
        self.assertEqual(
            report["envelope"]["case_ids"],
            list(generation_contract_probe.OBLIGATION_COUNT_CASE_IDS),
        )
        self.assertEqual(report["envelope"]["max_cases"], 1)
        self.assertEqual(report["envelope"]["max_calls"], 2)
        self.assertEqual(report["envelope"]["max_cost_cny_nanos"], 700_000_000)
        self.assertEqual(report["totals"]["provider_calls"], 2)

    def test_remaining_ticket_profile_is_fixed_to_unexecuted_case(self) -> None:
        code, report, _ = self._run(
            "remaining-ticket",
            profile="remaining-ticket-v6",
        )

        self.assertEqual(code, 0)
        self.assertEqual(report["profile"], "remaining-ticket-v6")
        self.assertEqual(
            report["envelope"]["case_ids"],
            list(generation_contract_probe.REMAINING_TICKET_CASE_IDS),
        )
        self.assertEqual(report["envelope"]["max_cases"], 1)
        self.assertEqual(report["envelope"]["max_calls"], 2)
        self.assertEqual(report["envelope"]["max_cost_cny_nanos"], 700_000_000)
        self.assertEqual(report["totals"]["provider_calls"], 2)

    def test_semantic_qa_profile_is_fixed_to_representative_case(self) -> None:
        code, report, _ = self._run(
            "semantic-qa",
            profile="semantic-qa-v10",
        )

        self.assertEqual(code, 0)
        self.assertEqual(report["profile"], "semantic-qa-v10")
        self.assertEqual(
            report["envelope"]["case_ids"],
            list(generation_contract_probe.SEMANTIC_QA_CASE_IDS),
        )
        self.assertEqual(report["envelope"]["max_cases"], 1)
        self.assertEqual(report["envelope"]["max_calls"], 2)
        self.assertEqual(report["envelope"]["max_cost_cny_nanos"], 700_000_000)
        self.assertEqual(report["totals"]["provider_calls"], 2)

    def test_v4_checklist_validation_profiles_are_single_case_bounded(self) -> None:
        for profile, case_ids in (
            ("semantic-qa-v11", generation_contract_probe.SEMANTIC_QA_CASE_IDS),
            (
                "qa-length-recovery-v13",
                generation_contract_probe.SEMANTIC_QA_CASE_IDS,
            ),
            (
                "checklist-count-alignment-v14",
                generation_contract_probe.SEMANTIC_QA_CASE_IDS,
            ),
            (
                "semantic-ticket-v12",
                generation_contract_probe.REMAINING_TICKET_CASE_IDS,
            ),
        ):
            with self.subTest(profile=profile):
                code, report, _ = self._run(profile, profile=profile)
                self.assertEqual(code, 0)
                self.assertEqual(report["profile"], profile)
                self.assertEqual(report["envelope"]["case_ids"], list(case_ids))
                self.assertEqual(report["envelope"]["max_cases"], 1)
                self.assertEqual(report["envelope"]["max_calls"], 2)
                self.assertEqual(
                    report["envelope"]["max_cost_cny_nanos"],
                    700_000_000,
                )
                self.assertEqual(report["totals"]["provider_calls"], 2)

    def test_scoring_allows_bound_extra_sources_but_requires_expected_sources(
        self,
    ) -> None:
        case = generation_contract_probe.load_cases(("GEN-DEV-QA-003",))[0]
        expected_sections = case["expected"]["source_sections"]
        evidence = [
            {
                "evidence_id": f"E{index}",
                "document_id": section.split("/", 1)[0],
                "section_id": section.split("/", 1)[1],
            }
            for index, section in enumerate(
                [*expected_sections, "FAULT-CODES/e101-wheel-blocked"],
                start=1,
            )
        ]
        package = {
            "outcome": "candidate",
            "failure_classification": None,
            "worst_cost_cny_nanos": 0,
            "usage": [],
            "evidence": evidence,
            "answer": {
                "used_evidence_ids": [entry["evidence_id"] for entry in evidence],
                "content": {
                    "answer": {
                        "text": "；".join(case["expected"]["required_facts"]),
                    },
                },
            },
        }

        scoring = generation_contract_probe.score_case(case, package, 2)
        self.assertTrue(scoring["passed"])
        self.assertIn(
            "FAULT-CODES/e101-wheel-blocked",
            scoring["used_source_sections"],
        )

        package["answer"]["used_evidence_ids"] = [
            evidence[0]["evidence_id"],
            evidence[2]["evidence_id"],
        ]
        scoring = generation_contract_probe.score_case(case, package, 2)
        self.assertFalse(scoring["passed"])
        self.assertIn(
            "required_source_sections_missing",
            scoring["failure_codes"],
        )

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
