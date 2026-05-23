# R:R Band Re-audit — 2026-05-04

## TL;DR

**Both Kimi C1 ("R:R 1.5-2.0 = best, PF 5.81") AND `audit_trail/quality_gates.py:2492-2511` ("DATA CORRECTED 2026-04-01: R:R 1.0-1.5 = 70.8% WR best") are WRONG against live closed-pick data.**

Computed across **7,472** closed picks from `alpha_engine/data/closed_picks.json` (every pick had populated `take_profit`, `stop_loss`, `entry_price`, `pnl_pct` — 0 skipped):

| R:R Band | n | Wins | Loss | WR | Avg PnL | PF |
|---|---|---|---|---|---|---|
| 0.0-0.5 | 27 | 27 | 0 | 100.0% | +0.03% | ∞ |
| 0.5-1.0 | 4 | 4 | 0 | 100.0% | +0.04% | ∞ |
| 1.0-1.5 | 709 | 328 | 381 | 46.3% | -0.02% | **0.52** |
| 1.5-2.0 | 3,818 | 1,022 | 2,796 | 26.8% | -0.15% | **0.36** |
| 2.0-3.0 | 2,883 | 1,066 | 1,817 | 37.0% | -0.17% | 0.45 |
| 3.0-5.0 | 30 | 2 | 28 | 6.7% | -0.03% | 0.07 |
| 5.0+ | 1 | 1 | 0 | 100.0% | +0.04% | ∞ |

## Reconciliation against the two prior claims

### Kimi C1 — REJECTED

Kimi claimed R:R 1.5-2.0 PF 5.81. **Live: PF 0.36 (n=3,818)**. Off by ~16×, opposite direction. Likely the band-segmentation logic Kimi used was applied to a different sample (e.g., "winners-only" cohort or backtest-survivor bias). Cannot be reproduced from `closed_picks.json` under any reasonable interpretation.

The current shipped branch `feat/rr-hard-gate-shadow-2026-05-04` (commit `149fbacd375`) was built to enforce this band. **Per live data, it would target the WORST band by PF.**

### Local 2026-04-01 "DATA CORRECTED" comment — REJECTED

`audit_trail/quality_gates.py:2492-2511` states:
> Closed-pick analysis (1868 picks) shows R:R is INVERTED:
>   R:R < 1.0 = 66.7% WR, R:R 1.0-1.5 = 70.8% WR (BEST),
>   R:R 1.5-2.0 = 45.6%, R:R 2.0-3.0 = 42.4%

**Live (7,472 picks): R:R 1.0-1.5 = 46.3% WR (NOT 70.8%); R:R 1.5-2.0 = 26.8% WR (NOT 45.6%); R:R 2.0-3.0 = 37.0% (NOT 42.4%).**

The 2026-04-01 numbers may have been correct against the n=1,868 sample at the time, but on the current 7,472-pick window they no longer hold. The score-rule in `quality_gates.py` lines 2492-2511 (+10 / 0 / -5 / -10 by band) is acting on outdated assumptions.

## What does the data actually show?

**No R:R band is profitable.** Every band with n > 30 has PF < 1.0:
- 1.0-1.5: PF 0.52 (least bad, but still loss-making)
- 1.5-2.0: PF 0.36 (worst)
- 2.0-3.0: PF 0.45
- 3.0-5.0: PF 0.07 (effectively random + bad)

The 100% WR bands (0.0-0.5, 0.5-1.0, 5.0+) have n ≤ 27 — too small to draw conclusions; almost certainly survivor / sample artifacts.

This is consistent with the broader audit finding (`reports/super_swarm_synthesis_2026_05_04.md` AHF-04): **11/11 strategies are in HIGH degradation alert, portfolio MDD is 680%, system Sharpe is 0.13**. The R:R band is a downstream symptom, not a fixable lever.

## Recommended actions

### 1. DO NOT MERGE `feat/rr-hard-gate-shadow-2026-05-04` as currently coded.

The constants `RR_HARD_GATE_MIN = 1.5`, `RR_HARD_GATE_MAX = 2.0` would gate to the WORST band by PF. This must change before merge.

**Option A** — Withdraw the gate entirely. None of the bands are tradable per current data. Open a follow-up investigation PR to find a different selection axis (asset class? trust_score? regime?).

**Option B** — Repoint the gate to `RR_HARD_GATE_MIN = 1.0`, `RR_HARD_GATE_MAX = 1.5` (the least-bad band). Ship in shadow mode only; flip ON only if shadow logs confirm in-band PF stays meaningfully above out-of-band PF over a 14-day window.

**Option C** — Ship a "diagnostic-only" shadow gate that LOGS R:R-vs-outcome correlation per pick to `logs/rr_diagnostic.log` for 14 days. No filtering. Use the data to design the right gate.

Recommend Option C for safety: the current data is loud enough that any hard-gate decision based on it is premature.

### 2. Update or remove the `quality_gates.py:2492-2511` comment.

The +10 / -5 / -10 score adjustments per band are acting on stale numbers. Either:
- **Remove** the band-based score adjustment entirely (simplest); or
- **Recompute** from current closed_picks.json and update the comment + branch breakpoints.

A separate PR (`fix/quality-gates-rr-score-recalibration-2026-05-04`) is the cleanest path.

### 3. Withdraw AHF-02 + C3 from the unified queue

(Already done in commit `7ce485e9605` — the null-TP claim was a swarm fabrication; 0/60 picks have null TP.)

## Methodology

- Source: `alpha_engine/data/closed_picks.json` (7,472 picks, all with TP/SL/entry/pnl populated)
- R:R formula: `abs(take_profit - entry_price) / abs(entry_price - stop_loss)`
- Win definition: `pnl_pct > 0`
- PF formula: `sum(positive pnl) / abs(sum(negative pnl))`
- No filtering by asset class, strategy, or time period — first-pass aggregate.

## Follow-up data slices to run before final decision

- Per-asset-class R:R bands (EQUITY may differ from CRYPTO)
- Time-windowed (last 30/60/90 days only) — current data may be diluted by stale entries
- Per-strategy R:R bands (some strategies may benefit from tight TP, others from wide)
- Per-source-system R:R bands — `quan_engine` vs `alpha_engine` vs `unknown` likely differ

These slices would inform Option B vs Option C choice.

## Provenance

- Run date: 2026-05-04
- Tool: ad-hoc Python on `closed_picks.json`; equivalent to `tools/mutation_analysis.py --json` but R:R-aware
- Branch: `feat/audit-score-tooltips-2026-05-04`, planned commit follows this report.
