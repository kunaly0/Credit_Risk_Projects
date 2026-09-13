-- Uniqueness rules R-08, R-09, R-10.
-- See docs/dq_rules.md for thresholds and rationale.
--
-- R-09 cannot fail - the PK enforces it. Retained as evidence only.
-- R-08 CAN fail: the PK is three columns (vintage_code included, as
-- PostgreSQL requires the partition key in the PK), so it does not block
-- the same loan-month under two vintages. This does.
-- R-10 CAN fail: vintage_code is derived in Python, unverified by any
-- constraint.
--
-- R-08 scans all 19.8M rows. Expect 20-60 seconds.

-- R-08  Duplicate loan-month rows. Expect 0 rows.
SELECT loan_sequence_number,
       monthly_reporting_period,
       COUNT(*) AS rows_for_this_month
FROM fact_loan_performance
GROUP BY loan_sequence_number, monthly_reporting_period
HAVING COUNT(*) > 1;

-- R-09  Primary key integrity. Expect 0 rows.
SELECT loan_sequence_number,
       COUNT(*) AS rows_for_this_loan
FROM dim_loan
GROUP BY loan_sequence_number
HAVING COUNT(*) > 1;

-- R-10  Vintage derivation integrity. Expect exactly 24 rows,
-- one ID prefix per vintage_code.
SELECT vintage_code,
       LEFT(loan_sequence_number, 5) AS id_prefix,
       COUNT(*) AS loans
FROM dim_loan
GROUP BY vintage_code, LEFT(loan_sequence_number, 5)
ORDER BY vintage_code;
