#!/usr/bin/env python3
"""
Classify the 35-ish simulated portfolios in audit_dashboard/data/claudes_test_state.json
into REPEAT_WINNER / REPEAT_LOSER / MIXED / INSUFFICIENT_HISTORY buckets, and emit
"invert-or-mutate" action items per docs/MUTATION_THREE_AXIS_PROTOCOL.md.

Outputs:
  - audit_dashboard/data/portfolio_classification.json (sidecar consumed by page)
  - reports/<date>_portfolio_winner_loser_classification.md (human summary)

This is a SIDECAR generator — it does NOT touch the live dashboard HTML and is
explicitly allowed by CLAUDE.md ("Never run dashboard generators locally" applies
to the HTML generators, not to data-sidecar builders).
"""
from __future__ import annotations
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
STATE = REPO / "audit_dashboard" / "data" / "claudes_test_state.json"
OUT_JSON = REPO / "audit_dashboard" / "data" / "portfolio_classification.json"
OUT_MD = REPO / "reports" / f"{datetime.now().strftime('%Y-%m-%d')}_portfolio_winner_loser_classification.md"

# Bucket thresholds
WINNER_STREAK_DAYS = 3
LOSER_STREAK_DAYS = 3
DRAWDOWN_LOOKBACK = 30  # days


def _parse_dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def _daily_pnl_series(equity_history):
    """Group equity points by date, return list of (date, last_equity)."""
    by_day = {}
    for pt in equity_history or []:
        dt = _parse_dt(pt.get("time"))
        if not dt:
            continue
        d = dt.date().isoformat()
        by_day[d] = pt.get("equity")
    return sorted(by_day.items())


def _streaks(daily_series):
    """Compute trailing positive-day and negative-day streaks based on daily returns."""
    if len(daily_series) < 2:
        return 0, 0
    rets = []
    prev = daily_series[0][1]
    for d, e in daily_series[1:]:
        if prev and prev > 0:
            rets.append((d, (e - prev) / prev))
        prev = e
    # walk from the tail
    pos = neg = 0
    for _, r in reversed(rets):
        if r > 0 and neg == 0:
            pos += 1
        elif r < 0 and pos == 0:
            neg += 1
        else:
            break
    return pos, neg


def _max_drawdown(daily_series, lookback_days=30):
    if len(daily_series) < 2:
        return 0.0
    tail = daily_series[-lookback_days:]
    peak = tail[0][1] or 1.0
    mdd = 0.0
    for _, e in tail:
        if e > peak:
            peak = e
        if peak:
            dd = (e - peak) / peak * 100.0
            if dd < mdd:
                mdd = dd
    return abs(mdd)


def _mutation_actions(methodology: str, direction_skew: str | None) -> list[dict]:
    """Per docs/MUTATION_THREE_AXIS_PROTOCOL.md — produce 3 axis options."""
    invert = "SHORT" if direction_skew == "LONG_HEAVY" else ("LONG" if direction_skew == "SHORT_HEAVY" else "FLIP")
    return [
        {
            "axis": 1,
            "name": "invert_direction",
            "detail": f"Flip default bias to {invert}; re-run 30d window on inverted side only",
        },
        {
            "axis": 2,
            "name": "tighten_gates",
            "detail": f"Raise elite_score floor by +10 for methodology '{methodology}'; require sys_pf>=1.6 entry filter",
        },
        {
            "axis": 3,
            "name": "substitute_regime",
            "detail": "Gate entries on regime: BULL-only for momentum/score, BEAR-only for contrarian/anti_meme",
        },
    ]


def _winner_actions() -> list[dict]:
    return [
        {"name": "scale_up_50pct", "detail": "Increase position_pct by 50% (cap at 0.20) for 14d trial"},
        {"name": "clone_to_new_universe", "detail": "Spawn shadow portfolio applying same methodology to ETF + COMMODITY classes"},
    ]


def _direction_skew(positions: list) -> str | None:
    if not positions:
        return None
    longs = sum(1 for p in positions if p.get("direction") == "LONG")
    shorts = sum(1 for p in positions if p.get("direction") == "SHORT")
    total = longs + shorts
    if total == 0:
        return None
    if longs / total >= 0.7:
        return "LONG_HEAVY"
    if shorts / total >= 0.7:
        return "SHORT_HEAVY"
    return "BALANCED"


def classify_portfolio(pid: str, p: dict) -> dict:
    initial = p.get("initial_capital", 10000) or 10000
    equity = p.get("equity", initial) or initial
    pct = (equity - initial) / initial * 100.0
    eh = p.get("equity_history", [])
    daily = _daily_pnl_series(eh)
    pos_streak, neg_streak = _streaks(daily)
    mdd30 = _max_drawdown(daily, DRAWDOWN_LOOKBACK)

    closed = p.get("closed", []) or []
    wins = p.get("wins", 0)
    losses = p.get("losses", 0)
    wr = (wins / (wins + losses) * 100.0) if (wins + losses) > 0 else None
    skew = _direction_skew((p.get("positions") or []) + closed[-20:])

    if len(daily) < 5:
        bucket = "INSUFFICIENT_HISTORY"
    elif pos_streak >= WINNER_STREAK_DAYS:
        # Sustained recent winning days = repeat winner pattern, even if still
        # climbing out of an earlier drawdown.
        bucket = "REPEAT_WINNER"
    elif neg_streak >= LOSER_STREAK_DAYS:
        bucket = "REPEAT_LOSER"
    else:
        bucket = "MIXED"

    return {
        "id": pid,
        "name": p.get("name", pid),
        "methodology": p.get("methodology"),
        "initial_capital": initial,
        "current_equity": round(equity, 2),
        "current_equity_vs_initial_pct": round(pct, 3),
        "high_water_mark": p.get("high_water_mark"),
        "max_drawdown_pct_alltime": p.get("max_drawdown_pct"),
        "max_drawdown_pct_30d": round(mdd30, 3),
        "repeat_winner_streak": pos_streak,
        "repeat_loser_streak": neg_streak,
        "win_rate_pct": round(wr, 2) if wr is not None else None,
        "wins": wins,
        "losses": losses,
        "closed_trades": len(closed),
        "open_positions": len(p.get("positions") or []),
        "direction_skew": skew,
        "daily_points_observed": len(daily),
        "verdict": bucket,
        "recommended_actions": (
            _mutation_actions(p.get("methodology") or "unknown", skew)
            if bucket == "REPEAT_LOSER"
            else _winner_actions()
            if bucket == "REPEAT_WINNER"
            else []
        ),
    }


def main():
    if not STATE.exists():
        print(f"ERROR: {STATE} not found", file=sys.stderr)
        sys.exit(1)
    with STATE.open() as f:
        data = json.load(f)

    portfolios = data
    if "portfolios" in data and isinstance(data["portfolios"], dict):
        portfolios = data["portfolios"]

    results = []
    for pid, p in portfolios.items():
        if not isinstance(p, dict) or "equity" not in p:
            continue
        results.append(classify_portfolio(pid, p))

    by_bucket = defaultdict(list)
    for r in results:
        by_bucket[r["verdict"]].append(r)

    # Sort: winners by streak desc then pct desc; losers by streak desc then pct asc
    by_bucket["REPEAT_WINNER"].sort(key=lambda r: (-r["repeat_winner_streak"], -r["current_equity_vs_initial_pct"]))
    by_bucket["REPEAT_LOSER"].sort(key=lambda r: (-r["repeat_loser_streak"], r["current_equity_vs_initial_pct"]))
    by_bucket["MIXED"].sort(key=lambda r: -r["current_equity_vs_initial_pct"])

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "audit_dashboard/data/claudes_test_state.json",
        "thresholds": {
            "winner_streak_days": WINNER_STREAK_DAYS,
            "loser_streak_days": LOSER_STREAK_DAYS,
            "drawdown_lookback_days": DRAWDOWN_LOOKBACK,
        },
        "counts": {k: len(v) for k, v in by_bucket.items()},
        "portfolios": results,
        "by_bucket": dict(by_bucket),
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSON.open("w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"Wrote {OUT_JSON} ({OUT_JSON.stat().st_size:,} bytes)")

    # Markdown report
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Portfolio Winner/Loser Classification — {datetime.now().strftime('%Y-%m-%d')}",
        "",
        f"Source: `{STATE.relative_to(REPO)}`  ",
        f"Generated: {out['generated_at']}  ",
        f"Total portfolios: **{len(results)}**  ",
        "",
        "## Bucket counts",
        "",
    ]
    for k in ["REPEAT_WINNER", "REPEAT_LOSER", "MIXED", "INSUFFICIENT_HISTORY"]:
        lines.append(f"- **{k}**: {len(by_bucket.get(k, []))}")
    lines.append("")

    for bucket, label in [
        ("REPEAT_WINNER", "Repeat Winners (scale-up candidates)"),
        ("REPEAT_LOSER", "Repeat Losers (invert-or-mutate per docs/MUTATION_THREE_AXIS_PROTOCOL.md)"),
        ("MIXED", "Mixed (hold)"),
        ("INSUFFICIENT_HISTORY", "Insufficient History"),
    ]:
        lst = by_bucket.get(bucket, [])
        lines.append(f"## {label} — n={len(lst)}")
        lines.append("")
        if not lst:
            lines.append("_None._")
            lines.append("")
            continue
        lines.append("| Portfolio | Methodology | Equity vs init % | Streak (+ / -) | MDD30d | WR% | Closed | Action |")
        lines.append("|---|---|---:|---:|---:|---:|---:|---|")
        for r in lst[:50]:
            streak = f"{r['repeat_winner_streak']} / {r['repeat_loser_streak']}"
            wr = f"{r['win_rate_pct']:.1f}" if r['win_rate_pct'] is not None else "--"
            action_summary = "; ".join(a.get("name", "") for a in r["recommended_actions"]) or "—"
            lines.append(
                f"| `{r['id']}` | {r['methodology']} | {r['current_equity_vs_initial_pct']:+.2f}% | {streak} | {r['max_drawdown_pct_30d']:.2f}% | {wr} | {r['closed_trades']} | {action_summary} |"
            )
        lines.append("")

    with OUT_MD.open("w") as f:
        f.write("\n".join(lines))
    print(f"Wrote {OUT_MD}")

    # Console summary
    print("\nTop 3 REPEAT_WINNERs:")
    for r in by_bucket.get("REPEAT_WINNER", [])[:3]:
        print(f"  - {r['id']:30s} methodology={r['methodology']:20s} streak=+{r['repeat_winner_streak']}d  equity={r['current_equity_vs_initial_pct']:+.2f}%")
    print("\nTop 3 REPEAT_LOSERs:")
    for r in by_bucket.get("REPEAT_LOSER", [])[:3]:
        print(f"  - {r['id']:30s} methodology={r['methodology']:20s} streak=-{r['repeat_loser_streak']}d  equity={r['current_equity_vs_initial_pct']:+.2f}%")


if __name__ == "__main__":
    main()
