"""
Backtest Round 3 baby strategies (daily yfinance).

New batch: equity_two_day_rsi_reversal, commodity_trend_pullback_rsi,
crypto_atr_ratio_expansion_long, forex_inside_day_breakout.

Run: python backtest_batch_round3.py
Output: baby_strategies/batch_round3_backtest_results.json
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import yfinance as yf
except ImportError as exc:
    raise SystemExit("pip install yfinance") from exc

from commodity_trend_pullback_rsi import CommodityTrendPullbackRsiStrategy
from crypto_atr_ratio_expansion_long import CryptoAtrRatioExpansionLongStrategy
from equity_two_day_rsi_reversal import EquityTwoDayRsiReversalStrategy
from forex_inside_day_breakout import ForexInsideDayBreakoutStrategy


@dataclass
class BacktestMetrics:
    symbol: str
    asset_class: str
    strategy: str
    trades: int
    win_rate: float
    profit_factor: float
    total_return_pct: float
    avg_trade_pct: float
    max_drawdown_pct: float


def _to_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if isinstance(out.columns, pd.MultiIndex):
        out.columns = [str(c[0]).lower() for c in out.columns]
    else:
        out.columns = [str(c).lower() for c in out.columns]
    out = out[[c for c in ["open", "high", "low", "close", "volume"] if c in out.columns]]
    return out.dropna()


def _simulate(df: pd.DataFrame, signals: list[dict]) -> BacktestMetrics:
    if not signals:
        return BacktestMetrics("", "", "", 0, 0.0, 0.0, 0.0, 0.0, 0.0)

    close = df["close"].astype(float).to_numpy()
    high = df["high"].astype(float).to_numpy()
    low = df["low"].astype(float).to_numpy()

    rets: list[float] = []
    equity = [1.0]
    next_allowed = 0

    for sig in sorted(signals, key=lambda x: int(x.get("bar_index", 0))):
        i = int(sig.get("bar_index", 0))
        if i >= len(df) - 2 or i < next_allowed:
            continue

        side = str(sig.get("side", "LONG")).upper()
        entry = float(sig["entry_price"])
        tp = float(sig["take_profit"])
        sl = float(sig["stop_loss"])
        max_hold = int(sig.get("max_hold_days", 10))

        exit_px = close[min(i + max_hold, len(df) - 1)]
        exit_idx = min(i + max_hold, len(df) - 1)

        for j in range(i + 1, min(i + max_hold + 1, len(df))):
            if side == "LONG":
                if high[j] >= tp:
                    exit_px = tp
                    exit_idx = j
                    break
                if low[j] <= sl:
                    exit_px = sl
                    exit_idx = j
                    break
            else:
                if low[j] <= tp:
                    exit_px = tp
                    exit_idx = j
                    break
                if high[j] >= sl:
                    exit_px = sl
                    exit_idx = j
                    break

        if side == "LONG":
            ret = (exit_px - entry) / max(1e-9, entry)
        else:
            ret = (entry - exit_px) / max(1e-9, entry)

        rets.append(float(ret))
        equity.append(equity[-1] * (1.0 + ret))
        next_allowed = exit_idx + 1

    if not rets:
        return BacktestMetrics("", "", "", 0, 0.0, 0.0, 0.0, 0.0, 0.0)

    wins = [r for r in rets if r > 0]
    losses = [r for r in rets if r <= 0]
    win_rate = 100.0 * len(wins) / len(rets)
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = gross_win / gross_loss if gross_loss > 0 else 999.0
    total_return_pct = (equity[-1] - 1.0) * 100.0
    avg_trade_pct = float(np.mean(rets) * 100.0)
    eq = np.array(equity)
    run_max = np.maximum.accumulate(eq)
    drawdown = (eq - run_max) / np.maximum(run_max, 1e-9)
    max_drawdown_pct = abs(float(drawdown.min() * 100.0))

    return BacktestMetrics(
        symbol="",
        asset_class="",
        strategy="",
        trades=len(rets),
        win_rate=round(win_rate, 2),
        profit_factor=round(float(profit_factor), 2),
        total_return_pct=round(float(total_return_pct), 2),
        avg_trade_pct=round(avg_trade_pct, 4),
        max_drawdown_pct=round(float(max_drawdown_pct), 2),
    )


def _download(symbol: str, years: str = "10y") -> pd.DataFrame:
    df = yf.download(symbol, period=years, interval="1d", auto_adjust=False, progress=False)
    if df is None or len(df) < 300:
        return pd.DataFrame()
    return _to_ohlcv(df)


def run(crypto_symbols: list[str] | None = None) -> dict:
    crypto_syms = crypto_symbols or ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD"]
    universe: dict[str, dict] = {
        "CRYPTO": {
            "symbols": crypto_syms,
            "strategy": CryptoAtrRatioExpansionLongStrategy(),
        },
        "FOREX": {
            "symbols": ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X"],
            "strategy": ForexInsideDayBreakoutStrategy(),
        },
        "EQUITY": {
            "symbols": ["SPY", "QQQ", "NVDA", "MSFT"],
            "strategy": EquityTwoDayRsiReversalStrategy(),
        },
        "COMMODITY": {
            "symbols": ["GLD", "SLV", "DBC", "USO"],
            "strategy": CommodityTrendPullbackRsiStrategy(),
        },
    }

    rows: list[dict] = []
    for asset_class, cfg in universe.items():
        strat = cfg["strategy"]
        for symbol in cfg["symbols"]:
            df = _download(symbol)
            if df.empty:
                continue
            signals = strat.generate_signals(df, symbol)
            m = _simulate(df, signals)
            if m.trades == 0:
                continue
            m.symbol = symbol
            m.asset_class = asset_class
            m.strategy = strat.NAME
            d = asdict(m)
            d["batch"] = "round3_apr2026"
            rows.append(d)

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "batch": "round3_apr2026",
        "results": rows,
    }
    out_path = Path(__file__).resolve().parent / "batch_round3_backtest_results.json"
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    print(f"\nSaved: {out_path}")
    return payload


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--crypto-mode",
        choices=("all", "btc_only"),
        default="all",
        help="all=BTC,ETH,SOL,BNB; btc_only=BTC-USD only.",
    )
    args = ap.parse_args()
    crypto_list = ["BTC-USD"] if args.crypto_mode == "btc_only" else None
    run(crypto_symbols=crypto_list)
