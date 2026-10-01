-- table_row_counts.sql - exact row counts for the eight tables.
-- Run on the live database and on a restored copy; the two must match.
SELECT 'dim_loan' AS table_name, COUNT(*) AS row_count FROM dim_loan
UNION ALL SELECT 'dim_macro', COUNT(*) FROM dim_macro
UNION ALL SELECT 'dim_macro_state', COUNT(*) FROM dim_macro_state
UNION ALL SELECT 'dim_vintage', COUNT(*) FROM dim_vintage
UNION ALL SELECT 'dq_results', COUNT(*) FROM dq_results
UNION ALL SELECT 'fact_loan_performance', COUNT(*) FROM fact_loan_performance
UNION ALL SELECT 'load_audit', COUNT(*) FROM load_audit
UNION ALL SELECT 'load_audit_field', COUNT(*) FROM load_audit_field
ORDER BY table_name;
