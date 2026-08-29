CREATE TABLE dim_vintage (
        vintage_code      VARCHAR(6)    PRIMARY KEY,
		vintage_year      SMALLINT      NOT NULL CHECK  (vintage_year BETWEEN 1999 AND 2030),
		vintage_quarter   SMALLINT      NOT NULL CHECK  (vintage_quarter BETWEEN 1 AND 4) ,
		economic_regime   VARCHAR(20)   NOT NULL CHECK  (economic_regime IN ('Pre-crisis','Crisis','Recovery','Benign')),
	    CHECK (vintage_code = vintage_year::TEXT || 'Q' || vintage_quarter::TEXT)
	);
