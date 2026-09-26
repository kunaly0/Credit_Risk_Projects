-- KNOW COLD (the migration pattern)
-- 09: correct two dim_macro CHECKs from S02.
-- hpi allowed 0 (a placeholder); gdp_growth +-30 rejected real data (Q3 2020 = +34.86).

BEGIN;

ALTER TABLE dim_macro DROP CONSTRAINT dim_macro_hpi_check;
ALTER TABLE dim_macro ADD CONSTRAINT dim_macro_hpi_check CHECK (hpi > 0);

ALTER TABLE dim_macro DROP CONSTRAINT dim_macro_gdp_growth_check;
ALTER TABLE dim_macro ADD CONSTRAINT dim_macro_gdp_growth_check CHECK (gdp_growth >= -100);

COMMIT;
