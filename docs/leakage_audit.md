# Leakage audit - Project 1 sample

Checked 13-19 Oct 2026 (S09), before any feature work. The rules are
D-055, D-056 and D-057 in the decision log.

## Sample

| Set | Vintages | Loans | Defaults | Rate | Read from |
|---|---|---|---|---|---|
| train | 2005-2012, 60% | 141,623 | 3,593 | 2.54% | pd_features_build |
| validation | 2005-2012, 20% | 47,209 | 1,198 | 2.54% | pd_features_build |
| test | 2005-2012, 20% | 47,212 | 1,200 | 2.54% | pd_features_final |
| oot | 2017 | 48,231 | 398 | 0.83% | pd_features_final |

Each vintage and target is split 60/20/20 separately, in the order of md5()
of the loan number, so every set has the same mix of years and defaults and
a loan always lands in the same set (sql/model/build_pd_sample_split.sql).

## Columns

All 32 dim_loan columns were checked against the Freddie Mac User Guide.

| Verdict | Columns |
|---|---|
| Candidate feature (21) | credit_score, first_time_homebuyer, msa, mi_percentage, number_of_units, occupancy_status, original_cltv, original_dti_ratio, original_upb, original_ltv, channel, prepayment_penalty_indicator, amortization_type, property_state, property_type, postal_code, loan_purpose, loan_term, number_of_borrowers, interest_only_indicator, harp_indicator |
| Only as a spread over the market rate, built in S10 | original_interest_rate |
| ID or date | loan_sequence_number (contains the year and quarter), vintage_code, first_payment_date, maturity_date, pre_harp_loan_sequence_number |
| Marks the year | property_valuation_method, vantagescore (D-036), special_eligibility_program, seller_name, super_conforming_flag |

credit_score is the score known when Freddie Mac bought the loan, and LTV
uses a new appraisal for a loan bought seasoned. Loans bought seasoned are
excluded (D-053), so for every loan in the sample both are origination
values. Servicer name is reported as of the last month of data; it sits in
the performance table and is not a feature.

## Process

| Check | Finding | Treatment |
|---|---|---|
| Outcome columns | pd_target holds default_month, default_trigger, exit_code, exit_month and target | Only target reaches the views, as the label |
| One borrower in two sets | 314 HARP loans whose earlier loan is also in the sample. 187 sit in a different set from it: 162 within 2005-2012, 25 between 2017 and 2005-2008 | Kept. The earlier loan's 24-month window ends before the refinance, its features are measured again at refinance, and the pairs are 0.07% of the sample |
| Exclusions decided on later events | 287 loans with zero balance code 96 (defect found before any other exit) inside the window, excluded as outcome unknown (D-052) | Kept out. No vintage's rate moves by more than 0.1 points (S08). In use, such loans are scored like any other |
| Late and early starts | 15,425 and 12 loans | Known when Freddie Mac buys the loan, not later (D-053) |
| Macro data | Not used as features (D-055) | The market rate is used only to measure each loan's rate against it |

## What each set may be used for

| Set | Use |
|---|---|
| train | Everything the model learns: bins, fills for missing values (D-036), feature selection, weights |
| validation | Comparing and choosing between options; calibration fit (decided in S13) |
| test, oot | Scored once, after the model is final |

## Controls

- The model reads only pd_features_build and pd_features_final (sql/15).
  Each holds the key, the set, the target and the 21 candidate features.
- sql/model/check_pd_sample.sql runs 9 checks - set coverage, oot is
  exactly 2017, equal default rates, the rows and the columns of each view -
  and stops on any failure. 9 of 9 passed on 19 Oct 2026.

## Limits

- There is no borrower ID. Only HARP refinances link two loans of one
  borrower, so other repeat borrowers cannot be found.
- oot is 2017, a low-default year. Ranking in a downturn is tested in-time
  only (D-056).
- Within training, harp_indicator is Y only in 2012 (D-057). S10 checks it
  within 2012.
