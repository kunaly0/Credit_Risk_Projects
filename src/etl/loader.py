import os
import time

import psycopg
import yaml
from dotenv import load_dotenv

from src.etl.transforms import parse_yyyymm, vintage_from_loan_id

with open("config/load_config.yaml", encoding="utf-8") as f:
    config = yaml.safe_load(f)

orig_columns = config["file_types"]["origination"]["source_columns"]
perf_columns = config["file_types"]["performance"]["source_columns"]

ORIG_SENTINELS = {
    "credit_score": "9999",
    "vantagescore": "9999",
    "mi_percentage": "999",
    "original_cltv": "999",
    "original_ltv": "999",
    "original_dti_ratio": "999",
    "number_of_units": "99",
    "number_of_borrowers": "99",
    "property_type": "99",
    "first_time_homebuyer": "9",
    "occupancy_status": "9",
    "channel": "9",
    "loan_purpose": "9",
    "postal_code": "000",
    "property_valuation_method": "7",
}
PERF_SENTINELS = {
    "estimated_loan_to_value": "999",
    "net_sales_proceeds": "U",
}


def blank_to_none(value: str) -> str | None:
    """Return None for an empty field, so it loads as NULL."""
    if value == "":
        return None
    return value


def transform_orig_row(fields: list[str], counts: dict) -> tuple:
    """Turn one origination line into a dim_loan row.

    Sentinel codes become NULL and are counted per field in counts. The two
    date fields are parsed from YYYYMM (D-026). vintage_code is derived from
    the loan ID and appended as the last value.
    """
    results = []
    for i, value in enumerate(fields):
        name = orig_columns[i]
        if value == ORIG_SENTINELS.get(name):
            counts[name] = counts.get(name, 0) + 1
            results.append(None)
        else:
            results.append(blank_to_none(value))
    results[1] = parse_yyyymm(fields[1])
    results[3] = parse_yyyymm(fields[3])
    loan_id = fields[19]
    vintage = vintage_from_loan_id(loan_id)
    results.append(vintage)
    return tuple(results)


def get_connection() -> psycopg.Connection:
    """Open a connection to the database named in .env (or the environment)."""
    load_dotenv()
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def start_audit(source_file: str, target_table: str) -> int:
    """Write the audit row for a load before any data moves, and return its run_id.

    The row is committed on its own connection, so a load that fails later
    cannot roll it back (defect #1). Same pattern as dq_results (D-037).
    A row still marked 'running' after a load means the process died before
    it could record the outcome.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO load_audit "
                "(source_file, target_table, started_at, status) "
                "VALUES (%s, %s, now(), 'running') RETURNING run_id",
                (source_file, target_table),
            )
            return cur.fetchone()[0]


def finish_audit(run_id: int, status: str, rows_read: int, rows_loaded: int) -> None:
    """Record how a load ended, on its own connection.

    Runs after the data transaction has committed or rolled back. now() is
    the start of this short transaction, so finished_at minus started_at is
    the real duration of the load (defect #2).
    """
    with get_connection() as conn:
        conn.execute(
            "UPDATE load_audit SET finished_at = now(), rows_read = %s, "
            "rows_loaded = %s, status = %s WHERE run_id = %s",
            (rows_read, rows_loaded, status, run_id),
        )


def write_field_metrics(
    cur: psycopg.Cursor, run_id: int, metric_type: str, values: dict
) -> None:
    """Write one load_audit_field row per field with a count above zero.

    Called inside the data transaction, so the counts are kept only if the
    rows they describe are kept.
    """
    for field_name, value in values.items():
        cur.execute(
            "INSERT INTO load_audit_field "
            "(run_id, field_name, metric_type, metric_value) "
            "VALUES (%s, %s, %s, %s)",
            (run_id, field_name, metric_type, value),
        )


def load_origination(path: str) -> dict:
    """Load one origination file into dim_loan and record the run in load_audit.

    Rows outside the 24 vintages in dim_vintage are skipped and counted
    (D-033). Returns the sentinel counts per field.
    """
    counts = {}
    rows_read = 0
    rows_loaded = 0
    scope_counts = {}
    columns = ", ".join(orig_columns + ["vintage_code"])
    sql = f"COPY dim_loan ({columns}) FROM STDIN"

    run_id = start_audit(path, "dim_loan")
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT vintage_code FROM dim_vintage")
                valid_vintages = set()
                for row in cur.fetchall():
                    valid_vintages.add(row[0])

                with cur.copy(sql) as copy:
                    with open(path, encoding="utf-8") as f:
                        for line in f:
                            rows_read += 1
                            fields = line.rstrip("\n").split("|")
                            # Scope first, so a rejected row adds nothing to the
                            # field counts that R-02 reconciles against the table
                            vintage = vintage_from_loan_id(fields[19])
                            if vintage not in valid_vintages:
                                scope_counts[vintage] = scope_counts.get(vintage, 0) + 1
                                continue
                            row = transform_orig_row(fields, counts)
                            copy.write_row(row)
                            rows_loaded += 1

                write_field_metrics(cur, run_id, "sentinel_null", counts)
                write_field_metrics(cur, run_id, "out_of_scope", scope_counts)
    except BaseException:  # BaseException so Ctrl+C is recorded too
        finish_audit(run_id, "failed", rows_read, 0)
        raise
    finish_audit(run_id, "success", rows_read, rows_loaded)
    return counts


def transform_perf_row(fields: list[str], counts: dict, range_counts: dict) -> tuple:
    """Turn one performance line into a fact_loan_performance row.

    As transform_orig_row, plus: current_interest_rate above 30 becomes NULL
    (D-032) and negative months_to_maturity is counted (D-034), both in
    range_counts.
    """
    results = []
    for i, value in enumerate(fields):
        name = perf_columns[i]
        if value == PERF_SENTINELS.get(name):
            counts[name] = counts.get(name, 0) + 1
            results.append(None)
        else:
            results.append(blank_to_none(value))
    results[1] = parse_yyyymm(fields[1])
    results[6] = parse_yyyymm(fields[6])
    results[9] = parse_yyyymm(fields[9])
    results[12] = parse_yyyymm(fields[12])
    if results[10] is not None and float(results[10]) > 30:
        range_counts["current_interest_rate"] = (
            range_counts.get("current_interest_rate", 0) + 1
        )
        results[10] = None
    if results[5] is not None and int(results[5]) < 0:
        range_counts["months_to_maturity"] = (
            range_counts.get("months_to_maturity", 0) + 1
        )
    loan_id = fields[0]
    vintage = vintage_from_loan_id(loan_id)
    results.append(vintage)
    return tuple(results)


def load_performance(path: str) -> dict:
    """Load one performance file into fact_loan_performance and record the run.

    Same audit pattern and scope rule as load_origination. Prints the rows
    per second. Returns the sentinel counts per field.
    """
    started = time.perf_counter()
    counts = {}
    range_counts = {}
    rows_read = 0
    rows_loaded = 0
    scope_counts = {}
    columns = ", ".join(perf_columns + ["vintage_code"])
    sql = f"COPY fact_loan_performance ({columns}) FROM STDIN"

    run_id = start_audit(path, "fact_loan_performance")
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT vintage_code FROM dim_vintage")
                valid_vintages = set()
                for row in cur.fetchall():
                    valid_vintages.add(row[0])

                with cur.copy(sql) as copy:
                    with open(path, encoding="utf-8") as f:
                        for line in f:
                            rows_read += 1
                            fields = line.rstrip("\n").split("|")
                            # Scope first, so a rejected row adds nothing to the
                            # field counts that R-02 reconciles against the table
                            vintage = vintage_from_loan_id(fields[0])
                            if vintage not in valid_vintages:
                                scope_counts[vintage] = scope_counts.get(vintage, 0) + 1
                                continue
                            row = transform_perf_row(fields, counts, range_counts)
                            copy.write_row(row)
                            rows_loaded += 1

                write_field_metrics(cur, run_id, "sentinel_null", counts)
                write_field_metrics(cur, run_id, "out_of_range", range_counts)
                write_field_metrics(cur, run_id, "out_of_scope", scope_counts)
    except BaseException:  # BaseException so Ctrl+C is recorded too
        finish_audit(run_id, "failed", rows_read, 0)
        raise
    finish_audit(run_id, "success", rows_read, rows_loaded)
    elapsed = time.perf_counter() - started
    print(
        f"{rows_loaded} rows in {elapsed:.1f}s = {rows_loaded / elapsed:.0f} rows/sec"
    )
    return counts
