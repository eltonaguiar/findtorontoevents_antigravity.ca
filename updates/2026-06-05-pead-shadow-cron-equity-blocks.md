# PEAD shadow on alpha-engine-live + EQUITY dragger blocks

## What changed

1. **`alpha-engine-live.yml`** — `PEAD_EQUITY_ENABLED=1`, `PEAD_REQUIRE_GUIDANCE_RAISE=0`, `PEAD_EQUITY_PROBATION=0` on full-cycle scanner (shadow log only).
2. **`quality_gates.py`** — block `("EQUITY", "multi_asset_copytrader")` and `("EQUITY", "regime_accumulation")` in `BLOCKED_ASSET_STRATEGY_PAIRS`.
3. **`tests/test_eagle2_phase0_gates.py`** — regression tests for new blocks.

## Verify

```bash
python3 -m pytest tests/test_eagle2_phase0_gates.py -q
```

## Ops

After merge, next hourly `:03` alpha-engine run should write `alpha_engine/data/pead_shadow_picks.json` when earnings cache has qualifying rows.