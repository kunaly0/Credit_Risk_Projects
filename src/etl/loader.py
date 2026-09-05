import os

import psycopg
import yaml
from dotenv import load_dotenv

from src.etl.transforms import parse_yyyymm, vintage_from_loan_id

with open("config/load_config.yaml", encoding="utf-8") as f:
    config = yaml.safe_load(f)

orig_columns = config["file_types"]["origination"]["source_columns"]


def count_rows(path: str) -> int:
    total = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            total += 1
    return total


def read_first_rows(path: str, limit: int) -> None:
    with open(path, encoding="utf-8") as f:
        count = 0
        for line in f:
            fields = line.rstrip("\n").split("|")
            print(len(fields), fields[19])
            count += 1
            if count >= limit:
                break


def blank_to_none(value: str) -> str | None:
    if value == "":
        return None
    return value


def transform_orig_row(fields: list[str], counts: dict) -> tuple:
    results = []
    for i, value in enumerate(fields):
        name = orig_columns[i]
        if value == ORIG_SENTINELS.get(name):
            counts[name] = counts.get(name, 0) + 1
            results.append(None)
        else:
            results.append(blank_to_none(value))
    results[1] = parse_yyyymm(fields[1])
    results[3] = parse_yyyymm(fields[3])
    loan_id = fields[19]
    vintage = vintage_from_loan_id(loan_id)
    results.append(vintage)
    return tuple(results)


ORIG_SENTINELS = {
    "credit_score": "9999",
    "vantagescore": "9999",
    "mi_percentage": "999",
    "original_cltv": "999",
    "original_ltv": "999",
    "original_dti_ratio": "999",
    "number_of_units": "99",
    "number_of_borrowers": "99",
    "property_type": "99",
    "first_time_homebuyer": "9",
    "occupancy_status": "9",
    "channel": "9",
    "loan_purpose": "9",
    "postal_code": "000",
    "property_valuation_method": "7",
}


def get_connection() -> psycopg.Connection:
    load_dotenv()
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )
