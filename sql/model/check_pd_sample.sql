-- check_pd_sample.sql - automatic checks on the PD sample (S09, D-056,
-- D-057). Run after build_pd_sample_split.sql and before any modelling.
-- Prints one row per check and stops with an error if any check fails.
-- Changes nothing in the database.
--
-- Usage, from the repo root:
--   psql -h localhost -U postgres -d credit_risk -f sql/model/check_pd_sample.sql

\set ON_ERROR_STOP on

CREATE TEMP TABLE IF NOT EXISTS sample_checks (
    check_no    int,
    check_name  text,
    detail      text,
    passed      boolean
);
TRUNCATE sample_checks;

-- 1-4: the split itself
INSERT INTO sample_checks
SELECT 1, 'every in-model loan has a set',
       split_loans || ' with a set, ' || in_model || ' in the model',
       split_loans = in_model
FROM (SELECT (SELECT COUNT(*) FROM pd_sample_split)                   AS split_loans,
             (SELECT COUNT(*) FROM pd_target WHERE target IS NOT NULL) AS in_model) x;

INSERT INTO sample_checks
SELECT 2, 'no left-out loan has a set', n || ' found', n = 0
FROM (SELECT COUNT(*) AS n
      FROM pd_sample_split s
      LEFT JOIN pd_target t ON t.loan_sequence_number = s.loan_sequence_number
      WHERE t.target IS NULL) x;

INSERT INTO sample_checks
SELECT 3, 'oot is 2017, and 2017 is oot', n || ' loans break it', n = 0
FROM (SELECT COUNT(*) AS n
      FROM pd_sample_split s
      JOIN pd_target t ON t.loan_sequence_number = s.loan_sequence_number
      WHERE (LEFT(t.vintage_code, 4) = '2017') <> (s.sample_set = 'oot')) x;

INSERT INTO sample_checks
SELECT 4, 'train, validation and test default rates within 0.05 points',
       'gap ' || ROUND(gap, 3) || ' points', gap <= 0.05
FROM (SELECT MAX(rate) - MIN(rate) AS gap
      FROM (SELECT 100.0 * AVG(t.target) AS rate
            FROM pd_sample_split s
            JOIN pd_target t ON t.loan_sequence_number = s.loan_sequence_number
            WHERE s.sample_set <> 'oot'
            GROUP BY s.sample_set) r) x;

-- 5-6: each view holds exactly its sets
INSERT INTO sample_checks
SELECT 5, 'pd_features_build is all of train and validation, nothing else',
       rows_in_view || ' rows, ' || expected || ' expected, ' || wrong_set || ' in a wrong set',
       rows_in_view = expected AND wrong_set = 0
FROM (SELECT COUNT(*) AS rows_in_view,
             COUNT(*) FILTER (WHERE sample_set NOT IN ('train', 'validation')) AS wrong_set
      FROM pd_features_build) v,
     (SELECT COUNT(*) AS expected
      FROM pd_sample_split WHERE sample_set IN ('train', 'validation')) e;

INSERT INTO sample_checks
SELECT 6, 'pd_features_final is all of test and oot, nothing else',
       rows_in_view || ' rows, ' || expected || ' expected, ' || wrong_set || ' in a wrong set',
       rows_in_view = expected AND wrong_set = 0
FROM (SELECT COUNT(*) AS rows_in_view,
             COUNT(*) FILTER (WHERE sample_set NOT IN ('test', 'oot')) AS wrong_set
      FROM pd_features_final) v,
     (SELECT COUNT(*) AS expected
      FROM pd_sample_split WHERE sample_set IN ('test', 'oot')) e;

-- 7-8: each view has exactly the allowed columns (D-057): key, set, target
-- and the 21 candidate features. Any extra column - a date, the vintage, an
-- outcome - fails.
INSERT INTO sample_checks
WITH allowed (column_name) AS (
    VALUES ('loan_sequence_number'), ('sample_set'), ('target'),
           ('credit_score'), ('first_time_homebuyer'), ('msa'), ('mi_percentage'),
           ('number_of_units'), ('occupancy_status'), ('original_cltv'),
           ('original_dti_ratio'), ('original_upb'), ('original_ltv'), ('channel'),
           ('prepayment_penalty_indicator'), ('amortization_type'), ('property_state'),
           ('property_type'), ('postal_code'), ('loan_purpose'), ('loan_term'),
           ('number_of_borrowers'), ('interest_only_indicator'), ('harp_indicator')
),
views (check_no, view_name) AS (
    VALUES (7, 'pd_features_build'), (8, 'pd_features_final')
),
actual AS (
    SELECT c.table_name AS view_name, c.column_name::text AS column_name
    FROM information_schema.columns c
    WHERE c.table_schema = 'public'
      AND c.table_name IN ('pd_features_build', 'pd_features_final')
),
diff AS (
    SELECT v.check_no,
           v.view_name,
           (SELECT string_agg(a.column_name, ', ' ORDER BY a.column_name)
            FROM actual a
            WHERE a.view_name = v.view_name
              AND a.column_name NOT IN (SELECT column_name FROM allowed))  AS extra,
           (SELECT string_agg(al.column_name, ', ' ORDER BY al.column_name)
            FROM allowed al
            WHERE al.column_name NOT IN (SELECT a.column_name FROM actual a
                                         WHERE a.view_name = v.view_name)) AS missing
    FROM views v
)
SELECT check_no,
       view_name || ' has only the 24 allowed columns',
       COALESCE('extra: ' || extra, 'no extra') || '; ' || COALESCE('missing: ' || missing, 'none missing'),
       extra IS NULL AND missing IS NULL
FROM diff;

-- 9: the two views never share a loan
INSERT INTO sample_checks
SELECT 9, 'no loan is in both views', n || ' found', n = 0
FROM (SELECT COUNT(*) AS n
      FROM pd_features_build b
      JOIN pd_features_final f ON f.loan_sequence_number = b.loan_sequence_number) x;

SELECT check_no, check_name, detail, passed
FROM sample_checks
ORDER BY check_no;

DO $$
DECLARE
    failed int;
BEGIN
    SELECT COUNT(*) INTO failed FROM sample_checks WHERE NOT passed;
    IF failed > 0 THEN
        RAISE EXCEPTION '% of 9 sample checks failed - see the table above', failed;
    END IF;
END $$;
