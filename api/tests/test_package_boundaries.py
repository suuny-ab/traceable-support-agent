from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

from traceable_support.api.runs import PublicRunService

REPOSITORY = Path(__file__).resolve().parents[2]
PACKAGE = REPOSITORY / "api" / "src" / "traceable_support"


def test_deepseek_key_alone_never_enables_public_live_mode(
    tmp_path: Path, monkeypatch: object
) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "placeholder-not-a-real-key")
    service = PublicRunService(
        tmp_path / "runs.sqlite3",
        allowed_origin="https://portfolio.example",
        live_enabled=True,
        start_cleanup_thread=False,
    )
    try:
        assert service.live_available is False
        assert service.health()["live_experience"] == "replay_only"
    finally:
        service.shutdown(wait=True)


def test_product_package_does_not_import_evals_scripts_or_history() -> None:
    forbidden = {"evals", "scripts", "workflow_v2", "evaluation", "evidence"}
    for path in (PACKAGE / "product").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        assert not imports & forbidden, f"{path.name}: {sorted(imports & forbidden)}"


def test_replay_control_plane_imports_without_site_packages() -> None:
    environment = {
        **os.environ,
        "PYTHONPATH": str(REPOSITORY / "api" / "src"),
        "PYTHONIOENCODING": "utf-8",
    }
    # The HTTP shell (api.http) intentionally requires the pinned FastAPI +
    # uvicorn base dependencies, which live in site-packages. The replay
    # boundary that must stay importable with -S is the control plane itself
    # (api.runs), matching the CI api.replay-assembly-boundary probe.
    result = subprocess.run(
        [
            sys.executable,
            "-S",
            "-c",
            "from traceable_support.api.runs import PublicRunService; print('replay-import-ok')",
        ],
        cwd=REPOSITORY,
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "replay-import-ok"
