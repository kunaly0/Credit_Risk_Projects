DROP TABLE IF EXISTS fact_loan_performance;

-- fact_loan_performance — one row per loan per month.
-- Source: perf_YYYYQn.txt (Release 47, 35 fields).
--
-- vintage_code is assigned by the loader from the source filename (D-020);
--   it is not present in the performance file.
--
-- SIGN CONVENTION (Release 47): recoveries and gains are negative,
--   expenses and losses are positive. Constraints below encode this.
--
-- Sentinel / special values converted to NULL at load:
--   net_sales_proceeds       'U'  -> NULL  (unknown sale price)
--   estimated_loan_to_value   999 -> NULL
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
        mi_recoveries                                NUMERIC(12,2)     CHECK(mi_recoveries <= 0),
        net_sales_proceeds                           NUMERIC(12,2)     CHECK(net_sales_proceeds <= 0),
        non_mi_recoveries                            NUMERIC(12,2)     CHECK(non_mi_recoveries <= 0),
        total_expenses                               NUMERIC(12,2)     CHECK(total_expenses >= 0),
        legal_costs                                  NUMERIC(12,2)     CHECK(legal_costs >= 0),
        maintenance_costs                            NUMERIC(12,2)     CHECK(maintenance_costs >= 0),
        taxes_and_insurance                          NUMERIC(12,2)     CHECK(taxes_and_insurance >= 0),
        miscellaneous_expenses                       NUMERIC(12,2)     CHECK(miscellaneous_expenses >= 0),
        actual_loss                                  NUMERIC(12,2),
        cumulative_modification_costs                NUMERIC(12,2)     CHECK(cumulative_modification_costs >= 0),
        interest_rate_step_indicator                 CHAR(1)           CHECK(interest_rate_step_indicator IN ('Y','N')),
        payment_deferral_flag                        CHAR(1)           CHECK(payment_deferral_flag IN ('C','P')),
        estimated_loan_to_value                      SMALLINT          CHECK(estimated_loan_to_value BETWEEN 1 AND 998),
        zero_balance_removal_upb                     NUMERIC(12,2)     CHECK(zero_balance_removal_upb >= 0),
        delinquent_accrued_interest                  NUMERIC(12,2)     CHECK(delinquent_accrued_interest <= 0),
        delinquency_due_to_disaster                  CHAR(1)           CHECK(delinquency_due_to_disaster IN ('Y')),
        borrower_assistance_plan                     CHAR(1)           CHECK(borrower_assistance_plan IN ('F','R','T')),
        current_period_modification_costs            NUMERIC(12,2)     CHECK(current_period_modification_costs >= 0),
        current_interest_bearing_upb                 NUMERIC(12,2)     CHECK(current_interest_bearing_upb >= 0),
        mortgage_insurance_cancellation_indicator    CHAR(1)           CHECK(mortgage_insurance_cancellation_indicator IN ('Y','N','7')),
        servicer_name                                VARCHAR(60),
        bankruptcy_cramdown_costs                    NUMERIC(12,2)     CHECK(bankruptcy_cramdown_costs >= 0),
        PRIMARY KEY (vintage_code, loan_sequence_number, monthly_reporting_period),
        CHECK (
        vintage_code = CASE
        WHEN SUBSTRING(loan_sequence_number FROM 2 FOR 2) >= '99'
        THEN '19' || SUBSTRING(loan_sequence_number FROM 2 FOR 4)
        ELSE '20' || SUBSTRING(loan_sequence_number FROM 2 FOR 4)
    END
)
) PARTITION BY LIST (vintage_code);
