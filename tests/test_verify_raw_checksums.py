"""Tests for scripts/verify_raw_checksums.py, the raw-layer checksum control."""

import hashlib
from pathlib import Path

from scripts.verify_raw_checksums import check_file

CONTENT = b"loan data"


def write_archive(tmp_path: Path) -> tuple[Path, str]:
    """Write a small file and return its path and SHA-256."""
    path = tmp_path / "archive.zip"
    path.write_bytes(CONTENT)
    return path, hashlib.sha256(CONTENT).hexdigest()


def test_matching_file_is_ok(tmp_path: Path) -> None:
    path, digest = write_archive(tmp_path)
    # The provenance CSVs store hashes in upper case
    assert check_file(path, digest.upper(), len(CONTENT)) == "ok"


def test_missing_file(tmp_path: Path) -> None:
    assert check_file(tmp_path / "absent.zip", "00", None) == "MISSING"


def test_wrong_size_is_caught_before_hashing(tmp_path: Path) -> None:
    path, digest = write_archive(tmp_path)
    assert check_file(path, digest, len(CONTENT) + 1).startswith("SIZE")


def test_one_changed_byte_fails(tmp_path: Path) -> None:
    path, digest = write_archive(tmp_path)
    path.write_bytes(b"loan dato")  # same size, one byte different
    assert check_file(path, digest, len(CONTENT)) == "HASH MISMATCH"
