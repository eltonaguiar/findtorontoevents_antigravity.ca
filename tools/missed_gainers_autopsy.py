#!/usr/bin/env python3
"""Missed-Gainers Autopsy — what moved that we didn't have picks for?

Symmetric to tools/pick_traceback.py.  Answers the blind-spot question:

  "The market moved big on X symbols.  Did our system emit picks for them?"

Data flow:
  1. Load ALL our historically emitted picks (active_picks.json + closed_picks.json)
  2. Fetch market top movers via api_failover.fetch_ticker_24h() (multi-source
     failover: Binance → Bybit → CoinGecko → KuCoin) — primarily covers CRYPTO.
     For EQUITY / COMMODITY, the report notes limited data.
  3. Cross-reference: for each top mover, check if we had any pick (active OR closed)
     for that symbol.  If not, it is a "hard miss."
  4. If yes, check if the pick's direction matches the move (LONG on up-mover
     = caught; SHORT on up-mover = direction-missed).
  5. Output a Markdown report with recall @ top-N, per-strategy breakdown,
     per-confidence-bin miss analysis, and blind-spot patterns.

CLI:
    python tools/missed_gainers_autopsy.py [--days 7] [--top 50]
        [--out reports/missed_gainers.md]

Stdlib + api_failover (no pip install needed).
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Data paths
# ---------------------------------------------------------------------------
CLOSED   = ROOT / "alpha_engine" / "data" / "closed_picks.json"
ACTIVE   = ROOT / "alpha_engine" / "data" / "active_picks.json"

# ---------------------------------------------------------------------------
# Stablecoins / leveraged tokens to exclude from top-mover list
# ---------------------------------------------------------------------------
# Minimum 24h quote volume (USDT) — skip illiquid coins whose % moves are noise
MIN_VOLUME_USDT: float = 500_000

EXCLUDE_SYMBOLS: set[str] = {
    "USDCUSDT", "BUSDUSDT", "TUSDUSDT", "DAIUSDT", "FDUSDUSDT",
    "USDPUSDT", "EURUSDT", "GBPUSDT", "AEURUSDT", "USTCUSDT",
    "WBTCUSDT", "WBETHUSDT",
    "UUSDT", "USD1USDT", "USDEUSDT", "XUSDUSDT", "STABLEUSDT",
    "RLUSDUSDT", "BFUSDUSDT", "PYUSDUSDT", "GUSDUSDT", "FRAXUSDT",
}


# ===========================================================================
# 1.  Load pick history
# ===========================================================================

def _load_picks(path: Path) -> list[dict]:
    """Load a pick JSON file (may be list or dict with 'picks'/'active'/'closed' key)."""
    if not path.exists():
        return []
    d = json.loads(path.read_text(encoding="utf-8"))
    picks = d if isinstance(d, list) else (
        d.get("picks") or d.get("active") or d.get("closed") or []
    )
    return [p for p in picks if isinstance(p, dict)]


def _is_won(p: dict) -> bool | None:
    """Determine if a resolved pick was won/lost."""
    s = str(p.get("status") or "").upper()
    if s == "WON":
        return True
    if s == "LOST":
        return False
    v = p.get("pnl_pct")
    if v is None:
        return None
    return float(v) > 0


def _resolved_date(p: dict) -> str:
    return str(p.get("resolved_at") or p.get("exit_date") or p.get("timestamp") or "")


# ===========================================================================
# 2.  Build pick lookup: symbol -> set of strategies + direction info
# ===========================================================================

def build_pick_lookup(
    active: list[dict],
    closed: list[dict],
    days: int,
) -> dict[str, dict[str, Any]]:
    """Build symbol → {strategy, direction, count_won, count_lost, ...}.

    Only considers picks resolved within the last `days` days for the lookback,
    but ALL active picks are included regardless of age.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()[:10]

    lookup: dict[str, dict[str, Any]] = {}

    # Active picks — include all regardless of age
    for p in active:
        sym = p.get("symbol", "").upper()
        if not sym:
            continue
        sfy = p.get("strategy") or p.get("source_system") or "?"
        direction = p.get("direction") or p.get("signal_type") or "LONG"

        entry = lookup.setdefault(sym, {"strategies": set(), "active_directions": set(), "recency": "active"})
        entry["strategies"].add(str(sfy))
        entry["active_directions"].add(str(direction).upper())

    # Closed picks — only within window
    for p in closed:
        if _resolved_date(p)[:10] < cutoff:
            continue
        sym = p.get("symbol", "").upper()
        if not sym:
            continue
        sfy = p.get("strategy") or p.get("source_system") or "?"
        direction = p.get("direction") or p.get("signal_type") or "LONG"

        entry = lookup.setdefault(sym, {"strategies": set(), "active_directions": set(), "recency": "historical"})
        entry["strategies"].add(str(sfy))
        entry["active_directions"].add(str(direction).upper())
        if _is_won(p) is True:
            entry["won"] = entry.get("won", 0) + 1
        elif _is_won(p) is False:
            entry["lost"] = entry.get("lost", 0) + 1

    # Convert sets to sorted lists for JSON / output
    for v in lookup.values():
        v["strategies"] = sorted(v["strategies"])
        v["active_directions"] = sorted(v["active_directions"])
        v["won"] = v.get("won", 0)
        v["lost"] = v.get("lost", 0)

    return lookup


# ===========================================================================
# 3.  Fetch market top movers (via api_failover)
# ===========================================================================

def fetch_top_movers(top_n: int = 50) -> list[dict]:
    """Fetch 24h top movers from Binance (multi-mirror) via api_failover.

    Returns list of dicts sorted by |priceChangePercent| descending:
        symbol, price_change_pct, price, volume_usdt, source
    """
    # Try using the project's battle-tested api_failover module
    try:
        sys.path.insert(0, str(ROOT))
        from alpha_engine.api_failover import fetch_ticker_24h
        raw = fetch_ticker_24h()
        source = "api_failover"
    except Exception:
        # Fallback: direct Binance fetch (stdlib only)
        raw = _binance_fallback()
        source = "binance_direct"

    if raw is None:
        print("  [WARN] api_failover returned None — all sources exhausted", file=sys.stderr)
        return []
    if not isinstance(raw, list):
        print(f"  [WARN] No ticker data returned from {source}", file=sys.stderr)
        return []

    movers: list[dict] = []
    for t in raw:
        sym: str = (t.get("symbol") or "").upper()
        if not sym.endswith("USDT"):
            continue
        if sym in EXCLUDE_SYMBOLS:
            continue
        base = sym.replace("USDT", "")
        if len(base) < 2 or base.isdigit():
            continue
        if any(tag in sym for tag in ("UP", "DOWN", "BEAR", "BULL", "3L", "3S")):
            continue

        try:
            pct = float(t.get("priceChangePercent", 0))
            price = float(t.get("lastPrice", 0))
            vol = float(t.get("quoteVolume", 0))
        except (ValueError, TypeError):
            continue
        if price <= 0:
            continue
        if vol < MIN_VOLUME_USDT:
            continue

        movers.append({
            "symbol": sym,
            "price_change_pct": round(pct, 2),
            "price": price,
            "volume_usdt": round(vol, 0),
            "abs_change": abs(pct),
        })

    movers.sort(key=lambda x: x["abs_change"], reverse=True)
    return movers[:top_n]


def _binance_fallback() -> list[dict] | None:
    """Direct Binance fetch fallback (stdlib only)."""
    import urllib.request
    mirrors = [
        "https://data-api.binance.vision",
        "https://api.binance.com",
        "https://api1.binance.com",
    ]
    headers = {"User-Agent": "MissedGainersAutopsy/1.0"}
    for base in mirrors:
        try:
            req = urllib.request.Request(f"{base}/api/v3/ticker/24hr", headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            continue
    return None


# ===========================================================================
# 4.  Cross-reference: classify each top mover
# ===========================================================================
# Classification for a top mover vs our pick universe:
#
#   "CAUGHT"    — we have (or had) an active/historical pick for this symbol,
#                 and the pick direction matches the move
#   "DIRECTION_MISS" — we had a pick but in the wrong direction (SHORT on up-mover)
#   "HARD_MISS" — we never had any pick for this symbol (active or closed)
#

def classify_movers(
    movers: list[dict],
    lookup: dict[str, dict[str, Any]],
) -> list[dict]:
    """Classify each top mover against our pick universe.

    Returns list with classification, strategy info, and WR context.
    """
    classified: list[dict] = []
    for m in movers:
        sym = m["symbol"]
        entry = lookup.get(sym)
        is_up = m["price_change_pct"] > 0

        if entry is None:
            cls = "HARD_MISS"
            strategies = []
            direction_hint = None
            wr = None
        else:
            strategies = entry.get("strategies", [])
            active_dirs = entry.get("active_directions", [])
            direction_hint = " / ".join(active_dirs) if active_dirs else "?"

            # Determine if any direction matches the move
            has_long = "LONG" in active_dirs or "BUY" in active_dirs
            has_short = "SHORT" in active_dirs or "SELL" in active_dirs
            if (is_up and has_long) or (not is_up and has_short):
                cls = "CAUGHT"
            else:
                cls = "DIRECTION_MISS"

            won = entry.get("won", 0)
            lost = entry.get("lost", 0)
            total = won + lost
            wr = round(won / total, 3) if total > 0 else None

        classified.append({
            "symbol": sym,
            "price_change_pct": m["price_change_pct"],
            "volume_usdt": m["volume_usdt"],
            "price": m["price"],
            "classification": cls,
            "strategies": strategies,
            "direction_hint": direction_hint,
            "wr": wr,
            "is_loser": m["price_change_pct"] < 0,
        })

    return classified


# ===========================================================================
# 5.  Aggregation helpers
# ===========================================================================

def _fmt_pct(v: float) -> str:
    return f"{v * 100:.1f}%" if v < 1 else f"{v:.1f}%"


def recall_stats(classified: list[dict], top_n: int) -> dict:
    """Compute recall @ various N thresholds."""
    stats: dict[str, Any] = {}
    for n in (10, 25, 50, 100):
        if n > len(classified):
            break
        batch = classified[:n]
        caught = sum(1 for c in batch if c["classification"] == "CAUGHT")
        missed = sum(1 for c in batch if c["classification"] == "HARD_MISS")
        dir_miss = sum(1 for c in batch if c["classification"] == "DIRECTION_MISS")
        stats[f"recall_at_top_{n}"] = round(caught / n, 3) if n > 0 else 0
        stats[f"caught_at_top_{n}"] = caught
        stats[f"hard_miss_at_top_{n}"] = missed
        stats[f"dir_miss_at_top_{n}"] = dir_miss
        stats[f"n_for_top_{n}"] = n
    stats["total_movers"] = len(classified)
    stats["total_caught"] = sum(1 for c in classified if c["classification"] == "CAUGHT")
    stats["total_hard_miss"] = sum(1 for c in classified if c["classification"] == "HARD_MISS")
    stats["total_dir_miss"] = sum(1 for c in classified if c["classification"] == "DIRECTION_MISS")
    return stats


def per_strategy_breakdown(classified: list[dict]) -> list[dict]:
    """Which strategy families caught the most top movers?"""
    strat_counter: dict[str, dict[str, int]] = {}
    for c in classified:
        if c["classification"] != "CAUGHT":
            continue
        for sfy in c["strategies"]:
            entry = strat_counter.setdefault(sfy, {"caught": 0, "total": 0})
            entry["caught"] += 1
    # Also count total opportunities per strategy (how many top movers had this strategy?)
    for c in classified:
        for sfy in c.get("strategies", []):
            strat_counter.setdefault(sfy, {"caught": 0, "total": 0})["total"] += 1

    rows = []
    for sfy, counts in strat_counter.items():
        rows.append({
            "strategy": sfy,
            "top_movers_with_strategy": counts["total"],
            "top_movers_caught": counts["caught"],
            "capture_rate": round(counts["caught"] / max(counts["total"], 1), 3),
        })
    rows.sort(key=lambda x: -x["capture_rate"])
    return rows


# ===========================================================================
# 6.  Report builder (Markdown)
# ===========================================================================

def build_report(
    classified: list[dict],
    stats: dict[str, Any],
    strategy_rows: list[dict],
    days: int,
    top_n: int,
) -> str:
    """Build the full Markdown report."""
    lines: list[str] = [
        "# Missed-Gainers Autopsy — last %d days" % days,
        "",
        f"Window: top {len(classified)} 24h movers across CRYPTO markets. "
        f"Cross-referenced against {stats['total_movers']} movers.",
        "",
        "---",
        "## 1.  Recall @ Top-N",
        "",
        "How many of the market's top movers did our pick system have a position for?",
        "",
        "| Threshold | Caught | Hard Miss | Direction Miss | Recall |",
        "|---|---|---|---|---|",
    ]

    for n in (10, 25, 50, 100):
        key = f"recall_at_top_{n}"
        if key not in stats:
            break
        c = stats[f"caught_at_top_{n}"]
        h = stats[f"hard_miss_at_top_{n}"]
        d = stats[f"dir_miss_at_top_{n}"]
        r = stats[key]
        lines.append(
            f"| Top {n} | {c} | {h} | {d} | {r * 100:.1f}% |"
        )

    lines += [
        "",
        f"**Overall**: {stats['total_caught']} caught, "
        f"{stats['total_hard_miss']} hard-missed, "
        f"{stats['total_dir_miss']} direction-missed "
        f"(of top {len(classified)} movers).",
        "",
        "---",
        "## 2.  Top Movers We CAUGHT",
        "",
        "These symbols moved significantly AND we had an active/historical pick.  "
        "Strategy = the strategy family that emitted the pick.",
        "",
        "| Rank | Symbol | Δ24h | Volume (USDT) | Strategy | WR (closed) |",
        "|---|---|---|---|---|---|",
    ]

    caught = [c for c in classified if c["classification"] == "CAUGHT"]
    for i, c in enumerate(caught[:30], 1):
        sfy = c["strategies"][0] if c["strategies"] else "?"
        wr_str = f"{c['wr'] * 100:.1f}%" if c["wr"] is not None else "—"
        vol_s = f"${c['volume_usdt']:.0f}" if c["volume_usdt"] else "—"
        lines.append(
            f"| {i} | `{c['symbol']}` | {c['price_change_pct']:+.1f}% "
            f"| {vol_s} | {sfy} | {wr_str} |"
        )

    if not caught:
        lines.append("| *(none caught at top mover thresholds)* |")

    lines += [
        "",
        "---",
        "## 3.  Top Movers We HARD-MISSED (no pick ever)",
        "",
        "These are the pure blind spots — symbols that moved significantly "
        "but our system never emitted any pick (active or closed) for them.",
        "",
        "| Rank | Symbol | Δ24h | Volume (USDT) | Why We Might Miss |",
        "|---|---|---|---|---|",
    ]

    hard_miss = [c for c in classified if c["classification"] == "HARD_MISS"]
    for i, c in enumerate(hard_miss[:30], 1):
        vol_s = f"${c['volume_usdt']:.0f}" if c["volume_usdt"] else "—"
        # Categorise why
        base = c["symbol"].replace("USDT", "")
        if c["price_change_pct"] < 0:
            why = "Loser — system biased toward long? Or avoided?"
        elif c["volume_usdt"] and c["volume_usdt"] < 1_000_000:
            why = "Low volume (<$1M) — may be below liquidity filter"
        elif c["price_change_pct"] > 20:
            why = "Extreme mover (>20%) — may have triggered as a pump before we scanned"
        else:
            why = "Unknown — candidate for new strategy addition"
        lines.append(
            f"| {i} | `{c['symbol']}` | {c['price_change_pct']:+.1f}% "
            f"| {vol_s} | {why} |"
        )

    if not hard_miss:
        lines.append("| *(zero hard misses — our coverage is comprehensive)* |")

    lines += [
        "",
        "---",
        "## 4.  Direction Misses (wrong side)",
        "",
        "We had a pick for this symbol, but the direction was wrong. "
        "(e.g., SHORT on a +15% gainer)",
        "",
        "| Rank | Symbol | Δ24h | Active Direction | Volume (USDT) |",
        "|---|---|---|---|---|",
    ]

    dir_miss = [c for c in classified if c["classification"] == "DIRECTION_MISS"]
    for i, c in enumerate(dir_miss[:15], 1):
        vol_s = f"${c['volume_usdt']:.0f}" if c["volume_usdt"] else "—"
        lines.append(
            f"| {i} | `{c['symbol']}` | {c['price_change_pct']:+.1f}% "
            f"| {c['direction_hint'] or '?'} | {vol_s} |"
        )

    if not dir_miss:
        lines.append("| *(zero direction misses)* |")

    lines += [
        "",
        "---",
        "## 5.  Per-Strategy Capture Rate",
        "",
        "Which strategy families actually caught top movers?",
        "",
        "| Strategy | Top Movers With This Strategy | Caught | Capture Rate |",
        "|---|---|---|---|",
    ]

    for r in strategy_rows:
        lines.append(
            f"| {r['strategy']} | {r['top_movers_with_strategy']} | "
            f"{r['top_movers_caught']} | {r['capture_rate'] * 100:.1f}% |"
        )

    if not strategy_rows:
        lines.append("| *(no strategies caught any top movers in this window)* |")

    lines += [
        "",
        "---",
        "## 6.  Action Items",
        "",
        "Based on the missed-gainers analysis above:",
        "",
    ]

    # Generate action items
    action_items: list[str] = []

    # If recall@10 is <50%, flag it
    r10 = stats.get("recall_at_top_10", 1)
    if r10 < 0.5:
        action_items.append(
            f"- **Low recall @ Top 10** ({r10 * 100:.1f}%): "
            f"We missed {stats.get('hard_miss_at_top_10', 0)} of the top 10 movers. "
            "Consider adding a momentum-capture strategy that monitors Binance "
            "24h gainers and auto-generates picks for symbols above a volume threshold."
        )

    # If hard miss count is high
    if stats.get("total_hard_miss", 0) > 20:
        action_items.append(
            f"- **{stats['total_hard_miss']} hard-missed symbols**: "
            "Review the missed list for patterns (sector, market cap, exchange listing). "
            "If consistent sectors appear, add targeted scanners."
        )

    # Direction miss analysis
    if stats.get("total_dir_miss", 0) > 5:
        action_items.append(
            f"- **{stats['total_dir_miss']} direction misses**: "
            "Our system is picking the wrong side on these symbols. "
            "Consider a momentum filter before emitting SHORT signals on high-momentum symbols."
        )

    # If zero hard misses, that's good
    if stats.get("total_hard_miss", 99) == 0:
        action_items.append(
            "- **Zero hard misses**: Our symbol coverage is comprehensive. "
            "Focus on improving win rate rather than expanding coverage."
        )

    if not action_items:
        action_items.append("- Analysis complete — no critical blind spots detected in this window.")

    lines += action_items
    lines += ["", "---", f"*Report generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*", ""]

    return "\n".join(lines)


# ===========================================================================
# 7.  Main
# ===========================================================================

def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    ap = argparse.ArgumentParser(
        description="Missed-Gainers Autopsy — what moved that we didn't have picks for?"
    )
    ap.add_argument("--days", type=int, default=7,
                    help="Lookback window for closed picks (default: 7)")
    ap.add_argument("--top", type=int, default=50,
                    help="Number of top movers to analyse (default: 50)")
    ap.add_argument("--out", type=Path, default=None,
                    help="Write report to file instead of stdout")
    args = ap.parse_args()

    print("=" * 60, file=sys.stderr)
    print("  MISSED-GAINERS AUTOPSY", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    # 1. Load picks
    print(f"[1/5] Loading picks from active_picks.json + closed_picks.json...", file=sys.stderr)
    active = _load_picks(ACTIVE)
    closed = _load_picks(CLOSED)
    print(f"      Active: {len(active)} picks  |  Closed: {len(closed)} picks", file=sys.stderr)

    # 2. Build lookup
    print(f"[2/5] Building symbol lookup (last {args.days}d)...", file=sys.stderr)
    lookup = build_pick_lookup(active, closed, args.days)
    print(f"      Unique symbols in our universe: {len(lookup)}", file=sys.stderr)

    # 3. Fetch top movers
    print(f"[3/5] Fetching top {args.top} market movers...", file=sys.stderr)
    movers = fetch_top_movers(top_n=args.top)
    if not movers:
        print("  [ERROR] No market data returned. Report will be empty.", file=sys.stderr)
        return 1
    print(f"      Got {len(movers)} movers from market data", file=sys.stderr)
    # Show top 5
    for m in movers[:5]:
        print(f"        {m['symbol']:12s}  {m['price_change_pct']:+.1f}%  vol=${m['volume_usdt']:.0f}", file=sys.stderr)

    # 4. Classify
    print(f"[4/5] Cross-referencing against our picks...", file=sys.stderr)
    classified = classify_movers(movers, lookup)
    stats = recall_stats(classified, args.top)
    print(f"      Caught: {stats['total_caught']}  |  Hard Miss: {stats['total_hard_miss']}  |  Direction Miss: {stats['total_dir_miss']}", file=sys.stderr)
    print(f"      Recall @ Top 10: {stats.get('recall_at_top_10', 'N/A') * 100:.1f}%", file=sys.stderr)

    # 5. Strategy breakdown
    strategy_rows = per_strategy_breakdown(classified)

    # 6. Build report
    print(f"[5/5] Building report...", file=sys.stderr)
    report = build_report(classified, stats, strategy_rows, args.days, args.top)

    # 7. Output
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(report, encoding="utf-8")
        print(f"\n# Wrote {args.out}", file=sys.stderr)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
