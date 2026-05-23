"""Backtest for bond_connors_rsi2 strategy (Connors RSI-2 on TLT/IEF/LQD).

Entry: RSI(2) < 10 AND price > SMA(200)
Exit:  first daily close >= TP (+2%) OR close <= SL (max(-2%, SMA200))
Direction: LONG only.
Capital: 10 000 USD / trade (fixed), no compounding, parallel slots OK.

Writes: audit_dashboard/data/bond_connors_rsi2_backtest.json
Run:    python tools/bond_connors_rsi2_backtest.py [--start YYYY-MM-DD] [--end YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "audit_dashboard" / "data" / "bond_connors_rsi2_backtest.json"

SYMBOLS = ["TLT", "IEF", "LQD"]
CAPITAL_PER_TRADE = 10_000.0
TP_PCT = 0.02
SL_PCT = -0.02  # floor


def _rsi(series: list[float], period: int) -> list[float]:
    """Wilder RSI (same as ta-lib default)."""
    if len(series) < period + 1:
        return [float("nan")] * len(series)
    result = [float("nan")] * len(series)
    deltas = [series[i] - series[i - 1] for i in range(1, len(series))]
    gains = [max(d, 0) for d in deltas]
    losses = [abs(min(d, 0)) for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        rs = avg_gain / avg_loss if avg_loss > 0 else float("inf")
        result[i + 1] = 100 - (100 / (1 + rs))
    return result


def _sma(series: list[float], period: int) -> list[float]:
    result = [float("nan")] * len(series)
    for i in range(period - 1, len(series)):
        result[i] = sum(series[i - period + 1 : i + 1]) / period
    return result


def run_backtest(start: str = "2005-01-01", end: str | None = None) -> dict:
    try:
        import yfinance as yf
        import pandas as pd
    except ImportError:
        print("yfinance/pandas required", file=sys.stderr)
        sys.exit(1)

    end = end or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"[bond_connors_rsi2] Fetching {SYMBOLS} {start}→{end} …")

    trades: list[dict] = []
    all_equity_curve: list[tuple[str, float]] = []  # (date, delta_pnl)

    for symbol in SYMBOLS:
        hist = yf.Ticker(symbol).history(start=start, end=end, interval="1d", auto_adjust=True)
        if hist.empty or len(hist) < 210:
            print(f"  {symbol}: insufficient data ({len(hist)} bars) — skip")
            continue

        dates = [str(d.date()) for d in hist.index]
        closes = hist["Close"].tolist()
        sma200 = _sma(closes, 200)
        rsi2 = _rsi(closes, 2)

        in_trade = False
        entry_price = tp = sl = 0.0
        entry_date = ""
        entry_idx = 0

        for i in range(200, len(closes)):
            close = closes[i]
            s200 = sma200[i]
            r2 = rsi2[i]

            if in_trade:
                # Check exit on today's close
                outcome = None
                exit_price = close
                if close >= tp:
                    outcome = "WIN"
                    exit_price = tp  # assume TP filled at limit
                elif close <= sl:
                    outcome = "LOSS"
                    exit_price = sl

                timed_out = outcome is None and (i - entry_idx) >= 30
                if timed_out:
                    # EXPIRED: neutral, excluded from WR/PF (aligned with shadow tracker)
                    outcome = "EXPIRED"
                    exit_price = close

                if outcome:
                    is_expired = outcome == "EXPIRED"
                    pnl_pct = (exit_price - entry_price) / entry_price if not is_expired else 0.0
                    pnl_usd = CAPITAL_PER_TRADE * pnl_pct
                    rr = (tp - entry_price) / (entry_price - sl) if entry_price > sl else 0
                    trades.append({
                        "symbol": symbol,
                        "entry_date": entry_date,
                        "exit_date": dates[i],
                        "entry_price": round(entry_price, 4),
                        "exit_price": round(exit_price, 4),
                        "tp": round(tp, 4),
                        "sl": round(sl, 4),
                        "outcome": outcome,
                        "pnl_pct": round(pnl_pct * 100, 4),
                        "pnl_usd": round(pnl_usd, 2),
                        "rr": round(rr, 2),
                        "hold_bars": i - entry_idx,
                    })
                    if not is_expired:
                        all_equity_curve.append((dates[i], pnl_usd))
                    in_trade = False
                continue

            # Entry signal
            if math.isnan(r2) or math.isnan(s200):
                continue
            if close > s200 and r2 < 10.0:
                entry_price = close
                tp = entry_price * (1 + TP_PCT)
                sl_pct_level = entry_price * (1 + SL_PCT)
                sl = max(sl_pct_level, s200)
                if sl >= entry_price:
                    sl = sl_pct_level
                if entry_price <= sl:
                    continue
                entry_date = dates[i]
                entry_idx = i
                in_trade = True

    if not trades:
        return {"error": "No trades generated", "symbols": SYMBOLS, "start": start, "end": end}

    wins = [t for t in trades if t["outcome"] == "WIN"]
    losses = [t for t in trades if t["outcome"] == "LOSS"]
    expired = [t for t in trades if t["outcome"] == "EXPIRED"]
    closed = [t for t in trades if t["outcome"] in ("WIN", "LOSS")]  # exclude EXPIRED from WR/PF
    pnl_list = [t["pnl_usd"] for t in closed]
    gross_win = sum(t["pnl_usd"] for t in wins)
    gross_loss = abs(sum(t["pnl_usd"] for t in losses))
    pf = round(gross_win / gross_loss, 4) if gross_loss > 0 else 9999.0
    wr = round(len(wins) / len(closed), 4) if closed else 0.0
    avg_pnl = round(sum(pnl_list) / len(pnl_list), 2) if pnl_list else 0.0
    total_pnl = round(sum(pnl_list), 2)

    # MDD on equity curve: worst peak-to-trough USD loss / CAPITAL_PER_TRADE
    cum_pnl = 0.0
    peak_usd = 0.0
    mdd_usd = 0.0
    for _, delta in sorted(all_equity_curve):
        cum_pnl += delta
        if cum_pnl > peak_usd:
            peak_usd = cum_pnl
        dd_usd = peak_usd - cum_pnl
        if dd_usd > mdd_usd:
            mdd_usd = dd_usd
    mdd = mdd_usd / CAPITAL_PER_TRADE  # express as fraction of one trade's capital

    # Sharpe (daily pnl_usd / CAPITAL_PER_TRADE as daily returns approximation)
    if len(pnl_list) > 1:
        mean_r = sum(pnl_list) / len(pnl_list) / CAPITAL_PER_TRADE
        var_r = sum((x / CAPITAL_PER_TRADE - mean_r) ** 2 for x in pnl_list) / len(pnl_list)
        std_r = math.sqrt(var_r) if var_r > 0 else 0
        sharpe = round(mean_r / std_r * math.sqrt(252) if std_r > 0 else 0, 4)
    else:
        sharpe = 0.0

    per_symbol = {}
    for sym in SYMBOLS:
        sym_all = [t for t in trades if t["symbol"] == sym]
        sym_closed = [t for t in sym_all if t["outcome"] in ("WIN", "LOSS")]
        sym_expired = [t for t in sym_all if t["outcome"] == "EXPIRED"]
        if not sym_all:
            continue
        sym_wins = sum(1 for t in sym_closed if t["outcome"] == "WIN")
        sym_gw = sum(t["pnl_usd"] for t in sym_closed if t["pnl_usd"] > 0)
        sym_gl = abs(sum(t["pnl_usd"] for t in sym_closed if t["pnl_usd"] < 0))
        per_symbol[sym] = {
            "n": len(sym_all),
            "n_closed": len(sym_closed),
            "n_expired": len(sym_expired),
            "wr": round(sym_wins / len(sym_closed), 4) if sym_closed else 0.0,
            "pf": round(sym_gw / sym_gl, 4) if sym_gl > 0 else 9999.0,
            "total_pnl_usd": round(sum(t["pnl_usd"] for t in sym_closed), 2),
        }

    return {
        "strategy": "bond_connors_rsi2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spec": "Connors RSI(2) mean reversion on TLT/IEF/LQD — entry: RSI(2)<10 + price>SMA200, TP=+2%, SL=max(-2%,SMA200)",
        "universe": SYMBOLS,
        "config": {"start": start, "end": end, "capital_per_trade_usd": CAPITAL_PER_TRADE, "tp_pct": TP_PCT, "sl_pct": SL_PCT},
        "results": {
            "n_trades": len(trades),
            "n_closed": len(closed),
            "n_expired": len(expired),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate_pct": round(wr * 100, 2),
            "profit_factor": pf,
            "avg_pnl_usd": avg_pnl,
            "total_pnl_usd": total_pnl,
            "max_drawdown_pct": round(mdd * 100, 2),
            "sharpe_annualized": sharpe,
            "note": "WR/PF computed on closed (WIN/LOSS) only; EXPIRED trades excluded (shadow-tracker alignment)",
        },
        "per_symbol": per_symbol,
        "trades": trades,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2005-01-01")
    parser.add_argument("--end", default=None)
    args = parser.parse_args()

    result = run_backtest(args.start, args.end)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    r = result.get("results", {})
    print(
        f"[bond_connors_rsi2] n={r.get('n_trades')} WR={r.get('win_rate_pct')}% "
        f"PF={r.get('profit_factor')} MDD={r.get('max_drawdown_pct')}% "
        f"Sharpe={r.get('sharpe_annualized')}"
    )
    print(f"[bond_connors_rsi2] Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
