-- Completeness: missing count per field per vintage.
-- Long format (field_name, vintage_code, missing_count) to match dq_results.
-- UNION ALL, never UNION - plain UNION would drop duplicate rows and
-- silently understate a vintage whose count matches another's.
-- Three fields only. The remaining 29 are generated in the step 9 runner,
-- not hand-written: 32 blocks is ~160 lines differing by one word each.

SELECT 'original_dti_ratio' AS field_name,
        vintage_code,
        COUNT(*) - COUNT(original_dti_ratio) AS missing_count
 FROM dim_loan
 GROUP BY vintage_code
 UNION ALL
SELECT 'credit_score',
        vintage_code,
        COUNT(*) - COUNT(credit_score)
 FROM dim_loan
 GROUP BY vintage_code
 UNION ALL
SELECT 'original_ltv',
        vintage_code,
        COUNT(*) - COUNT(original_ltv)
 FROM dim_loan
 GROUP BY vintage_code
 ORDER BY field_name, vintage_code;
