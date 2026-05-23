#!/usr/bin/env python3
"""
Run 15m TA scan over SYMBOLS_DASHBOARD and write a review-oriented Markdown doc:
patterns, implied direction, certainty from multi-signal agreement.

  set SCAN_UNIVERSE=dashboard   # optional; scanner uses dashboard list when set
  python tools/build_dashboard_universe_review_md.py

Output: tools/dashboard_universe_15m_signal_review.md
"""

from __future__ import annotations

import importlib.util
import re
import sys
import time
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
_ROOT = _TOOLS.parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

_spec = importlib.util.spec_from_file_location("scan15", _TOOLS / "scan_multi_symbol_15m.py")
assert _spec and _spec.loader
_scan = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_scan)


def _votes_from_patterns(lines: list[str]) -> tuple[int, int, list[str]]:
    bull = bear = 0
    names: list[str] = []
    for line in lines:
        if "[BULLISH]" in line:
            bull += 1
            names.append(line.strip())
        elif "[BEARISH]" in line:
            bear += 1
            names.append(line.strip())
    return bull, bear, names


def _vote_trend(ma_lines: list[str]) -> tuple[int, str]:
    for line in ma_lines:
        if "Bullish stack" in line:
            return 1, "Bullish EMA9>21>50"
        if "Bearish stack" in line:
            return -1, "Bearish EMA9<21<50"
        if "Mixed/Choppy" in line:
            return 0, "Mixed/choppy MA stack"
    return 0, "MA stack unclear"


def _vote_macro(ma_lines: list[str]) -> tuple[int, str]:
    for line in ma_lines:
        if "ABOVE SMA200" in line and "macro bullish" in line:
            return 1, "Price above SMA200 (macro long)"
        if "BELOW SMA200" in line and "macro bearish" in line:
            return -1, "Price below SMA200 (macro short)"
    return 0, "SMA200 state unclear"


def _parse_close(sr_lines: list[str]) -> float | None:
    for line in sr_lines:
        m = re.search(r"Current price:\s*([0-9.eE+-]+)", line)
        if m:
            return float(m.group(1))
    return None


def _certainty_label(votes: list[tuple[int, str]]) -> tuple[str, str]:
    """votes: list of (-1,0,+1) components with labels."""
    non_zero = [v for v, _ in votes if v != 0]
    if not non_zero:
        return "LOW", "No clear directional components (all neutral)."
    s = sum(non_zero)
    if all(v > 0 for v in non_zero):
        n = len(non_zero)
        if n >= 3:
            return "HIGH", f"All {n} components align LONG."
        return "MEDIUM", f"{n} component(s) align LONG; no opposing votes."
    if all(v < 0 for v in non_zero):
        n = len(non_zero)
        if n >= 3:
            return "HIGH", f"All {n} components align SHORT."
        return "MEDIUM", f"{n} component(s) align SHORT; no opposing votes."
    pos = sum(1 for v in non_zero if v > 0)
    neg = sum(1 for v in non_zero if v < 0)
    return "LOW", f"Conflict: {pos} long-leaning vs {neg} short-leaning among non-neutral signals."


def _pattern_vote(bull: int, bear: int) -> tuple[int, str]:
    if bull == 0 and bear == 0:
        return 0, "No candlestick pattern on latest bar"
    if bull > bear:
        return 1, f"Candle patterns lean LONG ({bull} bull vs {bear} bear)"
    if bear > bull:
        return -1, f"Candle patterns lean SHORT ({bear} bear vs {bull} bull)"
    return 0, f"Patterns mixed ({bull} bull, {bear} bear)"


def _implied_direction(score: int) -> str:
    if score >= 2:
        return "LONG"
    if score <= -2:
        return "SHORT"
    return "NEUTRAL / WAIT"


def _fmt_price(x: float | None) -> str:
    if x is None:
        return "—"
    ax = abs(x)
    if ax >= 1:
        s = f"{x:.8f}".rstrip("0").rstrip(".")
        return s or "0"
    if ax >= 0.01:
        return f"{x:.6f}".rstrip("0").rstrip(".")
    return f"{x:.12f}".rstrip("0").rstrip(".")


def build_rows() -> list[dict]:
    rows: list[dict] = []
    for sym in _scan.SYMBOLS_DASHBOARD:
        r = _scan.scan_symbol(sym)
        if "error" in r:
            rows.append(
                {
                    "symbol": sym,
                    "error": "; ".join(s.strip() for s in r["error"]),
                }
            )
            continue
        ma = r["moving_averages"]
        pat_lines = r["patterns"]
        sr = r["support_resistance"]
        bull, bear, pat_detail = _votes_from_patterns(pat_lines)
        pv, pnote = _pattern_vote(bull, bear)
        tv, tnote = _vote_trend(ma)
        mv, mnote = _vote_macro(ma)
        votes = [(pv, pnote), (tv, tnote), (mv, mnote)]
        score = pv + tv + mv
        cert_label, cert_note = _certainty_label(votes)
        close = _parse_close(sr)
        rows.append(
            {
                "symbol": sym,
                "close_15m": close,
                "pattern_note": pnote,
                "pattern_detail": pat_detail,
                "trend_note": tnote,
                "macro_note": mnote,
                "score": score,
                "direction": _implied_direction(score),
                "certainty": cert_label,
                "certainty_note": cert_note,
            }
        )
        if _scan.SCAN_SLEEP_SEC > 0:
            time.sleep(_scan.SCAN_SLEEP_SEC)
    return rows


def main() -> int:
    ts = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    out_path = _TOOLS / "dashboard_universe_15m_signal_review.md"

    rows = build_rows()

    lines: list[str] = []
    lines.append("# Dashboard universe — 15m signal review (TA scan)")
    lines.append("")
    lines.append(f"**Generated:** {ts}")
    lines.append(f"**Source:** `tools/scan_multi_symbol_15m.py` on **{_scan.EXCHANGE_ID}** ({_scan.MARKET_TYPE}), timeframe **{_scan.TIMEFRAME}**.")
    lines.append(
        "**Universe note:** Symbols match your dashboard screenshots (deduped). "
        "`RENDER/USDT` is used for the old RNDR ticker on Bybit spot. "
        "Some bases (e.g. ZEC) may not list on Bybit spot — that row will show **ERROR**; use another exchange or drop the symbol."
    )
    lines.append("")
    lines.append("## How to use this for later review")
    lines.append("")
    lines.append("1. **Anchor:** Each row records the **last closed 15m close** (approximate scan-time price) under **Anchor price**.")
    lines.append("2. **Implied direction** is **not** a trade recommendation: it aggregates (a) latest-bar candlestick patterns, (b) EMA9/21/50 stack, (c) price vs SMA200.")
    lines.append("3. **Certainty** reflects **how many of those three agree** in the same direction; conflicts are labeled LOW.")
    lines.append("4. When you ask for a review, provide **current price** (or ask the assistant to fetch it): compare vs anchor to judge whether **follow-through** matched the implied bias (LONG = higher, SHORT = lower, NEUTRAL = no strong edge).")
    lines.append("")
    lines.append("## Summary table")
    lines.append("")
    lines.append("| Symbol | Patterns (latest bar) | Trend / macro | Implied direction | Certainty | Anchor price |")
    lines.append("|--------|------------------------|---------------|-------------------|-----------|--------------|")

    for row in rows:
        if "error" in row:
            err = row["error"].replace("|", "\\|")
            lines.append(f"| {row['symbol']} | — | — | **ERROR** | — | `{err}` |")
            continue
        pat_short = row["pattern_note"].replace("|", "\\|")
        trend_macro = f"{row['trend_note']}; {row['macro_note']}".replace("|", "\\|")
        ap = _fmt_price(row["close_15m"])
        lines.append(
            f"| {row['symbol']} | {pat_short} | {trend_macro} | **{row['direction']}** | **{row['certainty']}** | {ap} |"
        )

    lines.append("")
    lines.append("## Per-symbol detail")
    lines.append("")

    for row in rows:
        lines.append(f"### {row['symbol']}")
        lines.append("")
        if "error" in row:
            lines.append(f"- **Fetch error:** {row['error']}")
            lines.append("")
            continue
        lines.append(f"- **Implied direction:** {row['direction']} (component score sum: {row['score']})")
        lines.append(f"- **Certainty:** {row['certainty']} — {row['certainty_note']}")
        lines.append(f"- **Anchor price (15m close at scan):** {row['close_15m']}")
        lines.append(f"- **Trend:** {row['trend_note']}")
        lines.append(f"- **Macro:** {row['macro_note']}")
        lines.append(f"- **Patterns:** {row['pattern_note']}")
        if row["pattern_detail"]:
            lines.append("- **Pattern lines:**")
            for p in row["pattern_detail"]:
                lines.append(f"  - `{p.strip()}`")
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
