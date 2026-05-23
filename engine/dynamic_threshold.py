#!/usr/bin/env python3
"""
Dynamic Score Threshold Engine — adaptive thresholds per asset class & symbol.

Reads resolved picks from the dashboard payload and computes optimal score
thresholds using a configurable lookback window with exponential time decay.
Outputs data/score_thresholds.json consumed by the scoring pipeline.

The key difference from static calibration: this engine weights recent trades
more heavily (exponential decay) so thresholds adapt as market conditions shift.

Usage:
  python engine/dynamic_threshold.py
  python engine/dynamic_threshold.py --half-life 14 --lookback 60
  python engine/dynamic_threshold.py --output data/score_thresholds.json
"""

import argparse
import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

_WORKSPACE = Path(__file__).resolve().parent.parent
_DEFAULT_PAYLOAD = _WORKSPACE / "audit_dashboard" / "data" / "dashboard_data.json"
_DEFAULT_OUTPUT = _WORKSPACE / "data" / "score_thresholds.json"

MIN_PNL_THRESHOLD = 0.01
PNL_CAP = 500.0
MIN_WEIGHTED_TRADES = 8.0
DEFAULT_THRESHOLD = 50
SEARCH_RANGE = range(30, 81, 5)


def _cap(v: float) -> float:
    return max(-PNL_CAP, min(PNL_CAP, v))


def _parse_dt(s: str) -> datetime | None:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def _time_weight(trade_dt: datetime, now: datetime, half_life_days: float) -> float:
    """Exponential decay: trades from half_life_days ago get weight 0.5."""
    age_days = (now - trade_dt).total_seconds() / 86400
    if age_days < 0:
        return 1.0
    return math.pow(2, -age_days / half_life_days)


def load_picks(payload_path: str) -> list[dict]:
    """Load and validate closed picks from dashboard payload."""
    with open(payload_path, encoding="utf-8") as f:
        data = json.load(f)
    picks_section = data.get("picks", data)
    raw = picks_section.get("recent_closed", [])
    out = []
    for p in raw:
        pnl = p.get("pnl_pct")
        score = p.get("score")
        if pnl is None or score is None:
            continue
        try:
            pnl_f = float(pnl)
            score_f = float(score)
        except (TypeError, ValueError):
            continue
        if pnl_f == 0 and not p.get("exit_reason"):
            continue
        dt = _parse_dt(p.get("closed_at", ""))
        out.append({
            "symbol": p.get("symbol", "UNKNOWN"),
            "asset_class": (p.get("asset_class") or "UNKNOWN").upper(),
            "score": score_f,
            "pnl_pct": _cap(pnl_f),
            "closed_dt": dt,
            "direction": (p.get("direction") or "LONG").upper(),
            "source_system": p.get("source_system", "unknown"),
            "strategy": p.get("strategy", "unknown"),
            "trust_score": float(p.get("trust_score") or 0),
            "confidence": float(p.get("confidence") or 0),
            "forward_wr": float(p.get("forward_wr") or 0),
        })
    return out


def _weighted_pf(picks: list[dict], threshold: float, now: datetime,
                 half_life: float, lookback_days: float) -> dict | None:
    """Compute time-weighted profit factor for picks above a score threshold."""
    cutoff = now - timedelta(days=lookback_days) if lookback_days else None
    above = []
    for p in picks:
        if p["score"] < threshold:
            continue
        if cutoff and p.get("closed_dt") and p["closed_dt"] < cutoff:
            continue
        above.append(p)

    if not above:
        return None

    w_win_pnl = 0.0
    w_loss_pnl = 0.0
    w_wins = 0.0
    w_losses = 0.0
    total_weight = 0.0

    for p in above:
        w = _time_weight(p["closed_dt"], now, half_life) if p.get("closed_dt") else 0.5
        total_weight += w
        pnl = p["pnl_pct"]
        if pnl > MIN_PNL_THRESHOLD:
            w_win_pnl += pnl * w
            w_wins += w
        elif pnl < -MIN_PNL_THRESHOLD:
            w_loss_pnl += abs(pnl) * w
            w_losses += w

    if total_weight < MIN_WEIGHTED_TRADES:
        return None

    pf = w_win_pnl / w_loss_pnl if w_loss_pnl > 0 else (999 if w_win_pnl > 0 else 0)
    wr = w_wins / (w_wins + w_losses) * 100 if (w_wins + w_losses) > 0 else 0

    return {
        "threshold": int(threshold),
        "profit_factor": round(pf, 3),
        "win_rate": round(wr, 1),
        "weighted_trades": round(total_weight, 1),
        "raw_trades": len(above),
        "weighted_win_pnl": round(w_win_pnl, 2),
        "weighted_loss_pnl": round(w_loss_pnl, 2),
    }


def optimize_threshold(picks: list[dict], now: datetime, half_life: float,
                       lookback_days: float, asset_class: str = None,
                       symbol: str = None) -> dict:
    """Find the score threshold maximizing time-weighted profit factor."""
    subset = picks
    if asset_class:
        subset = [p for p in subset if p["asset_class"] == asset_class]
    if symbol:
        subset = [p for p in subset if p["symbol"] == symbol]

    best = None
    for t in SEARCH_RANGE:
        result = _weighted_pf(subset, t, now, half_life, lookback_days)
        if result is None:
            continue
        if best is None or result["profit_factor"] > best["profit_factor"]:
            best = result

    if best is None:
        return {
            "threshold": DEFAULT_THRESHOLD,
            "profit_factor": 0,
            "win_rate": 0,
            "weighted_trades": 0,
            "raw_trades": 0,
            "reason": "insufficient_data",
            "asset_class": asset_class or "ALL",
        }

    best["asset_class"] = asset_class or "ALL"
    if symbol:
        best["symbol"] = symbol
    return best


def pf_circuit_breaker(picks: list[dict], now: datetime, half_life: float,
                       lookback_days: float, min_pf: float = 0.5,
                       min_trades: int = 30) -> list[dict]:
    """Identify asset classes that should be auto-disabled (PF < min_pf)."""
    alerts = []
    for ac in sorted(set(p["asset_class"] for p in picks)):
        ac_picks = [p for p in picks if p["asset_class"] == ac]
        result = _weighted_pf(ac_picks, 0, now, half_life, lookback_days)
        if result and result["raw_trades"] >= min_trades and result["profit_factor"] < min_pf:
            alerts.append({
                "asset_class": ac,
                "profit_factor": result["profit_factor"],
                "win_rate": result["win_rate"],
                "trades": result["raw_trades"],
                "action": "DISABLE",
                "reason": f"PF {result['profit_factor']:.2f} < {min_pf} over {result['raw_trades']} trades",
            })
    return alerts


def generate_output(picks: list[dict], now: datetime, half_life: float,
                    lookback_days: float) -> dict:
    """Generate the full thresholds output JSON."""
    asset_classes = sorted(set(p["asset_class"] for p in picks))

    ac_thresholds = {}
    for ac in asset_classes:
        ac_thresholds[ac] = optimize_threshold(picks, now, half_life, lookback_days, asset_class=ac)

    ac_thresholds["ALL"] = optimize_threshold(picks, now, half_life, lookback_days)

    # Per-symbol overrides (only symbols with enough trades)
    by_symbol = defaultdict(list)
    for p in picks:
        by_symbol[p["symbol"]].append(p)

    symbol_overrides = []
    for sym, sp in sorted(by_symbol.items(), key=lambda x: -len(x[1])):
        if len(sp) < 20:
            continue
        opt = optimize_threshold(sp, now, half_life, lookback_days)
        if opt.get("reason") == "insufficient_data":
            continue
        opt["symbol"] = sym
        opt["asset_class"] = sp[0]["asset_class"]
        opt["total_trades"] = len(sp)
        symbol_overrides.append(opt)

    circuit_breakers = pf_circuit_breaker(picks, now, half_life, lookback_days)

    return {
        "generated_at": now.isoformat(),
        "config": {
            "half_life_days": half_life,
            "lookback_days": lookback_days,
        },
        "total_closed_picks": len(picks),
        "asset_class_thresholds": ac_thresholds,
        "symbol_overrides": symbol_overrides[:50],
        "circuit_breakers": circuit_breakers,
    }


def main():
    parser = argparse.ArgumentParser(description="Dynamic score threshold optimizer")
    parser.add_argument("--payload", default=str(_DEFAULT_PAYLOAD))
    parser.add_argument("--output", default=str(_DEFAULT_OUTPUT))
    parser.add_argument("--half-life", type=float, default=30.0, help="Decay half-life in days")
    parser.add_argument("--lookback", type=float, default=90.0, help="Max lookback window in days")
    args = parser.parse_args()

    if not os.path.isfile(args.payload):
        print(f"ERROR: Payload not found at {args.payload}")
        sys.exit(1)

    picks = load_picks(args.payload)
    print(f"Loaded {len(picks)} closed picks")

    now = datetime.now(timezone.utc)
    output = generate_output(picks, now, args.half_life, args.lookback)

    # Print summary
    print(f"\n=== Dynamic Thresholds (half-life={args.half_life}d, lookback={args.lookback}d) ===")
    for ac, opt in output["asset_class_thresholds"].items():
        print(f"  {ac:>12s}: threshold={opt['threshold']:2d}, PF={opt.get('profit_factor', 0):.2f}, "
              f"WR={opt.get('win_rate', 0):.1f}%, n={opt.get('raw_trades', 0)}")

    if output["circuit_breakers"]:
        print("\n  CIRCUIT BREAKERS:")
        for cb in output["circuit_breakers"]:
            print(f"    {cb['asset_class']}: {cb['reason']} -> {cb['action']}")

    if output["symbol_overrides"]:
        print(f"\n  Top symbol overrides ({len(output['symbol_overrides'])} symbols):")
        for s in output["symbol_overrides"][:10]:
            print(f"    {s['symbol']:>15s}: threshold={s['threshold']:2d}, PF={s.get('profit_factor', 0):.2f}")

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nWrote thresholds to {args.output}")


if __name__ == "__main__":
    main()
