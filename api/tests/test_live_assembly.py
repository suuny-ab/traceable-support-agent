import os

from traceable_support.api import live_assembly
from traceable_support.product.runner import DefaultProductRunner


def test_dependencies_fail_closed_without_credential(monkeypatch):
    monkeypatch.delenv(live_assembly.CREDENTIAL_ENV, raising=False)
    assert live_assembly.live_dependencies_ready() is False


def test_dependencies_fail_closed_without_model_files(monkeypatch, tmp_path):
    monkeypatch.setenv(live_assembly.CREDENTIAL_ENV, "placeholder-not-read")
    monkeypatch.setenv("TRACEABLE_MODEL_ROOT", str(tmp_path))
    assert live_assembly.live_dependencies_ready() is False


def test_dependencies_fail_closed_with_incomplete_corpus(monkeypatch, tmp_path):
    monkeypatch.setenv(live_assembly.CREDENTIAL_ENV, "placeholder-not-read")
    monkeypatch.setattr(live_assembly, "KNOWLEDGE_DIR", tmp_path)
    assert live_assembly.live_dependencies_ready() is False


def test_assembled_runner_readiness_follows_the_dependency_gate(monkeypatch):
    monkeypatch.delenv(live_assembly.CREDENTIAL_ENV, raising=False)
    runner = live_assembly.assemble_product_runner()
    assert type(runner) is DefaultProductRunner
    assert runner.is_ready is False


def test_http_main_keeps_replay_only_without_the_explicit_switch(monkeypatch):
    from traceable_support.api import http

    monkeypatch.delenv("TRACEABLE_PUBLIC_LIVE_ENABLED", raising=False)
    assert http._parse_bool(os.environ.get("TRACEABLE_PUBLIC_LIVE_ENABLED")) is False


def test_unavailable_pgvector_does_not_disable_the_live_dependency_gate(
    monkeypatch, tmp_path
):
    for name in live_assembly.EXPECTED_KNOWLEDGE_FILES:
        (tmp_path / name).write_text("synthetic", encoding="utf-8")
    monkeypatch.setenv(live_assembly.CREDENTIAL_ENV, "placeholder-not-read")
    monkeypatch.setenv(
        "TRACEABLE_RETRIEVAL_VECTOR_DSN",
        "postgresql://unreachable.invalid/traceable",
    )
    monkeypatch.setattr(live_assembly, "KNOWLEDGE_DIR", tmp_path)
    monkeypatch.setattr(live_assembly, "load_local_model_manifest", lambda: {})
    monkeypatch.setattr(live_assembly, "validate_local_model_files", lambda manifest: tmp_path)
    monkeypatch.setattr(live_assembly.importlib.util, "find_spec", lambda name: object())

    assert live_assembly.live_dependencies_ready() is True
