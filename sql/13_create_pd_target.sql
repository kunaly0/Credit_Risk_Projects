-- 13_create_pd_target.sql
-- pd_target - the Project 1 PD target (S08). One row per loan in dim_loan,
-- included or not, so every exclusion can be counted and explained.
--
-- This file only creates the empty table. sql/model/build_pd_target.sql
-- fills it and is re-run after every loan reload. On a fresh build the
-- table is created empty, because the loan data is loaded after the schema.
--
-- Rules, from DECISIONS.md:
--   D-050  default = first month with status 03-99 (90+ days past due),
--          status RA, zero balance code 02/03/09/15, or a modification
--   D-051  target = 1 if that month falls before first_payment_date + 24
--          months
--   D-052  paid off inside the window = 0; bought back (96) inside the
--          window without a default = excluded
--   D-053  data must start one month before or in the first payment month
--   D-054  COVID needs no adjustment under the 24-month window
--
-- first_payment_date is the window start. sql/01 warns it can be
-- overwritten on modification. User Guide footnote 3 limits that to loans
-- modified before Freddie Mac bought them, and S08 found only 12 loans
-- whose data starts 2+ months before it, against 10,241 modified loans.
-- D-053 excludes those 12 (early_start).
--
-- target is NULL for an excluded loan, and exclusion_reason says why. The
-- two table CHECKs keep them consistent.
--
-- OUTCOME COLUMNS. default_month, default_trigger, exit_code, exit_month
-- and target record what happened after the loan was made. They exist to
-- audit the label. None of them may ever be used as a model feature.
DROP TABLE IF EXISTS pd_target;

CREATE TABLE pd_target (
    loan_sequence_number  VARCHAR(12)  PRIMARY KEY REFERENCES dim_loan(loan_sequence_number),
    vintage_code          VARCHAR(6)   NOT NULL REFERENCES dim_vintage(vintage_code),
    first_payment_date    DATE         NOT NULL,
    window_end            DATE         NOT NULL,
    data_start            DATE,
    data_start_offset     SMALLINT,
    default_month         DATE,
    default_trigger       VARCHAR(12)  CHECK (default_trigger IN ('dpd90', 'reo', 'loss_exit', 'modification')),
    exit_code             CHAR(2),
    exit_month            DATE,
    exclusion_reason      VARCHAR(20)  CHECK (exclusion_reason IN ('no_performance', 'early_start', 'late_start',
                                                                   'buyback_in_window', 'rpl_sale_in_window')),
    target                SMALLINT     CHECK (target IN (0, 1)),
    built_at              TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CHECK ((exclusion_reason IS NULL) = (target IS NOT NULL)),
    CHECK ((default_month IS NULL) = (default_trigger IS NULL))
);
