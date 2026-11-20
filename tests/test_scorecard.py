"""Check the scorecard maths and the hand-scored loan from S11.

The maths tests need no database and run everywhere, GitHub CI included.
The loan tests need the local database and skip themselves where there is none.
"""

import math
import os

import pytest
import statsmodels.api as sm
from dotenv import load_dotenv

from src.model.binning import fit_binners, to_woe
from src.model.prepare import get_engine, load_config, prepare_sets
from src.model.scorecard import fit_model, scale_numbers, score_loans, score_to_pd

load_dotenv()
needs_db = pytest.mark.skipif(
    not os.getenv("DB_HOST"), reason="needs the local credit_risk database"
)

HAND_SCORED_LOAN = "F05Q10000006"  # scored by hand in Excel, 18 Nov 2026


@pytest.mark.parametrize(
    ("score", "odds"), [(600, 50), (620, 100), (580, 25), (640, 200)]
)
def test_ladder(score: int, odds: int) -> None:
    assert score_to_pd(score, load_config()) == pytest.approx(1 / (1 + odds))


@pytest.mark.parametrize("tally", [-6.0, -3.646, -1.0905, 0.0])
def test_score_and_pd_agree(tally: float) -> None:
    cfg = load_config()
    factor, offset = scale_numbers(cfg)
    score = offset - factor * tally
    assert score_to_pd(score, cfg) == pytest.approx(1 / (1 + math.exp(-tally)))


@pytest.fixture(scope="module")
def scored_train():
    """Fit on train and score every train loan, once for the tests below."""
    cfg = load_config()
    train, _, _ = prepare_sets(get_engine(), cfg)
    binners = fit_binners(train, cfg)
    woe_train = to_woe(binners, train, cfg, "train")
    model = fit_model(woe_train, cfg["model_features"], cfg)
    return cfg, model, woe_train, score_loans(model, woe_train, cfg)


@needs_db
def test_hand_scored_loan(scored_train) -> None:
    _, _, _, scored = scored_train
    loan = scored.set_index("loan_sequence_number").loc[HAND_SCORED_LOAN]
    assert loan["score"] == pytest.approx(518.59, abs=0.01)
    assert loan["pd"] == pytest.approx(0.2515, abs=0.0001)


@needs_db
def test_pd_matches_the_model(scored_train) -> None:
    cfg, model, woe_train, scored = scored_train
    x = sm.add_constant(woe_train[cfg["model_features"]], has_constant="add")
    assert scored["pd"].to_numpy() == pytest.approx(model.predict(x).to_numpy())
    assert score_to_pd(scored["score"], cfg).to_numpy() == pytest.approx(
        scored["pd"].to_numpy()
    )
