-- 18_rate_spread_by_term.sql
-- Replaces both PD feature views so rate_spread uses the market rate for
-- the loan's term (S10, D-059): 180 months or less against the 15-year
-- rate (mortgage_rate_15, sql/17), longer loans against the 30-year rate.
-- The month is first_payment_date minus 3 months (D-058), but never later
-- than the last month of the loan's origination quarter, taken from
-- vintage_code: 1,106 train and validation loans have first payment dates
-- 6 to 77 months after their quarter.
--
-- Column names, order and types are unchanged, so CREATE OR REPLACE works.
-- A plain JOIN on dim_macro is on purpose: a loan with no market row drops
-- out of the view and checks 5-6 of check_pd_sample.sql fail.
CREATE OR REPLACE VIEW pd_features_build AS
SELECT s.loan_sequence_number,
       s.sample_set,
       t.target,
       d.credit_score,
       d.first_time_homebuyer,
       d.msa,
       d.mi_percentage,
       d.number_of_units,
       d.occupancy_status,
       d.original_cltv,
       d.original_dti_ratio,
       d.original_upb,
       d.original_ltv,
       d.channel,
       d.prepayment_penalty_indicator,
       d.amortization_type,
       d.property_state,
       d.property_type,
       d.postal_code,
       d.loan_purpose,
       d.loan_term,
       d.number_of_borrowers,
       d.interest_only_indicator,
       d.harp_indicator,
       d.original_interest_rate
         - CASE WHEN d.loan_term <= 180 THEN m.mortgage_rate_15
                ELSE m.mortgage_rate END AS rate_spread
FROM pd_sample_split s
JOIN pd_target t ON t.loan_sequence_number = s.loan_sequence_number
JOIN dim_loan  d ON d.loan_sequence_number = s.loan_sequence_number
JOIN dim_macro m
  ON m.month = LEAST((d.first_payment_date - INTERVAL '3 months')::date,
                     make_date(LEFT(d.vintage_code, 4)::int,
                               RIGHT(d.vintage_code, 1)::int * 3, 1))
WHERE s.sample_set IN ('train', 'validation');

CREATE OR REPLACE VIEW pd_features_final AS
SELECT s.loan_sequence_number,
       s.sample_set,
       t.target,
       d.credit_score,
       d.first_time_homebuyer,
       d.msa,
       d.mi_percentage,
       d.number_of_units,
       d.occupancy_status,
       d.original_cltv,
       d.original_dti_ratio,
       d.original_upb,
       d.original_ltv,
       d.channel,
       d.prepayment_penalty_indicator,
       d.amortization_type,
       d.property_state,
       d.property_type,
       d.postal_code,
       d.loan_purpose,
       d.loan_term,
       d.number_of_borrowers,
       d.interest_only_indicator,
       d.harp_indicator,
       d.original_interest_rate
         - CASE WHEN d.loan_term <= 180 THEN m.mortgage_rate_15
                ELSE m.mortgage_rate END AS rate_spread
FROM pd_sample_split s
JOIN pd_target t ON t.loan_sequence_number = s.loan_sequence_number
JOIN dim_loan  d ON d.loan_sequence_number = s.loan_sequence_number
JOIN dim_macro m
  ON m.month = LEAST((d.first_payment_date - INTERVAL '3 months')::date,
                     make_date(LEFT(d.vintage_code, 4)::int,
                               RIGHT(d.vintage_code, 1)::int * 3, 1))
WHERE s.sample_set IN ('test', 'oot');
