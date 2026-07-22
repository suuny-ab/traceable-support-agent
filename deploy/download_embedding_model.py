"""Download and verify the pinned FastEmbed model during an image build."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tarfile
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath
from typing import Any


MAX_ARCHIVE_BYTES = 160 * 1024 * 1024


def _fail(code: str) -> None:
    raise RuntimeError(code) from None


def _load_manifest(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        _fail("model_manifest_invalid")
    if type(value) is not dict or value.get("schema_version") != "local-embedding-model-v1":
        _fail("model_manifest_invalid")
    source = value.get("source")
    parsed = urllib.parse.urlparse(source) if type(source) is str else None
    if parsed is None or parsed.scheme != "https" or parsed.hostname != "storage.googleapis.com":
        _fail("model_source_not_allowed")
    files = value.get("files")
    if type(files) is not list or not files:
        _fail("model_file_contract_invalid")
    expected: dict[str, tuple[int, str]] = {}
    for item in files:
        if (
            type(item) is not dict
            or type(item.get("path")) is not str
            or type(item.get("size")) is not int
            or type(item.get("sha256")) is not str
            or not item["path"]
            or item["size"] < 1
            or len(item["sha256"]) != 64
        ):
            _fail("model_file_contract_invalid")
        candidate = PurePosixPath(item["path"])
        if candidate.is_absolute() or ".." in candidate.parts or str(candidate) != item["path"]:
            _fail("model_file_path_invalid")
        if item["path"] in expected:
            _fail("model_file_duplicate")
        expected[item["path"]] = (item["size"], item["sha256"])
    value["_expected"] = expected
    return value


def _download(source: str, destination: Path) -> None:
    request = urllib.request.Request(source, headers={"User-Agent": "traceable-support-image-build/1"})
    written = 0
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as output:
        final = urllib.parse.urlparse(response.geturl())
        if final.scheme != "https" or final.hostname != "storage.googleapis.com":
            _fail("model_download_redirect_not_allowed")
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            written += len(chunk)
            if written > MAX_ARCHIVE_BYTES:
                _fail("model_archive_too_large")
            output.write(chunk)
    if written == 0:
        _fail("model_archive_empty")


def _member_key(name: str, expected: dict[str, tuple[int, str]]) -> str | None:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        _fail("model_archive_path_invalid")
    normalized = str(path)
    matches = [key for key in expected if normalized == key or normalized.endswith("/" + key)]
    if len(matches) > 1:
        _fail("model_archive_member_ambiguous")
    return matches[0] if matches else None


def _extract_verified(archive: Path, destination: Path, expected: dict[str, tuple[int, str]]) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    found: set[str] = set()
    with tarfile.open(archive, mode="r:gz") as bundle:
        for member in bundle:
            if member.issym() or member.islnk():
                _fail("model_archive_link_not_allowed")
            if not member.isfile():
                continue
            key = _member_key(member.name, expected)
            if key is None:
                continue
            if key in found:
                _fail("model_archive_member_duplicate")
            expected_size, expected_hash = expected[key]
            if member.size != expected_size:
                _fail("model_file_size_invalid")
            source = bundle.extractfile(member)
            if source is None:
                _fail("model_archive_member_unreadable")
            target = destination / Path(key)
            target.parent.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha256()
            written = 0
            with source, target.open("wb") as output:
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > expected_size:
                        _fail("model_file_size_invalid")
                    digest.update(chunk)
                    output.write(chunk)
            if written != expected_size or digest.hexdigest() != expected_hash:
                _fail("model_file_hash_invalid")
            target.chmod(0o444)
            found.add(key)
    if found != set(expected):
        _fail("model_file_inventory_invalid")
    actual = {
        path.relative_to(destination).as_posix()
        for path in destination.rglob("*")
        if path.is_file()
    }
    if actual != set(expected):
        _fail("model_file_inventory_invalid")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    manifest = _load_manifest(args.manifest)
    model_root = args.root / manifest["model_root"]
    descriptor, temporary_name = tempfile.mkstemp(prefix="fastembed-", suffix=".tar.gz")
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        _download(manifest["source"], temporary)
        _extract_verified(temporary, model_root, manifest["_expected"])
    finally:
        temporary.unlink(missing_ok=True)
    print(f"verified_model_root={model_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
