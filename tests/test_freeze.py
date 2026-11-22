"""Check the frozen scorecard v1 (D-066).

The first four tests read only the saved files and run everywhere, GitHub CI
included. The last two need the local database and skip where there is none.
"""

import json
import os
import pickle

import pytest
from dotenv import load_dotenv

from src.model import freeze
from src.model.binning import fit_binners, to_woe
from src.model.prepare import get_engine, load_config, load_set, prepare_sets
from src.model.scorecard import fit_model, score_loans

load_dotenv()
needs_db = pytest.mark.skipif(
    not os.getenv("DB_HOST"), reason="needs the local credit_risk database"
)

HAND_SCORED_LOAN = "F05Q10000006"  # scored by hand in Excel, 18 Nov 2026


def read_card() -> dict:
    path = freeze.MODEL_DIR / f"{freeze.MODEL_NAME}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_card_is_the_s11_model() -> None:
    card = read_card()
    coefficients = card["coefficients"]
    assert card["train_loans"] == 131_366
    assert card["train_defaults"] == 3_456
    assert coefficients["const"] == pytest.approx(-3.646, abs=0.0005)
    assert coefficients["credit_score"] == pytest.approx(-0.848, abs=0.0005)
    assert list(coefficients)[1:] == load_config()["model_features"]
    assert all(value < 0 for value in coefficients.values())


def test_frozen_model_loads_and_matches_its_card() -> None:
    model = freeze.load_model()
    assert model["params"] == read_card()["coefficients"]
    assert list(model["binners"]) == list(model["config"]["features"])


def test_save_never_overwrites(tmp_path) -> None:
    freeze.save_model({"name": "test"}, {"name": "test"}, tmp_path)
    with pytest.raises(FileExistsError):
        freeze.save_model({"name": "test"}, {"name": "test"}, tmp_path)


def test_load_stops_on_other_package_versions(tmp_path) -> None:
    card = {"packages": {"pandas": "0.0.1"}}
    (tmp_path / f"{freeze.MODEL_NAME}.json").write_text(json.dumps(card))
    (tmp_path / f"{freeze.MODEL_NAME}.pkl").write_bytes(pickle.dumps({}))
    with pytest.raises(RuntimeError, match="differ"):
        freeze.load_model(tmp_path)


@needs_db
def test_frozen_scores_the_hand_scored_loan() -> None:
    model = freeze.load_model()
    train_raw = load_set(get_engine(), "train", model["config"])
    scored = freeze.score_set(model, train_raw, "train")
    loan = scored.set_index("loan_sequence_number").loc[HAND_SCORED_LOAN]
    assert loan["score"] == pytest.approx(518.59, abs=0.01)
    assert loan["pd"] == pytest.approx(0.2515, abs=0.0001)


@needs_db
def test_frozen_equals_refit_on_every_validation_loan() -> None:
    cfg = load_config()
    engine = get_engine()
    train, validation, _ = prepare_sets(engine, cfg)
    binners = fit_binners(train, cfg)
    refit = fit_model(to_woe(binners, train, cfg, "train"), cfg["model_features"], cfg)
    by_refit = score_loans(refit, to_woe(binners, validation, cfg, "validation"), cfg)

    model = freeze.load_model()
    validation_raw = load_set(engine, "validation", model["config"])
    by_frozen = freeze.score_set(model, validation_raw, "validation")

    assert len(by_frozen) == 43_790
    assert (by_frozen["loan_sequence_number"] == by_refit["loan_sequence_number"]).all()
    assert by_frozen["score"].to_numpy() == pytest.approx(by_refit["score"].to_numpy())
