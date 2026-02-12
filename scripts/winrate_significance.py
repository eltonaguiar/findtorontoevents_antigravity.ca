#!/usr/bin/env python3
"""
Win Rate Significance Tester — Statistical validation of algorithm performance.
Uses binomial test + Wilson score confidence intervals + power analysis.

Features:
  - Binomial test with scipy (fallback to normal approximation)
  - Wilson score 95% confidence intervals
  - Power analysis: minimum trades needed for statistical significance
  - Significance levels: *** (p<0.01), ** (p<0.05), * (p<0.10)
  - Compares each algorithm against 50% null hypothesis (coin flip)
  - Benjamini-Hochberg FDR correction for multiple testing (Harvey/Liu/Zhu 2016)
  - Bonferroni correction for comparison
  - Tiered confidence labels: HIGH / MEDIUM / LOW / INSUFFICIENT

Usage:
  python winrate_significance.py              # Analyze from DB
  python winrate_significance.py --csv FILE   # Analyze from CSV export
  python winrate_significance.py --null 0.55  # Custom null hypothesis (default 0.50)
  python winrate_significance.py --fdr 0.10   # FDR target (default 0.05)
"""
import os
import sys
import json
import csv
import math
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# DB config
DB_HOST = os.getenv('DB_HOST', 'mysql.50webs.com')
DB_USER = os.getenv('DB_USER', 'ejaguiar1_stocks')
DB_PASS = os.getenv('DB_PASS', 'stocks')
DB_NAME = os.getenv('DB_NAME', 'ejaguiar1_stocks')

API_HEADERS = {"User-Agent": "WorldClassIntelligence/1.0"}

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

# Significance thresholds
SIG_LEVELS = [
    (0.01, '***'),
    (0.05, '**'),
    (0.10, '*'),
]

# Minimum sample size tiers (for confidence labeling)
SAMPLE_TIER_HIGH = 50       # HIGH confidence: n >= 50
SAMPLE_TIER_MEDIUM = 20     # MEDIUM confidence: 20 <= n < 50
SAMPLE_TIER_LOW = 10        # LOW confidence: 10 <= n < 20
                            # INSUFFICIENT: n < 10


def fetch_from_db():
    """Fetch closed trades from the lm_trades table."""
    import mysql.connector
    conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT algorithm_name, asset_class, symbol, realized_pnl_usd, realized_pct,
               position_value_usd
        FROM lm_trades
        WHERE status = 'closed' AND algorithm_name != ''
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def fetch_from_csv(csv_path):
    """Load trades from CSV file."""
    rows = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            row['realized_pnl_usd'] = float(row.get('realized_pnl_usd', 0))
            row['realized_pct'] = float(row.get('realized_pct', 0))
            rows.append(row)
    return rows


def binomial_test(successes, trials, null_prob=0.5):
    """
    Two-sided binomial test. Uses scipy if available, otherwise normal approximation.
    Returns p-value.
    """
    try:
        from scipy.stats import binomtest
        result = binomtest(successes, trials, null_prob, alternative='two-sided')
        return result.pvalue
    except ImportError:
        pass

    # Normal approximation fallback
    expected = trials * null_prob
    std = math.sqrt(trials * null_prob * (1 - null_prob))
    if std == 0:
        return 1.0
    z = abs(successes - expected) / std

    # Approximate p-value from z-score using error function
    try:
        p = 2 * (1 - 0.5 * (1 + math.erf(z / math.sqrt(2))))
    except (ValueError, OverflowError):
        p = 0.0
    return max(0, min(1, p))


def wilson_ci(successes, trials, z=1.96):
    """
    Wilson score 95% confidence interval for a proportion.
    Returns (lower, upper) bounds.
    """
    if trials == 0:
        return (0, 0)

    p_hat = successes / trials
    denominator = 1 + z * z / trials
    center = (p_hat + z * z / (2 * trials)) / denominator
    spread = z * math.sqrt((p_hat * (1 - p_hat) + z * z / (4 * trials)) / trials) / denominator

    lower = max(0, center - spread)
    upper = min(1, center + spread)
    return (lower, upper)


def min_trades_for_significance(win_rate, null_prob=0.5, alpha=0.05, power=0.80):
    """
    Estimate minimum trades needed to detect a given win rate as significant
    at the specified alpha level with the desired power.
    Uses the formula: n = ((z_alpha + z_beta)^2 * p0*(1-p0)) / (p1-p0)^2
    """
    effect = abs(win_rate - null_prob)
    if effect == 0:
        return float('inf')

    # z-scores for alpha/2 and beta
    z_alpha = 1.96 if alpha == 0.05 else (2.576 if alpha == 0.01 else 1.645)
    z_beta = 0.842  # power = 0.80

    n = ((z_alpha + z_beta) ** 2 * null_prob * (1 - null_prob)) / (effect ** 2)
    return max(1, int(math.ceil(n)))


def significance_label(p_value):
    """Return significance stars based on p-value."""
    for threshold, stars in SIG_LEVELS:
        if p_value < threshold:
            return stars
    return 'n.s.'


def sample_confidence_tier(n):
    """Return confidence tier based on sample size (power-awareness)."""
    if n >= SAMPLE_TIER_HIGH:
        return 'HIGH'
    elif n >= SAMPLE_TIER_MEDIUM:
        return 'MEDIUM'
    elif n >= SAMPLE_TIER_LOW:
        return 'LOW'
    else:
        return 'INSUFFICIENT'


def apply_bh_fdr(p_values, alpha=0.05):
    """
    Benjamini-Hochberg FDR correction (Harvey/Liu/Zhu 2016 standard).
    Returns (rejected, adjusted_p_values) arrays.
    Uses statsmodels if available, otherwise pure-Python implementation.
    """
    m = len(p_values)
    if m == 0:
        return [], []

    try:
        from statsmodels.stats.multitest import fdrcorrection
        rejected, adj_pvals = fdrcorrection(p_values, alpha=alpha, method='indep')
        return list(rejected), list(adj_pvals)
    except ImportError:
        pass

    # Pure-Python BH fallback (no external dependency)
    # 1. Sort p-values, keeping original indices
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    adj_pvals = [0.0] * m
    rejected = [False] * m

    # 2. Step-up: adjusted_p[i] = min(1, min_{j>=i}(m * p_(j) / rank_j))
    prev_adj = 1.0
    for rank_from_end, (orig_idx, pval) in enumerate(reversed(indexed)):
        rank = m - rank_from_end  # 1-based rank from sorted order
        adj = min(prev_adj, m * pval / rank)
        adj = min(1.0, adj)
        adj_pvals[orig_idx] = adj
        prev_adj = adj

    for i in range(m):
        rejected[i] = adj_pvals[i] <= alpha

    return rejected, adj_pvals


def apply_bonferroni(p_values, alpha=0.05):
    """
    Bonferroni correction — the most conservative multiple testing correction.
    Included for comparison with BH-FDR to show how dramatically significance vanishes.
    """
    m = len(p_values)
    if m == 0:
        return [], []
    adj_pvals = [min(1.0, p * m) for p in p_values]
    rejected = [ap <= alpha for ap in adj_pvals]
    return rejected, adj_pvals


def analyze(trades, null_prob=0.5, fdr_alpha=0.05):
    """
    Run significance tests on all algorithms with multiple testing correction.

    Applies:
      1. Per-algorithm binomial test + Wilson CI + power analysis
      2. Benjamini-Hochberg FDR correction across all algorithms (HLZ 2016)
      3. Bonferroni correction for conservative comparison
      4. Sample-size confidence tiers
    """
    # Group by algorithm|asset
    algo_groups = {}
    for t in trades:
        algo = t.get('algorithm_name', 'Unknown')
        asset = t.get('asset_class', 'unknown')
        key = f"{algo}|{asset}"
        if key not in algo_groups:
            algo_groups[key] = {'algorithm': algo, 'asset_class': asset, 'trades': []}
        pnl = float(t.get('realized_pnl_usd', 0))
        algo_groups[key]['trades'].append(pnl)

    results = []
    raw_p_values = []

    for key, group in algo_groups.items():
        pnls = group['trades']
        n = len(pnls)
        wins = sum(1 for p in pnls if p > 0)
        win_rate = wins / n if n > 0 else 0

        # Binomial test
        p_value = binomial_test(wins, n, null_prob) if n > 0 else 1.0
        sig = significance_label(p_value)

        # Wilson confidence interval
        ci_lower, ci_upper = wilson_ci(wins, n)

        # Power analysis: min trades needed
        min_n = min_trades_for_significance(win_rate, null_prob) if win_rate != null_prob else 999

        # Is the CI entirely above/below null?
        ci_conclusion = 'ABOVE' if ci_lower > null_prob else ('BELOW' if ci_upper < null_prob else 'OVERLAPS')

        # Sample confidence tier
        confidence = sample_confidence_tier(n)

        results.append({
            'algorithm': group['algorithm'],
            'asset_class': group['asset_class'],
            'total_trades': n,
            'wins': wins,
            'win_rate_pct': round(win_rate * 100, 1),
            'null_hypothesis': null_prob,
            'p_value': round(p_value, 6),
            'significance': sig,
            'wilson_ci_lower': round(ci_lower * 100, 1),
            'wilson_ci_upper': round(ci_upper * 100, 1),
            'ci_vs_null': ci_conclusion,
            'min_trades_needed': min_n,
            'has_enough_data': n >= min_n,
            'sample_confidence': confidence,
            # Placeholders — filled after FDR correction
            'p_value_bh_adjusted': 1.0,
            'fdr_significant': False,
            'p_value_bonferroni': 1.0,
            'bonferroni_significant': False,
            'significance_after_fdr': 'n.s.',
        })
        raw_p_values.append(p_value)

    # --- Multiple Testing Corrections (applied across ALL algorithms) ---
    n_tests = len(raw_p_values)

    if n_tests > 0:
        # Benjamini-Hochberg FDR
        bh_rejected, bh_adj_pvals = apply_bh_fdr(raw_p_values, alpha=fdr_alpha)

        # Bonferroni (conservative comparison)
        bonf_rejected, bonf_adj_pvals = apply_bonferroni(raw_p_values, alpha=fdr_alpha)

        for i, r in enumerate(results):
            r['p_value_bh_adjusted'] = round(bh_adj_pvals[i], 6)
            r['fdr_significant'] = bool(bh_rejected[i])
            r['significance_after_fdr'] = significance_label(bh_adj_pvals[i])
            r['p_value_bonferroni'] = round(bonf_adj_pvals[i], 6)
            r['bonferroni_significant'] = bool(bonf_rejected[i])

    # Sort: FDR-significant first, then by adjusted p-value ascending
    sig_order = {'***': 0, '**': 1, '*': 2, 'n.s.': 3}
    results.sort(key=lambda x: (
        0 if x['fdr_significant'] else 1,
        sig_order.get(x['significance_after_fdr'], 4),
        x['p_value_bh_adjusted']
    ))

    return results


def save_results(results, null_prob, fdr_alpha):
    """Save to JSON with FDR correction metadata."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')

    n_tests = len(results)
    sig_raw = sum(1 for r in results if r['significance'] != 'n.s.')
    sig_fdr = sum(1 for r in results if r['fdr_significant'])
    sig_bonf = sum(1 for r in results if r['bonferroni_significant'])

    json_path = os.path.join(OUTPUT_DIR, 'winrate_significance.json')
    with open(json_path, 'w') as f:
        json.dump({
            'generated': ts,
            'null_hypothesis': null_prob,
            'fdr_alpha': fdr_alpha,
            'total_algorithms': n_tests,
            'multiple_testing': {
                'n_tests': n_tests,
                'significant_raw': sig_raw,
                'significant_bh_fdr': sig_fdr,
                'significant_bonferroni': sig_bonf,
                'method': 'Benjamini-Hochberg (independent)',
                'reference': 'Harvey, Liu, Zhu (2016) — ...and the Cross-Section of Expected Returns',
            },
            'sample_tiers': {
                'HIGH': f'>= {SAMPLE_TIER_HIGH} trades',
                'MEDIUM': f'>= {SAMPLE_TIER_MEDIUM} trades',
                'LOW': f'>= {SAMPLE_TIER_LOW} trades',
                'INSUFFICIENT': f'< {SAMPLE_TIER_LOW} trades',
            },
            'results': results
        }, f, indent=2)

    return json_path


def main():
    parser = argparse.ArgumentParser(description='Win Rate Significance Tester')
    parser.add_argument('--csv', help='Path to CSV trade export (skip DB)')
    parser.add_argument('--null', type=float, default=0.50,
                        help='Null hypothesis probability (default 0.50 = coin flip)')
    parser.add_argument('--fdr', type=float, default=0.05,
                        help='FDR target for Benjamini-Hochberg correction (default 0.05)')
    args = parser.parse_args()

    null_prob = args.null
    fdr_alpha = args.fdr

    print("=== Win Rate Significance Tester ===")
    print(f"Null hypothesis: {null_prob*100:.0f}% (H0: algorithm is no better than {null_prob*100:.0f}%)")
    print(f"FDR target: {fdr_alpha*100:.0f}% (Benjamini-Hochberg correction)")

    if args.csv:
        print(f"Loading from CSV: {args.csv}")
        trades = fetch_from_csv(args.csv)
    else:
        print("Fetching from database...")
        trades = fetch_from_db()

    print(f"Loaded {len(trades)} closed trades")

    if not trades:
        print("No trades found. Nothing to analyze.")
        return

    results = analyze(trades, null_prob, fdr_alpha)

    # --- Table 1: Raw results ---
    print(f"\n{'Algorithm':30s} | {'Asset':8s} | {'N':>5} | {'WR%':>6} | {'p-raw':>8} | {'Sig':>4} | "
          f"{'95% CI':>14} | {'Conf':>6}")
    print("-" * 105)
    for r in results:
        ci_str = f"[{r['wilson_ci_lower']:>4.1f}-{r['wilson_ci_upper']:>4.1f}%]"
        conf = r['sample_confidence'][:4]  # HIGH, MED, LOW, INSF
        print(f"{r['algorithm']:30s} | {r['asset_class']:8s} | {r['total_trades']:>5} | "
              f"{r['win_rate_pct']:>5.1f}% | {r['p_value']:>8.4f} | {r['significance']:>4} | "
              f"{ci_str:>14} | {conf:>6}")

    # --- Table 2: Multiple testing correction ---
    n_tests = len(results)
    sig_raw = sum(1 for r in results if r['significance'] != 'n.s.')
    sig_fdr = sum(1 for r in results if r['fdr_significant'])
    sig_bonf = sum(1 for r in results if r['bonferroni_significant'])

    print(f"\n=== Multiple Testing Correction ({n_tests} tests) ===")
    print(f"  Method              | Significant | Lost vs Raw")
    print(f"  --------------------|-------------|------------")
    print(f"  Raw (uncorrected)   | {sig_raw:>11} | {'(baseline)':>11}")
    print(f"  BH-FDR (q={fdr_alpha:.2f})    | {sig_fdr:>11} | {sig_raw - sig_fdr:>10} lost")
    print(f"  Bonferroni          | {sig_bonf:>11} | {sig_raw - sig_bonf:>10} lost")

    # Show which algos lost significance after FDR
    lost_after_fdr = [r for r in results if r['significance'] != 'n.s.' and not r['fdr_significant']]
    if lost_after_fdr:
        print(f"\n  Algorithms losing significance after FDR correction:")
        for r in lost_after_fdr:
            print(f"    - {r['algorithm']} ({r['asset_class']}): "
                  f"raw p={r['p_value']:.4f}{r['significance']} -> adj p={r['p_value_bh_adjusted']:.4f} (n.s.)")

    # Show FDR survivors
    fdr_survivors = [r for r in results if r['fdr_significant']]
    if fdr_survivors:
        print(f"\n  Algorithms surviving FDR correction (genuine signal):")
        for r in fdr_survivors:
            print(f"    + {r['algorithm']} ({r['asset_class']}): "
                  f"adj p={r['p_value_bh_adjusted']:.4f}{r['significance_after_fdr']} "
                  f"WR={r['win_rate_pct']:.1f}% [{r['sample_confidence']}]")

    # --- Sample size warnings ---
    insufficient = [r for r in results if r['sample_confidence'] == 'INSUFFICIENT']
    low_sample = [r for r in results if r['sample_confidence'] == 'LOW']

    if insufficient:
        print(f"\n  WARNING: {len(insufficient)} algorithm(s) have INSUFFICIENT data (n < {SAMPLE_TIER_LOW}):")
        for r in insufficient:
            print(f"    ! {r['algorithm']}: n={r['total_trades']} — results unreliable, need >= {SAMPLE_TIER_LOW}")

    if low_sample:
        print(f"\n  CAUTION: {len(low_sample)} algorithm(s) have LOW confidence (n < {SAMPLE_TIER_MEDIUM}):")
        for r in low_sample:
            min_n_str = str(r['min_trades_needed']) if r['min_trades_needed'] < 999 else "N/A"
            print(f"    ~ {r['algorithm']}: n={r['total_trades']}, needs ~{min_n_str} for power")

    json_path = save_results(results, null_prob, fdr_alpha)
    print(f"\nSaved: {json_path}")


if __name__ == '__main__':
    main()
