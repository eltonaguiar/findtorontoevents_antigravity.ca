# Peer Investigation — Daily Idea #1: Statistical Edge Validation Framework

**Date:** 2026-05-31
**Investigator:** Claude Opus 4.7
**Slug:** `statistical-edge-validation-framework`

## §1 Verbatim idea (from `/tmp/user_ideas_2026-05-31.json` index 0)

> "even if we back-test, we arent sure how to properly measure future performance, and how many trades would be considered a statistically valid edge? How can we determine if a strategy is ready for production?"

**What to investigate (user-supplied):** "Define a per-asset-class production-readiness framework: minimum sample size (n>=100 closed clean trades?), DSR/PSR/SPA thresholds, OOS validation requirements, walk-forward window, concentration/HHI gates, and a 'ready for real money' checklist. Codify into reports/PRODUCTION_READINESS_FRAMEWORK.md."

## §2 Hypothesis

The repo already *implements* the relevant statistical gates (n / WR / PF / DSR / SPA / PBO / concentration / expectancy) inside `alpha_engine/money_ready_verdict.py` and the per-class thresholds inside `docs/PERFORMANCE_CHARTER.md` — but they are scattered across code + a 135-line charter and there is no single "ready for real money" checklist a reviewer can run down. The hypothesis is that consolidating these into a framework doc will (a) prevent the recurring "is class X ready?" debate and (b) confirm today's NO_EDGE verdict by showing 0/9 classes pass every gate simultaneously.

## §3 Methodology

This is a meta/framework idea, **not** a strategy backtest, so the methodology is:

1. Enumerate the gate constants currently enforced by `money_ready_verdict.py`.
2. Cross-reference each gate to the Charter §2 / §7 / §9 / §10 it implements.
3. Apply every gate to the latest `money_ready_verdict.json` to count how many classes pass.
4. Produce a single checklist that a reviewer can use to block any "size up X" PR.

No SQL is required because the inputs are JSON snapshots already produced by the verdict pipeline.

## §4 Raw data inline

### 4.1 Gate constants — `alpha_engine/money_ready_verdict.py` lines 135–234

```
MIN_N_CLASS = 50          # minimum resolved picks for a class verdict
MIN_N_STRATEGY = 20       # minimum per-strategy picks for SPA inclusion
MIN_WR = 0.55             # default WR floor (per-class overrides in CLASS_WR_FLOORS)
MIN_PF = 1.5              # profit-factor floor (Tier 2)
DSR_THRESHOLD = 0.95      # Deflated Sharpe probability
PBO_THRESHOLD = 0.55      # backtest-overfit probability ceiling
MIN_STRATEGIES_FOR_PBO = 5
SPA_ALPHA = 0.10
MAX_SYMBOL_CONCENTRATION = 0.60       # COMMODITY override 0.85
MAX_SOURCE_CONCENTRATION = 0.40       # COMMODITY override 0.60
CLASS_WR_FLOORS = {COMMODITY=0.40, FOREX=0.40, FUTURES=0.40, ETF=0.45,
                   BOND=0.45, EQUITY=0.52, CRYPTO=0.50}
NB_TRIALS_BY_CLASS = {COMMODITY=3, CRYPTO=14, FOREX=6}
SLIPPAGE_BPS = {CRYPTO=15, EQUITY=10, COMMODITY=12, ETF=8, FOREX=5, BOND=8, FUTURES=10}
```

### 4.2 Live verdict — `audit_dashboard/data/money_ready_verdict.json` (generated 2026-05-30T23:05:42Z)

```
CRYPTO       n=327  WR=37.6%  PF=0.89  MDD=1.0   verdict=NOT_READY
EQUITY       n= 39  WR=28.2%  PF=0.15  MDD=0.98  verdict=INSUFFICIENT_DATA
FOREX        n= 28  WR=28.6%  PF=0.04  MDD=0.81  verdict=INSUFFICIENT_DATA
COMMODITY    n=  9  WR=44.4%  PF=1.81  MDD=—     verdict=INSUFFICIENT_DATA
FUTURES      n= 12  WR=16.7%  PF=0.54  MDD=0.17  verdict=INSUFFICIENT_DATA
ETF          n=  4  WR=50.0%  PF=0.48  MDD=—     verdict=INSUFFICIENT_DATA
BOND         n=  0  WR= 0.0%  PF=0.00  MDD=—     verdict=INSUFFICIENT_DATA
PENNY_STOCK  n=  1  WR= 0.0%  PF=0.00  MDD=—     verdict=INSUFFICIENT_DATA
UNKNOWN      n=  6  WR=66.7%  PF=2.63  MDD=—     verdict=INSUFFICIENT_DATA
TOTAL n_resolved = 426. money_ready classes = 0. watch classes = 0.
```

## §5 Statistical computations

- **Aggregate `n` across all classes:** 426. Only CRYPTO (n=327) clears `MIN_N_CLASS=50`, but it fails PF/WR/MDD.
- **Wilson 95% LB on CRYPTO WR (123/327):** point=0.376, LB ≈ 0.326 — below break-even and below `CLASS_WR_FLOORS[CRYPTO]=0.50`.
- **Bonferroni adjustment for the 9-class multi-test:** at family α=0.05 the per-class threshold is α'=0.0056. **No class produces a p-value below that** because every class fails at least one of {n<50, PF<1.5, WR<floor, MDD>20%}. The Bonferroni hurdle is therefore moot — the gates themselves already reject.
- **Effect size sanity:** the COMMODITY PF=1.81 is the only positive-PF result above the 1.5 floor, but n=9 (Wilson LB on WR ≈ 0.19, way below the 0.40 floor) → noise.

## §6 Cross-check against today's NO_EDGE verdict (10-agent swarm + 3 external AI)

The framework **confirms** the NO_EDGE verdict. Specifically:

- The framework's seven gates (§1 of `PRODUCTION_READINESS_FRAMEWORK.md`) all derive from `money_ready_verdict.py`. The verdict pipeline already evaluates them.
- 0 of 9 classes appear in `summary.money_ready`. 0 appear in `summary.watch`.
- CRYPTO is the only class with `n_resolved ≥ MIN_N_CLASS=50`, and it fails PF (0.89 vs 1.5), WR (37.6% vs 50% floor), and MDD (1.0 = max possible). Source concentration 57.2% would also fail the 40% gate.
- Therefore the user's idea **does not produce a contradiction** with the NO_EDGE verdict. The framework is **policy infrastructure**, not a new strategy. The classification "(a) real and missed earlier" / "(b) cherry-pick" / "(c) thin-sample" / "(d) leakage" does not apply — there is no edge claim being tested.

## §7 Verdict per CLAUDE.md tier system

- **Tier verdict:** **NO_EDGE** for the per-asset-class question (0/9 classes pass the seven gates) AND **INSUFFICIENT_N** for treating "the framework" as a strategy (it has no closed picks).
- **Confidence:** HIGH. Every number sourced verbatim from `money_ready_verdict.json` 2026-05-30T23:05 and `alpha_engine/money_ready_verdict.py` constants.
- **Risk of false negative:** LOW. The framework is the union of gates the verdict pipeline already runs; if anything it is conservative.

## §8 Recommended next step

1. **Adopt** `reports/PRODUCTION_READINESS_FRAMEWORK.md` as canonical companion to `docs/PERFORMANCE_CHARTER.md`.
2. **No size-up actions** until ≥ 1 class clears all seven gates on both rolling-90d and frozen walk-forward windows.
3. **Continue plumbing work** (resolver intrabar fix, dormant backtest edges per MEMORY 2026-05-31) — the binding constraint for 8/9 classes is `n_resolved < 50`, not strategy quality.
4. **Wire the §4 checklist into PR review** for any branch touching `BLOCKED_SOURCE_SYSTEMS`, `quality_gates.py`, or `money_ready_verdict.py`.

## §9 Files produced this investigation

- `reports/PRODUCTION_READINESS_FRAMEWORK.md` (new, ~6KB) — the framework doc the user requested.
- `reports/peer_claude-daily-idea-1-statistical-edge-validation-framework_2026-05-31.md` (this file).

No code touched. No quality_gates / money_ready_verdict changes. Scope ≤ 2 files — eligible for server-side docs PR.
