#!/usr/bin/env python3
"""
Context-Aware Score Calibration Engine — hierarchical expected-edge analysis.

Instead of asking "what score threshold is best?", this asks:
"Given this pick's context, what is the expected value of taking it right now?"

Produces context_rankings.json with per-context-bucket statistics and actions:
  promote | neutral | deprioritize | suppress | paper_trade_only

Hierarchy (blended with sample-size-weighted shrinkage):
  Level 0: Global
  Level 1: Asset class
  Level 2: Asset class + setup_type (strategy family)
  Level 3: Symbol (only when n >= MIN_SYMBOL_TRADES)

Usage:
  python analysis/score_calibration.py
  python analysis/score_calibration.py --payload audit_dashboard/data/dashboard_data.json
  python analysis/score_calibration.py --output data/context_rankings.json --verbose
"""

import argparse
import json
import math
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

_WORKSPACE = Path(__file__).resolve().parent.parent
_DEFAULT_PAYLOAD = _WORKSPACE / "audit_dashboard" / "data" / "dashboard_data.json"
_DEFAULT_OUTPUT = _WORKSPACE / "data" / "context_rankings.json"

# ── Constants ──
PNL_CAP = 500.0
MIN_PNL_THRESHOLD = 0.01
PRIOR_WEIGHT = 20          # Bayesian shrinkage prior sample count
MIN_SAMPLE_FOR_ACTION = 10
MIN_SYMBOL_TRADES = 20

# Decay weights by age bucket
DECAY_WEIGHTS = [
    (7, 1.0),     # 0-7 days
    (30, 0.6),    # 8-30 days
    (90, 0.3),    # 31-90 days
    (365, 0.1),   # 91-365 days
]


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


def _decay_weight(age_days: float) -> float:
    """Stepped decay weight based on trade age."""
    for max_age, weight in DECAY_WEIGHTS:
        if age_days <= max_age:
            return weight
    return 0.05


def _classify_strategy(strategy: str) -> str:
    """Map granular strategy names to broader setup_type families."""
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


def _score_bucket(score: float) -> str:
    """Bucket scores into actionable ranges."""
    if score < 30:
        return "<30"
    if score < 40:
        return "30-40"
    if score < 50:
        return "40-50"
    if score < 60:
        return "50-60"
    if score < 70:
        return "60-70"
    return "70+"


def _volatility_bucket(rr_ratio: float) -> str:
    """Rough volatility proxy from R:R ratio."""
    if rr_ratio <= 0:
        return "unknown"
    if rr_ratio < 1.5:
        return "tight"
    if rr_ratio < 2.5:
        return "normal"
    return "wide"


# ── Data Loading ──

def load_picks(payload_path: str) -> list[dict]:
    with open(payload_path, encoding="utf-8") as f:
        data = json.load(f)
    picks_section = data.get("picks", data)
    raw = picks_section.get("recent_closed", [])
    now = datetime.now(timezone.utc)
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
        age_days = (now - dt).total_seconds() / 86400 if dt else 180

        strategy = p.get("strategy", "unknown") or "unknown"

        out.append({
            "symbol": p.get("symbol", "UNKNOWN"),
            "asset_class": (p.get("asset_class") or "UNKNOWN").upper(),
            "score": score_f,
            "score_bucket": _score_bucket(score_f),
            "pnl_pct": _cap(pnl_f),
            "direction": (p.get("direction") or "LONG").upper(),
            "strategy": strategy,
            "setup_type": _classify_strategy(strategy),
            "source_system": p.get("source_system", "unknown"),
            "trade_timeframe": (p.get("trade_timeframe") or "UNKNOWN").upper(),
            "wf_verdict": (p.get("wf_verdict") or "UNKNOWN").upper(),
            "trust_tier": (p.get("trust_tier") or "UNKNOWN").upper(),
            "confidence": float(p.get("confidence") or 0),
            "trust_score": float(p.get("trust_score") or 0),
            "forward_wr": float(p.get("forward_wr") or 0),
            "rr_ratio": float(p.get("rr_ratio") or 0),
            "strat_fwd_pf": float(p.get("strat_fwd_pf") or 0),
            "strat_fwd_trades": int(p.get("strat_fwd_trades") or 0),
            "closed_dt": dt,
            "age_days": age_days,
            "decay_weight": _decay_weight(age_days),
        })
    return out


# ── Statistics Engine ──

class BucketStats:
    """Compute time-weighted statistics for a set of picks."""

    def __init__(self, picks: list[dict]):
        self.n = len(picks)
        if not picks:
            self.empty = True
            return
        self.empty = False

        total_w = 0.0
        w_wins = 0.0
        w_losses = 0.0
        w_win_pnl = 0.0
        w_loss_pnl = 0.0
        w_total_pnl = 0.0
        max_dd = 0.0
        holding_periods = []

        for p in picks:
            w = p.get("decay_weight", 1.0)
            total_w += w
            pnl = p["pnl_pct"]
            w_total_pnl += pnl * w
            if pnl > MIN_PNL_THRESHOLD:
                w_wins += w
                w_win_pnl += pnl * w
            elif pnl < -MIN_PNL_THRESHOLD:
                w_losses += w
                w_loss_pnl += abs(pnl) * w
                max_dd = max(max_dd, abs(pnl))
            if p.get("age_hours"):
                holding_periods.append(float(p["age_hours"]))

        self.total_weight = total_w
        self.weighted_wins = w_wins
        self.weighted_losses = w_losses
        resolved = w_wins + w_losses

        self.win_rate = w_wins / resolved if resolved > 0 else 0.0
        self.loss_rate = w_losses / resolved if resolved > 0 else 0.0
        self.avg_win = (w_win_pnl / w_wins) if w_wins > 0 else 0.0
        self.avg_loss = (w_loss_pnl / w_losses) if w_losses > 0 else 0.0
        self.profit_factor = (w_win_pnl / w_loss_pnl) if w_loss_pnl > 0 else (999 if w_win_pnl > 0 else 0)
        self.expectancy = (self.win_rate * self.avg_win) - (self.loss_rate * self.avg_loss)
        self.total_pnl = sum(p["pnl_pct"] for p in picks)
        self.max_drawdown = max_dd
        self.avg_score = sum(p["score"] for p in picks) / self.n

        # Recent trend: compare last-third PF vs first-third
        sorted_picks = sorted(picks, key=lambda x: x.get("closed_dt") or datetime.min.replace(tzinfo=timezone.utc))
        third = max(1, len(sorted_picks) // 3)
        first_third = BucketStats._raw_pf(sorted_picks[:third])
        last_third = BucketStats._raw_pf(sorted_picks[-third:])
        self.pf_trend = last_third - first_third  # positive = improving

    @staticmethod
    def _raw_pf(picks: list[dict]) -> float:
        w = sum(p["pnl_pct"] for p in picks if p["pnl_pct"] > MIN_PNL_THRESHOLD)
        l = abs(sum(p["pnl_pct"] for p in picks if p["pnl_pct"] < -MIN_PNL_THRESHOLD))
        return w / l if l > 0 else (999 if w > 0 else 0)

    def to_dict(self) -> dict:
        if self.empty:
            return {"sample_size": 0}
        return {
            "sample_size": self.n,
            "effective_sample": round(self.total_weight, 1),
            "win_rate": round(self.win_rate * 100, 1),
            "avg_win": round(self.avg_win, 3),
            "avg_loss": round(self.avg_loss, 3),
            "profit_factor": round(min(self.profit_factor, 999), 2),
            "expectancy": round(self.expectancy, 3),
            "total_pnl": round(self.total_pnl, 2),
            "max_drawdown": round(self.max_drawdown, 2),
            "avg_score": round(self.avg_score, 1),
            "pf_trend": round(self.pf_trend, 2),
        }


def shrink_metric(child_val: float, child_n: int, parent_val: float,
                  prior_weight: int = PRIOR_WEIGHT) -> float:
    """Bayesian shrinkage: blend child toward parent proportional to sample size.
    
    blended = (child_n * child_val + prior_weight * parent_val) / (child_n + prior_weight)
    """
    return (child_n * child_val + prior_weight * parent_val) / (child_n + prior_weight)


def decide_action(stats: dict, parent_stats: dict = None) -> str:
    """Decide promote/neutral/deprioritize/suppress/paper_trade_only."""
    n = stats.get("sample_size", 0)
    if n < MIN_SAMPLE_FOR_ACTION:
        return "paper_trade_only"

    pf = stats.get("profit_factor", 0)
    exp = stats.get("expectancy", 0)
    wr = stats.get("win_rate", 0)
    trend = stats.get("pf_trend", 0)

    # Blend with parent if available
    if parent_stats and parent_stats.get("sample_size", 0) >= MIN_SAMPLE_FOR_ACTION:
        pf = shrink_metric(pf, n, parent_stats.get("profit_factor", 1.0))
        exp = shrink_metric(exp, n, parent_stats.get("expectancy", 0))

    if pf < 0.5:
        return "suppress"
    if pf < 0.8 or exp < -0.1:
        return "deprioritize"
    if pf >= 1.3 and exp > 0.1 and n >= 20:
        if trend >= 0:
            return "promote"
        return "neutral"
    if pf >= 1.0:
        return "neutral"
    return "deprioritize"


# ── Hierarchical Analysis ──

def build_hierarchy(picks: list[dict]) -> dict:
    """Build the full context hierarchy: global → asset_class → setup_type → symbol."""

    # Group by context dimensions
    global_stats = BucketStats(picks)

    by_ac = defaultdict(list)
    by_ac_setup = defaultdict(list)
    by_ac_setup_score = defaultdict(list)
    by_symbol = defaultdict(list)
    by_ac_direction = defaultdict(list)
    by_ac_timeframe = defaultdict(list)
    by_ac_wf = defaultdict(list)

    for p in picks:
        ac = p["asset_class"]
        setup = p["setup_type"]
        sb = p["score_bucket"]
        sym = p["symbol"]
        d = p["direction"]
        tf = p["trade_timeframe"]
        wf = p["wf_verdict"]

        by_ac[ac].append(p)
        by_ac_setup[(ac, setup)].append(p)
        by_ac_setup_score[(ac, setup, sb)].append(p)
        by_symbol[sym].append(p)
        by_ac_direction[(ac, d)].append(p)
        by_ac_timeframe[(ac, tf)].append(p)
        by_ac_wf[(ac, wf)].append(p)

    global_d = global_stats.to_dict()
    global_d["action"] = decide_action(global_d)

    # Level 1: Asset class
    asset_classes = {}
    for ac, ac_picks in sorted(by_ac.items()):
        ac_stats = BucketStats(ac_picks)
        ac_d = ac_stats.to_dict()
        ac_d["action"] = decide_action(ac_d, global_d)
        ac_d["asset_class"] = ac

        # Direction breakdown
        ac_d["by_direction"] = {}
        for (a, d), dp in by_ac_direction.items():
            if a == ac:
                ds = BucketStats(dp).to_dict()
                ds["action"] = decide_action(ds, ac_d)
                ac_d["by_direction"][d] = ds

        # Timeframe breakdown
        ac_d["by_timeframe"] = {}
        for (a, tf), tp in by_ac_timeframe.items():
            if a == ac and tf != "UNKNOWN":
                ts = BucketStats(tp).to_dict()
                ts["action"] = decide_action(ts, ac_d)
                ac_d["by_timeframe"][tf] = ts

        # WF verdict breakdown
        ac_d["by_wf_verdict"] = {}
        for (a, wf), wp in by_ac_wf.items():
            if a == ac and wf != "UNKNOWN":
                ws = BucketStats(wp).to_dict()
                ws["action"] = decide_action(ws, ac_d)
                ac_d["by_wf_verdict"][wf] = ws

        # Level 2: Setup types within this asset class
        contexts = []
        for (a, setup), sp in sorted(by_ac_setup.items()):
            if a != ac:
                continue
            ss = BucketStats(sp)
            sd = ss.to_dict()
            sd["setup_type"] = setup
            sd["action"] = decide_action(sd, ac_d)

            # Level 2.5: Score buckets within setup_type
            score_buckets = {}
            for (a2, s2, sb), sbp in by_ac_setup_score.items():
                if a2 == ac and s2 == setup:
                    sbs = BucketStats(sbp).to_dict()
                    sbs["action"] = decide_action(sbs, sd)
                    score_buckets[sb] = sbs
            if score_buckets:
                sd["by_score_bucket"] = score_buckets

            contexts.append(sd)

        ac_d["contexts"] = sorted(contexts, key=lambda x: -x.get("expectancy", 0))
        asset_classes[ac] = ac_d

    # Level 3: Symbol-level (only high-frequency)
    symbol_rankings = []
    for sym, sp in sorted(by_symbol.items(), key=lambda x: -len(x[1])):
        if len(sp) < MIN_SYMBOL_TRADES:
            continue
        ac = sp[0]["asset_class"]
        parent = asset_classes.get(ac, global_d)
        ss = BucketStats(sp)
        sd = ss.to_dict()
        sd["symbol"] = sym
        sd["asset_class"] = ac

        # Blended metrics
        sd["blended_win_rate"] = round(
            shrink_metric(ss.win_rate * 100, len(sp), parent.get("win_rate", 50)), 1
        )
        sd["blended_pf"] = round(
            shrink_metric(min(ss.profit_factor, 50), len(sp), parent.get("profit_factor", 1.0)), 2
        )
        sd["blended_expectancy"] = round(
            shrink_metric(ss.expectancy, len(sp), parent.get("expectancy", 0)), 3
        )
        sd["action"] = decide_action(sd, parent)
        symbol_rankings.append(sd)

    symbol_rankings.sort(key=lambda x: -x.get("blended_expectancy", 0))

    return {
        "global": global_d,
        "asset_classes": asset_classes,
        "symbol_rankings": symbol_rankings,
    }


def generate_output(picks: list[dict]) -> dict:
    hierarchy = build_hierarchy(picks)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "engine": "context_aware_calibration_v2",
        "total_closed_picks": len(picks),
        "decay_weights": {f"<={d}d": w for d, w in DECAY_WEIGHTS},
        "prior_weight": PRIOR_WEIGHT,
        "min_sample_for_action": MIN_SAMPLE_FOR_ACTION,
        "global": hierarchy["global"],
        "asset_classes": hierarchy["asset_classes"],
        "symbol_rankings": hierarchy["symbol_rankings"][:80],
    }


def print_report(output: dict) -> None:
    g = output["global"]
    print(f"\n=== GLOBAL: {g['sample_size']} picks, WR={g['win_rate']}%, "
          f"PF={g['profit_factor']}, Exp={g['expectancy']}, Action={g['action']} ===")

    print("\n=== ASSET CLASS BREAKDOWN ===")
    for ac, ad in sorted(output["asset_classes"].items()):
        print(f"\n  {ac}: n={ad['sample_size']}, WR={ad['win_rate']}%, "
              f"PF={ad['profit_factor']}, Exp={ad['expectancy']}, "
              f"Trend={ad['pf_trend']:+.2f}, Action={ad['action']}")

        for ctx in ad.get("contexts", []):
            if ctx.get("sample_size", 0) < 5:
                continue
            print(f"    {ctx['setup_type']:>18s}: n={ctx['sample_size']:4d}, "
                  f"WR={ctx['win_rate']:5.1f}%, PF={ctx['profit_factor']:6.2f}, "
                  f"Exp={ctx['expectancy']:+.3f}, [{ctx['action']}]")

        for d, ds in ad.get("by_direction", {}).items():
            if ds.get("sample_size", 0) >= 10:
                print(f"    dir={d:>5s}: n={ds['sample_size']:4d}, "
                      f"WR={ds['win_rate']:5.1f}%, PF={ds['profit_factor']:6.2f}, [{ds['action']}]")

        for wf, ws in ad.get("by_wf_verdict", {}).items():
            if ws.get("sample_size", 0) >= 10:
                print(f"    wf={wf:>10s}: n={ws['sample_size']:4d}, "
                      f"WR={ws['win_rate']:5.1f}%, PF={ws['profit_factor']:6.2f}, [{ws['action']}]")

    print("\n=== TOP SYMBOL RANKINGS (blended) ===")
    for sr in output.get("symbol_rankings", [])[:15]:
        print(f"  {sr['symbol']:>15s} ({sr['asset_class']:>8s}): "
              f"n={sr['sample_size']:3d}, WR={sr['blended_win_rate']:5.1f}%, "
              f"PF={sr['blended_pf']:5.2f}, Exp={sr['blended_expectancy']:+.3f}, "
              f"[{sr['action']}]")

    # Summary of actionable contexts
    print("\n=== ACTIONABLE CONTEXT SUMMARY ===")
    promote_count = 0
    suppress_count = 0
    for ac, ad in output["asset_classes"].items():
        for ctx in ad.get("contexts", []):
            a = ctx.get("action", "")
            if a == "promote":
                promote_count += 1
                print(f"  PROMOTE: {ac} + {ctx['setup_type']} "
                      f"(PF={ctx['profit_factor']}, Exp={ctx['expectancy']:+.3f}, n={ctx['sample_size']})")
            elif a == "suppress":
                suppress_count += 1
                print(f"  SUPPRESS: {ac} + {ctx['setup_type']} "
                      f"(PF={ctx['profit_factor']}, Exp={ctx['expectancy']:+.3f}, n={ctx['sample_size']})")
    print(f"\n  Total: {promote_count} promoted, {suppress_count} suppressed")


def main():
    parser = argparse.ArgumentParser(description="Context-aware score calibration engine")
    parser.add_argument("--payload", default=str(_DEFAULT_PAYLOAD))
    parser.add_argument("--output", default=str(_DEFAULT_OUTPUT))
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if not os.path.isfile(args.payload):
        print(f"ERROR: Payload not found at {args.payload}")
        sys.exit(1)

    picks = load_picks(args.payload)
    print(f"Loaded {len(picks)} closed picks from {args.payload}")
    if not picks:
        print("No valid picks. Exiting.")
        sys.exit(1)

    output = generate_output(picks)

    if args.verbose:
        print_report(output)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nWrote context rankings to {args.output}")


if __name__ == "__main__":
    main()
