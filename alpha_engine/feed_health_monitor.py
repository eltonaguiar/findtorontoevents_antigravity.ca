#!/usr/bin/env python3
"""Feed Health Monitor — checks all data source freshness and pick counts."""
import json
import os
import logging
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parent.parent

SOURCES = {
    "alpha_engine": "alpha_engine/data/active_picks.json",
    "battleground": "battleground/data/active_picks.json",
    "luxalgo": "battleground/data/luxalgo_active_picks.json",
    "kimi_riseoftheclaw": "KIMI_RISEOFTHECLAW/data/active_picks.json",
    "claude_gainer_st": "claude_gainer_ml/tracker/short_term_active.json",
    "claude_gainer_ml": "claude_gainer_ml/tracker/claude_live_picks.json",
    "mercury2": "mercury2/data/active_picks.json",
    "copy_trader_intel": "copy_trader_intel/data/active_picks.json",
    "quan_engine": "quan_engine/data/active_signals.json",
    "regime_terminal": "regime_terminal/data/active_signals.json",
    "goldmine_stocks": "data/goldmine/stock_picks.json",
    "multi_asset": "multi_asset/data/active_picks.json",
    "contrarian": "alpha_engine/data/contrarian_picks.json",
    "inverse_mutations": "alpha_engine/data/inverse_picks.json",
    "pm_kalshi": "prediction_market_agents/data/kalshi_signals.json",
    "pm_whale": "prediction_market_agents/data/whale_signals.json",
    "smart_money": "smart_money/data/active_picks.json",
    "super_signals": "cross_aggregation/data/super_signals.json",
    "tsmom": "alpha_engine/data/tsmom_picks.json",
    "genome": "genome/data/universal_picks.json",
}


def check_feeds():
    now = datetime.now(timezone.utc)
    results = []
    for name, rel_path in sorted(SOURCES.items()):
        path = ROOT / rel_path
        entry = {"source": name, "path": rel_path}
        if not path.exists():
            entry.update(status="MISSING", age_hours=9999, picks=0)
        else:
            try:
                mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
                age_h = (now - mtime).total_seconds() / 3600
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    count = len(data)
                elif isinstance(data, dict):
                    for k in ("picks", "active", "signals", "active_picks", "winners"):
                        if k in data and isinstance(data[k], list):
                            count = len(data[k]); break
                    else:
                        count = len(data)
                else:
                    count = 0
                if age_h < 2 and count > 0: status = "FRESH"
                elif age_h < 24 and count > 0: status = "OK"
                elif age_h < 168: status = "STALE"
                else: status = "DEAD"
                if count == 0 and status not in ("MISSING",): status = "EMPTY"
                entry.update(status=status, age_hours=round(age_h, 1), picks=count)
            except Exception as e:
                entry.update(status="ERROR", age_hours=9999, picks=0, error=str(e)[:100])
        results.append(entry)

    fresh = sum(1 for r in results if r["status"] == "FRESH")
    ok = sum(1 for r in results if r["status"] == "OK")
    stale = sum(1 for r in results if r["status"] == "STALE")
    dead = sum(1 for r in results if r["status"] in ("DEAD", "MISSING", "EMPTY", "ERROR"))

    report = {
        "generated_at": now.isoformat(),
        "summary": {"fresh": fresh, "ok": ok, "stale": stale, "dead": dead, "total": len(results)},
        "feeds": results,
    }

    out = ROOT / "alpha_engine" / "data" / "feed_health_report.json"
    with open(out, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"Feed Health: {fresh} fresh, {ok} ok, {stale} stale, {dead} dead/{len(results)} total")
    for r in results:
        icon = {"FRESH": "[FRESH]", "OK": "[OK]", "STALE": "[STALE]", "DEAD": "[DEAD]", "MISSING": "[MISS]", "EMPTY": "[EMPTY]", "ERROR": "[ERR]"}.get(r["status"], "?")
        print(f"  {icon} {r['source']:<25} {r['status']:<8} age={r['age_hours']:>6.1f}h picks={r['picks']}")
    return report


def main():
    logging.basicConfig(level=logging.INFO)
    check_feeds()


if __name__ == "__main__":
    main()
