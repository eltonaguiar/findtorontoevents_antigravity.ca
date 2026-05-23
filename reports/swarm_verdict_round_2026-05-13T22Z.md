# Swarm Verdict Round — 2026-05-13T22:00Z

Three parallel subagents returned verdicts on the remaining P0.5 / P0 queue items. This doc captures the verdicts, the actions taken, and the items still open.

## P0-A — COT Paper-Pilot Graduation Decision

**Verdict: RETURN-TO-REHAB.** The 2026-05-23 graduation gate is not cleared.

**Root cause found by subagent:** The 100-pick CT=F history is **20× over-emission** from only 5 unique CFTC weekly cycles. Consolidating to 1-pick-per-week:
- n=5 real signals (not 101)
- WR = **40%** (2 wins / 5)
- PF = **0.165** (down from 2.73)
- Total PnL = **−$52** (down from +$360)

PR #941's 3-day publication-lag patch is live and correct — but it does NOT suppress any of the existing picks because they were all generated on Wed/Thu after Friday's release. The lag was never the real bug; **over-emission was.** The TIER-1 Renaissance claim is falsified by the over-emission artifact alone.

**Mitigation in place:** A parallel agent shipped the `EMITTED_RELEASES_PATH` dedup ledger in `alpha_engine/cot_positioning.py` (lines 47-114). One-pick-per-weekly-cycle is now enforced going forward. The retroactive history is unfixable; a **fresh 4-week pilot post-dedup** is the only path to graduation.

**New graduation gate (replaces the earlier 3-condition gate):**
1. 4+ unique weekly cycles fired with the dedup ledger
2. Consolidated WR ≥ 75% on that clean sample
3. DSR ≥ 0.85 on the dedup-clean series

Status: BLOCKED until ~2026-06-15 (4 fresh weekly cycles from when dedup landed).

Refs: `reports/cot_paper_pilot_overemission_falsified_20260513.md`, `alpha_engine/cot_positioning.py:47-114`.

## P0.5-5 — Portfolio Circuit-Breaker

**Verdict: ALREADY-WIRED. No work needed. But test coverage gap.**

The Charter §7 daily −3% cap is **live in production** — just not via `alpha_engine/portfolio_circuit_breaker.py` (orphan). It's wired through `alpha_engine/risk_controls.py::DAILY_CLOSE_PCT=-3.0` called from `production_scanner.py:3530`. Persists state to `alpha_engine/data/daily_pnl_tracker.json`. When breached, closes bottom-30% of positions by `elite_score`.

**Test gap:** `tests/test_risk_controls_circuit_breaker_mean.py` exists but tests the mean-vs-sum fix, **not** the −3% trigger. Future PR should add an explicit `test_daily_loss_cap_triggers_at_neg_3pct` regression.

**Orphan removal:** `alpha_engine/portfolio_circuit_breaker.py` + `risk_management/portfolio_circuit_breaker.py` are both unused. Candidate for cleanup in a P3 housekeeping PR (do not delete without a sweep confirming no stale references).

Status: ✅ closed.

## Wire-Up PR (3 charter modules → production)

**Verdict from subagent: READY-TO-IMPLEMENT, Option A (two separate PRs).**

| Module | Wire-up location | Edit size |
|---|---|---|
| `charter_position_sizer.py` | `production_scanner.py:3058` (after `passes_active_gate`, before `passed.append(pick)`) | ~5 lines + import |
| `charter_slippage.py` | `outcome_resolver.py:959` (after `pnl_pct` set, before `status` assignment) | ~3 lines + import |
| `charter_drift_circuit_breaker.py` | `dashboard_generator.py` near `compute_asset_class_health` | TBD — needs separate spec for `circuit_breaker` field |

Plan: ship two surgical PRs (sizer + slippage). Drift wire-up follows after dashboard-generator spec is drafted.

**Risk profile:**
- Sizer wire-up: medium (introduces `portfolio_equity` dependency)
- Slippage wire-up: low (idempotent stamping; doesn't change WIN/LOSS classification)
- Rollback: revert single hunks in each file

Next PR is a clean Option-A first half: slippage wire-up to `outcome_resolver.py`. Sizer wire-up follows separately because it needs portfolio-equity sourcing.

## Items still open after this round

| Item | Status |
|---|---|
| P0.5-4 concentration controls in `quality_gates.py` | TODO (collision risk — defer until cloud-agent's `quality_gates.py` edits stabilize) |
| P0.5-6 cross-class risk-budget allocator | TODO (GPT-OSS-120B find, grep-verified zero matches) |
| P0-B CRYPTO confidence-inversion reproducible-query | TODO |
| P0-C BOND Layers 2 + 3 | TODO |
| Wire-up of position_sizer + drift breaker | TODO (slippage wire-up coming next PR this round) |
| IDEA-B penny-stock float-size bucket analyzer | READY-TO-IMPLEMENT (3.5h, spec landed) |

## Procedural finding

**Parallel-agent coordination is now critical.** While I was investigating the COT graduation, another agent shipped the dedup ledger in the same file. This is the third time this session that parallel agents have either force-pushed branches, shipped identical PRs (PR #968), or modified files I was reading. Recommend a lightweight `.work-in-progress/{filename}.claim` JSON convention before the next session to prevent collisions. The current chaos is productive but fragile.
