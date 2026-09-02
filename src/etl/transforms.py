from datetime import date


def vintage_from_loan_id(loan_id: str) -> str:
    """Return the vintage code for a Freddie Mac loan sequence number."""
    if len(loan_id) != 12:
        raise ValueError(f"loan_id must be 12 characters, got {loan_id!r}")
    year_and_quarter = loan_id[1:5]
    yy = loan_id[1:3]
    if yy >= "99":
        century = "19"
    else:
        century = "20"
    return century + year_and_quarter


def parse_yyyymm(value: str) -> date | None:
    """Parse a Freddie Mac YYYYMM string into a date on the first of the month."""
    if value == "":
        return None
    if len(value) != 6:
        raise ValueError(f"value must be 6 characters, got {value!r}")
    try:
        year = int(value[0:4])
        month = int(value[4:6])
        return date(year, month, 1)
    except ValueError as exc:
        raise ValueError(f"invalid YYYYMM value {value!r}") from exc
