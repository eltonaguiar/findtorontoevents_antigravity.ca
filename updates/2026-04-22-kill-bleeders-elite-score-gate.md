# Kill Bleeders + Elite Score Gate + Strategy Confidence Throttle

**Date:** 2026-04-22
**Trigger:** 48h performance analysis showed overall portfolio unprofitable (-0.26% crypto avg), with specific filters/strategies having a clear edge.

---

## Changes Made

### 1. Kill `quan_engine_scalp` Strategy

**Problem:** 0% WR, -794% total PnL zombie strategy still generating signals across multiple pipelines.

**Fix:** Added to all kill/block lists:
- `alpha_engine/config.py` → `BLACKLISTED_STRATEGIES` (list)
- `alpha_engine/scanner.py` → `GENERATOR_HARD_KILL` (set)
- `alpha_engine/smart_picks_engine.py` → `BANNED_SYSTEMS` (set)
- `alpha_engine/copy_trader_bridge.py` → `BLACKLISTED_STRATEGIES` (set)

### 2. Throttle `ml_crypto_predictor` (Confidence ≥0.7)

**Problem:** ml_crypto_predictor generates 8/17 crypto picks with confidence=0.50 and elite_score=43 — the worst-performing source. These low-conviction picks dilute returns.

**Fix:**
- Added `STRATEGY_MIN_CONFIDENCE: dict[str, float]` to `alpha_engine/config.py` with `{"ml_crypto_predictor": 0.70}`
- Enforced in `alpha_engine/scanner.py` signal pipeline (post-GENERATOR_HARD_KILL sweep)
- Enforced in `alpha_engine/smart_picks_engine.py` `score_pick()` function

### 3. Implement `MIN_ELITE_SCORE_FOR_PICKS = 70` Gate

**Problem:** Picks with elite_score < 70 have 42.1% WR, -0.94% avg PnL, PF 0.87. Picks with elite_score ≥ 70 have 73.7% WR, +4.06% avg PnL, PF 3.59. The low-score picks are structurally unprofitable.

**Fix:**
- Added `MIN_ELITE_SCORE_FOR_PICKS = 70` to `alpha_engine/config.py` with documented data
- Enforced in `alpha_engine/scanner.py` signal pipeline (post-GENERATOR_HARD_KILL sweep, prints count of filtered signals)
- Enforced in `alpha_engine/smart_picks_engine.py` `score_pick()` function (returns `{"_filter": "elite_below_gate"}`)
- Added `"elite_below_gate": 0` and `"strategy_conf_gate": 0` to exclusion tracking dict

---

## Files Modified

| File | Change |
|------|--------|
| `alpha_engine/config.py` | Added `quan_engine_scalp` to BLACKLISTED_STRATEGIES; added `MIN_ELITE_SCORE_FOR_PICKS = 70`; added `STRATEGY_MIN_CONFIDENCE` dict |
| `alpha_engine/scanner.py` | Added `quan_engine_scalp` to GENERATOR_HARD_KILL; imported new config values; added elite_score gate + strategy confidence gate in signal pipeline |
| `alpha_engine/smart_picks_engine.py` | Added `quan_engine_scalp` to BANNED_SYSTEMS; imported config values; added elite_score gate + strategy confidence gate in `score_pick()`; added exclusion tracking keys |
| `alpha_engine/copy_trader_bridge.py` | Added `quan_engine_scalp` to BLACKLISTED_STRATEGIES |

---

## Expected Impact

- **~8 low-quality ml_crypto_predictor picks eliminated** per scan cycle (confidence <0.70)
- **~15-20 low elite_score picks filtered** per scan cycle (elite_score <70)
- **0 quan_engine_scalp signals** leak through (hard kill in 4 locations)
- Net result: fewer but higher-quality picks, projected WR improvement from ~42% to ~70%+ for admitted picks

---

## Verification

- Syntax-check all 4 modified Python files
- Monitor next scan cycle for `[ELITE_SCORE_GATE]` and `[STRATEGY_CONF_GATE]` log lines
- Track `elite_below_gate` and `strategy_conf_gate` in smart_picks exclusion stats
