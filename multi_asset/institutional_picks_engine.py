#!/usr/bin/env python3
"""
INSTITUTIONAL PICKS ENGINE v1.0
================================
Generates hedge-fund quality picks across all asset classes using:
1. Hyperopt-proven strategies with optimal per-symbol parameters
2. Multi-timeframe confirmation (daily + weekly alignment)
3. Regime-aware filtering (bull/bear/chop)
4. Correlation-aware position sizing
5. Strict risk management (Kelly criterion, max drawdown)

This runs ALONGSIDE the regular scanner to generate higher-quality,
lower-frequency picks with institutional-grade validation.

Usage:
  python multi_asset/institutional_picks_engine.py           # Full scan
  python multi_asset/institutional_picks_engine.py --status  # Show portfolio status
  python multi_asset/institutional_picks_engine.py --expand  # Scan expanded universe
"""

from __future__ import annotations
import argparse
import json
import math
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import yfinance as yf
except ImportError:
    print("ERROR: yfinance required")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

INSTITUTIONAL_PICKS_FILE = DATA_DIR / "institutional_picks.json"
INSTITUTIONAL_CLOSED_FILE = DATA_DIR / "institutional_closed.json"
RISK_STATE_FILE = DATA_DIR / "risk_state.json"

# ---------------------------------------------------------------------------
# EXPANDED Symbol Universe (institutional-grade coverage)
# ---------------------------------------------------------------------------
UNIVERSE = {
    # --- STOCKS: Mega/Large Cap (20 symbols) ---
    "AAPL":  {"name": "Apple",         "class": "EQUITY",      "sector": "Technology"},
    "MSFT":  {"name": "Microsoft",     "class": "EQUITY",      "sector": "Technology"},
    "NVDA":  {"name": "Nvidia",        "class": "EQUITY",      "sector": "Technology"},
    "GOOGL": {"name": "Alphabet",      "class": "EQUITY",      "sector": "Technology"},
    "AMZN":  {"name": "Amazon",        "class": "EQUITY",      "sector": "Consumer Disc"},
    "META":  {"name": "Meta",          "class": "EQUITY",      "sector": "Technology"},
    "TSLA":  {"name": "Tesla",         "class": "EQUITY",      "sector": "Consumer Disc"},
    "JPM":   {"name": "JPMorgan",      "class": "EQUITY",      "sector": "Financials"},
    "V":     {"name": "Visa",          "class": "EQUITY",      "sector": "Financials"},
    "JNJ":   {"name": "J&J",           "class": "EQUITY",      "sector": "Healthcare"},
    "WMT":   {"name": "Walmart",       "class": "EQUITY",      "sector": "Consumer Staples"},
    "PG":    {"name": "Procter&Gamble","class": "EQUITY",      "sector": "Consumer Staples"},
    "XOM":   {"name": "ExxonMobil",    "class": "EQUITY",      "sector": "Energy"},
    "UNH":   {"name": "UnitedHealth",  "class": "EQUITY",      "sector": "Healthcare"},
    "HD":    {"name": "Home Depot",    "class": "EQUITY",      "sector": "Consumer Disc"},
    "KO":    {"name": "Coca-Cola",     "class": "EQUITY",      "sector": "Consumer Staples"},
    "PEP":   {"name": "PepsiCo",       "class": "EQUITY",      "sector": "Consumer Staples"},
    "CVX":   {"name": "Chevron",       "class": "EQUITY",      "sector": "Energy"},
    "MRK":   {"name": "Merck",         "class": "EQUITY",      "sector": "Healthcare"},
    "ABBV":  {"name": "AbbVie",        "class": "EQUITY",      "sector": "Healthcare"},

    # --- PENNY STOCKS (16 symbols) ---
    "SOFI":  {"name": "SoFi",          "class": "PENNY_STOCK", "sector": "Fintech"},
    "NIO":   {"name": "NIO",           "class": "PENNY_STOCK", "sector": "EV"},
    "PLTR":  {"name": "Palantir",      "class": "PENNY_STOCK", "sector": "Technology"},
    "MARA":  {"name": "Marathon Dig",  "class": "PENNY_STOCK", "sector": "Crypto Mining"},
    "RIOT":  {"name": "Riot Platforms","class": "PENNY_STOCK", "sector": "Crypto Mining"},
    "IONQ":  {"name": "IonQ",          "class": "PENNY_STOCK", "sector": "Quantum"},
    "LCID":  {"name": "Lucid",         "class": "PENNY_STOCK", "sector": "EV"},
    "RIVN":  {"name": "Rivian",        "class": "PENNY_STOCK", "sector": "EV"},
    "HOOD":  {"name": "Robinhood",     "class": "PENNY_STOCK", "sector": "Fintech"},
    "OPEN":  {"name": "Opendoor",      "class": "PENNY_STOCK", "sector": "Real Estate"},
    "CLOV":  {"name": "Clover Health", "class": "PENNY_STOCK", "sector": "Healthcare"},
    "BB":    {"name": "BlackBerry",    "class": "PENNY_STOCK", "sector": "Technology"},
    "NOK":   {"name": "Nokia",         "class": "PENNY_STOCK", "sector": "Technology"},
    # "TELL": REMOVED — delisted as of 2026-03 (Yahoo: "No data found, symbol may be delisted")
    "SNDL":  {"name": "SNDL",          "class": "PENNY_STOCK", "sector": "Cannabis"},
    "AMC":   {"name": "AMC",           "class": "PENNY_STOCK", "sector": "Entertainment"},

    # --- ETFs: All 11 SPDR Sectors + Bond + Commodity (25 symbols) ---
    "SPY":   {"name": "S&P 500",       "class": "ETF",         "sector": "Broad Market"},
    "QQQ":   {"name": "Nasdaq 100",    "class": "ETF",         "sector": "Tech Heavy"},
    "IWM":   {"name": "Russell 2000",  "class": "ETF",         "sector": "Small Cap"},
    "XLK":   {"name": "Tech Select",   "class": "ETF",         "sector": "Technology"},
    "XLF":   {"name": "Financial",     "class": "ETF",         "sector": "Financials"},
    "XLE":   {"name": "Energy",        "class": "ETF",         "sector": "Energy"},
    "XLV":   {"name": "Healthcare",    "class": "ETF",         "sector": "Healthcare"},
    "XLP":   {"name": "Consumer Stpl", "class": "ETF",         "sector": "Consumer Staples"},
    "XLY":   {"name": "Consumer Disc", "class": "ETF",         "sector": "Consumer Disc"},
    "XLI":   {"name": "Industrial",    "class": "ETF",         "sector": "Industrials"},
    "XLB":   {"name": "Materials",     "class": "ETF",         "sector": "Materials"},
    "XLC":   {"name": "Communication", "class": "ETF",         "sector": "Communication"},
    "XLRE":  {"name": "Real Estate",   "class": "ETF",         "sector": "Real Estate"},
    "XLU":   {"name": "Utilities",     "class": "ETF",         "sector": "Utilities"},
    "GLD":   {"name": "Gold ETF",      "class": "ETF",         "sector": "Commodities"},
    "SLV":   {"name": "Silver ETF",    "class": "ETF",         "sector": "Commodities"},
    "TLT":   {"name": "20+ Yr Treasury","class": "BOND",        "sector": "Bonds"},
    "HYG":   {"name": "High Yield",    "class": "BOND",        "sector": "Bonds"},
    "DBC":   {"name": "Commodities",   "class": "ETF",         "sector": "Commodities"},
    "SOXX":  {"name": "Semiconductor", "class": "ETF",         "sector": "Technology"},
    "ARKK":  {"name": "ARK Innovation","class": "ETF",         "sector": "Innovation"},

    # --- FUTURES (11 contracts) ---
    "ES=F":  {"name": "S&P 500 E-mini","class": "FUTURES",     "sector": "Indices"},
    "NQ=F":  {"name": "Nasdaq E-mini", "class": "FUTURES",     "sector": "Indices"},
    "YM=F":  {"name": "Dow E-mini",    "class": "FUTURES",     "sector": "Indices"},
    "CL=F":  {"name": "Crude Oil WTI", "class": "FUTURES",     "sector": "Energy"},
    "GC=F":  {"name": "Gold",          "class": "FUTURES",     "sector": "Metals"},
    "SI=F":  {"name": "Silver",        "class": "FUTURES",     "sector": "Metals"},
    "ZN=F":  {"name": "10-Yr T-Note",  "class": "FUTURES",     "sector": "Rates"},
    "HG=F":  {"name": "Copper",        "class": "FUTURES",     "sector": "Metals"},
    "NG=F":  {"name": "Natural Gas",   "class": "FUTURES",     "sector": "Energy"},
    "ZT=F":  {"name": "2-Yr T-Note",   "class": "FUTURES",     "sector": "Rates"},

    # --- FOREX (11 pairs) ---
    # Carry yields updated 2026-04-01 (Fed 4.25%, ECB 2.50%, BoJ 0.50%,
    # RBA 4.10%, RBNZ 3.75%, BoC 2.75%, SNB 0.25%, BoE 4.50%)
    "EURUSD=X": {"name": "EUR/USD",    "class": "FOREX",       "sector": "Major", "carry": -1.75},
    "USDJPY=X": {"name": "USD/JPY",    "class": "FOREX",       "sector": "Major", "carry": 4.5},
    "GBPUSD=X": {"name": "GBP/USD",    "class": "FOREX",       "sector": "Major", "carry": 0.25},
    "AUDUSD=X": {"name": "AUD/USD",    "class": "FOREX",       "sector": "Commodity", "carry": 1.2},
    "NZDUSD=X": {"name": "NZD/USD",    "class": "FOREX",       "sector": "Commodity", "carry": 1.5},
    "USDCAD=X": {"name": "USD/CAD",    "class": "FOREX",       "sector": "Commodity", "carry": -0.3},
    "USDCHF=X": {"name": "USD/CHF",    "class": "FOREX",       "sector": "Major", "carry": 4.0},
    "EURJPY=X": {"name": "EUR/JPY",    "class": "FOREX",       "sector": "Cross", "carry": 2.0},
    "EURGBP=X": {"name": "EUR/GBP",    "class": "FOREX",       "sector": "Cross", "carry": -2.0},
    "AUDNZD=X": {"name": "AUD/NZD",    "class": "FOREX",       "sector": "Cross", "carry": 0.35},
    "CADJPY=X": {"name": "CAD/JPY",    "class": "FOREX",       "sector": "Cross", "carry": 2.25},
}

# ---------------------------------------------------------------------------
# Correlation Groups (max 3 picks per group)
# ---------------------------------------------------------------------------
CORRELATION_GROUPS = {
    "us_large_index": ["SPY", "QQQ", "ES=F", "NQ=F", "XLK", "IWM", "YM=F"],
    "us_bonds": ["TLT", "ZN=F", "ZT=F", "HYG"],
    "gold": ["GLD", "GC=F"],
    "oil_energy": ["CL=F", "XLE", "XOM", "CVX"],
    "big_tech": ["AAPL", "MSFT", "NVDA", "GOOGL", "META"],
    "ev_stocks": ["TSLA", "NIO", "LCID", "RIVN"],
    "crypto_miners": ["MARA", "RIOT"],
    "usd_pairs": ["EURUSD=X", "GBPUSD=X", "USDCHF=X"],
    "commodity_fx": ["AUDUSD=X", "NZDUSD=X", "USDCAD=X"],
    "jpy_cross": ["USDJPY=X", "EURJPY=X", "CADJPY=X"],
    "consumer_defensive": ["WMT", "PG", "KO", "PEP", "XLP"],
    "healthcare": ["JNJ", "UNH", "MRK", "ABBV", "XLV"],
}
MAX_PER_CORR_GROUP = 3

# ---------------------------------------------------------------------------
# Risk Parameters per Asset Class
# ---------------------------------------------------------------------------
RISK_PARAMS = {
    "EQUITY":      {"sl": -0.04, "tp": 0.08, "max_hold": 10, "kelly_fraction": 0.5, "max_picks": 8},
    "PENNY_STOCK": {"sl": -0.05, "tp": 0.10, "max_hold": 3,  "kelly_fraction": 0.2, "max_picks": 4},
    "ETF":         {"sl": -0.03, "tp": 0.06, "max_hold": 15, "kelly_fraction": 0.5, "max_picks": 8},
    "FUTURES":     {"sl": -0.03, "tp": 0.06, "max_hold": 10, "kelly_fraction": 0.4, "max_picks": 6},
    "FOREX":       {"sl": -0.02, "tp": 0.03, "max_hold": 14, "kelly_fraction": 0.4, "max_picks": 6},
}

# Per-symbol vol normalization — flat % pooling across futures contracts produced
# 0.28 R:R and -94% total PnL in 5-trade cohort. See docs/FUTURES_REVIVAL_FORENSICS_20260405.md.
# TP is set to 2x SL to guarantee R:R >= 2.0 (prevents futures_mean_reversion 0.28 R:R deathtrap).
FUTURES_SL_TP_BY_SYMBOL = {
    # Index futures
    "ES=F":  {"sl_pct": 0.012, "tp_pct": 0.024},
    "NQ=F":  {"sl_pct": 0.015, "tp_pct": 0.030},
    "YM=F":  {"sl_pct": 0.012, "tp_pct": 0.024},
    "RTY=F": {"sl_pct": 0.018, "tp_pct": 0.036},
    # Energy
    "CL=F":  {"sl_pct": 0.035, "tp_pct": 0.070},
    "NG=F":  {"sl_pct": 0.045, "tp_pct": 0.090},
    # Metals
    "GC=F":  {"sl_pct": 0.018, "tp_pct": 0.036},
    "SI=F":  {"sl_pct": 0.030, "tp_pct": 0.060},
    "HG=F":  {"sl_pct": 0.025, "tp_pct": 0.050},
    # Treasuries (low vol)
    "ZN=F":  {"sl_pct": 0.006, "tp_pct": 0.012},
    "ZB=F":  {"sl_pct": 0.006, "tp_pct": 0.012},
    "ZF=F":  {"sl_pct": 0.004, "tp_pct": 0.008},
    # FX futures
    "6E=F":  {"sl_pct": 0.010, "tp_pct": 0.020},
    "6J=F":  {"sl_pct": 0.010, "tp_pct": 0.020},
    "6B=F":  {"sl_pct": 0.012, "tp_pct": 0.024},
    # Grains
    "ZC=F":  {"sl_pct": 0.025, "tp_pct": 0.050},
    "ZS=F":  {"sl_pct": 0.022, "tp_pct": 0.044},
    "ZW=F":  {"sl_pct": 0.028, "tp_pct": 0.056},
}
FUTURES_DEFAULT_SL_PCT = 0.020  # fallback for unlisted futures symbols
FUTURES_DEFAULT_TP_PCT = 0.040

# ---------------------------------------------------------------------------
# Technical Indicators
# ---------------------------------------------------------------------------
def sma(s, p): return s.rolling(p).mean()
def ema(s, p): return s.ewm(span=p, adjust=False).mean()

def rsi(s, p=14):
    d = s.diff()
    g = d.where(d > 0, 0.0).rolling(p).mean()
    l = (-d.where(d < 0, 0.0)).rolling(p).mean()
    rs = g / l.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def bollinger_bands(s, p=20, std=2.0):
    mid = sma(s, p)
    sd = s.rolling(p).std()
    return mid, mid + std * sd, mid - std * sd

def macd(s, fast=12, slow=26, signal=9):
    ef = ema(s, fast); es = ema(s, slow)
    ml = ef - es; sl = ema(ml, signal)
    return ml, sl, ml - sl

def atr(h, l, c, p=14):
    tr = pd.concat([h-l, (h-c.shift(1)).abs(), (l-c.shift(1)).abs()], axis=1).max(axis=1)
    return tr.rolling(p).mean()

def adx(h, l, c, p=14):
    pdm = h.diff(); mdm = -l.diff()
    pdm = pdm.where((pdm > mdm) & (pdm > 0), 0.0)
    mdm = mdm.where((mdm > pdm) & (mdm > 0), 0.0)
    av = atr(h, l, c, p)
    pdi = 100 * ema(pdm, p) / av.replace(0, np.nan)
    mdi = 100 * ema(mdm, p) / av.replace(0, np.nan)
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return ema(dx, p)


# ---------------------------------------------------------------------------
# Regime Detection
# ---------------------------------------------------------------------------
def detect_regime(spy_data, vix_data):
    """Detect market regime from SPY and VIX data."""
    if spy_data is None or len(spy_data) < 200:
        return "UNKNOWN"
    if vix_data is None or len(vix_data) < 5:
        return "UNKNOWN"

    spy_close = spy_data["Close"]
    spy_price = float(spy_close.iloc[-1])
    spy_sma200 = float(sma(spy_close, 200).iloc[-1])
    spy_sma50 = float(sma(spy_close, 50).iloc[-1])
    vix = float(vix_data["Close"].iloc[-1])

    if spy_price > spy_sma200 and vix < 20:
        return "BULL"
    elif spy_price < spy_sma200 and vix > 25:
        return "BEAR"
    elif spy_price < spy_sma50 and vix > 22:
        return "BEAR_MILD"
    else:
        return "CHOP"


# ---------------------------------------------------------------------------
# INSTITUTIONAL STRATEGIES
# Each returns a confidence score and signal only when ALL conditions are met
# ---------------------------------------------------------------------------

def strategy_hyperopt_bollinger(df, symbol, info, regime):
    """Hyperopt-tuned Bollinger Mean Reversion — 73-92% backtest WR."""
    # Per-symbol optimal params from hyperopt
    PARAMS = {
        "ZN=F":     {"bb_std": 2.5, "rsi_buy": 25},
        "NZDUSD=X": {"bb_std": 1.5, "rsi_buy": 25},
        "GBPUSD=X": {"bb_std": 2.0, "rsi_buy": 30},
        "EURUSD=X": {"bb_std": 2.0, "rsi_buy": 30},
        "AMZN":     {"bb_std": 2.0, "rsi_buy": 25},
        "XLF":      {"bb_std": 2.0, "rsi_buy": 25},
        "ES=F":     {"bb_std": 2.0, "rsi_buy": 25},
        "XLE":      {"bb_std": 2.0, "rsi_buy": 25},
        "AUDUSD=X": {"bb_std": 1.5, "rsi_buy": 25},
        "USDCAD=X": {"bb_std": 1.5, "rsi_buy": 25},
        "USDCHF=X": {"bb_std": 1.5, "rsi_buy": 25},
        "NIO":      {"bb_std": 2.0, "rsi_buy": 25},
    }
    p = PARAMS.get(symbol)
    if not p or len(df) < 50:
        return None

    close = df["Close"]
    rsi_val = float(rsi(close, 14).iloc[-1])
    mid, upper, lower = bollinger_bands(close, 20, p["bb_std"])
    price = float(close.iloc[-1])
    lower_v = float(lower.iloc[-1])
    mid_v = float(mid.iloc[-1])

    if not all(np.isfinite([rsi_val, price, lower_v, mid_v])):
        return None

    # Multi-timeframe: check weekly also oversold
    weekly_rsi = float(rsi(close.resample("W").last().dropna(), 14).iloc[-1]) if len(close) > 100 else 50

    if price < lower_v and rsi_val < p["rsi_buy"]:
        # Regime adjustment
        conf_base = 0.75
        if regime == "BULL": conf_base += 0.10
        elif regime == "BEAR": conf_base -= 0.05

        # Weekly confirmation bonus
        if weekly_rsi < 40: conf_base += 0.05

        conf = min(0.95, conf_base + (p["rsi_buy"] - rsi_val) * 0.01)

        return {
            "direction": "LONG",
            "signal_type": "STRONG_BUY",
            "confidence": conf,
            "take_profit": mid_v,
            "reason": f"Hyperopt BB MR: price<BB({p['bb_std']}), RSI={rsi_val:.0f}<{p['rsi_buy']}, weekly_RSI={weekly_rsi:.0f}",
        }
    return None


def strategy_hyperopt_connors(df, symbol, info, regime):
    """Hyperopt-tuned Connors RSI — 67-92% backtest WR."""
    PARAMS = {
        "GLD":   {"rsi_p": 3, "rsi_buy": 10, "sma_trend": 200},
        "GC=F":  {"rsi_p": 3, "rsi_buy": 10, "sma_trend": 200},
        "IWM":   {"rsi_p": 3, "rsi_buy": 10, "sma_trend": 150},
        "SPY":   {"rsi_p": 2, "rsi_buy": 15, "sma_trend": 150},
        "ES=F":  {"rsi_p": 3, "rsi_buy": 15, "sma_trend": 150},
        "QQQ":   {"rsi_p": 2, "rsi_buy": 15, "sma_trend": 150},
        "SI=F":  {"rsi_p": 2, "rsi_buy": 10, "sma_trend": 200},
        "NQ=F":  {"rsi_p": 2, "rsi_buy": 10, "sma_trend": 150},
        "V":     {"rsi_p": 3, "rsi_buy": 15, "sma_trend": 150},
        "GOOGL": {"rsi_p": 3, "rsi_buy": 10, "sma_trend": 200},
        # Expanded: default conservative params for unlisted symbols
        # RSI(2) < 10 is the proven sweet spot (Connors & Alvarez)
        "AAPL":  {"rsi_p": 2, "rsi_buy": 10, "sma_trend": 200},
        "MSFT":  {"rsi_p": 2, "rsi_buy": 10, "sma_trend": 200},
        "NVDA":  {"rsi_p": 2, "rsi_buy": 10, "sma_trend": 200},
        "AMZN":  {"rsi_p": 2, "rsi_buy": 10, "sma_trend": 200},
        "META":  {"rsi_p": 2, "rsi_buy": 10, "sma_trend": 200},
        "TSLA":  {"rsi_p": 2, "rsi_buy": 15, "sma_trend": 150},
        "JPM":   {"rsi_p": 2, "rsi_buy": 10, "sma_trend": 200},
        "XLK":   {"rsi_p": 2, "rsi_buy": 10, "sma_trend": 200},
        "XLF":   {"rsi_p": 2, "rsi_buy": 10, "sma_trend": 200},
        "XLE":   {"rsi_p": 2, "rsi_buy": 10, "sma_trend": 200},
        "TLT":   {"rsi_p": 2, "rsi_buy": 10, "sma_trend": 200},
        "YM=F":  {"rsi_p": 2, "rsi_buy": 15, "sma_trend": 150},
        "CL=F":  {"rsi_p": 3, "rsi_buy": 10, "sma_trend": 200},
        "ZN=F":  {"rsi_p": 3, "rsi_buy": 10, "sma_trend": 200},
        "HG=F":  {"rsi_p": 3, "rsi_buy": 10, "sma_trend": 200},
    }
    p = PARAMS.get(symbol)
    if not p or len(df) < 200:
        return None

    close = df["Close"]
    rsi_val = float(rsi(close, p["rsi_p"]).iloc[-1])
    trend = float(sma(close, p["sma_trend"]).iloc[-1])
    price = float(close.iloc[-1])

    if not all(np.isfinite([rsi_val, price, trend])):
        return None

    # In BEAR regime, relax trend filter but lower confidence
    above_trend = price > trend
    if regime in ("BEAR", "BEAR_MILD") and rsi_val < 5:
        above_trend = True  # Allow extreme oversold in bear markets

    if rsi_val < p["rsi_buy"] and above_trend:
        conf = min(0.95, 0.75 + (p["rsi_buy"] - rsi_val) * 0.02)
        if regime == "BEAR": conf -= 0.10  # Penalize bear regime

        return {
            "direction": "LONG",
            "signal_type": "STRONG_BUY",
            "confidence": max(0.55, conf),
            "reason": f"Hyperopt Connors RSI({p['rsi_p']})={rsi_val:.1f}<{p['rsi_buy']}, trend={price>trend}",
        }

    # SHORT signal
    rsi_sell = 90 - (p["rsi_buy"] - 10) * 2  # Mirror buy threshold
    below_trend = price < trend
    if rsi_val > rsi_sell and below_trend:
        conf = min(0.90, 0.70 + (rsi_val - rsi_sell) * 0.02)
        if regime == "BULL": conf -= 0.10

        return {
            "direction": "SHORT",
            "signal_type": "STRONG_SELL",
            "confidence": max(0.55, conf),
            "reason": f"Hyperopt Connors RSI({p['rsi_p']})={rsi_val:.1f}>{rsi_sell}, below trend",
        }
    return None


def strategy_extreme_oversold(df, symbol, info, regime):
    """Extreme oversold bounce — works in selloffs without trend filter."""
    if len(df) < 50:
        return None

    close = df["Close"]
    rsi2 = float(rsi(close, 2).iloc[-1])
    rsi14 = float(rsi(close, 14).iloc[-1])
    price = float(close.iloc[-1])
    mid, _, lower = bollinger_bands(close, 20, 2.0)
    lower_v = float(lower.iloc[-1])
    mid_v = float(mid.iloc[-1])

    if not all(np.isfinite([rsi2, rsi14, price, lower_v, mid_v])):
        return None

    # Volume confirmation
    vol = df["Volume"]
    avg_vol = float(vol.rolling(20).mean().iloc[-1]) if "Volume" in df else 0
    cur_vol = float(vol.iloc[-1]) if "Volume" in df else 0
    high_vol = cur_vol > avg_vol * 1.5 if avg_vol > 0 else False

    if rsi2 < 5 and price < lower_v * 1.01:
        conf = min(0.92, 0.72 + (5 - rsi2) * 0.04)
        if high_vol: conf += 0.03  # Volume confirmation bonus
        if regime == "BULL": conf += 0.05

        tp = min(price * 1.03, mid_v)  # Tight TP
        return {
            "direction": "LONG",
            "signal_type": "STRONG_BUY",
            "confidence": min(0.95, conf),
            "take_profit": tp,
            "reason": f"Extreme oversold: RSI(2)={rsi2:.1f}, below BB, vol={'HIGH' if high_vol else 'normal'}",
        }
    return None


def strategy_rsi_overbought_short(df, symbol, info, regime):
    """RSI overbought SHORT — mirror of proven oversold LONG edge.

    Research basis: If RSI(2)<5 LONG has Sharpe 1.46 and 60.9% WR,
    the mirror RSI(2)>95 SHORT should work in downtrends.
    Only fires when price is BELOW SMA(200) — confirmed downtrend.
    Extra confirmation: RSI(14)>70 (intermediate overbought).

    This addresses the 97% LONG portfolio imbalance.
    """
    if len(df) < 200:
        return None

    # Skip penny stocks for shorting — hard to borrow, high squeeze risk
    if info.get("class") == "PENNY_STOCK":
        return None

    close = df["Close"]
    price = float(close.iloc[-1])
    rsi2 = float(rsi(close, 2).iloc[-1])
    rsi14 = float(rsi(close, 14).iloc[-1])
    sma200_val = float(sma(close, 200).iloc[-1])
    mid, upper, _ = bollinger_bands(close, 20, 2.0)
    upper_v = float(upper.iloc[-1])
    mid_v = float(mid.iloc[-1])

    if not all(np.isfinite([rsi2, rsi14, price, sma200_val, upper_v, mid_v])):
        return None

    # SHORT: RSI(2) > 95 + price below SMA(200) + RSI(14) > 65
    # The triple confirmation prevents shorting into uptrends
    if rsi2 > 95 and price < sma200_val and rsi14 > 65:
        conf = min(0.90, 0.70 + (rsi2 - 95) * 0.04)
        if price > upper_v:
            conf += 0.05  # Extra confirmation: above upper BB in downtrend = fade

        # In BEAR regime, boost confidence (shorting with the trend)
        if regime in ("BEAR", "BEAR_MILD"):
            conf += 0.05

        tp = max(price * 0.97, mid_v)  # Target BB mid or 3% drop
        return {
            "direction": "SHORT",
            "signal_type": "STRONG_SELL",
            "confidence": min(0.95, max(0.55, conf)),
            "take_profit": tp,
            "reason": f"RSI overbought short: RSI(2)={rsi2:.1f}>95, below SMA200, RSI(14)={rsi14:.0f}",
        }
    return None


def strategy_sector_rotation(df, symbol, info, regime):
    """Sector Rotation: buy top-momentum sectors, short worst."""
    # Only for sector ETFs
    if info.get("class") != "ETF" or symbol in ("SPY", "QQQ", "IWM", "GLD", "TLT", "HYG", "DBC", "ARKK", "SOXX"):
        return None
    if len(df) < 60:
        return None

    close = df["Close"]
    price = float(close.iloc[-1])

    # 1-month momentum
    mom_1m = (price / float(close.iloc[-22]) - 1) * 100 if len(close) > 22 else 0
    # 3-month momentum
    mom_3m = (price / float(close.iloc[-63]) - 1) * 100 if len(close) > 63 else 0

    # RSI
    rsi_val = float(rsi(close, 14).iloc[-1])

    # Strong positive momentum = buy sector
    if mom_1m > 3 and mom_3m > 5 and rsi_val < 70:
        conf = min(0.80, 0.55 + mom_1m * 0.02 + mom_3m * 0.005)
        return {
            "direction": "LONG",
            "signal_type": "BUY",
            "confidence": conf,
            "reason": f"Sector rotation: 1m={mom_1m:+.1f}%, 3m={mom_3m:+.1f}%, RSI={rsi_val:.0f}",
        }

    # Strong negative momentum = short sector
    if mom_1m < -5 and mom_3m < -8 and rsi_val > 30 and regime in ("BEAR", "BEAR_MILD"):
        conf = min(0.75, 0.50 + abs(mom_1m) * 0.02)
        return {
            "direction": "SHORT",
            "signal_type": "SELL",
            "confidence": conf,
            "reason": f"Sector rotation SHORT: 1m={mom_1m:+.1f}%, 3m={mom_3m:+.1f}%",
        }
    return None


def strategy_pairs_divergence(df, symbol, info, regime, all_data):
    """Pairs trading: trade when correlated pair diverges."""
    PAIRS = {
        "KO":  "PEP",  "PEP": "KO",
        "XOM": "CVX",  "CVX": "XOM",
        "JPM": "V",    "V":   "JPM",
        "AAPL": "MSFT", "MSFT": "AAPL",
        # v101: ETF pairs (proven academic strategies)
        "IWM": "SPY",  "SPY": "IWM",   # Size factor mean reversion (Fama-French)
        "GLD": "SLV",  "SLV": "GLD",   # Gold/Silver ratio (80-90 range, mean-reverts)
        # v101: Futures pairs
        "ES=F": "NQ=F", "NQ=F": "ES=F",  # Tech vs broad market rotation
        # v101: Commodity pairs
        "GC=F": "HG=F", "HG=F": "GC=F",  # Gold/Copper ratio (economic indicator, Gundlach)
    }
    pair = PAIRS.get(symbol)
    if not pair or pair not in all_data or len(df) < 60:
        return None

    df_pair = all_data[pair]
    if len(df_pair) < 60:
        return None

    close_a = df["Close"]
    close_b = df_pair["Close"]

    # Compute spread (log ratio)
    ratio = np.log(close_a / close_b)
    ratio_mean = float(ratio.rolling(60).mean().iloc[-1])
    ratio_std = float(ratio.rolling(60).std().iloc[-1])
    ratio_now = float(ratio.iloc[-1])

    if not all(np.isfinite([ratio_mean, ratio_std, ratio_now])) or ratio_std < 0.001:
        return None

    z_score = (ratio_now - ratio_mean) / ratio_std

    # Z-score > 2: symbol is expensive relative to pair → SHORT symbol
    if z_score > 2.0:
        conf = min(0.80, 0.55 + abs(z_score - 2) * 0.1)
        return {
            "direction": "SHORT",
            "signal_type": "SELL",
            "confidence": conf,
            "reason": f"Pairs: {symbol}/{pair} z-score={z_score:.2f}>2 (mean-revert expected)",
        }

    # Z-score < -2: symbol is cheap relative to pair → LONG symbol
    if z_score < -2.0:
        conf = min(0.80, 0.55 + abs(z_score + 2) * 0.1)
        return {
            "direction": "LONG",
            "signal_type": "BUY",
            "confidence": conf,
            "reason": f"Pairs: {symbol}/{pair} z-score={z_score:.2f}<-2 (mean-revert expected)",
        }
    return None


def strategy_macd_divergence_tuned(df, symbol, info, regime):
    """Hyperopt-tuned MACD Divergence — 67-83% WR on select symbols."""
    PARAMS = {
        "GC=F": {"lb": 10}, "JPM": {"lb": 10}, "XLE": {"lb": 5},
        "PLTR": {"lb": 10}, "SI=F": {"lb": 10}, "GLD": {"lb": 5},
        "RIOT": {"lb": 10}, "YM=F": {"lb": 10}, "META": {"lb": 5},
        "SPY":  {"lb": 10}, "MARA": {"lb": 10},
    }
    p = PARAMS.get(symbol)
    if not p or len(df) < 50:
        return None

    close = df["Close"]
    _, _, hist = macd(close, 12, 26, 9)
    price = float(close.iloc[-1])
    hist_now = float(hist.iloc[-1])
    lb = p["lb"]
    hist_prev = float(hist.iloc[-lb-1]) if len(hist) > lb else hist_now

    if not all(np.isfinite([price, hist_now, hist_prev])):
        return None

    price_low_now = float(close.iloc[-lb:].min())
    price_low_prev = float(close.iloc[-lb*2:-lb].min()) if len(close) > lb*2 else price_low_now

    # Bullish divergence
    if price_low_now < price_low_prev and hist_now > hist_prev and hist_now < 0:
        conf = 0.70
        if regime == "BULL": conf += 0.05
        return {
            "direction": "LONG",
            "signal_type": "BUY",
            "confidence": conf,
            "reason": f"MACD divergence (lb={lb}): bullish div detected",
        }
    return None


def strategy_volume_breakout(df, symbol, info, regime):
    """Volume Breakout for penny stocks — high volume + price break."""
    if info.get("class") != "PENNY_STOCK" or len(df) < 30:
        return None

    close = df["Close"]
    vol = df["Volume"]
    price = float(close.iloc[-1])
    high_20 = float(close.iloc[-20:].max())
    avg_vol = float(vol.rolling(20).mean().iloc[-1])
    cur_vol = float(vol.iloc[-1])

    if avg_vol <= 0 or not all(np.isfinite([price, high_20, avg_vol, cur_vol])):
        return None

    vol_ratio = cur_vol / avg_vol

    # Volume breakout: 3x volume + price above 20d high
    if vol_ratio > 3.0 and price >= high_20 * 0.98:
        conf = min(0.80, 0.55 + (vol_ratio - 3) * 0.05)
        return {
            "direction": "LONG",
            "signal_type": "BUY",
            "confidence": conf,
            "reason": f"Volume breakout: {vol_ratio:.1f}x avg vol, near 20d high ${high_20:.2f}",
        }
    return None


def strategy_penny_deep_oversold(df, symbol, info, regime):
    """Penny oversold bounce v2 — tighter filters after backtest showed 38% WR.

    Backtest learnings (1,456 trades):
    - Original 8% SL was too wide, 43% of trades hit SL
    - RSI(14)<20 was a falling knife indicator, not just a confidence penalty
    - Need volume confirmation to filter out low-conviction sells
    - Tighter SL (-5%), tighter TP (+10%), reject RSI(14)<25 entirely
    """
    if info.get("class") != "PENNY_STOCK":
        return None
    if len(df) < 50:
        return None

    close = df["Close"]
    vol = df["Volume"]
    rsi2 = float(rsi(close, 2).iloc[-1])
    rsi14 = float(rsi(close, 14).iloc[-1])
    price = float(close.iloc[-1])

    if not all(np.isfinite([rsi2, rsi14, price])):
        return None

    # HARD REJECT: RSI(14) < 25 means strong downtrend — falling knife
    if rsi14 < 25:
        return None

    # Volume must be above average (confirms selling exhaustion, not just drift)
    avg_vol = float(vol.rolling(20).mean().iloc[-1]) if len(vol) >= 20 else 0
    cur_vol = float(vol.iloc[-1]) if len(vol) > 0 else 0
    if avg_vol <= 0 or cur_vol < avg_vol * 1.2:
        return None  # Need at least 1.2x avg volume

    high_20d = float(close.rolling(20).max().iloc[-1])
    pct_off_high = 1 - (price / high_20d) if high_20d > 0 else 0

    # Tighter entry: RSI(2)<2 (not 3), >10% off high (not 8%), volume confirmed
    if rsi2 < 2 and pct_off_high > 0.10 and pct_off_high < 0.30:
        # Cap at 30% off high — beyond that is likely broken/delisted
        conf = min(0.80, 0.60 + pct_off_high * 1.5 + (2 - rsi2) * 0.02)

        return {
            "direction": "LONG",
            "signal_type": "BUY",
            "confidence": max(0.55, conf),
            "reason": f"Penny oversold v2: RSI(2)={rsi2:.1f}, {pct_off_high*100:.0f}% off high, vol={cur_vol/avg_vol:.1f}x, RSI(14)={rsi14:.0f}",
        }
    return None


def strategy_futures_mean_reversion(df, symbol, info, regime):
    """Futures Bollinger mean reversion — relaxed for BEAR/CHOP regimes.

    Research basis: Bollinger MR on futures shows 75-89% WR in hyperopt backtests.
    Uses wider BB (2.5 std) and shorter period for faster signals.
    """
    if info.get("class") != "FUTURES":
        return None
    if len(df) < 50:
        return None

    close = df["Close"]
    rsi_val = float(rsi(close, 3).iloc[-1])
    price = float(close.iloc[-1])
    mid, upper, lower = bollinger_bands(close, 15, 2.5)
    mid_v = float(mid.iloc[-1])
    lower_v = float(lower.iloc[-1])
    upper_v = float(upper.iloc[-1])

    if not all(np.isfinite([rsi_val, price, mid_v, lower_v, upper_v])):
        return None

    # LONG: price near/below lower band + RSI < 20
    if price < lower_v * 1.02 and rsi_val < 20:
        conf = min(0.90, 0.70 + (20 - rsi_val) * 0.01 + (lower_v - price) / lower_v * 10)
        return {
            "direction": "LONG",
            "signal_type": "BUY",
            "confidence": max(0.55, conf),
            "take_profit": mid_v,
            "reason": f"Futures BB MR: price=${price:.2f} < BB lower=${lower_v:.2f}, RSI(3)={rsi_val:.0f}",
            "seasonal_adj": _seasonal_confidence_adj(symbol, "LONG"),
        }

    # SHORT: price near/above upper band + RSI > 80
    if price > upper_v * 0.98 and rsi_val > 80:
        conf = min(0.90, 0.70 + (rsi_val - 80) * 0.01)
        return {
            "direction": "SHORT",
            "signal_type": "SELL",
            "confidence": max(0.55, conf),
            "take_profit": mid_v,
            "reason": f"Futures BB MR short: price=${price:.2f} > BB upper=${upper_v:.2f}, RSI(3)={rsi_val:.0f}",
            "seasonal_adj": _seasonal_confidence_adj(symbol, "SHORT"),
        }
    return None


def _seasonal_confidence_adj(symbol: str, direction: str) -> float:
    """Seasonal confidence adjustment for commodities/futures.

    Source: Moore Research Center (MRCI), CME Group seasonal studies.
    Returns a multiplier (0.8-1.15) based on historically favorable/unfavorable months.
    """
    from datetime import datetime
    month = datetime.now().month
    SEASONAL = {
        # Gold: strong Jan-Feb (wedding/CNY), Aug-Sep. Weak Jun-Jul.
        "GC=F":  {1: 1.10, 2: 1.10, 3: 1.0, 4: 1.0, 5: 0.95, 6: 0.85, 7: 0.85, 8: 1.05, 9: 1.05, 10: 1.0, 11: 1.0, 12: 1.05},
        "GLD":   {1: 1.10, 2: 1.10, 3: 1.0, 4: 1.0, 5: 0.95, 6: 0.85, 7: 0.85, 8: 1.05, 9: 1.05, 10: 1.0, 11: 1.0, 12: 1.05},
        # Nat gas: strong Oct-Feb (heating), weak Mar-May
        "NG=F":  {1: 1.10, 2: 1.05, 3: 0.85, 4: 0.85, 5: 0.85, 6: 0.90, 7: 0.95, 8: 1.0, 9: 1.0, 10: 1.10, 11: 1.15, 12: 1.10},
        # Crude: strong Feb-Jun (refinery+driving), weak Sep-Nov
        "CL=F":  {1: 1.0, 2: 1.05, 3: 1.10, 4: 1.10, 5: 1.05, 6: 1.05, 7: 1.0, 8: 0.95, 9: 0.85, 10: 0.85, 11: 0.85, 12: 0.95},
        # Copper: strong Jan-Apr (construction)
        "HG=F":  {1: 1.10, 2: 1.10, 3: 1.05, 4: 1.05, 5: 1.0, 6: 0.95, 7: 0.90, 8: 0.90, 9: 0.95, 10: 1.0, 11: 1.0, 12: 1.0},
    }
    adj = SEASONAL.get(symbol, {}).get(month, 1.0)
    # Seasonal applies to LONG direction; inverse for SHORT
    if direction == "SHORT":
        adj = 2.0 - adj  # e.g., 1.10 LONG favorable = 0.90 SHORT favorable
    return adj


def strategy_dual_momentum(df, symbol, info, regime, all_data):
    """Dual Momentum (Antonacci 2014) — absolute + relative momentum.

    Academic basis: Gary Antonacci, "Dual Momentum Investing" (2014).
    Combines relative momentum (SPY vs TLT) with absolute momentum (>0 return).
    Monthly signal, hold for 1 month. Historically ~15% CAGR with max DD ~20%.

    Rules:
    - If SPY 12m return > TLT 12m return AND SPY 12m > 0: LONG SPY
    - If SPY 12m return < 0 (absolute momentum fails): LONG TLT (safety)
    - If TLT 12m > SPY 12m AND TLT 12m > 0: LONG TLT
    """
    if symbol not in ("SPY", "TLT"):
        return None
    if "SPY" not in all_data or "TLT" not in all_data:
        return None

    spy_df = all_data["SPY"]
    tlt_df = all_data["TLT"]
    if len(spy_df) < 252 or len(tlt_df) < 252:
        return None

    spy_close = spy_df["Close"]
    tlt_close = tlt_df["Close"]
    spy_price = float(spy_close.iloc[-1])
    tlt_price = float(tlt_close.iloc[-1])
    spy_12m = (spy_price / float(spy_close.iloc[-252]) - 1) if len(spy_close) >= 252 else 0
    tlt_12m = (tlt_price / float(tlt_close.iloc[-252]) - 1) if len(tlt_close) >= 252 else 0

    # Determine which asset to hold
    if spy_12m > tlt_12m and spy_12m > 0:
        # Relative + absolute momentum: LONG SPY
        if symbol != "SPY":
            return None
        conf = min(0.85, 0.65 + spy_12m * 0.5)  # Scale with strength
        if regime == "BULL":
            conf += 0.05
        return {
            "direction": "LONG",
            "signal_type": "BUY",
            "confidence": min(0.90, max(0.60, conf)),
            "reason": f"Dual Momentum: SPY 12m={spy_12m*100:+.1f}% > TLT {tlt_12m*100:+.1f}%, absolute positive",
        }
    elif spy_12m <= 0 or tlt_12m > spy_12m:
        # Absolute momentum fails or TLT wins: LONG TLT (safety)
        if symbol != "TLT":
            return None
        conf = min(0.80, 0.60 + abs(tlt_12m) * 0.3)
        return {
            "direction": "LONG",
            "signal_type": "BUY",
            "confidence": min(0.85, max(0.60, conf)),
            "reason": f"Dual Momentum: TLT 12m={tlt_12m*100:+.1f}% > SPY {spy_12m*100:+.1f}%, risk-off rotation",
        }
    return None


def strategy_sector_rotation_enhanced(df, symbol, info, regime, all_data):
    """Enhanced Sector Rotation — composite multi-period momentum + SMA200 filter.

    Academic basis: Moskowitz & Grinblatt (1999) "Do Industries Explain Momentum?",
    Faber (2007) "A Quantitative Approach to Tactical Asset Allocation".

    Ranks all 11 SPDR sector ETFs by composite momentum:
      composite = 3m_return * 0.5 + 6m_return * 0.3 + 12m_return * 0.2
    Go LONG top 3 sectors (if above SMA200), avoid bottom 3.

    Replaces naive 1m/3m independent checks with proper cross-sectional ranking.
    """
    SECTOR_ETFS = ["XLK", "XLF", "XLE", "XLV", "XLP", "XLY", "XLI", "XLB", "XLC", "XLRE", "XLU"]
    if symbol not in SECTOR_ETFS:
        return None
    if len(df) < 252:
        return None

    # Compute composite momentum for all sectors we have data for
    sector_scores = {}
    for etf in SECTOR_ETFS:
        if etf not in all_data or len(all_data[etf]) < 252:
            continue
        etf_close = all_data[etf]["Close"]
        etf_price = float(etf_close.iloc[-1])
        mom_3m = (etf_price / float(etf_close.iloc[-63]) - 1) if len(etf_close) >= 63 else 0
        mom_6m = (etf_price / float(etf_close.iloc[-126]) - 1) if len(etf_close) >= 126 else 0
        mom_12m = (etf_price / float(etf_close.iloc[-252]) - 1) if len(etf_close) >= 252 else 0
        composite = mom_3m * 0.5 + mom_6m * 0.3 + mom_12m * 0.2
        sector_scores[etf] = {
            "composite": composite, "mom_3m": mom_3m, "mom_6m": mom_6m, "mom_12m": mom_12m,
        }

    if len(sector_scores) < 6 or symbol not in sector_scores:
        return None

    # Rank sectors by composite momentum
    ranked = sorted(sector_scores.keys(), key=lambda s: sector_scores[s]["composite"], reverse=True)
    rank = ranked.index(symbol) + 1  # 1-indexed
    total = len(ranked)
    sc = sector_scores[symbol]

    # SMA200 filter: skip if below 200-day SMA
    close = df["Close"]
    price = float(close.iloc[-1])
    sma200_val = float(sma(close, 200).iloc[-1])
    if not np.isfinite(sma200_val):
        return None

    # TOP 3: LONG (if above SMA200)
    if rank <= 3:
        if price < sma200_val:
            return None  # Below SMA200 — skip even if top-ranked
        conf = min(0.85, 0.60 + sc["composite"] * 2.0 + (4 - rank) * 0.03)
        if regime == "BULL":
            conf += 0.05
        return {
            "direction": "LONG",
            "signal_type": "BUY",
            "confidence": min(0.90, max(0.55, conf)),
            "reason": f"Sector rotation (rank {rank}/{total}): composite={sc['composite']*100:+.1f}% "
                      f"(3m={sc['mom_3m']*100:+.1f}%, 6m={sc['mom_6m']*100:+.1f}%, 12m={sc['mom_12m']*100:+.1f}%), above SMA200",
        }

    # BOTTOM 3: SHORT (only in bear regimes, adds directional edge)
    if rank > total - 3 and regime in ("BEAR", "BEAR_MILD"):
        if price > sma200_val:
            return None  # Above SMA200 — don't short
        conf = min(0.75, 0.50 + abs(sc["composite"]) * 1.5)
        return {
            "direction": "SHORT",
            "signal_type": "SELL",
            "confidence": min(0.80, max(0.55, conf)),
            "reason": f"Sector rotation SHORT (rank {rank}/{total}): composite={sc['composite']*100:+.1f}%, below SMA200",
        }
    return None


def strategy_credit_spread(df, symbol, info, regime, all_data):
    """Credit Spread Signal (HYG/TLT ratio) — risk-on/risk-off regime indicator.

    Academic basis: Fama & French (1993) default spread factor,
    Gilchrist & Zakrajsek (2012) "Credit Spreads and Business Cycle Fluctuations".

    HYG/TLT ratio rising = credit improving = risk-on (favor equities)
    HYG/TLT ratio falling = credit deteriorating = risk-off (favor treasuries)

    Uses 20-day ROC of HYG/TLT ratio as the signal.
    Applies to SPY (risk-on beneficiary) and TLT (risk-off beneficiary).
    """
    if symbol not in ("SPY", "QQQ", "TLT"):
        return None
    if "HYG" not in all_data or "TLT" not in all_data:
        return None

    hyg_df = all_data["HYG"]
    tlt_df = all_data["TLT"]
    if len(hyg_df) < 60 or len(tlt_df) < 60:
        return None

    hyg_close = hyg_df["Close"]
    tlt_close = tlt_df["Close"]

    # Compute HYG/TLT ratio and its 20-day ROC
    min_len = min(len(hyg_close), len(tlt_close))
    hyg_aligned = hyg_close.iloc[-min_len:]
    tlt_aligned = tlt_close.iloc[-min_len:]
    ratio = hyg_aligned.values / tlt_aligned.values

    if len(ratio) < 25:
        return None

    ratio_now = float(ratio[-1])
    ratio_20d_ago = float(ratio[-21])
    roc_20d = (ratio_now / ratio_20d_ago - 1) * 100  # percent change
    ratio_50d_ago = float(ratio[-51]) if len(ratio) >= 51 else ratio_20d_ago
    roc_50d = (ratio_now / ratio_50d_ago - 1) * 100 if len(ratio) >= 51 else roc_20d

    # Need the symbol's own RSI for confirmation
    sym_close = df["Close"]
    rsi14 = float(rsi(sym_close, 14).iloc[-1]) if len(sym_close) >= 20 else 50

    # Risk-ON signal: HYG/TLT rising -> favor SPY/QQQ
    if roc_20d > 0.5 and symbol in ("SPY", "QQQ"):
        conf = min(0.80, 0.55 + roc_20d * 0.05)
        if roc_50d > 0:
            conf += 0.05  # Longer-term confirmation
        if rsi14 < 40:
            conf += 0.05  # Oversold equity + improving credit = strong combo
        return {
            "direction": "LONG",
            "signal_type": "BUY",
            "confidence": min(0.85, max(0.55, conf)),
            "reason": f"Credit spread risk-ON: HYG/TLT 20d ROC={roc_20d:+.2f}%, 50d={roc_50d:+.2f}%, RSI(14)={rsi14:.0f}",
        }

    # Risk-OFF signal: HYG/TLT falling -> favor TLT
    if roc_20d < -0.5 and symbol == "TLT":
        conf = min(0.80, 0.55 + abs(roc_20d) * 0.05)
        if roc_50d < 0:
            conf += 0.05
        return {
            "direction": "LONG",
            "signal_type": "BUY",
            "confidence": min(0.85, max(0.55, conf)),
            "reason": f"Credit spread risk-OFF: HYG/TLT 20d ROC={roc_20d:+.2f}%, flight to safety",
        }
    return None


def strategy_forex_carry_momentum(df, symbol, info, regime):
    """Forex carry trade with trend filter (Lustig et al., 2011).

    Rule: go LONG high-yield currencies ONLY when carry > 0 AND price > SMA200.
    Interest rate differential momentum: if carry is widening (recent price
    momentum accelerating in carry direction), boost confidence.
    Previous approach (Connors RSI-2) was wrong for carry — carry is a trend
    strategy, not mean-reversion. 23 closed trades showed 4.3% WR.
    """
    if info.get("class") != "FOREX":
        return None
    if len(df) < 200:
        return None

    carry = info.get("carry", 0)
    # --- CORE RULE: Only trade positive carry (Lustig 2011) ---
    if carry <= 0:
        return None

    close = df["Close"]
    price = float(close.iloc[-1])
    sma200_val = float(sma(close, 200).iloc[-1])

    if not all(np.isfinite([price, sma200_val])):
        return None

    # --- TREND FILTER: price must be > SMA200 ---
    if price <= sma200_val:
        return None  # Below trend = carry crash risk

    rsi14 = float(rsi(close, 14).iloc[-1])
    if rsi14 > 70:
        return None  # Overbought, wait for pullback

    # --- Interest rate differential momentum ---
    # Proxy: 20d momentum accelerating vs 60d = "widening" differential
    mom_20d = float(close.iloc[-1] / close.iloc[-20] - 1) if len(close) >= 20 else 0
    mom_60d = float(close.iloc[-1] / close.iloc[-60] - 1) if len(close) >= 60 else mom_20d
    carry_widening = mom_20d > 0 and mom_20d > mom_60d / 3

    # Volatility filter: skip elevated vol (carry unwind conditions)
    returns = close.pct_change().dropna()
    if len(returns) >= 60:
        vol_20d = float(returns.iloc[-20:].std() * (252 ** 0.5))
        vol_60d = float(returns.iloc[-60:].std() * (252 ** 0.5))
        if vol_60d > 0 and vol_20d / vol_60d > 1.3:
            return None  # Vol spike = carry unwind risk

    # Confidence: carry size + trend strength + differential momentum
    trend_strength = (price - sma200_val) / sma200_val
    conf = min(0.78, 0.52 + carry / 15.0 + min(0.05, trend_strength * 2.0))
    if carry_widening:
        conf += 0.04
    else:
        conf -= 0.03
    conf = max(0.52, min(0.78, conf))

    return {
        "direction": "LONG",
        "signal_type": "BUY",
        "confidence": conf,
        "reason": (f"Carry +{carry:.1f}% + SMA200 trend, "
                   f"{'widening' if carry_widening else 'narrowing'} diff, "
                   f"RSI(14)={rsi14:.0f}, trend_str={trend_strength:.3f}"),
    }


def strategy_commodity_momentum(df, symbol, info, regime, all_data):
    """Cross-Commodity Momentum (Asness, Moskowitz, Pedersen 2013).

    Rank commodities by 3-month (63 trading day) return.
    Go LONG top 2 performers, SHORT bottom 1.

    Academic basis: "Value and Momentum Everywhere" (AMP 2013, JFE).
    Cross-sectional momentum in commodities: Sharpe 0.60-0.90,
    low correlation with equity momentum. Works because commodity
    returns are driven by fundamental supply/demand cycles that
    trend persistently.

    Only activates for FUTURES-class symbols in energy/metals sectors.
    """
    if info.get("class") != "FUTURES":
        return None
    sector = info.get("sector", "")
    if sector not in ("Energy", "Metals"):
        return None
    if len(df) < 80:
        return None

    # Commodity universe: only energy and metals futures from all_data
    COMMODITY_TICKERS = {
        "CL=F", "GC=F", "SI=F", "HG=F", "NG=F",
        "ZN=F",  # include for ranking diversity
    }

    # Compute 63-day (3-month) returns for all available commodities
    returns_list = []
    for ticker in COMMODITY_TICKERS:
        if ticker not in all_data:
            continue
        tdf = all_data[ticker]
        if len(tdf) < 70:
            continue
        close = tdf["Close"]
        price_now = float(close.iloc[-1])
        price_63d = float(close.iloc[-63]) if len(close) >= 63 else float(close.iloc[0])
        if price_63d <= 0:
            continue
        ret_3m = (price_now - price_63d) / price_63d
        returns_list.append((ticker, ret_3m, price_now))

    if len(returns_list) < 4:
        return None  # Need at least 4 commodities to rank meaningfully

    # Sort by 3-month return (highest first)
    returns_list.sort(key=lambda x: x[1], reverse=True)

    # Find this symbol's rank
    symbol_rank = None
    symbol_ret = None
    for i, (t, r, _) in enumerate(returns_list):
        if t == symbol:
            symbol_rank = i
            symbol_ret = r
            break

    if symbol_rank is None:
        return None

    total = len(returns_list)

    # LONG top 2 performers
    if symbol_rank < 2 and symbol_ret > 0.01:
        conf = min(0.82, 0.58 + abs(symbol_ret) * 1.5 + (2 - symbol_rank) * 0.03)
        seasonal = _seasonal_confidence_adj(symbol, "LONG")
        conf *= seasonal
        conf = min(0.85, max(0.55, conf))
        return {
            "direction": "LONG",
            "signal_type": "BUY",
            "confidence": round(conf, 2),
            "reason": (f"Commodity momentum: {symbol} ranked #{symbol_rank+1}/{total} "
                       f"(3m ret={symbol_ret*100:+.1f}%), LONG top-2 [AMP 2013]"),
            "seasonal_adj": seasonal,
        }

    # SHORT bottom 1 performer
    if symbol_rank == total - 1 and symbol_ret < -0.01:
        conf = min(0.78, 0.55 + abs(symbol_ret) * 1.2)
        seasonal = _seasonal_confidence_adj(symbol, "SHORT")
        conf *= seasonal
        conf = min(0.80, max(0.55, conf))
        return {
            "direction": "SHORT",
            "signal_type": "SELL",
            "confidence": round(conf, 2),
            "reason": (f"Commodity momentum: {symbol} ranked #{symbol_rank+1}/{total} "
                       f"(3m ret={symbol_ret*100:+.1f}%), SHORT bottom-1 [AMP 2013]"),
            "seasonal_adj": seasonal,
        }

    return None


# Strategy registry
STRATEGIES = [
    ("hyperopt_bollinger_mr", strategy_hyperopt_bollinger),
    ("hyperopt_connors_rsi2", strategy_hyperopt_connors),
    ("extreme_oversold_bounce", strategy_extreme_oversold),
    ("rsi_overbought_short", strategy_rsi_overbought_short),
    ("sector_rotation", strategy_sector_rotation),
    ("sector_rotation_enhanced", strategy_sector_rotation_enhanced),
    ("dual_momentum", strategy_dual_momentum),
    ("credit_spread", strategy_credit_spread),
    ("pairs_divergence", strategy_pairs_divergence),
    ("macd_divergence_tuned", strategy_macd_divergence_tuned),
    ("volume_breakout", strategy_volume_breakout),
    ("penny_deep_oversold", strategy_penny_deep_oversold),
    ("futures_mean_reversion", strategy_futures_mean_reversion),
    ("forex_carry_momentum", strategy_forex_carry_momentum),
    ("commodity_momentum", strategy_commodity_momentum),
]


# ---------------------------------------------------------------------------
# Data Fetching with Failover
# ---------------------------------------------------------------------------
def fetch_data(symbols, period="2y", interval="1d"):
    """Fetch price data with yfinance, retry on failure."""
    tickers = list(symbols)
    print(f"  Fetching {len(tickers)} symbols via yfinance...")

    try:
        raw = yf.download(tickers, period=period, interval=interval,
                          group_by="ticker", progress=False, threads=True)
        data = {}
        for sym in tickers:
            try:
                if len(tickers) == 1:
                    df = raw.dropna()
                else:
                    df = raw[sym].dropna()
                if len(df) > 20:
                    data[sym] = df
            except Exception:
                pass
        print(f"  Got {len(data)}/{len(tickers)} symbols")
        return data
    except Exception as e:
        print(f"  ERROR fetching data: {e}")
        return {}


# ---------------------------------------------------------------------------
# Position Sizing (Kelly Criterion)
# ---------------------------------------------------------------------------
def kelly_position_size(win_rate, avg_win, avg_loss, fraction=0.5):
    """Half-Kelly position sizing."""
    if avg_loss == 0:
        return 0.05
    b = avg_win / abs(avg_loss)
    p = win_rate
    q = 1 - p
    f = (b * p - q) / b
    f = max(0, min(0.25, f * fraction))  # Cap at 25%
    return round(f, 4)


# ---------------------------------------------------------------------------
# Correlation Check
# ---------------------------------------------------------------------------
def check_correlation_limit(symbol, active_picks):
    """Check if adding this symbol exceeds correlation group limit."""
    for group_name, group_symbols in CORRELATION_GROUPS.items():
        if symbol in group_symbols:
            count = sum(1 for p in active_picks if p["symbol"] in group_symbols)
            if count >= MAX_PER_CORR_GROUP:
                return False, f"Correlation group '{group_name}' full ({count}/{MAX_PER_CORR_GROUP})"
    return True, "OK"


# ---------------------------------------------------------------------------
# Main Engine
# ---------------------------------------------------------------------------
def load_picks(filepath):
    try:
        with open(filepath) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _dedupe_picks(picks):
    """Dedupe picks by pick id (or symbol+strategy+timestamp fallback).
    Prevents duplicate emissions of the same closed trade under two source_system
    tags — downstream aggregators (audit_trail/backfill.py) apply a <1 fraction
    heuristic to realized_pnl_pct that 100x-inflates values like -0.8789%.
    Keeping only one row per pick id structurally eliminates the duplicate path.
    See docs/FUTURES_REVIVAL_FORENSICS_20260405.md for the ZN=F incident."""
    if not isinstance(picks, list):
        return picks
    seen = set()
    out = []
    for p in picks:
        if not isinstance(p, dict):
            out.append(p)
            continue
        pid = p.get("id") or ""
        if not pid:
            pid = f"{p.get('strategy','')}::{p.get('symbol','')}::{str(p.get('timestamp',''))[:19]}::{p.get('entry_price','')}"
        if pid in seen:
            continue
        seen.add(pid)
        out.append(p)
    return out


def save_picks(picks, filepath):
    def _clean(obj):
        if isinstance(obj, dict):
            return {k: _clean(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_clean(v) for v in obj]
        if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            return None
        if hasattr(obj, "item"):
            v = obj.item()
            return None if isinstance(v, float) and (math.isnan(v) or math.isinf(v)) else v
        return obj

    picks = _dedupe_picks(picks)
    with open(filepath, "w") as f:
        json.dump(_clean(picks), f, indent=2, default=str)


def main():
    parser = argparse.ArgumentParser(description="Institutional Picks Engine v1.0")
    parser.add_argument("--status", action="store_true", help="Show portfolio status")
    parser.add_argument("--expand", action="store_true", help="Scan expanded universe")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print("=" * 60)
    print("INSTITUTIONAL PICKS ENGINE v1.0")
    print("=" * 60)
    start = time.time()

    # Load existing picks (dedupe closed on load — scrubs historical duplicates
    # that caused ZN=F to appear twice and 100x-inflate via backfill heuristic).
    active = load_picks(INSTITUTIONAL_PICKS_FILE)
    closed = _dedupe_picks(load_picks(INSTITUTIONAL_CLOSED_FILE))

    # Fetch data
    symbols = list(UNIVERSE.keys())
    print(f"\n[1/5] Fetching market data ({len(symbols)} symbols)...")
    data = fetch_data(symbols)

    # Fetch VIX
    vix_data = None
    try:
        vix_raw = yf.download("^VIX", period="3mo", interval="1d", progress=False)
        if len(vix_raw) > 0:
            vix_data = vix_raw
    except Exception:
        pass

    # Detect regime
    spy_data = data.get("SPY")
    regime = detect_regime(spy_data, vix_data)
    vix_val = float(vix_data["Close"].iloc[-1]) if vix_data is not None and len(vix_data) > 0 else 0
    print(f"\n[2/5] Market Regime: {regime} (VIX={vix_val:.1f})")

    # Check existing picks PnL
    print(f"\n[3/5] Checking {len(active)} active picks...")
    for pick in active:
        sym = pick["symbol"]
        if sym in data:
            pick["current_price"] = float(data[sym]["Close"].iloc[-1])
            entry = pick.get("entry_price", 0)
            cur = pick["current_price"]
            d = pick.get("direction", "LONG")
            if entry:
                pnl = (cur - entry) / entry * 100 if d == "LONG" else (entry - cur) / entry * 100
                pick["unrealized_pnl_pct"] = round(pnl, 4)

    # Auto-close: SL hits, max hold exceeded, hard circuit breaker
    HARD_CIRCUIT_BREAKER_PCT = -15  # absolute max loss per pick — no exceptions
    now = datetime.now(timezone.utc)
    still_active = []
    for pick in active:
        pnl = pick.get("unrealized_pnl_pct", 0)
        ac = pick.get("asset_class", "EQUITY")
        params = RISK_PARAMS.get(ac, RISK_PARAMS["EQUITY"])

        close_reason = None
        # Hard circuit breaker: -15% max loss per pick (catches IONQ -96.65% scenarios)
        if pnl is not None and pnl < HARD_CIRCUIT_BREAKER_PCT:
            close_reason = f"CIRCUIT BREAKER: catastrophic loss ({pnl:.2f}%)"
        elif pnl is not None and pnl < params["sl"] * 100:
            close_reason = f"Stop loss hit ({pnl:.2f}%)"

        ts = pick.get("timestamp", "")
        if ts:
            try:
                created = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                days_held = (now - created).days
                if days_held > params["max_hold"]:
                    close_reason = f"Max hold exceeded ({days_held}d > {params['max_hold']}d)"
            except Exception:
                pass

        if close_reason:
            pick["status"] = "CLOSED"
            pick["close_reason"] = close_reason
            pick["closed_at"] = now.isoformat()
            pick["realized_pnl_pct"] = pick.get("unrealized_pnl_pct", 0)
            closed.append(pick)
            print(f"  CLOSED: {pick['symbol']} {pick['strategy']} — {close_reason}")
        else:
            still_active.append(pick)
    active = still_active

    # Scan for new signals
    print(f"\n[4/5] Scanning {len(data)} symbols with {len(STRATEGIES)} strategies...")
    new_signals = []
    active_strat_sym = {(p["strategy"], p["symbol"]) for p in active}
    today = now.strftime("%Y-%m-%d")

    for sym, df in data.items():
        info = UNIVERSE.get(sym, {"class": "EQUITY"})
        ac = info.get("class", "EQUITY")
        params = RISK_PARAMS.get(ac, RISK_PARAMS["EQUITY"])

        for strat_name, strat_fn in STRATEGIES:
            if (strat_name, sym) in active_strat_sym:
                continue

            try:
                if strat_name in ("pairs_divergence", "dual_momentum", "sector_rotation_enhanced", "credit_spread", "commodity_momentum"):
                    result = strat_fn(df, sym, info, regime, data)
                else:
                    result = strat_fn(df, sym, info, regime)

                if result is None:
                    continue

                # Correlation check
                ok, reason = check_correlation_limit(sym, active + new_signals)
                if not ok:
                    continue

                # Class limit check
                class_count = sum(1 for p in active + new_signals if p.get("asset_class") == ac)
                if class_count >= params["max_picks"]:
                    continue

                price = float(df["Close"].iloc[-1])
                # Per-symbol vol-normalized SL/TP for FUTURES (overrides flat 3% pool).
                # See docs/FUTURES_REVIVAL_FORENSICS_20260405.md — flat pool gave 0.28 R:R.
                if ac == "FUTURES":
                    _fut = FUTURES_SL_TP_BY_SYMBOL.get(sym, {
                        "sl_pct": FUTURES_DEFAULT_SL_PCT,
                        "tp_pct": FUTURES_DEFAULT_TP_PCT,
                    })
                    _sl_pct = _fut["sl_pct"]
                    _tp_pct = _fut["tp_pct"]
                    if result["direction"] == "LONG":
                        sl = price * (1 - _sl_pct)
                        tp = result.get("take_profit") or price * (1 + _tp_pct)
                        # Enforce R:R >= 2.0 minimum
                        if (tp - price) < 2.0 * (price - sl):
                            tp = price * (1 + _tp_pct)
                    else:
                        sl = price * (1 + _sl_pct)
                        tp = result.get("take_profit") or price * (1 - _tp_pct)
                        if (price - tp) < 2.0 * (sl - price):
                            tp = price * (1 - _tp_pct)
                else:
                    if result["direction"] == "LONG":
                        tp = result.get("take_profit", price * (1 + abs(params["tp"])))
                        sl = price * (1 + params["sl"])
                    else:
                        tp = result.get("take_profit", price * (1 - abs(params["tp"])))
                        sl = price * (1 - params["sl"])

                signal = {
                    "strategy": strat_name,
                    "symbol": sym,
                    "asset_class": ac,
                    "category": ac.lower().replace("_", ""),
                    "sector": info.get("sector", ""),
                    "direction": result["direction"],
                    "signal_type": result["signal_type"],
                    "entry_price": price,
                    "current_price": price,
                    "take_profit": tp,
                    "stop_loss": sl,
                    "confidence": result["confidence"],
                    "risk_reward": abs(tp - price) / abs(sl - price) if abs(sl - price) > 0 else 1.0,
                    "reason": result["reason"],
                    "regime": regime,
                    "id": f"{strat_name}::{sym}::{today}",
                    "timestamp": now.isoformat(),
                    "status": "OPEN",
                    "source_system": "institutional_picks_engine",
                }
                new_signals.append(signal)

            except Exception as e:
                pass

    # Sort by confidence, take top picks
    new_signals.sort(key=lambda x: -x["confidence"])

    # Strategy concentration cap
    MAX_PER_STRATEGY = 8
    strat_counts = {}
    for p in active:
        s = p.get("strategy", "")
        strat_counts[s] = strat_counts.get(s, 0) + 1

    filtered = []
    for s in new_signals:
        st = s["strategy"]
        if strat_counts.get(st, 0) < MAX_PER_STRATEGY:
            filtered.append(s)
            strat_counts[st] = strat_counts.get(st, 0) + 1
    new_signals = filtered

    # Save
    print(f"\n[5/5] Results...")
    if not args.dry_run and new_signals:
        active.extend(new_signals)

    if not args.dry_run:
        save_picks(active, INSTITUTIONAL_PICKS_FILE)
        save_picks(closed, INSTITUTIONAL_CLOSED_FILE)

    # Report
    elapsed = time.time() - start
    print(f"\n{'=' * 60}")
    print(f"  SCAN COMPLETE ({elapsed:.1f}s)")
    print(f"{'=' * 60}")
    print(f"  Regime:       {regime} (VIX={vix_val:.1f})")
    print(f"  Active picks: {len(active)}")
    print(f"  Closed picks: {len(closed)}")
    print(f"  New signals:  {len(new_signals)}")

    if new_signals:
        print(f"\n  NEW SIGNALS:")
        for s in new_signals[:15]:
            print(f"    {s['direction']:5s} {s['symbol']:12s} @ ${s['entry_price']:.2f} | "
                  f"conf={s['confidence']:.2f} | {s['strategy']} | {s['reason'][:50]}")

    # Portfolio summary by class
    if active:
        print(f"\n  PORTFOLIO BY CLASS:")
        by_class = {}
        for p in active:
            ac = p.get("asset_class", "?")
            if ac not in by_class:
                by_class[ac] = {"long": 0, "short": 0, "pnls": []}
            d = p.get("direction", "LONG")
            if d == "LONG":
                by_class[ac]["long"] += 1
            else:
                by_class[ac]["short"] += 1
            pnl = p.get("unrealized_pnl_pct", 0)
            if pnl is not None:
                by_class[ac]["pnls"].append(pnl)

        for ac, info in sorted(by_class.items()):
            pnls = info["pnls"]
            avg_pnl = sum(pnls) / len(pnls) if pnls else 0
            print(f"    {ac:15s} {info['long']}L/{info['short']}S  avg PnL={avg_pnl:+.2f}%")

    # Long/Short balance
    total = len(active)
    longs = sum(1 for p in active if p.get("direction") == "LONG")
    shorts = total - longs
    print(f"\n  Long/Short: {longs}L / {shorts}S ({longs/total*100:.0f}%/{shorts/total*100:.0f}%)" if total > 0 else "")


if __name__ == "__main__":
    main()
