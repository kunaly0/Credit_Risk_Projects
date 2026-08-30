-- Indexes beyond those created automatically by PRIMARY KEY constraints.
--
-- Run order: 01 -> 02 -> 03 -> 04.
--
-- idx_dim_loan_vintage: PostgreSQL does not index foreign key columns
--   automatically. Without this, filtering 8.7M loans by vintage is a full
--   table scan. Small index, used in nearly every analysis.
--
-- idx_fact_perf_period: mitigates the accepted cost of partitioning by
--   vintage — cross-sectional queries by calendar month otherwise scan all
--   24 partitions. Declared here for the record, but S03 should create it
--   AFTER the bulk load, not before: maintaining an index across a
--   601M-row COPY is far slower than building it once on a populated table.

CREATE INDEX idx_dim_loan_vintage ON dim_loan(vintage_code);

CREATE INDEX idx_fact_perf_period ON fact_loan_performance(monthly_reporting_period);
