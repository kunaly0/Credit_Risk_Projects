-- dim_vintage — one row per origination quarter. 24 rows, six years.
--
-- Seed data, not schema. Run after 01-04; file 01 drops this table, so this
-- file must be re-run after any rebuild.
--
-- economic_regime per D-001. The regime describes the ORIGINATION environment,
--   not what the loan later lived through. A 2005 loan was underwritten in
--   loose pre-crisis conditions and then experienced the crisis — the regime
--   labels the first, which is what makes vintage comparison meaningful.
--
-- ON CONFLICT DO NOTHING makes this idempotent without deleting rows that
--   dim_loan and fact_loan_performance may already reference.

INSERT INTO dim_vintage (vintage_code, vintage_year, vintage_quarter, economic_regime) VALUES
    ('2005Q1', 2005, 1, 'Pre-crisis'),
    ('2005Q2', 2005, 2, 'Pre-crisis'),
    ('2005Q3', 2005, 3, 'Pre-crisis'),
    ('2005Q4', 2005, 4, 'Pre-crisis')
ON CONFLICT (vintage_code) DO NOTHING;

INSERT INTO dim_vintage (vintage_code, vintage_year, vintage_quarter, economic_regime) VALUES
    ('2006Q1', 2006, 1, 'Pre-crisis'),
    ('2006Q2', 2006, 2, 'Pre-crisis'),
    ('2006Q3', 2006, 3, 'Pre-crisis'),
    ('2006Q4', 2006, 4, 'Pre-crisis')
ON CONFLICT (vintage_code) DO NOTHING;

INSERT INTO dim_vintage (vintage_code, vintage_year, vintage_quarter, economic_regime) VALUES
    ('2007Q1', 2007, 1, 'Crisis'),
    ('2007Q2', 2007, 2, 'Crisis'),
    ('2007Q3', 2007, 3, 'Crisis'),
    ('2007Q4', 2007, 4, 'Crisis')
ON CONFLICT (vintage_code) DO NOTHING;

INSERT INTO dim_vintage (vintage_code, vintage_year, vintage_quarter, economic_regime) VALUES
    ('2008Q1', 2008, 1, 'Crisis'),
    ('2008Q2', 2008, 2, 'Crisis'),
    ('2008Q3', 2008, 3, 'Crisis'),
    ('2008Q4', 2008, 4, 'Crisis')
ON CONFLICT (vintage_code) DO NOTHING;

INSERT INTO dim_vintage (vintage_code, vintage_year, vintage_quarter, economic_regime) VALUES
    ('2012Q1', 2012, 1, 'Recovery'),
    ('2012Q2', 2012, 2, 'Recovery'),
    ('2012Q3', 2012, 3, 'Recovery'),
    ('2012Q4', 2012, 4, 'Recovery')
ON CONFLICT (vintage_code) DO NOTHING;

INSERT INTO dim_vintage (vintage_code, vintage_year, vintage_quarter, economic_regime) VALUES
    ('2017Q1', 2017, 1, 'Benign'),
    ('2017Q2', 2017, 2, 'Benign'),
    ('2017Q3', 2017, 3, 'Benign'),
    ('2017Q4', 2017, 4, 'Benign')
ON CONFLICT (vintage_code) DO NOTHING;
