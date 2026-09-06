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
    metric_type     VARCHAR(30)    NOT NULL CHECK(metric_type IN ('sentinel_null','against_convention')),
    metric_value    INTEGER        NOT NULL,
    PRIMARY KEY (run_id, field_name, metric_type)
);
