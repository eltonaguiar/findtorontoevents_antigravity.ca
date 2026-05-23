#!/usr/bin/env python3
"""Backtest FOREX COT Positioning Reversal on 5y yfinance OHLCV.

Strategy under test: ``alpha_engine/forex_cot_reversal.py`` (PR-L on main).
Fade non-commercial speculator positioning at >=80th / <=20th 52w pct,
2-week confirmation, 30d hold, ATR 1.0x TP / 0.5x SL (FX is tighter).

Data path:
  1. Try real CFTC COT via ``tools.cftc_cot_forex_fetcher`` (gated; only
     fetches when ``FOREX_COT_REVERSAL_ENABLED=1``).
  2. Otherwise generate synthetic deterministic signals via
     ``random.Random(42)`` so the backtest harness itself is testable
     offline.

Per CLAUDE.md FOREX directive / PR #909: FOREX picks are hard-capped at
0 size in prod until live PF >= 0.8. This backtest still runs (research
only) and the verdict line flags the prod cap.

Usage:
    python tools/backtest_forex_cot.py
    python tools/backtest_forex_cot.py --years 3 --output report.md
    python tools/backtest_forex_cot.py --synthetic

Exits 0 always (read-only).
"""
from __future__ import annotations

import argparse
import random
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

# Mirror live strategy constants where possible; fall back to literals so the
# backtest still runs if the live module fails to import.
try:
    from alpha_engine.forex_cot_reversal import (
        CONFIRM_WEEKS,
        EXTREME_LONG_PERCENTILE,
        EXTREME_SHORT_PERCENTILE,
        LOOKBACK_WEEKS,
        compute_signal,
    )
except Exception:  # pragma: no cover - defensive
    CONFIRM_WEEKS = 2
    EXTREME_LONG_PERCENTILE = 80
    EXTREME_SHORT_PERCENTILE = 20
    LOOKBACK_WEEKS = 52
    compute_signal = None  # type: ignore

# FX pair -> yfinance ticker (per spec).
PAIR_TO_YF = {
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "JPY=X",
    "AUDUSD": "AUDUSD=X",
}
# FX tighter stops than commodities: 1.0x TP, 0.5x SL.
ATR_TP_MULT = 1.0
ATR_SL_MULT = 0.5
HOLD_DAYS = 30
INVERTED = {"USDJPY"}  # YEN futures speculator long -> USDJPY SHORT


def _try_yfinance():
    try:
        import yfinance as yf
        return yf
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


def generate_synthetic_signals(pair: str, weeks: int, seed: int = 42) -> list[dict]:
    """Deterministic synthetic weekly signal stream.

    Returns list of {date, direction (LONG/SHORT/NEUTRAL), pct} ordered
    oldest -> newest. Pair name is mixed into the RNG so each pair is
    distinct yet reproducible across runs.
    """
    rng = random.Random(seed + sum(ord(c) for c in pair))
    out: list[dict] = []
    start = datetime.now(timezone.utc).date() - timedelta(weeks=weeks)
    prev_pct = 50.0
    for w in range(weeks):
        # Mean-reverting random walk in percentile space.
        pct = max(0.0, min(100.0, prev_pct + rng.gauss(0, 18) - (prev_pct - 50) * 0.15))
        prev_pct = pct
        if pct >= EXTREME_LONG_PERCENTILE:
            direction = "SHORT"
        elif pct <= EXTREME_SHORT_PERCENTILE:
            direction = "LONG"
        else:
            direction = "NEUTRAL"
        out.append({
            "date": (start + timedelta(weeks=w)).isoformat(),
            "pct": round(pct, 1),
            "direction": direction,
        })
    return out


def _confirmed_signals(stream: list[dict]) -> list[dict]:
    """Apply 2-week confirmation (CONFIRM_WEEKS): emit only when current
    AND prior week both flag the same non-NEUTRAL direction."""
    confirmed: list[dict] = []
    for i in range(CONFIRM_WEEKS - 1, len(stream)):
        cur = stream[i]
        if cur["direction"] == "NEUTRAL":
            continue
        ok = all(
            stream[i - k]["direction"] == cur["direction"]
            for k in range(CONFIRM_WEEKS)
        )
        if ok:
            confirmed.append(cur)
    return confirmed


def _signals_from_real_cot(pair: str, weeks: int) -> list[dict]:
    """Build weekly direction stream from real CFTC fetch (gated)."""
    try:
        from tools.cftc_cot_forex_fetcher import fetch_cot
    except Exception:
        return []
    res = fetch_cot(pair, limit=max(weeks, LOOKBACK_WEEKS + CONFIRM_WEEKS + 4))
    reports = (res or {}).get("reports") or []
    if not reports or compute_signal is None:
        return []
    # `reports` is DESC; build oldest->newest stream by rolling windows.
    asc = list(reversed(reports))
    stream: list[dict] = []
    for i in range(LOOKBACK_WEEKS, len(asc)):
        window_desc = list(reversed(asc[: i + 1]))  # newest first for compute_signal
        sig = compute_signal(window_desc)
        direction = sig.get("direction", "NEUTRAL")
        if pair in INVERTED and direction in {"LONG", "SHORT"}:
            direction = "SHORT" if direction == "LONG" else "LONG"
        stream.append({
            "date": str(asc[i].get("report_date_as_yyyy_mm_dd", ""))[:10],
            "pct": sig.get("percentile_rank", 50.0),
            "direction": direction,
        })
    return stream


def backtest_one_pair(yf_module, pair: str, years: int,
                      force_synthetic: bool = False) -> dict:
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=365 * years + 60)
    yf_sym = PAIR_TO_YF[pair]
    try:
        df = yf_module.download(
            yf_sym, start=start.isoformat(), end=end.isoformat(),
            progress=False, auto_adjust=False, threads=False,
        )
    except Exception as e:
        return {"pair": pair, "error": str(e), "trades": [], "source": "yf_error"}
    if df is None or df.empty:
        return {"pair": pair, "error": "no_data", "trades": [], "source": "yf_empty"}
    if hasattr(df.columns, "levels"):
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    highs = df["High"].tolist()
    lows = df["Low"].tolist()
    closes = df["Close"].tolist()
    dates = df.index.tolist()

    # Weekly signal stream
    weeks = max(years * 52 + 8, LOOKBACK_WEEKS + CONFIRM_WEEKS + 4)
    stream: list[dict] = []
    source = "synthetic"
    if not force_synthetic:
        stream = _signals_from_real_cot(pair, weeks)
        if stream:
            source = "cftc_real"
    if not stream:
        stream = generate_synthetic_signals(pair, weeks)
        source = "synthetic"
    confirmed = _confirmed_signals(stream)
    # Index confirmed signal dates -> direction for fast bar-wise lookup.
    sig_by_date = {s["date"]: s["direction"] for s in confirmed}

    trades = []
    in_pos = False
    entry_i = None
    entry_price = tp = sl = None
    direction = None
    used = set()

    for i in range(20, len(dates)):
        # Manage open position
        if in_pos:
            held = i - entry_i
            hi, lo = highs[i], lows[i]
            exit_price = exit_reason = None
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
                    "entry_date": dates[entry_i].isoformat()[:10],
                    "exit_date": dates[i].isoformat()[:10],
                    "direction": direction,
                    "entry": round(entry_price, 5),
                    "exit": round(exit_price, 5),
                    "pnl_pct": round(pnl_pct, 3),
                    "exit_reason": exit_reason,
                    "held_days": held,
                })
                in_pos = False

        # New entry: only when bar date matches a confirmed weekly signal we
        # have not yet acted on, and we are flat.
        if not in_pos:
            d_iso = dates[i].isoformat()[:10]
            # Match same-week trigger (signal weekly date may not align with
            # trading day); accept first trading day >= signal date.
            cand_dir = None
            for sd, dr in sig_by_date.items():
                if sd in used:
                    continue
                if sd <= d_iso:
                    cand_dir = dr
                    used.add(sd)
                    break
            if cand_dir is None:
                continue
            atr = _atr(highs[: i + 1], lows[: i + 1], closes[: i + 1])
            if atr is None or atr <= 0:
                continue
            entry_price = closes[i]
            if cand_dir == "LONG":
                tp = entry_price + ATR_TP_MULT * atr
                sl = entry_price - ATR_SL_MULT * atr
            else:
                tp = entry_price - ATR_TP_MULT * atr
                sl = entry_price + ATR_SL_MULT * atr
            in_pos = True
            entry_i = i
            direction = cand_dir

    return {"pair": pair, "trades": trades, "source": source,
            "n_signals": len(confirmed)}


def aggregate(trades: list[dict]) -> dict:
    if not trades:
        return {"n": 0, "wr_pct": 0.0, "pf": 0.0, "mdd_pct": 0.0,
                "expectancy": 0.0}
    wins = [t for t in trades if t["pnl_pct"] > 0]
    losses = [t for t in trades if t["pnl_pct"] <= 0]
    sw = sum(t["pnl_pct"] for t in wins)
    sl_ = abs(sum(t["pnl_pct"] for t in losses))
    pf = sw / sl_ if sl_ > 0 else float("inf")
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
    return {"n": len(trades), "wr_pct": round(wr, 2),
            "pf": round(pf, 3) if pf != float("inf") else "inf",
            "mdd_pct": round(mdd, 2),
            "expectancy": round(expectancy, 3)}


def verdict(pf) -> str:
    if pf == "inf":
        return "PASS"
    if pf >= 1.5:
        return "PASS"
    if pf >= 1.0:
        return "WARN"
    return "FAIL"


def write_report(results: list[dict], out_path: Path,
                 synthetic_used: bool) -> None:
    lines = ["# Backtest -- FOREX COT Positioning Reversal", ""]
    lines.append(f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("**Strategy:** alpha_engine/forex_cot_reversal.py (PR-L)")
    lines.append(f"**Signal source:** {'SYNTHETIC (random.Random(42))' if synthetic_used else 'CFTC real fetch (or mixed)'}")
    lines.append("")
    lines.append("> **PROD GUARD:** FOREX sizing currently OFF in prod "
                 "(PR #909, hard-cap until live PF >= 0.8). This is "
                 "research-only -- do NOT promote to live size on PASS alone.")
    lines.append("")
    lines.append("## Per-pair results")
    lines.append("")
    lines.append("| Pair | Source | Signals | n | WR% | PF | MDD% | Exp% | Verdict |")
    lines.append("|---|:---|---:|---:|---:|---:|---:|---:|:---|")
    all_trades = []
    for r in results:
        p = r["pair"]
        src = r.get("source", "?")
        trades = r.get("trades") or []
        all_trades.extend(trades)
        if "error" in r:
            lines.append(f"| {p} | {src} | 0 | 0 | - | - | - | - | ERROR: {r['error']} |")
            continue
        agg = aggregate(trades)
        v = verdict(agg["pf"])
        lines.append(f"| {p} | {src} | {r.get('n_signals', 0)} | {agg['n']} | "
                     f"{agg['wr_pct']} | {agg['pf']} | {agg['mdd_pct']} | "
                     f"{agg['expectancy']} | {v} |")
    lines.append("")
    overall = aggregate(all_trades)
    lines.append("## Overall")
    lines.append("")
    lines.append(f"- **n:** {overall['n']}")
    lines.append(f"- **WR:** {overall['wr_pct']}%")
    lines.append(f"- **PF:** {overall['pf']}")
    lines.append(f"- **MDD:** {overall['mdd_pct']}%")
    lines.append(f"- **Expectancy/trade:** {overall['expectancy']}%")
    lines.append(f"- **Verdict:** {verdict(overall['pf'])}  "
                 "(PASS = PF>=1.5, WARN = 1.0-1.5, FAIL = <1.0)")
    lines.append("")
    lines.append("**Reminder:** Even on PASS, FOREX live size = 0 until "
                 "the system-wide FOREX PF >= 0.8 (CLAUDE.md / PR #909).")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out_path.relative_to(REPO)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, default=5)
    ap.add_argument("--output", type=str)
    ap.add_argument("--synthetic", action="store_true",
                    help="Force synthetic signal generator (skip CFTC fetch)")
    args = ap.parse_args()

    yf_module = _try_yfinance()
    if yf_module is None:
        out_path = REPO / "reports" / (
            f"backtest_forex_cot_{datetime.now(timezone.utc).strftime('%Y_%m_%d_%H%MZ')}.md"
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            "# Backtest FOREX COT Reversal\n\n"
            "Verdict: DATA_GAP (yfinance not installed)\n",
            encoding="utf-8")
        print(f"yfinance missing; wrote stub {out_path}")
        return

    results = []
    synthetic_used = bool(args.synthetic)
    for pair in PAIR_TO_YF:
        print(f"  backtesting {pair} ({args.years}y)...", flush=True)
        r = backtest_one_pair(yf_module, pair, args.years,
                              force_synthetic=args.synthetic)
        if r.get("source") == "synthetic":
            synthetic_used = True
        n = len(r.get("trades") or [])
        print(f"    -> {n} trades  (signal={r.get('source')})")
        results.append(r)
        time.sleep(0.4)

    out_path = Path(args.output) if args.output else (
        REPO / "reports" / (
            f"backtest_forex_cot_{datetime.now(timezone.utc).strftime('%Y_%m_%d_%H%MZ')}.md"
        )
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_report(results, out_path, synthetic_used=synthetic_used)


if __name__ == "__main__":
    main()
