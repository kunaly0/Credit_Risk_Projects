"""Tests for src/etl/transforms.py - the two parsers every loaded row passes through."""

from datetime import date

import pytest

from src.etl.transforms import parse_yyyymm, vintage_from_loan_id


def test_vintage_from_loan_id() -> None:
    assert vintage_from_loan_id("F05Q10000071") == "2005Q1"


def test_vintage_from_loan_id_before_2000() -> None:
    assert vintage_from_loan_id("F99Q40000001") == "1999Q4"


def test_vintage_rejects_truncated_loan_id() -> None:
    # D-028: "F05Q1" would otherwise give 2005Q1 and load as a valid row
    with pytest.raises(ValueError):
        vintage_from_loan_id("F05Q1")


def test_parse_january_is_not_misread() -> None:
    # D-026: with DateStyle DMY, PostgreSQL read '200501' as 2020-05-01
    assert parse_yyyymm("200501") == date(2005, 1, 1)


def test_parse_empty_is_none() -> None:
    assert parse_yyyymm("") is None


@pytest.mark.parametrize("bad", ["20051", "2005013", "200513", "2005AB"])
def test_parse_rejects_malformed(bad: str) -> None:
    with pytest.raises(ValueError):
        parse_yyyymm(bad)
