#!/usr/bin/env python3
"""beta_hedge_selection_alpha.py — is our negative selection alpha beta or noise?

H-2026-11-20-04. Selection alpha is currently -0.2763%/trade
(CI [-0.506, -0.043], n=3192): we do worse than buy-and-hold over the same
window. Two explanations are observationally identical until hedged:

  (a) the picks carry information but time the market badly -> hedging the
      market-factor exposure recovers positive alpha;
  (b) the picks carry no information -> hedging does not recover it.

This tool distinguishes them. For each closed pick it estimates the symbol's
beta to the market from returns strictly BEFORE entry, hedges the market leg
over the holding window, and re-measures.

Design rules:
  - Point-in-time only. Beta uses bars ending at entry; the hedge uses the
    entry..exit window. No bar is ever used twice.
  - A pick with too few pre-entry bars is skipped and counted, never silently
    dropped and never given a default beta of 1.
  - If no class has enough hedged rows, this returns an explicit
    `inconclusive` with a reason instead of a None or a zero.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

MIN_BETA_BARS = 20          # pre-entry returns needed to estimate beta
MIN_HEDGED_ROWS = 30        # below this a class verdict is inconclusive
BOOT = 2000
SEED = 11

Bar = tuple[str, float]    # (iso date, close)


# ─────────────────────────────────────────────────────────────── primitives ──
def returns(closes: Sequence[float]) -> list[float]:
    """Simple returns between consecutive closes."""
    return [b / a - 1.0 for a, b in zip(closes, closes[1:]) if a]


def beta(sym_ret: Sequence[float], mkt_ret: Sequence[float]) -> float | None:
    """OLS slope of symbol on market. None when variance is degenerate."""
    n = min(len(sym_ret), len(mkt_ret))
    if n < MIN_BETA_BARS:
        return None
    s, m = list(sym_ret[-n:]), list(mkt_ret[-n:])
    ms, mm = sum(s) / n, sum(m) / n
    cov = sum((a - ms) * (b - mm) for a, b in zip(s, m)) / n
    var = sum((b - mm) ** 2 for b in m) / n
    if var <= 0:
        return None
    return cov / var


def window_return(bars: Sequence[Bar], start: str, end: str) -> float | None:
    """Return from the last bar at/before start to the last bar at/before end.

    Longest-match on ISO dates so it never needs a full calendar.
    """
    lo = hi = None
    for day, close in bars:
        if day <= start:
            lo = close
        if day <= end:
            hi = close
    if lo is None or hi is None or not lo:
        return None
    # a flat window is a legitimate 0.0 return — never treat it as missing
    return hi / lo - 1.0


def bootstrap_ci(values: Sequence[float], n_boot: int = BOOT,
                 seed: int = SEED) -> tuple[float, float] | None:
    """Percentile bootstrap CI for the mean."""
    if len(values) < 5:
        return None
    rng = __import__("random").Random(seed)
    n = len(values)
    means = sorted(sum(values[rng.randrange(n)] for _ in range(n)) / n
                   for _ in range(n_boot))
    return means[int(0.025 * n_boot)], means[int(0.975 * n_boot) - 1]


# ──────────────────────────────────────────────────────────── the measurement ─
def hedged_alpha(
    picks: Iterable[dict],
    bars_for: Callable[[str], Sequence[Bar]],
    market_bars: Sequence[Bar],
    factor_default: Callable[[dict], str] | None = None,
) -> dict[str, Any]:
    """Per-class unhedged vs beta-hedged selection alpha.

    `bars_for(symbol)` returns that symbol's bars; `market_bars` is the market
    proxy. `factor_default(pick)` maps a pick to a fallback synthetic series
    name when its own symbol has no bars (e.g. a sector ETF).
    """
    by_class: dict[str, dict[str, list[float]]] = {}
    skipped = {"no_bars": 0, "no_beta": 0, "no_window": 0, "no_entry_exit": 0}

    for p in picks:
        klass = (p.get("asset_class") or "UNKNOWN").upper()
        entry, exit_ = p.get("entry_time") or p.get("timestamp"), p.get("closed_at")
        pnl = p.get("pnl_pct")
        if entry is None or exit_ is None or pnl is None:
            skipped["no_entry_exit"] += 1
            continue
        entry, exit_ = str(entry)[:10], str(exit_)[:10]
        symbol = p.get("symbol")
        sym_bars = list(bars_for(symbol)) if symbol else []
        if not sym_bars and factor_default is not None:
            sym_bars = list(bars_for(factor_default(p)))
        if not sym_bars:
            skipped["no_bars"] += 1
            continue

        # beta from pre-entry returns ONLY — point in time
        pre = [(d, c) for d, c in sym_bars if d <= entry]
        mpre = [(d, c) for d, c in market_bars if d <= entry]
        b = beta(returns([c for _, c in pre]),
                 returns([c for _, c in mpre]))
        if b is None:
            skipped["no_beta"] += 1
            continue

        mret = window_return(market_bars, entry, exit_)
        if mret is None:
            skipped["no_window"] += 1
            continue

        direction = (p.get("direction") or p.get("side") or "LONG").upper()
        signed_beta = b if direction.startswith("L") else -b
        hedged = float(pnl) - signed_beta * mret * 100.0   # pct units

        cell = by_class.setdefault(klass, {"raw": [], "hedged": [], "betas": []})
        cell["raw"].append(float(pnl))
        cell["hedged"].append(hedged)
        cell["betas"].append(b)

    classes: dict[str, Any] = {}
    for klass, cell in sorted(by_class.items()):
        n = len(cell["hedged"])
        raw_m = sum(cell["raw"]) / n
        hed_m = sum(cell["hedged"]) / n
        ci = bootstrap_ci(cell["hedged"])
        rec = {
            "n": n,
            "mean_beta": round(sum(cell["betas"]) / n, 3),
            "unhedged_alpha_pct": round(raw_m, 4),
            "hedged_alpha_pct": round(hed_m, 4),
            "delta_pct": round(hed_m - raw_m, 4),
            "hedged_ci95": [round(ci[0], 4), round(ci[1], 4)] if ci else None,
        }
        if n < MIN_HEDGED_ROWS or ci is None:
            rec["verdict"] = (f"inconclusive — only {n} hedged rows "
                              f"(need {MIN_HEDGED_ROWS})")
        elif ci[0] > 0:
            rec["verdict"] = "RECOVERED — beta hedging yields positive alpha"
        elif ci[1] < 0:
            rec["verdict"] = "NOT RECOVERED — alpha stays negative after hedging"
        else:
            rec["verdict"] = "inconclusive — hedged CI spans zero"
        classes[klass] = rec

    if not classes:
        return {"available": False,
                "reason": "no class produced a hedged row",
                "skipped": skipped}

    return {
        "available": True,
        "schema": "beta_hedge_selection_alpha.v1",
        "market_proxy_bars": len(market_bars),
        "min_beta_bars": MIN_BETA_BARS,
        "classes": classes,
        "skipped": skipped,
        "doctrine": ("A hedged CI that spans zero is inconclusive, not a win. "
                     "Beta is estimated pre-entry only; a pick with no bar "
                     "history is skipped and counted, never defaulted to 1."),
    }


# ────────────────────────────────────────────────────────────────────── CLI ──
def _bars_from_json(path: str) -> list[Bar]:
    doc = json.load(open(path))
    rows = doc if isinstance(doc, list) else doc.get("bars") or doc.get("data") or []
    out: list[Bar] = []
    for r in rows:
        if isinstance(r, dict):
            day = str(r.get("date") or r.get("day") or r.get("timestamp") or "")[:10]
            close = r.get("close") or r.get("price") or r.get("c")
            if day and close is not None:
                out.append((day, float(close)))
    return sorted(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--picks", required=True, help="closed picks JSON (list or {picks:[...]})")
    ap.add_argument("--bars-dir", required=True, help="directory of <SYMBOL>.json bar files")
    ap.add_argument("--market", default="SPY", help="market proxy symbol file")
    ap.add_argument("--out", help="write the report here instead of stdout")
    a = ap.parse_args(argv)

    doc = json.load(open(a.picks))
    picks = doc if isinstance(doc, list) else doc.get("picks") or []
    bars_dir = Path(a.bars_dir)

    cache: dict[str, list[Bar]] = {}

    def bars_for(sym: str) -> Sequence[Bar]:
        if sym not in cache:
            f = bars_dir / f"{sym}.json"
            cache[sym] = _bars_from_json(str(f)) if f.exists() else []
        return cache[sym]

    res = hedged_alpha(picks, bars_for, bars_for(a.market))
    text = json.dumps(res, indent=2)
    if a.out:
        Path(a.out).write_text(text + "\n")
        print(f"wrote {a.out}")
    else:
        print(text)
    return 0 if res.get("available") else 3


if __name__ == "__main__":
    raise SystemExit(main())
