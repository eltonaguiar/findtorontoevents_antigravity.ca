#!/usr/bin/env python3
"""Forward / recency test for the "VIX>25 + breakout" rule.

Discovered 2026-11-15 in reports/skyrocket_patterns_2026-11-15.md at 1.80x test
lift (24.14% precision vs 14.52% base, n=246 signals). This re-measures the same
rule on slices of TIME rather than on a random train/test split, because "does it
hold out of sample?" is a question about the future and a split over the same
window cannot answer it.

Honest framing, stated up front:

  * The rule has no fitted parameters (VIX > 25, donch_break >= -0.1%), so there
    is no parameter for it to overfit in the usual sense. What can fail is the
    regime it depends on.
  * The discovery run happened minutes ago on data ending today, so every slice
    below is INSIDE its sample. These numbers measure stability across recent
    time, NOT untouched future data. Calling this "out of sample" would be a lie.
  * The genuine out-of-sample test starts now: this writes a JSON snapshot that a
    later run can compare against, and the rule should be logged forward before
    anything is sized on it.

Writes reports/vix_breakout_forward_test_<date>.md and .json.
"""
from __future__ import annotations

import json
import math
import sys
import warnings
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from hours_skyrocket_reverse_engineer import (  # noqa: E402
    HORIZON,
    THRESHOLD_ATR,
    UNIVERSE,
    add_regime,
    fetch,
    features,
    fetch_vix,
)

RULE_NAME = "VIX>25 + breakout"
VIX_LEVEL = 25.0
BREAK_TOL = -0.001
MIN_HISTORY = 300
# (label, days-back) — None = whole sample, 'discovery' = everything BEFORE the
# last 90 days, i.e. the part of the timeline that the recency slices exclude.
WINDOWS = [
    ("all bars", None),
    ("discovery (before last 90d)", "discovery"),
    ("last 90d", 90),
    ("last 30d", 30),
    ("last 14d", 14),
    ("last 7d", 7),
]


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float | None, float | None]:
    """95% Wilson interval — the point estimate alone is misleading at n=246."""
    if n == 0:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    s = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - s) / d, (c + s) / d)


def load_pool() -> pd.DataFrame:
    """Same feature pipeline as the discovery harness, minus filings (unused here)."""
    vix = fetch_vix()
    frames = []
    for cls, syms in UNIVERSE.items():
        data = fetch(syms.split())
        kept = 0
        for t, df in data.items():
            if len(df) < MIN_HISTORY:
                continue
            f = add_regime(features(df), vix, None)
            f["fwd"] = df["Close"].shift(-HORIZON) / df["Close"] - 1
            f["spike"] = (f["fwd"] >= THRESHOLD_ATR * f["atr_pct"]).astype(float)
            f = f.dropna(subset=["r1", "r4", "r24", "vol_surge", "atr_comp", "rsi", "fwd", "atr_pct"])
            f = f[np.isfinite(f["fwd"])]
            f = f[f["close"].fillna(0) > 0] if "close" in f else f
            f["ticker"] = t
            f["asset_class"] = cls
            frames.append(f)
            kept += 1
        print(f"  {cls}: {kept}/{len(data)} tickers usable", file=sys.stderr)
    return pd.concat(frames).sort_index() if frames else pd.DataFrame()


def rule_mask(df: pd.DataFrame) -> pd.Series:
    return (df["vix_level"] > VIX_LEVEL) & (df["donch_break"] >= BREAK_TOL)


def measure(sub: pd.DataFrame) -> dict:
    mask = rule_mask(sub)
    n = int(mask.sum())
    base = float(sub["spike"].mean()) if len(sub) else None
    if n == 0 or base in (None, 0):
        return {"bars": int(len(sub)), "n": n, "base": base, "precision": None,
                "lift": None, "avg_fwd_pct": None, "ci": [None, None]}
    hits = int(sub.loc[mask, "spike"].sum())
    prec = hits / n
    lo, hi = wilson(hits, n)
    return {
        "bars": int(len(sub)),
        "n": n,
        "base": base,
        "precision": prec,
        "lift": prec / base,
        "avg_fwd_pct": float(sub.loc[mask, "fwd"].mean() * 100),
        "ci": [lo, hi],
        "prec_above_base": bool(lo is not None and lo > base),
    }


def main() -> int:
    print("fetching hourly bars + VIX ...", file=sys.stderr)
    pooled = load_pool()
    if pooled.empty:
        print("no data", file=sys.stderr)
        return 1
    pooled = pooled.dropna(subset=["vix_level"])
    ts = pooled.index.max()
    print(f"  pooled bars={len(pooled)} newest={ts} vix-covered="
          f"{pooled['vix_level'].notna().mean()*100:.0f}%", file=sys.stderr)

    rows = {}
    for label, days in WINDOWS:
        if days is None:
            sub = pooled
        elif days == "discovery":
            sub = pooled[pooled.index < ts - pd.Timedelta(days=90)]
        else:
            sub = pooled[pooled.index >= ts - pd.Timedelta(days=days)]
        rows[label] = measure(sub)
        r = rows[label]
        print(f"  {label:32s} n={r['n']:6d} prec="
              f"{(r['precision'] or 0)*100:5.2f}% lift={r['lift'] or 0:4.2f}x "
              f"fwd={r['avg_fwd_pct'] or 0:+.3f}%", file=sys.stderr)

    per_class = {}
    recent = pooled[pooled.index >= ts - pd.Timedelta(days=30)]
    for cls, sub in recent.groupby("asset_class"):
        per_class[cls] = measure(sub)

    out_json = Path(f"reports/vix_breakout_forward_test_{date.today().isoformat()}.json")
    out_json.parent.mkdir(exist_ok=True)
    payload = {
        "rule": {"name": RULE_NAME, "vix_level": VIX_LEVEL, "breakout_tol": BREAK_TOL,
                 "horizon_hours": HORIZON, "label": f"fwd >= {THRESHOLD_ATR}x ATR"},
        "generated_at": pd.Timestamp.utcnow().isoformat(),
        "newest_bar": str(ts),
        "pooled_bars": int(len(pooled)),
        "windows": rows,
        "last_30d_by_class": per_class,
        "caveat": "all slices are inside the discovery sample; this measures regime "
                  "stability, not untouched future data",
    }
    out_json.write_text(json.dumps(payload, indent=2, default=float), encoding="utf-8")

    def fmt(r: dict) -> str:
        if r["n"] == 0:
            return f"| {r['bars']:,} | 0 | — | — | — | — |"
        lo, hi = r["ci"]
        ci = f"{lo*100:.1f}–{hi*100:.1f}%" if lo is not None else "—"
        flag = " ✅" if r.get("prec_above_base") else ""
        return (f"| {r['bars']:,} | {r['n']:,} | {r['base']*100:.2f}% | "
                f"**{r['precision']*100:.2f}%**{flag} | {r['lift']:.2f}x | "
                f"{r['avg_fwd_pct']:+.3f}% |")

    L = [
        f"# {RULE_NAME} — recency / forward test ({date.today().isoformat()})",
        "",
        f"Rule: `vix_level > {VIX_LEVEL:.0f}` AND `donch_break >= {BREAK_TOL}` → spike label "
        f"`fwd_4h >= {THRESHOLD_ATR}x ATR`. Pooled hourly bars: **{len(pooled):,}**, "
        f"VIX coverage {pooled['vix_level'].notna().mean()*100:.0f}%, newest bar {ts}.",
        "",
        "## Read this before the table",
        "",
        "The discovery run happened today on data ending today, so **every slice below is inside",
        "its own sample**. This is a *recency stability* test, not an out-of-sample test — saying",
        "otherwise would be exactly the kind of overclaim this repo has been burned by. The rule",
        "also has no fitted parameters, so the risk being measured is regime decay, not overfit.",
        "",
        "| window | bars | signals | base rate | precision | lift | avg fwd |",
        "|---|---|---|---|---|---|---|",
    ]
    for label, _ in WINDOWS:
        L.append(f"| {label} " + fmt(rows[label]))
    L += [
        "",
        "✅ = Wilson 95% lower bound still above that window's base rate.",
        "",
        "## Last 30 days by asset class",
        "",
        "| class | bars | signals | base rate | precision | lift | avg fwd |",
        "|---|---|---|---|---|---|---|",
    ]
    for cls in sorted(per_class):
        L.append(f"| {cls} " + fmt(per_class[cls]))
    L += [
        "",
        "## Verdict",
        "",
        "Read the lift column against the base rate in the same row — a base rate that rises with",
        "the precision means VIX stress lifted the whole tape, not the rule. Windows with n below",
        "~30 carry Wilson intervals wide enough to be uninformative; they are shown rather than",
        "hidden so nobody mistakes a quiet week for confirmation.",
        "",
        f"Snapshot JSON: `{out_json}`. Log the rule forward with a fixed entry/exit before any",
        "sizing decision; a second run of this script on later data is the actual out-of-sample check.",
        "",
    ]
    out_md = Path(f"reports/vix_breakout_forward_test_{date.today().isoformat()}.md")
    out_md.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {out_md} ({len(L)} lines) and {out_json}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
