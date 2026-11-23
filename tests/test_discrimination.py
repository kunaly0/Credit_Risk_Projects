"""Check KS, AUC and Gini on tiny hand-worked examples, and the train bands.

The maths tests need no database and run everywhere, GitHub CI included.
The band test needs the local database and skips where there is none.
"""

import os

import pandas as pd
import pytest
from dotenv import load_dotenv

from src.model import freeze
from src.model.discrimination import band_edges, band_table, measure
from src.model.prepare import get_engine, load_config, load_final_set, load_set

load_dotenv()
needs_db = pytest.mark.skipif(
    not os.getenv("DB_HOST"), reason="needs the local credit_risk database"
)

S11_TRAIN_BAND_DEFAULTS = [1695, 726, 419, 245, 176, 90, 59, 31, 11, 4]


def scored(scores: list[float], targets: list[int]) -> pd.DataFrame:
    return pd.DataFrame({"score": scores, "target": targets})


def test_hand_worked_example() -> None:
    # Defaults at 500 and 600, goods at 550 and 650. Of the 4 default-good
    # pairs, 3 have the default scoring lower: AUC 0.75, Gini 0.5.
    # Running totals from the lowest score: gaps 0.5, 0, 0.5, 0: KS 0.5.
    result = measure(scored([500, 550, 600, 650], [1, 0, 1, 0]), "hand")
    assert result["auc"] == pytest.approx(0.75)
    assert result["gini"] == pytest.approx(0.5)
    assert result["ks"] == pytest.approx(0.5)


def test_perfect_and_upside_down() -> None:
    perfect = measure(scored([400, 450, 700, 750], [1, 1, 0, 0]), "perfect")
    assert (perfect["auc"], perfect["gini"], perfect["ks"]) == (1, 1, 1)
    upside_down = measure(scored([400, 450, 700, 750], [0, 0, 1, 1]), "upside")
    assert (upside_down["auc"], upside_down["gini"]) == (0, -1)


def test_needs_both_defaults_and_goods() -> None:
    with pytest.raises(ValueError, match="needs defaults and goods"):
        measure(scored([500, 600], [0, 0]), "no defaults")


def test_sealed_view_gives_only_test_and_oot() -> None:
    with pytest.raises(ValueError, match="only"):
        load_final_set(None, "train", load_config())  # stops before any database call


@needs_db
def test_train_bands_match_s11() -> None:
    model = freeze.load_model()
    train = load_set(get_engine(), "train", model["config"])
    scored_train = freeze.score_set(model, train, "train")
    table = band_table(scored_train, band_edges(scored_train["score"]))
    assert table["defaults"].tolist() == S11_TRAIN_BAND_DEFAULTS
    assert measure(scored_train, "train")["auc"] > 0.839  # above the 10-band version
