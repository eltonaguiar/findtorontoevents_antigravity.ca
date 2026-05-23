# -*- coding: utf-8 -*-
"""Mercury 2 — XGBoost ensemble (3 learners: conservative, aggressive, balanced)."""

import logging, joblib, numpy as np, pandas as pd
import xgboost as xgb
from .config import ENSEMBLE_PARAMS, FEATURE_COLS, MODEL_DIR

log = logging.getLogger("mercury2.ensemble")


def train_ensemble(X_train: pd.DataFrame, y_train: pd.Series,
                   X_test: pd.DataFrame, y_test: pd.Series) -> dict:
    """Train 3 XGBoost classifiers and return dict of models."""
    # Compute scale_pos_weight from actual class ratios
    n_neg = int((y_train == 0).sum())
    n_pos = int((y_train == 1).sum())
    spw = max(1.0, n_neg / max(1, n_pos))
    log.info(f"  Class balance: neg={n_neg}, pos={n_pos}, scale_pos_weight={spw:.2f}")

    models = {}
    for name, params in ENSEMBLE_PARAMS.items():
        model = xgb.XGBClassifier(
            **params,
            scale_pos_weight=spw,
            use_label_encoder=False,
            eval_metric="logloss",
            verbosity=0,
        )
        model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
        acc = (model.predict(X_test) == y_test).mean()
        log.info(f"  [{name}] accuracy={acc:.3f}")
        models[name] = model
    return models


def save_ensemble(models: dict, prefix: str = "ensemble"):
    """Save all 3 models to disk."""
    for name, model in models.items():
        path = MODEL_DIR / f"{prefix}_{name}.joblib"
        joblib.dump(model, path)
        log.info(f"  Saved {path.name}")


def load_ensemble(prefix: str = "ensemble") -> dict | None:
    """Load pre-trained ensemble from disk. Returns None if not found."""
    models = {}
    for name in ENSEMBLE_PARAMS:
        path = MODEL_DIR / f"{prefix}_{name}.joblib"
        if not path.exists():
            log.warning(f"  Model not found: {path.name}")
            return None
        models[name] = joblib.load(path)
    log.info(f"  Loaded {len(models)} ensemble models")
    return models


def ensemble_predict(models: dict, X: pd.DataFrame) -> np.ndarray:
    """Average probability from all 3 learners. Returns array of probabilities."""
    # Runtime scanner input can come from a mixed-type Series row (dtype=object).
    # Coerce all features to numeric so XGBoost never receives object dtypes.
    X = X.copy()
    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors="coerce")
    X = X.fillna(0.0)

    probs = []
    for name, model in models.items():
        p = model.predict_proba(X)[:, 1]
        probs.append(p)
    return np.mean(probs, axis=0)
