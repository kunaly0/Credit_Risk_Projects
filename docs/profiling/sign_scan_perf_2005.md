# Sign scan — sample_perf_2005.txt

Scanned 2026-09-01. Source: `D:\Datasets\Working\Freddie_mac_sample\sample_2005\sample_perf_2005.txt`
Rows: 3,877,176 (matches `docs/row_counts_baseline.csv`). Method: full-file
streaming min/max per field, PowerShell. Supports D-027.

| Field | S02 constraint | n | Min | Max | Verdict |
|---|---|---|---|---|---|
| current_actual_upb | `>= 0` | 3,877,176 | 0 | 702,000.00 | pass |
| current_non_interest_bearing_upb | `>= 0` | 3,877,176 | 0 | 173,274.48 | pass |
| current_interest_bearing_upb | `>= 0` | 3,877,176 | 0 | 702,000.00 | pass |
| zero_balance_removal_upb | `>= 0` | 48,819 | 0.01 | 680,000.00 | pass |
| mi_recoveries | `<= 0` | 2,696 | -126,653.64 | 0 | pass |
| cumulative_modification_costs | `>= 0` | 1,411 | 13.26 | 268,644.74 | pass |
| bankruptcy_cramdown_costs | `>= 0` | 7,991 | 0 | 146,806.31 | pass |
| net_sales_proceeds | `<= 0` | 2,704 | -553,700.61 | **+4,997.37** | FAIL |
| non_mi_recoveries | `<= 0` | 2,696 | -206,944.30 | **+5,202.76** | FAIL |
| total_expenses | `>= 0` | 2,696 | **-69,219.56** | 227,788.74 | FAIL |
| legal_costs | `>= 0` | 2,696 | **-14,254.65** | 26,981.44 | FAIL |
| maintenance_costs | `>= 0` | 2,696 | **-316.83** | 150,941.95 | FAIL |
| taxes_and_insurance | `>= 0` | 2,696 | **-76,241.91** | 136,054.22 | FAIL |
| miscellaneous_expenses | `>= 0` | 2,696 | **-33,328.10** | 94,834.22 | FAIL |
| current_period_modification_costs | `>= 0` | 146,225 | **-318.50** | 2,477.25 | FAIL |
| delinquent_accrued_interest | `<= 0` | 2,704 | **-947.03** | **+264,875.74** | FAIL |

Eight of fifteen constrained fields carry values against the Release 47
convention. `delinquent_accrued_interest` listed separately — found first,
scanned in an earlier pass.

## Also established
- `net_sales_proceeds`: 0 non-numeric values. The documented `'U'` sentinel
  does not appear in this file. Loader conversion retained; other vintages
  unchecked.
- `servicer_name` max length 52. `VARCHAR(60)` sufficient.
- `bankruptcy_cramdown_costs`: 7,991 populated rows. A real field, not a
  trailing-delimiter artifact.

## Limitation
One vintage year, sample dataset only. Re-run per vintage during load; the
profiler moves to Python in S03 Step 3 so this becomes reproducible.
