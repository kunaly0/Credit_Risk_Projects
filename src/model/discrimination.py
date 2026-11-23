"""KS, AUC and Gini for a scored set, plus a score-band table (S12).

A lower score means riskier, so the model works when defaults score low.
KS and AUC are worked out loan by loan, not from 10 bands, so they come out
a little higher than the hand-worked band versions.

Run from the repo root:  python -m src.model.discrimination
"""

from __future__ import annotations

import logging
import sys

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, roc_curve

from src.model import freeze
from src.model.prepare import get_engine, load_set

TARGET = "target"
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


def main() -> int:
    """Score train and validation from the frozen model and print the results."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s"
    )
    try:
        model = freeze.load_model()
        engine = get_engine()
        scored = {
            sample_set: freeze.score_set(
                model, load_set(engine, sample_set, model["config"]), sample_set
            )
            for sample_set in ("train", "validation")
        }
        results = pd.DataFrame([measure(s, name) for name, s in scored.items()])
        edges = band_edges(scored["train"]["score"])
        tables = {name: band_table(s, edges) for name, s in scored.items()}
    except Exception:
        log.exception("discrimination failed")
        return 1
    print(results.round(4).to_string(index=False))
    for name, table in tables.items():
        print(f"\n{name}")
        print(table.round(4).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
