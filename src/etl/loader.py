import os

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


def count_rows(path: str) -> int:
    total = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            total += 1
    return total


def read_first_rows(path: str, limit: int) -> None:
    with open(path, encoding="utf-8") as f:
        count = 0
        for line in f:
            fields = line.rstrip("\n").split("|")
            print(len(fields), fields[19])
            count += 1
            if count >= limit:
                break


def blank_to_none(value: str) -> str | None:
    if value == "":
        return None
    return value


def transform_orig_row(fields: list[str], counts: dict) -> tuple:
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
    load_dotenv()
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def load_origination(path: str) -> dict:
    counts = {}
    rows_read = 0
    rows_loaded = 0
    scope_counts = {}
    columns = ", ".join(orig_columns + ["vintage_code"])
    sql = f"COPY dim_loan ({columns}) FROM STDIN"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO load_audit "
                "(source_file, target_table, started_at, status) "
                "VALUES (%s, %s, now(), 'running') RETURNING run_id",
                (path, "dim_loan"),
            )
            run_id = cur.fetchone()[0]
            cur.execute("SELECT vintage_code FROM dim_vintage")
            valid_vintages = set()
            for row in cur.fetchall():
                valid_vintages.add(row[0])

            with cur.copy(sql) as copy:
                with open(path, encoding="utf-8") as f:
                    for line in f:
                        rows_read += 1
                        fields = line.rstrip("\n").split("|")
                        row = transform_orig_row(fields, counts)
                        if row[-1] not in valid_vintages:
                            scope_counts[row[-1]] = scope_counts.get(row[-1], 0) + 1
                            continue
                        copy.write_row(row)
                        rows_loaded += 1

            for field_name, value in counts.items():
                cur.execute(
                    "INSERT INTO load_audit_field "
                    "(run_id, field_name, metric_type, metric_value) "
                    "VALUES (%s, %s, 'sentinel_null', %s)",
                    (run_id, field_name, value),
                )

            for field_name, value in scope_counts.items():
                cur.execute(
                    "INSERT INTO load_audit_field "
                    "(run_id, field_name, metric_type, metric_value) "
                    "VALUES (%s, %s, 'out_of_scope', %s)",
                    (run_id, field_name, value),
                )

            cur.execute(
                "UPDATE load_audit SET finished_at = now(), rows_read = %s, "
                "rows_loaded = %s, status = 'success' WHERE run_id = %s",
                (rows_read, rows_loaded, run_id),
            )
    return counts


def transform_perf_row(fields: list[str], counts: dict, range_counts: dict) -> tuple:
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
    counts = {}
    range_counts = {}
    rows_read = 0
    rows_loaded = 0
    scope_counts = {}
    columns = ", ".join(perf_columns + ["vintage_code"])
    sql = f"COPY fact_loan_performance ({columns}) FROM STDIN"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO load_audit "
                "(source_file, target_table, started_at, status) "
                "VALUES (%s, %s, now(), 'running') RETURNING run_id",
                (path, "fact_loan_performance"),
            )
            run_id = cur.fetchone()[0]
            cur.execute("SELECT vintage_code FROM dim_vintage")
            valid_vintages = set()
            for row in cur.fetchall():
                valid_vintages.add(row[0])

            with cur.copy(sql) as copy:
                with open(path, encoding="utf-8") as f:
                    for line in f:
                        rows_read += 1
                        fields = line.rstrip("\n").split("|")
                        row = transform_perf_row(fields, counts, range_counts)
                        if row[-1] not in valid_vintages:
                            scope_counts[row[-1]] = scope_counts.get(row[-1], 0) + 1
                            continue
                        copy.write_row(row)
                        rows_loaded += 1

            for field_name, value in counts.items():
                cur.execute(
                    "INSERT INTO load_audit_field "
                    "(run_id, field_name, metric_type, metric_value) "
                    "VALUES (%s, %s, 'sentinel_null', %s)",
                    (run_id, field_name, value),
                )

            for field_name, value in range_counts.items():
                cur.execute(
                    "INSERT INTO load_audit_field "
                    "(run_id, field_name, metric_type, metric_value) "
                    "VALUES (%s, %s, 'out_of_range', %s)",
                    (run_id, field_name, value),
                )

            for field_name, value in scope_counts.items():
                cur.execute(
                    "INSERT INTO load_audit_field "
                    "(run_id, field_name, metric_type, metric_value) "
                    "VALUES (%s, %s, 'out_of_scope', %s)",
                    (run_id, field_name, value),
                )

            cur.execute(
                "UPDATE load_audit SET finished_at = now(), rows_read = %s, "
                "rows_loaded = %s, status = 'success' WHERE run_id = %s",
                (rows_read, rows_loaded, run_id),
            )
    return counts
