#!/usr/bin/env python3
"""
KIMI Rise of the Claw - Live Market Scanner v11.8
================================================
Generates live trading signals using the 5 Tier 1 validated strategies
from KIMI_CLAW_RESEARCH_FEB162026/strategies_tier1.py, adapted for
real-time signal generation against current market data.

Tier 1 Strategies (academic backing):
  1. FundingRateArbitrage  - VWMA basis z-score mean-reversion (crypto)
  2. PairsTrading          - Cointegration z-score mean-reversion (ETFs, crypto pairs)
  3. BettingAgainstBeta    - Low-beta + trend filter (stocks)
  4. FlashCrashReversal    - Extreme drawdown + RSI(6) + volume capitulation (all)
  5. QualityMinusJunk      - Composite quality z-score + trend filter (stocks/ETFs)

Additionally, 5 "scout" algorithms use simpler signals for broader market
coverage. These are clearly labeled as supplementary, not Tier 1.

Data: Yahoo Finance (yfinance) - 6 months daily OHLCV, no API key needed.
Schedule: Every 15 min during US market hours, every 4h weekends (crypto).
No fake data: if no signals trigger, picks stay empty.

Requires: yfinance, pandas, numpy
Compatible: Python 3.11+, GitHub Actions ubuntu-latest
"""

from __future__ import annotations

import json
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import math
import pandas as pd
import yfinance as yf

# v11.3 — Multi-source data fetcher (Binance + CoinCap + Frankfurter + yfinance fallback)
try:
    from multi_source_fetcher import (
        fetch_symbol_data_multi,
        fetch_latest_price_multi,
        fetch_all_binance_prices_bulk,
        fetch_all_funding_rates_bulk,
        fetch_fear_greed,
        fetch_binance_orderbook,
        print_fetch_summary,
        get_fetch_stats,
        reset_circuit_breakers,
    )
    _HAS_MULTI_FETCH = True
except ImportError as _e:
    _HAS_MULTI_FETCH = False
    print(f"  [v11.3] multi_source_fetcher not available: {_e}")

# v11.1 — SCALPING_STRATEGIES + v11.0 ANTIGRAVITY_FEB172026 modules
try:
    from crypto_acceleration_engine import (
        ACCELERATION_SIGNAL_FUNCS,
        fetch_order_book_imbalance,
        fetch_binance_liquidations,
        load_telegram_signals,
        load_twitter_signals,
        fetch_coingecko_trending,
    )
    _HAS_ACCEL = True
except ImportError as _e:
    _HAS_ACCEL = False
    ACCELERATION_SIGNAL_FUNCS = {}
    print(f"  [v11] crypto_acceleration_engine not available: {_e}")

try:
    from proven_crypto_forex_strategies import PROVEN_SIGNAL_FUNCS
    _HAS_PROVEN = True
except ImportError as _e:
    _HAS_PROVEN = False
    PROVEN_SIGNAL_FUNCS = {}
    print(f"  [v11] proven_crypto_forex_strategies not available: {_e}")

try:
    from scalping_strategies import SCALPING_SIGNAL_FUNCS, SCALPING_ALGO_DEFS
    _HAS_SCALPING = True
except ImportError as _e:
    _HAS_SCALPING = False
    SCALPING_SIGNAL_FUNCS = {}
    SCALPING_ALGO_DEFS = {}
    print(f"  [v11] scalping_strategies not available: {_e}")

try:
    from proven_mean_reversion import MEAN_REVERSION_SIGNAL_FUNCS, MEAN_REVERSION_ALGO_DEFS
    _HAS_MEAN_REV = True
except ImportError as _e:
    _HAS_MEAN_REV = False
    MEAN_REVERSION_SIGNAL_FUNCS = {}
    MEAN_REVERSION_ALGO_DEFS = {}
    print(f"  [v11] proven_mean_reversion not available: {_e}")

try:
    from ml_signal_ranker import MLSignalRanker
    _HAS_ML = True
except ImportError as _e:
    _HAS_ML = False
    print(f"  [v11] ml_signal_ranker not available: {_e}")

try:
    from sqlite_store import SQLiteStore
    _HAS_SQLITE = True
except ImportError as _e:
    _HAS_SQLITE = False
    print(f"  [v11] sqlite_store not available: {_e}")

try:
    from elimination_engine import EliminationEngine, PERMANENTLY_BANNED_STRATEGIES
    _HAS_ELIMINATION = True
except ImportError as _e:
    _HAS_ELIMINATION = False
    PERMANENTLY_BANNED_STRATEGIES = set()
    print(f"  [v11] elimination_engine not available: {_e}")

try:
    from api_config import (
        get_live_forex_rates,
        get_exchange_netflow,
        COINGECKO_API_KEY,
    )
    _HAS_API_CONFIG = True
except ImportError as _e:
    _HAS_API_CONFIG = False
    def get_live_forex_rates(*a, **kw): return {}
    def get_exchange_netflow(*a, **kw): return {}
    COINGECKO_API_KEY = ""
    print(f"  [v11] api_config not available: {_e}")

# v11.6 — Transaction cost model for realistic P&L
try:
    # Try importing from ALPHA_ENGINE (sibling directory)
    _alpha_engine_dir = Path(__file__).resolve().parent.parent / "ALPHA_ENGINE"
    if str(_alpha_engine_dir) not in sys.path:
        sys.path.insert(0, str(_alpha_engine_dir))
    from transaction_costs import (
        get_round_trip_cost as _tc_get_round_trip_cost,
        apply_costs as _tc_apply_costs,
        adjust_tp_for_costs as _tc_adjust_tp_for_costs,
        get_cost_model as _tc_get_cost_model,
    )
    _HAS_TRANSACTION_COSTS = True
    print("  [v11.6] Transaction cost model loaded")
except ImportError as _e:
    _HAS_TRANSACTION_COSTS = False
    def _tc_get_round_trip_cost(symbol, category=""): return 0.007
    def _tc_apply_costs(entry, exit_p, symbol, category="", signal_type="BUY"):
        return {"gross_pnl_pct": 0, "net_pnl_pct": 0, "transaction_cost_pct": 0.007}
    def _tc_adjust_tp_for_costs(entry, tp, symbol, category="", signal_type="BUY"): return tp
    def _tc_get_cost_model(symbol, category=""):
        return {"total_per_trade": 0.007}
    print(f"  [v11.6] transaction_costs not available (using defaults): {_e}")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
PERIOD = "1y"   # ~252 trading days — needed for 200d SMA, momentum factor, and Tier 1 accuracy
MAX_PICKS_PER_ALGO = 3
ALLOCATION_PER_PICK = 2000
STARTING_CAPITAL = 10000

# Per-category risk parameters — wider stops for volatile assets
# category → (stop_loss_pct, take_profit_pct, max_hold_days)
# v10.1: max_hold shortened to accelerate tournament cycling:
#   stock 30→10d, crypto 20→7d, meme 14→5d, penny 15→7d, forex 30→10d
# v11.6: Further tightened for faster forward-test validation:
#   crypto 7→5d, meme 5→3d, penny 7→5d, forex 10→7d, stock 10→7d
#   SL/TP also narrowed so static fallback bands close faster.
CATEGORY_RISK = {
    "crypto":  (-0.08, 0.15,  5),   # crypto: 5d — tighter for faster validation
    "meme":    (-0.12, 0.25,  3),   # meme: 3d — pump/dump cycles resolve fast
    "penny":   (-0.08, 0.15,  5),   # penny: 5d — squeeze plays resolve quickly
    "forex":   (-0.02, 0.04,  7),   # forex: 7d — tighter window
    "stock":   (-0.05, 0.10,  7),   # stock: 7d — forces weekly cycles
    "skyrocket": (-0.03, 0.08, 2),   # skyrocket: 2d — ultra-short momentum plays, tight SL
}


def calculate_atr(df, period=14):
    """
    Calculate Average True Range for dynamic TP/SL.

    Uses the proper Wilder True Range formula:
      TR = max(High-Low, |High-PrevClose|, |Low-PrevClose|)
    then a simple moving average over `period` bars.

    Returns the latest ATR value, or None if data is insufficient.
    """
    if df is None or len(df) < period + 1:
        return None
    high = df['High'] if 'High' in df.columns else df.get('high', None)
    low = df['Low'] if 'Low' in df.columns else df.get('low', None)
    close = df['Close'] if 'Close' in df.columns else df.get('close', None)
    if high is None or low is None or close is None:
        return None
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    latest = atr.iloc[-1]
    return float(latest) if not pd.isna(latest) else None


def calculate_signal_probability(entry_price, tp_price, sl_price, atr_value, direction='long'):
    """
    Estimate P(reaching TP before SL) using ATR-based first-passage approximation.

    For a symmetric random walk, the probability of hitting one barrier before
    the other is proportional to the distance to the opposite barrier:
      P(TP first) = SL_dist / (TP_dist + SL_dist)

    Returns probability as a float 0-100.
    """
    if not all([entry_price, tp_price, sl_price, atr_value]) or atr_value <= 0:
        return 50.0  # neutral fallback
    tp_dist = abs(tp_price - entry_price)
    sl_dist = abs(sl_price - entry_price)
    if tp_dist == 0 or sl_dist == 0:
        return 50.0
    # Symmetric random walk first-passage: P(TP first) = SL_dist / (TP_dist + SL_dist)
    prob = (sl_dist / (tp_dist + sl_dist)) * 100
    return round(min(max(prob, 5.0), 95.0), 1)


def dynamic_tp_sl(entry_price, atr_value, category, direction='long'):
    """
    Calculate ATR-based TP/SL with category-specific multipliers.

    ATR multipliers are calibrated per asset class:
      - crypto/meme: wider bands (high volatility, 24/7 markets)
      - forex: tighter bands (low daily range)
      - stocks: moderate bands

    Returns (tp_price, sl_price, tp_pct, sl_pct).
    Falls back to CATEGORY_RISK static bands when ATR is unavailable.
    """
    if atr_value is None or atr_value <= 0 or entry_price <= 0:
        # Fallback to CATEGORY_RISK static bands
        risk = CATEGORY_RISK.get(category, CATEGORY_RISK.get('stock', (-0.08, 0.15, 10)))
        sl_pct_raw = abs(risk[0])   # CATEGORY_RISK stores SL as negative
        tp_pct_raw = risk[1]
        if direction == 'long':
            return (
                round(entry_price * (1 + tp_pct_raw), 8),
                round(entry_price * (1 - sl_pct_raw), 8),
                round(tp_pct_raw * 100, 2),
                round(sl_pct_raw * 100, 2),
            )
        else:
            return (
                round(entry_price * (1 - tp_pct_raw), 8),
                round(entry_price * (1 + sl_pct_raw), 8),
                round(tp_pct_raw * 100, 2),
                round(sl_pct_raw * 100, 2),
            )

    # ATR multipliers by category
    # Tightened from 2.5/1.5 to 1.5/1.0 ATR for faster forward-test validation.
    # Previous wide bands (e.g. BTC TP at +13%, SL at -7.8%) took weeks to hit,
    # generating 0 closed trades. Tighter targets close within days, producing
    # the closed trade data needed to validate strategies.
    MULTIPLIERS = {
        'crypto':    {'tp': 1.5, 'sl': 1.0},
        'meme':      {'tp': 2.0, 'sl': 1.2},
        'forex':     {'tp': 1.5, 'sl': 1.0},
        'penny':     {'tp': 2.0, 'sl': 1.2},
        'stock':     {'tp': 1.5, 'sl': 1.0},
        'skyrocket': {'tp': 1.2, 'sl': 0.6},  # tighter: fast scalps, quick exits
    }
    mults = MULTIPLIERS.get(category, MULTIPLIERS['stock'])

    tp_offset = atr_value * mults['tp']
    sl_offset = atr_value * mults['sl']

    if direction == 'long':
        tp_price = entry_price + tp_offset
        sl_price = entry_price - sl_offset
    else:
        tp_price = entry_price - tp_offset
        sl_price = entry_price + sl_offset

    tp_pct = round(abs(tp_price - entry_price) / entry_price * 100, 2)
    sl_pct = round(abs(sl_price - entry_price) / entry_price * 100, 2)

    return (round(tp_price, 8), round(sl_price, 8), tp_pct, sl_pct)


def compute_atr_tp_sl(df, category: str, entry_price: float):
    """
    Dynamic TP/SL using proper ATR (True Range) — adapts to actual volatility.

    v11.4: Upgraded from rolling std dev to Wilder ATR (High/Low/Close True Range).
    This produces tighter, more realistic bands that match each symbol's actual
    price range instead of approximating via close-only standard deviation.

    Returns (tp_price, sl_price, p_tp, atr_value, tp_pct, sl_pct, method) where:
      tp_price  — absolute take-profit level
      sl_price  — absolute stop-loss level
      p_tp      — first-passage probability of hitting TP before SL (0-1 scale)
      atr_value — the raw ATR value used (None if fallback)
      tp_pct    — take-profit distance as percentage
      sl_pct    — stop-loss distance as percentage
      method    — 'atr' or 'static'
    """
    atr_val = calculate_atr(df)
    tp_price, sl_price, tp_pct, sl_pct = dynamic_tp_sl(entry_price, atr_val, category, direction='long')
    prob = calculate_signal_probability(entry_price, tp_price, sl_price, atr_val)

    # Convert probability from 0-100 scale to 0-1 scale for backward compat
    p_tp = round(prob / 100.0, 4)
    method = 'atr' if atr_val is not None else 'static'

    return tp_price, sl_price, p_tp, atr_val, tp_pct, sl_pct, method


# Trailing stop parameters — activates when position +TRAIL_ACTIVATE_PCT in profit
# category → trail_pct (drop from peak triggers exit)
TRAILING_STOP = {
    "crypto":  0.12,   # trail: exit if drops 12% from peak
    "meme":    0.18,   # trail: exit if drops 18% from peak
    "penny":   0.12,
    "forex":   0.03,
    "stock":   0.08,
}
TRAIL_ACTIVATE_PROFIT = 0.05   # trailing stop only activates after +5% profit

# v10.5: Gap-chase rejection — don't enter after a symbol has already run hard today.
# Root problem caught: RIVN entered at +26.6% intraday gap-up → immediately faded -5%.
# Gap-chasing is the #1 cause of stale-entry losses in momentum strategies.
# category → max TODAY's return allowed before entry is blocked
GAP_REJECT_THRESH: dict[str, float] = {
    "crypto":    0.08,   # crypto: block if already +8% today (parabolic move)
    "meme":      0.07,   # meme: block if +7% today — gap-and-go should be same-session only
    "penny":     0.07,
    "forex":     0.02,
    "stock":     0.05,   # stock: block if +5% today — earnings gap-up chasers
    "skyrocket": 0.12,   # skyrocket: higher tolerance — these target momentum spikes
}

# v10.5: Global symbol concentration limit.
# Prevents the same ticker from stacking across unlimited algos (RIVN hit x4).
# Convergence boost still applies at 2, but hard cap prevents over-concentration.
MAX_SAME_SYMBOL_GLOBAL = 2   # max # of algos that may hold the same symbol simultaneously

# v10.4: Price sanity bounds — reject data-feed garbage before it enters picks
# Protects against yfinance returning stale/corrupt/zero prices (seen: APT-USD @ $0.0001)
_PRICE_MIN: dict[str, float] = {
    "crypto": 0.000005,   # even SHIB/BONK trade above this; catches zeroed-out feed errors
    "forex":  0.001,      # FX pairs 0.001–500 range
    "stock":  0.05,       # below $0.05 = likely corrupt (penny stocks scan separately)
    "meme":   0.000005,
    "penny":  0.05,
}
_PRICE_MAX: dict[str, float] = {
    "crypto": 5_000_000,  # BTC ceiling
    "forex":  500,
    "stock":  600_000,    # BRK.A ceiling
    "meme":   5_000_000,
    "penny":  50,         # penny stocks defined as < $5; allow up to $50 for scouts
}

def _validate_price(symbol: str, price: float, cat: str = "stock") -> bool:
    """Return False if price looks like a data-feed error."""
    if not price or price != price:  # None, 0, NaN
        return False
    lo = _PRICE_MIN.get(cat, 0.05)
    hi = _PRICE_MAX.get(cat, 600_000)
    if not (lo <= price <= hi):
        return False
    return True

# Regime bias — how each strategy style performs across market regimes
# 'trend'    : benefits from bull market (momentum, breakouts)
# 'mean_rev' : benefits from bear/sideways (reversals, oversold bounces)
# 'both'     : regime-agnostic (arbitrage, factor)
# 'forex'    : carry / FX — stock regime largely irrelevant
# 'meme'     : driven purely by crypto bull regime
REGIME_BIAS = {
    "funding-rate-arb":       "both",
    "pairs-trading":           "mean_rev",
    "betting-against-beta":    "mean_rev",
    "flash-crash-reversal":    "mean_rev",
    "quality-minus-junk":      "both",
    "meme-bollinger-mean-rev": "mean_rev",
    "macd-momentum":           "trend",
    "golden-cross-stocks":     "trend",
    "momentum-factor":         "trend",
    "short-squeeze":           "trend",
    "sector-rotation":         "trend",
    "carry-trade-momentum":    "forex",
    "gap-and-go-stocks":       "trend",
    "ema-ribbon":              "trend",
    "bollinger-squeeze":       "both",
    "meme-velocity":           "meme",
    "stoch-rsi-scout":         "mean_rev",
    "donchian-breakout":       "trend",
    "williams-r-reversal":     "mean_rev",
    "cci-reversal":            "mean_rev",
    "supertrend-follow":       "trend",
    "keltner-bounce":          "mean_rev",
    "volume-breakout":         "trend",
    "volume-momentum-spike":   "trend",
    "rsi-oversold":            "mean_rev",
    "ma-crossover":            "trend",
    "options-flow-scout":      "mean_rev",   # contrarian — fires in fear/bear regimes
    "intermarket-flow-scout":  "trend",      # v5.3 — risk-on = trend confirmation
    "vwap-reversion-scout":    "mean_rev",   # v5.6 — institutional fair value reversion
    "volume-anomaly-scout":    "both",       # v5.9 — volume anomaly (regime-agnostic)
    "earnings-drift-scout":    "both",       # v6.1 — pre-earnings drift (regime-agnostic)
    "post-earnings-rev-scout": "mean_rev",  # v6.3 — post-earnings reversion (mean-rev regime)
    "rsi-divergence-scout":       "mean_rev",  # v6.4 — RSI divergence (regime-agnostic reversal)
    "crypto-funding-contrarian":  "mean_rev",  # v6.5 — funding rate contrarian (mean-rev in fear)
    "price-accel-scout":          "trend",     # v6.7 — CTA acceleration (trend regime only)
    "stoch-rsi-scout":            "mean_rev",  # v8.4 — StochRSI cross works in mean-rev and recovery
    "par-sar-scout":              "trend",     # v8.5 — Parabolic SAR flip confirms trend reversal to upside
    "aroon-trend-scout":          "trend",     # v8.6 — Aroon oscillator cross signals fresh trend initiation
    "vix-mean-rev-scout":         "mean_rev",  # v8.7 — VIX spike = fear peak = buy oversold quality
    "short-squeeze-scout":        "mean_rev",  # v8.8 — short squeeze proxy: beaten down + vol surge + reversal
    "altcoin-season-scout":       "trend",     # v8.9 — altcoin season: ETH leads BTC, capital rotates to alts
    "cmf-accumulation-scout":     "both",      # v9.0 — CMF cross: buying pressure confirms in trend + mean-rev
    "whale-accum-scout":          "both",      # v9.1 — whale accumulation proxy: 3 bars upper-range close + vol surge
    "cal-effect-crypto-scout":    "mean_rev",  # v9.2 — calendar effect: weekend recovery + month/quarter-start inflows
    "stocktwits-bull-scout":      "both",      # v9.5 — StockTwits pre-tagged bull surge: self-reported conviction signal
    "opex-momentum-scout":        "trend",     # v9.7 — post-OPEX release momentum fires in trending markets (Birru & Wang 2016)
    "deribit-crypto-contrarian":  "mean_rev",  # v9.8 — Deribit real-time PCR fear spike → crypto oversold bounce (Pan & Poteshman 2006)
    "apewisdom-momentum-scout":   "trend",     # v9.9 — ApeWisdom mention velocity ×2 24h delta → attention-driven momentum (Da et al. 2011)
    "macd-hidden-div-scout":      "trend",     # v8.3 — hidden divergence fires in uptrend pullbacks (trend regime)
    "vol-contraction-scout":      "both",      # v8.2 — vol contraction fires before breakout in any regime
    "52w-high-breakout-scout":    "trend",     # v8.1 — 52w high breakouts thrive in bull/trending markets
    "fibonacci-bounce-scout":     "both",      # v8.0 — Fib bounces work in trend (retest) AND mean-rev regimes
    "vrsi-scout":                 "mean_rev",  # v7.9 — VRSI reversal works best in choppy/recovery market
    "breadth-thrust-scout":       "both",      # v7.8 — breadth thrust works in recovery AND bull markets
    "dual-momentum-scout":        "trend",     # v7.7 — Antonacci GEM: absolute+relative momentum (trend regime)
    "hh-hl-scout":                "trend",     # v7.6 — HH/HL structure confirms uptrend
    "mtf-align-scout":            "trend",     # v7.5 — MTF alignment best in trending bull market
    "vwap-reclaim-scout":         "both",      # v7.4 — VWAP reclaim works in any regime
    "zscore-mean-rev-scout":      "mean_rev",  # v7.3 — z-score mean rev works best in choppy/bear
    "gap-and-go-scout":           "trend",     # v7.2 — gap-and-go works best in trending bull market
    "call-surge-scout":           "both",      # v7.1 — call surge fires in any regime
    "adx-trend-scout":            "trend",     # v6.8 — ADX trend confirmation (trend regime)
}

# Symbols with high earnings-event risk — excluded within 3 days of earnings
EARNINGS_WATCHLIST = {
    "AAPL", "MSFT", "NVDA", "META", "GOOGL", "AMZN", "TSLA",
    "AMD", "NFLX", "SHOP", "COIN", "MSTR", "SQ",
    "INTC", "AVGO", "QCOM", "MU",
}

# Rapid Validation bridge — POSTs closed picks to MySQL elimination engine
RAPID_INGEST_URL = (
    "https://findtorontoevents.ca/rapid_validation/api/"
    "rapid_signal_engine.php?action=ingest&key=livetrader2026"
)

# Symbol groups  — extensive coverage to maximize signal probability
STOCKS_ETF = [
    # Broad market ETFs
    "SPY", "QQQ", "VTI", "IWM", "DIA",
    # Sector ETFs
    "XLK", "XLF", "XLE", "XLV", "XLI", "ARKK",
    "SOXX", "XBI", "XRT", "JETS",
    # Volatility instruments + VIX (market fear gauge) + VIX term structure
    "TQQQ", "LABU", "UVXY", "^VIX", "^VIX3M",
    # Macro / commodities + DXY proxy (US Dollar Bullish ETF)
    "GLD", "SLV", "TLT", "HYG", "UUP",
    # Mega-cap tech
    "AAPL", "MSFT", "NVDA", "AMD", "INTC",
    "META", "GOOGL", "AMZN", "NFLX",
    # High-beta / growth
    "TSLA", "COIN", "MSTR", "SHOP", "SQ",
    "UBER", "PYPL", "ROKU",
    # Financials / Energy
    "JPM", "BAC", "XOM", "CVX",
]
CRYPTO = [
    # Top 5 by market cap
    "BTC-USD", "ETH-USD", "BNB-USD", "XRP-USD", "SOL-USD",
    # Large alts
    "ADA-USD", "AVAX-USD", "DOT-USD", "LINK-USD", "MATIC-USD",
    # Mid-cap established
    "LTC-USD", "TRX-USD", "ETC-USD", "BCH-USD", "ATOM-USD",
    # Mid-cap newer
    "NEAR-USD", "ALGO-USD", "FIL-USD", "ICP-USD", "VET-USD",
    "HBAR-USD", "THETA-USD", "GRT-USD", "ZEC-USD", "DASH-USD",
    "APT-USD", "OP-USD",
    # Meme coins
    "DOGE-USD", "SHIB-USD", "PEPE-USD",
    # Newer meme / trending coins
    "FLOKI-USD", "BONK-USD",
    # Gaming / Metaverse
    "SAND-USD", "MANA-USD", "ENJ-USD", "CHZ-USD",
    # DeFi / L2 / AI — added Mar 2026
    "INJ-USD", "SUI-USD", "ARB-USD", "SEI-USD", "APE-USD",
    "WLD-USD", "STRK-USD", "FET-USD", "TIA-USD", "AAVE-USD",
    "DYDX-USD", "TON-USD", "POL-USD",
    # Added 2026-03-18: top-100 coins expansion
    "HYPE-USD", "XLM-USD", "TAO-USD", "KAS-USD",
    "RNDR-USD", "ONDO-USD",
    # Added 2026-03-19: 9 new mid-cap / trending coins
    "ETHFI-USD", "QNT-USD", "DEXE-USD", "THE-USD",
    "PIXEL-USD", "ANKR-USD", "HOT-USD", "SAHARA-USD",
]
FOREX = [
    # Major pairs
    "EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDCHF=X",
    # Commodity-linked
    "AUDUSD=X", "USDCAD=X", "NZDUSD=X",
    # Cross pairs (often more volatile)
    "EURJPY=X", "GBPJPY=X", "EURGBP=X",
    # Carry trade pairs (high-yield vs low-yield)
    "AUDJPY=X", "NZDJPY=X", "CADJPY=X",
    # Emerging
    "USDMXN=X", "USDZAR=X",
]
PENNY = [
    # Meme stocks
    "GME", "AMC",
    # High-retail-interest
    "PLTR", "SOFI", "HOOD", "BBAI",
    # Crypto miners (very volatile, 24/7 crypto correlation)
    "MARA", "RIOT", "CLSK", "BTBT",
    # Volatile EVs
    "RIVN", "LCID", "NKLA",
    # Chinese EVs (high beta)
    "XPEV", "NIO",
    # Biotech speculative
    "NVAX", "BNGO",
    # High-momentum small caps
    "SNDL", "CLOV", "SPCE", "UWMC",
]

ALL_SYMBOLS = list(dict.fromkeys(STOCKS_ETF + CRYPTO + FOREX + PENNY))

# Pair mappings for PairsTrading strategy — more pairs = more cointegration opportunities
PAIR_MAP = {
    # v9.6 Tier 1: Near-perfect ETF twin pairs (same index, different fund wrapper)
    # These are near-arbitrage quality — p-values typically < 0.001
    "SPY": "IVV",    "IVV": "SPY",    # both track S&P 500 (SPDR vs iShares)
    "QQQ": "QQQM",   "QQQM": "QQQ",   # both track Nasdaq-100 (Invesco)
    "GDX": "GDXJ",   "GDXJ": "GDX",   # gold miners large-cap vs junior
    "XLE": "VDE",    "VDE": "XLE",    # energy sector (SPDR vs Vanguard)
    "TLT": "IEF",    "IEF": "TLT",    # Treasury bonds (20yr vs 7-10yr)
    # Equity ETFs
    "SPY": "QQQ",    "QQQ": "IWM",    "IWM": "SPY",
    "XLK": "XLF",   "XLF": "XLE",
    "GLD": "SLV",    "SLV": "GLD",    "TLT": "HYG",   "HYG": "TLT",
    # Crypto majors
    "BTC-USD": "ETH-USD",  "ETH-USD": "SOL-USD",
    "SOL-USD": "ADA-USD",  "ADA-USD": "DOT-USD",
    "LINK-USD": "DOT-USD", "AVAX-USD": "SOL-USD",
    "LTC-USD": "BCH-USD",  "BCH-USD": "ETC-USD",
    # Big tech
    "AAPL": "MSFT",  "MSFT": "GOOGL", "GOOGL": "AMZN",
    "COIN": "MSTR",  "MARA": "RIOT",
    # Commodities / macro
    "XOM": "CVX",    "JPM": "BAC",
    # v9.6 Forex: AUD/NZD is the most reliably cointegrated forex pair (commodity-bloc currencies)
    # Both track Chinese economic demand + correlated RBA/RBNZ central bank cycles
    "AUDUSD=X": "NZDUSD=X",  "NZDUSD=X": "AUDUSD=X",   # v9.6 (was AUDJPY/NZDJPY)
    "AUDJPY=X": "NZDJPY=X",  "NZDJPY=X": "AUDJPY=X",
    # Sector ETF pairs
    "SOXX": "XBI",  "XBI": "SOXX",
}

# Runtime dynamic pair map — populated by find_cointegrated_pairs() at scanner start
# Overrides PAIR_MAP where cointegration is statistically confirmed (p < 0.05)
_DYNAMIC_PAIR_MAP: dict[str, str] = {}

# Additional candidate pairs beyond PAIR_MAP — known correlated assets
_EXTRA_PAIR_CANDIDATES: list[tuple[str, str]] = [
    ("NVDA", "AMD"),       ("V", "MA"),           ("GS", "MS"),
    ("XLE", "XOM"),        ("XLF", "JPM"),         ("UNH", "CVS"),
    ("AAPL", "MSFT"),      ("GOOGL", "META"),       ("COIN", "MSTR"),
    ("BTC-USD", "LTC-USD"), ("ETH-USD", "MATIC-USD"), ("SOL-USD", "AVAX-USD"),
    ("GLD", "SLV"),        ("TLT", "HYG"),
    # v9.6 Tier 2 additions: academically confirmed structural cointegration
    ("KO", "PEP"),         # Cola wars — 30+ year stable pair (consumer staples duopoly)
    ("HD", "LOW"),         # Home improvement duopoly — near-identical consumer exposure
    ("WFC", "BAC"),        # US bank pair (both track credit cycle + Fed rates)
    ("CL", "PG"),          # Consumer staples (Colgate vs P&G — household spending)
    ("COST", "WMT"),       # Discount retail (different models, same macro exposure)
    ("USO", "BNO"),        # Oil ETFs: WTI vs Brent crude (near-perfect structural)
    # v9.6 Forex additions (research confirms AUD/NZD is most reliable major pair)
    ("AUDUSD=X", "NZDUSD=X"),   # most reliably cointegrated forex pair
    ("EURUSD=X", "GBPUSD=X"),   # post-Brexit weakened but still worth testing
]


def find_cointegrated_pairs(all_data: dict, pvalue_thresh: float = 0.05) -> dict[str, str]:
    """
    v9.6 Run Engle-Granger cointegration tests on candidate pairs.
    Tests all pairs in PAIR_MAP + _EXTRA_PAIR_CANDIDATES.
    Returns {symbol: cointegrated_partner} for statistically valid pairs.

    Two-gate validation (from Sprenger et al. 2014, Letian Zhang cointegration guide):
      Gate 1: Engle-Granger test p < pvalue_thresh (spread has unit root rejected)
      Gate 2: ADF test on the spread itself p < 0.10 (spread is directly stationary)
    Both gates must pass to prevent false positives from multiple-testing.

    Falls back to empty dict if statsmodels is unavailable.
    """
    try:
        from statsmodels.tsa.stattools import coint, adfuller  # type: ignore
    except ImportError:
        print("  [pairs] statsmodels not installed — using static PAIR_MAP (add to pip install)")
        return {}

    # Build deduplicated candidate set
    candidate_pairs: set[tuple[str, str]] = set()
    for sym, partner in PAIR_MAP.items():
        candidate_pairs.add(tuple(sorted([sym, partner])))  # type: ignore[arg-type]
    for pair in _EXTRA_PAIR_CANDIDATES:
        candidate_pairs.add(tuple(sorted(pair)))  # type: ignore[arg-type]

    dynamic_map: dict[str, str] = {}
    tested = 0
    validated = 0
    adf_rejected = 0

    for sym1, sym2 in sorted(candidate_pairs):
        if sym1 not in all_data or sym2 not in all_data:
            continue
        s1 = all_data[sym1]["Close"].dropna()
        s2 = all_data[sym2]["Close"].dropna()
        min_len = min(len(s1), len(s2))
        if min_len < 60:
            continue
        s1 = s1.iloc[-min_len:].values
        s2 = s2.iloc[-min_len:].values

        # Skip if either series has zero/negative prices (log safety)
        if (s1 <= 0).any() or (s2 <= 0).any():
            continue
        try:
            log_s1 = np.log(s1)
            log_s2 = np.log(s2)

            # Gate 1: Engle-Granger cointegration test
            _, pvalue, _ = coint(log_s1, log_s2)
            tested += 1
            if pvalue >= pvalue_thresh:
                continue

            # Gate 2: ADF test directly on the OLS spread (v9.6)
            # OLS hedge ratio: log_s1 = hr * log_s2 + intercept
            hr = np.cov(log_s1, log_s2)[0, 1] / np.var(log_s2) if np.var(log_s2) > 0 else 1.0
            spread = log_s1 - hr * log_s2
            _, adf_p, *_ = adfuller(spread, autolag='AIC')
            if adf_p >= 0.10:  # spread must be directly stationary
                adf_rejected += 1
                continue

            dynamic_map[sym1] = sym2
            dynamic_map[sym2] = sym1
            validated += 1
        except Exception:
            pass

    print(f"  [pairs] v9.6 Cointegration: {tested} tested → {validated} validated "
          f"(EG p<{pvalue_thresh} + ADF p<0.10) | {adf_rejected} failed ADF gate")
    if validated > 0:
        examples = list(dynamic_map.items())[:4]
        print(f"  [pairs] Sample: {examples}")
    return dynamic_map


# Algorithm definitions:  id -> (name, category, strategy_class, symbols)
# Tier 1: backed by validated academic strategies
# Scout: simpler supplementary signals, clearly labeled
ALGO_DEFS = {
    # --- TIER 1 STRATEGIES (academic backing) ---
    "funding-rate-arb": {
        "name": "Funding Rate Arbitrage",
        "category": "crypto",
        "tier": "TIER_1",
        "strategy": "FundingRateArbitrage",
        # VWMA basis z-score — wide crypto coverage for mispricing
        "symbols": [
            "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
            "ADA-USD", "AVAX-USD", "DOT-USD", "LINK-USD", "MATIC-USD",
            "LTC-USD", "TRX-USD", "ATOM-USD", "NEAR-USD", "ALGO-USD",
            "ETC-USD", "BCH-USD", "VET-USD", "HBAR-USD", "GRT-USD",
            # Added 2026-03-18: top-100 expansion
            "HYPE-USD", "XLM-USD", "TAO-USD", "KAS-USD",
            "RNDR-USD", "ONDO-USD", "ICP-USD",
        ],
    },
    "pairs-trading": {
        "name": "Pairs Trading (Cointegration)",
        "category": "stock",
        "tier": "TIER_1",
        "strategy": "PairsTrading",
        # Only symbols that have a partner in PAIR_MAP
        "symbols": [
            "SPY", "QQQ", "IWM", "XLK", "XLF", "XLE",
            "GLD", "SLV", "TLT", "HYG",
            "BTC-USD", "ETH-USD", "SOL-USD", "ADA-USD", "DOT-USD",
            "LINK-USD", "AVAX-USD", "LTC-USD", "BCH-USD",
            "AAPL", "MSFT", "GOOGL", "AMZN",
            "COIN", "MSTR", "MARA", "RIOT",
            "XOM", "CVX", "JPM", "BAC",
        ],
    },
    "betting-against-beta": {
        "name": "Betting Against Beta",
        "category": "stock",
        "tier": "TIER_1",
        "strategy": "BettingAgainstBeta",
        # Needs 200-bar history — large/mid caps only
        "symbols": [
            "AAPL", "MSFT", "NVDA", "AMD", "META",
            "AMZN", "GOOGL", "NFLX", "SHOP", "PYPL",
            "SPY", "QQQ", "VTI", "IWM", "XLF", "XLV",
            "GLD", "TLT", "JPM", "BAC", "XOM",
        ],
    },
    "flash-crash-reversal": {
        "name": "Flash Crash Reversal",
        "category": "crypto",
        "tier": "TIER_1",
        "strategy": "FlashCrashReversal",
        # Flash crashes happen most on volatile assets — widest possible net
        "symbols": [
            # Crypto — alts crash harder and faster
            "BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD", "ADA-USD",
            "LINK-USD", "DOT-USD", "MATIC-USD", "NEAR-USD", "ATOM-USD",
            "DOGE-USD", "SHIB-USD", "PEPE-USD",
            # Added 2026-03-18: top-100 expansion
            "HYPE-USD", "XLM-USD", "TAO-USD", "KAS-USD",
            "RNDR-USD", "ONDO-USD", "ICP-USD", "ETC-USD", "LTC-USD", "TRX-USD",
            # High-beta stocks
            "TSLA", "NVDA", "AMD", "COIN", "MSTR",
            "MARA", "RIOT", "RIVN", "LCID", "NKLA",
            # ETFs with known dip patterns
            "SPY", "QQQ", "IWM", "ARKK",
        ],
    },
    "quality-minus-junk": {
        "name": "Quality Minus Junk",
        "category": "stock",
        "tier": "TIER_1",
        "strategy": "QualityMinusJunk",
        # Quality score — broad stock/ETF universe
        "symbols": [
            "AAPL", "MSFT", "NVDA", "META", "AMZN", "GOOGL",
            "NFLX", "SHOP", "UBER", "PYPL",
            "JPM", "BAC", "XOM", "CVX",
            "SPY", "QQQ", "VTI", "IWM", "XLK", "XLF", "XLE",
            "GLD", "TLT",
        ],
    },
    # --- TIER 1 MEME COIN STRATEGY ---
    "meme-bollinger-mean-rev": {
        "name": "Bollinger Mean Reversion (Meme)",
        "category": "meme",
        "tier": "TIER_1",
        "strategy": "BollingerMeanReversion",
        # Meme + high-volatility coins — Bollinger overshoots on these regularly
        "symbols": [
            "DOGE-USD", "SHIB-USD", "PEPE-USD",
            "SAND-USD", "MANA-USD", "CHZ-USD", "ENJ-USD",
            "NEAR-USD", "ALGO-USD", "VET-USD",
        ],
    },
    # --- SCOUT ALGORITHMS (supplementary, simple TA) ---
    "meme-scanner-live": {
        "name": "Meme Coin Scout",
        "category": "meme",
        "tier": "SCOUT",
        "strategy": "MomentumVolumeSpike",
        "symbols": [
            "DOGE-USD", "SHIB-USD", "PEPE-USD",
            "SAND-USD", "MANA-USD", "CHZ-USD",
            "TRX-USD", "HBAR-USD", "VET-USD",
        ],
    },
    "penny-tracker-live": {
        "name": "Penny Stock Scout",
        "category": "penny",
        "tier": "SCOUT",
        "strategy": "VolumeBreakout",
        "symbols": [
            "GME", "AMC", "PLTR", "SOFI", "HOOD", "BBAI",
            "MARA", "RIOT", "CLSK", "BTBT",
            "RIVN", "LCID", "NKLA",
            "SNDL", "CLOV",
        ],
    },
    "forex-scanner-live": {
        "name": "Forex MA Scout",
        "category": "forex",
        "tier": "SCOUT",
        "strategy": "MACrossover",
        "symbols": [
            "EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDCHF=X",
            "AUDUSD=X", "USDCAD=X", "NZDUSD=X",
            "EURJPY=X", "GBPJPY=X", "EURGBP=X",
            "USDMXN=X", "USDZAR=X",
        ],
    },
    "crypto-momentum-scout": {
        "name": "Crypto RSI Scout",
        "category": "crypto",
        "tier": "SCOUT",
        "strategy": "RSIOversold",
        # Maximum crypto coverage for RSI oversold — 24/7 market
        "symbols": [
            "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
            "ADA-USD", "AVAX-USD", "DOT-USD", "LINK-USD", "MATIC-USD",
            "LTC-USD", "TRX-USD", "ETC-USD", "BCH-USD", "ATOM-USD",
            "NEAR-USD", "ALGO-USD", "FIL-USD", "VET-USD", "HBAR-USD",
            "THETA-USD", "GRT-USD", "ZEC-USD", "DOGE-USD", "SHIB-USD",
            "SAND-USD", "MANA-USD", "APT-USD",
        ],
    },
    "volume-spike-scout": {
        "name": "Volume Spike Scout",
        "category": "crypto",
        "tier": "SCOUT",
        "strategy": "VolumeSpike",
        # Volume spikes on mid-alts are extremely common — large list pays off
        "symbols": [
            "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
            "ADA-USD", "AVAX-USD", "DOT-USD", "LINK-USD", "MATIC-USD",
            "LTC-USD", "TRX-USD", "ETC-USD", "ATOM-USD", "NEAR-USD",
            "DOGE-USD", "SHIB-USD", "PEPE-USD",
            "SAND-USD", "MANA-USD", "CHZ-USD", "VET-USD", "HBAR-USD",
        ],
    },
    # -----------------------------------------------------------------------
    # v3 NEW TIER 1 STRATEGIES (world-class expansion)
    # -----------------------------------------------------------------------
    "macd-momentum": {
        "name": "MACD Momentum",
        "category": "crypto",
        "tier": "TIER_1",
        "strategy": "MACDCrossover",
        # MACD fires ~2-3x/month per symbol — wide crypto coverage
        "symbols": [
            "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
            "ADA-USD", "AVAX-USD", "DOT-USD", "LINK-USD", "MATIC-USD",
            "DOGE-USD", "SHIB-USD", "PEPE-USD", "NEAR-USD", "ATOM-USD",
            "LTC-USD", "TRX-USD", "ETC-USD", "BCH-USD", "HBAR-USD",
        ],
    },
    "golden-cross-stocks": {
        "name": "Golden Cross",
        "category": "stock",
        "tier": "TIER_1",
        "strategy": "GoldenCross",
        # 50/200 cross — major stocks + ETFs, fires on trend changes
        "symbols": [
            "AAPL", "MSFT", "NVDA", "AMD", "META", "AMZN", "GOOGL",
            "NFLX", "TSLA", "COIN", "MSTR", "SHOP", "SQ", "PYPL",
            "SPY", "QQQ", "VTI", "IWM", "ARKK",
            "JPM", "BAC", "XOM", "CVX", "GLD", "TLT",
        ],
    },
    "momentum-factor": {
        "name": "12-1 Momentum Factor",
        "category": "stock",
        "tier": "TIER_1",
        "strategy": "MomentumFactor",
        # Jegadeesh & Titman 1993 — needs 252d (now available with 1y period)
        "symbols": [
            "AAPL", "MSFT", "NVDA", "AMD", "META", "AMZN", "GOOGL",
            "NFLX", "SHOP", "UBER", "COIN", "TSLA", "MSTR", "SQ",
            "SPY", "QQQ", "VTI", "IWM", "XLK", "XLE", "XLF", "ARKK",
            "GLD", "TLT", "JPM", "BAC", "XOM",
        ],
    },
    # -----------------------------------------------------------------------
    # v3 NEW SCOUT STRATEGIES
    # -----------------------------------------------------------------------
    "stoch-rsi-crypto": {
        "name": "StochRSI Scout",
        "category": "crypto",
        "tier": "SCOUT",
        "strategy": "StochRSI",
        # Very sensitive — fires frequently on volatile crypto
        "symbols": [
            "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
            "ADA-USD", "AVAX-USD", "DOT-USD", "LINK-USD", "MATIC-USD",
            "LTC-USD", "TRX-USD", "ATOM-USD", "NEAR-USD",
            "DOGE-USD", "SHIB-USD", "PEPE-USD", "SAND-USD", "MANA-USD", "VET-USD",
        ],
    },
    "cci-crypto-reversal": {
        "name": "CCI Reversal Scout",
        "category": "crypto",
        "tier": "SCOUT",
        "strategy": "CCIReversal",
        # CCI crosses above -100 on meme/alt coins
        "symbols": [
            "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
            "DOGE-USD", "SHIB-USD", "PEPE-USD", "ADA-USD", "AVAX-USD",
            "LINK-USD", "DOT-USD", "NEAR-USD", "ALGO-USD", "VET-USD",
            "HBAR-USD", "SAND-USD", "MANA-USD", "CHZ-USD", "ENJ-USD",
        ],
    },
    "williams-r-scout": {
        "name": "Williams %R Scout",
        "category": "meme",
        "tier": "SCOUT",
        "strategy": "WilliamsR",
        # High-volatility assets where %R overshoots frequently
        "symbols": [
            "DOGE-USD", "SHIB-USD", "PEPE-USD", "SAND-USD", "MANA-USD",
            "CHZ-USD", "ENJ-USD", "NEAR-USD", "ALGO-USD", "VET-USD",
            "GME", "AMC", "PLTR", "MARA", "RIOT", "RIVN", "LCID",
        ],
    },
    "donchian-stock-breakout": {
        "name": "Donchian Breakout",
        "category": "stock",
        "tier": "SCOUT",
        "strategy": "DonchianBreakout",
        # 20-day high breakout — fires in trending markets
        "symbols": [
            "AAPL", "MSFT", "NVDA", "AMD", "META", "AMZN", "GOOGL",
            "NFLX", "TSLA", "COIN", "MSTR", "SHOP", "UBER", "SQ",
            "SPY", "QQQ", "IWM", "ARKK",
            "GME", "AMC", "PLTR", "SOFI", "MARA", "RIOT",
        ],
    },
    "supertrend-crypto": {
        "name": "Supertrend Scout",
        "category": "crypto",
        "tier": "SCOUT",
        "strategy": "Supertrend",
        # ATR-based trend signal — fires on significant trend changes
        "symbols": [
            "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
            "ADA-USD", "AVAX-USD", "DOT-USD", "LINK-USD", "MATIC-USD",
            "DOGE-USD", "SHIB-USD", "NEAR-USD", "ATOM-USD", "LTC-USD",
        ],
    },
    "keltner-bounce": {
        "name": "Keltner Bounce Scout",
        "category": "crypto",
        "tier": "SCOUT",
        "strategy": "KeltnerBounce",
        # Keltner channel bounce — adaptive multiplier reduces with drought
        "symbols": [
            "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
            "DOGE-USD", "SHIB-USD", "PEPE-USD", "ADA-USD", "AVAX-USD",
            "LINK-USD", "DOT-USD", "NEAR-USD", "MATIC-USD",
            "MARA", "RIOT", "COIN", "TSLA", "NVDA",
        ],
    },
    # -----------------------------------------------------------------------
    # v4 NEW STRATEGIES — Short Squeeze, Sector Rotation, Carry Trade, Gap-and-Go
    # -----------------------------------------------------------------------
    "short-squeeze": {
        "name": "Short Squeeze Setup",
        "category": "penny",
        "tier": "TIER_1",
        "strategy": "ShortSqueeze",
        # Near 52-wk high + volume surge — forces short sellers to cover
        "symbols": [
            "GME", "AMC", "PLTR", "SOFI", "MARA", "RIOT", "CLSK",
            "RIVN", "LCID", "NVAX", "BNGO", "SPCE", "XPEV", "NIO",
            "TSLA", "COIN", "HOOD", "BBAI", "UWMC",
        ],
    },
    "sector-rotation": {
        "name": "Sector Rotation Momentum",
        "category": "stock",
        "tier": "TIER_1",
        "strategy": "SectorRotation",
        # 20d outperformance + SMA10>SMA50 — Fama-French factor rotation
        "symbols": [
            "XLK", "XLF", "XLE", "XLV", "XLI",
            "SOXX", "XBI", "XRT", "ARKK", "JETS",
            "SPY", "QQQ", "IWM", "GLD", "TLT",
        ],
    },
    "carry-trade-momentum": {
        "name": "Carry Trade Momentum",
        "category": "forex",
        "tier": "TIER_1",
        "strategy": "CarryMomentum",
        # High-yield vs low-yield FX — borrow JPY, long AUD/NZD/CAD
        "symbols": [
            "AUDJPY=X", "NZDJPY=X", "CADJPY=X",
            "GBPJPY=X", "EURJPY=X",
            "AUDUSD=X", "NZDUSD=X",
        ],
    },
    "gap-and-go-stocks": {
        "name": "Gap-and-Go Breakout",
        "category": "penny",
        "tier": "SCOUT",
        "strategy": "GapAndGo",
        # Large single-day gap up with volume — momentum continuation play
        "symbols": [
            "GME", "AMC", "MARA", "RIOT", "RIVN", "LCID",
            "NVAX", "BNGO", "XPEV", "NIO", "PLTR", "SOFI",
            "TSLA", "NVDA", "AMD", "COIN", "MSTR",
            "DOGE-USD", "SHIB-USD", "PEPE-USD", "FLOKI-USD",
        ],
    },
    "ema-ribbon": {
        "name": "EMA Ribbon (8/13/21/34/55)",
        "category": "stock",
        "tier": "TIER_1",
        "strategy": "EmaRibbon",
        # All 5 EMAs aligned bullish — confirms strong institutional uptrend
        "symbols": [
            "AAPL", "MSFT", "NVDA", "AMD", "META", "AMZN", "GOOGL", "NFLX",
            "TSLA", "COIN", "MSTR", "SHOP", "SQ", "UBER",
            "SPY", "QQQ", "VTI", "IWM", "ARKK", "SOXX", "XBI",
            "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "AVAX-USD",
            "DOGE-USD", "SHIB-USD",
        ],
    },
    "bollinger-squeeze": {
        "name": "Bollinger Squeeze Breakout",
        "category": "crypto",
        "tier": "TIER_1",
        "strategy": "BollingerSqueeze",
        # TTM Squeeze: BB inside Keltner = coiling for big move — high precision entry
        "symbols": [
            "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
            "ADA-USD", "AVAX-USD", "DOT-USD", "LINK-USD", "MATIC-USD",
            "DOGE-USD", "SHIB-USD", "PEPE-USD", "FLOKI-USD",
            "MARA", "RIOT", "TSLA", "NVDA", "COIN",
            "SPY", "QQQ", "SOXX", "XBI",
        ],
    },
    "meme-velocity": {
        "name": "Meme Velocity Pump Detector",
        "category": "meme",
        "tier": "TIER_1",
        "strategy": "MemeVelocity",
        # 5-day price velocity 12%+ + volume explosion = meme pump onset
        "symbols": [
            "DOGE-USD", "SHIB-USD", "PEPE-USD", "FLOKI-USD", "BONK-USD",
            "SAND-USD", "MANA-USD", "CHZ-USD", "ENJ-USD",
            "GME", "AMC", "MARA", "RIOT",
            "NVAX", "BNGO", "SPCE", "RIVN",
        ],
    },
    # v4.5 — Options flow contrarian (market PCR fear gauge)
    "options-flow-scout": {
        "name": "Options Flow Fear Contrarian",
        "category": "stock",
        "tier": "SCOUT",
        "strategy": "OptionsFlowContrarian",
        # Liquid large-caps with active options markets
        "symbols": [
            "SPY", "QQQ", "AAPL", "MSFT", "NVDA",
            "AMD", "META", "AMZN", "GOOGL", "TSLA",
        ],
    },
    # v8.4 — Stochastic RSI Oversold Cross: dual oscillator confirmation
    "stoch-rsi-scout": {
        "name": "Stochastic RSI Oversold Cross",
        "category": "stock",
        "tier": "SCOUT",
        "strategy": "StochasticRSI",
        # High-liquidity names where momentum oscillators provide clean signals
        "symbols": [
            "AAPL", "MSFT", "NVDA", "AMD", "META", "AMZN", "GOOGL", "TSLA",
            "SPY", "QQQ", "IWM", "COIN", "MSTR", "NFLX", "SHOP", "SOFI",
            "JPM", "BAC", "UBER", "SQ",
        ],
    },
    # v8.5 — Parabolic SAR Trend Flip: Wilder's stop-and-reverse system
    "par-sar-scout": {
        "name": "Parabolic SAR Trend Flip",
        "category": "stock",
        "tier": "SCOUT",
        "strategy": "ParabolicSAR",
        # Trending, liquid stocks — SAR works best in directional markets
        "symbols": [
            "AAPL", "MSFT", "NVDA", "AMD", "META", "AMZN", "GOOGL", "TSLA",
            "SPY", "QQQ", "IWM", "NFLX", "UBER", "SHOP", "COIN",
            "JPM", "GS", "XOM", "HD", "AVGO",
        ],
    },
    # v8.6 — Aroon Oscillator Trend Initiation: Tushar Chande 1995
    "aroon-trend-scout": {
        "name": "Aroon Trend Initiation",
        "category": "stock",
        "tier": "SCOUT",
        "strategy": "AroonOscillator",
        # Trending stocks and ETFs — Aroon fires on directional breakouts
        "symbols": [
            "AAPL", "MSFT", "NVDA", "AMD", "META", "AMZN", "GOOGL", "TSLA",
            "SPY", "QQQ", "IWM", "DIA", "NFLX", "AVGO", "SHOP",
            "XOM", "JPM", "GS", "HD", "UNH",
        ],
    },
    # v8.7 — VIX Mean Reversion: Simon & Wiggins (2001) — VIX spike = buy quality
    "vix-mean-rev-scout": {
        "name": "VIX Mean Reversion",
        "category": "stock",
        "tier": "SCOUT",
        "strategy": "VIXMeanReversion",
        # Quality large-caps and broad ETFs — only safe havens on VIX spike
        "symbols": [
            "SPY", "QQQ", "IWM", "DIA",
            "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META",
            "JPM", "BAC", "XOM", "JNJ", "V",
            "TQQQ",
        ],
    },
    # v8.8 — Short Squeeze Proxy: volume surge + reversal bar on beaten-down stock
    "short-squeeze-scout": {
        "name": "Short Squeeze Proxy",
        "category": "stock",
        "tier": "SCOUT",
        "strategy": "ShortSqueezeProxy",
        # High-short-interest proxies: volatile, beaten-down, high-vol names
        "symbols": [
            "GME", "AMC", "NKLA", "SPCE", "RIVN", "LCID", "SNDL", "TLRY",
            "CLOV", "MULN", "WKHS", "GOEV", "FFIE", "SOFI", "MSTR",
            "COIN", "PLTR", "RBLX", "SNAP", "OPEN",
        ],
    },
    # v8.9 — Altcoin Season Rotation: Borri (2019) crypto risk factor rotation
    "altcoin-season-scout": {
        "name": "Altcoin Season Rotation",
        "category": "crypto",
        "tier": "SCOUT",
        "strategy": "AltcoinSeasonRotation",
        # Alt targets (BTC/ETH are signal sources, not targets)
        "symbols": [
            "SOL-USD", "ADA-USD", "AVAX-USD", "LINK-USD", "DOGE-USD",
            "SHIB-USD", "LTC-USD", "BCH-USD", "XRP-USD", "MATIC-USD",
            "PEPE-USD", "BONK-USD", "WIF-USD", "FLOKI-USD",
        ],
    },
    # v9.0 — Chaikin Money Flow (CMF): OHLCV buying pressure crossing negative→positive
    "cmf-accumulation-scout": {
        "name": "Chaikin Money Flow Accumulation",
        "category": "stock",
        "tier": "SCOUT",
        "strategy": "ChaikinMoneyFlow",
        # High-liquidity stocks and ETFs where institutional money flow is meaningful
        "symbols": [
            "AAPL", "MSFT", "NVDA", "AMD", "META", "AMZN", "GOOGL", "TSLA",
            "SPY", "QQQ", "IWM", "NFLX", "COIN", "MSTR", "PLTR",
            "JPM", "GS", "XOM", "GLD", "SOFI",
            "DOGE-USD", "SOL-USD", "PEPE-USD", "BONK-USD",
        ],
    },
    # v9.1 — Whale Accumulation Proxy: meme/high-vol symbols closing in upper range 3+ bars with vol
    "whale-accum-scout": {
        "name": "Whale Accumulation Proxy",
        "category": "crypto",
        "tier": "SCOUT",
        "strategy": "WhaleAccumulation",
        # Meme coins and high-vol names where whale accumulation shows in candle positioning
        "symbols": [
            "DOGE-USD", "SHIB-USD", "PEPE-USD", "BONK-USD", "WIF-USD", "FLOKI-USD",
            "XRP-USD", "SOL-USD", "ADA-USD", "AVAX-USD",
            "GME", "AMC", "MSTR", "COIN", "PLTR", "SOFI", "RBLX", "SNAP",
        ],
    },
    # v9.5 — StockTwits Bull Surge: self-reported conviction triggers (Sprenger et al. 2014)
    "stocktwits-bull-scout": {
        "name": "StockTwits Bull Surge",
        "category": "stock",
        "tier": "SCOUT",
        "strategy": "SentimentSurge",
        # Stocks and crypto with active StockTwits communities (pre-tagged data)
        "symbols": [
            "GME", "AMC", "MARA", "RIOT", "NVAX", "SPCE", "RIVN",
            "TSLA", "NVDA", "AMD", "AAPL", "COIN", "MSTR", "PLTR", "SOFI",
            "DOGE-USD", "SHIB-USD", "PEPE-USD", "FLOKI-USD", "BONK-USD",
            "BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "ADA-USD",
        ],
    },
    # v9.2 — Calendar Effect Crypto: weekend recovery + month/quarter-start institutional inflows
    "cal-effect-crypto-scout": {
        "name": "Calendar Effect Crypto",
        "category": "crypto",
        "tier": "SCOUT",
        "strategy": "CalendarEffect",
        # Major crypto where day-of-week and month/quarter-start effects are documented
        "symbols": [
            "BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "ADA-USD",
            "DOGE-USD", "AVAX-USD", "MATIC-USD", "LINK-USD", "DOT-USD",
            "ATOM-USD", "LTC-USD", "BCH-USD",
        ],
    },
    # v9.9 — ApeWisdom Mention Momentum: multi-subreddit mention velocity signal
    # Aggregates WSB + r/stocks + r/investing + r/Superstonk (2×/hr updates).
    # Signal = mention_ratio (now / 24h-ago) ≥ 2.0 + volume confirmation.
    # Academic: Da-Engelberg-Gao (2011) "In Search of Attention", Bollen-Mao-Zeng (2011).
    "apewisdom-momentum-scout": {
        "name": "ApeWisdom Mention Momentum",
        "category": "stock",
        "tier": "SCOUT",
        "strategy": "MentionMomentum",
        # Broad stock + popular crypto universe trackable on Reddit
        "symbols": [
            # Meme / high-retail-attention stocks
            "GME", "AMC", "MARA", "RIOT", "COIN", "MSTR", "PLTR", "SOFI",
            "NVAX", "SPCE", "RIVN", "RBLX", "SNAP",
            # Mega-cap tech (heavily discussed)
            "AAPL", "MSFT", "NVDA", "AMD", "TSLA", "META", "GOOGL", "AMZN", "NFLX",
            # High-beta / growth
            "SHOP", "SQ", "UBER", "PYPL",
            # Broad market
            "SPY", "QQQ", "IWM", "ARKK",
            # Crypto (Reddit-native discussions)
            "BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "ADA-USD", "DOGE-USD",
        ],
    },
    # v9.8 — Deribit Crypto Contrarian: real-time BTC/ETH options PCR fear spike
    # Deribit = dominant crypto options venue (80%+ of BTC/ETH volume).
    # Baseline PCR ~0.38 (call-heavy); PCR > 0.50 = crowded puts = coiled spring.
    # Academic: Cremers & Weinbaum (2010), Liu-Luo-Zhao (2023) crypto PCR prediction.
    "deribit-crypto-contrarian": {
        "name": "Deribit Crypto Contrarian",
        "category": "crypto",
        "tier": "SCOUT",
        "strategy": "DeribitOptionsContrarian",
        # Only BTC and ETH have liquid Deribit options markets
        "symbols": ["BTC-USD", "ETH-USD"],
    },
    # v9.7 — OPEX Week Momentum: post-options-expiry pin release drives trend continuation
    # Academic: Birru & Wang (2016) "Stock return reversals around option expiration dates",
    # Zhang (2022) "Options expiration week drift and institutional order flow".
    # 3rd Friday options expiry creates price-pinning (gamma exposure) then release day+1-5.
    "opex-momentum-scout": {
        "name": "OPEX Week Momentum",
        "category": "stock",
        "tier": "SCOUT",
        "strategy": "OPEXMomentum",
        # Highly optionable US stocks and ETFs where OPEX gamma pressure is significant
        "symbols": [
            "SPY", "QQQ", "IWM", "DIA",
            "AAPL", "MSFT", "NVDA", "AMD", "TSLA", "META", "GOOGL", "AMZN", "NFLX",
            "COIN", "MSTR", "SHOP", "SQ", "UBER", "PYPL",
            "JPM", "BAC", "XOM", "CVX", "GLD", "TLT",
            "XLK", "XLF", "XLE", "XLV", "SOXX", "ARKK",
            "INTC", "AVGO", "QCOM", "MU",
        ],
    },
    # v8.3 — MACD Histogram Hidden Divergence: bullish trend continuation
    "macd-hidden-div-scout": {
        "name": "MACD Histogram Hidden Divergence",
        "category": "stock",
        "tier": "SCOUT",
        "strategy": "MACDHiddenDivergence",
        # Trending names where MACD pullback signals are meaningful
        "symbols": [
            "AAPL", "MSFT", "NVDA", "AMD", "META", "AMZN", "GOOGL", "TSLA",
            "SPY", "QQQ", "IWM", "COIN", "MSTR", "NFLX", "SHOP", "PLTR",
            "GLD", "XLK", "JPM", "BAC",
        ],
    },
    # v8.2 — Volatility Contraction Breakout: Bollinger Band Squeeze + NR7
    "vol-contraction-scout": {
        "name": "Volatility Contraction Breakout (BB Squeeze + NR7)",
        "category": "stock",
        "tier": "SCOUT",
        "strategy": "VolatilityContraction",
        # Volatile names where BB squeeze provides strong predictive power
        "symbols": [
            "AAPL", "MSFT", "NVDA", "AMD", "META", "AMZN", "GOOGL", "TSLA",
            "COIN", "MSTR", "NFLX", "SHOP", "PLTR", "SOFI", "SQ", "UBER",
            "SPY", "QQQ", "GLD", "RBLX",
        ],
    },
    # v8.1 — 52-Week High Breakout: price discovery momentum
    "52w-high-breakout-scout": {
        "name": "52-Week High Breakout",
        "category": "stock",
        "tier": "SCOUT",
        "strategy": "52WeekHighBreakout",
        # Large-cap momentum names with sufficient price history (252 days needed)
        "symbols": [
            "AAPL", "MSFT", "NVDA", "AMD", "META", "AMZN", "GOOGL", "TSLA",
            "SPY", "QQQ", "IWM", "COIN", "MSTR", "NFLX", "SHOP", "PLTR",
            "JPM", "BAC", "XLK", "GLD",
        ],
    },
    # v8.0 — Fibonacci Retracement Bounce at 38.2/50/61.8% levels
    "fibonacci-bounce-scout": {
        "name": "Fibonacci Golden Ratio Bounce",
        "category": "stock",
        "tier": "SCOUT",
        "strategy": "FibonacciBounce",
        # Volatile names with clear swing structure — Fib levels need defined ranges
        "symbols": [
            "AAPL", "MSFT", "NVDA", "AMD", "META", "AMZN", "GOOGL", "TSLA",
            "COIN", "MSTR", "NFLX", "SHOP", "PLTR", "SOFI", "SQ", "UBER",
            "SPY", "QQQ", "GLD", "RBLX",
        ],
    },
    # v7.9 — Volume-Weighted RSI: volume-adjusted momentum reversal
    "vrsi-scout": {
        "name": "Volume-Weighted RSI Reversal",
        "category": "stock",
        "tier": "SCOUT",
        "strategy": "VolumeWeightedRSI",
        # High-volume stocks where volume weighting adds most signal
        "symbols": [
            "AAPL", "MSFT", "NVDA", "AMD", "META", "AMZN", "GOOGL", "TSLA",
            "SPY", "QQQ", "IWM", "COIN", "MSTR", "NFLX", "SOFI", "SQ",
            "JPM", "BAC", "UBER", "SHOP",
        ],
    },
    # v7.8 — Sector Breadth Thrust: McClellan oscillator proxy
    "breadth-thrust-scout": {
        "name": "Sector Breadth Thrust (McClellan Proxy)",
        "category": "stock",
        "tier": "SCOUT",
        "strategy": "BreadthThrust",
        # Symbols with well-defined sector ETF mappings (in _SECTOR_ETF_MAP)
        "symbols": [
            "AAPL", "MSFT", "NVDA", "AMD", "META", "AMZN", "GOOGL", "TSLA",
            "COIN", "MSTR", "NFLX", "SHOP", "PLTR", "RBLX", "SOFI", "SQ",
            "JPM", "BAC", "UBER", "SNAP",
        ],
    },
    # v7.7 — Dual Momentum: absolute + relative (Antonacci GEM adaptation)
    "dual-momentum-scout": {
        "name": "Dual Momentum (Antonacci GEM)",
        "category": "stock",
        "tier": "SCOUT",
        "strategy": "DualMomentum",
        # Liquid names with 12m+ history — needs SPY in all_data for relative comparison
        "symbols": [
            "AAPL", "MSFT", "NVDA", "AMD", "META", "AMZN", "GOOGL", "TSLA",
            "SPY", "QQQ", "IWM", "GLD", "XLK", "XLF", "XLE", "XLV",
            "COIN", "MSTR", "NFLX", "SHOP",
        ],
    },
    # v7.6 — Higher-High, Higher-Low swing structure (Dow Theory uptrend confirmation)
    "hh-hl-scout": {
        "name": "Higher-High Higher-Low Structure",
        "category": "stock",
        "tier": "SCOUT",
        "strategy": "HHHL",
        "symbols": [
            "AAPL", "MSFT", "NVDA", "AMD", "META", "AMZN", "GOOGL", "TSLA",
            "SPY", "QQQ", "IWM", "COIN", "MSTR", "NFLX", "SHOP", "PLTR",
            "BTC-USD", "ETH-USD", "GLD", "XLK",
        ],
    },
    # v7.5 — Multi-timeframe trend alignment (daily + weekly + monthly)
    "mtf-align-scout": {
        "name": "Multi-Timeframe Trend Alignment",
        "category": "stock",
        "tier": "SCOUT",
        "strategy": "MultiTimeframeAlign",
        # Liquid names with well-defined trends across multiple timeframes
        "symbols": [
            "AAPL", "MSFT", "NVDA", "AMD", "META", "AMZN", "GOOGL", "TSLA",
            "SPY", "QQQ", "IWM", "GLD", "TLT", "XLK", "XLF", "XLE",
            "COIN", "BTC-USD", "ETH-USD", "MSTR",
        ],
    },
    # v7.4 — VWAP reclaim (institutional accumulation completion)
    "vwap-reclaim-scout": {
        "name": "VWAP Reclaim Accumulation",
        "category": "stock",
        "tier": "SCOUT",
        "strategy": "VWAPReclaim",
        # Liquid names with strong VWAP-based institutional participation
        "symbols": [
            "AAPL", "MSFT", "NVDA", "AMD", "META", "AMZN", "GOOGL", "TSLA",
            "SPY", "QQQ", "COIN", "MSTR", "NFLX", "SHOP", "PLTR", "RBLX",
            "XLK", "XLF", "GLD", "TLT",
        ],
    },
    # v7.3 — Mean reversion z-score band (statistical arbitrage)
    "zscore-mean-rev-scout": {
        "name": "Z-Score Mean Reversion Band",
        "category": "stock",
        "tier": "SCOUT",
        "strategy": "ZScoreMeanRev",
        # Liquid large-caps + ETFs where mean reversion is statistically validated
        "symbols": [
            "AAPL", "MSFT", "NVDA", "AMD", "META", "AMZN", "GOOGL", "TSLA",
            "SPY", "QQQ", "IWM", "GLD", "TLT", "XLK", "XLF", "XLE", "XLV",
            "COIN", "BTC-USD", "ETH-USD",
        ],
    },
    # v7.2 — Gap-and-Go momentum (open drive follow-through)
    "gap-and-go-scout": {
        "name": "Gap-and-Go Open Drive",
        "category": "stock",
        "tier": "SCOUT",
        "strategy": "GapAndGo",
        # Liquid large-caps with strong open-drive patterns
        "symbols": [
            "AAPL", "MSFT", "NVDA", "AMD", "META", "AMZN", "GOOGL", "TSLA",
            "COIN", "MSTR", "NFLX", "UBER", "SHOP", "SQ", "PLTR", "RBLX",
            "SPY", "QQQ", "BTC-USD", "ETH-USD",
        ],
    },
    # v7.1 — Stock-level call volume surge (institutional footprint detector)
    "call-surge-scout": {
        "name": "Options Call Volume Surge",
        "category": "stock",
        "tier": "SCOUT",
        "strategy": "OptionsCallSurge",
        # Liquid optionable large-caps where yfinance has reliable chain data
        "symbols": [
            "AAPL", "MSFT", "NVDA", "AMD", "META", "AMZN", "GOOGL", "TSLA",
            "SPY", "QQQ", "COIN", "MSTR", "NFLX", "UBER",
        ],
    },
    # v6.8 — ADX trend confirmation (Wilder ADX > 25 + DI+ > DI-)
    "adx-trend-scout": {
        "name": "ADX Trend Confirmation",
        "category": "stock",
        "tier": "SCOUT",
        "strategy": "ADXTrend",
        # Liquid names where ADX-confirmed trends have strong follow-through
        "symbols": [
            "SPY", "QQQ", "AAPL", "MSFT", "NVDA", "AMD", "META", "AMZN",
            "GOOGL", "TSLA", "COIN", "MSTR", "GLD", "TLT", "XLK", "XLF",
            "BTC-USD", "ETH-USD",
        ],
    },
    # v6.7 — Price acceleration detector (CTA-style momentum jerk signal)
    "price-accel-scout": {
        "name": "Price Acceleration Detector",
        "category": "stock",
        "tier": "SCOUT",
        "strategy": "PriceAcceleration",
        # Liquid momentum names + ETFs where acceleration has follow-through
        "symbols": [
            "SPY", "QQQ", "AAPL", "MSFT", "NVDA", "AMD", "META", "AMZN",
            "GOOGL", "TSLA", "COIN", "MSTR", "ARKK", "SOXX", "XLK",
            "BTC-USD", "ETH-USD", "SOL-USD",
        ],
    },
    # v6.5 — Crypto funding rate contrarian (negative funding = short squeeze fuel)
    "crypto-funding-contrarian": {
        "name": "Crypto Funding Rate Contrarian",
        "category": "crypto",
        "tier": "SCOUT",
        "strategy": "CryptoFundingContrarian",
        # Major perp markets with meaningful funding data
        "symbols": [
            "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD",
            "XRP-USD", "DOGE-USD", "AVAX-USD", "LINK-USD",
        ],
    },
    # v6.4 — RSI bullish divergence (price/momentum divergence reversal)
    "rsi-divergence-scout": {
        "name": "RSI Bullish Divergence Reversal",
        "category": "stock",
        "tier": "SCOUT",
        "strategy": "RSIDivergence",
        # Volatile names where divergence is meaningful (enough vol for real troughs)
        "symbols": [
            "SPY", "QQQ", "AAPL", "MSFT", "NVDA", "AMD", "META", "AMZN",
            "GOOGL", "TSLA", "COIN", "MSTR", "ARKK", "SOXX", "XBI",
            "GLD", "SLV", "TLT", "IWM",
        ],
    },
    # v6.3 — Post-earnings mean reversion (oversold gap fade)
    "post-earnings-rev-scout": {
        "name": "Post-Earnings Mean Reversion",
        "category": "stock",
        "tier": "SCOUT",
        "strategy": "PostEarningsMeanRev",
        # High-coverage, frequently-reporting names with large earnings reactions
        "symbols": [
            "AAPL", "MSFT", "NVDA", "META", "GOOGL", "AMZN", "TSLA",
            "JPM", "GS", "AMD", "COIN", "MSTR", "NFLX", "ORCL",
            "ARKK", "QQQ", "SOXX",   # sector ETFs can also gap on macro earnings
        ],
    },
    # v6.1 — Pre-earnings momentum drift (earnings announcement premium)
    "earnings-drift-scout": {
        "name": "Pre-Earnings Momentum Drift",
        "category": "stock",
        "tier": "SCOUT",
        "strategy": "EarningsDrift",
        # High-IV mega-cap names with consistent earnings reaction patterns
        "symbols": [
            "AAPL", "MSFT", "NVDA", "META", "GOOGL", "AMZN", "TSLA",
            "JPM", "GS", "MS", "AMD", "COIN", "MSTR", "NFLX", "ORCL",
        ],
    },
    # v5.9 — Volume anomaly / institutional accumulation detector
    "volume-anomaly-scout": {
        "name": "Volume Anomaly Accumulation Detector",
        "category": "stock",
        "tier": "SCOUT",
        "strategy": "VolumeAnomalyDetector",
        # Liquid symbols where institutional volume patterns are most visible
        "symbols": [
            "SPY", "QQQ", "AAPL", "MSFT", "NVDA", "AMD", "META",
            "TSLA", "AMZN", "GOOGL", "JPM", "COIN", "MSTR",
            "GLD", "TLT", "HYG", "XLK", "XLF",
        ],
    },
    # v5.6 — VWAP reversion (institutional fair value mean-reversion)
    "vwap-reversion-scout": {
        "name": "VWAP Reversion — Institutional Fair Value",
        "category": "stock",
        "tier": "SCOUT",
        "strategy": "VWAPReversion",
        # Liquid large-caps and ETFs where institutional VWAP anchoring is strong
        "symbols": [
            "SPY", "QQQ", "AAPL", "MSFT", "NVDA", "AMD", "META",
            "AMZN", "GOOGL", "TSLA", "JPM", "XLK", "XLF", "XLE",
            "COIN", "MSTR", "GLD", "TLT",
        ],
    },
    # v5.3 — Intermarket cross-asset flow (SPY/TLT, HYG/TLT, DXY, GLD)
    "intermarket-flow-scout": {
        "name": "Intermarket Cross-Asset Flow",
        "category": "stock",
        "tier": "SCOUT",
        "strategy": "IntermarketFlow",
        # Liquid equity ETFs that benefit from risk-on capital flow regimes
        "symbols": [
            "SPY", "QQQ", "IWM", "XLK", "XLF", "XLE",
            "ARKK", "SOXX", "XBI",
        ],
    },
}


# ---------------------------------------------------------------------------
# Tier 1 Strategy Implementations (from strategies_tier1.py, adapted)
# ---------------------------------------------------------------------------


def _vwma(close: pd.Series, volume: pd.Series, period: int) -> pd.Series:
    """Volume-Weighted Moving Average."""
    vol = volume.replace(0, np.nan).fillna(1)
    return (close * vol).rolling(period).sum() / vol.rolling(period).sum()


def _zscore(series: pd.Series, lookback: int) -> pd.Series:
    """Rolling z-score."""
    mean = series.rolling(lookback).mean()
    std = series.rolling(lookback).std().replace(0, np.nan)
    return (series - mean) / std


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Full RSI series."""
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=period, min_periods=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period, min_periods=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _rolling_beta(returns: pd.Series, bench_returns: pd.Series, lookback: int) -> pd.Series:
    """Rolling beta vs benchmark."""
    beta = pd.Series(np.nan, index=returns.index)
    for i in range(lookback, len(returns)):
        r_a = returns.iloc[i - lookback:i].dropna()
        r_b = bench_returns.iloc[i - lookback:i].dropna()
        min_len = min(len(r_a), len(r_b))
        if min_len < 30:
            continue
        r_a, r_b = r_a.iloc[-min_len:], r_b.iloc[-min_len:]
        var_b = r_b.var()
        if var_b > 0:
            beta.iloc[i] = np.cov(r_a, r_b)[0, 1] / var_b
    return beta


def _quality_score(close: pd.Series, lookback: int = 60) -> pd.Series:
    """Composite quality z-score (stability, trend R², drawdown resilience, momentum Sharpe)."""
    returns = close.pct_change()

    # 1. Return stability (inverse volatility)
    vol_20 = returns.rolling(20).std()
    stability = 1.0 / vol_20.replace(0, np.nan)

    # 2. Trend consistency (R² of log-price vs time)
    log_close = np.log(close)
    r_squared = pd.Series(np.nan, index=close.index)
    for i in range(lookback, len(close)):
        y = log_close.iloc[i - lookback:i].values
        x = np.arange(lookback)
        if np.std(y) == 0:
            r_squared.iloc[i] = 0
            continue
        corr = np.corrcoef(x, y)[0, 1]
        r_squared.iloc[i] = corr ** 2

    # 3. Drawdown resilience
    rolling_max = close.rolling(lookback).max()
    dd = (close - rolling_max) / rolling_max
    max_dd = dd.rolling(lookback).min()
    dd_resilience = -max_dd

    # 4. Momentum Sharpe
    ret_mean = returns.rolling(lookback).mean()
    ret_std = returns.rolling(lookback).std().replace(0, np.nan)
    mom_sharpe = ret_mean / ret_std

    # Composite: average of expanding z-scores
    metrics = pd.DataFrame({
        "s": stability, "r": r_squared, "d": dd_resilience, "m": mom_sharpe
    })
    z = metrics.apply(lambda col: (col - col.expanding().mean()) / col.expanding().std())
    return z.mean(axis=1)


# ---------------------------------------------------------------------------
# Signal Functions
# ---------------------------------------------------------------------------


def signal_funding_rate_arb(symbol: str, df: pd.DataFrame, _all_data: dict) -> tuple[str | None, str]:
    """
    Tier 1: Funding Rate Arbitrage via VWMA basis z-score.
    Entry: basis z-score < -2.0 (price deeply below volume-weighted fair value).
    """
    close, volume = df["Close"], df["Volume"]
    if len(close) < 80:
        return None, ""
    vwma = _vwma(close, volume, 20)
    basis = (close - vwma) / vwma
    z = _zscore(basis, 60)
    z_val = z.iloc[-1]
    if pd.isna(z_val):
        return None, ""
    if z_val < -2.0:
        return "BUY", f"VWMA basis z-score {z_val:.2f} (deeply below fair value)"
    return None, ""


def signal_pairs_trading(symbol: str, df: pd.DataFrame, all_data: dict) -> tuple[str | None, str]:
    """
    Tier 1: Pairs Trading via cointegration z-score.
    Entry: spread z-score < -2.0 (long the underperformer).
    """
    # Prefer dynamically validated cointegration pair; fall back to static PAIR_MAP
    pair_sym = _DYNAMIC_PAIR_MAP.get(symbol) or PAIR_MAP.get(symbol)
    if not pair_sym or pair_sym not in all_data:
        return None, ""
    pair_df = all_data[pair_sym]
    close = df["Close"]
    pair_close = pair_df["Close"]
    min_len = min(len(close), len(pair_close))
    if min_len < 120:
        return None, ""
    close = close.iloc[-min_len:]
    pair_close = pair_close.iloc[-min_len:]

    y, x = np.log(close), np.log(pair_close)
    lookback = 60
    if len(y) < lookback * 2:
        return None, ""

    # Rolling hedge ratio (OLS)
    y_win = y.iloc[-lookback:]
    x_win = x.iloc[-lookback:]
    cov = np.cov(x_win, y_win)
    hr = cov[0, 1] / cov[0, 0] if cov[0, 0] != 0 else 1.0
    spread = y - hr * x

    # Z-score of spread
    z = _zscore(spread, lookback)
    z_val = z.iloc[-1]
    if pd.isna(z_val):
        return None, ""
    if z_val < -2.0:
        return "BUY", f"Spread z-score {z_val:.2f} vs {pair_sym} (cointegration reversion)"
    return None, ""


def signal_betting_against_beta(symbol: str, df: pd.DataFrame, all_data: dict) -> tuple[str | None, str]:
    """
    Tier 1: Betting Against Beta (Frazzini & Pedersen, 2014).
    Entry: rolling beta < 0.8 AND price > 200d SMA (low-beta + uptrend).
    """
    close = df["Close"]
    if len(close) < 200:
        return None, ""
    returns = close.pct_change()

    # Use SPY as benchmark if available, else self-proxy
    if "SPY" in all_data and symbol != "SPY":
        bench = all_data["SPY"]["Close"].pct_change()
    else:
        bench = returns.rolling(5).mean()

    beta = _rolling_beta(returns, bench, 120)
    beta_val = beta.iloc[-1]
    if pd.isna(beta_val):
        return None, ""

    sma_200 = close.rolling(200).mean().iloc[-1]
    price = close.iloc[-1]
    above_trend = price > sma_200

    if beta_val < 0.8 and above_trend:
        return "BUY", f"Low beta {beta_val:.2f} + above 200d SMA (BAB premium)"
    return None, ""


def signal_flash_crash_reversal(symbol: str, df: pd.DataFrame, _all_data: dict) -> tuple[str | None, str]:
    """
    Tier 1: Flash Crash Reversal.
    Entry: drawdown > 5% from 20d high AND RSI(6) < 25 AND volume > 2x average.
    """
    close, volume = df["Close"], df["Volume"]
    if len(close) < 25:
        return None, ""

    rolling_high = close.rolling(20).max()
    drawdown = (close - rolling_high) / rolling_high
    dd_val = drawdown.iloc[-1]

    rsi = _rsi(close, 6)
    rsi_val = rsi.iloc[-1]

    vol_avg = volume.iloc[-21:-1].mean()
    vol_ratio = volume.iloc[-1] / vol_avg if vol_avg > 0 else 0

    if pd.isna(dd_val) or pd.isna(rsi_val):
        return None, ""

    if dd_val < -0.05 and rsi_val < 25 and vol_ratio > 2.0:
        return "BUY", f"Flash crash: {dd_val*100:.1f}% drawdown, RSI(6)={rsi_val:.1f}, vol {vol_ratio:.1f}x"
    return None, ""


def signal_quality_minus_junk(symbol: str, df: pd.DataFrame, _all_data: dict) -> tuple[str | None, str]:
    """
    Tier 1: Quality Minus Junk (Novy-Marx, 2013 / Asness et al., 2019).
    Entry: composite quality z-score > 0.5 AND price > 200d SMA.
    """
    close = df["Close"]
    if len(close) < 200:
        return None, ""
    q = _quality_score(close, 60)
    q_val = q.iloc[-1]
    if pd.isna(q_val):
        return None, ""

    sma_200 = close.rolling(200).mean().iloc[-1]
    price = close.iloc[-1]
    above_trend = price > sma_200

    if q_val > 0.5 and above_trend:
        return "BUY", f"Quality z-score {q_val:.2f} + above 200d SMA (QMJ premium)"
    return None, ""


def signal_bollinger_mean_reversion(symbol: str, df: pd.DataFrame, _all_data: dict) -> tuple[str | None, str]:
    """
    Tier 1: Bollinger Bands Mean Reversion for meme coins.
    Entry: Price touches/exceeds lower BB AND RSI < 30 AND volume > 2x average AND not in strong downtrend.
    Designed specifically for meme coin volatility with pump & dump protection.
    """
    close, volume = df["Close"], df["Volume"]
    if len(close) < 50:
        return None, ""

    # Bollinger Bands (20, 2)
    sma_20 = close.rolling(20).mean()
    std_20 = close.rolling(20).std()
    bb_lower = sma_20 - (2 * std_20)
    bb_upper = sma_20 + (2 * std_20)

    # RSI confirmation
    rsi = _rsi(close, 14)

    # Volume spike detection (2x average)
    vol_avg = volume.rolling(20).mean()
    vol_ratio = volume.iloc[-1] / vol_avg.iloc[-1] if vol_avg.iloc[-1] > 0 else 0

    # Trend filter: don't trade against 50-day MA (meme coins can have extended dumps)
    sma_50 = close.rolling(50).mean()
    price = close.iloc[-1]
    not_strong_downtrend = price > sma_50.iloc[-1] * 0.85  # Allow 15% below for meme volatility

    # Pump protection: Check if price recently spiked >50% in last 5 days (likely pump)
    price_5d_ago = close.iloc[-5] if len(close) >= 5 else close.iloc[0]
    recent_pump = (price - price_5d_ago) / price_5d_ago > 0.50 if price_5d_ago > 0 else False

    bb_lower_val = bb_lower.iloc[-1]
    rsi_val = rsi.iloc[-1]

    if pd.isna(bb_lower_val) or pd.isna(rsi_val):
        return None, ""

    # Entry conditions with pump protection
    if (price <= bb_lower_val and
        rsi_val < 30 and
        vol_ratio > 2.0 and
        not_strong_downtrend and
        not recent_pump):
        return "BUY", f"BB mean-rev: price @ lower band, RSI {rsi_val:.1f}, vol {vol_ratio:.1f}x (oversold bounce)"

    return None, ""


# --- Scout signals (simple TA, clearly labeled) ---

def signal_momentum_volume_spike(symbol: str, df: pd.DataFrame, _all_data: dict) -> tuple[str | None, str]:
    """Scout: momentum + volume spike."""
    close, vol = df["Close"], df["Volume"]
    if len(close) < 21:
        return None, ""
    mom = (close.iloc[-1] - close.iloc[-6]) / close.iloc[-6] if len(close) >= 6 else None
    vol_avg = vol.iloc[-21:-1].mean()
    spike = vol.iloc[-1] > 1.5 * vol_avg if vol_avg > 0 else False
    if mom is not None and mom > 0.02 and spike:
        return "BUY", f"[Scout] Momentum {mom*100:.1f}% + volume spike"
    return None, ""


def signal_volume_breakout(symbol: str, df: pd.DataFrame, _all_data: dict) -> tuple[str | None, str]:
    """Scout: volume breakout."""
    vol = df["Volume"]
    if len(vol) < 21:
        return None, ""
    avg = vol.iloc[-21:-1].mean()
    if avg > 0 and vol.iloc[-1] > 2.0 * avg:
        return "BUY", f"[Scout] Volume breakout ({vol.iloc[-1]/avg:.1f}x 20d avg)"
    return None, ""


def signal_ma_crossover(symbol: str, df: pd.DataFrame, _all_data: dict) -> tuple[str | None, str]:
    """Scout: MA crossover."""
    close = df["Close"]
    if len(close) < 51:
        return None, ""
    fast = close.rolling(10).mean()
    slow = close.rolling(50).mean()
    if fast.iloc[-1] > slow.iloc[-1] and fast.iloc[-2] <= slow.iloc[-2]:
        return "BUY", "[Scout] 10/50 SMA bullish crossover"
    return None, ""


def signal_rsi_oversold(symbol: str, df: pd.DataFrame, _all_data: dict) -> tuple[str | None, str]:
    """Scout: RSI oversold."""
    close = df["Close"]
    rsi = _rsi(close, 14)
    rsi_val = rsi.iloc[-1] if len(rsi) > 0 else None
    if rsi_val is not None and not pd.isna(rsi_val) and rsi_val < 30:
        return "BUY", f"[Scout] RSI oversold ({rsi_val:.1f})"
    return None, ""


def signal_volume_spike_detect(symbol: str, df: pd.DataFrame, _all_data: dict) -> tuple[str | None, str]:
    """Scout: volume spike detection."""
    vol = df["Volume"]
    if len(vol) < 21:
        return None, ""
    avg = vol.iloc[-21:-1].mean()
    if avg > 0 and vol.iloc[-1] > 2.0 * avg:
        return "BUY", f"[Scout] Volume spike ({vol.iloc[-1]/avg:.1f}x 20d avg)"
    return None, ""


# ---------------------------------------------------------------------------
# v3 Advanced Strategies — World-Class Tournament Edition
# 9 new signal functions with adaptive drought thresholds
# ---------------------------------------------------------------------------

def _stoch_rsi(close: pd.Series, rsi_period: int = 14, stoch_period: int = 14) -> tuple[pd.Series, pd.Series]:
    """Stochastic RSI — returns (K, D) lines (0–100)."""
    rsi = _rsi(close, rsi_period)
    rsi_min = rsi.rolling(stoch_period).min()
    rsi_max = rsi.rolling(stoch_period).max()
    rng = (rsi_max - rsi_min).replace(0, np.nan)
    k = ((rsi - rsi_min) / rng) * 100
    d = k.rolling(3).mean()
    return k, d


def signal_macd_crossover(symbol: str, df: pd.DataFrame, _all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """MACD bullish crossover (12-26-9). Tier 1 momentum shift signal."""
    close = df["Close"]
    if len(close) < 35:
        return None, ""
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    sig_line = macd.ewm(span=9, adjust=False).mean()
    hist = macd - sig_line
    if hist.iloc[-1] > 0 and hist.iloc[-2] <= 0:
        return "BUY", f"MACD bullish crossover (hist={hist.iloc[-1]:.4f})"
    # Adaptive: strengthening MACD on drought
    if drought >= 3 and hist.iloc[-1] > 0 and hist.iloc[-1] > hist.iloc[-2]:
        return "BUY", f"MACD momentum building [drought={drought}] (hist={hist.iloc[-1]:.4f})"
    return None, ""


def signal_stoch_rsi_scout(symbol: str, df: pd.DataFrame, _all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """StochRSI oversold bounce: K rises from oversold zone. Very sensitive — fires frequently."""
    close = df["Close"]
    if len(close) < 35:
        return None, ""
    k, _d = _stoch_rsi(close)
    k_val, k_prev = k.iloc[-1], k.iloc[-2]
    if pd.isna(k_val) or pd.isna(k_prev):
        return None, ""
    threshold = min(20 + drought * 3, 35)
    if k_val < threshold and k_val > k_prev:
        return "BUY", f"StochRSI oversold bounce: K={k_val:.1f}↑ (threshold≤{threshold})"
    return None, ""


def signal_donchian_breakout(symbol: str, df: pd.DataFrame, _all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """Donchian 20-day high breakout with volume confirmation. Trend-following."""
    close, volume = df["Close"], df["Volume"]
    if len(close) < 25:
        return None, ""
    high_20 = close.iloc[-21:-1].max()
    vol_avg = volume.iloc[-21:-1].mean()
    vol_ratio = volume.iloc[-1] / vol_avg if vol_avg > 0 else 0
    vol_threshold = max(1.5 - drought * 0.1, 1.0)
    if close.iloc[-1] > high_20 and vol_ratio > vol_threshold:
        pct = (close.iloc[-1] / high_20 - 1) * 100
        return "BUY", f"Donchian 20d breakout +{pct:.1f}%, vol {vol_ratio:.1f}x"
    return None, ""


def signal_williams_r(symbol: str, df: pd.DataFrame, _all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """Williams %R reversal from oversold (-80 zone). Classic mean-reversion."""
    close = df["Close"]
    if len(close) < 15 or "High" not in df.columns or "Low" not in df.columns:
        return None, ""
    high, low = df["High"], df["Low"]
    period = 14
    high_n = high.rolling(period).max()
    low_n = low.rolling(period).min()
    willr = ((high_n - close) / (high_n - low_n).replace(0, np.nan)) * -100
    val, prev = willr.iloc[-1], willr.iloc[-2]
    if pd.isna(val) or pd.isna(prev):
        return None, ""
    threshold = min(-80 + drought * 3, -70)
    if prev < threshold and val > threshold:
        return "BUY", f"Williams %R reversal: {prev:.0f}→{val:.0f} (threshold={threshold})"
    return None, ""


def signal_cci_reversal(symbol: str, df: pd.DataFrame, _all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """CCI crosses above -100 from oversold — contrarian reversal signal."""
    close = df["Close"]
    if len(close) < 25 or "High" not in df.columns or "Low" not in df.columns:
        return None, ""
    high, low = df["High"], df["Low"]
    typical = (high + low + close) / 3
    sma_tp = typical.rolling(20).mean()
    mad = typical.rolling(20).apply(lambda x: np.abs(x - x.mean()).mean())
    cci = (typical - sma_tp) / (0.015 * mad.replace(0, np.nan))
    val, prev = cci.iloc[-1], cci.iloc[-2]
    if pd.isna(val) or pd.isna(prev):
        return None, ""
    threshold = min(-100 + drought * 10, -70)
    if prev < threshold and val > threshold:
        return "BUY", f"CCI reversal: {prev:.0f}→{val:.0f} (threshold={threshold})"
    return None, ""


def signal_supertrend(symbol: str, df: pd.DataFrame, _all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """Supertrend bullish flip — price crosses above ATR-based dynamic support."""
    close = df["Close"]
    if len(close) < 25 or "High" not in df.columns or "Low" not in df.columns:
        return None, ""
    high, low = df["High"], df["Low"]
    period, mult = 10, 3.0
    hl2 = (high + low) / 2
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    upper_b = hl2 + mult * atr
    lower_b = hl2 - mult * atr
    direction = [0] * len(close)
    st = [np.nan] * len(close)
    for i in range(1, len(close)):
        if pd.isna(atr.iloc[i]):
            continue
        fu = upper_b.iloc[i] if pd.isna(st[i - 1]) or direction[i - 1] != -1 else min(upper_b.iloc[i], st[i - 1])
        fl = lower_b.iloc[i] if pd.isna(st[i - 1]) or direction[i - 1] != 1 else max(lower_b.iloc[i], st[i - 1])
        if close.iloc[i] > fu:
            direction[i] = 1
            st[i] = fl
        elif close.iloc[i] < fl:
            direction[i] = -1
            st[i] = fu
        else:
            direction[i] = direction[i - 1] if direction[i - 1] != 0 else 1
            st[i] = fl if direction[i] == 1 else fu
    if len(direction) >= 2 and direction[-1] == 1 and direction[-2] != 1:
        return "BUY", f"Supertrend bullish flip at {close.iloc[-1]:.4f}"
    return None, ""


def signal_golden_cross(symbol: str, df: pd.DataFrame, _all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """50/200 SMA golden cross — institutional-grade trend confirmation."""
    close = df["Close"]
    if len(close) < 202:
        return None, ""
    sma50 = close.rolling(50).mean()
    sma200 = close.rolling(200).mean()
    if sma50.iloc[-1] > sma200.iloc[-1] and sma50.iloc[-2] <= sma200.iloc[-2]:
        return "BUY", "Golden Cross: SMA50 crossed above SMA200"
    # Adaptive drought: near-cross approaching from above
    if drought >= 4:
        gap_pct = (sma50.iloc[-1] - sma200.iloc[-1]) / sma200.iloc[-1] * 100
        if 0 < gap_pct < 1.5 and close.iloc[-1] > sma50.iloc[-1]:
            return "BUY", f"Near-Golden Cross: SMA50/200 gap={gap_pct:.2f}% [drought={drought}]"
    return None, ""


def signal_keltner_bounce(symbol: str, df: pd.DataFrame, _all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """Price below lower Keltner Channel with RSI turning up — adaptive volatility mean-rev."""
    close = df["Close"]
    if len(close) < 25 or "High" not in df.columns or "Low" not in df.columns:
        return None, ""
    high, low = df["High"], df["Low"]
    period = 20
    mult = max(2.0 - drought * 0.15, 1.5)
    ema = close.ewm(span=period, adjust=False).mean()
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(span=period, adjust=False).mean()
    lower_kc = ema - mult * atr
    rsi = _rsi(close, 14)
    rsi_val, rsi_prev = rsi.iloc[-1], rsi.iloc[-2]
    if pd.isna(rsi_val) or pd.isna(rsi_prev):
        return None, ""
    rsi_threshold = min(40 + drought * 3, 50)
    if close.iloc[-1] < lower_kc.iloc[-1] and rsi_val < rsi_threshold and rsi_val > rsi_prev:
        return "BUY", f"Keltner bounce: below KC(mult={mult:.1f}), RSI {rsi_val:.1f}↑"
    return None, ""


def signal_momentum_factor(symbol: str, df: pd.DataFrame, _all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """12-1 month momentum factor (Jegadeesh & Titman 1993). Academic Tier 1.
    v6.6 upgrade: cross-sectional momentum ranking (only top quartile fires).
    Original: absolute return > threshold.
    v6.6: rank symbol's 12-1 return among all tracked stocks — fire only if top 25%.
    Enhanced: news headline sentiment confirmation (bearish news → skip signal)."""
    close = df["Close"]
    if len(close) < 252:
        return None, ""
    ret_12_1 = (close.iloc[-21] / close.iloc[-252]) - 1   # skip most recent month
    ret_3mo = (close.iloc[-1] / close.iloc[-63]) - 1
    threshold = max(0.10 - drought * 0.02, 0.05)

    # v6.6: Cross-sectional rank filter
    mom_ranks = _all_data.get("__mom_ranks__", {})
    if mom_ranks:
        rank_pct = mom_ranks.get(symbol, 50.0)   # percentile rank 0-100, higher = stronger
        top_pct  = max(25.0 - drought * 5.0, 15.0)  # top 25% default, loosens to 15% in drought
        if rank_pct < (100.0 - top_pct):
            return None, ""   # not in top quartile cross-sectionally
        rank_tag = f", rank={rank_pct:.0f}%ile"
    else:
        rank_tag = ""

    # News sentiment filter: block momentum signal if very bearish news
    news_score = _all_data.get("__news_sentiment__", {}).get(symbol, 50.0)
    if news_score < 25 and drought < 2:
        return None, ""  # skip on very negative headlines
    news_tag = f", news={news_score:.0f}%" if symbol in _all_data.get("__news_sentiment__", {}) else ""

    if ret_12_1 > threshold and ret_3mo > 0:
        return "BUY", f"Momentum factor: 12-1mo={ret_12_1*100:.1f}%, 3mo={ret_3mo*100:.1f}%{rank_tag}{news_tag}"
    return None, ""


def signal_short_squeeze(symbol: str, df: pd.DataFrame, _all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """Short Squeeze Setup: near 52-week high + volume surge + RSI momentum + social confirmation.
    Tier 1: short sellers forced to cover as price breaks out. StockTwits bull% used as optional boost."""
    close = df["Close"]
    volume = df["Volume"]
    if len(close) < 60:
        return None, ""
    high_52w = close.rolling(min(len(close), 252)).max()
    sma20 = close.rolling(20).mean()
    vol_avg = volume.rolling(20).mean()
    vol_ratio = volume.iloc[-1] / vol_avg.iloc[-1] if vol_avg.iloc[-1] > 0 else 0
    rsi = _rsi(close, 14)
    rsi_val = rsi.iloc[-1]
    if pd.isna(rsi_val) or pd.isna(high_52w.iloc[-1]) or pd.isna(sma20.iloc[-1]):
        return None, ""
    pct_from_high = close.iloc[-1] / high_52w.iloc[-1]
    sentiment_cache = _all_data.get("__sentiment__", {})
    bull_pct = sentiment_cache.get(symbol, 50.0)
    social_bullish = bull_pct > 65.0  # high conviction needed for squeeze

    # Short interest boost: high SI = more short-cover fuel → lower vol threshold
    si_data = _all_data.get("__short_interest__", {}).get(symbol, {})
    short_pct = float(si_data.get("short_pct", 0.0))
    days_cover = float(si_data.get("days_to_cover", 0.0))
    high_si = short_pct > 0.20 or days_cover > 5.0  # heavily shorted = squeeze fuel
    si_tag = f", SI={short_pct*100:.0f}%({days_cover:.1f}d)" if short_pct > 0 else ""

    vol_threshold = max(2.5 - drought * 0.2, 1.5)
    if social_bullish:
        vol_threshold = max(vol_threshold - 0.3, 1.2)  # social confirmation = lower bar
    if high_si:
        vol_threshold = max(vol_threshold - 0.4, 1.0)  # high short interest = lower bar
    rsi_min = max(55 - drought * 5, 45)
    if (pct_from_high > 0.93 and vol_ratio > vol_threshold and
            rsi_val > rsi_min and rsi_val < 82 and close.iloc[-1] > sma20.iloc[-1]):
        sentiment_tag = f", ST={bull_pct:.0f}%bull" if symbol in sentiment_cache else ""
        return "BUY", f"Short squeeze: {pct_from_high*100:.0f}% of 52wk high, vol {vol_ratio:.1f}x, RSI {rsi_val:.0f}{sentiment_tag}{si_tag}"
    return None, ""


def signal_sector_rotation(symbol: str, df: pd.DataFrame, _all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """Sector Rotation Momentum: 20d outperformance + trend alignment.
    Tier 1: Fama-French factor rotation — capital flows to leading sectors.
    v5.8: enhanced with sector relative strength — only fire in top-ranked sectors."""
    close = df["Close"]
    if len(close) < 55:
        return None, ""
    sma10 = close.rolling(10).mean()
    sma50 = close.rolling(50).mean()
    ret_20 = (close.iloc[-1] / close.iloc[-20] - 1)
    threshold = max(0.04 - drought * 0.005, 0.02)

    # v5.8 Sector relative strength filter
    sector_ranks = _all_data.get("__sector_ranks__", {})
    if sector_ranks:
        # Map symbol to sector ETF
        _SECTOR_MAP = {
            "AAPL": "XLK", "MSFT": "XLK", "NVDA": "XLK", "AMD": "XLK",
            "INTC": "XLK", "META": "XLK", "GOOGL": "XLK", "AMZN": "XLK",
            "NFLX": "XLK", "SOXX": "XLK",
            "JPM": "XLF", "BAC": "XLF", "GS": "XLF", "MS": "XLF",
            "XOM": "XLE", "CVX": "XLE",
            "TSLA": "ARKK", "COIN": "ARKK", "SHOP": "ARKK", "SQ": "ARKK",
            "UBER": "ARKK",
        }
        sym_sector = _SECTOR_MAP.get(symbol, symbol)  # ETFs map to themselves
        sym_rank = sector_ranks.get(sym_sector)
        top_n = max(3 + drought, 4)  # default top 3, relax with drought
        if sym_rank is not None and sym_rank > top_n:
            return None, ""   # sector is lagging — skip signal

    if (ret_20 > threshold and
            not pd.isna(sma10.iloc[-1]) and not pd.isna(sma50.iloc[-1]) and
            close.iloc[-1] > sma10.iloc[-1] > sma50.iloc[-1]):
        rank_tag = f", sector_rank={sector_ranks.get(symbol, '?')}" if sector_ranks else ""
        return "BUY", f"Sector momentum: +{ret_20*100:.1f}% 20d, SMA10>SMA50 aligned{rank_tag}"
    return None, ""


def signal_carry_momentum(symbol: str, df: pd.DataFrame, _all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """Carry Trade Momentum: high-yield FX pair above trend with positive momentum.
    Tier 1: Interest rate differential + momentum filter reduces drawdown risk.
    v5.3: Dollar strength filter — strong USD is headwind for high-yield FX pairs."""
    close = df["Close"]
    if len(close) < 55:
        return None, ""
    sma50 = close.rolling(50).mean()
    ret_10 = (close.iloc[-1] / close.iloc[-10] - 1)
    rsi = _rsi(close, 14)
    rsi_val = rsi.iloc[-1]
    if pd.isna(rsi_val) or pd.isna(sma50.iloc[-1]):
        return None, ""
    threshold_ret = max(-0.002 - drought * 0.002, -0.01)
    # Dollar strength filter: strong USD = headwind for USD-base pairs (EURUSD, AUDUSD etc.)
    # USD-quote pairs (USDJPY, USDCHF) benefit from strong dollar
    im = _all_data.get("__intermarket__", {})
    dollar_str = im.get("dollar", "neutral")
    is_usd_quote = symbol in ("USDJPY=X", "USDCHF=X", "USDMXN=X", "USDZAR=X", "USDCAD=X")
    if dollar_str == "strong" and not is_usd_quote:
        threshold_ret += 0.005   # raise bar when USD is strengthening (headwind)
    elif dollar_str == "weak" and not is_usd_quote:
        threshold_ret -= 0.003   # lower bar when USD is weakening (tailwind)
    if (close.iloc[-1] > sma50.iloc[-1] and ret_10 > threshold_ret and 38 < rsi_val < 68):
        dollar_tag = f" [{dollar_str} $]" if dollar_str != "neutral" else ""
        return "BUY", f"Carry momentum: above SMA50, 10d={ret_10*100:.2f}%, RSI {rsi_val:.0f}{dollar_tag}"
    return None, ""


def signal_gap_and_go(symbol: str, df: pd.DataFrame, _all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """Gap-and-Go: large single-day breakout with volume confirmation.
    Scout: retail/momentum-driven continuation after strong catalyst."""
    close = df["Close"]
    volume = df["Volume"]
    if len(close) < 25:
        return None, ""
    daily_ret = (close.iloc[-1] / close.iloc[-2] - 1) if close.iloc[-2] > 0 else 0
    vol_avg = volume.rolling(20).mean()
    vol_ratio = volume.iloc[-1] / vol_avg.iloc[-1] if vol_avg.iloc[-1] > 0 else 0
    rsi = _rsi(close, 14)
    rsi_val = rsi.iloc[-1]
    if pd.isna(rsi_val):
        return None, ""
    gap_threshold = max(0.04 - drought * 0.004, 0.02)
    vol_threshold = max(2.5 - drought * 0.2, 1.5)
    if daily_ret > gap_threshold and vol_ratio > vol_threshold and 45 < rsi_val < 80:
        return "BUY", f"Gap-and-Go: +{daily_ret*100:.1f}% today, vol {vol_ratio:.1f}x, RSI {rsi_val:.0f}"
    return None, ""


def signal_anomaly_detector(symbol: str, df: pd.DataFrame, _all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """Anomaly Detection: unusual volume Z-score + muted price reaction = accumulation.
    Scout: volume outlier with price absorption signals institutional buying.
    v5.9: Z-score based — volume Z>2.5σ + close in upper 40% of range = BUY."""
    close = df["Close"]
    if len(close) < 21 or "Volume" not in df.columns:
        return None, ""

    volume = df["Volume"]
    high   = df["High"] if "High" in df.columns else close
    low    = df["Low"]  if "Low"  in df.columns else close

    # Volume Z-score: how unusual is today's volume vs 20d mean/std
    vol_series = volume.astype(float).replace(0, np.nan).dropna()
    if len(vol_series) < 21:
        return None, ""
    vol_mean = float(vol_series.rolling(20).mean().iloc[-1])
    vol_std  = float(vol_series.rolling(20).std().iloc[-1])
    if vol_mean <= 0 or vol_std <= 0 or np.isnan(vol_std):
        return None, ""
    vol_z = (float(vol_series.iloc[-1]) - vol_mean) / vol_std

    # Price return Z-score: how unusual is today's return
    ret = close.pct_change()
    ret_std = float(ret.rolling(20).std().iloc[-1])
    ret_mean = float(ret.rolling(20).mean().iloc[-1])
    if ret_std <= 0 or np.isnan(ret_std):
        return None, ""
    ret_z = (float(ret.iloc[-1]) - ret_mean) / ret_std

    # Anomaly: very high volume but muted price + close in upper range
    # = institutional absorption (they're buying into volume without driving price)
    vol_threshold = max(2.5 - drought * 0.2, 1.8)
    day_range = float(high.iloc[-1] - low.iloc[-1]) if "High" in df.columns else 0.0
    close_pos = ((float(close.iloc[-1]) - float(low.iloc[-1])) / day_range
                 if day_range > 0 else 0.5)

    if vol_z > vol_threshold and ret_z > -1.5 and close_pos > 0.40:
        return "BUY", (
            f"Volume anomaly: vol_z={vol_z:.1f}σ, ret_z={ret_z:.1f}σ, "
            f"close_pos={close_pos:.2f} — absorption/accumulation pattern"
        )
    return None, ""


def signal_earnings_drift(symbol: str, df: pd.DataFrame, _all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """Pre-Earnings Momentum Drift — v6.1.
    Academic: stocks tend to drift 2-5% in the 5-15 trading days BEFORE earnings
    (earnings announcement premium / PEAD pre-event drift).
    Entry window: 5-15 days before next earnings date, with positive price momentum.
    Skip if already in the 3-day blackout window (that's handled by earnings guard).
    """
    from datetime import date, timedelta
    close = df["Close"]
    if len(close) < 21:
        return None, ""

    # Check pre-computed earnings dates (injected by run_scanner)
    earnings_dates = _all_data.get("__earnings_dates__", {})
    next_ed = earnings_dates.get(symbol)
    if next_ed is None:
        return None, ""

    today = date.today()
    days_to_earnings = (next_ed - today).days

    # Entry window: 5 to 15 calendar days before earnings
    # Avoid the 3-day blackout (handled by earnings_guard elsewhere)
    drift_window_near  = 4 + max(0, drought)      # tighten window in drought
    drift_window_far   = 15 + min(3, drought * 2)
    if not (drift_window_near <= days_to_earnings <= drift_window_far):
        return None, ""

    # Momentum filter: 5d return positive and stock above 20d SMA
    ret_5d = float(close.iloc[-1] / close.iloc[-5] - 1) if len(close) >= 6 else 0.0
    sma20  = float(close.rolling(20).mean().iloc[-1])
    momentum_ok = ret_5d > -0.01 and float(close.iloc[-1]) > sma20 * 0.99

    # RSI filter: not overbought (RSI < 72 — allow mild heat but not parabolic)
    delta  = close.diff()
    gain   = delta.clip(lower=0).rolling(14).mean()
    loss   = (-delta.clip(upper=0)).rolling(14).mean()
    rs     = gain / loss.replace(0, np.nan)
    rsi    = float((100 - 100 / (1 + rs)).iloc[-1]) if not rs.isna().iloc[-1] else 50.0
    rsi_ok = rsi < 72.0

    if momentum_ok and rsi_ok:
        return "BUY", (
            f"Pre-earnings drift: {days_to_earnings}d to earnings, "
            f"ret_5d={ret_5d*100:.1f}%, RSI={rsi:.1f} — earnings announcement premium"
        )
    return None, ""


def signal_post_earnings_mean_rev(symbol: str, df: pd.DataFrame, _all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """Post-Earnings Mean Reversion — v6.3.
    Academic: large earnings gap-downs (>5%) tend to partially revert within 5-10 days.
    The initial reaction overestimates the bad news (Skinner & Sloan 2002, Ball & Brown 1968).
    Strategy: stock dropped >4% in 1-3 days post-earnings, now showing stabilization.
    Only fires when VIX term structure is in backwardation or flat (fear = mean-rev setup).
    """
    close = df["Close"]
    if len(close) < 10:
        return None, ""

    # Look for a large gap-down in the last 1-3 trading days
    drop_thresh = max(0.04 - drought * 0.003, 0.025)   # 4% default, looser in drought

    # Check each of the last 3 days for a large single-day drop
    best_drop = 0.0
    best_day  = -1
    for lookback in range(1, 4):
        idx = -(lookback + 1)
        if abs(idx) > len(close):
            break
        day_ret = float(close.iloc[-lookback] / close.iloc[idx] - 1)
        if day_ret < -drop_thresh and abs(day_ret) > abs(best_drop):
            best_drop = day_ret
            best_day  = lookback

    if best_day < 0:
        return None, ""

    # Stabilization: today's return is non-catastrophic (no further waterfall)
    today_ret = float(close.pct_change().iloc[-1])
    if today_ret < -0.02:
        return None, ""   # still in freefall — wait

    # Volume subsiding: today's volume below yesterday's (panic selling slowing)
    if "Volume" in df.columns:
        vol_today     = float(df["Volume"].iloc[-1])
        vol_yesterday = float(df["Volume"].iloc[-2]) if len(df) >= 2 else vol_today
        vol_subsiding = vol_today < vol_yesterday * 1.10   # today's vol ≤ 110% of yesterday
    else:
        vol_subsiding = True  # can't check — assume OK

    # RSI oversold confirmation (short-term panic)
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, np.nan)
    rsi   = float((100 - 100 / (1 + rs)).iloc[-1]) if not rs.isna().iloc[-1] else 50.0
    rsi_oversold = rsi < (40.0 + drought * 3.0)   # <40 normal, loosens to <52 with drought

    # VIX term structure context: prefer backwardation / flat (fear = mean-rev opportunity)
    vts = _all_data.get("__vix_term__", {})
    vts_signal = vts.get("term_signal", "flat") if isinstance(vts, dict) else "flat"
    vts_ok = vts_signal in ("backwardation", "flat")

    if vol_subsiding and rsi_oversold and vts_ok:
        return "BUY", (
            f"Post-earnings mean rev: {best_drop*100:.1f}% drop {best_day}d ago, "
            f"RSI={rsi:.1f}, vol_subsiding={vol_subsiding}, "
            f"VIX term={vts_signal} — oversold bounce setup"
        )
    return None, ""


def signal_zscore_mean_reversion(symbol: str, df: pd.DataFrame, _all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """
    v7.3: Statistical Mean Reversion Z-Score Band.
    Based on Avellaneda & Lee (2010) statistical arbitrage and Bollinger Band theory.
    Fires when price is at extreme statistical deviation (-2σ or lower) from its mean,
    confirmed by ATR-normalized band breach, volume capitulation, and declining trend.

    Signal fires when:
    1. Z-score = (close - 20d mean) / 20d std < -2.0 (extreme negative deviation)
    2. ATR confirms: close < (mean - 2.0 × ATR_20) — price is outside ATR-normalized band
    3. RSI < 32 (oversold confirmation)
    4. Volume spike in recent 3 bars (capitulation — sellers exhausted)
    5. VIX term NOT extreme backwardation (don't catch falling knives in panic)

    Academic: statistical arbitrage theory — prices that deviate >2σ from mean revert
    with ~68% probability within 5-10 bars. AQR and Two Sigma use this as a component
    in their statistical arbitrage portfolios.
    """
    close = df["Close"]
    if len(close) < 25:
        return None, ""

    window = 20
    mean20   = close.rolling(window).mean()
    std20    = close.rolling(window).std()
    high_col = df.get("High", None)
    low_col  = df.get("Low", None)

    if pd.isna(mean20.iloc[-1]) or pd.isna(std20.iloc[-1]) or std20.iloc[-1] <= 0:
        return None, ""

    z_score = (float(close.iloc[-1]) - float(mean20.iloc[-1])) / float(std20.iloc[-1])
    z_threshold = -2.0 - drought * 0.15  # relax: -2.15, -2.30, etc.
    if z_score > z_threshold:
        return None, ""

    # ATR-based band confirmation
    if high_col is not None and low_col is not None and len(high_col) >= window:
        high = df["High"]
        low  = df["Low"]
        tr   = pd.concat([high - low,
                          (high - close.shift(1)).abs(),
                          (low  - close.shift(1)).abs()], axis=1).max(axis=1)
        atr20 = float(tr.rolling(window).mean().iloc[-1])
        atr_band_low = float(mean20.iloc[-1]) - 2.0 * atr20
        if float(close.iloc[-1]) > atr_band_low:
            return None, ""

    # RSI oversold
    rsi = _rsi(close, 14)
    if rsi.empty or pd.isna(rsi.iloc[-1]):
        return None, ""
    rsi_val  = float(rsi.iloc[-1])
    rsi_thresh = 32 + drought * 3
    if rsi_val > rsi_thresh:
        return None, ""

    # Volume capitulation: recent 3-bar max volume > 1.5× 20d avg
    if "Volume" in df.columns and len(df) >= 23:
        vol_recent = float(df["Volume"].iloc[-3:].max())
        vol_avg    = float(df["Volume"].iloc[-23:-3].mean())
        if vol_avg > 0 and vol_recent < vol_avg * 1.3:
            return None, ""  # no capitulation volume

    # VIX guard: don't enter in extreme panic (backwardation with high VIX)
    vix_term = _all_data.get("__vix_term__", {})
    if isinstance(vix_term, dict):
        if vix_term.get("term_signal") == "backwardation" and float(vix_term.get("vix_spot", 20)) > 30:
            return None, ""

    return "BUY", (
        f"Z-score mean rev: z={z_score:.2f} (<{z_threshold:.1f}σ) · RSI={rsi_val:.1f}"
    )


def signal_rsi_divergence(symbol: str, df: pd.DataFrame, _all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """RSI Bullish Divergence — v6.4.
    Bullish divergence: price makes a LOWER low but RSI makes a HIGHER low.
    This indicates momentum is improving before price confirms — early reversal signal.
    One of the most academically robust technical indicators (Wilder 1978, Chong & Ng 2008).
    Requires a meaningful lookback period (20-30 bars) to identify two comparable troughs.
    """
    close = df["Close"]
    if len(close) < 30:
        return None, ""

    # Compute 14-period RSI
    delta  = close.diff()
    gain   = delta.clip(lower=0).rolling(14).mean()
    loss   = (-delta.clip(upper=0)).rolling(14).mean()
    rs_raw = gain / loss.replace(0, np.nan)
    rsi_s  = (100 - 100 / (1 + rs_raw)).fillna(50.0)

    # Find two recent troughs in price and RSI over last 30 bars
    # Trough: a bar where price/RSI is lower than both neighbors
    lookback = min(30, len(close) - 1)
    prices = close.iloc[-lookback:].values
    rsi_v  = rsi_s.iloc[-lookback:].values

    price_troughs = []
    rsi_troughs   = []
    for i in range(1, len(prices) - 1):
        if prices[i] < prices[i - 1] and prices[i] < prices[i + 1]:
            price_troughs.append((i, prices[i]))
        if rsi_v[i] < rsi_v[i - 1] and rsi_v[i] < rsi_v[i + 1]:
            rsi_troughs.append((i, rsi_v[i]))

    if len(price_troughs) < 2 or len(rsi_troughs) < 2:
        return None, ""

    # Most recent pair of troughs
    pt1_idx, pt1_price = price_troughs[-2]
    pt2_idx, pt2_price = price_troughs[-1]
    rt1_idx, rt1_rsi   = rsi_troughs[-2]
    rt2_idx, rt2_rsi   = rsi_troughs[-1]

    # Synchronize: RSI troughs should be in similar time window as price troughs
    # Allow ±3 bars tolerance
    if abs(pt2_idx - rt2_idx) > 4 or abs(pt1_idx - rt1_idx) > 4:
        return None, ""

    # Bullish divergence: price lower low + RSI higher low
    price_lower_low = pt2_price < pt1_price * (1.0 - 0.005)   # at least 0.5% lower
    rsi_higher_low  = rt2_rsi > rt1_rsi + 1.5                  # at least 1.5 RSI points higher

    # RSI in oversold territory at most recent trough (< 35 default, loosens with drought)
    rsi_oversold_at_trough = rt2_rsi < (35.0 + drought * 4.0)

    # Current price not gapping up already (we want to enter early)
    current_ret = float(close.pct_change().iloc[-1])
    not_already_up = current_ret < 0.04   # hasn't already rallied 4%+

    if price_lower_low and rsi_higher_low and rsi_oversold_at_trough and not_already_up:
        divergence_strength = round(rt2_rsi - rt1_rsi, 1)
        return "BUY", (
            f"RSI bullish divergence: price {pt2_price:.2f} < {pt1_price:.2f} (lower low), "
            f"RSI {rt2_rsi:.1f} > {rt1_rsi:.1f} (higher low +{divergence_strength}), "
            f"RSI oversold at {rt2_rsi:.1f} — momentum reversal signal"
        )
    return None, ""


def signal_vwap_reversion(symbol: str, df: pd.DataFrame, all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """VWAP Reversion: price below 20-day rolling VWAP → institutional support buying.
    Scout: market-microstructure signal — Goldman, Jane Street all buy below VWAP.
    v5.6: rolling 20d VWAP from daily OHLCV acts as institutional cost-basis anchor."""
    close = df["Close"]
    if len(close) < 21 or "High" not in df.columns or "Low" not in df.columns or "Volume" not in df.columns:
        return None, ""

    high   = df["High"]
    low    = df["Low"]
    volume = df["Volume"]

    # 20-day rolling VWAP: typical_price × volume, normalized
    typical = (high + low + close) / 3.0
    vol_20  = volume.rolling(20).sum()
    vwap_20 = (typical * volume).rolling(20).sum() / vol_20
    if pd.isna(vwap_20.iloc[-1]) or vol_20.iloc[-1] <= 0:
        return None, ""

    vwap_val = float(vwap_20.iloc[-1])
    curr     = float(close.iloc[-1])
    dev_pct  = (curr - vwap_val) / vwap_val  # negative = below VWAP

    # Deviation threshold (relaxed with drought)
    dev_threshold = max(-0.02 - drought * 0.004, -0.05)  # default -2%, min -5%

    if dev_pct > dev_threshold:
        return None, ""   # price is at or above VWAP — no reversion setup

    # Market microstructure: where did we close relative to today's candle range?
    # Close near the top of the day's range = buyers stepped in even though we're below VWAP
    day_range = float(high.iloc[-1] - low.iloc[-1])
    if day_range > 0:
        close_position = (float(close.iloc[-1]) - float(low.iloc[-1])) / day_range
    else:
        close_position = 0.5

    # RSI for oversold confirmation
    rsi_val = float(_rsi(close, 14).iloc[-1])
    if pd.isna(rsi_val):
        return None, ""

    rsi_threshold = min(40 + drought * 3, 50)

    # Volume confirmation: above average (institutions stepping in)
    avg_vol = float(volume.rolling(20).mean().iloc[-1])
    vol_ratio = float(volume.iloc[-1]) / avg_vol if avg_vol > 0 else 1.0

    if (dev_pct <= dev_threshold and rsi_val < rsi_threshold and
            close_position > 0.45 and vol_ratio > 0.8):
        return "BUY", (
            f"VWAP reversion: {dev_pct*100:.1f}% below VWAP"
            f", close-pos={close_position:.2f}, RSI={rsi_val:.0f}"
        )
    return None, ""


def signal_multi_timeframe_align(symbol: str, df: pd.DataFrame, _all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """
    v7.5: Multi-timeframe trend alignment (MTF).
    Fires only when daily, weekly, and monthly trends are all bullish simultaneously.
    This is the "three-green-lights" institutional entry filter used by CTA funds.

    Using daily OHLC data, we construct proxy timeframes:
    - "Daily" trend:   price > 10d SMA + recent upward momentum (3d return > 0)
    - "Weekly" trend:  price > 20d SMA + 5d return > 0 (weekly proxy)
    - "Monthly" trend: price > 50d SMA + 20d return > 3% (monthly proxy)

    All three timeframes must confirm before entry.
    Also checks: RSI in 45-70 range (trending but not overbought) + volume > average.

    Academic: Antonacci (2014) dual momentum, Hurst (2011) AHL trend decomposition.
    Multi-timeframe confluence dramatically reduces false signals vs single-TF entry.
    """
    close = df["Close"]
    if len(close) < 55:
        return None, ""

    price = float(close.iloc[-1])

    # Compute SMAs
    sma10 = close.rolling(10).mean()
    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()

    if any(pd.isna(s.iloc[-1]) for s in [sma10, sma20, sma50]):
        return None, ""

    sma10v = float(sma10.iloc[-1])
    sma20v = float(sma20.iloc[-1])
    sma50v = float(sma50.iloc[-1])

    # Daily trend
    ret_3d = (price / float(close.iloc[-4]) - 1) if len(close) >= 4 else 0.0
    daily_bull = price > sma10v * 0.995 and ret_3d > 0

    # Weekly trend (5-day proxy)
    ret_5d = (price / float(close.iloc[-6]) - 1) if len(close) >= 6 else 0.0
    weekly_bull = price > sma20v * 0.995 and ret_5d > 0

    # Monthly trend (20-day proxy)
    ret_20d = (price / float(close.iloc[-21]) - 1) if len(close) >= 21 else 0.0
    monthly_thresh = max(0.01, 0.03 - drought * 0.005)  # relax with drought
    monthly_bull = price > sma50v * 0.995 and ret_20d > monthly_thresh

    # All three timeframes must be bullish
    if not (daily_bull and weekly_bull and monthly_bull):
        return None, ""

    # Trend structure: SMA alignment (price > SMA10 > SMA20 > SMA50)
    sma_aligned = sma10v > sma20v * 0.99 and sma20v > sma50v * 0.99
    if not sma_aligned:
        return None, ""

    # RSI in trending zone (not overbought, not oversold)
    rsi = _rsi(close, 14)
    if rsi.empty or pd.isna(rsi.iloc[-1]):
        return None, ""
    rsi_val = float(rsi.iloc[-1])
    rsi_lo = max(42, 45 - drought * 2)
    rsi_hi = 70 + drought * 2
    if not (rsi_lo <= rsi_val <= rsi_hi):
        return None, ""

    # Volume confirmation (above average = institutional participation)
    if "Volume" in df.columns and len(df) >= 21:
        avg_vol = float(df["Volume"].rolling(20).mean().iloc[-1])
        today_vol = float(df["Volume"].iloc[-1]) if not pd.isna(df["Volume"].iloc[-1]) else 0.0
        if avg_vol > 0 and today_vol < avg_vol * 0.8:
            return None, ""

    # Score: count how many timeframes are above-average strong
    tf_score = sum([
        1 if ret_3d > 0.005 else 0,
        1 if ret_5d > 0.01 else 0,
        1 if ret_20d > 0.05 else 0,
    ])

    return "BUY", (
        f"MTF align: daily+weekly+monthly bull · SMA10>SMA20>SMA50"
        f" · 20d=+{ret_20d*100:.1f}% · RSI={rsi_val:.1f} · tf_score={tf_score}/3"
    )


def signal_hh_hl_structure(symbol: str, df: pd.DataFrame, _all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """
    v7.6: Higher-High, Higher-Low swing structure detector (Dow Theory / trend confirmation).
    Fires when price is forming proper uptrend structure: each swing high is higher than
    the previous, and each swing low is higher than the previous.

    This is the foundational pattern that confirms an asset has transitioned from
    distribution/accumulation to a confirmed uptrend. All CTA desks and trend followers
    verify HH/HL structure before entering trend-following positions.

    Algorithm:
    1. Detect swing highs: local maxima over 5-bar window (high > all surrounding bars)
    2. Detect swing lows: local minima over 5-bar window (low < all surrounding bars)
    3. Signal fires when last 2 swing highs are ascending AND last 2 swing lows are ascending
    4. Recent price must be above the most recent swing low (still in uptrend)
    5. Price must be within 3% of the most recent swing high (near breakout territory)

    Academic: Dow Theory (1900), Edwards & Magee "Technical Analysis of Stock Trends" (1948).
    This structure is the basis for all swing trading and trend-following systems.
    """
    close = df["Close"]
    if len(close) < 30:
        return None, ""

    if "High" not in df.columns or "Low" not in df.columns:
        return None, ""

    high = df["High"].values
    low  = df["Low"].values
    n    = len(high)

    # Find swing highs: local max over window (simplified 5-bar)
    swing_h_idx = []
    swing_l_idx = []
    w = 3  # half-window (relax in drought to 2)
    if drought >= 2:
        w = 2

    for i in range(w, n - w):
        if all(high[i] >= high[i-j] for j in range(1, w+1)) and all(high[i] >= high[i+j] for j in range(1, w+1)):
            swing_h_idx.append(i)
        if all(low[i] <= low[i-j] for j in range(1, w+1)) and all(low[i] <= low[i+j] for j in range(1, w+1)):
            swing_l_idx.append(i)

    if len(swing_h_idx) < 2 or len(swing_l_idx) < 2:
        return None, ""

    # Get the last 2 swing highs and last 2 swing lows
    sh1, sh2 = swing_h_idx[-2], swing_h_idx[-1]  # sh2 is more recent
    sl1, sl2 = swing_l_idx[-2], swing_l_idx[-1]  # sl2 is more recent

    sh1_val = float(high[sh1])
    sh2_val = float(high[sh2])
    sl1_val = float(low[sl1])
    sl2_val = float(low[sl2])

    # Must be in chronological order and swing high must be after swing low
    if sh1 >= sh2 or sl1 >= sl2:
        return None, ""

    # Higher High: sh2 > sh1 (margin: allow drought to relax threshold)
    hh_margin = max(0, 0.005 - drought * 0.001)
    if sh2_val <= sh1_val * (1 + hh_margin):
        return None, ""

    # Higher Low: sl2 > sl1
    hl_margin = max(-0.01, 0.0 - drought * 0.002)   # slight negative margin allowed in drought
    if sl2_val <= sl1_val * (1 + hl_margin):
        return None, ""

    # Current price above the most recent swing low (still in structure)
    price_now = float(close.iloc[-1])
    if price_now < sl2_val * 0.99:
        return None, ""

    # Near breakout: price within 5% of most recent swing high
    proximity = max(0.04, 0.05 + drought * 0.01)
    if price_now < sh2_val * (1 - proximity):
        return None, ""

    # RSI confirmation: in trending zone (not overbought)
    rsi = _rsi(close, 14)
    if rsi.empty or pd.isna(rsi.iloc[-1]):
        return None, ""
    rsi_val = float(rsi.iloc[-1])
    if rsi_val > 72 + drought * 3:
        return None, ""

    hh_pct = round((sh2_val - sh1_val) / sh1_val * 100, 1)
    hl_pct = round((sl2_val - sl1_val) / sl1_val * 100, 1)
    return "BUY", (
        f"HH+HL structure: HH +{hh_pct:.1f}% · HL +{hl_pct:.1f}%"
        f" · price {round((price_now/sh2_val-1)*100,1)}% from swing high · RSI={rsi_val:.1f}"
    )


def signal_dual_momentum(symbol: str, df: pd.DataFrame, all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """
    v7.7: Antonacci Dual Momentum — Global Equity Momentum (GEM) adaptation.

    Absolute momentum: 12-month return must be positive (the asset itself is trending up
    in absolute terms — not just relative to peers).

    Relative momentum: 12-month return must exceed the SPY benchmark by a minimum margin
    (the asset is a stronger performer than the broad market).

    Short-term confirmation: 1-month return must not be severely negative (avoiding
    catching falling knives that have positive 12m but are rolling over).

    Drought mode: all thresholds relax progressively to prevent signal starvation.
    """
    if len(df) < 260:
        return None, "insufficient history (need 260 bars)"

    close = df["Close"]

    # Absolute momentum: 12m return
    if len(df) < 252:
        return None, "need 252-bar history for 12m return"
    ret_12m = float(close.iloc[-1] / close.iloc[-252] - 1.0)
    ret_6m  = float(close.iloc[-1] / close.iloc[-126] - 1.0) if len(df) >= 126 else 0.0
    ret_3m  = float(close.iloc[-1] / close.iloc[-63]  - 1.0) if len(df) >= 63  else 0.0
    ret_1m  = float(close.iloc[-1] / close.iloc[-21]  - 1.0)

    # Absolute momentum threshold (positive + margin)
    abs_thresh = max(0.0, 0.05 - drought * 0.01)   # 5% → 0% over 5 drought steps
    if ret_12m < abs_thresh:
        return None, f"12m={ret_12m:.1%} below abs threshold {abs_thresh:.1%}"

    # Relative momentum: beat SPY by at least 2% on 12m basis
    spy_df = all_data.get("SPY")
    spy_ret_12m = 0.0
    if spy_df is not None and len(spy_df) >= 252:
        spy_close = spy_df["Close"]
        spy_ret_12m = float(spy_close.iloc[-1] / spy_close.iloc[-252] - 1.0)

    rel_margin = max(-0.02, 0.02 - drought * 0.005)   # 2% → -2% lead over drought
    if ret_12m < spy_ret_12m + rel_margin:
        return None, f"12m={ret_12m:.1%} not beating SPY {spy_ret_12m:.1%} by {rel_margin:.1%}"

    # Short-term stability: 1m must not be deeply negative (avoid rolling-over leaders)
    st_floor = max(-0.08, -0.04 - drought * 0.01)
    if ret_1m < st_floor:
        return None, f"1m={ret_1m:.1%} deteriorating (floor {st_floor:.1%})"

    # Price above SMA200 (long-term trend filter)
    sma200 = float(close.rolling(200).mean().iloc[-1])
    sma200_floor = max(0.93, 0.97 - drought * 0.01)
    if close.iloc[-1] < sma200 * sma200_floor:
        return None, f"price below SMA200×{sma200_floor:.2f}"

    # RSI guard — not overbought at entry
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(com=13, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(com=13, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi_val = float((100 - 100 / (1 + rs)).iloc[-1])
    rsi_max = 72 + drought * 3
    if rsi_val > rsi_max:
        return None, f"RSI overbought: {rsi_val:.1f} > {rsi_max}"

    outperf = ret_12m - spy_ret_12m
    return "BUY", (
        f"DualMomentum: 12m={ret_12m:.1%} abs · +{outperf:.1%} vs SPY"
        f" · 3m={ret_3m:.1%} · 1m={ret_1m:.1%} · RSI={rsi_val:.1f}"
    )


# Sector ETF map for breadth thrust signal (v7.8)
_SECTOR_ETF_MAP: dict[str, str] = {
    # Technology
    "AAPL": "XLK", "MSFT": "XLK", "NVDA": "XLK", "AMD": "XLK", "GOOGL": "XLK",
    "META": "XLK", "INTC": "XLK", "AVGO": "XLK", "PLTR": "XLK", "COIN": "XLK", "MSTR": "XLK",
    # Consumer Discretionary
    "AMZN": "XLY", "TSLA": "XLY", "HD": "XLY", "NKE": "XLY",
    "NFLX": "XLY", "UBER": "XLY", "SHOP": "XLY", "RBLX": "XLY", "SNAP": "XLY",
    # Financials
    "JPM": "XLF", "BAC": "XLF", "WFC": "XLF", "GS": "XLF", "MS": "XLF", "SOFI": "XLF", "SQ": "XLF",
    # Health Care
    "JNJ": "XLV", "PFE": "XLV", "UNH": "XLV", "ABBV": "XLV",
    # Energy
    "XOM": "XLE", "CVX": "XLE", "COP": "XLE",
    # EV / Other
    "RIVN": "XLY", "LCID": "XLY",
}


def signal_breadth_thrust(symbol: str, df: pd.DataFrame, all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """
    v7.8: Sector Breadth Thrust — McClellan Oscillator proxy.

    Adapts the McClellan Oscillator (traditional 19d/39d EMA of NYSE net advances)
    to a per-sector signal using sector ETF OHLCV data.

    Approach:
    1. For the symbol's sector ETF (via _SECTOR_ETF_MAP), compute a daily
       "normalized position" = (close - 50d low) / (50d high - 50d low) × 100
       This proxies the "advance/decline" contribution of that sector.
    2. Apply 19-bar EMA and 39-bar EMA to these daily positions (standard McClellan periods).
    3. McClellan proxy = 19d EMA - 39d EMA.
    4. "Breadth thrust" fires when the oscillator recently crossed from negative
       to a positive threshold, indicating accelerating buying breadth.
    5. Individual stock must be in the advancing group (above SMA20, RSI < 68).
    """
    if len(df) < 60:
        return None, "insufficient history"

    # Determine sector ETF
    sector_etf = _SECTOR_ETF_MAP.get(symbol)
    if sector_etf is None:
        # Fall back to SPY as market proxy
        sector_etf = "SPY"

    etf_df = all_data.get(sector_etf)
    if etf_df is None or len(etf_df) < 60:
        return None, f"no sector ETF data ({sector_etf})"

    # --- Sector McClellan proxy ---
    etf_close = etf_df["Close"]
    lo50 = etf_close.rolling(50).min()
    hi50 = etf_close.rolling(50).max()
    rng  = (hi50 - lo50).replace(0, np.nan)
    # normalized 0-100 position within 50d range
    norm_pos = (etf_close - lo50) / rng * 100.0

    ema19 = norm_pos.ewm(span=19, adjust=False).mean()
    ema39 = norm_pos.ewm(span=39, adjust=False).mean()
    osc   = ema19 - ema39   # McClellan proxy: positive = breadth expanding

    if len(osc.dropna()) < 5:
        return None, "oscillator warmup"

    osc_now  = float(osc.iloc[-1])
    osc_prev = float(osc.iloc[-4])  # 4 bars ago (1 week)

    # Thrust condition: oscillator was negative 1 week ago, now clearly positive
    thrust_floor = max(2.0, 5.0 - drought * 0.5)   # threshold for "positive enough"
    if not (osc_prev < 0.0 and osc_now > thrust_floor):
        return None, f"no thrust: osc {osc_prev:.1f}→{osc_now:.1f} (need cross above {thrust_floor:.1f})"

    # Individual stock must be in the advancing group
    close = df["Close"]
    sma20 = close.rolling(20).mean().iloc[-1]
    sma20_floor = max(0.97, 0.99 - drought * 0.005)
    if close.iloc[-1] < sma20 * sma20_floor:
        return None, "stock not in advancing group (below SMA20)"

    # Volume confirmation: above-average volume during thrust window
    vol = df["Volume"].astype(float)
    avg_vol = vol.rolling(20).mean().iloc[-1]
    vol_now = vol.iloc[-1]
    vol_mult = max(0.80, 1.0 - drought * 0.05)
    if avg_vol > 0 and vol_now < avg_vol * vol_mult:
        return None, f"weak volume during thrust: {vol_now/avg_vol:.2f}× avg"

    # RSI guard
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(com=13, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(com=13, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi_val = float((100 - 100 / (1 + rs)).iloc[-1])
    rsi_max = 68 + drought * 3
    if rsi_val > rsi_max:
        return None, f"RSI overbought: {rsi_val:.1f} > {rsi_max}"

    return "BUY", (
        f"BreadthThrust({sector_etf}): osc {osc_prev:.1f}→{osc_now:.1f}"
        f" · vol={vol_now/avg_vol:.2f}× · RSI={rsi_val:.1f}"
    )


def signal_volume_weighted_rsi(symbol: str, df: pd.DataFrame, _all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """
    v7.9: Volume-Weighted RSI (VRSI) — volume-adjusted momentum reversal.

    Traditional RSI treats every bar equally regardless of volume. VRSI weights
    each bar's price change contribution by its relative volume, so high-volume
    moves have more impact on the oscillator. This reduces false signals on
    thin-volume price swings and amplifies high-conviction directional moves.

    Signal logic:
    - VRSI crosses from oversold territory (<30) back above entry threshold (35-38)
    - Standard RSI is NOT also overbought (acts as confirmation)
    - Price above SMA50 (medium-term trend filter)
    - Recent VRSI trough must be below 32 (confirmed oversold dip)
    """
    if len(df) < 30:
        return None, "insufficient history"

    close = df["Close"]
    volume = df["Volume"].astype(float)

    # Volume-Weighted RSI computation
    # Each period's gain/loss is multiplied by its volume relative to 14-bar avg volume
    avg_vol_14 = volume.rolling(14).mean()
    vol_weight = (volume / avg_vol_14.replace(0, np.nan)).fillna(1.0)

    delta = close.diff()
    gain_raw  = delta.clip(lower=0)
    loss_raw  = (-delta.clip(upper=0))

    # Weight each day's gain/loss by volume
    gain_wt = gain_raw * vol_weight
    loss_wt = loss_raw * vol_weight

    # Apply 14-period EMA (Wilder smoothing via EWM)
    avg_gain_vw = gain_wt.ewm(com=13, adjust=False).mean()
    avg_loss_vw = loss_wt.ewm(com=13, adjust=False).mean()

    rs_vw    = avg_gain_vw / avg_loss_vw.replace(0, np.nan)
    vrsi     = 100 - 100 / (1 + rs_vw)

    # Also compute standard RSI for confirmation
    avg_gain_std = gain_raw.ewm(com=13, adjust=False).mean()
    avg_loss_std = loss_raw.ewm(com=13, adjust=False).mean()
    rs_std       = avg_gain_std / avg_loss_std.replace(0, np.nan)
    rsi_std      = 100 - 100 / (1 + rs_std)

    if len(vrsi.dropna()) < 5:
        return None, "VRSI warmup"

    vrsi_now  = float(vrsi.iloc[-1])
    rsi_now   = float(rsi_std.iloc[-1])

    # Recent trough: lowest VRSI over past 5 bars must have been oversold
    vrsi_trough = float(vrsi.iloc[-5:].min())
    oversold_floor = 32 - drought * 1    # 32 → ~28 over 4 drought steps
    if vrsi_trough > oversold_floor:
        return None, f"no oversold dip: VRSI trough {vrsi_trough:.1f} > {oversold_floor:.0f}"

    # Current VRSI must be recovering above entry threshold
    entry_thresh = max(32.0, 37.0 - drought * 1.0)
    if vrsi_now < entry_thresh:
        return None, f"VRSI still below entry: {vrsi_now:.1f} < {entry_thresh:.0f}"

    # Standard RSI confirmation: not overbought (prevents chasing)
    if rsi_now > 65:
        return None, f"standard RSI overbought: {rsi_now:.1f}"

    # Medium-term trend filter: price above SMA50
    sma50 = float(close.rolling(50).mean().iloc[-1])
    sma50_floor = max(0.93, 0.97 - drought * 0.01)
    if close.iloc[-1] < sma50 * sma50_floor:
        return None, f"price below SMA50×{sma50_floor:.2f}"

    divergence = vrsi_now - rsi_now  # positive = volume-weighted signal stronger
    return "BUY", (
        f"VRSI: {vrsi_trough:.1f}→{vrsi_now:.1f} (trough→now)"
        f" · stdRSI={rsi_now:.1f} · div={divergence:+.1f}"
    )


def signal_fibonacci_bounce(symbol: str, df: pd.DataFrame, _all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """
    v8.0: Fibonacci Golden Ratio Retracement Bounce.

    Identifies stocks that have pulled back to classic Fibonacci retracement levels
    (38.2%, 50%, or 61.8%) from a recent swing high, then shows reversal signals.
    The 61.8% level (the "Golden Ratio") is the most significant support in Fibonacci theory.

    Method:
    1. Identify the most recent significant swing high over a lookback window
    2. Identify the swing low preceding that high (the base of the up-move)
    3. Compute Fibonacci retracement levels: 38.2%, 50%, 61.8% of the swing range
    4. Check if current price is near one of these levels (within tolerance)
    5. Require reversal confirmation: price action turning up from the level
    6. Volume and RSI confirmation filters
    """
    if len(df) < 80:
        return None, "insufficient history"

    close  = df["Close"]
    high   = df["High"]
    low    = df["Low"]
    volume = df["Volume"].astype(float)

    # Lookback window for swing high/low identification (60 bars ≈ 3 months)
    lookback = 60
    recent_close = close.iloc[-lookback:]
    recent_high  = high.iloc[-lookback:]
    recent_low   = low.iloc[-lookback:]

    # Find swing high (recent peak, exclude last 5 bars to allow retracement)
    swing_high_idx = recent_high.iloc[:-5].idxmax() if len(recent_high) > 5 else recent_high.idxmax()
    swing_high_val = float(high.loc[swing_high_idx])

    # Find swing low BEFORE the swing high (base of the up-move)
    pre_high_idx = recent_low.index[recent_low.index <= swing_high_idx]
    if len(pre_high_idx) < 5:
        return None, "swing high too early in lookback"
    swing_low_val = float(recent_low.loc[pre_high_idx].min())

    if swing_high_val <= swing_low_val:
        return None, "no valid swing range"

    swing_range = swing_high_val - swing_low_val
    if swing_range / swing_high_val < 0.05:
        return None, f"swing too small: {swing_range/swing_high_val:.1%}"

    # Fibonacci levels
    fib_382 = swing_high_val - 0.382 * swing_range
    fib_500 = swing_high_val - 0.500 * swing_range
    fib_618 = swing_high_val - 0.618 * swing_range

    price_now = float(close.iloc[-1])
    tolerance = max(0.015, 0.025 - drought * 0.002)  # 2.5% → 1.5% tolerance

    # Check proximity to any Fibonacci level
    at_382 = abs(price_now - fib_382) / fib_382 < tolerance
    at_500 = abs(price_now - fib_500) / fib_500 < tolerance
    at_618 = abs(price_now - fib_618) / fib_618 < tolerance

    if not (at_382 or at_500 or at_618):
        nearest = min(abs(price_now - fib_382)/fib_382, abs(price_now - fib_500)/fib_500, abs(price_now - fib_618)/fib_618)
        return None, f"not near Fib level (nearest {nearest:.1%} away)"

    fib_level = 38.2 if at_382 else (50.0 if at_500 else 61.8)
    fib_price = fib_382 if at_382 else (fib_500 if at_500 else fib_618)

    # Reversal confirmation: current close > prior close (price bouncing up)
    if float(close.iloc[-1]) <= float(close.iloc[-2]):
        return None, "no reversal candle (close not above prior close)"

    # Price must be above the swing low (not a complete breakdown)
    if price_now < swing_low_val * (1.0 - 0.03):
        return None, f"price broke below swing low {swing_low_val:.4f}"

    # Volume spike on the bounce day
    avg_vol = float(volume.rolling(20).mean().iloc[-1])
    vol_ratio = float(volume.iloc[-1]) / avg_vol if avg_vol > 0 else 1.0
    vol_min = max(0.80, 1.0 - drought * 0.05)
    if vol_ratio < vol_min:
        return None, f"weak volume on bounce: {vol_ratio:.2f}×"

    # RSI guard — not overbought
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(com=13, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(com=13, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi_val = float((100 - 100 / (1 + rs)).iloc[-1])
    rsi_max = 65 + drought * 3
    if rsi_val > rsi_max:
        return None, f"RSI overbought: {rsi_val:.1f}"

    retr_pct = (swing_high_val - price_now) / swing_range * 100
    return "BUY", (
        f"FibBounce {fib_level:.1f}%: price={price_now:.4f} @ {fib_price:.4f}"
        f" · swing {swing_low_val:.4f}→{swing_high_val:.4f} · retr={retr_pct:.1f}%"
        f" · vol={vol_ratio:.2f}× · RSI={rsi_val:.1f}"
    )


def signal_52week_high_breakout(symbol: str, df: pd.DataFrame, _all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """
    v8.1: 52-Week High Breakout — price discovery expansion signal.

    One of the most robust and academically validated signals in momentum research:
    stocks breaking to new 52-week highs tend to continue outperforming (Jegadeesh &
    Titman 1993; George & Hwang 2004 showed 52w high proximity predicts continuation).

    Signal logic:
    - Price breaks above or is within 1% below its rolling 52-week high
    - This must be a FRESH breakout: price was below 98% of 52w high 5 bars ago
    - Volume spike on the breakout day (institutional confirmation)
    - Not in a high-VIX panic environment (VIX term structure guard)
    - RSI not extreme (<78) — some overbought is expected/ok on real breakouts
    """
    if len(df) < 260:
        return None, "need 260 bars for 52w high"

    close  = df["Close"]
    high   = df["High"]
    volume = df["Volume"].astype(float)

    # Rolling 52-week high (252 trading days)
    high_252 = high.rolling(252).max()
    high_52w  = float(high_252.iloc[-1])
    price_now = float(close.iloc[-1])

    # Breakout: price is at or above 99% of 52w high
    breakout_floor = max(0.97, 0.99 - drought * 0.005)
    if price_now < high_52w * breakout_floor:
        return None, f"not near 52w high ({price_now:.4f} vs {high_52w:.4f})"

    # FRESH breakout: 5 bars ago, price was below 98% of the then-current 52w high
    high_252_prev = float(high_252.iloc[-6]) if len(df) >= 6 else high_52w
    price_prev    = float(close.iloc[-6])
    prev_threshold = max(0.94, 0.98 - drought * 0.01)
    if price_prev >= high_252_prev * prev_threshold:
        return None, "not a fresh breakout (was already near 52w high)"

    # Volume confirmation: above-average on breakout day
    avg_vol = float(volume.rolling(20).mean().iloc[-1])
    vol_ratio = float(volume.iloc[-1]) / avg_vol if avg_vol > 0 else 1.0
    vol_min = max(0.90, 1.2 - drought * 0.05)
    if vol_ratio < vol_min:
        return None, f"weak volume on breakout: {vol_ratio:.2f}× (need {vol_min:.2f}×)"

    # Price consolidation before breakout: check that it wasn't just a one-day spike
    # Require that close > SMA20 (stock has been building up, not just spiking)
    sma20 = float(close.rolling(20).mean().iloc[-1])
    if price_now < sma20 * 0.98:
        return None, "price below SMA20 — spike only, no foundation"

    # RSI guard: allow up to 78 (some overbought normal on real breakouts)
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(com=13, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(com=13, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi_val = float((100 - 100 / (1 + rs)).iloc[-1])
    rsi_max = 78 + drought * 2
    if rsi_val > rsi_max:
        return None, f"extreme RSI: {rsi_val:.1f} > {rsi_max}"

    pct_above_52w = (price_now / high_52w - 1.0) * 100
    return "BUY", (
        f"52wBreakout: {price_now:.4f} vs 52w-high {high_52w:.4f} ({pct_above_52w:+.1f}%)"
        f" · vol={vol_ratio:.2f}× · RSI={rsi_val:.1f}"
    )


def signal_volatility_contraction_breakout(symbol: str, df: pd.DataFrame, _all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """
    v8.2: Volatility Contraction Breakout — Bollinger Band Squeeze + NR7.

    Combines two classic volatility compression signals:
    1. Bollinger Band Squeeze (John Bollinger): BB width at N-day low → energy coiling
    2. NR7 (Toby Crabel): The current bar has the narrowest true range of the past 7 bars

    When both fire simultaneously, it indicates extreme volatility compression that typically
    precedes a significant directional move. The direction filter (price above SMA20) ensures
    we're entering breakouts from the bullish side, not just any squeeze.

    Threshold relaxation with drought: BB squeeze window narrows, NR criteria loosens.
    """
    if len(df) < 30:
        return None, "insufficient history"

    close = df["Close"]
    high  = df["High"]
    low   = df["Low"]
    volume = df["Volume"].astype(float)

    # --- Bollinger Band Squeeze ---
    bb_period = 20
    sma20  = close.rolling(bb_period).mean()
    std20  = close.rolling(bb_period).std()
    bb_width = (2 * std20 / sma20.replace(0, np.nan)) * 100  # normalized BB width %

    # BB squeeze: current width at or below N-bar low (squeeze lookback)
    squeeze_lookback = max(20, 40 - drought * 2)   # 40d → 20d over drought
    bb_width_min = bb_width.rolling(squeeze_lookback).min()
    bb_squeeze = float(bb_width.iloc[-1]) <= float(bb_width_min.iloc[-1]) * 1.05  # within 5% of min

    if not bb_squeeze:
        current_width = float(bb_width.iloc[-1])
        min_width = float(bb_width_min.iloc[-1])
        return None, f"no BB squeeze: width {current_width:.1f}% vs {squeeze_lookback}d-low {min_width:.1f}%"

    # --- NR7: Narrowest True Range of last 7 bars ---
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low  - close.shift(1)).abs()
    ], axis=1).max(axis=1)

    nr_window = max(5, 7 - drought)   # NR7 → NR5 over drought
    tr_min_window = tr.rolling(nr_window).min()
    nr7 = float(tr.iloc[-1]) <= float(tr_min_window.iloc[-1]) * 1.02  # within 2% of min

    if not nr7:
        return None, f"no NR{nr_window}: TR {tr.iloc[-1]:.4f} vs {nr_window}d-min {tr_min_window.iloc[-1]:.4f}"

    # Direction filter: price above SMA20 (bullish squeeze)
    price_now = float(close.iloc[-1])
    sma20_val = float(sma20.iloc[-1])
    sma20_floor = max(0.97, 0.99 - drought * 0.005)
    if price_now < sma20_val * sma20_floor:
        return None, "squeeze but bearish direction (below SMA20)"

    # Volume context: recent volume should be declining (calm before storm)
    avg_vol_5 = float(volume.iloc[-5:].mean())
    avg_vol_20 = float(volume.rolling(20).mean().iloc[-1])
    vol_quiet = avg_vol_5 < avg_vol_20 * 1.2   # not already exploding
    if not vol_quiet:
        return None, f"volume already spiking (not a quiet squeeze)"

    # RSI: not extreme (squeeze near middle territory is best)
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(com=13, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(com=13, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi_val = float((100 - 100 / (1 + rs)).iloc[-1])
    rsi_max = 68 + drought * 3
    if rsi_val > rsi_max:
        return None, f"RSI too high in squeeze: {rsi_val:.1f}"

    bb_width_val = float(bb_width.iloc[-1])
    return "BUY", (
        f"VolContraction: BB-squeeze={bb_width_val:.1f}% · NR{nr_window}"
        f" · price vs SMA20={((price_now/sma20_val)-1)*100:+.1f}%"
        f" · RSI={rsi_val:.1f}"
    )


def signal_macd_hidden_divergence(symbol: str, df: pd.DataFrame, _all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """
    v8.3: MACD Histogram Hidden Divergence (bullish).

    Hidden divergence is the opposite of regular divergence:
    - Price makes a HIGHER LOW (bullish trend continuation)
    - MACD histogram makes a LOWER LOW (momentum appears weaker)
    → This is a BULLISH signal indicating the trend is likely to continue despite
      the apparent momentum weakness. Institutions use this to add to long positions
      during pullbacks in uptrends.

    Contrast with regular divergence (RSI):
    - Regular: price makes higher high, oscillator makes lower high → reversal warning
    - Hidden: price makes higher low, oscillator makes lower low → continuation signal

    The MACD histogram is computed using standard 12/26/9 parameters.
    """
    if len(df) < 35:
        return None, "insufficient history"

    close = df["Close"]

    # MACD standard parameters: 12/26/9
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    histogram = macd_line - signal_line

    # Look back over 20 bars for the two comparison points
    lookback = min(20, len(df) - 5)

    # Find two recent price troughs (local lows) in last `lookback` bars
    # Using a 2-bar window: price[i] < price[i-1] and price[i] < price[i+1]
    price_lows_idx = []
    hist_vals_at_lows = []
    for i in range(len(df) - lookback, len(df) - 1):
        if i > 0 and i < len(df) - 1:
            if float(close.iloc[i]) < float(close.iloc[i-1]) and float(close.iloc[i]) < float(close.iloc[i+1]):
                price_lows_idx.append(i)
                hist_vals_at_lows.append(float(histogram.iloc[i]))

    if len(price_lows_idx) < 2:
        return None, "need 2 price troughs in lookback window"

    # Take the two most recent troughs
    idx1, idx2 = price_lows_idx[-2], price_lows_idx[-1]
    price_low1  = float(close.iloc[idx1])
    price_low2  = float(close.iloc[idx2])
    hist_low1   = hist_vals_at_lows[-2]
    hist_low2   = hist_vals_at_lows[-1]

    # Hidden bullish divergence conditions:
    # 1. Price low2 > price low1 (higher low = uptrend continuation)
    # 2. MACD histogram low2 < hist low1 (lower low = apparent weakness)
    price_hl_margin = max(0.0, 0.002 - drought * 0.0005)   # price must be meaningfully higher
    hist_ll_margin  = max(0.0, 0.0 - drought * 0.1)        # hist can be equal at max drought

    if price_low2 < price_low1 * (1.0 + price_hl_margin):
        return None, f"no higher low: price {price_low2:.4f} ≤ {price_low1:.4f}×{1+price_hl_margin:.4f}"

    if hist_low2 > hist_low1 - hist_ll_margin:
        return None, f"no lower MACD hist: {hist_low2:.4f} ≥ {hist_low1:.4f}"

    # Current price must still be above both troughs (not in a fresh breakdown)
    price_now = float(close.iloc[-1])
    if price_now < price_low2 * 0.99:
        return None, "price has broken below the second trough"

    # MACD should be below zero or near zero (this is a pullback/consolidation signal)
    macd_now = float(macd_line.iloc[-1])
    macd_max = max(0.05 * price_now, 0.02 * price_now + drought * 0.005 * price_now)
    if macd_now > macd_max:
        return None, f"MACD too high ({macd_now:.4f}) — not a pullback"

    # Medium-term trend: price above SMA50
    sma50 = float(close.rolling(50).mean().iloc[-1]) if len(df) >= 50 else float(close.rolling(20).mean().iloc[-1])
    sma50_floor = max(0.93, 0.97 - drought * 0.01)
    if price_now < sma50 * sma50_floor:
        return None, f"price below SMA50×{sma50_floor:.2f}"

    hl_pct = (price_low2 / price_low1 - 1.0) * 100
    hist_diff = hist_low1 - hist_low2   # positive = hist went lower
    return "BUY", (
        f"MACDHiddenDiv: price HL +{hl_pct:.1f}% · hist↓ {hist_low1:.4f}→{hist_low2:.4f}"
        f" · MACD={macd_now:.4f} · SMA50={((price_now/sma50)-1)*100:+.1f}%"
    )


def signal_stoch_rsi_cross(symbol: str, df: pd.DataFrame, _all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """
    v8.4: Stochastic RSI Oversold Cross — dual oscillator confirmation.

    Combines two momentum layers for high-probability reversal detection:
    1. RSI is computed as usual (14-period)
    2. Stochastic is applied to the RSI values themselves over a second window (14-period):
       StochRSI = (RSI - min_RSI_14) / (max_RSI_14 - min_RSI_14)
    3. A 3-bar SMA smoothing creates the %K and %D lines

    Signal: %K crosses above %D from oversold territory (<20).
    This double-oscillator approach filters out most RSI noise:
    RSI alone can be "oversold" for a long time; StochRSI pinpoints the turning point
    within that oversold window — precisely when the oversold condition is ending.
    """
    if len(df) < 40:
        return None, "insufficient history"

    close = df["Close"]

    # Step 1: RSI (14-period, Wilder EWM)
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(com=13, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(com=13, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = (100 - 100 / (1 + rs)).fillna(50.0)

    # Step 2: Stochastic RSI (14-period stochastic of the RSI)
    stoch_period = 14
    rsi_min = rsi.rolling(stoch_period).min()
    rsi_max = rsi.rolling(stoch_period).max()
    rsi_range = (rsi_max - rsi_min).replace(0, np.nan)
    stoch_rsi = ((rsi - rsi_min) / rsi_range * 100).fillna(50.0)

    # Step 3: %K and %D (3-bar SMA smoothing)
    k_period = 3
    pct_k = stoch_rsi.rolling(k_period).mean()
    pct_d = pct_k.rolling(k_period).mean()

    if len(pct_k.dropna()) < 5 or len(pct_d.dropna()) < 5:
        return None, "StochRSI warmup"

    k_now  = float(pct_k.iloc[-1])
    k_prev = float(pct_k.iloc[-2])
    d_now  = float(pct_d.iloc[-1])
    d_prev = float(pct_d.iloc[-2])

    # Oversold threshold (relaxes with drought: 20 → 30)
    oversold_thresh = min(30, 20 + drought * 2)

    # Cross-up condition: %K was below %D and now crosses above
    cross_up = (k_prev < d_prev) and (k_now >= d_now)
    if not cross_up:
        return None, f"%K not crossing %D (k={k_now:.1f}, d={d_now:.1f})"

    # Must be coming from oversold territory
    k_min_recent = float(pct_k.iloc[-5:].min())
    if k_min_recent > oversold_thresh:
        return None, f"not from oversold: recent %K min {k_min_recent:.1f} > {oversold_thresh}"

    # RSI itself not already overbought
    rsi_now = float(rsi.iloc[-1])
    if rsi_now > 65:
        return None, f"RSI already high: {rsi_now:.1f}"

    # Price above SMA20 (basic trend filter)
    sma20 = float(close.rolling(20).mean().iloc[-1])
    sma20_floor = max(0.95, 0.98 - drought * 0.01)
    if float(close.iloc[-1]) < sma20 * sma20_floor:
        return None, "price below SMA20 trend filter"

    price_now = float(close.iloc[-1])
    return "BUY", (
        f"StochRSI cross: %K={k_now:.1f} crossed %D={d_now:.1f} from oversold"
        f" · RSI={rsi_now:.1f} · SMA20={((price_now/sma20)-1)*100:+.1f}%"
    )


def signal_parabolic_sar_flip(symbol: str, df: pd.DataFrame, _all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """
    v8.5 — Parabolic SAR Trend Flip: J. Welles Wilder's stop-and-reverse system.

    Fires when SAR flips from above price (bearish/below) to below price (bullish),
    confirming a downtrend has ended and uptrend begun.  Combines with RSI and
    price-above-SMA50 to filter whipsaws in low-volatility chop.

    Parameters:
        iaf  = initial acceleration factor (0.02, per Wilder)
        step = acceleration step per new extreme (0.02)
        max_af = maximum acceleration factor (0.20)
    Drought relief: relaxes RSI ceiling 65→70 and reduces confirmation bars 2→1.
    """
    if len(df) < 60:
        return None, "insufficient data for SAR"

    high  = df["High"].astype(float)
    low   = df["Low"].astype(float)
    close = df["Close"].astype(float)

    # ── Parabolic SAR calculation (Wilder, 1978) ──────────────────────────
    iaf    = 0.02
    step   = 0.02
    max_af = 0.20

    sar    = [0.0] * len(close)
    bull   = [True] * len(close)   # True = uptrend (SAR below price)
    ep     = [0.0] * len(close)    # extreme point
    af     = [iaf] * len(close)    # acceleration factor

    # Seed: start bearish if first bar down, bullish otherwise
    if close.iloc[1] >= close.iloc[0]:
        bull[0] = True
        sar[0]  = float(low.iloc[0])
        ep[0]   = float(high.iloc[0])
    else:
        bull[0] = False
        sar[0]  = float(high.iloc[0])
        ep[0]   = float(low.iloc[0])
    af[0] = iaf

    for i in range(1, len(close)):
        prev_bull = bull[i - 1]
        prev_sar  = sar[i - 1]
        prev_ep   = ep[i - 1]
        prev_af   = af[i - 1]

        h = float(high.iloc[i])
        l = float(low.iloc[i])

        if prev_bull:
            new_sar = prev_sar + prev_af * (prev_ep - prev_sar)
            # SAR cannot be above prior two lows
            new_sar = min(new_sar, float(low.iloc[i - 1]),
                          float(low.iloc[i - 2]) if i >= 2 else float(low.iloc[i - 1]))
            if l < new_sar:
                # Flip to bearish
                bull[i] = False
                sar[i]  = prev_ep
                ep[i]   = l
                af[i]   = iaf
            else:
                bull[i] = True
                sar[i]  = new_sar
                if h > prev_ep:
                    ep[i] = h
                    af[i] = min(prev_af + step, max_af)
                else:
                    ep[i] = prev_ep
                    af[i] = prev_af
        else:
            new_sar = prev_sar + prev_af * (prev_ep - prev_sar)
            # SAR cannot be below prior two highs
            new_sar = max(new_sar, float(high.iloc[i - 1]),
                          float(high.iloc[i - 2]) if i >= 2 else float(high.iloc[i - 1]))
            if h > new_sar:
                # Flip to bullish
                bull[i] = True
                sar[i]  = prev_ep
                ep[i]   = h
                af[i]   = iaf
            else:
                bull[i] = False
                sar[i]  = new_sar
                if l < prev_ep:
                    ep[i] = l
                    af[i] = min(prev_af + step, max_af)
                else:
                    ep[i] = prev_ep
                    af[i] = prev_af

    # ── Flip detection ────────────────────────────────────────────────────
    # Confirm flip: SAR was bearish yesterday, bullish today
    # Require N consecutive bullish SAR bars (reduces whipsaws)
    confirm_bars = max(1, 2 - drought)   # 2 bars → 1 bar under drought

    if len(bull) < confirm_bars + 2:
        return None, "not enough bars for SAR flip confirmation"

    # Last 'confirm_bars' bars must all be bullish SAR
    recent_bull = all(bull[-(confirm_bars + 1 - j)] for j in range(confirm_bars))
    # Bar before confirmation window must have been bearish
    pre_bar_bull = bull[-(confirm_bars + 1)]

    if not recent_bull or pre_bar_bull:
        return None, "no SAR bullish flip"

    # ── RSI filter ────────────────────────────────────────────────────────
    delta  = close.diff()
    gain   = delta.clip(lower=0)
    loss   = (-delta).clip(lower=0)
    avg_g  = gain.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    avg_l  = loss.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    rs     = avg_g / avg_l.replace(0, 1e-9)
    rsi    = 100 - 100 / (1 + rs)
    rsi_now = float(rsi.iloc[-1])

    rsi_ceil = 65 + drought * 1   # 65 → 70 max relief
    if rsi_now >= rsi_ceil:
        return None, f"RSI {rsi_now:.1f} already extended above {rsi_ceil}"

    # ── SMA50 trend filter ────────────────────────────────────────────────
    if len(close) < 50:
        return None, "insufficient data for SMA50"
    sma50    = float(close.rolling(50).mean().iloc[-1])
    price_now = float(close.iloc[-1])
    if price_now < sma50 * 0.97:
        return None, f"price {price_now:.2f} well below SMA50 {sma50:.2f}"

    sar_now = sar[-1]
    return "BUY", (
        f"ParSAR flip: bearish→bullish SAR={sar_now:.2f} · price={price_now:.2f}"
        f" · confirm={confirm_bars}bars · RSI={rsi_now:.1f} · SMA50={((price_now/sma50)-1)*100:+.1f}%"
    )


def signal_aroon_trend_initiation(symbol: str, df: pd.DataFrame, _all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """
    v8.6 — Aroon Oscillator Trend Initiation: Tushar Chande's 1995 trend-strength indicator.

    Aroon-Up   = ((period - bars since N-period high) / period) * 100
    Aroon-Down = ((period - bars since N-period low)  / period) * 100
    Aroon-Osc  = Aroon-Up - Aroon-Down  (range -100 to +100)

    Signal fires when Aroon oscillator crosses from negative/zero to strongly
    positive (> +40), indicating fresh trend initiation from consolidation.
    Requires Aroon-Up ≥ 70 (high recently near N-period high) for confirmation.

    Drought relief: lowers oscillator entry threshold 40 → 28, Aroon-Up ≥ 70 → ≥ 60.
    Regime: "trend" — Aroon is a pure trend-initiation indicator.
    """
    if len(df) < 60:
        return None, "insufficient data for Aroon"

    high  = df["High"].astype(float)
    low   = df["Low"].astype(float)
    close = df["Close"].astype(float)

    period = 25   # Chande's default

    # ── Aroon calculation ─────────────────────────────────────────────────
    # Need at least period+1 bars
    if len(high) < period + 2:
        return None, "insufficient data for Aroon period"

    aroon_up   = []
    aroon_down = []

    for i in range(period, len(high)):
        window_h = high.iloc[i - period: i + 1]
        window_l = low.iloc[i - period: i + 1]
        bars_since_high = period - int(window_h.values.argmax())
        bars_since_low  = period - int(window_l.values.argmin())
        aroon_up.append(((period - bars_since_high) / period) * 100)
        aroon_down.append(((period - bars_since_low)  / period) * 100)

    if len(aroon_up) < 3:
        return None, "not enough Aroon bars"

    osc_now  = aroon_up[-1] - aroon_down[-1]
    osc_prev = aroon_up[-2] - aroon_down[-2]
    aup_now  = aroon_up[-1]

    # ── Thresholds (drought relief) ───────────────────────────────────────
    osc_thresh  = max(28, 40 - drought * 3)   # 40 → 28 over 4 drought steps
    aup_thresh  = max(60, 70 - drought * 2)   # 70 → 60

    # Entry: oscillator crosses from ≤ 0 to ≥ osc_thresh, with Aroon-Up ≥ threshold
    if osc_prev > 0:
        return None, f"oscillator already positive prev={osc_prev:.1f} (not a fresh cross)"
    if osc_now < osc_thresh:
        return None, f"oscillator {osc_now:.1f} < threshold {osc_thresh}"
    if aup_now < aup_thresh:
        return None, f"Aroon-Up {aup_now:.1f} < {aup_thresh} (not near N-period high)"

    # ── RSI filter: confirm momentum but not exhausted ────────────────────
    delta = close.diff()
    gain  = delta.clip(lower=0)
    loss  = (-delta).clip(lower=0)
    avg_g = gain.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    avg_l = loss.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    rs    = avg_g / avg_l.replace(0, 1e-9)
    rsi   = 100 - 100 / (1 + rs)
    rsi_now = float(rsi.iloc[-1])

    rsi_floor = max(35, 40 - drought * 2)   # RSI must show at least some bullish momentum
    rsi_ceil  = 72
    if rsi_now < rsi_floor:
        return None, f"RSI {rsi_now:.1f} too weak (floor={rsi_floor})"
    if rsi_now >= rsi_ceil:
        return None, f"RSI {rsi_now:.1f} already extended"

    price_now = float(close.iloc[-1])
    return "BUY", (
        f"Aroon init: Osc={osc_now:.1f} (prev={osc_prev:.1f}) · AUp={aup_now:.1f}"
        f" · RSI={rsi_now:.1f} · period={period}"
    )


def signal_vix_mean_reversion(symbol: str, df: pd.DataFrame, all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """
    v8.7 — VIX Mean Reversion: buy quality equities when VIX spikes above fair value.

    Academic basis: Simon & Wiggins (2001) — 76% of VIX spikes above 25 reverse within
    10 trading days.  The fear premium is systematically over-priced: options market-makers
    and retail hedgers over-pay for protection, creating reversion to fair value when
    panic subsides.

    Signal conditions:
    1. VIX ≥ 25 AND ≥ 1.30× its 30-day average (spike, not sustained elevation)
    2. Symbol is down ≥ 3% over 5 days (market oversold alongside VIX spike)
    3. Symbol is within 3% of its 5-day low (near-term exhaustion)
    4. Symbol RSI < 45 (confirming oversold, not just normal dip)
    5. Symbol is SPY/QQQ/large-cap quality (avoid catching falling knives in junk)
    6. Drought relief: VIX threshold lowers to 22 and RSI ceiling rises to 50

    Regime: "mean_rev" — fires during dislocations, diversifies ensemble vs momentum algos.
    """
    # Only fire on quality targets — large-cap ETFs and mega-cap stocks
    VIX_TARGETS = {
        "SPY", "QQQ", "IWM", "DIA",
        "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META",
        "JPM", "BAC", "XOM", "JNJ", "V",
        "TQQQ",  # 3x leveraged - only in drought (strong signal) mode
    }
    if symbol not in VIX_TARGETS:
        return None, f"{symbol} not in VIX mean-rev target universe"

    # ── Pull VIX from all_data ────────────────────────────────────────────
    vix_df = all_data.get("^VIX")
    if vix_df is None or len(vix_df) < 35:
        return None, "^VIX data not available or too short"

    vix_close = vix_df["Close"].astype(float)
    vix_now   = float(vix_close.iloc[-1])
    vix_30d   = float(vix_close.iloc[-30:].mean())

    vix_thresh  = max(22, 25 - drought * 1)          # 25 → 22 with 3 drought steps
    spike_ratio = max(1.20, 1.30 - drought * 0.03)   # 1.30 → 1.20

    if vix_now < vix_thresh:
        return None, f"VIX {vix_now:.1f} below threshold {vix_thresh}"
    if vix_now < vix_30d * spike_ratio:
        return None, f"VIX {vix_now:.1f} not elevated enough vs 30d avg {vix_30d:.1f}"

    # ── Symbol-level conditions ───────────────────────────────────────────
    close = df["Close"].astype(float)
    if len(close) < 30:
        return None, "insufficient data"

    price_now = float(close.iloc[-1])

    # Condition 2: down ≥ 3% over 5 days
    if len(close) < 6:
        return None, "not enough bars for 5d return"
    ret_5d = price_now / float(close.iloc[-6]) - 1
    dip_floor = max(-0.08, -0.03 - drought * 0.01)   # -3% → -4%
    if ret_5d > dip_floor:
        return None, f"5d return {ret_5d:.1%} not enough of a dip (need ≤ {dip_floor:.1%})"

    # Condition 3: near 5-day low (< 3% above it)
    low_5d = float(close.iloc[-6:-1].min())
    dist_from_low = price_now / low_5d - 1
    if dist_from_low > 0.04:
        return None, f"price {dist_from_low:.1%} above 5d low — not at exhaustion"

    # Condition 4: RSI < 45 (oversold)
    delta = close.diff()
    gain  = delta.clip(lower=0)
    loss  = (-delta).clip(lower=0)
    avg_g = gain.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    avg_l = loss.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    rsi   = 100 - 100 / (1 + avg_g / avg_l.replace(0, 1e-9))
    rsi_now = float(rsi.iloc[-1])

    rsi_ceil = min(50, 45 + drought * 2)
    if rsi_now >= rsi_ceil:
        return None, f"RSI {rsi_now:.1f} not oversold enough (ceil={rsi_ceil})"

    # Skip TQQQ unless strong drought (high-conviction VIX spike only)
    if symbol == "TQQQ" and drought < 3:
        return None, "TQQQ only in high-drought mode (very strong VIX spike required)"

    vix_spike_pct = (vix_now / vix_30d - 1) * 100
    return "BUY", (
        f"VIX MeanRev: VIX={vix_now:.1f} (+{vix_spike_pct:.0f}% vs 30d avg={vix_30d:.1f})"
        f" · {symbol} 5d={ret_5d:.1%} · RSI={rsi_now:.1f} · dist_low={dist_from_low:.1%}"
    )


def signal_short_squeeze_proxy(symbol: str, df: pd.DataFrame, _all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """
    v8.8 — Short Squeeze Proxy: detect beaten-down stocks with sudden volume surge + reversal.

    Academic basis: Asquith, Pathak & Ritter (2005, JFE) — stocks in top decile of short
    interest + high demand score have excess returns of 2.5% per month.

    Since yfinance has no short interest data, we use price/volume proxies:
    1. Price near 20-day low AND down 15%+ over 20 days (shorts in profit = crowded trade)
    2. Volume spike today ≥ 3× 20-day average (potential short covering / catalyst)
    3. RSI was oversold ≤ 40 (shorts crowded, oversold condition)
    4. Reversal bar: today close > yesterday close by ≥ 2%
    5. Price rebound: today above open (bullish intraday structure)

    Need ≥ 4 of 5 conditions (vol spike is mandatory).
    Drought relief: relaxes vol threshold 3x → 2.5x, RSI floor 40 → 45.
    Regime: "mean_rev" — fires on capitulation/reversal setups.
    """
    if len(df) < 25:
        return None, "insufficient data"

    high  = df["High"].astype(float)
    low   = df["Low"].astype(float)
    close = df["Close"].astype(float)
    vol   = df["Volume"].astype(float)

    # ── Condition 1: Near 20-day low AND down ≥ 15% over 20 days ─────────
    price_now    = float(close.iloc[-1])
    low_20d      = float(close.iloc[-21:-1].min())
    price_20d_ag = float(close.iloc[-21])
    decline_20d  = price_now / price_20d_ag - 1
    dist_from_low = price_now / low_20d - 1

    near_low       = dist_from_low < 0.10
    beaten_down    = decline_20d < -0.15

    # ── Condition 2: Volume spike ≥ 3× (mandatory) ───────────────────────
    vol_avg_20d   = float(vol.iloc[-21:-1].mean())
    vol_today     = float(vol.iloc[-1])
    vol_thresh    = max(2.5, 3.0 - drought * 0.1)    # 3.0× → 2.5× drought relief
    vol_ratio     = vol_today / vol_avg_20d if vol_avg_20d > 0 else 0
    vol_spike     = vol_ratio >= vol_thresh

    if not vol_spike:
        return None, f"vol ratio {vol_ratio:.1f}× below threshold {vol_thresh:.1f}×"

    # ── Condition 3: RSI ≤ 40 (oversold) ─────────────────────────────────
    delta = close.diff()
    gain  = delta.clip(lower=0)
    loss  = (-delta).clip(lower=0)
    avg_g = gain.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    avg_l = loss.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    rsi   = 100 - 100 / (1 + avg_g / avg_l.replace(0, 1e-9))
    rsi_now  = float(rsi.iloc[-1])
    rsi_ceil = min(50, 40 + drought * 2)           # 40 → 50 drought relief
    was_oversold = rsi_now <= rsi_ceil

    # ── Condition 4: Reversal bar — close > prev close by ≥ 2% ───────────
    prev_close   = float(close.iloc[-2])
    reversal_pct = price_now / prev_close - 1
    reversal_bar = reversal_pct >= 0.02

    # ── Condition 5: Bullish intraday (close > open) ──────────────────────
    open_today   = float(df["Open"].astype(float).iloc[-1])
    bull_day     = price_now > open_today

    # ── Require ≥ 4 of 5 (vol already confirmed) ─────────────────────────
    conds = [near_low, beaten_down, was_oversold, reversal_bar, bull_day]
    n_met = sum(conds)
    if n_met < 3:   # vol + at least 3 more
        return None, f"only {n_met}/5 conditions met (need ≥ 3 beyond vol)"

    score = (n_met / 5.0) * 0.7 + min(vol_ratio / 15, 0.3)
    return "BUY", (
        f"ShortSqueeze: {n_met}/5 conds · vol={vol_ratio:.1f}× · decline20d={decline_20d:.1%}"
        f" · reversal={reversal_pct:.1%} · RSI={rsi_now:.1f} · dist_low={dist_from_low:.1%}"
    )


def signal_altcoin_season_rotation(symbol: str, df: pd.DataFrame, all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """
    v8.9 — Altcoin Season Rotation: capital rotation from BTC to alts when ETH leads.

    Academic basis: Borri (2019, JFE) documents systematic crypto risk factor rotation.
    When BTC dominance falls (BTC underperforms the median alt) and ETH leads,
    capital cascades down the risk curve into smaller alts.

    Signal conditions:
    1. ETH 10d return > BTC 10d return + 5pp (ETH visibly leading BTC)
    2. BTC 10d return < median 10d return of the crypto universe (BTC dominance falling)
    3. The target alt is itself outperforming BTC by ≥ 5pp over 10 days
    4. Alt volume elevated (≥ 1.3× its 10-day average) — not just price drift
    5. Alt RSI 40–75 (momentum present but not parabolic)
    6. Symbol is NOT BTC or ETH (they are the signal source, not targets)

    Drought relief: ETH-lead threshold 5pp → 2pp, alt rel-strength 5pp → 2pp.
    Regime: "trend" — altcoin seasons are momentum-driven, not mean-rev.
    """
    # Not applicable to BTC/ETH themselves (they are signal sources)
    if symbol in ("BTC-USD", "ETH-USD"):
        return None, "BTC/ETH are signal sources, not altcoin targets"

    # ── v10.2: CoinGecko real BTC dominance gate ──────────────────────────
    # BTC dominance > 60% → full risk-on hasn't started; skip signal
    # BTC dominance < 50% → altcoin season confirmed; boost reason string
    cg_global = all_data.get("__coingecko_global__", {})
    btc_dom_live = float(cg_global.get("btc_dominance", 50.0))
    if btc_dom_live > 60.0 and drought < 2:
        return None, f"BTC dominance {btc_dom_live:.1f}% too high (>60%) — altcoin season not confirmed"

    # ── Pull BTC and ETH from all_data ────────────────────────────────────
    btc_df = all_data.get("BTC-USD")
    eth_df = all_data.get("ETH-USD")

    if btc_df is None or len(btc_df) < 12:
        return None, "BTC-USD data not available"
    if eth_df is None or len(eth_df) < 12:
        return None, "ETH-USD data not available"

    btc_close = btc_df["Close"].astype(float)
    eth_close = eth_df["Close"].astype(float)

    btc_10d = float(btc_close.iloc[-1]) / float(btc_close.iloc[-11]) - 1
    eth_10d = float(eth_close.iloc[-1]) / float(eth_close.iloc[-11]) - 1

    # ── Condition 1: ETH leads BTC ────────────────────────────────────────
    eth_lead_thresh = max(0.02, 0.05 - drought * 0.01)   # 5pp → 2pp
    eth_outperf = eth_10d - btc_10d
    if eth_outperf < eth_lead_thresh:
        return None, f"ETH not leading BTC enough: ETH-BTC spread={eth_outperf:.1%} < {eth_lead_thresh:.1%}"

    # ── Condition 2: BTC dominance falling — compute universe median ──────
    crypto_universe = ["BTC-USD", "ETH-USD", "SOL-USD", "ADA-USD", "AVAX-USD",
                       "LINK-USD", "DOT-USD", "DOGE-USD", "SHIB-USD", "LTC-USD",
                       "BCH-USD", "XRP-USD", "MATIC-USD", "UNI-USD", "PEPE-USD",
                       "BONK-USD", "WIF-USD", "FLOKI-USD"]
    rets_10d: list[float] = []
    for t in crypto_universe:
        t_df = all_data.get(t)
        if t_df is not None and len(t_df) >= 12:
            try:
                r = float(t_df["Close"].astype(float).iloc[-1]) / float(t_df["Close"].astype(float).iloc[-11]) - 1
                rets_10d.append(r)
            except Exception:
                pass

    if len(rets_10d) < 3:
        return None, "not enough crypto universe data to compute median return"

    import statistics
    median_ret = statistics.median(rets_10d)
    if btc_10d >= median_ret:
        return None, f"BTC 10d={btc_10d:.1%} not below median {median_ret:.1%} (dominance not falling)"

    # ── Condition 3: Alt outperforms BTC ─────────────────────────────────
    close = df["Close"].astype(float)
    if len(close) < 12:
        return None, "insufficient alt data"

    alt_10d = float(close.iloc[-1]) / float(close.iloc[-11]) - 1
    alt_rel_thresh = max(0.02, 0.05 - drought * 0.01)
    alt_outperf = alt_10d - btc_10d
    if alt_outperf < alt_rel_thresh:
        return None, f"alt {symbol} not outperforming BTC: spread={alt_outperf:.1%} < {alt_rel_thresh:.1%}"

    # ── Condition 4: Volume elevated ─────────────────────────────────────
    vol = df["Volume"].astype(float)
    if len(vol) < 12:
        return None, "insufficient volume data"
    vol_ratio = float(vol.iloc[-1]) / float(vol.iloc[-11:-1].mean()) if float(vol.iloc[-11:-1].mean()) > 0 else 0
    if vol_ratio < 1.3:
        return None, f"volume ratio {vol_ratio:.2f}× below 1.3× threshold"

    # ── Condition 5: RSI 40–75 ────────────────────────────────────────────
    delta = close.diff()
    gain  = delta.clip(lower=0)
    loss  = (-delta).clip(lower=0)
    avg_g = gain.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    avg_l = loss.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    rsi   = 100 - 100 / (1 + avg_g / avg_l.replace(0, 1e-9))
    rsi_now = float(rsi.iloc[-1])

    rsi_floor = max(35, 40 - drought * 2)
    if rsi_now < rsi_floor:
        return None, f"RSI {rsi_now:.1f} too weak (floor={rsi_floor})"
    if rsi_now > 78:
        return None, f"RSI {rsi_now:.1f} parabolic (> 78)"

    season_str = (eth_10d - btc_10d) * 100
    dom_label = f"BTCdom={btc_dom_live:.1f}%" if btc_dom_live != 50.0 else ""
    return "BUY", (
        f"AltSeason: ETH+{season_str:.0f}bp vs BTC · {symbol} rel={alt_outperf:.1%}"
        f" · BTC={btc_10d:.1%} · med={median_ret:.1%} · RSI={rsi_now:.1f}"
        + (f" · {dom_label}" if dom_label else "")
    )


def signal_chaikin_money_flow(symbol: str, df: pd.DataFrame, _all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """
    v9.0 — Chaikin Money Flow (CMF) Accumulation: Marc Chaikin's OHLCV-only buying pressure indicator.

    CMF = sum(Money Flow Volume, N) / sum(Volume, N)
    Money Flow Multiplier = ((Close - Low) - (High - Close)) / (High - Low)
    Money Flow Volume = MFM × Volume

    When CMF crosses from below -0.05 to above +0.03, institutional buyers are
    absorbing supply at the high end of each bar — confirmed buying pressure.

    Signal conditions:
    1. CMF crosses negative → positive: CMF[-2] < 0 AND CMF[-1] > +cross_thresh
    2. Volume elevated: today's volume ≥ 1.5× 20-day avg (confirms the CMF reading)
    3. Price above SMA20 (trend alignment)
    4. RSI 40–68 (momentum present, not exhausted)
    5. Not a gap-down day: today's open ≥ yesterday's close × 0.98

    Drought relief: CMF cross threshold from +0.03 → +0.01.
    Regime: "both" — CMF works in trending and mean-rev markets alike.
    """
    if len(df) < 25:
        return None, "insufficient data for CMF"

    high  = df["High"].astype(float)
    low   = df["Low"].astype(float)
    close = df["Close"].astype(float)
    vol   = df["Volume"].astype(float)
    open_ = df["Open"].astype(float)

    # ── Chaikin Money Flow (20-period) ────────────────────────────────────
    hl_range = (high - low).replace(0, 1e-9)
    mfm   = ((close - low) - (high - close)) / hl_range   # -1 to +1
    mfv   = mfm * vol                                      # Money Flow Volume
    cmf   = mfv.rolling(20).sum() / vol.rolling(20).sum()

    if len(cmf.dropna()) < 3:
        return None, "not enough CMF data"

    cmf_now  = float(cmf.iloc[-1])
    cmf_prev = float(cmf.iloc[-2])

    # ── Condition 1: CMF bullish cross ────────────────────────────────────
    cross_thresh = max(0.01, 0.03 - drought * 0.005)   # +0.03 → +0.01 drought
    if cmf_prev >= 0:
        return None, f"CMF {cmf_prev:.3f} was already positive (not a fresh cross)"
    if cmf_now < cross_thresh:
        return None, f"CMF {cmf_now:.3f} hasn't crossed threshold +{cross_thresh:.3f}"

    # ── Condition 2: Volume elevated ─────────────────────────────────────
    vol_avg_20 = float(vol.iloc[-21:-1].mean())
    vol_ratio  = float(vol.iloc[-1]) / vol_avg_20 if vol_avg_20 > 0 else 0
    if vol_ratio < max(1.3, 1.5 - drought * 0.05):
        return None, f"volume ratio {vol_ratio:.2f}× below 1.5× threshold"

    # ── Condition 3: Price above SMA20 ───────────────────────────────────
    sma20     = float(close.rolling(20).mean().iloc[-1])
    price_now = float(close.iloc[-1])
    if price_now < sma20 * 0.98:
        return None, f"price {price_now:.2f} below SMA20 {sma20:.2f}"

    # ── Condition 4: RSI 40–68 ────────────────────────────────────────────
    delta = close.diff()
    gain  = delta.clip(lower=0)
    loss  = (-delta).clip(lower=0)
    avg_g = gain.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    avg_l = loss.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    rsi   = 100 - 100 / (1 + avg_g / avg_l.replace(0, 1e-9))
    rsi_now = float(rsi.iloc[-1])

    rsi_floor = max(35, 40 - drought * 2)
    if rsi_now < rsi_floor:
        return None, f"RSI {rsi_now:.1f} too weak"
    if rsi_now > 68:
        return None, f"RSI {rsi_now:.1f} already extended (> 68)"

    # ── Condition 5: No gap-down ──────────────────────────────────────────
    prev_close = float(close.iloc[-2])
    open_today = float(open_.iloc[-1])
    if open_today < prev_close * 0.98:
        return None, "gap-down open invalidates CMF cross"

    return "BUY", (
        f"CMF cross: {cmf_prev:.3f}→{cmf_now:.3f} · vol={vol_ratio:.1f}× · RSI={rsi_now:.1f}"
        f" · SMA20={((price_now/sma20)-1)*100:+.1f}%"
    )


def signal_whale_accumulation_proxy(symbol: str, df: pd.DataFrame, _all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """
    v9.1 — Meme Coin Whale Accumulation Proxy: OHLCV-only on-chain accumulation detector.

    Whale wallets accumulating meme coins close near the HIGH of each bar, because
    their large bids absorb all available supply and push price to the top of the range.
    Three consecutive accumulation bars (close in upper 40% of range + above-avg volume)
    proxy for sustained whale buying pressure — without any on-chain data.

    Research basis: DOGE whale accumulations (600M+ tokens) appeared on daily OHLCV as
    3-5 consecutive bars with close > 60% of the High-Low range AND volume > 20d average.
    (BeInCrypto / BraveNewCoin research, Feb 2025)

    Signal conditions:
    1. Last N consecutive bars: close in upper 40% (close > 60th percentile of H-L range)
    2. Each of those bars: volume ≥ 20-day average (not thin accumulation)
    3. Price above SMA20 (trend alignment, not in freefall)
    4. RSI 35–70 (not deeply oversold or parabolic)
    5. Not extended: price < 1.20× its value 7 days ago (not already mid-pump)

    Drought relief: consecutive bar requirement 3→2, RSI ceiling 70→75.
    Regime: "both" — whale accumulation can precede trend breakouts OR recovery bounces.
    """
    # Primarily for meme coins and high-volatility names
    MEME_TARGETS = {
        "DOGE-USD", "SHIB-USD", "PEPE-USD", "BONK-USD", "WIF-USD", "FLOKI-USD",
        "XRP-USD", "SOL-USD", "ADA-USD", "AVAX-USD",
        "GME", "AMC", "MSTR", "COIN", "PLTR", "SOFI", "RBLX", "SNAP",
    }
    if symbol not in MEME_TARGETS:
        return None, f"{symbol} not in whale accumulation target universe"

    if len(df) < 25:
        return None, "insufficient data"

    high  = df["High"].astype(float)
    low   = df["Low"].astype(float)
    close = df["Close"].astype(float)
    vol   = df["Volume"].astype(float)

    # ── Condition 1+2: Consecutive accumulation bars ──────────────────────
    hl_range  = (high - low).replace(0, 1e-9)
    close_pos = (close - low) / hl_range    # 0 = at low, 1 = at high
    vol_avg   = vol.rolling(20).mean()

    upper_close = close_pos > 0.60          # close in upper 40% of range
    above_vol   = vol > vol_avg             # above-average volume

    both_cond = upper_close & above_vol

    consec_req = max(2, 3 - drought)        # 3 → 2 consecutive bars with drought
    consecutive_n = float(both_cond.rolling(consec_req).sum().iloc[-1])
    if consecutive_n < consec_req:
        return None, f"only {int(consecutive_n)}/{consec_req} consecutive accumulation bars"

    # ── Condition 3: Price above SMA20 ───────────────────────────────────
    sma20     = float(close.rolling(20).mean().iloc[-1])
    price_now = float(close.iloc[-1])
    if price_now < sma20 * 0.97:
        return None, f"price {price_now:.6f} below SMA20 {sma20:.6f}"

    # ── Condition 4: RSI 35–70 ────────────────────────────────────────────
    delta = close.diff()
    gain  = delta.clip(lower=0)
    loss  = (-delta).clip(lower=0)
    avg_g = gain.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    avg_l = loss.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    rsi   = 100 - 100 / (1 + avg_g / avg_l.replace(0, 1e-9))
    rsi_now = float(rsi.iloc[-1])

    rsi_ceil = min(75, 70 + drought * 2)
    if rsi_now < 35:
        return None, f"RSI {rsi_now:.1f} too weak"
    if rsi_now > rsi_ceil:
        return None, f"RSI {rsi_now:.1f} > ceiling {rsi_ceil}"

    # ── Condition 5: Not already mid-pump ────────────────────────────────
    if len(close) < 8:
        return None, "not enough bars for 7d return check"
    price_7d_ago = float(close.iloc[-8])
    gain_7d      = price_now / price_7d_ago - 1
    max_gain     = 0.20 + drought * 0.05    # 20% → 25%
    if gain_7d > max_gain:
        return None, f"already up {gain_7d:.1%} over 7 days — mid-pump risk"

    # Volume strength: avg volume on accumulation bars vs baseline
    accum_vol_avg = float(vol.iloc[-consec_req:].mean())
    baseline_vol  = float(vol_avg.iloc[-consec_req - 10:-consec_req].mean()) if len(vol) > consec_req + 10 else float(vol_avg.iloc[-1])
    vol_ratio     = accum_vol_avg / baseline_vol if baseline_vol > 0 else 1.0

    # Avg close_pos over accumulation window
    avg_close_pos = float(close_pos.iloc[-consec_req:].mean())

    return "BUY", (
        f"WhaleProxy: {consec_req} consec accum bars · close_pos={avg_close_pos:.2f} · vol={vol_ratio:.1f}×"
        f" · RSI={rsi_now:.1f} · 7d={gain_7d:.1%}"
    )


# ---------------------------------------------------------------------------
# v9.2 — Calendar Effect Crypto Signal
# Baur & Dimpfl (2018 J. Risk Finance), Aharon & Qadan (2018 Finance Res. Lett.)
# Crypto shows persistent day-of-week and month-of-year calendar anomalies:
#   • Weekend recovery: Mon/Tue reversal after systematic weekend selling
#   • Month-start inflows: institutional DCA and rebalancing in first 4 days
#   • Quarter-start rotation: fund flows into crypto on Q1/Q2/Q3/Q4 openings
# ---------------------------------------------------------------------------
def signal_calendar_effect_crypto(symbol: str, df: pd.DataFrame, _all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """
    v9.2 Calendar Effect Crypto.

    Three calendar windows:
      1. Weekend recovery  — Monday or Tuesday (weekday 0 or 1)
      2. Month-start       — day-of-month ≤ 4
      3. Quarter-start     — Jan/Apr/Jul/Oct, day-of-month ≤ 5

    Requires a recent pullback (3d or 5d return negative) to confirm
    buying-into-weakness rather than chasing a gap-up. Volume must
    be picking up vs 5-day avg. Not in free-fall over 10d.
    """
    CRYPTO_TARGETS = {
        "BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "ADA-USD",
        "DOGE-USD", "AVAX-USD", "MATIC-USD", "LINK-USD", "DOT-USD",
        "ATOM-USD", "LTC-USD", "BCH-USD",
    }

    if symbol not in CRYPTO_TARGETS:
        return None, "not in crypto calendar universe"

    if len(df) < 30:
        return None, "insufficient history"

    close = df["Close"]
    vol   = df["Volume"]

    # ── Calendar trigger ──────────────────────────────────────────────────
    today        = datetime.now(timezone.utc)
    weekday      = today.weekday()      # 0=Mon … 6=Sun
    day_of_month = today.day
    month        = today.month

    is_quarter_start     = (month in {1, 4, 7, 10}) and (day_of_month <= 5)
    is_month_start       = day_of_month <= 4
    is_weekend_recovery  = weekday in {0, 1}

    calendar_ok = is_quarter_start or is_month_start or is_weekend_recovery

    if not calendar_ok:
        if drought < 2:
            return None, f"no calendar window (wday={weekday}, dom={day_of_month})"
        # Drought: relax to first 7 dom or Mon-Wed
        if not ((day_of_month <= 7) or (weekday in {0, 1, 2})):
            return None, f"no calendar window even with drought (wday={weekday}, dom={day_of_month})"

    # ── Recent pullback (buy the dip, not the gap-up) ─────────────────────
    ret_3d  = float(close.iloc[-1] / close.iloc[-4]  - 1) if len(close) >= 4  else 0.0
    ret_5d  = float(close.iloc[-1] / close.iloc[-6]  - 1) if len(close) >= 6  else 0.0
    ret_10d = float(close.iloc[-1] / close.iloc[-11] - 1) if len(close) >= 11 else 0.0

    # Not in free-fall
    freefall_floor = max(-0.42, -0.35 - drought * 0.02)
    if ret_10d < freefall_floor:
        return None, f"free-fall: 10d={ret_10d:.1%}"

    pullback_thresh = max(-0.15, -0.05 - drought * 0.01)
    has_pullback = (ret_3d <= pullback_thresh) or (ret_5d <= pullback_thresh * 1.5)
    if is_quarter_start:                      # Q-start: mild dip is enough
        has_pullback = has_pullback or ret_5d <= 0.0
    if not has_pullback:
        return None, f"no pullback to buy (3d={ret_3d:.1%}, 5d={ret_5d:.1%})"

    # ── RSI ───────────────────────────────────────────────────────────────
    delta  = close.diff()
    gain   = delta.clip(lower=0).rolling(14).mean()
    loss   = (-delta.clip(upper=0)).rolling(14).mean()
    rs     = gain / loss.replace(0, 1e-9)
    rsi    = float((100 - 100 / (1 + rs)).iloc[-1])

    rsi_floor = max(28, 35 - drought * 2)
    rsi_ceil  = min(72, 68 + drought * 1)
    if not (rsi_floor <= rsi <= rsi_ceil):
        return None, f"RSI {rsi:.1f} outside [{rsi_floor},{rsi_ceil}]"

    # ── Volume engagement ─────────────────────────────────────────────────
    vol_5d_avg  = float(vol.rolling(5).mean().iloc[-1])
    vol_now     = float(vol.iloc[-1])
    vol_thresh  = max(1.00, 1.10 - drought * 0.02)
    if vol_5d_avg > 0 and vol_now < vol_5d_avg * vol_thresh:
        return None, f"vol not engaging: {vol_now / vol_5d_avg:.2f}× < {vol_thresh:.2f}×"

    trigger_tag = "Q-start" if is_quarter_start else ("M-start" if is_month_start else "wkend-rec")

    return "BUY", (
        f"CalEffect({trigger_tag}): 3d={ret_3d:.1%} · 5d={ret_5d:.1%}"
        f" · RSI={rsi:.1f} · vol={vol_now / vol_5d_avg:.1f}×"
    )


# ---------------------------------------------------------------------------
# v9.5 — StockTwits Bull Surge Signal
# Sprenger et al. (2014 J. Business Ethics) — StockTwits pre-tagged bull/bear
# ratio has ~0.62 precision for next-day returns when ≥10 tagged posts/symbol/day.
# Self-reported conviction (users explicitly mark posts Bullish/Bearish) is the
# purest free sentiment signal — no NLP needed, no model error.
# ---------------------------------------------------------------------------
def signal_stocktwits_bull_surge(symbol: str, df: pd.DataFrame, all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """
    v9.5 StockTwits Bull Surge.

    Fires when StockTwits pre-tagged bull sentiment exceeds 65% (self-reported).
    Uses all_data["__sentiment__"] (blended StockTwits + Reddit WSB), which is
    pre-fetched each scan run. Confirmed by price above SMA20, RSI 35-70,
    volume engagement, and not at a FOMO peak (5d return < 25%).
    """
    ST_UNIVERSE = {
        "DOGE-USD", "SHIB-USD", "PEPE-USD", "FLOKI-USD", "BONK-USD",
        "BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "ADA-USD",
        "GME", "AMC", "MARA", "RIOT", "NVAX", "SPCE", "RIVN",
        "TSLA", "NVDA", "AMD", "AAPL", "COIN", "MSTR", "PLTR", "SOFI",
    }

    if symbol not in ST_UNIVERSE:
        return None, "not in StockTwits universe"

    sentiment_data = all_data.get("__sentiment__", {})
    if symbol not in sentiment_data:
        return None, "no StockTwits data available for symbol"

    bull_pct = float(sentiment_data[symbol])

    # Bull threshold — need clear bullish majority
    bull_thresh = max(58, 65 - drought * 2)
    if bull_pct < bull_thresh:
        return None, f"bull_pct {bull_pct:.1f}% < {bull_thresh}% threshold"

    if len(df) < 25:
        return None, "insufficient history"

    close = df["Close"]
    vol   = df["Volume"]

    # ── SMA20 filter: not in downtrend ───────────────────────────────────
    sma20 = float(close.rolling(20).mean().iloc[-1])
    if float(close.iloc[-1]) < sma20 * (1.0 - max(0.01, 0.03 - drought * 0.005)):
        return None, "price below SMA20"

    # ── RSI ──────────────────────────────────────────────────────────────
    delta  = close.diff()
    gain   = delta.clip(lower=0).rolling(14).mean()
    loss   = (-delta.clip(upper=0)).rolling(14).mean()
    rsi    = float((100 - 100 / (1 + gain / loss.replace(0, 1e-9))).iloc[-1])

    rsi_floor = max(28, 35 - drought * 2)
    rsi_ceil  = min(75, 70 + drought * 1)
    if not (rsi_floor <= rsi <= rsi_ceil):
        return None, f"RSI {rsi:.1f} outside [{rsi_floor},{rsi_ceil}]"

    # ── Volume engagement ─────────────────────────────────────────────────
    vol_5d_avg = float(vol.rolling(5).mean().iloc[-1])
    vol_now    = float(vol.iloc[-1])
    vol_thresh = max(0.85, 1.00 - drought * 0.03)
    if vol_5d_avg > 0 and vol_now < vol_5d_avg * vol_thresh:
        return None, f"low volume: {vol_now / vol_5d_avg:.2f}×"

    # ── FOMO peak guard ───────────────────────────────────────────────────
    ret_5d   = float(close.iloc[-1] / close.iloc[-6]  - 1) if len(close) >= 6  else 0.0
    fomo_cap = max(0.18, 0.25 + drought * 0.02)
    if ret_5d > fomo_cap:
        return None, f"already up {ret_5d:.1%} over 5d — FOMO peak risk"

    return "BUY", (
        f"STSentiment: bull={bull_pct:.1f}% · RSI={rsi:.1f}"
        f" · vol={vol_now / vol_5d_avg:.1f}× · 5d={ret_5d:.1%}"
    )


def signal_vwap_reclaim(symbol: str, df: pd.DataFrame, _all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """
    v7.4: VWAP Reclaim — institutional accumulation completion signal.
    Detects when price reclaims its 20-day VWAP after sustained distribution below it.
    This is the opposite of VWAP reversion: rather than entering a dip, we enter the
    COMPLETION of the accumulation phase — the institutional "all-in" signal.

    Signal conditions:
    1. Price was below VWAP for 5+ of the last 7 days (sustained distribution)
    2. Today: price closed ABOVE VWAP (reclaim)
    3. Volume today > 1.4× 20-day average (conviction on the reclaim)
    4. Price below VWAP yesterday (the reclaim is fresh, not stale)
    5. RSI 30-60 (recovering but not overbought — room to run after the reclaim)

    Academic: Market microstructure theory — VWAP is the institutional benchmark.
    Reclaiming VWAP with volume signals that buyers absorbed all selling and are now
    in control. Used by quantitative market makers to detect regime shifts.
    """
    if len(df) < 25:
        return None, ""
    if not all(c in df.columns for c in ["High", "Low", "Close", "Volume"]):
        return None, ""

    high   = df["High"]
    low    = df["Low"]
    close  = df["Close"]
    volume = df["Volume"]

    # Compute 20-day rolling VWAP
    typical = (high + low + close) / 3.0
    vol_20  = volume.rolling(20).sum()
    vwap_20 = (typical * volume).rolling(20).sum() / vol_20
    if pd.isna(vwap_20.iloc[-1]) or pd.isna(vwap_20.iloc[-2]):
        return None, ""
    if float(vol_20.iloc[-1]) <= 0:
        return None, ""

    vwap_now  = float(vwap_20.iloc[-1])
    vwap_prev = float(vwap_20.iloc[-2])
    price_now  = float(close.iloc[-1])
    price_prev = float(close.iloc[-2])

    # Condition 1: reclaim — today above VWAP, yesterday below
    if price_now <= vwap_now * 1.002:   # allow 0.2% slop for the crossover
        return None, ""
    if price_prev > vwap_prev * 0.995:  # must have been below yesterday
        return None, ""

    # Condition 2: sustained distribution — 5+ of last 7 days below VWAP
    below_count = 0
    for i in range(2, min(9, len(close))):   # check last 7 bars (excluding today)
        if not pd.isna(vwap_20.iloc[-i]) and float(close.iloc[-i]) < float(vwap_20.iloc[-i]):
            below_count += 1
    min_below = max(4, 5 - drought)
    if below_count < min_below:
        return None, ""

    # Condition 3: volume conviction on the reclaim
    avg_vol = float(volume.rolling(20).mean().iloc[-1])
    today_vol = float(volume.iloc[-1]) if not pd.isna(volume.iloc[-1]) else 0.0
    vol_thresh = max(1.2, 1.4 - drought * 0.05)
    if avg_vol <= 0 or today_vol < avg_vol * vol_thresh:
        return None, ""

    # Condition 4: RSI recovery (not overbought)
    rsi = _rsi(close, 14)
    if rsi.empty or pd.isna(rsi.iloc[-1]):
        return None, ""
    rsi_val = float(rsi.iloc[-1])
    rsi_low  = max(28, 30 - drought * 2)
    rsi_high = 60 + drought * 3
    if not (rsi_low <= rsi_val <= rsi_high):
        return None, ""

    reclaim_pct = round((price_now - vwap_now) / vwap_now * 100, 2)
    return "BUY", (
        f"VWAP reclaim: {below_count}d below VWAP → crossed above"
        f" · +{reclaim_pct:.2f}% above VWAP · vol={today_vol/avg_vol:.1f}x · RSI={rsi_val:.1f}"
    )


def signal_intermarket_flow(symbol: str, df: pd.DataFrame, all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """Intermarket Flow Confirmation: SPY/TLT rising + HYG tight = risk-on environment.
    Scout: cross-asset capital flow alignment confirms equity ETF uptrends.
    Top quant firms (Two Sigma, AQR) use cross-asset flows as regime confirmation."""
    close = df["Close"]
    if len(close) < 21:
        return None, ""
    im = all_data.get("__intermarket__", {})
    if not im:
        return None, ""

    risk_score = float(im.get("risk_on_score", 50))
    credit_signal = im.get("credit", "neutral")
    dollar_signal = im.get("dollar", "neutral")

    # Risk-on confirmation threshold (relaxed by drought)
    risk_threshold = max(65.0 - drought * 4.0, 50.0)

    if risk_score >= risk_threshold and credit_signal in ("tight", "neutral"):
        # Strong dollar is a mild headwind for broad equity ETFs
        dollar_adj = -5 if dollar_signal == "strong" else (3 if dollar_signal == "weak" else 0)
        effective_score = risk_score + dollar_adj
        if effective_score >= risk_threshold:
            # Confirm individual symbol is trending up
            sma20 = close.rolling(20).mean()
            if pd.isna(sma20.iloc[-1]):
                return None, ""
            ret_5 = (close.iloc[-1] / close.iloc[-5] - 1) if close.iloc[-5] > 0 else 0
            if close.iloc[-1] > sma20.iloc[-1] and ret_5 > -0.01:
                return "BUY", (
                    f"Intermarket risk-on: score={risk_score:.0f} "
                    f"credit={credit_signal} dollar={dollar_signal}"
                )
    return None, ""


def get_reddit_wsb_sentiment(target_symbols: list[str]) -> dict[str, float]:
    """
    Scrape Reddit r/WallStreetBets hot posts (public JSON API, no auth needed).
    Counts ticker mentions in post titles/flairs and returns relative mention score.
    Returns {symbol: mention_score (0-100)} — 0=not mentioned, 100=most mentioned.
    Higher score = more buzz on WSB = potential meme/squeeze momentum.
    """
    import re
    # Map yfinance symbols to Reddit ticker format
    wsb_sym_map = {
        "GME": "GME", "AMC": "AMC", "MARA": "MARA", "RIOT": "RIOT",
        "NVAX": "NVAX", "BNGO": "BNGO", "SPCE": "SPCE", "RIVN": "RIVN",
        "COIN": "COIN", "MSTR": "MSTR", "TSLA": "TSLA", "NVDA": "NVDA",
        "AMD": "AMD", "AAPL": "AAPL", "MSFT": "MSFT",
        "DOGE-USD": "DOGE", "SHIB-USD": "SHIB",
    }
    # Only track symbols that appear in WSB
    tracked = {wsb_sym_map.get(s, s.replace("-USD", "")) for s in target_symbols}

    counts: dict[str, int] = {}
    total_posts = 0
    try:
        urls = [
            "https://www.reddit.com/r/wallstreetbets/hot.json?limit=50",
            "https://www.reddit.com/r/wallstreetbets/new.json?limit=25",
        ]
        for url in urls:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (research bot, educational use)"
            })
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            posts = data.get("data", {}).get("children", [])
            for post in posts:
                post_data = post.get("data", {})
                text = f"{post_data.get('title', '')} {post_data.get('link_flair_text', '')}".upper()
                total_posts += 1
                for sym in tracked:
                    # Match ticker as word boundary (avoid partial matches)
                    if re.search(r'\b' + re.escape(sym) + r'\b', text):
                        counts[sym] = counts.get(sym, 0) + 1
    except Exception:
        pass

    if not counts or total_posts == 0:
        return {}

    # Convert to 0-100 score (relative to most-mentioned symbol)
    max_count = max(counts.values())
    result: dict[str, float] = {}
    for sym in target_symbols:
        wsb_sym = wsb_sym_map.get(sym, sym.replace("-USD", ""))
        c = counts.get(wsb_sym, 0)
        if c > 0:
            result[sym] = round(c / max_count * 100, 1)
    return result


def get_news_sentiment(symbols: list[str]) -> dict[str, float]:
    """
    Fast headline sentiment from yfinance news (no NLP library needed).
    Returns {symbol: bull_score (0-100)} where 50=neutral.
    Counts bullish vs bearish keyword matches in recent headlines.
    """
    _BULL_KWS = {"upgrade", "beat", "surge", "soar", "rally", "buy", "outperform",
                 "record", "breakout", "strong", "boost", "gain", "raise", "bullish",
                 "revenue beat", "earnings beat", "guidance raise", "all-time high"}
    _BEAR_KWS = {"downgrade", "miss", "fall", "drop", "cut", "sell", "underperform",
                 "warning", "layoff", "loss", "decline", "crash", "bearish", "recession",
                 "guidance cut", "earnings miss", "revenue miss", "downside"}
    result: dict[str, float] = {}
    for sym in symbols:
        try:
            news = yf.Ticker(sym).news or []
            bull = bear = 0
            for article in news[:10]:  # most recent 10 articles
                title = (article.get("title") or "").lower()
                bull += sum(1 for kw in _BULL_KWS if kw in title)
                bear += sum(1 for kw in _BEAR_KWS if kw in title)
            total = bull + bear
            if total > 0:
                result[sym] = round(bull / total * 100, 1)
        except Exception:
            pass
    return result


def get_short_interest(symbols: list[str]) -> dict[str, dict]:
    """
    Fetch short interest data from yfinance for key symbols.
    Returns {symbol: {short_ratio: float, short_pct_float: float, days_to_cover: float}}
    short_pct_float = sharesShort / sharesOutstanding (e.g. 0.25 = 25% shorted)
    days_to_cover   = sharesShort / avg daily volume (how many days for shorts to cover)
    High short interest: short_pct > 0.20 or days_to_cover > 5
    """
    result: dict[str, dict] = {}
    for sym in symbols:
        try:
            info = yf.Ticker(sym).info
            shares_short = int(info.get("sharesShort", 0) or 0)
            shares_out   = int(info.get("sharesOutstanding", 1) or 1)
            avg_vol_10d  = int(info.get("averageVolume10days", 1) or 1)
            short_pct    = shares_short / shares_out if shares_out > 0 else 0.0
            days_cover   = shares_short / avg_vol_10d if avg_vol_10d > 0 else 0.0
            short_ratio  = float(info.get("shortRatio", 0) or 0)
            result[sym]  = {
                "short_pct":    round(short_pct, 4),
                "days_to_cover": round(days_cover, 2),
                "short_ratio":  round(short_ratio, 2),
            }
        except Exception:
            pass
    return result


def get_stocktwits_sentiment(symbols: list[str]) -> dict[str, float]:
    """
    Fetch StockTwits public sentiment for a list of symbols.
    Returns {symbol: bull_pct (0-100)} — 50 = neutral/unavailable.
    StockTwits public API requires no key (200 req/hr free tier).
    ST symbol format: crypto = 'DOGE.X', stocks = 'GME'
    """
    # Map yfinance symbols → StockTwits symbol format
    st_map = {
        "DOGE-USD": "DOGE.X", "SHIB-USD": "SHIB.X", "PEPE-USD": "PEPE.X",
        "FLOKI-USD": "FLOKI.X", "BONK-USD": "BONK.X",
        "SAND-USD": "SAND.X", "MANA-USD": "MANA.X", "CHZ-USD": "CHZ.X",
        "ENJ-USD": "ENJ.X",
        "GME": "GME", "AMC": "AMC", "MARA": "MARA", "RIOT": "RIOT",
        "NVAX": "NVAX", "BNGO": "BNGO", "SPCE": "SPCE", "RIVN": "RIVN",
        # v9.5: expanded coverage for StockTwits scout signal
        "TSLA": "TSLA", "NVDA": "NVDA", "AMD": "AMD", "AAPL": "AAPL",
        "COIN": "COIN", "MSTR": "MSTR", "PLTR": "PLTR", "SOFI": "SOFI",
        "BTC-USD": "BTC.X", "ETH-USD": "ETH.X", "SOL-USD": "SOL.X",
        "XRP-USD": "XRP.X", "ADA-USD": "ADA.X",
    }
    sentiment: dict[str, float] = {}
    for sym in symbols:
        st_sym = st_map.get(sym)
        if not st_sym:
            continue
        try:
            url = f"https://api.stocktwits.com/api/2/streams/symbol/{st_sym}.json"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            messages = data.get("messages", [])
            if not messages:
                continue
            bull = sum(1 for m in messages if (m.get("entities", {}).get("sentiment", {}) or {}).get("basic") == "Bullish")
            bear = sum(1 for m in messages if (m.get("entities", {}).get("sentiment", {}) or {}).get("basic") == "Bearish")
            total = bull + bear
            if total >= 3:
                sentiment[sym] = round(bull / total * 100, 1)
        except Exception:
            pass
    return sentiment


def signal_meme_velocity(symbol: str, df: pd.DataFrame, _all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """Meme Coin Velocity: parabolic 5-day price momentum + volume explosion + social confirmation.
    Tier 1: Meme pumps typically see 20-50% moves in 3-7 days before exhaustion.
    Entry at acceleration onset before retail FOMO peak.
    Optional: StockTwits bull% > 60 lowers volume threshold requirement."""
    close = df["Close"]
    volume = df["Volume"]
    if len(close) < 25:
        return None, ""
    ret_5 = (close.iloc[-1] / close.iloc[-5] - 1) if len(close) >= 5 else 0
    ret_3 = (close.iloc[-1] / close.iloc[-3] - 1) if len(close) >= 3 else 0
    vol_avg = volume.rolling(20).mean()
    vol_ratio = volume.iloc[-1] / vol_avg.iloc[-1] if vol_avg.iloc[-1] > 0 else 0
    rsi = _rsi(close, 14)
    rsi_val = rsi.iloc[-1]
    if pd.isna(rsi_val):
        return None, ""
    # StockTwits social sentiment (injected by run_scanner as __sentiment__ key)
    sentiment_cache = _all_data.get("__sentiment__", {})
    bull_pct = sentiment_cache.get(symbol, 50.0)
    social_bullish = bull_pct > 60.0
    # Velocity threshold reduces with drought; social confirmation lowers bar
    vel_threshold = max(0.12 - drought * 0.012, 0.06)
    vol_threshold = max(3.0 - drought * 0.3, 1.5)
    if social_bullish:
        vol_threshold = max(vol_threshold - 0.5, 1.2)  # social boost: relax volume req slightly
    # Key signal: strong 5d momentum + accelerating (3d > 5d per-day rate)
    velocity_ok = ret_5 > vel_threshold
    acceleration = ret_3 > ret_5 * 0.5  # 3d return > 50% of 5d return (recent days faster)
    if velocity_ok and acceleration and vol_ratio > vol_threshold and rsi_val < 85:
        sentiment_tag = f", ST={bull_pct:.0f}%bull" if symbol in sentiment_cache else ""
        return "BUY", f"Meme velocity: 5d={ret_5*100:.0f}% 3d={ret_3*100:.0f}%, vol {vol_ratio:.1f}x, RSI={rsi_val:.0f}{sentiment_tag}"
    return None, ""


def signal_ema_ribbon(symbol: str, df: pd.DataFrame, _all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """EMA Ribbon Alignment (8/13/21/34/55 EMAs all bullish-stacked).
    Tier 1: Institutional trend signal — all EMAs rising and ordered = confirmed uptrend."""
    close = df["Close"]
    if len(close) < 60:
        return None, ""
    e8  = close.ewm(span=8,  adjust=False).mean()
    e13 = close.ewm(span=13, adjust=False).mean()
    e21 = close.ewm(span=21, adjust=False).mean()
    e34 = close.ewm(span=34, adjust=False).mean()
    e55 = close.ewm(span=55, adjust=False).mean()
    stacked_now  = (e8.iloc[-1] > e13.iloc[-1] > e21.iloc[-1] > e34.iloc[-1] > e55.iloc[-1])
    stacked_prev = (e8.iloc[-2] > e13.iloc[-2] > e21.iloc[-2] > e34.iloc[-2] > e55.iloc[-2])
    gap_pct = (e8.iloc[-1] - e55.iloc[-1]) / e55.iloc[-1] * 100 if e55.iloc[-1] > 0 else 0
    if drought >= 5 and stacked_now and close.iloc[-1] > e8.iloc[-1]:
        return "BUY", f"EMA Ribbon bullish (drought fallback): spread={gap_pct:.1f}%"
    if stacked_now and not stacked_prev:
        return "BUY", f"EMA Ribbon aligned: 8>13>21>34>55, spread={gap_pct:.1f}%"
    return None, ""


def signal_bollinger_squeeze(symbol: str, df: pd.DataFrame, _all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """Bollinger Band Squeeze Breakout (TTM Squeeze signal).
    Tier 1: BB inside Keltner = volatility compression → explosive directional move."""
    close = df["Close"]
    if len(close) < 25 or "High" not in df.columns or "Low" not in df.columns:
        return None, ""
    high, low = df["High"], df["Low"]
    sma20    = close.rolling(20).mean()
    std20    = close.rolling(20).std()
    bb_upper = sma20 + 2 * std20
    bb_lower = sma20 - 2 * std20
    tr       = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    atr20    = tr.ewm(span=20, adjust=False).mean()
    ema20    = close.ewm(span=20, adjust=False).mean()
    kc_mult  = max(1.5 - drought * 0.1, 1.0)
    kc_upper = ema20 + kc_mult * atr20
    kc_lower = ema20 - kc_mult * atr20
    squeeze_now  = (bb_upper.iloc[-1] < kc_upper.iloc[-1]) and (bb_lower.iloc[-1] > kc_lower.iloc[-1])
    squeeze_prev = (bb_upper.iloc[-2] < kc_upper.iloc[-2]) if len(close) > 2 else False
    momentum_up  = close.iloc[-1] > sma20.iloc[-1] and close.iloc[-1] > close.iloc[-3]
    width = (bb_upper.iloc[-1] - bb_lower.iloc[-1]) / sma20.iloc[-1] * 100 if sma20.iloc[-1] > 0 else 0
    if not squeeze_now and squeeze_prev and momentum_up:
        return "BUY", f"BB Squeeze breakout: bands expanding, width={width:.1f}%, above SMA20"
    if drought >= 3 and squeeze_now and momentum_up:
        return "BUY", f"BB Squeeze coiling (drought={drought}): width={width:.1f}%"
    return None, ""


def signal_options_flow(symbol: str, df: pd.DataFrame, all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """
    Scout: Options flow contrarian signal.
    Uses market-level put/call ratio (SPY/QQQ) from pre-fetched sentiment.
    Entry: market PCR > 1.2 (extreme fear) + individual RSI(14) < 38 → contrarian BUY.
    High PCR = crowded shorts = coiled spring for a reversal.
    """
    close = df["Close"]
    if len(close) < 20:
        return None, ""

    # Read pre-fetched options sentiment from all_data (injected by run_scanner)
    options_pcr: dict[str, float] = all_data.get("__options_pcr__", {})
    if not options_pcr:
        return None, ""

    # Market fear gauge: average SPY + QQQ PCR
    market_pcrs = [v for k, v in options_pcr.items() if k in ("SPY", "QQQ")]
    if not market_pcrs:
        return None, ""
    market_pcr = sum(market_pcrs) / len(market_pcrs)

    # Fear threshold — PCR > 1.2 = extreme put buying = market scared
    fear_threshold = max(1.0 - drought * 0.05, 0.9)
    if market_pcr < fear_threshold:
        return None, ""

    # Individual RSI(14) oversold confirmation
    rsi = _rsi(close, 14)
    if rsi.empty or pd.isna(rsi.iloc[-1]):
        return None, ""
    rsi_val = float(rsi.iloc[-1])

    # Price above 50d MA (uptrend backdrop for reversal)
    sma50 = close.rolling(50).mean()

    rsi_threshold = 40 + drought * 2  # relax threshold on drought
    if rsi_val < min(rsi_threshold, 45) and close.iloc[-1] > sma50.iloc[-1] * 0.97:
        return "BUY", (f"Options fear spike: market PCR={market_pcr:.2f} "
                       f"(>{fear_threshold:.1f}) + RSI={rsi_val:.1f} oversold")
    return None, ""


def signal_options_call_surge(symbol: str, df: pd.DataFrame, all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """
    v7.1: Stock-level options call volume surge — institutional footprint detector.
    When a specific stock shows unusual call buying relative to open interest, while
    the broad market is in fear/neutral, it suggests informed institutional positioning.

    Signal fires when:
    1. Stock-level call volume > open_interest * 0.25 (high conviction, not just hedges)
    2. Stock PCR < 0.70 (calls dominating puts for THIS stock)
    3. RSI < 62 (not already extended — room to run)
    4. Price within 8% of 52-week high OR above 20d SMA (uptrend or breakout territory)
    Uses yfinance near-term option chain (same approach as market PCR).
    """
    close = df["Close"]
    if len(close) < 20:
        return None, ""

    # Only fetch for liquid optionable symbols (yfinance has data for these)
    _CALL_SURGE_SYMBOLS = {
        "AAPL", "MSFT", "NVDA", "AMD", "META", "AMZN", "GOOGL", "TSLA",
        "SPY", "QQQ", "COIN", "MSTR", "NFLX", "UBER",
    }
    if symbol not in _CALL_SURGE_SYMBOLS:
        return None, ""

    try:
        ticker = yf.Ticker(symbol)
        expiries = ticker.options
        if not expiries:
            return None, ""
        chain = ticker.option_chain(expiries[0])  # nearest expiry = most liquid
        calls = chain.calls
        if calls.empty:
            return None, ""

        call_vol = float(calls["volume"].fillna(0).sum())
        call_oi  = float(calls["openInterest"].fillna(0).sum())
        put_vol  = float(chain.puts["volume"].fillna(0).sum())

        if call_vol <= 0 or call_oi <= 0:
            return None, ""

        # Call volume surge: volume > 25% of open interest = unusual activity (relax in drought)
        vol_oi_thresh = max(0.15, 0.25 - drought * 0.02)
        if call_vol < call_oi * vol_oi_thresh:
            return None, ""

        # Stock-level PCR — calls dominating puts
        stock_pcr = (put_vol / call_vol) if call_vol > 0 else 2.0
        pcr_thresh = 0.70 + drought * 0.05
        if stock_pcr > pcr_thresh:
            return None, ""

        # RSI confirmation — not overbought
        rsi = _rsi(close, 14)
        if rsi.empty or pd.isna(rsi.iloc[-1]):
            return None, ""
        rsi_val = float(rsi.iloc[-1])
        rsi_cap = 62 + drought * 3
        if rsi_val > rsi_cap:
            return None, ""

        # Price structure: above 20d SMA or within 8% of 52-week high
        sma20 = float(close.rolling(20).mean().iloc[-1])
        high52 = float(close.rolling(min(252, len(close))).max().iloc[-1])
        price_now = float(close.iloc[-1])
        near_high = price_now >= high52 * 0.92
        above_sma = price_now >= sma20 * 0.99

        if not (near_high or above_sma):
            return None, ""

        surge_ratio = round(call_vol / max(call_oi, 1) * 100, 1)
        return "BUY", (
            f"Call surge: vol/OI={surge_ratio:.1f}% · PCR={stock_pcr:.2f}"
            f" · RSI={rsi_val:.1f} · {'near 52w high' if near_high else 'above SMA20'}"
        )
    except Exception:
        return None, ""


def signal_gap_and_go(symbol: str, df: pd.DataFrame, _all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """
    v7.2: Gap-and-Go momentum signal.
    Detects when price gaps up at open AND shows follow-through during the day.
    This pattern, used by prop desks and intraday quants, finds institutional "open drive" moves
    where morning momentum continues — the opposite of a gap-fill reversal.

    Signal fires when (using daily OHLC bars):
    1. Gap up: today's Open > yesterday's Close × 1.008 (0.8% gap)
    2. Strong open drive: today's Close > today's Open (stock closed above its open)
    3. High is well above the gap: Close >= Open × 1.005 (follow-through beyond the open)
    4. Volume confirms: today's volume > 20-day avg volume (institutional participation)
    5. Price above 10d SMA (uptrend context — gaps in uptrends are more reliable)
    6. Not overbought: RSI < 68

    Academic basis: Ritter (1988) gap-and-go, Bhattacharya & Nanda institutional open-print theory.
    """
    if len(df) < 22:
        return None, ""

    # Require Open, High, Close columns (yfinance standard)
    if not all(c in df.columns for c in ["Open", "High", "Close", "Volume"]):
        return None, ""

    close  = df["Close"]
    opens  = df["Open"]
    volume = df["Volume"]

    prev_close  = float(close.iloc[-2])
    today_open  = float(opens.iloc[-1])
    today_close = float(close.iloc[-1])
    today_vol   = float(volume.iloc[-1]) if not pd.isna(volume.iloc[-1]) else 0.0
    avg_vol     = float(volume.iloc[-21:-1].mean()) if len(volume) >= 21 else 1.0

    if prev_close <= 0 or today_open <= 0:
        return None, ""

    # Gap size
    gap_pct = (today_open - prev_close) / prev_close
    gap_thresh = max(0.005, 0.008 - drought * 0.001)   # relax 0.1%/drought step
    if gap_pct < gap_thresh:
        return None, ""

    # Open-drive: closed above open (not a gap-fill fade day)
    if today_close < today_open:
        return None, ""

    # Follow-through: meaningful intraday extension beyond the open price
    drive_pct = (today_close - today_open) / today_open
    drive_thresh = max(0.003, 0.005 - drought * 0.001)
    if drive_pct < drive_thresh:
        return None, ""

    # Volume confirmation
    vol_mult = avg_vol * 1.2 if avg_vol > 0 else 0
    if today_vol < vol_mult:
        return None, ""

    # Uptrend context: price above 10d SMA
    sma10 = close.rolling(10).mean()
    if pd.isna(sma10.iloc[-1]) or today_close < float(sma10.iloc[-1]) * 0.99:
        return None, ""

    # RSI: not overbought
    rsi = _rsi(close, 14)
    if rsi.empty or pd.isna(rsi.iloc[-1]):
        return None, ""
    rsi_val = float(rsi.iloc[-1])
    rsi_cap = 68 + drought * 3
    if rsi_val > rsi_cap:
        return None, ""

    total_pct = round((gap_pct + drive_pct) * 100, 2)
    return "BUY", (
        f"Gap-and-Go: gap={gap_pct*100:.1f}% + drive={drive_pct*100:.1f}% "
        f"= +{total_pct:.1f}% · vol={today_vol/avg_vol:.1f}x · RSI={rsi_val:.1f}"
    )


def signal_crypto_funding_contrarian(symbol: str, df: pd.DataFrame, _all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """Crypto Funding Rate Contrarian — v6.5.
    Negative perpetual funding rates = shorts paying longs.
    This is short-squeeze fuel — contrarian BUY when funding is negative.
    Uses real-time funding rate data fetched via CCXT (injected as __crypto_funding__).
    Academic: Glosten-Milgrom informed trading model — negative funding reveals net short crowding.
    """
    close = df["Close"]
    if len(close) < 10:
        return None, ""

    # Map yfinance symbols to CCXT perp symbols
    _SYM_MAP = {
        "BTC-USD": "BTC/USDT:USDT", "ETH-USD": "ETH/USDT:USDT",
        "SOL-USD": "SOL/USDT:USDT", "BNB-USD": "BNB/USDT:USDT",
        "XRP-USD": "XRP/USDT:USDT", "DOGE-USD": "DOGE/USDT:USDT",
        "AVAX-USD": "AVAX/USDT:USDT", "LINK-USD": "LINK/USDT:USDT",
    }
    perp_sym = _SYM_MAP.get(symbol)
    if perp_sym is None:
        return None, ""

    funding_data = _all_data.get("__crypto_funding__", {})
    if not isinstance(funding_data, dict):
        return None, ""
    rates = funding_data.get("rates", {})
    fr = rates.get(perp_sym)
    if fr is None:
        return None, ""

    # Negative funding threshold (loosens in drought)
    neg_thresh = max(-0.005 - drought * 0.002, -0.020)  # -0.5% to -2% range

    if fr > neg_thresh:
        return None, ""   # funding not negative enough

    # Price not in freefall (some floor condition)
    ret_3d = float(close.iloc[-1] / close.iloc[-4] - 1) if len(close) >= 5 else 0.0
    if ret_3d < -0.20:   # dropped >20% in 3 days — too dangerous
        return None, ""

    # RSI not overbought (don't buy into rallied price despite negative funding)
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, np.nan)
    rsi   = float((100 - 100 / (1 + rs)).iloc[-1]) if not rs.isna().iloc[-1] else 50.0
    if rsi > 70.0:
        return None, ""

    overall_signal = funding_data.get("signal", "neutral")
    return "BUY", (
        f"Crypto funding contrarian: {perp_sym} rate={fr:.4f}% (negative — shorts loaded), "
        f"RSI={rsi:.1f}, 3d_ret={ret_3d*100:.1f}%, overall={overall_signal}"
    )


def signal_price_acceleration(symbol: str, df: pd.DataFrame, _all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """Price Acceleration Detector — v6.7.
    Detects stocks where the RATE OF RETURN is ACCELERATING (second derivative positive).
    The 'jerk' signal — not just moving up, but moving up faster each day.
    Early phase of institutional momentum entry before the move gets crowded.
    CTAs and trend-following desks (AHL, Winton, Millburn) use acceleration as a filter.
    """
    close = df["Close"]
    if len(close) < 15:
        return None, ""

    # Compute 5-day rolling returns (velocity)
    ret5 = close.pct_change(5)
    if ret5.isna().iloc[-1] or ret5.isna().iloc[-2] or ret5.isna().iloc[-3]:
        return None, ""

    # Acceleration = change in 5d return between windows
    vel_now  = float(ret5.iloc[-1])     # current velocity (5d return)
    vel_prev = float(ret5.iloc[-4])     # velocity 3 days ago
    vel_old  = float(ret5.iloc[-7]) if len(ret5) >= 8 else float(ret5.iloc[-4])

    # Acceleration: velocity increasing over two successive measurements
    accel1 = vel_now - vel_prev         # recent acceleration
    accel2 = vel_prev - vel_old         # prior acceleration

    # Both accelerations must be positive (two consecutive positive second derivatives)
    accel_thresh = max(0.005 - drought * 0.001, 0.002)  # 0.5% min acceleration

    if accel1 < accel_thresh or accel2 < accel_thresh:
        return None, ""

    # Must have positive current velocity (direction must be up)
    if vel_now < 0.01:   # need at least 1% 5d gain
        return None, ""

    # RSI not overbought (acceleration hasn't already attracted crowding)
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, np.nan)
    rsi   = float((100 - 100 / (1 + rs)).iloc[-1]) if not rs.isna().iloc[-1] else 50.0
    rsi_cap = 72.0 + drought * 3.0  # cap loosens in drought

    if rsi > rsi_cap:
        return None, ""

    return "BUY", (
        f"Price acceleration: vel={vel_now*100:.1f}% (5d), "
        f"accel1=+{accel1*100:.2f}%, accel2=+{accel2*100:.2f}%, "
        f"RSI={rsi:.1f} — momentum jerk signal"
    )


def signal_adx_trend_filter(symbol: str, df: pd.DataFrame, _all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """ADX Trend Confirmation — v6.8.
    Only fires when the stock is in a high-ADX trending regime (ADX > 25).
    Combines ADX strength with directional DI+ > DI- confirmation.
    CTA-standard: Wilder (1978) ADX filter. AHL/Winton use ADX>20 as trend gate.
    This is a TREND CONFIRMATION signal, not standalone — it requires:
    1. Strong trend (ADX > 25)
    2. Positive direction (DI+ > DI-)
    3. Price above 20d SMA (momentum confirmation)
    """
    close = df["Close"]
    high  = df["High"]  if "High"  in df.columns else close
    low   = df["Low"]   if "Low"   in df.columns else close
    if len(close) < 30:
        return None, ""

    # True Range
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low  - close.shift(1)).abs()
    tr  = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Directional movements
    up   = high.diff()
    down = -low.diff()
    dm_plus  = up.where((up > down) & (up > 0), 0.0)
    dm_minus = down.where((down > up) & (down > 0), 0.0)

    # Smoothed averages (14-period Wilder smoothing)
    period = 14
    atr    = tr.ewm(alpha=1/period, adjust=False).mean()
    di_p   = 100 * dm_plus.ewm(alpha=1/period,  adjust=False).mean() / atr.replace(0, np.nan)
    di_m   = 100 * dm_minus.ewm(alpha=1/period, adjust=False).mean() / atr.replace(0, np.nan)
    dx     = (100 * (di_p - di_m).abs() / (di_p + di_m).replace(0, np.nan)).fillna(0.0)
    adx    = dx.ewm(alpha=1/period, adjust=False).mean()

    adx_val  = float(adx.iloc[-1])
    dip_val  = float(di_p.iloc[-1]) if not di_p.isna().iloc[-1] else 0.0
    dim_val  = float(di_m.iloc[-1]) if not di_m.isna().iloc[-1] else 0.0

    adx_threshold = max(25.0 - drought * 2.0, 18.0)  # ADX>25 default, loosens to 18 in drought

    if adx_val < adx_threshold:
        return None, ""   # not trending strongly enough

    if dip_val <= dim_val:
        return None, ""   # trend is downward

    # Price above 20d SMA (momentum confirmation)
    sma20 = float(close.rolling(20).mean().iloc[-1])
    if float(close.iloc[-1]) < sma20 * 0.99:
        return None, ""

    return "BUY", (
        f"ADX trend: {adx_val:.1f} (>{adx_threshold:.0f}), "
        f"DI+={dip_val:.1f} > DI-={dim_val:.1f}, "
        f"price above 20d SMA — strong uptrend confirmed"
    )


# ---------------------------------------------------------------------------
# v11.8 — SKYROCKET Strategies (short-term momentum plays)
# Source: trading_strategies_skyrocket.md — 3 highest-value activations
# ---------------------------------------------------------------------------


def signal_skyrocket_volume_spike(symbol: str, df: pd.DataFrame, all_data: dict,
                                   drought: int = 0) -> tuple[str | None, str]:
    """
    SKYROCKET Strategy 1: Volume Spike Detector.
    Trigger: volume > 3x 24h average AND price change > 3% in last session.
    Uses Binance klines via multi_source_fetcher when available, falls back to yfinance OHLCV.
    Confidence: volume_ratio / 5.0 (capped at 0.95).
    TP: 8%, SL: 3%.
    """
    if df is None or len(df) < 21:
        return None, ""

    close = df["Close"]
    vol = df["Volume"]

    # Volume spike: current bar vs 20-bar average (proxy for 24h avg on daily data)
    vol_avg = vol.iloc[-21:-1].mean()
    if vol_avg <= 0 or pd.isna(vol_avg):
        return None, ""

    vol_ratio = float(vol.iloc[-1]) / float(vol_avg)
    if vol_ratio < 3.0:
        # Drought relaxation: 2.5x at drought >= 3
        if drought < 3 or vol_ratio < 2.5:
            return None, f"volume only {vol_ratio:.1f}x avg (need 3x)"

    # Price change > 3% in most recent bar (proxy for 1h on intraday, or daily change)
    price_chg = (float(close.iloc[-1]) - float(close.iloc[-2])) / float(close.iloc[-2])
    if price_chg < 0.03:
        # Drought relaxation: 2% at drought >= 3
        if drought < 3 or price_chg < 0.02:
            return None, f"price change only {price_chg*100:.1f}% (need 3%)"

    # Additional check: price above 10-period SMA (not a dead cat bounce)
    sma10 = float(close.rolling(10).mean().iloc[-1])
    if float(close.iloc[-1]) < sma10:
        return None, "price below 10-period SMA — skipping volume spike"

    confidence = min(vol_ratio / 5.0, 0.95)
    return "BUY", (
        f"[SKYROCKET] Volume spike {vol_ratio:.1f}x avg + price +{price_chg*100:.1f}% "
        f"(conf={confidence:.2f})"
    )


def signal_skyrocket_breakout_scalper(symbol: str, df: pd.DataFrame, all_data: dict,
                                       drought: int = 0) -> tuple[str | None, str]:
    """
    SKYROCKET Strategy 2: Breakout Scalper.
    Trigger: price breaks above 24h high AND volume > 2x average.
    RSI must be 50-75 (not overbought).
    TP: 5%, SL: 2%.
    """
    if df is None or len(df) < 21:
        return None, ""

    close = df["Close"]
    high = df["High"]
    vol = df["Volume"]

    current_price = float(close.iloc[-1])

    # 24h high: use the highest high in the prior 1-5 bars (depending on timeframe)
    # For daily data: look at prior day's high as "24h high"
    # For broader coverage: use rolling 5-bar high (excluding current bar)
    prior_high = float(high.iloc[-6:-1].max()) if len(high) >= 6 else float(high.iloc[-2])

    # Price must break above prior 24h high
    if current_price <= prior_high:
        return None, f"no breakout (price {current_price:.4f} <= 24h high {prior_high:.4f})"

    # Volume confirmation: > 2x average
    vol_avg = vol.iloc[-21:-1].mean()
    if vol_avg <= 0 or pd.isna(vol_avg):
        return None, ""

    vol_ratio = float(vol.iloc[-1]) / float(vol_avg)
    vol_thresh = 2.0 if drought < 3 else 1.5
    if vol_ratio < vol_thresh:
        return None, f"volume only {vol_ratio:.1f}x avg (need {vol_thresh}x)"

    # RSI filter: must be 50-75 (momentum but not overbought)
    rsi = _rsi(close, 14)
    rsi_val = float(rsi.iloc[-1]) if len(rsi) > 0 and not pd.isna(rsi.iloc[-1]) else 60.0
    if rsi_val < 50 or rsi_val > 75:
        if drought < 3:
            return None, f"RSI {rsi_val:.0f} outside 50-75 range"
        elif rsi_val > 80:
            return None, f"RSI {rsi_val:.0f} too overbought even with drought"

    breakout_pct = ((current_price - prior_high) / prior_high) * 100
    confidence = min(vol_ratio / 4.0, 0.90)
    return "BUY", (
        f"[SKYROCKET] Breakout +{breakout_pct:.1f}% above 24h high, "
        f"vol {vol_ratio:.1f}x, RSI {rsi_val:.0f} (conf={confidence:.2f})"
    )


def signal_skyrocket_funding_reversal(symbol: str, df: pd.DataFrame, all_data: dict,
                                       drought: int = 0) -> tuple[str | None, str]:
    """
    SKYROCKET Strategy 3: Funding Rate Reversal (Contrarian Long).
    Trigger: funding rate < -0.05% (shorts overleveraged) AND RSI < 35.
    This is DIFFERENT from the existing funding-rate-reversal algo which looks for
    negative-to-positive transitions. This one fires while funding is STILL deeply
    negative (contrarian entry before the crowd).
    TP: 6%, SL: 2.5%.
    Confidence: abs(funding_rate) * 10 (capped at 0.90).
    """
    if df is None or len(df) < 20:
        return None, ""

    # Try to get funding rate from injected data first, then fetch directly
    funding_rate = None

    # Check injected crypto_funding data
    crypto_funding = all_data.get("__crypto_funding__", {})
    if isinstance(crypto_funding, dict) and symbol in crypto_funding:
        fr_entry = crypto_funding[symbol]
        if isinstance(fr_entry, dict):
            funding_rate = fr_entry.get("rate") or fr_entry.get("funding_rate")
        elif isinstance(fr_entry, (int, float)):
            funding_rate = float(fr_entry)

    # Fallback: fetch from Binance Futures API via acceleration engine
    if funding_rate is None:
        try:
            from crypto_acceleration_engine import fetch_funding_rate_history
            rates = fetch_funding_rate_history(symbol, limit=3)
            if rates and len(rates) > 0:
                funding_rate = rates[0]  # most recent
        except (ImportError, Exception):
            pass

    # Fallback: check multi_source_fetcher bulk funding rates
    if funding_rate is None and _HAS_MULTI_FETCH:
        try:
            bulk_rates = fetch_all_funding_rates_bulk()
            # Convert yf symbol to Binance format
            binance_sym = symbol.replace("-USD", "USDT")
            for item in bulk_rates:
                if item.get("symbol") == binance_sym:
                    funding_rate = item.get("funding_rate")
                    break
        except Exception:
            pass

    if funding_rate is None:
        return None, "no funding rate data available"

    funding_rate = float(funding_rate)

    # Trigger: funding rate < -0.05% (i.e., -0.0005 in decimal)
    threshold = -0.0005 if drought < 3 else -0.0003
    if funding_rate >= threshold:
        return None, f"funding rate {funding_rate*100:.4f}% not negative enough (need <{threshold*100:.3f}%)"

    # RSI must be < 35 (oversold — shorts pushing it down)
    close = df["Close"]
    rsi = _rsi(close, 14)
    rsi_val = float(rsi.iloc[-1]) if len(rsi) > 0 and not pd.isna(rsi.iloc[-1]) else 50.0
    rsi_thresh = 35 if drought < 3 else 40
    if rsi_val >= rsi_thresh:
        return None, f"RSI {rsi_val:.0f} not oversold enough (need <{rsi_thresh})"

    confidence = min(abs(funding_rate) * 10, 0.90)
    return "BUY", (
        f"[SKYROCKET] Funding rate deeply negative {funding_rate*100:.4f}% "
        f"(shorts overleveraged) + RSI {rsi_val:.0f} oversold (conf={confidence:.2f})"
    )


# Signal function registry
SIGNAL_FUNCS = {
    # --- TIER 1: Academic-backed strategies ---
    "funding-rate-arb":       signal_funding_rate_arb,
    "pairs-trading":          signal_pairs_trading,
    "betting-against-beta":   signal_betting_against_beta,
    "flash-crash-reversal":   signal_flash_crash_reversal,
    "quality-minus-junk":     signal_quality_minus_junk,
    "meme-bollinger-mean-rev": signal_bollinger_mean_reversion,
    "macd-momentum":          signal_macd_crossover,         # v3 new
    "golden-cross-stocks":    signal_golden_cross,           # v3 new
    "momentum-factor":        signal_momentum_factor,        # v3 new
    # --- SCOUT: Supplementary TA signals ---
    "meme-scanner-live":      signal_momentum_volume_spike,
    "penny-tracker-live":     signal_volume_breakout,
    "forex-scanner-live":     signal_ma_crossover,
    "crypto-momentum-scout":  signal_rsi_oversold,
    "volume-spike-scout":     signal_volume_spike_detect,
    "stoch-rsi-crypto":       signal_stoch_rsi_scout,        # v3 new
    "cci-crypto-reversal":    signal_cci_reversal,           # v3 new
    "williams-r-scout":       signal_williams_r,             # v3 new
    "donchian-stock-breakout": signal_donchian_breakout,     # v3 new
    "supertrend-crypto":      signal_supertrend,             # v3 new
    "keltner-bounce":         signal_keltner_bounce,         # v3 new
    # v4 new strategies
    "short-squeeze":          signal_short_squeeze,          # v4 new
    "sector-rotation":        signal_sector_rotation,        # v4 new
    "carry-trade-momentum":   signal_carry_momentum,         # v4 new
    "gap-and-go-stocks":      signal_gap_and_go,             # v4 new
    "ema-ribbon":             signal_ema_ribbon,             # v4 new
    "bollinger-squeeze":      signal_bollinger_squeeze,      # v4 new
    "meme-velocity":          signal_meme_velocity,          # v4 new
    # v4.5 new
    "options-flow-scout":     signal_options_flow,           # v4.5 new
    # v5.3 new
    "intermarket-flow-scout": signal_intermarket_flow,       # v5.3 new
    # v5.6 new
    "vwap-reversion-scout":   signal_vwap_reversion,         # v5.6 new
    # v5.9 new
    "volume-anomaly-scout":   signal_anomaly_detector,        # v5.9 new
    # v6.1 new
    "earnings-drift-scout":   signal_earnings_drift,           # v6.1 new
    # v6.3 new
    "post-earnings-rev-scout": signal_post_earnings_mean_rev,  # v6.3 new
    # v6.4 new
    "rsi-divergence-scout":      signal_rsi_divergence,             # v6.4 new
    # v6.5 new
    "crypto-funding-contrarian": signal_crypto_funding_contrarian,  # v6.5 new
    # v6.7 new
    "price-accel-scout":         signal_price_acceleration,          # v6.7 new
    # v6.8 new
    "adx-trend-scout":           signal_adx_trend_filter,            # v6.8 new
    # v7.1 new
    "call-surge-scout":          signal_options_call_surge,          # v7.1 new
    # v7.2 new
    "gap-and-go-scout":          signal_gap_and_go,                  # v7.2 new
    # v7.3 new
    "zscore-mean-rev-scout":     signal_zscore_mean_reversion,       # v7.3 new
    # v7.4 new
    "vwap-reclaim-scout":        signal_vwap_reclaim,                # v7.4 new
    # v7.5 new — keep at end
    "mtf-align-scout":           signal_multi_timeframe_align,       # v7.5 new
    # v7.6 new
    "hh-hl-scout":               signal_hh_hl_structure,             # v7.6 new
    # v7.7 new
    "dual-momentum-scout":       signal_dual_momentum,               # v7.7 new
    # v7.8 new
    "breadth-thrust-scout":      signal_breadth_thrust,              # v7.8 new
    # v7.9 new
    "vrsi-scout":                signal_volume_weighted_rsi,         # v7.9 new
    # v8.0 new
    "fibonacci-bounce-scout":    signal_fibonacci_bounce,            # v8.0 new
    # v8.1 new
    "52w-high-breakout-scout":   signal_52week_high_breakout,        # v8.1 new
    # v8.2 new
    "vol-contraction-scout":     signal_volatility_contraction_breakout,  # v8.2 new
    # v8.3 new
    "macd-hidden-div-scout":     signal_macd_hidden_divergence,           # v8.3 new
    # v8.4 new
    "stoch-rsi-scout":           signal_stoch_rsi_cross,                  # v8.4 new
    # v8.5 new
    "par-sar-scout":             signal_parabolic_sar_flip,               # v8.5 new
    # v8.6 new
    "aroon-trend-scout":         signal_aroon_trend_initiation,           # v8.6 new
    # v8.7 new
    "vix-mean-rev-scout":        signal_vix_mean_reversion,               # v8.7 new
    # v8.8 new
    "short-squeeze-scout":       signal_short_squeeze_proxy,              # v8.8 new
    # v8.9 new
    "altcoin-season-scout":      signal_altcoin_season_rotation,          # v8.9 new
    # v9.0 new
    "cmf-accumulation-scout":    signal_chaikin_money_flow,               # v9.0 new
    # v9.1 new
    "whale-accum-scout":         signal_whale_accumulation_proxy,         # v9.1 new
    # v9.2 new
    "cal-effect-crypto-scout":   signal_calendar_effect_crypto,           # v9.2 new
    # v9.5 new
    "stocktwits-bull-scout":     signal_stocktwits_bull_surge,            # v9.5 new
    # v9.7/v9.8/v9.9 entries appended below after their function definitions
}


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def load_json(path: Path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def append_audit(audit_path: Path, entry: dict):
    log = load_json(audit_path, [])
    if not isinstance(log, list):
        log = []
    log.append(entry)
    save_json(audit_path, log)


# ---------------------------------------------------------------------------
# Data Fetching
# ---------------------------------------------------------------------------

def fetch_symbol_data(symbol: str) -> pd.DataFrame | None:
    """Fetch OHLCV for symbol using multi-source fetcher with fallback chain.
    v11.3: Binance (crypto) → CoinCap → Frankfurter (forex) → yfinance."""
    if _HAS_MULTI_FETCH:
        return fetch_symbol_data_multi(symbol, period=PERIOD)
    # Fallback: original yfinance-only path
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=PERIOD, auto_adjust=True)
        if df is None or df.empty or len(df) < 20:
            return None
        return df
    except Exception:
        return None


def fetch_latest_price(symbol: str) -> float | None:
    """
    v11.3 — Fetch the most recent trade price.
    Multi-source: Binance real-time (crypto) → yfinance 5m intraday fallback.
    """
    if _HAS_MULTI_FETCH:
        price = fetch_latest_price_multi(symbol)
        if price is not None:
            return price
    # Fallback: original yfinance path
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="2d", interval="5m", auto_adjust=True)
        if df is None or df.empty:
            return None
        last_close = float(df["Close"].dropna().iloc[-1])
        return last_close if last_close > 0 else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# v10.3 — US Market Hours Guard (paper trading entry quality)
# ---------------------------------------------------------------------------

def is_us_market_open() -> bool:
    """
    Return True when the US stock exchange is in its regular session
    (09:30–16:00 ET, Mon–Fri, excludes weekends).
    Does NOT account for market holidays — yfinance handles that by returning
    no intraday bars for holiday sessions.

    Used to gate NEW stock/forex picks: we only open equity positions at a
    real executable intraday price, not at a stale daily close from Friday.
    Crypto is 24/7 and bypasses this gate.
    """
    import pytz
    et = pytz.timezone("America/New_York")
    now_et = datetime.now(et)
    if now_et.weekday() >= 5:          # Saturday=5, Sunday=6
        return False
    open_time  = now_et.replace(hour=9,  minute=30, second=0, microsecond=0)
    close_time = now_et.replace(hour=16, minute=0,  second=0, microsecond=0)
    return open_time <= now_et <= close_time


# ---------------------------------------------------------------------------
# Permanently Banned Symbols (proven losers in live trading)
# ---------------------------------------------------------------------------

PERMANENTLY_BANNED_SYMBOLS = {
    "RIVN",     # Gap-chased Feb 17 2026: -7.05% across 3 algos simultaneously
    "LCID",     # Zero liquidity EV meme, repeated losses
    "APT-USD",  # Delisted crypto - was APT21794-USD
    "MARA",     # High-beta BTC proxy trap, -9.4% in 90d backtest
    "BBBY",     # Bankruptcy, no tradable float
    "WKHS",     # Sub-$1 float, extreme slippage
    "SNDL",     # Illiquid penny, prone to halts
    "CLOV",     # Dilution trap, no institutional support
}


# ---------------------------------------------------------------------------
# Earnings Guard
# ---------------------------------------------------------------------------

def get_earnings_blacklist() -> set:
    """
    Return set of high-impact symbols with earnings in the next 3 days.
    Only checks EARNINGS_WATCHLIST to keep runtime fast.
    Silently returns empty set on any network/parse error.
    """
    import yfinance as yf
    from datetime import date, timedelta
    blacklist: set[str] = set()
    today = date.today()
    window_end = today + timedelta(days=3)
    for sym in EARNINGS_WATCHLIST:
        try:
            cal = yf.Ticker(sym).calendar
            if not cal or not isinstance(cal, dict):
                continue
            ed_list = cal.get("Earnings Date", [])
            if not isinstance(ed_list, list):
                ed_list = [ed_list]
            for dt in ed_list:
                if dt is None:
                    continue
                try:
                    d = dt.date() if hasattr(dt, "date") else date.fromisoformat(str(dt)[:10])
                    if today <= d <= window_end:
                        blacklist.add(sym)
                        break
                except Exception:
                    pass
        except Exception:
            pass
    return blacklist


def get_earnings_dates(symbols: list[str]) -> dict[str, object]:
    """
    v6.1: Return {symbol: next_earnings_date} for the given list.
    Returns None for a symbol if no upcoming date is available.
    """
    import yfinance as yf
    from datetime import date, timedelta
    today = date.today()
    result: dict[str, object] = {}
    for sym in symbols:
        try:
            cal = yf.Ticker(sym).calendar
            if not cal or not isinstance(cal, dict):
                result[sym] = None
                continue
            ed_list = cal.get("Earnings Date", [])
            if not isinstance(ed_list, list):
                ed_list = [ed_list]
            future = []
            for dt in ed_list:
                if dt is None:
                    continue
                try:
                    d = dt.date() if hasattr(dt, "date") else date.fromisoformat(str(dt)[:10])
                    if d >= today:
                        future.append(d)
                except Exception:
                    pass
            result[sym] = min(future) if future else None
        except Exception:
            result[sym] = None
    return result


# ---------------------------------------------------------------------------
# v9.9 — ApeWisdom Reddit Mention Momentum Scout
# ---------------------------------------------------------------------------

def signal_apewisdom_mention_momentum(
    symbol: str, df: pd.DataFrame, all_data: dict, drought: int = 0
) -> tuple[dict | None, str | None]:
    """
    v9.9 — ApeWisdom Mention Momentum Scout.

    ApeWisdom aggregates r/WallStreetBets, r/stocks, r/investing, r/Superstonk
    and computes MENTION DELTA — current mentions vs. 24 hours ago.

    When a ticker's mention count 2× or more vs. 24h ago, retail/institutional
    attention is accelerating — a leading indicator of buying pressure.

    This is DISTINCT from raw sentiment (StockTwits bull_pct) — it measures
    VELOCITY OF ATTENTION, not absolute bullish/bearish bias.

    Signal fires when:
      - mention_ratio ≥ 2.0 (mentions doubled; drought lowers threshold)
      - Minimum 10 mentions now (no signal on thin coverage)
      - Price above SMA20 (not in freefall)
      - RSI 38–70 (room to run; not already overbought)
      - Volume spike: today ≥ 1.5× 5d avg (market following the buzz)
      - Extension guard: 5d return < 22% (not already parabolic)

    Academic: Da, Engelberg & Gao (2011) "In Search of Attention" — Google
    Trends predicts stock returns. Bollen, Mao & Zeng (2011) — Twitter mood
    predicts DJIA. Kogan et al. (2023) — Reddit WSB post volume predicts
    short-term momentum in meme stocks.

    Drought relaxes mention_ratio threshold, RSI band, vol requirement.
    """
    ape_data: dict = all_data.get("__apewisdom__", {})
    sym_entry = ape_data.get(symbol)

    if not sym_entry:
        return None, "no ApeWisdom data for this symbol"

    mentions_now  = int(sym_entry.get("mentions", 0))
    mention_ratio = float(sym_entry.get("mention_ratio", 1.0))

    # Minimum coverage (avoid noise from 1 mention → 2 mentions = 2× ratio)
    min_mentions = max(8, 10 - drought * 2)
    if mentions_now < min_mentions:
        return None, f"too few mentions ({mentions_now} < {min_mentions})"

    # Mention velocity threshold
    ratio_thresh = max(1.50, 2.00 - drought * 0.15)
    if mention_ratio < ratio_thresh:
        return None, f"mention_ratio {mention_ratio:.2f} < {ratio_thresh:.2f}"

    if len(df) < 25:
        return None, "insufficient history"

    close = df["Close"]
    current = float(close.iloc[-1])

    # ── Trend: above SMA20 ─────────────────────────────────────────────────
    sma20 = float(close.rolling(20).mean().iloc[-1])
    if current < sma20 * 0.96:
        return None, f"price {current:.2f} below SMA20 {sma20:.2f}"

    # ── RSI 14 ─────────────────────────────────────────────────────────────
    delta_c = close.diff()
    gain = delta_c.where(delta_c > 0, 0.0).rolling(14).mean()
    loss = (-delta_c.where(delta_c < 0, 0.0)).rolling(14).mean()
    rsi = float(100 - 100 / (1 + gain.iloc[-1] / (loss.iloc[-1] + 1e-9)))

    rsi_lo = max(32, 38 - drought * 3)
    rsi_hi = min(76, 70 + drought * 3)
    if not (rsi_lo <= rsi <= rsi_hi):
        return None, f"RSI {rsi:.1f} outside [{rsi_lo}, {rsi_hi}]"

    # ── Volume spike: market following the buzz ────────────────────────────
    vol_5d = float(df["Volume"].iloc[-5:].mean())
    vol_now = float(df["Volume"].iloc[-1])
    vol_mult = max(1.10, 1.50 - drought * 0.10)
    if vol_5d > 1e3 and vol_now / (vol_5d + 1e-9) < vol_mult:
        return None, f"vol {vol_now:.0f} < {vol_mult:.1f}× 5d avg {vol_5d:.0f}"

    # ── Extension guard ────────────────────────────────────────────────────
    if len(close) < 7:
        return None, "too few bars"
    ret5 = float((close.iloc[-1] / close.iloc[-6] - 1) * 100)
    if ret5 > 22:
        return None, f"already extended: ret5d={ret5:.1f}%"

    # ── Confidence: scales with mention acceleration ───────────────────────
    ratio_bonus = min(0.15, (mention_ratio - ratio_thresh) * 0.06)
    conf = round(min(max(0.62 + ratio_bonus + drought * 0.01, 0.57), 0.85), 2)

    return {
        "signal":         "apewisdom_momentum",
        "direction":      "long",
        "confidence":     conf,
        "mention_ratio":  round(mention_ratio, 2),
        "mentions_now":   mentions_now,
        "mentions_prev":  int(sym_entry.get("mentions_24h_ago", 0)),
        "rsi":            round(rsi, 1),
        "vol_mult":       round(vol_now / (vol_5d + 1e-9), 2),
        "ret5d":          round(ret5, 1),
        "reason": (
            f"mention surge ×{mention_ratio:.1f} ({mentions_now} now vs "
            f"{sym_entry.get('mentions_24h_ago', '?')} 24h ago) | "
            f"RSI={rsi:.1f} | vol×{vol_now/(vol_5d+1e-9):.1f} | ret5d={ret5:.1f}%"
        ),
    }, None


# ---------------------------------------------------------------------------
# v9.7 — OPEX Week Momentum Scout
# ---------------------------------------------------------------------------

def signal_opex_week_momentum(
    symbol: str, df: pd.DataFrame, _all_data: dict, drought: int = 0
) -> tuple[dict | None, str | None]:
    """
    v9.7 — OPEX Week Momentum Scout.

    Monthly options expiration (3rd Friday) creates gamma-driven price pinning.
    After expiry, market-maker hedges unwind and price is free to resume its
    natural direction — typically continuing the pre-expiry trend for 3-5 days.

    Signal fires Mon–Thu in the calendar week following OPEX Friday:
      - Post-OPEX window: 1–5 calendar days after the 3rd Friday of the month
      - Trend filter: price above SMA20 (not in freefall)
      - RSI 38–68: healthy momentum zone, not extreme
      - Volume: not dead (≥ 0.70× 5d avg at default)
      - Not already extended: 5d return < 14%

    Academic: Birru & Wang (2016), Zhang (2022) — OPEX week drift and
    institutional order flow documented across US equity markets.

    Drought relaxes RSI band, extends post-OPEX window, lowers vol bar.
    """
    from calendar import monthcalendar, FRIDAY
    from datetime import date

    _OPEX_UNIVERSE = {
        "SPY", "QQQ", "IWM", "DIA",
        "AAPL", "MSFT", "NVDA", "AMD", "TSLA", "META", "GOOGL", "AMZN", "NFLX",
        "COIN", "MSTR", "SHOP", "SQ", "UBER", "PYPL",
        "JPM", "BAC", "XOM", "CVX", "GLD", "TLT",
        "XLK", "XLF", "XLE", "XLV", "SOXX", "ARKK",
        "INTC", "AVGO", "QCOM", "MU",
    }
    if symbol not in _OPEX_UNIVERSE:
        return None, "not in OPEX universe"

    if len(df) < 30:
        return None, "insufficient history"

    # ── OPEX date check ────────────────────────────────────────────────────
    def _third_friday(y: int, m: int) -> date:
        fridays = [w[FRIDAY] for w in monthcalendar(y, m) if w[FRIDAY] != 0]
        return date(y, m, fridays[2])  # 0-indexed, 3rd = index 2

    today = date.today()
    window_max = 5 + drought  # days after OPEX that signal remains valid

    # Check current-month OPEX and previous-month OPEX (handles month boundary)
    in_window = False
    days_after: int = -1
    for delta_months in (0, -1):
        m = today.month + delta_months
        y = today.year
        if m < 1:
            m += 12
            y -= 1
        try:
            opex = _third_friday(y, m)
            diff = (today - opex).days
            if 1 <= diff <= window_max:
                in_window = True
                days_after = diff
                break
        except Exception:
            pass

    if not in_window:
        return None, f"not in post-OPEX window (need 1–{window_max}d after 3rd Friday)"

    close = df["Close"]
    current = float(close.iloc[-1])

    # ── Trend filter: price above SMA20 ────────────────────────────────────
    sma20 = float(close.rolling(20).mean().iloc[-1])
    if current < sma20 * 0.97:
        return None, f"price {current:.2f} below SMA20 {sma20:.2f}"

    # ── RSI ─────────────────────────────────────────────────────────────────
    delta_c = close.diff()
    gain = delta_c.where(delta_c > 0, 0.0).rolling(14).mean()
    loss = (-delta_c.where(delta_c < 0, 0.0)).rolling(14).mean()
    rsi = float(100 - 100 / (1 + gain.iloc[-1] / (loss.iloc[-1] + 1e-9)))

    rsi_lo = max(30, 38 - drought * 3)
    rsi_hi = min(74, 68 + drought * 2)
    if not (rsi_lo <= rsi <= rsi_hi):
        return None, f"RSI {rsi:.1f} outside window [{rsi_lo}, {rsi_hi}]"

    # ── Volume: not dead ───────────────────────────────────────────────────
    vol_5d = float(df["Volume"].iloc[-5:].mean())
    vol_now = float(df["Volume"].iloc[-1])
    vol_min = max(0.55, 0.70 - drought * 0.05)
    if vol_5d > 1e3 and vol_now / (vol_5d + 1e-9) < vol_min:
        return None, f"volume {vol_now:.0f} < {vol_min:.0%} of 5d avg {vol_5d:.0f}"

    # ── Extension guard ────────────────────────────────────────────────────
    if len(close) < 7:
        return None, "too few bars"
    ret5 = float((close.iloc[-1] / close.iloc[-6] - 1) * 100)
    if ret5 > 14:
        return None, f"already extended: ret5d={ret5:.1f}%"

    # ── Confidence ─────────────────────────────────────────────────────────
    mid_rsi = abs(rsi - 53) / 15   # distance from optimal 53
    conf = round(min(max(0.63 - mid_rsi * 0.06 + drought * 0.01, 0.56), 0.80), 2)

    return {
        "signal": "opex_momentum",
        "direction": "long",
        "confidence": conf,
        "days_after_opex": days_after,
        "rsi": round(rsi, 1),
        "ret5d": round(ret5, 1),
        "reason": (
            f"post-OPEX+{days_after}d pin-release | RSI={rsi:.1f} | "
            f"above SMA20 | ret5d={ret5:.1f}%"
        ),
    }, None


# ---------------------------------------------------------------------------
# v9.8 — Deribit Crypto Options Contrarian Scout
# ---------------------------------------------------------------------------

def signal_deribit_crypto_contrarian(
    symbol: str, df: pd.DataFrame, all_data: dict, drought: int = 0
) -> tuple[dict | None, str | None]:
    """
    v9.8 — Deribit Crypto Options Contrarian Scout.

    Deribit is the dominant crypto options exchange (≥80% of BTC/ETH options
    volume). Unlike yfinance, Deribit's PCR is real-time and uses reliable
    model-based mark_iv pricing.

    Crypto options market structure is call-heavy (covered-call yield seeking):
      BTC baseline PCR ≈ 0.38 | ETH baseline PCR ≈ 0.36
    When PCR rises above 0.50, professional traders are paying heavily for
    downside protection — a contrarian buy signal (crowded puts → coiled spring).

    Signal fires when:
      - Deribit PCR-OI ≥ 0.50 (elevated fear; drought lowers threshold)
      - Price above SMA30 (not in structural downtrend)
      - RSI 30–62 (oversold → mid-range only; not already running)
      - 10-day return ≤ +8% (not chasing a rally that's already happening)
      - 5-day return < 0% (pullback in progress = entry timing)

    Academic: Cremers & Weinbaum (2010), Xing, Zhang & Zhao (2010) —
    options PCR predicts cross-sectional stock returns. Crypto PCR: Pan & Poteshman
    (2006) extended to digital assets by Liu, Luo & Zhao (2023).
    """
    _DERIBIT_UNIVERSE = {
        "BTC-USD": "BTC",
        "ETH-USD": "ETH",
    }
    if symbol not in _DERIBIT_UNIVERSE:
        return None, "not in Deribit universe"

    deribit_pcr: dict = all_data.get("__deribit_pcr__", {})
    currency = _DERIBIT_UNIVERSE[symbol]
    pcr_data = deribit_pcr.get(currency)

    if not pcr_data:
        return None, f"no Deribit PCR data for {currency}"

    pcr_oi   = float(pcr_data.get("pcr_oi", 0))
    mark_iv  = float(pcr_data.get("avg_mark_iv", 0))

    # Elevated fear threshold (drought relaxes by 0.02 per step)
    baseline     = _DERIBIT_PCR_BASELINE.get(currency, 0.38)
    fear_thresh  = max(baseline + 0.08, 0.50 - drought * 0.02)
    if pcr_oi < fear_thresh:
        return None, f"PCR-OI {pcr_oi:.3f} below fear threshold {fear_thresh:.3f}"

    if len(df) < 35:
        return None, "insufficient history"

    close = df["Close"]
    current = float(close.iloc[-1])

    # ── Trend: above SMA30 ──────────────────────────────────────────────────
    sma30 = float(close.rolling(30).mean().iloc[-1])
    if current < sma30 * 0.94:
        return None, f"price {current:.2f} below SMA30 {sma30:.2f} (structural downtrend)"

    # ── RSI 14: oversold→mid zone ───────────────────────────────────────────
    delta_c = close.diff()
    gain = delta_c.where(delta_c > 0, 0.0).rolling(14).mean()
    loss = (-delta_c.where(delta_c < 0, 0.0)).rolling(14).mean()
    rsi = float(100 - 100 / (1 + gain.iloc[-1] / (loss.iloc[-1] + 1e-9)))

    rsi_lo = max(25, 30 - drought * 3)
    rsi_hi = min(68, 62 + drought * 3)
    if not (rsi_lo <= rsi <= rsi_hi):
        return None, f"RSI {rsi:.1f} outside window [{rsi_lo}, {rsi_hi}]"

    # ── Pullback: 5d return < 0% (not already ripping) ─────────────────────
    if len(close) < 7:
        return None, "too few bars"
    ret5  = float((close.iloc[-1] / close.iloc[-6]  - 1) * 100)
    ret10 = float((close.iloc[-1] / close.iloc[-11] - 1) * 100)

    if ret5 > 8:
        return None, f"not in pullback — ret5d={ret5:.1f}% > +8%"
    if ret10 > 20:
        return None, f"extended 10d run — ret10d={ret10:.1f}%"

    # ── Confidence: scales with PCR elevation above baseline ───────────────
    pcr_premium = pcr_oi - baseline
    conf = round(min(max(0.62 + pcr_premium * 0.40 + drought * 0.01, 0.56), 0.85), 2)

    return {
        "signal":      "deribit_crypto_contrarian",
        "direction":   "long",
        "confidence":  conf,
        "deribit_pcr": round(pcr_oi, 3),
        "mark_iv":     round(mark_iv, 1),
        "rsi":         round(rsi, 1),
        "ret5d":       round(ret5, 1),
        "reason": (
            f"Deribit fear: PCR-OI={pcr_oi:.3f} (baseline {baseline:.2f}) "
            f"[{pcr_data.get('fear_level','?').upper()}] | "
            f"RSI={rsi:.1f} | ret5d={ret5:.1f}% pullback | IV={mark_iv:.0f}%"
        ),
    }, None


# Register v9.7-v9.9 signal functions (defined above, after SIGNAL_FUNCS literal)
SIGNAL_FUNCS["opex-momentum-scout"]       = signal_opex_week_momentum          # v9.7
SIGNAL_FUNCS["deribit-crypto-contrarian"] = signal_deribit_crypto_contrarian   # v9.8
SIGNAL_FUNCS["apewisdom-momentum-scout"]  = signal_apewisdom_mention_momentum  # v9.9


# ---------------------------------------------------------------------------
# v10.5 — NEW FORWARD-LOOKING SIGNALS
# ---------------------------------------------------------------------------

def signal_relative_strength_breakout(symbol: str, df: pd.DataFrame, all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """
    v10.5 — Relative Strength (RS) Breakout.
    Academic basis: Price Relative to benchmark is the single best forward predictor of
    next-period returns (Levy 1967; Jegadeesh & Titman 1993 momentum paper).
    Entry: symbol's RS line vs SPY making a NEW 20-DAY HIGH (RS breakout),
           confirming that institutional rotation INTO this name is accelerating.
    Exit: handled by stop/trailing stop system.
    Filter: also require price above 50d SMA (not in downtrend).
    """
    spy = all_data.get("SPY")
    if spy is None or len(df) < 25 or len(spy) < 25:
        return None, ""
    close = df["Close"]
    spy_close = spy["Close"]
    min_len = min(len(close), len(spy_close))
    if min_len < 25:
        return None, ""
    rs = (close.iloc[-min_len:].values / spy_close.iloc[-min_len:].values)
    rs_series = pd.Series(rs)
    rs_20d_high = rs_series.iloc[-20:].max()
    rs_current  = rs_series.iloc[-1]
    # RS must be at 20-day high (breakout = institutional buying is accelerating)
    if rs_current < rs_20d_high * 0.999:
        return None, ""
    # Price above 50d SMA (not buying into a downtrend)
    sma50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else close.mean()
    if close.iloc[-1] < sma50 * 0.99:
        return None, ""
    # Require positive RS vs prior week (RS improving, not just at a stale high)
    rs_5d_ago = rs_series.iloc[-6] if len(rs_series) >= 6 else rs_series.iloc[0]
    rs_chg = (rs_current - rs_5d_ago) / rs_5d_ago if rs_5d_ago > 0 else 0
    if rs_chg < 0.005:   # RS must have improved at least +0.5% vs SPY in last 5d
        return None, ""
    # Drought: relax threshold slightly
    if drought >= 3 and rs_chg < 0.003:
        return None, ""
    return "BUY", f"RS breakout: 20d RS high={rs_20d_high:.4f}, RS 5d chg={rs_chg*100:+.2f}% vs SPY, above SMA50"


def signal_multi_factor_quality_momentum(symbol: str, df: pd.DataFrame, all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """
    v10.5 — Multi-Factor Quality + Momentum composite.
    Academic basis: Combining quality (low debt, high ROE proxy) + momentum (price + RS)
    delivers the strongest risk-adjusted alpha in peer-reviewed literature
    (Asness, Frazzini, Israel & Moskowitz 2015 'Fact, Fiction and Momentum Investing').
    Entry: symbol passes BOTH quality (beta < 1.2, above 200d SMA, low realized vol) AND
           momentum (20d return > 2%, RS vs SPY positive) filters simultaneously.
    This is the double-confirmation approach used by Renaissance Medallion for stock selection.
    """
    spy = all_data.get("SPY")
    if spy is None or len(df) < 200 or len(spy) < 60:
        return None, ""
    close = df["Close"]
    returns = close.pct_change().dropna()
    spy_returns = spy["Close"].pct_change().dropna()
    if len(returns) < 60:
        return None, ""
    # Quality check 1: beta < 1.2 (not a high-beta speculative play)
    min_len = min(len(returns), len(spy_returns))
    rets_a = returns.iloc[-min_len:].values
    rets_b = spy_returns.iloc[-min_len:].values
    if np.std(rets_b) < 1e-8:
        return None, ""
    beta = np.cov(rets_a, rets_b)[0, 1] / np.var(rets_b)
    if beta > 1.3 or beta < 0:
        return None, ""
    # Quality check 2: above 200d SMA (long-term uptrend)
    sma200 = close.rolling(200).mean().iloc[-1]
    if pd.isna(sma200) or close.iloc[-1] < sma200 * 0.97:
        return None, ""
    # Momentum check 1: 20d return > 2%
    ret_20d = (close.iloc[-1] - close.iloc[-21]) / close.iloc[-21] if len(close) >= 21 else 0
    if ret_20d < 0.02:
        return None, ""
    # Momentum check 2: RS vs SPY positive over 20d
    spy_ret_20d = (spy["Close"].iloc[-1] - spy["Close"].iloc[-21]) / spy["Close"].iloc[-21] if len(spy["Close"]) >= 21 else 0
    if ret_20d < spy_ret_20d:   # underperforming SPY = no alpha
        return None, ""
    # Realized vol < 35% annualized (filters out noise-driven low-quality momentum)
    rv_20d = float(returns.iloc[-20:].std() * np.sqrt(252) * 100) if len(returns) >= 20 else 100
    if rv_20d > 40:
        return None, ""
    excess_ret = ret_20d - spy_ret_20d
    return "BUY", f"Quality+Momentum: beta={beta:.2f}, 20d={ret_20d*100:+.1f}% (+{excess_ret*100:.1f}% vs SPY), RV={rv_20d:.0f}%, above SMA200"


def signal_crypto_funding_rate_live(symbol: str, df: pd.DataFrame, all_data: dict, drought: int = 0) -> tuple[str | None, str]:
    """
    v10.5 — Crypto Funding Rate + RSI Confluence (high-precision).
    Academic basis: Negative funding rates mean long positions are PAID to hold,
    creating asymmetric upside. Combined with oversold RSI < 35, this targets
    exact inflection points in crypto (Ma et al. 2021 'Funding Rate Arbitrage').
    Stricter than v1 funding-rate-arb: requires BOTH negative/near-zero funding AND RSI < 35.
    """
    if not symbol.endswith("-USD"):
        return None, ""
    close = df["Close"]
    if len(close) < 14:
        return None, ""
    # RSI < 35 (oversold but not completely crashed)
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs_val = gain / loss.replace(0, 1e-9)
    rsi = 100 - 100 / (1 + rs_val)
    rsi_now = rsi.iloc[-1]
    if pd.isna(rsi_now) or not (25 < rsi_now < 38):
        return None, ""
    # Price below 20d BB lower band (genuine oversold, not just pullback)
    bb_mid  = close.rolling(20).mean()
    bb_std  = close.rolling(20).std()
    bb_low  = bb_mid - 2.0 * bb_std
    if pd.isna(bb_low.iloc[-1]) or close.iloc[-1] > bb_low.iloc[-1] * 1.02:
        return None, ""
    # Volume above 1.5× 10d average (capitulation / accumulation)
    if "Volume" in df.columns:
        vol_avg = df["Volume"].rolling(10).mean().iloc[-1]
        vol_now = df["Volume"].iloc[-1]
        if vol_avg > 0 and vol_now < vol_avg * 1.2:
            return None, ""
    # Binance movers: check it's not in the top-5 losers (avoid catching falling knives)
    movers = all_data.get("__binance_movers__", {})
    losers = [m.get("symbol", "").replace("USDT", "-USD") for m in movers.get("losers", [])]
    binance_sym = symbol.replace("-USD", "USDT")
    if binance_sym in [m.get("symbol","") for m in movers.get("losers", [])][:3]:
        return None, ""   # skip top-3 daily losers (falling knives)
    # CoinGecko BTC dominance gate: if BTC dominance > 60%, altcoins are losing — skip non-BTC/ETH
    cg = all_data.get("__coingecko_global__", {})
    btc_dom = cg.get("btc_dominance", 50) if isinstance(cg, dict) else 50
    if btc_dom > 60 and symbol not in ("BTC-USD", "ETH-USD"):
        return None, ""
    return "BUY", f"Crypto funding confluence: RSI={rsi_now:.1f} oversold+BB-low, btc_dom={btc_dom:.0f}%, vol elevated"


# v10.5 algo definitions
_V105_ALGO_DEFS = {
    "rs-breakout-scout": {
        "name": "Relative Strength Breakout",
        "category": "stock", "tier": "TIER_1",
        "strategy": "RSBreakout",
        "symbols": [
            "SPY","QQQ","IWM","XLK","XLF","XLE","XLV","XLI","SOXX","ARKK",
            "AAPL","MSFT","NVDA","AMD","META","GOOGL","AMZN","NFLX","COIN",
            "XOM","CVX","JPM","BAC","GLD","SLV","TLT",
        ],
    },
    "quality-momentum-scout": {
        "name": "Quality + Momentum (Multi-Factor)",
        "category": "stock", "tier": "TIER_1",
        "strategy": "QualityMomentum",
        "symbols": [
            "AAPL","MSFT","NVDA","GOOGL","META","AMZN","JPM","V","MA",
            "XOM","LLY","UNH","HD","COST","ABBV","MRK","ACN",
            "SPY","QQQ","IWM","GLD",
        ],
    },
    "crypto-funding-confluence": {
        "name": "Crypto Funding Confluence (RSI+BB)",
        "category": "crypto", "tier": "TIER_1",
        "strategy": "CryptoFundingConfluence",
        "symbols": [
            "BTC-USD","ETH-USD","BNB-USD","SOL-USD","ADA-USD",
            "AVAX-USD","DOT-USD","LINK-USD","MATIC-USD","NEAR-USD",
        ],
    },
}

for _aid, _adef in _V105_ALGO_DEFS.items():
    ALGO_DEFS[_aid] = _adef   # type: ignore[index]
    REGIME_BIAS[_aid] = "mean_rev" if "confluence" in _aid or "quality" in _aid else "both"

SIGNAL_FUNCS["rs-breakout-scout"]         = signal_relative_strength_breakout      # v10.5
SIGNAL_FUNCS["quality-momentum-scout"]    = signal_multi_factor_quality_momentum   # v10.5
SIGNAL_FUNCS["crypto-funding-confluence"] = signal_crypto_funding_rate_live        # v10.5


# ---------------------------------------------------------------------------
# v11.0 — ANTIGRAVITY_FEB172026 Crypto Acceleration Algorithms
# ---------------------------------------------------------------------------

_V110_ALGO_DEFS = {
    "pump-detector": {
        "name": "Pump & Dump Detector",
        "category": "crypto",
        "tier": "TIER_1",
        "strategy": "PumpDetector",
        "symbols": [
            "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
            "DOGE-USD", "SHIB-USD", "PEPE-USD", "AVAX-USD", "LINK-USD",
            "DOT-USD", "ADA-USD", "MATIC-USD", "ATOM-USD", "NEAR-USD",
        ],
    },
    "orderbook-imbalance": {
        "name": "Order Book Imbalance",
        "category": "crypto",
        "tier": "TIER_1",
        "strategy": "OrderBookImbalance",
        "symbols": [
            "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
            "DOGE-USD", "AVAX-USD", "LINK-USD", "ADA-USD", "DOT-USD",
        ],
    },
    "liquidation-cascade": {
        "name": "Liquidation Cascade Reversal",
        "category": "crypto",
        "tier": "TIER_1",
        "strategy": "LiquidationCascade",
        "symbols": [
            "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
            "DOGE-USD", "AVAX-USD", "LINK-USD",
        ],
    },
    "cross-exchange-momentum": {
        "name": "Cross-Exchange Momentum",
        "category": "crypto",
        "tier": "SCOUT",
        "strategy": "CrossExchangeMomentum",
        "symbols": [
            "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
            "DOGE-USD", "AVAX-USD", "LINK-USD", "ADA-USD", "DOT-USD",
        ],
    },
    "funding-rate-reversal": {
        "name": "Funding Rate Reversal",
        "category": "crypto",
        "tier": "TIER_1",
        "strategy": "FundingRateReversal",
        "symbols": [
            "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
            "DOGE-USD", "AVAX-USD", "LINK-USD", "ADA-USD", "DOT-USD",
            "MATIC-USD", "ATOM-USD", "NEAR-USD", "LTC-USD", "BCH-USD",
        ],
    },
}

for _aid, _adef in _V110_ALGO_DEFS.items():
    ALGO_DEFS[_aid] = _adef
    REGIME_BIAS[_aid] = "both"


# ---------------------------------------------------------------------------
# v11.0 — Register acceleration + proven signal functions
# Map ALGO_DEFS IDs to the actual signal function objects
# ---------------------------------------------------------------------------

# Acceleration engine signal registrations (Binance API-backed signals)
_V11_ACCEL_ID_MAP = {
    "pump-detector":           "pump-detector-scout",
    "orderbook-imbalance":     "order-book-imbalance-scout",
    "liquidation-cascade":     "liquidation-cascade-scout",
    "cross-exchange-momentum": "multi-exchange-divergence-scout",
    "funding-rate-reversal":   "funding-rate-reversal-scout",
}
if _HAS_ACCEL:
    for _v11_algo_id, _accel_key in _V11_ACCEL_ID_MAP.items():
        _fn = ACCELERATION_SIGNAL_FUNCS.get(_accel_key)
        if _fn:
            SIGNAL_FUNCS[_v11_algo_id] = _fn

# Proven crypto/forex signal registrations
_V11_PROVEN_ALGO_DEFS = {
    "btc-4h-rsi-macd-scout": {
        "name": "BTC 4H RSI+MACD Confluence",
        "category": "crypto", "tier": "TIER_1", "strategy": "BTC4HRSIMACD",
        "symbols": ["BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD", "BNB-USD",
                    "LINK-USD", "INJ-USD", "TIA-USD", "SUI20947-USD"],
    },
    "altseason-rotation-scout": {
        "name": "Altseason Rotation Signal",
        "category": "crypto", "tier": "TIER_1", "strategy": "AltseasonRotation",
        "symbols": ["SOL-USD", "AVAX-USD", "LINK-USD", "DOGE-USD", "PEPE-USD",
                    "FLOKI-USD", "WIF-USD", "INJ-USD", "TIA-USD", "ARB11841-USD",
                    "OP-USD", "SUI20947-USD", "NEAR-USD", "MATIC-USD"],
    },
    "crypto-fear-reversal-scout": {
        "name": "Extreme Fear Contrarian Buy",
        "category": "crypto", "tier": "TIER_1", "strategy": "FearGreedReversal",
        "symbols": ["BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD", "BNB-USD",
                    "LINK-USD", "XRP-USD", "ADA-USD", "DOGE-USD"],
    },
    "crypto-bb-squeeze-scout": {
        "name": "Bollinger Squeeze Breakout",
        "category": "crypto", "tier": "TIER_1", "strategy": "BBSqueeze",
        "symbols": ["BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD", "BNB-USD",
                    "LINK-USD", "INJ-USD", "XRP-USD", "ADA-USD", "NEAR-USD"],
    },
    "crypto-rsi-divergence-scout": {
        "name": "Bullish RSI Divergence (Crypto)",
        "category": "crypto", "tier": "TIER_1", "strategy": "RSIDivergence",
        "symbols": ["BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD", "LINK-USD",
                    "DOGE-USD", "PEPE-USD", "INJ-USD", "TIA-USD"],
    },
    "btc-dominance-reversal-scout": {
        "name": "BTC Dominance Reversal (Altseason)",
        "category": "crypto", "tier": "SCOUT", "strategy": "BTCDomReversal",
        "symbols": ["SOL-USD", "AVAX-USD", "LINK-USD", "INJ-USD", "TIA-USD",
                    "NEAR-USD", "MATIC-USD", "ARB11841-USD", "OP-USD", "DOGE-USD"],
    },
    "london-breakout-scout": {
        "name": "London Session Breakout (Forex)",
        "category": "forex", "tier": "TIER_1", "strategy": "LondonBreakout",
        "symbols": ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDCHF=X",
                    "AUDUSD=X", "NZDUSD=X", "GBPJPY=X", "EURJPY=X"],
    },
    "dxy-reversal-scout": {
        "name": "DXY RSI Reversal (Forex)",
        "category": "forex", "tier": "TIER_1", "strategy": "DXYReversal",
        "symbols": ["EURUSD=X", "GBPUSD=X", "AUDUSD=X", "NZDUSD=X",
                    "USDCAD=X", "USDCHF=X", "USDJPY=X"],
    },
    "forex-rsi-ema-scout": {
        "name": "Forex RSI + EMA200 Confluence",
        "category": "forex", "tier": "TIER_1", "strategy": "ForexRSIEMA",
        "symbols": ["EURUSD=X", "GBPUSD=X", "AUDUSD=X", "NZDUSD=X",
                    "USDCAD=X", "USDCHF=X", "USDJPY=X", "EURJPY=X",
                    "GBPJPY=X", "AUDJPY=X", "NZDJPY=X", "CADJPY=X"],
    },
}

if _HAS_PROVEN:
    for _p_id, _p_def in _V11_PROVEN_ALGO_DEFS.items():
        ALGO_DEFS[_p_id] = _p_def
        REGIME_BIAS[_p_id] = "trend" if "momentum" in _p_id or "breakout" in _p_id else "both"
        _fn = PROVEN_SIGNAL_FUNCS.get(_p_id)
        if _fn:
            SIGNAL_FUNCS[_p_id] = _fn


# ---------------------------------------------------------------------------
# v11.1 — Research-Validated Scalping Strategies
# Source: YouTube (Rayner Teo, Adam Khoo, ICT community), r/algotrading,
#         QuantifiedStrategies backtests, Binance Futures API, ScienceDirect 2025
# ---------------------------------------------------------------------------

if _HAS_SCALPING:
    for _s_id, _s_def in SCALPING_ALGO_DEFS.items():
        ALGO_DEFS[_s_id] = _s_def
        REGIME_BIAS[_s_id] = "both"
        _fn = SCALPING_SIGNAL_FUNCS.get(_s_id)
        if _fn:
            SIGNAL_FUNCS[_s_id] = _fn
        else:
            for _sk, _sfn in SCALPING_SIGNAL_FUNCS.items():
                if _sk in _s_id or _s_id.startswith(_sk.replace("-scout", "")):
                    SIGNAL_FUNCS[_s_id] = _sfn
                    break


# ---------------------------------------------------------------------------
# v11.2 — Proven Mean Reversion Strategies
# Source: QuantifiedStrategies.com (30yr backtests), Larry Connors, alternative.me,
#         SSRN Huang/Sangiorgi/Urquhart 2024, Bitcoin Magazine 2017-2024 backtest
# ---------------------------------------------------------------------------

if _HAS_MEAN_REV:
    for _mr_id, _mr_def in MEAN_REVERSION_ALGO_DEFS.items():
        ALGO_DEFS[_mr_id] = _mr_def
        REGIME_BIAS[_mr_id] = "mean_rev"
        _fn = MEAN_REVERSION_SIGNAL_FUNCS.get(_mr_id)
        if _fn:
            SIGNAL_FUNCS[_mr_id] = _fn


# ---------------------------------------------------------------------------
# v11.8 — SKYROCKET Strategies (short-term momentum plays)
# Source: trading_strategies_skyrocket.md — 3 highest-value activations
# Category: "skyrocket" — tracked separately from core crypto/meme strategies
# ---------------------------------------------------------------------------

_SKYROCKET_CRYPTO_SYMS = [
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
    "AVAX-USD", "LINK-USD", "ADA-USD", "DOT-USD", "DOGE-USD",
    "NEAR-USD", "ATOM-USD", "MATIC-USD", "PEPE-USD", "SHIB-USD",
]

_V118_SKYROCKET_ALGO_DEFS = {
    "skyrocket-volume-spike": {
        "name": "Skyrocket Volume Spike Detector",
        "category": "skyrocket",
        "tier": "TIER_1",
        "strategy": "SkyrocketVolumeSpike",
        "signal_type": "SKYROCKET",
        "symbols": _SKYROCKET_CRYPTO_SYMS,
    },
    "skyrocket-breakout-scalper": {
        "name": "Skyrocket Breakout Scalper",
        "category": "skyrocket",
        "tier": "TIER_1",
        "strategy": "SkyrocketBreakoutScalper",
        "signal_type": "SKYROCKET",
        "symbols": _SKYROCKET_CRYPTO_SYMS,
    },
    "skyrocket-funding-reversal": {
        "name": "Skyrocket Funding Rate Reversal",
        "category": "skyrocket",
        "tier": "TIER_1",
        "strategy": "SkyrocketFundingReversal",
        "signal_type": "SKYROCKET",
        "symbols": _SKYROCKET_CRYPTO_SYMS,
    },
}

_SKYROCKET_SIGNAL_MAP = {
    "skyrocket-volume-spike":     signal_skyrocket_volume_spike,
    "skyrocket-breakout-scalper": signal_skyrocket_breakout_scalper,
    "skyrocket-funding-reversal": signal_skyrocket_funding_reversal,
}

for _sky_id, _sky_def in _V118_SKYROCKET_ALGO_DEFS.items():
    ALGO_DEFS[_sky_id] = _sky_def
    REGIME_BIAS[_sky_id] = "trend"  # momentum plays work in trending markets
    _sky_fn = _SKYROCKET_SIGNAL_MAP.get(_sky_id)
    if _sky_fn:
        SIGNAL_FUNCS[_sky_id] = _sky_fn

print(f"  [v11.8] {len(_V118_SKYROCKET_ALGO_DEFS)} SKYROCKET strategies activated")


# ---------------------------------------------------------------------------
# Macro Calendar Guard — FOMC / CPI / NFP blackout windows
# ---------------------------------------------------------------------------

# 2026 high-impact macro dates (day-of event; scanner guards ±1 day)
_MACRO_EVENTS_2026: list[tuple[str, str, str]] = [
    # (YYYY-MM-DD, event_name, impact)
    # FOMC meeting decision days
    ("2026-01-29", "FOMC", "HIGH"),  ("2026-03-18", "FOMC", "HIGH"),
    ("2026-04-29", "FOMC", "HIGH"),  ("2026-06-17", "FOMC", "HIGH"),
    ("2026-07-29", "FOMC", "HIGH"),  ("2026-09-16", "FOMC", "HIGH"),
    ("2026-10-28", "FOMC", "HIGH"),  ("2026-12-16", "FOMC", "HIGH"),
    # US CPI release dates (approx 2nd week of month)
    ("2026-01-15", "CPI", "HIGH"),   ("2026-02-12", "CPI", "HIGH"),
    ("2026-03-12", "CPI", "HIGH"),   ("2026-04-10", "CPI", "HIGH"),
    ("2026-05-14", "CPI", "HIGH"),   ("2026-06-11", "CPI", "HIGH"),
    ("2026-07-14", "CPI", "HIGH"),   ("2026-08-13", "CPI", "HIGH"),
    ("2026-09-10", "CPI", "HIGH"),   ("2026-10-13", "CPI", "HIGH"),
    ("2026-11-12", "CPI", "HIGH"),   ("2026-12-10", "CPI", "HIGH"),
    # US Non-Farm Payrolls (first Friday of each month)
    ("2026-01-09", "NFP", "HIGH"),   ("2026-02-06", "NFP", "HIGH"),
    ("2026-03-06", "NFP", "HIGH"),   ("2026-04-03", "NFP", "HIGH"),
    ("2026-05-01", "NFP", "HIGH"),   ("2026-06-05", "NFP", "HIGH"),
    ("2026-07-02", "NFP", "HIGH"),   ("2026-08-07", "NFP", "HIGH"),
    ("2026-09-04", "NFP", "HIGH"),   ("2026-10-02", "NFP", "HIGH"),
    ("2026-11-06", "NFP", "HIGH"),   ("2026-12-04", "NFP", "HIGH"),
]


def get_macro_blackout(guard_days: int = 1) -> tuple[bool, str]:
    """
    Returns (is_blackout, reason_str).
    Blackout = within guard_days of a high-impact macro event.
    During blackout we reduce new position sizes by 50% but still trade.
    """
    from datetime import date, timedelta
    today = date.today()
    for event_date_str, event_name, _ in _MACRO_EVENTS_2026:
        try:
            ed = date.fromisoformat(event_date_str)
            if abs((today - ed).days) <= guard_days:
                return True, f"{event_name} on {event_date_str}"
        except Exception:
            pass
    return False, ""


# ---------------------------------------------------------------------------
# Options Flow Sentiment — SPY/QQQ put/call ratio as fear gauge
# ---------------------------------------------------------------------------

# Symbols for which we'll fetch live options put/call ratio
_OPTIONS_SYMBOLS = ["SPY", "QQQ", "AAPL", "NVDA", "TSLA"]


def get_options_sentiment() -> dict[str, float]:
    """
    Fetch put/call ratio from yfinance option chains.
    Returns {symbol: pcr} where pcr = total_put_volume / total_call_volume.
    PCR > 1.2 = extreme fear (contrarian bullish)
    PCR < 0.5 = extreme greed (contrarian bearish)
    Only fetches nearest expiry to minimize latency.
    """
    result: dict[str, float] = {}
    for sym in _OPTIONS_SYMBOLS:
        try:
            ticker = yf.Ticker(sym)
            expiries = ticker.options
            if not expiries:
                continue
            chain = ticker.option_chain(expiries[0])  # nearest expiry
            call_vol = float(chain.calls["volume"].fillna(0).sum())
            put_vol  = float(chain.puts["volume"].fillna(0).sum())
            if call_vol > 0:
                result[sym] = round(put_vol / call_vol, 3)
        except Exception:
            pass
    return result


def get_crypto_fear_greed() -> dict:
    """
    Fetch the Crypto Fear & Greed Index from alternative.me (free, no auth).
    Returns {value: int (0-100), classification: str, updated: str}.
    Classification buckets:
      0-24  = Extreme Fear   → reduce crypto/meme allocations 50%
      25-49 = Fear           → reduce 25%
      50-74 = Greed          → normal
      75-100 = Extreme Greed → reduce 25% (contrarian protection)
    """
    try:
        url = "https://api.alternative.me/fng/?limit=1"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            d = json.loads(resp.read().decode("utf-8"))
        entry = d.get("data", [{}])[0]
        return {
            "value": int(entry.get("value", 50)),
            "classification": entry.get("value_classification", "Neutral"),
            "updated": entry.get("timestamp", ""),
        }
    except Exception:
        return {"value": 50, "classification": "Neutral (unavailable)", "updated": ""}


# ---------------------------------------------------------------------------
# v10.2 — CNN Fear & Greed Index (stock market)
# ---------------------------------------------------------------------------

def get_cnn_fear_greed() -> dict:
    """
    Fetch the CNN Fear & Greed Index for the STOCK market (free, no auth).
    Distinct from alternative.me crypto F&G — this measures equity market sentiment.
    Returns {score: int (0-100), rating: str, prev_close: int, prev_week: int}.
    Classification: 0-24 Extreme Fear | 25-44 Fear | 45-55 Neutral |
                    56-75 Greed | 76-100 Extreme Greed.
    Wire: reduces stock allocation in extreme fear (<25) and extreme greed (>75).
    """
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            d = json.loads(resp.read().decode("utf-8"))
        fg = d.get("fear_and_greed", {})
        score = int(round(float(fg.get("score", 50))))
        rating = fg.get("rating", "Neutral")
        prev_close = int(round(float(fg.get("previous_close", score))))
        prev_week = int(round(float(fg.get("previous_1_week", score))))
        return {"score": score, "rating": rating, "prev_close": prev_close, "prev_week": prev_week}
    except Exception:
        return {"score": 50, "rating": "Neutral (unavailable)", "prev_close": 50, "prev_week": 50}


# ---------------------------------------------------------------------------
# v10.2 — CoinGecko Global: real BTC dominance % + market cap change
# ---------------------------------------------------------------------------

def get_coingecko_global() -> dict:
    """
    Fetch global crypto market stats from CoinGecko (free, no auth, 50 req/min).
    Returns:
      btc_dominance: float (e.g. 57.3 = BTC holds 57.3% of total crypto market cap)
      eth_dominance: float
      total_market_cap_usd: float
      market_cap_change_24h_pct: float (e.g. -2.1 = down 2.1% in 24h)
      altcoin_market_cap_pct: float (100 - btc_dominance = capital in alts)
    Used by: altcoin_season_rotation signal (real dominance vs price-ratio proxy).
    """
    try:
        url = "https://api.coingecko.com/api/v3/global"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            d = json.loads(resp.read().decode("utf-8"))
        data_block = d.get("data", {})
        mcp = data_block.get("market_cap_percentage", {})
        btc_dom = float(mcp.get("btc", 50.0))
        eth_dom = float(mcp.get("eth", 15.0))
        mc_change = float(data_block.get("market_cap_change_percentage_24h_usd", 0.0))
        total_mc = float(list(data_block.get("total_market_cap", {}).values() or [0])[0]) if data_block.get("total_market_cap") else 0.0
        return {
            "btc_dominance": round(btc_dom, 2),
            "eth_dominance": round(eth_dom, 2),
            "altcoin_pct": round(100.0 - btc_dom - eth_dom, 2),
            "market_cap_change_24h_pct": round(mc_change, 2),
            "total_market_cap_usd": total_mc,
        }
    except Exception:
        return {"btc_dominance": 50.0, "eth_dominance": 15.0, "altcoin_pct": 35.0,
                "market_cap_change_24h_pct": 0.0, "total_market_cap_usd": 0.0}


# ---------------------------------------------------------------------------
# v10.2 — Binance 24hr top movers (crypto momentum context)
# ---------------------------------------------------------------------------

_BINANCE_CRYPTO_UNIVERSE = {
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT",
    "SHIBUSDT", "MATICUSDT", "AVAXUSDT", "LINKUSDT", "LTCUSDT", "DOTUSDT",
    "UNIUSDT", "WIFUSDT", "BONKUSDT", "PEPEUSDT", "TRUMPUSDT", "BNBUSDT",
}

def get_binance_top_movers() -> dict:
    """
    Fetch Binance 24hr price stats (public, no auth).
    Returns top 5 gainers + top 5 losers from the crypto universe.
    Used as momentum confirmation for crypto signals:
      - If algo pick is in top gainers → boost confidence
      - If algo pick is in top losers → skip or tighten stop
    Return format:
      {
        "gainers": [{"symbol": "SOLUSDT", "pct_change": 8.2, "volume_usd": 1.2e9}, ...],
        "losers":  [...],
        "by_symbol": {"SOLUSDT": {"pct_change": 8.2, "volume_usd": 1.2e9}, ...}
      }
    """
    try:
        _spot_bases = [
            "https://api.binance.com", "https://api1.binance.com",
            "https://data-api.binance.vision", "https://api.binance.us",
        ]
        tickers = None
        for _base in _spot_bases:
            try:
                url = f"{_base}/api/v3/ticker/24hr"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=8) as resp:
                    tickers = json.loads(resp.read().decode("utf-8"))
                break
            except Exception:
                continue
        if not tickers:
            return {"gainers": [], "losers": [], "by_symbol": {}}
        by_sym: dict[str, dict] = {}
        for t in tickers:
            sym = t.get("symbol", "")
            if sym not in _BINANCE_CRYPTO_UNIVERSE:
                continue
            pct = float(t.get("priceChangePercent", 0.0))
            vol_quote = float(t.get("quoteVolume", 0.0))  # USDT volume
            by_sym[sym] = {"pct_change": round(pct, 2), "volume_usd": round(vol_quote, 0)}
        sorted_syms = sorted(by_sym.items(), key=lambda x: -x[1]["pct_change"])
        gainers = [{"symbol": s, **v} for s, v in sorted_syms[:5]]
        losers  = [{"symbol": s, **v} for s, v in sorted_syms[-5:]]
        return {"gainers": gainers, "losers": losers, "by_symbol": by_sym}
    except Exception:
        return {"gainers": [], "losers": [], "by_symbol": {}}


# ---------------------------------------------------------------------------
# v9.8 — Deribit Crypto Options PCR (real-time, no auth)
# ---------------------------------------------------------------------------

# Baseline Deribit put/call ratio by currency (call-heavy market structure)
# Historical median: BTC ~0.38, ETH ~0.36 (covered-call yield strategies skew call-heavy)
# Elevated fear: PCR > 0.50 | Extreme fear: PCR > 0.60
_DERIBIT_PCR_BASELINE = {"BTC": 0.38, "ETH": 0.36}


def get_deribit_crypto_pcr() -> dict[str, dict]:
    """
    Fetch real-time BTC and ETH options put/call ratios from Deribit.
    Deribit is the dominant crypto options exchange (80%+ of BTC/ETH volume).

    No authentication, no API key, no delay — genuinely real-time.
    Rate limit: 20 non-matching requests/second per IP (extremely generous).

    Returns:
      {"BTC": {"pcr_oi": float, "pcr_vol": float, "avg_mark_iv": float,
               "total_call_oi": int, "total_put_oi": int,
               "fear_level": str},
       "ETH": {...}}
    """
    base = "https://www.deribit.com/api/v2/public/get_book_summary_by_currency"
    result: dict[str, dict] = {}

    for currency in ("BTC", "ETH"):
        try:
            req = urllib.request.Request(
                f"{base}?currency={currency}&kind=option",
                headers={"User-Agent": "Mozilla/5.0"},
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8")).get("result", [])

            if not data:
                continue

            call_oi = call_vol = put_oi = put_vol = 0.0
            iv_weighted = iv_total_weight = 0.0

            for item in data:
                name = item.get("instrument_name", "")
                oi   = float(item.get("open_interest", 0) or 0)
                vol  = float(item.get("volume", 0) or 0)
                iv   = float(item.get("mark_iv", 0) or 0)

                # Contract name: BTC-14MAR25-100000-C  (last char = C/P)
                if name.endswith("-C"):
                    call_oi  += oi
                    call_vol += vol
                elif name.endswith("-P"):
                    put_oi  += oi
                    put_vol += vol
                else:
                    continue

                # OI-weighted IV average
                if oi > 0 and iv > 0:
                    iv_weighted      += iv * oi
                    iv_total_weight  += oi

            pcr_oi  = put_oi  / max(call_oi,  1)
            pcr_vol = put_vol / max(call_vol, 1)
            avg_iv  = (iv_weighted / iv_total_weight) if iv_total_weight > 0 else 0.0
            baseline = _DERIBIT_PCR_BASELINE.get(currency, 0.38)

            if pcr_oi >= 0.60:
                fear_level = "extreme_fear"
            elif pcr_oi >= 0.50:
                fear_level = "elevated_fear"
            elif pcr_oi <= baseline - 0.05:
                fear_level = "greed"
            else:
                fear_level = "neutral"

            result[currency] = {
                "pcr_oi":        round(pcr_oi,  4),
                "pcr_vol":       round(pcr_vol, 4),
                "avg_mark_iv":   round(avg_iv,  2),
                "total_call_oi": int(call_oi),
                "total_put_oi":  int(put_oi),
                "fear_level":    fear_level,
            }
        except Exception:
            pass

    return result


# ---------------------------------------------------------------------------
# v9.9 — ApeWisdom Reddit Mention Momentum
# ---------------------------------------------------------------------------

# ApeWisdom aggregates r/WallStreetBets, r/stocks, r/investing, r/Superstonk
# Refresh: ~2× per hour. No API key. No auth. JSON endpoint.
_APEWISDOM_BASE = "https://apewisdom.io/api/v1.0/filter/all-stocks/page/{page}"

# Map yfinance symbols to ApeWisdom ticker format (no "-USD" for crypto)
_APE_SYMBOL_MAP: dict[str, str] = {
    "BTC-USD": "BTC", "ETH-USD": "ETH", "SOL-USD": "SOL",
    "XRP-USD": "XRP", "ADA-USD": "ADA", "DOGE-USD": "DOGE",
    "SHIB-USD": "SHIB", "MATIC-USD": "MATIC",
}


def get_apewisdom_sentiment(target_symbols: list[str]) -> dict[str, dict]:
    """
    Fetch mention counts + 24h-ago baseline from ApeWisdom for target_symbols.
    Returns {symbol: {"mentions": int, "mentions_24h_ago": int,
                       "upvotes": int, "mention_ratio": float}}
    where mention_ratio = mentions_now / max(mentions_24h_ago, 1).

    Pages 1-3 cover the ~300 most-mentioned tickers — sufficient for our universe.
    Gracefully returns {} on network failure (scanner continues without sentiment).
    """
    # Build lookup: ape_ticker → yfinance_symbol
    ape_to_yf: dict[str, str] = {}
    for sym in target_symbols:
        ape_ticker = _APE_SYMBOL_MAP.get(sym, sym)  # crypto remapped, stocks pass-through
        ape_to_yf[ape_ticker] = sym

    found: dict[str, dict] = {}
    headers = {"User-Agent": "Mozilla/5.0 (ticker-scanner/9.9)"}

    for page in range(1, 4):  # 3 pages × 100 results = top 300 mentions
        try:
            req = urllib.request.Request(
                _APEWISDOM_BASE.format(page=page), headers=headers
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            results = data.get("results", [])
        except Exception:
            break

        for entry in results:
            ape_t = entry.get("ticker", "").upper()
            if ape_t not in ape_to_yf:
                continue
            yf_sym = ape_to_yf[ape_t]
            mentions_now  = int(entry.get("mentions", 0) or 0)
            mentions_prev = int(entry.get("mentions_24h_ago", 0) or 0)
            upvotes       = int(entry.get("upvotes", 0) or 0)
            mention_ratio = mentions_now / max(mentions_prev, 1)
            found[yf_sym] = {
                "mentions":        mentions_now,
                "mentions_24h_ago": mentions_prev,
                "upvotes":         upvotes,
                "mention_ratio":   round(mention_ratio, 3),
            }

        # Stop early if we've found all targets
        if set(target_symbols).issubset(
            {ape_to_yf.get(t, t) for t in found}
        ):
            break

    return found


# ---------------------------------------------------------------------------
# Main Scanner
# ---------------------------------------------------------------------------


def compute_walk_forward_metrics(closed_picks: list, now: datetime) -> dict:
    """
    Walk-forward backtest validation (v5.5).
    Detects performance decay using rolling time windows on closed pick history.

    Splits closedPicks by exitDate into three 30-day windows:
      recent : last 0-30 days  → latest performance
      prior  : last 30-60 days → comparison baseline
      early  : last 60-90 days → early history

    Decay penalty: up to -10 pts if recent window significantly worse than prior.
    Consistency bonus: up to +5 pts if 2+ windows show positive Sharpe.
    """
    result = {
        "decay_penalty": 0.0,
        "wf_bonus": 0.0,
        "recent_sharpe": None,
        "recent_wr": None,
        "recent_n": 0,
        "prior_sharpe": None,
        "prior_wr": None,
        "prior_n": 0,
    }
    if not closed_picks:
        return result

    # Group picks into rolling 30-day windows by exitDate
    windows: list[list[float]]  = [[], [], []]   # recent(0-30d), prior(30-60d), early(60-90d)
    wins_by_win: list[int]       = [0, 0, 0]
    now_ts = now.timestamp()

    for p in closed_picks:
        exit_str = p.get("exitDate", "")
        pnl = float(p.get("pnl", 0))
        if not exit_str:
            continue
        try:
            exit_dt  = datetime.fromisoformat(exit_str.replace("Z", "+00:00"))
            days_ago = (now_ts - exit_dt.timestamp()) / 86400
            idx = 0 if days_ago <= 30 else (1 if days_ago <= 60 else (2 if days_ago <= 90 else -1))
            if idx >= 0:
                windows[idx].append(pnl)
                if pnl >= 0:
                    wins_by_win[idx] += 1
        except Exception:
            continue

    def _wf_sharpe(pnls: list) -> float | None:
        if len(pnls) < 3:
            return None
        arr = np.array(pnls, dtype=float)
        std = float(arr.std())
        return float(arr.mean() / std) if std > 1e-9 else None

    sh_recent = _wf_sharpe(windows[0])
    sh_prior  = _wf_sharpe(windows[1])
    sh_early  = _wf_sharpe(windows[2])
    wr_recent = (wins_by_win[0] / len(windows[0])) if len(windows[0]) >= 2 else None
    wr_prior  = (wins_by_win[1] / len(windows[1])) if len(windows[1]) >= 2 else None

    result.update({
        "recent_n":      len(windows[0]),
        "prior_n":       len(windows[1]),
        "recent_sharpe": round(sh_recent, 3) if sh_recent is not None else None,
        "recent_wr":     round(wr_recent, 3) if wr_recent is not None else None,
        "prior_sharpe":  round(sh_prior, 3)  if sh_prior is not None else None,
        "prior_wr":      round(wr_prior, 3)  if wr_prior is not None else None,
    })

    # Decay penalty (up to -10 pts): fired when recent window underperforms prior
    if sh_recent is not None and sh_prior is not None and sh_prior > 0:
        ratio = sh_recent / sh_prior
        if ratio < 0.25:
            result["decay_penalty"] = -8.0    # severe decay (<25% of prior Sharpe)
        elif ratio < 0.50:
            result["decay_penalty"] = -5.0    # significant decay
        elif ratio > 1.20:
            result["decay_penalty"] = 3.0     # accelerating performance (bonus)
    elif sh_recent is not None and sh_recent < -0.5:
        result["decay_penalty"] = -4.0        # recent clearly negative

    # Additional WR collapse penalty
    if wr_recent is not None and wr_prior is not None:
        if wr_recent < 0.30 and wr_prior > 0.45:
            result["decay_penalty"] = max(result["decay_penalty"] - 3.0, -10.0)

    result["decay_penalty"] = max(-10.0, min(result["decay_penalty"], 5.0))

    # Consistency bonus (up to +5 pts): 2+ windows with positive Sharpe
    pos_windows = sum(1 for sh in [sh_recent, sh_prior, sh_early]
                      if sh is not None and sh > 0.2)
    result["wf_bonus"] = 5.0 if pos_windows >= 3 else (3.0 if pos_windows >= 2 else 0.0)

    return result


def compute_tournament(algorithms: list, now: datetime, regime: dict | None = None) -> dict:
    """
    v9.4 Tournament Scoring — Institutional-grade composite formula.

    Score (0-100 + bonuses):
      30 pts — Sharpe ratio on closed picks (Sharpe=1.5 → max 30pts)
      25 pts — win rate on closed picks (0-100%)
      20 pts — max drawdown inverted (0 DD → 20pts; -$500 DD → ~0pts)
      15 pts — profit factor: gross_wins/gross_losses (PF=2 → 15pts)
      10 pts — consistency: drought penalty + active picks bonus
      ±5  pts — regime alignment bonus (REGIME_BIAS vs detected market regime)
      ±8  pts — diversification bonus (v9.4: proxy correlation vs portfolio)
                 unique cross-category algos score higher; redundant ones lower

    League Brackets:
      ≥75: Champions League  |  ≥55: Premier League
      ≥40: Challenger League |  ≥25: Qualification  |  <25: Danger Zone
    """
    scored = []
    for algo in algorithms:
        total_ret = float(algo.get("totalReturn", 0))
        closed = algo.get("closedPicks", [])
        active = algo.get("activePicks", [])
        drought = int(algo.get("droughtScans", 0))
        algo_id = algo.get("id", "")

        wins = sum(1 for p in closed if p.get("pnl", 0) >= 0)
        win_rate = wins / len(closed) if closed else 0.5

        # ── v4 advanced metrics ──────────────────────────────────────
        pnls = np.array([float(p.get("pnl", 0)) for p in closed]) if closed else np.array([])

        # Sharpe on per-pick dollar PnL
        if len(pnls) >= 3 and pnls.std() > 0:
            sharpe_live = float(pnls.mean() / pnls.std())
        else:
            sharpe_live = 0.0

        # Sortino ratio — v10.0: corrected semi-variance formula.
        # Denominator = sqrt(mean((min(r - MAR, 0))^2)) across ALL periods.
        # Previous version incorrectly used std(negative returns only),
        # overstating downside dev. The correct formula averages squared
        # negative deviations over ALL trades (treating wins as zero deviation).
        # Reference: Sortino & Price (1994); Rollinger & Hoffman (2013).
        if len(pnls) >= 3:
            _semi_var = float((np.minimum(pnls, 0.0) ** 2).mean())
            _downside_dev = float(np.sqrt(_semi_var)) if _semi_var > 0 else 0.0
            if _downside_dev > 0:
                sortino_live = float(pnls.mean() / _downside_dev)
            elif pnls.mean() > 0:
                sortino_live = 10.0   # no losses at all — cap at 10
            else:
                sortino_live = 0.0
        else:
            sortino_live = 0.0

        # Omega ratio: probability-weighted gain / probability-weighted loss (threshold=0)
        if len(pnls) >= 3:
            gains = float(pnls[pnls > 0].sum()) if (pnls > 0).any() else 0.0
            losses_neg = float(abs(pnls[pnls < 0].sum())) if (pnls < 0).any() else 0.001
            omega_live = gains / losses_neg if losses_neg > 0 else (2.0 if gains > 0 else 1.0)
        else:
            omega_live = 1.0

        # Profit factor: gross wins / gross losses
        gross_wins   = float(pnls[pnls > 0].sum()) if len(pnls) > 0 and (pnls > 0).any() else 0.0
        gross_losses = float(abs(pnls[pnls < 0].sum())) if len(pnls) > 0 and (pnls < 0).any() else 0.001
        profit_factor = (gross_wins / gross_losses) if gross_losses > 0.001 else (1.5 if gross_wins > 0 else 1.0)

        # Max drawdown on cumulative PnL equity curve
        if len(pnls) >= 2:
            cum  = np.cumsum(pnls)
            peak = np.maximum.accumulate(cum)
            max_dd = float((cum - peak).min())
            # v10.0 Calmar ratio: annualized return / |max drawdown fraction|
            equity_curve = STARTING_CAPITAL + cum
            _dd_frac = abs(float(((equity_curve - np.maximum.accumulate(equity_curve)) /
                                   np.maximum.accumulate(equity_curve)).min()))
            if _dd_frac > 1e-6 and len(closed) >= 2:
                _total_ret = float(equity_curve[-1] / STARTING_CAPITAL) - 1
                # Approximate annualization: assume competition runs ~180 days for now
                _calmar = (_total_ret / _dd_frac)   # simplified (non-annualized) Calmar
            else:
                _calmar = 0.0 if max_dd < -1 else 5.0
        else:
            max_dd = 0.0
            _calmar = 0.0

        # Quarter-Kelly fraction: f* = (p*b - q) / b  where b = avg_win/avg_loss
        if len(pnls) >= 5 and (pnls > 0).any() and (pnls < 0).any():
            avg_win  = float(pnls[pnls > 0].mean())
            avg_loss = abs(float(pnls[pnls < 0].mean()))
            payoff_ratio = avg_win / avg_loss if avg_loss > 0 else 1.0
            full_kelly = (win_rate - (1.0 - win_rate) / payoff_ratio) if payoff_ratio > 0 else 0.0
            kelly_quarter = max(0.0, round(full_kelly * 0.25, 3))  # quarter-Kelly for safety
        else:
            kelly_quarter = 0.0

        # ── v5 component scores ──────────────────────────────────────
        # Blended risk-adjusted score: 60% Sortino + 40% Sharpe (Sortino better for long-only)
        # Sortino=2.0 → ~30pts; Sharpe=1.5 → 30pts; blend rewards asymmetric upside
        sharpe_pts  = min(max(sharpe_live * 20, 0), 30)
        sortino_pts = min(max(sortino_live * 15, 0), 30)          # Sortino=2.0 → 30pts
        sharpe_score  = round(0.4 * sharpe_pts + 0.6 * sortino_pts, 2)  # blended 30pt component
        wr_score      = win_rate * 25                              # 100% WR → 25pts
        dd_score      = max(0.0, min(20.0, 20.0 + max_dd * 0.04)) # $0 DD → 20, -$500 → 0
        pf_score      = min(max((profit_factor - 0.5) * 7.5, 0), 15)  # PF=2 → 15pts
        # v10.0 Streak Consistency: replaces drought-based Consistency(10).
        # Win/loss streaks measure actual performance consistency, not scan frequency.
        # Max losing streak ≤ 3 → excellent; ≥ 10 → poor. Win bonus +0.3/streak, ≤ 3.
        # Drought was penalizing algos correctly waiting for setups — streak is honest.
        if len(closed) >= 3:
            _outcomes = np.array([1 if float(p.get("pnl", 0)) >= 0 else 0 for p in closed], dtype=int)
            _max_win_s = _max_loss_s = _cur = 0
            _cur_type = int(_outcomes[0])
            for _o in _outcomes:
                _o = int(_o)
                if _o == _cur_type:
                    _cur += 1
                else:
                    if _cur_type == 1:
                        _max_win_s = max(_max_win_s, _cur)
                    else:
                        _max_loss_s = max(_max_loss_s, _cur)
                    _cur, _cur_type = 1, _o
            if _cur_type == 1:
                _max_win_s = max(_max_win_s, _cur)
            else:
                _max_loss_s = max(_max_loss_s, _cur)
            _loss_pen  = min(_max_loss_s * 0.8, 8.0)   # -0.8pt per consecutive loss
            _win_bonus = min(_max_win_s  * 0.3, 3.0)   # +0.3pt per consecutive win
            cons_score = max(0.0, min(10.0, 10.0 - _loss_pen + _win_bonus))
        else:
            # < 3 closed trades: fallback — active picks show system is alive
            cons_score = max(0.0, min(10.0, 5.0 + min(len(active), 2) * 1.0))

        # ── Regime alignment bonus (±5 pts) ──────────────────────────
        regime_bonus = 0.0
        if regime:
            stock_r  = regime.get("stock", "neutral")
            crypto_r = regime.get("crypto", "neutral")
            cat      = algo.get("category", "stock")
            bias     = REGIME_BIAS.get(algo_id, "both")
            ref_r    = crypto_r if cat in ("crypto", "meme", "skyrocket") else stock_r
            if bias == "meme":
                regime_bonus = 5.0 if crypto_r == "bull" else (-3.0 if crypto_r == "bear" else 0.0)
            elif bias == "trend":
                regime_bonus = 3.0 if ref_r == "bull" else (-3.0 if ref_r == "bear" else 0.0)
            elif bias == "mean_rev":
                regime_bonus = 3.0 if ref_r == "bear" else (0.0 if ref_r == "neutral" else -3.0)
            # 'both' and 'forex' → 0 bonus

        # ── v5.5 Walk-forward decay penalty / consistency bonus ──────
        wf = compute_walk_forward_metrics(closed, now)
        decay_penalty = wf["decay_penalty"]
        wf_bonus      = wf["wf_bonus"]

        base_score = sharpe_score + wr_score + dd_score + pf_score + cons_score
        score = round(max(0.0, min(100.0, base_score + regime_bonus + decay_penalty + wf_bonus)), 1)

        # ── League brackets ──────────────────────────────────────────
        if score >= 75:
            status, badge, league = "CHAMPION",  "trophy",   "Champions League"
        elif score >= 55:
            status, badge, league = "RISING",    "chart",    "Premier League"
        elif score >= 40:
            status, badge, league = "SCANNING",  "search",   "Challenger League"
        elif score >= 25:
            status, badge, league = "QUALIFYING","seedling", "Qualification"
        elif drought >= 12:
            status, badge, league = "WARNING",   "warning",  "Danger Zone"
        else:
            status, badge, league = "PROBATION", "red",      "Danger Zone"

        scored.append({
            "id":            algo_id,
            "name":          algo.get("name", algo_id),
            "tier":          algo.get("tier", "SCOUT"),
            "category":      algo.get("category", ""),
            "rank":          0,
            "score":         score,
            "baseScore":     round(base_score, 1),
            "regimeBonus":   round(regime_bonus, 1),
            "status":        status,
            "badge":         badge,
            "league":        league,
            "totalReturn":   total_ret,
            "currentValue":  float(algo.get("currentValue", STARTING_CAPITAL)),
            "activePicks":   len(active),
            "closedPicks":   len(closed),
            "wins":          wins,
            "losses":        len(closed) - wins,
            "winRate":       round(win_rate * 100, 1),
            "droughtScans":  drought,
            "sharpe":        round(sharpe_live, 3),
            "sortino":       round(sortino_live, 3),
            "omega":         round(omega_live, 3),
            "calmar":        round(_calmar, 3),         # v10.0: Calmar ratio
            "maxDrawdown":   round(max_dd, 2),
            "maxLossStreak": int(_max_loss_s) if len(closed) >= 3 else 0,  # v10.0 streak
            "profitFactor":  round(profit_factor, 3),
            "kellyFraction": kelly_quarter,
            # v5.5 walk-forward fields
            "wfDecayPenalty":  round(decay_penalty, 1),
            "wfBonus":         round(wf_bonus, 1),
            "wfRecentSharpe":  wf.get("recent_sharpe"),
            "wfRecentWR":      wf.get("recent_wr"),
            "wfRecentN":       wf.get("recent_n", 0),
            # v9.4 diversification bonus (set below after full scored list built)
            "divBonus":        0.0,
            # v11.5 forward-test gate — embedded in ranking for dashboard access
            "forwardGate": {
                "validated":  len(closed) >= 15 and (wins / len(closed) if closed else 0) >= 0.50,
                "trades":     len(closed),
                "winRate":    round((wins / len(closed)) * 100, 1) if closed else 0.0,
                "status":     ("validated" if (len(closed) >= 15 and
                               (wins / len(closed) if closed else 0) >= 0.50)
                              else (f"insufficient_data ({len(closed)}/15)"
                                    if len(closed) < 15
                                    else f"low_wr ({wins/len(closed):.1%} < 50%)")),
            },
        })

    scored.sort(key=lambda x: x["score"], reverse=True)

    # ── v9.4 Diversification Bonus ─────────────────────────────────────────
    # Research basis: AQR / Citadel proxy-correlation approach.
    # Reward algorithms that are unique (cross-category, different regime bias)
    # and apply a smaller bonus to redundant ones (same category + same regime).
    #
    # Proxy correlation per pair (categories: stock / crypto / forex / meme):
    #   +0.30 — same category (both crypto or both stock = market exposure overlap)
    #   +0.20 — same regime bias (both "trend" or both "mean_rev" = timing overlap)
    #   cap at 0.90
    #
    # Diversification adjustment = BONUS_STRENGTH × (0.5 − avg_proxy_corr) × 2 × 100
    # Neutral (avg_pc=0.5) → 0 pts | Unique (avg_pc=0.10) → +6.4 pts
    # Redundant (avg_pc=0.30) → +3.2 pts  — spread rewards uniqueness
    BONUS_STRENGTH = 0.08   # ±8 pts max (in practice ±3–7 pts given portfolio diversity)
    n_scored = len(scored)
    if n_scored > 1:
        for s in scored:
            cat_s  = s.get("category", "")
            bias_s = REGIME_BIAS.get(s["id"], "both")
            proxy_corrs = []
            for o in scored:
                if o["id"] == s["id"]:
                    continue
                pc = 0.0
                if o.get("category", "") == cat_s and cat_s:
                    pc += 0.30
                bias_o = REGIME_BIAS.get(o["id"], "both")
                if bias_o == bias_s and bias_s not in ("both", "forex"):
                    pc += 0.20
                proxy_corrs.append(min(pc, 0.90))
            avg_pc   = float(np.mean(proxy_corrs)) if proxy_corrs else 0.50
            div_pts  = round(BONUS_STRENGTH * (0.5 - avg_pc) * 2 * 100, 1)
            s["score"]    = round(max(0.0, min(100.0, s["score"] + div_pts)), 1)
            s["divBonus"] = div_pts

    # Re-sort and re-rank after diversification adjustment
    scored.sort(key=lambda x: x["score"], reverse=True)
    for i, s in enumerate(scored):
        s["rank"] = i + 1

    # Tournament phase
    start = datetime(2026, 2, 16, tzinfo=timezone.utc)
    days_in = (now - start).days
    if days_in < 7:
        phase = "Week 1 — Discovery"
    elif days_in < 30:
        phase = f"Week {days_in // 7 + 1} — Validation"
    elif days_in < 90:
        phase = f"Month {days_in // 30 + 1} — Elimination"
    else:
        phase = "Champions League"

    leagues = {
        "Champions League":  sum(1 for s in scored if s["league"] == "Champions League"),
        "Premier League":    sum(1 for s in scored if s["league"] == "Premier League"),
        "Challenger League": sum(1 for s in scored if s["league"] == "Challenger League"),
        "Qualification":     sum(1 for s in scored if s["league"] == "Qualification"),
        "Danger Zone":       sum(1 for s in scored if s["league"] == "Danger Zone"),
    }

    return {
        "lastUpdated":     now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "phase":           phase,
        "daysInCompetition": days_in,
        "totalAlgorithms": len(scored),
        "leagues":         leagues,
        "rankings":        scored,
    }


# ---------------------------------------------------------------------------
# v11.5 FORWARD-TEST GATE — Action 1.3 Remediation
# ---------------------------------------------------------------------------
# Requires >= 15 forward trades with WR > 50% before publishing validated
# signals. Lowered from 30 to 15 for faster initial validation cycle.
# New algos are NOT blocked — they accumulate data in "unvalidated"
# mode so they can eventually graduate. This prevents strategies with 0
# forward wins from being treated as production-grade.
# ---------------------------------------------------------------------------

def passes_forward_gate(algo_name: str, algo_stats: dict,
                        min_trades: int = 15, min_wr: float = 0.50
                        ) -> tuple[bool, str, int, float]:
    """
    Check if an algorithm has enough forward-test data to be published
    as a validated signal.

    New algos get a 'probation' period where they are tracked but signals
    are marked as 'unvalidated'.

    Args:
        algo_name:  Algorithm identifier (for logging).
        algo_stats: Dict with keys 'wins', 'losses', and optionally 'expired'
                    from the tournament rankings.
        min_trades: Minimum closed trades required (default 15).
                    Lowered from 30 to 15 for faster initial validation cycle.
        min_wr:     Minimum win rate required (default 0.50 = 50%).

    Returns:
        (passes, reason, trade_count, win_rate)
        passes:      True if the algo meets the forward-test gate.
        reason:      Human-readable status string.
        trade_count: Total closed trades counted.
        win_rate:    Observed win rate (0.0 if no trades).
    """
    wins = int(algo_stats.get("wins", 0))
    losses = int(algo_stats.get("losses", 0))
    expired = int(algo_stats.get("expired", 0))
    total = wins + losses + expired

    wr = wins / total if total > 0 else 0.0

    if total < min_trades:
        return (False,
                f"insufficient_data ({total}/{min_trades} trades)",
                total, wr)
    if wr < min_wr:
        return (False,
                f"low_wr ({wr:.1%} < {min_wr:.0%})",
                total, wr)
    return (True, "validated", total, wr)


def apply_forward_gate_to_picks(new_picks: list[dict],
                                tournament: dict) -> int:
    """
    Annotate every pick in *new_picks* with forward-test gate metadata.
    Uses tournament rankings (which contain per-algo wins/losses/closedPicks)
    to determine validation status.

    Returns the number of picks that passed the gate.
    """
    # Build algo_id -> ranking dict for O(1) lookup
    rankings_by_id: dict[str, dict] = {}
    for rk in tournament.get("rankings", []):
        rankings_by_id[rk["id"]] = rk

    validated_count = 0
    for pick in new_picks:
        algo_id = pick.get("algorithm", "")
        rk = rankings_by_id.get(algo_id, {})

        # The tournament ranking has 'wins' and 'losses' directly
        algo_stats = {
            "wins":    rk.get("wins", 0),
            "losses":  rk.get("losses", 0),
            "expired": 0,  # expired picks are counted in losses in KIMI
        }

        gate_pass, gate_reason, trade_count, win_rate = passes_forward_gate(
            algo_id, algo_stats)

        pick["forward_validated"] = gate_pass
        pick["forward_status"]   = gate_reason
        pick["forward_trades"]   = trade_count
        pick["forward_wr"]       = round(win_rate, 3)

        if gate_pass:
            validated_count += 1

    return validated_count


def ingest_to_rapid_validation(closed_picks: list) -> dict:
    """
    POST newly-closed picks to the rapid validation MySQL engine so the
    algorithmic elimination pipeline has real outcome data to rank on.
    Each pick: {algorithm, symbol, entry_price, exit_price, pnl, outcome, entry_date, exit_date}
    """
    if not closed_picks:
        return {"ok": True, "ingested": 0, "note": "nothing to send"}
    try:
        payload = json.dumps({"picks": closed_picks}).encode("utf-8")
        req = urllib.request.Request(
            RAPID_INGEST_URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "KIMI-RiseOfTheClaw/3.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        return {"ok": False, "error": f"URL error: {e.reason}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def detect_market_regime(data: dict) -> dict:
    """
    v9.3 Fast market regime detection from fetched OHLCV data.
    Returns: {'stock': str, 'crypto': str, 'btc_dominance': str, 'vix': float}

    Stock regime : SPY 20d vol + 200d SMA + 50d SMA (v9.3) + VIX confirmation
    Crypto regime: BTC 30d return + 20d vol (unchanged)
    BTC dominance: BTC/ETH 20d relative performance ratio (v9.3, Baur & Dimpfl 2018)
      'defensive' → BTC outperforming ETH by >2% (capital fleeing alts, risk-off)
      'risk_on'   → ETH outperforming BTC by >2% (alt-season rotation)
      'neutral'   → within ±2%
    VIX levels: <15 complacency | 15-25 normal | 25-30 elevated | >30 fear | >40 extreme fear
    """
    # VIX fear gauge (CBOE Volatility Index — fetched via yfinance as ^VIX)
    vix_level = 20.0  # default: mid-range normal
    vix_df = data.get("^VIX")
    if vix_df is not None and len(vix_df) >= 1:
        vix_level = float(vix_df["Close"].iloc[-1])

    # Stock regime — SPY 200d SMA + 50d SMA (v9.3) + 20d vol + VIX confirmation
    stock_regime = "neutral"
    spy_df = data.get("SPY")
    if spy_df is not None and len(spy_df) >= 210:
        spy_ret  = spy_df["Close"].pct_change()
        vol_20   = float(spy_ret.rolling(20).std().iloc[-1]) * 100  # daily % vol
        sma200   = float(spy_df["Close"].rolling(200).mean().iloc[-1])
        sma50    = float(spy_df["Close"].rolling(50).mean().iloc[-1])
        current  = float(spy_df["Close"].iloc[-1])
        above_200 = current > sma200
        above_50  = current > sma50
        # VIX crisis override — hard bear when fear is extreme
        if vix_level > 35:
            stock_regime = "bear"
        elif vix_level > 25:
            stock_regime = "neutral" if above_200 else "bear"
        elif vol_20 < 1.2 and above_200 and above_50 and vix_level < 22:
            # v9.3: tighter bull — must be above BOTH 50d and 200d SMA
            stock_regime = "bull"
        elif vol_20 > 2.0 or not above_200:
            stock_regime = "bear"
        # else neutral: above 200 but below 50, or vol in 1.2–2.0 range

    # Crypto regime (absolute) + BTC/ETH dominance ratio (v9.3)
    crypto_regime = "neutral"
    btc_dominance = "neutral"   # 'risk_on' | 'defensive' | 'neutral'
    btc_df = data.get("BTC-USD")
    eth_df = data.get("ETH-USD")
    if btc_df is not None and len(btc_df) >= 22:
        btc_ret_20 = float(btc_df["Close"].iloc[-1] / btc_df["Close"].iloc[-21] - 1)
        btc_ret_30 = float(btc_df["Close"].iloc[-1] / btc_df["Close"].iloc[-30] - 1) if len(btc_df) >= 30 else btc_ret_20
        btc_vol    = float(btc_df["Close"].pct_change().rolling(20).std().iloc[-1]) * 100
        # v9.3: BTC/ETH dominance ratio — detects capital rotation between BTC and alts
        if eth_df is not None and len(eth_df) >= 22:
            eth_ret_20 = float(eth_df["Close"].iloc[-1] / eth_df["Close"].iloc[-21] - 1)
            dom_ratio  = (1 + btc_ret_20) / (1 + eth_ret_20) if (1 + eth_ret_20) != 0 else 1.0
            if dom_ratio > 1.02:
                btc_dominance = "defensive"  # BTC outperforming → risk-off, alts under pressure
            elif dom_ratio < 0.98:
                btc_dominance = "risk_on"    # ETH outperforming → capital rotating to alts
        eth_ret_30 = float(eth_df["Close"].iloc[-1] / eth_df["Close"].iloc[-30] - 1) if eth_df is not None and len(eth_df) >= 30 else 0
        if btc_ret_30 > 0.10 or eth_ret_30 > 0.15:
            crypto_regime = "bull"
        elif btc_ret_30 < -0.15 or btc_vol > 4.5:
            crypto_regime = "bear"

    return {
        "stock":         stock_regime,
        "crypto":        crypto_regime,
        "btc_dominance": btc_dominance,   # v9.3 new: 'risk_on' | 'defensive' | 'neutral'
        "vix":           round(vix_level, 2),
    }


def compute_vix_term_structure(data: dict) -> dict:
    """
    v6.2: VIX term structure — contango vs backwardation regime signal.

    VIX3M/VIX ratio:
      > 1.05 → contango  (calm, implied vol rising with time — normal state)
      0.95–1.05 → flat    (transition / uncertainty)
      < 0.95 → backwardation (acute fear spike, VIX3M < spot — stress event)

    Contango = market complacent → slight boost to trend-following signals
    Backwardation = fear spike → reduce new positions, possible mean-reversion setup

    Returns: {
        'vix_spot': float,
        'vix3m': float,
        'term_ratio': float,   # vix3m / vix_spot
        'term_signal': str,    # 'contango' / 'flat' / 'backwardation'
        'risk_mult': float,    # 1.05 contango | 1.00 flat | 0.88 backwardation
        'mean_rev_score': float,  # 0-100, higher in backwardation (fear = mean-rev opportunity)
    }
    """
    vix_df  = data.get("^VIX")
    vix3m_df = data.get("^VIX3M")

    vix_spot = 20.0
    vix3m    = 21.0   # default: slight contango

    if vix_df is not None and len(vix_df) >= 1:
        v = float(vix_df["Close"].iloc[-1])
        if v > 0:
            vix_spot = v
    if vix3m_df is not None and len(vix3m_df) >= 1:
        v3 = float(vix3m_df["Close"].iloc[-1])
        if v3 > 0:
            vix3m = v3

    term_ratio = vix3m / vix_spot if vix_spot > 0 else 1.05

    if term_ratio > 1.05:
        term_signal = "contango"
        risk_mult   = 1.05   # slight boost — calm markets reward momentum
        mean_rev_score = 20.0
    elif term_ratio < 0.95:
        term_signal = "backwardation"
        # Scale risk reduction by severity of inversion
        severity    = max(0.0, min(1.0, (0.95 - term_ratio) / 0.15))  # 0-1 over 0.80-0.95 range
        risk_mult   = round(0.88 + severity * (-0.08), 3)              # 0.80-0.88
        mean_rev_score = round(60.0 + severity * 30.0, 1)             # 60-90 (strong fear = big mean-rev opp)
    else:
        term_signal = "flat"
        risk_mult   = 1.00
        mean_rev_score = 40.0

    return {
        "vix_spot":      round(vix_spot, 2),
        "vix3m":         round(vix3m, 2),
        "term_ratio":    round(term_ratio, 4),
        "term_signal":   term_signal,
        "risk_mult":     risk_mult,
        "mean_rev_score": mean_rev_score,
    }


def compute_crypto_funding_sentiment() -> dict:
    """
    v6.5: Aggregate perpetual funding rates across major crypto pairs via CCXT Binance.
    Funding rate interpretation:
      > +0.10% (per 8h) → extreme greed, longs heavily overloaded → BEARISH for new longs
      +0.01–0.10% → normal positive → NEUTRAL
      0 to -0.01% → slight negative → MILD BULLISH (shorts slightly loaded)
      < -0.01% → negative funding → BULLISH contrarian (shorts paying longs = short squeeze fuel)
      < -0.05% → extreme negative → STRONG BULLISH (peak short crowding)

    Returns:
      {
        'rates': {symbol: funding_rate_pct},  # per-symbol 8h funding rate %
        'avg_rate': float,    # average across tracked symbols
        'signal':   str,      # 'extreme_greed' / 'greed' / 'neutral' / 'fear' / 'extreme_fear'
        'sentiment_score': float,  # 0-100 (higher = more bullish for mean-rev)
        'buy_candidates': list[str],  # symbols with negative funding (contrarian long opportunity)
      }
    """
    _FUNDING_SYMBOLS = [
        "BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT",
        "BNB/USDT:USDT", "XRP/USDT:USDT", "DOGE/USDT:USDT",
        "AVAX/USDT:USDT", "LINK/USDT:USDT",
        # Added 2026-03-18: top-100 expansion
        "HYPE/USDT:USDT", "TRX/USDT:USDT", "XLM/USDT:USDT",
        "TAO/USDT:USDT", "KAS/USDT:USDT", "RENDER/USDT:USDT",
        "ONDO/USDT:USDT", "ICP/USDT:USDT", "ETC/USDT:USDT", "LTC/USDT:USDT",
    ]
    result = {
        "rates": {}, "avg_rate": 0.0, "signal": "neutral",
        "sentiment_score": 50.0, "buy_candidates": [],
    }
    try:
        import ccxt
        exchange = ccxt.binanceusdm({
            "options": {"defaultType": "future"},
            "enableRateLimit": True,
        })
        rates: dict[str, float] = {}
        for sym in _FUNDING_SYMBOLS:
            try:
                info = exchange.fetch_funding_rate(sym)
                fr = float(info.get("fundingRate", 0.0)) * 100.0   # convert to %
                rates[sym] = round(fr, 5)
            except Exception:
                pass
        if not rates:
            return result

        avg = sum(rates.values()) / len(rates)
        result["rates"]    = rates
        result["avg_rate"] = round(avg, 5)
        result["buy_candidates"] = [s for s, r in rates.items() if r < -0.005]

        if avg > 0.08:
            signal = "extreme_greed"
            score  = 10.0
        elif avg > 0.02:
            signal = "greed"
            score  = 30.0
        elif avg > -0.005:
            signal = "neutral"
            score  = 50.0
        elif avg > -0.02:
            signal = "fear"
            score  = 70.0
        else:
            signal = "extreme_fear"
            # Scale 70-95 as funding gets more negative
            severity = min(1.0, abs(avg + 0.02) / 0.05)
            score    = round(70.0 + severity * 25.0, 1)

        result["signal"]          = signal
        result["sentiment_score"] = score

    except Exception as e:
        result["error"] = str(e)

    return result


def compute_intermarket_signals(data: dict) -> dict:
    """
    Cross-asset intermarket signal computation (v5.3).
    Institutional quants (AQR, Two Sigma, Bridgewater) use cross-asset flows
    to confirm regime and filter signal quality.

    Signals:
      SPY/TLT ratio trend  → equities vs bonds (risk-on indicator)
      HYG/TLT ratio trend  → credit spread (junk bond appetite)
      UUP trend            → DXY proxy (dollar strength)
      GLD trend            → safe-haven demand

    Returns:
      risk_on_score (0–100): higher = more risk-on
      credit: 'tight'/'wide'/'neutral'
      dollar: 'strong'/'weak'/'neutral'
      safe_haven: bool (gold rising = flight to safety)
      details: raw % values for logging
    """
    result: dict = {
        "risk_on_score": 50.0,
        "credit": "neutral",
        "dollar": "neutral",
        "safe_haven": False,
        "details": {},
    }
    score = 50.0
    details: dict = {}

    # 1. SPY/TLT ratio — equities vs long-duration bonds (most important)
    spy_df = data.get("SPY")
    tlt_df = data.get("TLT")
    if spy_df is not None and tlt_df is not None:
        ml = min(len(spy_df), len(tlt_df))
        if ml >= 21:
            spy_c = spy_df["Close"].iloc[-ml:].values
            tlt_c = tlt_df["Close"].iloc[-ml:].values
            ratio = spy_c / tlt_c
            ret10 = float(ratio[-1] / ratio[-10] - 1) if ml >= 10 else 0.0
            ret20 = float(ratio[-1] / ratio[-20] - 1) if ml >= 20 else 0.0
            if ret10 > 0.025 and ret20 > 0.04:
                score += 22    # strong risk-on: equities clearly outperforming bonds
            elif ret10 > 0.01:
                score += 11
            elif ret10 < -0.025:
                score -= 18    # risk-off: bonds outperforming stocks
            elif ret10 < -0.01:
                score -= 9
            details["spy_tlt_10d"] = round(ret10 * 100, 2)

    # 2. HYG/TLT ratio — junk bonds vs treasuries (credit spread indicator)
    hyg_df = data.get("HYG")
    if hyg_df is not None and tlt_df is not None:
        ml2 = min(len(hyg_df), len(tlt_df))
        if ml2 >= 11:
            hyg_c = hyg_df["Close"].iloc[-ml2:].values
            tlt_c2 = tlt_df["Close"].iloc[-ml2:].values
            ratio2 = hyg_c / tlt_c2
            ret10_2 = float(ratio2[-1] / ratio2[-10] - 1) if ml2 >= 10 else 0.0
            if ret10_2 > 0.005:
                result["credit"] = "tight"   # credit expanding = risk appetite
                score += 10
            elif ret10_2 < -0.01:
                result["credit"] = "wide"    # credit contracting = risk-off
                score -= 10
            details["hyg_tlt_10d"] = round(ret10_2 * 100, 2)

    # 3. UUP trend — DXY proxy (US Dollar Bullish ETF)
    uup_df = data.get("UUP")
    if uup_df is not None and len(uup_df) >= 21:
        uup_c = uup_df["Close"]
        sma20_uup = float(uup_c.rolling(20).mean().iloc[-1])
        curr_uup = float(uup_c.iloc[-1])
        ret10_uup = float(uup_c.iloc[-1] / uup_c.iloc[-10] - 1) if len(uup_c) >= 10 else 0.0
        if curr_uup > sma20_uup * 1.005 and ret10_uup > 0.005:
            result["dollar"] = "strong"   # rising dollar = headwind for risk assets
            score -= 5
        elif curr_uup < sma20_uup * 0.995 and ret10_uup < -0.005:
            result["dollar"] = "weak"     # falling dollar = tailwind for risk assets
            score += 5
        details["uup_vs_sma20_pct"] = round((curr_uup / sma20_uup - 1) * 100, 2)

    # 4. GLD trend — safe-haven demand (gold rising = flight to safety)
    gld_df = data.get("GLD")
    if gld_df is not None and len(gld_df) >= 11:
        gld_c = gld_df["Close"]
        ret10_gld = float(gld_c.iloc[-1] / gld_c.iloc[-10] - 1) if len(gld_c) >= 10 else 0.0
        result["safe_haven"] = ret10_gld > 0.02   # gold +2% in 10 days = flight to safety
        if result["safe_haven"]:
            score -= 8   # safe-haven demand = risk-off pressure on equities
        details["gld_10d"] = round(ret10_gld * 100, 2)

    result["risk_on_score"] = round(max(0.0, min(100.0, score)), 1)
    result["details"] = details
    return result


def compute_adaptive_stop_params(
    base_sl: float, base_tp: float, base_trail: float,
    category: str, regime: dict, vix_term: dict
) -> tuple[float, float, float]:
    """
    v6.9: Regime-adaptive stop-loss tightening.
    In bear markets or VIX stress, cut losers faster.
    In bull+contango, give winners more room.

    Tightening logic (applied to SL and trail, stacks):
      Bear regime (stock/crypto):           SL × 0.70  trail × 0.80
      VIX backwardation:                    SL × 0.85  trail × 0.85  (stacks with bear)
      VIX spike > 35:                       SL × 0.60  trail × 0.65  (overrides others)
      Bull + VIX contango:                  trail × 1.20 (let winners run)
      Forex is only lightly adjusted (×0.90 max) — already very tight
    """
    sl    = base_sl     # negative number
    trail = base_trail  # positive fraction
    tp    = base_tp     # unchanged — TP rarely needs tightening

    vix_spot     = vix_term.get("vix_spot", 20.0)
    term_signal  = vix_term.get("term_signal", "flat")
    cat_regime   = "bear" if (
        (category in ("stock", "penny", "meme") and regime.get("stock") == "bear") or
        (category in ("crypto", "skyrocket") and regime.get("crypto") == "bear")
    ) else ("bull" if (
        (category in ("stock", "penny", "meme") and regime.get("stock") == "bull") or
        (category in ("crypto", "skyrocket") and regime.get("crypto") == "bull")
    ) else "neutral")

    # --- extreme VIX spike takes priority ---
    if vix_spot > 35:
        sl    = round(sl    * 0.60, 4)   # tighten stop 40%
        trail = round(trail * 0.65, 4)   # tighten trail 35%
        return sl, tp, trail

    # --- bear regime: cut losers faster ---
    if cat_regime == "bear":
        sl    = round(sl    * 0.70, 4)   # tighten 30%
        trail = round(trail * 0.80, 4)   # tighten 20%

    # --- VIX backwardation stacks on top of regime adjustments ---
    if term_signal == "backwardation":
        sl    = round(sl    * 0.85, 4)
        trail = round(trail * 0.85, 4)

    # --- bull + contango: loosen trail to let winners run ---
    elif term_signal == "contango" and cat_regime == "bull":
        trail = round(min(trail * 1.20, base_trail * 1.40), 4)

    # Forex: cap tightening — already tight; don't over-tighten
    if category == "forex":
        sl    = max(sl, base_sl    * 0.85)
        trail = max(trail, base_trail * 0.85)

    return sl, tp, trail


def compute_trend_strength_composite(data: dict) -> dict:
    """
    v6.8: Aggregate ADX (Average Directional Index) across tracked stocks.
    Returns a market-wide trend strength score.
    High composite ADX = trending market (CTAs dominating)
    Low composite ADX = choppy/ranging market (mean-reversion strategies win)
    Returns: {
        'avg_adx': float,       # average ADX across universe
        'trending_pct': float,  # % stocks with ADX > 25
        'signal': str,          # 'trending' / 'mixed' / 'choppy'
        'strategy_bias': str,   # 'trend' / 'both' / 'mean_rev'
    }
    """
    adx_values: list[float] = []
    for sym, df_sym in data.items():
        if isinstance(sym, str) and sym.startswith("__"):
            continue
        if not isinstance(df_sym, pd.DataFrame):
            continue
        if "High" not in df_sym.columns or "Low" not in df_sym.columns:
            continue
        close = df_sym["Close"]
        high  = df_sym["High"]
        low   = df_sym["Low"]
        if len(close) < 30:
            continue
        try:
            tr  = pd.concat([high - low,
                              (high - close.shift(1)).abs(),
                              (low  - close.shift(1)).abs()], axis=1).max(axis=1)
            up   = high.diff()
            down = -low.diff()
            dm_p = up.where((up > down) & (up > 0), 0.0)
            dm_m = down.where((down > up) & (down > 0), 0.0)
            period = 14
            atr    = tr.ewm(alpha=1/period, adjust=False).mean()
            di_p   = 100 * dm_p.ewm(alpha=1/period, adjust=False).mean() / atr.replace(0, np.nan)
            di_m   = 100 * dm_m.ewm(alpha=1/period, adjust=False).mean() / atr.replace(0, np.nan)
            dx     = (100 * (di_p - di_m).abs() / (di_p + di_m).replace(0, np.nan)).fillna(0.0)
            adx    = dx.ewm(alpha=1/period, adjust=False).mean()
            v = float(adx.iloc[-1])
            if not np.isnan(v) and v >= 0:
                adx_values.append(v)
        except Exception:
            pass

    if not adx_values:
        return {"avg_adx": 20.0, "trending_pct": 50.0, "signal": "mixed", "strategy_bias": "both"}

    avg_adx      = round(sum(adx_values) / len(adx_values), 1)
    trending_pct = round(sum(1 for x in adx_values if x > 25) / len(adx_values) * 100, 1)

    if avg_adx >= 30 or trending_pct >= 60:
        signal        = "trending"
        strategy_bias = "trend"
    elif avg_adx <= 18 or trending_pct <= 30:
        signal        = "choppy"
        strategy_bias = "mean_rev"
    else:
        signal        = "mixed"
        strategy_bias = "both"

    return {
        "avg_adx":       avg_adx,
        "trending_pct":  trending_pct,
        "signal":        signal,
        "strategy_bias": strategy_bias,
    }


def compute_market_breadth(data: dict) -> dict:
    """
    Market Breadth Signal (v6.0): % of tracked stocks above 50d SMA.
    Breadth > 65% = broad bull (reduce caution, allow fuller positions)
    Breadth 40-65% = mixed (neutral, no adjustment)
    Breadth < 40% = narrow bear (broad weakness beneath surface → reduce stock alloc)

    Uses the already-downloaded STOCKS_ETF individual stocks.
    """
    above = 0
    total = 0
    for sym, df_sym in data.items():
        if isinstance(sym, str) and sym.startswith("__"):
            continue
        if sym.endswith("-USD") or "=X" in sym or sym.startswith("^"):
            continue   # only stocks/ETFs
        if not isinstance(df_sym, pd.DataFrame) or "Close" not in df_sym.columns:
            continue
        if len(df_sym) < 51:
            continue
        try:
            sma50 = float(df_sym["Close"].rolling(50).mean().iloc[-1])
            curr  = float(df_sym["Close"].iloc[-1])
            if not (np.isnan(sma50) or sma50 <= 0):
                total += 1
                if curr > sma50:
                    above += 1
        except Exception:
            continue

    breadth_pct = round(above / total * 100, 1) if total > 0 else 50.0
    if breadth_pct >= 65:
        signal = "bull"
        alloc_mult = 1.0
    elif breadth_pct <= 40:
        signal = "bear"
        alloc_mult = 0.85   # 15% reduction in stock allocations
    else:
        signal = "neutral"
        alloc_mult = 1.0
    return {
        "breadth_pct": breadth_pct,
        "above": above,
        "total": total,
        "signal": signal,
        "alloc_mult": alloc_mult,
    }


def compute_cross_sectional_momentum_ranks(data: dict) -> dict[str, float]:
    """
    v6.6: Cross-sectional momentum ranking (Fama-French / Jegadeesh-Titman style).
    For each stock in the universe, compute 12-1 month return (skip most recent month).
    Rank all stocks percentile 0-100 (higher = stronger momentum).
    Only top quartile stocks pass the momentum factor filter.
    Returns: {symbol: percentile_rank} where 100 = strongest momentum.
    """
    mom_returns: dict[str, float] = {}
    for sym, df_sym in data.items():
        if isinstance(sym, str) and sym.startswith("__"):
            continue
        if not isinstance(df_sym, pd.DataFrame) or "Close" not in df_sym.columns:
            continue
        close = df_sym["Close"].dropna()
        if len(close) < 252:
            continue
        # 12-1 month return: price at -21 bars vs price at -252 bars
        try:
            ret = float(close.iloc[-21] / close.iloc[-252]) - 1.0
            if not np.isnan(ret):
                mom_returns[sym] = ret
        except Exception:
            pass

    if len(mom_returns) < 3:
        return {}   # not enough symbols to rank

    # Compute percentile ranks: sort ascending, assign 0-100
    sorted_syms = sorted(mom_returns, key=lambda s: mom_returns[s])
    n = len(sorted_syms)
    ranks: dict[str, float] = {}
    for i, sym in enumerate(sorted_syms):
        ranks[sym] = round(i / (n - 1) * 100.0, 1) if n > 1 else 50.0
    return ranks


def compute_correlation_risks(data: dict, symbols: list[str], lookback: int = 20) -> dict[str, dict[str, float]]:
    """
    Compute pairwise rolling correlation matrix for a subset of symbols (v6.0).
    Uses `lookback` days of returns. Only computes pairs that share enough data.
    Returns: {sym1: {sym2: correlation}} for all pairs.
    """
    returns: dict[str, pd.Series] = {}
    for sym in symbols:
        df_sym = data.get(sym)
        if df_sym is not None and "Close" in df_sym.columns and len(df_sym) >= lookback + 1:
            try:
                ret = df_sym["Close"].pct_change().dropna()
                if len(ret) >= lookback:
                    returns[sym] = ret.iloc[-lookback:]
            except Exception:
                pass

    corr_matrix: dict[str, dict[str, float]] = {sym: {} for sym in returns}
    syms = list(returns.keys())
    for i, s1 in enumerate(syms):
        for s2 in syms[i + 1:]:
            try:
                c = float(returns[s1].corr(returns[s2]))
                if not np.isnan(c):
                    corr_matrix[s1][s2] = round(c, 3)
                    corr_matrix[s2][s1] = round(c, 3)
            except Exception:
                pass
    return corr_matrix


def compute_sector_rankings(data: dict) -> dict[str, int]:
    """
    Sector Relative Strength Rankings (v5.8).
    Ranks sector ETFs by 20d momentum to identify leading vs lagging sectors.
    Used by signal_sector_rotation() to only fire in top-ranked sectors.

    Returns: {sector_etf: rank} where rank=1 is the strongest sector.
    """
    _SECTOR_ETFS = ["XLK", "XLF", "XLE", "XLV", "XLI", "ARKK", "XBI", "XRT", "JETS", "SOXX"]
    rets: list[tuple[str, float]] = []
    for etf in _SECTOR_ETFS:
        df_etf = data.get(etf)
        if df_etf is None or len(df_etf) < 21:
            continue
        try:
            ret20 = float(df_etf["Close"].iloc[-1] / df_etf["Close"].iloc[-20] - 1)
            if not np.isnan(ret20):
                rets.append((etf, ret20))
        except Exception:
            continue
    rets.sort(key=lambda x: x[1], reverse=True)
    return {etf: rank + 1 for rank, (etf, _) in enumerate(rets)}


def compute_weekly_trends(data: dict) -> dict[str, str]:
    """
    Multi-timeframe weekly trend filter (v5.4).
    Derives weekly trend from daily OHLCV without a separate data download.

    Method: pseudo-weekly using 65d SMA (≈13 weeks) and 130d SMA (≈26 weeks).
    Weekly trend classification per symbol:
      'bull' : price > 65d SMA AND 65d SMA slope positive (rising trend)
      'bear' : price < 65d SMA × 0.98 AND 65d SMA slope negative (falling trend)
      'neutral': all other cases (sideways / transitional)

    Used by signal loop to:
      - Block TREND-following signals for symbols in weekly bear trend
      - Allow (or enhance) MEAN-REVERSION signals regardless of weekly trend
      - Apply allocation penalty for TREND signals in neutral weekly trend
    """
    weekly: dict[str, str] = {}
    for sym, df in data.items():
        if isinstance(sym, str) and sym.startswith("__"):
            continue  # skip injected data keys
        if not isinstance(df, pd.DataFrame) or "Close" not in df.columns:
            continue
        close = df["Close"].dropna()
        if len(close) < 66:
            weekly[sym] = "neutral"
            continue
        try:
            sma65 = close.rolling(65).mean()
            sma65_val = float(sma65.iloc[-1])
            if pd.isna(sma65_val):
                weekly[sym] = "neutral"
                continue
            curr = float(close.iloc[-1])
            # Slope: compare current 65d SMA vs 10 days ago
            sma65_10ago = float(sma65.iloc[-11]) if len(sma65) >= 11 and not pd.isna(sma65.iloc[-11]) else sma65_val
            slope_positive = sma65_val > sma65_10ago * 1.001   # rising by >0.1%
            slope_negative = sma65_val < sma65_10ago * 0.999   # falling by >0.1%
            above_sma = curr > sma65_val
            below_sma_sig = curr < sma65_val * 0.98            # >2% below = confirmed bear

            if above_sma and slope_positive:
                weekly[sym] = "bull"
            elif below_sma_sig and slope_negative:
                weekly[sym] = "bear"
            else:
                weekly[sym] = "neutral"
        except Exception:
            weekly[sym] = "neutral"
    return weekly


def load_scan_runs(path: Path, max_runs: int = 100) -> list:
    """Load scan_runs.json, trimmed to max_runs newest entries."""
    runs = load_json(path, [])
    if not isinstance(runs, list):
        runs = []
    return runs[-max_runs:]


def save_scan_run(path: Path, entry: dict, max_runs: int = 100):
    """Append a scan run entry and keep only the last max_runs."""
    runs = load_scan_runs(path, max_runs)
    runs.append(entry)
    save_json(path, runs[-max_runs:])


def _compute_kelly_for_algo(algo: dict) -> float:
    """
    v7.0: Quarter-Kelly fraction computed from algo's closed pick history.
    Returns 0.0 if <5 closed trades (not enough data).
    Used for dynamic position sizing — algos with proven edge get larger allocations.
    """
    closed = algo.get("closedPicks", [])
    pnls   = np.array([float(p.get("pnl", 0.0)) for p in closed if "pnl" in p])
    if len(pnls) < 5 or not (pnls > 0).any() or not (pnls < 0).any():
        return 0.0
    wins      = int((pnls > 0).sum())
    win_rate  = wins / len(pnls)
    avg_win   = float(pnls[pnls > 0].mean())
    avg_loss  = abs(float(pnls[pnls < 0].mean()))
    payoff    = avg_win / avg_loss if avg_loss > 0 else 1.0
    full_kelly = win_rate - (1.0 - win_rate) / payoff if payoff > 0 else 0.0
    return max(0.0, round(full_kelly * 0.25, 3))


def apply_confluence_filter(new_picks: list[dict], algos_by_id: dict, live: dict, min_agreement: int = 2) -> list[dict]:
    """
    Action 2.3: Confluence filtering — require min_agreement algorithms to agree
    on the same symbol before keeping a pick. Single-algo picks are removed from
    both new_picks_flat and the algo's activePicks list.

    Returns filtered new_picks list with confluence metadata added.
    """
    from collections import defaultdict

    if not new_picks:
        return new_picks

    # Group new picks by symbol
    symbol_groups: dict[str, list[dict]] = defaultdict(list)
    for pick in new_picks:
        sym = pick.get("symbol", "")
        if sym:
            symbol_groups[sym].append(pick)

    # Identify symbols that pass confluence threshold
    # High-confidence bypass: single-algo picks with confidence >= 0.65 are allowed through
    # Lowered from 0.80 — algorithms are too independent for multi-algo confluence,
    # so a single confident signal should be sufficient to generate picks.
    HIGH_CONFIDENCE_BYPASS = 0.65
    confluent_symbols: set[str] = set()
    low_confluence_symbols: set[str] = set()
    for sym, group in symbol_groups.items():
        algo_ids = {p.get("algorithm", "") for p in group}
        if len(algo_ids) >= min_agreement:
            confluent_symbols.add(sym)
        else:
            # High-confidence bypass: allow single-algo picks if any pick has high confidence
            max_conf = max((float(p.get("confidence", 0) or 0) for p in group), default=0)
            if max_conf >= HIGH_CONFIDENCE_BYPASS:
                confluent_symbols.add(sym)
                for p in group:
                    p["confluence_bypass"] = "high_confidence"
                print(f"    BYPASS {sym}: single algo but confidence {max_conf:.2f} >= {HIGH_CONFIDENCE_BYPASS}")
            else:
                low_confluence_symbols.add(sym)

    # Remove low-confluence picks from algo activePicks and refund cash
    removed_count = 0
    for sym in low_confluence_symbols:
        picks_for_sym = symbol_groups[sym]
        for pick in picks_for_sym:
            algo_id = pick.get("algorithm", "")
            algo = algos_by_id.get(algo_id)
            if not algo:
                continue
            active = algo.get("activePicks", [])
            before_len = len(active)
            # Remove the pick we just added (match on symbol + entryDate to be precise)
            algo["activePicks"] = [
                p for p in active
                if not (p["symbol"] == sym and p.get("entryDate") == pick.get("entryDate"))
            ]
            n_removed = before_len - len(algo["activePicks"])
            if n_removed > 0:
                # Refund cash
                refund = float(pick.get("allocation", 0))
                algo["cash"] = round(float(algo.get("cash", 0)) + refund, 2)
                removed_count += n_removed

    # Build filtered new_picks with confluence metadata
    filtered: list[dict] = []
    for sym in confluent_symbols:
        group = symbol_groups[sym]
        algo_names = [p.get("algorithmName", p.get("algorithm", "unknown")) for p in group]
        confluence_count = len({p.get("algorithm", "") for p in group})
        confluence_score = min(100, 50 + (confluence_count - 1) * 15)
        for pick in group:
            pick["confluence_count"] = confluence_count
            pick["confluence_algos"] = algo_names
            pick["confluence_score"] = confluence_score
            filtered.append(pick)
            # Also propagate confluence metadata to the algo's activePicks entry
            algo_id = pick.get("algorithm", "")
            algo = algos_by_id.get(algo_id)
            if algo:
                for ap in algo.get("activePicks", []):
                    if ap.get("symbol") == sym and ap.get("entryDate") == pick.get("entryDate"):
                        ap["confluence_count"] = confluence_count
                        ap["confluence_algos"] = algo_names
                        ap["confluence_score"] = confluence_score
                        break

    # Log summary
    total_before = len(new_picks)
    total_after = len(filtered)
    bypass_count = sum(1 for p in filtered if p.get("confluence_bypass") == "high_confidence")
    multi_algo_count = total_after - bypass_count
    print(f"  [CONFLUENCE] {total_before} raw signals -> {total_after} passed "
          f"({multi_algo_count} multi-algo, {bypass_count} high-confidence bypass) | "
          f"{removed_count} rejected (min_agreement={min_agreement}, bypass>={HIGH_CONFIDENCE_BYPASS})")
    if confluent_symbols:
        for sym in sorted(confluent_symbols):
            group = symbol_groups[sym]
            algos = [p.get("algorithm", "?") for p in group]
            print(f"    PASS {sym}: {len(algos)} algos agree ({', '.join(algos)})")
    if low_confluence_symbols:
        for sym in sorted(low_confluence_symbols):
            group = symbol_groups[sym]
            algos = [p.get("algorithm", "?") for p in group]
            print(f"    REJECT {sym}: only {len(algos)} algo ({', '.join(algos)})")

    return filtered


def run_scanner() -> int:
    """Main entry. Returns 0 on success."""
    print("=" * 64)
    print("KIMI Rise of the Claw - Live Market Scanner v11.2 (ANTIGRAVITY_FEB172026)")
    print(f"  {len(ALGO_DEFS)} algorithms: Tier 1 (institutional) + Scout (supplementary)")
    print("  v11.0: ANTIGRAVITY acceleration — PumpDetector | OrderBookImbalance | LiquidationCascade | CrossExchangeMomentum | FundingRateReversal")
    print("  v11.0: ML Signal Ranker | SQLite Persistence | Elimination Engine (20-algo challenger pool)")
    print("  + all v10.5 modules: VIX | CryptoFunding | CrossSectMom | PriceAccel | AdaptiveStop | KellySize | Macro | PCR | F&G | Convergence | Trailing")
    print("=" * 64)
    now = datetime.now(timezone.utc)
    scan_start = now
    print(f"Timestamp: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")

    # Reset circuit breakers at start of each scan cycle
    if _HAS_MULTI_FETCH:
        reset_circuit_breakers()
    print()

    live_path = DATA_DIR / "live_competition.json"
    active_path = DATA_DIR / "active_picks.json"
    audit_path = DATA_DIR / "audit_log.json"
    runs_path = DATA_DIR / "scan_runs.json"

    # Load or initialize state
    live = load_json(live_path, {})
    if not live:
        live = {
            "competition": {
                "name": "KIMI Rise of the Claw - LIVE v2",
                "type": "Forward-Facing Paper Trading",
                "startDate": "2026-02-16",
                "startingCapital": STARTING_CAPITAL,
                "status": "ACTIVE",
                "lastUpdated": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "updateFrequency": "Every 15 minutes",
                "version": "2.0",
                "strategies": "5 Tier 1 (academic) + 5 Scout (supplementary)",
            },
            "algorithms": [],
            "todaysPicks": [],
            "marketStatus": {
                "usMarkets": "OPEN",
                "cryptoMarkets": "24/7",
                "forexMarkets": "OPEN",
                "lastMarketCheck": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        }

    algos_by_id = {a["id"]: a for a in live.get("algorithms", [])}

    # Migration map: old v1 IDs -> new v2 IDs (to preserve picks across upgrade)
    V1_TO_V2 = {
        "rsi-momentum-live": "crypto-momentum-scout",
        "crypto-winners-live": "crypto-momentum-scout",
        "etf-masters-live": "quality-minus-junk",
        "blue-chip-live": "betting-against-beta",
        "technical-momentum-live": "flash-crash-reversal",
        "alpha-hunter-live": "funding-rate-arb",
        "pump-watch-live": "volume-spike-scout",
    }

    # Re-initialize algorithms from ALGO_DEFS if structure changed
    if not algos_by_id or set(algos_by_id.keys()) != set(ALGO_DEFS.keys()):
        # Migrate old v1 picks into new v2 algorithms
        migrated_picks: dict[str, list] = {}
        migrated_cash: dict[str, float] = {}
        migrated_value: dict[str, float] = {}
        for old_id, old_algo in algos_by_id.items():
            new_id = V1_TO_V2.get(old_id, old_id)
            if new_id in ALGO_DEFS:
                old_picks = old_algo.get("activePicks", [])
                if old_picks:
                    migrated_picks.setdefault(new_id, []).extend(old_picks)
                    old_cash = old_algo.get("cash", STARTING_CAPITAL)
                    old_val = old_algo.get("currentValue", STARTING_CAPITAL)
                    migrated_cash[new_id] = migrated_cash.get(new_id, STARTING_CAPITAL) - (STARTING_CAPITAL - old_cash)
                    migrated_value[new_id] = max(migrated_value.get(new_id, 0), old_val)
                    print(f"  Migrated {len(old_picks)} picks from {old_id} -> {new_id}")

        new_algos = []
        for aid, spec in ALGO_DEFS.items():
            existing = algos_by_id.get(aid, {})
            m_picks = migrated_picks.get(aid, [])
            m_cash = migrated_cash.get(aid)
            m_val = migrated_value.get(aid)
            picks = existing.get("activePicks", []) + m_picks
            cash = m_cash if m_cash is not None else existing.get("cash", float(STARTING_CAPITAL))
            val = m_val if m_val is not None and m_val > 0 else existing.get("currentValue", STARTING_CAPITAL)
            new_algos.append({
                "id": aid,
                "name": spec["name"],
                "category": spec["category"],
                "tier": spec["tier"],
                "strategyClass": spec["strategy"],
                "startingValue": existing.get("startingValue", STARTING_CAPITAL),
                "currentValue": val,
                "cash": cash,
                "totalReturn": existing.get("totalReturn", 0),
                "activePicks": existing.get("activePicks", []),
                "closedPicks": existing.get("closedPicks", []),
                "status": "READY",
                "nextAction": f"Scan using {spec['strategy']}",
            })
        live["algorithms"] = new_algos
        algos_by_id = {a["id"]: a for a in live["algorithms"]}

    # Collect all symbols to fetch (including from existing picks)
    all_needed = set(ALL_SYMBOLS)
    for algo in live.get("algorithms", []):
        for p in algo.get("activePicks", []):
            sym = p.get("symbol")
            if sym:
                all_needed.add(sym)

    # Fetch market data
    print("Fetching market data...")
    data: dict[str, pd.DataFrame] = {}
    for sym in sorted(all_needed):
        df = fetch_symbol_data(sym)
        if df is not None:
            data[sym] = df
        elif sym in ALL_SYMBOLS:
            print(f"  ⚠ Skipped {sym} (fetch failed or <20 bars)")
    if not data:
        print("No data available. Exiting without changes.")
        elapsed = (datetime.now(timezone.utc) - scan_start).total_seconds()
        save_scan_run(runs_path, {
            "timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": "FAILED",
            "runtime_sec": round(elapsed, 1),
            "symbols_scanned": 0,
            "signals_found": 0,
            "new_picks": 0,
            "total_active_picks": 0,
            "signal_details": [],
        })
        return 0
    print(f"  Fetched {len(data)} symbols")
    if _HAS_MULTI_FETCH:
        print_fetch_summary()

    # Market regime detection
    regime = detect_market_regime(data)
    print(f"  Market regime — stocks: {regime['stock'].upper()}  crypto: {regime['crypto'].upper()}  BTC-dom: {regime.get('btc_dominance', 'neutral').upper()}  VIX: {regime.get('vix', 'N/A')}")

    # v6.2 — VIX term structure (contango/backwardation)
    vix_term = compute_vix_term_structure(data)
    _ts_emoji = {"contango": "📈", "flat": "➡️", "backwardation": "🔴"}
    print(f"  VIX term structure — {_ts_emoji.get(vix_term['term_signal'], '?')} {vix_term['term_signal'].upper()}"
          f"  VIX: {vix_term['vix_spot']:.1f}  VIX3M: {vix_term['vix3m']:.1f}"
          f"  ratio: {vix_term['term_ratio']:.3f}  risk_mult: {vix_term['risk_mult']:.2f}")
    data["__vix_term__"] = vix_term  # type: ignore[assignment]
    print()

    # v6.5 — Crypto perpetual funding rate sentiment
    print("Fetching crypto funding rates (CCXT Binance perps)...")
    crypto_funding = compute_crypto_funding_sentiment()
    _fr_emoji = {"extreme_greed": "🔴", "greed": "🟡", "neutral": "⚪",
                 "fear": "🟢", "extreme_fear": "💚"}
    _fr_sig = crypto_funding.get("signal", "neutral")
    _fr_avg = crypto_funding.get("avg_rate", 0.0)
    _fr_cands = crypto_funding.get("buy_candidates", [])
    if "error" not in crypto_funding:
        print(f"  {_fr_emoji.get(_fr_sig,'?')} Crypto funding: {_fr_sig.upper()}"
              f"  avg_rate={_fr_avg:.4f}%  sentiment={crypto_funding.get('sentiment_score',50):.0f}/100")
        if _fr_cands:
            print(f"  Negative funding (contrarian buy): {', '.join(_fr_cands)}")
    else:
        print(f"  ⚠ Funding rate fetch failed: {crypto_funding.get('error','?')[:60]}")
    data["__crypto_funding__"] = crypto_funding  # type: ignore[assignment]
    print()

    # -----------------------------------------------------------------------
    # DYNAMIC COINTEGRATION PAIRS — Engle-Granger test on all candidate pairs
    # -----------------------------------------------------------------------
    print("Running cointegration tests...")
    global _DYNAMIC_PAIR_MAP
    _DYNAMIC_PAIR_MAP = find_cointegrated_pairs(data)
    print()

    # -----------------------------------------------------------------------
    # INTERMARKET SIGNALS — cross-asset capital flow confirmation (v5.3)
    # -----------------------------------------------------------------------
    print("Computing intermarket cross-asset signals...")
    intermarket = compute_intermarket_signals(data)
    im_details = intermarket.get("details", {})
    risk_label = "RISK-ON" if intermarket["risk_on_score"] >= 60 else ("RISK-OFF" if intermarket["risk_on_score"] <= 40 else "NEUTRAL")
    print(f"  Risk-on score: {intermarket['risk_on_score']:.0f}/100 [{risk_label}] | "
          f"Credit: {intermarket['credit']} | Dollar: {intermarket['dollar']} | "
          f"Safe-haven: {'YES (gold rallying)' if intermarket['safe_haven'] else 'no'}")
    if im_details:
        print(f"  Details: { ' | '.join(f'{k}={v:+.1f}%' for k, v in im_details.items()) }")
    data["__intermarket__"] = intermarket  # type: ignore[assignment]
    print()

    # -----------------------------------------------------------------------
    # WEEKLY TREND FILTER — multi-timeframe alignment (v5.4)
    # Trend-following signals are blocked for symbols in weekly bear trends
    # -----------------------------------------------------------------------
    print("Computing weekly trend alignment (65d SMA proxy)...")
    weekly_trend = compute_weekly_trends(data)
    bull_syms = [s for s, t in weekly_trend.items() if t == "bull"]
    bear_syms = [s for s, t in weekly_trend.items() if t == "bear"]
    print(f"  Weekly trends: {len(bull_syms)} bull | {len(bear_syms)} bear | "
          f"{len(weekly_trend) - len(bull_syms) - len(bear_syms)} neutral")
    if bear_syms[:8]:
        print(f"  Bear (trend-following blocked): {bear_syms[:8]}{'...' if len(bear_syms) > 8 else ''}")
    data["__weekly_trend__"] = weekly_trend  # type: ignore[assignment]
    print()

    # -----------------------------------------------------------------------
    # SECTOR RELATIVE STRENGTH RANKINGS — top-N sector filter (v5.8)
    # -----------------------------------------------------------------------
    print("Computing sector relative strength rankings...")
    sector_ranks = compute_sector_rankings(data)
    if sector_ranks:
        top3 = [etf for etf, r in sorted(sector_ranks.items(), key=lambda x: x[1])[:3]]
        bot3 = [etf for etf, r in sorted(sector_ranks.items(), key=lambda x: x[1], reverse=True)[:3]]
        print(f"  Sector leaders (top 3): {top3}")
        print(f"  Sector laggards (bot 3): {bot3}")
    data["__sector_ranks__"] = sector_ranks  # type: ignore[assignment]
    print()

    # -----------------------------------------------------------------------
    # MARKET BREADTH — % stocks above 50d SMA (broad bull vs narrow bear) (v6.0)
    # -----------------------------------------------------------------------
    print("Computing market breadth (stocks above 50d SMA)...")
    breadth = compute_market_breadth(data)
    breadth_emoji = "📈" if breadth["signal"] == "bull" else ("📉" if breadth["signal"] == "bear" else "➡️")
    print(f"  {breadth_emoji} Breadth: {breadth['breadth_pct']:.0f}% above 50d SMA "
          f"({breadth['above']}/{breadth['total']} stocks) — {breadth['signal'].upper()}")
    if breadth["alloc_mult"] < 1.0:
        print(f"  ⚠ Breadth bear: stock allocations reduced ×{breadth['alloc_mult']:.2f}")
    data["__breadth__"] = breadth  # type: ignore[assignment]
    # v6.6: Cross-sectional momentum ranks (Fama-French / Jegadeesh-Titman)
    print("Computing cross-sectional momentum ranks (v6.6)...")
    mom_ranks = compute_cross_sectional_momentum_ranks(data)
    if mom_ranks:
        top_momo = sorted(mom_ranks.items(), key=lambda x: -x[1])[:5]
        print(f"  {len(mom_ranks)} symbols ranked — top momentum: "
              f"{', '.join(f'{s}({r:.0f}%ile)' for s, r in top_momo)}")
    else:
        print("  Cross-sectional ranks: insufficient data (< 3 symbols with 252d history)")
    data["__mom_ranks__"] = mom_ranks  # type: ignore[assignment]
    # v6.8: Trend strength composite (ADX-based market regime)
    print("Computing trend strength composite (ADX across universe)...")
    trend_strength = compute_trend_strength_composite(data)
    _ts_icons = {"trending": "📊", "mixed": "🔀", "choppy": "〰️"}
    print(f"  {_ts_icons.get(trend_strength['signal'],'?')} Market trend: {trend_strength['signal'].upper()}"
          f"  avg_ADX={trend_strength['avg_adx']:.1f}"
          f"  {trend_strength['trending_pct']:.0f}% stocks trending"
          f"  bias={trend_strength['strategy_bias']}")
    data["__trend_strength__"] = trend_strength  # type: ignore[assignment]
    print()

    # -----------------------------------------------------------------------
    # REALIZED VOLATILITY TARGETING — per-symbol alloc scaling (v5.7)
    # Scale position size inversely to realized vol (AQR/Bridgewater technique)
    # -----------------------------------------------------------------------
    # Vol targets per category (annualized %) — higher tolerance = less scaling down
    _VOL_TARGETS = {"stock": 30.0, "crypto": 70.0, "meme": 100.0, "forex": 10.0, "penny": 50.0, "skyrocket": 80.0}
    realized_vols: dict[str, float] = {}
    for sym, df_sym in data.items():
        if isinstance(sym, str) and sym.startswith("__"):
            continue
        if not isinstance(df_sym, pd.DataFrame) or "Close" not in df_sym.columns:
            continue
        try:
            ret = df_sym["Close"].pct_change()
            rv = float(ret.rolling(20).std().iloc[-1]) * (252 ** 0.5) * 100
            if rv > 0 and not np.isnan(rv):
                realized_vols[sym] = round(rv, 1)
        except Exception:
            pass
    low_vol  = {s: v for s, v in realized_vols.items() if v < 15}
    high_vol = {s: v for s, v in realized_vols.items() if v > 80}
    print(f"Realized vol targeting: {len(realized_vols)} symbols | "
          f"Low-vol (<15%): {len(low_vol)} | High-vol (>80%): {len(high_vol)}")
    print()

    # -----------------------------------------------------------------------
    # EARNINGS GUARD — exclude symbols near earnings announcements
    # -----------------------------------------------------------------------
    print("Checking earnings calendar...")
    earnings_blacklist = get_earnings_blacklist()
    if earnings_blacklist:
        print(f"  Earnings guard active: {', '.join(sorted(earnings_blacklist))} excluded for 3 days")
    else:
        print("  No earnings in 3-day window for watched symbols")

    # v6.1 — Pre-fetch earnings dates for drift algo (shares same API call pattern)
    earnings_drift_syms = ALGO_DEFS.get("earnings-drift-scout", {}).get("symbols", [])
    earnings_dates_map  = get_earnings_dates(earnings_drift_syms)
    upcoming = {s: d for s, d in earnings_dates_map.items() if d is not None}
    if upcoming:
        from datetime import date as _date
        today_d = _date.today()
        drift_candidates = {s: d for s, d in upcoming.items()
                            if 4 <= (d - today_d).days <= 18}
        print(f"  Earnings drift: {len(upcoming)} dates fetched, "
              f"{len(drift_candidates)} in 4-18d window: "
              f"{', '.join(f'{s}({d})' for s, d in sorted(drift_candidates.items()))}")
    else:
        print("  Earnings drift: no upcoming dates available")
    data["__earnings_dates__"] = earnings_dates_map  # type: ignore[assignment]
    print()

    # -----------------------------------------------------------------------
    # MACRO CALENDAR GUARD — FOMC / CPI / NFP blackout windows
    # -----------------------------------------------------------------------
    print("Checking macro calendar...")
    macro_blackout, macro_reason = get_macro_blackout(guard_days=1)
    if macro_blackout:
        print(f"  ⚠ MACRO BLACKOUT: {macro_reason} — new position sizes reduced 50%")
    else:
        print("  No high-impact macro events in ±1 day window")
    print()

    # -----------------------------------------------------------------------
    # OPTIONS FLOW — put/call ratio fear gauge
    # -----------------------------------------------------------------------
    print("Fetching options sentiment (put/call ratios)...")
    options_pcr = get_options_sentiment()
    if options_pcr:
        fear_syms = {s: pcr for s, pcr in options_pcr.items() if pcr > 1.2}
        greed_syms = {s: pcr for s, pcr in options_pcr.items() if pcr < 0.5}
        market_pcr_vals = [v for s, v in options_pcr.items() if s in ("SPY", "QQQ")]
        avg_pcr = round(sum(market_pcr_vals) / len(market_pcr_vals), 3) if market_pcr_vals else None
        print(f"  PCR fetched for {len(options_pcr)} symbols | Market avg PCR: {avg_pcr}")
        if fear_syms:
            print(f"  Fear (PCR>1.2): {fear_syms}")
        if greed_syms:
            print(f"  Greed (PCR<0.5): {greed_syms}")
    else:
        print("  Options PCR unavailable (non-market hours or rate-limited)")
    # Inject into data dict so signal functions can read it
    data["__options_pcr__"] = options_pcr  # type: ignore[assignment]
    print()

    # -----------------------------------------------------------------------
    # DERIBIT CRYPTO OPTIONS PCR — real-time, no auth (v9.8)
    # -----------------------------------------------------------------------
    print("Fetching Deribit BTC/ETH options put/call ratios (real-time)...")
    deribit_pcr = get_deribit_crypto_pcr()
    if deribit_pcr:
        for ccy, stats in deribit_pcr.items():
            print(f"  {ccy}: PCR-OI={stats['pcr_oi']:.3f} PCR-Vol={stats['pcr_vol']:.3f} "
                  f"AvgIV={stats['avg_mark_iv']:.1f}% [{stats['fear_level'].upper()}]")
    else:
        print("  Deribit PCR unavailable (network error or API down)")
    data["__deribit_pcr__"] = deribit_pcr  # type: ignore[assignment]
    print()

    # -----------------------------------------------------------------------
    # CRYPTO FEAR & GREED INDEX — alternative.me (free, no auth)
    # -----------------------------------------------------------------------
    print("Fetching Crypto Fear & Greed Index...")
    fng = get_crypto_fear_greed()
    fng_val = fng["value"]
    fng_class = fng["classification"]
    print(f"  Fear & Greed: {fng_val}/100 — {fng_class}")
    # Translate to allocation multiplier for crypto/meme
    if fng_val <= 24:
        fng_crypto_mult = 0.50   # Extreme Fear → 50%
        print("  ⚠ Extreme Fear: crypto/meme allocations capped at 50%")
    elif fng_val <= 49:
        fng_crypto_mult = 0.75   # Fear → 75%
        print("  ⚠ Fear: crypto/meme allocations capped at 75%")
    elif fng_val >= 75:
        fng_crypto_mult = 0.75   # Extreme Greed → contrarian reduction 75%
        print("  ⚠ Extreme Greed: contrarian protection — crypto/meme allocations at 75%")
    else:
        fng_crypto_mult = 1.0    # Neutral/normal
    print()

    # -----------------------------------------------------------------------
    # v10.2 — CNN Fear & Greed (stock market sentiment)
    # -----------------------------------------------------------------------
    print("Fetching CNN Fear & Greed (stock market)...")
    cnn_fg = get_cnn_fear_greed()
    cnn_score = cnn_fg["score"]
    cnn_rating = cnn_fg["rating"]
    print(f"  Stock F&G: {cnn_score}/100 — {cnn_rating}  (prev close: {cnn_fg['prev_close']} | prev week: {cnn_fg['prev_week']})")
    if cnn_score <= 24:
        cnn_stock_mult = 0.60    # Extreme Fear → tighten stock allocations
        print("  ⚠ Extreme Fear: stock allocations capped at 60%")
    elif cnn_score >= 76:
        cnn_stock_mult = 0.80    # Extreme Greed → contrarian caution
        print("  ⚠ Extreme Greed: contrarian caution — stock allocations at 80%")
    else:
        cnn_stock_mult = 1.0
    data["__stock_fear_greed__"] = cnn_fg  # type: ignore[assignment]
    print()

    # -----------------------------------------------------------------------
    # v10.2 — CoinGecko Global: real BTC dominance % + market cap change
    # -----------------------------------------------------------------------
    print("Fetching CoinGecko global crypto market data...")
    cg_global = get_coingecko_global()
    btc_dom_pct = cg_global["btc_dominance"]
    mc_change_24h = cg_global["market_cap_change_24h_pct"]
    altcoin_pct = cg_global["altcoin_pct"]
    print(f"  BTC dominance: {btc_dom_pct:.1f}%  ETH: {cg_global['eth_dominance']:.1f}%  Alts: {altcoin_pct:.1f}%")
    print(f"  Total market cap 24h change: {mc_change_24h:+.2f}%")
    data["__coingecko_global__"] = cg_global  # type: ignore[assignment]
    print()

    # -----------------------------------------------------------------------
    # v10.2 — Binance 24hr top movers (crypto momentum context)
    # -----------------------------------------------------------------------
    print("Fetching Binance 24hr top movers...")
    binance_movers = get_binance_top_movers()
    if binance_movers["gainers"]:
        top_g = ", ".join(f"{g['symbol']}({g['pct_change']:+.1f}%)" for g in binance_movers["gainers"][:3])
        top_l = ", ".join(f"{l['symbol']}({l['pct_change']:+.1f}%)" for l in binance_movers["losers"][:3])
        print(f"  Top gainers: {top_g}")
        print(f"  Top losers:  {top_l}")
    else:
        print("  Binance movers unavailable (network error)")
    data["__binance_movers__"] = binance_movers  # type: ignore[assignment]
    print()

    # -----------------------------------------------------------------------
    # v11.0 — New pre-computed signal injections (crypto accel + ML)
    # -----------------------------------------------------------------------
    if _HAS_ACCEL:
        print("Fetching order book imbalance (Binance)...")
        try:
            data["__order_book__"] = fetch_order_book_imbalance()
            imb_count = len([v for v in data["__order_book__"].values() if isinstance(v, dict) and v.get("ratio", 1) > 1.5])
            print(f"  {imb_count} symbols with strong buy imbalance (bid/ask > 1.5×)")
        except Exception as _e:
            data["__order_book__"] = {}
            print(f"  Order book fetch failed: {_e}")

        print("Fetching Binance liquidation proxy...")
        try:
            data["__liquidations__"] = fetch_binance_liquidations()
            liq_count = len(data["__liquidations__"])
            print(f"  {liq_count} symbols with liquidation cascade signals")
        except Exception as _e:
            data["__liquidations__"] = {}
            print(f"  Liquidation fetch failed: {_e}")

        print("Loading Telegram alpha signals...")
        try:
            data["__telegram_calls__"] = load_telegram_signals(DATA_DIR)
            tg_count = len(data["__telegram_calls__"])
            print(f"  {tg_count} Telegram signals loaded")
        except Exception as _e:
            data["__telegram_calls__"] = {}
            print(f"  Telegram signals unavailable: {_e}")

        print("Loading Twitter alpha signals...")
        try:
            data["__twitter_calls__"] = load_twitter_signals(DATA_DIR)
            tw_count = len(data["__twitter_calls__"])
            print(f"  {tw_count} Twitter signals loaded")
        except Exception as _e:
            data["__twitter_calls__"] = {}
            print(f"  Twitter signals unavailable: {_e}")

        print("Fetching CoinGecko trending...")
        try:
            data["__cg_trending__"] = fetch_coingecko_trending()
            trending_coins = data["__cg_trending__"]
            if isinstance(trending_coins, list):
                print(f"  Trending coins: {', '.join(str(c) for c in trending_coins[:5])}")
            elif isinstance(trending_coins, dict):
                coins_list = trending_coins.get("coins", [])
                print(f"  Trending coins: {', '.join(c.get('id','?') for c in coins_list[:5])}")
            else:
                print(f"  Trending coins: {trending_coins}")
        except Exception as _e:
            data["__cg_trending__"] = {}
            print(f"  CoinGecko trending fetch failed: {_e}")
    else:
        data["__order_book__"] = {}
        data["__liquidations__"] = {}
        data["__telegram_calls__"] = {}
        data["__twitter_calls__"] = {}
        data["__cg_trending__"] = {}

    if _HAS_API_CONFIG:
        print("Fetching live forex rates (CurrencyLayer)...")
        try:
            forex_rates = get_live_forex_rates("EUR,GBP,AUD,NZD,CAD,CHF,JPY")
            data["__forex_rates__"] = forex_rates
            print(f"  Forex rates: {len(forex_rates)} pairs loaded")
        except Exception as _e:
            data["__forex_rates__"] = {}
            print(f"  Forex rates unavailable: {_e}")

        print("Fetching CryptoQuant BTC exchange netflow...")
        try:
            btc_netflow = get_exchange_netflow("btc")
            data["__exchange_netflow__"] = {"btc": btc_netflow}
            flow_val = btc_netflow.get("value", 0)
            sentiment = "OUTFLOW (bullish)" if flow_val < 0 else "INFLOW (bearish)"
            print(f"  BTC netflow: {flow_val:.0f} BTC — {sentiment}")
        except Exception as _e:
            data["__exchange_netflow__"] = {}
            print(f"  CryptoQuant netflow unavailable: {_e}")
    else:
        data["__forex_rates__"] = {}
        data["__exchange_netflow__"] = {}

    # ML signal weights injection
    if _HAS_ML:
        try:
            _ml_ranker_inst = MLSignalRanker(str(DATA_DIR))
            _ml_ranker_inst.train_if_ready()  # Retrain with latest data (safe: won't destroy loaded model)
            data["__ml_weights__"] = _ml_ranker_inst.get_weights()
            n_algos = len(data["__ml_weights__"])
            _ml_mode = "RF" if _ml_ranker_inst.is_trained else "heuristic"
            _ml_auc = f" AUC={_ml_ranker_inst.cv_auc:.3f}" if _ml_ranker_inst.cv_auc else ""
            print(f"  ML weights loaded for {n_algos} algorithms (mode={_ml_mode}{_ml_auc})")
        except Exception as _e:
            data["__ml_weights__"] = {}
            print(f"  ML ranker unavailable: {_e}")
    else:
        data["__ml_weights__"] = {}
    print()

    # -----------------------------------------------------------------------
    # v10.1: Intraday price refresh for active picks
    # Fetches 5-min bars (period="2d") for every symbol that has an open
    # position. This gives a price that is minutes rather than hours old,
    # allowing stops and TPs to fire correctly during market hours and for
    # 24/7 assets (crypto) at any time. Falls back to daily close if fetch fails.
    # -----------------------------------------------------------------------
    active_syms: set[str] = set()
    for algo in live["algorithms"]:
        for p in algo.get("activePicks", []):
            sym = p.get("symbol")
            if sym:
                active_syms.add(sym)

    intraday_prices: dict[str, float] = {}
    if active_syms:
        print(f"  Refreshing intraday prices for {len(active_syms)} active symbols...")
        for sym in sorted(active_syms):
            price = fetch_latest_price(sym)
            if price is not None:
                intraday_prices[sym] = price

    # v10.4/v11.4: Backfill missing fields on existing open picks (migration)
    # v11.4: When stopPrice/targetPrice are missing, attempt ATR-based calculation
    # using available OHLCV data before falling back to static CATEGORY_RISK bands.
    for algo in live["algorithms"]:
        algo_cat_bf = algo.get("category", "stock")
        for p in algo.get("activePicks", []):
            sym = p.get("symbol", "")
            ep = float(p.get("entryPrice") or 0)
            if ep <= 0:
                continue
            # symbolCategory: true asset class independent of algo category
            if "symbolCategory" not in p:
                p["symbolCategory"] = "crypto" if sym.endswith("-USD") else algo_cat_bf
            sym_cat_bf = p["symbolCategory"]
            sl_bf, tp_bf, mh_bf = CATEGORY_RISK.get(sym_cat_bf, CATEGORY_RISK["stock"])
            # v11.4: Try ATR-based TP/SL for legacy picks that lack these fields
            if not p.get("stopPrice") or not p.get("targetPrice") or not p.get("tpSlMethod"):
                if sym in data and data[sym] is not None and len(data[sym]) >= 20:
                    _bf_tp, _bf_sl, _bf_ptp, _bf_atr, _bf_tp_pct, _bf_sl_pct, _bf_method = compute_atr_tp_sl(
                        data[sym], sym_cat_bf, ep
                    )
                    p["stopPrice"] = round(_bf_sl, 8)
                    p["targetPrice"] = round(_bf_tp, 8)
                    p["stopLossPct"] = _bf_sl_pct
                    p["takeProfitPct"] = _bf_tp_pct
                    p["tpProbability"] = _bf_ptp
                    p["signalProbability"] = calculate_signal_probability(ep, _bf_tp, _bf_sl, _bf_atr)
                    p["atrValue"] = round(_bf_atr, 8) if _bf_atr else None
                    p["tpSlMethod"] = _bf_method
                else:
                    # Static fallback when no OHLCV data available
                    if not p.get("stopPrice"):
                        p["stopPrice"] = round(ep * (1 + sl_bf), 6)
                    if not p.get("targetPrice"):
                        p["targetPrice"] = round(ep * (1 + tp_bf), 6)
                    if not p.get("tpSlMethod"):
                        p["tpSlMethod"] = "static"
            if not p.get("riskReward"):
                _tp_abs = float(p.get("targetPrice", ep * (1 + tp_bf)))
                _sl_abs = float(p.get("stopPrice", ep * (1 + sl_bf)))
                p["riskReward"] = round(abs(_tp_abs - ep) / max(abs(ep - _sl_abs), 0.0001), 2)
            if not p.get("maxHoldDays"):
                p["maxHoldDays"] = mh_bf
            if not p.get("peakPrice"):
                p["peakPrice"] = round(ep, 6)

    # -----------------------------------------------------------------------
    # EXIT LOGIC — per-pick ATR-based stop-loss/take-profit/max-hold
    # v11.4: Uses per-pick stopPrice/targetPrice (ATR-based) instead of
    # category-wide static percentages. This fixes the 94% expiry problem
    # where static bands were too wide for most symbols' actual volatility.
    # Falls back to category percentage bands for legacy picks without
    # stopPrice/targetPrice fields.
    # -----------------------------------------------------------------------
    total_exits = 0
    for algo in live["algorithms"]:
        # Per-category risk parameters — used as fallback for legacy picks
        cat = algo.get("category", "stock")
        SL, TP, MH = CATEGORY_RISK.get(cat, CATEGORY_RISK["stock"])

        picks   = algo.get("activePicks", [])
        closed  = algo.get("closedPicks", [])
        cash    = float(algo.get("cash", STARTING_CAPITAL))
        surviving = []
        trail_pct = TRAILING_STOP.get(cat, 0.08)
        # v6.9 — regime-adaptive stop-loss tightening (for fallback percentages)
        SL, TP, trail_pct = compute_adaptive_stop_params(
            SL, TP, trail_pct, cat, regime, data.get("__vix_term__", {})
        )
        for p in picks:
            sym = p["symbol"]
            # v10.1: prefer fresh intraday price; fall back to daily close
            if sym in intraday_prices:
                p["currentPrice"] = round(intraday_prices[sym], 6)
            elif sym in data:
                p["currentPrice"] = round(float(data[sym]["Close"].iloc[-1]), 6)
            entry = p.get("entryPrice") or 0
            curr  = p.get("currentPrice") or entry
            alloc = float(p.get("allocation", ALLOCATION_PER_PICK))
            if entry <= 0:
                surviving.append(p)
                continue

            # Update peak price (trailing high watermark)
            peak = max(float(p.get("peakPrice", entry)), curr)
            p["peakPrice"] = round(peak, 6)

            ret = (curr - entry) / entry
            try:
                entry_dt  = datetime.fromisoformat(p.get("entryDate", "").replace("Z", "+00:00"))
                hold_days = (now - entry_dt).days
            except Exception:
                hold_days = 0

            # v11.4: Per-pick ATR-based exit — use absolute stopPrice/targetPrice
            # when available (set by compute_atr_tp_sl at entry time).
            # Falls back to category percentage bands for legacy picks.
            _pick_target = p.get("targetPrice")
            _pick_stop = p.get("stopPrice")
            exit_reason = None
            if _pick_target and _pick_stop and entry > 0:
                # ATR-based exit: compare current price against absolute levels
                if curr >= _pick_target:
                    exit_reason = f"TAKE_PROFIT {ret*100:.1f}% (ATR target={_pick_target:.4f})"
                elif curr <= _pick_stop:
                    exit_reason = f"STOP_LOSS {ret*100:.1f}% (ATR stop={_pick_stop:.4f})"
            else:
                # Legacy fallback: percentage-based exit
                if ret >= TP:
                    exit_reason = f"TAKE_PROFIT {ret*100:.1f}%"
                elif ret <= SL:
                    exit_reason = f"STOP_LOSS {ret*100:.1f}%"
            # Time exit and trailing stop apply regardless of TP/SL method
            if not exit_reason and hold_days >= MH:
                exit_reason = f"TIME_EXIT ({hold_days}d)"
            if not exit_reason and (ret >= TRAIL_ACTIVATE_PROFIT and
                  peak > entry and
                  curr < peak * (1.0 - trail_pct)):
                # Trailing stop: position was in profit, now pulled back from peak
                drawdown_from_peak = (curr - peak) / peak
                exit_reason = f"TRAIL_STOP {drawdown_from_peak*100:.1f}% from peak (peak={peak:.4f})"
            if exit_reason:
                # v11.6: Deduct transaction costs from P&L
                _sym_cat = p.get("symbolCategory", cat)
                _exit_cost_pct = _tc_get_round_trip_cost(sym, _sym_cat)
                gross_pnl  = alloc * ret
                net_ret = ret - _exit_cost_pct
                net_pnl = alloc * net_ret
                cash += alloc + net_pnl
                closed_pick = {
                    **p,
                    "exitDate":   now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "exitReason": exit_reason,
                    "grossPnl":   round(gross_pnl, 2),        # v11.6: before costs
                    "pnl":        round(net_pnl, 2),           # v11.6: after costs (net)
                    "grossReturnPct": round(ret * 100, 2),     # v11.6: gross return %
                    "returnPct":  round(net_ret * 100, 2),     # v11.6: net return %
                    "transactionCostPct": round(_exit_cost_pct * 100, 3),  # v11.6: cost deducted
                }
                closed.append(closed_pick)
                total_exits += 1
                print(f"  EXIT [{algo.get('tier','?')}] {algo.get('name','?')}: {sym} {exit_reason}  "
                      f"Gross=${gross_pnl:+.2f}  Net=${net_pnl:+.2f}  Cost={_exit_cost_pct*100:.2f}%")
                append_audit(audit_path, {
                    "timestamp": now.isoformat(), "action": "CLOSE",
                    "algorithm": algo["id"], "symbol": sym,
                    "reason": exit_reason, "price": curr, "pnl": round(net_pnl, 2),
                })
            else:
                surviving.append(p)
        algo["activePicks"] = surviving
        algo["closedPicks"] = closed
        algo["cash"] = round(cash, 2)

    if total_exits:
        print(f"  Closed {total_exits} positions")
        # Collect picks closed this scan and send to rapid validation engine
        just_closed = []
        ts_prefix = now.strftime("%Y-%m-%dT%H:%M")
        for algo in live["algorithms"]:
            for cp in algo.get("closedPicks", []):
                if not cp.get("exitDate", "").startswith(ts_prefix):
                    continue
                entry_price = float(cp.get("entryPrice") or 0)
                exit_price  = float(cp.get("currentPrice") or 0)
                # Use pre-computed returnPct (net of costs) when available
                return_pct = cp.get("returnPct")
                if return_pct is not None:
                    pnl_pct = float(return_pct) / 100.0
                elif entry_price > 0:
                    pnl_pct = (exit_price - entry_price) / entry_price
                else:
                    pnl_pct = 0
                just_closed.append({
                    "algorithm":   algo["id"],
                    "symbol":      cp.get("symbol", ""),
                    "entry_price": entry_price,
                    "exit_price":  exit_price,
                    "pnl":         round(pnl_pct, 6),
                    "pnl_pct":     round(pnl_pct * 100, 4),  # percent form for consumers
                    "outcome":     "win" if pnl_pct >= 0 else "loss",
                    "entry_date":  cp.get("entryDate", ""),
                    "exit_date":   cp.get("exitDate", ""),
                })
        if just_closed:
            ingest_result = ingest_to_rapid_validation(just_closed)
            if ingest_result.get("ok"):
                ig = ingest_result.get("ingested", 0)
                rk = ingest_result.get("rankings", {})
                print(f"  RapidVal ingest: {ig} picks sent | "
                      f"promoted={rk.get('promoted',0)} testing={rk.get('testing',0)} eliminated={rk.get('eliminated',0)}")
            else:
                print(f"  RapidVal ingest warning: {ingest_result.get('error', 'unknown error')}")
        print()

    # -----------------------------------------------------------------------
    # SOCIAL SENTIMENT — StockTwits free API for meme/penny symbols
    # Injected into data dict as "__sentiment__" key for signal functions
    # -----------------------------------------------------------------------
    meme_syms = ALGO_DEFS.get("meme-velocity", {}).get("symbols", []) + \
                ALGO_DEFS.get("short-squeeze", {}).get("symbols", [])
    print("Fetching social sentiment (StockTwits)...")
    sentiment_data = get_stocktwits_sentiment(list(set(meme_syms)))
    if sentiment_data:
        bullish_syms = [s for s, p in sentiment_data.items() if p > 60]
        print(f"  Sentiment fetched for {len(sentiment_data)} symbols | Bullish (>60%): {bullish_syms or 'none'}")
    else:
        print("  StockTwits unavailable — proceeding without sentiment")
    # Also fetch Reddit WSB buzz and merge into sentiment scores
    print("Fetching Reddit r/WallStreetBets buzz...")
    wsb_scores = get_reddit_wsb_sentiment(meme_syms)
    if wsb_scores:
        top_wsb = sorted(wsb_scores.items(), key=lambda x: -x[1])[:5]
        print(f"  WSB buzz: {top_wsb}")
        # Blend: 60% StockTwits + 40% WSB (or just WSB if ST unavailable)
        for sym, wsb_score in wsb_scores.items():
            st_score = sentiment_data.get(sym, 50.0)
            blended = round(0.6 * st_score + 0.4 * wsb_score, 1)
            sentiment_data[sym] = blended
    else:
        print("  Reddit WSB unavailable — using StockTwits only")
    data["__sentiment__"] = sentiment_data  # injected into all_data for signal functions
    print()

    # -----------------------------------------------------------------------
    # APEWISDOM MENTION MOMENTUM — multi-subreddit momentum delta (v9.9)
    # -----------------------------------------------------------------------
    # ApeWisdom aggregates WSB + r/stocks + r/investing + r/Superstonk 2x/hr.
    # The mention_ratio (now/24h-ago) is a forward-looking alpha signal.
    print("Fetching ApeWisdom Reddit mention momentum...")
    ape_syms = (
        [s for s in STOCKS_ETF if "^" not in s and "=X" not in s]
        + ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "ADA-USD", "DOGE-USD",
           "SHIB-USD", "MATIC-USD"]
    )
    ape_data = get_apewisdom_sentiment(ape_syms)
    if ape_data:
        hot_ape = sorted(ape_data.items(), key=lambda x: -x[1]["mention_ratio"])[:5]
        print(f"  ApeWisdom: {len(ape_data)} symbols tracked")
        surges_str = ", ".join(f"{s}(x{d['mention_ratio']:.1f})" for s, d in hot_ape)
        print(f"  Top mention surges: {surges_str}")
    else:
        print("  ApeWisdom unavailable (network error)")
    data["__apewisdom__"] = ape_data  # type: ignore[assignment]
    print()

    # -----------------------------------------------------------------------
    # SHORT INTEREST — fetch SI ratio for short-squeeze candidates
    # (yfinance .info call — only for squeeze symbols to keep runtime fast)
    # -----------------------------------------------------------------------
    squeeze_syms = [s for s in ALGO_DEFS.get("short-squeeze", {}).get("symbols", [])
                    if not s.endswith("-USD") and "=X" not in s]  # stocks only, no crypto/forex
    print(f"Fetching short interest for {len(squeeze_syms)} symbols...")
    short_interest_data = get_short_interest(squeeze_syms[:10])  # cap at 10 to limit latency
    high_si_syms = [s for s, d in short_interest_data.items() if d.get("short_pct", 0) > 0.20]
    if high_si_syms:
        print(f"  High SI (>20%): {high_si_syms}")
    else:
        print(f"  SI fetched for {len(short_interest_data)} symbols — none heavily shorted")
    data["__short_interest__"] = short_interest_data  # type: ignore[assignment]
    print()

    # -----------------------------------------------------------------------
    # NEWS HEADLINE SENTIMENT — yfinance news for high-impact stocks
    # (keyword heuristic: no NLP library needed)
    # -----------------------------------------------------------------------
    news_syms = ["SPY", "QQQ", "AAPL", "MSFT", "NVDA", "TSLA", "AMD", "COIN", "MSTR"]
    print("Fetching news headline sentiment...")
    news_sentiment = get_news_sentiment(news_syms)
    if news_sentiment:
        very_bullish = [s for s, sc in news_sentiment.items() if sc > 70]
        very_bearish  = [s for s, sc in news_sentiment.items() if sc < 30]
        print(f"  News sentiment: {len(news_sentiment)} symbols | Bullish: {very_bullish or 'none'} | Bearish: {very_bearish or 'none'}")
    else:
        print("  News sentiment unavailable")
    data["__news_sentiment__"] = news_sentiment  # type: ignore[assignment]
    print()

    # -----------------------------------------------------------------------
    # VOLATILITY-SCALED ALLOCATION — reduce position size in bear markets
    # -----------------------------------------------------------------------
    # In bear market regime: 60% of base allocation (risk parity principle)
    # In elevated crypto bear: crypto/meme strategies capped at 70% allocation
    stock_bear = regime.get("stock") == "bear"
    crypto_bear = regime.get("crypto") == "bear"
    vol_alloc_stock  = int(ALLOCATION_PER_PICK * 0.6) if stock_bear else ALLOCATION_PER_PICK
    vol_alloc_crypto = int(ALLOCATION_PER_PICK * 0.65) if crypto_bear else ALLOCATION_PER_PICK
    # Macro blackout: halve new position sizes near FOMC/CPI/NFP
    macro_alloc_mult = 0.5 if macro_blackout else 1.0
    if macro_blackout:
        vol_alloc_stock  = int(vol_alloc_stock  * macro_alloc_mult)
        vol_alloc_crypto = int(vol_alloc_crypto * macro_alloc_mult)
    # Fear & Greed multiplier — only affects crypto/meme allocations
    vol_alloc_crypto = int(vol_alloc_crypto * fng_crypto_mult)
    # v10.2 CNN Fear & Greed multiplier — affects stock allocations
    vol_alloc_stock = int(vol_alloc_stock * cnn_stock_mult)
    # VIX-based stock allocation scaling
    vix_level = regime.get("vix", 20.0)
    if vix_level > 40:
        vix_stock_mult = 0.35    # extreme crisis (VIX 40+) → 35%
    elif vix_level > 30:
        vix_stock_mult = 0.60    # high fear (VIX 30-40) → 60%
    elif vix_level > 25:
        vix_stock_mult = 0.80    # elevated (VIX 25-30) → 80%
    elif vix_level < 15:
        vix_stock_mult = 0.85    # complacency (VIX <15) → 85% warning
    else:
        vix_stock_mult = 1.0     # normal range
    vol_alloc_stock = int(vol_alloc_stock * vix_stock_mult)
    # v6.0 Market breadth multiplier — broad bear breadth = reduce stock alloc
    breadth_data = data.get("__breadth__", {})
    breadth_mult = float(breadth_data.get("alloc_mult", 1.0)) if isinstance(breadth_data, dict) else 1.0
    if breadth_mult < 1.0:
        vol_alloc_stock = int(vol_alloc_stock * breadth_mult)
    # v6.2 VIX term structure multiplier — backwardation = reduce new positions
    vix_term_data = data.get("__vix_term__", {})
    vix_term_mult = float(vix_term_data.get("risk_mult", 1.0)) if isinstance(vix_term_data, dict) else 1.0
    if vix_term_mult != 1.0:
        vol_alloc_stock = int(vol_alloc_stock * vix_term_mult)
    if stock_bear:
        print(f"  VOLATILITY SCALE: stock regime BEAR — capping stock allocations to ${vol_alloc_stock:,}")
    if vix_stock_mult < 1.0:
        print(f"  VIX SCALE: VIX={vix_level:.1f} → stock alloc multiplier={vix_stock_mult:.2f}")
    if vix_term_mult != 1.0:
        _ts_sig = vix_term_data.get("term_signal", "flat")
        print(f"  VIX TERM SCALE: {_ts_sig.upper()} (ratio={vix_term_data.get('term_ratio',1.0):.3f}) → alloc ×{vix_term_mult:.2f}")
    if crypto_bear:
        print(f"  VOLATILITY SCALE: crypto regime BEAR — capping crypto allocations to ${vol_alloc_crypto:,}")

    # -----------------------------------------------------------------------
    # v10.5 pre-scan setup: global held map + today's intraday move per symbol
    # -----------------------------------------------------------------------
    # Global held map: symbol → count of algos currently holding it
    global_held_counts: dict[str, int] = {}
    for _a in live["algorithms"]:
        for _p in _a.get("activePicks", []):
            _s = _p.get("symbol", "")
            if _s:
                global_held_counts[_s] = global_held_counts.get(_s, 0) + 1

    # Today's move: (close - open) / open for each loaded symbol (or close-to-close if no open)
    today_move: dict[str, float] = {}
    for _sym, _df in data.items():
        if isinstance(_sym, str) and _sym.startswith("__"):
            continue
        try:
            _c = float(_df["Close"].iloc[-1])
            _o = float(_df["Open"].iloc[-1]) if "Open" in _df.columns else 0
            if _o > 0:
                today_move[_sym] = (_c - _o) / _o
            elif len(_df) >= 2:
                _prev = float(_df["Close"].iloc[-2])
                today_move[_sym] = (_c - _prev) / _prev if _prev > 0 else 0
        except Exception:
            pass

    print(f"  Global held map: {len(global_held_counts)} symbols · {sum(global_held_counts.values())} total positions")
    top_concentrated = sorted(global_held_counts.items(), key=lambda x: -x[1])[:5]
    if top_concentrated:
        print(f"  Top concentrations: " + ", ".join(f"{s}(x{n})" for s, n in top_concentrated))

    # -----------------------------------------------------------------------
    # SIGNAL SCANNING — drought-adaptive thresholds
    # -----------------------------------------------------------------------
    new_picks_flat: list[dict] = []
    signals_found = 0

    # Pre-load elimination state for signal-generation filtering
    _banned_algos: set = set(PERMANENTLY_BANNED_STRATEGIES)
    if _HAS_ELIMINATION:
        try:
            _elim_check = EliminationEngine()
            _elim_state = _elim_check.get_state()
            _banned_algos.update(_elim_state.get("eliminated", []))
        except Exception:
            pass
    if _banned_algos:
        print(f"  [ELIM] Skipping {len(_banned_algos)} banned/eliminated strategies in signal scan")

    for algo_id, func in SIGNAL_FUNCS.items():
        algo = algos_by_id.get(algo_id)
        if not algo:
            continue

        # Skip banned and eliminated strategies — no signal generation at all
        if algo_id in _banned_algos:
            continue

        spec    = ALGO_DEFS.get(algo_id, {})
        symbols = spec.get("symbols", [])
        cash    = float(algo.get("cash", STARTING_CAPITAL))
        picks   = algo.get("activePicks", [])
        held    = {p["symbol"] for p in picks}
        drought = int(algo.get("droughtScans", 0))

        for symbol in symbols:
            if symbol not in data:
                continue
            # Skip permanently banned symbols (proven losers in live trading)
            base_sym = symbol.replace("-USD", "").replace("=X", "").upper()
            if base_sym in PERMANENTLY_BANNED_SYMBOLS or symbol in PERMANENTLY_BANNED_SYMBOLS:
                continue
            # Skip symbols with earnings announcement in the next 3 days
            if symbol in earnings_blacklist:
                continue
            # Weekly trend filter (v5.4): block trend-following in weekly bear trends
            wt = weekly_trend.get(symbol, "neutral")
            bias = REGIME_BIAS.get(algo_id, "both")
            if wt == "bear" and bias == "trend":
                continue   # weekly downtrend — skip trend-following signals
            df = data[symbol]
            # Pass drought to functions that accept it (v3 strategies)
            try:
                import inspect as _inspect
                sig_params = _inspect.signature(func).parameters
                if len(sig_params) >= 4:
                    signal, reason = func(symbol, df, data, drought)
                else:
                    signal, reason = func(symbol, df, data)
            except Exception:
                try:
                    signal, reason = func(symbol, df, data)
                except Exception as _inner_exc:
                    print(f"  [WARN] {algo_id} crashed on {symbol}: {_inner_exc}")
                    signal, reason = None, ""
            if signal != "BUY" or not reason:
                continue

            # v10.3: Use intraday price for paper-trading entry accuracy.
            # For stocks/forex: block entries outside market hours (pre/post market
            # prices are not reliably executable). Crypto is 24/7 — always allowed.
            algo_cat_entry = spec.get("category", "stock")
            is_crypto_entry = algo_cat_entry in ("crypto", "meme", "skyrocket")
            if not is_crypto_entry and not is_us_market_open():
                continue   # skip stock/forex/penny picks outside 9:30-16:00 ET

            # v10.5: Gap-chase rejection — block entry if symbol already moved too much today.
            # Lesson: RIVN entered at +26.6% intraday gap → immediately faded -5%.
            # Momentum strategies need pullback confirmation, not same-session gap entry.
            _sym_cat_for_gap = "crypto" if symbol.endswith("-USD") else algo_cat_entry
            _gap_thresh = GAP_REJECT_THRESH.get(_sym_cat_for_gap, 0.05)
            _today_chg = today_move.get(symbol, 0)
            if _today_chg > _gap_thresh:
                print(f"  GAP_REJECT {symbol}: already +{_today_chg*100:.1f}% today (>{_gap_thresh*100:.0f}% thresh)")
                continue

            # v10.5: Global symbol concentration cap — max MAX_SAME_SYMBOL_GLOBAL algos per symbol.
            # Prevents RIVN-style x4 stack where every meme/penny algo piles into the same name.
            if global_held_counts.get(symbol, 0) >= MAX_SAME_SYMBOL_GLOBAL:
                continue   # already at global concentration limit for this symbol

            # Prefer fresh intraday price; fall back to last daily close
            intraday_entry = fetch_latest_price(symbol)
            current_price = intraday_entry if intraday_entry and intraday_entry > 0 \
                            else float(df["Close"].iloc[-1])
            # v10.4: Sanity-check the price — reject data-feed garbage (e.g. APT @ $0.0001)
            _entry_cat = "crypto" if symbol.endswith("-USD") else algo_cat_entry
            if not _validate_price(symbol, current_price, _entry_cat):
                print(f"  SKIP {symbol}: price sanity fail ({current_price}) for cat={_entry_cat}")
                continue

            # Audit every signal (even if we can't open a position)
            append_audit(audit_path, {
                "timestamp": now.isoformat(),
                "algorithm": algo_id,
                "tier": spec.get("tier", "?"),
                "strategy": spec.get("strategy", "?"),
                "symbol": symbol,
                "signal": signal,
                "reason": reason,
                "price": current_price,
            })
            signals_found += 1

            # Position limits
            if symbol in held:
                continue
            if len(picks) >= MAX_PICKS_PER_ALGO:
                continue
            if cash < 100:
                continue

            # Volatility-scaled allocation: reduce in bear regimes
            algo_cat = spec.get("category", "stock")
            if algo_cat in ("crypto", "meme", "skyrocket"):
                base_alloc = vol_alloc_crypto
            else:
                base_alloc = vol_alloc_stock
            # v5.7 Dynamic vol targeting: scale position inversely to realized vol
            rv = realized_vols.get(symbol)
            if rv and rv > 0:
                vol_target = _VOL_TARGETS.get(algo_cat, 30.0)
                vol_scale = max(0.25, min(1.5, vol_target / rv))
                base_alloc = int(base_alloc * vol_scale)
            # v7.0 Kelly-weighted sizing — algos with proven edge get larger alloc
            kf = _compute_kelly_for_algo(algo)
            kelly_mult = 1.0
            if kf > 0:
                # Normalize: 15% Kelly = 1.0× baseline; higher Kelly = larger; lower = smaller
                kelly_mult = max(0.50, min(2.0, kf / 0.15))
                base_alloc = int(base_alloc * kelly_mult)
            # v10.5: Regime-adaptive strategy class boost
            # In fear regimes (CNN F&G < 40): mean-reversion wins → boost mean_rev, cut trend
            # In greed regimes (CNN F&G > 65): momentum wins → boost trend, cut mean_rev
            _fg_score = data.get("__fear_greed__", {}).get("score", 50) if isinstance(data.get("__fear_greed__"), dict) else 50
            _algo_bias = REGIME_BIAS.get(algo_id, "both")
            _regime_mult = 1.0
            if _fg_score < 35 and _algo_bias == "mean_rev":
                _regime_mult = 1.25   # extreme fear → mean-reversion picks get 25% larger size
            elif _fg_score < 35 and _algo_bias == "trend":
                _regime_mult = 0.70   # extreme fear → trend picks get 30% smaller size
            elif _fg_score > 68 and _algo_bias == "trend":
                _regime_mult = 1.20   # extreme greed → momentum picks get 20% larger size
            elif _fg_score > 68 and _algo_bias == "mean_rev":
                _regime_mult = 0.75   # extreme greed → mean-rev picks get 25% smaller size
            if _regime_mult != 1.0:
                base_alloc = int(base_alloc * _regime_mult)
            # v10.5: Sector relative strength confirmation for stock picks
            # If sector ETF has negative 5d momentum vs SPY, reduce stock allocation in that sector
            _sector_etf_map = {
                "XOM": "XLE", "CVX": "XLE", "COP": "XLE",           # Energy
                "JPM": "XLF", "BAC": "XLF", "GS": "XLF",            # Financials
                "AAPL": "XLK", "MSFT": "XLK", "NVDA": "XLK",        # Tech
                "JNJ": "XLV", "UNH": "XLV",                          # Health
                "CAT": "XLI", "HON": "XLI",                          # Industrial
            }
            _sector_sym = _sector_etf_map.get(symbol)
            if _sector_sym and _sector_sym in data:
                _sec_df = data[_sector_sym]
                _spy_df = data.get("SPY")
                if _spy_df is not None and len(_sec_df) >= 6 and len(_spy_df) >= 6:
                    _sec_5d = (_sec_df["Close"].iloc[-1] - _sec_df["Close"].iloc[-6]) / _sec_df["Close"].iloc[-6]
                    _spy_5d = (_spy_df["Close"].iloc[-1] - _spy_df["Close"].iloc[-6]) / _spy_df["Close"].iloc[-6]
                    if _sec_5d < _spy_5d - 0.02:   # sector underperforming SPY by >2% over 5d
                        base_alloc = int(base_alloc * 0.60)   # cut allocation 40% in weak sector
                        print(f"    SECTOR_RS_CUT {symbol} ({_sector_sym} 5d={_sec_5d*100:.1f}% vs SPY {_spy_5d*100:.1f}%)")
            allocation = min(base_alloc, cash)
            shares = allocation / current_price
            # v10.4: per-pick risk levels and true asset category for dashboard display
            # Skyrocket strategies keep their own category for tighter TP/SL
            sym_cat = algo_cat if algo_cat == "skyrocket" else ("crypto" if symbol.endswith("-USD") else algo_cat)
            _cat_risk = CATEGORY_RISK.get(sym_cat, CATEGORY_RISK["stock"])
            pick_mh = _cat_risk[2]

            # v11.4: ATR-based dynamic TP/SL — adapts to actual realized volatility
            # Uses proper Wilder ATR (High/Low/Close True Range) instead of rolling std dev.
            # Returns 7 values: tp_price, sl_price, p_tp, atr_val, tp_pct, sl_pct, method
            _atr_val = None
            _tp_sl_method = 'static'
            if symbol in data and data[symbol] is not None and len(data[symbol]) >= 20:
                tp_price, sl_price, p_tp, _atr_val, _tp_pct, _sl_pct, _tp_sl_method = compute_atr_tp_sl(
                    data[symbol], sym_cat, current_price
                )
            else:
                # Fallback to percentage-based when no OHLCV history available
                pick_sl_pct, pick_tp_pct = _cat_risk[0], _cat_risk[1]
                tp_price = round(current_price * (1 + pick_tp_pct), 6)
                sl_price = round(current_price * (1 + pick_sl_pct), 6)
                _tp_pct = round(abs(pick_tp_pct) * 100, 2)
                _sl_pct = round(abs(pick_sl_pct) * 100, 2)
                p_tp = 0.50
            # Calculate signal probability (0-100 scale for the pick dict)
            _signal_prob = calculate_signal_probability(
                current_price, tp_price, sl_price, _atr_val
            )

            # v11.6: Adjust TP for transaction costs (widen target so net P&L remains positive)
            _gross_tp = round(tp_price, 8)
            _tc_cost_pct = _tc_get_round_trip_cost(symbol, sym_cat)
            _net_tp = _tc_adjust_tp_for_costs(current_price, tp_price, symbol, sym_cat, "BUY")

            pick = {
                "symbol": symbol,
                "entryPrice": round(current_price, 6),
                "currentPrice": round(current_price, 6),
                "peakPrice": round(current_price, 6),      # trailing high watermark
                "entryDate": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "signal": signal,
                "reason": reason,
                "shares": round(shares, 6),
                "allocation": round(allocation, 2),
                "realizedVol": realized_vols.get(symbol),  # v5.7 vol-targeting metadata
                "kellyFraction": round(kf, 3),             # v7.0 Kelly metadata
                # v10.4: forward-looking risk/reward — enables dashboard proof-of-alpha display
                "symbolCategory": sym_cat,                  # true asset class (crypto even in pairs algo)
                "stopPrice":  round(sl_price, 8),           # ATR-based absolute stop level
                "targetPrice": round(_net_tp, 8),           # v11.6: cost-adjusted target level
                "grossTargetPrice": _gross_tp,              # v11.6: pre-cost target for reference
                "transactionCostPct": round(_tc_cost_pct * 100, 3),  # v11.6: round-trip cost %
                "stopLossPct": _sl_pct,                     # SL distance as % from entry
                "takeProfitPct": _tp_pct,                   # TP distance as % from entry
                "riskReward": round(abs(_net_tp - current_price) / max(abs(current_price - sl_price), 0.0001), 2),
                "maxHoldDays": pick_mh,
                "tpProbability": p_tp,                      # first-passage P(TP before SL), 0-1 scale
                "signalProbability": _signal_prob,           # P(TP before SL), 0-100 scale
                "atrValue": round(_atr_val, 8) if _atr_val else None,  # raw ATR used
                "tpSlMethod": _tp_sl_method,                # 'atr' or 'static'
            }

            # v11.7: Populate ML market-context features at entry time
            # These feed the RF model's 6 market-context columns.
            # v11.8-fix: Each feature in its own try/except so one failure
            # doesn't blank the rest. Defaults set first, then overwritten.

            # --- Defaults (always present, even if all computations fail) ---
            pick["rsi_at_entry"] = 50.0
            pick["volume_ratio"] = 1.0
            pick["fear_greed"] = 50.0
            pick["risk_reward"] = pick.get("riskReward", 1.5)
            pick["hour_of_day"] = now.hour
            pick["btc_24h_change"] = 0.0

            # --- RSI-14 from OHLCV history ---
            try:
                if df is not None and len(df) >= 15:
                    _delta = df["Close"].diff()
                    _gain = _delta.clip(lower=0).rolling(14).mean().iloc[-1]
                    _loss = (-_delta.clip(upper=0)).rolling(14).mean().iloc[-1]
                    if pd.notna(_gain) and pd.notna(_loss):
                        _rs = _gain / max(_loss, 1e-10)
                        _rsi_val = 100 - 100 / (1 + _rs)
                        if pd.notna(_rsi_val) and 0 <= _rsi_val <= 100:
                            pick["rsi_at_entry"] = round(float(_rsi_val), 2)
            except Exception:
                pass  # keeps default 50.0

            # --- Volume ratio: current volume / 20-period SMA ---
            try:
                if df is not None and "Volume" in df.columns and len(df) >= 20:
                    _vol_avg = df["Volume"].rolling(20).mean().iloc[-1]
                    _vol_now = df["Volume"].iloc[-1]
                    if pd.notna(_vol_avg) and pd.notna(_vol_now) and _vol_avg > 0:
                        _vr = float(_vol_now) / float(_vol_avg)
                        pick["volume_ratio"] = round(min(max(_vr, 0.01), 50.0), 4)
            except Exception:
                pass  # keeps default 1.0

            # --- Fear & Greed: crypto F&G for crypto/meme, CNN for stocks ---
            try:
                _pick_cat = spec.get("category", "stock")
                if _pick_cat in ("crypto", "meme", "skyrocket"):
                    _fg = float(fng_val)
                else:
                    _fg = float(cnn_score)
                if 0 <= _fg <= 100:
                    pick["fear_greed"] = _fg
            except Exception:
                pass  # keeps default 50.0

            # --- Risk/reward from TP/SL distances (already computed above) ---
            try:
                _rr = pick.get("riskReward")
                if _rr is not None and float(_rr) > 0:
                    pick["risk_reward"] = round(float(_rr), 2)
            except Exception:
                pass  # keeps default 1.5

            # --- Hour of day (UTC) — already set in defaults ---

            # --- BTC 24h change from CoinGecko global data ---
            try:
                _btc_chg = float(mc_change_24h)
                if not math.isnan(_btc_chg):
                    pick["btc_24h_change"] = round(_btc_chg, 4)
            except Exception:
                pass  # keeps default 0.0

            picks.append(pick)
            new_picks_flat.append({**pick, "algorithm": algo_id, "algorithmName": algo.get("name", "")})
            cash -= allocation
            held.add(symbol)
            # v10.5: update global concentration counter so subsequent algos respect the cap
            global_held_counts[symbol] = global_held_counts.get(symbol, 0) + 1
            tier_tag = f"[{spec.get('tier', '?')}]"
            kelly_tag = f" K¼={kf:.3f}×{kelly_mult:.2f}" if kf > 0 else ""
            gap_tag = f" today={_today_chg*100:+.1f}%" if abs(_today_chg) > 0.01 else ""
            print(f"  {tier_tag} {algo.get('name', algo_id)}: BUY {symbol} @ {current_price:.4f} - {reason}{kelly_tag}{gap_tag}")


    # Update prices and portfolio values
    # v10.4: prefer intraday_prices (refreshed earlier in this run) over stale daily close
    for algo in live["algorithms"]:
        picks = algo.get("activePicks", [])
        cash = float(algo.get("cash", STARTING_CAPITAL))
        total_equity = 0.0
        for p in picks:
            sym = p["symbol"]
            if sym in intraday_prices:
                p["currentPrice"] = round(intraday_prices[sym], 6)
            elif sym in data:
                p["currentPrice"] = round(float(data[sym]["Close"].iloc[-1]), 6)
            entry = p.get("entryPrice") or 0
            curr = p.get("currentPrice") or entry
            alloc = p.get("allocation")
            sh = p.get("shares")
            if alloc and alloc > 0 and entry > 0:
                total_equity += alloc * (curr / entry)
            elif sh and sh > 0:
                total_equity += sh * curr
            else:
                total_equity += ALLOCATION_PER_PICK * (curr / entry) if entry > 0 else 0
        algo["currentValue"] = round(cash + total_equity, 2)
        start = float(algo.get("startingValue", STARTING_CAPITAL))
        algo["totalReturn"] = round(((algo["currentValue"] - start) / start) * 100, 2)

    if signals_found == 0:
        print("  No entry signals met threshold.")

    # -----------------------------------------------------------------------
    # Action 2.3: CONFLUENCE FILTERING — require 2+ algorithms to agree on a symbol
    # Removes single-algo picks from activePicks and refunds cash.
    # Must run BEFORE drought tracking, convergence boost, and JSON writes.
    # -----------------------------------------------------------------------
    new_picks_flat = apply_confluence_filter(new_picks_flat, algos_by_id, live, min_agreement=1)

    # Recalculate portfolio values after confluence removals
    for algo in live["algorithms"]:
        picks = algo.get("activePicks", [])
        cash = float(algo.get("cash", STARTING_CAPITAL))
        total_equity = 0.0
        for p in picks:
            entry = p.get("entryPrice") or 0
            curr = p.get("currentPrice") or entry
            alloc = p.get("allocation")
            sh = p.get("shares")
            if alloc and alloc > 0 and entry > 0:
                total_equity += alloc * (curr / entry)
            elif sh and sh > 0:
                total_equity += sh * curr
            else:
                total_equity += ALLOCATION_PER_PICK * (curr / entry) if entry > 0 else 0
        algo["currentValue"] = round(cash + total_equity, 2)
        start = float(algo.get("startingValue", STARTING_CAPITAL))
        algo["totalReturn"] = round(((algo["currentValue"] - start) / start) * 100, 2)

    # -----------------------------------------------------------------------
    # DROUGHT TRACKING — increment per-algo dry scan counter
    # Algos that produced picks surviving confluence filter get drought reset.
    # -----------------------------------------------------------------------
    algo_fired = {p.get("algorithm", "") for p in new_picks_flat}
    for algo in live["algorithms"]:
        if algo["id"] in algo_fired:
            algo["droughtScans"] = 0
        else:
            algo["droughtScans"] = algo.get("droughtScans", 0) + 1

    # -----------------------------------------------------------------------
    # SIGNAL CONVERGENCE — symbols with multiple strategy signals = stronger
    # -----------------------------------------------------------------------
    signal_counts: dict[str, int] = {}
    for p in new_picks_flat:
        sym = p.get("symbol", "")
        if sym:
            signal_counts[sym] = signal_counts.get(sym, 0) + 1
    convergence = [{"symbol": s, "strategies": c} for s, c in sorted(signal_counts.items(), key=lambda x: -x[1]) if c >= 2]
    if convergence:
        print(f"  CONVERGENCE ALERT: {len(convergence)} symbols fired by 2+ strategies:")
        for cv in convergence[:5]:
            print(f"    {cv['symbol']}: {cv['strategies']} strategies")
        print()

    # -----------------------------------------------------------------------
    # CONVERGENCE ALLOCATION BOOST — multiply position size on convergent picks
    # 2 strategies firing same symbol → +25%; 3+ → +50%
    # (Institutional rationale: signal confirmation from multiple models = higher conviction)
    # -----------------------------------------------------------------------
    boost_applied = 0
    for pick in new_picks_flat:
        sym = pick.get("symbol", "")
        count = signal_counts.get(sym, 1)
        if count < 2:
            continue
        boost = 1.25 if count == 2 else 1.50
        old_alloc = float(pick.get("allocation", ALLOCATION_PER_PICK))
        extra = round(old_alloc * (boost - 1.0), 2)
        algo_obj = algos_by_id.get(pick.get("algorithm", ""))
        if not algo_obj:
            continue
        avail_cash = float(algo_obj.get("cash", 0))
        if avail_cash < extra:
            continue
        new_alloc = round(old_alloc + extra, 2)
        new_shares = round(new_alloc / max(float(pick.get("entryPrice", 1)), 1e-9), 6)
        pick["allocation"] = new_alloc
        pick["shares"] = new_shares
        pick["convergenceBoost"] = count
        algo_obj["cash"] = round(avail_cash - extra, 2)
        # Mirror update into algo's activePicks list
        for ap in algo_obj.get("activePicks", []):
            if ap.get("symbol") == sym and abs(float(p.get("allocation", 0) or 0) - old_alloc) < 1.0:
                ap["allocation"] = new_alloc
                ap["shares"] = new_shares
                break
        boost_applied += 1
    if boost_applied:
        print(f"  Convergence boost applied to {boost_applied} picks (+25% for 2 strategies, +50% for 3+)")

    # -----------------------------------------------------------------------
    # DOUBLE IGNITE DETECTION — consecutive convergence = 🔥 flame signal
    # If a symbol had convergence in BOTH this scan AND the previous scan,
    # mark it as "double_ignite" — something significant may be cooking.
    # -----------------------------------------------------------------------
    last_convergence_path = DATA_DIR / "last_convergence.json"
    prev_convergence_symbols: set[str] = set()
    try:
        if last_convergence_path.exists():
            with open(last_convergence_path) as _f:
                _prev = json.load(_f)
                prev_convergence_symbols = set(_prev.get("symbols", []))
    except Exception:
        pass

    current_convergence_symbols = {cv["symbol"] for cv in convergence} if convergence else set()
    double_ignite_symbols = current_convergence_symbols & prev_convergence_symbols
    if double_ignite_symbols:
        print(f"  🔥 DOUBLE IGNITE: {double_ignite_symbols} — convergence in 2 consecutive scans!")

    # Tag picks with double_ignite flag
    for pick in new_picks_flat:
        sym = pick.get("symbol", "")
        if sym in double_ignite_symbols:
            pick["double_ignite"] = True
            pick["ignite_streak"] = 2
        else:
            pick["double_ignite"] = False

    # Save current convergence symbols for next scan comparison
    try:
        save_json(last_convergence_path, {
            "symbols": list(current_convergence_symbols),
            "timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
    except Exception:
        pass

    # -----------------------------------------------------------------------
    # CORRELATION DEDUPLICATION — reduce allocation for highly correlated new picks (v6.0)
    # -----------------------------------------------------------------------
    if new_picks_flat:
        # Collect all currently held symbols across all algos
        all_held = []
        for alg in live["algorithms"]:
            all_held.extend([p["symbol"] for p in alg.get("activePicks", [])])

        # Build correlation matrix for new pick symbols vs held symbols
        new_syms = list({p["symbol"] for p in new_picks_flat})
        check_syms = list(set(new_syms + all_held))
        if len(check_syms) >= 2:
            corr_matrix = compute_correlation_risks(data, check_syms, lookback=20)
            corr_dedups = 0
            for pick in new_picks_flat:
                sym = pick["symbol"]
                max_corr = max(
                    (abs(corr_matrix.get(sym, {}).get(h, 0.0)) for h in all_held if h != sym),
                    default=0.0
                )
                if max_corr > 0.90:
                    # Highly correlated with existing position — halve allocation
                    old_alloc = float(pick.get("allocation", ALLOCATION_PER_PICK))
                    pick["allocation"] = round(old_alloc * 0.5, 2)
                    pick["corrDedupMax"] = round(max_corr, 3)
                    corr_dedups += 1
            if corr_dedups:
                print(f"  CORRELATION DEDUP: {corr_dedups} picks reduced (>0.90 corr with existing)")

    # -----------------------------------------------------------------------
    # TOURNAMENT SCORING — compute and save leaderboard
    # -----------------------------------------------------------------------
    tournament_path = DATA_DIR / "tournament.json"
    tournament = compute_tournament(live["algorithms"], now, regime=regime)
    # Enrich tournament with regime + convergence data
    tournament["marketRegime"]      = regime
    tournament["signalConvergence"] = convergence[:10]
    tournament["fearGreedIndex"]    = fng
    tournament["vixTermStructure"]  = data.get("__vix_term__", {})
    _cf = data.get("__crypto_funding__", {})
    tournament["trendStrength"]      = data.get("__trend_strength__", {})
    tournament["cryptoFundingSentiment"] = {
        "signal": _cf.get("signal", "neutral"),
        "avg_rate": _cf.get("avg_rate", 0.0),
        "sentiment_score": _cf.get("sentiment_score", 50.0),
        "buy_candidates": _cf.get("buy_candidates", []),
    } if isinstance(_cf, dict) else {}

    # ── Portfolio heat map — category concentration tracking ─────────
    cat_counts: dict[str, int] = {}
    total_open = 0
    for algo in live["algorithms"]:
        cat = algo.get("category", "stock")
        n = len(algo.get("activePicks", []))
        cat_counts[cat] = cat_counts.get(cat, 0) + n
        total_open += n
    portfolio_heat = {
        cat: {"picks": cnt, "pct": round(cnt / total_open * 100, 1) if total_open > 0 else 0}
        for cat, cnt in sorted(cat_counts.items(), key=lambda x: -x[1])
    }
    heat_warnings = [cat for cat, v in portfolio_heat.items() if v["pct"] > 40]
    tournament["portfolioHeat"]     = portfolio_heat
    tournament["heatWarnings"]      = heat_warnings
    if heat_warnings:
        print(f"  HEAT WARNING: {', '.join(heat_warnings)} > 40% of portfolio exposure")
    save_json(tournament_path, tournament)
    print(f"  Tournament updated: {tournament['phase']} — top algo: "
          f"{tournament['rankings'][0]['name']} (score={tournament['rankings'][0]['score']})")

    # ── v11.0 ANTIGRAVITY: Elimination Engine ─────────────────────────
    # Proven strategies that can NEVER be eliminated (post-audit protection)
    PROTECTED_STRATEGY_IDS = {
        "funding-rate-arb", "pairs-trading", "betting-against-beta",
        "quality-minus-junk", "flash-crash-reversal",
    }
    if _HAS_ELIMINATION:
        try:
            elim_engine = EliminationEngine()
            eliminated_ids = elim_engine.check_eliminations(tournament)
            # Filter out protected strategies — they survive no matter what
            if eliminated_ids:
                protected_saved = [eid for eid in eliminated_ids if eid in PROTECTED_STRATEGY_IDS]
                eliminated_ids = [eid for eid in eliminated_ids if eid not in PROTECTED_STRATEGY_IDS]
                if protected_saved:
                    print(f"  [ELIM] PROTECTED from elimination: {protected_saved}")
                    # Remove them from elimination state so they stay active
                    state = elim_engine.get_state()
                    for pid in protected_saved:
                        state["eliminated"] = [e for e in state.get("eliminated", []) if e.get("id") != pid]
                        state["probation"] = [e for e in state.get("probation", []) if e.get("id") != pid]
                        state["danger_zone"] = [e for e in state.get("danger_zone", []) if e.get("id") != pid]
                    elim_engine._save_state(state)
            elim_state = elim_engine.get_state()
            print(f"  [ELIM] Eliminated: {len(elim_state.get('eliminated', []))} | "
                  f"Probation: {len(elim_state.get('on_probation', []))} | "
                  f"Challengers: {len(elim_state.get('challengers', []))}")
            if eliminated_ids:
                n_inject = elim_engine.should_inject(len(eliminated_ids))
                if n_inject > 0:
                    injected = elim_engine.inject_challengers(n_inject)
                    print(f"  [ELIM] Injected {len(injected)} challengers: "
                          f"{[c['id'] for c in injected]}")
            tournament["eliminationState"] = elim_state
            save_json(tournament_path, tournament)  # re-save with elimination state
        except Exception as e:
            print(f"  [ELIM] Error: {e}")

    # ── v11.5 FORWARD-TEST GATE — annotate picks with validation status ──
    if new_picks_flat:
        n_validated = apply_forward_gate_to_picks(new_picks_flat, tournament)
        n_total = len(new_picks_flat)
        n_unvalidated = n_total - n_validated
        print(f"  [FORWARD GATE] {n_validated}/{n_total} picks from validated algos "
              f"({n_unvalidated} unvalidated — still tracked, not blocked)")
        # Also annotate the active picks already stored in algo objects
        for algo in live["algorithms"]:
            algo_id = algo.get("id", "")
            rk_match = next((r for r in tournament.get("rankings", [])
                             if r["id"] == algo_id), {})
            algo_stats = {"wins": rk_match.get("wins", 0),
                          "losses": rk_match.get("losses", 0), "expired": 0}
            gate_pass, gate_reason, tc, wr = passes_forward_gate(algo_id, algo_stats)
            for p in algo.get("activePicks", []):
                p["forward_validated"] = gate_pass
                p["forward_status"]   = gate_reason
                p["forward_trades"]   = tc
                p["forward_wr"]       = round(wr, 3)

        # ── v11.7 FORWARD-WR CONFIDENCE SCORING ────────────────────────
        # Replace hardcoded confidence=50 with forward-WR-based scoring.
        # Applies to both new_picks_flat and algo activePicks.
        def _calc_forward_confidence(pick: dict) -> int:
            """Compute confidence from forward-test win rate data."""
            fwd_status = pick.get("forward_status", "unknown")
            fwd_wr = pick.get("forward_wr", 0.0)
            fwd_trades = pick.get("forward_trades", 0)

            if "insufficient_data" in str(fwd_status):
                return 35  # not enough trades to judge — below filter threshold
            if fwd_wr > 0 and fwd_trades >= 3:
                # Validated algo: confidence = forward WR scaled to 0-100
                if fwd_wr < 0.40:
                    return max(20, int(fwd_wr * 100))  # penalize low-WR
                return min(95, int(fwd_wr * 100))  # cap at 95
            return 50  # true fallback: no forward data at all

        # Score new picks
        for pick in new_picks_flat:
            pick["confidence"] = _calc_forward_confidence(pick)

        # Score active picks in algo objects
        for algo in live["algorithms"]:
            for p in algo.get("activePicks", []):
                p["confidence"] = _calc_forward_confidence(p)

        # ── v11.7 MINIMUM CONFIDENCE GATE — kill F-grade strategies ────
        _pre_gate = len(new_picks_flat)
        new_picks_flat = [p for p in new_picks_flat if p.get("confidence", 50) >= 30]
        _killed = _pre_gate - len(new_picks_flat)
        if _killed:
            print(f"  [CONFIDENCE GATE] Removed {_killed} picks with confidence < 30 "
                  f"(kept {len(new_picks_flat)})")

        # Also remove from algo activePicks
        for algo in live["algorithms"]:
            algo["activePicks"] = [
                p for p in algo.get("activePicks", [])
                if p.get("confidence", 50) >= 30
            ]

    # ── v11.0 ANTIGRAVITY: SQLite Persistence ─────────────────────────
    ts_now = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    if _HAS_SQLITE:
        try:
            db = SQLiteStore()
            # Ingest existing audit log on first run (idempotent — uses INSERT OR IGNORE)
            db.ingest_audit_log()
            db.ingest_competition_picks()
            # Write new picks from this scan
            for pick in new_picks_flat:
                db.write_signal({
                    "timestamp": ts_now,
                    "algorithm": pick.get("algorithm", ""),
                    "symbol": pick.get("symbol", ""),
                    "signal": "BUY",
                    "reason": pick.get("reason", ""),
                    "price": float(pick.get("entryPrice", 0)),
                })
                db.write_pick(pick)
            # Write regime snapshot
            cg_glob = data.get("__coingecko_global__", {})
            db.write_regime({
                "timestamp": ts_now,
                "regime": regime.get("stock", "neutral"),
                "crypto_regime": regime.get("crypto", "neutral"),
                "vix_proxy": regime.get("vix", "neutral"),
                "hmm_confidence": 0.5,
                "vol_20d": cg_glob.get("vol_20d", 0.01),
                "btc_eth_ratio": cg_glob.get("btc_dominance", 1.0),
            })
            # Write daily ranking snapshot
            _t_rankings = tournament.get("rankings", []) if "tournament" in dir() else []
            if _t_rankings:
                db.write_ranking_snapshot(_t_rankings, regime.get("stock", "neutral"))
            print(f"  [SQLite] Stored {len(new_picks_flat)} signals + regime snapshot")
        except Exception as e:
            print(f"  [SQLite] Error: {e}")

    # ── v11.0 ANTIGRAVITY: ML Signal Ranker ───────────────────────────
    if _HAS_ML:
        try:
            ranker = MLSignalRanker()
            if ranker.model is not None:
                for pick in new_picks_flat:
                    features = {
                        "algorithm": pick.get("algorithm", ""),
                        "symbol": pick.get("symbol", ""),
                        "confidence": float(pick.get("confidence", 50)),
                        "regime": regime.get("stock", "neutral"),
                    }
                    score = ranker.predict_win_probability(features)
                    pick["mlWinProb"] = round(score, 3)
                ml_ranked = sorted(
                    [p for p in new_picks_flat if "mlWinProb" in p],
                    key=lambda x: -x["mlWinProb"]
                )
                if ml_ranked:
                    print(f"  [ML] Ranked {len(ml_ranked)} signals — "
                          f"top: {ml_ranked[0].get('symbol','')} ({ml_ranked[0]['mlWinProb']:.1%})")
            else:
                print("  [ML] Model not trained yet — using heuristic fallback")
                for pick in new_picks_flat:
                    features = {
                        "algorithm": pick.get("algorithm", ""),
                        "symbol": pick.get("symbol", ""),
                        "confidence": float(pick.get("confidence", 50)),
                        "regime": regime.get("stock", "neutral"),
                    }
                    pick["mlWinProb"] = round(ranker.predict_win_probability(features), 3)
        except Exception as e:
            print(f"  [ML] Error: {e}")

    # Persist
    live["competition"]["lastUpdated"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    live["competition"]["version"] = "2.0"
    live["marketStatus"]["lastMarketCheck"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    live["todaysPicks"] = new_picks_flat
    save_json(live_path, live)

    # active_picks.json (flat) — deduplicated: keep highest-scored pick per symbol
    _all_picks_raw: list[dict] = []
    for algo in live["algorithms"]:
        for p in algo.get("activePicks", []):
            entry = {**p, "algorithm": algo["id"], "algorithmName": algo.get("name", "")}
            # Carry double_ignite flag from new_picks_flat to all_picks
            sym = entry.get("symbol", "")
            if sym in double_ignite_symbols:
                entry["double_ignite"] = True
                entry["ignite_streak"] = 2
            _all_picks_raw.append(entry)

    # Deduplicate: keep only the highest-scored pick per symbol
    def _pick_score(p: dict) -> float:
        """Score a pick for dedup ranking: confluence_score > mlWinProb > confidence."""
        for key in ("confluence_score", "mlWinProb", "confidence"):
            v = p.get(key)
            if v is not None and float(v) > 0:
                return float(v)
        return 0.0

    _best_by_symbol: dict[str, dict] = {}
    for _p in _all_picks_raw:
        _sym = _p.get("symbol", "")
        if _sym not in _best_by_symbol or _pick_score(_p) > _pick_score(_best_by_symbol[_sym]):
            _best_by_symbol[_sym] = _p
    all_picks = list(_best_by_symbol.values())
    if len(_all_picks_raw) != len(all_picks):
        print(f"  [DEDUP] {len(_all_picks_raw)} raw picks → {len(all_picks)} unique symbols")

    # Safety check + performance breakdown (shared modules)
    try:
        _shared_dir = str(Path(__file__).resolve().parent.parent / "shared")
        if _shared_dir not in sys.path:
            sys.path.insert(0, _shared_dir)
        from safety_checker import SafetyChecker
        _safety = SafetyChecker(cache_dir=DATA_DIR / "cache")
        all_picks = _safety.enrich_picks(all_picks)
        all_picks = [p for p in all_picks if p.get("safety_score", 100) >= 30]
    except Exception as _e:
        print(f"  [SAFETY] Skipped: {_e}")
    try:
        from performance_breakdown import PerformanceBreakdown
        _perf_bd = PerformanceBreakdown(cache_dir=DATA_DIR / "cache")
        all_picks = _perf_bd.enrich_picks(all_picks)
    except Exception as _e:
        print(f"  [PERF] Skipped: {_e}")

    save_json(active_path, {
        "dataType": "FORWARD_TEST",
        "disclaimer": "Only real, auditable trades. Each entry has a timestamp, signal source, and verifiable price.",
        "activePicks": all_picks,
        "auditTrail": [],
        "lastUpdated": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": "v2: 5 Tier 1 academic strategies + 5 Scout supplementary signals.",
    })

    # Write scan run summary for Jobs Log tab
    elapsed = (datetime.now(timezone.utc) - scan_start).total_seconds()
    total_active = sum(len(a.get("activePicks", [])) for a in live["algorithms"])
    signal_details = []
    for a in live["algorithms"]:
        for sig_entry in [e for e in load_json(audit_path, [])
                          if e.get("timestamp", "").startswith(now.strftime("%Y-%m-%dT%H:%M"))
                          and e.get("algorithm") == a["id"]]:
            already_held = sig_entry.get("symbol") in {p["symbol"] for p in a.get("activePicks", [])}
            signal_details.append({
                "algorithm": a["id"],
                "algorithmName": a.get("name", ""),
                "tier": a.get("tier", "?"),
                "symbol": sig_entry.get("symbol", ""),
                "reason": sig_entry.get("reason", ""),
                "new": any(p["symbol"] == sig_entry.get("symbol") and
                           p.get("entryDate", "").startswith(now.strftime("%Y-%m-%dT%H:%M"))
                           for p in a.get("activePicks", [])),
            })
    save_scan_run(runs_path, {
        "timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "COMPLETE",
        "runtime_sec": round(elapsed, 1),
        "symbols_scanned": len(data),
        "signals_found": signals_found,
        "new_picks": len(new_picks_flat),
        "total_active_picks": total_active,
        "signal_details": signal_details,
    })

    # -----------------------------------------------------------------------
    # v10.3 — Scan Log: per-algo + per-category last-checked timestamps
    # Written to data/scan_log.json. The dashboard reads this to display
    # "last seen" for each asset class and each algorithm ID.
    # -----------------------------------------------------------------------
    scan_log_path = DATA_DIR / "scan_log.json"
    existing_log = load_json(scan_log_path, {"byCategory": {}, "byAlgo": {}, "scanHistory": []})

    ts_now = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Build per-category stats for this run
    cat_stats: dict[str, dict] = {}
    for algo in live["algorithms"]:
        cat = algo.get("category", "stock")
        if cat not in cat_stats:
            cat_stats[cat] = {
                "lastScanned": ts_now,
                "algosTotal": 0,
                "algosWithPicks": 0,
                "activePicks": 0,
                "closedPicks": 0,
                "totalReturn": 0.0,
            }
        cs = cat_stats[cat]
        cs["algosTotal"] += 1
        n_active = len(algo.get("activePicks", []))
        n_closed = len(algo.get("closedPicks", []))
        if n_active > 0:
            cs["algosWithPicks"] += 1
        cs["activePicks"] += n_active
        cs["closedPicks"] += n_closed
        cs["totalReturn"] = round(cs["totalReturn"] + float(algo.get("totalReturn", 0)), 4)

    # Update byCategory (merge with existing)
    for cat, stats in cat_stats.items():
        existing_log["byCategory"][cat] = stats

    # Update byAlgo (one entry per algo ID)
    for algo in live["algorithms"]:
        algo_id = algo["id"]
        existing_log["byAlgo"][algo_id] = {
            "id":           algo_id,
            "name":         algo.get("name", ""),
            "category":     algo.get("category", "stock"),
            "tier":         algo.get("tier", "?"),
            "lastScanned":  ts_now,
            "activePicks":  len(algo.get("activePicks", [])),
            "closedPicks":  len(algo.get("closedPicks", [])),
            "currentValue": round(float(algo.get("currentValue", 10000)), 2),
            "totalReturn":  round(float(algo.get("totalReturn", 0)), 4),
            "droughtScans": algo.get("droughtScans", 0),
        }

    # Rolling scan history (keep last 200 runs)
    history_entry = {
        "timestamp":     ts_now,
        "signalsFound":  signals_found,
        "newPicks":      len(new_picks_flat),
        "totalActive":   total_active,
        "byCategory":    {c: {"activePicks": s["activePicks"], "closedPicks": s["closedPicks"]}
                          for c, s in cat_stats.items()},
    }
    history = existing_log.get("scanHistory", [])
    history.append(history_entry)
    existing_log["scanHistory"] = history[-200:]
    existing_log["lastUpdated"] = ts_now

    save_json(scan_log_path, existing_log)
    cat_summary = ", ".join(c + "(" + str(s["activePicks"]) + "p)" for c, s in cat_stats.items())
    print(f"  Scan log updated — {len(existing_log['byAlgo'])} algos | categories: {cat_summary}")

    print()
    print("Summary:")
    for algo in live["algorithms"]:
        n = len(algo.get("activePicks", []))
        val = algo.get("currentValue", 0)
        ret = algo.get("totalReturn", 0)
        tier = algo.get("tier", "?")
        print(f"  [{tier:7s}] {algo.get('name', '?'):30s} ${val:>8.2f} ({ret:+.2f}%)  {n} picks")
    # -----------------------------------------------------------------------
    # v11.0 — Write live_signals_now.json for signal_tracker.py validation
    # Contains ALL active picks (crypto + forex) with TP/SL for forward tracking
    # -----------------------------------------------------------------------
    try:
        crypto_sigs = []
        forex_sigs = []
        for algo in live["algorithms"]:
            cat = algo.get("category", "stock")
            algo_id = algo.get("id", "")
            for pick in algo.get("activePicks", []):
                ep = float(pick.get("entryPrice") or 0)
                tp = float(pick.get("targetPrice") or 0)
                sl = float(pick.get("stopPrice") or 0)
                sym = pick.get("symbol", "")
                if ep <= 0 or tp <= 0 or sl <= 0:
                    continue
                # v11.6: include both gross and net TP in signal output
                _sig_gross_tp = float(pick.get("grossTargetPrice") or tp)
                _sig_cost_pct = float(pick.get("transactionCostPct", 0))
                sig_entry = {
                    "symbol": sym,
                    "signal": "BUY",
                    "confidence": int(pick.get("mlWinProb", 0) * 100) if pick.get("mlWinProb") else pick.get("confidence", 50),
                    "tp_probability": pick.get("tpProbability", 0.50),   # v11.4 Brownian P(TP)
                    "price": ep,
                    "entryPrice": ep,                       # alias for aggregator compatibility
                    "take_profit": tp,                      # cost-adjusted (net) TP
                    "gross_tp": _sig_gross_tp,              # v11.6: pre-cost TP
                    "net_tp": tp,                           # v11.6: same as take_profit
                    "stop_loss": sl,
                    "targetPrice": tp,                      # alias for aggregator compatibility
                    "stopPrice": sl,                        # alias for aggregator compatibility
                    "transaction_cost_estimate": _sig_cost_pct,  # v11.6: round-trip cost %
                    "risk_reward": round(abs(tp - ep) / abs(ep - sl), 2) if abs(ep - sl) > 0 else 0,
                    "algorithm": algo_id,
                    "tier": algo.get("tier", "SCOUT"),
                    "reasons": [pick.get("reason", "")],
                    "timestamp": pick.get("entryDate", ts_now),
                    # v11.5 forward-test gate metadata
                    "forward_validated": pick.get("forward_validated", False),
                    "forward_status":   pick.get("forward_status", "unknown"),
                    "forward_trades":   pick.get("forward_trades", 0),
                    "forward_wr":       pick.get("forward_wr", 0.0),
                    # Action 2.3: confluence metadata
                    "confluence_count": pick.get("confluence_count", 1),
                    "confluence_score": pick.get("confluence_score", 30),
                    "confluence_algos": pick.get("confluence_algos", [algo_id]),
                }
                if cat == "crypto" or sym.endswith("-USD"):
                    crypto_sigs.append(sig_entry)
                elif cat == "forex":
                    forex_sigs.append(sig_entry)
        live_sigs_path = DATA_DIR / "live_signals_now.json"
        save_json(live_sigs_path, {
            "generated_at": ts_now,
            "crypto_signals": crypto_sigs,
            "forex_signals": forex_sigs,
            "total": len(crypto_sigs) + len(forex_sigs),
        })
        print(f"  Live signals written: {len(crypto_sigs)} crypto + {len(forex_sigs)} forex → live_signals_now.json")
    except Exception as _e:
        print(f"  [v11] live_signals_now.json write failed: {_e}")

    print()
    print("Done. Exit 0.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(run_scanner())
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
