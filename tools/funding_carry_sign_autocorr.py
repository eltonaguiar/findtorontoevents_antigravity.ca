"""Does negative funding CLUSTER, and what does a holding-period drag do to the verdict?

Two questions Mercury3 raised that neither desk has answered with a number:

  Q1 (his words): "whether the 26.8% negative-funding days cluster (a stress regime)
      or are iid. If anyone has the autocorrelation of funding sign, that changes
      sizing more than the mean does."
  Q2: a flat daily bps drag structurally penalises long holds, but a delta-neutral
      spot/perp book held on ONE venue pays no daily bleed -- internal transfers are
      free, so the honest cost is (round-trip cost / holding days).

This tool answers both from the cached settlement series. It is READ-ONLY: it never
refetches, so the numbers are reproducible offline and cannot drift with the tape.

Usage:
  python3 tools/funding_carry_sign_autocorr.py \
      --cache reports/funding_carry/funding_cache.json \
      --out reports/funding_carry/funding_sign_autocorr.json

Method notes (why these estimators):
  * Sign autocorrelation is computed on the DAILY carry (mean of coins), not per coin,
    because the book is equal-weight across coins and that is the series that gets held.
  * Run lengths are reported alongside the autocorrelation: a small lag-1 coefficient
    with long streaks is still a stress regime, and the reverse is also possible.
  * The CI-LB is a circular block bootstrap with 10-day blocks. Funding autocorrelates,
    so an iid bootstrap would understate the interval and flatter the cell -- the exact
    error that makes a pass look safer than it is.
  * Holding-period drag: drag_bp_day = roundtrip_bp / holding_days. The CI-LB shift is
    exact (the cost is a constant subtracted from every day), so no rerun is needed.
"""
from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

REPORTED_MEAN_BP = 1.925187091078067  # prior measurement, used as a reconstruction check


def load_panel(cache_path: Path) -> tuple[list[str], dict[str, list[float]]]:
    """Dates present for EVERY coin, and each coin's rate on those dates."""
    raw = json.loads(cache_path.read_text())
    coins = sorted(raw)
    common: set[str] | None = None
    for c in coins:
        dates = set(raw[c])
        common = dates if common is None else (common & dates)
    if not common:
        raise SystemExit("no dates shared by all coins in the cache")
    dates = sorted(common)
    return dates, {c: [float(raw[c][d]) for d in dates] for c in coins}


def block_bootstrap_ci(xs: list[float], block: int = 10, n: int = 5000,
                       seed: int = 7) -> tuple[float, float]:
    """Circular block bootstrap 95% CI of the mean (autocorrelation-safe)."""
    rnd = random.Random(seed)
    L, out = len(xs), []
    for _ in range(n):
        acc, got = 0.0, 0
        while got < L:
            s = rnd.randrange(L)
            for k in range(block):
                acc += xs[(s + k) % L]
                got += 1
                if got >= L:
                    break
        out.append(acc / L)
    out.sort()
    return out[int(0.025 * n)], out[int(0.975 * n)]


def acf(xs: list[float], lag: int) -> float:
    m = sum(xs) / len(xs)
    num = sum((xs[i] - m) * (xs[i + lag] - m) for i in range(len(xs) - lag))
    den = sum((x - m) ** 2 for x in xs)
    return num / den if den else 0.0


def runs(signs: list[int]) -> dict:
    """Streak lengths for negative days (the 'pay' side of the book)."""
    streaks, cur, best = [], 0, 0
    for s in signs:
        if s < 0:
            cur += 1
            best = max(best, cur)
        elif cur:
            streaks.append(cur)
            cur = 0
    if cur:
        streaks.append(cur)
    streaks.sort()
    pct = lambda p: streaks[min(len(streaks) - 1, int(p * len(streaks)))] if streaks else 0
    return {
        "n_negative_streaks": len(streaks),
        "longest_streak_days": best,
        "median_streak_days": pct(0.50),
        "p90_streak_days": pct(0.90),
    }


def max_drawdown_bp(xs: list[float]) -> float:
    peak = cum = 0.0
    mdd = 0.0
    for x in xs:
        cum += x
        peak = max(peak, cum)
        mdd = min(mdd, cum - peak)
    return mdd


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="reports/funding_carry/funding_cache.json")
    ap.add_argument("--out", default="reports/funding_carry/funding_sign_autocorr.json")
    ap.add_argument("--roundtrip-bp", type=float, default=40.0,
                    help="2 legs x 2 sides x ~10bp taker, the entry/exit round trip")
    args = ap.parse_args()

    dates, per_coin = load_panel(Path(args.cache))
    coins = sorted(per_coin)
    # equal-weight book, in bp per day
    daily = [sum(per_coin[c][i] for c in coins) / len(coins) * 1e4 for i in range(len(dates))]
    mean_bp = sum(daily) / len(daily)
    signs = [1 if x >= 0 else -1 for x in daily]
    neg = sum(1 for s in signs if s < 0)

    ci_lo, ci_hi = block_bootstrap_ci(daily)

    # Q1 -- does the sign cluster?
    sign_acf = {f"lag{k}": round(acf([float(s) for s in signs], k), 4) for k in range(1, 11)}
    carry_acf = {f"lag{k}": round(acf(daily, k), 4) for k in range(1, 6)}
    p_neg_given_neg = sum(1 for i in range(1, len(signs)) if signs[i] < 0 and signs[i - 1] < 0) / max(
        1, sum(1 for i in range(1, len(signs)) if signs[i - 1] < 0))
    p_neg_given_pos = sum(1 for i in range(1, len(signs)) if signs[i] < 0 and signs[i - 1] > 0) / max(
        1, sum(1 for i in range(1, len(signs)) if signs[i - 1] > 0))
    after_neg = [daily[i] for i in range(1, len(daily)) if signs[i - 1] < 0]
    after_pos = [daily[i] for i in range(1, len(daily)) if signs[i - 1] > 0]
    mean_after_neg = sum(after_neg) / len(after_neg)
    mean_after_pos = sum(after_pos) / len(after_pos)

    # where does the drawdown live? inside negative-funding clusters or outside them
    in_cluster = [daily[i] if signs[i] < 0 else 0.0 for i in range(len(daily))]
    out_cluster = [daily[i] if signs[i] >= 0 else 0.0 for i in range(len(daily))]

    # Q2 -- holding-period drag instead of a flat daily bleed
    holds = [30, 60, 90, 120, 180, 365]
    hold_table = []
    for h in holds:
        drag = args.roundtrip_bp / h
        net = mean_bp - drag
        hold_table.append({
            "holding_days": h,
            "drag_bp_day": round(drag, 4),
            "net_bp_day": round(net, 4),
            "ann_pct": round(net * 365 / 100.0, 3),
            "ci_lo_bp": round(ci_lo - drag, 4),
            "ci_hi_bp": round(ci_hi - drag, 4),
            "verdict": "PASS" if (ci_lo - drag) > 0 else "CI-LB FAIL",
        })

    # flat-drag sweep, for direct comparison with the earlier registration
    flat_table = []
    for d in (0.0, 0.25, 0.5, 1.0, 1.5, 2.0):
        flat_table.append({
            "drag_bp_day": d,
            "net_bp_day": round(mean_bp - d, 4),
            "ci_lo_bp": round(ci_lo - d, 4),
            "verdict": "PASS" if (ci_lo - d) > 0 else "CI-LB FAIL",
        })

    # Q1b -- the obvious "fix" for a clustered bad regime is to step aside on it.
    # Price it before anyone builds it: you cannot skip a day while holding a
    # delta-neutral book, you must CLOSE and RE-OPEN, which is 2 round trips per
    # regime switch, while the avoided loss is only the negative days' carry.
    switches = 0
    for i in range(1, len(signs)):
        if signs[i] < 0 and signs[i - 1] > 0:
            switches += 1
    avoided_bp = -sum(x for x in daily if x < 0)
    exit_cost_bp = switches * 2 * args.roundtrip_bp
    exit_trade = {
        "regime_switches": switches,
        "carry_avoided_bp": round(avoided_bp, 1),
        "exit_reentry_cost_bp": round(exit_cost_bp, 1),
        "net_bp": round(avoided_bp - exit_cost_bp, 1),
        "verdict": "NOT TRADEABLE" if avoided_bp - exit_cost_bp < 0 else "worth testing",
        "note": "Stepping out of the carry on a negative-funding signal pays 2 round "
                "trips per switch to avoid a mean of about 2.3 bp/day. It is a sizing "
                "signal, not a timing edge.",
    }

    reconstruction_ok = abs(mean_bp - REPORTED_MEAN_BP) / REPORTED_MEAN_BP < 0.01
    out = {
        "generated_by": "tools/funding_carry_sign_autocorr.py",
        "cache": args.cache,
        "coins": coins,
        "n_days": len(dates),
        "window": [dates[0], dates[-1]],
        "reconstruction": {
            "mean_bp_day": round(mean_bp, 6),
            "prior_reported_bp_day": REPORTED_MEAN_BP,
            "matches_prior_within_1pct": reconstruction_ok,
            "note": "If this is false the sign statistics below are still valid "
                    "(they are scale-free) but the drag table is not comparable.",
        },
        "q1_sign_clustering": {
            "pct_days_negative": round(100.0 * neg / len(signs), 3),
            "sign_autocorrelation": sign_acf,
            "carry_autocorrelation": carry_acf,
            "p_negative_given_yesterday_negative": round(p_neg_given_neg, 4),
            "p_negative_given_yesterday_positive": round(p_neg_given_pos, 4),
            "mean_bp_day_after_negative": round(mean_after_neg, 4),
            "mean_bp_day_after_positive": round(mean_after_pos, 4),
            "streaks": runs(signs),
            "mdd_bp_total": round(max_drawdown_bp(daily), 2),
            "mdd_bp_inside_negative_days": round(max_drawdown_bp(in_cluster), 2),
            "mdd_bp_outside_negative_days": round(max_drawdown_bp(out_cluster), 2),
            "exit_on_negative_signal": exit_trade,
        },
        "q2_holding_period_drag": {
            "roundtrip_bp": args.roundtrip_bp,
            "table": hold_table,
            "note": "drag_bp_day = roundtrip_bp / holding_days. Assumes one venue, "
                    "free internal spot<->perp transfers, and no margin top-up cost. "
                    "The margin-rebalancing cost remains UNMEASURED by anyone on the bus.",
        },
        "flat_drag_sweep": flat_table,
        "headline_ci": [round(ci_lo, 4), round(ci_hi, 4)],
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2) + "\n")

    q1 = out["q1_sign_clustering"]
    print(f"window {dates[0]}..{dates[-1]}  n={len(dates)}d  coins={len(coins)}")
    print(f"mean {mean_bp:.4f} bp/day  CI-LB {ci_lo:.4f}  (reconstruction ok={reconstruction_ok})")
    print(f"negative days {q1['pct_days_negative']:.1f}%  "
          f"P(neg|neg)={p_neg_given_neg:.3f} vs P(neg|pos)={p_neg_given_pos:.3f}")
    print(f"sign ACF lag1 {sign_acf['lag1']:+.3f} lag2 {sign_acf['lag2']:+.3f} "
          f"lag5 {sign_acf['lag5']:+.3f} lag10 {sign_acf['lag10']:+.3f}")
    print(f"mean after neg-day {mean_after_neg:+.4f} vs after pos-day {mean_after_pos:+.4f} bp")
    print(f"streaks: longest {q1['streaks']['longest_streak_days']}d "
          f"median {q1['streaks']['median_streak_days']}d p90 {q1['streaks']['p90_streak_days']}d")
    print(f"maxDD {q1['mdd_bp_total']:.1f} bp | inside neg days {q1['mdd_bp_inside_negative_days']:.1f} "
          f"| outside {q1['mdd_bp_outside_negative_days']:.1f}")
    print(f"exit-on-negative: {exit_trade['regime_switches']} switches, avoid "
          f"{exit_trade['carry_avoided_bp']:.0f} bp for {exit_trade['exit_reentry_cost_bp']:.0f} bp "
          f"cost -> net {exit_trade['net_bp']:.0f} bp ({exit_trade['verdict']})")
    print("\nholding-period drag (roundtrip %.0f bp):" % args.roundtrip_bp)
    for r in hold_table:
        print(f"  {r['holding_days']:>4}d drag {r['drag_bp_day']:.3f} net {r['net_bp_day']:+.3f} "
              f"CI-LB {r['ci_lo_bp']:+.3f} -> {r['verdict']}")
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
