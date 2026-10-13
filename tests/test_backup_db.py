"""Tests for the parts of scripts/backup_db.py that need no database."""

import sys
from pathlib import Path

import pytest

from scripts.backup_db import (
    compare_counts,
    drop_test_db,
    extra_dumps,
    last_line,
    run_with_progress,
)


def test_drop_refuses_a_database_that_is_not_a_restore_test() -> None:
    with pytest.raises(ValueError):
        drop_test_db("credit_risk")


def test_counts_that_match_pass() -> None:
    rows = compare_counts(
        {"dim_loan": 5, "pd_target": 5}, {"dim_loan": 5, "pd_target": 5}
    )
    assert all(ok for *_, ok in rows)


def test_a_different_count_fails() -> None:
    rows = compare_counts({"dim_loan": 5}, {"dim_loan": 4})
    assert rows == [("dim_loan", 5, 4, False)]


def test_a_table_missing_from_the_restore_fails() -> None:
    rows = compare_counts({"dim_loan": 5, "pd_target": 5}, {"dim_loan": 5})
    assert ("pd_target", 5, -1, False) in rows


def test_extra_dumps_are_the_oldest_beyond_three() -> None:
    names = [f"credit_risk_2026100{d}_120000.dump" for d in (5, 1, 9, 3)]
    extra = extra_dumps([Path(n) for n in names])
    assert [p.name for p in extra] == ["credit_risk_20261001_120000.dump"]


SLOW = [
    sys.executable,
    "-c",
    "import time; print('step one', flush=True); time.sleep(3)",
]


def test_a_command_that_finishes_returns_its_exit_code(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DB_PASSWORD", "unused")
    log_file = tmp_path / "run.log"
    assert run_with_progress(SLOW, log_file, timeout_s=30, every_s=1) == 0
    assert last_line(log_file) == "step one"


def test_a_command_past_the_timeout_is_stopped(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DB_PASSWORD", "unused")
    assert run_with_progress(SLOW, tmp_path / "run.log", timeout_s=1, every_s=1) is None
