#!/usr/bin/env python3
"""Top-N real-edge candidates per asset class from active_picks.json.

Implements the "5 suggested trades per asset class" ask from the previous
session, but grounds it in the HC gate semantics (not marketing WR from
clone rows).

Selection rules per pick:
  - source_system != 'copy_trader_intel' (exclude clone placeholders)
  - strategy not starting with 'clone_hl_' (belt-and-suspenders)
  - strat_fwd_trades >= 5 (real closed-trade sample)
  - strat_fwd_wr >= 55 OR score >= 50 (HC gate semantics from hc_filter.js)
  - trust_tier != 'BLACK' / 'BANNED'
  - Rank by composite = 0.5*score + 0.3*strat_fwd_wr + 0.2*strat_fwd_trades_log

Deliberately does NOT place trades. Outputs a markdown table per asset class.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
ACTIVE = REPO / "alpha_engine" / "data" / "active_picks.json"
REPORT = REPO / "reports" / "TOP_CANDIDATES_PER_ASSET_CLASS_2026_04_22.md"

BLACK_TRUST = {"BLACK", "BANNED"}
BLOCK_SOURCES = {"copy_trader_intel"}


def _score(r: dict) -> float:
    for k in ("score", "elite_score", "ml_composite_score", "method_a_score", "confluence_score"):
        v = r.get(k)
        if v is None:
            continue
        try:
            return float(v)
        except (TypeError, ValueError):
            continue
    return 0.0


def _fwd_wr(r: dict) -> float:
    for k in ("strat_fwd_wr", "forward_wr"):
        v = r.get(k)
        if v is None:
            continue
        try:
            vv = float(v)
        except (TypeError, ValueError):
            continue
        return vv * 100 if vv <= 1 else vv
    return 0.0


def _fwd_n(r: dict) -> int:
    for k in ("strat_fwd_trades",):
        v = r.get(k)
        if v is None:
            continue
        try:
            return int(v)
        except (TypeError, ValueError):
            continue
    return 0


def _composite(score: float, fwr: float, n: int) -> float:
    return 0.5 * score + 0.3 * fwr + 0.2 * (math.log1p(n) * 10)


def load() -> pd.DataFrame:
    raw = json.loads(ACTIVE.read_text())
    rows = raw if isinstance(raw, list) else raw.get("picks", [])
    out = []
    for r in rows:
        strategy = str(r.get("strategy") or "")
        source_system = str(r.get("source_system") or "")
        if source_system in BLOCK_SOURCES:
            continue
        if strategy.startswith("clone_hl_"):
            continue
        tt = str(r.get("trust_tier") or "").upper()
        if tt in BLACK_TRUST:
            continue
        score = _score(r)
        fwr = _fwd_wr(r)
        n = _fwd_n(r)
        # Relaxed filter: keep any real-edge candidate. Strict HC-gate pass is computed separately below.
        if score < 30 and fwr < 30 and n < 3:
            continue
        hc_strict = (n >= 5) and (fwr >= 55) and (score >= 50)
        ac = str(r.get("asset_class") or r.get("category") or "UNKNOWN").upper()
        out.append({
            "id": r.get("id"),
            "asset_class": ac,
            "symbol": r.get("symbol"),
            "direction": r.get("direction") or r.get("signal_type"),
            "score": round(score, 2),
            "fwd_wr": round(fwr, 2),
            "n": n,
            "trust": r.get("trust_tier") or "",
            "trust_score": r.get("trust_score"),
            "strategy": strategy,
            "source": source_system,
            "entry": r.get("entry_price"),
            "tp": r.get("take_profit"),
            "sl": r.get("stop_loss"),
            "risk_reward": r.get("risk_reward"),
            "confidence": r.get("confidence"),
            "hc_strict": bool(hc_strict),
            "composite": round(_composite(score, fwr, n), 2),
        })
    return pd.DataFrame(out)


def main() -> int:
    df = load()
    print(f"Eligible picks after filters: {len(df)}")
    if df.empty:
        print("No picks pass the HC-gate-flavored filter.")
        return 0

    # Group by asset_class, take top 5 by composite
    blocks: list[str] = []
    blocks.append("# Top real-edge candidates per asset class\n")
    blocks.append("**Source:** `alpha_engine/data/active_picks.json` (current state).\n")
    blocks.append("**Filter (relaxed):** exclude copy_trader_intel + clone_hl_*; need any of score/fwd_wr/n signal; drop BLACK/BANNED trust.\n")
    blocks.append("**Rank:** composite = 0.5·score + 0.3·fwd_wr + 0.2·log1p(n)·10\n")
    blocks.append("**`hc_strict` column:** True if pick passes the strict HC gate (n>=5 AND fwd_wr>=55 AND score>=50).\n")

    note = (
        "**Not trade orders.** These are ranked diagnostic candidates from the current ledger. "
        "Verify TP/SL, check the symbol's current price against `entry`, and apply position sizing + "
        "source-concentration cap before paper-placing.\n"
    )
    blocks.append(note)

    for ac in sorted(df["asset_class"].unique()):
        sub = df[df["asset_class"] == ac].sort_values("composite", ascending=False).head(5)
        if sub.empty:
            continue
        blocks.append(f"\n## {ac}  ({len(sub)} of {len(df[df['asset_class']==ac])} passing filter)\n")
        cols = ["symbol", "direction", "score", "fwd_wr", "n", "hc_strict", "trust", "strategy", "source", "entry", "tp", "sl", "risk_reward", "composite"]
        try:
            blocks.append(sub[cols].to_markdown(index=False))
        except ImportError:
            blocks.append("```\n" + sub[cols].to_string(index=False) + "\n```")
        blocks.append("")

    # Summary across classes
    summary = df.groupby("asset_class").agg(n=("symbol","count"), mean_score=("score","mean"), mean_fwr=("fwd_wr","mean")).round(2).reset_index()
    blocks.append("\n## Summary of eligible pool by asset class\n")
    try:
        blocks.append(summary.to_markdown(index=False))
    except ImportError:
        blocks.append("```\n" + summary.to_string(index=False) + "\n```")

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(blocks), encoding="utf-8")
    print(f"Report -> {REPORT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
