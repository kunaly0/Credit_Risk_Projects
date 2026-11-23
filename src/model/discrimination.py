"""KS, AUC and Gini for a scored set, plus a score-band table (S12).

A lower score means riskier, so the model works when defaults score low.
KS and AUC are worked out loan by loan, not from 10 bands, so they come out
a little higher than the hand-worked band versions.

Train and validation come from pd_features_build; test and 2017 (oot) from
the sealed pd_features_final, read only to grade the frozen model. Results go
to docs/s12_discrimination.csv and docs/s12_band_tables.csv.

Run from the repo root:  python -m src.model.discrimination
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, roc_curve

from src.model import freeze
from src.model.prepare import REPO_ROOT, get_engine, load_final_set, load_set

TARGET = "target"
RESULTS_CSV = REPO_ROOT / "docs" / "s12_discrimination.csv"
BANDS_CSV = REPO_ROOT / "docs" / "s12_band_tables.csv"
N_BANDS = 10

log = logging.getLogger(__name__)


def check_both_kinds(scored: pd.DataFrame, sample_set: str) -> None:
    """KS and AUC compare defaults with goods, so a set needs both."""
    kinds = scored[TARGET].nunique()
    if kinds != 2:
        raise ValueError(f"{sample_set}: needs defaults and goods, found {kinds} kind")


def measure(scored: pd.DataFrame, sample_set: str) -> dict[str, float | int | str]:
    """Loans, defaults, KS, AUC and Gini for one scored set."""
    check_both_kinds(scored, sample_set)
    risk = -scored["score"]  # flip: sklearn expects higher = more likely to default
    goods_caught, defaults_caught, _ = roc_curve(scored[TARGET], risk)
    auc = roc_auc_score(scored[TARGET], risk)
    return {
        "set": sample_set,
        "loans": len(scored),
        "defaults": int(scored[TARGET].sum()),
        "default_rate": float(scored[TARGET].mean()),
        "ks": float(np.max(defaults_caught - goods_caught)),
        "auc": float(auc),
        "gini": float(2 * auc - 1),
    }


def band_edges(train_scores: pd.Series, n_bands: int = N_BANDS) -> np.ndarray:
    """Cut points for equal-sized score bands, set on train only."""
    inner = train_scores.quantile(np.linspace(0, 1, n_bands + 1)[1:-1]).to_numpy()
    return np.concatenate([[-np.inf], inner, [np.inf]])


def band_table(scored: pd.DataFrame, edges: np.ndarray) -> pd.DataFrame:
    """Loans and defaults per band, worst band first, with the two running totals."""
    bands = pd.cut(scored["score"], edges)
    table = scored.groupby(bands, observed=False)[TARGET].agg(
        loans="count", defaults="sum"
    )
    table["goods"] = table["loans"] - table["defaults"]
    table["bad_rate"] = table["defaults"] / table["loans"]
    table["defaults_caught"] = table["defaults"].cumsum() / table["defaults"].sum()
    table["goods_caught"] = table["goods"].cumsum() / table["goods"].sum()
    table["gap"] = table["defaults_caught"] - table["goods_caught"]
    return table


def score_all(model: dict[str, Any]) -> dict[str, pd.DataFrame]:
    """Score all four sets from the frozen model - the same pieces for every set."""
    engine = get_engine()
    cfg = model["config"]
    raw = {name: load_set(engine, name, cfg) for name in ("train", "validation")}
    raw |= {name: load_final_set(engine, name, cfg) for name in ("test", "oot")}
    return {name: freeze.score_set(model, df, name) for name, df in raw.items()}


def main() -> int:
    """Grade the frozen model on all four sets, save and print the results."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s"
    )
    try:
        scored = score_all(freeze.load_model())
        results = pd.DataFrame([measure(s, name) for name, s in scored.items()])
        edges = band_edges(scored["train"]["score"])  # band edges set on train only
        tables = pd.concat(
            {name: band_table(s, edges) for name, s in scored.items()}, names=["set"]
        )
        results.to_csv(RESULTS_CSV, index=False)
        tables.reset_index().astype({"score": str}).to_csv(BANDS_CSV, index=False)
    except Exception:
        log.exception("discrimination failed")
        return 1
    print(results.round(4).to_string(index=False))
    for name in ("test", "oot"):
        print(f"\n{name}")
        print(tables.loc[name].round(4).to_string())
    log.info("saved %s and %s", RESULTS_CSV.name, BANDS_CSV.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
