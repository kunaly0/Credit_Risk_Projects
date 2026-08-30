DROP TABLE IF EXISTS fact_loan_performance;
DROP TABLE IF EXISTS dim_loan;
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


-- dim_loan — one row per loan, sourced from orig_YYYYQn.txt (Release 47 layout, 31 fields).
--
-- COLUMN ORDER IS NOT SOURCE-FILE ORDER.
--   loan_sequence_number is position 20 in the file, moved to position 1 here.
--   The loader must therefore specify an explicit column list in COPY. See S03.
--
-- vintage_code is assigned by the loader from the source filename (D-020).
--   It does not appear anywhere in the origination file. First Payment Date
--   must never be used for this — it is overwritten on loan modification.
--
-- SENTINEL HANDLING: every documented "not available" code is converted to
-- NULL during load. The constraints below assume this has already happened,
-- so the sentinel values themselves are deliberately absent from the CHECKs.
--   credit_score           9999  -> NULL
--   vantagescore           9999  -> NULL
--   mi_percentage           999  -> NULL   (0 = no MI is a real value, kept)
--   original_cltv           999  -> NULL
--   original_ltv            999  -> NULL
--   original_dti_ratio      999  -> NULL
--   number_of_units          99  -> NULL
--   number_of_borrowers      99  -> NULL
--   property_type          '99'  -> NULL
--   first_time_homebuyer    '9'  -> NULL
--   occupancy_status        '9'  -> NULL
--   channel                 '9'  -> NULL
--   loan_purpose            '9'  -> NULL
--   postal_code           '000'  -> NULL
--
-- Field 20 is named "Loan Identifier" as of Release 47. The older name
-- "Loan Sequence Number" is retained here as it is what twenty years of
-- published Freddie Mac research uses.
CREATE TABLE dim_loan(
	    loan_sequence_number          VARCHAR(12)    PRIMARY KEY,
		vintage_code                  VARCHAR(6)     NOT NULL REFERENCES dim_vintage(vintage_code),
	    credit_score                  SMALLINT       CHECK(credit_score BETWEEN 300 AND 850),
		first_payment_date            DATE           CHECK(EXTRACT(DAY FROM first_payment_date) = 1),
		first_time_homebuyer          BOOLEAN,
		maturity_date                 DATE           CHECK(EXTRACT(DAY FROM maturity_date) = 1),
		msa                           CHAR(5)        CHECK(msa ~ '^[0-9]{5}$'),
		mi_percentage                 SMALLINT       CHECK(mi_percentage BETWEEN 0 AND 55),
		number_of_units               SMALLINT       CHECK(number_of_units BETWEEN 1 AND 4),
		occupancy_status              CHAR(1)        CHECK(occupancy_status IN ('P','I','S')),
		original_cltv                 SMALLINT       CHECK(original_cltv BETWEEN 0 AND 998),
		original_dti_ratio            SMALLINT       CHECK(original_dti_ratio BETWEEN 0 AND 65),
		original_upb                  INTEGER        CHECK(original_upb >= 0),
		original_ltv                  SMALLINT       CHECK(original_ltv BETWEEN 0 AND 998),
		original_interest_rate        NUMERIC(5,3)   CHECK(original_interest_rate BETWEEN 0 AND 30),
		channel                       CHAR(1)        CHECK(channel IN ('R','B','C','T')),
		prepayment_penalty_indicator  CHAR(1)        CHECK(prepayment_penalty_indicator IN ('Y','N')),
		amortization_type             CHAR(3)        CHECK(amortization_type IN ('FRM','ARM')),
		property_state                CHAR(2)        CHECK(property_state ~ '^[A-Z]{2}$'),
		property_type                 CHAR(2)        CHECK(property_type IN ('CO','PU','MH','SF','CP')),
		postal_code                   CHAR(3)        CHECK(postal_code ~ '^[0-9]{3}$'),
		loan_purpose                  CHAR(1)        CHECK(loan_purpose IN ('P','C','N','R')),
		loan_term                     SMALLINT       CHECK(loan_term BETWEEN 1 AND 999),
		number_of_borrowers           SMALLINT       CHECK(number_of_borrowers BETWEEN 1 AND 10),
		seller_name                   VARCHAR(60),
		super_conforming_flag         BOOLEAN,
        pre_harp_loan_sequence_number VARCHAR(12),
		special_eligibility_program   CHAR(1)        CHECK(special_eligibility_program IN ('H','F','R')),
		harp_indicator                CHAR(1)        CHECK(harp_indicator IN ('Y','N')),
		property_valuation_method     CHAR(1)        CHECK(property_valuation_method IN ('1','2','3','4','7')),
		interest_only_indicator       BOOLEAN,
		vantagescore                  SMALLINT       CHECK(vantagescore BETWEEN 300 AND 850)
);
