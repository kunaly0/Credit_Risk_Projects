# Data Dictionary — Freddie Mac SFLLD Origination Data File

**Dataset:** Single-Family Loan-Level Dataset (SFLLD), Standard Dataset, Release 47 layout (effective July 2026)
**File naming:** `orig_YYYYQn.txt`, pipe-delimited, no header row, empty-string nulls
**Status:** All 31 positions verified against 6 raw records from `orig_2005Q1.txt` (2026-08-24). Field count, enumerations, and cross-file consistency (loan F05Q10000001 matches its performance-file counterpart on UPB and rate) all confirmed. No open discrepancies.
**Sources:** Freddie Mac SFLLD General User Guide (Jan 2026, project knowledge); `release_notes.pdf` and `disclosure-changes-summary.pdf`, freddiemac.com/fmac-resources/research/pdf/.

## Note on Length

This is pipe-delimited, not fixed-width — Freddie Mac's "Length" spec is a documented *maximum*, not the actual on-wire width, so a short observed value (e.g. `1` for Number of Units) doesn't confirm or contradict the documented max. Fields marked `*` have a length that wasn't independently reconfirmed from documentation this session; treat as approximate until checked against `file_layout.xlsx` or a wider sample. This matters for S02's `VARCHAR` sizing, not for anything in S01.

## Field layout

| Pos | Field Name | Type | Length | Valid Values / Enumeration | Definition | Notes |
|---|---|---|---|---|---|---|
| 1 | Credit Score (Classic FICO®) | Numeric | 4 | 300–850, 9999=NA | Third-party credit score used to originate the loan. | Renamed to specify "Classic FICO®" in Release 47 |
| 2 | First Payment Date | Date | 6 | YYYYMM | First scheduled mortgage payment date. | |
| 3 | First Time Homebuyer Indicator | Alpha | 1 | Y / N / 9 | No ownership interest in a residential property in the prior 3 years. | Renamed from "First Time Homebuyer Flag" |
| 4 | Maturity Date | Date | 6 | YYYYMM | Scheduled mortgage maturity date. | |
| 5 | MSA or Metropolitan Division | Numeric | 5* | 5-digit code, Null=not in an MSA/division or unknown | Geographic classification of the property. | |
| 6 | Mortgage Insurance Percentage (MI%) | Numeric | 3 | 1–55%, 0=No MI, 999=NA | % loss coverage from a mortgage insurer at purchase. | |
| 7 | Number of Units | Numeric | 1–2* | 1–4, 99=NA | Property unit count. | |
| 8 | Occupancy Status | Alpha | 1 | P / I / S / 9 | Primary residence / investment / second home. | |
| 9 | Original CLTV | Numeric | 3* | 6–200% (pre-2018Q1) or 1–998% (since), 999=NA | Combined LTV including secondary financing. | |
| 10 | Original DTI Ratio | Numeric | 3 | 0–65%, 999=NA | Debt-to-income ratio at underwriting. | |
| 11 | Original UPB | Numeric (decimal) | * | $ amount, rounded to nearest $1,000 | Loan amount at origination. | |
| 12 | Original LTV | Numeric | 3 | 6–105% (pre-2018Q1) or 1–998% (since), 999=NA | Loan-to-value at origination. | |
| 13 | Original Interest Rate | Numeric (decimal) | * | rate % | Note rate at origination. | |
| 14 | Channel | Alpha | 1 | R / B / C / T / 9 | Origination channel: retail / broker / correspondent / TPO. | |
| 15 | Prepayment Penalty Indicator | Alpha | 1 | Y / N | | Renamed from "Prepayment Penalty Mortgage (PPM) Flag" |
| 16 | Amortization Type | Alpha | 3 | FRM / ARM | | |
| 17 | Property State | Alpha | 2 | US state postal abbreviation | | |
| 18 | Property Type | Alpha | 2 | CP / CO / PU / SF / MH / 99 | Cooperative / condo / PUD / single-family / manufactured. | |
| 19 | Postal Code | Numeric | 3 | first 3 digits of ZIP, 000=unknown | | Release 47 shortened from the old 5-char `###00` format |
| 20 | Loan Identifier | Alphanumeric | 12 | `PYYQnXXXXXXX` | Unique loan-level ID. | Renamed from "Loan Sequence Number" |
| 21 | Loan Purpose | Alpha | 1 | P / C / N / R / 9 | Purchase / cash-out refi / no-cash-out refi / refi-not-specified. | |
| 22 | Original Loan Term | Numeric | * | months | | |
| 23 | Number of Borrowers | Numeric | 2 | 1–10, 99=NA | | Release 47: no longer zero-padded for single digits (`1`, not `01`) |
| 24 | Seller Name | Alphanumeric | * | name, or `OTHER` | `OTHER` if under 1% of the quarter's total UPB. | Release 47 sentinel changed from `Other Sellers` to `OTHER` |
| 25 | Super Conforming Flag | Alpha | 1 | Y / N | | Release 47: `N` case changed from blank/space to explicit `N` |
| 26 | Pre-HARP Loan Sequence Number | Alphanumeric | 12 | `PYYQnXXXXXXX` or blank | Links a HARP loan back to its pre-HARP ID. | |
| 27 | Special Eligibility Program | Alpha | 1 | H / F / R / null | Home Possible / HFA Advantage / Refi Possible. | Release 47: NA sentinel changed from `9` to null |
| 28 | HARP Indicator | Alpha | 1 | Y / N | | Release 47: non-HARP case changed from blank/space to `N` |
| 29 | Property Valuation Method | Numeric | 1 | 1 / 2 / 3 / 4 / 7 | Appraisal waiver / appraisal / other / ACE+PDR / not available. | |
| 30 | Interest Only (I/O) Indicator | Alpha | 1 | Y / N | | |
| 31 | VantageScore® 4.0 | Numeric | 4 | 300–850, 9999=NA | Standardized VantageScore used alongside Classic FICO. | New field, Release 47 |

## Cross-reference

Loan `F05Q10000001` appears in both this file and `data_dictionary_performance.md`'s verification sample — Original UPB (190000) and Original Interest Rate (5.625) here match Current Actual UPB and Current Interest Rate at that loan's first performance record. Same-loan consistency across files, useful if S02's join logic ever needs sanity-checking.
