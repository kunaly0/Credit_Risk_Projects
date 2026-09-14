# Data Quality Rules - Project 0, S04

Schema for every rule. Five required labels, two optional.
Labels are padded to 12 characters; continuation lines indent 12 spaces.

  Dimension   one of: Completeness, Validity, Uniqueness,
              Consistency, Timeliness
  Checks      what the query measures
  Threshold   the pass/fail boundary, or "Report only" where the rule
              produces a number for a human rather than a verdict
  Why         why that boundary, and why the rule exists at all
  Result      dated outcome
  Notes       optional - limitations, related findings, actions taken
  Open        optional - unresolved items. Step 10 collects these

Queries live in sql/dq/. Results move to the dq_results table at step 8.

---

R-01  Audit-to-table reconciliation
Dimension   Consistency
Checks      SUM(rows_loaded) in load_audit for fact_loan_performance
            equals COUNT(*) of fact_loan_performance
Threshold   Difference = 0
Why         Row counts are exact; any gap means the audit trail does not
            describe the data, so lineage cannot be trusted
Result      11 Sep 2026 - FAIL
            Audit 28,260,469 vs table 19,859,812
            Gap 8,400,657 = 3 x 2,800,219
            Cause: 2017 reloads; TRUNCATE is not logged
Notes       Not "fixed" by deleting the three extra audit rows. An audit
            trail that can be edited until it matches the data proves
            nothing. Supersede, never delete
Open        Defect #12 - TRUNCATE is not audited. Fixing it means logging
            a removal event, after which R-01 compares loaded minus
            removed against the table

R-02  Audit-to-table completeness reconciliation
Dimension   Consistency
Checks      Sum of load_audit_field sentinel_null per field per year
            equals COUNT(*) - COUNT(field) in dim_loan for that year
Threshold   Difference = 0
Why         Counts are exact. A gap means values arrived NULL by a path
            the loader never counted, so the audit understates missingness
Result      11 Sep 2026 - PASS
            original_dti_ratio, credit_score, original_ltv
            9 of 9 year-field combinations exact
Notes       load_audit_field only writes a row when a count exceeds zero,
            so "no row" is ambiguous - zero, or never checked. dq_results
            must record passes and zeros

R-03  Completeness by field by vintage
Dimension   Completeness
Checks      (COUNT(*) - COUNT(field)) / COUNT(*) per vintage_code
Threshold   Baseline is the median missing rate for that field across all
            24 vintages. Deadband: nothing fires below 0.1% missing,
            whatever the multiple. Above the deadband, WARN above 2x
            baseline and FAIL above 4x baseline
Why         Fields differ by orders of magnitude in normal missingness, so
            one absolute line is either blind or noisy. The deadband
            exists because a near-zero baseline makes any multiple of it
            near-zero too - original_ltv has a median of 0 missing, so
            without a floor 11 vintages would FAIL on 1 to 3 loans out of
            12,500. Alert fatigue on day one
Result      11 Sep 2026
            original_dti_ratio  baseline 2.62%  WARN 2017Q1 6.50%
                                FAIL 2012Q1-Q4  32.0 to 39.1%
            credit_score        baseline 0.060%  max 0.112% - silent
            original_ltv        baseline 0%      max 0.024% - silent
Notes       Cannot flag a uniformly bad field - see R-04. The 2012 FAIL
            was investigated and is explained: see R-14

R-04  Absolute completeness floor
Dimension   Completeness
Checks      (COUNT(*) - COUNT(field)) / COUNT(*) per field per vintage
Threshold   FAIL if above 90% in every one of the 24 vintages
Why         R-03 is relative and cannot flag a uniformly empty field. A
            field missing in over 90% of rows across the whole development
            window carries no usable information, whatever its own
            baseline says
Result      11 Sep 2026 - FAIL
            vantagescore              100% missing, all 24 vintages
            property_valuation_method 100% missing 2005-2012,
                                      99.1% in 2017
Notes       Both excluded from Project 1 feature candidates. Excluded by
            evidence, not by assumption

R-05  Categorical domain conformance
Dimension   Validity
Checks      Every distinct value in a coded field appears in that field's
            documented domain
Threshold   Zero values outside the domain
Why         A code outside its domain cannot be interpreted. Unlike a
            numeric outlier there is no "close enough"
Result      12 Sep 2026 - PASS
            harp_indicator  Y 19,203 / N 280,796 / no NULLs. Domain {Y,N}
Notes       The 21 CHECK constraints enforce these domains at load, so a
            violation could never reach the table. R-05 verifies the
            constraint is doing its job; it cannot detect a bad value
            rejected at the door. Those live in load_audit_field as
            out_of_range

R-06  Documented sentinel ceilings
Dimension   Validity
Checks      MAX and MIN per field per vintage against the documented range
Threshold   Report only
Why         The ceiling is the finding, not a failure. User Guide field 10:
            DTI above 65 is disclosed as Not Available, so 65 is a
            reporting boundary, not a natural maximum. A rule that FAILed
            on it would be flagging documented behaviour as a defect
Result      12 Sep 2026
            original_dti_ratio  2005-2008 max 65 in all 16 quarters
                                2012-2017 max 50, except 2012Q2 at 57
Notes       A NULL DTI pre-2012 may mean "not collected" or "above 65".
            The data cannot distinguish them, so median imputation would
            replace the riskiest borrowers with an average one
Open        The 50 ceiling is not documented and is not enforced in the
            data - the single 57 proves it. DTI above 50 falls from
            9.8-14.6% pre-crisis to 0.001% after: a structural break, not
            drift. Cause unresolved - step 7

R-07  Numeric plausibility
Dimension   Validity
Checks      MIN, MAX and a low-end tail count per numeric field per vintage
Threshold   Report only
Why         CHECK constraints enforce the legal range. Plausibility is a
            separate question with no defensible cut-off without business
            input. A $9,000 mortgage is unusual, not invalid. Deleting 129
            loans on appearance alone is an unevidenced intervention a
            validator would reject
Result      12 Sep 2026
            original_upb  min 9,000 (2005Q1, 2008Q4)
                          max 1,187,000 (2012Q4)
                          129 loans under 20,000 = 0.043% of portfolio
Notes       All 48 min/max values end in 000 - User Guide field 11 rounds
            UPB to the nearest $1,000. It is a rounded figure, not exact
Open        MAX rises from 692,000 (2005Q1) to 1,187,000 (2012Q4),
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
            not block the same loan-month appearing under two different
            vintages. This check covers that gap. vintage_code is derived
            in Python from the loan ID, so a derivation fault would put
            one loan in two partitions and double-count its exposure
Result      13 Sep 2026 - PASS
            0 duplicate groups across 19,859,812 rows

R-09  Primary key integrity
Dimension   Uniqueness
Checks      Duplicate loan_sequence_number in dim_loan
Threshold   Zero
Why         Enforced by the PK, so it cannot fail. Retained as evidence
            the constraint is present and active, not as a live control
Result      13 Sep 2026 - PASS
            0 duplicates across 299,999 rows

R-10  Vintage derivation integrity
Dimension   Uniqueness
Checks      Each vintage_code pairs with exactly one loan ID prefix
            GROUP BY vintage_code, LEFT(loan_sequence_number, 5)
Threshold   Exactly 24 groups - one per vintage
Why         vintage_code is derived in Python from the loan ID and no
            database constraint verifies it. A wrong derivation would put
            loans in the wrong partition, corrupting every vintage-level
            statistic in Project 1 with nothing to signal it. The only
            uniqueness rule that can actually fail
Result      13 Sep 2026 - PASS
            24 groups, one prefix per vintage, 12,500 loans each except
            2008Q4 at 12,499
Notes       The 2008Q4 shortfall is loan F09Q10107924, rejected at load as
            out-of-scope 2009Q1 per D-033. The loader derives vintage from
            the loan ID, not the filename - had it trusted the filename,
            the loan would have loaded silently as 2008

R-11  Referential integrity, fact to dimension
Dimension   Consistency
Checks      LEFT JOIN fact to dim on loan_sequence_number, count rows
            where the dimension side is NULL
Threshold   Zero orphans
Why         Enforced by the FK, so it cannot fail while the FK is in
            place. Retained as a live control because sql/02 notes the FK
            may be dropped and re-added around a bulk load for throughput.
            If it is ever dropped and not restored, this check is the only
            thing that would catch orphaned performance rows
Result      13 Sep 2026 - PASS
            0 orphans across 19,859,812 rows, in ~2s - the join used
            indexes on both sides rather than scanning the tables
Notes       The reverse direction (loans with no performance history) was
            tested in the S04 SQL diagnostic: also 0

R-12  Current balance vs original balance
Dimension   Consistency
Checks      INNER JOIN fact to dim, count rows and distinct loans where
            current_actual_upb > original_upb
Threshold   Report only
Why         A balance above the original is expected, not a fault. Unpaid
            interest is capitalised onto the loan during a modification.
            A rule that FAILed here would flag correct data
Result      13 Sep 2026
            186,046 rows from 5,702 distinct loans = 1.9% of portfolio
            32.6 reporting months per affected loan on average - a
            permanent change, not a transient blip
            4,549 of 5,702 (79.8%) carry modification_flag = 'Y' on at
            least one row
            Excess: min $0.02, max $267,799, avg $16,495
Notes       modification_flag is PER ROW, not per loan. 5,695 of the 5,702
            have at least one row where the flag is not 'Y'. The flag
            marks the month a modification was reported, not the loan's
            status thereafter. Any Project 1 feature using it must
            aggregate to loan level first
            Max excess far exceeds the $1,000 UPB rounding in R-07, so
            rounding does not explain the large cases
Open        1,153 loans (20.2%) show a raised balance with no
            modification_flag on any row. Unexplained. Isolating them
            needs a loan-level subquery - deferred to step 7

R-13  Date ordering, maturity after first payment
Dimension   Consistency
Checks      COUNT of dim_loan rows where first_payment_date >
            maturity_date
Threshold   Zero
Why         No CHECK constraint enforces this. It was deliberately
            omitted in S02 because D-020 found first_payment_date is
            overwritten on modification, so the ordering could not be
            guaranteed at load. A live control, not evidence of a
            constraint - it can actually fail
Result      13 Sep 2026 - PASS
            0 rows across 299,999 loans. D-020's concern did not
            materialise in the sample

R-15  Reporting gaps in monthly history
Dimension   Timeliness
Checks      LAG on monthly_reporting_period converted to a month number,
            per loan. A step above 1 means months were never reported
Threshold   WARN above 0.1% of months missing per vintage,
            FAIL above 1%
Why         The User Guide states a servicer can fail to report a month,
            so a hole is documented and expected, not corruption. The rule
            measures the rate. 1% would mean one month in a hundred is
            absent, at which point time-to-default and performance windows
            in Project 1 stop being reliable
Result      13 Sep 2026 - PASS
            106 loans of 299,999 (0.035%) have at least one gap
            643 months missing of 19,859,812 (0.0032%)
            107 gap events from 106 loans - one loan went dark twice
Notes       24 of 107 gaps (22%) fall within 3 months of the loan's final
            reporting month; average is 35 months before the end. Most
            gaps are ordinary mid-life misses, but a fifth sit where
            deterioration before termination would be hidden. Those loans
            need checking in Project 1

R-16  loan_age is not a reliable monthly counter
Dimension   Validity
Checks      LAG on loan_age per loan; a step of 0 means the same age was
            reported in two different months
Threshold   Report only
Why         Found while measuring R-15. Gap counts computed from loan_age
            disagreed with counts computed from dates, and chasing the
            difference exposed the cause
Result      13 Sep 2026
            471,248 rows (2.4% of the fact table) across 11,606 loans
            (3.9% of the portfolio) repeat the previous row's loan_age
            All such steps are exactly 0 - repeats, never backwards
Notes       Measuring gaps on loan_age gave 88 loans / 688 months by
            arithmetic and 102 / 754 by LAG. The date-based figure is
            106 / 643. Both loan_age methods were wrong in both
            directions. Loan F05Q10002092 has 249 rows across a 249-month
            span with no gap at all, yet the arithmetic method scored it
            -1 and excluded it
            Any Project 1 feature built on loan_age - seasoning,
            time-to-default, performance windows - inherits this
Open        Cause unverified. D-020 records that first_payment_date is
            overwritten on modification, and loan_age is presumably
            derived from it, so a modification may stall the counter.
            Testable against modification_flag - step 7
