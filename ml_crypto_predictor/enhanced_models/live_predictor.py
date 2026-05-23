import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import json
import numpy as np
import pandas as pd
import joblib
from datetime import datetime, timezone

from .config import CRYPTO_PAIRS, TIMEFRAMES, MODELS_DIR, RESULTS_DIR
from .data_fetcher import fetch_klines, fetch_fear_greed, fetch_funding_rates
from .feature_engine import build_features
from .meta_labeler import apply_meta_filter

# v2 Feature pipeline imports (mirrors model_trainer.py lines 578-612)
try:
    from .feature_engine_v2 import build_v2_features, build_advanced_volatility_features
    HAS_V2_FEATURES = True
except ImportError:
    HAS_V2_FEATURES = False

try:
    from .external_data import fetch_all_external_features
    HAS_EXTERNAL_DATA = True
except ImportError:
    HAS_EXTERNAL_DATA = False

print(f"[live_predictor] v2 features: {HAS_V2_FEATURES}, external data: {HAS_EXTERNAL_DATA}")

# Cache the expected feature names from the first successful model load
_MODEL_FEATURE_CACHE: dict[str, list[str]] = {}

SCAN_STATE_PATH = RESULTS_DIR / "last_scan_state.json"


def _check_candle_gate() -> bool:
    """Returns True if a new 1h candle has closed since last scan.

    Fetches a FRESH BTC 1h candle (bypassing cache) to avoid the circular
    dependency where stale parquet cache always matches last_scan_state.json.
    The 2h cron schedule already prevents over-scanning, so this gate is
    a lightweight dedup -- not a hard block.
    """
    try:
        # Fetch just 2 candles directly from API (no cache) for the gate check
        fresh_df = fetch_klines("BTCUSDT", "1h", limit=2, cache=False)
        if fresh_df is None or fresh_df.empty:
            return True  # API failed = let it try anyway
        latest_close = str(fresh_df.index[-1])
    except Exception:
        return True  # On any error, allow the scan

    if SCAN_STATE_PATH.exists():
        try:
            with open(SCAN_STATE_PATH) as f:
                state = json.load(f)
            if state.get("last_candle_close") == latest_close:
                return False
        except (json.JSONDecodeError, OSError):
            pass
    # Update state
    SCAN_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SCAN_STATE_PATH, 'w') as f:
        json.dump({"last_candle_close": latest_close}, f)
    return True


def load_model(pair: str, timeframe: str, variant: str) -> tuple:
    model_path = MODELS_DIR / f"{pair}_{timeframe}_{variant}.joblib"
    scaler_path = MODELS_DIR / f"{pair}_{timeframe}_scaler.joblib"

    if not model_path.exists() or not scaler_path.exists():
        print(f"Model not found for {pair}/{timeframe}/{variant}")
        return None, None

    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)
    return model, scaler


def _get_expected_feature_count(model) -> int:
    """Get the number of features the model expects."""
    if hasattr(model, 'n_features_in_'):
        return model.n_features_in_
    if hasattr(model, 'n_features_'):
        return model.n_features_
    return 0


def _align_features(features: pd.DataFrame, model, scaler) -> pd.DataFrame:
    """
    Align feature columns to match what the model was trained on.

    If feature_engine produces more columns than the model expects,
    we select only the first N columns (models were trained on the
    first N features from the same build_features() output).
    """
    expected = _get_expected_feature_count(model)
    actual = features.shape[1]

    if expected > 0 and actual != expected:
        if actual > expected:
            # Feature engine added new features after training -- trim to match
            print(f"  [ALIGN] Trimming features {actual} -> {expected} (model expects {expected})")
            features = features.iloc[:, :expected]
        else:
            # Model expects more features -- pad with zeros
            print(f"  [ALIGN] Padding features {actual} -> {expected} (model expects {expected})")
            for i in range(actual, expected):
                features[f"_pad_{i}"] = 0.0

    return features


def predict_single(model, scaler, features: pd.DataFrame) -> float:
    aligned = _align_features(features, model, scaler)
    X = scaler.transform(aligned.values)
    proba = model.predict_proba(X)[:, 1][0]
    return proba


def _fetch_btc_df(timeframe: str) -> pd.DataFrame:
    """Fetch BTC data for cross-correlation features."""
    try:
        return fetch_klines("BTCUSDT", timeframe, limit=100)
    except Exception:
        return pd.DataFrame()


def run_live_scan(timeframe: str = "1h", threshold: float = 0.55):
    picks = []

    # Fetch BTC data once for cross-correlation features
    btc_df = _fetch_btc_df(timeframe)
    btc_arg = btc_df if not btc_df.empty else None

    # --- Candle-Close Gate: skip scan if no new 1h candle has closed ---
    if not _check_candle_gate():
        print(f"  Skipping scan: no new {timeframe} candle closed since last scan")
        # Return empty result without running inference
        out_path = RESULTS_DIR / f"live_picks_{timeframe}.json"
        result = {"active_picks": [], "picks": [], "count": 0, "skipped": "no_new_candle"}
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)
        return result

    # --- Pre-fetch shared market context once for the whole scan ---
    fear_greed = 50.0
    funding_rates: dict = {}
    if HAS_V2_FEATURES:
        try:
            fear_greed = fetch_fear_greed()
            print(f"  [v2] Fear & Greed: {fear_greed:.0f}")
        except Exception as e:
            print(f"  [WARN] Fear & Greed fetch failed: {e}")
        try:
            funding_rates = fetch_funding_rates()
        except Exception as e:
            print(f"  [WARN] Funding rates fetch failed: {e}")

    for pair in CRYPTO_PAIRS:
        df = fetch_klines(pair, timeframe, limit=100)  # Last 100 bars for features
        if df.empty:
            continue

        # Fix: pass btc_df (DataFrame) not pair (string) as second arg
        features = build_features(df, btc_df=btc_arg)
        if features.empty:
            continue

        # === v2 Integration: add 52+ enhanced features (mirrors model_trainer.py) ===
        if HAS_V2_FEATURES:
            try:
                funding = funding_rates.get(pair, 0.0)
                
                v2_dict = build_v2_features(df, btc_df=btc_arg,
                                            fear_greed=fear_greed,
                                            funding_rate=funding,
                                            include_v1=False)
                v2_frames = []
                for group_name, group_df in v2_dict.items():
                    if isinstance(group_df, pd.DataFrame):
                        new_cols = [c for c in group_df.columns if c not in features.columns]
                        if new_cols:
                            v2_frames.append(group_df[new_cols])
                    elif isinstance(group_df, dict):
                        new_data = {c: s for c, s in group_df.items() if c not in features.columns}
                        if new_data:
                            v2_frames.append(pd.DataFrame(new_data, index=features.index))

                adv_vol = build_advanced_volatility_features(df)
                adv_data = {c: s for c, s in adv_vol.items() if c not in features.columns}
                if adv_data:
                    v2_frames.append(pd.DataFrame(adv_data, index=features.index))

                if v2_frames:
                    features = pd.concat([features] + v2_frames, axis=1).copy()
                        
            except Exception as e:
                print(f"  [WARN] v2 features failed for {pair}: {e}")

        # === External data: OI, DVOL, SPX/VIX, Coinbase premium, etc. ===
        if HAS_EXTERNAL_DATA:
            try:
                ext_features = fetch_all_external_features(pair)
                ext_data = {c: float(v) for c, v in ext_features.items() if c not in features.columns}
                if ext_data:
                    ext_df = pd.DataFrame(ext_data, index=features.index)
                    features = pd.concat([features, ext_df], axis=1).copy()
            except Exception as e:
                print(f"  [WARN] External data failed for {pair}: {e}")

        latest_features = features.iloc[-1:]  # Last row

        for variant in ["A_xgboost", "B_lightgbm", "C_random_forest", "D_ensemble_stack"]:
            model, scaler = load_model(pair, timeframe, variant)
            if model is None:
                continue

            try:
                proba = predict_single(model, scaler, latest_features)
            except Exception as e:
                print(f"  [ERROR] {pair}/{variant}: {e}")
                continue

            if proba >= threshold:
                # Meta-labeler quality gate (M2 filter)
                try:
                    aligned = _align_features(latest_features, model, scaler)
                    scaled_features = scaler.transform(aligned.values)
                    feature_names = list(latest_features.columns) if hasattr(latest_features, 'columns') else []
                    should_trade, meta_conf = apply_meta_filter(
                        pair, timeframe, scaled_features[0], proba,
                        feature_names, threshold=0.55,
                    )
                    if not should_trade:
                        print(f"  [META-FILTER] {pair}/{variant} blocked (meta_conf={meta_conf:.3f})")
                        continue
                except Exception:
                    meta_conf = float(proba)  # Passthrough if meta model unavailable

                picks.append({
                    "pair": pair,
                    "timeframe": timeframe,
                    "variant": variant,
                    "confidence": float(proba),
                    "meta_confidence": float(meta_conf),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

    # Save picks
    out_path = RESULTS_DIR / f"live_picks_{timeframe}.json"
    result = {"active_picks": picks, "picks": picks, "count": len(picks)}
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)

    return result

if __name__ == "__main__":
    picks = run_live_scan()
    print(f"Found {len(picks)} picks:")
    for p in picks:
        print(f"  {p['pair']} ({p['variant']}): {p['confidence']:.2%} confidence")
