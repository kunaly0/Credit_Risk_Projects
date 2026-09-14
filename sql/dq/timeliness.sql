-- Timeliness rules R-15 and R-16.
-- See docs/dq_rules.md for thresholds and rationale.
--
-- BASIS: gaps are measured on monthly_reporting_period, NOT loan_age.
-- loan_age repeats in 471,248 rows across 11,606 loans, so any gap count
-- derived from it is wrong in both directions - see R-16 and query 3.
--
-- Dates are converted to a single month number (year * 12 + month) so a
-- subtraction gives months, not days. Every reporting period is the 1st
-- of a month, enforced by a CHECK in sql/02.
--
-- Queries 1 and 3 scan all 19.8M rows and sort them into 299,999 windows.
-- Expect 2-4 minutes each.

-- R-15  Reporting gap rate.
-- Expect ~107 gap events, ~106 loans, ~643 missing months.
WITH numbered AS (
    SELECT loan_sequence_number,
           EXTRACT(YEAR  FROM monthly_reporting_period) * 12
         + EXTRACT(MONTH FROM monthly_reporting_period) AS month_no
    FROM fact_loan_performance
),
stepped AS (
    SELECT loan_sequence_number,
           month_no - LAG(month_no) OVER (PARTITION BY loan_sequence_number
                                          ORDER BY month_no) AS month_step
    FROM numbered
)
SELECT COUNT(*)                             AS gap_events,
       COUNT(DISTINCT loan_sequence_number) AS loans_with_gaps,
       SUM(month_step - 1)                  AS total_missing_months
FROM stepped
WHERE month_step > 1;

-- R-15 supporting: where do the gaps sit in a loan's life?
-- months_before_end = 0 means the gap is at the loan's final row.
-- Expect ~24 of 107 within 3 months of the end, average ~35 months.
WITH numbered AS (
    SELECT loan_sequence_number,
           EXTRACT(YEAR  FROM monthly_reporting_period) * 12
         + EXTRACT(MONTH FROM monthly_reporting_period) AS month_no
    FROM fact_loan_performance
),
stepped AS (
    SELECT loan_sequence_number,
           month_no,
           month_no - LAG(month_no) OVER (PARTITION BY loan_sequence_number
                                          ORDER BY month_no) AS month_step,
           MAX(month_no) OVER (PARTITION BY loan_sequence_number) AS last_month_no
    FROM numbered
),
gaps AS (
    SELECT loan_sequence_number,
           month_step - 1           AS months_missing,
           last_month_no - month_no AS months_before_end
    FROM stepped
    WHERE month_step > 1
)
SELECT COUNT(*)                         AS gap_events,
       MIN(months_before_end)           AS closest_to_end,
       MAX(months_before_end)           AS furthest_from_end,
       ROUND(AVG(months_before_end), 1) AS avg_months_before_end,
       COUNT(CASE WHEN months_before_end <= 3 THEN 1 END) AS within_3_months_of_end
FROM gaps;

-- R-16  loan_age repeats. Report only.
-- A step of 0 means the same loan_age appeared in two different months.
-- R-08 already proved no duplicate loan-month rows, so these are
-- genuinely different months carrying the same age.
-- Expect ~471,248 rows across ~11,606 loans.
WITH stepped AS (
    SELECT loan_sequence_number,
           loan_age - LAG(loan_age) OVER (PARTITION BY loan_sequence_number
                                          ORDER BY loan_age) AS age_step
    FROM fact_loan_performance
)
SELECT COUNT(*)                             AS repeat_rows,
       COUNT(DISTINCT loan_sequence_number) AS loans_affected
FROM stepped
WHERE age_step < 1;
