"""Check src/model reproduces S10 exactly: fills, bins and IV (s10_binning_tables.csv).

Needs the local database, so it skips itself where there is none (GitHub CI).
"""

import os
from pathlib import Path

import pandas as pd
import pytest
from dotenv import load_dotenv
from optbinning import OptimalBinning

from src.model.binning import fit_binners
from src.model.prepare import get_engine, load_config, prepare_sets

load_dotenv()
pytestmark = pytest.mark.skipif(
    not os.getenv("DB_HOST"), reason="needs the local credit_risk database"
)

S10_TABLES = Path(__file__).resolve().parents[1] / "docs" / "s10_binning_tables.csv"
FEATURES = [
    "credit_score",
    "original_ltv",
    "rate_spread",
    "original_dti_ratio",
    "mi_percentage",
    "number_of_borrowers",
    "loan_term",
    "property_state",
    "channel",
]
S10_FILLS = {
    "credit_score": 745.0,
    "original_ltv": 75.0,
    "original_dti_ratio": 35.0,
    "mi_percentage": 0.0,
    "number_of_borrowers": 2.0,
}


@pytest.fixture(scope="module")
def fitted() -> tuple[dict[str, float], dict[str, OptimalBinning]]:
    """Prepare train and fit the 9 binners once, shared by every test here."""
    cfg = load_config()
    train, _, fills = prepare_sets(get_engine(), cfg)
    return fills, fit_binners(train, cfg)


@pytest.fixture(scope="module")
def s10() -> pd.DataFrame:
    """The 9 binning tables saved at the end of S10."""
    return pd.read_csv(S10_TABLES, index_col=0)


def test_fill_values_match_s10(fitted) -> None:
    fills, _ = fitted
    assert fills == S10_FILLS


def test_same_nine_features_in_same_order(fitted, s10) -> None:
    _, binners = fitted
    assert list(binners) == FEATURES == list(s10["feature"].unique())


@pytest.mark.parametrize("feature", FEATURES)
def test_bins_match_s10(fitted, s10, feature: str) -> None:
    _, binners = fitted
    new = binners[feature].binning_table.build()
    old = s10[s10["feature"] == feature]
    assert len(new) == len(old)  # same rows, so the same number of bins
    assert new["Count"].tolist() == old["Count"].tolist()  # loans in each bin
    assert new["Event"].tolist() == old["Event"].tolist()  # defaults in each bin
    assert new.loc["Totals", "IV"] == pytest.approx(old.loc["Totals", "IV"])
