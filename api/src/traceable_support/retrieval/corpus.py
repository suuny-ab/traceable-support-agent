"""Parse, chunk and publish a deterministic local knowledge index."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import time
import unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

BUILDER_VERSION = "m2.1"


PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_SOURCE = PROJECT_ROOT / "data" / "knowledge" / "synthetic-kb-v1"
DEFAULT_OUTPUT = PROJECT_ROOT / "artifacts" / "knowledge-base"
SUPPORTED_FORMATS = {".md": "markdown", ".json": "paged_json"}
REQUIRED_TYPES = {
    "product_manual",
    "faq",
    "troubleshooting",
    "after_sales_policy",
    "customer_service_sop",
}
REQUIRED_METADATA = {
    "schema_version",
    "corpus_version",
    "document_id",
    "title",
    "brand",
    "source_file",
    "source_format",
    "document_version",
    "applicable_models",
    "document_type",
    "effective_date",
    "language",
    "synthetic",
    "contains_personal_data",
    "synthetic_notice",
}
SECTION_RE = re.compile(r"^##\s+\[([a-z0-9-]+)\]\s+(.+?)\s*$")
ATTEMPT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
PII_PATTERNS = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "mobile_phone": re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    "identity_number": re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)"),
}


class InputError(Exception):
    def __init__(self, code: str, message: str, source_file: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.source_file = source_file

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message, "source_file": self.source_file}


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def repository_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def validate_metadata(metadata: dict[str, Any], actual_source: str, actual_format: str) -> None:
    missing = sorted(REQUIRED_METADATA - metadata.keys())
    if missing:
        raise InputError("missing_metadata", f"missing fields: {', '.join(missing)}", actual_source)
    if metadata["source_file"] != actual_source:
        raise InputError(
            "source_path_mismatch",
            f"metadata source_file={metadata['source_file']!r} does not match {actual_source!r}",
            actual_source,
        )
    if metadata["source_format"] != actual_format:
        raise InputError("source_format_mismatch", "metadata source_format does not match extension", actual_source)
    if metadata["synthetic"] is not True or metadata["contains_personal_data"] is not False:
        raise InputError("unsafe_data_classification", "document must be synthetic and contain no personal data", actual_source)
    if "虚构" not in metadata["synthetic_notice"] or "非真实" not in metadata["synthetic_notice"]:
        raise InputError("missing_synthetic_notice", "synthetic_notice must explicitly say fictional and non-real", actual_source)
    models = metadata["applicable_models"]
    if not isinstance(models, list) or not models or not set(models) <= {"CZ-R1", "CZ-R2"}:
        raise InputError("invalid_models", "applicable_models must use CZ-R1/CZ-R2", actual_source)
    if metadata["document_type"] not in REQUIRED_TYPES:
        raise InputError("invalid_document_type", "unsupported document_type", actual_source)
    try:
        date.fromisoformat(metadata["effective_date"])
    except (TypeError, ValueError) as exc:
        raise InputError("invalid_effective_date", "effective_date must be ISO YYYY-MM-DD", actual_source) from exc
    if metadata["language"] != "zh-CN":
        raise InputError("invalid_language", "language must be zh-CN", actual_source)


def assert_no_obvious_personal_data(text: str, source_file: str) -> None:
    for name, pattern in PII_PATTERNS.items():
        if pattern.search(text):
            raise InputError("suspected_personal_data", f"matched guard: {name}", source_file)


def split_markdown(path: Path, source_file: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    text = path.read_text(encoding="utf-8")
    assert_no_obvious_personal_data(text, source_file)
    lines = text.splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        raise InputError("invalid_markdown_header", "missing JSON metadata front matter", source_file)
    try:
        closing = lines.index("---", 1)
    except ValueError as exc:
        raise InputError("invalid_markdown_header", "unclosed metadata front matter", source_file) from exc
    try:
        metadata = json.loads("\n".join(lines[1:closing]))
    except json.JSONDecodeError as exc:
        raise InputError("invalid_metadata_json", str(exc), source_file) from exc
    validate_metadata(metadata, source_file, "markdown")

    fragments: list[dict[str, Any]] = []
    section_id: str | None = None
    section_title: str | None = None
    paragraph_lines: list[str] = []
    ordinal = 0

    def flush() -> None:
        nonlocal paragraph_lines, ordinal
        text_value = "\n".join(line.strip() for line in paragraph_lines).strip()
        paragraph_lines = []
        if not text_value:
            return
        if section_id is None or section_title is None:
            raise InputError("content_without_section", "content must follow an explicit section id", source_file)
        ordinal += 1
        fragments.append(
            {
                "section_id": section_id,
                "section": section_title,
                "page_number": None,
                "page_id": None,
                "chunk_ordinal": ordinal,
                "text": unicodedata.normalize("NFKC", text_value),
            }
        )

    for line in lines[closing + 1 :]:
        section_match = SECTION_RE.match(line)
        if section_match:
            flush()
            section_id, section_title = section_match.groups()
            ordinal = 0
        elif line.startswith("# "):
            continue
        elif not line.strip():
            flush()
        else:
            paragraph_lines.append(line)
    flush()
    if not fragments:
        raise InputError("empty_document", "no content fragments found", source_file)
    return metadata, fragments


def split_paged_json(path: Path, source_file: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    raw_text = path.read_text(encoding="utf-8")
    assert_no_obvious_personal_data(raw_text, source_file)
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise InputError("invalid_json", str(exc), source_file) from exc
    metadata = payload.get("metadata")
    pages = payload.get("pages")
    if not isinstance(metadata, dict) or not isinstance(pages, list) or not pages:
        raise InputError("invalid_paged_json", "metadata object and non-empty pages list are required", source_file)
    validate_metadata(metadata, source_file, "paged_json")
    page_numbers = [page.get("page_number") for page in pages if isinstance(page, dict)]
    if page_numbers != list(range(1, len(pages) + 1)):
        raise InputError("unstable_page_numbers", "page_number must be consecutive starting at 1", source_file)
    page_ids = [page.get("page_id") for page in pages]
    if any(not isinstance(value, str) or not value for value in page_ids) or len(page_ids) != len(set(page_ids)):
        raise InputError("invalid_page_ids", "page_id must be non-empty and unique", source_file)

    fragments: list[dict[str, Any]] = []
    for page in pages:
        sections = page.get("sections")
        if not isinstance(sections, list) or not sections:
            raise InputError("empty_page", f"page {page['page_number']} has no sections", source_file)
        for section in sections:
            section_id = section.get("section_id")
            heading = section.get("heading")
            paragraphs = section.get("paragraphs")
            if not isinstance(section_id, str) or not isinstance(heading, str) or not isinstance(paragraphs, list):
                raise InputError("invalid_page_section", f"invalid section on page {page['page_number']}", source_file)
            for ordinal, paragraph in enumerate(paragraphs, start=1):
                if not isinstance(paragraph, str) or not paragraph.strip():
                    raise InputError("invalid_paragraph", "paragraph must be non-empty text", source_file)
                fragments.append(
                    {
                        "section_id": section_id,
                        "section": heading,
                        "page_number": page["page_number"],
                        "page_id": page["page_id"],
                        "chunk_ordinal": ordinal,
                        "text": unicodedata.normalize("NFKC", paragraph.strip()),
                    }
                )
    return metadata, fragments


def tokenize(text: str) -> Counter[str]:
    normalized = unicodedata.normalize("NFKC", text).lower()
    tokens: list[str] = re.findall(r"[a-z0-9-]+", normalized)
    for sequence in re.findall(r"[\u3400-\u9fff]+", normalized):
        tokens.extend(sequence)
        tokens.extend(sequence[index : index + 2] for index in range(len(sequence) - 1))
    return Counter(token for token in tokens if token.strip())


def parse_document(path: Path) -> dict[str, Any]:
    source_file = repository_path(path)
    source_format = SUPPORTED_FORMATS.get(path.suffix.lower())
    if source_format is None:
        raise InputError("unsupported_format", f"unsupported extension: {path.suffix or '<none>'}", source_file)
    if source_format == "markdown":
        metadata, fragments = split_markdown(path, source_file)
    else:
        metadata, fragments = split_paged_json(path, source_file)
    content_hash = sha256_bytes(path.read_bytes())
    chunks = []
    for fragment in fragments:
        stable_fragment_id = (
            f"{metadata['document_id']}::{fragment['page_id'] or 'no-page'}::"
            f"{fragment['section_id']}::{fragment['chunk_ordinal']:03d}"
        )
        identity = {
            "builder_version": BUILDER_VERSION,
            "source_file": source_file,
            "document_version": metadata["document_version"],
            "stable_fragment_id": stable_fragment_id,
            "text": fragment["text"],
        }
        chunks.append(
            {
                "chunk_id": f"chk_{sha256_json(identity)}",
                "stable_fragment_id": stable_fragment_id,
                "source_file": source_file,
                "source_content_sha256": content_hash,
                "document_id": metadata["document_id"],
                "document_version": metadata["document_version"],
                "corpus_version": metadata["corpus_version"],
                "title": metadata["title"],
                "applicable_models": metadata["applicable_models"],
                "document_type": metadata["document_type"],
                "effective_date": metadata["effective_date"],
                "section_id": fragment["section_id"],
                "section": fragment["section"],
                "page_number": fragment["page_number"],
                "page_id": fragment["page_id"],
                "chunk_ordinal": fragment["chunk_ordinal"],
                "text": fragment["text"],
            }
        )
    return {
        "metadata": metadata,
        "source_file": source_file,
        "source_format": source_format,
        "source_content_sha256": content_hash,
        "chunks": chunks,
    }


def load_current(output: Path) -> dict[str, Any] | None:
    path = output / "current.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def validate_existing_index(
    target: Path,
    expected_manifest: dict[str, Any],
    expected_chunks: list[dict[str, Any]],
    expected_postings: dict[str, dict[str, int]],
) -> InputError | None:
    """Reject a damaged immutable version instead of silently reusing it."""

    manifest_path = target / "manifest.json"
    chunks_path = target / "chunks.jsonl"
    postings_path = target / "postings.json"
    try:
        existing_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return InputError(
            "existing_index_manifest_invalid",
            f"cannot read existing manifest: {type(exc).__name__}: {exc}",
            repository_path(manifest_path),
        )
    if existing_manifest != expected_manifest:
        return InputError(
            "existing_index_manifest_mismatch",
            "existing immutable manifest differs from the expected build",
            repository_path(manifest_path),
        )

    try:
        existing_chunks = [
            json.loads(line)
            for line in chunks_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return InputError(
            "existing_index_chunks_invalid",
            f"cannot read existing chunks: {type(exc).__name__}: {exc}",
            repository_path(chunks_path),
        )
    if existing_chunks != expected_chunks:
        return InputError(
            "existing_index_chunks_mismatch",
            "existing immutable chunks differ from the expected build",
            repository_path(chunks_path),
        )

    try:
        existing_postings = json.loads(postings_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return InputError(
            "existing_index_postings_invalid",
            f"cannot read existing postings: {type(exc).__name__}: {exc}",
            repository_path(postings_path),
        )
    if existing_postings != expected_postings:
        return InputError(
            "existing_index_postings_mismatch",
            "existing immutable postings differ from the expected build",
            repository_path(postings_path),
        )
    return None


def record_failure(
    output: Path,
    attempt_label: str,
    started_at: str,
    errors: list[InputError],
    previous: dict[str, Any] | None,
    input_count: int,
) -> dict[str, Any]:
    current_after = load_current(output)
    report = {
        "status": "failed",
        "attempt_label": attempt_label,
        "started_at": started_at,
        "finished_at": utc_now(),
        "exit_code": 2,
        "input_document_count": input_count,
        "successful_document_count": 0,
        "failed_document_count": len(errors),
        "errors": [error.as_dict() for error in errors],
        "previous_current": previous,
        "current_after_failure": current_after,
        "preserved_current_index": previous == current_after,
    }
    failure_path = output / "failures" / f"{attempt_label}.json"
    atomic_write_json(failure_path, report)
    report["failure_record"] = repository_path(failure_path)
    return report


def build(
    source: Path,
    output: Path,
    attempt_label: str,
    extra_inputs: list[Path] | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    started_at = utc_now()
    source = source.resolve()
    output = output.resolve()
    previous = load_current(output)
    if not source.is_dir():
        error = InputError("missing_source_directory", "source directory does not exist", repository_path(source))
        return record_failure(output, attempt_label, started_at, [error], previous, 0)

    inputs = sorted((path for path in source.rglob("*") if path.is_file()), key=lambda item: item.as_posix())
    inputs.extend(extra_inputs or [])
    inputs = [path.resolve() for path in inputs]
    if not inputs:
        error = InputError("empty_corpus", "source directory contains no input documents", repository_path(source))
        return record_failure(output, attempt_label, started_at, [error], previous, 0)
    errors: list[InputError] = []
    documents: list[dict[str, Any]] = []
    for path in inputs:
        try:
            documents.append(parse_document(path))
        except (InputError, OSError, UnicodeError) as exc:
            if isinstance(exc, InputError):
                errors.append(exc)
            else:
                errors.append(InputError("read_error", f"{type(exc).__name__}: {exc}", repository_path(path)))
    document_ids = [doc["metadata"]["document_id"] for doc in documents]
    duplicates = sorted(name for name, count in Counter(document_ids).items() if count > 1)
    if duplicates:
        errors.append(InputError("duplicate_document_id", f"duplicate ids: {duplicates}", repository_path(source)))
    corpus_versions = sorted({doc["metadata"]["corpus_version"] for doc in documents})
    if len(corpus_versions) > 1:
        errors.append(InputError("mixed_corpus_versions", f"versions: {corpus_versions}", repository_path(source)))
    if errors:
        return record_failure(output, attempt_label, started_at, errors, previous, len(inputs))

    documents.sort(key=lambda item: item["source_file"])
    corpus_manifest = [
        {
            "source_file": doc["source_file"],
            "source_format": doc["source_format"],
            "source_content_sha256": doc["source_content_sha256"],
            "metadata": doc["metadata"],
        }
        for doc in documents
    ]
    corpus_fingerprint = sha256_json(corpus_manifest)
    chunks = [chunk for doc in documents for chunk in doc["chunks"]]
    chunks.sort(key=lambda item: (item["source_file"], item["stable_fragment_id"]))
    stable_fragment_ids = [chunk["stable_fragment_id"] for chunk in chunks]
    duplicate_locators = sorted(
        name for name, count in Counter(stable_fragment_ids).items() if count > 1
    )
    if duplicate_locators:
        error = InputError(
            "duplicate_stable_fragment_id",
            f"duplicate stable fragment ids: {duplicate_locators}",
            repository_path(source),
        )
        return record_failure(output, attempt_label, started_at, [error], previous, len(inputs))
    chunk_ids = [chunk["chunk_id"] for chunk in chunks]
    if len(chunk_ids) != len(set(chunk_ids)):
        error = InputError("duplicate_chunk_id", "duplicate chunk ids are not allowed", repository_path(source))
        return record_failure(output, attempt_label, started_at, [error], previous, len(inputs))

    locator_projection = [
        {
            "chunk_id": chunk["chunk_id"],
            "source_file": chunk["source_file"],
            "stable_fragment_id": chunk["stable_fragment_id"],
            "section_id": chunk["section_id"],
            "page_number": chunk["page_number"],
            "page_id": chunk["page_id"],
        }
        for chunk in chunks
    ]
    chunk_id_digest = sha256_bytes("\n".join(sorted(chunk_ids)).encode("utf-8"))
    locator_digest = sha256_json(locator_projection)
    semantic_digest = sha256_json(
        [{"chunk_id": chunk["chunk_id"], "locator": locator_projection[index], "text": chunk["text"]} for index, chunk in enumerate(chunks)]
    )
    build_fingerprint = sha256_json(
        {
            "builder_version": BUILDER_VERSION,
            "corpus_fingerprint": corpus_fingerprint,
            "semantic_digest": semantic_digest,
            "index_schema_version": "1.0",
        }
    )
    index_version = f"m2-{build_fingerprint[:16]}"

    postings: dict[str, dict[str, int]] = defaultdict(dict)
    for chunk in chunks:
        for token, frequency in tokenize(chunk["text"]).items():
            postings[token][chunk["chunk_id"]] = frequency
    ordered_postings = {token: dict(sorted(values.items())) for token, values in sorted(postings.items())}

    document_results = []
    for doc in documents:
        document_results.append(
            {
                "document_id": doc["metadata"]["document_id"],
                "source_file": doc["source_file"],
                "source_format": doc["source_format"],
                "document_version": doc["metadata"]["document_version"],
                "applicable_models": doc["metadata"]["applicable_models"],
                "document_type": doc["metadata"]["document_type"],
                "effective_date": doc["metadata"]["effective_date"],
                "status": "success",
                "chunk_count": len(doc["chunks"]),
                "page_numbers": sorted({chunk["page_number"] for chunk in doc["chunks"] if chunk["page_number"] is not None}),
                "first_chunk_id": doc["chunks"][0]["chunk_id"],
            }
        )

    manifest = {
        "schema_version": "1.0",
        "builder_version": BUILDER_VERSION,
        "index_version": index_version,
        "corpus_version": corpus_versions[0] if corpus_versions else None,
        "corpus_fingerprint": corpus_fingerprint,
        "build_fingerprint": build_fingerprint,
        "semantic_digest": semantic_digest,
        "chunk_id_digest": chunk_id_digest,
        "locator_digest": locator_digest,
        "input_document_count": len(inputs),
        "successful_document_count": len(documents),
        "failed_document_count": 0,
        "chunk_count": len(chunks),
        "effective_record_count": len(chunks),
        "posting_token_count": len(ordered_postings),
        "posting_record_count": sum(len(value) for value in ordered_postings.values()),
        "duplicate_chunk_id_count": 0,
        "source_formats": sorted({doc["source_format"] for doc in documents}),
        "stable_page_document_count": sum(bool(result["page_numbers"]) for result in document_results),
        "documents": document_results,
    }

    indexes = output / "indexes"
    target = indexes / build_fingerprint
    publication_action = "reused_existing_version"
    if not target.exists():
        staging_root = output / ".staging"
        staging_root.mkdir(parents=True, exist_ok=True)
        # tempfile.mkdtemp uses a private 0o700 ACL on modern Windows.  A
        # published immutable index must instead inherit the repository ACL so
        # the user's normal account and Git can read it after the sandbox exits.
        staging = staging_root / f"{attempt_label}-{os.getpid()}-{time.time_ns()}"
        staging.mkdir()
        try:
            with (staging / "chunks.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
                for chunk in chunks:
                    handle.write(canonical_json(chunk) + "\n")
            atomic_write_json(staging / "postings.json", ordered_postings)
            atomic_write_json(staging / "manifest.json", manifest)
            indexes.mkdir(parents=True, exist_ok=True)
            os.replace(staging, target)
            publication_action = "created_new_version"
        finally:
            if staging.exists():
                shutil.rmtree(staging)
    else:
        error = validate_existing_index(target, manifest, chunks, ordered_postings)
        if error is not None:
            return record_failure(output, attempt_label, started_at, [error], previous, len(inputs))

    pointer = {
        "schema_version": "1.0",
        "index_version": index_version,
        "build_fingerprint": build_fingerprint,
        "index_path": repository_path(target),
        "manifest_path": repository_path(target / "manifest.json"),
    }
    if previous != pointer:
        atomic_write_json(output / "current.json", pointer)

    report = {
        "status": "success",
        "attempt_label": attempt_label,
        "started_at": started_at,
        "finished_at": utc_now(),
        "duration_seconds": round(time.monotonic() - started, 4),
        "exit_code": 0,
        "publication_action": publication_action,
        "new_valid_record_count": len(chunks) if publication_action == "created_new_version" else 0,
        "index_path": repository_path(target),
        "failure_record_directory": repository_path(output / "failures"),
        **manifest,
    }
    report_path = output / "builds" / f"{attempt_label}.json"
    atomic_write_json(report_path, report)
    atomic_write_json(output / "latest-success.json", report)
    report["build_report"] = repository_path(report_path)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the deterministic local knowledge index")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--attempt-label", default="manual-build")
    parser.add_argument("--extra-input", action="append", type=Path, default=[])
    args = parser.parse_args()
    if not ATTEMPT_RE.fullmatch(args.attempt_label):
        parser.error("--attempt-label must use letters, numbers, dot, underscore or hyphen")
    return args


def main() -> int:
    args = parse_args()
    try:
        result = build(args.source, args.output, args.attempt_label, args.extra_input)
    except KeyboardInterrupt:
        print(canonical_json({"status": "interrupted", "exit_code": 130}), file=sys.stderr)
        return 130
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return int(result["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
