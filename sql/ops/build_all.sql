-- build_all.sql - build the schema from nothing by running every numbered
-- file in sql/ in order (D-048). For a new, empty database only: sql/01
-- starts by dropping tables. Refuses to run against credit_risk.
--
-- Usage, from the repo root:
--   psql -h localhost -U postgres -d <new database> -f sql/ops/build_all.sql
-- Then load data with src/etl/loader.py and src/macro/load_fred.py.

\set ON_ERROR_STOP on

SELECT current_database() = 'credit_risk' AS is_live \gset
\if :is_live
    DO $$ BEGIN RAISE EXCEPTION 'build_all.sql must not run against credit_risk'; END $$;
\endif

\ir ../01_create_dimensions.sql
\ir ../02_create_facts.sql
\ir ../03_create_partitions.sql
\ir ../04_create_indexes.sql
\ir ../05_seed_dim_vintage.sql
\ir ../06_load_audit.sql
\ir ../07_dq_results.sql
\ir ../08_create_dim_macro_state.sql
\ir ../09_fix_dim_macro_checks.sql
\ir ../10_move_fact_to_pg_default.sql
\ir ../11_drop_tablespace_credit_risk_ts.sql
\ir ../12_create_dashboard_views.sql

-- Compare with the live database: 8 tables, 24 partitions, 24 vintages
SELECT
    (SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public'
       AND tablename NOT LIKE 'fact_loan_performance_%') AS tables,
    (SELECT COUNT(*) FROM pg_inherits
       WHERE inhparent = 'fact_loan_performance'::regclass) AS partitions,
    (SELECT COUNT(*) FROM dim_vintage) AS vintages;
