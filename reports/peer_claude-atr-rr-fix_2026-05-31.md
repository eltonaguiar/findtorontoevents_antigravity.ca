# Peer: Variant C R:R Fix for `atr_percentile_gate_scanner`

**Date:** 2026-05-31
**Author:** Claude Opus 4.7 (peer subagent)
**Branch:** `fix/atr-percentile-gate-rr-variant-c`
**Evidence source:** `reports/rr_optimization_analysis_2026-05-31.md`

## TL;DR

`atr_percentile_gate_scanner` has a real entry edge (WR 56.58% on
`at_signal_outcomes`) but bleeds money — PF 0.49, payoff 0.38 — because the
fixed-multiple SL/TP (1.5x / 2.5x ATR) lets wins cap at +0.67% (p90) while
SL_HIT losses tail to −9.85%. Variant C replaces the SL/TP with a tighter
SL (0.75x ATR) and wider TP (3.0x ATR), shifting nominal R:R from 1.67:1 to
4:1. Behavior is gated behind env var `ATR_GATE_VARIANT_C=1` — default OFF
so production stays unchanged until live acceptance metrics pass.

## Approach

- **No new module.** Strategy code edited in place to avoid a second
  parallel scanner that drifts from the original. Single TP/SL block now
  reads multipliers from env vars; old behavior is the explicit `else`.
- **Feature flag default OFF** so this PR is a no-op in prod the moment it
  merges. Acceptance run is opt-in via env in the picks job.
- **Tunable knobs**: `ATR_GATE_TP_MULT` (default 3.0), `ATR_GATE_SL_MULT`
  (default 0.75). The orchestrator can sweep these without code changes.

## Code locations

| File | Lines | Change |
|---|---|---|
| `alpha_engine/proven_edge_strategies.py` | ~957-985 (was 957-963) | Replaced fixed TP/SL block with env-flagged Variant C path; legacy 2.5/1.5 multipliers preserved as default. |

No callers changed — `atr_percentile_gate_scanner` remains wired into
`SCANNERS` registry (line ~1154) and `STRATEGY_FUNCTIONS` (line ~1514) and
is referenced by `alpha_engine/smart_picks_engine.py` (line 307) +
`alpha_engine/pair_exceptions.py` (line 60). All current callers retain
identical behavior with `ATR_GATE_VARIANT_C` unset.

## Acceptance criteria (must all pass before flag flips on by default)

1. **n >= 100** closed picks under the flagged-on path.
2. **WR >= 45%** (drop tolerated vs 56.58% baseline because tighter SL
   converts marginal wins into losses).
3. **PF >= 1.5** (Tier 2 floor per `reports/hedge_fund_performance_review_*`).
4. **No SL_HIT < −2.0%** — the entire point of Variant C is killing the
   −9.85% loss tail. Any breach is a hard fail (likely indicates ATR
   collapsed mid-trade or slippage > expectation).
5. Sharpe(realized) >= 1.0 on the flagged cohort.

## Monitoring plan

- Tag picks emitted under the flag with `source_system="proven_edge"` AND
  `rationale` already records ATR percentile — operator queries via
  `WHERE strategy='atr_percentile_gate_scanner' AND created_at >= '<flip-date>'`.
- Daily check on `audit_dashboard/data/pick_summary_stats_48h.json` for the
  strategy row.
- Weekly: rerun `tools/strategy_tier_tracker.py` and confirm tier change.

## Rollback plan

- **Instant**: unset `ATR_GATE_VARIANT_C` in the picks job env — next run
  reverts to 2.5/1.5 multipliers immediately.
- **Code revert**: `git revert <merge sha>` — the only file touched is
  `alpha_engine/proven_edge_strategies.py` and the edit is one contiguous
  block, so a revert cleanly restores the original TP/SL constants.
- **In-flight picks** under the flag continue with the multipliers stamped
  at signal time (TP/SL are absolute prices in the pick record). No
  retroactive change needed.

## Why a feature flag (not direct replacement)

- The evidence is from `at_signal_outcomes` (signal-level fills), not
  live-traded outcomes — sample is forward-looking but unrealized.
- Tighter SL changes the failure mode; we must observe the new failure
  distribution before sizing up.
- Per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`: mutate-before-kill, and gate
  the mutation behind a switch so the old behavior remains a one-line
  rollback.

## NOT done in this PR (deliberate)

- No change to the entry gate (RSI 30-70, EMA9>EMA21, vol 0.85x, ATR pct
  35-97). Entry edge is the strength — only exit math is broken.
- No change to confidence calculation.
- No retroactive backfill on closed picks.
- No auto-merge — human review required.
