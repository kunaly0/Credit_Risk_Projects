"""Freeze the PD scorecard once and score any set from the frozen copy (D-066).

The model is fitted on train exactly as in S11, then saved with its config,
train fill values, binners and coefficients. Every later step loads this
file instead of refitting, so the model that was measured is the model
that is used. A refit means a new version, never an overwrite.

Run from the repo root, with every change committed first:
    python -m src.model.freeze
"""

from __future__ import annotations

import json
import logging
import pickle
import platform
import subprocess
import sys
from datetime import date
from importlib.metadata import version
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import Engine

from src.model.binning import fit_binners, to_woe
from src.model.prepare import (
    REPO_ROOT,
    get_engine,
    load_config,
    prepare_set,
    prepare_sets,
)
from src.model.scorecard import fit_model, score_with_params

MODEL_NAME = "pd_scorecard_v1"
MODEL_DIR = REPO_ROOT / "models"
PINNED = ("pandas", "optbinning", "scikit-learn", "statsmodels")

log = logging.getLogger(__name__)


def git_state() -> tuple[str, bool]:
    """Short commit of the code in use, and whether anything is uncommitted."""

    def git(*args: str) -> str:
        result = subprocess.run(
            ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True
        )
        return result.stdout.strip()

    return git("rev-parse", "--short=7", "HEAD"), bool(git("status", "--porcelain"))


def build_model(
    engine: Engine, cfg: dict[str, Any]
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Fit on train as in S11. Returns the pieces to save, and train for the card."""
    train, _, fills = prepare_sets(engine, cfg)
    binners = fit_binners(train, cfg)
    woe_train = to_woe(binners, train, cfg, "train")
    fitted = fit_model(woe_train, cfg["model_features"], cfg)
    model = {
        "name": MODEL_NAME,
        "config": cfg,  # a copy, so a later config edit cannot change v1
        "fills": fills,
        "binners": binners,
        # plain numbers: the statsmodels result would carry every train row
        "params": {name: float(value) for name, value in fitted.params.items()},
    }
    return model, train


def model_card(
    model: dict[str, Any], train: pd.DataFrame, commit: str
) -> dict[str, Any]:
    """The label saved next to the model: what it is, how and when it was made."""
    cfg = model["config"]
    return {
        "name": MODEL_NAME,
        "fitted_on": date.today().isoformat(),
        "git_commit": commit,
        "train_loans": len(train),
        "train_defaults": int(train[cfg["target"]].sum()),
        "fills": model["fills"],
        "coefficients": model["params"],
        "scaling": cfg["scaling"],
        "python": platform.python_version(),
        "packages": {package: version(package) for package in PINNED},
    }


def save_model(
    model: dict[str, Any], card: dict[str, Any], folder: Path = MODEL_DIR
) -> Path:
    """Write the model and its card. Never overwrites a saved version."""
    folder.mkdir(exist_ok=True)
    model_path = folder / f"{MODEL_NAME}.pkl"
    if model_path.exists():
        raise FileExistsError(f"{model_path} exists - a refit is a new version")
    with model_path.open("wb") as handle:
        pickle.dump(model, handle)
    card_path = folder / f"{MODEL_NAME}.json"
    card_path.write_text(json.dumps(card, indent=2) + "\n", encoding="utf-8")
    return model_path


def load_model(folder: Path = MODEL_DIR) -> dict[str, Any]:
    """Load the frozen model, after checking the packages match its card."""
    card_path = folder / f"{MODEL_NAME}.json"
    card = json.loads(card_path.read_text(encoding="utf-8"))
    installed = {package: version(package) for package in PINNED}
    if installed != card["packages"]:
        raise RuntimeError(
            f"packages {installed} differ from the frozen model's {card['packages']}"
        )
    with (folder / f"{MODEL_NAME}.pkl").open("rb") as handle:
        return pickle.load(handle)  # only this project's own file (D-066)


def score_set(
    model: dict[str, Any], raw: pd.DataFrame, sample_set: str
) -> pd.DataFrame:
    """Prepare, convert to WoE and score one set, using only the frozen pieces."""
    cfg = model["config"]
    prepared = prepare_set(raw, model["fills"], cfg, sample_set)
    woe = to_woe(model["binners"], prepared, cfg, sample_set)
    return score_with_params(pd.Series(model["params"]), woe, cfg)


def main() -> int:
    """Fit on train, save v1 and its card. 0 on success, 1 on failure."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s"
    )
    try:
        commit, dirty = git_state()
        if dirty:
            raise RuntimeError(
                "uncommitted changes - commit first, so the card's "
                "commit is the code that built the model"
            )
        cfg = load_config()
        model, train = build_model(get_engine(), cfg)
        card = model_card(model, train, commit)
        path = save_model(model, card)
    except Exception:
        log.exception("freeze failed")
        return 1
    print(json.dumps(card, indent=2))
    log.info("saved %s (%.0f KB)", path, path.stat().st_size / 1024)
    return 0


if __name__ == "__main__":
    sys.exit(main())
