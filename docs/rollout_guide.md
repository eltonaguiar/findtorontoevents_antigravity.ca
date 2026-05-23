# Rollout Guide — Non-Crypto Policy System

Step-by-step deployment guide for enabling the non-crypto policy system in production. The rollout is split into three phases to isolate risk and enable incremental verification.

---

## Prerequisites

- Access to the signal engine config (`config.json` or equivalent)
- Ability to restart the signal engine and verify health
- Monitoring dashboards for signal throughput, rejection rates, and PnL
- Rollback procedure tested in staging

---

## Phase 1: Configuration Only (No Behavioral Change)

**Goal:** Deploy config flags without activating any new logic. Verifies that the config loads correctly and defaults are sane.

### Steps

1. **Add all new config flags with safe defaults:**

   ```jsonc
   {
     "enable_non_crypto_hf": false,
     "non_crypto_enabled": false,
     "non_crypto_tier_a_strategies": [],
     "non_crypto_tier_b_strategies": [],
     "non_crypto_tier_a_confidence_threshold": 0.75,
     "non_crypto_tier_b_confidence_threshold": 0.60,
     "non_crypto_min_forward_trades": 20,
     "non_crypto_min_forward_wr_pct": 55.0,
     "non_crypto_trust_tiers": ["A", "B"],
     "non_crypto_asset_classes": ["equities", "futures", "forex", "commodities"],
     "direction_penalty_regime_aware": true,
     "short_penalty_bull": 15,
     "short_penalty_bear": 3,
     "short_penalty_neutral": 8,
     "long_bonus_bull": 10,
     "long_bonus_bear": -5,
     "long_bonus_neutral": 2,
     "goldmine_score_floor_enabled": true,
     "goldmine_score_floor": 70,
     "goldmine_min_confidence": 0.65,
     "goldmine_min_closed_n": 30,
     "dynamic_non_crypto_cap_enabled": true,
     "non_crypto_cap_floor": 3,
     "non_crypto_cap_ratio": 0.05,
     "statistical_kill_enabled": true,
     "kill_min_trades": 15,
     "kill_max_pf": 1.0,
     "kill_max_wr_pct": 45.0,
     "kill_rolling_window_days": 90,
     "max_symbol_exposure_pct": 15.0,
     "max_daily_var_pct": 5.0,
     "concentration_hhi_warn": 0.25,
     "quarantine_enabled": true,
     "quarantine_size_multiplier": 0.5,
     "quarantine_expiry_days": 30,
     "asset_class_composite_weights": { /* defaults */ },
     "last_policy_change_at": null
   }
   ```

2. **Deploy and restart the signal engine.**

3. **Verify:**
   - [ ] Engine starts without config errors
   - [ ] All new flags appear in `/config/inspect` or equivalent endpoint
   - [ ] Defaults match expected values
   - [ ] No new signals are emitted (both master switches are `false`)
   - [ ] Existing signal pipeline is unchanged

4. **Set `last_policy_change_at`** to the current ISO-8601 timestamp:
   ```jsonc
   { "last_policy_change_at": "2026-04-10T00:00:00Z" }
   ```

### Rollback

Remove the new config keys. Engine falls back to legacy behavior.

---

## Phase 2: Enable Admission (Non-Crypto Signals Start Flowing)

**Goal:** Activate non-crypto signal admission with conservative settings.

### Steps

1. **Enable non-crypto HF classification:**
   ```jsonc
   { "enable_non_crypto_hf": true }
   ```

2. **Enable non-crypto admission with tight filters:**
   ```jsonc
   {
     "non_crypto_enabled": true,
     "non_crypto_tier_a_strategies": ["<strategy_id_1>", "<strategy_id_2>"],
     "non_crypto_tier_a_confidence_threshold": 0.80,
     "non_crypto_min_forward_trades": 30,
     "non_crypto_min_forward_wr_pct": 60.0,
     "non_crypto_trust_tiers": ["A"],
     "non_crypto_asset_classes": ["equities"]
   }
   ```
   Start with **1–2 proven strategies**, **one asset class**, **Tier A only**, and **high thresholds**.

3. **Deploy and restart.**

4. **Verify (monitor for 48–72 hours):**
   - [ ] Non-crypto signals appear in the signal log
   - [ ] Signal count is low and manageable (check cap is working: `max(3, int(0.05 × N))`)
   - [ ] Goldmine gate is filtering low-score strategies (check rejection logs)
   - [ ] Forward validation is blocking under-qualified strategies
   - [ ] No crashes or config errors

5. **Gradually widen filters:**
   - Add Tier B strategies: `"non_crypto_tier_b_strategies": ["<strategy_id_3>"]`
   - Lower confidence thresholds by 0.05 increments
   - Add asset classes one at a time
   - Update `last_policy_change_at` after each change

6. **Enable regime-aware direction scoring** (if not already active):
   ```jsonc
   { "direction_penalty_regime_aware": true }
   ```
   Monitor that direction penalties/bonuses are being applied correctly per regime.

### Rollback

```jsonc
{ "non_crypto_enabled": false, "enable_non_crypto_hf": false }
```
Existing non-crypto signals in the portfolio continue to their natural close. No new signals are admitted.

---

## Phase 3: Enable Scoring & Risk Controls

**Goal:** Activate statistical kill gating, quarantine, portfolio risk limits, and dynamic cap tuning.

### Steps

1. **Enable statistical kill gating:**
   ```jsonc
   {
     "statistical_kill_enabled": true,
     "kill_min_trades": 15,
     "kill_max_pf": 1.0,
     "kill_max_wr_pct": 45.0,
     "kill_rolling_window_days": 90
   }
   ```
   Monitor for false positives — strategies with insufficient data being killed prematurely.

2. **Enable quarantine system:**
   ```jsonc
   {
     "quarantine_enabled": true,
     "quarantine_size_multiplier": 0.5,
     "quarantine_expiry_days": 30
   }
   ```
   Verify quarantined strategies receive reduced position sizing.

3. **Set portfolio risk limits:**
   ```jsonc
   {
     "max_symbol_exposure_pct": 15.0,
     "max_daily_var_pct": 5.0,
     "concentration_hhi_warn": 0.25
   }
   ```
   Monitor for rejected signals due to risk breaches.

4. **Tune dynamic cap** based on observed signal volumes:
   - If too many signals are being queued: lower `non_crypto_cap_ratio`
   - If portfolio feels under-allocated: raise `non_crypto_cap_floor`

5. **Configure composite scoring weights** per asset class if defaults don't match observed performance.

### Rollback

Set individual feature flags to `false`. Each feature is independently toggleable.

---

## Verification Checklist

After each phase, run through this checklist:

### Signal Pipeline
- [ ] Signal throughput matches expectations (check `/metrics/signals`)
- [ ] Rejection reasons are logged and explainable
- [ ] No signals are silently dropped

### Gating Logic
- [ ] Goldmine gate: low-score strategies are blocked
- [ ] Forward validation: strategies with < N trades are blocked
- [ ] Direction scoring: penalties/bonuses match regime
- [ ] Kill gate: underperforming strategies are suppressed
- [ ] Quarantine: flagged strategies get reduced sizing

### Portfolio Risk
- [ ] No single symbol exceeds `max_symbol_exposure_pct`
- [ ] Daily VaR is within `max_daily_var_pct`
- [ ] HHI alerts fire when concentration is high

### Configuration
- [ ] `last_policy_change_at` is set and accurate
- [ ] All flags load without errors
- [ ] No orphaned or unrecognized config keys

### Monitoring
- [ ] Dashboards show non-crypto signal flow
- [ ] Alert thresholds are set for kill/quarantine events
- [ ] PnL attribution is separated by crypto vs. non-crypto

---

## Timeline

| Phase | Duration | Risk Level | Can Rollback? |
|-------|----------|------------|---------------|
| Phase 1: Config | 1 day | Low | Yes — remove keys |
| Phase 2: Admission | 3–7 days | Medium | Yes — disable switches |
| Phase 3: Scoring | Ongoing | Low–Medium | Yes — per-feature toggle |

**Total time to full rollout: ~2 weeks**, assuming Phase 2 monitoring shows clean signal flow.

---

## Emergency Procedures

### Kill Switch

To immediately disable all non-crypto activity:

```jsonc
{
  "enable_non_crypto_hf": false,
  "non_crypto_enabled": false
}
```

Restart the engine. No new non-crypto signals will be emitted. Existing open positions are unaffected.

### Partial Rollback

Each subsystem can be disabled independently:

| Want to disable… | Set to `false` |
|-------------------|----------------|
| All non-crypto signals | `non_crypto_enabled` |
| Goldmine gating | `goldmine_score_floor_enabled` |
| Kill gating | `statistical_kill_enabled` |
| Quarantine | `quarantine_enabled` |
| Dynamic cap | `dynamic_non_crypto_cap_enabled` |
| Direction scoring | `direction_penalty_regime_aware` |
