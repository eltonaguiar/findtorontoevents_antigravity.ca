# Swarm review: FX1 JPY-cross block on multi_asset_copytrader

## Context

Branch `fix/forex-jpy-cross-block-multi-asset-copytrader-2026-05-13` adds 5 surgical (FOREX, multi_asset_copytrader, SYMBOL) blocks to `BLOCKED_ASSET_STRATEGY_SYMBOL_TRIPLES`.

## Evidence (AA-7 mutation analysis)

Per-symbol decomposition of `multi_asset_copytrader × FOREX` (n=662 terminal picks):

| Symbol | n | WR% | PF | Verdict |
|---|---:|---:|---:|---|
| EURJPY=X | 154 | 1.9 | 0.02 | KILL |
| USDJPY=X | 132 | 3.0 | 0.04 | KILL |
| GBPJPY=X | 84 | 7.1 | 0.10 | KILL |
| AUDJPY=X | 77 | 3.9 | 0.06 | KILL |
| CADJPY=X | 37 | 10.8 | 0.14 | KILL |
| NZDUSD=X | 58 | 15.5 | 0.29 | watch |
| USDCAD=X | 31 | 35.5 | 0.74 | keep |
| EURGBP=X | 38 | 63.2 | 2.35 | KEEP edge |
| GBPUSD=X | 26 | 61.5 | 1.87 | KEEP edge |
| AUDUSD=X | 16 | 62.5 | 2.67 | KEEP edge |
| USDCHF=X | 8 | 100.0 | ∞ | KEEP edge |

**Pattern:** all 5 JPY-crosses (n=484, ~73% of universe) catastrophic. Non-JPY majors (n=88) at 61-100% WR. Class-wide block destroys real edge; surgical triple-block preserves it.

**Root cause** (4/4 swarm engines): BoJ tightening 2024-2025 inverted prior LONG-USD-vs-JPY carry bias without strategy update.

## Proposed diff

5 tuples added to `BLOCKED_ASSET_STRATEGY_SYMBOL_TRIPLES`:
```python
("FOREX", "multi_asset_copytrader", "EURJPY=X"),
("FOREX", "multi_asset_copytrader", "USDJPY=X"),
("FOREX", "multi_asset_copytrader", "GBPJPY=X"),
("FOREX", "multi_asset_copytrader", "AUDJPY=X"),
("FOREX", "multi_asset_copytrader", "CADJPY=X"),
```

4 unit tests added to `tests/test_fx1_jpy_cross_block.py` — all pass.

## Question to engines

Return strict JSON ONLY:

```json
{
  "verdict": "APPROVE | APPROVE_WITH_CAVEATS | REQUEST_CHANGES | REJECT",
  "merge_decision": "MERGE | HOLD | REJECT",
  "scope_assessment": "<correct | too_aggressive | too_conservative>",
  "missing_symbols_to_consider": ["<symbols that should also be blocked>"],
  "should_block_NZDUSD": "<yes | no | watchlist_only>",
  "production_safety_assessment": "<safe | risky | needs_shadow_mode_first>",
  "rollback_complexity": "<one_block_revert | multi_step | hard>",
  "remaining_concerns": ["<list>"]
}
```

## Constraints

- Surgical triple-block is reversible (just delete the 5 lines)
- This is opposite of class-wide block; preserves non-JPY edge
- Expected impact: removes ~73% of multi_asset_copytrader × FOREX volume that's currently dragging class PF 0.27 → ~1.8 projected
- Note: NZDUSD=X n=58 WR 15.5% PF 0.29 is borderline — left unblocked pending more data
