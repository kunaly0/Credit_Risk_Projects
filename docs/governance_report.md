# Governance report - Project 0

2 October 2026, updated 5 October. Covers S00 to S07: data acquisition, schema, load, data
quality, macro data and the controls around them.

The data and the code held up. Raw files match their checksums on both
disks, the backup restores, the load reconciles to the source files, and the
DQ suite gave identical results before and after the database moved disks.

The weak point was the records about the work. Eleven times between August
and October a record said one thing and the system showed another. Most
came from two habits: handoffs written from memory at the end of a session
instead of from command output, and controls written down as plans ("refresh
at every section close") that nobody checked later. From S07 the rule is
that conclusions come from logs and command output, every commit is checked
before it is made, and anything planned for later is listed in the handoff
and checked at the next session's opener. That rule is new; the S08 opener
is its first test.

## Controls that were tested and work

| Control | How it was tested | Result |
|---|---|---|
| SHA-256 checksums on raw files | Recomputed for every file, 2 Oct | 227 of 227 match |
| Second copy of the raw layer on C: | Same check on the copy | 227 of 227 match |
| Database backup | Restored into a throwaway database, row counts compared, 1 Oct | All 8 tables match |
| Pre-commit hooks, including secret scanning | Stopped a commit with trailing spaces on 1 Oct; black and ruff passed on a new script on 2 Oct | Working |
| DQ suite, 8 automated rules | Run 13 after the disk move compared with run 12 before it | Identical |
| Macro coverage gate (R-20) | Anti-join of every loan month against the macro tables, 28 Sep | 255 of 255 months |
| Load reconciliation | Source file lines against table rows | Both differences come from one out-of-scope loan |
| Fresh build from the repo | `sql/ops/build_all.sql` on an empty database, 5 Oct | 8 tables, 24 partitions, 24 vintages |
| Load audit records failed loads | Same file loaded twice into that database, 5 Oct | First load success, second recorded as failed, both with real durations |
| Automated checks on every push | GitHub Actions runs black, ruff and the unit tests | See the Actions tab on GitHub |
| CHECK constraints | Real data at load | Blocked bad values. Three limits were set too tight and were corrected (D-031, D-034, D-044) |

## Controls that did not work

| Control | What happened | Status |
|---|---|---|
| Project Knowledge refreshed at every section close (D-018) | Never refreshed. It still describes the project as of 23 Aug. The S04 section pack was never uploaded | Refresh at S07 close |
| Incidents recorded in handoffs | 3 of 12 read failures were recorded. The S06 handoff said the server was not restarted; its log shows two restarts | Incidents now taken from the server log |
| Disk sleep fix for the read failures (D-039) | Five more failures followed | Superseded by D-047 |
| Load audit | Failed loads left no row, and TRUNCATE is not logged, so the audit total does not match the table (R-01 fails) | Failed loads fixed 5 Oct (#1). TRUNCATE still open (#12) |
| Exposed FRED key "monitored" (D-005) | Nothing monitored it | Key rotated 1 Oct; closed |

## Findings

**F1 - High. The repo could not rebuild the database.** The fact
partitions used a tablespace that was created by hand and never scripted, so
`sql/03` would fail on any other machine. The 48 fact indexes had also
landed on C: without anyone deciding it. Fixed 1 Oct: the partitions use
the default tablespace, the old one is dropped, and D-048 sets the rule for
keeping a fresh build working. Verified 5 Oct: `sql/ops/build_all.sql`
builds the full schema on an empty database.

**F2 - High. The fact data sat on a disk with unexplained read failures.**
Twelve failures between 13 and 28 Sep, all on D:, all on the first block of
a file. Root cause not found. Fixed 30 Sep: data moved to C: (D-047). If the
error appears on C:, the disk was not the cause and the decision reopens.

**F3 - Medium. Records written from memory.** The handoffs held 3 of 12
failures and denied a restart the log shows. A commit message said a
correction was made that was not in the file. Fixed: conclusions from logs,
and a check step before every commit.

**F4 - Medium. Planned controls not followed up.** The D-018 refresh, the
S04 pack upload and the D-005 monitoring were all written as plans and never
checked. Open until S07 close.

**F5 - Medium. The load audit cannot explain the table on its own.** Runs
2, 3, 7 and 13 exist only as gaps, and the audit cannot say which of four
2017 loads is in the table. The lineage document explains each gap from the
decision log. Fixed 5 Oct for future loads: a failed load now leaves a
'failed' row with real timings (#1, #2). Testing the fix found that rows
rejected as out of scope were still added to the field counts; fixed the
same day (#14). Past runs are unchanged, and TRUNCATE is still not logged
(#12).

**F6 - Medium. The macro tables do not record which FRED pull they hold.**
D-041 said they did. Since FRED revises history, the pull date matters.
Recorded in `docs/lineage.md`; fix when `load_fred.py` next runs.

**F7 - Low. The loader ignores most of its config file.** Encoding and file
paths are hard-coded; the config said otherwise. 5 Oct: the config now states
which keys are read and its encoding matches the loader. Making the loader
read it is a Project 1 item (#16).

**F8 - Low. `docs/methodology.md` was a generic template.** It referred to
a prompt as its governing specification and said nothing specific to this
project. Deleted 5 Oct; the method is in the README, the decision log and
this report.

## Decision log

49 entries, D-001 to D-049. D-019 was never used. Five were replaced or
corrected by later entries: D-002's volumes by D-025, D-004 by D-008, D-031
by D-034, and D-022 and D-039 by D-047. Two were recorded late and say so
(D-018, D-046). Corrections and outcomes are added under the original entry
with a date, never written over it (D-005, D-039, D-041, D-047).

## Open items carried into Project 1

- Load audit defects #4 and #12 (`docs/known_defects.md`).
- FRED pull not recorded in the database (F6).
- Territory loans (GU, VI, PR) have no state macro data. S10 decides whether
  to use national values or exclude them.
- 1,153 loans carry a raised balance with no modification on record (R-12),
  and 1,395 repeat a loan age with no modification (R-17). Unexplained.
- The undocumented DTI ceiling of 50 from 2012 (R-06).
- Carried since S05: UPB curtailments on F06Q10000466, zero_balance_code 16
  on F06Q10000685, field lengths at positions 34-35, the sign of
  delinquent_accrued_interest.
- LendingClub source URL not recorded (D-003).
- Unit tests cover the date and vintage parsers and the checksum script.
  The loader and the DQ suite need a database and have no tests yet.
- No backup off this laptop.

## Limitations for anyone using this data

- A prime, fixed-rate, conforming book: 100% fixed rate, 2.6% of loans below
  FICO 620. Results will not carry over to subprime or adjustable-rate
  lending.
- The sample takes 12,500 loans per quarter, so it is not weighted by how
  many loans were actually made each quarter (D-033).
- No 2009-2011 vintages. The book shrinks after 2008 for sampling reasons,
  not economic ones.
- Missing DTI means different things before and after 2012: withheld above
  65 earlier, HARP refinances later (R-06, R-14).
- loan_age stalls after modifications and should be derived from dates
  (R-16, R-17).
- vantagescore and property_valuation_method are almost entirely empty
  (R-04).
- FRED values are the latest revisions, and the delay before each figure was
  published is not modelled (D-041, D-043).
- State and national house price indices are different measures and cannot
  be compared directly (D-046).
