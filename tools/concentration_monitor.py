"""
EAGLE2 Concentration Monitor — v1.0 (2026-06-02)

Monitors strategy/book concentration risk via Herfindahl-Hirschman Index (HHI),
per-symbol weight distribution, and source-system diversification.

Alerts when HHI > 0.25 or any single symbol/source dominates the book.

Usage:
    python -m tools.concentration_monitor [--json] [--alert]
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger("concentration_monitor")

ROOT = Path(__file__).resolve().parent.parent

# Thresholds
HHI_WARNING = 0.20
HHI_ALERT = 0.25
SYMBOL_SHARE_ALERT = 0.25   # Single symbol > 25% of book
SOURCE_SHARE_ALERT = 0.40    # Single source system > 40% of picks

# Data sources
ACTIVE_PICKS_PATHS = [
    ROOT / "alpha_engine" / "data" / "active_picks.json",
    ROOT / "alpha_engine" / "data" / "premium_signals.json",
    ROOT / "audit_trail" / "data" / "universal_resolved_picks.json",
    ROOT / "paper_trading" / "data" / "active_picks.json",
    ROOT / "paper_trading" / "data" / "portfolios.json",
]


def compute_hhi(items: List[str]) -> float:
    """Compute Herfindahl-Hirschman Index for a list of category labels."""
    if not items:
        return 0.0
    counts: Dict[str, int] = {}
    for item in items:
        counts[item] = counts.get(item, 0) + 1
    n = len(items)
    return sum((c / n) ** 2 for c in counts.values())


def load_picks_from_file(path: Path) -> List[Dict]:
    """Load picks from a JSON file, handling various formats."""
    if not path.exists():
        return []
    try:
        with open(path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        log.warning("Failed to load %s: %s", path, e)
        return []

    if isinstance(data, list):
        return [p for p in data if isinstance(p, dict)]
    if isinstance(data, dict):
        for key in ("active_picks", "picks", "signals", "activePicks", "portfolios"):
            val = data.get(key)
            if isinstance(val, list):
                return [p for p in val if isinstance(p, dict)]
    return []


def analyze_concentration(picks: List[Dict], label: str = "unknown") -> Dict[str, Any]:
    """Analyze concentration metrics for a set of picks."""
    if not picks:
        return {"label": label, "total_picks": 0, "symbol_hhi": 0.0,
                "source_hhi": 0.0, "status": "no_data"}

    symbols = [p.get("symbol", p.get("pair", "unknown")) for p in picks]
    sources = [p.get("source_system", p.get("system", p.get("strategy", "unknown")))
               for p in picks]
    asset_classes = [p.get("asset_class", p.get("class", "unknown"))
                     for p in picks]
    directions = [p.get("direction", "LONG") for p in picks]

    symbol_hhi = compute_hhi(symbols)
    source_hhi = compute_hhi(sources)
    class_hhi = compute_hhi(asset_classes)

    # Top symbols
    symbol_counts: Dict[str, int] = defaultdict(int)
    for s in symbols:
        symbol_counts[s] += 1
    top_symbols = sorted(symbol_counts.items(), key=lambda x: -x[1])[:10]
    top_symbol_pcts = [(s, c / len(symbols), c) for s, c in top_symbols]

    # Top sources
    source_counts: Dict[str, int] = defaultdict(int)
    for s in sources:
        source_counts[s] += 1
    top_sources = sorted(source_counts.items(), key=lambda x: -x[1])[:10]
    top_source_pcts = [(s, c / len(sources), c) for s, c in top_sources]

    # Direction bias
    long_count = sum(1 for d in directions if d.upper() in ("LONG", "BUY"))
    short_count = sum(1 for d in directions if d.upper() in ("SHORT", "SELL"))
    long_pct = long_count / max(len(directions), 1)
    short_pct = short_count / max(len(directions), 1)

    # Status
    status = "ok"
    alerts = []
    if symbol_hhi >= HHI_ALERT:
        status = "alert"
        alerts.append(f"Symbol HHI {symbol_hhi:.3f} >= {HHI_ALERT}")
    elif symbol_hhi >= HHI_WARNING:
        status = "warning"
        alerts.append(f"Symbol HHI {symbol_hhi:.3f} >= {HHI_WARNING}")

    if source_hhi >= HHI_ALERT:
        status = "alert"
        alerts.append(f"Source HHI {source_hhi:.3f} >= {HHI_ALERT}")

    if top_symbol_pcts and top_symbol_pcts[0][1] >= SYMBOL_SHARE_ALERT:
        alerts.append(f"Top symbol {top_symbol_pcts[0][0]} = {top_symbol_pcts[0][1]:.1%} "
                      f">= {SYMBOL_SHARE_ALERT:.0%}")

    if top_source_pcts and top_source_pcts[0][1] >= SOURCE_SHARE_ALERT:
        alerts.append(f"Top source {top_source_pcts[0][0]} = {top_source_pcts[0][1]:.1%} "
                      f">= {SOURCE_SHARE_ALERT:.0%}")

    return {
        "label": label,
        "total_picks": len(picks),
        "unique_symbols": len(symbol_counts),
        "unique_sources": len(source_counts),
        "symbol_hhi": round(symbol_hhi, 4),
        "source_hhi": round(source_hhi, 4),
        "class_hhi": round(class_hhi, 4),
        "long_pct": round(long_pct, 4),
        "short_pct": round(short_pct, 4),
        "top_symbols": [{"symbol": s, "pct": round(p, 4), "count": c}
                        for s, p, c in top_symbol_pcts[:5]],
        "top_sources": [{"source": s, "pct": round(p, 4), "count": c}
                        for s, p, c in top_source_pcts[:5]],
        "status": status,
        "alerts": alerts,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def run_full_audit() -> Dict[str, Any]:
    """Run concentration analysis across all active pick sources."""
    results = []

    for path in ACTIVE_PICKS_PATHS:
        picks = load_picks_from_file(path)
        if picks:
            result = analyze_concentration(picks, path.name)
            results.append(result)

    # Aggregate across all sources
    all_picks = []
    for path in ACTIVE_PICKS_PATHS:
        all_picks.extend(load_picks_from_file(path))

    aggregate = analyze_concentration(all_picks, "aggregate")

    return {
        "aggregate": aggregate,
        "by_source": results,
    }


def main():
    parser = argparse.ArgumentParser(description="EAGLE2 Concentration Monitor")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--alert", action="store_true", help="Exit 1 if any alerts")
    parser.add_argument("--source", type=str, help="Check a specific source file")
    args = parser.parse_args()

    if args.source:
        path = Path(args.source)
        if not path.exists():
            path = ROOT / args.source if not args.source.startswith("/") else path
        picks = load_picks_from_file(path)
        result = analyze_concentration(picks, str(path))
        results = {"aggregate": result, "by_source": []}
    else:
        results = run_full_audit()

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        agg = results["aggregate"]
        print(f"\n{'='*60}")
        print(f"  EAGLE2 CONCENTRATION MONITOR — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"{'='*60}")
        print(f"  Total picks:       {agg['total_picks']}")
        print(f"  Unique symbols:    {agg['unique_symbols']}")
        print(f"  Unique sources:    {agg['unique_sources']}")
        print(f"  Symbol HHI:        {agg['symbol_hhi']:.4f} {'⚠️ ' if agg['symbol_hhi'] >= HHI_WARNING else '✅'}")
        print(f"  Source HHI:        {agg['source_hhi']:.4f} {'⚠️ ' if agg['source_hhi'] >= HHI_WARNING else '✅'}")
        print(f"  Long/Short:        {agg['long_pct']:.1%} / {agg['short_pct']:.1%}")
        print(f"  Status:            {agg['status'].upper()}")
        print()

        if agg.get("alerts"):
            print("  ALERTS:")
            for a in agg["alerts"]:
                print(f"    ⚠️  {a}")
            print()

        if agg.get("top_symbols"):
            print("  Top Symbols:")
            for s in agg["top_symbols"]:
                bar = "█" * int(s["pct"] * 50)
                print(f"    {s['symbol']:12s} {s['pct']:6.1%} {s['count']:4d} {bar}")
            print()

        if agg.get("top_sources"):
            print("  Top Sources:")
            for s in agg["top_sources"]:
                bar = "█" * int(s["pct"] * 50)
                print(f"    {s['source'][:25]:25s} {s['pct']:6.1%} {s['count']:4d} {bar}")
            print()

        for src in results["by_source"]:
            if src.get("alerts"):
                print(f"  SOURCE ALERTS — {src['label']}:")
                for a in src["alerts"]:
                    print(f"    ⚠️  {a}")
                print()

    # Exit code
    has_alerts = (results["aggregate"].get("status") == "alert" or
                  any(s.get("status") == "alert" for s in results.get("by_source", [])))
    if args.alert and has_alerts:
        sys.exit(1)


if __name__ == "__main__":
    main()
