"""Backtest: do tier-stamped picks with fwdWR<45% outperform non-stamped picks
with fwdWR<45%?

Answers the Option A vs Option B policy question surfaced by Copilot's analysis
(docs/HIGH_CONVICTION_DEEP_ANALYSIS_2026-04-14.md): should HC bypass Gate G3b
(forwardWRMinPct) for stamped S/A/B picks?

Method:
  1. Load recent_closed picks from audit_dashboard/data/dashboard_data.json
  2. Re-apply classify_hf_conviction_tier to each (closed picks don't carry
     hf_conviction_tier historically — the field is stamped at generation
     time only on active picks)
  3. Partition picks by (simulated tier, fwdWR band, asset class)
  4. Compute actual WR/PF/sum_pnl per partition
  5. Compare:
     - A1: stamped + fwdWR < 45%  (Option B candidates)
     - A2: stamped + fwdWR >= 45% (current HC-passing picks)
     - B1: unstamped + fwdWR < 45%  (baseline low-WR picks)
     - B2: unstamped + fwdWR >= 45% (baseline high-WR picks)

Decision criterion:
  If A1 WR exceeds B1 WR by at least 10pp AND PF exceeds 1.5,
  then Option B has statistical merit. Otherwise stay Option A.

Caveat: strat_fwd_wr in closed picks is the CURRENT value (updated by each
dashboard regeneration), not the value at entry time. This introduces
look-ahead bias. But if even the look-ahead-biased test shows no signal,
Option A is unambiguously correct.
"""
from __future__ import annotations
import sys
import json
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from alpha_engine.conviction_stack import classify_hf_conviction_tier, load_conviction_tiers_config


def _fnum(x, default=0.0):
    try:
        return float(x) if x is not None else default
    except (TypeError, ValueError):
        return default


def _fwd_wr_at_entry(p: dict) -> float | None:
    """Extract forward WR as a 0-1 float or None."""
    for k in ("strat_fwd_wr", "forward_wr", "fwd_wr"):
        v = p.get(k)
        if v is None:
            continue
        f = _fnum(v, None)
        if f is None:
            continue
        if f > 1.5:
            f = f / 100.0
        return f
    return None


def _normalize_asset(p: dict) -> str:
    ac = str(p.get("asset_class") or "").upper()
    if ac in ("STOCKS", "PENNY_STOCK", "EQUITIES"):
        return "EQUITY"
    if ac == "COMMODITIES":
        return "COMMODITY"
    if ac == "BONDS":
        return "BOND"
    return ac or "CRYPTO"


def partition_stats(picks: list) -> dict:
    """Compute WR/PF/sum/n for a list of picks."""
    pnls = [_fnum(p.get("pnl_pct"), 0.0) for p in picks]
    if not pnls:
        return {"n": 0, "wr": 0.0, "pf": 0.0, "sum": 0.0, "avg": 0.0}
    wins = [x for x in pnls if x > 0]
    losses = [x for x in pnls if x <= 0]
    gp = sum(wins)
    gl = abs(sum(losses))
    return {
        "n": len(pnls),
        "wr": round(len(wins) / len(pnls) * 100, 2),
        "pf": round(gp / gl, 3) if gl > 0 else (99.0 if gp > 0 else 0.0),
        "sum": round(sum(pnls), 2),
        "avg": round(sum(pnls) / len(pnls), 3),
    }


def main():
    d = json.load(open("audit_dashboard/data/dashboard_data.json", encoding="utf-8"))
    closed = d["picks"]["recent_closed"]
    print(f"Total recent_closed picks loaded: {len(closed)}")

    cfg = load_conviction_tiers_config()
    print(f"Tier config: min_fwdWR={cfg.get('min_forward_wr_pct')}% "
          f"min_fwdTrades={cfg.get('min_forward_trades')} "
          f"elite_range={cfg.get('elite_min')}-{cfg.get('elite_max')}")

    # Re-stamp tier on every closed pick
    stamp_counts = defaultdict(int)
    for p in closed:
        try:
            tier, reasons = classify_hf_conviction_tier(p, cfg)
        except Exception:
            tier, reasons = (None, ["classify_error"])
        p["_backtest_tier"] = tier or "NONE"
        p["_backtest_reasons"] = reasons
        stamp_counts[tier or "NONE"] += 1
    print(f"\nRe-stamped tiers: {dict(stamp_counts)}")

    # Partition by (stamped?, fwdWR band)
    def label(p):
        tier = p.get("_backtest_tier")
        stamped = tier in ("S", "A", "B")
        wr = _fwd_wr_at_entry(p)
        if wr is None:
            wr_band = "WR_UNKNOWN"
        elif wr < 0.45:
            wr_band = "WR<45"
        else:
            wr_band = "WR>=45"
        return f"{'STAMPED' if stamped else 'UNSTAMPED'}_{wr_band}"

    buckets: dict[str, list] = defaultdict(list)
    for p in closed:
        buckets[label(p)].append(p)

    print("\n=== Main partition: stamp × fwdWR band ===")
    print(f"{'Bucket':30} {'n':>6} {'WR':>8} {'PF':>8} {'Sum PnL':>10} {'Avg PnL':>10}")
    print("-" * 80)
    for k in sorted(buckets.keys()):
        s = partition_stats(buckets[k])
        print(f"{k:30} {s['n']:>6} {s['wr']:>7.2f}% {s['pf']:>8} {s['sum']:>10} {s['avg']:>10}")

    # Decision: compare STAMPED_WR<45 to UNSTAMPED_WR<45
    print("\n=== Option B decision test ===")
    a1 = partition_stats(buckets.get("STAMPED_WR<45", []))
    b1 = partition_stats(buckets.get("UNSTAMPED_WR<45", []))
    a2 = partition_stats(buckets.get("STAMPED_WR>=45", []))
    b2 = partition_stats(buckets.get("UNSTAMPED_WR>=45", []))
    print(f"A1 (STAMPED + fwdWR<45%, Option B candidates): n={a1['n']} WR={a1['wr']}% PF={a1['pf']}")
    print(f"B1 (UNSTAMPED + fwdWR<45%, baseline low-WR)  : n={b1['n']} WR={b1['wr']}% PF={b1['pf']}")
    print(f"A2 (STAMPED + fwdWR>=45%, current HC pass)   : n={a2['n']} WR={a2['wr']}% PF={a2['pf']}")
    print(f"B2 (UNSTAMPED + fwdWR>=45%, baseline high-WR): n={b2['n']} WR={b2['wr']}% PF={b2['pf']}")

    wr_delta = a1["wr"] - b1["wr"]
    print(f"\nA1 WR minus B1 WR: {wr_delta:+.2f}pp")
    print(f"A1 PF: {a1['pf']}")

    verdict_wr = "yes" if wr_delta >= 10 else "no"
    verdict_pf = "yes" if a1["pf"] >= 1.5 else "no"
    print(f"\nDecision criteria:")
    print(f"  A1 WR beats B1 by >= 10pp? {verdict_wr} (delta={wr_delta:+.2f}pp)")
    print(f"  A1 PF >= 1.5?              {verdict_pf} (pf={a1['pf']})")
    if verdict_wr == "yes" and verdict_pf == "yes":
        verdict = "OPTION B has merit (stamped-low-WR outperforms baseline-low-WR)"
    else:
        verdict = "OPTION A is correct (stamped-low-WR does NOT outperform baseline)"
    print(f"\n>>> VERDICT: {verdict}")

    # Also break down by tier (S/A/B) within the stamped-low-WR bucket
    print("\n=== Breakdown by tier (S/A/B) within STAMPED + fwdWR<45% ===")
    per_tier: dict[str, list] = defaultdict(list)
    for p in buckets.get("STAMPED_WR<45", []):
        per_tier[p["_backtest_tier"]].append(p)
    for t in ("S", "A", "B"):
        s = partition_stats(per_tier.get(t, []))
        print(f"  Tier {t}: n={s['n']} WR={s['wr']}% PF={s['pf']} sum={s['sum']}")

    # Also break down by asset class
    print("\n=== Breakdown by asset class within STAMPED + fwdWR<45% ===")
    per_ac: dict[str, list] = defaultdict(list)
    for p in buckets.get("STAMPED_WR<45", []):
        per_ac[_normalize_asset(p)].append(p)
    for ac in sorted(per_ac.keys()):
        s = partition_stats(per_ac[ac])
        print(f"  {ac}: n={s['n']} WR={s['wr']}% PF={s['pf']} sum={s['sum']}")

    # Save full results for the doc
    out = {
        "generated_at": "2026-04-14",
        "source": "audit_dashboard/data/dashboard_data.json.picks.recent_closed",
        "n_closed_picks": len(closed),
        "tier_config": cfg,
        "stamp_counts": dict(stamp_counts),
        "main_partition": {k: partition_stats(v) for k, v in buckets.items()},
        "decision_test": {
            "A1_stamped_fwdWR_lt_45": a1,
            "B1_unstamped_fwdWR_lt_45": b1,
            "A2_stamped_fwdWR_gte_45": a2,
            "B2_unstamped_fwdWR_gte_45": b2,
            "wr_delta_A1_minus_B1_pp": wr_delta,
            "decision_criteria_met": verdict_wr == "yes" and verdict_pf == "yes",
            "verdict": verdict,
        },
        "per_tier_stamped_low_wr": {t: partition_stats(per_tier.get(t, [])) for t in ("S", "A", "B")},
        "per_asset_class_stamped_low_wr": {ac: partition_stats(per_ac[ac]) for ac in per_ac},
        "caveats": [
            "strat_fwd_wr is the CURRENT value, not the value at pick-creation time. Introduces look-ahead bias.",
            "Historical closed picks do not carry hf_conviction_tier natively; tier was re-stamped via classify_hf_conviction_tier() using the CURRENT classifier logic.",
            "Closed-pick sample includes many auto-expired and time-exit picks; not all are definitive TP/SL resolutions.",
        ],
    }
    Path("docs/BACKTEST_TIER_BYPASS_2026-04-14.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8"
    )
    print("\nWrote docs/BACKTEST_TIER_BYPASS_2026-04-14.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
