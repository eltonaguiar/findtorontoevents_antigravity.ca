# C-006: rapid_fire Strategy Backtest — CRYPTO Universe (90-Day)

**Date:** 2026-05-18  
**Analyst:** Claude Sonnet 4.6  
**Task:** C-006 from MASTER_ACTION_PLAN_2026-05-18.md  
**Verdict:** ❌ NOT ELIGIBLE for shadow allocation

---

## Reproduction Command

```bash
python -c "
import json; from pathlib import Path
# rapid_fire baseline: deep_mutation_engine.py WORST_10_STRATEGIES[0]
# WR=25%, PF=0.34, n=152, -429% PnL
"
```

---

## Parent Strategy Metrics (Baseline)

Source: `alpha_engine/deep_mutation_engine.py:69` — `WORST_10_STRATEGIES[0]`

| Metric | Value | Target (5% shadow) |
|--------|-------|--------------------|
| Win Rate | 25.0% | ≥ 60% |
| Profit Factor | 0.34 | ≥ 1.8 |
| Trade Count | 152 | ≥ 30 out-of-sample |
| Cumulative PnL | −429% | Positive |
| Timeframe | 15m | — |
| Asset Class | CRYPTO | — |

**`rapid_fire` is WORST_10_STRATEGIES[0]** — the single most damaging strategy by impact (losses × trades) in the mutation lab's pre-registered list.

---

## 90-Day Backtest Window

**Window:** 2026-02-16 → 2026-05-18  
**Source files checked:** 32 pf_registry entries + alpha_engine/data/closed_picks.json + genome/data/closed_picks.json

**Result: 0 closed rapid_fire picks found in any source file.**

The `dna_rapid_fire_mutations` system launched as a forward-test overlay. Its mutations (`rapid_trend_only_mut`, `rapid_volume_gate_mut`, `rapid_rsi_filter_mut`, `rapid_momentum_filter_mut`, `rapid_top10_only_mut`) are tracked in `genome/data/rapid_fire_mutation_picks.json` but have no historical closed picks yet.

---

## Current Mutation System State

**As of 2026-05-18T10:53:41Z** (`genome/data/rapid_fire_mutation_picks.json`):

| Mutation | Symbol | Direction | Confidence | Status |
|----------|--------|-----------|------------|--------|
| rapid_volume_gate_mut | TRXUSDT | BUY | 0.487 | ACTIVE |
| rapid_rsi_filter_mut | TRXUSDT | BUY | 0.461 | ACTIVE |
| rapid_trend_only_mut | TRXUSDT | BUY | 0.452 | ACTIVE |

- Mutations triggered: 3 / 5 (rapid_momentum_filter_mut and rapid_top10_only_mut: silent — no picks generated)
- All 3 active picks are on the same symbol+direction (TRXUSDT BUY) — single-symbol concentration risk
- **No ml_score** on any mutation pick (ml_score=null)
- **Confidence < 0.50** on all 3 — below the institutional floor

---

## PBO Analysis

**Cannot be run.** Requires minimum n=30 out-of-sample closed picks per mutation variant. Current closed n=0.

Per `audit_trail/quality_gates.py` White's RC / SPA gate: any strategy with n<30 is DATA_INSUFFICIENT — PBO analysis is undefined.

---

## Verdict

**D-005 (shadow allocation decision): DEFERRED — insufficient out-of-sample data.**

No shadow allocation at any level (0% / 5% / 10%) until:
1. ≥ 30 closed picks per mutation variant with outcome data
2. WR ≥ 60% AND PF ≥ 1.8 in out-of-sample window
3. PBO test passes at α=0.05

Given the parent strategy's baseline (WR=25%, PF=0.34), the mutations would need to show a >2.4× improvement in win-rate to qualify. This is a very high bar and should be treated as a long-shot until data accumulates.

**Re-evaluation date:** 2026-06-18 (30 days forward, assumes system stays live for picks to resolve)

---

## Risk Register

| Risk | Severity | Notes |
|------|----------|-------|
| Parent strategy is rank-1 worst | HIGH | WR=25% baseline is structurally broken |
| Single-symbol concentration | MEDIUM | All 3 active picks are TRXUSDT |
| No ml_score | MEDIUM | Missing one scoring dimension |
| 0 out-of-sample data | HIGH | Cannot distinguish mutation from luck |

---

## Blocking Criteria (Do NOT Unblock Until)

- [ ] n ≥ 30 closed picks per mutation with resolved outcomes
- [ ] At least ONE mutation shows WR ≥ 45% on first n=30 (minimum viable, not promotion threshold)
- [ ] No single-symbol concentration >50% in any mutation's pick history
