"""
Live Scanner / Inference Pipeline -- Crypto ML Edge Engine
==========================================================
Loads trained models, fetches live OHLCV + funding, computes features via
the same engine used in training, runs inference, sizes positions, and
writes active_picks.json.

Usage:
    from crypto_ml_edge.scanner import scan, track_picks

    # Run one full scan cycle
    results = scan()

    # Track TP/SL on existing open picks
    track_picks()

The scanner is designed to run every 15-30 min via GitHub Actions or cron.
It is fully idempotent -- running it twice produces the same result if
market data has not changed.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

try:
    import joblib as _joblib
    _JOBLIB_AVAILABLE = True
except ImportError:
    _JOBLIB_AVAILABLE = False

from crypto_ml_edge.config import (
    DEFAULT_PAIRS,
    TIMEFRAMES,
    CAPITAL_BASE,
    CONFIDENCE_THRESHOLD,
    MAX_CONCURRENT_PICKS,
    SCANNER_VERSION,
    MODELS_DIR,
    DATA_DIR,
    TPSL_CONFIG,
    BINANCE_SPOT_BASE,
)
from crypto_ml_edge.data_fetcher import (
    fetch_klines,
    fetch_funding_rate_history,
    fetch_current_funding_rates,
)
from crypto_ml_edge.features.engine import build_features, WARMUP_BARS
from crypto_ml_edge.risk import compute_position_size, compute_tp_sl

# Market health gate — imported from ml_battleground if available
try:
    from ml_battleground.shared.market_health import (
        check_market_health,
        apply_health_gate,
        MarketHealth,
    )
    _MARKET_HEALTH_AVAILABLE = True
except ImportError:
    _MARKET_HEALTH_AVAILABLE = False
    MarketHealth = None

logger = logging.getLogger(__name__)

# ─── File paths ──────────────────────────────────────────────────────────────

ACTIVE_PICKS_PATH = DATA_DIR / "active_picks.json"


# ─── Model loading ──────────────────────────────────────────────────────────

def _load_model(pair: str, timeframe: str) -> Optional[tuple]:
    """
    Load a trained pipeline + metadata sidecar for a pair/timeframe.

    Returns (pipeline, meta_dict) or None if model files are missing.
    """
    slug = f"{pair}_{timeframe}_edge"
    model_path = MODELS_DIR / f"{slug}.joblib"
    meta_path = MODELS_DIR / f"{slug}_meta.json"

    if not model_path.exists():
        return None

    try:
        if _JOBLIB_AVAILABLE:
            pipeline = _joblib.load(model_path)
        else:
            import pickle
            with open(model_path, "rb") as f:
                pipeline = pickle.load(f)
    except Exception as e:
        logger.warning("Failed to load model %s: %s", model_path, e)
        return None

    meta = {}
    if meta_path.exists():
        try:
            with open(meta_path, "r") as f:
                meta = json.load(f)
        except Exception as e:
            logger.warning("Failed to load meta %s: %s", meta_path, e)

    return pipeline, meta


def _get_available_models(
    pairs: list[str],
    timeframes: list[str],
) -> list[dict]:
    """
    Discover all available trained models for the given pairs/timeframes.
    Returns list of dicts with keys: pair, timeframe, pipeline, meta.
    """
    models = []
    for pair in pairs:
        for tf in timeframes:
            result = _load_model(pair, tf)
            if result is not None:
                pipeline, meta = result
                # Only use models that passed validation (verdict=PASS)
                verdict = meta.get("validation", {}).get("verdict", "UNKNOWN")
                if verdict == "PASS":
                    models.append({
                        "pair": pair,
                        "timeframe": tf,
                        "pipeline": pipeline,
                        "meta": meta,
                    })
                else:
                    logger.info(
                        "Skipping %s %s: verdict=%s (not PASS)",
                        pair, tf, verdict,
                    )
    return models


# ─── Live data + feature computation ────────────────────────────────────────

def _fetch_live_features(
    pair: str,
    timeframe: str,
    feature_names: Optional[list[str]] = None,
) -> Optional[dict]:
    """
    Fetch live OHLCV + funding and compute features for one pair/timeframe.

    Returns dict with keys: features_row (pd.Series), price, atr, ohlcv_df
    or None on failure.
    """
    tf_config = TIMEFRAMES.get(timeframe)
    if tf_config is None:
        logger.warning("Unknown timeframe: %s", timeframe)
        return None

    # Fetch enough bars for feature warmup + a safety margin
    n_bars = WARMUP_BARS + 50
    try:
        ohlcv = fetch_klines(pair, tf_config["interval"], limit=n_bars, cache=False)
    except Exception as e:
        logger.warning("OHLCV fetch failed for %s %s: %s", pair, timeframe, e)
        return None

    if ohlcv.empty or len(ohlcv) < WARMUP_BARS + 10:
        logger.warning(
            "Insufficient OHLCV data for %s %s: got %d bars",
            pair, timeframe, len(ohlcv),
        )
        return None

    # Fetch funding rates (last 30 days is enough for live features)
    try:
        funding = fetch_funding_rate_history(pair, days=30, cache=True)
    except Exception as e:
        logger.warning("Funding fetch failed for %s: %s", pair, e)
        funding = None

    # Build features using the same engine as training
    try:
        features_df = build_features(ohlcv, funding_df=funding, timeframe=timeframe)
    except Exception as e:
        logger.warning("Feature build failed for %s %s: %s", pair, timeframe, e)
        return None

    # Get the latest fully-valid feature row
    features_clean = features_df.iloc[WARMUP_BARS:]
    if features_clean.empty:
        return None

    # Use only the feature columns the model was trained on
    latest_row = features_clean.iloc[-1]

    if feature_names:
        available = [f for f in feature_names if f in latest_row.index]
        if len(available) < len(feature_names):
            missing = set(feature_names) - set(available)
            logger.warning(
                "Missing features for %s %s: %s (filling with 0)",
                pair, timeframe, missing,
            )
        latest_row = latest_row.reindex(feature_names, fill_value=0.0)

    # Fill any NaN in the feature row
    latest_row = latest_row.fillna(0.0)

    # Current price and ATR (absolute) for position sizing
    current_price = float(ohlcv["close"].iloc[-1])
    atr_pct = float(latest_row.get("atr_14", 0.01))
    atr_abs = atr_pct * current_price

    return {
        "features_row": latest_row,
        "price": current_price,
        "atr_abs": atr_abs,
        "atr_pct": atr_pct,
        "ohlcv": ohlcv,
    }


# ─── Inference ──────────────────────────────────────────────────────────────

def _run_inference(
    pipeline,
    features_row: pd.Series,
) -> dict:
    """
    Run model inference on a single feature row.

    Returns dict with keys: direction, confidence, class_probabilities.
    Binary model: class 0 = no-trade, class 1 = long.
    """
    X = features_row.values.reshape(1, -1)

    try:
        proba = pipeline.predict_proba(X)[0]
    except Exception as e:
        logger.warning("Inference failed: %s", e)
        return {"direction": "hold", "confidence": 0.0, "class_probabilities": []}

    # Binary model: class 0 = no-trade, class 1 = long
    hold_prob = float(proba[0])
    long_prob = float(proba[1])

    if long_prob > hold_prob:
        direction = "long"
        confidence = long_prob
    else:
        direction = "hold"
        confidence = hold_prob

    return {
        "direction": direction,
        "confidence": round(confidence, 4),
        "class_probabilities": {
            "short": 0.0,
            "hold": round(hold_prob, 4),
            "long": round(long_prob, 4),
        },
    }


# ─── Pick construction ──────────────────────────────────────────────────────

def _build_pick(
    pair: str,
    timeframe: str,
    direction: str,
    confidence: float,
    price: float,
    atr_abs: float,
    capital: float,
) -> Optional[dict]:
    """
    Build a fully-sized pick with TP/SL from inference results.
    Returns None if confidence is below threshold or position size is zero.
    """
    if confidence < CONFIDENCE_THRESHOLD:
        return None

    if direction == "hold":
        return None

    # Compute TP/SL
    try:
        tp_sl = compute_tp_sl(
            price=price,
            atr=atr_abs,
            timeframe=timeframe,
            direction=direction,
        )
    except Exception as e:
        logger.warning("TP/SL computation failed for %s: %s", pair, e)
        return None

    # Compute position size
    try:
        sizing = compute_position_size(
            confidence=confidence,
            atr=atr_abs,
            price=price,
            capital=capital,
            pair=pair,
        )
    except Exception as e:
        logger.warning("Position sizing failed for %s: %s", pair, e)
        return None

    if sizing["position_size_usd"] <= 0:
        return None

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "pair": pair,
        "timeframe": timeframe,
        "direction": direction,
        "confidence": confidence,
        "entry_price": round(price, 8),
        "tp_price": tp_sl["tp_price"],
        "sl_price": tp_sl["sl_price"],
        "position_size_usd": sizing["position_size_usd"],
        "position_size_pct": sizing["position_size_pct"],
        "risk_reward_ratio": tp_sl["risk_reward_ratio"],
        "max_hold_bars": tp_sl["max_hold_bars"],
        "signal_time": now_iso,
        "source": "edge_engine",
        "status": "active",
        "bars_held": 0,
    }


# ─── JSON persistence ───────────────────────────────────────────────────────

def _load_picks_json() -> dict:
    """Load the active_picks.json file, returning default structure if missing."""
    default = {
        "generated_at": "",
        "engine_version": SCANNER_VERSION,
        "capital_base": CAPITAL_BASE,
        "picks": [],
        "closed_picks": [],
        "performance": {
            "total_picks": 0,
            "wins": 0,
            "losses": 0,
            "timeouts": 0,
            "win_rate": 0.0,
            "total_return_pct": 0.0,
            "sharpe_estimate": 0.0,
        },
    }
    if not ACTIVE_PICKS_PATH.exists():
        return default

    try:
        with open(ACTIVE_PICKS_PATH, "r") as f:
            data = json.load(f)
        # Ensure all required keys exist
        for key in default:
            if key not in data:
                data[key] = default[key]
        return data
    except Exception as e:
        logger.warning("Failed to load %s: %s", ACTIVE_PICKS_PATH, e)
        return default


def _save_picks_json(data: dict) -> None:
    """Save the active_picks.json file atomically."""
    data["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    data["engine_version"] = SCANNER_VERSION
    data["capital_base"] = CAPITAL_BASE

    # Feed hygiene: strip resolved/zero-entry picks before persisting
    raw_picks = data.get("picks", [])
    try:
        import sys as _sys
        _sys.path.insert(0, str(DATA_DIR.parent.parent))
        from alpha_engine.feed_hygiene import sanitize_active_picks
        clean_picks = sanitize_active_picks(raw_picks)
    except Exception:
        clean_picks = [p for p in raw_picks if float(p.get("entry_price") or 0) > 0]
    if len(clean_picks) < len(raw_picks):
        logger.info("[feed_hygiene] crypto_ml_edge: removed %d invalid active picks", len(raw_picks) - len(clean_picks))
    data["picks"] = clean_picks

    # Ensure data dir exists
    ACTIVE_PICKS_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Write to temp then rename for atomicity
    tmp_path = ACTIVE_PICKS_PATH.with_suffix(".tmp")
    try:
        with open(tmp_path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        tmp_path.replace(ACTIVE_PICKS_PATH)
    except Exception as e:
        logger.error("Failed to save picks: %s", e)
        # Fallback: write directly
        try:
            with open(ACTIVE_PICKS_PATH, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e2:
            logger.error("Fallback save also failed: %s", e2)


# ─── Performance tracking ───────────────────────────────────────────────────

def _update_performance(data: dict) -> None:
    """Recalculate performance metrics from closed picks."""
    closed = data.get("closed_picks", [])
    if not closed:
        data["performance"] = {
            "total_picks": 0,
            "wins": 0,
            "losses": 0,
            "timeouts": 0,
            "win_rate": 0.0,
            "total_return_pct": 0.0,
            "sharpe_estimate": 0.0,
        }
        return

    wins = sum(1 for p in closed if p.get("result") == "win")
    losses = sum(1 for p in closed if p.get("result") == "loss")
    timeouts = sum(1 for p in closed if p.get("result") == "timeout")
    total = len(closed)

    # Calculate returns
    returns = []
    for p in closed:
        entry = p.get("entry_price", 0)
        exit_price = p.get("exit_price", 0)
        if entry > 0 and exit_price > 0:
            if p.get("direction") == "long":
                ret = (exit_price - entry) / entry
            else:
                ret = (entry - exit_price) / entry
            returns.append(ret)

    total_return = sum(returns) if returns else 0.0

    # Sharpe estimate (annualized, assume ~365 picks/year as rough estimate)
    if len(returns) >= 2:
        ret_arr = np.array(returns)
        mean_ret = float(np.mean(ret_arr))
        std_ret = float(np.std(ret_arr, ddof=1))
        if std_ret > 0:
            sharpe = (mean_ret / std_ret) * np.sqrt(min(len(returns), 365))
        else:
            sharpe = 0.0
    else:
        sharpe = 0.0

    data["performance"] = {
        "total_picks": total,
        "wins": wins,
        "losses": losses,
        "timeouts": timeouts,
        "win_rate": round(wins / total, 4) if total > 0 else 0.0,
        "total_return_pct": round(total_return * 100, 2),
        "sharpe_estimate": round(sharpe, 2),
    }


# ─── TP/SL Tracking ────────────────────────────────────────────────────────

_PAIR_TO_COINGECKO_ID = {
    "BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "SOLUSDT": "solana",
    "BNBUSDT": "binancecoin", "XRPUSDT": "ripple", "DOGEUSDT": "dogecoin",
    "ADAUSDT": "cardano", "AVAXUSDT": "avalanche-2", "LINKUSDT": "chainlink",
    "DOTUSDT": "polkadot", "SUIUSDT": "sui", "NEARUSDT": "near",
    "APTUSDT": "aptos", "ARBUSDT": "arbitrum", "INJUSDT": "injective-protocol",
    "MATICUSDT": "matic-network",
}

# ETF/Stock symbols that use Yahoo Finance instead of Binance/CoinGecko
_ETF_STOCK_SYMBOLS = {"SPY", "QQQ", "IWM", "GLD", "TLT", "DIA", "VTI", "ARKK"}


def _fetch_etf_price(symbol: str) -> Optional[float]:
    """Fetch current price for an ETF/stock symbol via Yahoo Finance API."""
    import requests

    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        params = {"range": "1d", "interval": "1d"}
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        meta = data.get("chart", {}).get("result", [{}])[0].get("meta", {})
        price = meta.get("regularMarketPrice")
        if price:
            return float(price)
    except Exception as e:
        logger.warning("Yahoo Finance fetch failed for %s: %s", symbol, e)

    return None


def _fetch_current_price(pair: str) -> Optional[float]:
    """Fetch the current price for a pair. Handles crypto (Binance/CoinGecko) and ETFs (Yahoo Finance)."""
    import requests

    # Check if this is an ETF/stock symbol
    if pair in _ETF_STOCK_SYMBOLS:
        return _fetch_etf_price(pair)

    # Try Binance first (for crypto)
    try:
        url = f"{BINANCE_SPOT_BASE}/api/v3/ticker/price"
        resp = requests.get(url, params={"symbol": pair}, timeout=10)
        resp.raise_for_status()
        return float(resp.json()["price"])
    except Exception as e:
        logger.debug("Binance price fetch failed for %s: %s", pair, e)

    # Fallback: CoinGecko (works from US IPs)
    cg_id = _PAIR_TO_COINGECKO_ID.get(pair)
    if cg_id:
        try:
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=usd"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            price = resp.json().get(cg_id, {}).get("usd")
            if price:
                return float(price)
        except Exception as e2:
            logger.warning("CoinGecko price fetch also failed for %s: %s", pair, e2)

    logger.warning("All price sources failed for %s", pair)
    return None


def track_picks(data: Optional[dict] = None) -> dict:
    """
    Check existing open picks against current prices.
    Closes picks that have hit TP, SL, or max hold time.

    Parameters
    ----------
    data : dict, optional
        The picks JSON structure. If None, loads from disk.

    Returns
    -------
    dict : Updated picks data structure.
    """
    if data is None:
        data = _load_picks_json()
    if not isinstance(data, dict):
        data = {"picks": [], "closed_picks": []}

    active_picks = data.get("picks", [])
    if not active_picks:
        return data

    still_active = []
    newly_closed = []

    for pick in active_picks:
        pair = pick.get("pair", "")
        current_price = _fetch_current_price(pair)

        if current_price is None:
            # Cannot check -- keep active
            still_active.append(pick)
            continue

        tp_price = pick.get("tp_price", 0)
        sl_price = pick.get("sl_price", 0)
        direction = pick.get("direction", "long")
        max_hold = pick.get("max_hold_bars", 24)
        bars_held = pick.get("bars_held", 0) + 1

        # Check TP/SL hit
        closed = False
        result = None
        exit_price = current_price

        if direction == "long":
            if current_price >= tp_price:
                closed = True
                result = "win"
                exit_price = tp_price
            elif current_price <= sl_price:
                closed = True
                result = "loss"
                exit_price = sl_price
        else:  # short
            if current_price <= tp_price:
                closed = True
                result = "win"
                exit_price = tp_price
            elif current_price >= sl_price:
                closed = True
                result = "loss"
                exit_price = sl_price

        # Check max hold timeout
        if not closed and bars_held >= max_hold:
            closed = True
            result = "timeout"
            exit_price = current_price

        if closed:
            closed_pick = {**pick}
            closed_pick["status"] = "closed"
            closed_pick["result"] = result
            closed_pick["exit_price"] = round(exit_price, 8)
            closed_pick["bars_held"] = bars_held
            closed_pick["closed_at"] = datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            # Compute PnL
            entry = pick.get("entry_price", 0)
            if entry > 0:
                if direction == "long":
                    pnl_pct = (exit_price - entry) / entry
                else:
                    pnl_pct = (entry - exit_price) / entry
                closed_pick["pnl_pct"] = round(pnl_pct * 100, 4)
            else:
                closed_pick["pnl_pct"] = 0.0

            newly_closed.append(closed_pick)
            logger.info(
                "CLOSED %s %s %s: %s (PnL: %.2f%%)",
                pair, direction, pick.get("timeframe", ""),
                result, closed_pick.get("pnl_pct", 0),
            )
        else:
            pick["bars_held"] = bars_held
            pick["current_price"] = round(current_price, 8)
            entry = pick.get("entry_price", 0)
            if entry > 0:
                if direction == "long":
                    pnl = (current_price - entry) / entry
                else:
                    pnl = (entry - current_price) / entry
                pick["unrealized_pnl_pct"] = round(pnl * 100, 4)
            pick["last_checked"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            still_active.append(pick)

    data["picks"] = still_active
    data["closed_picks"] = data.get("closed_picks", []) + newly_closed

    # Recalculate performance
    _update_performance(data)

    return data


# ─── Market health gate ────────────────────────────────────────────────────

def _get_market_health(pairs: list[str]) -> tuple:
    """
    Assess market health using the ml_battleground circuit breaker.

    Returns (MarketHealth enum, signals_dict) or (None, {}) if unavailable.
    """
    if not _MARKET_HEALTH_AVAILABLE:
        return None, {}

    import requests
    from crypto_ml_edge.config import FEAR_GREED_URL

    # 1. Fetch Fear & Greed index (with retry)
    import time as _time
    fear_greed = 50  # neutral fallback
    for _attempt in range(3):
        try:
            resp = requests.get(FEAR_GREED_URL, timeout=10)
            resp.raise_for_status()
            fg_data = resp.json()
            fear_greed = int(fg_data["data"][0]["value"])
            break
        except Exception as e:
            if _attempt == 2:
                logger.warning("Fear & Greed fetch failed after 3 attempts: %s (using neutral=50)", e)
            else:
                _time.sleep(2 * (_attempt + 1))

    # 2. Fetch BTC 1h OHLCV for trend checks
    btc_df = None
    try:
        btc_df = fetch_klines("BTCUSDT", "1h", limit=250)
    except Exception as e:
        logger.warning("BTC health data fetch failed: %s", e)

    # 3. Fetch funding rates for top pairs
    funding_rates = {}
    try:
        rates = fetch_current_funding_rates(pairs[:5])
        if rates:
            funding_rates = rates
    except Exception as e:
        logger.warning("Funding rate health check failed: %s", e)

    health, signals = check_market_health(
        fear_greed=fear_greed,
        btc_df=btc_df,
        funding_rates=funding_rates,
    )
    return health, signals


# ─── Main scan function ────────────────────────────────────────────────────

def scan(
    pairs: Optional[list[str]] = None,
    timeframes: Optional[list[str]] = None,
    capital: Optional[float] = None,
    dry_run: bool = False,
) -> dict:
    """
    Run one full scan cycle: load models, fetch data, infer, size, write JSON.

    Parameters
    ----------
    pairs : list[str], optional
        Pairs to scan. Defaults to DEFAULT_PAIRS.
    timeframes : list[str], optional
        Timeframes to scan. Defaults to all keys in TIMEFRAMES.
    capital : float, optional
        Capital base for position sizing. Defaults to CAPITAL_BASE.
    dry_run : bool
        If True, do not write to disk. Returns the picks data structure.

    Returns
    -------
    dict : The complete active_picks.json structure.
    """
    t0 = time.time()
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if pairs is None:
        pairs = DEFAULT_PAIRS
    if timeframes is None:
        timeframes = list(TIMEFRAMES.keys())
    if capital is None:
        capital = CAPITAL_BASE

    logger.info(
        "=== SCAN CYCLE START === %s | %d pairs x %d timeframes | capital=$%.0f",
        now_iso, len(pairs), len(timeframes), capital,
    )

    # Step 1: Load existing picks (preserves closed history + active picks)
    data = _load_picks_json()

    # Step 2: Track existing open picks (check TP/SL)
    data = track_picks(data)
    n_currently_active = len(data.get("picks", []))

    # Step 2.5: Market health gate — circuit breaker before new inference
    health, health_signals = _get_market_health(pairs)
    if health is not None:
        logger.info(
            "Market health: %s (F&G=%s, panic=%d, warning=%d)",
            health_signals.get("health", "unknown"),
            health_signals.get("fear_greed", "?"),
            health_signals.get("panic_signals", 0),
            health_signals.get("warning_signals", 0),
        )
        if health == MarketHealth.PANIC:
            logger.warning(
                "PANIC MODE — proceeding with reduced position sizing (was: full block)."
            )
            # Don't return early — let inference run but with reduced sizing
            # Full block was causing multi-day signal staleness
    else:
        logger.debug("Market health check unavailable — proceeding without gate")

    # Step 3: Discover available models
    available_models = _get_available_models(pairs, timeframes)
    logger.info("Found %d trained models", len(available_models))

    if not available_models:
        logger.warning("No trained models found. Writing empty picks.")
        if not dry_run:
            _save_picks_json(data)
        elapsed = round(time.time() - t0, 1)
        logger.info("=== SCAN CYCLE END === %.1fs | 0 new picks", elapsed)
        return data

    # Step 4: Check how many new picks we can add
    slots_available = MAX_CONCURRENT_PICKS - n_currently_active
    if slots_available <= 0:
        logger.info(
            "All %d slots occupied. No new picks this cycle.",
            MAX_CONCURRENT_PICKS,
        )
        if not dry_run:
            _save_picks_json(data)
        return data

    # Step 5: Run inference on each model
    candidates = []
    active_pair_tfs = {
        (p["pair"], p["timeframe"])
        for p in data.get("picks", [])
    }

    for model_info in available_models:
        pair = model_info["pair"]
        tf = model_info["timeframe"]
        pipeline = model_info["pipeline"]
        meta = model_info["meta"]

        # Skip if we already have an active pick for this pair/tf
        if (pair, tf) in active_pair_tfs:
            logger.info("Skipping %s %s: already active", pair, tf)
            continue

        # Fetch live features
        feature_names = meta.get("feature_names", None)
        live_data = _fetch_live_features(pair, tf, feature_names)
        if live_data is None:
            continue

        # Run inference
        inference = _run_inference(pipeline, live_data["features_row"])

        if inference["direction"] == "hold":
            logger.info(
                "HOLD %s %s: conf=%.3f probs=%s",
                pair, tf, inference["confidence"],
                inference["class_probabilities"],
            )
            continue

        logger.info(
            "SIGNAL %s %s: %s conf=%.3f probs=%s",
            pair, tf, inference["direction"], inference["confidence"],
            inference["class_probabilities"],
        )

        candidates.append({
            "pair": pair,
            "timeframe": tf,
            "direction": inference["direction"],
            "confidence": inference["confidence"],
            "price": live_data["price"],
            "atr_abs": live_data["atr_abs"],
        })

    # Step 6: Sort candidates by confidence (highest first)
    candidates.sort(key=lambda x: x["confidence"], reverse=True)

    # Step 6.5: Apply health gate filter to candidates
    if health is not None and _MARKET_HEALTH_AVAILABLE and health != MarketHealth.SAFE:
        pre_filter = len(candidates)
        candidates = apply_health_gate(health, candidates)
        logger.info(
            "Health gate (%s): %d → %d candidates after filter",
            health.value, pre_filter, len(candidates),
        )

    # Step 7: Build picks for top candidates (respecting slot limit)
    new_picks = []
    for cand in candidates:
        if len(new_picks) >= slots_available:
            break

        pick = _build_pick(
            pair=cand["pair"],
            timeframe=cand["timeframe"],
            direction=cand["direction"],
            confidence=cand["confidence"],
            price=cand["price"],
            atr_abs=cand["atr_abs"],
            capital=capital,
        )

        if pick is not None:
            new_picks.append(pick)
            logger.info(
                "NEW PICK: %s %s %s | conf=%.3f | size=$%.0f | TP=%.8f SL=%.8f",
                pick["pair"], pick["timeframe"], pick["direction"],
                pick["confidence"], pick["position_size_usd"],
                pick["tp_price"], pick["sl_price"],
            )

    # Step 8: Merge new picks into active list
    data["picks"] = data.get("picks", []) + new_picks

    # Step 9: Save
    if not dry_run:
        _save_picks_json(data)

    elapsed = round(time.time() - t0, 1)
    logger.info(
        "=== SCAN CYCLE END === %.1fs | %d active | %d new | %d closed total",
        elapsed,
        len(data["picks"]),
        len(new_picks),
        len(data.get("closed_picks", [])),
    )

    return data


# ─── CLI entry point ────────────────────────────────────────────────────────

def main():
    """CLI entry point for running the scanner."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    import argparse
    parser = argparse.ArgumentParser(description="Crypto ML Edge Scanner")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Run inference without writing to disk",
    )
    parser.add_argument(
        "--track-only", action="store_true",
        help="Only track existing picks (no new inference)",
    )
    parser.add_argument(
        "--capital", type=float, default=None,
        help=f"Capital base (default: ${CAPITAL_BASE})",
    )
    args = parser.parse_args()

    if args.track_only:
        data = _load_picks_json()
        data = track_picks(data)
        if not args.dry_run:
            _save_picks_json(data)
        perf = data.get("performance", {})
        print(f"Tracked: {len(data.get('picks', []))} active, "
              f"{perf.get('total_picks', 0)} closed, "
              f"WR={perf.get('win_rate', 0):.1%}")
    else:
        result = scan(capital=args.capital, dry_run=args.dry_run)
        perf = result.get("performance", {})
        print(f"Scan complete: {len(result.get('picks', []))} active picks, "
              f"{perf.get('total_picks', 0)} total closed, "
              f"WR={perf.get('win_rate', 0):.1%}")


if __name__ == "__main__":
    main()
