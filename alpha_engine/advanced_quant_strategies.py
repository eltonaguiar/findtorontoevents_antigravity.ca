"""
ALPHA_ENGINE -- Advanced Quantitative Strategies
=================================================
5 uncorrelated algorithms from 100_ALGORITHMS_MASTER_CATALOG.md.

AQ1: Beta-Neutral Arbitrage (#24, 60-66% WR) - Frazzini & Pedersen (2014)
AQ2: Volatility Arbitrage (#25, 59-65% WR) - Sinclair (2013)
AQ3: Correlation Breakdown (#23, 55-62% WR) - Kritzman et al. (2011)
AQ4: Kernel Density Estimation Bands (#14, 60-66% WR) - Silverman (1986)
AQ5: Poisson Event Trading (#12, 52-58% WR) - Cont & Tankov (2004)
"""

from __future__ import annotations

import json
import logging
import math
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd

from config import CRYPTO_SYMBOLS
from indicators import rsi, atr, sma, volume_ratio

logger = logging.getLogger(__name__)


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _smart_round(v):
    if v == 0:
        return 0.0
    av = abs(v)
    if av >= 100:
        return round(v, 2)
    if av >= 1:
        return round(v, 4)
    if av >= 0.01:
        return round(v, 6)
    return round(v, 10)


def _get_category(symbol):
    info = CRYPTO_SYMBOLS.get(symbol, {})
    return info.get("cat", "crypto")


def _fetch_json(url, timeout=8):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/2.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception:
        return None


def _atr_tp_sl(close, high, low, tp_mult=2.0, sl_mult=1.5, atr_period=14):
    atr_val = atr(high, low, close, atr_period)
    current_atr = float(atr_val.iloc[-1])
    price = float(close.iloc[-1])
    tp = price + tp_mult * current_atr
    sl = price - sl_mult * current_atr
    return _smart_round(price), _smart_round(tp), _smart_round(sl)


def _atr_tp_sl_short(close, high, low, tp_mult=2.0, sl_mult=1.5, atr_period=14):
    atr_val = atr(high, low, close, atr_period)
    current_atr = float(atr_val.iloc[-1])
    price = float(close.iloc[-1])
    tp = price - tp_mult * current_atr
    sl = price + sl_mult * current_atr
    return _smart_round(price), _smart_round(tp), _smart_round(sl)


def _make_pick(symbol, direction, entry, tp, sl, confidence, strategy, reason=""):
    return {
        "symbol": symbol,
        "direction": direction,
        "entry": entry,
        "tp": tp,
        "sl": sl,
        "confidence": round(confidence, 3),
        "strategy": strategy,
        "asset_class": _get_category(symbol),
        "timestamp": _now_iso(),
        "reason": reason,
    }


# =========================================================================
# AQ1: Beta-Neutral Arbitrage (#24)
# Frazzini & Pedersen (2014) "Betting Against Beta", JFE
# =========================================================================

def _compute_rolling_beta(alt_returns, btc_returns, window=20):
    n = len(alt_returns)
    betas = np.full(n, np.nan)
    for i in range(window, n):
        x = btc_returns[i - window:i]
        y = alt_returns[i - window:i]
        x_mean = np.mean(x)
        cov = np.sum((x - x_mean) * (y - np.mean(y)))
        var = np.sum((x - x_mean) ** 2)
        if var > 1e-20:
            betas[i] = cov / var
    return betas


def beta_neutral_arbitrage(data, context=None):
    """Long low-beta alpha, short high-beta decay vs BTC."""
    signals = []
    btc_df = data.get("BTCUSDT") or data.get("BTC-USD")
    if btc_df is None or len(btc_df) < 30:
        return signals
    btc_close = btc_df["Close"].values.astype(float)
    btc_returns = np.diff(np.log(np.maximum(btc_close, 1e-10)))

    for symbol, df in data.items():
        if symbol in ("BTCUSDT", "BTC-USD"):
            continue
        if _get_category(symbol) != "crypto":
            continue
        if df is None or len(df) < 30:
            continue
        try:
            close, high, low = df["Close"], df["High"], df["Low"]
            alt_close = close.values.astype(float)
            min_len = min(len(btc_returns), len(alt_close) - 1)
            if min_len < 25:
                continue
            alt_rets = np.diff(np.log(np.maximum(alt_close[-min_len - 1:], 1e-10)))
            btc_rets = btc_returns[-min_len:]
            betas = _compute_rolling_beta(alt_rets, btc_rets, window=20)
            cb = betas[-1]
            if np.isnan(cb):
                continue
            if len(alt_close) < 11:
                continue
            mom10 = np.log(alt_close[-1] / alt_close[-11])
            if cb < 0.5 and mom10 > 0.02:
                entry, tp, sl = _atr_tp_sl(close, high, low, tp_mult=2.5, sl_mult=1.5)
                conf = min(0.66, 0.55 + (0.5 - cb) * 0.15)
                signals.append(_make_pick(symbol, "BUY", entry, tp, sl, conf,
                    "beta_neutral_arbitrage",
                    f"Low-beta BUY: beta={cb:.2f}, mom10d={mom10:.3f}"))
            elif cb > 1.8 and mom10 < -0.02:
                entry, tp, sl = _atr_tp_sl_short(close, high, low, tp_mult=2.5, sl_mult=1.5)
                conf = min(0.66, 0.55 + (cb - 1.8) * 0.1)
                signals.append(_make_pick(symbol, "SELL", entry, tp, sl, conf,
                    "beta_neutral_arbitrage",
                    f"High-beta SELL: beta={cb:.2f}, mom10d={mom10:.3f}"))
        except Exception as e:
            logger.debug("beta_neutral_arbitrage %s error: %s", symbol, e)
    return signals


# =========================================================================
# AQ2: Volatility Arbitrage (#25)
# Sinclair (2013) "Volatility Trading"; Carr & Wu (2009)
# =========================================================================

def _realized_vol(returns, window):
    n = len(returns)
    vol = np.full(n, np.nan)
    for i in range(window, n):
        vol[i] = np.std(returns[i - window:i], ddof=1) * math.sqrt(365)
    return vol


def volatility_arbitrage(data, context=None):
    """Trade realized vol ratio (RV5/RV30) extremes."""
    signals = []
    for symbol, df in data.items():
        if _get_category(symbol) != "crypto":
            continue
        if df is None or len(df) < 40:
            continue
        try:
            close, high, low = df["Close"], df["High"], df["Low"]
            prices = close.values.astype(float)
            log_rets = np.diff(np.log(np.maximum(prices, 1e-10)))
            rv5 = _realized_vol(log_rets, 5)
            rv30 = _realized_vol(log_rets, 30)
            if np.isnan(rv5[-1]) or np.isnan(rv30[-1]) or rv30[-1] < 1e-10:
                continue
            vr = rv5[-1] / rv30[-1]
            rsi_vals = rsi(close, 14)
            cr = float(rsi_vals.iloc[-1]) if not pd.isna(rsi_vals.iloc[-1]) else 50.0
            if vr < 0.5 and cr < 60:
                entry, tp, sl = _atr_tp_sl(close, high, low, tp_mult=3.0, sl_mult=1.5)
                conf = min(0.65, 0.52 + (0.5 - vr) * 0.2)
                signals.append(_make_pick(symbol, "BUY", entry, tp, sl, conf,
                    "volatility_arbitrage",
                    f"Vol compression BUY: vr={vr:.2f}, RV5={rv5[-1]:.1%}, RV30={rv30[-1]:.1%}, RSI={cr:.0f}"))
            elif vr > 2.0 and cr > 70:
                entry, tp, sl = _atr_tp_sl_short(close, high, low, tp_mult=2.5, sl_mult=1.5)
                conf = min(0.65, 0.52 + (vr - 2.0) * 0.05)
                signals.append(_make_pick(symbol, "SELL", entry, tp, sl, conf,
                    "volatility_arbitrage",
                    f"Vol spike SELL: vr={vr:.2f}, RSI={cr:.0f}"))
            elif vr > 2.0 and cr < 30:
                entry, tp, sl = _atr_tp_sl(close, high, low, tp_mult=3.0, sl_mult=2.0)
                conf = min(0.62, 0.50 + (vr - 2.0) * 0.04)
                signals.append(_make_pick(symbol, "BUY", entry, tp, sl, conf,
                    "volatility_arbitrage",
                    f"Vol panic BUY: vr={vr:.2f}, RSI={cr:.0f}"))
        except Exception as e:
            logger.debug("volatility_arbitrage %s error: %s", symbol, e)
    return signals


# =========================================================================
# AQ3: Correlation Breakdown (#23)
# Kritzman et al. (2011); Cont (2001)
# =========================================================================

def _rolling_correlation(x, y, window=20):
    n = min(len(x), len(y))
    corr = np.full(n, np.nan)
    for i in range(window, n):
        xw, yw = x[i - window:i], y[i - window:i]
        if np.std(xw) < 1e-20 or np.std(yw) < 1e-20:
            corr[i] = 0.0
            continue
        corr[i] = np.corrcoef(xw, yw)[0, 1]
    return corr


def correlation_breakdown(data, context=None):
    """Detect BTC-alt decorrelation regime shifts."""
    signals = []
    btc_df = data.get("BTCUSDT") or data.get("BTC-USD")
    if btc_df is None or len(btc_df) < 40:
        return signals
    btc_close = btc_df["Close"].values.astype(float)
    btc_returns = np.diff(np.log(np.maximum(btc_close, 1e-10)))

    for symbol, df in data.items():
        if symbol in ("BTCUSDT", "BTC-USD"):
            continue
        if _get_category(symbol) != "crypto":
            continue
        if df is None or len(df) < 40:
            continue
        try:
            close, high, low = df["Close"], df["High"], df["Low"]
            ac = close.values.astype(float)
            ml = min(len(btc_returns), len(ac) - 1)
            if ml < 30:
                continue
            ar = np.diff(np.log(np.maximum(ac[-ml - 1:], 1e-10)))
            br = btc_returns[-ml:]
            corrs = _rolling_correlation(ar, br, window=20)
            cc = corrs[-1]
            if np.isnan(cc):
                continue
            rc = corrs[-11:-1]
            rc = rc[~np.isnan(rc)]
            if len(rc) < 5:
                continue
            avg_c = np.mean(rc)
            cd = avg_c - cc
            if len(ac) < 6:
                continue
            m5 = (ac[-1] / ac[-6]) - 1.0
            if cd > 0.4 and cc < 0.3 and m5 > 0.01:
                entry, tp, sl = _atr_tp_sl(close, high, low, tp_mult=2.5, sl_mult=1.5)
                conf = min(0.62, 0.50 + cd * 0.15)
                signals.append(_make_pick(symbol, "BUY", entry, tp, sl, conf,
                    "correlation_breakdown",
                    f"Decorrelation BUY: corr={cc:.2f} (was {avg_c:.2f}), mom5d={m5:.3f}"))
            elif cd > 0.4 and cc < 0.3 and m5 < -0.01:
                entry, tp, sl = _atr_tp_sl_short(close, high, low, tp_mult=2.5, sl_mult=1.5)
                conf = min(0.60, 0.48 + cd * 0.12)
                signals.append(_make_pick(symbol, "SELL", entry, tp, sl, conf,
                    "correlation_breakdown",
                    f"Decorrelation SELL: corr={cc:.2f} (was {avg_c:.2f}), mom5d={m5:.3f}"))
            elif cc > 0.85 and avg_c < 0.5 and m5 < -0.03:
                entry, tp, sl = _atr_tp_sl(close, high, low, tp_mult=2.0, sl_mult=1.5)
                conf = min(0.58, 0.48 + (cc - 0.85) * 0.5)
                signals.append(_make_pick(symbol, "BUY", entry, tp, sl, conf,
                    "correlation_breakdown",
                    f"Herding catch-up BUY: corr={cc:.2f} (was {avg_c:.2f}), mom5d={m5:.3f}"))
        except Exception as e:
            logger.debug("correlation_breakdown %s error: %s", symbol, e)
    return signals


# =========================================================================
# AQ4: Kernel Density Estimation Bands (#14)
# Silverman (1986) "Density Estimation for Statistics"
# =========================================================================

def _erf_array(x):
    sign = np.sign(x)
    x = np.abs(x)
    a1, a2, a3, a4, a5 = 0.254829592, -0.284496736, 1.421413741, -1.453152027, 1.061405429
    p = 0.3275911
    t = 1.0 / (1.0 + p * x)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * np.exp(-x * x)
    return sign * y


def _gaussian_kde_density(pts, ev, bw=None):
    n = len(pts)
    if n < 5:
        return 0.0
    if bw is None:
        std = np.std(pts, ddof=1)
        iqr = np.percentile(pts, 75) - np.percentile(pts, 25)
        sp = min(std, iqr / 1.34) if iqr > 0 else std
        if sp < 1e-20:
            return 0.0
        bw = 0.9 * sp * (n ** (-0.2))
    if bw < 1e-20:
        return 0.0
    u = (ev - pts) / bw
    return float(np.mean(np.exp(-0.5 * u * u) / math.sqrt(2 * math.pi)) / bw)


def _kde_percentile(pts, ev):
    n = len(pts)
    if n < 5:
        return 0.5
    std = np.std(pts, ddof=1)
    if std < 1e-20:
        return 0.5
    iqr = np.percentile(pts, 75) - np.percentile(pts, 25)
    sp = min(std, iqr / 1.34) if iqr > 0 else std
    if sp < 1e-20:
        return 0.5
    bw = 0.9 * sp * (n ** (-0.2))
    if bw < 1e-20:
        return 0.5
    u = (ev - pts) / bw
    cdf_vals = 0.5 * (1 + _erf_array(u / math.sqrt(2)))
    return float(np.mean(cdf_vals))


def kernel_density_bands(data, context=None):
    """Non-parametric KDE probability bands on 30-day returns."""
    signals = []
    for symbol, df in data.items():
        if _get_category(symbol) != "crypto":
            continue
        if df is None or len(df) < 35:
            continue
        try:
            close, high, low = df["Close"], df["High"], df["Low"]
            prices = close.values.astype(float)
            lr = np.diff(np.log(np.maximum(prices, 1e-10)))
            if len(lr) < 30:
                continue
            hist = lr[-30:]
            cur = lr[-1]
            den = _gaussian_kde_density(hist, cur)
            pct = _kde_percentile(hist, cur)
            med_den = _gaussian_kde_density(hist, np.median(hist))
            rd = den / med_den if med_den > 1e-10 else 1.0
            if pct < 0.05 and cur < 0:
                entry, tp, sl = _atr_tp_sl(close, high, low, tp_mult=2.5, sl_mult=1.5)
                conf = min(0.66, 0.52 + (0.05 - pct) * 3.0)
                signals.append(_make_pick(symbol, "BUY", entry, tp, sl, conf,
                    "kernel_density_bands",
                    f"KDE tail BUY: pctile={pct:.1%}, density_ratio={rd:.2f}"))
            elif pct > 0.95 and cur > 0:
                entry, tp, sl = _atr_tp_sl_short(close, high, low, tp_mult=2.5, sl_mult=1.5)
                conf = min(0.66, 0.52 + (pct - 0.95) * 3.0)
                signals.append(_make_pick(symbol, "SELL", entry, tp, sl, conf,
                    "kernel_density_bands",
                    f"KDE tail SELL: pctile={pct:.1%}, density_ratio={rd:.2f}"))
            elif rd < 0.3 and cur > 0.03 and 0.80 < pct < 0.95:
                entry, tp, sl = _atr_tp_sl(close, high, low, tp_mult=3.0, sl_mult=2.0)
                conf = min(0.60, 0.48 + (0.3 - rd) * 0.3)
                signals.append(_make_pick(symbol, "BUY", entry, tp, sl, conf,
                    "kernel_density_bands",
                    f"KDE new-mode BUY: low density ({rd:.2f}), return={cur:.3f}"))
        except Exception as e:
            logger.debug("kernel_density_bands %s error: %s", symbol, e)
    return signals


# =========================================================================
# AQ5: Poisson Event Trading (#12)
# Cont & Tankov (2004) "Financial Modelling With Jump Processes"
# =========================================================================

def poisson_event_trading(data, context=None):
    """Exploit large-move (>2 sigma) frequency anomalies via Poisson model."""
    signals = []
    for symbol, df in data.items():
        if _get_category(symbol) != "crypto":
            continue
        if df is None or len(df) < 50:
            continue
        try:
            close, high, low = df["Close"], df["High"], df["Low"]
            prices = close.values.astype(float)
            lr = np.diff(np.log(np.maximum(prices, 1e-10)))
            if len(lr) < 45:
                continue
            sigma = np.std(lr[-45:], ddof=1)
            if sigma < 1e-10:
                continue
            thr = 2.0 * sigma
            events = (np.abs(lr) > thr).astype(float)
            lw = min(30, len(events))
            lam = np.sum(events[-lw:]) / (lw / 5.0)
            se = np.sum(events[-5:])
            l5 = lr[-5:]
            big = l5[np.abs(l5) > thr]
            ld = "up" if (len(big) > 0 and big[-1] > 0) else ("down" if len(big) > 0 else "none")
            if se >= 3 and lam < 2.0:
                if ld == "up":
                    entry, tp, sl = _atr_tp_sl_short(close, high, low, tp_mult=2.0, sl_mult=1.5)
                    conf = min(0.58, 0.48 + se * 0.03)
                    signals.append(_make_pick(symbol, "SELL", entry, tp, sl, conf,
                        "poisson_event_trading",
                        f"Event cluster SELL: {int(se)} events/5d (lambda={lam:.1f}), last=UP"))
                elif ld == "down":
                    entry, tp, sl = _atr_tp_sl(close, high, low, tp_mult=2.5, sl_mult=1.5)
                    conf = min(0.58, 0.48 + se * 0.03)
                    signals.append(_make_pick(symbol, "BUY", entry, tp, sl, conf,
                        "poisson_event_trading",
                        f"Event cluster BUY: {int(se)} events/5d (lambda={lam:.1f}), last=DOWN"))
            elif np.sum(events[-10:]) == 0 and lam > 0.5:
                mm = lr[-3:].sum()
                if mm > 0.005:
                    entry, tp, sl = _atr_tp_sl(close, high, low, tp_mult=3.0, sl_mult=1.5)
                    conf = min(0.55, 0.45 + lam * 0.05)
                    signals.append(_make_pick(symbol, "BUY", entry, tp, sl, conf,
                        "poisson_event_trading",
                        f"Event drought BUY: 0 events/10d (lambda={lam:.1f})"))
                elif mm < -0.005:
                    entry, tp, sl = _atr_tp_sl_short(close, high, low, tp_mult=3.0, sl_mult=1.5)
                    conf = min(0.55, 0.45 + lam * 0.05)
                    signals.append(_make_pick(symbol, "SELL", entry, tp, sl, conf,
                        "poisson_event_trading",
                        f"Event drought SELL: 0 events/10d (lambda={lam:.1f})"))
        except Exception as e:
            logger.debug("poisson_event_trading %s error: %s", symbol, e)
    return signals


# =========================================================================
# Strategy Registry
# =========================================================================

ADVANCED_QUANT_STRATEGIES = {
    "beta_neutral_arbitrage": beta_neutral_arbitrage,
    "volatility_arbitrage": volatility_arbitrage,
    "correlation_breakdown": correlation_breakdown,
    "kernel_density_bands": kernel_density_bands,
    "poisson_event_trading": poisson_event_trading,
}
