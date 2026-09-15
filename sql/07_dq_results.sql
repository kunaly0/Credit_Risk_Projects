-- dq_results - one row per metric, per rule, per suite run.
--
-- LONG FORMAT, like load_audit_field. The measurement is NAMED in
-- metric_name and HELD in metric_value, rather than each measurement
-- having its own column. Rules produce different shapes: R-01 is one
-- number for the whole portfolio, R-03 is one per field per vintage,
-- R-12 is six numbers at once. All three fit without an ALTER TABLE,
-- and a new rule adds rows, not columns.
--
-- scope_type says what level a number describes; scope_value holds the
-- vintage or field name when there is one. Portfolio-scope rules leave
-- scope_value NULL - it is not applicable, not missing.
--
-- STATUS IS WRITTEN BEFORE THE RULE RUNS. The suite inserts a row with
-- status 'running', commits it on a SEPARATE connection, then updates it
-- to pass/warn/fail when the rule completes. This is deliberate: in S03
-- the load_audit INSERT sat inside the same transaction as the COPY, so
-- six failed loads rolled their own audit rows back and left no trace
-- (defect #1 - run_ids 2, 3, 7 and 13 exist only as gaps in the
-- sequence). A 'running' row still present after the suite finishes is
-- the evidence that a rule crashed. An audit that records only successes
-- is not an audit.
--
-- metric_value is nullable because a 'running' row has no value yet.
-- A placeholder would be a fake number in a column meant for real ones.
CREATE TABLE dq_results (
    dq_result_id	 BIGSERIAL	    PRIMARY KEY,
    run_id	         BIGINT	        NOT NULL,
    rule_id	         VARCHAR(10)	NOT NULL,
    scope_type	     VARCHAR(20)	NOT NULL CHECK(scope_type IN ('portfolio','vintage','field','field_vintage')),
    scope_value	     VARCHAR(60),
    metric_name	     VARCHAR(60)	NOT NULL,
    metric_value	 NUMERIC(12,2),
    status	         VARCHAR(20)	NOT NULL CHECK(status IN ('pass', 'warn', 'fail', 'running')),
    checked_at	     TIMESTAMPTZ	NOT NULL,
    UNIQUE NULLS NOT DISTINCT (run_id, rule_id, scope_type, scope_value, metric_name)
);
