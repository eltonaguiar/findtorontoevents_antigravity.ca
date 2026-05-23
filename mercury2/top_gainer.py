# -*- coding: utf-8 -*-
"""Mercury 2 — Daily top-gainer regressor (LightGBM)."""

import logging, joblib, numpy as np, pandas as pd

log = logging.getLogger("mercury2.top_gainer")

try:
    import lightgbm as lgb
    HAS_LGB = True
except ImportError:
    HAS_LGB = False
    log.warning("LightGBM not installed — top-gainer regressor disabled")

from .config import TOP_GAINER_PARAMS, MODEL_DIR, TOP_K, FEATURE_COLS

# Extended features for top-gainer (12 base + funding_std_30d)
TOP_GAINER_FEATURES = FEATURE_COLS + ["funding_std_30d"]


def train_top_gainer(X_train: pd.DataFrame, y_train: pd.Series,
                     X_test: pd.DataFrame, y_test: pd.Series):
    """Train LightGBM regressor for next-day return prediction."""
    if not HAS_LGB:
        log.warning("  LightGBM not available, skipping top-gainer training")
        return None

    reg = lgb.LGBMRegressor(**TOP_GAINER_PARAMS)
    reg.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        callbacks=[lgb.early_stopping(30, verbose=False), lgb.log_evaluation(0)],
    )

    # Validation: Precision@k
    pred = reg.predict(X_test)
    k = TOP_K
    n = len(y_test)
    if n >= k:
        true_top = set(np.argsort(y_test.values)[-k:])
        pred_top = set(np.argsort(pred)[-k:])
        precision_k = len(true_top & pred_top) / k
        log.info(f"  [top-gainer] Precision@{k} = {precision_k:.1%}")
    else:
        log.warning(f"  [top-gainer] Not enough test data ({n} < {k})")

    return reg


def save_top_gainer(model, name: str = "top_gainer"):
    if model is None:
        return
    path = MODEL_DIR / f"{name}.joblib"
    joblib.dump(model, path)
    log.info(f"  Saved {path.name}")


def load_top_gainer(name: str = "top_gainer"):
    path = MODEL_DIR / f"{name}.joblib"
    if not path.exists():
        log.warning(f"  Top-gainer model not found: {path.name}")
        return None
    model = joblib.load(path)
    log.info(f"  Loaded top-gainer model")
    return model


def predict_top_gainers(model, df: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    """Predict next-day returns and return top-k rows."""
    if model is None:
        return pd.DataFrame()

    # Ensure all features exist
    for f in features:
        if f not in df.columns:
            df[f] = 0.0

    X = df[features].copy()
    # Ensure all features are numeric (API can return strings)
    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors="coerce")
    X = X.fillna(0)
    df = df.copy()
    raw_pred = model.predict(X)
    # Sanity cap: match training label clip range of [-20%, +20%]
    df["pred_next_ret"] = np.clip(raw_pred, -0.20, 0.20)
    top = df.nlargest(TOP_K, "pred_next_ret")
    return top
