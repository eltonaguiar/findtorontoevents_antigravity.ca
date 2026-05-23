#!/usr/bin/env python3
"""
Hourly Performance Monitor — Auto-Tweaking Crypto/Forex Scoring
================================================================
Runs every hour to:
  1. Snapshot current active/closed pick performance
  2. Compute per-strategy hourly WR, PnL, momentum signals
  3. Auto-adjust scoring boosts/penalties based on live data
  4. Detect degrading strategies and flag for review
  5. Boost improving strategies automatically
  6. Log all adjustments for audit trail

The tweaker modifies PROVEN_WINNERS boosts and BANNED_SYSTEMS in
smart_picks_engine.py data layer (not source code — uses JSON state).

Stdlib only. Windows UTF-8 safe.
"""

import json
import math
import os
import ssl
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
MONITOR_STATE = DATA / "hourly_monitor_state.json"
MONITOR_LOG = DATA / "hourly_monitor_log.json"
SCORING_OVERRIDES = DATA / "scoring_overrides.json"

# ─── Thresholds ────────────────────────────────────────────────────────
# Strategy momentum detection
MOMENTUM_WINDOW = 20          # Last N closed picks for momentum calc
IMPROVING_THRESHOLD = 15      # WR improved >15% → boost
DEGRADING_THRESHOLD = -15     # WR dropped >15% → penalize
CRITICAL_DEGRADING = -25      # WR dropped >25% → consider kill

# Score adjustment limits
MAX_BOOST = 20                # Maximum positive boost
MAX_PENALTY = -30             # Maximum negative penalty
BOOST_STEP = 5                # How much to adjust per cycle
PENALTY_STEP = -5

# Minimum data for decisions
MIN_RECENT_PICKS = 5          # Need at least 5 picks in window
MIN_TOTAL_PICKS = 10          # Need 10+ total for any scoring adjustment

# Fear & Greed integration
EXTREME_FEAR_THRESHOLD = 20
EXTREME_GREED_THRESHOLD = 80

# Binance mirrors for price fetching
BINANCE_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://data-api.binance.vision",
]


def _load_json(path: Path) -> Any:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def _fetch_json(url: str, timeout: int = 10) -> Any:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
    return json.loads(resp.read())


def _fetch_fear_greed() -> int:
    """Fetch Fear & Greed Index."""
    try:
        data = _fetch_json("https://api.alternative.me/fng/?limit=1")
        return int(data["data"][0]["value"])
    except Exception:
        return 50  # Default neutral


def _fetch_btc_price() -> float:
    """Fetch BTC price from Binance mirrors."""
    for mirror in BINANCE_MIRRORS:
        try:
            url = f"{mirror}/api/v3/ticker/price?symbol=BTCUSDT"
            data = _fetch_json(url)
            return float(data["price"])
        except Exception:
            continue
    return 0.0


# ═══════════════════════════════════════════════════════════════════════
# PERFORMANCE SNAPSHOT
# ═══════════════════════════════════════════════════════════════════════

def take_performance_snapshot() -> dict:
    """Take hourly snapshot of all strategy performance."""
    now = datetime.now(timezone.utc)
    fgi = _fetch_fear_greed()
    btc = _fetch_btc_price()

    # Load picks
    active_picks = _load_json(DATA / "active_picks.json") or []
    closed_picks = _load_json(DATA / "closed_picks.json") or []

    # Dashboard payload for richer data
    dashboard = _load_json(BASE.parent / "audit_trail" / "data" / "dashboard_payload.json")
    if dashboard:
        dp_active = dashboard.get("picks", {}).get("active", [])
        dp_closed = dashboard.get("picks", {}).get("recent_closed", [])
        if dp_active:
            active_picks = dp_active
        if dp_closed:
            closed_picks = dp_closed

    # Per-strategy metrics from active picks
    strat_active = defaultdict(lambda: {"count": 0, "pnls": [], "symbols": set()})
    for p in active_picks:
        strat = p.get("strategy", "unknown")
        try:
            pnl = float(p.get("pnl_pct", 0) or 0)
        except (ValueError, TypeError):
            continue
        d = strat_active[strat]
        d["count"] += 1
        d["pnls"].append(pnl)
        d["symbols"].add(p.get("symbol", ""))

    # Per-strategy metrics from closed picks (recent window)
    strat_closed = defaultdict(lambda: {"wins": 0, "losses": 0, "pnls": [], "symbols": set()})
    for p in closed_picks:
        strat = p.get("strategy", "unknown")
        try:
            pnl = float(p.get("pnl_pct", 0) or 0)
        except (ValueError, TypeError):
            continue
        d = strat_closed[strat]
        d["pnls"].append(pnl)
        if pnl > 0:
            d["wins"] += 1
        else:
            d["losses"] += 1
        d["symbols"].add(p.get("symbol", ""))

    # Build strategy report
    strategies = {}
    all_strats = set(strat_active.keys()) | set(strat_closed.keys())
    for strat in all_strats:
        a = strat_active.get(strat, {"count": 0, "pnls": [], "symbols": set()})
        c = strat_closed.get(strat, {"wins": 0, "losses": 0, "pnls": [], "symbols": set()})

        total_closed = c["wins"] + c["losses"]
        wr = c["wins"] / total_closed * 100 if total_closed > 0 else None
        avg_pnl = sum(c["pnls"]) / len(c["pnls"]) if c["pnls"] else None
        active_avg = sum(a["pnls"]) / len(a["pnls"]) if a["pnls"] else None

        # Momentum: compare recent vs overall
        recent_pnls = c["pnls"][-MOMENTUM_WINDOW:] if len(c["pnls"]) > MOMENTUM_WINDOW else c["pnls"]
        older_pnls = c["pnls"][:-MOMENTUM_WINDOW] if len(c["pnls"]) > MOMENTUM_WINDOW else []

        recent_wr = sum(1 for p in recent_pnls if p > 0) / len(recent_pnls) * 100 if recent_pnls else None
        older_wr = sum(1 for p in older_pnls if p > 0) / len(older_pnls) * 100 if older_pnls else None

        momentum = None
        if recent_wr is not None and older_wr is not None:
            momentum = recent_wr - older_wr

        strategies[strat] = {
            "active_count": a["count"],
            "active_avg_pnl": round(active_avg, 4) if active_avg is not None else None,
            "closed_total": total_closed,
            "closed_wr": round(wr, 1) if wr is not None else None,
            "closed_avg_pnl": round(avg_pnl, 4) if avg_pnl is not None else None,
            "recent_wr": round(recent_wr, 1) if recent_wr is not None else None,
            "momentum": round(momentum, 1) if momentum is not None else None,
            "symbols": len(a["symbols"] | c["symbols"]),
        }

    snapshot = {
        "timestamp": now.isoformat(),
        "btc_price": btc,
        "fear_greed": fgi,
        "total_active": len(active_picks),
        "total_closed": len(closed_picks),
        "strategies": strategies,
    }

    return snapshot


# ═══════════════════════════════════════════════════════════════════════
# AUTO-TWEAKER
# ═══════════════════════════════════════════════════════════════════════

def compute_scoring_adjustments(snapshot: dict) -> dict:
    """Compute scoring boosts/penalties based on performance data.

    Rules:
    1. Strategies improving by >15% WR → +5 boost (up to +20 max)
    2. Strategies degrading by >15% WR → -5 penalty (up to -30 max)
    3. Strategies with 0% recent WR (5+ picks) → -25 immediate penalty
    4. Multi-symbol strategies get +3 bonus per extra profitable pair
    5. In extreme fear (FGI<20): boost SHORT strategies +10, penalize LONG-only -5
    6. In extreme greed (FGI>80): boost LONG strategies +5, penalize SHORT-only -10
    """
    fgi = snapshot.get("fear_greed", 50)
    adjustments = {}

    # Load existing overrides
    existing = _load_json(SCORING_OVERRIDES) or {}
    existing_adj = existing.get("adjustments", {})

    # Strategies confirmed OVERFIT by Monte Carlo — never boost, always 0
    MC_CONFIRMED_OVERFIT = {"quan_engine_scalp", "quan_engine_position", "macd_crossover"}

    # Walk-forward FAILING strategies — cap maximum boost (monitor can't exceed these)
    WF_FAILING_CAPS = {
        "clone_hl_copy_Auros_66M": 10,       # WF FAILING 61.5% WR
        "funding_momentum": 0,                # WF FAILING 35.6% WR
        "st_fear_greed_contrarian": 15,       # WF FAILING but +82% total PnL
        "fractal_sr_bounce": 5,               # WF FAILING 40% WR
        "ensemble": -5,                       # WF FAILING 29.6% WR
        "st_rsi_momentum_confluence": 0,      # WF FAILING 33.3% WR
        "enhanced_ml_A_xgboost": -10,         # WF FAILING 29.6% WR
    }

    # Walk-forward STRONG strategies — minimum boost floor (don't over-penalize proven winners)
    # Updated 2026-04-01 09:54 WF refresh: rsi_overbought demoted to MARGINAL, vwap_sol promoted
    WF_STRONG_FLOORS = {
        "drawdown_recovery_rsi_eth": -5,      # WF STRONG 76.2% WR
        "hs_lb_None": 10,                     # WF STRONG 91.7% WR
        "crypto_kalman_trend_residual_reversion_v1": 5,  # WF STRONG 83.3% WR
        "vwap_deviation_reversion_sol_v1": 10,  # WF STRONG 70.0% WR — boosted per PEER_INTEL 2026-04-02
    }

    for strat, data in snapshot.get("strategies", {}).items():
        # Skip confirmed OVERFIT strategies — they must not get positive boosts
        if strat in MC_CONFIRMED_OVERFIT:
            if existing_adj.get(strat, {}).get("boost", 0) != 0:
                adjustments[strat] = {
                    "boost": 0, "previous": existing_adj.get(strat, {}).get("boost", 0),
                    "delta": -existing_adj.get(strat, {}).get("boost", 0),
                    "reasons": ["mc_confirmed_overfit: permanent reset to 0"],
                    "closed_wr": data.get("closed_wr"), "momentum": data.get("momentum"),
                    "recent_wr": data.get("recent_wr"),
                }
            continue

        current_adj = existing_adj.get(strat, {}).get("boost", 0)
        new_adj = current_adj
        reasons = []

        total = data.get("closed_total", 0)
        if total < MIN_TOTAL_PICKS:
            continue

        momentum = data.get("momentum")
        recent_wr = data.get("recent_wr")

        # Rule 1: Improving strategies
        if momentum is not None and momentum > IMPROVING_THRESHOLD:
            new_adj = min(current_adj + BOOST_STEP, MAX_BOOST)
            reasons.append(f"improving:+{momentum:.0f}%WR")

        # Rule 2: Degrading strategies
        if momentum is not None and momentum < DEGRADING_THRESHOLD:
            new_adj = max(current_adj + PENALTY_STEP, MAX_PENALTY)
            reasons.append(f"degrading:{momentum:.0f}%WR")

        # Rule 3: Recent 0% WR with enough picks
        if recent_wr is not None and recent_wr == 0 and total >= MIN_RECENT_PICKS:
            new_adj = max(-25, MAX_PENALTY)
            reasons.append("zero_recent_wr")

        # Rule 4: Multi-symbol bonus
        nsym = data.get("symbols", 0)
        if nsym >= 5 and (data.get("closed_wr") or 0) > 55:
            sym_bonus = min((nsym - 4) * 3, 15)  # +3 per extra pair, cap at +15
            new_adj = min(new_adj + sym_bonus, MAX_BOOST)
            reasons.append(f"multi_sym_bonus:+{sym_bonus}")

        # Rule 5/6: Regime-based adjustments
        # (these are session-level, not persistent)
        regime_adj = 0
        if fgi < EXTREME_FEAR_THRESHOLD:
            # We don't know direction from strategy name alone,
            # but copy_hl and SHORT-themed strategies get a boost
            if "short" in strat.lower() or "funding" in strat.lower():
                regime_adj = 10
                reasons.append("fear_short_boost:+10")
        elif fgi > EXTREME_GREED_THRESHOLD:
            if "short" in strat.lower():
                regime_adj = -10
                reasons.append("greed_short_penalty:-10")

        final_adj = max(min(new_adj + regime_adj, MAX_BOOST), MAX_PENALTY)

        # Enforce WF-FAILING caps — these strategies must not exceed their ceiling
        if strat in WF_FAILING_CAPS:
            cap = WF_FAILING_CAPS[strat]
            if final_adj > cap:
                final_adj = cap
                reasons.append(f"wf_failing_cap:{cap}")

        # Enforce WF-STRONG floors — don't over-penalize proven winners
        if strat in WF_STRONG_FLOORS:
            floor = WF_STRONG_FLOORS[strat]
            if final_adj < floor:
                final_adj = floor
                reasons.append(f"wf_strong_floor:{floor}")

        if final_adj != current_adj or reasons:
            adjustments[strat] = {
                "boost": final_adj,
                "previous": current_adj,
                "delta": final_adj - current_adj,
                "reasons": reasons,
                "closed_wr": data.get("closed_wr"),
                "momentum": momentum,
                "recent_wr": recent_wr,
            }

    return adjustments


# ── Mercury #15: Gini Drift Alert ─────────────────────────────────────
GINI_DRIFT_THRESHOLD = 0.05
GINI_HISTORY_FILE = DATA / "gini_drift_history.json"
SYMBOL_TIERS_PATH = BASE / "data" / "ab_test_portfolios" / "symbol_strength_tiers.json"


def check_gini_drift_alerts() -> list:
    """Fire alert when a strategy's Gini rises >0.05 in 7 days."""
    alerts = []
    try:
        if not SYMBOL_TIERS_PATH.exists():
            return alerts
        tiers = json.loads(SYMBOL_TIERS_PATH.read_text(encoding="utf-8"))
        details = tiers.get("details", {})
        now = datetime.now(timezone.utc)

        history = {}
        if GINI_HISTORY_FILE.exists():
            history = json.loads(GINI_HISTORY_FILE.read_text(encoding="utf-8"))

        for strat, info in details.items():
            robustness = info.get("robustness")
            if robustness is None:
                continue
            gini = round(1.0 - float(robustness), 4)
            prev = history.get(strat)
            if prev:
                try:
                    prev_ts = datetime.fromisoformat(prev["ts"])
                    if (now - prev_ts) <= timedelta(days=7):
                        drift = gini - prev["gini"]
                        if drift > GINI_DRIFT_THRESHOLD:
                            msg = f"GINI DRIFT: {strat} {prev['gini']:.3f}->{gini:.3f} (+{drift:.3f})"
                            print(f"  [MONITOR] WARNING {msg}")
                            alerts.append({"strategy": strat, "drift": round(drift, 4)})
                except Exception:
                    pass
            history[strat] = {"gini": gini, "ts": now.isoformat()}

        GINI_HISTORY_FILE.write_text(json.dumps(history, indent=2, default=str), encoding="utf-8")
    except Exception:
        pass
    return alerts


def apply_scoring_overrides(adjustments: dict) -> dict:
    """Persist scoring overrides to JSON for smart_picks_engine to consume."""
    now = datetime.now(timezone.utc)

    existing = _load_json(SCORING_OVERRIDES) or {
        "created_at": now.isoformat(),
        "adjustments": {},
        "history": [],
    }

    # Update adjustments
    for strat, adj in adjustments.items():
        existing["adjustments"][strat] = {
            "boost": adj["boost"],
            "updated_at": now.isoformat(),
            "reasons": adj["reasons"],
        }

    # Append to history (keep last 168 = 7 days hourly)
    existing["history"].append({
        "timestamp": now.isoformat(),
        "changes": {s: {"boost": a["boost"], "delta": a["delta"]}
                    for s, a in adjustments.items() if a["delta"] != 0},
    })
    existing["history"] = existing["history"][-168:]
    existing["updated_at"] = now.isoformat()

    _save_json(SCORING_OVERRIDES, existing)
    return existing


# ═══════════════════════════════════════════════════════════════════════
# STRATEGY HEALTH REPORT
# ═══════════════════════════════════════════════════════════════════════

def generate_health_report(snapshot: dict, adjustments: dict) -> str:
    """Generate human-readable health report for logging."""
    lines = []
    now = snapshot["timestamp"]
    fgi = snapshot.get("fear_greed", "?")
    btc = snapshot.get("btc_price", 0)

    lines.append(f"{'='*60}")
    lines.append(f"HOURLY PERFORMANCE MONITOR — {now}")
    lines.append(f"BTC: ${btc:,.2f} | Fear & Greed: {fgi} | Active: {snapshot['total_active']} | Closed: {snapshot['total_closed']}")
    lines.append(f"{'='*60}")

    # Sort strategies by momentum
    strats = [(s, d) for s, d in snapshot.get("strategies", {}).items()
              if d.get("closed_total", 0) >= MIN_RECENT_PICKS]
    strats.sort(key=lambda x: x[1].get("momentum") or 0, reverse=True)

    # Top improving
    improving = [(s, d) for s, d in strats if (d.get("momentum") or 0) > 10]
    if improving:
        lines.append("\n  IMPROVING STRATEGIES:")
        for s, d in improving[:10]:
            adj = adjustments.get(s, {})
            boost_str = f" → boost={adj.get('boost', '?')}" if s in adjustments else ""
            lines.append(f"    {s[:45]:<45} WR={d['closed_wr']}% momentum=+{d['momentum']:.0f}%{boost_str}")

    # Degrading
    degrading = [(s, d) for s, d in strats if (d.get("momentum") or 0) < -10]
    if degrading:
        lines.append("\n  DEGRADING STRATEGIES:")
        for s, d in degrading[:10]:
            adj = adjustments.get(s, {})
            penalty_str = f" → penalty={adj.get('boost', '?')}" if s in adjustments else ""
            lines.append(f"    {s[:45]:<45} WR={d['closed_wr']}% momentum={d['momentum']:.0f}%{penalty_str}")

    # Active adjustments
    changed = {s: a for s, a in adjustments.items() if a.get("delta", 0) != 0}
    if changed:
        lines.append(f"\n  SCORING ADJUSTMENTS ({len(changed)}):")
        for s, a in sorted(changed.items(), key=lambda x: abs(x[1]["delta"]), reverse=True):
            lines.append(f"    {s[:45]:<45} {a['previous']:+d} → {a['boost']:+d} ({a['delta']:+d}) {a['reasons']}")

    lines.append("")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════
# MASTER MONITOR FUNCTION
# ═══════════════════════════════════════════════════════════════════════

def run_hourly_monitor() -> dict:
    """Run the full hourly monitoring cycle.

    1. Take performance snapshot
    2. Compute scoring adjustments
    3. Apply overrides
    4. Generate health report
    5. Log everything
    """
    print("  [MONITOR] Taking performance snapshot...")
    snapshot = take_performance_snapshot()

    print("  [MONITOR] Computing scoring adjustments...")
    adjustments = compute_scoring_adjustments(snapshot)

    print("  [MONITOR] Applying overrides...")
    overrides = apply_scoring_overrides(adjustments)

    report = generate_health_report(snapshot, adjustments)
    print(report)

    # Save snapshot to rolling log
    log = _load_json(MONITOR_LOG) or {"snapshots": []}
    log["snapshots"].append({
        "timestamp": snapshot["timestamp"],
        "btc_price": snapshot["btc_price"],
        "fear_greed": snapshot["fear_greed"],
        "total_active": snapshot["total_active"],
        "adjustments_count": len([a for a in adjustments.values() if a.get("delta", 0) != 0]),
    })
    log["snapshots"] = log["snapshots"][-168:]  # Keep 7 days
    _save_json(MONITOR_LOG, log)

    # Save full snapshot
    _save_json(MONITOR_STATE, snapshot)

    # Mercury #15: Check Gini drift alerts
    gini_alerts = check_gini_drift_alerts()
    if gini_alerts:
        print(f"  [MONITOR] {len(gini_alerts)} Gini drift alert(s)")

    changed = sum(1 for a in adjustments.values() if a.get("delta", 0) != 0)
    print(f"  [MONITOR] Done. {changed} scoring adjustments applied.")

    return {
        "snapshot": snapshot,
        "adjustments": adjustments,
        "gini_alerts": gini_alerts,
        "report": report,
    }


if __name__ == "__main__":
    result = run_hourly_monitor()
