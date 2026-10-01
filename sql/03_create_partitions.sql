-- 24 partitions of fact_loan_performance, one per source file (D-002 vintages).
-- Generated, not hand-written: 24 near-identical statements are an error surface.
--
-- Run order: 01 -> 02 -> 03. This file assumes the parent was just created by 02.
-- No DROP statements needed here: dropping the parent drops its partitions.
--
-- Partitions use the database default tablespace (pg_default, C:). They were
-- on credit_risk_ts (D:) until D-047 moved them after repeated read failures
-- on D: (sql/10). D-022, which put them there, is superseded.
--
-- ENCODING: this file must be saved as UTF-8 without BOM. A BOM here silently
-- consumed the 2005Q1 partition on first run (see D-021).
CREATE TABLE fact_loan_performance_2005q1 PARTITION OF fact_loan_performance FOR VALUES IN ('2005Q1');
CREATE TABLE fact_loan_performance_2005q2 PARTITION OF fact_loan_performance FOR VALUES IN ('2005Q2');
CREATE TABLE fact_loan_performance_2005q3 PARTITION OF fact_loan_performance FOR VALUES IN ('2005Q3');
CREATE TABLE fact_loan_performance_2005q4 PARTITION OF fact_loan_performance FOR VALUES IN ('2005Q4');
CREATE TABLE fact_loan_performance_2006q1 PARTITION OF fact_loan_performance FOR VALUES IN ('2006Q1');
CREATE TABLE fact_loan_performance_2006q2 PARTITION OF fact_loan_performance FOR VALUES IN ('2006Q2');
CREATE TABLE fact_loan_performance_2006q3 PARTITION OF fact_loan_performance FOR VALUES IN ('2006Q3');
CREATE TABLE fact_loan_performance_2006q4 PARTITION OF fact_loan_performance FOR VALUES IN ('2006Q4');
CREATE TABLE fact_loan_performance_2007q1 PARTITION OF fact_loan_performance FOR VALUES IN ('2007Q1');
CREATE TABLE fact_loan_performance_2007q2 PARTITION OF fact_loan_performance FOR VALUES IN ('2007Q2');
CREATE TABLE fact_loan_performance_2007q3 PARTITION OF fact_loan_performance FOR VALUES IN ('2007Q3');
CREATE TABLE fact_loan_performance_2007q4 PARTITION OF fact_loan_performance FOR VALUES IN ('2007Q4');
CREATE TABLE fact_loan_performance_2008q1 PARTITION OF fact_loan_performance FOR VALUES IN ('2008Q1');
CREATE TABLE fact_loan_performance_2008q2 PARTITION OF fact_loan_performance FOR VALUES IN ('2008Q2');
CREATE TABLE fact_loan_performance_2008q3 PARTITION OF fact_loan_performance FOR VALUES IN ('2008Q3');
CREATE TABLE fact_loan_performance_2008q4 PARTITION OF fact_loan_performance FOR VALUES IN ('2008Q4');
CREATE TABLE fact_loan_performance_2012q1 PARTITION OF fact_loan_performance FOR VALUES IN ('2012Q1');
CREATE TABLE fact_loan_performance_2012q2 PARTITION OF fact_loan_performance FOR VALUES IN ('2012Q2');
CREATE TABLE fact_loan_performance_2012q3 PARTITION OF fact_loan_performance FOR VALUES IN ('2012Q3');
CREATE TABLE fact_loan_performance_2012q4 PARTITION OF fact_loan_performance FOR VALUES IN ('2012Q4');
CREATE TABLE fact_loan_performance_2017q1 PARTITION OF fact_loan_performance FOR VALUES IN ('2017Q1');
CREATE TABLE fact_loan_performance_2017q2 PARTITION OF fact_loan_performance FOR VALUES IN ('2017Q2');
CREATE TABLE fact_loan_performance_2017q3 PARTITION OF fact_loan_performance FOR VALUES IN ('2017Q3');
CREATE TABLE fact_loan_performance_2017q4 PARTITION OF fact_loan_performance FOR VALUES IN ('2017Q4');
