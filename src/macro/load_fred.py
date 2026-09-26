"""Pull FRED macro series and load dim_macro and dim_macro_state (S06).

Run from the repo root:  python src/macro/load_fred.py

Stages: read config -> read the state list from dim_loan -> download every
series -> save raw responses unchanged -> align to the monthly grain (D-043)
-> replace both tables in one transaction.

Decisions: D-041 latest figures only, D-042 dim_macro_state, D-043 frequency
alignment. The FRED key and database login come from .env only, and neither
the key nor any request URL is ever logged.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, NamedTuple

import pandas as pd
import psycopg
import requests
import yaml
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "config" / "macro_config.yaml"

# Match the numeric scale of each column in sql/01 and sql/08, so rounding
# happens here, visibly, instead of silently inside Postgres.
DECIMALS = {"unemployment": 1, "hpi": 2, "mortgage_rate": 3, "gdp_growth": 2}

RETRY_STATUSES = {429, 500, 502, 503, 504}

log = logging.getLogger("load_fred")


class SeriesSpec(NamedTuple):
    """One FRED series and where its values go."""

    table: str
    column: str
    state: str | None
    series_id: str
    frequency: str
    transform: str | None


class SeriesNotFoundError(Exception):
    """FRED has no series with this ID."""


# --- Settings and connections ---------------------------------------------


def load_config(path: Path) -> dict[str, Any]:
    """Read the YAML config. The path is fixed relative to this file (D-038)."""
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def require_env(name: str) -> str:
    """Return an environment variable from .env, or stop with a clear error."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} missing from .env")
    return value


def get_connection() -> psycopg.Connection:
    """Open a connection to the credit_risk database.

    Duplicated from src/dq/run_dq_suite.py on purpose - see D-038.
    """
    load_dotenv()
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def read_states() -> list[str]:
    """Return every property_state in dim_loan - the loans decide coverage."""
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT property_state FROM dim_loan "
            "WHERE property_state IS NOT NULL ORDER BY property_state"
        )
        return [row[0] for row in cur.fetchall()]


def build_specs(cfg: dict[str, Any], states: list[str]) -> list[SeriesSpec]:
    """Turn the config into one SeriesSpec per series to download."""
    specs = [
        SeriesSpec(
            "dim_macro",
            column,
            None,
            s["series_id"],
            s["frequency"],
            s.get("transform"),
        )
        for column, s in cfg["national"].items()
    ]
    for state in states:
        for column, s in cfg["state"].items():
            specs.append(
                SeriesSpec(
                    "dim_macro_state",
                    column,
                    state,
                    s["series_id"].format(state=state),
                    s["frequency"],
                    s.get("transform"),
                )
            )
    return specs


# --- Download and raw layer -----------------------------------------------


def fetch_series(
    session: requests.Session, series_id: str, api_key: str, cfg: dict[str, Any]
) -> bytes:
    """Download one series as raw JSON bytes, retrying temporary failures.

    Errors name the series and the HTTP status only. The request URL holds
    the API key, so it never appears in a message or a traceback.
    """
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": cfg["pull_start"],
    }
    fred = cfg["fred"]
    error = "unknown"
    for attempt in range(1, fred["max_attempts"] + 1):
        try:
            response = session.get(
                fred["url"], params=params, timeout=fred["timeout_seconds"]
            )
        except requests.RequestException as exc:
            error = type(exc).__name__
        else:
            if response.status_code == 200:
                return response.content
            if response.status_code == 400 and "does not exist" in response.text:
                raise SeriesNotFoundError(series_id)
            if response.status_code not in RETRY_STATUSES:
                try:
                    message = response.json().get("error_message", "")
                except ValueError:  # the body was not JSON
                    message = ""
                raise RuntimeError(
                    f"{series_id}: HTTP {response.status_code} {message}"
                )
            error = f"HTTP {response.status_code}"
        log.warning("%s: attempt %d failed (%s)", series_id, attempt, error)
        time.sleep(2 * attempt)
    raise RuntimeError(f"{series_id}: gave up after retries ({error})")


def parse_observations(content: bytes, series_id: str) -> pd.DataFrame:
    """Turn a FRED response into date and value columns.

    FRED's missing-value marker "." becomes NaN. Anything else that is not a
    number stops the run (no errors="coerce").
    """
    rows = json.loads(content)["observations"]
    if not rows:
        raise ValueError(f"{series_id}: no observations returned")
    obs = pd.DataFrame(rows, columns=["date", "value"])
    obs["date"] = pd.to_datetime(obs["date"], format="%Y-%m-%d")
    missing = obs["value"] == "."
    obs["value"] = pd.to_numeric(obs["value"].where(~missing))
    return obs


def download_all(
    specs: list[SeriesSpec], api_key: str, cfg: dict[str, Any], raw_dir: Path
) -> tuple[dict[SeriesSpec, pd.DataFrame], list[dict[str, Any]]]:
    """Download every series, save each response unchanged, and parse it."""
    raw_dir.mkdir(parents=True, exist_ok=False)  # a new folder every run
    frames: dict[SeriesSpec, pd.DataFrame] = {}
    manifest: list[dict[str, Any]] = []
    with requests.Session() as session:
        for number, spec in enumerate(specs, start=1):
            if number > 1:
                time.sleep(cfg["fred"]["pause_seconds"])
            entry: dict[str, Any] = {
                "series_id": spec.series_id,
                "table": spec.table,
                "column": spec.column,
                "state": spec.state,
            }
            try:
                content = fetch_series(session, spec.series_id, api_key, cfg)
            except SeriesNotFoundError:
                log.warning("%s: series does not exist on FRED", spec.series_id)
                manifest.append({**entry, "status": "not_found"})
                continue
            raw_file = raw_dir / f"{spec.series_id}.json"
            raw_file.write_bytes(content)
            obs = parse_observations(content, spec.series_id)
            frames[spec] = obs
            missing_dates = obs.loc[obs["value"].isna(), "date"]
            manifest.append(
                {
                    **entry,
                    "status": "ok",
                    "file": raw_file.name,
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "observations": len(obs),
                    "missing_dates": missing_dates.dt.strftime("%Y-%m-%d").tolist(),
                }
            )
            if number % 20 == 0:
                log.info("downloaded %d of %d series", number, len(specs))
    return frames, manifest


def write_manifest(
    raw_dir: Path, manifest: list[dict[str, Any]], pulled_at: datetime
) -> None:
    """Record what was pulled, when, and a checksum of each raw file."""
    record = {"pulled_at": pulled_at.isoformat(timespec="seconds"), "series": manifest}
    path = raw_dir / "manifest.json"
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    log.info("raw files and manifest saved to %s", raw_dir)


# --- Alignment to the monthly grain (D-043) -------------------------------


def annualised_growth(quarterly: pd.Series, series_id: str) -> pd.Series:
    """((Q / previous Q) ^ 4 - 1) x 100. Needs an unbroken run of quarters."""
    expected = pd.period_range(quarterly.index.min(), quarterly.index.max(), freq="Q")
    if len(quarterly) != len(expected):
        raise ValueError(f"{series_id}: quarters are not consecutive")
    return ((quarterly / quarterly.shift(1)) ** 4 - 1) * 100


def align_to_month(
    obs: pd.DataFrame, spec: SeriesSpec, current_month: pd.Period
) -> pd.Series:
    """Return one value per month, indexed by month period."""
    dates = obs["date"]
    if spec.frequency == "monthly":
        if (dates.dt.day != 1).any():
            raise ValueError(f"{spec.series_id}: monthly date not on the 1st")
        monthly = pd.Series(
            obs["value"].to_numpy(), index=dates.dt.to_period("M").to_numpy()
        )
    elif spec.frequency == "weekly":
        # A week counts in the month its Thursday falls in. The current month
        # is dropped because its average would cover only some of its weeks.
        months = dates.dt.to_period("M")
        monthly = obs["value"].groupby(months.to_numpy()).mean()
        monthly = monthly[monthly.index < current_month]
    elif spec.frequency == "quarterly":
        if (~dates.dt.month.isin([1, 4, 7, 10]) | (dates.dt.day != 1)).any():
            raise ValueError(f"{spec.series_id}: date is not a quarter start")
        quarterly = pd.Series(
            obs["value"].to_numpy(), index=pd.PeriodIndex(dates, freq="Q")
        )
        if spec.transform == "annualised_growth":
            quarterly = annualised_growth(quarterly, spec.series_id)
        first_months = quarterly.index.asfreq("M", how="start")
        # The quarter's value is repeated in all three of its months.
        monthly = pd.concat(
            [
                pd.Series(quarterly.to_numpy(), index=first_months + offset)
                for offset in range(3)
            ]
        ).sort_index()
    else:
        raise ValueError(f"{spec.series_id}: unknown frequency {spec.frequency}")
    if not monthly.index.is_unique:
        raise ValueError(f"{spec.series_id}: more than one value for a month")
    return monthly.rename(spec.column)


def finish_table(table: pd.DataFrame, table_start: pd.Period) -> pd.DataFrame:
    """Trim to table_start, drop months with no values at all, round."""
    table = table[table.index >= table_start].dropna(how="all")
    for column in table.columns:
        table[column] = table[column].round(DECIMALS[column])
    table.index.name = "month"
    return table.reset_index()


def build_national(
    frames: dict[SeriesSpec, pd.DataFrame],
    specs: list[SeriesSpec],
    current_month: pd.Period,
    table_start: pd.Period,
) -> pd.DataFrame:
    """One row per month for dim_macro. Every national series must exist."""
    columns = {}
    for spec in specs:
        if spec.table != "dim_macro":
            continue
        if spec not in frames:
            raise RuntimeError(f"national series {spec.series_id} was not downloaded")
        columns[spec.column] = align_to_month(frames[spec], spec, current_month)
    return finish_table(pd.concat(columns, axis=1), table_start)


def build_state(
    frames: dict[SeriesSpec, pd.DataFrame],
    specs: list[SeriesSpec],
    current_month: pd.Period,
    table_start: pd.Period,
) -> pd.DataFrame:
    """One row per state per month for dim_macro_state.

    A state with no series at all gets no rows, so the S06 gate anti-join
    reports it instead of it hiding behind rows full of NULLs.
    """
    by_state: dict[str, dict[str, pd.Series]] = {}
    for spec in specs:
        if spec.table != "dim_macro_state":
            continue
        columns = by_state.setdefault(spec.state, {})
        if spec in frames:
            columns[spec.column] = align_to_month(frames[spec], spec, current_month)
    parts = []
    for state, columns in by_state.items():
        if not columns:
            log.warning("%s: no state series on FRED - no rows written", state)
            continue
        part = finish_table(pd.concat(columns, axis=1), table_start)
        part.insert(1, "property_state", state)
        parts.append(part)
    table = pd.concat(parts, ignore_index=True)
    return table.reindex(columns=["month", "property_state", "unemployment", "hpi"])


# --- Summary and load ------------------------------------------------------


def summarise(
    national: pd.DataFrame, state: pd.DataFrame, manifest: list[dict[str, Any]]
) -> None:
    """Log what is about to be loaded, so a failed load still leaves a record."""
    ok = [m for m in manifest if m["status"] == "ok"]
    not_found = [m["series_id"] for m in manifest if m["status"] == "not_found"]
    log.info("series downloaded: %d of %d", len(ok), len(manifest))
    log.info("series not on FRED: %s", ", ".join(not_found) or "none")
    missing = Counter(d for m in ok for d in m["missing_dates"])
    with_gaps = sum(1 for m in ok if m["missing_dates"])
    log.info("series containing '.' values: %d", with_gaps)
    for day, count in missing.most_common(3):
        log.info("    missing %s in %d series", day, count)
    for name, table in [("dim_macro", national), ("dim_macro_state", state)]:
        log.info(
            "%s: %d rows, %s to %s",
            name,
            len(table),
            table["month"].min(),
            table["month"].max(),
        )
        nulls = table.isna().sum()
        log.info("    NULLs per column: %s", nulls[nulls > 0].to_dict() or "none")
    log.info("dim_macro_state states: %d", state["property_state"].nunique())


def to_db_value(value: Any) -> Any:
    """Convert pandas values to plain Python: NaN -> None, Period -> date."""
    if isinstance(value, pd.Period):
        return value.start_time.date()
    if isinstance(value, str):
        return value
    if pd.isna(value):
        return None
    return float(value)


def to_rows(table: pd.DataFrame) -> list[tuple[Any, ...]]:
    """DataFrame -> list of tuples ready for executemany."""
    return [
        tuple(to_db_value(v) for v in record)
        for record in table.itertuples(index=False, name=None)
    ]


def load_tables(national: pd.DataFrame, state: pd.DataFrame) -> None:
    """Replace both tables in one transaction - all or nothing."""
    national_sql = (
        "INSERT INTO dim_macro (month, unemployment, hpi, mortgage_rate, gdp_growth) "
        "VALUES (%s, %s, %s, %s, %s)"
    )
    state_sql = (
        "INSERT INTO dim_macro_state (month, property_state, unemployment, hpi) "
        "VALUES (%s, %s, %s, %s)"
    )
    national = national[["month", "unemployment", "hpi", "mortgage_rate", "gdp_growth"]]
    # Leaving the with-block commits; any error inside it rolls everything back.
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM dim_macro_state")
        cur.execute("DELETE FROM dim_macro")
        cur.executemany(national_sql, to_rows(national))
        cur.executemany(state_sql, to_rows(state))
    log.info(
        "loaded dim_macro (%d rows) and dim_macro_state (%d rows)",
        len(national),
        len(state),
    )


def main() -> int:
    """Run every stage. Returns 0 on success, 1 on any failure."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s"
    )
    load_dotenv()
    try:
        cfg = load_config(CONFIG_PATH)
        api_key = require_env("FRED_API_KEY")
        pulled_at = datetime.now()
        raw_dir = (
            Path(require_env("DATA_ROOT"))
            / cfg["raw_subdir"]
            / pulled_at.strftime("%Y%m%d_%H%M%S")
        )
        current_month = pd.Period(pulled_at, freq="M")
        table_start = pd.Period(cfg["table_start"], freq="M")

        states = read_states()
        log.info("states in dim_loan: %d", len(states))
        specs = build_specs(cfg, states)
        log.info("series to download: %d", len(specs))

        frames, manifest = download_all(specs, api_key, cfg, raw_dir)
        write_manifest(raw_dir, manifest, pulled_at)

        national = build_national(frames, specs, current_month, table_start)
        state = build_state(frames, specs, current_month, table_start)
        summarise(national, state, manifest)
        load_tables(national, state)
    except psycopg.errors.CheckViolation as exc:
        log.error("a CHECK constraint rejected a row - nothing was loaded")
        log.error("    %s", exc.diag.message_primary)
        log.error("    %s", exc.diag.message_detail)
        return 1
    except Exception:
        log.exception("run failed - nothing was loaded")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
