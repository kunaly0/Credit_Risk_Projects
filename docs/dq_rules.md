R-01  Audit-to-table reconciliation
Dimension   Consistency (audit trail vs actual data)
Checks      SUM(rows_loaded) in load_audit for fact_loan_performance
            equals COUNT(*) of fact_loan_performance
Threshold   Difference = 0
Why         Row counts are exact; any gap means the audit trail
            does not describe the data, so lineage cannot be trusted
Result      11 Sep 2026 - FAIL
            Audit 28,260,469 vs table 19,859,812
            Gap 8,400,657 = 3 x 2,800,219
            Cause: 2017 reloads; TRUNCATE is not logged

R-02  Audit-to-table completeness reconciliation
Dimension   Consistency (audit trail vs actual data)
Checks      Sum of load_audit_field sentinel_null per field per year
            equals COUNT(*) - COUNT(field) in dim_loan for that year
Threshold   Difference = 0
Why         Counts are exact. A gap means values arrived NULL by a path
            the loader never counted, so the audit understates missingness
Result      11 Sep 2026 - PASS for original_dti_ratio and credit_score
            6 of 6 years exact on both

R-03  Completeness by field by vintage
Dimension   Completeness
Checks      (COUNT(*) - COUNT(field)) / COUNT(*) per vintage_code
Baseline    Median missing rate for that field across all 24 vintages
Threshold   Deadband - no rule fires below 0.1% missing, whatever the
            multiple. Above the deadband: WARN above 2x baseline,
            FAIL above 4x baseline
Why         Fields differ by orders of magnitude in normal missingness,
            so one absolute line is either blind or noisy. The deadband
            exists because a near-zero baseline makes any multiple of it
            near-zero too - original_ltv has a median of 0 missing, so
            without a floor 11 vintages would FAIL on 1 to 3 loans out
            of 12,500. Alert fatigue on day one
Result      11 Sep 2026
            original_dti_ratio  baseline 2.62%  WARN 2017Q1 6.50%
                                FAIL 2012Q1-Q4  32.0 to 39.1%
            credit_score        baseline 0.060%  max 0.112% - silent
            original_ltv        baseline 0%      max 0.024% - silent
Limitation  Cannot flag a uniformly bad field - see R-04

R-04  Absolute completeness floor
Dimension   Completeness
Checks      (COUNT(*) - COUNT(field)) / COUNT(*) per field per vintage
Threshold   FAIL if above 90% in every one of the 24 vintages
Why         R-03 is relative and cannot flag a uniformly empty field.
            A field missing in over 90% of rows across the whole
            development window carries no usable information, whatever
            its own baseline says
Result      11 Sep 2026 - FAIL
            vantagescore              100% missing, all 24 vintages
            property_valuation_method 100% missing 2005-2012,
                                      99.1% in 2017
Action      Both excluded from Project 1 feature candidates.
            Excluded by evidence, not by assumption
