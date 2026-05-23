#!/usr/bin/env python3
"""
Forex Smart Picks — Backtest Engine
====================================
Downloads 1 year of daily data for 10 forex pairs via yfinance,
backtests 6 academic strategies with ATR-based TP/SL, then evaluates
4 portfolio variants (A/B/C/D) and ranks by Sharpe ratio.

Strategies:
  1. carry_trade_momentum     — Lustig & Verdelhan 2007
  2. forex_rsi2_mean_reversion — Connors RSI-2 (68% WR academic)
  3. forex_mean_reversion_200d — Poterba & Summers
  4. forex_tsmom_12m           — Jegadeesh-Titman cross-sectional momentum
  5. cta_tsmom_blend           — TSMOM 1/3/12 month blend
  6. ig_contrarian_sentiment   — IG client sentiment contrarian (proxy: RSI extreme)

Portfolio Variants:
  A: RSI-filtered (RSI<40 BUY, RSI>60 SELL)
  B: Volume-confirmed (volume > 1.5x 20-day avg)
  C: Multi-timeframe (daily + weekly trend agree)
  D: Carry-only (AUDJPY, GBPJPY, USDJPY only)
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import yfinance as yf
except ImportError:
    print("ERROR: yfinance not installed. Run: pip install yfinance")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PAIRS = [
    "EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X",
    "NZDUSD=X", "USDCHF=X", "EURJPY=X", "GBPJPY=X", "AUDJPY=X",
]

CARRY_YIELD_DIFF = {
    "EURUSD=X": -0.5, "GBPUSD=X": 0.25, "USDJPY=X": 4.5,
    "AUDUSD=X": 0.75, "USDCAD=X": 0.5, "NZDUSD=X": 1.0,
    "USDCHF=X": 3.0, "EURJPY=X": 4.0, "GBPJPY=X": 4.75,
    "AUDJPY=X": 5.25,
}

CARRY_ONLY_PAIRS = {"AUDJPY=X", "GBPJPY=X", "USDJPY=X"}

TP_MULT = 1.2
SL_MULT = 1.0
TP_CAP_PCT = 0.008   # 0.8%
SL_CAP_PCT = 0.005   # 0.5%
MAX_HOLD_DAYS = 10

OUTPUT_DIR = Path(__file__).parent / "data"


# ---------------------------------------------------------------------------
# Indicators (pure numpy/pandas)
# ---------------------------------------------------------------------------
def calc_sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period, min_periods=period).mean()


def calc_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(window=period, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).rolling(window=period, min_periods=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def calc_atr(high: pd.Series, low: pd.Series, close: pd.Series,
             period: int = 14) -> pd.Series:
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period, min_periods=period).mean()


def calc_adx(high: pd.Series, low: pd.Series, close: pd.Series,
             period: int = 14) -> pd.Series:
    """Simplified ADX."""
    plus_dm = high.diff().clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)
    # Zero out when the other is larger
    plus_dm[plus_dm < minus_dm] = 0
    minus_dm[minus_dm < plus_dm] = 0
    atr_vals = calc_atr(high, low, close, period)
    plus_di = 100 * calc_sma(plus_dm, period) / atr_vals.replace(0, np.nan)
    minus_di = 100 * calc_sma(minus_dm, period) / atr_vals.replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return calc_sma(dx, period)


def calc_weekly_sma(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Resample to weekly and compute SMA, then reindex to daily."""
    weekly = df["Close"].resample("W-FRI").last().dropna()
    weekly_sma = calc_sma(weekly, period)
    return weekly_sma.reindex(df.index, method="ffill")


# ---------------------------------------------------------------------------
# TP/SL computation
# ---------------------------------------------------------------------------
def compute_tp_sl(price: float, atr_val: float, direction: str):
    """Return (tp, sl) based on direction, ATR, and caps."""
    tp_dist = min(TP_MULT * atr_val, price * TP_CAP_PCT)
    sl_dist = min(SL_MULT * atr_val, price * SL_CAP_PCT)
    if direction == "BUY":
        return price + tp_dist, price - sl_dist
    else:
        return price - tp_dist, price + sl_dist


# ---------------------------------------------------------------------------
# Trade simulator
# ---------------------------------------------------------------------------
def simulate_trade(df: pd.DataFrame, entry_idx: int, direction: str,
                   tp: float, sl: float) -> dict:
    """Simulate a single trade from entry_idx forward, max MAX_HOLD_DAYS bars."""
    entry_price = float(df["Close"].iloc[entry_idx])
    for offset in range(1, MAX_HOLD_DAYS + 1):
        bar_idx = entry_idx + offset
        if bar_idx >= len(df):
            break
        h = float(df["High"].iloc[bar_idx])
        l = float(df["Low"].iloc[bar_idx])
        c = float(df["Close"].iloc[bar_idx])

        if direction == "BUY":
            if l <= sl:
                pnl = (sl - entry_price) / entry_price
                return {"pnl": pnl, "exit": "SL", "bars": offset}
            if h >= tp:
                pnl = (tp - entry_price) / entry_price
                return {"pnl": pnl, "exit": "TP", "bars": offset}
        else:  # SELL
            if h >= sl:
                pnl = (entry_price - sl) / entry_price
                return {"pnl": pnl, "exit": "SL", "bars": offset}
            if l <= tp:
                pnl = (entry_price - tp) / entry_price
                return {"pnl": pnl, "exit": "TP", "bars": offset}

    # Max hold — exit at close
    exit_idx = min(entry_idx + MAX_HOLD_DAYS, len(df) - 1)
    exit_price = float(df["Close"].iloc[exit_idx])
    if direction == "BUY":
        pnl = (exit_price - entry_price) / entry_price
    else:
        pnl = (entry_price - exit_price) / entry_price
    return {"pnl": pnl, "exit": "TIMEOUT", "bars": exit_idx - entry_idx}


# ---------------------------------------------------------------------------
# Strategy signal generators — return list of (bar_index, direction)
# ---------------------------------------------------------------------------
def signals_carry_trade(df: pd.DataFrame, symbol: str) -> list[tuple[int, str]]:
    """Carry trade: go long high-carry, short low-carry, with trend filter."""
    carry = CARRY_YIELD_DIFF.get(symbol, 0)
    close = df["Close"]
    sma50 = calc_sma(close, 50)
    rsi14 = calc_rsi(close, 14)
    signals = []
    for i in range(60, len(df) - MAX_HOLD_DAYS):
        mom_20d = close.iloc[i] / close.iloc[i - 20] - 1
        score = carry + mom_20d * 10
        direction = "BUY" if score > 0.5 else ("SELL" if score < -0.5 else None)
        if direction is None:
            continue
        # Trend filter
        if direction == "BUY" and close.iloc[i] < sma50.iloc[i]:
            continue
        if direction == "SELL" and close.iloc[i] > sma50.iloc[i]:
            continue
        # RSI filter
        r = rsi14.iloc[i]
        if direction == "BUY" and r > 65:
            continue
        if direction == "SELL" and r < 35:
            continue
        signals.append((i, direction))
    return signals


def signals_rsi2_mean_reversion(df: pd.DataFrame, symbol: str) -> list[tuple[int, str]]:
    """Connors RSI-2 mean reversion: BUY when RSI(2) < 10, SELL > 90."""
    close = df["Close"]
    rsi2 = calc_rsi(close, 2)
    sma200 = calc_sma(close, 200)
    signals = []
    for i in range(200, len(df) - MAX_HOLD_DAYS):
        r = rsi2.iloc[i]
        if pd.isna(r):
            continue
        # Only trade in direction of long-term trend
        above_200 = close.iloc[i] > sma200.iloc[i]
        if r < 10 and above_200:
            signals.append((i, "BUY"))
        elif r > 90 and not above_200:
            signals.append((i, "SELL"))
    return signals


def signals_mean_reversion_200d(df: pd.DataFrame, symbol: str) -> list[tuple[int, str]]:
    """Mean reversion to 200-day SMA when stretched > 2 z-score."""
    close = df["Close"]
    sma200 = calc_sma(close, 200)
    signals = []
    for i in range(200, len(df) - MAX_HOLD_DAYS):
        if pd.isna(sma200.iloc[i]):
            continue
        deviation = (close.iloc[i] - sma200.iloc[i]) / sma200.iloc[i]
        if deviation < -0.02:  # 2% below 200d SMA
            signals.append((i, "BUY"))
        elif deviation > 0.02:  # 2% above 200d SMA
            signals.append((i, "SELL"))
    return signals


def signals_tsmom_12m(df: pd.DataFrame, symbol: str) -> list[tuple[int, str]]:
    """Time-series momentum: 12-month return direction."""
    close = df["Close"]
    signals = []
    for i in range(252, len(df) - MAX_HOLD_DAYS):
        ret_12m = close.iloc[i] / close.iloc[i - 252] - 1
        if ret_12m > 0.01:
            signals.append((i, "BUY"))
        elif ret_12m < -0.01:
            signals.append((i, "SELL"))
    return signals


def signals_cta_tsmom_blend(df: pd.DataFrame, symbol: str) -> list[tuple[int, str]]:
    """CTA-style TSMOM blend: 1/3/12 month momentum vote."""
    close = df["Close"]
    signals = []
    for i in range(252, len(df) - MAX_HOLD_DAYS):
        ret_1m = close.iloc[i] / close.iloc[i - 21] - 1
        ret_3m = close.iloc[i] / close.iloc[i - 63] - 1
        ret_12m = close.iloc[i] / close.iloc[i - 252] - 1
        vote = (1 if ret_1m > 0 else -1) + (1 if ret_3m > 0 else -1) + (1 if ret_12m > 0 else -1)
        if vote >= 2:
            signals.append((i, "BUY"))
        elif vote <= -2:
            signals.append((i, "SELL"))
    return signals


def signals_ig_contrarian(df: pd.DataFrame, symbol: str) -> list[tuple[int, str]]:
    """IG contrarian sentiment proxy: extreme RSI(14) as crowd proxy."""
    close = df["Close"]
    rsi14 = calc_rsi(close, 14)
    sma50 = calc_sma(close, 50)
    signals = []
    for i in range(50, len(df) - MAX_HOLD_DAYS):
        r = rsi14.iloc[i]
        if pd.isna(r):
            continue
        # Contrarian: when crowd is extremely bearish (RSI<25), go long
        # when crowd is extremely bullish (RSI>75), go short
        # But only with trend confirmation from 50d SMA direction
        sma_slope = (sma50.iloc[i] - sma50.iloc[i - 5]) / sma50.iloc[i - 5] if i >= 55 else 0
        if r < 25 and sma_slope > 0:
            signals.append((i, "BUY"))
        elif r > 75 and sma_slope < 0:
            signals.append((i, "SELL"))
    return signals


STRATEGIES = {
    "carry_trade_momentum": signals_carry_trade,
    "forex_rsi2_mean_reversion": signals_rsi2_mean_reversion,
    "forex_mean_reversion_200d": signals_mean_reversion_200d,
    "forex_tsmom_12m": signals_tsmom_12m,
    "cta_tsmom_blend": signals_cta_tsmom_blend,
    "ig_contrarian_sentiment": signals_ig_contrarian,
}


# ---------------------------------------------------------------------------
# Portfolio filter functions
# ---------------------------------------------------------------------------
def filter_portfolio_a(df: pd.DataFrame, idx: int, direction: str) -> bool:
    """Portfolio A: RSI-filtered. BUY only when RSI(14)<40, SELL when RSI(14)>60."""
    rsi14 = calc_rsi(df["Close"], 14)
    r = rsi14.iloc[idx]
    if pd.isna(r):
        return False
    if direction == "BUY":
        return r < 40
    else:
        return r > 60


def filter_portfolio_b(df: pd.DataFrame, idx: int, direction: str) -> bool:
    """Portfolio B: Volume-confirmed. Volume > 1.5x 20-day average."""
    if "Volume" not in df.columns:
        return True  # no volume data — pass through
    vol = df["Volume"]
    avg_vol = vol.rolling(20, min_periods=10).mean()
    if pd.isna(avg_vol.iloc[idx]) or avg_vol.iloc[idx] == 0:
        return True
    return vol.iloc[idx] > 1.5 * avg_vol.iloc[idx]


def filter_portfolio_c(df: pd.DataFrame, idx: int, direction: str) -> bool:
    """Portfolio C: Multi-timeframe. Daily SMA(50) and weekly SMA(20) agree on trend."""
    close = df["Close"]
    sma50 = calc_sma(close, 50)
    if pd.isna(sma50.iloc[idx]):
        return False
    daily_bullish = close.iloc[idx] > sma50.iloc[idx]

    # Weekly trend: resample
    weekly = close.resample("W-FRI").last().dropna()
    weekly_sma20 = calc_sma(weekly, 20)
    if len(weekly_sma20.dropna()) == 0:
        return False
    # Find the latest weekly value at or before the current date
    current_date = df.index[idx]
    weekly_before = weekly_sma20[:current_date]
    if len(weekly_before.dropna()) == 0:
        return False
    weekly_bullish = weekly.iloc[-1] > weekly_before.dropna().iloc[-1]

    if direction == "BUY":
        return daily_bullish and weekly_bullish
    else:
        return (not daily_bullish) and (not weekly_bullish)


def filter_portfolio_d(df: pd.DataFrame, idx: int, direction: str,
                       symbol: str = "") -> bool:
    """Portfolio D: Carry-only pairs (AUDJPY, GBPJPY, USDJPY)."""
    return symbol in CARRY_ONLY_PAIRS


PORTFOLIO_FILTERS = {
    "A_RSI_filtered": filter_portfolio_a,
    "B_Volume_confirmed": filter_portfolio_b,
    "C_Multi_timeframe": filter_portfolio_c,
    "D_Carry_only": filter_portfolio_d,
}


# ---------------------------------------------------------------------------
# Backtest runner
# ---------------------------------------------------------------------------
def run_backtest(data: dict[str, pd.DataFrame]) -> dict:
    """Run all strategies x all pairs x all portfolio filters. Return results."""
    results = {
        "strategies": {},
        "portfolios": {},
        "raw_trades": [],
        "meta": {
            "pairs": PAIRS,
            "tp_mult": TP_MULT,
            "sl_mult": SL_MULT,
            "tp_cap_pct": TP_CAP_PCT,
            "sl_cap_pct": SL_CAP_PCT,
            "max_hold_days": MAX_HOLD_DAYS,
            "run_date": datetime.utcnow().isoformat() + "Z",
        },
    }

    all_trades = []  # (strategy, symbol, idx, direction, trade_result)

    # Generate all signals
    for strat_name, strat_fn in STRATEGIES.items():
        strat_trades = []
        for symbol in PAIRS:
            df = data.get(symbol)
            if df is None or len(df) < 260:
                continue
            signals = strat_fn(df, symbol)
            atr_series = calc_atr(df["High"], df["Low"], df["Close"], 14)

            # De-duplicate: min 5 bars between entries on same pair
            last_entry = -999
            for idx, direction in signals:
                if idx - last_entry < 5:
                    continue
                if pd.isna(atr_series.iloc[idx]):
                    continue
                atr_val = float(atr_series.iloc[idx])
                price = float(df["Close"].iloc[idx])
                tp, sl = compute_tp_sl(price, atr_val, direction)
                result = simulate_trade(df, idx, direction, tp, sl)
                trade = {
                    "strategy": strat_name,
                    "symbol": symbol,
                    "idx": idx,
                    "date": str(df.index[idx].date()),
                    "direction": direction,
                    "entry_price": price,
                    "tp": tp,
                    "sl": sl,
                    "atr": atr_val,
                    **result,
                }
                strat_trades.append(trade)
                all_trades.append(trade)
                last_entry = idx

        # Strategy-level stats
        results["strategies"][strat_name] = _compute_stats(strat_trades)

    # Portfolio-level stats
    for port_name, port_filter in PORTFOLIO_FILTERS.items():
        port_trades = []
        for t in all_trades:
            symbol = t["symbol"]
            df = data.get(symbol)
            if df is None:
                continue
            idx = t["idx"]
            direction = t["direction"]
            if port_name == "D_Carry_only":
                if port_filter(df, idx, direction, symbol=symbol):
                    port_trades.append(t)
            else:
                if port_filter(df, idx, direction):
                    port_trades.append(t)
        results["portfolios"][port_name] = _compute_stats(port_trades)

    # Also compute "all trades" baseline
    results["portfolios"]["ALL_unfiltered"] = _compute_stats(all_trades)

    # Rank portfolios by Sharpe
    ranking = []
    for pname, pstats in results["portfolios"].items():
        ranking.append({
            "portfolio": pname,
            "sharpe": pstats["sharpe"],
            "win_rate": pstats["win_rate"],
            "profit_factor": pstats["profit_factor"],
            "total_pnl_pct": pstats["total_pnl_pct"],
            "num_trades": pstats["num_trades"],
        })
    ranking.sort(key=lambda x: x["sharpe"], reverse=True)
    results["portfolio_ranking"] = ranking

    # Save top 20 trades for reference
    results["sample_trades"] = sorted(all_trades, key=lambda t: t["pnl"], reverse=True)[:20]

    return results


def _compute_stats(trades: list[dict]) -> dict:
    """Compute WR, PF, Sharpe, total PnL from a list of trades."""
    if not trades:
        return {
            "num_trades": 0, "win_rate": 0, "profit_factor": 0,
            "sharpe": -999, "total_pnl_pct": 0,
            "avg_pnl_pct": 0, "max_dd_pct": 0,
            "avg_bars": 0, "tp_exits": 0, "sl_exits": 0, "timeout_exits": 0,
        }
    pnls = [t["pnl"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    wr = len(wins) / len(pnls) if pnls else 0
    gross_profit = sum(wins) if wins else 0
    gross_loss = abs(sum(losses)) if losses else 0.0001
    pf = gross_profit / gross_loss if gross_loss > 0 else 99.0
    total_pnl = sum(pnls)
    avg_pnl = np.mean(pnls)
    sharpe = (np.mean(pnls) / np.std(pnls) * np.sqrt(252)) if np.std(pnls) > 0 else 0

    # Max drawdown
    cum = np.cumsum(pnls)
    peak = np.maximum.accumulate(cum)
    dd = cum - peak
    max_dd = float(np.min(dd)) if len(dd) > 0 else 0

    tp_exits = sum(1 for t in trades if t["exit"] == "TP")
    sl_exits = sum(1 for t in trades if t["exit"] == "SL")
    timeout_exits = sum(1 for t in trades if t["exit"] == "TIMEOUT")
    avg_bars = np.mean([t["bars"] for t in trades])

    # Per-strategy breakdown
    by_strategy = {}
    for t in trades:
        s = t["strategy"]
        if s not in by_strategy:
            by_strategy[s] = []
        by_strategy[s].append(t["pnl"])
    strategy_breakdown = {}
    for s, spnls in by_strategy.items():
        sw = [p for p in spnls if p > 0]
        strategy_breakdown[s] = {
            "trades": len(spnls),
            "wr": len(sw) / len(spnls) if spnls else 0,
            "total_pnl": sum(spnls),
        }

    return {
        "num_trades": len(trades),
        "win_rate": round(wr, 4),
        "profit_factor": round(pf, 4),
        "sharpe": round(sharpe, 4),
        "total_pnl_pct": round(total_pnl * 100, 4),
        "avg_pnl_pct": round(avg_pnl * 100, 6),
        "max_dd_pct": round(max_dd * 100, 4),
        "avg_bars": round(avg_bars, 2),
        "tp_exits": tp_exits,
        "sl_exits": sl_exits,
        "timeout_exits": timeout_exits,
        "strategy_breakdown": strategy_breakdown,
    }


# ---------------------------------------------------------------------------
# Data download
# ---------------------------------------------------------------------------
def download_data() -> dict[str, pd.DataFrame]:
    """Download 1y+ of daily data for all pairs."""
    end = datetime.utcnow()
    start = end - timedelta(days=400)  # >1 year for 252 trading days
    print(f"Downloading forex data from {start.date()} to {end.date()}...")

    data = {}
    for pair in PAIRS:
        try:
            df = yf.download(pair, start=start.strftime("%Y-%m-%d"),
                             end=end.strftime("%Y-%m-%d"),
                             progress=False, auto_adjust=True)
            if df is not None and len(df) > 100:
                # Flatten multi-level columns if present
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                data[pair] = df
                print(f"  {pair}: {len(df)} bars")
            else:
                print(f"  {pair}: INSUFFICIENT DATA ({len(df) if df is not None else 0} bars)")
        except Exception as e:
            print(f"  {pair}: ERROR - {e}")
    return data


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("FOREX SMART PICKS — BACKTEST ENGINE")
    print("=" * 70)

    data = download_data()
    if len(data) < 5:
        print("FATAL: Not enough data downloaded. Exiting.")
        sys.exit(1)

    print(f"\nRunning backtest on {len(data)} pairs...")
    results = run_backtest(data)

    # Print strategy results
    print("\n" + "=" * 70)
    print("STRATEGY RESULTS")
    print("=" * 70)
    print(f"{'Strategy':<30} {'Trades':>7} {'WR%':>7} {'PF':>7} {'Sharpe':>8} {'PnL%':>8}")
    print("-" * 70)
    for sname, stats in sorted(results["strategies"].items(),
                                key=lambda x: x[1]["sharpe"], reverse=True):
        print(f"{sname:<30} {stats['num_trades']:>7} "
              f"{stats['win_rate']*100:>6.1f}% {stats['profit_factor']:>7.2f} "
              f"{stats['sharpe']:>8.2f} {stats['total_pnl_pct']:>7.2f}%")

    # Print portfolio results
    print("\n" + "=" * 70)
    print("PORTFOLIO RANKING (by Sharpe)")
    print("=" * 70)
    print(f"{'#':>2} {'Portfolio':<25} {'Trades':>7} {'WR%':>7} {'PF':>7} {'Sharpe':>8} {'PnL%':>8}")
    print("-" * 70)
    for rank, p in enumerate(results["portfolio_ranking"], 1):
        print(f"{rank:>2} {p['portfolio']:<25} {p['num_trades']:>7} "
              f"{p['win_rate']*100:>6.1f}% {p['profit_factor']:>7.2f} "
              f"{p['sharpe']:>8.2f} {p['total_pnl_pct']:>7.2f}%")

    winner = results["portfolio_ranking"][0]
    print(f"\n*** WINNER: {winner['portfolio']} (Sharpe: {winner['sharpe']:.2f}) ***")

    # Save results
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "forex_backtest_results.json"

    # Make JSON-serializable
    clean_results = json.loads(json.dumps(results, default=str))
    with open(output_path, "w") as f:
        json.dump(clean_results, f, indent=2)
    print(f"\nResults saved to {output_path}")

    return results


if __name__ == "__main__":
    main()
