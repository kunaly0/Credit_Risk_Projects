# Known defects

Carried across sections. Append, don't delete — a fixed defect gets marked, not removed.

| # | Defect | Status | Notes |
|---|--------|--------|-------|
| 1 | Audit row rolls back with a failed load | open | 4 failed S03 runs left no trace — run_ids 2, 3, 7, 13 are gaps. Handoff said 6; live table says 4. Fixed in dq_results via separate connection (D-037) |
| 2 | load_origination timestamps use `now()` | open | Durations read 00:00:00. Only load_performance got perf_counter |
| 3 | Timing printed, not stored | open | Needs a column on load_audit |
| 4 | rows_loaded counted in Python | open | Not read back from the COPY result |
| 5 | Interest-rate check is upper-bound only | open | A negative rate would fail the load rather than be nulled |
| 6 | Dead code in loader.py | open | count_rows, read_first_rows. The latter hardcodes fields[19] |
| 7 | Indexes built before the bulk load | accepted | More fragmented than a rebuild. Not worth fixing at this scale |
| 8 | No .pgpass | open | Four password prompts per rebuild |
| 9 | No CHECK on maturity vs first payment date | accepted | Omitted per D-020. R-13 tested it: 0 violations in 299,999 loans |
| 10 | net_sales_proceeds 'U' sentinel never exercised | open | 0 occurrences across six vintages |
| 11 | idx_fact_perf_period value assumed, not measured | open | S04 queries are the first real workload against it |
| 12 | TRUNCATE is not audited | open | See below |
| 13 | Smart App Control blocks unsigned executables | partly fixed | See below |

**12 — TRUNCATE is not audited.** load_audit records rows added, because the loader adds them. It records no removals, because TRUNCATE is run separately in psql. The 2017 performance file was reloaded three times during S03 throughput measurement, each preceded by a TRUNCATE — deliberate, since reloading needs the partition cleared. R-01 now fails: audit says 28,260,469 rows, table holds 19,859,812. Fix is either a loader function that truncates and logs together, or R-01 reconciling against the live table. Not fixed by deleting audit rows.

**13 — Smart App Control.** Turned itself on mid-S04 and blocked pip-installed executables in .venv (WinError 4551). black, ruff and detect-secrets moved to local hooks run via `python -m` (D-040). The other eight hooks started passing again on their own — reason unknown, so don't rely on it. black and ruff are still unproven: no .py file has been staged since the change.
