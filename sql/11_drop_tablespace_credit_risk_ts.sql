-- 11_drop_tablespace_credit_risk_ts.sql
-- D-047 follow-up: credit_risk_ts (D:) is empty after sql/10, and no build
-- script creates or uses it. DROP fails if anything is still in it, in any
-- database, so a successful run proves it was empty.
-- Cannot run inside a transaction block.
-- IF EXISTS (D-048): on a fresh build the tablespace never existed.
DROP TABLESPACE IF EXISTS credit_risk_ts;

SELECT spcname FROM pg_tablespace ORDER BY spcname;
