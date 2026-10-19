-- 15_create_pd_feature_views.sql
-- The only two places the PD model may read its data from (S09, D-056,
-- D-057).
--
--   pd_features_build  train and validation. Used to build and choose:
--                      binning, feature selection, fitting, calibration.
--   pd_features_final  test and oot (2017). Sealed: scored once, after the
--                      model is final (S12 onwards).
--
-- Each view holds a key (loan_sequence_number, never a feature - it
-- contains the origination year and quarter), the set, the target, and the
-- 21 candidate features of D-057. Nothing else: no dates, no vintage, no
-- outcome columns other than target. sql/model/check_pd_sample.sql fails if
-- a column is added or removed.
--
-- original_interest_rate is left out on purpose. D-057 allows it only as a
-- spread over the market rate of its month, which S10 adds here in a new
-- numbered file (D-048).
CREATE VIEW pd_features_build AS
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
       d.harp_indicator
FROM pd_sample_split s
JOIN pd_target t ON t.loan_sequence_number = s.loan_sequence_number
JOIN dim_loan  d ON d.loan_sequence_number = s.loan_sequence_number
WHERE s.sample_set IN ('train', 'validation');

CREATE VIEW pd_features_final AS
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
       d.harp_indicator
FROM pd_sample_split s
JOIN pd_target t ON t.loan_sequence_number = s.loan_sequence_number
JOIN dim_loan  d ON d.loan_sequence_number = s.loan_sequence_number
WHERE s.sample_set IN ('test', 'oot');
