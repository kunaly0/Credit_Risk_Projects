-- Audit reconciliation rules R-01 and R-02.
-- See docs/dq_rules.md for thresholds and rationale.
--
-- These compare what the loader RECORDED against what the table HOLDS.
-- Every other DQ file interrogates the data; this one interrogates the
-- audit trail.

-- R-01  Row counts: audit vs table. Currently FAILS.
-- Audit sums 28,260,469 against 19,859,812 actually present.
-- Cause: the 2017 performance file was loaded four times with TRUNCATE
-- between each, and TRUNCATE is not logged (defect #12). Not "fixed" by
-- deleting the extra audit rows - supersede, never delete.
SELECT SUM(rows_loaded) AS audit_rows_loaded
FROM load_audit
WHERE target_table = 'fact_loan_performance';

SELECT COUNT(*) AS table_rows
FROM fact_loan_performance;

-- R-02  Sentinel counts: audit vs table, per field per year.
-- The loader counted sentinel conversions at load time; this counts the
-- NULLs actually present now. They must agree, or values arrived NULL by
-- a path the loader never counted.
-- Verified 9 of 9 year-field combinations for original_dti_ratio,
-- credit_score and original_ltv.
SELECT laf.field_name,
       LEFT(la.source_file, LENGTH(la.source_file) - 4) AS source,
       laf.metric_value AS audit_sentinel_count
FROM load_audit_field laf
INNER JOIN load_audit la ON laf.run_id = la.run_id
WHERE laf.metric_type = 'sentinel_null'
  AND la.target_table = 'dim_loan'
ORDER BY laf.field_name, la.source_file;

-- Table-side counterpart. Sum the four quarters of a year and compare
-- against the audit figure above.
SELECT vintage_code,
       COUNT(*) - COUNT(original_dti_ratio) AS dti_missing,
       COUNT(*) - COUNT(credit_score)       AS credit_score_missing,
       COUNT(*) - COUNT(original_ltv)       AS ltv_missing
FROM dim_loan
GROUP BY vintage_code
ORDER BY vintage_code;
