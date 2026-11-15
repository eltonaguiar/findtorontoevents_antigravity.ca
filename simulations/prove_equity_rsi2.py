#!/usr/bin/env python3
"""
Simulation 2: Prove Equity RSI-2 Mean Reversion vs SPY Buy-and-Hold
====================================================================
Tests the Connors RSI-2 pullback strategy on SPY — the most promising
EQUITY candidate identified in the live audit (n=78, WR=44.9%, PF=1.11).

Strategy Rules (Connors RSI-2):
  LONG:  RSI(2) < 10 AND close > SMA(200)
  SHORT: RSI(2) > 90 AND close < SMA(200)
  TP:    2× ATR(14)
  SL:    1× ATR(14)
  Max Hold: 10 bars (time exit)
  Cost:  0.05% per side (0.10% round-trip)

This simulation asks: Does this strategy beat simply holding SPY?
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

# ── Configuration ──────────────────────────────────────────────────────────
SYMBOL = "SPY"
START_DATE = "2015-01-01"
END_DATE = "2026-11-14"
TIMEFRAME = "1d"  # Daily bars for swing trading

# Strategy parameters
RSI_PERIOD = 2
SMA_PERIOD = 200
ATR_PERIOD = 14
RSI_LONG_THRESH = 10
RSI_SHORT_THRESH = 90
TP_ATR_MULT = 2.0
SL_ATR_MULT = 1.0
MAX_HOLD_BARS = 10
COMMISSION_PCT = 0.10 / 100  # 0.10% round-trip

OUT_PATH = Path(__file__).parent / "results_equity_rsi2.json"


def compute_rsi(prices: pd.Series, period: int = 2) -> pd.Series:
    """Compute RSI using Wilder's smoothing."""
    delta = prices.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def compute_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Compute Average True Range."""
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period, min_periods=period).mean()
    return atr


def backtest_rsi2(df: pd.DataFrame) -> list[dict]:
    """
    Run RSI-2 backtest on daily bars.
    Returns list of trade dicts.
    """
    trades = []
    df = df.copy()
    df["rsi2"] = compute_rsi(df["Close"], RSI_PERIOD)
    df["sma200"] = df["Close"].rolling(window=SMA_PERIOD, min_periods=SMA_PERIOD).mean()
    df["atr14"] = compute_atr(df["High"], df["Low"], df["Close"], ATR_PERIOD)
    df = df.dropna()

    in_trade = False
    entry_price = 0.0
    entry_date = None
    direction = None
    sl_price = 0.0
    tp_price = 0.0
    bars_held = 0

    for date, row in df.iterrows():
        close = float(row["Close"])
        rsi = float(row["rsi2"])
        sma200 = float(row["sma200"])
        atr = float(row["atr14"])

        # Check exits first
        if in_trade:
            bars_held += 1
            exit_reason = None
            exit_price = close

            if direction == "LONG":
                if close <= sl_price:
                    exit_reason = "SL_HIT"
                elif close >= tp_price:
                    exit_reason = "TP_HIT"
                elif bars_held >= MAX_HOLD_BARS:
                    exit_reason = "TIME_EXIT"
            else:  # SHORT
                if close >= sl_price:
                    exit_reason = "SL_HIT"
                elif close <= tp_price:
                    exit_reason = "TP_HIT"
                elif bars_held >= MAX_HOLD_BARS:
                    exit_reason = "TIME_EXIT"

            if exit_reason:
                pnl_pct = ((exit_price - entry_price) / entry_price * 100) - (COMMISSION_PCT * 100)
                if direction == "SHORT":
                    pnl_pct = -pnl_pct - (COMMISSION_PCT * 100)

                trades.append({
                    "entry_date": entry_date.strftime("%Y-%m-%d"),
                    "exit_date": date.strftime("%Y-%m-%d"),
                    "direction": direction,
                    "entry_price": round(entry_price, 2),
                    "exit_price": round(exit_price, 2),
                    "pnl_pct": round(pnl_pct, 4),
                    "exit_reason": exit_reason,
                    "bars_held": bars_held,
                })
                in_trade = False

        # Check entries (only if not in trade)
        if not in_trade and not pd.isna(rsi) and not pd.isna(sma200) and not pd.isna(atr):
            if rsi < RSI_LONG_THRESH and close > sma200:
                direction = "LONG"
                entry_price = close
                entry_date = date
                sl_price = close - (atr * SL_ATR_MULT)
                tp_price = close + (atr * TP_ATR_MULT)
                bars_held = 0
                in_trade = True
            elif rsi > RSI_SHORT_THRESH and close < sma200:
                direction = "SHORT"
                entry_price = close
                entry_date = date
                sl_price = close + (atr * SL_ATR_MULT)
                tp_price = close - (atr * TP_ATR_MULT)
                bars_held = 0
                in_trade = True

    return trades


def compute_trade_metrics(trades: list[dict]) -> dict:
    """Compute metrics from list of trade dicts."""
    if not trades:
        return {"n": 0, "verdict": "NO_TRADES"}

    pnls = [t["pnl_pct"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    n = len(pnls)
    wr = len(wins) / n if n > 0 else 0
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    pf = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    avg_trade = sum(pnls) / n if n > 0 else 0
    expectancy = avg_trade

    # Sharpe (simplified: daily trade returns)
    mean_pnl = np.mean(pnls)
    std_pnl = np.std(pnls, ddof=1)
    sharpe = (mean_pnl / std_pnl * np.sqrt(252 / 10)) if std_pnl > 0 else 0  # ~10 trades/year

    # Max drawdown from equity curve
    equity = [1.0]
    for p in pnls:
        equity.append(equity[-1] * (1 + p / 100))
    equity = np.array(equity)
    cummax = np.maximum.accumulate(equity)
    dd = (equity - cummax) / cummax
    max_dd = dd.min()

    return {
        "n": n,
        "win_rate": round(wr, 4),
        "profit_factor": round(pf, 4),
        "expectancy_pct": round(expectancy, 4),
        "sharpe_ratio": round(sharpe, 4),
        "max_drawdown": round(max_dd, 4),
        "avg_trade_pct": round(avg_trade, 4),
        "gross_profit_pct": round(gross_profit, 4),
        "gross_loss_pct": round(-gross_loss, 4),
        "total_return_pct": round((equity[-1] / equity[0] - 1) * 100, 4),
    }


def main() -> int:
    print(f"[RSI-2 EQUITY] Fetching {SYMBOL} daily data from {START_DATE} to {END_DATE}...")
    df = yf.download(SYMBOL, start=START_DATE, end=END_DATE, progress=False, auto_adjust=True)
    if df.empty:
        print(f"[ERROR] No data for {SYMBOL}")
        return 1
    print(f"[RSI-2 EQUITY] Loaded {len(df)} bars.")

    trades = backtest_rsi2(df)
    metrics = compute_trade_metrics(trades)

    # Benchmark: SPY buy-and-hold over same period
    first_close = float(df["Close"].iloc[0])
    last_close = float(df["Close"].iloc[-1])
    bench_return = (last_close / first_close - 1) * 100
    bench_annual = ((last_close / first_close) ** (252 / len(df)) - 1) * 100

    # Determine verdict
    deployable = False
    if metrics["n"] >= 30 and metrics["profit_factor"] >= 1.2 and metrics["win_rate"] >= 0.45:
        verdict = "PROMISING — meets minimum thresholds for forward testing"
        deployable = True
    elif metrics["n"] >= 30 and metrics["profit_factor"] >= 1.0:
        verdict = "BREAKEVEN — not deployable but worth refining"
    else:
        verdict = "FAIL — does not meet minimum thresholds"

    results = {
        "simulation": "equity_rsi2_mean_reversion",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "parameters": {
            "symbol": SYMBOL,
            "start_date": START_DATE,
            "end_date": END_DATE,
            "rsi_period": RSI_PERIOD,
            "sma_period": SMA_PERIOD,
            "atr_period": ATR_PERIOD,
            "rsi_long_thresh": RSI_LONG_THRESH,
            "rsi_short_thresh": RSI_SHORT_THRESH,
            "tp_atr_mult": TP_ATR_MULT,
            "sl_atr_mult": SL_ATR_MULT,
            "max_hold_bars": MAX_HOLD_BARS,
            "commission_pct": COMMISSION_PCT,
        },
        "trade_metrics": metrics,
        "benchmark": {
            "symbol": SYMBOL,
            "total_return_pct": round(bench_return, 4),
            "annualized_return_pct": round(bench_annual, 4),
        },
        "excess_return_pct": round(metrics.get("total_return_pct", 0) - bench_return, 4),
        "verdict": verdict,
        "deployable": deployable,
        "forward_test_gates": {
            "n_min": 100,
            "pf_min": 1.5,
            "wr_min": 0.55,
            "sharpe_min": 0.8,
            "max_dd_max": -0.20,
        },
        "rationale": "Connors RSI-2 is one of the most tested mean-reversion systems. If it cannot beat SPY buy-and-hold in a 12-year backtest, no technical system will." if not deployable else "Historical backtest supports forward testing with strict gates.",
    }

    with open(OUT_PATH, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n[RSI-2 EQUITY] Results saved to {OUT_PATH}")
    print(f"  Trades:          {metrics['n']}")
    print(f"  Win Rate:        {metrics['win_rate']:.1%}")
    print(f"  Profit Factor:   {metrics['profit_factor']:.2f}")
    print(f"  Expectancy:      {metrics['expectancy_pct']:.3f}%")
    print(f"  Sharpe:          {metrics['sharpe_ratio']:.2f}")
    print(f"  Max Drawdown:    {metrics['max_drawdown']:.1%}")
    print(f"  Total Return:    {metrics['total_return_pct']:.1f}%")
    print(f"  Benchmark (SPY): {bench_return:.1f}%")
    print(f"  Excess Return:   {results['excess_return_pct']:.1f}%")
    print(f"  Verdict:         {verdict}")
    print(f"  Deployable:      {deployable}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
