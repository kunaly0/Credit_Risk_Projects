"""Back up the database with pg_dump, and optionally prove the dump restores.

Usage, from the repo root:
    python -m scripts.backup_db            dump only
    python -m scripts.backup_db --test     dump, restore it into a throwaway
                                           database, compare row counts

Connection details and the password come from .env, so nothing is typed at
a prompt. The dump goes to BACKUP_DIR from .env - a different disk from the
database (D-047). Procedure and log: docs/postgres_backup.md.

The restore prints a progress line every 30 seconds with the step it has
reached, and gives up after --timeout minutes. Its full --verbose output goes
to a .restore.log file next to the dump, kept only if the test fails. The
throwaway database is dropped at the end whether the test passes or fails.
"""

import argparse
import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg import sql

COUNTS_SQL = Path("sql/ops/table_row_counts.sql")
TEST_SUFFIX = "_restore_test"
KEEP = 3

log = logging.getLogger("backup_db")

Counts = dict[str, int]


def setting(name: str) -> str:
    """Return a setting from .env or the environment, or stop with a clear error."""
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"{name} is not set in .env")
    return value


def tool(name: str) -> str:
    """Return the path of a PostgreSQL command-line tool, or stop if not on PATH."""
    path = shutil.which(name)
    if path is None:
        raise SystemExit(f"{name} not found on PATH")
    return path


def pg_args() -> list[str]:
    """Host, port and user flags shared by pg_dump and pg_restore."""
    return [
        "-h",
        setting("DB_HOST"),
        "-p",
        setting("DB_PORT"),
        "-U",
        setting("DB_USER"),
    ]


def pg_env() -> dict[str, str]:
    """A copy of the environment with PGPASSWORD set, so the tools never prompt."""
    env = os.environ.copy()
    env["PGPASSWORD"] = setting("DB_PASSWORD")
    return env


def connect(dbname: str, autocommit: bool = False) -> psycopg.Connection:
    """Open a connection to one database on the server named in .env."""
    return psycopg.connect(
        host=setting("DB_HOST"),
        port=setting("DB_PORT"),
        user=setting("DB_USER"),
        password=setting("DB_PASSWORD"),
        dbname=dbname,
        autocommit=autocommit,
    )


def dump(dbname: str, folder: Path) -> Path:
    """Write a custom-format dump of one database and return its path."""
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{dbname}_{datetime.now():%Y%m%d_%H%M%S}.dump"
    log.info("dumping %s to %s", dbname, target)
    start = time.monotonic()
    command = [tool("pg_dump"), *pg_args(), "-d", dbname, "-Fc", "-f", str(target)]
    subprocess.run(command, env=pg_env(), check=True)
    log.info(
        "dump done: %.0f MB in %.1f min",
        target.stat().st_size / 1024**2,
        (time.monotonic() - start) / 60,
    )
    return target


def extra_dumps(files: list[Path], keep: int = KEEP) -> list[Path]:
    """Dumps beyond the newest `keep`, oldest first. Names sort by timestamp."""
    ordered = sorted(files, key=lambda p: p.name)
    return ordered[: max(len(ordered) - keep, 0)]


def row_counts(dbname: str) -> Counts:
    """Run sql/ops/table_row_counts.sql against one database."""
    with connect(dbname) as conn:
        rows = conn.execute(COUNTS_SQL.read_text(encoding="utf-8")).fetchall()
    return {name: count for name, count in rows}


def compare_counts(live: Counts, restored: Counts) -> list[tuple[str, int, int, bool]]:
    """One row per table in either database: name, live, restored, match.

    A table missing on one side is reported with -1 there, and fails.
    """
    rows = []
    for name in sorted(live.keys() | restored.keys()):
        a, b = live.get(name, -1), restored.get(name, -1)
        rows.append((name, a, b, a == b and a >= 0))
    return rows


def drop_test_db(name: str) -> None:
    """Drop the throwaway database. Refuses any name not ending in _restore_test."""
    if not name.endswith(TEST_SUFFIX):
        raise ValueError(f"refusing to drop {name!r}: not a {TEST_SUFFIX} database")
    with connect(setting("DB_NAME"), autocommit=True) as conn:
        conn.execute(
            sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(
                sql.Identifier(name)
            )
        )


def last_line(path: Path) -> str:
    """The last non-blank line of a text file, or '' if there is none yet."""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return next((line.strip() for line in reversed(lines) if line.strip()), "")


def run_with_progress(
    command: list[str], log_file: Path, timeout_s: float, every_s: float = 30
) -> int | None:
    """Run a command with its output going to log_file, reporting every_s seconds.

    Returns the exit code, or None if it ran past timeout_s and was stopped.
    """
    start = time.monotonic()
    with log_file.open("w", encoding="utf-8") as out:
        proc = subprocess.Popen(
            command, env=pg_env(), stdout=out, stderr=subprocess.STDOUT
        )
        while True:
            try:
                return proc.wait(timeout=every_s)
            except subprocess.TimeoutExpired:
                elapsed = time.monotonic() - start
                if elapsed >= timeout_s:
                    proc.kill()
                    proc.wait()
                    return None
                log.info(
                    "still restoring, %.1f min - %s",
                    elapsed / 60,
                    last_line(log_file)[:100],
                )


def restore_test(dump_file: Path, dbname: str, timeout_min: int) -> bool:
    """Restore the dump into <dbname>_restore_test and compare row counts."""
    test_db = f"{dbname}{TEST_SUFFIX}"
    log_file = dump_file.with_suffix(".restore.log")
    drop_test_db(test_db)
    with connect(dbname, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(test_db)))
    try:
        log.info("restoring into %s", test_db)
        start = time.monotonic()
        command = [
            tool("pg_restore"),
            *pg_args(),
            "-d",
            test_db,
            "-j",
            "4",
            "--verbose",
            str(dump_file),
        ]
        code = run_with_progress(command, log_file, timeout_min * 60)
        if code is None:
            log.error(
                "restore did not finish in %d min and was stopped. Last step: %s."
                " Full output: %s",
                timeout_min,
                last_line(log_file),
                log_file,
            )
            return False
        log.info("restore done in %.1f min", (time.monotonic() - start) / 60)
        if code != 0:
            log.warning("pg_restore exit code %d - see %s", code, log_file)

        rows = compare_counts(row_counts(dbname), row_counts(test_db))
        print(f"\n{'table':<24}{'live':>12}{'restored':>12}  match")
        for name, a, b, ok in rows:
            print(f"{name:<24}{a:>12,}{b:>12,}  {'yes' if ok else 'NO'}")
        passed = all(ok for *_, ok in rows)
        log.info("restore test %s", "PASSED" if passed else "FAILED")
        if passed and code == 0:
            log_file.unlink()
        return passed
    finally:
        drop_test_db(test_db)
        log.info("dropped %s", test_db)


def main() -> int:
    """Dump, warn about old dumps, optionally restore-test. Returns the exit code."""
    parser = argparse.ArgumentParser(description="Back up the database with pg_dump")
    parser.add_argument(
        "--test",
        action="store_true",
        help="restore into a throwaway database and compare row counts",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=20,
        help="minutes before the restore test gives up (default 20)",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    load_dotenv()

    dbname = setting("DB_NAME")
    folder = Path(setting("BACKUP_DIR"))
    try:
        dump_file = dump(dbname, folder)
    except subprocess.CalledProcessError as exc:
        log.error("pg_dump failed with exit code %d", exc.returncode)
        return 1

    for old in extra_dumps(list(folder.glob(f"{dbname}_*.dump"))):
        log.warning("more than %d dumps kept - delete the oldest: %s", KEEP, old.name)

    if not args.test:
        log.info("restore test skipped (add --test to run it)")
        return 0
    return 0 if restore_test(dump_file, dbname, args.timeout) else 1


if __name__ == "__main__":
    sys.exit(main())
