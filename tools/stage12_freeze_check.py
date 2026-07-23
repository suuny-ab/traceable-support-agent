"""Freeze validator for the Stage 12 unseen evaluation set.

Mechanically proves, with zero Provider calls, that every expectation in the
unseen set is verbatim-traceable to the local synthetic corpus: each
``source_section`` exists and each ``required_fact`` is a verbatim span of the
sections bound to its case. On full success the set SHA-256 is printed so the
spec can record the frozen identity. Any failure lists all problems and exits
non-zero.

Usage::

    PYTHONPATH=api/src python tools/stage12_freeze_check.py <unseen-set.json> \
        [--corpus-root data/knowledge]
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
_API_SRC = REPO_ROOT / "api" / "src"
if str(_API_SRC) not in sys.path:
    sys.path.insert(0, str(_API_SRC))

from traceable_support.generation.checklist import _squash  # noqa: E402

# Load corpus.py directly from its file path.  Importing it as
# ``traceable_support.retrieval.corpus`` executes the retrieval package
# ``__init__``, which pulls the hybrid pipeline and its numpy/fastembed
# dependencies; the freeze checker must stay runnable with the standard
# library alone (corpus.py itself is stdlib-only).
_CORPUS_SPEC = importlib.util.spec_from_file_location(
    "stage12_freeze_corpus",
    _API_SRC / "traceable_support" / "retrieval" / "corpus.py",
)
_corpus = importlib.util.module_from_spec(_CORPUS_SPEC)
_CORPUS_SPEC.loader.exec_module(_corpus)
SUPPORTED_FORMATS = _corpus.SUPPORTED_FORMATS
parse_document = _corpus.parse_document

SET_SCHEMA_VERSION = "stage12-unseen-v1"
MAX_CASES = 24
OUTCOMES = ("candidate", "handoff")
TASK_TYPES = ("qa", "ticket")
PRODUCT_MODELS = ("CZ-R1", "CZ-R2")
CATEGORIES = ("故障排查", "使用咨询", "安全风险", "售后申请")
PRIORITIES = ("P0-紧急", "P1-高", "P2-普通", "P3-低")
CASE_ID_RE = re.compile(r"^STG12-[A-Z0-9]+-[A-Z0-9]+-[0-9]{3}$")
SECTION_RE = re.compile(r"^[A-Z0-9-]+/[a-z0-9-]+$")
CASE_KEYS = {"case_id", "task_type", "product_model", "input", "expected"}
EXPECTED_KEYS = {
    "outcome", "source_sections", "required_facts", "category", "priority",
    "handoff_reason",
}


def _normalize_fact(text: str) -> str:
    """Match the corpus NFKC normalization, then squash like the gate."""

    return _squash(unicodedata.normalize("NFKC", text))


def _load_section_texts(corpus_root: Path) -> dict[str, str]:
    """Return ``DOCUMENT-ID/section-id`` -> squashed section text."""

    sections: dict[str, list[str]] = {}
    paths = sorted(
        path
        for path in corpus_root.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_FORMATS
    )
    if not paths:
        raise ValueError("stage12_freeze_corpus_empty")
    for path in paths:
        document = parse_document(path)
        document_id = document["metadata"]["document_id"]
        for chunk in document["chunks"]:
            key = f"{document_id}/{chunk['section_id']}"
            sections.setdefault(key, []).append(chunk["text"])
    return {key: _squash("\n".join(texts)) for key, texts in sections.items()}


def _validate_case(case: Any, index: int, problems: list[str]) -> dict[str, Any] | None:
    label = f"cases[{index}]"
    if type(case) is not dict or set(case) != CASE_KEYS:
        problems.append(f"{label}: keys must be exactly {sorted(CASE_KEYS)}")
        return None
    case_id = case["case_id"]
    label = f"case {case_id!r}"
    ok = True
    if type(case_id) is not str or CASE_ID_RE.fullmatch(case_id) is None:
        problems.append(f"{label}: case_id must match {CASE_ID_RE.pattern}")
        ok = False
    if case["task_type"] not in TASK_TYPES:
        problems.append(f"{label}: task_type must be one of {TASK_TYPES}")
        ok = False
    if case["product_model"] not in PRODUCT_MODELS:
        problems.append(f"{label}: product_model must be one of {PRODUCT_MODELS}")
        ok = False
    question = case["input"]
    if type(question) is not str or not question.strip() or len(question) > 500:
        problems.append(f"{label}: input must be a non-empty string of at most 500 characters")
        ok = False
    expected = case["expected"]
    if type(expected) is not dict or not set(expected) <= EXPECTED_KEYS:
        problems.append(f"{label}: expected keys must be a subset of {sorted(EXPECTED_KEYS)}")
        return None
    for required_key in ("outcome", "source_sections", "required_facts"):
        if required_key not in expected:
            problems.append(f"{label}: expected.{required_key} is required")
            ok = False
    if not ok:
        return None
    if expected["outcome"] not in OUTCOMES:
        problems.append(f"{label}: outcome must be one of {OUTCOMES}")
        ok = False
    sections = expected["source_sections"]
    if (
        type(sections) is not list
        or any(type(item) is not str or SECTION_RE.fullmatch(item) is None for item in sections)
        or len(set(sections)) != len(sections)
    ):
        problems.append(f"{label}: source_sections must be unique DOCUMENT-ID/section-id strings")
        ok = False
    facts = expected["required_facts"]
    if (
        type(facts) is not list
        or any(type(item) is not str or not 2 <= len(item) <= 500 for item in facts)
        or len(set(facts)) != len(facts)
    ):
        problems.append(f"{label}: required_facts must be unique strings of 2..500 characters")
        ok = False
    handoff_reason = expected.get("handoff_reason")
    if handoff_reason is not None and (
        expected["outcome"] != "handoff"
        or type(handoff_reason) is not str
        or not handoff_reason
    ):
        problems.append(f"{label}: handoff_reason is only allowed for handoff cases")
        ok = False
    if case["task_type"] == "ticket" and expected["outcome"] == "candidate":
        if expected.get("category") not in CATEGORIES:
            problems.append(f"{label}: candidate ticket cases require category in {CATEGORIES}")
            ok = False
        if expected.get("priority") not in PRIORITIES:
            problems.append(f"{label}: candidate ticket cases require priority in {PRIORITIES}")
            ok = False
    if expected["outcome"] == "candidate" and not facts:
        problems.append(f"{label}: candidate cases require at least one required_fact")
        ok = False
    return case if ok else None


def validate_set(set_path: Path, corpus_root: Path) -> list[str]:
    """Return every freeze problem found; an empty list means frozen."""

    problems: list[str] = []
    try:
        raw = set_path.read_bytes()
        suite = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return [f"{set_path}: unreadable or invalid JSON"]
    if type(suite) is not dict or suite.get("schema_version") != SET_SCHEMA_VERSION:
        problems.append(f"schema_version must be {SET_SCHEMA_VERSION!r}")
    cases = suite.get("cases") if type(suite) is dict else None
    if type(cases) is not list or not 1 <= len(cases) <= MAX_CASES:
        problems.append(f"cases must be a list of 1..{MAX_CASES} entries")
        return problems
    checked: list[dict[str, Any]] = []
    for index, case in enumerate(cases):
        valid = _validate_case(case, index, problems)
        if valid is not None:
            checked.append(valid)
    seen: dict[str, int] = {}
    for case in checked:
        if case["case_id"] in seen:
            problems.append(f"case {case['case_id']!r}: duplicate case_id")
        seen[case["case_id"]] = 1
    try:
        section_texts = _load_section_texts(corpus_root)
    except (ValueError, OSError) as exc:
        return problems + [f"corpus root {corpus_root}: {exc}"]
    for case in checked:
        bound = case["expected"]["source_sections"]
        missing_sections = [key for key in bound if key not in section_texts]
        for key in missing_sections:
            problems.append(f"case {case['case_id']!r}: source_section {key!r} not in corpus")
        available = [key for key in bound if key in section_texts]
        bound_text = _squash("\n".join(section_texts[key] for key in available))
        for fact in case["expected"]["required_facts"]:
            if _normalize_fact(fact) not in bound_text:
                problems.append(
                    f"case {case['case_id']!r}: required_fact is not a verbatim span "
                    f"of its bound source_sections"
                )
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Freeze-check the Stage 12 unseen set")
    parser.add_argument("set_path", type=Path, help="path to the private unseen set JSON")
    parser.add_argument(
        "--corpus-root",
        type=Path,
        default=REPO_ROOT / "data" / "knowledge",
        help="synthetic corpus root (default: data/knowledge)",
    )
    args = parser.parse_args(argv)
    problems = validate_set(args.set_path, args.corpus_root)
    if problems:
        for problem in problems:
            print(f"problem: {problem}")
        print(f"freeze_check=failed problems={len(problems)}")
        return 1
    digest = hashlib.sha256(args.set_path.read_bytes()).hexdigest()
    case_count = len(json.loads(args.set_path.read_text(encoding="utf-8"))["cases"])
    print(f"freeze_check=passed cases={case_count} unseen_set_sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
