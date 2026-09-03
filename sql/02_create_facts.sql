DROP TABLE IF EXISTS fact_loan_performance;

-- fact_loan_performance — one row per loan per month.
-- Source: Freddie Mac Monthly Performance Data File, Release 47, 35 fields.
--   Standard: perf_YYYYQn.txt, one file per quarter.
--   Sample:   sample_perf_YYYY.txt, one file per YEAR.
--
-- vintage_code is assigned by the loader; it is not present in the file.
--   Standard files: derived from the filename (one file per quarter, D-020).
--   Sample files:   derived from loan_sequence_number characters 2-5, because
--                   the filename gives the year only and carries no quarter.
--   The table-level CHECK at the foot of this file validates either path.
--
-- DATES are stored in the source as YYYYMM. The loader parses them in Python
--   to the first of the month before COPY; PostgreSQL never receives the raw
--   string (D-026). With DateStyle = ISO, DMY a bare six-digit value parses as
--   YY|MM|DD, so '200501' becomes 2020-05-01 — wrong by fifteen years, yet
--   day = 1, so the CHECK constraints below would accept it. Those CHECKs are
--   a backstop against malformed input, not the parsing mechanism.
--   Affects: monthly_reporting_period, defect_settlement_date,
--            zero_balance_effective_date, ddlpi.
--
-- SIGN CONVENTION (Release 47): recoveries and gains are normally disclosed
--   as negative, expenses and losses as positive. This describes the usual
--   direction of a flow, not an invariant, and is NOT enforced here (D-027).
--   Profiling sample_perf_2005.txt (3,877,176 rows) found 8 of 15 money
--   fields carrying values against convention — reversals, clawbacks and
--   escrow refunds are legitimate servicing activity.
--     Balance fields keep CHECK (>= 0): a balance cannot be negative.
--       current_actual_upb, current_non_interest_bearing_upb,
--       current_interest_bearing_upb, zero_balance_removal_upb
--     Flow fields carry no sign constraint, whether or not this sample
--       happened to violate the convention. The rule is structural, not
--       fitted to one year of one sample.
--   Sign distributions are monitored in the load audit as a data quality
--   metric instead of being enforced as a constraint.
--
-- Sentinel / special values converted to NULL at load:
--   estimated_loan_to_value   999 -> NULL  (confirmed present in data)
--   net_sales_proceeds        'U' -> NULL  (documented; NOT observed in
--                                           sample_perf_2005.txt, 0 of
--                                           3,877,176 rows — conversion
--                                           retained, other vintages unchecked)
--
-- The foreign key to dim_loan is validated per row on insert. S03 may need
--   to drop and re-add it around the bulk load for throughput.
--
-- Vintage/ID consistency CHECK assumes 20xx vintages.
CREATE TABLE fact_loan_performance(
        vintage_code                                 VARCHAR(6)        NOT NULL REFERENCES dim_vintage(vintage_code),
        loan_sequence_number                         VARCHAR(12)       NOT NULL REFERENCES dim_loan(loan_sequence_number),
        monthly_reporting_period                     DATE              NOT NULL CHECK(EXTRACT(DAY FROM monthly_reporting_period) = 1),
        current_actual_upb                           NUMERIC(12,2)     CHECK(current_actual_upb >= 0),
        loan_delinquency_status                      CHAR(2)           CHECK (loan_delinquency_status ~ '^([0-9]{2}|XX|RA)$'),
        loan_age                                     SMALLINT          CHECK(loan_age >= -12),
        months_to_maturity                           SMALLINT          CHECK(months_to_maturity >= 0),
        defect_settlement_date                       DATE              CHECK(EXTRACT(DAY FROM defect_settlement_date) = 1),
        modification_flag                            CHAR(1)           CHECK(modification_flag IN ('Y','P')),
        zero_balance_code                            CHAR(2)           CHECK(zero_balance_code IN ('01','02','03','09','15','16','96')),
        zero_balance_effective_date                  DATE              CHECK(EXTRACT(DAY FROM zero_balance_effective_date) = 1),
        current_interest_rate                        NUMERIC(5,3)      CHECK(current_interest_rate BETWEEN 0 AND 30),
        current_non_interest_bearing_upb             NUMERIC(12,2)     CHECK(current_non_interest_bearing_upb >= 0),
        ddlpi                                        DATE              CHECK(EXTRACT(DAY FROM ddlpi) = 1),
        mi_recoveries                                NUMERIC(12,2),
        net_sales_proceeds                           NUMERIC(12,2),
        non_mi_recoveries                            NUMERIC(12,2),
        total_expenses                               NUMERIC(12,2),
        legal_costs                                  NUMERIC(12,2),
        maintenance_costs                            NUMERIC(12,2),
        taxes_and_insurance                          NUMERIC(12,2),
        miscellaneous_expenses                       NUMERIC(12,2),
        actual_loss                                  NUMERIC(12,2),
        cumulative_modification_costs                NUMERIC(12,2),
        interest_rate_step_indicator                 CHAR(1)           CHECK(interest_rate_step_indicator IN ('Y','N')),
        payment_deferral_flag                        CHAR(1)           CHECK(payment_deferral_flag IN ('C','P')),
        estimated_loan_to_value                      SMALLINT          CHECK(estimated_loan_to_value BETWEEN 1 AND 998),
        zero_balance_removal_upb                     NUMERIC(12,2)     CHECK(zero_balance_removal_upb >= 0),
        -- Flow field, no sign constraint (D-027). First field where the
        -- convention was found to break: -947.03 to +264,875.74.
        delinquent_accrued_interest                  NUMERIC(12,2),
        delinquency_due_to_disaster                  CHAR(1)           CHECK(delinquency_due_to_disaster IN ('Y')),
        borrower_assistance_plan                     CHAR(1)           CHECK(borrower_assistance_plan IN ('F','R','T')),
        current_period_modification_costs            NUMERIC(12,2),
        current_interest_bearing_upb                 NUMERIC(12,2)     CHECK(current_interest_bearing_upb >= 0),
        mortgage_insurance_cancellation_indicator    CHAR(1)           CHECK(mortgage_insurance_cancellation_indicator IN ('Y','N','7')),
        servicer_name                                VARCHAR(60),
        bankruptcy_cramdown_costs                    NUMERIC(12,2),
        PRIMARY KEY (vintage_code, loan_sequence_number, monthly_reporting_period),
        CHECK (
        vintage_code = CASE
           WHEN SUBSTRING(loan_sequence_number FROM 2 FOR 2) >= '99'
           THEN '19' || SUBSTRING(loan_sequence_number FROM 2 FOR 4)
           ELSE '20' || SUBSTRING(loan_sequence_number FROM 2 FOR 4)
        END
)
) PARTITION BY LIST (vintage_code);
