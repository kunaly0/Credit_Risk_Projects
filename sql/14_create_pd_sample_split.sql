-- 14_create_pd_sample_split.sql
-- pd_sample_split - which sample set each in-model loan belongs to (S09,
-- D-056). One row per loan with a target in pd_target; excluded loans have
-- no row.
--
-- This file only creates the empty table. sql/model/build_pd_sample_split.sql
-- fills it, and is re-run after every rebuild of pd_target.
--
-- Sets, from D-056:
--   oot         2017, the out-of-time test. Used for no choice, scored once
--   train       60% of 2005-2012
--   validation  20% of 2005-2012
--   test        20% of 2005-2012, the in-time test
--
-- The key is dim_loan, not pd_target: build_pd_target.sql empties pd_target
-- with TRUNCATE, which a foreign key from this table would block.
DROP TABLE IF EXISTS pd_sample_split;

CREATE TABLE pd_sample_split (
    loan_sequence_number  VARCHAR(12)  PRIMARY KEY REFERENCES dim_loan(loan_sequence_number),
    sample_set            VARCHAR(10)  NOT NULL CHECK (sample_set IN ('train', 'validation', 'test', 'oot')),
    built_at              TIMESTAMPTZ  NOT NULL DEFAULT now()
);
