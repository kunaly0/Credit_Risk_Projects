-- 12_create_dashboard_views.sql
-- Views the Power BI DQ dashboard reads, so it imports small summaries
-- instead of the 19.86M-row fact table. Re-runnable: CREATE OR REPLACE.

-- v_dq_latest - grain: one row per measurement in the most recent DQ run.
-- Marker rows (metric_name = 'rule_status') are left out; v_dq_rule_history
-- holds those. R-03 stores 'vintage|field' in scope_value, split here so
-- Power BI can join on vintage_code.
CREATE OR REPLACE VIEW v_dq_latest AS
SELECT
    d.run_id,
    d.rule_id,
    CASE WHEN d.scope_type = 'field_vintage'
         THEN SPLIT_PART(d.scope_value, '|', 1)
    END                         AS vintage_code,
    CASE WHEN d.scope_type = 'field_vintage'
         THEN SPLIT_PART(d.scope_value, '|', 2)
         WHEN d.scope_type = 'field'
         THEN d.scope_value
    END                         AS field_name,
    d.metric_name,
    d.metric_value,
    d.status,
    d.checked_at::date          AS checked_on
FROM dq_results AS d
WHERE d.run_id = (SELECT MAX(run_id) FROM dq_results)
  AND d.metric_name <> 'rule_status';

-- v_dq_rule_history - grain: one row per rule per DQ run (the marker rows)
CREATE OR REPLACE VIEW v_dq_rule_history AS
SELECT
    run_id,
    rule_id,
    status,
    checked_at::date            AS run_date
FROM dq_results
WHERE metric_name = 'rule_status';

-- v_load_latest - grain: one row per source file, its latest successful load.
-- The 2017 performance file was loaded four times (defect #12); only the
-- last is shown.
CREATE OR REPLACE VIEW v_load_latest AS
WITH ranked AS (
    SELECT
        a.run_id,
        a.target_table,
        REGEXP_REPLACE(a.source_file, '^.*[\\/]', '') AS file_name,
        a.rows_read,
        a.rows_loaded,
        ROW_NUMBER() OVER (PARTITION BY a.source_file
                           ORDER BY a.run_id DESC)     AS rn
    FROM load_audit AS a
    WHERE a.status = 'success'
)
SELECT
    run_id,
    target_table,
    file_name,
    rows_read,
    rows_loaded,
    rows_read - rows_loaded     AS rows_rejected
FROM ranked
WHERE rn = 1;

-- v_vintage_summary - grain: one row per vintage (24 rows)
CREATE OR REPLACE VIEW v_vintage_summary AS
SELECT
    v.vintage_code,
    v.vintage_year,
    v.vintage_quarter,
    v.economic_regime,
    COALESCE(l.loans, 0)        AS loans,
    COALESCE(f.loan_months, 0)  AS loan_months
FROM dim_vintage AS v
LEFT JOIN (SELECT vintage_code, COUNT(*) AS loans
           FROM dim_loan GROUP BY vintage_code) AS l
       ON l.vintage_code = v.vintage_code
LEFT JOIN (SELECT vintage_code, COUNT(*) AS loan_months
           FROM fact_loan_performance GROUP BY vintage_code) AS f
       ON f.vintage_code = v.vintage_code;

-- v_macro_national - grain: one row per month. Adds the month-on-month
-- unemployment change and the R-19 flag (move above 2 points, or GDP growth
-- beyond +-20). A NULL month gives no flag, as in sql/dq/macro_jumps.sql.
CREATE OR REPLACE VIEW v_macro_national AS
WITH changes AS (
    SELECT
        month,
        unemployment,
        hpi,
        mortgage_rate,
        gdp_growth,
        unemployment - LAG(unemployment) OVER (ORDER BY month) AS unemployment_change
    FROM dim_macro
)
SELECT
    *,
    COALESCE(ABS(unemployment_change) > 2, false)
        OR COALESCE(ABS(gdp_growth) > 20, false)            AS r19_flag
FROM changes;
