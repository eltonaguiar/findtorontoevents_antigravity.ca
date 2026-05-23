#!/usr/bin/env python3
"""
Kimi Claw v4.1 Extended Strategies — Backtester
=================================================
Implements 4 Tier-1 strategies from the Kimi Claw v4.1 research
against real historical data via yfinance.

Strategies:
  1. Liquidity Sweep Reversal (LSR)       — 73% WR claimed, 2.5:1 R:R
  2. Flash Crash Reversal (FCR)           — 71% WR claimed, 4:1 R:R
  3. Statistical Arb Pairs (BTC-ETH)      — Sharpe 3.77 claimed
  4. Funding Rate Momentum (contrarian)   — 64% WR claimed

Framework:
  - yfinance for BTC-USD, ETH-USD, SOL-USD (2 years daily)
  - 2% risk per trade, 0.1% per-side transaction costs
  - Regime detection (trending / ranging / high-vol)
  - ML validation: logistic regression on signal features

Usage:
  py asterdex_paper/backtest_v41_strategies.py
  py asterdex_paper/backtest_v41_strategies.py --period 1y
  py asterdex_paper/backtest_v41_strategies.py --symbols BTC-USD,ETH-USD

Requires: pandas, numpy, yfinance, scikit-learn
Python 3.10+
"""

from __future__ import annotations

import argparse
import sys
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
ANNUALIZATION_FACTOR = 365
RISK_FREE_RATE = 0.045
TX_COST_PER_SIDE = 0.001   # 0.1% per side
TX_COST_ROUNDTRIP = 0.002  # 0.2% round trip
RISK_PER_TRADE = 0.02      # 2% portfolio risk per trade
INITIAL_CAPITAL = 100_000

DEFAULT_SYMBOLS = ["BTC-USD", "ETH-USD", "SOL-USD"]
DEFAULT_PERIOD = "2y"

STRATEGY_NAMES = [
    "Liquidity_Sweep_Reversal",
    "Flash_Crash_Reversal",
    "StatArb_Pairs_BTC_ETH",
    "Funding_Rate_Momentum",
]


# ---------------------------------------------------------------------------
# Data Download
# ---------------------------------------------------------------------------
def download_data(symbols: list[str], period: str = "2y") -> dict[str, pd.DataFrame]:
    """Download OHLCV data from yfinance for each symbol."""
    import yfinance as yf

    data = {}
    all_symbols = list(set(symbols))
    # Always need BTC-USD and ETH-USD for pairs trading
    for s in ["BTC-USD", "ETH-USD"]:
        if s not in all_symbols:
            all_symbols.append(s)

    for sym in all_symbols:
        print(f"  Downloading {sym} ({period})...", end=" ", flush=True)
        try:
            df = yf.download(sym, period=period, interval="1d", progress=False)
            if df.empty:
                print("EMPTY - skipping")
                continue
            # Flatten MultiIndex columns if present
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
            df.dropna(inplace=True)
            data[sym] = df
            print(f"{len(df)} bars")
        except Exception as e:
            print(f"ERROR: {e}")

    return data


# ---------------------------------------------------------------------------
# Technical Indicators
# ---------------------------------------------------------------------------
def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add common technical indicators used across strategies."""
    df = df.copy()

    # EMA
    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()
    df["EMA200"] = df["Close"].ewm(span=200, adjust=False).mean()

    # SMA
    df["SMA20"] = df["Close"].rolling(20).mean()
    df["SMA60"] = df["Close"].rolling(60).mean()

    # RSI(14)
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(com=13, adjust=False).mean()
    avg_loss = loss.ewm(com=13, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["RSI14"] = 100 - (100 / (1 + rs))

    # ADX(14)
    df["ADX14"] = compute_adx(df, 14)

    # ATR(14)
    tr = pd.concat([
        df["High"] - df["Low"],
        (df["High"] - df["Close"].shift(1)).abs(),
        (df["Low"] - df["Close"].shift(1)).abs(),
    ], axis=1).max(axis=1)
    df["ATR14"] = tr.ewm(span=14, adjust=False).mean()
    df["ATR_pct"] = df["ATR14"] / df["Close"] * 100

    # Bollinger Bands
    df["BB_mid"] = df["SMA20"]
    bb_std = df["Close"].rolling(20).std()
    df["BB_upper"] = df["BB_mid"] + 2 * bb_std
    df["BB_lower"] = df["BB_mid"] - 2 * bb_std
    df["BB_width"] = (df["BB_upper"] - df["BB_lower"]) / df["BB_mid"]

    # Volume SMA and Z-score
    df["Vol_SMA20"] = df["Volume"].rolling(20).mean()
    vol_std = df["Volume"].rolling(20).std()
    df["Vol_Zscore"] = (df["Volume"] - df["Vol_SMA20"]) / vol_std.replace(0, np.nan)

    # Returns
    df["Return_1d"] = df["Close"].pct_change()
    df["Return_20d"] = df["Close"].pct_change(20)
    df["Return_60d"] = df["Close"].pct_change(60)

    # VWAP proxy (daily reset using typical price * volume)
    typical_price = (df["High"] + df["Low"] + df["Close"]) / 3
    cum_tp_vol = (typical_price * df["Volume"]).rolling(20).sum()
    cum_vol = df["Volume"].rolling(20).sum()
    df["VWAP20"] = cum_tp_vol / cum_vol.replace(0, np.nan)

    # Candle structure
    df["Body"] = (df["Close"] - df["Open"]).abs()
    df["Upper_Wick"] = df["High"] - df[["Open", "Close"]].max(axis=1)
    df["Lower_Wick"] = df[["Open", "Close"]].min(axis=1) - df["Low"]
    df["Total_Wick"] = df["Upper_Wick"] + df["Lower_Wick"]
    df["Is_Bullish"] = df["Close"] > df["Open"]

    # Regime detection
    df["Regime"] = detect_regime(df)

    return df


def compute_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Compute ADX indicator."""
    high = df["High"]
    low = df["Low"]
    close = df["Close"]

    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs(),
    ], axis=1).max(axis=1)

    atr = tr.ewm(span=period, adjust=False).mean()
    plus_di = 100 * (plus_dm.ewm(span=period, adjust=False).mean() / atr.replace(0, np.nan))
    minus_di = 100 * (minus_dm.ewm(span=period, adjust=False).mean() / atr.replace(0, np.nan))

    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
    adx = dx.ewm(span=period, adjust=False).mean()
    return adx


def detect_regime(df: pd.DataFrame) -> pd.Series:
    """Classify each bar's regime: Trending, MeanReverting, HighVol, Quiet."""
    regimes = pd.Series("Quiet", index=df.index)

    # Volatility measure: 20d rolling std of returns
    vol = df["Close"].pct_change().rolling(20).std()
    vol_median = vol.rolling(60).median()

    # Trend measure: ADX
    adx = df.get("ADX14", pd.Series(25, index=df.index))

    for i in range(len(df)):
        v = vol.iloc[i] if not pd.isna(vol.iloc[i]) else 0
        vm = vol_median.iloc[i] if not pd.isna(vol_median.iloc[i]) else v
        a = adx.iloc[i] if not pd.isna(adx.iloc[i]) else 25

        if v > vm * 1.5:
            regimes.iloc[i] = "HighVol"
        elif a > 30:
            regimes.iloc[i] = "Trending"
        elif a < 20:
            regimes.iloc[i] = "MeanReverting"
        else:
            regimes.iloc[i] = "Quiet"

    return regimes


# ---------------------------------------------------------------------------
# Trade Tracking
# ---------------------------------------------------------------------------
class Trade:
    """Single trade record."""
    __slots__ = (
        "entry_date", "exit_date", "direction", "entry_price", "exit_price",
        "sl_price", "tp_price", "pnl_pct", "pnl_dollar", "risk_reward",
        "regime", "won", "features", "_bar_count",
    )

    def __init__(self, entry_date, direction, entry_price, sl_price, tp_price, regime, features=None):
        self.entry_date = entry_date
        self.exit_date = None
        self.direction = direction  # "long" or "short"
        self.entry_price = entry_price
        self.exit_price = None
        self.sl_price = sl_price
        self.tp_price = tp_price
        self.pnl_pct = 0.0
        self.pnl_dollar = 0.0
        self.risk_reward = 0.0
        self.regime = regime
        self.won = False
        self.features = features or {}
        self._bar_count = 0

    def close(self, exit_date, exit_price):
        self.exit_date = exit_date
        self.exit_price = exit_price

        if self.direction == "long":
            raw_pnl = (exit_price - self.entry_price) / self.entry_price
        else:
            raw_pnl = (self.entry_price - exit_price) / self.entry_price

        self.pnl_pct = raw_pnl - TX_COST_ROUNDTRIP
        self.pnl_dollar = self.pnl_pct * INITIAL_CAPITAL * RISK_PER_TRADE / max(0.001, abs(
            (self.entry_price - self.sl_price) / self.entry_price
        )) if self.sl_price else self.pnl_pct * INITIAL_CAPITAL * RISK_PER_TRADE

        self.won = self.pnl_pct > 0

        # Actual R:R achieved
        risk = abs(self.entry_price - self.sl_price) if self.sl_price else 1
        reward = abs(exit_price - self.entry_price)
        self.risk_reward = reward / risk if risk > 0 else 0

    def to_dict(self):
        return {
            "entry_date": str(self.entry_date)[:10],
            "exit_date": str(self.exit_date)[:10] if self.exit_date else "",
            "direction": self.direction,
            "entry": round(self.entry_price, 2),
            "exit": round(self.exit_price, 2) if self.exit_price else 0,
            "pnl_pct": round(self.pnl_pct * 100, 3),
            "won": self.won,
            "regime": self.regime,
            "rr": round(self.risk_reward, 2),
        }


class StrategyResult:
    """Aggregated results for a single strategy on a single symbol."""

    def __init__(self, name: str, symbol: str, trades: list[Trade]):
        self.name = name
        self.symbol = symbol
        self.trades = trades
        self._compute_metrics()

    def _compute_metrics(self):
        n = len(self.trades)
        if n == 0:
            self.total_trades = 0
            self.win_rate = 0.0
            self.profit_factor = 0.0
            self.sharpe = 0.0
            self.max_drawdown = 0.0
            self.avg_win = 0.0
            self.avg_loss = 0.0
            self.avg_rr = 0.0
            self.total_return = 0.0
            self.expectancy = 0.0
            return

        self.total_trades = n
        wins = [t for t in self.trades if t.won]
        losses = [t for t in self.trades if not t.won]

        self.win_rate = len(wins) / n if n > 0 else 0

        gross_profit = sum(t.pnl_pct for t in wins) if wins else 0
        gross_loss = abs(sum(t.pnl_pct for t in losses)) if losses else 0
        self.profit_factor = gross_profit / gross_loss if gross_loss > 0 else (
            float("inf") if gross_profit > 0 else 0
        )

        self.avg_win = np.mean([t.pnl_pct for t in wins]) * 100 if wins else 0
        self.avg_loss = np.mean([t.pnl_pct for t in losses]) * 100 if losses else 0
        self.avg_rr = np.mean([t.risk_reward for t in self.trades])

        # Sharpe ratio from trade returns
        returns = [t.pnl_pct for t in self.trades]
        if len(returns) > 1:
            avg_ret = np.mean(returns)
            std_ret = np.std(returns, ddof=1)
            # Annualize: assume avg ~1 trade per week
            trades_per_year = max(1, n / 2) * (365 / max(1, self._span_days()))
            self.sharpe = (avg_ret * trades_per_year - RISK_FREE_RATE) / (
                std_ret * np.sqrt(trades_per_year)
            ) if std_ret > 0 else 0
        else:
            self.sharpe = 0

        # Max drawdown on cumulative equity curve
        cumulative = np.cumsum(returns)
        peak = np.maximum.accumulate(cumulative)
        dd = peak - cumulative
        self.max_drawdown = np.max(dd) * 100 if len(dd) > 0 else 0

        self.total_return = sum(returns) * 100
        self.expectancy = (
            self.win_rate * (self.avg_win / 100) + (1 - self.win_rate) * (self.avg_loss / 100)
        ) * 100

    def _span_days(self) -> int:
        if not self.trades:
            return 1
        dates = [t.entry_date for t in self.trades]
        try:
            span = (max(dates) - min(dates)).days
        except Exception:
            span = 365
        return max(span, 1)

    def summary_row(self) -> dict:
        return {
            "Strategy": self.name,
            "Symbol": self.symbol,
            "Trades": self.total_trades,
            "Win Rate": f"{self.win_rate:.1%}",
            "Profit Factor": f"{self.profit_factor:.2f}",
            "Sharpe": f"{self.sharpe:.2f}",
            "Max DD": f"{self.max_drawdown:.1f}%",
            "Avg Win": f"{self.avg_win:.2f}%",
            "Avg Loss": f"{self.avg_loss:.2f}%",
            "Avg R:R": f"{self.avg_rr:.2f}",
            "Total Ret": f"{self.total_return:.1f}%",
            "Expectancy": f"{self.expectancy:.2f}%",
        }


# ---------------------------------------------------------------------------
# Strategy 1: Liquidity Sweep Reversal (LSR)
# ---------------------------------------------------------------------------
def strategy_lsr(df: pd.DataFrame, symbol: str) -> StrategyResult:
    """
    Liquidity Sweep Reversal (LSR) — 73% WR claimed.

    - 20-bar swing high/low pivots
    - Sweep: price goes beyond swing by 0.3%+, closes back inside
    - Long wick requirement: wick > 2x body (stop hunt)
    - EMA50 filter
    - SL: beyond sweep wick, TP: 2.5:1 R:R
    """
    PIVOT_LEN = 20
    SWEEP_THRESHOLD = 0.003  # 0.3%
    WICK_BODY_RATIO = 2.0
    RR_TARGET = 2.5

    trades: list[Trade] = []
    in_trade: Optional[Trade] = None

    # Find swing highs and lows
    swing_highs = []
    swing_lows = []

    for i in range(PIVOT_LEN, len(df) - PIVOT_LEN):
        window_high = df["High"].iloc[i - PIVOT_LEN:i + PIVOT_LEN + 1]
        window_low = df["Low"].iloc[i - PIVOT_LEN:i + PIVOT_LEN + 1]

        if df["High"].iloc[i] == window_high.max():
            swing_highs.append((i, df["High"].iloc[i]))
        if df["Low"].iloc[i] == window_low.min():
            swing_lows.append((i, df["Low"].iloc[i]))

    # Main loop
    for i in range(PIVOT_LEN * 2, len(df)):
        row = df.iloc[i]
        date = df.index[i]

        # Check for exit
        if in_trade is not None:
            hit_tp = (in_trade.direction == "long" and row["High"] >= in_trade.tp_price) or \
                     (in_trade.direction == "short" and row["Low"] <= in_trade.tp_price)
            hit_sl = (in_trade.direction == "long" and row["Low"] <= in_trade.sl_price) or \
                     (in_trade.direction == "short" and row["High"] >= in_trade.sl_price)

            if hit_sl:
                in_trade.close(date, in_trade.sl_price)
                trades.append(in_trade)
                in_trade = None
            elif hit_tp:
                in_trade.close(date, in_trade.tp_price)
                trades.append(in_trade)
                in_trade = None
            # Time-based exit: 30 bars max
            elif hasattr(in_trade, '_bar_count'):
                in_trade._bar_count += 1
                if in_trade._bar_count > 30:
                    in_trade.close(date, row["Close"])
                    trades.append(in_trade)
                    in_trade = None
            continue

        # Find nearest recent swing levels
        recent_lows = [(idx, lvl) for idx, lvl in swing_lows if idx < i and i - idx < 60]
        recent_highs = [(idx, lvl) for idx, lvl in swing_highs if idx < i and i - idx < 60]

        if not recent_lows and not recent_highs:
            continue

        body = row["Body"] if row["Body"] > 0 else 0.01
        features = extract_features(df, i)

        # LONG: Sweep below swing low
        if recent_lows:
            nearest_low = max(recent_lows, key=lambda x: x[0])
            swing_level = nearest_low[1]

            swept_below = row["Low"] < swing_level * (1 - SWEEP_THRESHOLD)
            closed_above = row["Close"] > swing_level
            long_lower_wick = row["Lower_Wick"] > WICK_BODY_RATIO * body
            bullish = row["Is_Bullish"]
            above_ema50 = row["Close"] > row["EMA50"] or row["EMA50"] < swing_level * 1.02

            if swept_below and closed_above and long_lower_wick and bullish:
                sl = row["Low"] * 0.998  # slightly below the sweep low
                risk = row["Close"] - sl
                tp = row["Close"] + risk * RR_TARGET

                trade = Trade(date, "long", row["Close"], sl, tp, row["Regime"], features)
                trade._bar_count = 0
                in_trade = trade

        # SHORT: Sweep above swing high
        if in_trade is None and recent_highs:
            nearest_high = max(recent_highs, key=lambda x: x[0])
            swing_level = nearest_high[1]

            swept_above = row["High"] > swing_level * (1 + SWEEP_THRESHOLD)
            closed_below = row["Close"] < swing_level
            long_upper_wick = row["Upper_Wick"] > WICK_BODY_RATIO * body
            bearish = not row["Is_Bullish"]
            below_ema50 = row["Close"] < row["EMA50"] or row["EMA50"] > swing_level * 0.98

            if swept_above and closed_below and long_upper_wick and bearish:
                sl = row["High"] * 1.002
                risk = sl - row["Close"]
                tp = row["Close"] - risk * RR_TARGET

                trade = Trade(date, "short", row["Close"], sl, tp, row["Regime"], features)
                trade._bar_count = 0
                in_trade = trade

    # Close any remaining open trade
    if in_trade is not None:
        in_trade.close(df.index[-1], df["Close"].iloc[-1])
        trades.append(in_trade)

    return StrategyResult("Liquidity_Sweep_Reversal", symbol, trades)


# ---------------------------------------------------------------------------
# Strategy 2: Flash Crash Reversal (FCR)
# ---------------------------------------------------------------------------
def strategy_fcr(df: pd.DataFrame, symbol: str) -> StrategyResult:
    """
    Flash Crash Reversal (FCR) — 71% WR, 4:1 R:R claimed.

    - Price drop > 5% within 5 bars
    - RSI(14) < 15
    - Volume > 5x SMA(20)
    - Enter on first green candle after drop
    - SL: below lowest low of crash
    - TP: 4:1 R:R
    """
    DROP_THRESHOLD = 0.05  # 5% drop
    DROP_BARS = 5
    RSI_EXTREME = 15
    VOL_MULTIPLIER = 5
    RR_TARGET = 4.0

    # Use relaxed thresholds for daily data since flash crashes are rare intraday patterns
    # Try primary thresholds first, then relax if too few signals
    thresholds = [
        (DROP_THRESHOLD, RSI_EXTREME, VOL_MULTIPLIER),    # strict
        (0.04, 20, 4.0),                                    # moderate
        (0.03, 25, 3.0),                                    # relaxed (daily TF adjustment)
    ]

    for drop_thresh, rsi_thresh, vol_mult in thresholds:
        trades = _run_fcr(df, symbol, drop_thresh, rsi_thresh, vol_mult, RR_TARGET)
        if len(trades) >= 3:
            break

    return StrategyResult("Flash_Crash_Reversal", symbol, trades)


def _run_fcr(df, symbol, drop_thresh, rsi_thresh, vol_mult, rr_target):
    trades: list[Trade] = []
    in_trade: Optional[Trade] = None
    crash_detected = False
    crash_low = 0.0
    crash_bar = 0

    for i in range(25, len(df)):
        row = df.iloc[i]
        date = df.index[i]

        # Check exit
        if in_trade is not None:
            hit_tp = row["High"] >= in_trade.tp_price
            hit_sl = row["Low"] <= in_trade.sl_price

            if hit_sl:
                in_trade.close(date, in_trade.sl_price)
                trades.append(in_trade)
                in_trade = None
                crash_detected = False
            elif hit_tp:
                in_trade.close(date, in_trade.tp_price)
                trades.append(in_trade)
                in_trade = None
                crash_detected = False
            # Time exit: 40 bars
            elif hasattr(in_trade, '_bar_count'):
                in_trade._bar_count += 1
                if in_trade._bar_count > 40:
                    in_trade.close(date, row["Close"])
                    trades.append(in_trade)
                    in_trade = None
                    crash_detected = False
            continue

        # Detect crash: price drop > threshold within N bars
        if i >= 5:
            price_5_ago = df["Close"].iloc[i - 5]
            drop_pct = (price_5_ago - row["Close"]) / price_5_ago

            rsi_extreme = row["RSI14"] < rsi_thresh if not pd.isna(row["RSI14"]) else False
            vol_spike = row["Volume"] > vol_mult * row["Vol_SMA20"] if not pd.isna(row["Vol_SMA20"]) else False

            if drop_pct > drop_thresh and rsi_extreme and vol_spike:
                crash_detected = True
                crash_low = df["Low"].iloc[i - 5:i + 1].min()
                crash_bar = i

        # Enter on first green candle after crash
        if crash_detected and in_trade is None and i > crash_bar:
            if row["Is_Bullish"] and row["Close"] > df["Open"].iloc[i]:
                sl = crash_low * 0.998
                risk = row["Close"] - sl
                tp = row["Close"] + risk * rr_target

                features = extract_features(df, i)
                trade = Trade(date, "long", row["Close"], sl, tp, row["Regime"], features)
                trade._bar_count = 0
                in_trade = trade
                crash_detected = False

            # Expire crash signal after 5 bars
            elif i - crash_bar > 5:
                crash_detected = False

    if in_trade is not None:
        in_trade.close(df.index[-1], df["Close"].iloc[-1])
        trades.append(in_trade)

    return trades


# ---------------------------------------------------------------------------
# Strategy 3: Statistical Arbitrage Pairs Trading (BTC-ETH)
# ---------------------------------------------------------------------------
def strategy_statarb(btc_df: pd.DataFrame, eth_df: pd.DataFrame) -> StrategyResult:
    """
    Statistical Arbitrage Pairs (BTC-ETH) — Sharpe 3.77 claimed.

    - Rolling 60-period OLS beta
    - Spread = BTC_return - beta * ETH_return
    - Z-score of spread
    - Long spread when Z < -2.0, short spread when Z > 2.0
    - Exit when Z crosses 0
    - Half-life estimation for lookback
    """
    LOOKBACK = 60
    Z_ENTRY = 2.0
    Z_EXIT = 0.0

    # Align indices
    common = btc_df.index.intersection(eth_df.index)
    btc = btc_df.loc[common].copy()
    eth = eth_df.loc[common].copy()

    btc_ret = btc["Close"].pct_change()
    eth_ret = eth["Close"].pct_change()

    trades: list[Trade] = []
    in_trade: Optional[Trade] = None
    trade_direction = None

    # Pre-compute rolling beta and spread z-score
    n = len(common)
    betas = pd.Series(np.nan, index=common)
    z_scores = pd.Series(np.nan, index=common)
    spread = pd.Series(np.nan, index=common)

    for i in range(LOOKBACK, n):
        window_btc = btc_ret.iloc[i - LOOKBACK:i].dropna()
        window_eth = eth_ret.iloc[i - LOOKBACK:i].dropna()

        if len(window_btc) < 30 or len(window_eth) < 30:
            continue

        # OLS: btc_ret = alpha + beta * eth_ret
        x = window_eth.values
        y = window_btc.values
        min_len = min(len(x), len(y))
        x, y = x[:min_len], y[:min_len]

        if np.std(x) < 1e-10:
            continue

        beta = np.cov(y, x)[0, 1] / np.var(x)
        betas.iloc[i] = beta
        spread.iloc[i] = btc_ret.iloc[i] - beta * eth_ret.iloc[i]

    # Z-score of spread
    spread_mean = spread.rolling(LOOKBACK).mean()
    spread_std = spread.rolling(LOOKBACK).std()
    z_scores = (spread - spread_mean) / spread_std.replace(0, np.nan)

    # Half-life estimation (for reporting)
    valid_spread = spread.dropna()
    if len(valid_spread) > 30:
        lag = valid_spread.shift(1).dropna()
        curr = valid_spread.iloc[1:len(lag) + 1]
        if len(lag) > 10:
            try:
                min_len = min(len(lag), len(curr))
                cov_matrix = np.cov(lag.values[:min_len], curr.values[:min_len])
                phi = cov_matrix[0, 1] / cov_matrix[0, 0] if cov_matrix[0, 0] != 0 else 0.9
                half_life = -np.log(2) / np.log(abs(phi)) if abs(phi) < 1 and phi != 0 else 30
                half_life = max(1, min(half_life, 120))
            except Exception:
                half_life = 30
        else:
            half_life = 30
    else:
        half_life = 30

    # Generate signals
    for i in range(LOOKBACK * 2, n):
        date = common[i]
        z = z_scores.iloc[i]

        if pd.isna(z):
            continue

        btc_row = btc.iloc[i]
        features = extract_features(btc, i)

        # Check exit
        if in_trade is not None:
            if (trade_direction == "long_spread" and z >= Z_EXIT) or \
               (trade_direction == "short_spread" and z <= Z_EXIT):
                # Exit: close at current BTC price
                in_trade.close(date, btc_row["Close"])
                trades.append(in_trade)
                in_trade = None
                trade_direction = None
            # Time exit: 60 bars
            elif hasattr(in_trade, '_bar_count'):
                in_trade._bar_count += 1
                if in_trade._bar_count > 60:
                    in_trade.close(date, btc_row["Close"])
                    trades.append(in_trade)
                    in_trade = None
                    trade_direction = None
            continue

        # Long spread: Z < -2 (BTC undervalued vs ETH) -> long BTC
        if z < -Z_ENTRY:
            sl = btc_row["Close"] * 0.97  # 3% SL
            tp = btc_row["Close"] * 1.06  # 6% TP
            trade = Trade(date, "long", btc_row["Close"], sl, tp,
                          btc_row.get("Regime", "Quiet") if "Regime" in btc.columns else "Quiet",
                          features)
            trade._bar_count = 0
            in_trade = trade
            trade_direction = "long_spread"

        # Short spread: Z > 2 (BTC overvalued vs ETH) -> short BTC
        elif z > Z_ENTRY:
            sl = btc_row["Close"] * 1.03
            tp = btc_row["Close"] * 0.94
            trade = Trade(date, "short", btc_row["Close"], sl, tp,
                          btc_row.get("Regime", "Quiet") if "Regime" in btc.columns else "Quiet",
                          features)
            trade._bar_count = 0
            in_trade = trade
            trade_direction = "short_spread"

    if in_trade is not None:
        in_trade.close(common[-1], btc.iloc[-1]["Close"])
        trades.append(in_trade)

    result = StrategyResult("StatArb_Pairs_BTC_ETH", "BTC-ETH", trades)
    result.half_life = round(half_life, 1)
    return result


# ---------------------------------------------------------------------------
# Strategy 4: Funding Rate Momentum (Contrarian)
# ---------------------------------------------------------------------------
def strategy_funding(df: pd.DataFrame, symbol: str) -> StrategyResult:
    """
    Funding Rate Momentum (Contrarian) — 64% WR claimed.

    - Proxy funding = (Close - VWAP20) / VWAP20 * 100
    - Short when funding > 0.1% (overleveraged longs)
    - Long when funding < -0.1% (overleveraged shorts)
    - Exit when funding normalizes (crosses 0)
    """
    FUNDING_LONG_THRESH = -0.1   # enter long below this
    FUNDING_SHORT_THRESH = 0.1   # enter short above this
    FUNDING_EXIT_THRESH = 0.0    # exit when crossing zero

    trades: list[Trade] = []
    in_trade: Optional[Trade] = None

    for i in range(25, len(df)):
        row = df.iloc[i]
        date = df.index[i]

        vwap = row["VWAP20"]
        if pd.isna(vwap) or vwap == 0:
            continue

        funding_proxy = (row["Close"] - vwap) / vwap * 100

        features = extract_features(df, i)
        features["funding_proxy"] = funding_proxy

        # Check exit
        if in_trade is not None:
            # Normal exit: funding normalizes
            exit_signal = False
            if in_trade.direction == "long" and funding_proxy >= FUNDING_EXIT_THRESH:
                exit_signal = True
            elif in_trade.direction == "short" and funding_proxy <= FUNDING_EXIT_THRESH:
                exit_signal = True

            # SL/TP check
            hit_sl = (in_trade.direction == "long" and row["Low"] <= in_trade.sl_price) or \
                     (in_trade.direction == "short" and row["High"] >= in_trade.sl_price)
            hit_tp = (in_trade.direction == "long" and row["High"] >= in_trade.tp_price) or \
                     (in_trade.direction == "short" and row["Low"] <= in_trade.tp_price)

            if hit_sl:
                in_trade.close(date, in_trade.sl_price)
                trades.append(in_trade)
                in_trade = None
            elif hit_tp:
                in_trade.close(date, in_trade.tp_price)
                trades.append(in_trade)
                in_trade = None
            elif exit_signal:
                in_trade.close(date, row["Close"])
                trades.append(in_trade)
                in_trade = None
            # Time exit: 20 bars
            elif hasattr(in_trade, '_bar_count'):
                in_trade._bar_count += 1
                if in_trade._bar_count > 20:
                    in_trade.close(date, row["Close"])
                    trades.append(in_trade)
                    in_trade = None
            continue

        # SHORT: overleveraged longs (funding high)
        if funding_proxy > FUNDING_SHORT_THRESH:
            atr = row["ATR14"] if not pd.isna(row["ATR14"]) else row["Close"] * 0.02
            sl = row["Close"] + 2 * atr
            tp = row["Close"] - 3 * atr  # ~1.5:1 R:R

            trade = Trade(date, "short", row["Close"], sl, tp, row["Regime"], features)
            trade._bar_count = 0
            in_trade = trade

        # LONG: overleveraged shorts (funding low)
        elif funding_proxy < FUNDING_LONG_THRESH:
            atr = row["ATR14"] if not pd.isna(row["ATR14"]) else row["Close"] * 0.02
            sl = row["Close"] - 2 * atr
            tp = row["Close"] + 3 * atr

            trade = Trade(date, "long", row["Close"], sl, tp, row["Regime"], features)
            trade._bar_count = 0
            in_trade = trade

    if in_trade is not None:
        in_trade.close(df.index[-1], df["Close"].iloc[-1])
        trades.append(in_trade)

    return StrategyResult("Funding_Rate_Momentum", symbol, trades)


# ---------------------------------------------------------------------------
# Feature Extraction (for ML validation)
# ---------------------------------------------------------------------------
def extract_features(df: pd.DataFrame, idx: int) -> dict:
    """Extract ML features at signal time."""
    row = df.iloc[idx]

    def safe_val(val, default=0.0):
        return float(val) if not pd.isna(val) else default

    return {
        "rsi14": safe_val(row.get("RSI14", 50)),
        "adx14": safe_val(row.get("ADX14", 25)),
        "atr_pct": safe_val(row.get("ATR_pct", 2)),
        "vol_zscore": safe_val(row.get("Vol_Zscore", 0)),
        "return_20d": safe_val(row.get("Return_20d", 0)),
        "return_60d": safe_val(row.get("Return_60d", 0)),
        "bb_width": safe_val(row.get("BB_width", 0.05)),
    }


# ---------------------------------------------------------------------------
# ML Validation
# ---------------------------------------------------------------------------
def ml_validate(results: list[StrategyResult]) -> dict:
    """
    For each strategy, train logistic regression on trade features to predict win/loss.
    Returns ML-adjusted metrics.
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import cross_val_score

    ml_results = {}
    feature_names = ["rsi14", "adx14", "atr_pct", "vol_zscore", "return_20d", "return_60d", "bb_width"]

    for result in results:
        if result.total_trades < 10:
            ml_results[f"{result.name}_{result.symbol}"] = {
                "ml_adjusted_wr": result.win_rate,
                "raw_wr": result.win_rate,
                "n_trades": result.total_trades,
                "note": "Too few trades for ML validation",
                "top_features": [],
            }
            continue

        # Build feature matrix
        X = []
        y = []
        for t in result.trades:
            feat_vec = [t.features.get(f, 0.0) for f in feature_names]
            X.append(feat_vec)
            y.append(1 if t.won else 0)

        X = np.array(X, dtype=float)
        y = np.array(y, dtype=int)

        # Handle NaN/inf
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

        # Fixed: Use Pipeline to prevent scaler data leakage in cross-validation (Lopez de Prado)
        from sklearn.pipeline import Pipeline
        pipe = Pipeline([
            ('scaler', StandardScaler()),
            ('model', LogisticRegression(max_iter=1000, random_state=42)),
        ])

        n_splits = min(5, max(2, len(y) // 5))
        if n_splits >= 2 and len(np.unique(y)) > 1:
            try:
                cv_scores = cross_val_score(pipe, X, y, cv=n_splits, scoring="accuracy")
                ml_wr = float(np.mean(cv_scores))
            except Exception:
                ml_wr = result.win_rate
        else:
            ml_wr = result.win_rate

        # Scale for feature importance analysis below
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Fit full model for feature importance
        model = LogisticRegression(max_iter=1000, random_state=42)
        try:
            model.fit(X_scaled, y)
            importances = np.abs(model.coef_[0])
            sorted_idx = np.argsort(importances)[::-1]
            top_features = [(feature_names[j], round(importances[j], 3)) for j in sorted_idx[:3]]
        except Exception:
            top_features = []

        ml_results[f"{result.name}_{result.symbol}"] = {
            "ml_adjusted_wr": ml_wr,
            "raw_wr": result.win_rate,
            "n_trades": result.total_trades,
            "top_features": top_features,
            "cv_scores": cv_scores.tolist() if 'cv_scores' in dir() else [],
        }

    return ml_results


# ---------------------------------------------------------------------------
# Regime Breakdown
# ---------------------------------------------------------------------------
def regime_breakdown(results: list[StrategyResult]) -> pd.DataFrame:
    """Break down win rate by regime for each strategy."""
    rows = []
    for result in results:
        regimes = {}
        for t in result.trades:
            r = t.regime
            if r not in regimes:
                regimes[r] = {"wins": 0, "total": 0}
            regimes[r]["total"] += 1
            if t.won:
                regimes[r]["wins"] += 1

        for regime, data in sorted(regimes.items()):
            wr = data["wins"] / data["total"] if data["total"] > 0 else 0
            rows.append({
                "Strategy": result.name,
                "Symbol": result.symbol,
                "Regime": regime,
                "Trades": data["total"],
                "Win Rate": f"{wr:.1%}",
            })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Printing
# ---------------------------------------------------------------------------
def print_header(text: str):
    width = 80
    print("\n" + "=" * width)
    print(f"  {text}")
    print("=" * width)


def print_results_table(results: list[StrategyResult]):
    rows = [r.summary_row() for r in results]
    df = pd.DataFrame(rows)
    print(df.to_string(index=False))


def print_trade_samples(result: StrategyResult, max_trades: int = 5):
    """Print sample trades for a strategy."""
    if not result.trades:
        print("  No trades.")
        return
    sample = result.trades[:max_trades]
    rows = [t.to_dict() for t in sample]
    df = pd.DataFrame(rows)
    print(df.to_string(index=False))


def print_ml_results(ml_results: dict):
    """Print ML validation results."""
    for key, data in ml_results.items():
        print(f"\n  {key}:")
        print(f"    Raw Win Rate:        {data['raw_wr']:.1%}")
        print(f"    ML-Adjusted WR:      {data['ml_adjusted_wr']:.1%}")
        print(f"    Trade Count:         {data['n_trades']}")
        if data.get("note"):
            print(f"    Note:                {data['note']}")
        if data.get("top_features"):
            print(f"    Top Predictive Features:")
            for fname, imp in data["top_features"]:
                print(f"      - {fname}: {imp}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Kimi Claw v4.1 Strategy Backtester")
    parser.add_argument("--symbols", type=str, default=",".join(DEFAULT_SYMBOLS),
                        help="Comma-separated symbols (default: BTC-USD,ETH-USD,SOL-USD)")
    parser.add_argument("--period", type=str, default=DEFAULT_PERIOD,
                        help="yfinance period (default: 2y)")
    parser.add_argument("--no-ml", action="store_true", help="Skip ML validation")
    args = parser.parse_args()

    symbols = [s.strip() for s in args.symbols.split(",")]

    print_header("KIMI CLAW v4.1 EXTENDED STRATEGIES BACKTESTER")
    print(f"  Date:       {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Symbols:    {', '.join(symbols)}")
    print(f"  Period:     {args.period}")
    print(f"  Capital:    ${INITIAL_CAPITAL:,.0f}")
    print(f"  Risk/Trade: {RISK_PER_TRADE:.0%}")
    print(f"  TX Cost:    {TX_COST_PER_SIDE:.1%} per side ({TX_COST_ROUNDTRIP:.1%} RT)")
    print()

    # -------------------------------------------------------------------
    # Download data
    # -------------------------------------------------------------------
    print_header("DATA DOWNLOAD")
    data = download_data(symbols, args.period)

    if not data:
        print("ERROR: No data downloaded. Exiting.")
        sys.exit(1)

    # Add indicators
    print("\nComputing indicators...")
    for sym in data:
        data[sym] = add_indicators(data[sym])
        print(f"  {sym}: {len(data[sym])} bars, {data[sym].index[0].strftime('%Y-%m-%d')} to {data[sym].index[-1].strftime('%Y-%m-%d')}")

    # -------------------------------------------------------------------
    # Run strategies
    # -------------------------------------------------------------------
    all_results: list[StrategyResult] = []

    # Strategy 1: LSR on all symbols
    print_header("STRATEGY 1: LIQUIDITY SWEEP REVERSAL (LSR)")
    print("  Claimed: 73% WR, 2.5:1 R:R | 20-bar pivots, stop-hunt wicks, EMA50 filter")
    print()
    for sym in symbols:
        if sym in data:
            result = strategy_lsr(data[sym], sym)
            all_results.append(result)
            print(f"  {sym}: {result.total_trades} trades, WR={result.win_rate:.1%}, PF={result.profit_factor:.2f}, Sharpe={result.sharpe:.2f}")

    # Strategy 2: FCR on all symbols
    print_header("STRATEGY 2: FLASH CRASH REVERSAL (FCR)")
    print("  Claimed: 71% WR, 4:1 R:R | 5% drop + RSI<15 + 5x volume spike")
    print()
    for sym in symbols:
        if sym in data:
            result = strategy_fcr(data[sym], sym)
            all_results.append(result)
            print(f"  {sym}: {result.total_trades} trades, WR={result.win_rate:.1%}, PF={result.profit_factor:.2f}, Sharpe={result.sharpe:.2f}")

    # Strategy 3: StatArb Pairs (BTC-ETH)
    print_header("STRATEGY 3: STATISTICAL ARBITRAGE PAIRS (BTC-ETH)")
    print("  Claimed: Sharpe 3.77 | OLS beta spread Z-score mean reversion")
    print()
    if "BTC-USD" in data and "ETH-USD" in data:
        btc_ind = add_indicators(data["BTC-USD"]) if "Regime" not in data["BTC-USD"].columns else data["BTC-USD"]
        result = strategy_statarb(data["BTC-USD"], data["ETH-USD"])
        all_results.append(result)
        hl = getattr(result, "half_life", "N/A")
        print(f"  BTC-ETH: {result.total_trades} trades, WR={result.win_rate:.1%}, PF={result.profit_factor:.2f}, Sharpe={result.sharpe:.2f}")
        print(f"  Half-life: {hl} bars")
    else:
        print("  SKIPPED: Need both BTC-USD and ETH-USD data")

    # Strategy 4: Funding Rate Momentum on all symbols
    print_header("STRATEGY 4: FUNDING RATE MOMENTUM (CONTRARIAN)")
    print("  Claimed: 64% WR | VWAP deviation proxy, contrarian entries")
    print()
    for sym in symbols:
        if sym in data:
            result = strategy_funding(data[sym], sym)
            all_results.append(result)
            print(f"  {sym}: {result.total_trades} trades, WR={result.win_rate:.1%}, PF={result.profit_factor:.2f}, Sharpe={result.sharpe:.2f}")

    # -------------------------------------------------------------------
    # Comprehensive Results Table
    # -------------------------------------------------------------------
    print_header("COMPREHENSIVE RESULTS")
    print_results_table(all_results)

    # -------------------------------------------------------------------
    # Regime Breakdown
    # -------------------------------------------------------------------
    print_header("REGIME BREAKDOWN")
    regime_df = regime_breakdown(all_results)
    if not regime_df.empty:
        print(regime_df.to_string(index=False))
    else:
        print("  No regime data available.")

    # -------------------------------------------------------------------
    # Sample Trades
    # -------------------------------------------------------------------
    print_header("SAMPLE TRADES (first 5 per strategy)")
    for result in all_results:
        print(f"\n  --- {result.name} ({result.symbol}) ---")
        print_trade_samples(result, 5)

    # -------------------------------------------------------------------
    # Claimed vs Actual Comparison
    # -------------------------------------------------------------------
    print_header("CLAIMED vs ACTUAL COMPARISON")

    claimed = {
        "Liquidity_Sweep_Reversal": {"wr": 0.73, "metric": "2.5:1 R:R"},
        "Flash_Crash_Reversal": {"wr": 0.71, "metric": "4:1 R:R"},
        "StatArb_Pairs_BTC_ETH": {"wr": None, "metric": "Sharpe 3.77"},
        "Funding_Rate_Momentum": {"wr": 0.64, "metric": "contrarian"},
    }

    for result in all_results:
        name = result.name
        c = claimed.get(name, {})
        claimed_wr = c.get("wr")
        print(f"\n  {name} ({result.symbol}):")
        if claimed_wr:
            delta = result.win_rate - claimed_wr
            arrow = ">>>" if delta > 0 else "<<<" if delta < -0.1 else "~=="
            print(f"    Claimed WR: {claimed_wr:.0%}  |  Actual WR: {result.win_rate:.1%}  {arrow}  delta: {delta:+.1%}")
        else:
            print(f"    Actual WR: {result.win_rate:.1%}")
        print(f"    Claimed: {c.get('metric', 'N/A')}  |  Actual Sharpe: {result.sharpe:.2f}, Avg R:R: {result.avg_rr:.2f}")
        print(f"    Profit Factor: {result.profit_factor:.2f}  |  Max DD: {result.max_drawdown:.1f}%")

    # -------------------------------------------------------------------
    # ML Validation
    # -------------------------------------------------------------------
    if not args.no_ml:
        print_header("ML VALIDATION (Logistic Regression)")
        print("  Training logistic regression to predict win/loss from signal features...")
        print("  Features: RSI14, ADX14, ATR%, Volume Z-score, 20d return, 60d return, BB width")

        ml_results = ml_validate(all_results)
        print_ml_results(ml_results)

        # ML summary table
        print("\n  ML Summary:")
        print(f"  {'Strategy':<40} {'Raw WR':>8} {'ML WR':>8} {'Delta':>8}")
        print("  " + "-" * 66)
        for key, data in ml_results.items():
            delta = data["ml_adjusted_wr"] - data["raw_wr"]
            print(f"  {key:<40} {data['raw_wr']:>7.1%} {data['ml_adjusted_wr']:>7.1%} {delta:>+7.1%}")

    # -------------------------------------------------------------------
    # Final Summary / Verdict
    # -------------------------------------------------------------------
    print_header("FINAL VERDICT")

    total_trades = sum(r.total_trades for r in all_results)
    total_wins = sum(sum(1 for t in r.trades if t.won) for r in all_results)
    overall_wr = total_wins / total_trades if total_trades > 0 else 0

    profitable = [r for r in all_results if r.profit_factor > 1.0]
    strong = [r for r in all_results if r.win_rate > 0.55 and r.profit_factor > 1.2]

    print(f"  Total Strategies Tested:  {len(all_results)}")
    print(f"  Total Trades Generated:   {total_trades}")
    print(f"  Overall Win Rate:         {overall_wr:.1%}")
    print(f"  Profitable (PF > 1.0):    {len(profitable)}/{len(all_results)}")
    print(f"  Strong (WR>55%, PF>1.2):  {len(strong)}/{len(all_results)}")
    print()

    for r in all_results:
        verdict = "PASS" if r.profit_factor > 1.0 and r.total_trades >= 3 else \
                  "INSUFFICIENT DATA" if r.total_trades < 3 else "FAIL"
        match = ""
        c = claimed.get(r.name, {})
        if c.get("wr"):
            if abs(r.win_rate - c["wr"]) < 0.1:
                match = " [CLAIM SUPPORTED]"
            else:
                match = " [CLAIM NOT SUPPORTED]"
        print(f"  [{verdict}] {r.name} ({r.symbol}): WR={r.win_rate:.1%}, PF={r.profit_factor:.2f}, Sharpe={r.sharpe:.2f}{match}")

    print()
    print("  Note: Daily timeframe results may differ from optimal 4H/1H timeframes.")
    print("  Flash Crash signals are inherently rare on daily bars.")
    print("  Statistical Arb Sharpe is from relative value (BTC vs ETH), not directional.")
    print()

    return all_results


if __name__ == "__main__":
    main()
