-- Validity rules R-05, R-06, R-07.
-- See docs/dq_rules.md for thresholds and rationale.
--
-- The 21 CHECK constraints enforce legal ranges at load, so a violation
-- can never reach the table. These rules measure two other things:
-- what the constraints LET THROUGH, and what the documentation says a
-- boundary means. Values the constraints REJECTED live in
-- load_audit_field as out_of_range.

-- R-05  Categorical domain conformance. Expect only documented codes.
-- harp_indicator domain is {Y,N}. Expect Y 19,203 / N 280,796 / no NULLs.
SELECT harp_indicator, COUNT(*) AS loans
FROM dim_loan
GROUP BY harp_indicator
ORDER BY harp_indicator;

-- loan_delinquency_status domain per the S01 dictionary: '00'-'99',
-- 'RA' (REO acquisition), 'XX' (not available).
-- Expect 'RA' 65,289 rows and 'XX' 0 rows.
-- NOTE: a filter written as >= '03' would sweep in 'RA' silently,
-- because letters sort after digits in text comparison.
SELECT loan_delinquency_status, COUNT(*) AS rows
FROM fact_loan_performance
WHERE loan_delinquency_status NOT BETWEEN '00' AND '99'
GROUP BY loan_delinquency_status
ORDER BY loan_delinquency_status;

-- R-06  Documented sentinel ceilings. Report only.
-- User Guide field 10: DTI above 65 is disclosed as Not Available, so 65
-- is a reporting boundary, not a natural maximum.
-- Expect max 65 in all 16 pre-crisis quarters; max 50 in 2012-2017
-- except 2012Q2 at 57. The 50 ceiling is NOT documented - see R-06 Open.
SELECT vintage_code,
       MIN(original_dti_ratio) AS min_dti,
       MAX(original_dti_ratio) AS max_dti,
       COUNT(CASE WHEN original_dti_ratio > 50 THEN 1 END) AS dti_over_50
FROM dim_loan
GROUP BY vintage_code
ORDER BY vintage_code;

-- R-07  Numeric plausibility. Report only.
-- No pass/fail: a $9,000 mortgage is unusual, not invalid, and there is
-- no defensible cut-off without business input.
-- Expect min 9,000 / max 1,187,000 / 129 loans under 20,000 portfolio-wide.
-- All min and max values end in 000 - User Guide field 11 rounds UPB to
-- the nearest $1,000.
SELECT vintage_code,
       MIN(original_upb) AS min_upb,
       MAX(original_upb) AS max_upb,
       COUNT(CASE WHEN original_upb < 20000 THEN 1 END) AS upb_under_20k
FROM dim_loan
GROUP BY vintage_code
ORDER BY vintage_code;
