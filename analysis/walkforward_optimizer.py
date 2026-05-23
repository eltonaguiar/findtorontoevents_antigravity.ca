#!/usr/bin/env python3
"""
Walk-Forward Context Optimizer — validates that context rankings generalize.

Splits historical picks into rolling train/test windows and checks whether the
"best combinations" from each training window actually perform in the subsequent
test window. This prevents overfitting to one lucky period.

Outputs stability metrics per context bucket:
  - How many windows was it profitable?
  - What is the cross-window PF variance?
  - Does the action (promote/suppress) stay stable?

Usage:
  python analysis/walkforward_optimizer.py
  python analysis/walkforward_optimizer.py --train-days 60 --test-days 14
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

_WORKSPACE = Path(__file__).resolve().parent.parent
_DEFAULT_PAYLOAD = _WORKSPACE / "audit_dashboard" / "data" / "dashboard_data.json"
_DEFAULT_OUTPUT = _WORKSPACE / "data" / "walkforward_results.json"

MIN_PNL = 0.01
PNL_CAP = 500.0
MIN_BUCKET_TRADES = 5


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


def _classify_strategy(strategy: str) -> str:
    s = (strategy or "unknown").lower().strip()
    if not s or s == "unknown":
        return "unknown"
    families = {
        "breakout": ["breakout", "squeeze", "volume_spike", "bollinger"],
        "mean_reversion": ["mean_rev", "rsi_bounce", "rsi2", "williams_r", "vwap_rev", "reversion"],
        "momentum": ["momentum", "macd", "ema_stack", "trend", "hma", "triple_confirm"],
        "scalp": ["scalp", "quick", "rapid"],
        "fear_greed": ["fear_greed", "contrarian", "sentiment"],
        "copy_trader": ["copy_", "copytrader", "copy_hl", "consensus"],
        "ml_model": ["ml_", "xgboost", "lightgbm", "gainer", "predictor"],
        "prop_firm": ["irb_", "prop_", "hoffman"],
    }
    for family, patterns in families.items():
        for pat in patterns:
            if pat in s:
                return family
    return "other"


def load_picks(payload_path: str) -> list[dict]:
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
        if not dt:
            continue
        out.append({
            "symbol": p.get("symbol", "UNKNOWN"),
            "asset_class": (p.get("asset_class") or "UNKNOWN").upper(),
            "score": score_f,
            "pnl_pct": _cap(pnl_f),
            "direction": (p.get("direction") or "LONG").upper(),
            "setup_type": _classify_strategy(p.get("strategy", "")),
            "closed_dt": dt,
        })
    out.sort(key=lambda x: x["closed_dt"])
    return out


def _bucket_pf(picks: list[dict]) -> float:
    w = sum(p["pnl_pct"] for p in picks if p["pnl_pct"] > MIN_PNL)
    l = abs(sum(p["pnl_pct"] for p in picks if p["pnl_pct"] < -MIN_PNL))
    return w / l if l > 0 else (999 if w > 0 else 0)


def _bucket_wr(picks: list[dict]) -> float:
    wins = sum(1 for p in picks if p["pnl_pct"] > MIN_PNL)
    losses = sum(1 for p in picks if p["pnl_pct"] < -MIN_PNL)
    total = wins + losses
    return wins / total if total > 0 else 0


def _bucket_expectancy(picks: list[dict]) -> float:
    wins = [p["pnl_pct"] for p in picks if p["pnl_pct"] > MIN_PNL]
    losses = [abs(p["pnl_pct"]) for p in picks if p["pnl_pct"] < -MIN_PNL]
    total = len(wins) + len(losses)
    if total == 0:
        return 0
    wr = len(wins) / total
    avg_win = sum(wins) / len(wins) if wins else 0
    avg_loss = sum(losses) / len(losses) if losses else 0
    return wr * avg_win - (1 - wr) * avg_loss


def _context_key(p: dict) -> str:
    return f"{p['asset_class']}|{p['setup_type']}"


def walk_forward(picks: list[dict], train_days: int, test_days: int,
                 step_days: int) -> dict:
    """Run walk-forward analysis across rolling windows."""
    if not picks:
        return {"windows": [], "stability": {}}

    start = picks[0]["closed_dt"]
    end = picks[-1]["closed_dt"]

    windows = []
    cursor = start

    while cursor + timedelta(days=train_days + test_days) <= end:
        train_end = cursor + timedelta(days=train_days)
        test_end = train_end + timedelta(days=test_days)

        train_picks = [p for p in picks if cursor <= p["closed_dt"] < train_end]
        test_picks = [p for p in picks if train_end <= p["closed_dt"] < test_end]

        if len(train_picks) < 20 or len(test_picks) < 5:
            cursor += timedelta(days=step_days)
            continue

        # Group train picks by context
        train_by_ctx = defaultdict(list)
        for p in train_picks:
            train_by_ctx[_context_key(p)].append(p)

        # Compute train-period stats per context
        train_actions = {}
        for ctx, tp in train_by_ctx.items():
            pf = _bucket_pf(tp)
            exp = _bucket_expectancy(tp)
            n = len(tp)
            if n < MIN_BUCKET_TRADES:
                action = "paper_trade_only"
            elif pf < 0.5:
                action = "suppress"
            elif pf >= 1.3 and exp > 0.1 and n >= 10:
                action = "promote"
            elif pf >= 1.0:
                action = "neutral"
            else:
                action = "deprioritize"
            train_actions[ctx] = {
                "action": action, "train_pf": round(pf, 2),
                "train_exp": round(exp, 3), "train_n": n,
            }

        # Measure how train actions perform on test data
        test_by_ctx = defaultdict(list)
        for p in test_picks:
            test_by_ctx[_context_key(p)].append(p)

        ctx_results = {}
        for ctx, ta in train_actions.items():
            tp = test_by_ctx.get(ctx, [])
            if not tp:
                continue
            test_pf = _bucket_pf(tp)
            test_exp = _bucket_expectancy(tp)
            test_wr = _bucket_wr(tp)
            ctx_results[ctx] = {
                **ta,
                "test_pf": round(test_pf, 2),
                "test_exp": round(test_exp, 3),
                "test_wr": round(test_wr * 100, 1),
                "test_n": len(tp),
                "action_correct": (
                    (ta["action"] == "promote" and test_pf >= 1.0) or
                    (ta["action"] == "suppress" and test_pf < 1.0) or
                    (ta["action"] in ("neutral", "deprioritize"))
                ),
            }

        # Overall window stats
        promoted = [p for p in test_picks if train_actions.get(_context_key(p), {}).get("action") == "promote"]
        suppressed = [p for p in test_picks if train_actions.get(_context_key(p), {}).get("action") == "suppress"]
        all_test_pf = _bucket_pf(test_picks)
        promoted_pf = _bucket_pf(promoted) if promoted else 0
        suppressed_pf = _bucket_pf(suppressed) if suppressed else 0

        windows.append({
            "window_start": cursor.isoformat(),
            "train_end": train_end.isoformat(),
            "test_end": test_end.isoformat(),
            "train_n": len(train_picks),
            "test_n": len(test_picks),
            "all_test_pf": round(all_test_pf, 2),
            "promoted_pf": round(promoted_pf, 2),
            "promoted_n": len(promoted),
            "suppressed_pf": round(suppressed_pf, 2),
            "suppressed_n": len(suppressed),
            "improvement": round(promoted_pf - all_test_pf, 2) if promoted else None,
            "context_results": ctx_results,
        })

        cursor += timedelta(days=step_days)

    # Compute stability: per-context consistency across windows
    ctx_window_results = defaultdict(list)
    for w in windows:
        for ctx, cr in w.get("context_results", {}).items():
            ctx_window_results[ctx].append(cr)

    stability = {}
    for ctx, results in ctx_window_results.items():
        pfs = [r["test_pf"] for r in results if r["test_pf"] < 999]
        actions = [r["action"] for r in results]
        correct = sum(1 for r in results if r.get("action_correct"))

        import statistics
        stability[ctx] = {
            "windows_seen": len(results),
            "action_accuracy": round(correct / len(results) * 100, 1) if results else 0,
            "dominant_action": max(set(actions), key=actions.count) if actions else "unknown",
            "action_consistency": round(actions.count(max(set(actions), key=actions.count)) / len(actions) * 100, 1) if actions else 0,
            "mean_test_pf": round(statistics.mean(pfs), 2) if pfs else 0,
            "stdev_test_pf": round(statistics.stdev(pfs), 2) if len(pfs) > 1 else 0,
            "profitable_windows": sum(1 for pf in pfs if pf >= 1.0),
            "total_windows": len(pfs),
        }

    return {"windows": windows, "stability": stability}


def main():
    parser = argparse.ArgumentParser(description="Walk-forward context optimizer")
    parser.add_argument("--payload", default=str(_DEFAULT_PAYLOAD))
    parser.add_argument("--output", default=str(_DEFAULT_OUTPUT))
    parser.add_argument("--train-days", type=int, default=60)
    parser.add_argument("--test-days", type=int, default=14)
    parser.add_argument("--step-days", type=int, default=7)
    args = parser.parse_args()

    if not os.path.isfile(args.payload):
        print(f"ERROR: Payload not found at {args.payload}")
        sys.exit(1)

    picks = load_picks(args.payload)
    print(f"Loaded {len(picks)} dated closed picks")

    results = walk_forward(picks, args.train_days, args.test_days, args.step_days)

    print(f"\n=== Walk-Forward Results ({args.train_days}d train / {args.test_days}d test / {args.step_days}d step) ===")
    print(f"  Windows: {len(results['windows'])}")

    if results["windows"]:
        improvements = [w["improvement"] for w in results["windows"] if w.get("improvement") is not None]
        if improvements:
            import statistics
            print(f"  Avg PF improvement (promoted vs all): {statistics.mean(improvements):+.2f}")
            print(f"  Windows where promoted > all: {sum(1 for i in improvements if i > 0)}/{len(improvements)}")

        print(f"\n=== Context Stability (across {len(results['windows'])} windows) ===")
        for ctx, s in sorted(results["stability"].items(), key=lambda x: -x[1].get("mean_test_pf", 0)):
            if s["windows_seen"] < 2:
                continue
            print(f"  {ctx:>35s}: PF={s['mean_test_pf']:5.2f}±{s['stdev_test_pf']:.2f}, "
                  f"action={s['dominant_action']:<15s} "
                  f"consistent={s['action_consistency']:5.1f}%, "
                  f"profitable={s['profitable_windows']}/{s['total_windows']} windows")

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config": {
            "train_days": args.train_days,
            "test_days": args.test_days,
            "step_days": args.step_days,
        },
        "total_picks": len(picks),
        **results,
    }

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nWrote walk-forward results to {args.output}")


if __name__ == "__main__":
    main()
