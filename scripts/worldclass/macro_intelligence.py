#!/usr/bin/env python3
"""
Macro Intelligence — FRED Macro Overlay + VIX Term Structure + Cross-Asset Spillover
Fetches free macro data and computes regime scores.

FRED: Yield curve (T10Y2Y), VIX, unemployment, Fed Funds, consumer sentiment
VIX: Term structure contango/backwardation from Yahoo Finance
Cross-Asset: Lagged bond/commodity/VIX returns to predict stock/crypto

Runs via GitHub Actions daily.
"""

import sys
import json
import warnings
import requests
import numpy as np
from datetime import datetime, timedelta

warnings.filterwarnings("ignore")

try:
    import yfinance as yf
except ImportError:
    print("pip install yfinance")
    sys.exit(1)

from config import INTEL_API, ADMIN_KEY


def store_metric(metric_name, asset_class, value, label, metadata=None):
    """Store a metric via PHP API."""
    try:
        data = {
            "action": "store",
            "key": ADMIN_KEY,
            "metric_name": metric_name,
            "asset_class": asset_class,
            "metric_value": str(value),
            "metric_label": label,
        }
        if metadata:
            data["metadata"] = json.dumps(metadata)
        resp = requests.post(INTEL_API, data=data, timeout=15)
        return resp.json().get("ok", False)
    except Exception as e:
        print(f"  Store error: {e}")
        return False


def store_batch(metrics):
    """Store multiple metrics at once."""
    try:
        data = {
            "action": "store_batch",
            "key": ADMIN_KEY,
            "metrics": json.dumps(metrics)
        }
        resp = requests.post(INTEL_API, data=data, timeout=15)
        return resp.json().get("ok", False)
    except Exception as e:
        print(f"  Batch store error: {e}")
        return False


# ════════════════════════════════════════════════════════════════
#  FRED Macro Overlay
# ════════════════════════════════════════════════════════════════

def fetch_fred_via_yahoo():
    """
    Fetch macro indicators using Yahoo Finance as FRED proxy.
    No API key needed. Falls back gracefully.
    """
    indicators = {}

    # Treasury yield curve spread (10Y-2Y)
    try:
        tnx = yf.download("^TNX", period="3mo", interval="1d", progress=False)  # 10Y yield
        twy = yf.download("^IRX", period="3mo", interval="1d", progress=False)  # 13-week T-bill
        if not tnx.empty and not twy.empty:
            y10 = float(tnx["Close"].iloc[-1])
            y3m = float(twy["Close"].iloc[-1])
            spread = y10 - y3m
            indicators["yield_spread"] = spread
            print(f"  Yield Spread (10Y-3M): {spread:.3f}%")
        else:
            print("  Yield data unavailable")
    except Exception as e:
        print(f"  Yield error: {e}")

    # VIX level
    try:
        vix = yf.download("^VIX", period="3mo", interval="1d", progress=False)
        if not vix.empty:
            vix_current = float(vix["Close"].iloc[-1])
            vix_avg = float(vix["Close"].tail(20).mean())
            indicators["vix_current"] = vix_current
            indicators["vix_avg_20d"] = vix_avg
            indicators["vix_ratio"] = vix_current / vix_avg if vix_avg > 0 else 1.0
            print(f"  VIX: {vix_current:.2f} (20d avg: {vix_avg:.2f}, ratio: {indicators['vix_ratio']:.3f})")
    except Exception as e:
        print(f"  VIX error: {e}")

    # Consumer sentiment proxy: AAII survey isn't on Yahoo, use VIX as sentiment
    # Gold as inflation/fear proxy
    try:
        gold = yf.download("GLD", period="3mo", interval="1d", progress=False)
        if not gold.empty and len(gold) > 20:
            gold_return = float((gold["Close"].iloc[-1] / gold["Close"].iloc[-20] - 1) * 100)
            indicators["gold_20d_return"] = gold_return
            print(f"  Gold 20d return: {gold_return:.2f}%")
    except Exception as e:
        print(f"  Gold error: {e}")

    # Dollar strength (DXY proxy)
    try:
        dxy = yf.download("DX-Y.NYB", period="3mo", interval="1d", progress=False)
        if not dxy.empty:
            dxy_current = float(dxy["Close"].iloc[-1])
            dxy_avg = float(dxy["Close"].tail(20).mean())
            indicators["dxy_current"] = dxy_current
            indicators["dxy_20d_change"] = float((dxy_current / dxy_avg - 1) * 100)
            print(f"  DXY: {dxy_current:.2f} (20d change: {indicators['dxy_20d_change']:.2f}%)")
    except Exception as e:
        print(f"  DXY error: {e}")

    return indicators


def compute_macro_score(indicators):
    """
    Compute macro regime score (0-100).
    High = bullish macro environment, Low = bearish.
    Based on Bridgewater's All Weather framework.
    """
    score = 50  # Neutral start
    components = {}

    # Yield curve: positive spread = bullish, inverted = bearish
    if "yield_spread" in indicators:
        spread = indicators["yield_spread"]
        if spread > 1.0:
            adj = min(15, spread * 5)
        elif spread > 0:
            adj = spread * 10
        elif spread > -0.5:
            adj = spread * 15
        else:
            adj = max(-20, spread * 10)
        score += adj
        components["yield_curve"] = round(adj, 2)

    # VIX: low = complacent (slightly bullish), high = fear (bearish)
    if "vix_ratio" in indicators:
        ratio = indicators["vix_ratio"]
        if ratio < 0.85:
            adj = 10   # VIX well below average = calm
        elif ratio < 1.0:
            adj = 5
        elif ratio < 1.3:
            adj = -5
        elif ratio < 1.5:
            adj = -10
        else:
            adj = -15  # VIX spiking = fear
        score += adj
        components["vix"] = round(adj, 2)

    # Gold: rising gold = risk-off (bearish for stocks)
    if "gold_20d_return" in indicators:
        gold_ret = indicators["gold_20d_return"]
        if gold_ret > 5:
            adj = -10
        elif gold_ret > 2:
            adj = -5
        elif gold_ret < -2:
            adj = 5
        else:
            adj = 0
        score += adj
        components["gold"] = round(adj, 2)

    # Dollar: strengthening dollar = mixed (good for US, bad for EM/commodities)
    if "dxy_20d_change" in indicators:
        dxy = indicators["dxy_20d_change"]
        if dxy > 3:
            adj = -5  # Strong dollar = headwind
        elif dxy < -3:
            adj = 5   # Weak dollar = tailwind
        else:
            adj = 0
        score += adj
        components["dollar"] = round(adj, 2)

    score = max(0, min(100, score))

    # Label
    if score >= 65:
        label = "bullish"
    elif score >= 55:
        label = "mildly_bullish"
    elif score >= 45:
        label = "neutral"
    elif score >= 35:
        label = "mildly_bearish"
    else:
        label = "bearish"

    return score, label, components


# ════════════════════════════════════════════════════════════════
#  VIX Term Structure
# ════════════════════════════════════════════════════════════════

def fetch_vix_term_structure():
    """
    Fetch VIX spot vs VIX futures proxy to determine contango/backwardation.
    Uses VIX (spot) and VIX3M (3-month VIX) from Yahoo.
    """
    try:
        vix_spot = yf.download("^VIX", period="5d", interval="1d", progress=False)
        vix_3m = yf.download("^VIX3M", period="5d", interval="1d", progress=False)

        if vix_spot.empty or vix_3m.empty:
            print("  VIX term structure data unavailable")
            return None

        spot = float(vix_spot["Close"].iloc[-1])
        m3 = float(vix_3m["Close"].iloc[-1])

        if m3 == 0:
            return None

        # Ratio: spot / 3-month. > 1.0 = backwardation (fear), < 1.0 = contango (calm)
        ratio = spot / m3

        if ratio > 1.05:
            structure = "backwardation"  # Fear peaking — contrarian BUY
        elif ratio > 0.95:
            structure = "flat"
        else:
            structure = "contango"  # Normal calm market

        result = {
            "vix_spot": round(spot, 2),
            "vix_3m": round(m3, 2),
            "ratio": round(ratio, 4),
            "structure": structure
        }

        print(f"  VIX Spot: {spot:.2f}, VIX3M: {m3:.2f}, Ratio: {ratio:.4f} ({structure})")
        return result

    except Exception as e:
        print(f"  VIX term structure error: {e}")
        return None


# ════════════════════════════════════════════════════════════════
#  Cross-Asset Momentum Spillover
# ════════════════════════════════════════════════════════════════

def compute_cross_asset_signals():
    """
    Compute cross-asset lead-lag signals.
    Science: arXiv 2308.11294 (Network Momentum)
    - Bond-to-equity: positive spillover
    - Equity-to-bond: negative spillover
    - Oil volatility → stocks: negative
    """
    tickers = {
        "SPY": "stocks",
        "TLT": "bonds",
        "GLD": "gold",
        "USO": "oil",
        "BTC-USD": "crypto"
    }

    try:
        data = yf.download(list(tickers.keys()), period="1mo", interval="1d", progress=False)
        if data.empty:
            print("  Cross-asset data unavailable")
            return None

        closes = data["Close"]
        if closes.ndim == 1:
            print("  Cross-asset: insufficient tickers")
            return None

        # Calculate daily returns
        returns = closes.pct_change().dropna()
        if len(returns) < 10:
            print("  Cross-asset: insufficient history")
            return None

        signals = {}

        # Bond-to-equity spillover (1-day lag)
        if "TLT" in returns.columns and "SPY" in returns.columns:
            bond_yesterday = float(returns["TLT"].iloc[-2]) if len(returns) > 1 else 0
            stock_today = float(returns["SPY"].iloc[-1])

            # If bonds rallied yesterday and stocks haven't followed → bullish stock signal
            if bond_yesterday > 0.005 and stock_today < 0.002:
                signals["bond_to_equity"] = {"signal": "bullish", "strength": min(80, abs(bond_yesterday) * 5000)}
            elif bond_yesterday < -0.005 and stock_today > -0.002:
                signals["bond_to_equity"] = {"signal": "bearish", "strength": min(80, abs(bond_yesterday) * 5000)}
            else:
                signals["bond_to_equity"] = {"signal": "neutral", "strength": 0}

        # Oil-to-equity (oil vol spike → bearish stocks)
        if "USO" in returns.columns and "SPY" in returns.columns:
            oil_vol_5d = float(returns["USO"].tail(5).std()) * 100
            oil_vol_20d = float(returns["USO"].tail(20).std()) * 100 if len(returns) >= 20 else oil_vol_5d

            if oil_vol_20d > 0:
                oil_ratio = oil_vol_5d / oil_vol_20d
            else:
                oil_ratio = 1.0

            if oil_ratio > 1.5:
                signals["oil_to_equity"] = {"signal": "bearish", "strength": min(70, (oil_ratio - 1) * 50)}
            else:
                signals["oil_to_equity"] = {"signal": "neutral", "strength": 0}

        # Gold-to-crypto (gold fear → crypto fear usually)
        if "GLD" in returns.columns and "BTC-USD" in returns.columns:
            gold_5d = float(returns["GLD"].tail(5).sum()) * 100
            btc_5d = float(returns["BTC-USD"].tail(5).sum()) * 100

            if gold_5d > 2 and btc_5d < 0:
                signals["gold_to_crypto"] = {"signal": "bearish", "strength": 50}
            elif gold_5d < -2 and btc_5d > 0:
                signals["gold_to_crypto"] = {"signal": "bullish", "strength": 50}
            else:
                signals["gold_to_crypto"] = {"signal": "neutral", "strength": 0}

        # Cross-asset correlation matrix (last 20 days)
        if len(returns) >= 20:
            corr = returns.tail(20).corr()
            # Stock-bond correlation (normally negative; if positive → risk-off regime)
            if "SPY" in corr.columns and "TLT" in corr.columns:
                sb_corr = float(corr.loc["SPY", "TLT"])
                signals["stock_bond_correlation"] = {
                    "value": round(sb_corr, 4),
                    "regime": "risk_off" if sb_corr > 0.3 else ("risk_on" if sb_corr < -0.3 else "normal")
                }

        print(f"  Cross-asset signals: {len(signals)} computed")
        for k, v in signals.items():
            print(f"    {k}: {v}")

        return signals

    except Exception as e:
        print(f"  Cross-asset error: {e}")
        return None


# ════════════════════════════════════════════════════════════════
#  Main
# ════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("WORLD-CLASS INTELLIGENCE: Macro + VIX + Cross-Asset")
    print("=" * 60)

    all_metrics = []

    # ──── FRED Macro Overlay ────
    print("\n--- FRED Macro Overlay ---")
    indicators = fetch_fred_via_yahoo()
    macro_score, macro_label, components = compute_macro_score(indicators)
    print(f"  Macro Score: {macro_score}/100 ({macro_label})")
    print(f"  Components: {components}")

    store_metric("macro_regime", "ALL", macro_score, macro_label,
                {"components": components, "indicators": indicators})

    # Store individual macro indicators
    for name, value in indicators.items():
        all_metrics.append({
            "metric_name": f"macro_{name}",
            "asset_class": "ALL",
            "metric_value": float(value),
            "metric_label": str(value)
        })

    # ──── VIX Term Structure ────
    print("\n--- VIX Term Structure ---")
    vix_data = fetch_vix_term_structure()
    if vix_data:
        store_metric("vix_term_structure", "STOCK", vix_data["ratio"],
                    vix_data["structure"], vix_data)

    # ──── Cross-Asset Spillover ────
    print("\n--- Cross-Asset Momentum Spillover ---")
    cross_signals = compute_cross_asset_signals()
    if cross_signals:
        for name, signal in cross_signals.items():
            sig_value = signal.get("strength", signal.get("value", 0))
            sig_label = signal.get("signal", signal.get("regime", "neutral"))
            store_metric(f"cross_asset_{name}", "ALL", sig_value, sig_label, signal)

    # ──── Store batch ────
    if all_metrics:
        store_batch(all_metrics)

    print(f"\n{'=' * 60}")
    print("MACRO INTELLIGENCE COMPLETE")
    print(f"  Macro Score: {macro_score}/100 ({macro_label})")
    if vix_data:
        print(f"  VIX Structure: {vix_data['structure']} (ratio: {vix_data['ratio']:.4f})")
    if cross_signals:
        for k, v in cross_signals.items():
            print(f"  {k}: {v.get('signal', v.get('regime', 'n/a'))}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
