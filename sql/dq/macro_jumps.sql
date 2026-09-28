-- DQ rule: macro jump flags (S06, D-044). Flags possible-but-unusual values
-- for review. Flags never block the load.
-- Thresholds: unemployment moves more than 2 points in one month;
-- gdp_growth beyond +-20 (annualised).
-- Limits: misses slow crises (2008 never flags). A NULL month switches the
-- check off for the month after it (Nov 2025). LAG compares rows, not
-- calendar months, so PR May 2020 is compared with Feb 2020.
--
-- Reviewed 2026-09-28:
--   National Apr-Sep 2020: COVID (unemployment Apr +10.4, Jun -2.2;
--     GDP Q2 -27.98, Q3 +34.86). Real.
--   LA 2005-09 +6.4, MS 2005-09 +2.7: Hurricane Katrina. Real.
--   LA 2005-12 -5.2: post-Katrina fall. Likely real, not confirmed.
--   NC 2008-11 +2.3, PR 2002-02 +2.2: cause not confirmed. Kept as is.
--   State flags in 2020: COVID, not reviewed one by one.

-- National
WITH changes AS (
    SELECT
        month,
        unemployment,
        unemployment - LAG(unemployment) OVER (ORDER BY month) AS unemp_change,
        gdp_growth
    FROM dim_macro
)
SELECT month, unemployment, unemp_change, gdp_growth
FROM changes
WHERE ABS(unemp_change) > 2
   OR ABS(gdp_growth) > 20
ORDER BY month;

-- State
WITH changes AS (
    SELECT
        property_state,
        month,
        unemployment,
        unemployment - LAG(unemployment)
            OVER (PARTITION BY property_state ORDER BY month) AS unemp_change
    FROM dim_macro_state
)
SELECT property_state, month, unemployment, unemp_change
FROM changes
WHERE ABS(unemp_change) > 2
ORDER BY property_state, month;
