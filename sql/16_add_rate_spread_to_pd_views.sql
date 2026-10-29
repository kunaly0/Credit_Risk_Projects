-- 16_add_rate_spread_to_pd_views.sql
-- Adds rate_spread to both PD feature views (S10, D-057, D-058).
--
-- rate_spread = original_interest_rate minus the MORTGAGE30US monthly
-- average (dim_macro.mortgage_rate) for first_payment_date minus 3 months.
-- The raw rate stays out of the views: on its own it mostly tells the
-- model which year a loan was made.
--
-- CREATE OR REPLACE keeps the 25 columns of sql/15 in the same order and
-- adds rate_spread last. Postgres only allows new view columns at the end.
-- A plain JOIN on dim_macro is on purpose: a loan with no market rate
-- would drop out of the view, and checks 5-6 of check_pd_sample.sql fail.
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
       d.original_interest_rate - m.mortgage_rate AS rate_spread
FROM pd_sample_split s
JOIN pd_target t ON t.loan_sequence_number = s.loan_sequence_number
JOIN dim_loan  d ON d.loan_sequence_number = s.loan_sequence_number
JOIN dim_macro m ON m.month = (d.first_payment_date - INTERVAL '3 months')::date
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
       d.original_interest_rate - m.mortgage_rate AS rate_spread
FROM pd_sample_split s
JOIN pd_target t ON t.loan_sequence_number = s.loan_sequence_number
JOIN dim_loan  d ON d.loan_sequence_number = s.loan_sequence_number
JOIN dim_macro m ON m.month = (d.first_payment_date - INTERVAL '3 months')::date
WHERE s.sample_set IN ('test', 'oot');
