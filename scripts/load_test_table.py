"""Create and populate a 10,000-row test table in Neon.

Measures insert throughput to inform ETL time estimates.
Disposable — this table exists only to verify write access and to give
the Day 3 Streamlit smoke test something to read.
"""

from __future__ import annotations

import logging
import os
import random
import time
from datetime import date, timedelta

import psycopg
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

RANDOM_STATE = 42  # mirrors config/constants.py
N_ROWS = 10_000
TABLE_NAME = "test_loan_sample"

STATES = ["CA", "TX", "FL", "NY", "IL", "PA", "OH", "GA", "NC", "MI"]

DDL = f"""
DROP TABLE IF EXISTS {TABLE_NAME};
CREATE TABLE {TABLE_NAME} (
    loan_id           TEXT PRIMARY KEY,
    origination_date  DATE        NOT NULL,
    original_upb      NUMERIC(12, 2) NOT NULL,
    credit_score      SMALLINT,
    dti               SMALLINT,
    ltv               SMALLINT,
    property_state    CHAR(2)     NOT NULL
);
"""


def generate_rows(n: int) -> list[tuple]:
    """Generate n synthetic loan records with a fixed seed."""
    rng = random.Random(RANDOM_STATE)
    start = date(2005, 1, 1)
    rows = []
    for i in range(n):
        rows.append(
            (
                f"L{i:08d}",
                start + timedelta(days=rng.randint(0, 4_000)),
                round(rng.uniform(50_000, 750_000), 2),
                rng.randint(580, 820),
                rng.randint(10, 55),
                rng.randint(30, 100),
                rng.choice(STATES),
            )
        )
    return rows


def main() -> None:
    """Create the table, bulk-load rows via COPY, and verify the count."""
    load_dotenv()
    database_url = os.getenv("NEON_DATABASE_URL")
    if not database_url:
        raise ValueError("NEON_DATABASE_URL not found in .env")

    logger.info("Generating %d rows...", N_ROWS)
    rows = generate_rows(N_ROWS)

    try:
        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cur:
                logger.info("Creating table %s...", TABLE_NAME)
                cur.execute(DDL)

                logger.info("Loading rows via COPY...")
                start = time.perf_counter()
                copy_sql = (
                    f"COPY {TABLE_NAME} (loan_id, origination_date, "
                    "original_upb, credit_score, dti, ltv, property_state) "
                    "FROM STDIN"
                )
                with cur.copy(copy_sql) as copy:
                    for row in rows:
                        copy.write_row(row)
                elapsed = time.perf_counter() - start

                cur.execute(f"SELECT COUNT(*) FROM {TABLE_NAME};")
                count = cur.fetchone()[0]

            conn.commit()

        logger.info(
            "Loaded %d rows in %.2f s (%.0f rows/sec)", count, elapsed, count / elapsed
        )

        if count != N_ROWS:
            raise ValueError(f"Expected {N_ROWS} rows, found {count}")
        logger.info("Row count reconciled.")

    except psycopg.Error:
        logger.exception("Database operation failed")
        raise


if __name__ == "__main__":
    main()
