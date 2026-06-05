# luxalgo_confluence forward truth — deduped MySQL (2026-06-05)

## What was broken

`luxalgo_confluence_forward_pilot.py` queried non-existent column `resolved_at` on `trading_picks`, fell back to thin JSON samples (n≈13), and overstated promotion proximity.

## What changed

- MySQL path uses `closed_at`, strategy=`luxalgo_confluence`, dedupe by `(symbol, direction, entry_price, close day)`.
- State exports `rolling_30d_pnls` (last 100) + `tier2_evaluation` via `evaluate_forward_tier2()`.

## Verified numbers (2026-06-05)

| Metric | Raw 30d | Deduped 30d |
|--------|---------|-------------|
| n | 909 | **827** |
| WR | 38.3% | **42.0%** |
| PF | ~0.97 | **0.97** |

Lab claim (deep_audit deduped unique): WR 64.4%, PF 2.36, n=381 — **forward deduped does not replicate lab** → remain **SHADOW**, not `PROMOTED_STRATEGIES`.

Tier-2 on last 100 closes: WR 25%, PF 0.57 — **hard fail**.

## Reproducer

```bash
python3 verified_strategies/paper_pilot/luxalgo_confluence_forward_pilot.py --one-shot
python3 tools/phase3_promotion_readiness.py
```