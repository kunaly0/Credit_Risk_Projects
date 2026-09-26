--- unemployment and hpi are allowed to be null : never store zero as placeholder
CREATE TABLE dim_macro_state(
	    month           DATE           CHECK(EXTRACT(DAY FROM month) = 1),
		property_state  CHAR(2)        CHECK(property_state ~ '^[A-Z]{2}$'),
		unemployment    NUMERIC(4,1)   CHECK(unemployment BETWEEN 0 AND 100),
		hpi             NUMERIC(8,2)   CHECK(hpi > 0),
		PRIMARY KEY(property_state, month)
);
