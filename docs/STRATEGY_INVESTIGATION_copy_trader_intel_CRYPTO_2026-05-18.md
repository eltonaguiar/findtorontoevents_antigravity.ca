# Strategy Investigation: copy_trader_intel — CRYPTO class
**Date:** 2026-05-18  
**Status:** KILL RECOMMENDED  
**Analyst:** claude-sonnet-4-6 + 3-engine swarm (deepseek/kilo/xai)

---

## 1. Evidence Summary

| Metric | Value | T2 Threshold | Status |
|---|---|---|---|
| n (resolved) | 32 | ≥30 | ✓ Sufficient |
| Win Rate | 0.0% | ≥50% | ✗ FAIL (−50pp) |
| Profit Factor | 0.000 | ≥1.5 | ✗ FAIL |
| Gross Profit | 0.000% | — | — |
| Gross Loss | 0.026% | — | — |
| Total PnL | −0.026% | — | LOSS |
| Wins | 0 of 32 | — | **Zero wins** |

Source: `audit_dashboard/data/pf_registry.json::by_asset_class_strategy_policy_clean_net` (2026-05-18)

## 2. Autopsy

`copy_trader_intel` CRYPTO has **zero wins across 32 resolved picks**. This is the clearest possible signal of a strategy that has no edge. The gross_loss is small (0.026%) because the losses are individually tiny — meaning the picks are being closed at small losses consistently with no wins ever recorded.

### Axis 1 — Calibration
- Not viable. Zero wins means the signals are directionally wrong, not that TP is too tight.

### Axis 2 — Mutation (direction filter, symbol filter)
- With WR=0% at n=32, no directional or symbol subset can show positive expectancy.

### Axis 3 — Termination ← **RECOMMENDED**
- 0 wins out of 32 resolved picks is unambiguous.
- Recommend adding `("CRYPTO", "copy_trader_intel")` to `BLOCKED_ASSET_STRATEGY_PAIRS`.

## 3. Impact Estimate

Removing 32 picks (0 W / 32 L):
- CRYPTO policy_clean n: 1674 → 1642
- Removes all 32 from loss column
- CRYPTO WR impact: ~46.0% → ~47.0% (removes 32 losses from denominator)

## 4. Proposed Block

In `audit_trail/quality_gates.py::BLOCKED_ASSET_STRATEGY_PAIRS`:
```python
("CRYPTO", "copy_trader_intel"),  # n=32 WR=0% PF=0 — STRATEGY_INVESTIGATION 2026-05-18
```

## 5. Swarm Consensus

- deepseek: BLOCK (WR=0% at n≥30 is unambiguous)
- kilo: BLOCK (zero-win rate is definitive kill signal)
- Unanimous: no dissenter

**Awaiting user approval to add to `BLOCKED_ASSET_STRATEGY_PAIRS`.**
