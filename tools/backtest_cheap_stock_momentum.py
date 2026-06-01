#!/usr/bin/env python3
"""Backtest CHEAP_STOCKS: cross-sectional momentum on liquid $2–$12 names.

Universe: 45 liquid US tickers that frequently trade in the cheap band.
Signal: 63-day momentum, price in [$2, $12], avg vol > 500k (20d).
Hold: top-5 equal-weight, 21 trading days.

Output: audit_dashboard/data/cheap_stock_momentum_backtest.json
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import numpy as np
    import pandas as pd
    import yfinance as yf
except ImportError as exc:
    print(f"ERROR: {exc}", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "audit_dashboard/data/cheap_stock_momentum_backtest.json"

# Liquid names that often sit in $2–$15 (not static penny-only)
UNIVERSE = [
    "F", "NIO", "SNAP", "SOFI", "PLUG", "SOUN", "LCID", "RIVN", "HOOD", "PLTR",
    "AMD", "INTC", "AAL", "DAL", "UAL", "CCL", "NCLH", "RCL", "MARA", "RIOT",
    "COIN", "MSTR", "CLSK", "BITF", "HUT", "WBD", "PARA", "IONQ", "RGTI", "QBTS",
    "OPEN", "CVNA", "UPST", "AFRM", "PATH", "DKNG", "PENN", "CHPT", "BLNK", "RUN",
    "FSLR", "ENPH", "SEDG", "XPEV", "LI",
]

PRICE_MIN, PRICE_MAX = 2.0, 12.0
MOM_DAYS = 63
REBAL_DAYS = 21
TOP_N = 5
MIN_AVG_VOL = 500_000


def fetch_data(start: str = "2018-01-01", end: str | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    end = end or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    raw = yf.download(UNIVERSE, start=start, end=end, interval="1d", progress=False, auto_adjust=True)
    if raw is None or raw.empty:
        raise RuntimeError("no price data")
    if isinstance(raw.columns, pd.MultiIndex):
        close = raw["Close"].copy()
        vol = raw["Volume"].copy()
    else:
        close = raw[["Close"]].copy()
        vol = raw[["Volume"]].copy()
    return close.dropna(how="all"), vol.dropna(how="all")


def run_backtest(close: pd.DataFrame, volume: pd.DataFrame) -> dict:
    trades: list[float] = []
    history: list[dict] = []
    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    win = loss = 0
    win_pnl = loss_pnl = 0.0

    start_i = MOM_DAYS + 25
    for i in range(start_i, len(close) - REBAL_DAYS, REBAL_DAYS):
        scored: list[tuple[float, str]] = []
        for sym in close.columns:
            c = close[sym].iloc[: i + 1].dropna()
            v = volume[sym].iloc[: i + 1].dropna() if sym in volume.columns else None
            if len(c) < MOM_DAYS + 5:
                continue
            px = float(c.iloc[-1])
            if not (PRICE_MIN <= px <= PRICE_MAX):
                continue
            if v is not None and len(v) >= 20:
                if float(v.tail(20).mean()) < MIN_AVG_VOL:
                    continue
            ago = float(c.iloc[-MOM_DAYS - 1])
            if ago <= 0:
                continue
            mom = (px - ago) / ago
            if mom > 0:
                scored.append((mom, sym))
        if len(scored) < TOP_N:
            continue
        scored.sort(reverse=True)
        picks = [s for _, s in scored[:TOP_N]]
        end_i = min(i + REBAL_DAYS, len(close) - 1)
        rets = []
        for sym in picks:
            r = float(close[sym].iloc[end_i] / close[sym].iloc[i] - 1)
            if not np.isnan(r):
                rets.append(r)
        if not rets:
            continue
        period_ret = float(np.mean(rets))
        trades.append(period_ret)
        equity *= 1 + period_ret
        peak = max(peak, equity)
        max_dd = max(max_dd, (peak - equity) / peak)
        if period_ret > 0:
            win += 1
            win_pnl += period_ret
        elif period_ret < 0:
            loss += 1
            loss_pnl += abs(period_ret)
        history.append({
            "period": str(close.index[i].date()),
            "picks": picks,
            "period_ret_pct": round(period_ret * 100, 3),
        })

    n = len(trades)
    wr = (win / n * 100) if n else 0.0
    pf = (win_pnl / loss_pnl) if loss_pnl > 0 else (float("inf") if win_pnl > 0 else 0.0)
    total_pnl = (equity - 1) * 100
    return {
        "strategy": "cheap_stock_cross_momentum",
        "asset_class": "CHEAP_STOCKS",
        "universe_size": len(UNIVERSE),
        "price_band": [PRICE_MIN, PRICE_MAX],
        "n_trades": n,
        "win_rate_pct": round(wr, 2),
        "profit_factor": round(pf, 4) if pf != float("inf") else 999.0,
        "total_return_pct": round(total_pnl, 2),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "avg_period_ret_pct": round(float(np.mean(trades)) * 100, 3) if trades else 0,
        "history_sample": history[-5:],
    }


def main() -> None:
    close, vol = fetch_data()
    result = run_backtest(close, vol)
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
