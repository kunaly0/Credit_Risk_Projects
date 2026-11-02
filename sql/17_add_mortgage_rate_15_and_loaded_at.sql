-- 17_add_mortgage_rate_15_and_loaded_at.sql
-- Adds to dim_macro the 15-year market rate (FRED MORTGAGE15US, monthly
-- average like mortgage_rate, D-043) for the rate spread of loans of 180
-- months or less (D-059).
--
-- Adds loaded_at to dim_macro and dim_macro_state: when each row was
-- written. load_fred.py replaces both tables on every run, so this is the
-- time of the last load. Raw responses keep the exact pull time in their
-- folder name. Closes F6.
ALTER TABLE dim_macro
    ADD COLUMN mortgage_rate_15 NUMERIC(5,3)
        CHECK (mortgage_rate_15 BETWEEN 0 AND 30);

ALTER TABLE dim_macro
    ADD COLUMN loaded_at TIMESTAMPTZ NOT NULL DEFAULT now();

ALTER TABLE dim_macro_state
    ADD COLUMN loaded_at TIMESTAMPTZ NOT NULL DEFAULT now();
