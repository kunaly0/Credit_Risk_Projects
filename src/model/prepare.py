"""Prepare a sample set for the PD scorecard (S11).

Every set goes through the same steps in the same order: merge channel
(D-062), check credit scores are in range, fill blanks with values learned
on train only (D-061), then confirm no blank is left in the 9 features.

Run from the repo root:  python -m src.model.prepare
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import yaml
from dotenv import load_dotenv
from sqlalchemy import URL, Engine, create_engine, text

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "config" / "model_config.yaml"
SETS = ("train", "validation")  # the only sets in pd_features_build

log = logging.getLogger(__name__)


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    """Read the model config. Called inside functions only (D-038)."""
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def require_env(name: str) -> str:
    """Return a setting from .env, or stop with a clear error."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} missing from .env")
    return value


def get_engine() -> Engine:
    """SQLAlchemy engine for the credit_risk database - what pandas prefers."""
    load_dotenv()
    url = URL.create(
        "postgresql+psycopg",
        username=require_env("DB_USER"),
        password=require_env("DB_PASSWORD"),
        host=require_env("DB_HOST"),
        port=int(require_env("DB_PORT")),
        database=require_env("DB_NAME"),
    )
    return create_engine(url)


def load_set(engine: Engine, sample_set: str, cfg: dict[str, Any]) -> pd.DataFrame:
    """Read one set: key, target and the 9 features, always in the same order."""
    if sample_set not in SETS:
        raise ValueError(f"{sample_set!r} is not readable here - only {SETS}")
    features = list(cfg["features"])  # the dict's keys are the 9 feature names
    columns = ", ".join([cfg["key"], cfg["target"], *features])
    query = text(
        f"SELECT {columns} FROM {cfg['source_view']} "
        f"WHERE sample_set = :sample_set ORDER BY {cfg['key']}"
    )
    df = pd.read_sql(query, engine, params={"sample_set": sample_set})
    log.info("%s: %d loans read", sample_set, len(df))
    return df


def merge_channel(df: pd.DataFrame, cfg: dict[str, Any]) -> pd.DataFrame:
    """D-062: broker, correspondent and unspecified third party become TP."""
    df = df.copy()
    df["channel"] = df["channel"].replace(cfg["channel_merge"])
    return df


def check_credit_score_range(
    df: pd.DataFrame, cfg: dict[str, Any], sample_set: str
) -> None:
    """Stop if any credit score is outside the valid range. Blanks pass here."""
    low, high = cfg["credit_score_range"]
    score = df["credit_score"]
    outside = score.notna() & ((score < low) | (score > high))
    if outside.any():
        raise ValueError(
            f"{sample_set}: {int(outside.sum())} credit scores outside "
            f"{low}-{high} - fix the data before these loans are scored"
        )


def learn_fill_values(train: pd.DataFrame, cfg: dict[str, Any]) -> dict[str, float]:
    """D-061: the train median of each column listed in the config. Train only."""
    medians = train[cfg["fill_with_train_median"]].median()
    fills = {column: float(value) for column, value in medians.items()}
    log.info("fill values learned on train: %s", fills)
    return fills


def fill_blanks(
    df: pd.DataFrame, fills: dict[str, float], cfg: dict[str, Any], sample_set: str
) -> pd.DataFrame:
    """Fill with the train values, then stop if anything is still blank."""
    before = df[list(fills)].isna().sum()
    df = df.fillna(fills)
    log.info("%s: blanks filled %s", sample_set, before[before > 0].to_dict())
    left = df[[cfg["target"], *cfg["features"]]].isna().sum()
    if left.any():
        raise ValueError(f"{sample_set}: blanks with no fill rule {left[left > 0]}")
    return df


def prepare_set(
    df: pd.DataFrame, fills: dict[str, float], cfg: dict[str, Any], sample_set: str
) -> pd.DataFrame:
    """The same steps for every set, in the same order."""
    df = merge_channel(df, cfg)
    check_credit_score_range(df, cfg, sample_set)
    return fill_blanks(df, fills, cfg, sample_set)


def prepare_sets(
    engine: Engine, cfg: dict[str, Any]
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float]]:
    """Train and validation, prepared alike, with fills learned on train only."""
    train_raw = load_set(engine, "train", cfg)
    # Checked before learning, so a bad score can never move the median
    check_credit_score_range(train_raw, cfg, "train")
    fills = learn_fill_values(train_raw, cfg)
    train = prepare_set(train_raw, fills, cfg, "train")
    validation_raw = load_set(engine, "validation", cfg)
    validation = prepare_set(validation_raw, fills, cfg, "validation")
    return train, validation, fills


def main() -> int:
    """Prepare both sets and report their shapes. 0 on success, 1 on failure."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s"
    )
    try:
        cfg = load_config()
        train, validation, _ = prepare_sets(get_engine(), cfg)
    except Exception:
        log.exception("preparation failed")
        return 1
    log.info("train %s, validation %s", train.shape, validation.shape)
    log.info("channel on train: %s", train["channel"].value_counts().to_dict())
    return 0


if __name__ == "__main__":
    sys.exit(main())
