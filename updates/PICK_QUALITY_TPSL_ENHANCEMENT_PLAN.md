# Pick Quality & TP/SL Enhancement Plan
## Response to XIAOMI MIMO Deep Quant Analysis (April 6, 2026)

---

## Executive Summary

XIAOMI MIMO's deep quant analysis of our live dashboard data (`dashboard_data.json`) revealed **6 critical system flaws** that require immediate remediation. This document outlines the enhancement plan to address each finding with concrete implementation steps.

---

## Critical Findings & Remediation Plan

### 1. SPORTS BET CONTAMINATION IN `goldmine_stocks`

**Finding:** A college basketball game (`Cal Poly Mustangs vs UC Irvine Anteaters`) appeared in the trading dashboard with score 41, elite 24, strategy `value_bet`.

**Root Cause:** The `goldmine_unified` feed is ingesting sports betting data alongside equities.

**Remediation:**
```python
# Add to alpha_engine/config.py
SPORTS_BLOCKLIST = frozenset({
    "Cal Poly Mustangs", "UC Irvine Anteaters", 
    # Add all detected sports tickers
})

# In smart_picks_engine.py, add filter:
if any(blocked in symbol for blocked in SPORTS_BLOCKLIST):
    return None  # Hard block sports data
```

**Status:** P0 - Implement immediately

---

### 2. SCORE/ELITE_SCORE DECOUPLING

**Finding:** 58 out of 110 active picks (53%) are winning despite having garbage scores (0-15). Examples:
- ETHUSDT: score=5, elite=81, PnL +0.96%
- BTCUSDT: score=0, elite=70, PnL +0.88%
- BNBUSDT: score=0, elite=76, PnL +0.63%

**Root Cause:** 
- `elite_score` measures strategy track record quality
- `score` measures composite ranking (includes regime, freshness, etc.)
- Goldmine stocks get score 15-30 because they have 0 closed trades (track record penalty)
- But market has been green and they're all up

**Remediation:**
```python
# In smart_picks_engine.py, decouple scoring:

# For new strategies (<20 trades), use Bayesian prior instead of 0
def _bayesian_prior_wr(trades: int, population_wr: float = 0.45) -> float:
    """Shrink toward population mean for low-n strategies."""
    prior_strength = 20  # Equivalent to 20 prior trades
    return (trades * observed_wr + prior_strength * population_wr) / (trades + prior_strength)

# Add dual-track scoring:
# Track A: quality_score = elite_score (for ranking by proven strategy)
# Track B: composite_score = current scoring formula (for fresh signals)
# Use composite_score for display, quality_score for sorting when trades < 20
```

**Status:** P0 - Implement in smart_picks_engine.py

---

### 3. SUSPICIOUS CONSENSUS COMBOS (Data Leakage Risk)

**Finding:** 
```
"chatgpt_combined_v1 (strong) + proven_tsmom_momentum + unknown"
  -> 280 trades, 9.3% WR, 691.9% total PnL
```

**Root Cause:** Either data leakage, lookahead bias, or survivorship bias (only winners tracked).

**Remediation:**
```python
# In strategy_registry.py, add consensus validation:
CONSENSUS_MAX_WR = 95.0  # Cap at 95% - above this is suspicious
CONSENSUS_MIN_TRADES = 50  # Minimum sample size for consensus claims

def validate_consensus(combo_name: str, trades: int, wr: float) -> bool:
    """Flag suspicious consensus combos."""
    if trades < CONSENSUS_MIN_TRADES:
        return True  # Insufficient data, don't trust
    if wr > CONSENSUS_MAX_WR:
        logger.warning(f"Suspicious consensus {combo_name}: {wr}% WR on {trades} trades")
        return False
    return True
```

**Status:** P1 - Add validation layer

---

### 4. DEAD SYSTEMS STILL ACTIVE

**Finding:** 7 systems with PF <= 0.17 still generating picks:

| System | Trades | WR | PnL | PF |
|--------|--------|-----|-----------|-----|
| ml_bg_ensemble | 8 | 0.0% | -32.98% | 0.00 |
| ml_bg_system_c | 5 | 0.0% | -4.04% | 0.00 |
| ml_bg_system_b | 19 | 5.3% | -54.70% | 0.02 |
| ml_bg_system_a | 19 | 10.5% | -49.84% | 0.14 |
| momentum_evolver | 8 | 0.0% | -12.0% | 0.00 |
| contrarian_evolver | 5 | 0.0% | -7.50% | 0.00 |
| mega_mutation | 7 | 14.3% | -15.78% | 0.03 |

**Remediation:**
```python
# Extend BANNED_SYSTEMS in smart_picks_engine.py:
BANNED_SYSTEMS_EXTENDED = BANNED_SYSTEMS | {
    "ml_bg_ensemble",      # 0% WR, -32.98% PnL
    "ml_bg_system_c",      # 0% WR, -4.04% PnL
    "ml_bg_system_b",      # 5.3% WR, -54.70% PnL
    "ml_bg_system_a",      # 10.5% WR, -49.84% PnL
    "momentum_evolver",    # 0% WR, -12.0% PnL
    "contrarian_evolver",  # 0% WR, -7.50% PnL
    "mega_mutation",       # 14.3% WR, -15.78% PnL
}

# Auto-kill threshold: PF < 0.2 with 10+ trades
AUTO_KILL_PF_THRESHOLD = 0.2
AUTO_KILL_MIN_TRADES = 10
```

**Status:** P0 - Add to banned systems immediately

---

### 5. REGIME DETECTION NON-FUNCTIONAL

**Finding:** 248 active picks, **0 have regime data**. Regime routing is fiction.

```json
"regime_validation": {
  "active_regime_composition": {
    "total": 248,
    "with_regime_data": 0,
    "aligned": 0,
    "misaligned": 0,
    "neutral": 0
  },
  "signal_reduction_pct": 0.0
}
```

**Remediation:**
```python
# In smart_picks_engine.py, enforce regime tagging:

def _ensure_regime_data(pick: dict, regime_data: dict) -> bool:
    """Ensure pick has regime data, else tag as unknown."""
    sym = pick.get("symbol", "")
    regime = regime_data.get("per_symbol", {}).get(sym, {}).get("kimi_regime")
    if regime:
        pick["regime"] = regime
        return True
    # Fallback to real-time BTC-based regime detection
    pick["regime"] = _detect_realtime_regime()
    return False

# Add regime validation gate:
def _regime_gate(pick: dict) -> bool:
    """Block picks with unknown regime unless proven strategy."""
    if pick.get("regime") in ("unknown", None, ""):
        strat = pick.get("strategy", "")
        if strat not in PROVEN_WINNERS:
            logger.warning(f"Blocked {pick.get('symbol')}: no regime data, unproven strategy")
            return False
    return True
```

**Status:** P0 - Fix regime data pipeline

---

### 6. PERFORMANCE ALERTS NOT ACTING ON DECAY

**Finding:** 10/10 HIGH severity alerts showing rolling 7d WR drops >20%:

| Strategy | Baseline WR | Rolling 7d WR | Drop |
|----------|---------------|------|-----|
| keltner_compression_expansion_sol | 60% | 9% | -51pp |
| crypto_drawdown_convexity_recovery | 53% | 21% | -32pp |
| crypto_mtf_ema_slope_alignment | 46% | 24% | -22pp |
| enhanced_ml_A_xgboost | 59% | 30% | -29pp |
| ml_crypto_predictor | 58% | 3% | -25pp |

**Remediation:**
```python
# In kill_switch.py, add auto-pause on decay alert:

DECAY_ALERT_THRESHOLD = -20  # pp drop triggering auto-reduction
DECAY_ACTION_MAP = {
    "HIGH": "score_floor_80",  # Only allow score >= 80
    "CRITICAL": "auto_pause",  # Stop generating new picks
    "EMERGENCY": "halt_all",   # Full system halt
}

def handle_decay_alert(strategy: str, baseline_wr: float, current_wr: float):
    drop_pp = baseline_wr - current_wr
    if drop_pp >= DECAY_ALERT_THRESHOLD:
        severity = "HIGH" if drop_pp >= 30 else "CRITICAL" if drop_pp >= 40 else "HIGH"
        action = DECAY_ACTION_MAP[severity]
        
        # Apply scoring penalty or pause
        if action == "score_floor_80":
            # Elevate minimum score threshold for this strategy
            strategy_score_floors[strategy] = 80
        elif action == "auto_pause":
            # Add to auto-pause list
            AUTO_PAUSED_STRATEGIES.add(strategy)
```

**Status:** P1 - Wire decay alerts to action

---

## TP/SL Enhancement Recommendations

### Current Problems Identified:

1. **SL Noise Gate:** 12% of losses had SL < 0.3% from entry (noise-triggered exits)
2. **No Adaptive SL:** Static SL doesn't adapt to volatility regime
3. **No TP Trailing:** Fixed TP doesn't capture extended moves

### Proposed Enhancements:

```python
# In position_manager.py or smart_picks_engine.py:

def calculate_adaptive_sl(
    entry_price: float, 
    direction: str, 
    atr: float,
    volatility_regime: str
) -> float:
    """Calculate volatility-adaptive stop loss."""
    
    # SL distance by regime
    regime_sl_mult = {
        "low_vol": 1.5,    # Tight stops in low volatility
        "normal": 2.0,     # Standard
        "high_vol": 3.0,   # Wide stops in high volatility
        "crisis": 4.0      # Very wide in crisis mode
    }
    
    mult = regime_sl_mult.get(volatility_regime, 2.0)
    sl_distance = atr * mult
    
    if direction == "LONG":
        return entry_price - sl_distance
    else:
        return entry_price + sl_distance


def calculate_trailing_tp(
    entry_price: float,
    current_price: float,
    direction: str,
    initial_tp: float,
    trail_distance_pct: float = 0.5
) -> float:
    """Calculate trailing take profit."""
    
    if direction == "LONG":
        profit_pct = (current_price - entry_price) / entry_price * 100
    else:
        profit_pct = (entry_price - current_price) / entry_price * 100
    
    # Only activate trailing after 1% profit
    if profit_pct > 1.0:
        trail_activation = profit_pct - trail_distance_pct
        if direction == "LONG":
            return entry_price * (1 + trail_activation / 100)
        else:
            return entry_price * (1 - trail_activation / 100)
    
    return initial_tp
```

---

## Score/PnL Mismatch Analysis

### High-Score Losses (score >= 70, PnL < -1%):
- All 4 are `TAOUSDT` from `rapid_fire` system
- This is a known bad signal source

### Low-Score Winners (score < 40, PnL > +10%):
- SPCE +13.94% (score 37) - short squeeze scout
- AMC +13.37% (score 27) - whale accumulation  
- CLOV +11.66% (score 3) - Value + Quality
- RENDERUSDT +10.92% (score 20!) - alpha_engine ml_enhanced

**These are contrarian/event-driven picks** that the scoring formula hates because they have low "Forward WR + Track Record" but are actually the most profitable.

**Remediation:** Add contrarian/event-driven scoring boost:
```python
# Add to scoring:
if pnl_pct > 5.0 and score < 40:
    # This is a potential contrarian winner - apply boost
    score += 10  # Recognize the outlier
    explanation_parts.append("Contrarian outlier boost (+10)")
```

---

## Implementation Priority Matrix

| Priority | Item | Owner | ETA |
|----------|------|-------|-----|
| P0 | Sports blocklist | smart_picks_engine.py | 24h |
| P0 | Dead systems ban | BANNED_SYSTEMS | 24h |
| P0 | Bayesian prior for new strategies | scoring logic | 48h |
| P0 | Regime data pipeline fix | hmm_regime + scoring | 48h |
| P1 | Consensus validation | strategy_registry | 72h |
| P1 | Decay alert auto-action | kill_switch.py | 72h |
| P2 | Adaptive TP/SL | position_manager | 1 week |
| P2 | Contrarian boost | scoring logic | 1 week |

---

## Validation Checklist

After implementation, verify:

- [ ] No sports data in crypto/equity picks
- [ ] Score 0-20 picks show elite_score in explanation
- [ ] All 248 active picks have regime data
- [ ] Dead systems (ml_bg_*) no longer in active picks
- [ ] Decay alerts trigger score floor or pause
- [ ] TP/SL respects minimum distance (0.3% crypto, 0.15% non-crypto)
- [ ] Low-score winners get contrarian recognition

---

## References

- Dashboard data source: `audit_trail/data/dashboard_data.json`
- Smart picks engine: `alpha_engine/smart_picks_engine.py`
- Position manager: `trading/position_manager.py`
- Kill switch: `alpha_engine/kill_switch.py`

**Analysis by:** XIAOMI MIMO  
**Document created:** 2026-04-07  
**Response required by:** Immediate (P0 items)