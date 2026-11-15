"""Fit the 9 WoE binnings on train, with the S10 settings (D-063).

The settings come from config/model_config.yaml. Each binner is fitted on
train only; to_woe applies them unchanged to any prepared set.

Run from the repo root:  python -m src.model.binning
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import pandas as pd
from optbinning import OptimalBinning

from src.model.prepare import get_engine, load_config, prepare_sets

log = logging.getLogger(__name__)


def fit_binners(train: pd.DataFrame, cfg: dict[str, Any]) -> dict[str, OptimalBinning]:
    """Fit one binner per feature on train, using that feature's settings."""
    binners = {}
    for feature, kind in cfg["features"].items():
        settings = cfg["binning"][kind]
        binner = OptimalBinning(name=feature, **settings)
        binner.fit(train[feature], train[cfg["target"]])
        binners[feature] = binner
        log.info("%s: fitted with %s settings", feature, kind)
    return binners


def summary_table(binners: dict[str, OptimalBinning]) -> pd.DataFrame:
    """One row per feature: number of bins and IV, read from the binning tables."""
    rows = []
    for feature, binner in binners.items():
        table = binner.binning_table.build()
        rows.append(
            {
                "feature": feature,
                "bins": len(table) - 3,  # minus the Special, Missing and Totals rows
                "iv": table.loc["Totals", "IV"],
            }
        )
    return pd.DataFrame(rows)


def to_woe(
    binners: dict[str, OptimalBinning],
    df: pd.DataFrame,
    cfg: dict[str, Any],
    sample_set: str,
) -> pd.DataFrame:
    """Swap each feature's value for its train bin's WoE. Key and target stay."""
    woe = df[[cfg["key"], cfg["target"]]].copy()
    for feature, binner in binners.items():
        # A category train never saw lands in bin -1 and would get WoE 0
        # (average risk) without any warning, so stop instead - same as rule B.
        unseen = int((binner.transform(df[feature], metric="indices") < 0).sum())
        if unseen:
            raise ValueError(
                f"{sample_set}: {unseen} values of {feature} are in no train bin"
            )
        woe[feature] = binner.transform(df[feature], metric="woe")
    log.info("%s: WoE table %s", sample_set, woe.shape)
    return woe


def main() -> int:
    """Fit on train, convert train and validation to WoE, print a check table."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s"
    )
    try:
        cfg = load_config()
        train, validation, _ = prepare_sets(get_engine(), cfg)
        binners = fit_binners(train, cfg)
        woe_train = to_woe(binners, train, cfg, "train")
        woe_validation = to_woe(binners, validation, cfg, "validation")
    except Exception:
        log.exception("binning failed")
        return 1
    features = list(binners)
    summary = summary_table(binners)
    summary["woe_values_train"] = woe_train[features].nunique().to_numpy()
    summary["woe_values_val"] = woe_validation[features].nunique().to_numpy()
    print(summary.to_string(index=False, float_format="%.2f"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
