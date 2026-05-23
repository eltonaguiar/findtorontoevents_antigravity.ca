#!/usr/bin/env python3
"""
Post-Trade Attribution Engine — Daily Performance Attribution
=============================================================
Mercury AI / Inception Labs Recommendation §3.4:
  "Run after every market-close to recompute WR/expectancy per component
   and write to component_perf_daily.json"

Features:
  1. Normalizes all PnL to USDT
  2. Computes WR, expectancy, max DD, Sharpe per component
  3. Tracks daily performance snapshots
  4. Generates component_perf_daily.json for PM dashboard
  5. Flags components for demotion/kill based on Mercury AI thresholds

Created: 2026-03-03 18:27 EST
Source: Mercury AI Feedback (ANTIGRAVITY_PLAN_MERCURYFEEDBACK.MD)
"""

import json
import logging
import pathlib
import math
from datetime import datetime, timezone, timedelta
from typing import Optional

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("post_trade_attribution")

# ── Paths ──────────────────────────────────────────────────
BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

COMPONENT_PERF_PATH = OUTPUT_DIR / "component_perf_daily.json"
ATTRIBUTION_LOG_PATH = OUTPUT_DIR / "attribution_log.json"

# ── Systems to scan for closed picks ──────────────────────
SYSTEMS = {
    "mercury2": {
        "name": "Mercury 2",
        "closed": BASE_DIR / "mercury2" / "data" / "closed_picks.json",
        "family": "Mercury",
    },
    "alpha_engine": {
        "name": "Alpha Engine",
        "closed": BASE_DIR / "alpha_engine" / "data" / "closed_picks.json",
        "family": "Alpha",
    },
    "battleground": {
        "name": "Baby Battleground",
        "closed": BASE_DIR / "battleground" / "data" / "closed_picks.json",
        "family": "BabyStrategies",
    },
    "kimi_claw": {
        "name": "Claws of Doom",
        "closed": BASE_DIR / "KIMI_RISEOFTHECLAW" / "data" / "closed_picks.json",
        "family": "BabyStrategies",
    },
    "crypto_signal_engine": {
        "name": "Signal Engine",
        "closed": BASE_DIR / "crypto_signal_engine" / "data" / "closed_picks.json",
        "family": "SignalEngine",
    },
    "breakout_a": {
        "name": "Breakout A",
        "closed": BASE_DIR / "breakout_arena" / "approach_a_sr_breakout" / "data" / "closed_picks.json",
        "family": "Breakout",
    },
    "breakout_b": {
        "name": "Breakout B",
        "closed": BASE_DIR / "breakout_arena" / "approach_b_vol_breakout" / "data" / "closed_picks.json",
        "family": "Breakout",
    },
}

# ── Mercury AI Thresholds ─────────────────────────────────
DEMOTE_WIN_RATE = 0.30       # < 30% WR → demote to incubator
KILL_EXPECTANCY = 0.0        # < 0% expectancy → kill or demote
DEMOTE_MAX_DD_PCT = 0.05     # > 5% DD on allocation → demote
ALERT_SLIPPAGE = 0.002       # > 0.2% slippage per trade → tighten RR gate


def _load_json(path: pathlib.Path) -> list | dict | None:
    """Load JSON file safely."""
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.warning("Failed to load %s: %s", path, e)
        return None


def _extract_picks(data) -> list:
    """Extract picks list from various JSON structures."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("picks", "closed_picks", "trades", "results", "signals"):
            if key in data and isinstance(data[key], list):
                return data[key]
        return list(data.values()) if data else []
    return []


def _normalize_pnl(pick: dict) -> float:
    """
    Normalize PnL to USDT.

    Handles various formats:
      - "pnl": 150.0 (assumed USDT)
      - "pnl_pct": 2.5 (percentage of entry)
      - "pnl_percent": -1.2
      - "profit": 50.0
      - "exit_price" / "entry_price" → compute
    """
    # Direct USDT PnL
    for key in ("pnl", "pnl_usdt", "profit", "profit_usdt", "realized_pnl"):
        val = pick.get(key)
        if val is not None:
            try:
                return float(val)
            except (ValueError, TypeError):
                continue

    # Percentage PnL → estimate USDT from entry
    for key in ("pnl_pct", "pnl_percent", "profit_pct", "return_pct"):
        pct = pick.get(key)
        if pct is not None:
            try:
                pct = float(pct)
                entry = float(pick.get("entry_price", 0))
                size = float(pick.get("size", pick.get("quantity", 1)))
                if entry > 0 and size > 0:
                    return (pct / 100.0) * entry * size
                return pct  # Return raw percentage as a rough proxy
            except (ValueError, TypeError):
                continue

    # Compute from exit − entry
    try:
        entry = float(pick.get("entry_price", 0))
        exit_p = float(pick.get("exit_price", 0))
        size = float(pick.get("size", pick.get("quantity", 1)))
        direction = str(pick.get("direction", "LONG")).upper()
        if entry > 0 and exit_p > 0:
            if direction in ("SHORT", "SELL"):
                return (entry - exit_p) * size
            else:
                return (exit_p - entry) * size
    except (ValueError, TypeError):
        pass

    return 0.0


def _is_win(pick: dict) -> bool:
    """Determine if a pick was a win."""
    # Check explicit result field
    result = str(pick.get("result", pick.get("outcome", ""))).lower()
    if result in ("win", "tp_hit", "take_profit"):
        return True
    if result in ("loss", "sl_hit", "stop_loss"):
        return False

    # Check exit reason
    exit_reason = str(pick.get("exit_reason", "")).lower()
    if "tp" in exit_reason or "profit" in exit_reason:
        return True
    if "sl" in exit_reason or "stop" in exit_reason:
        return False

    # Fall back to PnL
    return _normalize_pnl(pick) > 0


def _get_strategy(pick: dict) -> str:
    """Extract strategy identifier from a pick."""
    for key in ("strategy", "strategy_dna", "substrategy", "signal_type"):
        val = pick.get(key)
        if val:
            return str(val).strip()
    return "unknown"


def _get_direction(pick: dict) -> str:
    """Extract direction from a pick."""
    d = str(pick.get("direction", pick.get("signal_type", "LONG"))).upper()
    if d in ("SELL", "SHORT", "S"):
        return "SHORT"
    return "LONG"


def _parse_timestamp(pick: dict) -> Optional[datetime]:
    """Parse timestamp from a pick."""
    for key in ("timestamp", "closed_at", "exit_time", "close_time", "created_at"):
        ts = pick.get(key)
        if ts is None:
            continue
        try:
            if isinstance(ts, (int, float)):
                return datetime.fromtimestamp(ts, tz=timezone.utc)
            ts_str = str(ts)
            if ts_str.endswith("Z"):
                ts_str = ts_str[:-1] + "+00:00"
            dt = datetime.fromisoformat(ts_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            continue
    return None


def compute_attribution(lookback_days: int = 30) -> dict:
    """
    Compute performance attribution for all components.

    Returns:
        dict with per-component metrics and flags
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=lookback_days)

    # Collect all closed picks across systems
    all_picks = []
    for sys_id, sys_info in SYSTEMS.items():
        data = _load_json(sys_info["closed"])
        if data is None:
            continue
        picks = _extract_picks(data)
        for p in picks:
            if not isinstance(p, dict):
                continue
            # Add system info
            p["_system_id"] = sys_id
            p["_system_name"] = sys_info["name"]
            p["_family"] = sys_info["family"]
            all_picks.append(p)

    log.info("Loaded %d total closed picks across %d systems", len(all_picks), len(SYSTEMS))

    # Group by component (strategy)
    components = {}
    for pick in all_picks:
        strategy = _get_strategy(pick)
        direction = _get_direction(pick)
        pnl = _normalize_pnl(pick)
        win = _is_win(pick)
        ts = _parse_timestamp(pick)

        # Time filter
        if ts and ts < cutoff:
            continue

        key = strategy
        if key not in components:
            components[key] = {
                "strategy": strategy,
                "system": pick.get("_system_name", "unknown"),
                "family": pick.get("_family", "unknown"),
                "trades": [],
                "wins": 0,
                "losses": 0,
                "total_pnl": 0.0,
                "long_trades": {"wins": 0, "losses": 0, "pnl": 0.0},
                "short_trades": {"wins": 0, "losses": 0, "pnl": 0.0},
                "pnl_series": [],
            }

        comp = components[key]
        comp["trades"].append({
            "pnl": round(pnl, 2),
            "win": win,
            "direction": direction,
            "symbol": pick.get("symbol", "UNKNOWN"),
            "timestamp": ts.isoformat() if ts else None,
        })
        comp["total_pnl"] += pnl
        comp["pnl_series"].append(pnl)

        if win:
            comp["wins"] += 1
        else:
            comp["losses"] += 1

        dir_key = "short_trades" if direction == "SHORT" else "long_trades"
        comp[dir_key]["pnl"] += pnl
        if win:
            comp[dir_key]["wins"] += 1
        else:
            comp[dir_key]["losses"] += 1

    # Compute metrics for each component
    results = {}
    for key, comp in components.items():
        total = comp["wins"] + comp["losses"]
        if total == 0:
            continue

        wr = comp["wins"] / total
        avg_pnl = comp["total_pnl"] / total
        expectancy_pct = (avg_pnl / 100) if abs(avg_pnl) < 10 else avg_pnl  # Rough normalization

        # Compute max draw-down on PnL series
        cum_pnl = 0
        peak_pnl = 0
        max_dd = 0
        for p in comp["pnl_series"]:
            cum_pnl += p
            if cum_pnl > peak_pnl:
                peak_pnl = cum_pnl
            dd = peak_pnl - cum_pnl
            if dd > max_dd:
                max_dd = dd

        # Compute Sharpe (annualized from daily returns approximation)
        if len(comp["pnl_series"]) > 1:
            mean_r = sum(comp["pnl_series"]) / len(comp["pnl_series"])
            variance = sum((x - mean_r) ** 2 for x in comp["pnl_series"]) / (len(comp["pnl_series"]) - 1)
            std_r = math.sqrt(variance) if variance > 0 else 1
            sharpe = (mean_r / std_r) * math.sqrt(252) if std_r > 0 else 0
        else:
            sharpe = 0

        # Long/short breakdown
        long_total = comp["long_trades"]["wins"] + comp["long_trades"]["losses"]
        short_total = comp["short_trades"]["wins"] + comp["short_trades"]["losses"]
        long_wr = comp["long_trades"]["wins"] / long_total if long_total > 0 else 0
        short_wr = comp["short_trades"]["wins"] / short_total if short_total > 0 else 0

        # Flags (Mercury AI thresholds)
        flags = []
        if wr < DEMOTE_WIN_RATE:
            flags.append("LOW_WR_DEMOTE")
        if avg_pnl < 0:
            flags.append("NEGATIVE_EXPECTANCY")
        if max_dd > comp["total_pnl"] * DEMOTE_MAX_DD_PCT if comp["total_pnl"] > 0 else max_dd > 500:
            flags.append("HIGH_DRAWDOWN")
        if long_wr < 0.30 and long_total >= 5:
            flags.append("LONG_SIDE_TOXIC")
        if total < 10:
            flags.append("LOW_SAMPLE_SIZE")

        # Recommendation
        if "NEGATIVE_EXPECTANCY" in flags and total >= 20:
            recommendation = "KILL"
        elif "LOW_WR_DEMOTE" in flags and total >= 20:
            recommendation = "DEMOTE_TO_INCUBATOR"
        elif "LONG_SIDE_TOXIC" in flags:
            recommendation = "SHORT_ONLY"
        elif len(flags) == 0 and wr > 0.50 and avg_pnl > 0:
            recommendation = "CORE_QUALIFIED"
        else:
            recommendation = "MONITOR"

        results[key] = {
            "strategy": comp["strategy"],
            "system": comp["system"],
            "family": comp["family"],
            "total_trades": total,
            "wins": comp["wins"],
            "losses": comp["losses"],
            "win_rate": round(wr, 4),
            "total_pnl_usdt": round(comp["total_pnl"], 2),
            "avg_pnl_usdt": round(avg_pnl, 2),
            "max_drawdown_usdt": round(max_dd, 2),
            "sharpe_annualized": round(sharpe, 2),
            "long_trades": long_total,
            "long_wr": round(long_wr, 4),
            "long_pnl": round(comp["long_trades"]["pnl"], 2),
            "short_trades": short_total,
            "short_wr": round(short_wr, 4),
            "short_pnl": round(comp["short_trades"]["pnl"], 2),
            "flags": flags,
            "recommendation": recommendation,
        }

    return results


def generate_daily_report():
    """Generate and save the daily component performance report."""
    now = datetime.now(timezone.utc)
    log.info("Generating post-trade attribution report for %s", now.date())

    results = compute_attribution(lookback_days=30)

    # Sort by recommendation priority
    priority = {"KILL": 0, "DEMOTE_TO_INCUBATOR": 1, "SHORT_ONLY": 2, "MONITOR": 3, "CORE_QUALIFIED": 4}
    sorted_results = dict(
        sorted(results.items(), key=lambda x: (priority.get(x[1]["recommendation"], 5), -x[1]["total_trades"]))
    )

    report = {
        "generated_at": now.isoformat(),
        "lookback_days": 30,
        "total_components": len(sorted_results),
        "summary": {
            "core_qualified": sum(1 for r in sorted_results.values() if r["recommendation"] == "CORE_QUALIFIED"),
            "monitor": sum(1 for r in sorted_results.values() if r["recommendation"] == "MONITOR"),
            "short_only": sum(1 for r in sorted_results.values() if r["recommendation"] == "SHORT_ONLY"),
            "demote": sum(1 for r in sorted_results.values() if r["recommendation"] == "DEMOTE_TO_INCUBATOR"),
            "kill": sum(1 for r in sorted_results.values() if r["recommendation"] == "KILL"),
        },
        "components": sorted_results,
    }

    # Save report
    with open(COMPONENT_PERF_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    log.info("Report saved to %s", COMPONENT_PERF_PATH)

    # Print summary
    print("\n" + "=" * 70)
    print("  POST-TRADE ATTRIBUTION REPORT")
    print(f"  Generated: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"  Lookback: 30 days | Components: {len(sorted_results)}")
    print("=" * 70)

    print(f"\n  Core Qualified: {report['summary']['core_qualified']}")
    print(f"  Monitor:        {report['summary']['monitor']}")
    print(f"  Short Only:     {report['summary']['short_only']}")
    print(f"  Demote:         {report['summary']['demote']}")
    print(f"  Kill:           {report['summary']['kill']}")

    print("\n  TOP PERFORMERS (Core Qualified):")
    print("  " + "-" * 66)
    for key, comp in sorted_results.items():
        if comp["recommendation"] == "CORE_QUALIFIED":
            print(
                f"  ✅ {comp['strategy']:30s} | WR: {comp['win_rate']:.0%} | "
                f"PnL: ${comp['total_pnl_usdt']:>8,.2f} | Trades: {comp['total_trades']}"
            )

    print("\n  ⚠️ FLAGGED COMPONENTS:")
    print("  " + "-" * 66)
    for key, comp in sorted_results.items():
        if comp["recommendation"] in ("KILL", "DEMOTE_TO_INCUBATOR", "SHORT_ONLY"):
            icon = "☠️" if comp["recommendation"] == "KILL" else "🔻" if comp["recommendation"] == "DEMOTE_TO_INCUBATOR" else "📉"
            print(
                f"  {icon} {comp['strategy']:30s} | WR: {comp['win_rate']:.0%} | "
                f"PnL: ${comp['total_pnl_usdt']:>8,.2f} | Action: {comp['recommendation']}"
            )

    print("\n" + "=" * 70)
    return report


if __name__ == "__main__":
    generate_daily_report()
