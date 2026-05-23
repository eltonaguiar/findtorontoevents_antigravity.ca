#!/usr/bin/env python3
"""
v10.0 Accuracy + Performance Test Suite
Tests the three v10.0 scoring changes against known inputs.
Also benchmarks compute_tournament() against 63-algo x N-pick scenarios.
"""
import sys
import math
import time
import random
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np

# ?? Import scoring functions from live_scanner ?????????????????????????????
sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_scanner import compute_tournament, compute_walk_forward_metrics, STARTING_CAPITAL

NOW = datetime.now(timezone.utc)

PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"
WARN = "\033[93m[WARN]\033[0m"

results = []

def assert_close(label, got, expected, tol=1e-6):
    ok = abs(got - expected) <= tol
    status = PASS if ok else FAIL
    print(f"  {status} {label}")
    print(f"       got={got:.8f}  expected={expected:.8f}  diff={abs(got-expected):.2e}")
    results.append(ok)
    return ok

def assert_eq(label, got, expected):
    ok = got == expected
    status = PASS if ok else FAIL
    print(f"  {status} {label}: got={got!r}  expected={expected!r}")
    results.append(ok)
    return ok

def assert_range(label, got, lo, hi):
    ok = lo <= got <= hi
    status = PASS if ok else FAIL
    print(f"  {status} {label}: got={got:.4f}  [{lo}, {hi}]")
    results.append(ok)
    return ok

# ?????????????????????????????????????????????????????????????????????????????
# SECTION 1: Sortino semi-variance formula
# ?????????????????????????????????????????????????????????????????????????????
print("\n" + "="*60)
print("SECTION 1 -- Sortino semi-variance accuracy")
print("="*60)

def sortino_v10(pnls_arr):
    """Exact v10.0 implementation."""
    p = np.array(pnls_arr, dtype=float)
    if len(p) < 3:
        return 0.0
    semi_var = float((np.minimum(p, 0.0) ** 2).mean())
    dd = math.sqrt(semi_var) if semi_var > 0 else 0.0
    if dd > 0:
        return float(p.mean() / dd)
    return 10.0 if p.mean() > 0 else 0.0

def sortino_old(pnls_arr):
    """Old (buggy) implementation: std(negatives only)."""
    p = np.array(pnls_arr, dtype=float)
    neg = p[p < 0]
    if len(neg) < 2:
        return 0.0
    return float(p.mean() / neg.std())

# Test 1a: all wins -- new should give 10.0 cap; old gives 0 (no negatives)
p1 = [100, 200, 150, 80]
assert_close("All wins: v10 returns 10.0 cap", sortino_v10(p1), 10.0)
assert_close("All wins: old returns 0.0 (no negatives)",  sortino_old(p1), 0.0)

# Test 1b: known manual calculation
# pnls = [100, -50, 200, -30, 150]
# semi_var = mean([0, 2500, 0, 900, 0]) = 3400/5 = 680
# downside_dev = sqrt(680) ~= 26.0768
# mean = (100-50+200-30+150)/5 = 370/5 = 74
# sortino = 74 / 26.0768 ~= 2.8382
p2 = [100, -50, 200, -30, 150]
expected_sv = (0 + 2500 + 0 + 900 + 0) / 5  # = 680
expected_dd = math.sqrt(expected_sv)
expected_s  = np.mean(p2) / expected_dd
assert_close("Known pnl [100,-50,200,-30,150] sortino_v10", sortino_v10(p2), expected_s, tol=1e-4)

# Test 1c: v10 vs old divergence -- old overstates downside
# pnls = [200, -10, 300, -5, 250, -8]
# Old: std([-10,-5,-8]) = std of 3 values = ~2.16, dd large relative to tiny losses
# New: mean([100, 25, 64])/6 = 189/6 = 31.5, dd=sqrt(31.5)=5.61, mean=727/6=121.2, sortino=21.6
p3 = [200, -10, 300, -5, 250, -8]
s_new = sortino_v10(p3)
s_old = sortino_old(p3)
print(f"  [INFO]   Many wins, tiny losses - v10 Sortino={s_new:.3f}, old={s_old:.3f}")
# Old formula uses std(negatives only) -> smaller denominator -> inflated Sortino
# New formula includes all N periods -> correct, lower, more conservative
ok_diverge = s_old > s_new
status = PASS if ok_diverge else FAIL
print(f"  {status} old Sortino > v10 Sortino (old inflates, v10 is more conservative)")
results.append(ok_diverge)

# Test 1d: symmetric losses -- old and new should be fairly close
# pnls = [-50, 100, -50, 100, -50, 100]
# New: semi_var = mean([2500,0,2500,0,2500,0]) = 7500/6 = 1250, dd=35.36, mean=25, s=0.707
# Old: std([-50,-50,-50]) = 0 -> division by zero edge case -> 0.0
p4 = [-50, 100, -50, 100, -50, 100]
s4_new = sortino_v10(p4)
expected_sv4 = 7500/6
expected_s4  = 25.0 / math.sqrt(expected_sv4)
assert_close("Alternating [-50,100]: v10 Sortino", s4_new, expected_s4, tol=1e-4)

# Test 1e: single large loss -- v10 should penalize more appropriately
# pnls = [-500, 100, 100, 100, 100]  (one catastrophic loss)
p5 = [-500, 100, 100, 100, 100]
# semi_var = mean([250000, 0, 0, 0, 0]) = 50000, dd=223.6, mean=(-100), sortino=-0.447
s5_new = sortino_v10(p5)
expected_sv5 = 250000 / 5
expected_s5  = np.mean(p5) / math.sqrt(expected_sv5)
assert_close("One big loss [-500,100x4]: v10 Sortino", s5_new, expected_s5, tol=1e-4)
ok5 = s5_new < 0
print(f"  {PASS if ok5 else FAIL} Catastrophic loss gives negative Sortino: {s5_new:.4f}")
results.append(ok5)

# ?????????????????????????????????????????????????????????????????????????????
# SECTION 2: Streak consistency score
# ?????????????????????????????????????????????????????????????????????????????
print("\n" + "="*60)
print("SECTION 2 -- Streak consistency scoring")
print("="*60)

def streak_score(outcomes):
    """Exact v10.0 streak computation. outcomes: list of 1(win) or 0(loss)."""
    if len(outcomes) < 3:
        return 7.0  # fallback with 2 active
    arr = np.array(outcomes, dtype=int)
    max_win = max_loss = cur = 0
    cur_type = int(arr[0])
    for o in arr:
        o = int(o)
        if o == cur_type:
            cur += 1
        else:
            if cur_type == 1:
                max_win = max(max_win, cur)
            else:
                max_loss = max(max_loss, cur)
            cur, cur_type = 1, o
    if cur_type == 1:
        max_win = max(max_win, cur)
    else:
        max_loss = max(max_loss, cur)
    loss_pen  = min(max_loss * 0.8, 8.0)
    win_bonus = min(max_win  * 0.3, 3.0)
    return max(0.0, min(10.0, 10.0 - loss_pen + win_bonus))

# Test 2a: all wins -- max_loss=0, max_win=N
sc_all_wins = streak_score([1,1,1,1,1,1,1,1,1,1])
assert_close("All wins (10): cons_score = 10.0 (capped)", sc_all_wins, 10.0, tol=1e-9)

# Test 2b: 3-loss streak
sc_3loss = streak_score([1,1,1,0,0,0,1,1])
# max_loss=3, max_win=3, pen=2.4, bonus=0.9, score=8.5
assert_close("3-loss streak: cons=10-2.4+0.9=8.5", sc_3loss, 8.5, tol=1e-9)

# Test 2c: 10-loss streak -- should cap at 8.0 penalty
sc_10loss = streak_score([1,0,0,0,0,0,0,0,0,0,0,1])
# max_loss=10, pen=min(8,8)=8, max_win=1, bonus=0.3, score=2.3
assert_close("10-loss streak: cons=10-8.0+0.3=2.3", sc_10loss, 2.3, tol=1e-9)

# Test 2d: alternating wins/losses -- max_loss=1
sc_alt = streak_score([1,0,1,0,1,0,1,0])
# max_loss=1, max_win=1, pen=0.8, bonus=0.3, score=9.5
assert_close("Alternating W/L: cons=10-0.8+0.3=9.5", sc_alt, 9.5, tol=1e-9)

# Test 2e: long win streak capped at +3
sc_long_win = streak_score([0,1,1,1,1,1,1,1,1,1,1,1,1,1,1])
# max_loss=1, max_win=14, pen=0.8, bonus=min(4.2,3)=3, score=10 (cap)
assert_close("Long win streak: win_bonus capped at 3.0", sc_long_win, 10.0, tol=1e-9)

# Test 2f: < 3 closed picks (fallback)
sc_few = streak_score([1])  # triggers fallback
assert_close("< 3 picks: fallback score = 7.0 (5+2active)", sc_few, 7.0, tol=1e-9)

# ?????????????????????????????????????????????????????????????????????????????
# SECTION 3: Calmar ratio
# ?????????????????????????????????????????????????????????????????????????????
print("\n" + "="*60)
print("SECTION 3 -- Calmar ratio accuracy")
print("="*60)

def calmar_v10(pnls_list):
    """Exact v10.0 Calmar computation."""
    if len(pnls_list) < 2:
        return 0.0
    pnls = np.array(pnls_list, dtype=float)
    cum  = np.cumsum(pnls)
    equity = STARTING_CAPITAL + cum
    running_max = np.maximum.accumulate(equity)
    dd_frac = abs(float(((equity - running_max) / running_max).min()))
    if dd_frac > 1e-6:
        total_ret = float(equity[-1] / STARTING_CAPITAL) - 1
        return total_ret / dd_frac
    return 5.0  # no drawdown -> generous default

# Test 3a: known pnl sequence
# pnls = [200, -100, 300, -150, 500]
# equity = [10200, 10100, 10400, 10250, 10750]
# peak   = [10200, 10200, 10400, 10400, 10750]
# dd_abs = [0, -100, 0, -150, 0] -> dd_frac = 150/10400 ~= 0.01442
# total_ret = (10750/10000) - 1 = 0.075
# calmar = 0.075 / 0.01442 ~= 5.201
p_c1 = [200, -100, 300, -150, 500]
equity = STARTING_CAPITAL + np.cumsum(p_c1)
peak   = np.maximum.accumulate(equity)
dd_frac_expected = abs(((equity - peak) / peak).min())
total_ret_expected = equity[-1] / STARTING_CAPITAL - 1
calmar_expected = total_ret_expected / dd_frac_expected
c1 = calmar_v10(p_c1)
assert_close("Calmar [200,-100,300,-150,500]", c1, calmar_expected, tol=1e-4)

# Test 3b: no drawdown -> returns 5.0
p_c2 = [100, 200, 300, 400]  # monotonically increasing equity
c2 = calmar_v10(p_c2)
assert_close("No drawdown: Calmar = 5.0 (default)", c2, 5.0, tol=1e-9)

# Test 3c: large drawdown -> low Calmar
p_c3 = [200, -800, 300, 200, 100]  # big crash
c3 = calmar_v10(p_c3)
ok_c3 = c3 < 1.0
print(f"  {PASS if ok_c3 else FAIL} Large drawdown gives Calmar < 1.0: {c3:.4f}")
results.append(ok_c3)

# ?????????????????????????????????????????????????????????????????????????????
# SECTION 4: Full compute_tournament() integration
# ?????????????????????????????????????????????????????????????????????????????
print("\n" + "="*60)
print("SECTION 4 -- compute_tournament() integration")
print("="*60)

def make_pick(pnl, days_ago=15, win=None):
    if win is None:
        win = pnl >= 0
    exit_dt = NOW - timedelta(days=days_ago)
    return {
        "pnl": pnl,
        "exitDate": exit_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "CLOSED"
    }

def make_algo(algo_id, closed_pnls, active=0, days_ago_spread=None):
    if days_ago_spread is None:
        days_ago_spread = list(range(5, 5 + len(closed_pnls) * 5, 5))
    picks = [make_pick(pnl, d) for pnl, d in zip(closed_pnls, days_ago_spread)]
    wins = sum(1 for p in closed_pnls if p >= 0)
    total = sum(closed_pnls)
    return {
        "id": algo_id,
        "name": f"Test-{algo_id}",
        "tier": "SCOUT",
        "category": "stock",
        "closedPicks": picks,
        "activePicks": [{"symbol": "SPY"}] * active,
        "droughtScans": 0,
        "totalReturn": (total / STARTING_CAPITAL) * 100,
        "currentValue": STARTING_CAPITAL + total,
    }

# Test 4a: perfect algo (all wins, growing equity)
algo_perfect = make_algo("perfect", [200, 300, 250, 400, 180, 220], active=2)
result_p = compute_tournament([algo_perfect], NOW, regime={"stock": "bull", "crypto": "bull"})
s_perfect = result_p["rankings"][0]["score"]
ok4a = s_perfect >= 60
print(f"  {PASS if ok4a else FAIL} Perfect algo (all wins) score >= 60: {s_perfect}")
results.append(ok4a)

# Test 4b: terrible algo (all losses)
algo_bad = make_algo("terrible", [-200, -300, -150, -400, -180])
result_b = compute_tournament([algo_bad], NOW, regime={"stock": "bull", "crypto": "bull"})
s_bad = result_b["rankings"][0]["score"]
ok4b = s_bad < 20
print(f"  {PASS if ok4b else FAIL} All-loss algo score < 20: {s_bad}")
results.append(ok4b)

# Test 4c: good algo outranks bad algo
ok4c = s_perfect > s_bad
print(f"  {PASS if ok4c else FAIL} Perfect ({s_perfect}) outranks terrible ({s_bad})")
results.append(ok4c)

# Test 4d: regime bonus -- trend algo in bull market gets bonus
algo_trend = make_algo("trend-test", [100, 150, 80, 120])
algo_trend["id"] = "gap-and-go-scout"   # REGIME_BIAS = "trend"
result_bull = compute_tournament([algo_trend], NOW, regime={"stock": "bull", "crypto": "bull"})
result_bear = compute_tournament([algo_trend], NOW, regime={"stock": "bear", "crypto": "bear"})
s_bull = result_bull["rankings"][0]["score"]
s_bear = result_bear["rankings"][0]["score"]
ok4d = s_bull > s_bear
print(f"  {PASS if ok4d else FAIL} Trend algo: bull({s_bull}) > bear({s_bear})")
results.append(ok4d)

# Test 4e: maxLossStreak and calmar present in output
out_fields = result_p["rankings"][0]
ok4e = "maxLossStreak" in out_fields and "calmar" in out_fields
print(f"  {PASS if ok4e else FAIL} JSON has maxLossStreak={out_fields.get('maxLossStreak')} and calmar={out_fields.get('calmar')}")
results.append(ok4e)

# Test 4f: all-wins algo has maxLossStreak=0
ok4f = out_fields["maxLossStreak"] == 0
print(f"  {PASS if ok4f else FAIL} All-wins algo maxLossStreak == 0: {out_fields['maxLossStreak']}")
results.append(ok4f)

# Test 4g: calmar is positive for winning algo
ok4g = out_fields.get("calmar", -1) >= 0
print(f"  {PASS if ok4g else FAIL} Perfect algo calmar >= 0: {out_fields.get('calmar')}")
results.append(ok4g)

# Test 4h: ranking is correct -- scores descend
algos = [
    make_algo("a1", [200, 300, 400, 200, 250]),
    make_algo("a2", [-100, -200, -50, 100, -80]),
    make_algo("a3", [50, 80, 120, 60, 90]),
]
result_r = compute_tournament(algos, NOW)
ranked = result_r["rankings"]
ok4h = ranked[0]["score"] >= ranked[1]["score"] >= ranked[2]["score"]
print(f"  {PASS if ok4h else FAIL} Ranking descends: {ranked[0]['score']} >= {ranked[1]['score']} >= {ranked[2]['score']}")
results.append(ok4h)

# ?????????????????????????????????????????????????????????????????????????????
# SECTION 5: Performance benchmark
# ?????????????????????????????????????????????????????????????????????????????
print("\n" + "="*60)
print("SECTION 5 -- Performance benchmark")
print("="*60)

def make_benchmark_algo(idx, n_closed=20, n_active=2):
    rng = random.Random(idx)
    pnls = [rng.uniform(-300, 500) for _ in range(n_closed)]
    days = sorted(random.sample(range(1, 180), min(n_closed, 179)), reverse=False)
    return {
        "id": f"bench-algo-{idx}",
        "name": f"Bench Algorithm {idx}",
        "tier": "SCOUT",
        "category": rng.choice(["stock", "crypto", "forex"]),
        "closedPicks": [make_pick(p, d) for p, d in zip(pnls, days)],
        "activePicks": [{"symbol": "X"}] * n_active,
        "droughtScans": rng.randint(0, 20),
        "totalReturn": sum(pnls) / STARTING_CAPITAL * 100,
        "currentValue": STARTING_CAPITAL + sum(pnls),
    }

regime_bench = {"stock": "bull", "crypto": "neutral"}

print(f"\n  Scenario A -- 63 algos x 20 closed picks each (realistic):")
algos_63 = [make_benchmark_algo(i, n_closed=20) for i in range(63)]
# Warm-up
compute_tournament(algos_63, NOW, regime_bench)
# Timed
N = 50
t0 = time.perf_counter()
for _ in range(N):
    compute_tournament(algos_63, NOW, regime_bench)
t1 = time.perf_counter()
avg_ms = (t1 - t0) / N * 1000
ok5a = avg_ms < 100
print(f"    {PASS if ok5a else WARN} 63-algo tournament: {avg_ms:.2f} ms avg over {N} runs")
results.append(ok5a)

print(f"\n  Scenario B -- 63 algos x 100 closed picks each (stress):")
algos_stress = [make_benchmark_algo(i, n_closed=100) for i in range(63)]
compute_tournament(algos_stress, NOW, regime_bench)
t0 = time.perf_counter()
for _ in range(20):
    compute_tournament(algos_stress, NOW, regime_bench)
t1 = time.perf_counter()
avg_ms_stress = (t1 - t0) / 20 * 1000
ok5b = avg_ms_stress < 500
print(f"    {PASS if ok5b else WARN} 63-algo x 100 picks: {avg_ms_stress:.2f} ms avg over 20 runs")
results.append(ok5b)

print(f"\n  Scenario C -- single call with no closed picks (cold start / first run):")
algos_empty = [{
    "id": f"empty-{i}", "name": f"Empty {i}", "tier": "SCOUT", "category": "stock",
    "closedPicks": [], "activePicks": [], "droughtScans": 5,
    "totalReturn": 0.0, "currentValue": float(STARTING_CAPITAL),
} for i in range(63)]
t0 = time.perf_counter()
for _ in range(100):
    compute_tournament(algos_empty, NOW, regime_bench)
t1 = time.perf_counter()
avg_ms_empty = (t1 - t0) / 100 * 1000
ok5c = avg_ms_empty < 20
print(f"    {PASS if ok5c else WARN} 63 algos, zero history: {avg_ms_empty:.3f} ms avg (should be near 0)")
results.append(ok5c)

# ?????????????????????????????????????????????????????????????????????????????
# SECTION 6: Edge cases
# ?????????????????????????????????????????????????????????????????????????????
print("\n" + "="*60)
print("SECTION 6 -- Edge cases")
print("="*60)

# Test 6a: pnl = 0 exactly (no win, no loss)
algo_zero = make_algo("zero-pnl", [0, 0, 0, 0])
result_z = compute_tournament([algo_zero], NOW)
ok6a = 0 <= result_z["rankings"][0]["score"] <= 100
print(f"  {PASS if ok6a else FAIL} Zero PnL produces valid score: {result_z['rankings'][0]['score']}")
results.append(ok6a)

# Test 6b: very large positive pnls -- score should be capped at 100
algo_huge = make_algo("huge-wins", [100000, 200000, 150000, 300000])
result_h = compute_tournament([algo_huge], NOW)
ok6b = result_h["rankings"][0]["score"] <= 100.0
print(f"  {PASS if ok6b else FAIL} Huge wins: score capped <= 100: {result_h['rankings'][0]['score']}")
results.append(ok6b)

# Test 6c: exactly 2 closed picks -- below sortino/streak threshold
algo_2 = make_algo("two-picks", [100, -50])
result_2 = compute_tournament([algo_2], NOW)
ok6c = result_2["rankings"][0]["maxLossStreak"] == 0  # < 3 closed -> 0
print(f"  {PASS if ok6c else FAIL} 2 closed picks: maxLossStreak==0 (fallback): {result_2['rankings'][0]['maxLossStreak']}")
results.append(ok6c)

# Test 6d: sortino is NaN-safe
algo_nan = {
    "id": "nan-test", "name": "NaN Test", "tier": "SCOUT", "category": "stock",
    "closedPicks": [make_pick(0), make_pick(0), make_pick(0)],  # all zero pnl
    "activePicks": [], "droughtScans": 0, "totalReturn": 0.0,
    "currentValue": float(STARTING_CAPITAL),
}
result_nan = compute_tournament([algo_nan], NOW)
s_nan = result_nan["rankings"][0]["score"]
ok6d = not math.isnan(s_nan) and not math.isinf(s_nan)
print(f"  {PASS if ok6d else FAIL} All-zero PnL produces finite score: {s_nan}")
results.append(ok6d)

# Test 6e: no regime provided -- doesn't crash, regimeBonus=0
algo_noreg = make_algo("noreg", [100, 200, 150])
result_nr = compute_tournament([algo_noreg], NOW, regime=None)
ok6e = result_nr["rankings"][0]["regimeBonus"] == 0.0
print(f"  {PASS if ok6e else FAIL} regime=None: regimeBonus==0: {result_nr['rankings'][0]['regimeBonus']}")
results.append(ok6e)

# ?????????????????????????????????????????????????????????????????????????????
# SUMMARY
# ?????????????????????????????????????????????????????????????????????????????
print("\n" + "="*60)
passed = sum(results)
total  = len(results)
rate   = passed / total * 100
verdict = "\033[92m ALL PASSED\033[0m" if passed == total else f"\033[91m{total-passed} FAILED\033[0m"
print(f"RESULT: {passed}/{total} passed ({rate:.0f}%)  --  {verdict}")
print("="*60)

sys.exit(0 if passed == total else 1)
