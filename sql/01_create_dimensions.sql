DROP TABLE IF EXISTS dim_macro;
DROP TABLE IF EXISTS dim_vintage;

CREATE TABLE dim_vintage (
        vintage_code      VARCHAR(6)    PRIMARY KEY,
		vintage_year      SMALLINT      NOT NULL CHECK  (vintage_year BETWEEN 1999 AND 2030),
		vintage_quarter   SMALLINT      NOT NULL CHECK  (vintage_quarter BETWEEN 1 AND 4) ,
		economic_regime   VARCHAR(20)   NOT NULL CHECK  (economic_regime IN ('Pre-crisis','Crisis','Recovery','Benign')),
	    CHECK (vintage_code = vintage_year::TEXT || 'Q' || vintage_quarter::TEXT)
	);


CREATE TABLE dim_macro(
	    month           DATE           CHECK(EXTRACT(DAY FROM month) = 1) PRIMARY KEY,
		unemployment    NUMERIC(4,1)   CHECK(unemployment BETWEEN 0 AND 100),
		hpi             NUMERIC(8,2)   CHECK(hpi >= 0),
		mortgage_rate   NUMERIC(5,3)   CHECK(mortgage_rate BETWEEN 0 AND 30),
		gdp_growth      NUMERIC(5,2)   CHECK(gdp_growth BETWEEN -30 AND 30)
);
