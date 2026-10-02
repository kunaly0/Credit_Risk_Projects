r"""Verify the raw data layer against its recorded SHA-256 checksums.

Two kinds of record are checked:
- docs/provenance/checksums_*.csv - one row per source archive, written at
  acquisition (D-003). Columns: Algorithm, Hash, FileName, Bytes.
- Raw/FRED/<pull>/manifest.json - one entry per series, written by
  src/macro/load_fred.py when the pull was made.

The folder holding Raw/ comes from DATA_ROOT in .env, or from --root to check
another copy, such as the backup on C: (D-047). Read-only: nothing is written.

Exit code 0 if every file matches, 1 if any does not, 2 if the run could not
start.

Usage:
    python scripts/verify_raw_checksums.py
    python scripts/verify_raw_checksums.py --root C:\Backup\Datasets
"""

import argparse
import csv
import hashlib
import json
import logging
import os
import sys
import time
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
PROVENANCE_DIR = REPO_ROOT / "docs" / "provenance"
CHUNK_BYTES = 1024 * 1024

log = logging.getLogger("verify_raw")

# One result per file checked: (source record, file name, "ok" or a reason)
Result = tuple[str, str, str]


def sha256_of(path: Path) -> str:
    """Return the SHA-256 of a file as lowercase hex, reading 1 MB at a time."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def check_file(path: Path, expected_hash: str, expected_bytes: int | None) -> str:
    """Compare one file with its record. Returns "ok" or a short reason.

    Size is compared first because it is free; the hash needs a full read.
    """
    if not path.is_file():
        return "MISSING"
    size = path.stat().st_size
    if expected_bytes is not None and size != expected_bytes:
        return f"SIZE {size} != {expected_bytes}"
    if sha256_of(path) != expected_hash.lower():
        return "HASH MISMATCH"
    return "ok"


def find_archive(raw_dir: Path, name: str) -> Path:
    """Return the one file called name under raw_dir.

    The checksum records hold a file name only, not a path, so the file is
    searched for. Raises FileNotFoundError if absent, and ValueError if the
    name appears more than once, since the record could then match either.
    """
    matches = [p for p in raw_dir.rglob(name) if p.is_file()]
    if not matches:
        raise FileNotFoundError(name)
    if len(matches) > 1:
        raise ValueError(f"{name} found {len(matches)} times")
    return matches[0]


def archive_checks(raw_dir: Path) -> list[Result]:
    """Check every archive listed in docs/provenance/checksums_*.csv."""
    results: list[Result] = []
    for record in sorted(PROVENANCE_DIR.glob("checksums_*.csv")):
        # utf-8-sig: PowerShell wrote these files with a byte-order mark
        with record.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                name = row["FileName"]
                if row["Algorithm"].upper() != "SHA256":
                    results.append((record.name, name, "NOT SHA256"))
                    continue
                try:
                    path = find_archive(raw_dir, name)
                except FileNotFoundError:
                    results.append((record.name, name, "MISSING"))
                    continue
                except ValueError as exc:
                    results.append((record.name, name, f"DUPLICATE: {exc}"))
                    continue
                result = check_file(path, row["Hash"], int(row["Bytes"]))
                results.append((record.name, name, result))
    return results


def fred_checks(raw_dir: Path) -> list[Result]:
    """Check every saved series file against the manifest of its FRED pull."""
    results: list[Result] = []
    for manifest_path in sorted((raw_dir / "FRED").glob("*/manifest.json")):
        pull_dir = manifest_path.parent
        source = f"FRED/{pull_dir.name}"
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            results.append((source, "manifest.json", f"UNREADABLE: {exc}"))
            continue
        for series in manifest["series"]:
            if series["status"] != "ok":  # not_found series saved no file
                continue
            path = pull_dir / series["file"]
            results.append(
                (source, series["file"], check_file(path, series["sha256"], None))
            )
    return results


def resolve_root(cli_root: Path | None) -> Path | None:
    """Return the folder that holds Raw/: --root if given, else DATA_ROOT."""
    if cli_root is not None:
        return cli_root
    load_dotenv(REPO_ROOT / ".env")
    data_root = os.getenv("DATA_ROOT")
    return Path(data_root) if data_root else None


def main() -> int:
    """Run every check, log a summary per record, and return the exit code."""
    parser = argparse.ArgumentParser(description="Verify raw files against checksums")
    parser.add_argument("--root", type=Path, help="folder that holds Raw/")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    root = resolve_root(args.root)
    if root is None:
        log.error("DATA_ROOT is not set in .env and --root was not given")
        return 2
    raw_dir = root / "Raw"
    if not raw_dir.is_dir():
        log.error("no Raw folder under %s", root)
        return 2

    log.info("checking %s", raw_dir)
    started = time.perf_counter()
    results = archive_checks(raw_dir) + fred_checks(raw_dir)
    elapsed = time.perf_counter() - started

    checked = Counter(source for source, _, _ in results)
    passed = Counter(source for source, _, result in results if result == "ok")
    for source in checked:
        log.info("%-32s %3d of %3d ok", source, passed[source], checked[source])
    for source, name, result in results:
        if result != "ok":
            log.error("%s  %s  %s", source, name, result)

    failures = len(results) - sum(passed.values())
    log.info("%d files in %.0fs - %d failed", len(results), elapsed, failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
