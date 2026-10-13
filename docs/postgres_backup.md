# PostgreSQL backup

| | |
|---|---|
| What | Full dump of `credit_risk`, custom format (`pg_dump -Fc`) |
| Where | `D:\Backups\credit_risk\credit_risk_<yyyyMMdd_HHmmss>.dump` - a different physical disk from the database, which is on C: (D-047) |
| When | At every section close, and before any change that moves or rewrites tables |
| Proof | Restore into a throwaway database and run `sql/ops/table_row_counts.sql` on both. Every count must match |
| Keep | The three most recent dumps |

## Steps

The normal way, from the repo root: `python -m scripts.backup_db --test`.
It dumps to BACKUP_DIR from `.env`, restores into `credit_risk_restore_test`,
compares `sql/ops/table_row_counts.sql` on both, drops the test database and
warns when more than three dumps are kept. The password comes from `.env`.
Without `--test` it only dumps. By hand:

1. Dump: `pg_dump -h localhost -U postgres -d credit_risk -Fc -f <file>`
2. In psql: `CREATE DATABASE credit_risk_restore_test;`
3. Restore: `pg_restore -h localhost -U postgres -d credit_risk_restore_test -j 4 <file>`
4. In psql: run `sql/ops/table_row_counts.sql` on `credit_risk`, then `\c credit_risk_restore_test` and run it again
5. `\c credit_risk`, then `DROP DATABASE credit_risk_restore_test;`

## Log

| Date | File | Size | Dump | Restore | Result |
|---|---|---|---|---|---|
| 2026-10-01 | credit_risk_20261001_161012.dump | 305 MB | 1.3 min | 3.9 min | 8 of 8 tables match; fact_loan_performance 19,859,812 |
| 2026-10-05 | credit_risk_20261005_172608.dump | 305 MB | - | not repeated | S07 close. Same procedure as the 1 Oct restore test |
| 2026-10-13 | credit_risk_20261013_113338.dump | 308 MB | 2.0 min | stopped | S08 close, by hand. The restore printed nothing for about 10 minutes and was cancelled, probably at a password prompt that never showed. Not tested |
| 2026-10-13 | credit_risk_20261013_115703.dump | 308 MB | 1.0 min | 3.2 min | scripts/backup_db.py --test. 9 of 9 tables match, pd_target included; fact_loan_performance 19,859,812 |

## Not covered

- The raw layer. It has its own second copy at `C:\Backup\Datasets\Raw` (D-047).
- `.env` and `postgresql.conf`.
- Losing the laptop. Every copy is on one machine. load_audit, load_audit_field and dq_results record past runs and cannot be rebuilt from Raw, so they are the part an off-machine copy would protect.
