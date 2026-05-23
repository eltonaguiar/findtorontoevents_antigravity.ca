# Config Flags Reference — Non-Crypto Policy System

Complete reference for every configuration flag in the non-crypto and policy gating system.

---

## Non-Crypto HF Classification

| Flag | Type | Default | Module | Description |
|------|------|---------|--------|-------------|
| `enable_non_crypto_hf` | `bool` | `false` | `non_crypto_hf_classifier` | Master toggle for non-crypto HF tier classification. When `false`, all non-crypto signals bypass HF logic entirely. |
| `non_crypto_enabled` | `bool` | `false` | `non_crypto_admission` | Second-level gate for non-crypto tiers. Even if HF classification is on, signals are rejected unless this is `true`. |

### Examples

```jsonc
// config.json
{
  "enable_non_crypto_hf": true,
  "non_crypto_enabled": true
}
```

---

## Non-Crypto Tier Eligibility

| Flag | Type | Default | Module | Description |
|------|------|---------|--------|-------------|
| `non_crypto_tier_a_strategies` | `list[string]` | `[]` | `non_crypto_admission` | Strategy IDs eligible for non-crypto Tier A (highest confidence path). |
| `non_crypto_tier_b_strategies` | `list[string]` | `[]` | `non_crypto_admission` | Strategy IDs eligible for non-crypto Tier B (moderate confidence path). |
| `non_crypto_tier_a_confidence_threshold` | `float` | `0.75` | `non_crypto_admission` | Minimum composite confidence score to admit a signal as Tier A. Range: `0.0–1.0`. |
| `non_crypto_tier_b_confidence_threshold` | `float` | `0.60` | `non_crypto_admission` | Minimum composite confidence score to admit a signal as Tier B. Range: `0.0–1.0`. |

### Examples

```jsonc
{
  "non_crypto_tier_a_strategies": ["momentum_v3", "mean_revert_etf"],
  "non_crypto_tier_b_strategies": ["breakout_futures", "pairs_stat_arb"],
  "non_crypto_tier_a_confidence_threshold": 0.80,
  "non_crypto_tier_b_confidence_threshold": 0.65
}
```

---

## Forward Validation

| Flag | Type | Default | Module | Description |
|------|------|---------|--------|-------------|
| `non_crypto_min_forward_trades` | `int` | `20` | `non_crypto_admission` | Minimum number of closed forward-trades required before a non-crypto strategy is eligible for signal emission. Prevents cold-start noise. |
| `non_crypto_min_forward_wr_pct` | `float` | `55.0` | `non_crypto_admission` | Minimum forward win rate (percent) a strategy must demonstrate. Strategies below this are excluded regardless of backtest quality. |

### Examples

```jsonc
{
  "non_crypto_min_forward_trades": 30,
  "non_crypto_min_forward_wr_pct": 58.0
}
```

---

## Trust & Asset Class Filters

| Flag | Type | Default | Module | Description |
|------|------|---------|--------|-------------|
| `non_crypto_trust_tiers` | `list[string] | `["A", "B"]` | `non_crypto_admission` | Trust tier labels permitted to emit non-crypto signals. Lower tiers (e.g., `"C"`) are excluded by default. |
| `non_crypto_asset_classes` | `list[string]` | `["equities", "futures", "forex", "commodities"]` | `non_crypto_admission` | Asset classes that qualify for non-crypto signal emission. Unknown classes are silently rejected. |

### Examples

```jsonc
{
  "non_crypto_trust_tiers": ["A"],
  "non_crypto_asset_classes": ["equities", "futures"]
}
```

---

## Regime-Aware Direction Scoring

| Flag | Type | Default | Module | Description |
|------|------|---------|--------|-------------|
| `direction_penalty_regime_aware` | `bool` | `true` | `direction_scorer` | When `true`, direction penalties/bonuses are applied based on the current market regime (bull/bear/neutral). When `false`, a flat penalty is used. |
| `short_penalty_bull` | `int` | `15` | `direction_scorer` | Penalty (points) applied to short-direction signals when the market regime is **bullish**. Higher = stronger discouragement. |
| `short_penalty_bear` | `int` | `3` | `direction_scorer` | Penalty applied to short-direction signals when the regime is **bearish**. Lower because shorts are natural in bear markets. |
| `short_penalty_neutral` | `int` | `8` | `direction_scorer` | Penalty applied to short-direction signals in **neutral** regime. |
| `long_bonus_bull` | `int` | `10` | `direction_scorer` | Bonus (points) applied to long-direction signals in a **bullish** regime. Rewards alignment with regime. |
| `long_bonus_bear` | `int` | `-5` | `direction_scorer` | Bonus applied to long-direction signals in a **bearish** regime. Negative = penalty, discourages longs against trend. |
| `long_bonus_neutral` | `int` | `2` | `direction_scorer` | Bonus applied to long-direction signals in a **neutral** regime. |

### Examples

```jsonc
{
  "direction_penalty_regime_aware": true,
  "short_penalty_bull": 20,
  "short_penalty_bear": 2,
  "short_penalty_neutral": 8,
  "long_bonus_bull": 12,
  "long_bonus_bear": -5,
  "long_bonus_neutral": 3
}
```

---

## Goldmine Score Floor

| Flag | Type | Default | Module | Description |
|------|------|---------|--------|-------------|
| `goldmine_score_floor_enabled` | `bool` | `true` | `goldmine_gate` | Enables the goldmine gate, which blocks signals whose strategy's elite score is below the floor — unless enough closed trades exist to relax it. |
| `goldmine_score_floor` | `int` | `70` | `goldmine_gate` | Minimum elite score (0–100) a strategy must have for its signals to pass the goldmine gate. Backed by empirical score–PnL correlation (r=0.629). |
| `goldmine_min_confidence` | `float` | `0.65` | `goldmine_gate` | Minimum signal confidence for goldmine picks, applied in addition to tier thresholds. |
| `goldmine_min_closed_n` | `int` | `30` | `goldmine_gate` | Number of closed trades after which the score floor auto-expires for a strategy. If a strategy has ≥ this many closed trades, the floor is relaxed and only confidence/forward-validation gates apply. |

### Examples

```jsonc
{
  "goldmine_score_floor_enabled": true,
  "goldmine_score_floor": 75,
  "goldmine_min_confidence": 0.70,
  "goldmine_min_closed_n": 30
}
```

---

## Dynamic Non-Crypto Cap

| Flag | Type | Default | Module | Description |
|------|------|---------|--------|-------------|
| `dynamic_non_crypto_cap_enabled` | `bool` | `true` | `signal_router` | Enables a proportional cap on the number of non-crypto signals emitted, scaling with active pick count. |
| `non_crypto_cap_floor` | `int` | `3` | `signal_router` | Absolute minimum number of non-crypto signals allowed, regardless of active pick count. Prevents starvation. |
| `non_crypto_cap_ratio` | `float` | `0.05` | `signal_router` | Ratio of active non-crypto picks used to calculate the cap: `max(cap_floor, int(cap_ratio * active_count))`. |

### Examples

```jsonc
{
  "dynamic_non_crypto_cap_enabled": true,
  "non_crypto_cap_floor": 3,
  "non_crypto_cap_ratio": 0.05
}
```

---

## Statistical Kill Gating

| Flag | Type | Default | Module | Description |
|------|------|---------|--------|-------------|
| `statistical_kill_enabled` | `bool` | `true` | `kill_gate` | Enables statistical kill gating — automatically suppresses strategies that fail performance thresholds over a rolling window. |
| `kill_min_trades` | `int` | `15` | `kill_gate` | Minimum closed trades in the rolling window before a kill evaluation is triggered. Prevents premature kills on small samples. |
| `kill_max_pf` | `float` | `1.0` | `kill_gate` | Maximum profit factor threshold. Strategies with PF **below** this are flagged for kill. A PF < 1.0 means net-losing. |
| `kill_max_wr_pct` | `float` | `45.0` | `kill_gate` | Maximum win-rate (percent) threshold — **note:** this is an upper-bound filter for the kill condition. Strategies whose WR drops **below** this floor are flagged. Effectively acts as a minimum acceptable win rate. |
| `kill_rolling_window_days` | `int` | `90` | `kill_gate` | Number of days in the rolling evaluation window. Performance is assessed over this period. |

### Examples

```jsonc
{
  "statistical_kill_enabled": true,
  "kill_min_trades": 20,
  "kill_max_pf": 1.05,
  "kill_max_wr_pct": 48.0,
  "kill_rolling_window_days": 60
}
```

---

## Portfolio Risk Limits

| Flag | Type | Default | Module | Description |
|------|------|---------|--------|-------------|
| `max_symbol_exposure_pct` | `float` | `15.0` | `risk_manager` | Maximum portfolio exposure (percent) to any single symbol. Signals that would breach this are rejected or sized down. |
| `max_daily_var_pct` | `float` | `5.0` | `risk_manager` | Maximum acceptable daily Value-at-Risk (percent of portfolio). Signals exceeding this are rejected. |
| `concentration_hhi_warn` | `float` | `0.25` | `risk_manager` | Herfindahl-Hirschman Index (HHI) warning threshold. When portfolio concentration exceeds this value, an alert is raised. Range: `0` (perfectly diversified) to `1` (fully concentrated). |

### Examples

```jsonc
{
  "max_symbol_exposure_pct": 12.0,
  "max_daily_var_pct": 4.0,
  "concentration_hhi_warn": 0.20
}
```

---

## Quarantine System

| Flag | Type | Default | Module | Description |
|------|------|---------|--------|-------------|
| `quarantine_enabled` | `bool` | `true` | `quarantine_manager` | Enables the quarantine system. Strategies that underperform are quarantined (signals suppressed) rather than killed outright. |
| `quarantine_size_multiplier` | `float` | `0.5` | `quarantine_manager` | Position size multiplier applied to quarantined strategies. `0.5` = half-size. Allows partial observation during quarantine. |
| `quarantine_expiry_days` | `int` | `30` | `quarantine_manager` | Number of days a quarantine lasts before the strategy is re-evaluated for release or permanent kill. |

### Examples

```jsonc
{
  "quarantine_enabled": true,
  "quarantine_size_multiplier": 0.3,
  "quarantine_expiry_days": 21
}
```

---

## Composite Scoring Weights

| Flag | Type | Default | Module | Description |
|------|------|---------|--------|-------------|
| `asset_class_composite_weights` | `dict[string, dict]` | *(see below)* | `composite_scorer` | Per-asset-class weight maps controlling how individual sub-scores (confidence, freshness, regime-fit, etc.) are combined into a composite score. Each key is an asset class; each value is a `sub_score → weight` mapping. Weights should sum to `1.0` per asset class. |

### Default Weights

| Asset Class | confidence | freshness | regime_fit | direction_align | volatility_adj |
|-------------|-----------|-----------|------------|-----------------|----------------|
| equities | 0.35 | 0.15 | 0.20 | 0.20 | 0.10 |
| futures | 0.30 | 0.15 | 0.25 | 0.20 | 0.10 |
| forex | 0.30 | 0.20 | 0.20 | 0.15 | 0.15 |
| commodities | 0.35 | 0.15 | 0.20 | 0.15 | 0.15 |
| crypto | 0.40 | 0.15 | 0.15 | 0.20 | 0.10 |

### Examples

```jsonc
{
  "asset_class_composite_weights": {
    "equities": {
      "confidence": 0.40,
      "freshness": 0.10,
      "regime_fit": 0.20,
      "direction_align": 0.20,
      "volatility_adj": 0.10
    }
  }
}
```

---

## Policy Anchoring

| Flag | Type | Default | Module | Description |
|------|------|---------|--------|-------------|
| `last_policy_change_at` | `string` (ISO-8601) | `null` | `policy_evaluator` | Timestamp of the last policy configuration change. Anchors the A/B evaluation window: all performance comparisons (pre/post change) are split on this timestamp. Must be in ISO-8601 format (`YYYY-MM-DDTHH:MM:SSZ`). |

### Examples

```jsonc
{
  "last_policy_change_at": "2026-04-10T00:00:00Z"
}
```

---

## Quick-Start: Minimal Config for Non-Crypto

```jsonc
{
  "enable_non_crypto_hf": true,
  "non_crypto_enabled": true,
  "non_crypto_tier_a_strategies": ["momentum_v3"],
  "non_crypto_tier_a_confidence_threshold": 0.75,
  "non_crypto_min_forward_trades": 20,
  "non_crypto_min_forward_wr_pct": 55.0,
  "non_crypto_trust_tiers": ["A"],
  "non_crypto_asset_classes": ["equities"]
}
```
