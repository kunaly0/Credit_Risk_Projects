# Missing Data Methodology - Project 0, S04

One entry per field where values are absent or unreliable. Each states a
decision and the evidence behind it. Decisions bind Project 1 feature
work unless superseded by a dated DECISIONS entry.

Three possible decisions:
  KEEP AS CATEGORY  missingness carries information - do not impute
  IMPUTE            missingness is incidental - filling is safe
  EXCLUDE           the field is unusable in the development window

---

original_dti_ratio
Missing     23,957 loans (8.0%). By vintage: ~2.6% normal, 32-39% in 2012,
            6.5% in 2017Q1
Cause       HARP loans are disclosed as Not Available (R-14). 17,399 of
            2012's 17,400 are HARP. Pre-2012 missingness has a different
            cause: DTI above 65 is also suppressed (R-06)
Evidence    Missing-DTI loans reach serious delinquency at 7.77% vs 10.26%
            for loans with DTI - a 2.5pp separation (R-18)
Decision    KEEP AS CATEGORY
Why         Missingness separates on the outcome, so a median fill erases
            a real signal. It is also a perfect proxy for HARP status,
            meaning imputation would hide that these are post-crisis
            refinances
Caveat      The same NULL means two different things - HARP after 2012,
            suppressed-above-65 before. A single "missing" category
            conflates them. Project 1 should consider splitting by vintage
            era or using harp_indicator directly

vantagescore
Missing     100% in all 24 vintages. Zero usable values anywhere in the
            development window
Cause       A Release 47 field, backfilled as 9999 for historical
            originations. It did not exist when these loans were made
Evidence    R-04. Also invisible to R-03, because a field with a 100%
            baseline cannot deviate from itself - the reason R-04 exists
Decision    EXCLUDE
Why         No values to impute from and no variation to model. A field
            present in the schema but empty in the data
Caveat      Excluded for THIS development window only. Vintages after
            Release 47 will carry real values, so a model retrained on
            recent data should revisit this

credit_score
Missing     180 loans (0.060%). By vintage: 0 to 0.112%, worst 2008Q3.
            Zero missing in all four 2012 quarters
Cause       Not established. Rare enough that no pattern is visible
Evidence    R-03 - silent at every threshold, including the 0.1% deadband
            in most vintages. R-02 reconciles the counts to the loader
            audit exactly, 6 of 6 years
Decision    IMPUTE
Why         At 0.06% the treatment barely affects the model whichever way
            it goes, and nothing suggests these loans differ
            systematically. Unlike DTI, there is no documented suppression
            rule and no HARP-style proxy behind the blanks
Caveat      Not tested against the outcome the way DTI was in R-18. The
            decision rests on the rate being negligible, not on evidence
            that missingness is uninformative. If the rate rises in a
            future vintage, retest before carrying this forward

property_valuation_method
Missing     100% in 2005-2012, 99.1% in 2017. 445 loans portfolio-wide
            have a value - 0.15%
Cause       A Release 47 field that begins populating in 2017. It did not
            exist for earlier originations
Evidence    R-04. Sentinel '7' is converted to NULL per D-030
Decision    EXCLUDE
Why         445 loans cannot support a stable category. A WoE bin built on
            them would be noise. Worse, because the field only populates
            from 2017, its presence is a proxy for vintage - a model could
            learn it as a disguised origination-year indicator, which is
            the vintage-effect trap flagged for S10
Caveat      Excluded for THIS window only. Post-Release-47 vintages carry
            real values and a model retrained on recent data should
            revisit this

loan_age
Missing     Not missing - present in every row. Unreliable
Problem     471,248 rows (2.4%) across 11,606 loans (3.9%) repeat the
            previous row's value, so the column does not advance one per
            month for those loans
Cause       88.0% of affected loans were modified at some point (R-17).
            D-020 records that first_payment_date is overwritten on
            modification and loan_age is derived from it, so the counter
            stalls. 1,395 loans (12%) unexplained
Evidence    R-16, R-17. Gap counts built on loan_age gave 88 loans / 688
            months by arithmetic and 102 / 754 by LAG; the date-based
            figure is 106 / 643. Both loan_age methods were wrong in both
            directions
Decision    EXCLUDE the stored column. DERIVE the quantity instead
Why         Loan age is months since origination, which can be computed
            from monthly_reporting_period and the vintage using the same
            EXTRACT arithmetic as R-15. The concept is sound; the stored
            column is not
Caveat      The derived version measures calendar months since
            origination. The stored column appears to measure months since
            first payment, which modification resets. These are not the
            same quantity, and any Freddie Mac documentation or external
            benchmark quoting "loan age" may mean the stored definition
