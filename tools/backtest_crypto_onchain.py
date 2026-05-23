#!/usr/bin/env python3
"""Backtest CRYPTO On-chain Momentum strategy on 5y data.

LONG  BTC/ETH when MVRV-Z < -0.5 AND active-addresses rising over 30d.
SHORT BTC/ETH when MVRV-Z > 2.0 AND exchange-balance falling over 30d.

MVRV-Z source priority:
  1. Glassnode API (env GLASSNODE_API_KEY) via tools.glassnode_data_fetcher.
  2. Synthetic proxy: price z-score over rolling 180d window.

Usage:
    python tools/backtest_crypto_onchain.py
    python tools/backtest_crypto_onchain.py --years 3 --output report.md

Writes report at reports/backtest_crypto_onchain_<UTC>.md.
Exits 0 always (read-only).
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

ASSETS = [("BTC", "BTC-USD"), ("ETH", "ETH-USD")]
ATR_TP_MULT = 1.5
ATR_SL_MULT = 1.0
HOLD_DAYS = 14
MVRV_LONG_THRESHOLD = -0.5
MVRV_SHORT_THRESHOLD = 2.0
PROXY_LOOKBACK = 180
TREND_LOOKBACK = 30


def _try_yfinance():
    try:
        import yfinance as yf
        return yf
    except ImportError:
        return None


def _try_glassnode():
    try:
        from tools import glassnode_data_fetcher as glass
        return glass
    except ImportError:
        return None


def _atr(highs, lows, closes, period=14):
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


def _download(yf_module, ticker, years):
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=365 * years + PROXY_LOOKBACK + 30)
    try:
        df = yf_module.download(ticker, start=start.isoformat(), end=end.isoformat(),
                                progress=False, auto_adjust=False, threads=False)
    except Exception:
        return None
    if df is None or df.empty:
        return None
    if hasattr(df.columns, "levels"):
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    return df


def _glassnode_mvrv_map(glass, asset):
    """Return dict[iso_date] -> mvrv_z from Glassnode, or None."""
    if glass is None:
        return None
    series = glass.fetch_mvrv_z(asset)
    if not series:
        return None
    out = {}
    for d in series:
        try:
            t = d.get("t")
            v = d.get("v")
            if t is None or v is None:
                continue
            iso = datetime.fromtimestamp(int(t), tz=timezone.utc).date().isoformat()
            out[iso] = float(v)
        except (KeyError, TypeError, ValueError, OSError):
            continue
    return out or None


def _glassnode_trend_map(glass, asset, fetcher_name):
    """Return dict[iso_date] -> 30d trend % from a Glassnode series, or None."""
    if glass is None:
        return None
    fetcher = getattr(glass, fetcher_name, None)
    if fetcher is None:
        return None
    series = fetcher(asset)
    if not series or len(series) < TREND_LOOKBACK:
        return None
    out = {}
    for i in range(TREND_LOOKBACK, len(series)):
        try:
            window = series[i - TREND_LOOKBACK:i]
            vals = [float(p["v"]) for p in window if p.get("v") is not None]
            if len(vals) < TREND_LOOKBACK:
                continue
            baseline = sum(vals[:15]) / 15.0
            recent = sum(vals[-15:]) / 15.0
            if baseline == 0:
                continue
            trend = (recent - baseline) / abs(baseline)
            t = series[i].get("t")
            if t is None:
                continue
            iso = datetime.fromtimestamp(int(t), tz=timezone.utc).date().isoformat()
            out[iso] = trend
        except (KeyError, TypeError, ValueError, ZeroDivisionError, OSError):
            continue
    return out or None


def _build_proxy_mvrv(closes, dates):
    """Synthetic MVRV-Z proxy: 180d rolling z-score of log-price."""
    import math
    out = {}
    for i in range(PROXY_LOOKBACK, len(closes)):
        try:
            window = [math.log(c) for c in closes[i - PROXY_LOOKBACK:i] if c > 0]
            if len(window) < PROXY_LOOKBACK // 2:
                continue
            mean = sum(window) / len(window)
            var = sum((x - mean) ** 2 for x in window) / len(window)
            std = math.sqrt(var) if var > 0 else 0.0
            if std == 0:
                continue
            cur = math.log(closes[i]) if closes[i] > 0 else None
            if cur is None:
                continue
            z = (cur - mean) / std
            out[dates[i]] = z
        except (ValueError, ZeroDivisionError):
            continue
    return out


def _build_proxy_trend(closes, dates):
    """Synthetic trend proxy: 30d % change of closes."""
    out = {}
    for i in range(TREND_LOOKBACK, len(closes)):
        try:
            prev = closes[i - TREND_LOOKBACK]
            if prev <= 0:
                continue
            out[dates[i]] = (closes[i] - prev) / prev
        except (ValueError, ZeroDivisionError):
            continue
    return out


def _signal_for_date(mvrv_map, addr_trend_map, exch_trend_map, date):
    """Return 'LONG'/'SHORT'/None for given iso date."""
    mvrv = mvrv_map.get(date)
    if mvrv is None:
        return None
    if mvrv < MVRV_LONG_THRESHOLD:
        trend = addr_trend_map.get(date)
        if trend is not None and trend > 0:
            return "LONG"
    if mvrv > MVRV_SHORT_THRESHOLD:
        trend = exch_trend_map.get(date)
        if trend is not None and trend < 0:
            return "SHORT"
    return None


def backtest_asset(yf_module, glass, asset, ticker, years):
    df = _download(yf_module, ticker, years)
    if df is None:
        return {"asset": asset, "symbol": ticker, "error": "no_data", "trades": [], "source": "n/a"}
    highs = df["High"].tolist()
    lows = df["Low"].tolist()
    closes = df["Close"].tolist()
    dates = [d.date().isoformat() for d in df.index.tolist()]

    mvrv_map = _glassnode_mvrv_map(glass, asset)
    source = "Glassnode"
    if mvrv_map is None:
        mvrv_map = _build_proxy_mvrv(closes, dates)
        source = "synthetic price z-score (180d)"

    addr_map = _glassnode_trend_map(glass, asset, "fetch_active_addresses")
    exch_map = _glassnode_trend_map(glass, asset, "fetch_exchange_balance")
    if addr_map is None:
        addr_map = _build_proxy_trend(closes, dates)
    if exch_map is None:
        # Inverse of price trend as exchange-balance proxy (price-up -> coins-leave-exch typically)
        price_trend = _build_proxy_trend(closes, dates)
        exch_map = {d: -v for d, v in price_trend.items()}

    trades = []
    in_pos = False
    entry_i = entry_price = tp = sl = None
    direction = None
    last_signal_i = -999

    start_i = max(PROXY_LOOKBACK, TREND_LOOKBACK + 14)
    for i in range(start_i, len(dates)):
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
                exit_price, exit_reason = closes[i], "TIME"
            if exit_price is not None:
                pnl_pct = (exit_price - entry_price) / entry_price * 100
                if direction == "SHORT":
                    pnl_pct = -pnl_pct
                trades.append({
                    "entry_date": dates[entry_i],
                    "exit_date": dates[i],
                    "direction": direction,
                    "entry": round(entry_price, 4),
                    "exit": round(exit_price, 4),
                    "pnl_pct": round(pnl_pct, 3),
                    "exit_reason": exit_reason,
                    "held_days": held,
                })
                in_pos = False

        if not in_pos:
            sig = _signal_for_date(mvrv_map, addr_map, exch_map, dates[i])
            if sig is None:
                continue
            if i - last_signal_i < 5:
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
            last_signal_i = i

    return {"asset": asset, "symbol": ticker, "trades": trades, "source": source}


def aggregate(trades):
    if not trades:
        return {"n": 0, "wr_pct": 0.0, "pf": 0.0, "mdd_pct": 0.0, "expectancy": 0.0}
    wins = [t for t in trades if t["pnl_pct"] > 0]
    losses = [t for t in trades if t["pnl_pct"] <= 0]
    sum_wins = sum(t["pnl_pct"] for t in wins)
    sum_losses = abs(sum(t["pnl_pct"] for t in losses))
    pf = sum_wins / sum_losses if sum_losses > 0 else float("inf")
    wr = len(wins) / len(trades) * 100
    expectancy = sum(t["pnl_pct"] for t in trades) / len(trades)
    equity = peak = mdd = 0.0
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


def verdict(pf):
    if pf == "inf":
        return "PASS"
    if pf >= 1.5:
        return "PASS"
    if pf >= 1.0:
        return "WARN"
    return "FAIL"


def write_report(results, out_path):
    lines = ["# Backtest - CRYPTO On-chain Momentum", ""]
    lines.append(f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("**Strategy:** LONG MVRV-Z<-0.5 + active-addr rising; SHORT MVRV-Z>2.0 + exch-bal falling")
    lines.append(f"**Hold:** {HOLD_DAYS}d max | **TP:** {ATR_TP_MULT}xATR | **SL:** {ATR_SL_MULT}xATR")
    lines.append("")
    lines.append("## Per-asset results")
    lines.append("")
    lines.append("| Asset | Source | n | WR% | PF | MDD% | Expectancy% | Verdict |")
    lines.append("|---|---|---:|---:|---:|---:|---:|:---|")
    all_trades = []
    for r in results:
        sym = r["asset"]
        src = r.get("source", "n/a")
        trades = r.get("trades") or []
        all_trades.extend(trades)
        if "error" in r:
            lines.append(f"| {sym} | {src} | 0 | - | - | - | - | ERROR: {r['error']} |")
            continue
        agg = aggregate(trades)
        v = verdict(agg["pf"])
        lines.append(f"| {sym} | {src} | {agg['n']} | {agg['wr_pct']} | {agg['pf']} | {agg['mdd_pct']} | {agg['expectancy']} | {v} |")
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
    print(f"wrote {out_path.relative_to(REPO)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, default=5)
    ap.add_argument("--output", type=str)
    args = ap.parse_args()

    out_path = Path(args.output) if args.output else (
        REPO / "reports" / f"backtest_crypto_onchain_{datetime.now(timezone.utc).strftime('%Y_%m_%d_%H%MZ')}.md"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)

    yf_module = _try_yfinance()
    if yf_module is None:
        print("yfinance not installed; verdict=DATA_GAP")
        out_path.write_text("# Backtest CRYPTO On-chain Momentum\n\nVerdict: DATA_GAP (yfinance not installed)\n", encoding="utf-8")
        return

    glass = _try_glassnode()
    if glass is not None and not os.getenv("GLASSNODE_API_KEY"):
        glass_mode = "synthetic-proxy (no GLASSNODE_API_KEY)"
    elif glass is None:
        glass_mode = "synthetic-proxy (glassnode_data_fetcher missing)"
    else:
        glass_mode = "Glassnode-live"
    print(f"  MVRV source: {glass_mode}")

    results = []
    for asset, ticker in ASSETS:
        print(f"  backtesting {asset} ({ticker}, {args.years}y)...", flush=True)
        r = backtest_asset(yf_module, glass, asset, ticker, args.years)
        print(f"    -> {len(r.get('trades') or [])} trades [{r.get('source','n/a')}]")
        results.append(r)
        time.sleep(0.4)

    write_report(results, out_path)


if __name__ == "__main__":
    main()
