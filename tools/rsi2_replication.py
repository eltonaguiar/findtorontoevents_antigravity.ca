#!/usr/bin/env python3
"""rsi2_replication.py — replicate Connors RSI(2) and let the tribunal judge it.

H-2026-11-20-06. The point is not to discover anything: RSI(2) mean reversion on
equity indices is documented since the 1990s. The point is to prove this repo's
measurement pipeline can reproduce a *known* effect, and to see whether it
survives the same gates that killed everything else here. A pipeline that cannot
reproduce a documented effect is not measuring what it claims to measure.

The BTC/SOL run is a control, not a target. Crypto trades 24/7 with no overnight
gap structure, so the "sharp 2-day drop reverts" story has no mechanism there.
If the control also shows alpha at the same significance, the test is picking up
market beta or a coding artifact, and the SPY/QQQ result means nothing.

Deliberate choices:
  * signal at close of day t, entry at the OPEN of t+1 — no same-bar fill
  * exit at the close of the day the exit condition first holds
  * selection alpha is computed per trade as pick net minus direction-adjusted
    buy-and-hold over the SAME window, so a long that made 2% while the index
    made 3% is scored as -1%, not +2%
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

RSI_PERIOD = 2
ENTRY_RSI = 10.0
EXIT_RSI = 60.0
EXIT_SMA = 5
MAX_HOLD = 10


def wilder_rsi(closes: list[float], period: int = RSI_PERIOD) -> list[float | None]:
    """Wilder-smoothed RSI. None until enough history exists.

    A zero average loss means no down-move in the window: RSI is 100 by
    definition, not a division error and not 0.
    """
    out: list[float | None] = [None] * len(closes)
    if len(closes) <= period:
        return out
    gains: list[float] = []
    losses: list[float] = []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0.0))
        losses.append(max(-d, 0.0))
    avg_g = sum(gains[:period]) / period
    avg_l = sum(losses[:period]) / period

    def _rsi(g: float, l: float) -> float:
        # No losses in the window is 100 by convention, not a division error.
        return 100.0 if l == 0 else 100.0 - 100.0 / (1.0 + g / l)

    # The seed consumes deltas[0:period], so the first defined value sits at
    # price index `period` — and every later delta must be smoothed, including
    # the very next one. Skipping it (as an `i > period` guard did) left one
    # stale value after the seed and hid the first real move.
    out[period] = _rsi(avg_g, avg_l)
    for i in range(period, len(gains)):
        avg_g = (avg_g * (period - 1) + gains[i]) / period
        avg_l = (avg_l * (period - 1) + losses[i]) / period
        out[i + 1] = _rsi(avg_g, avg_l)
    return out


def sma(values: list[float], window: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    for i in range(window - 1, len(values)):
        out[i] = sum(values[i - window + 1:i + 1]) / window
    return out


def simulate(bars: list[dict], symbol: str, asset_class: str) -> list[dict]:
    """Walk one symbol's daily bars and emit closed trades in canonical shape."""
    closes = [b["close"] for b in bars]
    opens = [b["open"] for b in bars]
    rsi = wilder_rsi(closes)
    ma = sma(closes, EXIT_SMA)
    rows: list[dict] = []
    i = 0
    while i < len(bars):
        r = rsi[i]
        if r is None or r >= ENTRY_RSI:
            i += 1
            continue
        entry_i = i + 1
        if entry_i >= len(bars):
            break
        entry = opens[entry_i]
        if not entry:
            i += 1
            continue
        exit_i = None
        for j in range(entry_i, len(bars)):
            held = j - entry_i + 1
            m = ma[j]
            rj = rsi[j]
            if (m is not None and closes[j] > m) or (rj is not None and rj > EXIT_RSI) or held >= MAX_HOLD:
                exit_i = j
                break
        if exit_i is None:
            break
        exit_px = closes[exit_i]
        gross = (exit_px / entry - 1.0) * 100.0
        hold = (exit_i - entry_i) + 1
        bh = (closes[exit_i] / closes[entry_i] - 1.0) * 100.0
        rows.append({
            "symbol": symbol,
            "asset_class": asset_class,
            "direction": "LONG",
            "strategy": f"RSI2_MR_{symbol}",
            "entry_price": round(entry, 6),
            "pnl_pct": round(gross, 6),
            "pnl_gross_pct": round(gross, 6),
            "closed_at": str(bars[exit_i].get("date", "")),
            "opened_at": str(bars[entry_i].get("date", "")),
            "hold_days": hold,
            "buy_hold_pct": round(bh, 6),
            "selection_alpha_pct": round(gross - bh, 6),
            "status": "WON" if gross > 0 else "LOST",
        })
        i = exit_i + 1
    return rows


def summarize(rows: list[dict]) -> dict:
    if not rows:
        return {"n": 0, "verdict": "INCONCLUSIVE — no trades"}
    nets = [r["pnl_pct"] for r in rows]
    alphas = [r["selection_alpha_pct"] for r in rows]
    win = sum(1 for n in nets if n > 0)
    return {
        "n": len(rows),
        "mean_net_pct": round(statistics.fmean(nets), 4),
        "median_net_pct": round(statistics.median(nets), 4),
        "win_rate": round(win / len(rows), 4),
        "mean_selection_alpha_pct": round(statistics.fmean(alphas), 4),
        "mean_hold_days": round(statistics.fmean([r["hold_days"] for r in rows]), 2),
        "mean_buy_hold_pct": round(statistics.fmean([r["buy_hold_pct"] for r in rows]), 4),
    }


def fetch(symbol: str, period: str = "10y"):
    import yfinance as yf  # imported late: tests never touch the network

    df = yf.Ticker(symbol).history(period=period, interval="1d", auto_adjust=True)
    bars = []
    for ts, row in df.iterrows():
        o, c = float(row["Open"]), float(row["Close"])
        if not o or not c:
            continue
        bars.append({"date": str(ts)[:10], "open": o, "close": c})
    return bars


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="RSI(2) replication through the tribunal")
    ap.add_argument("--period", default="10y")
    ap.add_argument("--out", default=None)
    ap.add_argument("--fetch", action="store_true", help="hit the network (yfinance)")
    args = ap.parse_args(argv)

    targets = [("SPY", "ETF"), ("QQQ", "ETF"), ("BTC-USD", "CRYPTO"), ("SOL-USD", "CRYPTO")]
    if not args.fetch:
        print("dry run: pass --fetch to download bars; logic is in simulate()")
        return 0

    report: dict = {"hypothesis": "H-2026-11-20-06", "period": args.period, "by_symbol": {}}
    for sym, klass in targets:
        try:
            bars = fetch(sym, args.period)
        except Exception as exc:  # network is not a code path we control
            report["by_symbol"][sym] = {"error": f"{type(exc).__name__}: {exc}"}
            continue
        rows = simulate(bars, sym, klass)
        report["by_symbol"][sym] = summarize(rows)
        report["by_symbol"][sym]["asset_class"] = klass
        report["by_symbol"][sym]["role"] = "target" if klass == "ETF" else "control"

    controls_ok = all(
        (v.get("mean_selection_alpha_pct") or 0) <= (report["by_symbol"].get("SPY", {}).get("mean_selection_alpha_pct") or 0)
        for k, v in report["by_symbol"].items() if v.get("role") == "control"
    ) if report["by_symbol"].get("SPY", {}).get("n") else None
    report["control_check"] = (
        "control shows alpha >= the equity target — the mechanism claim fails"
        if controls_ok is False else
        ("control below target — consistent with the gap-structure story"
         if controls_ok else "not evaluated")
    )

    text = json.dumps(report, indent=1)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
