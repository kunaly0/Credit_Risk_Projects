-- 11_drop_tablespace_credit_risk_ts.sql
-- D-047 follow-up: credit_risk_ts (D:) is empty after sql/10, and no build
-- script creates or uses it. DROP fails if anything is still in it, in any
-- database, so a successful run proves it was empty.
-- Cannot run inside a transaction block.

DROP TABLESPACE credit_risk_ts;

SELECT spcname FROM pg_tablespace ORDER BY spcname;
