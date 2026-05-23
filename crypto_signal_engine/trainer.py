"""Model training, validation (DSR/PSR), and persistence.

Models:
  3x XGBoost classifiers (conservative/aggressive/balanced) — day-trade ensemble
  1x LightGBM regressor — top-gainer next-day return predictor

Validation:
  DSR (Deflated Sharpe Ratio) — Bailey & Lopez de Prado 2014
  PSR (Probabilistic Sharpe Ratio) — probability true Sharpe > target
"""
import json
import logging
import numpy as np
import pandas as pd
import xgboost as xgb
import lightgbm as lgb
from scipy import stats
from . import config

logger = logging.getLogger(__name__)


def compute_cost(symbol):
    """Total round-trip cost = fee + 2x slippage."""
    sl = config.SLIPPAGE_MAP.get(symbol, config.DEFAULT_SLIPPAGE)
    return config.ROUND_TRIP_FEE + 2 * sl


def deflated_sharpe_ratio(probs):
    """DSR — probability that true Sharpe > 0.

    Based on Bailey & Lopez de Prado (2014). Uses the model's predicted
    probabilities to estimate a Sharpe ratio, then tests whether it's
    statistically significantly greater than zero.
    """
    p_mean = np.mean(probs)
    if p_mean <= 0 or p_mean >= 1:
        return 0.0
    sharpe_hat = (p_mean - 0.5) / np.sqrt(p_mean * (1 - p_mean))
    se = np.sqrt((1 + sharpe_hat ** 2 / 2) / max(1, len(probs)))
    return float(stats.norm.cdf(sharpe_hat / se))


def probabilistic_sharpe_ratio(sharpe_hat, n, target=None):
    """PSR — probability that true Sharpe exceeds the target.

    A PSR of 0.75 means 75% confidence that the model's true Sharpe
    ratio is above the target (default 2.0).
    """
    if target is None:
        target = config.TARGET_SR
    se = np.sqrt((1 + sharpe_hat ** 2 / 2) / max(1, n))
    return float(stats.norm.cdf((sharpe_hat - target) / se))


def train_xgb_ensemble(df, features=None):
    """Train 3 XGBoost classifiers with walk-forward split.

    Returns: (models_dict, features_list, validation_dict)
    """
    if features is None:
        features = config.FEATURES

    # Only use features that exist in the DataFrame
    available = [f for f in features if f in df.columns]
    X = df[available]
    y = df["label"]

    # Walk-forward: 80% train, 20% test with 20-bar purge gap
    split = int(0.8 * len(df))
    purge = 20
    X_train = X.iloc[:split]
    y_train = y.iloc[:split]
    X_test = X.iloc[split + purge:]
    y_test = y.iloc[split + purge:]

    if len(X_test) < 50:
        logger.warning(f"Test set too small ({len(X_test)} rows), using 70/30 split")
        split = int(0.7 * len(df))
        X_train = X.iloc[:split]
        y_train = y.iloc[:split]
        X_test = X.iloc[split + purge:]
        y_test = y.iloc[split + purge:]

    # Class weighting to balance bullish/bearish bias in imbalanced markets
    n_pos = int(y_train.sum())
    n_neg = len(y_train) - n_pos
    scale_pos = n_neg / n_pos if n_pos > 0 else 1.0
    logger.info(f"  Class weighting: scale_pos_weight={scale_pos:.3f} "
                f"(pos={n_pos}, neg={n_neg})")

    models = {}
    for name, params in config.XGB_CONFIGS.items():
        model = xgb.XGBClassifier(
            **params,
            scale_pos_weight=scale_pos,
            use_label_encoder=False,
            eval_metric="logloss",
            early_stopping_rounds=config.EARLY_STOPPING_ROUNDS,
            verbosity=0,
        )
        model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False,
        )
        models[name] = model
        train_acc = model.score(X_train, y_train)
        test_acc = model.score(X_test, y_test)
        overfit = train_acc - test_acc
        logger.info(f"  {name}: train={train_acc:.3f}, test={test_acc:.3f}, "
                     f"overfit_gap={overfit:.3f}, best_iter={model.best_iteration}")

    # Ensemble probability on test set
    probs = np.mean(
        [m.predict_proba(X_test)[:, 1] for m in models.values()],
        axis=0,
    )

    # Validation metrics
    dsr = deflated_sharpe_ratio(probs)
    p_mean = float(np.mean(probs))
    sharpe_hat = (p_mean - 0.5) / np.sqrt(p_mean * (1 - p_mean)) if 0 < p_mean < 1 else 0
    psr_val = probabilistic_sharpe_ratio(sharpe_hat, len(probs))

    validation = {
        "dsr": round(dsr, 4),
        "psr": round(psr_val, 4),
        "sharpe": round(sharpe_hat, 4),
        "prob_mean": round(p_mean, 4),
        "train_size": len(X_train),
        "test_size": len(X_test),
        "label_balance": round(float(y.mean()), 4),
        "dsr_pass": dsr >= config.DSR_GATE,
        "psr_pass": psr_val >= config.PSR_GATE,
    }

    status = "PASS" if validation["dsr_pass"] else "FAIL"
    logger.info(f"Validation: DSR={dsr:.3f} ({status}), PSR={psr_val:.3f}, Sharpe={sharpe_hat:.2f}")

    return models, available, validation


def train_top_gainer_regressor(df, features=None):
    """Train LightGBM regressor for next-day return prediction.

    Returns: (model, features_list, precision_at_5)
    """
    if features is None:
        features = config.TOP_GAINER_FEATURES

    df = df.copy()
    if "pair_id" not in df.columns:
        df["pair_id"] = pd.factorize(df["symbol"])[0]

    # Target: next 24h return
    df["next_ret"] = df["close"].shift(-24) / df["close"] - 1
    df = df.dropna(subset=["next_ret"])

    available = [f for f in features if f in df.columns]
    X = df[available]
    y = df["next_ret"]

    split = int(0.8 * len(df))
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]

    reg = lgb.LGBMRegressor(**config.LGB_CONFIG, verbosity=-1)
    reg.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        callbacks=[lgb.early_stopping(30, verbose=False)],
    )

    # Precision@5 sanity check
    pred = reg.predict(X_test)
    k = min(5, len(y_test))
    true_top = set(np.argsort(y_test.values)[-k:])
    pred_top = set(np.argsort(pred)[-k:])
    precision_k = len(true_top & pred_top) / k if k > 0 else 0

    logger.info(f"Top-gainer regressor: Precision@{k} = {precision_k:.0%}")

    return reg, available, precision_k


def save_models(xgb_models, lgb_model=None):
    """Save models to disk."""
    config.MODEL_DIR.mkdir(parents=True, exist_ok=True)
    for name, model in xgb_models.items():
        path = config.MODEL_DIR / f"xgb_{name}.json"
        model.save_model(str(path))
        logger.info(f"Saved {path.name}")
    if lgb_model is not None:
        path = config.MODEL_DIR / "lgb_top_gainer.txt"
        lgb_model.booster_.save_model(str(path))
        logger.info(f"Saved {path.name}")


def load_models():
    """Load saved models. Returns (xgb_dict, lgb_booster) or (None, None)."""
    xgb_models = {}
    for name in config.XGB_CONFIGS:
        path = config.MODEL_DIR / f"xgb_{name}.json"
        if not path.exists():
            logger.warning(f"Model not found: {path}")
            return None, None
        model = xgb.XGBClassifier()
        model.load_model(str(path))
        xgb_models[name] = model

    lgb_model = None
    lgb_path = config.MODEL_DIR / "lgb_top_gainer.txt"
    if lgb_path.exists():
        lgb_model = lgb.Booster(model_file=str(lgb_path))

    return xgb_models, lgb_model
