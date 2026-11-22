"""Fit the logistic regression scorecard on the train WoE values (S11).

The model learns one intercept and one coefficient per WoE feature, on
train only. Positive WoE means safer, so every coefficient should be
negative; a positive one points to overlap between features.

Run from the repo root:  python -m src.model.scorecard
"""

from __future__ import annotations

import logging
import math
import sys
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm
from optbinning import OptimalBinning
from statsmodels.discrete.discrete_model import BinaryResultsWrapper

from src.model.binning import fit_binners, to_woe
from src.model.prepare import REPO_ROOT, get_engine, load_config, prepare_sets

SCORECARD_CSV = REPO_ROOT / "docs" / "s11_scorecard.csv"

log = logging.getLogger(__name__)


def fit_model(
    woe_train: pd.DataFrame, features: list[str], cfg: dict[str, Any]
) -> BinaryResultsWrapper:
    """Logistic regression of default on the WoE features, fitted on train only."""
    x = sm.add_constant(woe_train[features])  # a column of 1s for the intercept
    model = sm.Logit(woe_train[cfg["target"]], x).fit(disp=0)
    if not model.mle_retvals["converged"]:
        raise RuntimeError("logistic regression did not converge")
    log.info("fitted on %d loans with %d features", len(woe_train), len(features))
    return model


def coefficient_table(model: BinaryResultsWrapper) -> pd.DataFrame:
    """Coefficient, standard error and p-value per feature, and the sign check."""
    table = pd.DataFrame(
        {"coef": model.params, "std_err": model.bse, "p_value": model.pvalues}
    ).drop(index="const")
    table["negative"] = table["coef"] < 0
    return table


def scale_numbers(cfg: dict[str, Any]) -> tuple[float, float]:
    """Factor and offset from the base score, base odds and PDO (D-065)."""
    scaling = cfg["scaling"]
    factor = scaling["pdo"] / math.log(2)
    offset = scaling["base_score"] - factor * math.log(scaling["base_odds"])
    return factor, offset


def points_table(
    binners: dict[str, OptimalBinning],
    model: BinaryResultsWrapper,
    cfg: dict[str, Any],
) -> pd.DataFrame:
    """Points for every bin of every model feature.

    Each feature gets an equal share of the starting score, plus or minus
    its bin's part of the tally turned into points. An average loan (WoE 0
    in every feature) scores offset - factor * intercept.
    """
    factor, offset = scale_numbers(cfg)
    features = cfg["model_features"]
    share = (offset - factor * model.params["const"]) / len(features)
    rows = []
    for feature in features:
        # The last three rows of a binning table are Special, Missing and Totals
        bins = binners[feature].binning_table.build().iloc[:-3]
        coef = model.params[feature]
        for label, woe in zip(bins["Bin"], bins["WoE"]):
            if not isinstance(label, str):  # a categorical bin holds a list of values
                label = ", ".join(str(value) for value in label)
            points = share - factor * coef * float(woe)
            rows.append(
                {
                    "feature": feature,
                    "bin": label,
                    "woe": float(woe),
                    "points": points,
                }
            )
    return pd.DataFrame(rows)


def score_loans(
    model: BinaryResultsWrapper, woe: pd.DataFrame, cfg: dict[str, Any]
) -> pd.DataFrame:
    """Score and PD for every loan in a WoE table, from the train-fitted model."""
    return score_with_params(model.params, woe, cfg)


def score_with_params(
    params: pd.Series, woe: pd.DataFrame, cfg: dict[str, Any]
) -> pd.DataFrame:
    """Score and PD from an intercept and coefficients - fitted now or frozen.

    The one place the scoring sum is written, so a refit and the frozen
    model (D-066) can never score with two different formulas.
    """
    factor, offset = scale_numbers(cfg)
    # has_constant="add": with one loan every column looks constant, and the
    # default would then skip the intercept column without a word.
    x = sm.add_constant(woe[cfg["model_features"]], has_constant="add")
    tally = x.dot(params)  # matched by column name
    scored = woe[[cfg["key"], cfg["target"]]].copy()
    scored["score"] = offset - factor * tally
    scored["pd"] = 1 / (1 + np.exp(-tally))
    return scored


def score_to_pd(score: float | pd.Series, cfg: dict[str, Any]) -> float | pd.Series:
    """Turn a score back into a PD with the ladder (D-065)."""
    scaling = cfg["scaling"]
    steps = (score - scaling["base_score"]) / scaling["pdo"]
    odds = scaling["base_odds"] * 2**steps
    return 1 / (1 + odds)


def main() -> int:
    """Fit on train, build the points table, save it, print a summary."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s"
    )
    try:
        cfg = load_config()
        train, _, _ = prepare_sets(get_engine(), cfg)
        binners = fit_binners(train, cfg)
        woe_train = to_woe(binners, train, cfg, "train")
        model = fit_model(woe_train, cfg["model_features"], cfg)
        points = points_table(binners, model, cfg)
        points.to_csv(SCORECARD_CSV, index=False)
    except Exception:
        log.exception("scorecard build failed")
        return 1
    print(f"intercept {model.params['const']:.3f}")
    print(coefficient_table(model).round(4).to_string())
    by_feature = points.groupby("feature", sort=False)["points"].agg(["min", "max"])
    by_feature["spread"] = by_feature["max"] - by_feature["min"]
    print(by_feature.round(1).to_string())
    print(f"score range {by_feature['min'].sum():.0f} to {by_feature['max'].sum():.0f}")
    log.info("points table saved to %s", SCORECARD_CSV)
    return 0


if __name__ == "__main__":
    sys.exit(main())
