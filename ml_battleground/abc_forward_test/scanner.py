"""
ABC Forward Test Scanner: 3 approaches head-to-head.
  A) Bear Profiteer  -- Crypto SELL-only with ML
  B) Safe Haven      -- Equity/Forex/Commodity ML (BUY+SELL)
  C) Kitchen Sink    -- Multi-asset rule-based cross-momentum (control)

Run: python -m abc_forward_test.scanner   (from ml_battleground/)
"""

import os
import sys
import json
import time
import logging
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.data_fetcher import fetch_ohlcv, fetch_fear_greed, fetch_single
from shared.indicators import atr, rsi, ema, macd, bollinger_bands, rate_of_change

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

CRYPTO_PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT"]
EQUITY_SYMBOLS = ["SPY", "QQQ", "IWM", "GLD", "TLT"]
FOREX_SYMBOLS = ["GBPUSD=X", "AUDUSD=X", "EURUSD=X", "USDJPY=X"]
ALL_YAHOO = EQUITY_SYMBOLS + FOREX_SYMBOLS

MAX_ACTIVE_PER_APPROACH = 999  # TESTING SPRINT: was 3, uncapped
CRYPTO_EXPIRY_HOURS = 48
TRAD_EXPIRY_DAYS = 10

log = logging.getLogger("abc_scanner")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

# ---------------------------------------------------------------------------
# Yahoo Finance fetcher (no external library)
# ---------------------------------------------------------------------------

def fetch_yahoo(symbol: str, period: str = "60d", interval: str = "1d") -> Optional[pd.DataFrame]:
    """Fetch OHLCV from Yahoo Finance v8 chart API."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {"range": period, "interval": interval, "includePrePost": "false"}
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        data = resp.json()
        result = data["chart"]["result"][0]
        timestamps = result["timestamp"]
        quotes = result["indicators"]["quote"][0]
        df = pd.DataFrame({
            "Open": quotes["open"],
            "High": quotes["high"],
            "Low": quotes["low"],
            "Close": quotes["close"],
            "Volume": quotes["volume"],
        }, index=pd.to_datetime(timestamps, unit="s", utc=True))
        return df.dropna()
    except Exception as exc:
        log.warning("Yahoo fetch failed for %s: %s", symbol, exc)
        return None


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def _path(name: str) -> str:
    return os.path.join(DATA_DIR, f"{name}.json")


def load_picks(name: str) -> dict:
    path = _path(name)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {"active": [], "closed": []}


def save_picks(name: str, picks: dict):
    with open(_path(name), "w") as f:
        json.dump(picks, f, indent=2, default=str)


# ---------------------------------------------------------------------------
# Validation -- check TP/SL/expiry for all active picks
# ---------------------------------------------------------------------------

def _current_price(pick: dict) -> Optional[float]:
    """Fetch latest price for a pick's symbol."""
    sym = pick["symbol"]
    ac = pick.get("asset_class", "crypto")
    if ac == "crypto":
        df = fetch_single(sym, interval="1h", limit=2)
        if df is not None and len(df):
            return float(df["Close"].iloc[-1])
    else:
        df = fetch_yahoo(sym, period="5d", interval="1d")
        if df is not None and len(df):
            return float(df["Close"].iloc[-1])
    return None


def validate_picks(picks: dict) -> dict:
    """Move active picks to closed when TP/SL/expiry hit."""
    now = datetime.now(timezone.utc)
    still_active = []
    for p in picks.get("active", []):
        price = _current_price(p)
        if price is None:
            still_active.append(p)
            continue

        entry = p["entry_price"]
        tp = p["take_profit"]
        sl = p["stop_loss"]
        is_sell = p["signal_type"] == "SELL"

        # Track MFE / MAE
        if is_sell:
            excursion = entry - price
        else:
            excursion = price - entry
        p["mfe"] = max(p.get("mfe", 0), excursion)
        p["mae"] = min(p.get("mae", 0), excursion)

        # TP/SL check (direction-aware)
        hit_tp = (price <= tp) if is_sell else (price >= tp)
        hit_sl = (price >= sl) if is_sell else (price <= sl)

        entry_dt = datetime.fromisoformat(p["entry_date"].replace("Z", "+00:00"))
        is_crypto = str(p.get("asset_class", "")).upper() == "CRYPTO"
        max_hold = timedelta(hours=CRYPTO_EXPIRY_HOURS) if is_crypto else timedelta(days=TRAD_EXPIRY_DAYS)
        expired = (now - entry_dt) > max_hold

        if hit_tp:
            p["status"] = "won"
            p["exit_price"] = price
            p["exit_date"] = now.isoformat()
            pnl_mult = -1 if is_sell else 1
            p["pnl_pct"] = round(pnl_mult * (price / entry - 1) * 100, 3)
            picks["closed"].append(p)
        elif hit_sl:
            p["status"] = "lost"
            p["exit_price"] = price
            p["exit_date"] = now.isoformat()
            pnl_mult = -1 if is_sell else 1
            p["pnl_pct"] = round(pnl_mult * (price / entry - 1) * 100, 3)
            picks["closed"].append(p)
        elif expired:
            p["status"] = "expired"
            p["exit_price"] = price
            p["exit_date"] = now.isoformat()
            pnl_mult = -1 if is_sell else 1
            p["pnl_pct"] = round(pnl_mult * (price / entry - 1) * 100, 3)
            picks["closed"].append(p)
        else:
            still_active.append(p)

    picks["active"] = still_active
    return picks


# ---------------------------------------------------------------------------
# ML helpers  (sklearn GradientBoosting as universal fallback)
# ---------------------------------------------------------------------------

def _train_model(X: np.ndarray, y: np.ndarray):
    """Train a lightweight gradient-boosting classifier. Returns model or None."""
    try:
        from sklearn.ensemble import GradientBoostingClassifier
    except ImportError:
        log.warning("sklearn not available -- ML disabled")
        return None
    if len(X) < 60 or len(np.unique(y)) < 2:
        return None
    model = GradientBoostingClassifier(
        n_estimators=80, max_depth=3, learning_rate=0.1,
        subsample=0.8, random_state=42,
    )
    model.fit(X, y)
    return model


# ---------------------------------------------------------------------------
# APPROACH A : Bear Profiteer -- crypto SELL only
# ---------------------------------------------------------------------------

def _approach_a_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build feature matrix for approach A."""
    close = df["Close"]
    feat = pd.DataFrame(index=df.index)
    feat["rsi14"] = rsi(close)
    m, s, hist = macd(close)
    feat["macd_hist"] = hist
    feat["atr_ratio"] = atr(df["High"], df["Low"], close) / close
    feat["ema_dist"] = (close - ema(close, 20)) / close
    feat["vol_ratio"] = df["Volume"] / df["Volume"].rolling(20).mean()
    feat["ret_1h"] = close.pct_change()
    feat["ret_4h"] = close.pct_change(4)
    return feat.dropna()


def _approach_a_labels(df: pd.DataFrame, feat_idx: pd.Index) -> pd.Series:
    """Triple-barrier labels for SELL: TP = 2x ATR down, SL = 1.5x ATR up, 24-bar horizon."""
    close = df["Close"].reindex(feat_idx)
    atr_vals = atr(df["High"], df["Low"], df["Close"]).reindex(feat_idx)
    labels = pd.Series(0, index=feat_idx)
    for i in range(len(feat_idx) - 24):
        idx = feat_idx[i]
        entry = close.loc[idx]
        a = atr_vals.loc[idx]
        if pd.isna(a) or a == 0:
            continue
        tp_price = entry - 2.0 * a
        sl_price = entry + 1.5 * a
        future = df["Close"].iloc[df.index.get_loc(idx) + 1: df.index.get_loc(idx) + 25]
        for fp in future:
            if fp <= tp_price:
                labels.loc[idx] = 1   # profitable SELL
                break
            if fp >= sl_price:
                labels.loc[idx] = 0
                break
    return labels


def run_approach_a() -> list[dict]:
    """Scan crypto for SELL signals with ML confirmation."""
    log.info("[A] Bear Profiteer scanning %s", CRYPTO_PAIRS)
    now = datetime.now(timezone.utc)
    fear_greed = fetch_fear_greed()
    log.info("[A] Fear & Greed: %d (info only, not blocking)", fear_greed)

    data = fetch_ohlcv(pairs=CRYPTO_PAIRS, interval="1h", limit=500)
    picks: list[dict] = []

    for pair, df in data.items():
        if len(df) < 100:
            continue

        feat = _approach_a_features(df)
        if len(feat) < 80:
            continue

        # Train on older data, predict on latest bar
        X = feat.iloc[:-1].values
        y = _approach_a_labels(df, feat.iloc[:-1].index).values
        model = _train_model(X, y)

        latest_feat = feat.iloc[-1]
        close = float(df["Close"].iloc[-1])
        atr_val = float(atr(df["High"], df["Low"], df["Close"]).iloc[-1])
        ema20 = float(ema(df["Close"], 20).iloc[-1])
        ema50 = float(ema(df["Close"], 50).iloc[-1])
        rsi_val = float(latest_feat["rsi14"])

        # Rule filters: bearish structure
        ema_cross_bear = ema20 < ema50
        rsi_rejection = 35 < rsi_val < 65  # not oversold already
        breakdown = close < ema20

        if not (ema_cross_bear and rsi_rejection and breakdown):
            continue

        # ML confidence
        confidence = 0.60
        if model is not None:
            prob = model.predict_proba(latest_feat.values.reshape(1, -1))
            if prob.shape[1] == 2:
                confidence = float(prob[0][1])
            else:
                confidence = float(max(prob[0]))

        if confidence < 0.60:
            continue

        tp = round(close - 2.0 * atr_val, 2)
        sl = round(close + 1.5 * atr_val, 2)
        rr = abs(close - tp) / max(abs(sl - close), 1e-8)
        if rr < 1.5:
            continue

        reasons = []
        if ema_cross_bear:
            reasons.append(f"EMA20 ({ema20:.0f}) < EMA50 ({ema50:.0f})")
        reasons.append(f"RSI {rsi_val:.1f}")
        reasons.append(f"breakdown below ${ema20:.0f}")

        picks.append({
            "id": f"A_bear_{pair}_{now.strftime('%Y%m%d%H')}",
            "approach": "A",
            "approach_name": "Bear Profiteer",
            "symbol": pair,
            "asset_class": "crypto",
            "signal_type": "SELL",
            "entry_price": close,
            "take_profit": tp,
            "stop_loss": sl,
            "confidence": round(confidence, 3),
            "risk_reward": round(rr, 2),
            "strategy": "ema_breakdown",
            "reason": ", ".join(reasons),
            "position_size_pct": 1.0,
            "status": "active",
            "entry_date": now.isoformat(),
            "fear_greed": fear_greed,
            "ml_features": {k: round(float(v), 4) for k, v in latest_feat.items()},
            "mfe": 0,
            "mae": 0,
        })

    # Sort by confidence descending
    picks.sort(key=lambda p: p["confidence"], reverse=True)
    log.info("[A] Generated %d SELL signals", len(picks))
    return picks


# ---------------------------------------------------------------------------
# APPROACH B : Safe Haven -- equity / forex / commodity ML (BUY + SELL)
# ---------------------------------------------------------------------------

def _approach_b_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build feature matrix for approach B."""
    close = df["Close"]
    feat = pd.DataFrame(index=df.index)
    feat["rsi2"] = rsi(close, 2)
    feat["rsi14"] = rsi(close)
    _, _, hist = macd(close)
    feat["macd_hist"] = hist
    feat["atr_ratio"] = atr(df["High"], df["Low"], close) / close
    _, _, _, _, pctb = bollinger_bands(close)
    feat["bb_pctb"] = pctb
    feat["vol_ratio"] = df["Volume"] / df["Volume"].rolling(20).mean()
    feat["ret5d"] = close.pct_change(5)
    feat["ret10d"] = close.pct_change(10)
    feat["ret20d"] = close.pct_change(20)
    return feat.dropna()


def _approach_b_labels(df: pd.DataFrame, feat_idx: pd.Index) -> pd.Series:
    """Next-5-day return: >1% = BUY(1), <-1% = SELL(2), else HOLD(0)."""
    close = df["Close"]
    labels = pd.Series(0, index=feat_idx)
    for i, idx in enumerate(feat_idx):
        loc = df.index.get_loc(idx)
        if loc + 5 >= len(df):
            continue
        future = float(df["Close"].iloc[loc + 5])
        entry = float(close.loc[idx])
        ret = (future / entry) - 1
        if ret > 0.01:
            labels.loc[idx] = 1   # BUY
        elif ret < -0.01:
            labels.loc[idx] = 2   # SELL
    return labels


def _classify_asset(symbol: str) -> str:
    if symbol in ("GLD", "TLT"):
        return "commodity"
    if "=" in symbol:
        return "forex"
    return "equity"


def run_approach_b() -> list[dict]:
    """Scan equities, forex, commodities for BUY/SELL with ML."""
    log.info("[B] Safe Haven scanning %s", ALL_YAHOO)
    now = datetime.now(timezone.utc)
    picks: list[dict] = []

    # Group by asset class for shared models
    asset_data: dict[str, list[tuple[str, pd.DataFrame, pd.DataFrame]]] = {}

    for sym in ALL_YAHOO:
        df = fetch_yahoo(sym, period="60d", interval="1d")
        if df is None or len(df) < 40:
            log.warning("[B] Skipped %s (insufficient data)", sym)
            continue
        feat = _approach_b_features(df)
        if len(feat) < 30:
            continue
        ac = _classify_asset(sym)
        asset_data.setdefault(ac, []).append((sym, df, feat))
        time.sleep(0.3)  # polite rate limit

    for ac, items in asset_data.items():
        # Pool data across same asset class for a shared model
        all_X, all_y = [], []
        for sym, df, feat in items:
            X = feat.iloc[:-1].values
            y = _approach_b_labels(df, feat.iloc[:-1].index).values
            all_X.append(X)
            all_y.append(y)

        X_pool = np.vstack(all_X) if all_X else np.empty((0, 9))
        y_pool = np.concatenate(all_y) if all_y else np.empty(0)
        model = _train_model(X_pool, y_pool)

        for sym, df, feat in items:
            latest = feat.iloc[-1]
            close = float(df["Close"].iloc[-1])
            atr_val = float(atr(df["High"], df["Low"], df["Close"]).iloc[-1])

            # Rule-based signals
            rsi2_val = float(latest["rsi2"])
            rsi14_val = float(latest["rsi14"])
            bb_pctb = float(latest["bb_pctb"]) if not pd.isna(latest["bb_pctb"]) else 0.5

            signal = None
            strategy = None
            reason_parts = []

            # Connors RSI-2 mean reversion
            if rsi2_val < 10:
                signal = "BUY"
                strategy = "connors_rsi2"
                reason_parts.append(f"RSI-2={rsi2_val:.1f} (extreme oversold)")
            elif rsi2_val > 90:
                signal = "SELL"
                strategy = "connors_rsi2"
                reason_parts.append(f"RSI-2={rsi2_val:.1f} (extreme overbought)")

            # EMA ribbon momentum
            ema9 = float(ema(df["Close"], 9).iloc[-1])
            ema21 = float(ema(df["Close"], 21).iloc[-1])
            if signal is None and ema9 > ema21 and rsi14_val > 50 and bb_pctb > 0.5:
                signal = "BUY"
                strategy = "ema_ribbon"
                reason_parts.append(f"EMA9 > EMA21, RSI-14={rsi14_val:.1f}")
            elif signal is None and ema9 < ema21 and rsi14_val < 50 and bb_pctb < 0.5:
                signal = "SELL"
                strategy = "ema_ribbon"
                reason_parts.append(f"EMA9 < EMA21, RSI-14={rsi14_val:.1f}")

            # Fibonacci retracement bounce
            if signal is None:
                high52 = float(df["High"].rolling(52).max().iloc[-1])
                low52 = float(df["Low"].rolling(52).min().iloc[-1])
                fib_382 = high52 - 0.382 * (high52 - low52)
                fib_618 = high52 - 0.618 * (high52 - low52)
                if fib_618 <= close <= fib_382 and rsi14_val < 45:
                    signal = "BUY"
                    strategy = "fib_retracement"
                    reason_parts.append(f"Price in 38.2-61.8% fib zone, RSI-14={rsi14_val:.1f}")

            if signal is None:
                continue

            # ML confidence
            confidence = 0.55
            expected_class = 1 if signal == "BUY" else 2
            if model is not None:
                prob = model.predict_proba(latest.values.reshape(1, -1))
                classes = list(model.classes_)
                if expected_class in classes:
                    ci = classes.index(expected_class)
                    confidence = float(prob[0][ci])

            if confidence < 0.55:
                continue

            # TP / SL
            if signal == "BUY":
                tp = round(close + 2.0 * atr_val, 4)
                sl = round(close - 1.5 * atr_val, 4)
            else:
                tp = round(close - 2.0 * atr_val, 4)
                sl = round(close + 1.5 * atr_val, 4)

            rr = abs(close - tp) / max(abs(sl - close), 1e-8)
            reason_parts.append(f"BB%B={bb_pctb:.2f}")

            picks.append({
                "id": f"B_{strategy}_{sym}_{now.strftime('%Y%m%d')}",
                "approach": "B",
                "approach_name": "Safe Haven",
                "symbol": sym,
                "asset_class": ac,
                "signal_type": signal,
                "entry_price": close,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(confidence, 3),
                "risk_reward": round(rr, 2),
                "strategy": strategy,
                "reason": ", ".join(reason_parts),
                "position_size_pct": 1.0,
                "status": "active",
                "entry_date": now.isoformat(),
                "ml_features": {k: round(float(v), 4) for k, v in latest.items()},
                "mfe": 0,
                "mae": 0,
            })

    picks.sort(key=lambda p: p["confidence"], reverse=True)
    log.info("[B] Generated %d signals", len(picks))
    return picks


# ---------------------------------------------------------------------------
# APPROACH C : Kitchen Sink -- multi-asset cross-momentum (rule-based control)
# ---------------------------------------------------------------------------

def run_approach_c() -> list[dict]:
    """Cross-asset momentum: rule-based ensemble as ML control group."""
    log.info("[C] Kitchen Sink scanning cross-asset momentum")
    now = datetime.now(timezone.utc)
    picks: list[dict] = []

    # Fetch reference assets for correlation signals
    gld = fetch_yahoo("GLD", period="30d", interval="1d")
    spy = fetch_yahoo("SPY", period="30d", interval="1d")
    dxy = fetch_yahoo("DX-Y.NYB", period="30d", interval="1d")  # dollar index
    btc_df = fetch_single("BTCUSDT", interval="1d", limit=30)

    # Compute regime signals
    gold_rising = False
    crypto_falling = False
    dxy_falling = False

    if gld is not None and len(gld) >= 10:
        gold_ret = float(gld["Close"].iloc[-1] / gld["Close"].iloc[-5] - 1)
        gold_rising = gold_ret > 0.005

    if btc_df is not None and len(btc_df) >= 10:
        btc_ret = float(btc_df["Close"].iloc[-1] / btc_df["Close"].iloc[-5] - 1)
        crypto_falling = btc_ret < -0.02

    if dxy is not None and len(dxy) >= 10:
        dxy_ret = float(dxy["Close"].iloc[-1] / dxy["Close"].iloc[-5] - 1)
        dxy_falling = dxy_ret < -0.003

    # Risk-off signal: gold up + crypto down
    risk_off = gold_rising and crypto_falling
    log.info("[C] Regime: gold_rising=%s, crypto_falling=%s, dxy_falling=%s, risk_off=%s",
             gold_rising, crypto_falling, dxy_falling, risk_off)

    # Scan crypto for SELL if risk-off
    if risk_off:
        crypto_data = fetch_ohlcv(pairs=CRYPTO_PAIRS, interval="1h", limit=200)
        for pair, df in crypto_data.items():
            if len(df) < 50:
                continue
            close = float(df["Close"].iloc[-1])
            atr_val = float(atr(df["High"], df["Low"], df["Close"]).iloc[-1])
            rsi_val = float(rsi(df["Close"]).iloc[-1])
            mom = float(rate_of_change(df["Close"], 24).iloc[-1])  # 24h momentum

            # Ensemble: RSI signal + momentum signal + correlation signal
            rsi_sig = 1 if rsi_val > 55 else (0 if rsi_val > 40 else -1)
            mom_sig = 1 if mom < -0.02 else (0 if mom < 0 else -1)
            corr_sig = 1  # risk-off confirmed
            ensemble = (rsi_sig + mom_sig + corr_sig) / 3.0

            if ensemble < 0.33:  # need at least 2/3 signals agreeing
                continue

            tp = round(close - 2.0 * atr_val, 2)
            sl = round(close + 1.5 * atr_val, 2)
            rr = abs(close - tp) / max(abs(sl - close), 1e-8)

            picks.append({
                "id": f"C_riskoff_{pair}_{now.strftime('%Y%m%d%H')}",
                "approach": "C",
                "approach_name": "Kitchen Sink",
                "symbol": pair,
                "asset_class": "crypto",
                "signal_type": "SELL",
                "entry_price": close,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(ensemble, 3),
                "risk_reward": round(rr, 2),
                "strategy": "cross_momentum_riskoff",
                "reason": f"Risk-off: gold up, crypto down. RSI={rsi_val:.1f}, 24h mom={mom:.3f}",
                "position_size_pct": 1.0,
                "status": "active",
                "entry_date": now.isoformat(),
                "ml_features": {"rsi": round(rsi_val, 2), "momentum_24h": round(mom, 4),
                                "ensemble": round(ensemble, 3)},
                "mfe": 0,
                "mae": 0,
            })

    # Scan forex for BUY non-USD pairs if DXY falling
    if dxy_falling:
        for sym in FOREX_SYMBOLS:
            if "USD=X" not in sym:
                continue
            df = fetch_yahoo(sym, period="30d", interval="1d")
            if df is None or len(df) < 20:
                continue
            close = float(df["Close"].iloc[-1])
            atr_val = float(atr(df["High"], df["Low"], df["Close"]).iloc[-1])
            rsi_val = float(rsi(df["Close"]).iloc[-1])
            mom = float(rate_of_change(df["Close"], 5).iloc[-1])

            # For USDJPY, DXY falling means SELL (USD weakens vs JPY)
            is_usd_base = sym.startswith("USD")
            sig_type = "SELL" if is_usd_base else "BUY"

            rsi_sig = 1 if (rsi_val < 55 and not is_usd_base) or (rsi_val > 45 and is_usd_base) else 0
            mom_sig = 1 if (mom > 0 and not is_usd_base) or (mom < 0 and is_usd_base) else 0
            dxy_sig = 1  # DXY falling confirmed
            ensemble = (rsi_sig + mom_sig + dxy_sig) / 3.0

            if ensemble < 0.33:
                continue

            if sig_type == "BUY":
                tp = round(close + 2.0 * atr_val, 5)
                sl = round(close - 1.5 * atr_val, 5)
            else:
                tp = round(close - 2.0 * atr_val, 5)
                sl = round(close + 1.5 * atr_val, 5)
            rr = abs(close - tp) / max(abs(sl - close), 1e-8)

            picks.append({
                "id": f"C_dxy_{sym}_{now.strftime('%Y%m%d')}",
                "approach": "C",
                "approach_name": "Kitchen Sink",
                "symbol": sym,
                "asset_class": "forex",
                "signal_type": sig_type,
                "entry_price": close,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(ensemble, 3),
                "risk_reward": round(rr, 2),
                "strategy": "cross_momentum_dxy",
                "reason": f"DXY falling -> {sig_type} {sym}. RSI={rsi_val:.1f}, 5d mom={mom:.4f}",
                "position_size_pct": 1.0,
                "status": "active",
                "entry_date": now.isoformat(),
                "ml_features": {"rsi": round(rsi_val, 2), "momentum_5d": round(mom, 4),
                                "ensemble": round(ensemble, 3)},
                "mfe": 0,
                "mae": 0,
            })
            time.sleep(0.3)

    # Scan gold/TLT for BUY if risk-off
    if risk_off:
        for sym in ["GLD", "TLT"]:
            df = fetch_yahoo(sym, period="30d", interval="1d")
            if df is None or len(df) < 20:
                continue
            close = float(df["Close"].iloc[-1])
            atr_val = float(atr(df["High"], df["Low"], df["Close"]).iloc[-1])
            rsi_val = float(rsi(df["Close"]).iloc[-1])

            if rsi_val > 75:  # don't chase overbought safe havens
                continue

            tp = round(close + 2.0 * atr_val, 2)
            sl = round(close - 1.5 * atr_val, 2)
            rr = abs(close - tp) / max(abs(sl - close), 1e-8)

            picks.append({
                "id": f"C_haven_{sym}_{now.strftime('%Y%m%d')}",
                "approach": "C",
                "approach_name": "Kitchen Sink",
                "symbol": sym,
                "asset_class": "commodity",
                "signal_type": "BUY",
                "entry_price": close,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": 0.6,
                "risk_reward": round(rr, 2),
                "strategy": "cross_momentum_haven",
                "reason": f"Risk-off regime: BUY safe haven {sym}. RSI={rsi_val:.1f}",
                "position_size_pct": 1.0,
                "status": "active",
                "entry_date": now.isoformat(),
                "ml_features": {"rsi": round(rsi_val, 2)},
                "mfe": 0,
                "mae": 0,
            })

    picks.sort(key=lambda p: p["confidence"], reverse=True)
    log.info("[C] Generated %d cross-momentum signals", len(picks))
    return picks


# ---------------------------------------------------------------------------
# Consolidated comparison
# ---------------------------------------------------------------------------

def _approach_stats(picks: dict) -> dict:
    closed = picks.get("closed", [])
    wins = [p for p in closed if p.get("status") == "won"]
    losses = [p for p in closed if p.get("status") == "lost"]
    total_closed = len(closed)
    total_pnl = sum(float(p.get("pnl_pct", 0) or 0) for p in closed)
    wr = (len(wins) / total_closed * 100) if total_closed else 0

    # Simple Sharpe proxy from closed P&L
    pnls = [float(p.get("pnl_pct", 0) or 0) for p in closed]
    if len(pnls) >= 2:
        sharpe = round(np.mean(pnls) / max(np.std(pnls), 1e-6), 2)
    else:
        sharpe = 0

    return {
        "active": len(picks.get("active", [])),
        "closed": total_closed,
        "wins": len(wins),
        "losses": len(losses),
        "expired": total_closed - len(wins) - len(losses),
        "win_rate": round(wr, 1),
        "total_pnl": round(total_pnl, 3),
        "sharpe": sharpe,
    }


def write_consolidated(a: dict, b: dict, c: dict):
    """Write head-to-head comparison to abc_consolidated.json."""
    now = datetime.now(timezone.utc)
    stats_a = _approach_stats(a)
    stats_b = _approach_stats(b)
    stats_c = _approach_stats(c)
    stats_a.update({"name": "Bear Profiteer", "asset": "crypto"})
    stats_b.update({"name": "Safe Haven", "asset": "equity/forex/commodity"})
    stats_c.update({"name": "Kitchen Sink", "asset": "multi"})

    # Determine leader (need 10+ closed each)
    leader = None
    head_to_head = "No winner yet (need 10+ closed trades each)"
    all_stats = {"A": stats_a, "B": stats_b, "C": stats_c}
    ready = {k: v for k, v in all_stats.items() if v["closed"] >= 10}
    if len(ready) >= 2:
        best = max(ready.items(), key=lambda x: x[1]["total_pnl"])
        leader = best[0]
        head_to_head = (f"Leader: Approach {leader} ({best[1]['name']}) "
                        f"with {best[1]['total_pnl']:.2f}% total P&L, "
                        f"{best[1]['win_rate']}% WR")

    consolidated = {
        "last_updated": now.isoformat(),
        "approaches": all_stats,
        "head_to_head": head_to_head,
        "leader": leader,
    }

    with open(os.path.join(DATA_DIR, "abc_consolidated.json"), "w") as f:
        json.dump(consolidated, f, indent=2, default=str)


def write_scan_summary(a_new: int, b_new: int, c_new: int, duration_s: float):
    """Write scan metadata."""
    # Check DSR validation across sub-systems
    _dsr_validated = False
    try:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for _sys in ["system_a_filter", "system_b_regime", "system_c_deeplearn"]:
            _vr_path = os.path.join(base, _sys, "models", "validation_report.json")
            if os.path.exists(_vr_path):
                with open(_vr_path) as _vf:
                    if json.load(_vf).get("passed", False):
                        _dsr_validated = True
                        break
    except Exception:
        pass

    summary = {
        "last_scan": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": round(duration_s, 1),
        "new_picks": {"A": a_new, "B": b_new, "C": c_new},
        "version": "1.0.0",
        "dsr_validated": _dsr_validated,
    }
    with open(os.path.join(DATA_DIR, "scan_summary.json"), "w") as f:
        json.dump(summary, f, indent=2, default=str)


# ---------------------------------------------------------------------------
# Main scan orchestrator
# ---------------------------------------------------------------------------

def scan():
    """Run all 3 approaches, validate existing picks, save results."""
    t0 = time.time()
    now = datetime.now(timezone.utc)
    log.info("=== ABC Forward Test Scan at %s ===", now.isoformat())

    # Load existing picks
    a_picks = load_picks("approach_a_picks")
    b_picks = load_picks("approach_b_picks")
    c_picks = load_picks("approach_c_picks")

    # Validate existing (TP/SL/expiry)
    a_picks = validate_picks(a_picks)
    b_picks = validate_picks(b_picks)
    c_picks = validate_picks(c_picks)

    # Run approaches (only generate if room for more active picks)
    a_new, b_new, c_new = [], [], []

    def _dedup_extend(existing: list, new: list, slots: int):
        """Add new picks, skipping any whose symbol already has an active pick."""
        active_symbols = {p["symbol"] for p in existing}
        added = 0
        for p in new:
            if added >= slots:
                break
            if p["symbol"] not in active_symbols:
                existing.append(p)
                active_symbols.add(p["symbol"])
                added += 1
        return added

    if len(a_picks["active"]) < MAX_ACTIVE_PER_APPROACH:
        try:
            a_new = run_approach_a()
            slots = MAX_ACTIVE_PER_APPROACH - len(a_picks["active"])
            _dedup_extend(a_picks["active"], a_new, slots)
        except Exception as exc:
            log.error("[A] Failed: %s", exc)

    if len(b_picks["active"]) < MAX_ACTIVE_PER_APPROACH:
        try:
            b_new = run_approach_b()
            slots = MAX_ACTIVE_PER_APPROACH - len(b_picks["active"])
            _dedup_extend(b_picks["active"], b_new, slots)
        except Exception as exc:
            log.error("[B] Failed: %s", exc)

    if len(c_picks["active"]) < MAX_ACTIVE_PER_APPROACH:
        try:
            c_new = run_approach_c()
            slots = MAX_ACTIVE_PER_APPROACH - len(c_picks["active"])
            _dedup_extend(c_picks["active"], c_new, slots)
        except Exception as exc:
            log.error("[C] Failed: %s", exc)

    # Save
    save_picks("approach_a_picks", a_picks)
    save_picks("approach_b_picks", b_picks)
    save_picks("approach_c_picks", c_picks)

    # Consolidated comparison
    write_consolidated(a_picks, b_picks, c_picks)

    duration = time.time() - t0
    write_scan_summary(len(a_new), len(b_new), len(c_new), duration)

    # Print summary
    log.info("--- Results ---")
    log.info("[A] Bear Profiteer:  %d active, %d closed, %d new",
             len(a_picks["active"]), len(a_picks["closed"]), len(a_new))
    log.info("[B] Safe Haven:      %d active, %d closed, %d new",
             len(b_picks["active"]), len(b_picks["closed"]), len(b_new))
    log.info("[C] Kitchen Sink:    %d active, %d closed, %d new",
             len(c_picks["active"]), len(c_picks["closed"]), len(c_new))
    log.info("Scan completed in %.1fs", duration)


if __name__ == "__main__":
    scan()
