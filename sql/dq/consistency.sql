-- Consistency rules R-11, R-12, R-13.
-- See docs/dq_rules.md for thresholds and rationale.
--
-- R-11 cannot fail while the FK is in place - but sql/02 notes the FK may
-- be dropped around a bulk load, so it stays a live control.
-- R-12 is report-only. A balance above the original is capitalised
-- interest from a modification, not a fault.
-- R-13 CAN fail: no constraint enforces it (see D-020).

-- R-11  Referential integrity, fact to dimension. Expect 0.
-- LEFT JOIN keeps every fact row; a NULL on the dimension side means
-- no matching loan exists.
SELECT COUNT(*) AS orphan_rows
FROM fact_loan_performance f
LEFT JOIN dim_loan d
  ON f.loan_sequence_number = d.loan_sequence_number
WHERE d.loan_sequence_number IS NULL;

-- R-12  Current balance above original balance. Report only.
-- Expect ~186,046 rows from ~5,702 distinct loans.
-- Count loans, not rows: one modified loan reports a raised balance
-- every month for years, so the row count overstates the scale.
SELECT COUNT(*)                                AS upb_exceeds_original,
       COUNT(DISTINCT f.loan_sequence_number)  AS loans_affected,
       COUNT(DISTINCT CASE WHEN f.modification_flag = 'Y'
                           THEN f.loan_sequence_number END) AS loans_modified,
       MIN(f.current_actual_upb - d.original_upb) AS min_excess,
       MAX(f.current_actual_upb - d.original_upb) AS max_excess,
       AVG(f.current_actual_upb - d.original_upb) AS avg_excess
FROM fact_loan_performance f
INNER JOIN dim_loan d
  ON f.loan_sequence_number = d.loan_sequence_number
WHERE f.current_actual_upb > d.original_upb;

-- R-13  Maturity date must not precede first payment date. Expect 0.
-- No CHECK constraint enforces this - omitted in S02 per D-020, because
-- first_payment_date is overwritten on modification.
SELECT COUNT(*) AS early_maturity
FROM dim_loan
WHERE first_payment_date > maturity_date;
