-- build_pd_target.sql - fill pd_target from the loan data (S08).
-- Re-runnable: empties the table and rebuilds it in one transaction, so a
-- failure leaves the previous version in place. Run after every loan
-- reload. Reads all 19.86M performance rows once; expect about a minute.
--
-- Usage, from the repo root:
--   psql -h localhost -U postgres -d credit_risk -f sql/model/build_pd_target.sql
--
-- Rules: header of sql/13_create_pd_target.sql, and D-050 to D-054.

\set ON_ERROR_STOP on

BEGIN;

TRUNCATE pd_target;

INSERT INTO pd_target (
    loan_sequence_number, vintage_code, first_payment_date, window_end,
    data_start, data_start_offset, default_month, default_trigger,
    exit_code, exit_month, exclusion_reason, target
)
-- Step 1 - one row per loan: the first month of each event.
-- A loan has at most one zero balance code (checked in S08), so
-- MIN(zero_balance_code) is that code.
WITH events AS (
    SELECT loan_sequence_number,
           MIN(monthly_reporting_period)                               AS data_start,
           MIN(CASE WHEN loan_delinquency_status BETWEEN '03' AND '99'
                    THEN monthly_reporting_period END)                  AS dpd90_month,
           MIN(CASE WHEN loan_delinquency_status = 'RA'
                    THEN monthly_reporting_period END)                  AS reo_month,
           MIN(CASE WHEN zero_balance_code IN ('02', '03', '09', '15')
                    THEN monthly_reporting_period END)                  AS loss_exit_month,
           MIN(CASE WHEN modification_flag IS NOT NULL
                    THEN monthly_reporting_period END)                  AS modification_month,
           MIN(CASE WHEN zero_balance_code IS NOT NULL
                    THEN monthly_reporting_period END)                  AS exit_month,
           MIN(zero_balance_code)                                       AS exit_code
    FROM fact_loan_performance
    GROUP BY loan_sequence_number
),
-- Step 2 - every loan, its window, and the earliest default event.
-- LEAST skips NULLs, so default_month is the first event that happened.
per_loan AS (
    SELECT d.loan_sequence_number,
           d.vintage_code,
           d.first_payment_date,
           (d.first_payment_date + INTERVAL '24 months')::date         AS window_end,
           e.data_start,
           (EXTRACT(YEAR FROM e.data_start) * 12 + EXTRACT(MONTH FROM e.data_start))
         - (EXTRACT(YEAR FROM d.first_payment_date) * 12
            + EXTRACT(MONTH FROM d.first_payment_date))                 AS data_start_offset,
           LEAST(e.dpd90_month, e.reo_month,
                 e.loss_exit_month, e.modification_month)               AS default_month,
           e.dpd90_month,
           e.reo_month,
           e.loss_exit_month,
           e.exit_code,
           e.exit_month
    FROM dim_loan d
    LEFT JOIN events e ON e.loan_sequence_number = d.loan_sequence_number
),
-- Step 3 - which event set the default month (on a tie, the first one
-- listed wins), and whether it fell inside the window.
flagged AS (
    SELECT p.*,
           CASE WHEN p.default_month IS NULL             THEN NULL
                WHEN p.dpd90_month     = p.default_month THEN 'dpd90'
                WHEN p.reo_month       = p.default_month THEN 'reo'
                WHEN p.loss_exit_month = p.default_month THEN 'loss_exit'
                ELSE 'modification'
           END                                                          AS default_trigger,
           COALESCE(p.default_month < p.window_end, FALSE)              AS bad_in_window
    FROM per_loan p
),
-- Step 4 - exclusions. The first reason that applies is the one recorded.
labelled AS (
    SELECT f.*,
           CASE WHEN f.data_start IS NULL           THEN 'no_performance'
                WHEN f.data_start_offset < -1       THEN 'early_start'         -- D-053
                WHEN f.data_start_offset > 0        THEN 'late_start'          -- D-053
                WHEN f.exit_code = '96'
                 AND f.exit_month < f.window_end
                 AND NOT f.bad_in_window            THEN 'buyback_in_window'   -- D-052
                WHEN f.exit_code = '16'
                 AND f.exit_month < f.window_end
                 AND NOT f.bad_in_window            THEN 'rpl_sale_in_window'  -- D-052 reasoning, none in the sample
           END                                                          AS exclusion_reason
    FROM flagged f
)
SELECT loan_sequence_number,
       vintage_code,
       first_payment_date,
       window_end,
       data_start,
       data_start_offset,
       default_month,
       default_trigger,
       exit_code,
       exit_month,
       exclusion_reason,
       CASE WHEN exclusion_reason IS NOT NULL THEN NULL
            WHEN bad_in_window                THEN 1
            ELSE 0
       END                                                              AS target
FROM labelled;

COMMIT;

ANALYZE pd_target;

-- Check: one row per exclusion reason, and the included loans by target.
SELECT COALESCE(exclusion_reason, 'included') AS status,
       target,
       COUNT(*)                               AS loans
FROM pd_target
GROUP BY exclusion_reason, target
ORDER BY status, target;
