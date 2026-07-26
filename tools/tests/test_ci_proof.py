from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

from tools.ci_proof import (
    CATEGORIES,
    CLAIMS,
    SCHEMA_VERSION,
    ProofError,
    load_entries,
    main,
    missing_expected,
    record_result,
    render_summary,
    require_claim,
    run_command,
)


def passing_command() -> list[str]:
    return [sys.executable, "-c", "print('ok')"]


def failing_command() -> list[str]:
    return [sys.executable, "-c", "import sys; sys.exit(3)"]


class ClaimRegistryTest(unittest.TestCase):
    def test_every_claim_has_statement_boundary_and_remediation(self) -> None:
        for claim, (statement, boundary, remediation) in CLAIMS.items():
            with self.subTest(claim=claim):
                self.assertTrue(statement)
                self.assertTrue(remediation)
                self.assertIsInstance(boundary, str)

    def test_categories_are_fixed(self) -> None:
        self.assertEqual(set(CATEGORIES), {"product", "boundary", "external"})

    def test_unknown_claim_fails_closed(self) -> None:
        with self.assertRaisesRegex(ProofError, "unknown_claim"):
            require_claim("no.such.claim")


class RunCommandTest(unittest.TestCase):
    def test_pass_records_proof_entry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            proof = Path(directory, "proof.jsonl")
            exit_code = run_command(
                "web.static-contract", "product", proof, passing_command()
            )
            self.assertEqual(exit_code, 0)
            entries = load_entries(proof)
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["schema_version"], SCHEMA_VERSION)
        self.assertEqual(entry["claim"], "web.static-contract")
        self.assertEqual(entry["category"], "product")
        self.assertEqual(entry["status"], "pass")
        self.assertEqual(entry["exit_code"], 0)

    def test_failure_records_and_propagates_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            proof = Path(directory, "proof.jsonl")
            captured = io.StringIO()
            with contextlib.redirect_stderr(captured):
                exit_code = run_command(
                    "api.product-tests", "product", proof, failing_command()
                )
            self.assertEqual(exit_code, 3)
            entry = load_entries(proof)[0]
        self.assertEqual(entry["status"], "fail")
        self.assertEqual(entry["exit_code"], 3)
        failure_output = captured.getvalue()
        self.assertIn("ci_failure category=product claim=api.product-tests", failure_output)
        self.assertIn("::error title=ci[product] api.product-tests::", failure_output)
        self.assertIn("处理入口", failure_output)

    def test_run_prints_attribution_before_command(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            proof = Path(directory, "proof.jsonl")
            captured = io.StringIO()
            with contextlib.redirect_stdout(captured):
                self.assertEqual(
                    run_command(
                        "web.static-contract", "product", proof, passing_command()
                    ),
                    0,
                )
        lines = captured.getvalue().splitlines()
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith("ci_check claim=web.static-contract"))

    def test_unknown_category_and_empty_command_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            proof = Path(directory, "proof.jsonl")
            with self.assertRaisesRegex(ProofError, "unknown_category"):
                run_command("web.static-contract", "infra", proof, passing_command())
            with self.assertRaisesRegex(ProofError, "missing_command"):
                run_command("web.static-contract", "product", proof, [])
            self.assertFalse(proof.exists())


class RecordResultTest(unittest.TestCase):
    def test_record_pass_and_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            proof = Path(directory, "proof.jsonl")
            captured = io.StringIO()
            with contextlib.redirect_stderr(captured):
                self.assertEqual(
                    record_result("containers.image-build", "product", 0, proof), 0
                )
                self.assertEqual(
                    record_result("containers.replay-smoke", "product", 1, proof), 1
                )
            entries = load_entries(proof)
        self.assertEqual(
            [entry["status"] for entry in entries], ["pass", "fail"]
        )
        self.assertEqual(entries[1]["exit_code"], 1)
        self.assertIn(
            "::error title=ci[product] containers.replay-smoke::", captured.getvalue()
        )

    def test_record_rejects_unknown_category(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            proof = Path(directory, "proof.jsonl")
            with self.assertRaisesRegex(ProofError, "unknown_category"):
                record_result("containers.image-build", "infra", 1, proof)


class SkipAndSummaryTest(unittest.TestCase):
    def test_skip_records_reason_and_summary_marks_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            proof = Path(directory, "proof.jsonl")
            exit_code = main(
                [
                    "skip",
                    "--claim",
                    "web.build-and-tests",
                    "--claim",
                    "web.routes",
                    "--reason",
                    "governance_only",
                    "--proof",
                    str(proof),
                ]
            )
            self.assertEqual(exit_code, 0)
            entries = load_entries(proof)
            text = render_summary("web", entries)
        self.assertEqual([entry["status"] for entry in entries], ["skipped", "skipped"])
        self.assertIn("governance_only", text)
        self.assertIn("跳过=2", text)
        self.assertIn("跳过与未执行表示该检查本次没有证明任何东西", text)

    def test_summary_counts_and_failure_remediation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            proof = Path(directory, "proof.jsonl")
            run_command("web.static-contract", "product", proof, passing_command())
            with contextlib.redirect_stderr(io.StringIO()):
                run_command("api.product-tests", "product", proof, failing_command())
            text = render_summary("mixed", load_entries(proof))
        self.assertIn("证明=1", text)
        self.assertIn("失败=1", text)
        self.assertIn("docs/engineering/quality.md", text)

    def test_missing_proof_file_explains_itself(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            text = render_summary("web", load_entries(Path(directory, "none.jsonl")))
        self.assertIn("合同检查执行前失败", text)

    def test_expected_claims_never_run_are_listed_as_missing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            proof = Path(directory, "proof.jsonl")
            with contextlib.redirect_stderr(io.StringIO()):
                run_command("web.static-contract", "product", proof, failing_command())
            text = render_summary(
                "web",
                load_entries(proof),
                ["web.static-contract", "web.build-and-tests", "web.routes"],
            )
        self.assertIn("未执行", text)
        self.assertIn("未执行=2", text)
        self.assertIn("没有证明任何东西", text)

    def test_missing_expected_counts_only_unrecorded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            proof = Path(directory, "proof.jsonl")
            main(
                [
                    "skip",
                    "--claim",
                    "web.routes",
                    "--reason",
                    "governance_only",
                    "--proof",
                    str(proof),
                ]
            )
            entries = load_entries(proof)
        self.assertEqual(
            missing_expected(entries, ["web.routes", "web.static-contract"]),
            ["web.static-contract"],
        )

    def test_summary_cli_fails_closed_on_missing_expected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            proof = Path(directory, "proof.jsonl")
            run_command("web.static-contract", "product", proof, passing_command())
            captured = io.StringIO()
            with contextlib.redirect_stderr(captured):
                exit_code = main(
                    [
                        "summary",
                        "--job",
                        "web",
                        "--proof",
                        str(proof),
                        "--expect",
                        "web.static-contract",
                        "--expect",
                        "web.routes",
                    ]
                )
            self.assertEqual(exit_code, 1)
            self.assertIn("missing=web.routes", captured.getvalue())

    def test_summary_cli_passes_when_all_expected_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            proof = Path(directory, "proof.jsonl")
            run_command("web.static-contract", "product", proof, passing_command())
            main(
                [
                    "skip",
                    "--claim",
                    "web.routes",
                    "--reason",
                    "governance_only",
                    "--proof",
                    str(proof),
                ]
            )
            exit_code = main(
                [
                    "summary",
                    "--job",
                    "web",
                    "--proof",
                    str(proof),
                    "--expect",
                    "web.static-contract",
                    "--expect",
                    "web.routes",
                ]
            )
            self.assertEqual(exit_code, 0)

    def test_summary_cli_writes_step_summary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            proof = Path(directory, "proof.jsonl")
            step_summary = Path(directory, "summary.md")
            run_command("web.static-contract", "product", proof, passing_command())
            exit_code = main(
                [
                    "summary",
                    "--job",
                    "web",
                    "--proof",
                    str(proof),
                    "--step-summary",
                    str(step_summary),
                ]
            )
            self.assertEqual(exit_code, 0)
            written = step_summary.read_text(encoding="utf-8")
        self.assertIn("CI 证明合同 — web", written)

    def test_corrupt_proof_entry_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            proof = Path(directory, "proof.jsonl")
            proof.write_text("not json\n", encoding="utf-8")
            with self.assertRaisesRegex(ProofError, "proof_entry_invalid"):
                load_entries(proof)


if __name__ == "__main__":
    unittest.main()
