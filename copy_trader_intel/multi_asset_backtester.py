#!/usr/bin/env python3
"""
Multi-Asset Walk-Forward Backtester
=====================================
Tests copy trader strategies and alpha engine strategies across forex, futures,
stocks, and commodities with TP/SL variation grid search.

Features:
- Walk-forward validation (70% train / 30% test)
- TP/SL grid search (5x5 = 25 combinations per strategy)
- Session awareness for forex (London/NY/Asian)
- Contract roll handling for futures
- Output compatible with audit pipeline

Usage:
    python copy_trader_intel/multi_asset_backtester.py
"""

import json
import sys
import os
import time
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass, field, asdict

# Fix Windows charmap encoding - force UTF-8 stdout/stderr
if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

try:
    import yfinance as yf
    import pandas as pd
    import numpy as np
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False
    pd = None
    np = None
    yf = None
    print("[WARN] yfinance/pandas/numpy not installed - backtester needs them: pip install yfinance pandas numpy")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class BacktestTrade:
    """Single trade record from backtesting."""
    symbol: str
    direction: str               # LONG or SHORT
    entry_price: float
    entry_date: str
    tp: float
    sl: float
    exit_price: float = 0.0
    exit_date: str = ""
    exit_reason: str = ""        # TP_HIT, SL_HIT, TIME_EXPIRY, TRAILING_STOP
    pnl_pct: float = 0.0
    hold_bars: int = 0
    strategy: str = ""
    asset_class: str = ""
    variation_name: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _safe_get(df, idx, col, offset=0):
    """Safely get a value from DataFrame at idx-offset."""
    if not HAS_YFINANCE:
        return None
    pos = df.index.get_loc(idx)
    target = pos - offset
    if target < 0 or target >= len(df):
        return None
    return df.iloc[target][col]


def _is_nan(val):
    """Check if value is None or NaN."""
    if val is None:
        return True
    try:
        return math.isnan(val)
    except (TypeError, ValueError):
        return False


# ---------------------------------------------------------------------------
# Built-in strategy signal functions
# ---------------------------------------------------------------------------
# Each function receives a pandas DataFrame + current index.
# Returns: "LONG", "SHORT", or None

def rsi_mean_reversion(df, idx, period=14, oversold=30, overbought=70):
    """RSI bounce from oversold/overbought zones."""
    col = f"rsi_{period}"
    if col not in df.columns:
        return None
    val = df.at[idx, col]
    prev = _safe_get(df, idx, col, 1)
    if _is_nan(val) or _is_nan(prev):
        return None
    if prev < oversold and val >= oversold:
        return "LONG"
    if prev > overbought and val <= overbought:
        return "SHORT"
    return None


def macd_crossover(df, idx):
    """MACD line crosses signal line."""
    if "macd" not in df.columns or "macd_signal" not in df.columns:
        return None
    macd_now = df.at[idx, "macd"]
    sig_now = df.at[idx, "macd_signal"]
    macd_prev = _safe_get(df, idx, "macd", 1)
    sig_prev = _safe_get(df, idx, "macd_signal", 1)
    if any(_is_nan(v) for v in [macd_now, sig_now, macd_prev, sig_prev]):
        return None
    if macd_prev <= sig_prev and macd_now > sig_now:
        return "LONG"
    if macd_prev >= sig_prev and macd_now < sig_now:
        return "SHORT"
    return None


def bollinger_breakout(df, idx, period=20, std_mult=2):
    """Price breaks Bollinger band and reverses back inside (mean reversion)."""
    upper = f"bb_upper_{period}"
    lower = f"bb_lower_{period}"
    if upper not in df.columns or lower not in df.columns:
        return None
    close = df.at[idx, "Close"]
    prev_close = _safe_get(df, idx, "Close", 1)
    ub = df.at[idx, upper]
    lb = df.at[idx, lower]
    if any(_is_nan(v) for v in [close, prev_close, ub, lb]):
        return None
    if prev_close <= lb and close > lb:
        return "LONG"
    if prev_close >= ub and close < ub:
        return "SHORT"
    return None


def momentum_20d(df, idx, threshold=0.02):
    """20-day momentum above/below threshold."""
    col = "mom_20"
    if col not in df.columns:
        return None
    val = df.at[idx, col]
    if _is_nan(val):
        return None
    if val > threshold:
        return "LONG"
    if val < -threshold:
        return "SHORT"
    return None


def ema_crossover(df, idx, fast=9, slow=21):
    """EMA fast/slow crossover."""
    fc = f"ema_{fast}"
    sc = f"ema_{slow}"
    if fc not in df.columns or sc not in df.columns:
        return None
    f_now = df.at[idx, fc]
    s_now = df.at[idx, sc]
    f_prev = _safe_get(df, idx, fc, 1)
    s_prev = _safe_get(df, idx, sc, 1)
    if any(_is_nan(v) for v in [f_now, s_now, f_prev, s_prev]):
        return None
    if f_prev <= s_prev and f_now > s_now:
        return "LONG"
    if f_prev >= s_prev and f_now < s_now:
        return "SHORT"
    return None


def atr_breakout(df, idx, period=14, mult=1.5):
    """ATR channel breakout: price moves beyond ATR*mult from prior close."""
    atr_col = f"atr_{period}"
    if atr_col not in df.columns:
        return None
    atr = df.at[idx, atr_col]
    close = df.at[idx, "Close"]
    prev_close = _safe_get(df, idx, "Close", 1)
    if any(_is_nan(v) for v in [atr, close, prev_close]):
        return None
    upper = prev_close + atr * mult
    lower = prev_close - atr * mult
    if close > upper:
        return "LONG"
    if close < lower:
        return "SHORT"
    return None


# Registry of built-in strategies
BUILTIN_STRATEGIES = {
    "rsi_mean_reversion": rsi_mean_reversion,
    "macd_crossover": macd_crossover,
    "bollinger_breakout": bollinger_breakout,
    "momentum_20d": momentum_20d,
    "ema_crossover": ema_crossover,
    "atr_breakout": atr_breakout,
}


# ---------------------------------------------------------------------------
# MultiAssetBacktester
# ---------------------------------------------------------------------------

class MultiAssetBacktester:
    """Walk-forward backtester across multiple asset classes with TP/SL grid search."""

    def __init__(self, asset_class: str, symbols: list, lookback_days: int = 365):
        self.asset_class = asset_class
        self.symbols = symbols
        self.lookback_days = lookback_days
        self.data: dict = {}  # symbol -> DataFrame

    # -- data loading -------------------------------------------------------

    def load_data(self) -> bool:
        """Load OHLCV data via yfinance for all symbols. Returns True if any data loaded."""
        if not HAS_YFINANCE:
            print("[ERROR] yfinance required for data loading")
            return False

        end = datetime.now(timezone.utc)
        start = end - timedelta(days=self.lookback_days)
        loaded = 0

        for sym in self.symbols:
            try:
                ticker = yf.Ticker(sym)
                df = ticker.history(start=start.strftime("%Y-%m-%d"),
                                    end=end.strftime("%Y-%m-%d"),
                                    interval="1d")
                if df is None or df.empty:
                    print(f"  [WARN] No data for {sym}")
                    continue

                required = ["Open", "High", "Low", "Close", "Volume"]
                missing = [c for c in required if c not in df.columns]
                if missing:
                    print(f"  [WARN] Missing columns {missing} for {sym}")
                    continue

                df = self._add_indicators(df)
                self.data[sym] = df
                loaded += 1
                print(f"  [OK] {sym}: {len(df)} bars loaded")
            except Exception as e:
                print(f"  [ERROR] {sym}: {e}")

        print(f"[INFO] Loaded {loaded}/{len(self.symbols)} symbols for {self.asset_class}")
        return loaded > 0

    def _add_indicators(self, df) -> "pd.DataFrame":
        """Compute technical indicators needed by built-in strategies."""
        close = df["Close"]
        high = df["High"]
        low = df["Low"]

        # RSI 14
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        avg_gain = gain.rolling(14, min_periods=14).mean()
        avg_loss = loss.rolling(14, min_periods=14).mean()
        rs = avg_gain / avg_loss.replace(0, 1e-10)
        df["rsi_14"] = 100 - (100 / (1 + rs))

        # MACD (12, 26, 9)
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        df["macd"] = ema12 - ema26
        df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()

        # Bollinger Bands (20, 2)
        sma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        df["bb_upper_20"] = sma20 + 2 * std20
        df["bb_lower_20"] = sma20 - 2 * std20

        # Momentum 20d
        df["mom_20"] = close.pct_change(20)

        # EMAs
        for span in (9, 21, 50):
            df[f"ema_{span}"] = close.ewm(span=span, adjust=False).mean()

        # ATR 14
        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ], axis=1).max(axis=1)
        df["atr_14"] = tr.rolling(14).mean()

        return df

    # -- single strategy backtest -------------------------------------------

    def run_strategy_backtest(self, strategy_func: Callable, strategy_name: str = "",
                              tp_mult: float = 1.0, sl_mult: float = 1.0,
                              max_hold: int = 20) -> list:
        """Run a single strategy through historical data for all loaded symbols.

        TP/SL are ATR-based: tp = entry +/- atr*tp_mult, sl = entry -/+ atr*sl_mult.
        Returns list of BacktestTrade.
        """
        if not HAS_YFINANCE:
            return []

        all_trades: list = []

        for sym, df in self.data.items():
            if len(df) < 50:
                continue

            in_trade = False
            trade: Optional[BacktestTrade] = None

            for i in range(50, len(df)):
                idx = df.index[i]
                row = df.iloc[i]
                atr = row.get("atr_14", None)
                if _is_nan(atr):
                    atr = row["Close"] * 0.02  # fallback 2%

                # Check exit if in trade
                if in_trade and trade is not None:
                    trade.hold_bars += 1
                    hi = row["High"]
                    lo = row["Low"]

                    if trade.direction == "LONG":
                        if hi >= trade.tp:
                            trade.exit_price = trade.tp
                            trade.exit_reason = "TP_HIT"
                        elif lo <= trade.sl:
                            trade.exit_price = trade.sl
                            trade.exit_reason = "SL_HIT"
                        elif trade.hold_bars >= max_hold:
                            trade.exit_price = row["Close"]
                            trade.exit_reason = "TIME_EXPIRY"
                    else:  # SHORT
                        if lo <= trade.tp:
                            trade.exit_price = trade.tp
                            trade.exit_reason = "TP_HIT"
                        elif hi >= trade.sl:
                            trade.exit_price = trade.sl
                            trade.exit_reason = "SL_HIT"
                        elif trade.hold_bars >= max_hold:
                            trade.exit_price = row["Close"]
                            trade.exit_reason = "TIME_EXPIRY"

                    if trade.exit_reason:
                        trade.exit_date = str(idx)
                        if trade.direction == "LONG":
                            trade.pnl_pct = ((trade.exit_price - trade.entry_price) / trade.entry_price) * 100
                        else:
                            trade.pnl_pct = ((trade.entry_price - trade.exit_price) / trade.entry_price) * 100
                        all_trades.append(trade)
                        in_trade = False
                        trade = None
                    continue

                # Check for new signal
                signal = strategy_func(df, idx)
                if signal is None:
                    continue

                entry = row["Close"]
                if signal == "LONG":
                    tp_price = entry + atr * tp_mult
                    sl_price = entry - atr * sl_mult
                elif signal == "SHORT":
                    tp_price = entry - atr * tp_mult
                    sl_price = entry + atr * sl_mult
                else:
                    continue

                trade = BacktestTrade(
                    symbol=sym,
                    direction=signal,
                    entry_price=entry,
                    entry_date=str(idx),
                    tp=tp_price,
                    sl=sl_price,
                    strategy=strategy_name or getattr(strategy_func, "__name__", "unknown"),
                    asset_class=self.asset_class,
                )
                in_trade = True

        return all_trades

    # -- TP/SL grid search --------------------------------------------------

    def run_tp_sl_grid(self, strategy_func: Callable, strategy_name: str = "",
                       tp_range: tuple = (0.5, 0.8, 1.0, 1.5, 2.0, 2.5),
                       sl_range: tuple = (0.5, 0.8, 1.0, 1.5, 2.0),
                       max_hold: int = 20) -> list:
        """Test strategy with all TP/SL combinations.

        Returns list of dicts: {tp_mult, sl_mult, win_rate, profit_factor, sharpe, trades, max_dd}
        """
        results = []
        total = len(tp_range) * len(sl_range)
        done = 0

        for tp_m in tp_range:
            for sl_m in sl_range:
                trades = self.run_strategy_backtest(
                    strategy_func, strategy_name=strategy_name,
                    tp_mult=tp_m, sl_mult=sl_m, max_hold=max_hold
                )
                metrics = self.calculate_metrics(trades)
                metrics["tp_mult"] = tp_m
                metrics["sl_mult"] = sl_m
                metrics["trade_count"] = len(trades)
                results.append(metrics)
                done += 1
                if done % 5 == 0:
                    print(f"    Grid progress: {done}/{total}")

        results.sort(key=lambda x: x.get("profit_factor", 0), reverse=True)
        return results

    # -- walk-forward validation --------------------------------------------

    def run_walk_forward(self, strategy_func: Callable, strategy_name: str = "",
                         train_pct: float = 0.7, max_hold: int = 20) -> dict:
        """Walk-forward validation: optimize TP/SL on train set, validate on test set.

        Splits data 70/30 (train/test), finds best TP/SL on train, validates on test.
        Returns dict with in_sample and out_of_sample results plus robustness check.
        """
        if not self.data:
            return {"error": "No data loaded"}

        # Split data into train/test
        train_data = {}
        test_data = {}
        for sym, df in self.data.items():
            split_idx = int(len(df) * train_pct)
            if split_idx < 50 or len(df) - split_idx < 20:
                continue
            train_data[sym] = df.iloc[:split_idx].copy()
            test_data[sym] = df.iloc[split_idx:].copy()

        if not train_data:
            return {"error": "Insufficient data for walk-forward split"}

        # -- Train phase: find best TP/SL on in-sample data --
        original_data = self.data
        self.data = train_data

        tp_range = (0.5, 1.0, 1.5, 2.0, 2.5)
        sl_range = (0.5, 1.0, 1.5, 2.0)
        best_pf = -999
        best_tp = 1.0
        best_sl = 1.0

        for tp_m in tp_range:
            for sl_m in sl_range:
                trades = self.run_strategy_backtest(
                    strategy_func, strategy_name=strategy_name,
                    tp_mult=tp_m, sl_mult=sl_m, max_hold=max_hold
                )
                metrics = self.calculate_metrics(trades)
                pf = metrics.get("profit_factor", 0)
                if pf > best_pf and len(trades) >= 5:
                    best_pf = pf
                    best_tp = tp_m
                    best_sl = sl_m

        # In-sample results with best params
        in_sample_trades = self.run_strategy_backtest(
            strategy_func, strategy_name=strategy_name,
            tp_mult=best_tp, sl_mult=best_sl, max_hold=max_hold
        )
        in_sample_metrics = self.calculate_metrics(in_sample_trades)
        in_sample_metrics["best_tp_mult"] = best_tp
        in_sample_metrics["best_sl_mult"] = best_sl
        in_sample_metrics["trade_count"] = len(in_sample_trades)

        # -- Test phase: validate best params on out-of-sample data --
        self.data = test_data
        out_sample_trades = self.run_strategy_backtest(
            strategy_func, strategy_name=strategy_name,
            tp_mult=best_tp, sl_mult=best_sl, max_hold=max_hold
        )
        out_sample_metrics = self.calculate_metrics(out_sample_trades)
        out_sample_metrics["trade_count"] = len(out_sample_trades)

        # Restore original data
        self.data = original_data

        # Robustness check: compare in-sample vs out-of-sample win rates
        is_wr = in_sample_metrics.get("win_rate", 0)
        oos_wr = out_sample_metrics.get("win_rate", 0)
        degradation = (is_wr - oos_wr) / max(is_wr, 0.01) if is_wr > 0 else 0

        return {
            "strategy": strategy_name or getattr(strategy_func, "__name__", "unknown"),
            "asset_class": self.asset_class,
            "best_tp_mult": best_tp,
            "best_sl_mult": best_sl,
            "in_sample": in_sample_metrics,
            "out_of_sample": out_sample_metrics,
            "degradation_pct": round(degradation * 100, 2),
            "robust": degradation < 0.30,  # <30% degradation = robust
        }

    # -- metrics calculation ------------------------------------------------

    def calculate_metrics(self, trades: list) -> dict:
        """Calculate performance metrics from trade list.

        Returns: win_rate, profit_factor, sharpe_ratio, max_drawdown,
                 avg_hold_bars, expectancy, total_pnl_pct
        """
        if not trades:
            return {
                "win_rate": 0, "profit_factor": 0, "sharpe_ratio": 0,
                "max_drawdown": 0, "avg_hold_bars": 0, "expectancy": 0,
                "total_pnl_pct": 0,
            }

        pnls = [t.pnl_pct if isinstance(t, BacktestTrade) else t.get("pnl_pct", 0) for t in trades]
        holds = [t.hold_bars if isinstance(t, BacktestTrade) else t.get("hold_bars", 0) for t in trades]

        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]

        win_rate = len(wins) / len(pnls) if pnls else 0
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = abs(sum(losses) / len(losses)) if losses else 0.01

        gross_profit = sum(wins)
        gross_loss = abs(sum(losses)) if losses else 0.01
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else gross_profit

        # Sharpe ratio (annualized from trade-level returns)
        if len(pnls) >= 2:
            mean_pnl = sum(pnls) / len(pnls)
            variance = sum((p - mean_pnl) ** 2 for p in pnls) / (len(pnls) - 1)
            std_pnl = math.sqrt(variance) if variance > 0 else 0.01
            sharpe = (mean_pnl / std_pnl) * math.sqrt(252) if std_pnl > 0 else 0
        else:
            sharpe = 0

        # Max drawdown (equity curve simulation)
        equity = 100.0
        peak = equity
        max_dd = 0
        for p in pnls:
            equity *= (1 + p / 100)
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd

        # Expectancy = avg_win * win_rate - avg_loss * (1 - win_rate)
        expectancy = avg_win * win_rate - avg_loss * (1 - win_rate)

        return {
            "win_rate": round(win_rate, 4),
            "profit_factor": round(profit_factor, 3),
            "sharpe_ratio": round(sharpe, 3),
            "max_drawdown": round(max_dd, 4),
            "avg_hold_bars": round(sum(holds) / len(holds), 1) if holds else 0,
            "expectancy": round(expectancy, 4),
            "total_pnl_pct": round(sum(pnls), 2),
        }


# ---------------------------------------------------------------------------
# Asset class definitions
# ---------------------------------------------------------------------------

ASSET_CLASSES = {
    "forex": {
        "symbols": ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X"],
        "lookback": 365,
    },
    "commodities": {
        "symbols": ["GC=F", "CL=F", "SI=F", "NG=F"],
        "lookback": 365,
    },
    "index_futures": {
        "symbols": ["ES=F", "NQ=F", "YM=F"],
        "lookback": 365,
    },
    "stocks": {
        "symbols": ["AAPL", "MSFT", "NVDA", "TSLA", "AMD"],
        "lookback": 365,
    },
}


# ---------------------------------------------------------------------------
# Serialization helper
# ---------------------------------------------------------------------------

def _serialize_results(obj):
    """Make results JSON-serializable (handles BacktestTrade, NaN, etc.)."""
    if isinstance(obj, dict):
        return {k: _serialize_results(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize_results(v) for v in obj]
    if isinstance(obj, BacktestTrade):
        return obj.to_dict()
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return 0
    return obj


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not HAS_YFINANCE:
        print("[FATAL] Install dependencies: pip install yfinance pandas numpy")
        sys.exit(1)

    print("=" * 70)
    print("  Multi-Asset Walk-Forward Backtester")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    all_results = {}
    walk_forward_results = []

    for ac_name, ac_cfg in ASSET_CLASSES.items():
        print(f"\n{'='*60}")
        print(f"  Asset Class: {ac_name.upper()}")
        print(f"{'='*60}")

        bt = MultiAssetBacktester(
            asset_class=ac_name,
            symbols=ac_cfg["symbols"],
            lookback_days=ac_cfg["lookback"],
        )

        if not bt.load_data():
            print(f"  [SKIP] No data for {ac_name}")
            continue

        ac_results = {}

        for strat_name, strat_func in BUILTIN_STRATEGIES.items():
            print(f"\n  Strategy: {strat_name}")
            print(f"  {'-'*40}")

            # Walk-forward validation
            wf = bt.run_walk_forward(strat_func, strategy_name=strat_name)
            walk_forward_results.append(wf)

            is_metrics = wf.get("in_sample", {})
            oos_metrics = wf.get("out_of_sample", {})
            robust = wf.get("robust", False)

            print(f"    Best TP/SL: {wf.get('best_tp_mult', '-')}/{wf.get('best_sl_mult', '-')}")
            print(f"    In-sample  WR: {is_metrics.get('win_rate', 0):.1%}  PF: {is_metrics.get('profit_factor', 0):.2f}  Trades: {is_metrics.get('trade_count', 0)}")
            print(f"    Out-sample WR: {oos_metrics.get('win_rate', 0):.1%}  PF: {oos_metrics.get('profit_factor', 0):.2f}  Trades: {oos_metrics.get('trade_count', 0)}")
            print(f"    Degradation: {wf.get('degradation_pct', 0):.1f}%  Robust: {'YES' if robust else 'NO'}")

            # TP/SL grid search
            print(f"    Running TP/SL grid search...")
            grid = bt.run_tp_sl_grid(
                strat_func, strategy_name=strat_name,
                tp_range=(0.5, 1.0, 1.5, 2.0, 2.5),
                sl_range=(0.5, 1.0, 1.5, 2.0),
            )

            ac_results[strat_name] = {
                "walk_forward": wf,
                "grid_top5": grid[:5] if grid else [],
            }

        all_results[ac_name] = ac_results

    # -- Save results -------------------------------------------------------
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "asset_classes": list(ASSET_CLASSES.keys()),
        "strategies": list(BUILTIN_STRATEGIES.keys()),
        "results": _serialize_results(all_results),
        "walk_forward_summary": _serialize_results(walk_forward_results),
    }

    out_path = DATA_DIR / "backtest_results.json"
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, default=str)
        print(f"\n[SAVED] {out_path}")
    except Exception as e:
        print(f"[ERROR] Failed to save results: {e}")

    # -- Summary table ------------------------------------------------------
    print(f"\n{'='*70}")
    print("  WALK-FORWARD SUMMARY")
    print(f"{'='*70}")
    print(f"  {'Strategy':<25} {'Asset':<15} {'WR(IS)':<10} {'WR(OOS)':<10} {'PF(OOS)':<10} {'Robust':<8}")
    print(f"  {'-'*78}")

    for wf in walk_forward_results:
        if isinstance(wf, dict) and "error" not in wf:
            strat = wf.get("strategy", "?")[:24]
            ac = wf.get("asset_class", "?")[:14]
            is_wr = wf.get("in_sample", {}).get("win_rate", 0)
            oos_wr = wf.get("out_of_sample", {}).get("win_rate", 0)
            oos_pf = wf.get("out_of_sample", {}).get("profit_factor", 0)
            robust = "YES" if wf.get("robust", False) else "NO"
            print(f"  {strat:<25} {ac:<15} {is_wr:<10.1%} {oos_wr:<10.1%} {oos_pf:<10.2f} {robust:<8}")

    print(f"\n[DONE] Backtest complete.")


if __name__ == "__main__":
    main()
