"""
Skyrocket Detector — Training Module
======================================
Fetches historical 1h klines from Binance, builds labels, computes features,
trains the model, and saves it to disk.

Designed to run on CI (GitHub Actions) with only: requests, numpy, pandas,
scikit-learn, joblib.  No database required.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import requests

from skyrocket_detector import config
from skyrocket_detector.feature_engine import compute_features, FEATURE_NAMES
from skyrocket_detector.label_builder import build_labels
from skyrocket_detector.model import SkyrocketModel

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
_MODEL_PATH = os.path.join(_DATA_DIR, "skyrocket_model.joblib")
_META_PATH = os.path.join(_DATA_DIR, "training_meta.json")

# Binance endpoints with failover (per API failover rule: 3+ sources)
_BINANCE_ENDPOINTS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://data-api.binance.vision",
]

_FUTURES_ENDPOINT = "https://fapi.binance.com"


def _fetch_klines_binance(symbol: str, limit: int = 1500) -> list:
    """
    Fetch 1h klines from Binance with failover across multiple endpoints.

    Returns list of [timestamp_ms, open, high, low, close, volume].
    """
    # Try futures API first (more symbols, more history)
    try:
        url = f"{_FUTURES_ENDPOINT}/fapi/v1/klines?symbol={symbol}&interval=1h&limit={limit}"
        r = requests.get(url, timeout=15, headers={"User-Agent": "SkyrocketTrainer/1.0"})
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and len(data) >= 100:
                return _parse_binance_klines(data)
    except Exception:
        pass

    # Spot API failover chain
    for base in _BINANCE_ENDPOINTS:
        try:
            url = f"{base}/api/v3/klines?symbol={symbol}&interval=1h&limit={limit}"
            r = requests.get(url, timeout=15, headers={"User-Agent": "SkyrocketTrainer/1.0"})
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list) and len(data) >= 100:
                    return _parse_binance_klines(data)
        except Exception:
            continue

    return []


def _parse_binance_klines(raw: list) -> list:
    """Parse Binance kline response into [ts, o, h, l, c, v] rows."""
    result = []
    for k in raw:
        result.append([
            int(k[0]),
            float(k[1]),
            float(k[2]),
            float(k[3]),
            float(k[4]),
            float(k[5]),
        ])
    return result


def collect_training_data(symbols: list[str] = None, limit: int = 1500) -> tuple:
    """
    Collect training data from Binance for multiple symbols.

    Args:
        symbols: List of symbols to fetch (default: first 10 from config)
        limit: Max klines per symbol

    Returns:
        (X: pd.DataFrame, y: pd.Series) or (None, None) if insufficient data.
    """
    if symbols is None:
        symbols = config.SYMBOLS[:10]

    all_X = []
    all_y = []
    failed = []

    total = len(symbols)
    for idx, sym in enumerate(symbols, 1):
        print(f"[train] Fetching {idx}/{total}: {sym}...")
        try:
            klines = _fetch_klines_binance(sym, limit=limit)
            if not klines or len(klines) < 100:
                print(f"  {sym} SKIPPED: only {len(klines)} bars")
                failed.append(sym)
                continue

            df = pd.DataFrame(klines, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)

            # Build labels
            df = build_labels(df)

            # Compute features
            featured_df = compute_features(df)

            # Extract feature columns + label, drop NaN
            feature_cols = [c for c in FEATURE_NAMES if c in featured_df.columns]
            merged = featured_df[feature_cols + ["label"]].dropna()

            if len(merged) > 100:
                all_X.append(merged[feature_cols])
                all_y.append(merged["label"])
                n_pos = int(merged["label"].sum())
                print(f"  {sym}: {len(merged)} bars, {n_pos} positive")
            else:
                print(f"  {sym} SKIPPED: only {len(merged)} valid bars after NaN removal")

            # Rate limit
            time.sleep(0.5)

        except Exception as e:
            print(f"  {sym} FAILED: {e}")
            failed.append(sym)

    if failed:
        print(f"[train] Failed symbols: {failed}")

    if not all_X:
        print("[train] ERROR: No training data collected from any symbol")
        return None, None

    X = pd.concat(all_X, ignore_index=True)
    y = pd.concat(all_y, ignore_index=True)

    print(f"[train] Total training bars: {len(X)}, positive: {int(y.sum())} ({y.mean()*100:.1f}%)")
    return X, y


def train_model(X: pd.DataFrame, y: pd.Series, validate: bool = True) -> SkyrocketModel:
    """
    Train the skyrocket model and save to disk.

    Args:
        X: Feature DataFrame
        y: Binary labels
        validate: Run walk-forward validation before final training

    Returns:
        Trained SkyrocketModel instance.
    """
    model = SkyrocketModel()
    metrics = {}

    if validate and len(X) >= 500:
        print("[train] Running walk-forward validation (3 splits)...")
        val_metrics = model.walk_forward_validate(X, y, n_splits=3)
        metrics["validation"] = val_metrics
        print(f"[train] Walk-forward precision: {val_metrics.get('avg_precision', 0):.3f}")
        print(f"[train] Walk-forward recall:    {val_metrics.get('avg_recall', 0):.3f}")
        print(f"[train] Walk-forward F1:        {val_metrics.get('avg_f1', 0):.3f}")
        print(f"[train] Walk-forward AUC:       {val_metrics.get('avg_auc', 0):.3f}")
    elif len(X) < 500:
        print(f"[train] WARNING: Only {len(X)} bars -- skipping validation (need >= 500)")

    print("[train] Training final model on all data...")
    train_metrics = model.train(X, y)
    metrics["training"] = train_metrics

    # Save model
    os.makedirs(_DATA_DIR, exist_ok=True)
    model.save(_MODEL_PATH)

    # Feature importance
    imp = model.feature_importance()
    top5 = dict(list(imp.items())[:5])
    print(f"[train] Top features: {json.dumps(top5, indent=2)}")

    # Save metadata
    meta = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "total_bars": len(X),
        "positive_labels": int(y.sum()),
        "negative_labels": int((y == 0).sum()),
        "positive_rate": float(y.mean()),
        "metrics": metrics,
        "feature_importance": imp,
    }
    with open(_META_PATH, "w") as f:
        json.dump(meta, f, indent=2, default=str)

    print("[train] Training complete -- model saved.")
    return model


def train_if_needed(force: bool = False) -> bool:
    """
    Train the model if it doesn't exist (or if force=True).

    Returns True if model exists (either already existed or was just trained).
    """
    if not force and os.path.exists(_MODEL_PATH):
        print(f"[train] Model already exists at {_MODEL_PATH} -- skipping training")
        return True

    reason = "forced retrain" if force else "no model found"
    print(f"[train] Training required ({reason})...")

    X, y = collect_training_data()
    if X is None or len(X) < 200:
        print("[train] ERROR: Insufficient training data")
        return False

    train_model(X, y)
    return True


def main():
    """CLI entry point for training."""
    import argparse

    parser = argparse.ArgumentParser(description="Skyrocket Detector Training")
    parser.add_argument("--force", action="store_true", help="Force retrain even if model exists")
    args = parser.parse_args()

    print("=" * 60)
    print("  SKYROCKET DETECTOR -- Training")
    print(f"  Time: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    success = train_if_needed(force=args.force)
    if not success:
        print("[train] Training failed -- model not available")
        sys.exit(1)

    print("[train] Done.")


if __name__ == "__main__":
    main()
