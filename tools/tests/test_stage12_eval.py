"""Offline tests for the Stage 12 evaluation runner and freeze checker.

Every execution test injects scripted responses through the offline transport:
zero network, zero Provider calls. Retrieval runs against the local synthetic
corpus exactly like the reviewed api product tests do.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# The governance CI job runs the tools tests without the live retrieval
# dependencies (numpy/fastembed).  Guard each import chain separately so the
# freeze-checker tests (stdlib-only by design) still run there while the
# product-chain evaluation tests skip instead of erroring at import time.
try:
    from tools import stage12_freeze_check

    _FREEZE_IMPORT_ERROR: ModuleNotFoundError | None = None
except ModuleNotFoundError as exc:  # pragma: no cover - depends on environment
    stage12_freeze_check = None
    _FREEZE_IMPORT_ERROR = exc

try:
    from tools import stage12_eval

    _EVAL_IMPORT_ERROR: ModuleNotFoundError | None = None
except ModuleNotFoundError as exc:  # pragma: no cover - depends on environment
    stage12_eval = None
    _EVAL_IMPORT_ERROR = exc

QUESTION = "CZ-R1 怎么开始局部清扫？"
USAGE = {
    "prompt_tokens": 100,
    "completion_tokens": 100,
    "total_tokens": 200,
    "prompt_cache_hit_tokens": 0,
    "prompt_cache_miss_tokens": 100,
}


def _top_hit(channel: str):
    from traceable_support.retrieval.hybrid import (
        BusinessRetrievalRequest,
        ModelAwareRrfPipeline,
    )

    result = ModelAwareRrfPipeline(unit_strategy="native_section", delivery_k=5).retrieve(
        BusinessRetrievalRequest(
            query_text=QUESTION,
            known_product_model="CZ-R1",
            channel=channel,
            candidate_pool_limit=10,
            delivery_limit=5,
        )
    )
    return result.candidate_hits[0].unit


def _retrieved_evidence() -> list[dict]:
    from traceable_support.retrieval.hybrid import (
        BusinessRetrievalRequest,
        ModelAwareRrfPipeline,
    )

    result = ModelAwareRrfPipeline(unit_strategy="native_section", delivery_k=5).retrieve(
        BusinessRetrievalRequest(
            query_text=QUESTION,
            known_product_model="CZ-R1",
            channel="qa",
            candidate_pool_limit=10,
            delivery_limit=5,
        )
    )
    return [
        {"evidence_id": candidate.unit.unit_id, "text": candidate.unit.text}
        for candidate in result.candidate_hits
    ]


def _checklist(selected: dict, ignored: list[str]) -> dict:
    return {
        "schema_version": "obligation-checklist-v4",
        "obligations": [
            {
                "obligation_id": "o1",
                "description": "义务",
                "clause_ids": [selected["clause_id"]],
            }
        ],
        "ignored_clause_ids": ignored,
    }


def _qa_steps(hit, *, valid: bool = True) -> list[dict]:
    from traceable_support.generation.checklist import build_clause_inventory

    if not valid:
        return [{"kind": "response", "json": {"schema_version": "wrong"}, "usage": USAGE}]
    inventory = build_clause_inventory(_retrieved_evidence())
    selected = inventory[0]
    first = selected["text"][:60]
    answer = {
        "schema_version": "retrieved-top10-qa-result-v4",
        "task_type": "qa",
        "content": {
            "kind": "qa_answer",
            "answer": {"text": f"回答。{first}"},
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
    return [
        {
            "kind": "response",
            "json": _checklist(
                selected,
                [entry["clause_id"] for entry in inventory[1:]],
            ),
            "usage": USAGE,
        },
        {"kind": "response", "json": answer, "usage": USAGE},
    ]


def _ticket_steps(hit, *, valid: bool = True) -> list[dict]:
    from traceable_support.generation.checklist import build_clause_inventory

    if not valid:
        return [{"kind": "response", "json": {"schema_version": "wrong"}, "usage": USAGE}]
    inventory = build_clause_inventory(_retrieved_evidence())
    selected = inventory[0]
    first = selected["text"][:60]
    proposal = {
        "schema_version": "ticket-proposal-result-v3",
        "task_type": "ticket",
        "content": {
            "kind": "ticket_proposal",
            "action_steps": ["步骤一"],
            "draft_reply": f"客户回复。{first}",
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
    return [
        {
            "kind": "response",
            "json": _checklist(
                selected,
                [entry["clause_id"] for entry in inventory[1:]],
            ),
            "usage": USAGE,
        },
        {"kind": "response", "json": proposal, "usage": USAGE},
    ]


def _case(case_id: str, task_type: str, hit, *, outcome: str = "candidate") -> dict:
    from traceable_support.generation.checklist import _clauses

    clauses = _clauses(hit.text)
    expected = {
        "outcome": outcome,
        "source_sections": [f"{hit.document_id}/{hit.section_id}"],
        "required_facts": [clauses[0][:60]],
    }
    if task_type == "ticket":
        expected["category"] = "使用咨询"
        expected["priority"] = "P2-普通"
    return {
        "case_id": case_id,
        "task_type": task_type,
        "product_model": "CZ-R1",
        "input": QUESTION,
        "expected": expected,
    }


@unittest.skipUnless(
    stage12_eval is not None,
    f"live retrieval dependencies unavailable: {_EVAL_IMPORT_ERROR}",
)
class Stage12EvalTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.qa_hit = _top_hit("qa")
        cls.ticket_hit = _top_hit("ticket")
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def _write_run(
        self,
        name: str,
        cases: list[dict],
        responses: dict[str, list[dict]],
        *,
        extra_args: list[str] | None = None,
    ) -> tuple[int, dict, dict]:
        run_dir = self.root / name
        run_dir.mkdir(parents=True, exist_ok=True)
        set_path = run_dir / "unseen.json"
        set_path.write_text(
            json.dumps(
                {"schema_version": "stage12-unseen-v1", "cases": cases},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        responses_path = run_dir / "unseen.offline-responses.json"
        responses_path.write_text(
            json.dumps(
                {
                    "schema_version": "stage12-offline-responses-v1",
                    "cases": responses,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        out_dir = run_dir / "private"
        report_path = run_dir / "report.json"
        argv = [
            "--set", str(set_path),
            "--out", str(out_dir),
            "--report", str(report_path),
            "--git-sha", "0" * 40,
        ] + (extra_args or [])
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = stage12_eval.main(argv)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        raw = json.loads((out_dir / "stage12-raw-records.json").read_text(encoding="utf-8"))
        return code, report, raw

    def _passing_pair(self) -> tuple[list[dict], dict[str, list[dict]]]:
        cases = [
            _case("STG12-TEST-MSQ-001", "qa", self.qa_hit),
            _case("STG12-TEST-ATK-001", "ticket", self.ticket_hit),
        ]
        responses = {
            "STG12-TEST-MSQ-001": _qa_steps(self.qa_hit),
            "STG12-TEST-ATK-001": _ticket_steps(self.ticket_hit),
        }
        return cases, responses

    def test_offline_full_pass(self) -> None:
        cases, responses = self._passing_pair()
        code, report, raw = self._write_run("pass", cases, responses)
        self.assertEqual(code, 0)
        self.assertEqual(report["schema_version"], "stage12-aggregate-v1")
        self.assertEqual(report["totals"]["cases_executed"], 2)
        self.assertEqual(report["totals"]["provider_calls"], 4)
        self.assertFalse(report["totals"]["stopped_early"])
        self.assertEqual(report["generation_failures"]["failures"], 0)
        self.assertTrue(all(case["passed"] for case in report["cases"]))
        self.assertEqual(report["cases"][0]["dimension"], "multi-source-qa")
        self.assertEqual(report["cases"][1]["dimension"], "approvable-ticket")
        self.assertEqual(report["identity"]["git_sha"], "0" * 40)
        self.assertEqual(len(report["identity"]["unseen_set_sha256"]), 64)
        self.assertEqual(raw["cases"][0]["package"]["outcome"], "candidate")

    def test_source_sections_mismatch_is_reported(self) -> None:
        cases, responses = self._passing_pair()
        cases[0]["expected"]["source_sections"] = ["COMMON-FAQ/other-section"]
        code, report, _ = self._write_run("source", cases, responses)
        self.assertEqual(code, 1)
        self.assertIn("source_sections_mismatch", report["cases"][0]["failure_codes"])
        self.assertTrue(report["cases"][1]["passed"])

    def test_boundary_handoff_sources_are_scored_without_a_generated_proposal(self) -> None:
        case = {
            "case_id": "STG12-TEST-MH-001",
            "task_type": "ticket",
            "product_model": "CZ-R1",
            "input": "R1刚吸进一小滩水，我想继续开机把剩下的吸完。",
            "expected": {
                "outcome": "handoff",
                "handoff_reason": "safety_risk",
                "source_sections": [
                    "COMMON-FAQ/wet-environment",
                    "CUSTOMER-SERVICE-SOP/manual-escalation",
                ],
                "required_facts": [],
                "category": "安全风险",
                "priority": "P0-紧急",
            },
        }
        runner = stage12_eval.DefaultProductRunner(
            transport_factory=lambda: self.fail("transport factory must not be called"),
            transport_mode="offline_injected",
            dependencies_ready=True,
        )
        execution = runner.execute(
            stage12_eval.RunInput(
                case["case_id"],
                case["task_type"],
                case["input"],
                case["product_model"],
                1,
            ),
            lambda _stage, _status: None,
        )
        score = stage12_eval.score_case(
            case,
            execution.package,
            execution.provider_call_count,
            1,
        )
        self.assertTrue(score["passed"], score)
        self.assertEqual(
            score["detail"]["used_source_sections"],
            sorted(case["expected"]["source_sections"]),
        )

    def test_missing_required_fact_is_reported(self) -> None:
        cases, responses = self._passing_pair()
        cases[0]["expected"]["required_facts"] = ["正文中绝不存在的事实片段zz"]
        code, report, _ = self._write_run("fact", cases, responses)
        self.assertEqual(code, 1)
        self.assertIn("required_fact_missing", report["cases"][0]["failure_codes"])

    def test_required_fact_scoring_normalizes_nfkc_punctuation(self) -> None:
        self.assertEqual(
            stage12_eval._score_text("断电，检查。"),
            stage12_eval._score_text("断电,检查。"),
        )

    def test_unexpected_handoff_is_reported(self) -> None:
        cases, responses = self._passing_pair()
        responses["STG12-TEST-ATK-001"] = _ticket_steps(self.ticket_hit, valid=False)
        code, report, raw = self._write_run("handoff", cases, responses)
        self.assertEqual(code, 1)
        ticket_case = report["cases"][1]
        self.assertIn("outcome_mismatch", ticket_case["failure_codes"])
        self.assertEqual(ticket_case["observed_outcome"], "handoff")
        self.assertEqual(
            ticket_case["generation_failure"]["phase"],
            "enumeration_contract",
        )
        self.assertEqual(
            report["generation_failures"]["families"],
            {"checklist_shape": 1},
        )
        self.assertTrue(
            raw["cases"][1]["package"]["handoff_reason"].startswith(
                "enumeration_contract_failure"
            )
        )

    def test_call_envelope_stops_execution(self) -> None:
        cases, responses = self._passing_pair()
        code, report, _ = self._write_run(
            "envelope", cases, responses, extra_args=["--max-calls", "2"]
        )
        self.assertEqual(code, 1)
        self.assertEqual(report["totals"]["cases_executed"], 1)
        self.assertEqual(report["totals"]["provider_calls"], 2)
        self.assertTrue(report["totals"]["stopped_early"])
        self.assertEqual(report["totals"]["stop_code"], "envelope_exceeded")

    def test_public_report_contains_no_plaintext(self) -> None:
        cases, responses = self._passing_pair()
        code, report, _ = self._write_run("noplain", cases, responses)
        self.assertEqual(code, 0)
        report_path = self.root / "noplain" / "report.json"
        report_text = report_path.read_text(encoding="utf-8")
        self.assertNotIn(QUESTION, report_text)
        fact = cases[0]["expected"]["required_facts"][0]
        self.assertNotIn(fact, report_text)
        self.assertNotIn("回答。", report_text)
        self.assertNotIn("客户回复。", report_text)
        raw_text = (self.root / "noplain" / "private" / "stage12-raw-records.json").read_text(
            encoding="utf-8"
        )
        self.assertIn(fact, raw_text)

    def test_real_mode_setup_never_reads_credential(self) -> None:
        from traceable_support.product.qa import default_qa_transport
        from traceable_support.product.runner import DefaultProductRunner
        from traceable_support.provider.deepseek import MODE_AUTHORIZED_REAL

        reads: list[str] = []
        real_get = os.environ.get

        def spy(key, default=None):
            reads.append(key)
            return real_get(key, default)

        with mock.patch.object(os.environ, "get", spy):
            stage12_eval._arguments(
                ["--set", "s", "--out", "o", "--report", "r", "--mode", "real"]
            )
            runner = DefaultProductRunner(
                transport_factory=default_qa_transport,
                transport_mode=MODE_AUTHORIZED_REAL,
                dependencies_ready=True,
            )
            self.assertTrue(runner.is_ready)
            default_qa_transport()
        self.assertNotIn("DEEPSEEK_API_KEY", reads)

    def test_real_mode_without_key_fails_closed_without_network(self) -> None:
        cases, responses = self._passing_pair()
        run_dir = self.root / "real"
        run_dir.mkdir(parents=True, exist_ok=True)
        set_path = run_dir / "unseen.json"
        set_path.write_text(
            json.dumps({"schema_version": "stage12-unseen-v1", "cases": cases[:1]},
                       ensure_ascii=False),
            encoding="utf-8",
        )
        report_path = run_dir / "report.json"
        argv = [
            "--set", str(set_path),
            "--out", str(run_dir / "private"),
            "--report", str(report_path),
            "--mode", "real",
        ]
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("DEEPSEEK_API_KEY", None)
            with contextlib.redirect_stdout(io.StringIO()):
                code = stage12_eval.main(argv)
        self.assertEqual(code, 1)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["totals"]["stop_code"], "execution_failure_stop")
        self.assertEqual(report["cases"][0]["observed_outcome"], "handoff")
        raw = json.loads(
            (run_dir / "private" / "stage12-raw-records.json").read_text(encoding="utf-8")
        )
        self.assertIn(
            "provider_credential_missing",
            raw["cases"][0]["package"]["handoff_reason"],
        )


@unittest.skipUnless(
    stage12_freeze_check is not None,
    f"freeze checker dependencies unavailable: {_FREEZE_IMPORT_ERROR}",
)
class Stage12FreezeCheckTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.corpus_root = REPO_ROOT / "data" / "knowledge"
        cls.section_texts = stage12_freeze_check._load_section_texts(cls.corpus_root)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def _write_set(self, name: str, cases: list[dict]) -> Path:
        path = self.root / name
        path.write_text(
            json.dumps(
                {"schema_version": "stage12-unseen-v1", "cases": cases},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return path

    def _valid_case(self, fact: str) -> dict:
        section = sorted(self.section_texts)[0]
        return {
            "case_id": "STG12-TEST-MSQ-001",
            "task_type": "qa",
            "product_model": "CZ-R1",
            "input": "合成问题？",
            "expected": {
                "outcome": "candidate",
                "source_sections": [section],
                "required_facts": [fact],
            },
        }

    def test_valid_sample_passes_and_prints_sha256(self) -> None:
        section = sorted(self.section_texts)[0]
        fact = self.section_texts[section][:40]
        set_path = self._write_set("valid.json", [self._valid_case(fact)])
        self.assertEqual(
            stage12_freeze_check.validate_set(set_path, self.corpus_root), []
        )
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = stage12_freeze_check.main([str(set_path), "--corpus-root", str(self.corpus_root)])
        self.assertEqual(code, 0)
        self.assertIn("freeze_check=passed", stdout.getvalue())
        self.assertIn("unseen_set_sha256=", stdout.getvalue())

    def test_fabricated_fact_is_rejected(self) -> None:
        set_path = self._write_set(
            "fake.json", [self._valid_case("语料中绝不存在的伪造事实zz")]
        )
        problems = stage12_freeze_check.validate_set(set_path, self.corpus_root)
        self.assertTrue(any("required_fact" in problem for problem in problems))
        with contextlib.redirect_stdout(io.StringIO()):
            code = stage12_freeze_check.main([str(set_path), "--corpus-root", str(self.corpus_root)])
        self.assertEqual(code, 1)

    def test_unknown_source_section_is_rejected(self) -> None:
        case = self._valid_case("任意事实")
        case["expected"]["source_sections"] = ["COMMON-FAQ/no-such-section"]
        set_path = self._write_set("missing.json", [case])
        problems = stage12_freeze_check.validate_set(set_path, self.corpus_root)
        self.assertTrue(any("not in corpus" in problem for problem in problems))


class Stage12PublishedAggregateTest(unittest.TestCase):
    def _load(self, name: str) -> dict:
        return json.loads((REPO_ROOT / "evals" / name).read_text(encoding="utf-8"))

    def test_original_and_post_fix_observations_remain_distinct(self) -> None:
        original = self._load("stage12-aggregate-v1.json")
        post_fix = self._load("stage12-post-fix-revalidation-v1.json")

        self.assertEqual(original["totals"]["cases_planned"], 24)
        self.assertEqual(original["totals"]["cases_executed"], 19)
        self.assertEqual(sum(case["passed"] for case in original["cases"]), 9)
        self.assertEqual(original["totals"]["stop_code"], "execution_failure_stop")

        self.assertEqual(post_fix["totals"]["cases_planned"], 24)
        self.assertEqual(post_fix["totals"]["cases_executed"], 24)
        self.assertEqual(sum(case["passed"] for case in post_fix["cases"]), 2)
        self.assertEqual(post_fix["totals"]["provider_calls"], 39)
        self.assertEqual(post_fix["totals"]["estimated_cost_cny_nanos"], 1_259_912_400)
        self.assertFalse(post_fix["totals"]["stopped_early"])
        self.assertIsNone(post_fix["totals"]["stop_code"])
        self.assertEqual(post_fix["envelope"]["automatic_retry_count"], 0)
        original_ids = {case["case_id"] for case in original["cases"]}
        post_fix_ids = {case["case_id"] for case in post_fix["cases"]}
        self.assertLess(original_ids, post_fix_ids)
        self.assertEqual(
            post_fix_ids - original_ids,
            {
                "STG12-01-FC-002", "STG12-01-FC-003",
                "STG12-01-SO-001", "STG12-01-SO-002", "STG12-01-SO-003",
            },
        )
        self.assertEqual(
            post_fix["identity"]["unseen_set_sha256"],
            original["identity"]["unseen_set_sha256"],
        )

    def test_post_fix_identity_and_public_projection_are_frozen(self) -> None:
        path = REPO_ROOT / "evals" / "stage12-post-fix-revalidation-v1.json"
        payload = self._load(path.name)
        self.assertEqual(
            hashlib.sha256(path.read_bytes()).hexdigest(),
            "2de8d63be45974bcb58fdbc2d43d75d470854ae4268a7a30d229989a136b57b9",
        )
        self.assertEqual(
            payload["identity"],
            {
                "git_sha": "df01968c56350626544ca4acc4ed88cf13dfd337",
                "image_digest": (
                    "sha256:95d6a0b5dad4d4a9a9e070525fccdef78cf2301a4e98ae6682678ba423fd48a1"
                ),
                "model": "deepseek-v4-pro",
                "prompt_sha256": (
                    "108ab9aae60eb86806383cc2fea4511d358955f50503531e0da2e82be1ba8584"
                ),
                "unseen_set_sha256": (
                    "7d73073cd0227b0ced81398fcbadc7e5f85867a633a9654d82bd0b516c358ab0"
                ),
            },
        )
        forbidden_keys = {
            "input", "required_facts", "source_sections", "answer", "proposal",
            "request_headers", "provider_response",
        }

        def walk(value: object) -> None:
            if isinstance(value, dict):
                self.assertTrue(forbidden_keys.isdisjoint(value))
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)

        walk(payload)


if __name__ == "__main__":
    unittest.main()
