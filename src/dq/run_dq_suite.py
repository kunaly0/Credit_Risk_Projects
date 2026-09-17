"""Data quality suite runner.

Executes the rules in docs/dq_rules.md against the loaded Freddie Mac
data and persists results to dq_results.

Connection handling is duplicated from src/etl/loader.py rather than
imported (D-038). loader.py reads config/load_config.yaml at module
import, on a relative path, so importing anything from it would force
this runner to be launched from the repo root and to load a config file
it never uses.

Eight of the 18 rules in docs/dq_rules.md are automated here. The rest
are report-only (R-06, R-07, R-12, R-16, R-17, R-18) or need the audit
trail rather than the data (R-01, R-02). R-04 and R-14 are one-off
findings, not recurring checks.

R-03 applies a single threshold pair to both fields it covers, derived
from original_dti_ratio's baseline of 2.62%. credit_score is therefore
judged against the wrong baseline. Per-field thresholds need a rule
structure this runner does not yet have.
"""

import os

import psycopg
from dotenv import load_dotenv


def get_connection() -> psycopg.Connection:
    """Open a connection to the credit_risk database.

    Credentials come from .env, never from code or config.
    """
    load_dotenv()
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def next_run_id() -> int:
    """Return the next suite run_id.

    dq_results has no sequence of its own for run_id - the surrogate key
    counts rows, not runs - so the next run is one past the highest
    recorded. COALESCE handles the empty-table case, where MAX returns
    NULL.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COALESCE(MAX(run_id), 0) + 1 FROM dq_results")
            return cur.fetchone()[0]


RULES = [
    {
        "rule_id": "R-03",
        "scope_type": "field_vintage",
        "metric_name": "missing_pct",
        "sql": "SELECT vintage_code || '|original_dti_ratio' AS scope_value, "
        "ROUND(100.0 * (COUNT(*) - COUNT(original_dti_ratio)) / COUNT(*), 3) "
        "FROM dim_loan GROUP BY vintage_code "
        "UNION ALL "
        "SELECT vintage_code || '|credit_score', "
        "ROUND(100.0 * (COUNT(*) - COUNT(credit_score)) / COUNT(*), 3) "
        "FROM dim_loan GROUP BY vintage_code "
        "ORDER BY 1",
        "warn_above": 5.23,
        "fail_above": 10.46,
    },
    {
        "rule_id": "R-05",
        "scope_type": "field",
        "metric_name": "undocumented_codes",
        "sql": "SELECT 'loan_delinquency_status', COUNT(*) "
        "FROM fact_loan_performance "
        "WHERE loan_delinquency_status NOT BETWEEN '00' AND '99' "
        "AND loan_delinquency_status <> 'RA'",
        "fail_above": 0,
    },
    {
        "rule_id": "R-08",
        "scope_type": "portfolio",
        "metric_name": "duplicate_loan_months",
        "sql": "SELECT NULL, COUNT(*) FROM (SELECT loan_sequence_number, "
        "monthly_reporting_period FROM fact_loan_performance "
        "GROUP BY loan_sequence_number, monthly_reporting_period "
        "HAVING COUNT(*) > 1) AS d",
        "fail_above": 0,
    },
    {
        "rule_id": "R-09",
        "scope_type": "portfolio",
        "metric_name": "duplicate_loans",
        "sql": "SELECT NULL AS scope_value, COUNT(*) AS metric_value "
        "FROM (SELECT loan_sequence_number FROM dim_loan "
        "GROUP BY loan_sequence_number HAVING COUNT(*) > 1) AS d",
        "fail_above": 0,
    },
    {
        "rule_id": "R-10",
        "scope_type": "portfolio",
        "metric_name": "vintage_prefix_deviation",
        "sql": "SELECT NULL, ABS(COUNT(*) - 24) FROM (SELECT vintage_code, "
        "LEFT(loan_sequence_number, 5) FROM dim_loan "
        "GROUP BY vintage_code, LEFT(loan_sequence_number, 5)) AS g",
        "fail_above": 0,
    },
    {
        "rule_id": "R-11",
        "scope_type": "portfolio",
        "metric_name": "orphan_rows",
        "sql": "SELECT NULL AS scope_value, COUNT(*) AS metric_value "
        "FROM fact_loan_performance f "
        "LEFT JOIN dim_loan d ON "
        "f.loan_sequence_number = d.loan_sequence_number "
        "WHERE d.loan_sequence_number IS NULL",
        "fail_above": 0,
    },
    {
        "rule_id": "R-13",
        "scope_type": "portfolio",
        "metric_name": "early_maturity",
        "sql": "SELECT NULL AS scope_value, COUNT(*) AS metric_value "
        "FROM dim_loan WHERE first_payment_date > maturity_date",
        "fail_above": 0,
    },
    {
        "rule_id": "R-15",
        "scope_type": "portfolio",
        "metric_name": "missing_months_pct",
        "sql": "WITH numbered AS (SELECT loan_sequence_number, "
        "EXTRACT(YEAR FROM monthly_reporting_period) * 12 "
        "+ EXTRACT(MONTH FROM monthly_reporting_period) AS month_no "
        "FROM fact_loan_performance), "
        "stepped AS (SELECT month_no - LAG(month_no) OVER "
        "(PARTITION BY loan_sequence_number ORDER BY month_no) AS month_step "
        "FROM numbered) "
        "SELECT NULL, ROUND(100.0 * COALESCE(SUM(month_step - 1), 0) "
        "/ (SELECT COUNT(*) FROM fact_loan_performance), 4) "
        "FROM stepped WHERE month_step > 1",
        "warn_above": 0.1,
        "fail_above": 1.0,
    },
]


def run_rule(rule: dict, conn: psycopg.Connection) -> list:
    """Execute one rule's SQL and return its rows."""
    with conn.cursor() as cur:
        cur.execute(rule["sql"])
        return cur.fetchall()


def evaluate(value, rule: dict) -> str:
    """Compare a metric against a rule's thresholds.

    Returns 'pass', 'warn' or 'fail'. Rules with no threshold are
    report-only and always return 'pass' - the number is the finding,
    not a verdict.
    """
    if rule.get("fail_above") is not None and value > rule["fail_above"]:
        return "fail"
    if rule.get("warn_above") is not None and value > rule["warn_above"]:
        return "warn"
    return "pass"


def start_result(run_id: int, rule: dict) -> int:
    """Write the marker row for a rule and commit it on its own connection.

    One marker per rule, written BEFORE the rule executes, so a crash
    leaves evidence (D-037). scope_value is NULL and metric_name is
    'rule_status' - the literal name keeps the marker from colliding with
    a portfolio rule's detail row on the NULLS NOT DISTINCT constraint,
    since both would otherwise have a NULL scope_value.
    """
    with get_connection() as audit_conn:
        with audit_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO dq_results
                    (run_id, rule_id, scope_type, scope_value,
                     metric_name, metric_value, status, checked_at)
                VALUES (%s, %s, %s, NULL, 'rule_status', NULL, 'running', now())
                RETURNING dq_result_id
                """,
                (run_id, rule["rule_id"], rule["scope_type"]),
            )
            return cur.fetchone()[0]


def write_details(run_id: int, rule: dict, rows: list) -> str:
    """Write one detail row per result row. Returns the worst status seen.

    Every rule's SQL returns two columns: scope_value then metric_value.
    A portfolio rule returns one row with a NULL scope; R-03 returns 48
    with a vintage in each. Both are handled by the same loop.
    """
    worst = "pass"
    with get_connection() as audit_conn:
        with audit_conn.cursor() as cur:
            for scope_value, metric_value in rows:
                status = evaluate(metric_value, rule)
                if status == "fail":
                    worst = "fail"
                elif status == "warn" and worst != "fail":
                    worst = "warn"
                cur.execute(
                    """
                    INSERT INTO dq_results
                        (run_id, rule_id, scope_type, scope_value,
                         metric_name, metric_value, status, checked_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, now())
                    """,
                    (
                        run_id,
                        rule["rule_id"],
                        rule["scope_type"],
                        scope_value,
                        rule["metric_name"],
                        metric_value,
                        status,
                    ),
                )
    return worst


def finish_result(result_id: int, status: str) -> None:
    """Update a rule's marker row with its overall status."""
    with get_connection() as audit_conn:
        with audit_conn.cursor() as cur:
            cur.execute(
                "UPDATE dq_results SET status = %s, checked_at = now() "
                "WHERE dq_result_id = %s",
                (status, result_id),
            )


if __name__ == "__main__":
    conn = get_connection()
    run_id = next_run_id()
    for rule in RULES:
        result_id = start_result(run_id, rule)
        try:
            rows = run_rule(rule, conn)
            worst = write_details(run_id, rule, rows)
            finish_result(result_id, worst)
            print(f"run {run_id} - {rule['rule_id']}: {worst} ({len(rows)} rows)")
        except Exception as exc:
            conn.rollback()
            print(f"run {run_id} - {rule['rule_id']}: ERROR - {exc}")
    conn.close()
