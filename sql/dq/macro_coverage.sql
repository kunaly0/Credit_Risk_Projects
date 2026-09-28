-- macro coverage of the loan data (D-042, D-045).
-- Rerun after every load_fred.py run or loan reload.
-- Pass: query 1 fact_months = matched_months. Query 2 returns only GU, VI,
-- and PR for 2020-03 to 2020-04 (documented gaps, D-045).
-- Result 2026-09-28: 255 of 255 months matched. Unmatched loan-months:
-- GU 6,549, PR 603 (Mar-Apr 2020 only), VI 926 - about 0.04%. PASS.

-- 1. National: every loan month finds a dim_macro row
SELECT
    COUNT(*)       AS fact_months,
    COUNT(m.month) AS matched_months,
    MIN(f.month)   AS first_month,
    MAX(f.month)   AS last_month
FROM (SELECT DISTINCT monthly_reporting_period AS month
      FROM fact_loan_performance) AS f
LEFT JOIN dim_macro AS m ON m.month = f.month;

-- 2. State: loan-months with no dim_macro_state row, by state
SELECT
    l.property_state,
    COUNT(*)                        AS unmatched_loan_months,
    MIN(f.monthly_reporting_period) AS first_month,
    MAX(f.monthly_reporting_period) AS last_month
FROM fact_loan_performance AS f
JOIN dim_loan AS l
     ON l.loan_sequence_number = f.loan_sequence_number
LEFT JOIN dim_macro_state AS s
     ON s.property_state = l.property_state
    AND s.month = f.monthly_reporting_period
WHERE s.month IS NULL
GROUP BY l.property_state
ORDER BY l.property_state;
