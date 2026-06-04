"""
MOMENTUM RIDER Strategy
========================
Detects active LONG picks already winning (+3%+) and predicts whether
the trend will continue to hit TP or reverse.

Uses:
1. Bar close confirmation (MA alignment, candle body vs wick)
2. MFE/TP ratio as primary continuation predictor
3. PnL velocity (accelerating vs decelerating gains)
4. Short-term price prediction (linear regression on recent candles)
5. ML model (heuristic-first, auto-trains XGBoost at 50+ samples)

Empirical foundation (from 326 closed alpha_engine picks):
- Picks reaching +3% MFE: 65.4% continued to hit TP
- mfe_tp_ratio is the strongest predictor (winners avg 0.96 vs losers 0.47)
- Higher confidence at entry (+0.098 diff) and longer hold_days (+2.56 diff)
  both predict continuation
- Losers that reached +2% before reversing: avg MFE 5.6%, final PnL -1.9%

Actions:
- HOLD: momentum confirmed, let winner run
- ADD: strong continuation signal, consider adding to position
- TIGHTEN_SL: momentum weakening, move SL to breakeven or better
- EXIT: reversal signals, take profit now

References:
- Jegadeesh & Titman (1993): Momentum profits persist 3-12 months
- Moskowitz, Ooi & Pedersen (2012): Time-series momentum across assets
- Barberis, Shleifer & Vishny (1998): Investor underreaction model
"""

from __future__ import annotations

import json
import math
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Optional

import numpy as np

# Add parent to path for imports
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

try:
    from config import CRYPTO_SYMBOLS, fetch_binance_json
except ImportError:
    CRYPTO_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "XRPUSDT",
                       "LINKUSDT", "DOGEUSDT", "ADAUSDT", "DOTUSDT", "BNBUSDT"]
    fetch_binance_json = None

# -- Paths --
DATA_DIR = os.path.join(BASE_DIR, "data")
ACTIVE_PICKS_PATH = os.path.join(DATA_DIR, "active_picks.json")
CLOSED_PICKS_PATH = os.path.join(DATA_DIR, "closed_picks.json")
RIDER_MODEL_PATH = os.path.join(DATA_DIR, "momentum_rider_model.json")
RIDER_BACKTEST_PATH = os.path.join(DATA_DIR, "momentum_rider_backtest.json")

# -- Strategy Parameters --
MIN_UNREALIZED_PNL = 0.03      # 3% minimum unrealized PnL to trigger scan
MFE_TP_RATIO_STRONG = 0.70     # 70%+ of TP captured = strong momentum
MFE_TP_RATIO_WEAK = 0.30       # <30% = weak, likely early stage
MA_ALIGNMENT_MIN = 2           # At least 2 of 3 MAs (5/10/20) aligned
RSI_OVERBOUGHT = 80            # Above this = overbought, caution
RSI_OVERSOLD = 30              # Below this = oversold (for shorts)
CANDLE_BODY_RATIO_MIN = 0.55   # Body > 55% of total range = conviction
CONFIDENCE_THRESHOLD = 0.55    # Minimum continuation probability for HOLD
ADD_THRESHOLD = 0.75           # Minimum for ADD recommendation
TIGHTEN_THRESHOLD = 0.40       # Below this = TIGHTEN_SL
EXIT_THRESHOLD = 0.30          # Below this = EXIT

# -- CoinGecko ID Map (for price fallback) --
_CG_IDS = {
    "BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "SOLUSDT": "solana",
    "BNBUSDT": "binancecoin", "XRPUSDT": "ripple", "ADAUSDT": "cardano",
    "AVAXUSDT": "avalanche-2", "DOTUSDT": "polkadot", "LINKUSDT": "chainlink",
    "DOGEUSDT": "dogecoin", "LTCUSDT": "litecoin", "BCHUSDT": "bitcoin-cash",
    "APTUSDT": "aptos", "NEARUSDT": "near", "SUIUSDT": "sui",
    "CAKEUSDT": "pancakeswap-token", "CFXUSDT": "conflux-token",
    "FETUSDT": "artificial-superintelligence-alliance",
    "TRXUSDT": "tron", "XLMUSDT": "stellar", "UNIUSDT": "uniswap",
    "WLDUSDT": "worldcoin-wld", "TONUSDT": "the-open-network",
    "SEIUSDT": "sei-network", "TIAUSDT": "celestia",
}


def _fetch_live_prices() -> dict:
    """Fetch live crypto prices with robust multi-API fallback chain.

    Order: Binance (via config fallback chain) -> CoinGecko -> KuCoin -> CryptoCompare
    Rule: Always have 3+ independent API sources for price data.
    """
    prices = {}

    # API 1: Binance with built-in failover (binance.com -> data-api.binance.vision -> binance.us)
    if fetch_binance_json:
        try:
            data = fetch_binance_json("/api/v3/ticker/price")
            if data:
                prices = {t["symbol"]: float(t["price"]) for t in data}
                print(f"  [RIDER PRICE] Binance chain: {len(prices)} symbols")
                return prices
        except Exception as e:
            print(f"  [RIDER PRICE] Binance chain failed: {e}")

    # API 2: CoinGecko (no geo-block, free tier)
    try:
        ids_str = ",".join(set(_CG_IDS.values()))
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids_str}&vs_currencies=usd"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data = json.loads(urllib.request.urlopen(req, timeout=10).read())
        reverse = {v: k for k, v in _CG_IDS.items()}
        for cg_id, pd in data.items():
            if "usd" in pd and cg_id in reverse:
                prices[reverse[cg_id]] = pd["usd"]
        if prices:
            print(f"  [RIDER PRICE] CoinGecko: {len(prices)} symbols")
            return prices
    except Exception as e:
        print(f"  [RIDER PRICE] CoinGecko failed: {e}")

    # API 3: KuCoin (no geo-block, good uptime)
    try:
        url = "https://api.kucoin.com/api/v1/market/allTickers"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data = json.loads(urllib.request.urlopen(req, timeout=10).read())
        if data.get("data", {}).get("ticker"):
            for t in data["data"]["ticker"]:
                sym = t["symbol"].replace("-", "")
                if sym.endswith("USDT"):
                    prices[sym] = float(t["last"])
        if prices:
            print(f"  [RIDER PRICE] KuCoin: {len(prices)} symbols")
            return prices
    except Exception as e:
        print(f"  [RIDER PRICE] KuCoin failed: {e}")

    # API 4: CryptoCompare (widely available, free tier)
    try:
        syms = "BTC,ETH,SOL,BNB,XRP,ADA,AVAX,DOT,LINK,DOGE,LTC,BCH,APT,NEAR,SUI,CAKE,CFX,FET,TRX,WLD,TON,SEI,TIA"
        url = f"https://min-api.cryptocompare.com/data/pricemulti?fsyms={syms}&tsyms=USDT"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data = json.loads(urllib.request.urlopen(req, timeout=10).read())
        for sym, pd in data.items():
            if "USDT" in pd:
                prices[f"{sym}USDT"] = float(pd["USDT"])
        if prices:
            print(f"  [RIDER PRICE] CryptoCompare: {len(prices)} symbols")
            return prices
    except Exception as e:
        print(f"  [RIDER PRICE] CryptoCompare failed: {e}")

    print("  [RIDER PRICE] WARNING: All price APIs failed!")
    return prices


def _fetch_klines(symbol: str, interval: str = "1h", limit: int = 30) -> list:
    """Fetch recent klines/candles with Binance -> KuCoin -> CryptoCompare fallback.

    Returns list of dicts: [{open, high, low, close, volume, timestamp}, ...]
    """
    candles = []

    # Normalize symbol for different exchanges
    base_sym = symbol.replace("-USD", "USDT").replace("=X", "")
    if not base_sym.endswith("USDT"):
        base_sym = base_sym + "USDT"

    # API 1: Binance klines
    if fetch_binance_json:
        try:
            data = fetch_binance_json(
                f"/api/v3/klines?symbol={base_sym}&interval={interval}&limit={limit}"
            )
            if data and isinstance(data, list) and len(data) > 5:
                for k in data:
                    candles.append({
                        "timestamp": k[0],
                        "open": float(k[1]),
                        "high": float(k[2]),
                        "low": float(k[3]),
                        "close": float(k[4]),
                        "volume": float(k[5]),
                    })
                return candles
        except Exception as e:
            print(f"  [RIDER KLINES] Binance failed for {symbol}: {e}")

    # API 2: KuCoin klines
    try:
        kucoin_sym = base_sym.replace("USDT", "-USDT")
        # KuCoin interval mapping
        kc_interval = {"1h": "1hour", "4h": "4hour", "1d": "1day"}.get(interval, "1hour")
        url = f"https://api.kucoin.com/api/v1/market/candles?type={kc_interval}&symbol={kucoin_sym}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data = json.loads(urllib.request.urlopen(req, timeout=10).read())
        if data.get("data") and len(data["data"]) > 5:
            # KuCoin returns [timestamp, open, close, high, low, volume, turnover] in DESC order
            for k in reversed(data["data"][-limit:]):
                candles.append({
                    "timestamp": int(k[0]) * 1000,
                    "open": float(k[1]),
                    "high": float(k[3]),
                    "low": float(k[4]),
                    "close": float(k[2]),
                    "volume": float(k[5]),
                })
            return candles
    except Exception as e:
        print(f"  [RIDER KLINES] KuCoin failed for {symbol}: {e}")

    # API 3: CryptoCompare hourly
    try:
        base_ticker = base_sym.replace("USDT", "")
        cc_limit = min(limit, 100)
        url = f"https://min-api.cryptocompare.com/data/v2/histohour?fsym={base_ticker}&tsym=USDT&limit={cc_limit}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data = json.loads(urllib.request.urlopen(req, timeout=10).read())
        if data.get("Data", {}).get("Data"):
            for k in data["Data"]["Data"]:
                if k.get("close", 0) > 0:
                    candles.append({
                        "timestamp": k["time"] * 1000,
                        "open": float(k["open"]),
                        "high": float(k["high"]),
                        "low": float(k["low"]),
                        "close": float(k["close"]),
                        "volume": float(k.get("volumefrom", 0)),
                    })
            return candles
    except Exception as e:
        print(f"  [RIDER KLINES] CryptoCompare failed for {symbol}: {e}")

    return candles


def _load_json(path: str):
    """Safely load JSON file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _parse_ts(ts_str) -> Optional[datetime]:
    """Parse various timestamp formats to datetime."""
    if not ts_str:
        return None
    try:
        s = str(ts_str).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------
# Technical Indicators (computed from klines)
# ---------------------------------------------------------------------

def _compute_sma(closes: list, period: int) -> float:
    """Simple moving average of last N closes."""
    if len(closes) < period:
        return 0.0
    return float(np.mean(closes[-period:]))


def _compute_rsi(closes: list, period: int = 14) -> float:
    """RSI from close prices."""
    if len(closes) < period + 1:
        return 50.0  # neutral default
    deltas = np.diff(closes[-(period + 1):])
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains) if len(gains) > 0 else 0
    avg_loss = np.mean(losses) if len(losses) > 0 else 0
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100 - (100 / (1 + rs)))


def _compute_ema(closes: list, period: int) -> float:
    """Exponential moving average."""
    if len(closes) < period:
        return 0.0
    multiplier = 2 / (period + 1)
    ema = closes[0]
    for c in closes[1:]:
        ema = (c - ema) * multiplier + ema
    return float(ema)


def _bar_close_confirmation(candles: list, direction: str = "LONG") -> dict:
    """
    Bar close confirmation analysis.

    Checks:
    1. Last 3 candle closes vs MA5 (strong momentum if all above for LONG)
    2. Candle body vs wick ratio (conviction check)
    3. Higher-timeframe alignment proxy (MA20 slope)

    Returns dict with scores and details.
    """
    if len(candles) < 20:
        return {"score": 0.5, "ma_aligned": False, "body_conviction": False,
                "htf_aligned": False, "details": "Insufficient candle data"}

    closes = [c["close"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]

    ma5 = _compute_sma(closes, 5)
    ma10 = _compute_sma(closes, 10)
    ma20 = _compute_sma(closes, 20)

    # 1. Last 3 closes vs MA5
    last_3_closes = closes[-3:]
    if direction == "LONG":
        ma_passes = sum(1 for c in last_3_closes if c > ma5)
    else:
        ma_passes = sum(1 for c in last_3_closes if c < ma5)

    ma_aligned = ma_passes >= 2

    # MA stack alignment (LONG: close > MA5 > MA10 > MA20)
    if direction == "LONG":
        ma_stack = int(closes[-1] > ma5) + int(ma5 > ma10) + int(ma10 > ma20)
    else:
        ma_stack = int(closes[-1] < ma5) + int(ma5 < ma10) + int(ma10 < ma20)

    # 2. Candle body conviction (last 3 candles)
    body_ratios = []
    for i in range(-3, 0):
        c = candles[i]
        total_range = c["high"] - c["low"]
        if total_range > 0:
            body = abs(c["close"] - c["open"])
            body_ratios.append(body / total_range)
    avg_body_ratio = np.mean(body_ratios) if body_ratios else 0
    body_conviction = avg_body_ratio >= CANDLE_BODY_RATIO_MIN

    # 3. Higher TF proxy: MA20 slope (positive = uptrend for LONG)
    if len(closes) >= 25:
        ma20_prev = np.mean(closes[-25:-5])
        ma20_slope = (ma20 - ma20_prev) / ma20_prev if ma20_prev > 0 else 0
    else:
        ma20_slope = 0

    if direction == "LONG":
        htf_aligned = ma20_slope > 0.001  # MA20 trending up
    else:
        htf_aligned = ma20_slope < -0.001  # MA20 trending down

    # Composite score (0-1)
    score = 0.0
    score += 0.30 * (ma_passes / 3)           # MA5 alignment
    score += 0.25 * (ma_stack / 3)             # MA stack
    score += 0.20 * min(1.0, avg_body_ratio)   # Body conviction
    score += 0.15 * (1.0 if htf_aligned else 0.0)  # HTF alignment
    score += 0.10 * (1.0 if body_conviction else 0.0)  # Body threshold bonus

    return {
        "score": round(float(score), 4),
        "ma_aligned": ma_aligned,
        "ma_stack": ma_stack,
        "body_conviction": body_conviction,
        "avg_body_ratio": round(float(avg_body_ratio), 4),
        "htf_aligned": htf_aligned,
        "ma20_slope": round(float(ma20_slope), 6),
        "details": (f"MA5 passes: {ma_passes}/3, MA stack: {ma_stack}/3, "
                    f"body ratio: {avg_body_ratio:.2f}, HTF: {'up' if htf_aligned else 'down/flat'}")
    }


def _predict_price_direction(candles: list, horizon: int = 4) -> dict:
    """
    Short-term price prediction using linear regression on recent closes.

    Uses last 24 candles to fit a linear trend, then extrapolates.
    Also computes momentum (rate of change) and acceleration.

    Args:
        candles: list of candle dicts with 'close'
        horizon: number of candles to predict ahead

    Returns:
        dict with predicted direction, slope, confidence, acceleration
    """
    if len(candles) < 12:
        return {"direction": "NEUTRAL", "slope": 0, "r_squared": 0,
                "predicted_change_pct": 0, "acceleration": 0}

    closes = np.array([c["close"] for c in candles[-24:]])
    n = len(closes)
    x = np.arange(n)

    # Linear regression
    x_mean = np.mean(x)
    y_mean = np.mean(closes)
    ss_xy = np.sum((x - x_mean) * (closes - y_mean))
    ss_xx = np.sum((x - x_mean) ** 2)

    if ss_xx == 0:
        return {"direction": "NEUTRAL", "slope": 0, "r_squared": 0,
                "predicted_change_pct": 0, "acceleration": 0}

    slope = ss_xy / ss_xx
    intercept = y_mean - slope * x_mean

    # R-squared (goodness of fit)
    y_pred = slope * x + intercept
    ss_res = np.sum((closes - y_pred) ** 2)
    ss_tot = np.sum((closes - y_mean) ** 2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

    # Predicted price at horizon
    future_price = slope * (n + horizon) + intercept
    current_price = closes[-1]
    predicted_change_pct = (future_price - current_price) / current_price if current_price > 0 else 0

    # Acceleration: compare slope of first half vs second half
    half = n // 2
    if half >= 3:
        first_half = closes[:half]
        second_half = closes[half:]
        x1 = np.arange(len(first_half))
        x2 = np.arange(len(second_half))
        slope1 = np.polyfit(x1, first_half, 1)[0] if len(first_half) > 1 else 0
        slope2 = np.polyfit(x2, second_half, 1)[0] if len(second_half) > 1 else 0
        # Normalize slopes by price level
        norm_slope1 = slope1 / np.mean(first_half) if np.mean(first_half) > 0 else 0
        norm_slope2 = slope2 / np.mean(second_half) if np.mean(second_half) > 0 else 0
        acceleration = norm_slope2 - norm_slope1
    else:
        acceleration = 0

    direction = "UP" if slope > 0 and r_squared > 0.1 else "DOWN" if slope < 0 and r_squared > 0.1 else "NEUTRAL"

    return {
        "direction": direction,
        "slope": round(float(slope), 8),
        "r_squared": round(float(max(0, r_squared)), 4),
        "predicted_change_pct": round(float(predicted_change_pct), 6),
        "acceleration": round(float(acceleration), 6),
    }


# ---------------------------------------------------------------------
# ML Model (Heuristic + Auto-train)
# ---------------------------------------------------------------------

def _load_rider_model() -> Optional[dict]:
    """Load persisted rider model weights/state."""
    return _load_json(RIDER_MODEL_PATH)


def _save_rider_model(model_state: dict):
    """Persist rider model state."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(RIDER_MODEL_PATH, "w", encoding="utf-8") as f:
        json.dump(model_state, f, indent=2, default=str)


def _compute_continuation_probability_heuristic(features: dict) -> float:
    """
    Heuristic model for continuation probability.

    Based on empirical analysis of 326 closed picks:
    - mfe_tp_ratio is the strongest predictor (winners avg 0.96, losers 0.47)
    - confidence at entry matters (+0.098 diff)
    - hold_days matters (winners hold longer: 4.1 vs 1.6 days)
    - bar close confirmation and price prediction add signal

    Returns probability 0-1.
    """
    prob = 0.50  # base rate

    # Feature 1: MFE/TP ratio (strongest predictor, +/- 0.20)
    mfe_tp = features.get("mfe_tp_ratio", 0)
    if mfe_tp >= 0.80:
        prob += 0.20  # very close to TP, high continuation
    elif mfe_tp >= 0.50:
        prob += 0.10
    elif mfe_tp < 0.30:
        prob -= 0.10  # barely started, less certain

    # Feature 2: Bar close confirmation score (+/- 0.15)
    bar_score = features.get("bar_close_score", 0.5)
    prob += (bar_score - 0.5) * 0.30  # scale to +/- 0.15

    # Feature 3: Price prediction alignment (+/- 0.10)
    pred_change = features.get("predicted_change_pct", 0)
    direction = features.get("direction", "LONG")
    if direction == "LONG":
        if pred_change > 0.005:   # predicting +0.5% up
            prob += 0.10
        elif pred_change < -0.005:
            prob -= 0.10
    else:  # SHORT
        if pred_change < -0.005:
            prob += 0.10
        elif pred_change > 0.005:
            prob -= 0.10

    # Feature 4: Confidence at entry (+/- 0.08)
    conf = features.get("confidence_at_entry", 0.6)
    if conf >= 0.80:
        prob += 0.08
    elif conf >= 0.70:
        prob += 0.04
    elif conf < 0.55:
        prob -= 0.05

    # Feature 5: PnL velocity / acceleration (+/- 0.07)
    acceleration = features.get("price_acceleration", 0)
    if acceleration > 0.001:
        prob += 0.07  # accelerating gains
    elif acceleration < -0.001:
        prob -= 0.07  # decelerating

    # Feature 6: RSI check (penalty for extreme overbought/oversold)
    rsi = features.get("rsi", 50)
    if direction == "LONG" and rsi > RSI_OVERBOUGHT:
        prob -= 0.10
    elif direction == "SHORT" and rsi < RSI_OVERSOLD:
        prob -= 0.10

    # Feature 7: Hold days (longer holds that are still winning = stronger)
    hold_days = features.get("hold_days", 0)
    # 2026-06-04 null-coalesce: features.get(k, 0) returns None when key is
    # present with explicit None (mark-to-market failure); comparison crashes.
    if hold_days >= 3 and (features.get("unrealized_pnl_pct") or 0) > 0.03:
        prob += 0.05
    elif hold_days == 0:
        prob -= 0.03  # too fresh, could be noise

    # Feature 8: R-squared of price trend (higher = more reliable trend)
    r_squared = features.get("price_r_squared", 0)
    if r_squared > 0.5:
        prob += 0.05
    elif r_squared < 0.1:
        prob -= 0.03

    return max(0.05, min(0.95, prob))


def _compute_continuation_probability_ml(features: dict, model_state: dict) -> float:
    """
    ML model for continuation probability.
    Uses XGBoost if available and trained, otherwise falls back to heuristic.
    """
    if not model_state or model_state.get("model_type") != "xgboost":
        return _compute_continuation_probability_heuristic(features)

    try:
        import xgboost as xgb
        import pickle
        import base64

        model_bytes = base64.b64decode(model_state["model_b64"])
        model = pickle.loads(model_bytes)

        feature_names = model_state["feature_names"]
        x = np.array([[features.get(f, 0) for f in feature_names]])
        prob = float(model.predict_proba(x)[0][1])
        return max(0.05, min(0.95, prob))
    except Exception:
        return _compute_continuation_probability_heuristic(features)


def _train_ml_model(training_data: list) -> Optional[dict]:
    """
    Train XGBoost model on historical continuation data.
    Only trains when 50+ samples available.

    Args:
        training_data: list of dicts with features + 'target' (1=hit TP, 0=reversed)

    Returns:
        model_state dict or None if insufficient data / training failed
    """
    if len(training_data) < 50:
        return None

    try:
        import xgboost as xgb
        import pickle
        import base64
    except ImportError:
        return None

    feature_names = [
        "mfe_tp_ratio", "bar_close_score", "predicted_change_pct",
        "confidence_at_entry", "price_acceleration", "rsi",
        "hold_days", "price_r_squared", "unrealized_pnl_pct",
        "pnl_velocity",
    ]

    X = np.array([[d.get(f, 0) for f in feature_names] for d in training_data])
    y = np.array([d["target"] for d in training_data])

    # Handle class imbalance
    n_pos = sum(y)
    n_neg = len(y) - n_pos
    scale = n_neg / n_pos if n_pos > 0 else 1.0

    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        scale_pos_weight=scale,
        eval_metric="logloss",
        random_state=42,
    )
    model.fit(X, y)

    # Serialize model
    model_bytes = pickle.dumps(model)
    model_b64 = base64.b64encode(model_bytes).decode("ascii")

    # Feature importance
    importances = dict(zip(feature_names, [float(x) for x in model.feature_importances_]))

    return {
        "model_type": "xgboost",
        "model_b64": model_b64,
        "feature_names": feature_names,
        "n_samples": len(training_data),
        "n_positive": int(n_pos),
        "n_negative": int(n_neg),
        "feature_importances": importances,
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------
# Main Strategy Functions
# ---------------------------------------------------------------------

def _determine_action(prob: float, features: dict) -> str:
    """Determine recommended action based on continuation probability and features."""
    if prob >= ADD_THRESHOLD and features.get("bar_close_score", 0) > 0.6:
        return "ADD"
    elif prob >= CONFIDENCE_THRESHOLD:
        return "HOLD"
    elif prob >= TIGHTEN_THRESHOLD:
        return "TIGHTEN_SL"
    else:
        return "EXIT"


def _normalize_symbol(symbol: str) -> str:
    """Normalize symbol for Binance-style lookup (e.g., ETH-USD -> ETHUSDT)."""
    sym = symbol.upper().replace("-USD", "USDT").replace("=X", "")
    if not sym.endswith("USDT") and not sym.endswith("USD"):
        sym = sym + "USDT"
    return sym


def scan_active_for_riders(data: dict = None) -> list:
    """
    Main strategy: scan active picks for momentum riding opportunities.

    Heuristic model -- no ML training required.

    Args:
        data: dict of {symbol: pd.DataFrame} with OHLCV (optional)

    Returns:
        list of signal dicts compatible with alpha_engine
    """
    active_picks = _load_json(ACTIVE_PICKS_PATH)
    if not active_picks or not isinstance(active_picks, list):
        return []

    # Filter for LONG picks with sufficient unrealized PnL
    candidates = []
    for p in active_picks:
        if not isinstance(p, dict):
            continue
        direction = p.get("direction", p.get("signal_type", "")).upper()
        if "BUY" in direction or "LONG" in direction:
            direction = "LONG"
        elif "SELL" in direction or "SHORT" in direction:
            direction = "SHORT"
        else:
            continue

        unrealized = float(p.get("unrealized_pnl_pct", 0) or 0)
        mfe = float(p.get("mfe", 0) or 0)

        # Check if currently winning at +3%+ (or MFE reached +3%+)
        if unrealized >= MIN_UNREALIZED_PNL or mfe >= MIN_UNREALIZED_PNL:
            p["_direction"] = direction
            p["_unrealized"] = unrealized
            p["_mfe"] = mfe
            candidates.append(p)

    if not candidates:
        return []

    print(f"  [RIDER] Found {len(candidates)} active picks at +{MIN_UNREALIZED_PNL*100:.0f}%+ unrealized PnL")

    # Fetch live prices
    live_prices = _fetch_live_prices()

    signals = []
    now = datetime.now(timezone.utc)

    for pick in candidates:
        symbol = pick.get("symbol", "")
        direction = pick["_direction"]
        entry_price = float(pick.get("entry_price", 0) or 0)
        tp = float(pick.get("take_profit", 0) or 0)
        sl = float(pick.get("stop_loss", 0) or 0)
        mfe = pick["_mfe"]
        unrealized = pick["_unrealized"]
        confidence_at_entry = float(pick.get("confidence", 0) or 0)
        hold_days = int(pick.get("hold_days", 0) or 0)

        if entry_price <= 0 or tp <= 0:
            continue

        # Compute MFE/TP ratio
        if direction == "LONG":
            tp_pct = (tp - entry_price) / entry_price if entry_price > 0 else 0
        else:
            tp_pct = (entry_price - tp) / entry_price if entry_price > 0 else 0
        mfe_tp_ratio = mfe / tp_pct if tp_pct > 0 else 0

        # Get current price
        norm_sym = _normalize_symbol(symbol)
        current_price = live_prices.get(norm_sym, 0)
        if current_price <= 0:
            # Try original symbol
            current_price = float(pick.get("current_price", 0) or 0)
        if current_price <= 0:
            continue

        # Compute PnL velocity (unrealized PnL / hold time in hours)
        created_at = _parse_ts(pick.get("created_at", pick.get("timestamp", "")))
        hours_held = (now - created_at).total_seconds() / 3600 if created_at else 24
        hours_held = max(hours_held, 0.5)  # avoid division by zero
        pnl_velocity = unrealized / hours_held

        # Fetch candles for bar close confirmation
        candles = _fetch_klines(symbol, "1h", 30)

        bar_close = _bar_close_confirmation(candles, direction) if candles else {
            "score": 0.5, "ma_aligned": False, "body_conviction": False,
            "htf_aligned": False, "details": "No candle data"
        }

        # Price prediction
        price_pred = _predict_price_direction(candles) if candles else {
            "direction": "NEUTRAL", "slope": 0, "r_squared": 0,
            "predicted_change_pct": 0, "acceleration": 0
        }

        # RSI
        rsi = _compute_rsi([c["close"] for c in candles]) if candles and len(candles) > 14 else 50.0

        # Assemble features
        features = {
            "mfe_tp_ratio": mfe_tp_ratio,
            "bar_close_score": bar_close["score"],
            "predicted_change_pct": price_pred["predicted_change_pct"],
            "confidence_at_entry": confidence_at_entry,
            "price_acceleration": price_pred["acceleration"],
            "rsi": rsi,
            "hold_days": hold_days,
            "price_r_squared": price_pred["r_squared"],
            "unrealized_pnl_pct": unrealized,
            "pnl_velocity": pnl_velocity,
            "direction": direction,
        }

        # Compute continuation probability (heuristic)
        prob = _compute_continuation_probability_heuristic(features)
        action = _determine_action(prob, features)

        # Only generate signals for picks where we have a meaningful recommendation
        if action in ("HOLD", "ADD"):
            # Generate a continuation signal (BUY more / hold)
            # TP: use remaining distance to original TP
            # SL: tighten to just below current entry (breakeven protection)
            if direction == "LONG":
                new_entry = current_price
                new_tp = tp  # ride to original TP
                new_sl = max(sl, entry_price * 1.005)  # at least breakeven + 0.5%
                signal_type = "BUY"
            else:
                new_entry = current_price
                new_tp = tp
                new_sl = min(sl, entry_price * 0.995)
                signal_type = "SELL"

            rr = (abs(new_tp - new_entry) / abs(new_entry - new_sl)
                  if abs(new_entry - new_sl) > 0 else 0)

            signals.append({
                "strategy": "momentum_rider_base",
                "symbol": symbol,
                "category": pick.get("category", "crypto"),
                "signal_type": signal_type,
                "direction": direction,
                "entry_price": round(new_entry, 8),
                "take_profit": round(new_tp, 8),
                "stop_loss": round(new_sl, 8),
                "confidence": round(prob, 4),
                "risk_reward": round(rr, 2),
                "reason": (f"Momentum rider ({action}): {symbol} at +{unrealized*100:.1f}% unrealized, "
                           f"MFE/TP={mfe_tp_ratio:.0%}, bar_close={bar_close['score']:.2f}, "
                           f"pred={price_pred['direction']}, RSI={rsi:.0f}. "
                           f"Continuation prob: {prob:.0%}. "
                           f"Barberis et al. (1998): underreaction model."),
                "timestamp": now.isoformat(),
                "rider_action": action,
                "rider_probability": round(prob, 4),
                "rider_features": {k: round(v, 4) if isinstance(v, float) else v
                                   for k, v in features.items()},
                "original_pick_id": pick.get("id", ""),
                "bar_close_details": bar_close["details"],
                "price_prediction": price_pred["direction"],
            })
        else:
            # For TIGHTEN_SL / EXIT, log but don't generate new entry signal
            print(f"  [RIDER] {symbol}: {action} (prob={prob:.0%}, MFE/TP={mfe_tp_ratio:.0%}, "
                  f"bar={bar_close['score']:.2f}, pred={price_pred['direction']})")

    return signals


def scan_active_for_riders_ml(data: dict = None) -> list:
    """
    ML-enhanced version of momentum rider.
    Uses XGBoost when trained model is available, otherwise heuristic.

    Also handles auto-training: when 50+ closed picks with MFE data exist,
    trains and persists an XGBoost model.

    Args:
        data: dict of {symbol: pd.DataFrame} with OHLCV (optional)

    Returns:
        list of signal dicts
    """
    # Check if we should retrain
    model_state = _load_rider_model()
    should_retrain = False

    if not model_state:
        should_retrain = True
    elif model_state.get("model_type") != "xgboost":
        should_retrain = True
    else:
        # Retrain if model is >24h old
        trained_at = _parse_ts(model_state.get("trained_at", ""))
        if trained_at and (datetime.now(timezone.utc) - trained_at).total_seconds() > 86400:
            should_retrain = True

    # Build training data from closed picks
    if should_retrain:
        closed_picks = _load_json(CLOSED_PICKS_PATH)
        if closed_picks and isinstance(closed_picks, list):
            training_data = _build_training_data(closed_picks)
            if len(training_data) >= 50:
                new_model = _train_ml_model(training_data)
                if new_model:
                    _save_rider_model(new_model)
                    model_state = new_model
                    print(f"  [RIDER ML] Trained XGBoost model on {len(training_data)} samples "
                          f"({new_model['n_positive']} pos, {new_model['n_negative']} neg)")
            else:
                print(f"  [RIDER ML] Only {len(training_data)} training samples, "
                      f"need 50+. Using heuristic.")

    # Now run the same scan as base, but with ML probability
    active_picks = _load_json(ACTIVE_PICKS_PATH)
    if not active_picks or not isinstance(active_picks, list):
        return []

    candidates = []
    for p in active_picks:
        if not isinstance(p, dict):
            continue
        direction = p.get("direction", p.get("signal_type", "")).upper()
        if "BUY" in direction or "LONG" in direction:
            direction = "LONG"
        elif "SELL" in direction or "SHORT" in direction:
            direction = "SHORT"
        else:
            continue

        unrealized = float(p.get("unrealized_pnl_pct", 0) or 0)
        mfe = float(p.get("mfe", 0) or 0)

        if unrealized >= MIN_UNREALIZED_PNL or mfe >= MIN_UNREALIZED_PNL:
            p["_direction"] = direction
            p["_unrealized"] = unrealized
            p["_mfe"] = mfe
            candidates.append(p)

    if not candidates:
        return []

    live_prices = _fetch_live_prices()
    signals = []
    now = datetime.now(timezone.utc)

    for pick in candidates:
        symbol = pick.get("symbol", "")
        direction = pick["_direction"]
        entry_price = float(pick.get("entry_price", 0) or 0)
        tp = float(pick.get("take_profit", 0) or 0)
        sl = float(pick.get("stop_loss", 0) or 0)
        mfe = pick["_mfe"]
        unrealized = pick["_unrealized"]
        confidence_at_entry = float(pick.get("confidence", 0) or 0)
        hold_days = int(pick.get("hold_days", 0) or 0)

        if entry_price <= 0 or tp <= 0:
            continue

        if direction == "LONG":
            tp_pct = (tp - entry_price) / entry_price if entry_price > 0 else 0
        else:
            tp_pct = (entry_price - tp) / entry_price if entry_price > 0 else 0
        mfe_tp_ratio = mfe / tp_pct if tp_pct > 0 else 0

        norm_sym = _normalize_symbol(symbol)
        current_price = live_prices.get(norm_sym, 0)
        if current_price <= 0:
            current_price = float(pick.get("current_price", 0) or 0)
        if current_price <= 0:
            continue

        created_at = _parse_ts(pick.get("created_at", pick.get("timestamp", "")))
        hours_held = (now - created_at).total_seconds() / 3600 if created_at else 24
        hours_held = max(hours_held, 0.5)
        pnl_velocity = unrealized / hours_held

        candles = _fetch_klines(symbol, "1h", 30)
        bar_close = _bar_close_confirmation(candles, direction) if candles else {
            "score": 0.5, "details": "No candle data"
        }
        price_pred = _predict_price_direction(candles) if candles else {
            "direction": "NEUTRAL", "slope": 0, "r_squared": 0,
            "predicted_change_pct": 0, "acceleration": 0
        }
        rsi = _compute_rsi([c["close"] for c in candles]) if candles and len(candles) > 14 else 50.0

        features = {
            "mfe_tp_ratio": mfe_tp_ratio,
            "bar_close_score": bar_close["score"],
            "predicted_change_pct": price_pred["predicted_change_pct"],
            "confidence_at_entry": confidence_at_entry,
            "price_acceleration": price_pred["acceleration"],
            "rsi": rsi,
            "hold_days": hold_days,
            "price_r_squared": price_pred["r_squared"],
            "unrealized_pnl_pct": unrealized,
            "pnl_velocity": pnl_velocity,
            "direction": direction,
        }

        # Use ML model if available, otherwise heuristic
        if model_state and model_state.get("model_type") == "xgboost":
            prob = _compute_continuation_probability_ml(features, model_state)
            model_used = "xgboost"
        else:
            prob = _compute_continuation_probability_heuristic(features)
            model_used = "heuristic"

        action = _determine_action(prob, features)

        if action in ("HOLD", "ADD"):
            if direction == "LONG":
                new_entry = current_price
                new_tp = tp
                new_sl = max(sl, entry_price * 1.005)
                signal_type = "BUY"
            else:
                new_entry = current_price
                new_tp = tp
                new_sl = min(sl, entry_price * 0.995)
                signal_type = "SELL"

            rr = (abs(new_tp - new_entry) / abs(new_entry - new_sl)
                  if abs(new_entry - new_sl) > 0 else 0)

            signals.append({
                "strategy": "momentum_rider_ml",
                "symbol": symbol,
                "category": pick.get("category", "crypto"),
                "signal_type": signal_type,
                "direction": direction,
                "entry_price": round(new_entry, 8),
                "take_profit": round(new_tp, 8),
                "stop_loss": round(new_sl, 8),
                "confidence": round(prob, 4),
                "risk_reward": round(rr, 2),
                "reason": (f"Momentum rider ML ({action}, {model_used}): {symbol} at "
                           f"+{unrealized*100:.1f}% unrealized, "
                           f"MFE/TP={mfe_tp_ratio:.0%}, bar={bar_close['score']:.2f}, "
                           f"pred={price_pred['direction']}, RSI={rsi:.0f}. "
                           f"P(continuation)={prob:.0%}."),
                "timestamp": now.isoformat(),
                "rider_action": action,
                "rider_probability": round(prob, 4),
                "rider_model": model_used,
                "rider_features": {k: round(v, 4) if isinstance(v, float) else v
                                   for k, v in features.items()},
                "original_pick_id": pick.get("id", ""),
            })
        else:
            print(f"  [RIDER ML] {symbol}: {action} (prob={prob:.0%}, model={model_used})")

    return signals


def _build_training_data(closed_picks: list) -> list:
    """
    Build training data from closed picks for ML model.

    For each closed pick that had MFE >= 3%, create a training sample
    with features and target (1 = hit TP, 0 = reversed/SL hit).
    """
    training_data = []

    for p in closed_picks:
        if not isinstance(p, dict):
            continue

        direction = p.get("direction", p.get("signal_type", "")).upper()
        if "BUY" in direction or "LONG" in direction:
            direction = "LONG"
        elif "SELL" in direction or "SHORT" in direction:
            direction = "SHORT"
        else:
            continue

        mfe = float(p.get("mfe", 0) or 0)
        if mfe < MIN_UNREALIZED_PNL:
            continue  # only train on picks that reached our threshold

        entry_price = float(p.get("entry_price", 0) or 0)
        tp = float(p.get("take_profit", 0) or 0)
        pnl_pct = float(p.get("pnl_pct", 0) or 0)
        status = p.get("status", "").upper()

        if entry_price <= 0 or tp <= 0:
            continue

        # Compute features from what we know at close time
        if direction == "LONG":
            tp_pct = (tp - entry_price) / entry_price
        else:
            tp_pct = (entry_price - tp) / entry_price
        mfe_tp_ratio = mfe / tp_pct if tp_pct > 0 else 0

        confidence_at_entry = float(p.get("confidence", 0) or 0)
        hold_days = int(p.get("hold_days", 0) or 0)
        rr = float(p.get("risk_reward", 0) or 0)
        mae = float(p.get("mae", 0) or 0)

        # Target: did it hit TP?
        won = status in ("WON", "WIN", "TP_HIT") or pnl_pct > 0

        # Approximate features (we don't have candle data for historical picks,
        # so use what we have)
        training_data.append({
            "mfe_tp_ratio": mfe_tp_ratio,
            "bar_close_score": 0.5,  # unknown for historical
            "predicted_change_pct": 0,  # unknown
            "confidence_at_entry": confidence_at_entry,
            "price_acceleration": 0,  # unknown
            "rsi": 50,  # unknown
            "hold_days": hold_days,
            "price_r_squared": 0,  # unknown
            "unrealized_pnl_pct": mfe,  # use MFE as proxy
            "pnl_velocity": mfe / max(hold_days * 24, 1),  # approximate
            "target": 1 if won else 0,
        })

    return training_data


# ---------------------------------------------------------------------
# Backtest
# ---------------------------------------------------------------------

def backtest_momentum_rider() -> dict:
    """
    Backtest the momentum rider strategy on historical closed picks.

    For each closed pick that reached +3% MFE:
    - Compute features at the point it was at +3%
    - Run heuristic model to get continuation probability
    - Check if the pick actually hit TP or reversed
    - Calculate accuracy, precision, recall

    Returns:
        dict with backtest results
    """
    closed_picks = _load_json(CLOSED_PICKS_PATH)
    if not closed_picks or not isinstance(closed_picks, list):
        return {"error": "No closed picks data found"}

    training_data = _build_training_data(closed_picks)
    if not training_data:
        return {"error": "No picks with sufficient MFE data"}

    # Run heuristic model on each
    results = []
    for sample in training_data:
        prob = _compute_continuation_probability_heuristic(sample)
        action = _determine_action(prob, sample)
        predicted_hold = action in ("HOLD", "ADD")
        actual_won = sample["target"] == 1

        results.append({
            "mfe_tp_ratio": round(sample["mfe_tp_ratio"], 4),
            "confidence_at_entry": sample["confidence_at_entry"],
            "hold_days": sample["hold_days"],
            "unrealized_pnl_pct": round(sample["unrealized_pnl_pct"], 4),
            "continuation_prob": round(prob, 4),
            "action": action,
            "predicted_hold": predicted_hold,
            "actual_won": actual_won,
            "correct": predicted_hold == actual_won,
        })

    # Calculate metrics
    n_total = len(results)
    n_correct = sum(1 for r in results if r["correct"])
    accuracy = n_correct / n_total if n_total > 0 else 0

    # Precision: of those we said HOLD/ADD, how many actually won?
    predicted_holds = [r for r in results if r["predicted_hold"]]
    true_positives = sum(1 for r in predicted_holds if r["actual_won"])
    precision = true_positives / len(predicted_holds) if predicted_holds else 0

    # Recall: of those that actually won, how many did we say HOLD/ADD?
    actual_wins = [r for r in results if r["actual_won"]]
    recall = true_positives / len(actual_wins) if actual_wins else 0

    # F1
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    # Breakdown by action
    action_counts = {}
    for r in results:
        a = r["action"]
        if a not in action_counts:
            action_counts[a] = {"total": 0, "correct": 0, "win_rate": 0}
        action_counts[a]["total"] += 1
        if r["correct"]:
            action_counts[a]["correct"] += 1
    for a in action_counts:
        ac = action_counts[a]
        ac["win_rate"] = round(ac["correct"] / ac["total"], 4) if ac["total"] > 0 else 0

    # Breakdown by MFE/TP ratio bucket
    mfe_buckets = {"0-30%": [], "30-50%": [], "50-70%": [], "70-100%": [], "100%+": []}
    for r in results:
        ratio = r["mfe_tp_ratio"]
        if ratio < 0.30:
            mfe_buckets["0-30%"].append(r)
        elif ratio < 0.50:
            mfe_buckets["30-50%"].append(r)
        elif ratio < 0.70:
            mfe_buckets["50-70%"].append(r)
        elif ratio < 1.0:
            mfe_buckets["70-100%"].append(r)
        else:
            mfe_buckets["100%+"].append(r)

    bucket_stats = {}
    for bucket, items in mfe_buckets.items():
        if items:
            n_won = sum(1 for r in items if r["actual_won"])
            bucket_stats[bucket] = {
                "count": len(items),
                "win_rate": round(n_won / len(items), 4),
                "avg_prob": round(np.mean([r["continuation_prob"] for r in items]), 4),
            }

    backtest_output = {
        "backtest_timestamp": datetime.now(timezone.utc).isoformat(),
        "strategy": "momentum_rider",
        "total_samples": n_total,
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "action_breakdown": action_counts,
        "mfe_bucket_stats": bucket_stats,
        "individual_results": results,
        "model_type": "heuristic",
        "notes": (
            "Backtest on historical closed picks. Features are approximate since "
            "we lack real-time candle data for historical picks. Bar close score "
            "and price prediction default to neutral (0.5 / 0). Live performance "
            "will be better due to real candle confirmation."
        ),
    }

    # Save results
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(RIDER_BACKTEST_PATH, "w", encoding="utf-8") as f:
        json.dump(backtest_output, f, indent=2, default=str)
    print(f"  [RIDER BACKTEST] Results saved to: {RIDER_BACKTEST_PATH}")

    return backtest_output


# ---------------------------------------------------------------------
# Strategy Registration
# ---------------------------------------------------------------------

MOMENTUM_RIDER_STRATEGIES = {
    "momentum_rider_base": scan_active_for_riders,
    "momentum_rider_ml": scan_active_for_riders_ml,
}


if __name__ == "__main__":
    print("=" * 60)
    print("  MOMENTUM RIDER -- Backtest")
    print("=" * 60)
    result = backtest_momentum_rider()
    print(f"\n  Samples: {result.get('total_samples', 0)}")
    print(f"  Accuracy: {result.get('accuracy', 0):.1%}")
    print(f"  Precision: {result.get('precision', 0):.1%}")
    print(f"  Recall: {result.get('recall', 0):.1%}")
    print(f"  F1: {result.get('f1_score', 0):.1%}")
    print(f"\n  Action breakdown:")
    for a, s in result.get("action_breakdown", {}).items():
        print(f"    {a}: {s['total']} picks, {s['win_rate']:.0%} correct")
    print(f"\n  MFE/TP bucket stats:")
    for b, s in result.get("mfe_bucket_stats", {}).items():
        print(f"    {b}: {s['count']} picks, {s['win_rate']:.0%} actual WR, avg prob {s['avg_prob']:.0%}")
