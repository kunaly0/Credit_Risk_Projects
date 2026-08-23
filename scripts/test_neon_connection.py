"""Verify connectivity to the Neon cloud PostgreSQL instance.

Reads credentials from .env. Run from the repository root.
"""

import logging
import os

import psycopg
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def test_connection() -> None:
    """Open a connection to Neon and log the server version."""
    load_dotenv()

    database_url = os.getenv("NEON_DATABASE_URL")
    if not database_url:
        raise ValueError("NEON_DATABASE_URL not found in .env")

    logger.info("Connecting to Neon...")

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            version = cur.fetchone()[0]
            logger.info("Connected. Server: %s", version)

            cur.execute("SELECT current_database(), current_user;")
            db, user = cur.fetchone()
            logger.info("Database: %s | User: %s", db, user)


if __name__ == "__main__":
    test_connection()
