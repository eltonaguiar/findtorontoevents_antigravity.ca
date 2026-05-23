"""
Statistical Validation -- Criteria 1 & 2
========================================
Criterion 1: 30+ trades per strategy before claiming edge
Criterion 2: 3+ strategies with p<0.05 at n>30

Tests each strategy against the null hypothesis that it performs
no better than random (50% WR with same R:R profile).
"""
import json, os, math, sys
import numpy as np

# Force UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Pure-Python scipy-free implementation
# (scipy won't build on 32-bit Python 3.14 without VS toolchain)


def load_closed_picks():
    path = os.path.join(os.path.dirname(__file__), "data", "closed_picks.json")
    with open(path) as f:
        return json.load(f)


def _binomial_pmf(k, n, p):
    """Binomial PMF: P(X=k) given n trials, success probability p."""
    return math.comb(n, k) * (p ** k) * ((1 - p) ** (n - k))


def binomial_test(wins, total, null_p=0.5):
    """One-sided binomial test: is WR significantly > null_p?
    Returns p-value = P(X >= wins) under null hypothesis.
    """
    # Sum P(X >= wins) for the upper tail
    p_value = sum(_binomial_pmf(k, total, null_p) for k in range(wins, total + 1))
    return p_value


def bootstrap_test(pnls, n_bootstrap=10000):
    """Bootstrap test: is mean PnL significantly > 0?"""
    observed_mean = np.mean(pnls)
    boot_means = [np.mean(np.random.choice(pnls, len(pnls), replace=True)) for _ in range(n_bootstrap)]
    p_value = np.mean([m <= 0 for m in boot_means])
    ci_95 = (np.percentile(boot_means, 2.5), np.percentile(boot_means, 97.5))
    return observed_mean, p_value, ci_95


def validate():
    picks = load_closed_picks()

    # Group by strategy
    by_strategy = {}
    for p in picks:
        strat = p.get("strategy", p.get("source_system", "unknown"))
        by_strategy.setdefault(strat, []).append(p)

    print("=" * 70)
    print("CRITERION 1: 30+ Trades Per Strategy")
    print("=" * 70)

    sufficient = []
    insufficient = []
    for strat, trades in sorted(by_strategy.items(), key=lambda x: -len(x[1])):
        n = len(trades)
        wins = sum(1 for t in trades if (t.get("pnl_pct") or 0) > 0)
        wr = wins / n if n > 0 else 0
        if n >= 30:
            sufficient.append((strat, n, wins, wr))
        else:
            insufficient.append((strat, n, wins, wr))

    print(f"\nStrategies with 30+ trades: {len(sufficient)}")
    for strat, n, wins, wr in sufficient:
        print(f"  {strat:50s} n={n:4d}  WR={wr:.1%}  ({wins}W/{n-wins}L)")

    print(f"\nStrategies with <30 trades: {len(insufficient)} (INSUFFICIENT for edge claims)")

    print("\n" + "=" * 70)
    print("CRITERION 2: 3+ Strategies with p<0.05 at n>30")
    print("=" * 70)

    significant = []
    for strat, n, wins, wr in sufficient:
        trades = by_strategy[strat]
        pnls = [float(t.get("pnl_pct") or 0) for t in trades]

        # Binomial test (WR > 50%)
        p_binom = binomial_test(wins, n)

        # Bootstrap test (mean PnL > 0)
        mean_pnl, p_boot, ci = bootstrap_test(pnls)

        sig = p_binom < 0.05 or p_boot < 0.05
        marker = "*** SIGNIFICANT ***" if sig else ""

        print(f"\n  {strat} (n={n})")
        print(f"    WR: {wr:.1%} | Binomial p={p_binom:.4f} {'<0.05 ✓' if p_binom < 0.05 else '>0.05 ✗'}")
        print(f"    Mean PnL: {mean_pnl:+.2f}% | Bootstrap p={p_boot:.4f} {'<0.05 ✓' if p_boot < 0.05 else '>0.05 ✗'}")
        print(f"    95% CI: [{ci[0]:+.2f}%, {ci[1]:+.2f}%] {marker}")

        if sig:
            significant.append(strat)

    print(f"\n{'=' * 70}")
    print(f"VERDICT: {len(significant)} strategies significant at p<0.05")
    target = 3
    if len(significant) >= target:
        print(f"  CRITERION 2: PASS ({len(significant)} >= {target})")
    else:
        print(f"  CRITERION 2: FAIL ({len(significant)} < {target})")
    print(f"  Significant strategies: {significant}")

    # Also test COMBINED portfolio
    print(f"\n{'=' * 70}")
    print("COMBINED PORTFOLIO TEST")
    print("=" * 70)
    all_pnls = [float(p.get("pnl_pct") or 0) for p in picks]
    all_wins = sum(1 for p in picks if (p.get("pnl_pct") or 0) > 0)
    mean, p_boot, ci = bootstrap_test(all_pnls)
    p_binom = binomial_test(all_wins, len(picks))
    print(f"  Total trades: {len(picks)}")
    print(f"  WR: {all_wins/len(picks):.1%} | Binomial p={p_binom:.4f}")
    print(f"  Mean PnL: {mean:+.3f}% | Bootstrap p={p_boot:.4f}")
    print(f"  95% CI: [{ci[0]:+.3f}%, {ci[1]:+.3f}%]")

    # POST-GATE projection
    print(f"\n{'=' * 70}")
    print("POST-QUALITY-GATE PROJECTION")
    print("=" * 70)
    gated = [p for p in picks
             if (p.get("confidence") or 0) >= 0.70
             and p.get("category", "crypto").lower() != "forex"
             and not ((p.get("signal_type", "BUY").upper() in ("SELL", "SHORT"))
                      and p.get("regime", "neutral").lower() != "bearish")]
    if gated:
        g_wins = sum(1 for p in gated if (p.get("pnl_pct") or 0) > 0)
        g_pnls = [float(p.get("pnl_pct") or 0) for p in gated]
        g_mean, g_p, g_ci = bootstrap_test(g_pnls)
        print(f"  Picks passing gates: {len(gated)} / {len(picks)} ({len(gated)/len(picks):.0%})")
        print(f"  Gated WR: {g_wins/len(gated):.1%} (was {all_wins/len(picks):.1%})")
        print(f"  Gated Mean PnL: {g_mean:+.3f}% (was {mean:+.3f}%)")
        print(f"  Bootstrap p={g_p:.4f}")


if __name__ == "__main__":
    validate()
