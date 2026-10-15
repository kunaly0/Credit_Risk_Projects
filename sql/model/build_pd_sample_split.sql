-- build_pd_sample_split.sql - give every in-model loan its sample set (S09,
-- D-056). Re-runnable: empties the table and rebuilds it in one
-- transaction, so a failure leaves the previous version in place. Run after
-- every rebuild of pd_target.
--
-- Usage, from the repo root:
--   psql -h localhost -U postgres -d credit_risk -f sql/model/build_pd_sample_split.sql
--
-- How a loan's set is chosen:
--   1. Loans are grouped into piles by vintage year and target, so every
--      set gets the same share of each year and of the defaults.
--   2. Inside each pile the loans are put in the order of md5() of their
--      loan number. That order looks random but is the same on every run,
--      so the same loan always lands in the same set.
--   3. The first 60% of each pile is train, the next 20% validation, the
--      last 20% test. 2017 is oot whatever its position.
-- If pd_target changes (a new target rule, a reload), the piles change and
-- some loans move set. Re-run this file, and re-run everything built on it.

\set ON_ERROR_STOP on

BEGIN;

TRUNCATE pd_sample_split;

INSERT INTO pd_sample_split (loan_sequence_number, sample_set)
WITH in_model AS (
    -- Step 1: only loans with a target. Excluded loans get no set.
    SELECT loan_sequence_number,
           LEFT(vintage_code, 4) AS vintage_year,
           target
    FROM pd_target
    WHERE target IS NOT NULL
),
shuffled AS (
    -- Step 2: each loan's place in its pile (pos) and the pile's size (n).
    SELECT loan_sequence_number,
           vintage_year,
           ROW_NUMBER() OVER (PARTITION BY vintage_year, target
                              ORDER BY md5(loan_sequence_number),
                                       loan_sequence_number)      AS pos,
           COUNT(*)     OVER (PARTITION BY vintage_year, target)  AS n
    FROM in_model
)
-- Step 3: deal the piles out 60 / 20 / 20.
SELECT loan_sequence_number,
       CASE WHEN vintage_year = '2017' THEN 'oot'
            WHEN pos <= 0.6 * n        THEN 'train'
            WHEN pos <= 0.8 * n        THEN 'validation'
            ELSE                            'test'
       END AS sample_set
FROM shuffled;

-- Stop before COMMIT if the split does not cover exactly the in-model loans.
DO $$
DECLARE
    in_model_loans  bigint;
    split_loans     bigint;
    not_in_model    bigint;
BEGIN
    SELECT COUNT(*) INTO in_model_loans FROM pd_target WHERE target IS NOT NULL;
    SELECT COUNT(*) INTO split_loans    FROM pd_sample_split;
    SELECT COUNT(*) INTO not_in_model
    FROM pd_sample_split s
    LEFT JOIN pd_target t ON t.loan_sequence_number = s.loan_sequence_number
    WHERE t.target IS NULL;

    IF split_loans <> in_model_loans OR not_in_model > 0 THEN
        RAISE EXCEPTION 'split has % loans, pd_target has % in-model loans, % split loans are not in the model',
            split_loans, in_model_loans, not_in_model;
    END IF;
END $$;

COMMIT;

ANALYZE pd_sample_split;

-- Check: loans, defaults and default rate per set and vintage year.
SELECT s.sample_set,
       LEFT(t.vintage_code, 4)                      AS vintage_year,
       COUNT(*)                                     AS loans,
       SUM(t.target)                                AS bads,
       ROUND(100.0 * SUM(t.target) / COUNT(*), 2)   AS bad_rate_pct
FROM pd_sample_split s
JOIN pd_target t ON t.loan_sequence_number = s.loan_sequence_number
GROUP BY s.sample_set, LEFT(t.vintage_code, 4)
ORDER BY CASE s.sample_set WHEN 'train' THEN 1 WHEN 'validation' THEN 2
                           WHEN 'test' THEN 3 ELSE 4 END,
         vintage_year;

-- Check: the same per set. train, validation and test should show the same
-- default rate.
SELECT s.sample_set,
       COUNT(*)                                     AS loans,
       SUM(t.target)                                AS bads,
       ROUND(100.0 * SUM(t.target) / COUNT(*), 2)   AS bad_rate_pct
FROM pd_sample_split s
JOIN pd_target t ON t.loan_sequence_number = s.loan_sequence_number
GROUP BY s.sample_set
ORDER BY CASE s.sample_set WHEN 'train' THEN 1 WHEN 'validation' THEN 2
                           WHEN 'test' THEN 3 ELSE 4 END;
