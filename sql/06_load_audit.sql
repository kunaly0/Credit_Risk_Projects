-- load_audit, load_audit_field - the ETL audit trail.
--
-- load_audit is a logbook: one row per load run, recording the source
-- file, target table, timings, row counts and outcome.
-- load_audit_field holds the notes attached to a run: one row per field
-- per metric, in LONG FORMAT (metric named in metric_type, number in
-- metric_value) so a new metric adds rows, not columns.
--
-- KNOWN DEFECT #1: the audit INSERT sits inside the same transaction as
-- the COPY, so a failed load rolls its own audit row back. Six S03 loads
-- failed and left no trace - run_ids 2, 3, 7 and 13 exist only as gaps in
-- the sequence. status allows 'failed' and finished_at is nullable, so
-- the DESIGN is correct; the transaction boundary defeats it. Fixing it
-- means committing the audit row on a separate connection, as
-- sql/07_dq_results.sql does.
--
-- KNOWN DEFECT #12: TRUNCATE is not logged. The 2017 performance file was
-- loaded four times with a TRUNCATE between each, so the audit sums four
-- loads while the table holds one. This is why R-01 fails. The fix is to
-- log a removal event, not to delete the extra rows - supersede, never
-- delete.
--
-- load_audit_field only writes a row when a count exceeds zero, so "no
-- row" is ambiguous: zero, or never checked. against_convention is in the
-- CHECK but appears in no row, and the audit cannot say which case that
-- is. dq_results records passes and zeros for this reason.
CREATE TABLE load_audit(
    run_id          BIGSERIAL      PRIMARY KEY,
    source_file     VARCHAR(200)   NOT NULL,
    target_table    VARCHAR(60)    NOT NULL,
    started_at      TIMESTAMPTZ    NOT NULL,
    finished_at     TIMESTAMPTZ,
    rows_read       INTEGER,
    rows_loaded     INTEGER,
    status          VARCHAR(20)    NOT NULL CHECK(status IN ('running','success','failed'))
);

CREATE TABLE load_audit_field(
    run_id          BIGINT         NOT NULL REFERENCES load_audit(run_id),
    field_name      VARCHAR(60)    NOT NULL,
    metric_type     VARCHAR(30)    NOT NULL CHECK(metric_type IN ('sentinel_null','against_convention','out_of_range','out_of_scope')),
    metric_value    INTEGER        NOT NULL,
    PRIMARY KEY (run_id, field_name, metric_type)
);
