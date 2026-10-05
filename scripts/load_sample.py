"""Load the six Freddie Mac sample vintages into a built database.

Run after sql/ops/build_all.sql. Loads every origination file first, then
every performance file, because performance rows need their loan in dim_loan.
Each file is one load_audit run; a failure stops the script with the failed
run recorded.

Usage, from the repo root (as a module, so src/ can be imported and the
loader finds config/load_config.yaml):
    python -m scripts.load_sample --root D:/Datasets/working/Freddie_mac_sample

The database is the one named in .env (DB_NAME), unless DB_NAME is set in the
environment first.
"""

import argparse
import logging
import sys
from pathlib import Path

from src.etl.loader import load_origination, load_performance

YEARS = (2005, 2006, 2007, 2008, 2012, 2017)

log = logging.getLogger("load_sample")


def main() -> int:
    """Check every file exists, then load them in order. Returns the exit code."""
    parser = argparse.ArgumentParser(description="Load the Freddie Mac sample files")
    parser.add_argument(
        "--root", type=Path, required=True, help="folder holding sample_<year>/"
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    plan = [
        (kind, args.root / f"sample_{year}" / f"sample_{kind}_{year}.txt")
        for kind in ("orig", "perf")
        for year in YEARS
    ]
    missing = [str(path) for _, path in plan if not path.is_file()]
    if missing:
        log.error("missing files, nothing loaded: %s", ", ".join(missing))
        return 2

    for kind, path in plan:
        log.info("loading %s", path.name)
        loader = load_origination if kind == "orig" else load_performance
        loader(str(path))
    log.info("all 12 files loaded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
