#!/usr/bin/env python3
"""Mercury 2 Regime-Aware Trade Scorer — integrates with quality_gates.py.
Stdlib only + Binance 3+ mirror failover. Computes regime, features,
class-specific weights, logistic transform, regime/risk adjustments."""

import json, math, os, ssl, sys, urllib.error, urllib.request
from typing import Any, Dict

if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# -- Binance API helpers (3+ mirror failover per CLAUDE.md) ----------------
BINANCE_MIRRORS = [
    "https://api.binance.com", "https://api1.binance.com",
    "https://api2.binance.com", "https://api3.binance.com",
    "https://data-api.binance.vision",
]

def _fetch_json(url: str, timeout: int = 10) -> Any:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return json.loads(urllib.request.urlopen(req, timeout=timeout, context=ctx).read())

def _fetch_price(symbol: str) -> float:
    for m in BINANCE_MIRRORS:
        try:
            return float(_fetch_json(f"{m}/api/v3/ticker/price?symbol={symbol}")["price"])
        except Exception:
            continue
    return 0.0

def _fetch_klines(symbol: str, interval: str = "1d", limit: int = 60) -> list:
    for m in BINANCE_MIRRORS:
        try:
            return _fetch_json(f"{m}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}")
        except Exception:
            continue
    return []

# -- Regime detection ------------------------------------------------------
REGIME_MULTIPLIERS = {"bull": 1.1, "bear": 0.9, "high_vol": 0.8}
HIGH_VOL_THRESHOLD = 0.04  # daily returns std > 4% => high_vol

def _detect_regime(closes: list) -> str:
    """bull: SMA10>SMA50, bear: SMA10<=SMA50, high_vol: 20d std > threshold."""
    if len(closes) < 50:
        return "bear"
    sma10 = sum(closes[-10:]) / 10
    sma50 = sum(closes[-50:]) / 50
    rets = [(closes[i] / closes[i - 1]) - 1 for i in range(-20, 0)]
    mean_r = sum(rets) / len(rets)
    std_r = math.sqrt(sum((r - mean_r) ** 2 for r in rets) / len(rets))
    if std_r > HIGH_VOL_THRESHOLD:
        return "high_vol"
    return "bull" if sma10 > sma50 else "bear"

# -- Feature computation ---------------------------------------------------
def _compute_features(closes: list, volumes: list,
                      highs: list, lows: list) -> Dict[str, float]:
    """Returns {ret_5d, ret_20d, atr_ratio, vol_ratio, rsi_norm}."""
    if len(closes) < 21 or len(highs) < 14:
        return {"ret_5d": 0, "ret_20d": 0, "atr_ratio": 0,
                "vol_ratio": 0, "rsi_norm": 0.5}
    ret_5d = (closes[-1] / closes[-6]) - 1 if closes[-6] else 0
    ret_20d = (closes[-1] / closes[-21]) - 1 if closes[-21] else 0
    # ATR(14) / price
    trs = [max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]),
               abs(lows[i] - closes[i - 1])) for i in range(-14, 0)]
    atr_ratio = (sum(trs) / 14) / closes[-1] if closes[-1] else 0
    # Volume ratio: 5d avg / 20d avg
    vol5 = sum(volumes[-5:]) / 5 if volumes[-5:] else 1
    vol20 = sum(volumes[-20:]) / 20 if volumes[-20:] else 1
    vol_ratio = vol5 / vol20 if vol20 > 0 else 1.0
    # RSI(14) normalised to [0,1]
    deltas = [closes[i] - closes[i - 1] for i in range(-14, 0)]
    avg_gain = sum(d for d in deltas if d > 0) / 14
    avg_loss = sum(-d for d in deltas if d < 0) / 14
    if avg_loss == 0:
        rsi_norm = 1.0
    else:
        rs = avg_gain / avg_loss
        rsi_norm = rs / (1 + rs)
    return {"ret_5d": ret_5d, "ret_20d": ret_20d, "atr_ratio": atr_ratio,
            "vol_ratio": vol_ratio, "rsi_norm": rsi_norm}

# -- Class-specific weights (from closed-pick analysis) --------------------
WEIGHTS = {
    "CRYPTO": {"ret_5d": 0.30, "ret_20d": 0.25, "atr_ratio": 0.10,
               "vol_ratio": 0.15, "rsi_norm": 0.20},
    "EQUITY": {"ret_5d": 0.15, "ret_20d": 0.15, "atr_ratio": 0.15,
               "vol_ratio": 0.15, "rsi_norm": 0.40},
}
DEFAULT_THRESHOLD = 0.55

# -- Helpers ---------------------------------------------------------------
def _logistic(x: float) -> float:
    x = max(-10, min(10, x))
    return 1.0 / (1.0 + math.exp(-x))

def _risk_budget_factor(atr_ratio: float, vol_ratio: float) -> float:
    """Penalise high vol / volume spikes. Returns multiplier in [0.7, 1.0]."""
    penalty = (0.15 if atr_ratio > 0.06 else 0) + (0.15 if vol_ratio > 2.5 else 0)
    return max(0.7, 1.0 - penalty)

# -- Core scorer -----------------------------------------------------------
def score_trade(symbol: str, direction: str = "LONG",
                asset_class: str = "CRYPTO") -> dict:
    """Score a trade candidate with regime awareness.
    Returns {"score": float, "regime": str, "accept": bool, "features": dict}
    """
    asset_class, direction = asset_class.upper(), direction.upper()
    klines = _fetch_klines(symbol, interval="1d", limit=60)
    if len(klines) < 21:
        return {"score": 0.0, "regime": "bear", "accept": False,
                "features": {}, "reason": "insufficient_data"}
    closes = [float(k[4]) for k in klines]
    highs = [float(k[2]) for k in klines]
    lows = [float(k[3]) for k in klines]
    volumes = [float(k[5]) for k in klines]
    # 1. Regime
    regime = _detect_regime(closes)
    # 2. Features
    feats = _compute_features(closes, volumes, highs, lows)
    # 3. Weighted raw score
    w = WEIGHTS.get(asset_class, WEIGHTS["CRYPTO"])
    raw = sum(w[k] * feats[k] for k in w)
    if direction == "SHORT":
        raw = -raw  # flip for bearish bias
    # 4. Logistic transform
    prob = _logistic(raw * 10)
    # 5. Regime multiplier (inverted for shorts)
    regime_mult = REGIME_MULTIPLIERS.get(regime, 1.0)
    if direction == "SHORT":
        regime_mult = 2.0 - regime_mult  # bull=0.9, bear=1.1, high_vol=1.2
    adjusted = prob * regime_mult
    # 6. Risk budget factor
    risk_factor = _risk_budget_factor(feats["atr_ratio"], feats["vol_ratio"])
    final_score = round(min(1.0, adjusted * risk_factor), 4)
    return {
        "score": final_score, "regime": regime,
        "accept": final_score >= DEFAULT_THRESHOLD,
        "features": {k: round(v, 6) for k, v in feats.items()},
        "direction": direction, "asset_class": asset_class,
        "regime_multiplier": regime_mult, "risk_factor": round(risk_factor, 4),
    }

# ── Mercury #11: Dynamic TP/SL with regime-adjusted ATR ──────────────
TP_SL_REGIME_MULT = {"bull": 1.2, "bear": 0.8, "high_vol": 0.6}
TP_SL_K = {
    "CRYPTO": {"k_tp": 2.0, "k_sl": 1.2},   # wider TP, tighter SL (tight R:R wins more)
    "EQUITY": {"k_tp": 1.5, "k_sl": 1.0},
    "FOREX":  {"k_tp": 1.3, "k_sl": 0.8},
}


def compute_dynamic_tp_sl(symbol: str, entry_price: float, direction: str,
                          asset_class: str = "CRYPTO") -> dict:
    """Compute regime-adjusted TP/SL using ATR. Mercury AI item #11."""
    klines = _fetch_klines(symbol, "4h", 50)
    if len(klines) < 20:
        return {"error": "insufficient data", "tp": 0, "sl": 0}

    closes = [float(k[4]) for k in klines]
    regime = _detect_regime(closes)

    # ATR(14)
    trs = []
    for i in range(1, len(klines)):
        h, l, c_prev = float(klines[i][2]), float(klines[i][3]), float(klines[i - 1][4])
        trs.append(max(h - l, abs(h - c_prev), abs(l - c_prev)))
    atr = sum(trs[-14:]) / 14 if len(trs) >= 14 else sum(trs) / max(len(trs), 1)

    k = TP_SL_K.get(asset_class.upper(), TP_SL_K["CRYPTO"])
    r_mult = TP_SL_REGIME_MULT.get(regime, 1.0)

    tp_dist = k["k_tp"] * atr * r_mult
    sl_dist = k["k_sl"] * atr * r_mult

    if direction.upper() in ("LONG", "BUY"):
        tp = round(entry_price + tp_dist, 8)
        sl = round(entry_price - sl_dist, 8)
    else:
        tp = round(entry_price - tp_dist, 8)
        sl = round(entry_price + sl_dist, 8)

    return {"tp": tp, "sl": sl, "atr": round(atr, 4), "regime": regime,
            "regime_multiplier": r_mult, "direction": direction.upper()}


if __name__ == "__main__":
    print(json.dumps(score_trade("BTCUSDT", "LONG", "CRYPTO"), indent=2))
    result = compute_dynamic_tp_sl("BTCUSDT", 68500, "SHORT", "CRYPTO")
    print(f"\nDynamic TP/SL: {json.dumps(result, indent=2)}")
