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

R-05  Categorical domain conformance
Dimension   Validity
Checks      Every distinct value in a coded field appears in that field's
            documented domain
Threshold   Zero values outside the domain
Why         A code outside its domain cannot be interpreted. Unlike a
            numeric outlier there is no "close enough"
Result      12 Sep 2026 - PASS
            harp_indicator  Y 19,203 / N 280,796 / no NULLs. Domain {Y,N}
Limitation  The 21 CHECK constraints enforce these domains at load, so a
            violation could never reach the table. R-05 verifies the
            constraint is doing its job; it cannot detect a bad value
            that was rejected at the door. Those live in load_audit_field
            as out_of_range

R-06  Documented sentinel ceilings
Dimension   Validity
Checks      MAX and MIN per field per vintage against the documented range
Threshold   Report only - no pass/fail
Why         The ceiling is the finding, not a failure. User Guide field 10:
            DTI above 65 is disclosed as Not Available, so 65 is a
            reporting boundary, not a natural maximum. A rule that FAILed
            on it would be flagging documented behaviour as a defect
Result      12 Sep 2026
            original_dti_ratio  2005-2008 max 65 in all 16 quarters
                                2012-2017 max 50, except 2012Q2 at 57
            The 50 ceiling is NOT documented in the User Guide and is
            not enforced in the data - the single 57 proves it. Open
Finding     DTI above 50 falls from 9.8-14.6% pre-crisis to 0.001% after.
            A structural break, not drift. Cause unresolved - step 7

R-07  Numeric plausibility
Dimension   Validity
Checks      MIN, MAX and a low-end tail count per numeric field per vintage
Threshold   Report only - no pass/fail
Why         CHECK constraints enforce the legal range. Plausibility is a
            separate question and has no defensible cut-off without
            business input. A $9,000 mortgage is unusual, not invalid.
            Deleting 129 loans on appearance alone is an unevidenced
            intervention a validator would reject
Result      12 Sep 2026
            original_upb  min 9,000 (2005Q1, 2008Q4)  max 1,187,000 (2012Q4)
                          129 loans under 20,000 = 0.043% of portfolio
Findings    All 48 min/max values end in 000 - User Guide field 11 rounds
            UPB to the nearest $1,000. It is a rounded figure, not exact
            MAX rises from 692,000 (2005Q1) to 1,187,000 (2012Q4),
            consistent with conforming loan limits. Untested - the
            super_conforming_flag column could confirm it

R-08  Duplicate loan-month rows
Dimension   Uniqueness
Checks      GROUP BY loan_sequence_number, monthly_reporting_period
            HAVING COUNT(*) > 1 across all 24 partitions
Threshold   Zero groups
Why         The PK is (vintage_code, loan_sequence_number,
            monthly_reporting_period) - three columns, because PostgreSQL
            requires the partition key in the PK. So the constraint does
            NOT block the same loan-month appearing under two different
            vintages. This check covers that gap. vintage_code is derived
            in Python from the loan ID, so a derivation fault would put
            one loan in two partitions and double-count its exposure
Result      13 Sep 2026 - PASS. 0 duplicate groups across 19,859,812 rows

R-09  Primary key integrity
Dimension   Uniqueness
Checks      Duplicate loan_sequence_number in dim_loan
Threshold   Zero
Why         Enforced by the PK, so it cannot fail. Retained as evidence
            the constraint is present and active, not as a live control
Result      13 Sep 2026 - PASS. 0 duplicate loan_sequence_number
            across 299,999 rows

R-10  Vintage derivation integrity
Dimension   Uniqueness / Consistency
Checks      Each vintage_code pairs with exactly one loan ID prefix
            GROUP BY vintage_code, LEFT(loan_sequence_number, 5)
Threshold   Exactly 24 groups - one per vintage
Why         vintage_code is derived in Python from the loan ID and no
            database constraint verifies it. A wrong derivation would put
            loans in the wrong partition, corrupting every vintage-level
            statistic in Project 1 with nothing to signal it. This is the
            only uniqueness rule that can actually fail
Result      13 Sep 2026 - PASS. 24 groups, one prefix per vintage,
            12,500 loans each except 2008Q4 at 12,499 (loan F09Q10107924
            rejected at load as out-of-scope 2009Q1, per D-033)
