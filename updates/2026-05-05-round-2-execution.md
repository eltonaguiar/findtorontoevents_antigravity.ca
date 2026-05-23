# Round 2 Execution Results — Audit Performance

**Date:** 2026-05-05  
**Areas investigated:** 8, 9, 10 (top 3 from Round 2 research map)  
**Parent map:** [[CHATWITHCLAUDE.MD]]

---

## Area 8: Closed Picks Data Integrity — CONFIRMED CRITICAL

**Finding:** All score fields are 0% populated across 7,645 records.

| Field | Populated | Null |
|-------|-----------|------|
| score | 0/7,645 (0.0%) | ALL NULL |
| trust_score | 0/7,645 (0.0%) | ALL NULL |
| smart_score | 0/7,645 (0.0%) | ALL NULL |
| grade | 0/7,645 (0.0%) | ALL NULL |
| strat_fwd_wr | 3/7,645 (0.0%) | 99.9% null |
| trust_tier | 3/7,645 (0.0%) | 99.9% null |

**Impact:** Dashboard tooltips claiming "Score ≥ 70 = 82% WR" are completely unverifiable. Any backtest using score bands on closed data is meaningless.

**Actual record structure:** `{id, strategy, symbol, category, signal_type, direction, entry_price, entry_date, timestamp, take_profit, stop_loss, confidence, ml_score, risk_reward, reason, status, source_system, forward_test_only, exit_price, exit_date}`

**Missing fields that should exist:** `score`, `trust_score`, `smart_score`, `grade`, `strat_fwd_wr`, `trust_tier`

**Additional findings:**
- KIMI closed_picks has SL mislabeling: exit_reason says "SL hit" but live price never breached stop. PF=0.045 (essentially zero).
- FreeBuff queries `closed_picks.json` instead of `dashboard_data.json` — profitable strategies get shut down.

**Root cause:** The fields are computed at signal time for `active_picks.json` but NOT written back to `closed_picks.json` when the pick closes. The close-path only writes: exit_price, exit_date, status, pnl.

**Fix needed:** In the pick-closing logic (likely `forward_validator.py` or `dashboard_generator.py`), write `score`, `trust_score`, `smart_score`, `grade`, `strat_fwd_wr`, `trust_tier` to the closed pick record at close time.

---

## Area 9: Real High-Conviction Gate — CONFIRMED

**Finding:** The Mercury combo (`score>=50 & trust>=3`) = 54.4% WR (coin flip). The real high-conviction gate is `strat_fwd_wr>=70`.

From `conviction_stack.py` (the institutional filter):
```python
# Default config values:
"min_forward_wr_pct": 50.0,       # Default institutional gate
"min_forward_wr_pct_strict": 55.0,
"blocked_trust_tiers": ["BANNED", "UNTRUSTED"],
"conviction_min_trade_pts": 40,
```

From `edge-deepscan-2-filter-combos` analysis (brute-force filter scan of 3,500+ closed picks):

| Gate | n | WR | PF | Verdict |
|------|---|---|-----|---------|
| `score>=50 & trust>=3` (Mercury) | ~500 | 54.4% | 2.35 | Overhyped |
| `strat_fwd_wr>=70 & trust_score>=3` | 128 | 77.3% | 14.0 | Real high-conviction |
| `strat_fwd_wr>=70 & PROVEN/RELIABLE & no_conflict` | 22 | 95.5% | 26+ | Super-golden (small sample) |
| `consensus_in_strat & fwd_wr_60+` | 111 | 88.3% | 12.96 | Very strong |
| `strat_fwd_wr>=70 & direction=LONG` (all assets) | — | — | — | LONG bias in bounce regime |

**But:** `strat_fwd_wr` has 5-10pp lookahead bias (point-in-time at close, not emission). Real forward WR is likely 5-10pp lower than backtested.

**Recommended gate (from the analysis):**
```yaml
# Tier-1: Full size
strat_fwd_wr >= 70 AND trust_tier in [PROVEN, RELIABLE] AND has_conflict == false
# Expected: ~90% WR (backtested 95.5%, minus 5pp lookahead)

# Tier-2: Half size  
strat_fwd_wr >= 70 AND trust_score >= 3
# Expected: ~70% WR (backtested 77.3%, minus 5-7pp lookahead)

# Hard exclusions:
- smart_picks_tag == true  # Currently negative edge (54% WR, PF 0.56)
- source_system == claude_gainer_st AND strat_fwd_wr < 70
- asset_class == COMMODITY AND score >= 50  # n=2, no edge
```

**Additional issue:** Smart Picks tag is broken (54% WR, PF 0.56). It's being used as a positive filter but has negative edge.

---

## Area 10: LightGBM Schema Drift — PARTIALLY FIXED, NOW STALE COMMENT

**Finding:** The active model WAS retrained with 16 features. The old comment in engine.py is now outdated.

**Model comparison:**

| Model | Size | Features |
|-------|------|----------|
| ACTIVE (lgb_top_gainer.txt) | 28KB | 14 base + pair_id = 15 features: `ret_1h, ret_4h, ret_24h, rsi_14, macd, atr, bb_width, vol_ratio, above_200, rsi_slope, close_ema9, atr_ratio, candle_body, high_low_pos, ret_vol_corr, pair_id` |
| BACKUP (lgb_top_gainer.txt.backup) | 51KB | 12 base + pair_id = 13 features: same minus the 6 new ones, plus `fng, btc_dom, funding_z` |

**Schema alignment fix (commit 4dd878da0b):** Engine uses `model.feature_name()` introspection at predict time to align features. This was written when the model had 13 features and config had 16. Now the model has ~15 and config has 16.

**Current gap:** The config has 14 FEATURES but the model was trained on a slightly different set. The `feature_name()` introspection handles the mismatch at runtime, but the model is predicting on features it knows (not the 3 that grew from config). The model needs a **proper retrain** with the current full feature set to regain prediction quality.

**The fix comment in engine.py says:** "TOP_GAINER_FEATURES grew to 16 (15 base + pair_id) but the saved model has 13." This is now WRONG. The model was retrained but the upsdated config grew further. Need to re-verify alignment.

---

## Consolidated Action Items (Executable This Week)

| Priority | Action | Area | File |
|----------|--------|------|------|
| P0 | Write score fields to closed_picks at close time | 8 | `forward_validator.py` or close-path in `dashboard_generator.py` |
| P0 | Deprecate Smart Picks as positive filter (54% WR) | 9 | `smart_picks_engine.py` |
| P0 | Update High Conviction button to use `strat_fwd_wr>=70 & trust_tier` | 9 | Dashboard JS/config |
| P1 | Retrain LightGBM with current full feature set | 10 | `crypto_signal_engine/trainer.py` |
| P1 | Update engine.py comment to reflect current state | 10 | `crypto_signal_engine/engine.py` |
| P1 | Fix KIMI SL mislabeling (exit_reason vs actual price) | 8 | `forward_validator.py` |
| P1 | Fix FreeBuff data path (dashboard_data vs closed_picks) | 8 | FreeBuff codebase |
| P2 | Add `at_issue_fwd_wr` point-in-time field | 11 | closed_picks schema |
| P2 | Fix alpha-engine-data-loss-bug (111 strategies dropped/scan) | 12 | scan dump logic |

---
*OWL — 2026-05-05 — Round 2 execution results*
