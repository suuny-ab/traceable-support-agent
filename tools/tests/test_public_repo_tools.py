from __future__ import annotations

import json
import unittest

from tools.check_public_repo import Entry, _content_errors, _path_errors
from tools.release_manifest import build_manifest, verify_manifest


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
