# Data Dictionary — Freddie Mac SFLLD Monthly Performance Data File

**Dataset:** Single-Family Loan-Level Dataset (SFLLD), Standard Dataset, Release 47 layout (effective July 2026)
**File naming:** `perf_YYYYQn.txt`, pipe-delimited, no header row, empty-string nulls
**Status:** Positions 1–34 verified against 2 raw records from `perf_2005Q1.txt` (2026-08-24), cross-checked against Freddie Mac's Release 47 Release Notes and Disclosure Changes summary. Position 35 (Bankruptcy Cramdown Costs) wasn't populated in that 2-row spot check, but the missingness census (below) confirms it's genuinely live in the data (~0.8% of rows) — just rare, not absent.
**Sources:** Freddie Mac SFLLD General User Guide (Jan 2026, project knowledge); `release_notes.pdf` and `disclosure-changes-summary.pdf`, freddiemac.com/fmac-resources/research/pdf/, fetched 2026-08-24.
**Related decision:** D-016 (closed 2026-08-24)

## Read this before using the table

- **Sign convention (Release 47):** Recoveries/gains are negative, expenses/losses are positive, on every $ field marked "sign flip" below. This is reversed from the pre-Release-47 convention and is critical for any LGD / actual-loss calculation downstream.
- **Current Loan Delinquency Status (position 4):** zero-padded 2-digit string, capped at 99, `XX` = not available. Treat as string, not int — casting will silently drop leading zeros and break on `XX`/`RA`.
- **Loss/recovery fields (14–22, 28) are conditional:** only populated for Zero Balance Codes 02, 03, 09, 15, and set to null when a Defect Settlement Date is populated. Blank here is usually correct, not missing data — Step 4's missingness census needs to read against this rule, not flag it blind.

## Field layout

| Pos | Field Name | Type | Length | Valid Values / Enumeration | Definition | Notes |
|---|---|---|---|---|---|---|
| 1 | Loan Identifier | Alphanumeric | 12 | `PYYQnXXXXXXX` (P: F=FRM, A=ARM) | Unique loan-level ID: product, origination year/quarter, random sequence. | Renamed from "Loan Sequence Number" |
| 2 | Period | Date | 6 | YYYYMM | As-of month for this record. | Renamed from "Monthly Reporting Period" |
| 3 | Current Actual UPB | Numeric (decimal) | 12 | $ amount | Servicer-reported ending balance; interest-bearing + non-interest-bearing UPB. | |
| 4 | Current Loan Delinquency Status | Alphanumeric | 3 | `00`–`99`, `RA`=REO acquisition, `XX`=not available | Days-delinquent bucket per DDLPI, MBA method. | Release 47: now zero-padded, capped at 99, `XX` replaces blank for N/A |
| 5 | Loan Age | Numeric | 3 | integer | Scheduled payments since first payment (or modification) date. | |
| 6 | Remaining Months to Legal Maturity | Numeric | 3 | integer | Months to (modified) maturity date. | |
| 7 | Underwriting Defect and Major Servicing Defect Settlement Date | Date | 6 | YYYYMM | Date an underwriting/servicing defect was resolved. | Renamed from "Defect Settlement Date" |
| 8 | Modification Flag | Alpha | 1 | Y / P / null | Y=modified this period, P=modified prior period. | |
| 9 | Zero Balance Code | Numeric | 2 | 01, 02, 03, 09, 15, 16, 96 | Reason balance went to zero — the termination-event source field. | 96 redefined: "Confirmed Underwriting/Major Servicing Defect prior to credit event" |
| 10 | Zero Balance Effective Date | Date | 6 | YYYYMM | Period the zero-balance event occurred. | |
| 11 | Current Interest Rate | Numeric (decimal) | 8 | rate % | Current note rate, incl. modifications. | |
| 12 | Current Non-Interest Bearing UPB | Numeric | 12 | $ amount | Deferred, non-amortizing UPB portion. | Renamed from "Current Deferred UPB" |
| 13 | DDLPI | Date | 6 | YYYYMM | Due date through which scheduled P&I is paid. | |
| 14 | MI Recoveries | Numeric (decimal) | 12 | $ amount | MI claim proceeds on a credit loss. | Sign flip: now negative |
| 15 | Net Sales Proceeds | Alphanumeric (decimal) | 14 | $ amount, or `U`=unknown | Disposition/sale proceeds net of selling expenses. | Sign flip: now negative |
| 16 | Non MI Recoveries | Numeric (decimal) | 12 | $ amount | Non-MI proceeds (make-whole, refunds, escrow, etc.). | Sign flip: now negative |
| 17 | Total Expenses | Numeric (decimal) | 12 | $ amount | Sum of Legal + Maintenance/Preservation + Taxes/Insurance + Misc expenses. | Sign flip: now positive |
| 18 | Legal Costs | Numeric (decimal) | 12 | $ amount | Legal expenses on disposition. | Sign flip: now positive |
| 19 | Maintenance and Preservation Costs | Numeric (decimal) | 12 | $ amount | Property upkeep costs pre-disposition. | Sign flip: now positive. Length inferred from adjacent expense fields, not directly confirmed in source text. |
| 20 | Taxes and Insurance | Numeric (decimal) | 12 | $ amount | Property tax/insurance tied to disposition. | Sign flip: now positive |
| 21 | Miscellaneous Expenses | Numeric (decimal) | 12 | $ amount | Other disposition costs (title, admin, auction fees). | Sign flip: now positive |
| 22 | Actual Loss | Numeric (decimal) | 12 | $ amount | Freddie Mac's realized loss calculation at disposition. | Sign flip: now positive=loss, negative=gain |
| 23 | Cumulative Modification Costs | Numeric (decimal) | 12 | $ amount | Running modification cost since the first modification. | Release 47: now disclosed every period, not just once |
| 24 | Interest Rate Step Indicator | Alpha | 1 | Y / N / null | Flags a scheduled rate step-up in the latest modification. | Renamed from "Step Modification Flag" |
| 25 | Payment Deferral Flag | Alpha | 1 | C / P / null | C=current-period deferral, P=prior-period. | Renamed from "Deferred Payment Plan"; value changed Y→C |
| 26 | Estimated Loan-to-Value (ELTV) | Numeric | 4 | 1–998, 999=not available | Current LTV via Freddie Mac's AVM. Only populated Apr 2017 onward. | Release 47 removed the separate "null" option — 999 now covers it |
| 27 | Zero Balance Removal UPB | Numeric (decimal) | 12 | $ amount | Total UPB immediately before the zero-balance code was applied. | |
| 28 | Delinquent Accrued Interest | Numeric (decimal) | 12 | $ amount | Interest owed by the borrower at default. | Sign flip: now negative |
| 29 | Delinquency Due to Disaster | Alpha | 1 | Y / null | Servicer-reported disaster hardship flag. Populated Jan 2014 onward. | |
| 30 | Borrower Assistance Plan | Alpha | 1 | F / R / T / null | Payment-relief plan type, if any. | Renamed from "Borrower Assistance Status Code" |
| 31 | Current Period Modification Costs | Numeric (decimal) | 12 | $ amount | This period's modification cost only (vs. field 23's cumulative figure). | Renamed from "Current Month Modification Cost" |
| 32 | Current Interest Bearing UPB | Numeric (decimal) | 12 | $ amount | Amortizing UPB portion of a modified loan. | Renamed from "Interest Bearing UPB" |
| 33 | Mortgage Insurance Cancellation Indicator | Alpha/Numeric | 1 | Y / N / 7 | Whether MI has been cancelled since acquisition. | Moved in from Origination file, Release 47 |
| 34 | Servicer Name | Alphanumeric | **TBD** | Servicer name, or `OTHER` | Current servicer; `OTHER` if under 1% of the quarter's total UPB. | Moved in from Origination file, Release 47. Length not confirmed from documentation reviewed — verify empirically or via `file_layout.xlsx`. |
| 35 | Bankruptcy Cramdown Costs | Numeric (decimal), inferred | **TBD** | $ amount | Bankruptcy cramdown costs, incl. court-ordered UPB reduction. | New field, Release 47. Not observed live in samples — type/length inferred from sibling $ fields, not confirmed. |

## Missingness census

Computed on the full Sample Dataset (all 6 vintages, ~20.16M rows, D-002-confirmed 50,000 loans/vintage), not Standard — a genuine random sample of loans, so field-level missingness should mirror the ~602M-row Standard population. Per-vintage breakdown lives in `Scratch/missingness_census.csv` (2026-08-24 run); this table is the overall figure.

| Field | % Null (overall) | Read as |
|---|---|---|
| 1–6, 11–13*, 25–26, 32–34 (loan_id, period, current_actual_upb, delinquency_status, loan_age, remaining_months, current_interest_rate, current_non_interest_bearing_upb, eltv raw, current_interest_bearing_upb, mi_cancellation_indicator, servicer_name) | 0.0% | Always populated — core fields, no conditional logic |
| 7 Defect Settlement Date | 100.0% (exact count pending) | Extremely rare event; verify true zero vs. sub-0.05% |
| 8 Modification Flag / 24 Interest Rate Step Indicator | 92.0–99.6% by vintage, 96.3% overall | Move together exactly — same trigger, confirms correct joint population |
| 9/10/27 Zero Balance Code / Effective Date / Removal UPB | 98.0–99.1% by vintage, 98.6% overall | Move together exactly — termination-event fields |
| 13 DDLPI | 99.6% overall | Populated at disposition — narrower trigger than Zero Balance Code |
| 14–22, 28 Loss/recovery fields (MI Recoveries, Net Sales Proceeds, Non-MI Recoveries, Expenses, Legal/Maintenance/Tax/Misc costs, Actual Loss, Delinquent Accrued Interest) | 99.9–100.0% overall | Correctly *more* missing than Zero Balance Code — only fires for codes 02/03/09/15, a subset |
| 23 Cumulative Modification Costs / 31 Current Period Modification Costs | 95.8–99.9% overall | Tracks the modification fields, not identical (cumulative vs. this-period-only) |
| 25 Payment Deferral Flag | 99.4% overall | |
| 29 Delinquency Due to Disaster | 99.7% overall | |
| 30 Borrower Assistance Plan | 99.6% overall | |
| 35 Bankruptcy Cramdown Costs | 99.2% overall (~0.8% populated) | Genuinely rare, not absent — see cross-vintage note below |

**26 ELTV, raw vs. sentinel-adjusted:** raw `.isnull()` shows 0.0% missing everywhere — misleading, since Release 47 uses `999` as the "not available" sentinel instead of a blank. Adjusted (`999` treated as missing):

| Vintage | % effectively unavailable |
|---|---|
| 2005 | 94.6% |
| 2006 | 94.2% |
| 2007 | 92.9% |
| 2008 | 92.0% |
| 2012 | 58.9% |
| 2017 | 13.0% |

Clean monotonic gradient — ELTV only populates from April 2017 onward, so this tracks exactly how much of each vintage's performance history falls after that date. Strongest available confirmation that the field's population rule is understood correctly, not assumed.

**Worth another look during EDA, not urgent:** `bankruptcy_cramdown_costs` is populated *more* in 2012/2017 (1.3–2.7%) than in the 2005–2008 crisis vintages (0.2–0.3%) — counter to naive expectation that crisis-era loans would show more bankruptcy activity. Possibly a reporting-practice or legal-provision timing effect; not investigated further here.

## Open items

- **Position 34 & 35 Type/Length** — not confirmed from documentation reviewed. Close by either finding a raw row with a real value at position 35, or pulling `file_layout.xlsx` from Freddie Mac's site.
- **Defect Settlement Date exact count** — confirm true zero vs. sub-0.05% before treating this field as structurally inert in the sample dataset.
