"""
CROSS-ASSET VARIANT 1: ConnorsRSI2 Equity Scanner
===================================================
Origin: crypto `stoch-rsi-crypto` is BANNED (0% WR) but the equity variant
`connors_rsi2_scanner` hits 75.7% WR on SPY (p=6e-6, Sharpe 4.84).

Strategy:
  - RSI(2) < 5 for ENTRY (extreme oversold -- tighter than standard RSI(2)<10)
  - RSI(2) > 65 for EXIT (earlier exit captures reversal before fade)
  - 200d SMA uptrend filter (only buy in established uptrends)
  - 3% TP / 2% SL (tightened equity defaults)

Universe: alpha_engine/config.py DEFAULT_UNIVERSE equities

Status: CANDIDATE
"""

import json
import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Allow imports from parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from integration import save_live_pick

# Import DEFAULT_UNIVERSE from config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    from config import DEFAULT_UNIVERSE
except ImportError:
    DEFAULT_UNIVERSE = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
        "JPM", "GS", "WFC", "BAC", "V", "MA",
        "UNH", "JNJ", "PFE", "ABBV", "LLY",
        "WMT", "HD", "MCD", "KO", "PEP", "PG", "COST",
        "BA", "CAT", "CVX", "XOM",
        "DIS", "VZ", "T", "NFLX", "CRM",
    ]

# Filter out ETFs -- this is an equity-only strategy
EQUITY_UNIVERSE = [s for s in DEFAULT_UNIVERSE if s not in ("SPY", "QQQ", "IWM")]

# ----------- Parameters -----------
RSI_PERIOD = 2
RSI_ENTRY_THRESHOLD = 5       # Tighter than standard 10
RSI_EXIT_THRESHOLD = 65       # Exit on mean reversion
SMA_TREND_PERIOD = 200        # Uptrend filter
TP_PCT = 0.03                 # 3% take profit
SL_PCT = 0.02                 # 2% stop loss
COMMISSION = 0.05 / 100       # $0.05/$100
POSITION_SIZE = 0.10          # 10% per position
LOOKBACK_DAYS = 730           # 2 years for backtest
STARTING_CAPITAL = 10_000.0

STRATEGY_META = {
    "name": "connors_rsi2_equity_scanner",
    "status": "CANDIDATE",
    "origin": "cross_asset_mutation",
    "banned_parent": "stoch-rsi-crypto (0% WR crypto)",
    "proven_sibling": "connors_rsi2 (75.7% WR equities)",
    "asset_class": "equity",
    "tp_pct": TP_PCT,
    "sl_pct": SL_PCT,
    "rsi_entry": RSI_ENTRY_THRESHOLD,
    "rsi_exit": RSI_EXIT_THRESHOLD,
}


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Wilder RSI."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Add ConnorsRSI2 signals to dataframe."""
    close = df["Close"]
    df["rsi2"] = _rsi(close, RSI_PERIOD)
    df["sma200"] = close.rolling(SMA_TREND_PERIOD).mean()

    # Entry: RSI(2) < 5 AND price above 200d SMA (uptrend filter)
    df["entry_long"] = (df["rsi2"] < RSI_ENTRY_THRESHOLD) & (close > df["sma200"])
    # Exit: RSI(2) > 65
    df["exit_long"] = df["rsi2"] > RSI_EXIT_THRESHOLD

    return df


def backtest(df: pd.DataFrame) -> dict:
    """Backtest ConnorsRSI2 on a single symbol."""
    df = compute_signals(df)

    equity = STARTING_CAPITAL
    pos = 0
    entry_price = 0.0
    trades = []
    equity_curve = [equity]

    for i in range(SMA_TREND_PERIOD + 1, len(df)):
        row = df.iloc[i]
        price = float(row["Close"])
        rsi_val = float(row["rsi2"]) if not np.isnan(row["rsi2"]) else 50.0

        if pos == 0:
            # Entry
            if row["entry_long"]:
                pos = 1
                entry_price = price
                equity -= equity * POSITION_SIZE * COMMISSION
        else:
            pnl_pct = (price / entry_price - 1) * 100

            # TP hit
            if pnl_pct >= TP_PCT * 100:
                pnl = equity * POSITION_SIZE * TP_PCT
                equity += pnl - (equity * POSITION_SIZE * COMMISSION)
                trades.append({"pnl_pct": TP_PCT * 100, "reason": "TP", "bars": 0})
                pos = 0
            # SL hit
            elif pnl_pct <= -SL_PCT * 100:
                pnl = equity * POSITION_SIZE * (-SL_PCT)
                equity += pnl - (equity * POSITION_SIZE * COMMISSION)
                trades.append({"pnl_pct": -SL_PCT * 100, "reason": "SL", "bars": 0})
                pos = 0
            # RSI exit signal
            elif row["exit_long"]:
                pnl = equity * POSITION_SIZE * (pnl_pct / 100)
                equity += pnl - (equity * POSITION_SIZE * COMMISSION)
                trades.append({"pnl_pct": pnl_pct, "reason": "RSI_EXIT", "bars": 0})
                pos = 0

        equity_curve.append(equity)

    wins = [t for t in trades if t["pnl_pct"] > 0]
    losses = [t for t in trades if t["pnl_pct"] <= 0]
    win_rate = len(wins) / len(trades) * 100 if trades else 0
    avg_win = np.mean([t["pnl_pct"] for t in wins]) if wins else 0
    avg_loss = np.mean([abs(t["pnl_pct"]) for t in losses]) if losses else 1
    profit_factor = (sum(t["pnl_pct"] for t in wins) / sum(abs(t["pnl_pct"]) for t in losses)) if losses and sum(abs(t["pnl_pct"]) for t in losses) > 0 else 0
    total_return = (equity / STARTING_CAPITAL - 1) * 100

    return {
        "trades": len(trades),
        "win_rate": round(win_rate, 1),
        "avg_win_pct": round(float(avg_win), 2),
        "avg_loss_pct": round(float(avg_loss), 2),
        "profit_factor": round(float(profit_factor), 2),
        "total_return_pct": round(total_return, 2),
        "final_equity": round(equity, 2),
        "trade_details": trades,
    }


def run_backtest_all() -> dict:
    """Run backtest across all equity universe symbols."""
    try:
        import yfinance as yf
    except ImportError:
        return {"error": "yfinance not installed", "symbols": {}}

    results = {}
    agg_trades = 0
    agg_wins = 0

    for sym in EQUITY_UNIVERSE:
        try:
            start_date = (datetime.now() - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")
            df = yf.download(sym, start=start_date, interval="1d", progress=False)
            if df.empty or len(df) < SMA_TREND_PERIOD + 50:
                continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            res = backtest(df)
            results[sym] = res
            agg_trades += res["trades"]
            agg_wins += int(res["trades"] * res["win_rate"] / 100)

            # Check for live signal on last bar
            df_sig = compute_signals(df)
            last = df_sig.iloc[-1]
            if last["entry_long"]:
                price = float(last["Close"])
                tp = price * (1 + TP_PCT)
                sl = price * (1 - SL_PCT)
                save_live_pick(
                    strategy_name="connors_rsi2_equity_scanner",
                    symbol=sym,
                    signal=1,
                    entry_price=price,
                    tp=tp,
                    sl=sl,
                    confidence=0.75,
                    category="equity",
                )
        except Exception as e:
            results[sym] = {"error": str(e)}

    agg_wr = (agg_wins / agg_trades * 100) if agg_trades > 0 else 0

    return {
        "strategy": "connors_rsi2_equity_scanner",
        "status": "CANDIDATE",
        "asset_class": "equity",
        "universe_size": len(EQUITY_UNIVERSE),
        "symbols_tested": len(results),
        "aggregate_trades": agg_trades,
        "aggregate_win_rate": round(agg_wr, 1),
        "parameters": {
            "rsi_period": RSI_PERIOD,
            "rsi_entry": RSI_ENTRY_THRESHOLD,
            "rsi_exit": RSI_EXIT_THRESHOLD,
            "sma_trend": SMA_TREND_PERIOD,
            "tp_pct": TP_PCT,
            "sl_pct": SL_PCT,
        },
        "per_symbol": results,
    }


if __name__ == "__main__":
    result = run_backtest_all()
    print(f"\n=== ConnorsRSI2 Equity Scanner ===")
    print(f"Symbols tested: {result.get('symbols_tested', 0)}")
    print(f"Total trades: {result.get('aggregate_trades', 0)}")
    print(f"Aggregate WR: {result.get('aggregate_win_rate', 0):.1f}%")
    for sym, r in result.get("per_symbol", {}).items():
        if "error" not in r:
            print(f"  {sym}: WR={r['win_rate']:.1f}%, Trades={r['trades']}, Return={r['total_return_pct']:.1f}%")
