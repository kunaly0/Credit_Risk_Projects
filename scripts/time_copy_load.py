"""S00 Day 5 — measure COPY throughput into local PostgreSQL.

Loads a Freddie Mac performance file into an all-TEXT staging table and
times it. Type conversion is deliberately excluded: this measures raw
ingest, not parsing into typed columns.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

import psycopg
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

N_COLUMNS = 35  # 34 fields + trailing delimiter
MAX_LINES: int | None = None  # None for full file
TABLE = "staging_perf_test"

SOURCE = Path(
    r"D:\Datasets\Working\Freddie_mac\historical_data_2005"
    r"\historical_data_2005Q1\perf_2005Q1.txt"
)

COLUMNS = ",\n    ".join(f"col_{i:02d} TEXT" for i in range(1, N_COLUMNS + 1))
DDL = f"""
DROP TABLE IF EXISTS {TABLE};
CREATE TABLE {TABLE} (
    {COLUMNS}
) TABLESPACE credit_risk_ts;
"""

COPY_SQL = (
    f"COPY {TABLE} FROM STDIN "
    "WITH (FORMAT csv, DELIMITER '|', NULL '', QUOTE E'\\x01')"
)


def local_dsn() -> str:
    """Build a connection string for the local Postgres instance."""
    load_dotenv()
    required = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]
    vals = {k: os.getenv(k) for k in required}
    missing = [k for k, v in vals.items() if not v]
    if missing:
        raise ValueError(f"Missing in .env: {', '.join(missing)}")
    return (
        f"host={vals['DB_HOST']} port={vals['DB_PORT']} "
        f"dbname={vals['DB_NAME']} user={vals['DB_USER']} "
        f"password={vals['DB_PASSWORD']}"
    )


def main() -> None:
    """Create staging table, stream the file via COPY, time and reconcile."""
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)

    size_gb = SOURCE.stat().st_size / 1024**3
    logger.info("Source: %s (%.2f GB)", SOURCE.name, size_gb)
    logger.info("Mode: %s", f"first {MAX_LINES:,} lines" if MAX_LINES else "FULL FILE")

    with psycopg.connect(local_dsn()) as conn:
        with conn.cursor() as cur:
            logger.info("Creating %s with %d TEXT columns...", TABLE, N_COLUMNS)
            cur.execute(DDL)
            conn.commit()

            logger.info("Loading...")
            start = time.perf_counter()

            with cur.copy(COPY_SQL) as copy:
                with open(SOURCE, "rb") as fh:
                    if MAX_LINES is None:
                        while chunk := fh.read(4 * 1024 * 1024):
                            copy.write(chunk)
                    else:
                        for i, line in enumerate(fh):
                            if i >= MAX_LINES:
                                break
                            copy.write(line)

            elapsed = time.perf_counter() - start
            conn.commit()

            cur.execute(f"SELECT COUNT(*) FROM {TABLE};")
            rows = cur.fetchone()[0]

            cur.execute(f"SELECT pg_total_relation_size('{TABLE}');")
            bytes_on_disk = cur.fetchone()[0]

    logger.info("Rows loaded : %s", f"{rows:,}")
    logger.info("Elapsed     : %.1f s", elapsed)
    logger.info("Throughput  : %s rows/sec", f"{rows / elapsed:,.0f}")
    logger.info("On disk     : %.2f GB", bytes_on_disk / 1024**3)


if __name__ == "__main__":
    main()
