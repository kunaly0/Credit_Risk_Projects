-- 10_move_fact_to_pg_default.sql
-- D-047: move fact_loan_performance partitions from credit_risk_ts (D:) to pg_default (C:).
-- Indexes are already on pg_default and are not touched.
-- One transaction: if any partition fails to move, none move.

\set ON_ERROR_STOP on

SELECT COUNT(*) AS rows_before FROM fact_loan_performance;

BEGIN;

SELECT format('ALTER TABLE %s SET TABLESPACE pg_default;', inhrelid::regclass)
FROM pg_inherits
WHERE inhparent = 'fact_loan_performance'::regclass
ORDER BY 1
\gexec

COMMIT;

SELECT COUNT(*) AS rows_after FROM fact_loan_performance;

-- grain: one row per tablespace holding fact partitions
SELECT COALESCE(t.spcname, '(database default)') AS tablespace,
       COUNT(*) AS partitions
FROM pg_inherits i
JOIN pg_class c ON c.oid = i.inhrelid
LEFT JOIN pg_tablespace t ON t.oid = c.reltablespace
WHERE i.inhparent = 'fact_loan_performance'::regclass
GROUP BY 1;
