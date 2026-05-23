#!/usr/bin/env python3
"""Backtest ETF Economic Momentum strategy on 5y yfinance OHLCV.

Validates expected PF 1.65 before flipping ETF_ECONOMIC_MOMENTUM_ENABLED=1.

Signal logic mirrors ``alpha_engine/etf_economic_momentum.py``:
  LONG  when ISM > 50  AND M2 YoY > 0 AND GDP momentum z >  0.5
  SHORT when ISM < 50                AND GDP momentum z < -0.5

Macro data sources (in order of preference):
  1. FRED via ``tools.fred_data_fetcher`` (needs FRED_API_KEY)
  2. yfinance proxy: ^VIX (risk-off when high z) and DX-Y.NYB (USD strength)
     - Proxy regime: LONG when VIX_z < -0.5 AND DXY_z < 0
                     SHORT when VIX_z > 0.5  AND DXY_z > 0

Per-ETF + overall: PF, WR, MDD, Verdict (PASS PF>=1.5 / WARN / FAIL).

Usage:
    python tools/backtest_etf_economic.py
    python tools/backtest_etf_economic.py --years 3 --output report.md

Writes report at reports/backtest_etf_economic_<UTC>.md.
Exits 0 always (read-only).
"""
from __future__ import annotations

import argparse
import statistics
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _print_wrote_path(out_path: Path, suffix: str = "") -> None:
    """Log output path; supports --output outside repo (e.g. pytest tmp dirs on CI)."""
    try:
        rel = out_path.resolve().relative_to(REPO.resolve())
        print(f"wrote {rel}{suffix}")
    except ValueError:
        print(f"wrote {out_path}{suffix}")
sys.path.insert(0, str(REPO))

try:
    from alpha_engine.etf_economic_momentum import (
        ETF_UNIVERSE,
        GDP_LONG_Z,
        GDP_SHORT_Z,
        ISM_LONG_THRESHOLD,
        ISM_SHORT_THRESHOLD,
    )
except Exception as e:
    print(f"FATAL: cannot import etf_economic_momentum: {e}")
    sys.exit(0)

HOLD_DAYS = 30
ATR_TP_MULT = 1.2
ATR_SL_MULT = 1.0
ATR_PERIOD = 14


def _try_yfinance():
    try:
        import yfinance as yf
        return yf
    except ImportError:
        return None


def _try_fred():
    try:
        from tools import fred_data_fetcher as fred
        return fred
    except Exception:
        return None


def _atr(highs, lows, closes, period=ATR_PERIOD):
    if len(closes) < period + 1:
        return None
    trs = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    return sum(trs[-period:]) / period if trs else None


def _zscore(values: list[float]) -> float | None:
    if len(values) < 5:
        return None
    try:
        mean = statistics.mean(values[:-1])
        std = statistics.pstdev(values[:-1])
    except statistics.StatisticsError:
        return None
    if std == 0:
        return None
    return (values[-1] - mean) / std


def fetch_fred_monthly_series(fred, years: int) -> dict[str, dict[str, float]] | None:
    """Return ``{'NAPM': {date: val}, 'M2SL': {...}, 'GDPC1': {...}}`` or None."""
    if fred is None:
        return None
    out: dict[str, dict[str, float]] = {}
    for sid in ("NAPM", "M2SL", "GDPC1"):
        rec = fred.fetch_series(sid)
        if rec.get("source") != "fred_api_v1":
            return None
        obs = rec.get("observations") or []
        out[sid] = {row["date"]: float(row["value"]) for row in obs}
    return out


def fetch_yf_proxy_monthly(yf_module, years: int) -> dict[str, dict[str, float]] | None:
    """Return month-end close map for ^VIX and DX-Y.NYB or None."""
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=365 * years + 60)
    out: dict[str, dict[str, float]] = {}
    for proxy in ("^VIX", "DX-Y.NYB"):
        try:
            df = yf_module.download(
                proxy, start=start.isoformat(), end=end.isoformat(),
                progress=False, auto_adjust=False, threads=False,
            )
        except Exception:
            return None
        if df is None or df.empty:
            return None
        if hasattr(df.columns, "levels"):
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        closes = df["Close"]
        # resample to month-end
        try:
            me = closes.resample("ME").last()
        except Exception:
            try:
                me = closes.resample("M").last()
            except Exception:
                return None
        out[proxy] = {idx.isoformat()[:10]: float(v) for idx, v in me.items() if v == v}
    return out


def signal_from_fred(fred_data: dict[str, dict[str, float]], asof: str) -> str | None:
    """Reproduce evaluate_macro for a given as-of date string (YYYY-MM-DD)."""
    napm = fred_data.get("NAPM", {})
    m2 = fred_data.get("M2SL", {})
    gdp = fred_data.get("GDPC1", {})

    napm_dates = sorted(d for d in napm if d <= asof)
    if not napm_dates:
        return None
    ism = napm[napm_dates[-1]]

    m2_dates = sorted(d for d in m2 if d <= asof)
    m2_yoy = None
    if len(m2_dates) >= 13:
        latest = m2[m2_dates[-1]]
        prior = m2[m2_dates[-13]]
        if prior:
            m2_yoy = (latest - prior) / prior

    gdp_dates = sorted(d for d in gdp if d <= asof)
    if len(gdp_dates) < 6:
        return None
    gdp_vals = [gdp[d] for d in gdp_dates[-16:]]
    gdp_z = _zscore(gdp_vals)
    if gdp_z is None:
        return None

    if ism > ISM_LONG_THRESHOLD and (m2_yoy is None or m2_yoy > 0) and gdp_z > GDP_LONG_Z:
        return "LONG"
    if ism < ISM_SHORT_THRESHOLD and gdp_z < GDP_SHORT_Z:
        return "SHORT"
    return None


def signal_from_proxy(proxy: dict[str, dict[str, float]], asof: str) -> str | None:
    vix_map = proxy.get("^VIX", {})
    dxy_map = proxy.get("DX-Y.NYB", {})
    vix_dates = sorted(d for d in vix_map if d <= asof)
    dxy_dates = sorted(d for d in dxy_map if d <= asof)
    if len(vix_dates) < 13 or len(dxy_dates) < 13:
        return None
    vix_vals = [vix_map[d] for d in vix_dates[-12:]]
    dxy_vals = [dxy_map[d] for d in dxy_dates[-12:]]
    vix_z = _zscore(vix_vals)
    dxy_z = _zscore(dxy_vals)
    if vix_z is None or dxy_z is None:
        return None
    if vix_z < -0.5 and dxy_z < 0:
        return "LONG"
    if vix_z > 0.5 and dxy_z > 0:
        return "SHORT"
    return None


def backtest_one_symbol(yf_module, symbol: str, years: int,
                        signal_fn, signal_data) -> dict:
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=365 * years + 60)
    try:
        df = yf_module.download(
            symbol, start=start.isoformat(), end=end.isoformat(),
            progress=False, auto_adjust=False, threads=False,
        )
    except Exception as e:
        return {"symbol": symbol, "error": str(e), "trades": []}
    if df is None or df.empty:
        return {"symbol": symbol, "error": "no_data", "trades": []}
    if hasattr(df.columns, "levels"):
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]

    highs = df["High"].tolist()
    lows = df["Low"].tolist()
    closes = df["Close"].tolist()
    dates = df.index.tolist()

    trades = []
    in_pos = False
    entry_i = None
    entry_price = None
    tp = sl = None
    direction = None
    last_eval_month = None

    for i in range(ATR_PERIOD + 1, len(dates)):
        if in_pos:
            held = i - entry_i
            hi, lo = highs[i], lows[i]
            exit_price = None
            exit_reason = None
            if direction == "LONG":
                if hi >= tp:
                    exit_price, exit_reason = tp, "TP"
                elif lo <= sl:
                    exit_price, exit_reason = sl, "SL"
            else:
                if lo <= tp:
                    exit_price, exit_reason = tp, "TP"
                elif hi >= sl:
                    exit_price, exit_reason = sl, "SL"
            if exit_price is None and held >= HOLD_DAYS:
                exit_price = closes[i]
                exit_reason = "TIME"
            if exit_price is not None:
                pnl_pct = (exit_price - entry_price) / entry_price * 100
                if direction == "SHORT":
                    pnl_pct = -pnl_pct
                trades.append({
                    "entry_date": dates[entry_i].isoformat()[:10],
                    "exit_date": dates[i].isoformat()[:10],
                    "direction": direction,
                    "entry": round(entry_price, 4),
                    "exit": round(exit_price, 4),
                    "pnl_pct": round(pnl_pct, 3),
                    "exit_reason": exit_reason,
                    "held_days": held,
                })
                in_pos = False

        if in_pos:
            continue

        ym = (dates[i].year, dates[i].month)
        # Only evaluate once per month at first available bar of new month
        if ym == last_eval_month:
            continue
        last_eval_month = ym
        asof = dates[i].isoformat()[:10]
        sig = signal_fn(signal_data, asof)
        if sig not in ("LONG", "SHORT"):
            continue
        atr = _atr(highs[: i + 1], lows[: i + 1], closes[: i + 1])
        if atr is None or atr <= 0:
            continue
        entry_price = closes[i]
        if sig == "LONG":
            tp = entry_price + ATR_TP_MULT * atr
            sl = entry_price - ATR_SL_MULT * atr
        else:
            tp = entry_price - ATR_TP_MULT * atr
            sl = entry_price + ATR_SL_MULT * atr
        in_pos = True
        entry_i = i
        direction = sig

    return {"symbol": symbol, "trades": trades}


def aggregate(trades: list[dict]) -> dict:
    if not trades:
        return {"n": 0, "wr_pct": 0.0, "pf": 0.0, "mdd_pct": 0.0, "expectancy": 0.0}
    wins = [t for t in trades if t["pnl_pct"] > 0]
    losses = [t for t in trades if t["pnl_pct"] <= 0]
    sum_wins = sum(t["pnl_pct"] for t in wins)
    sum_losses = abs(sum(t["pnl_pct"] for t in losses))
    pf = sum_wins / sum_losses if sum_losses > 0 else float("inf")
    wr = len(wins) / len(trades) * 100
    expectancy = sum(t["pnl_pct"] for t in trades) / len(trades)
    equity = 0.0
    peak = 0.0
    mdd = 0.0
    for t in trades:
        equity += t["pnl_pct"]
        if equity > peak:
            peak = equity
        dd = peak - equity
        if dd > mdd:
            mdd = dd
    return {
        "n": len(trades),
        "wr_pct": round(wr, 2),
        "pf": round(pf, 3) if pf != float("inf") else "inf",
        "mdd_pct": round(mdd, 2),
        "expectancy": round(expectancy, 3),
    }


def verdict(pf) -> str:
    if pf == "inf":
        return "PASS"
    if pf >= 1.5:
        return "PASS"
    if pf >= 1.0:
        return "WARN"
    return "FAIL"


def write_report(results: list[dict], out_path: Path, source_label: str) -> None:
    lines = ["# Backtest — ETF Economic Momentum", ""]
    lines.append(f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"**Macro source:** {source_label}")
    lines.append("")
    lines.append("## Per-ETF results")
    lines.append("")
    lines.append("| Symbol | n | WR% | PF | MDD% | Expectancy% | Verdict |")
    lines.append("|---|---:|---:|---:|---:|---:|:---|")
    all_trades = []
    for r in results:
        sym = r["symbol"]
        trades = r.get("trades") or []
        all_trades.extend(trades)
        if "error" in r:
            lines.append(f"| {sym} | 0 | — | — | — | — | ERROR: {r['error']} |")
            continue
        agg = aggregate(trades)
        v = verdict(agg["pf"])
        lines.append(f"| {sym} | {agg['n']} | {agg['wr_pct']} | {agg['pf']} | {agg['mdd_pct']} | {agg['expectancy']} | {v} |")
    lines.append("")
    overall = aggregate(all_trades)
    overall_v = verdict(overall["pf"])
    lines.append("## Overall")
    lines.append("")
    lines.append(f"- **n:** {overall['n']}")
    lines.append(f"- **WR:** {overall['wr_pct']}%")
    lines.append(f"- **PF:** {overall['pf']}")
    lines.append(f"- **MDD:** {overall['mdd_pct']}%")
    lines.append(f"- **Expectancy/trade:** {overall['expectancy']}%")
    lines.append(f"- **Verdict:** {overall_v}  (PASS = PF>=1.5, WARN = 1.0-1.5, FAIL = <1.0)")
    lines.append("")
    if all_trades:
        srt = sorted(all_trades, key=lambda t: t["pnl_pct"], reverse=True)
        lines.append("## Best 5 trades")
        for t in srt[:5]:
            lines.append(f"- {t['entry_date']} -> {t['exit_date']} {t['direction']} pnl={t['pnl_pct']:+.2f}% ({t['exit_reason']})")
        lines.append("")
        lines.append("## Worst 5 trades")
        for t in srt[-5:][::-1]:
            lines.append(f"- {t['entry_date']} -> {t['exit_date']} {t['direction']} pnl={t['pnl_pct']:+.2f}% ({t['exit_reason']})")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    _print_wrote_path(out_path)


def _data_gap_report(out_path: Path, reason: str) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        f"# Backtest ETF Economic Momentum\n\nVerdict: DATA_GAP ({reason})\n",
        encoding="utf-8",
    )
    _print_wrote_path(out_path, " (DATA_GAP)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, default=5)
    ap.add_argument("--output", type=str)
    args = ap.parse_args()

    out_path = Path(args.output) if args.output else (
        REPO / "reports" / f"backtest_etf_economic_{datetime.now(timezone.utc).strftime('%Y_%m_%d_%H%MZ')}.md"
    )

    yf_module = _try_yfinance()
    if yf_module is None:
        _data_gap_report(out_path, "yfinance not installed")
        return

    fred = _try_fred()
    fred_data = fetch_fred_monthly_series(fred, args.years) if fred else None
    if fred_data:
        signal_fn = signal_from_fred
        signal_data = fred_data
        source_label = "FRED (NAPM/M2SL/GDPC1)"
    else:
        proxy = fetch_yf_proxy_monthly(yf_module, args.years)
        if proxy is None:
            _data_gap_report(out_path, "no FRED key and yfinance proxy fetch failed")
            return
        signal_fn = signal_from_proxy
        signal_data = proxy
        source_label = "yfinance proxy (^VIX, DX-Y.NYB)"

    results = []
    for symbol in ETF_UNIVERSE:
        print(f"  backtesting {symbol} ({args.years}y)...", flush=True)
        r = backtest_one_symbol(yf_module, symbol, args.years, signal_fn, signal_data)
        n = len(r.get("trades") or [])
        print(f"    -> {n} trades")
        results.append(r)
        time.sleep(0.3)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_report(results, out_path, source_label)


if __name__ == "__main__":
    main()
