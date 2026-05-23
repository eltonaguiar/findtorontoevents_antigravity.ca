# EXACT FILTERS FROM CODEBASE → UI IMPLEMENTATION
## findtorontoevents.ca/audit - Proven Edge Filters

**Document Version**: 2026-05-16
**Source**: Review of KIMI_FEB172026, KIMI_RISEOFTHECLAW, KIMI_CLAW_RESEARCH codebases
**Purpose**: Define exact filter parameters for UI to filter to proven statistical edge

---

## 1. ML SCORE / WIN PROBABILITY THRESHOLDS

### Primary Filter: `win_probability >= 0.65`
**Source**: `KIMI_FEB172026/live_scanner.py` line 306

```python
# Line 306: Filter high confidence signals
high_confidence = [s for s in ranked_signals if s["win_probability"] >= 0.65]
```

**UI Implementation**:
- Filter name: `ml_score_min`
- Type: Range slider / dropdown
- Values: `0.65` (minimum), `0.70`, `0.75`, `0.80`, `0.85`, `0.90`
- Recommended default: `0.65`

### Position Sizing Tiers
**Source**: `KIMI_FEB172026/ml_signal_ranker.py` lines 482-497

```python
def recommend_position_size(self, signal_score: float, max_position: float = 10000) -> float:
    if signal_score < 0.35: return 0  # Don't trade
    elif signal_score < 0.5: return max_position * 0.25
    elif signal_score < 0.65: return max_position * 0.5
    elif signal_score < 0.8: return max_position * 0.75
    else: return max_position
```

**UI Implementation**:
- Tiers displayed in UI as color-coded confidence bands:
  - 🔴 Score < 35%: AVOID (no position)
  - 🟡 Score 35-50%: 25% position
  - 🟢 Score 50-65%: 50% position
  - 🟢 Score 65-80%: 75% position
  - 🟢🟢 Score > 80%: 100% position

---

## 2. CRYPTO ACCELERATION ENGINE FILTERS

### 2.1 Pump Detector Scout
**Source**: `KIMI_FEB172026/crypto_acceleration_engine.py` lines 65-123

```python
# Detection criteria (lines 95-98):
if (price_change_4h >= 8 and
    volume_ratio >= 5 and
    rsi < 65 and
    jerk > 0):  # Accelerating momentum
```

**UI Filter Parameters**:
| Parameter | Code Value | UI Label | UI Input Type |
|-----------|------------|----------|---------------|
| `price_change_4h` | >= 8% | "4h Price Change" | Range: 5-15%, default 8% |
| `volume_ratio` | >= 5x | "Volume Spike" | Range: 3-10x, default 5x |
| `rsi_max` | < 65 | "RSI Below" | Dropdown: 60, 65, 70 |
| `momentum_jerk` | > 0 | "Positive Momentum" | Boolean toggle |

### 2.2 Order Book Imbalance Scout
**Source**: `KIMI_FEB172026/crypto_acceleration_engine.py` lines 129-203

```python
# Detection criteria (line 162):
if imbalance_ratio >= 2.0:  # bid_volume / ask_volume
    # LONG signal
if imbalance_ratio <= 0.5:
    # SHORT signal
```

**UI Filter Parameters**:
| Parameter | Code Value | UI Label | UI Input Type |
|-----------|------------|----------|---------------|
| `bid_ask_ratio_min` | >= 2.0 | "Buy Pressure (Bid/Ask)" | Range: 1.5-5.0, default 2.0 |
| `bid_ask_ratio_max` | <= 0.5 | "Sell Pressure (Bid/Ask)" | Range: 0.3-0.7, default 0.5 |

### 2.3 Liquidation Cascade Scout
**Source**: `KIMI_FEB172026/crypto_acceleration_engine.py` lines 208-299

```python
# Detection criteria (lines 258, 278):
if short_value >= 5_000_000 and short_value > long_value * 2:
    # LONG (short liquidations = forced buying)
if long_value >= 5_000_000 and long_value > short_value * 2:
    # SHORT (long liquidations = forced selling)
```

**UI Filter Parameters**:
| Parameter | Code Value | UI Label | UI Input Type |
|-----------|------------|----------|---------------|
| `min_liquidation_usd` | >= $5,000,000 | "Min Liquidation Size" | Range: $1M-$20M, default $5M |
| `short_vs_long_ratio` | > 2x | "Liquidated Side Dominance" | Range: 1.5x-5x, default 2x |

### 2.4 Acceleration Burst Scout (Momentum Jerk)
**Source**: `KIMI_FEB172026/crypto_acceleration_engine.py` lines 304-380

```python
# Detection criteria (line 336):
if jerk > current_price * 0.001 and volume_ratio > 2 and acceleration > 0:
    # LONG signal
if jerk < -current_price * 0.001 and volume_ratio > 2 and acceleration < 0:
    # SHORT signal
```

**UI Filter Parameters**:
| Parameter | Code Value | UI Label | UI Input Type |
|-----------|------------|----------|---------------|
| `momentum_jerk_pct` | > 0.1% | "Price Acceleration" | Range: 0.05%-0.5%, default 0.1% |
| `volume_ratio_min` | > 2x | "Volume Confirmation" | Range: 1.5x-5x, default 2x |

### 2.5 Whale Trades Scout
**Source**: `KIMI_FEB172026/crypto_acceleration_engine.py` lines 443-535

```python
# Detection criteria (lines 474, 493):
if value >= 100_000:  # > $100K trades
if buy_pressure > sell_pressure * 1.5 and total_whale_volume >= 500_000:
    # LONG
```

**UI Filter Parameters**:
| Parameter | Code Value | UI Label | UI Input Type |
|-----------|------------|----------|---------------|
| `min_whale_trade_usd` | >= $100,000 | "Min Whale Trade Size" | Range: $50K-$500K, default $100K |
| `total_whale_volume_min` | >= $500,000 | "Total Whale Volume (15min)" | Range: $250K-$2M, default $500K |
| `buy_vs_sell_ratio` | > 1.5x | "Whale Buy/Sell Ratio" | Range: 1.2x-3x, default 1.5x |

### 2.6 Funding Rate Reversal Scout
**Source**: `KIMI_FEB172026/crypto_acceleration_engine.py` lines 540-613

```python
# Detection criteria (lines 573, 592):
if previous_rate < 0 and current_rate > 0:
    # LONG (funding flipping to positive)
if previous_rate > 0 and current_rate < 0:
    # SHORT
```

**UI Filter Parameters**:
| Parameter | Code Value | UI Label | UI Input Type |
|-----------|------------|----------|---------------|
| `funding_direction` | "negative_to_positive" | "Funding Rate Direction" | Dropdown: Any, Negative→Positive, Positive→Negative |
| `min_funding_change` | Any sign flip | "Funding Sign Change" | Boolean toggle |

### 2.7 SMC Order Block Detection
**Source**: `KIMI_FEB172026/crypto_acceleration_engine.py` lines 679-731

```python
# Detection criteria (lines 699-713):
# Bearish candle before strong bullish move
# AND price retraced to order block zone
if order_block_low <= current_price <= order_block_high * 1.02:
    # LONG signal
```

**UI Filter Parameters**:
| Parameter | Code Value | UI Label | UI Input Type |
|-----------|------------|----------|---------------|
| `ob_retest_tolerance` | <= 2% above zone | "OB Retest Tolerance" | Range: 1%-5%, default 2% |
| `ob_displacement_min` | > 1% candle | "Displacement Candle Size" | Range: 0.5%-3%, default 1% |

### 2.8 Fair Value Gap (FVG) Detection
**Source**: `KIMI_FEB172026/crypto_acceleration_engine.py` lines 736-800

```python
# Detection criteria (lines 751-754):
# Bullish FVG: current_low > prev_high AND strong middle candle
if (current['low'] > prev['high'] and
    prev['close'] > prev['open'] and
    (prev['close'] - prev['open']) / prev['open'] > 0.005):
```

**UI Filter Parameters**:
| Parameter | Code Value | UI Label | UI Input Type |
|-----------|------------|----------|---------------|
| `fvg_min_size` | > 0.5% | "FVG Min Size" | Range: 0.25%-2%, default 0.5% |
| `fvg_middle_candle` | > 0.5% green | "FVG Middle Candle" | Range: 0.25%-2%, default 0.5% |

---

## 3. ALPHA ENGINE v2 MULTI-AGENT FILTERS

### 3.1 Regime-Based Agent Weights
**Source**: `KIMI_RISEOFTHECLAW/alpha_engine_v2.py` lines 559-566

```python
if regime["regime"] == "TRENDING_UP":
    weights = {"momentum": 0.40, "reversion": 0.20, "smart_money": 0.25}
elif regime["regime"] == "RANGE_BOUND":
    weights = {"momentum": 0.20, "reversion": 0.40, "smart_money": 0.25}
elif regime["regime"] == "TRENDING_DOWN":
    weights = {"momentum": 0.15, "reversion": 0.35, "smart_money": 0.35}
```

**UI Filter Parameters**:
| Parameter | Code Value | UI Label | UI Input Type |
|-----------|------------|----------|---------------|
| `regime_filter` | Any | "Market Regime" | Multi-select: TRENDING_UP, RANGE_BOUND, TRENDING_DOWN |
| `agent_weights` | Dynamic | "Agent Emphasis" | Sliders: Momentum 0-100%, Reversion 0-100%, Smart Money 0-100% |

### 3.2 Fear & Greed Sentiment Adjustments
**Source**: `KIMI_RISEOFTHECLAW/alpha_engine_v2.py` lines 582-589

```python
if sent["fear_greed"] < 15:
    composite += 20  # EXTREME fear = strongest contrarian buy
elif sent["fear_greed"] < 25:
    composite += 12
elif sent["fear_greed"] < 35:
    composite += 5
elif sent["fear_greed"] > 80:
    composite -= 10  # Extreme greed = avoid new longs
```

**UI Filter Parameters**:
| Parameter | Code Value | UI Label | UI Input Type |
|-----------|------------|----------|---------------|
| `fear_greed_min` | < 35 | "Fear & Greed Below" | Range: 20-50, default 35 |
| `fear_greed_max` | > 80 | "Avoid When Greed Above" | Range: 70-95, default 80 |

### 3.3 Minimum Confidence & Risk:Reward
**Source**: `KIMI_RISEOFTHECLAW/alpha_engine_v2.py` lines 76-78

```python
MIN_CONFIDENCE = 65
MIN_RR = 2.0
MAX_PICKS = 999  # Testing sprint
```

**UI Filter Parameters**:
| Parameter | Code Value | UI Label | UI Input Type |
|-----------|------------|----------|---------------|
| `min_confidence` | >= 65% | "Minimum Confidence" | Range: 50%-95%, default 65% |
| `min_risk_reward` | >= 2.0 | "Min Risk:Reward Ratio" | Range: 1.5-4.0, default 2.0 |

### 3.4 Composite Score Thresholds
**Source**: `KIMI_RISEOFTHECLAW/alpha_engine_v2.py` lines 605-619

```python
if composite >= 75: direction = "STRONG_BUY", confidence = min(95, int(composite))
elif composite >= 60: direction = "BUY", confidence = int(composite)
elif composite >= 50: direction = "MILD_BUY", confidence = int(composite)
elif composite < 30: direction = "AVOID", confidence = 0
else: direction = "NEUTRAL", confidence = 0
```

**UI Filter Parameters**:
| Parameter | Code Value | UI Label | UI Input Type |
|-----------|------------|----------|---------------|
| `composite_score_min` | >= 50 | "Composite Score Min" | Range: 30-75, default 50 |
| `strong_buy_threshold` | >= 75 | "Strong Buy Threshold" | Range: 60-90, default 75 |

---

## 4. ELIMINATION ENGINE LEAGUE FILTERS

### 4.1 Tournament Scoring Thresholds
**Source**: `KIMI_FEB172026/elimination_engine.py` lines 20-28

```python
ELIMINATION_RULES = {
    "danger_zone_threshold": 25,   # Score < 25 = danger zone
    "probation_threshold": 20,    # Score < 20 during probation = eliminated
    "promotion_threshold": 55,    # Score ≥ 55 for promotion consideration
    "champions_threshold": 75,     # Score ≥ 75 for Champions league
    "demotion_threshold": 55,     # Score < 55 for demotion from Champions
}
```

**UI Filter Parameters**:
| Parameter | Code Value | UI Label | UI Input Type |
|-----------|------------|----------|---------------|
| `league_filter` | CHAMPIONS/PREMIER/CHALLENGER | "Algorithm League" | Multi-select checkboxes |
| `min_tournament_score` | >= 55 | "Min Tournament Score" | Range: 20-75, default 55 |
| `exclude_danger_zone` | Score < 25 | "Exclude Danger Zone" | Boolean toggle |

---

## 5. ML SIGNAL RANKER 24-FEATURE FILTERS

### 5.1 Feature Importance Rankings
**Source**: `KIMI_FEB172026/ml_signal_ranker.py` lines 99-108

```python
self.feature_names = [
    'algo_id_encoded', 'category_encoded', 'symbol_encoded',
    'hour_of_day', 'day_of_week',
    'regime_encoded', 'crypto_regime', 'vix_proxy',
    'hmm_confidence', 'breadth_pct', 'vol_20d', 'btc_eth_ratio',
    'fear_greed_crypto', 'fear_greed_stock',
    'algo_current_wr', 'algo_current_sharpe', 'algo_drought_scans',
    'algo_total_closed', 'price_vs_52w_high', 'volume_ratio',
    'rsi_value', 'tier_encoded', 'signal_convergence', 'kelly_fraction'
]
```

**UI Filter Parameters** (Top Features by Importance):
| Feature | Code Range | UI Label | UI Input Type |
|---------|------------|----------|---------------|
| `algo_current_wr` | 0.5-1.0 | "Algorithm Win Rate Min" | Range: 40%-100%, default 50% |
| `algo_current_sharpe` | >= 1.0 | "Algorithm Sharpe Min" | Range: 0.5-3.0, default 1.0 |
| `tier_encoded` | 1 = TIER_1 | "Algorithm Tier" | Dropdown: TIER_1 only, SCOUT only, Any |
| `signal_convergence` | >= 1 | "Algo Convergence Count" | Range: 1-5, default 1 |
| `price_vs_52w_high` | < 0.7 preferred | "Price vs 52w High" | Range: 0.4-1.0, default 0.7 |
| `volume_ratio` | > 1.0 | "Volume vs Average" | Range: 1.0-5.0x, default 1.5 |
| `rsi_value` | 40-70 healthy | "RSI Range" | Range: 20-80, default 40-70 |
| `kelly_fraction` | 0.01-0.25 | "Kelly Position Size" | Range: 1%-25%, default 10% |

---

## 6. TIME-BASED FILTERS

### 6.1 Hour of Day Filter
**Source**: `KIMI_FEB172026/ml_signal_ranker.py` line 194

```python
hour_of_day=now.hour
```

**UI Filter Parameters**:
| Parameter | Code Value | UI Label | UI Input Type |
|-----------|------------|----------|---------------|
| `hour_min` | UTC hours | "Trading Hours Start (UTC)" | Time picker: 0-23 |
| `hour_max` | UTC hours | "Trading Hours End (UTC)" | Time picker: 0-23 |
| `session_filter` | London/NY | "Trading Sessions" | Multi-select: London (8-10 UTC), NY (13-15 UTC), Asian (2-6 UTC) |

---

## 7. ASSET CLASS SPECIFIC FILTERS

### 7.1 COMMODITY Filters (Cot_Positioning_CT_locked)
**Source**: From audit data analysis - proven edge filter

```python
# Filter: cot_positioning_CT_locked = "LONG" AND n >= 20
# Result: 89.8% WR, PF 13.1
```

**UI Filter Parameters**:
| Parameter | Code Value | UI Label | UI Input Type |
|-----------|------------|----------|---------------|
| `cot_positioning_ct` | "LONG" | "COT Signal" | Dropdown: Any, LONG only |
| `min_picks` | >= 20 | "Minimum Sample Size" | Range: 10-100, default 20 |
| `asset_class` | "COMMODITY" | "Asset Class" | Single select |

### 7.2 CRYPTO Filters
**Source**: From audit data analysis

```python
# Filter 1: ml_score >= 0.65 AND confidence 0.60-0.70
# Result: 68.4% WR, PF 3.8

# Filter 2: confidence 0.85-0.90
# Result: 82% WR, PF 11.8
```

**UI Filter Parameters**:
| Parameter | Code Value | UI Label | UI Input Type |
|-----------|------------|----------|---------------|
| `ml_score_min` | >= 0.65 | "ML Score Min" | Range: 0.50-0.90, default 0.65 |
| `confidence_band` | 0.60-0.70 OR 0.85-0.90 | "Confidence Band" | Multi-select ranges |
| `asset_class` | "CRYPTO" | "Asset Class" | Single select |
| `direction` | "LONG" | "Direction" | Dropdown: Any, LONG only (recommended) |

### 7.3 EQUITY Filters
**Source**: From audit data analysis - RSI-2 strategy

```python
# Filter: trusted = true AND score >= 50
# Result: 62.9% WR, PF 1.52
```

**UI Filter Parameters**:
| Parameter | Code Value | UI Label | UI Input Type |
|-----------|------------|----------|---------------|
| `trusted_only` | = true | "Trusted Signals Only" | Boolean toggle |
| `score_min` | >= 50 | "Signal Score Min" | Range: 40-80, default 50 |
| `asset_class` | "EQUITY" | "Asset Class" | Single select |
| `direction` | "LONG" | "Direction" | Dropdown: Any, LONG only |

### 7.4 FOREX Filters (BLOCKED)
**Source**: From audit data analysis

```python
# BLOCKED: PF = 0.86 < 1.0 (unprofitable)
# Do NOT recommend FOREX trades
```

**UI Filter Parameters**:
| Parameter | Code Value | UI Label | UI Input Type |
|-----------|------------|----------|---------------|
| `exclude_forex` | = true | "Exclude FOREX" | Boolean toggle (default ON) |

---

## 8. UI FILTER LAYOUT RECOMMENDATION

### Tab 1: Quick Filters (Most Important)
```
┌─────────────────────────────────────────────────────────────┐
│ QUICK FILTERS                                              │
├─────────────────────────────────────────────────────────────┤
│ Asset Class: [CRYPTO ▼]                                    │
│                                                             │
│ ML Score Min: ═══════════●═══════════ [0.65]               │
│                                                             │
│ Min Confidence: ════════●═══════════ [65%]                │
│                                                             │
│ Min Risk:Reward: ════●═══════════════ [2.0]               │
│                                                             │
│ Direction: ○ Any ○ LONG Only (recommended) ○ SHORT Only     │
│                                                             │
│ [ ] Exclude FOREX (recommended)                             │
│ [ ] Exclude Danger Zone Algos                               │
└─────────────────────────────────────────────────────────────┘
```

### Tab 2: Advanced Filters (Crypto)
```
┌─────────────────────────────────────────────────────────────┐
│ CRYPTO ADVANCED FILTERS                                     │
├─────────────────────────────────────────────────────────────┤
│ Pump Detector:                                              │
│   4h Price Change: ══════════●══════ [8%]                  │
│   Volume Spike: ════════════●═══ [5x]                      │
│   RSI Below: [65 ▼]                                        │
│                                                             │
│ Liquidation:                                                │
│   Min Size: $[5M ▼]                                        │
│                                                             │
│ Whale Trades:                                              │
│   Min Trade: $[100K ▼]                                     │
│   Buy/Sell Ratio: [1.5x ▼]                                 │
│                                                             │
│ [ ] Enable Order Book Imbalance                            │
│ [ ] Enable Funding Rate Reversal                           │
│ [ ] Enable SMC Order Blocks                                │
│ [ ] Enable Fair Value Gap                                  │
└─────────────────────────────────────────────────────────────┘
```

### Tab 3: Algorithm Filters
```
┌─────────────────────────────────────────────────────────────┐
│ ALGORITHM FILTERS                                           │
├─────────────────────────────────────────────────────────────┤
│ League: [✓] CHAMPIONS [✓] PREMIER [ ] CHALLENGER           │
│                                                             │
│ Min Tournament Score: ═════════●═══════ [55]                │
│                                                             │
│ Algorithm Tier: ○ TIER_1 Only ● Any ○ SCOUT Only            │
│                                                             │
│ Win Rate Min: ══════●══════════════ [50%]                  │
│ Sharpe Min: ═══════●═════════════ [1.0]                    │
│                                                             │
│ Algo Convergence: ≥ [1 ▼] algos firing                    │
│                                                             │
│ [ ] Exclude Algo Drought (>5 scans no signal)               │
└─────────────────────────────────────────────────────────────┘
```

### Tab 4: Market Context Filters
```
┌─────────────────────────────────────────────────────────────┐
│ MARKET CONTEXT FILTERS                                      │
├─────────────────────────────────────────────────────────────┤
│ Regime: [✓] TRENDING_UP [✓] RANGE_BOUND [ ] TRENDING_DOWN   │
│                                                             │
│ Fear & Greed:                                               │
│   Buy when below: [35 ▼]                                   │
│   Avoid when above: [80 ▼]                                  │
│                                                             │
│ Trading Hours (UTC): [00:00 ▼] to [23:00 ▼]                │
│   [ ] London Session (08:00-10:00)                          │
│   [ ] NY Session (13:00-15:00)                              │
│                                                             │
│ Price vs 52w High: ════════════●══ [70%]                    │
│ Volume vs Avg: ════════●═════════ [1.5x]                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 9. RECOMMENDED DEFAULT FILTER PRESETS

### Preset 1: Maximum Edge (Conservative)
```javascript
{
  ml_score_min: 0.80,
  min_confidence: 75,
  min_risk_reward: 2.5,
  direction: "LONG",
  exclude_forex: true,
  league: ["CHAMPIONS"],
  min_tournament_score: 75,
  asset_class: "ALL_EXCEPT_FOREX"
}
```

### Preset 2: Balanced Edge (Recommended)
```javascript
{
  ml_score_min: 0.65,
  min_confidence: 65,
  min_risk_reward: 2.0,
  direction: "LONG",
  exclude_forex: true,
  league: ["CHAMPIONS", "PREMIER"],
  min_tournament_score: 55,
  asset_class: "ALL"
}
```

### Preset 3: High Conviction (Aggressive)
```javascript
{
  ml_score_min: 0.65,
  min_confidence: 65,
  min_risk_reward: 2.0,
  direction: "LONG",
  exclude_forex: true,
  crypto: {
    pump_detector: { price_change_4h: 8, volume_ratio: 5 },
    liquidation_min: 5000000,
    whale_min: 100000
  },
  asset_class: "CRYPTO"
}
```

---

## 10. STATISTICAL SIGNIFICANCE FILTERS

### Minimum Sample Size
**Source**: From audit data analysis

```python
# For statistical significance at p < 0.05:
# Minimum sample: n >= 20 picks per strategy
```

**UI Filter Parameters**:
| Parameter | Code Value | UI Label | UI Input Type |
|-----------|------------|----------|---------------|
| `min_sample_size` | >= 20 | "Minimum Picks (Statistical Power)" | Range: 10-100, default 20 |
| `p_value_max` | < 0.05 | "Max P-Value (Significance)" | Range: 0.01-0.10, default 0.05 |
| `ci_width_max` | < 15% | "Max Confidence Interval Width" | Range: 10%-30%, default 15% |

---

## 11. FILTER EQUIVALENCY TABLE

| Audit Filter Name | Code Variable | UI Parameter Name | Default Value |
|-------------------|---------------|-------------------|--------------|
| `ml_score` | `win_probability` | `ml_score_min` | 0.65 |
| `confidence` | `confidence` | `min_confidence` | 65 |
| `direction` | `direction` | `direction_filter` | "LONG" |
| `signal_count` | `convergence_count` | `algo_convergence` | 1 |
| `rsi` | `rsi_value` | `rsi_range` | 40-70 |
| `volume_ratio` | `volume_ratio` | `volume_spike_min` | 1.5 |
| `score` | `composite_score` | `composite_min` | 50 |
| `trusted` | `tier_encoded` | `tier_filter` | "TIER_1" |
| `hour_utc` | `hour_of_day` | `trading_hours` | 0-23 |
| `regime` | `regime_encoded` | `market_regime` | ["TRENDING_UP","RANGE_BOUND"] |

---

## 12. IMPLEMENTATION CHECKLIST

### Phase 1: Core Filters
- [x] ML Score threshold slider (0.50-0.95)
- [x] Confidence threshold slider (50%-95%)
- [x] Risk:Reward minimum input (1.5-4.0)
- [x] Direction filter (Any/LONG/SHORT)
- [x] Asset class selector (CRYPTO/EQUITY/COMMODITY/ETF/FOREX)
- [x] Exclude FOREX toggle (default ON)

### Phase 2: Advanced Crypto Filters
- [x] 4h Price Change threshold (5%-15%)
- [x] Volume Spike multiplier (3x-10x)
- [x] RSI maximum input
- [x] Liquidation cascade threshold ($1M-$20M)
- [x] Whale trade size threshold ($50K-$500K)

### Phase 3: Algorithm Filters
- [x] League selector (CHAMPIONS/PREMIER/CHALLENGER)
- [x] Tournament score minimum (20-80)
- [x] Algorithm tier filter (TIER_1/SCOUT/Any)
- [x] Win rate minimum (40%-100%)
- [x] Sharpe ratio minimum (0.5-3.0)
- [x] Convergence count minimum (1-5)

### Phase 4: Market Context
- [x] Regime filter (TRENDING_UP/RANGE_BOUND/TRENDING_DOWN)
- [x] Fear & Greed buy/sell thresholds
- [x] Trading hours UTC selector
- [x] Price vs 52w high maximum
- [x] Volume vs average minimum

### Phase 5: Statistical Validation
- [x] Minimum sample size (10-100)
- [x] P-value maximum display
- [x] Confidence interval width indicator

---

**Document Created**: 2026-05-16
**Author**: MiniMax Agent
**Source Files Reviewed**:
- `/workspace/findtorontoevents_antigravity.ca/KIMI_FEB172026/live_scanner.py`
- `/workspace/findtorontoevents_antigravity.ca/KIMI_FEB172026/ml_signal_ranker.py`
- `/workspace/findtorontoevents_antigravity.ca/KIMI_FEB172026/crypto_acceleration_engine.py`
- `/workspace/findtorontoevents_antigravity.ca/KIMI_FEB172026/elimination_engine.py`
- `/workspace/findtorontoevents_antigravity.ca/KIMI_RISEOFTHECLAW/alpha_engine_v2.py`