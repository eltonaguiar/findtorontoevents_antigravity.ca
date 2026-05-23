# Crypto Prediction System: Critical Diagnosis & World-Class Fixes

**Date:** March 24, 2026  
**System:** Antigravity Trading Platform  
**Status:** CRITICAL - Requires Immediate Intervention

---

## Executive Summary

Your system has **strong architectural foundations** but suffers from **signal dilution** (~572 active picks → 11 Smart Picks = 98% rejection rate) and **scoring that doesn't predict outcomes** (r=0.05 correlation). The ML layer is effectively disabled, and your performance metrics are inflated by a single outlier (FETUSDT = 153.6% of total PnL).

**Bottom Line:** Remove FETUSDT → System PnL goes from +2,951% to **-1,582%**.

---

## 🔴 CRITICAL ISSUES (Fix This Week)

### 1. Score-PnL Correlation r=0.05 — The Core Scoring Problem

**The Problem:**
- Your 21-component elite scorer + 5D Smart Picks engine has **near-zero predictive power**
- A pick scored 95 is statistically indistinguishable from a pick scored 30
- The 40pt regime match in Smart Picks is the ONLY survival mechanism — the quality scoring below that is decorative

**Root Cause:**
- Smart picks engine dimension 1 (regime match) dominates at 40pt weight
- When regime is correct, picks look good. When wrong, they fail
- The "quality" scoring (components 1-21) collectively produces r=0.05 value added

**Immediate Fix:**
```python
# In smart_picks_engine.py - REDUCE quality weight temporarily
smart_score = (
    regime_match * 0.50 +      # INCREASE from 0.40 (regime is only thing working)
    elite_quality * 0.10 +     # DECREASE from 0.20 (ML broken, quality is noise)
    freshness * 0.15 +         
    tp_upside * 0.15 +         
    currently_winning * 0.10   
) * 100
```

---

### 2. FETUSDT Single-Stock Risk — Performance Mirage

**The Problem:**
- System reports +2,951% total PnL
- **153.6% of that comes from FETUSDT alone**
- Remove FETUSDT: **-1,582% PnL**

**Impact:**
- Strategy WR stats used in elite_scorer are inflated by FETUSDT trades
- Profit factor 1.19 should actually be < 1.0 ex-FETUSDT
- Calmar ratio 11.34 and Sortino 18.85 are meaningless

**Immediate Fix:**
```python
# In elite_scorer.py - Add symbol outlier filtering
SYMBOL_EXCLUDE_LIST = ['FETUSDT', 'RENDERUSDT']  # Add symbols with >20% of total PnL

def compute_forward_wr(strategy):
    trades = get_closed_trades(strategy)
    # Exclude outlier symbols from WR calculation
    filtered_trades = [t for t in trades if t.symbol not in SYMBOL_EXCLUDE_LIST]
    return win_rate(filtered_trades)
```

---

### 3. ML Champion Model BROKEN — Feature Population Crisis

**The Problem:**
- AUC = 1.0 persists (overfitting artifact)
- Champion model is INCOMPATIBLE (feature mismatch)
- **Only 1 of 46 features is "truly alive"** (>20% non-zero)
- 25+ features are "dead" (80%+ at default value)

**Feature Health Breakdown:**
| Feature Group | Count | Population | Status |
|--------------|-------|------------|--------|
| Core (strategy, confidence, RR) | 5 | 100% | ✅ Working |
| Time-of-day | 6 | 100% | ✅ Working |
| Trade structure | 3 | 100% | ✅ Working |
| RSI/ATR/volume at entry | 4 | 5-17% | 🔴 Nearly dead |
| Funding/microstructure | 9 | <5% | 🔴 Dead |
| Cross-sectional | 4 | <5% | 🔴 Dead |
| Chi-squared technical | 7 | <5% | 🔴 Dead |

**Immediate Fix (P0):**
```python
# Wire technical_features.py into scanner signal generation
# In scanner.py or production_scanner.py:

from technical_features import compute_all_features
from cross_sectional import compute_cross_sectional_features

def generate_signal(symbol, strategy):
    # ... existing signal generation ...
    
    # ADD: Populate technical features at signal creation
    ohlcv = fetch_ohlcv(symbol, timeframe='30m', bars=50)
    tech_features = compute_all_features(ohlcv)
    
    # ADD: Populate cross-sectional features
    cs_features = compute_cross_sectional_features(symbol, universe=get_top_50_symbols())
    
    signal.update(tech_features)
    signal.update(cs_features)
    
    return signal
```

---

### 4. Consensus = Negative Signal, But Gets +45 Boost

**The Problem:**
- Confluence Penalty (elite_scorer): 3+ systems agreeing = -3 pts (34% WR — anti-predictive)
- Multi-agree consensus WR: 18.1% vs 35% solo
- Yet `score_booster.py` applies `copy_trader_consensus: +45` for ≥4 trader agreement

**Direct Contradiction:** System simultaneously penalizes consensus (-3) and rewards it (+45)

**Immediate Fix:**
```python
# In score_booster.py - Audit and fix consensus boost
CONSENSUS_BOOSTS = {
    'copy_trader_consensus': {
        'old': 45,  # Based on "72% known WR" (outdated)
        'new': 5,   # Live WR is 18.1% — barely worth boosting
        'condition': lambda wr: 10 if wr > 60 else (5 if wr > 50 else 0)
    },
    'copy_trader_clones': {
        'old': 40,
        'new': 8,   # Scale by actual live WR
    }
}

def apply_family_boost(pick, system_wr):
    """Scale boost by actual system WR, not historical claims"""
    base_boost = CONSENSUS_BOOSTS.get(pick.source_system, {}).get('new', 0)
    # Scale: if system WR is 18%, boost is 18/72 * base = 0.25x
    scaling_factor = system_wr / 0.72  # 72% was the claimed WR
    return base_boost * max(scaling_factor, 0.1)
```

---

### 5. R:R Filter Bypassed — Sub-1.0 Picks Slipping Through

**The Problem:**
- R:R 2.0-2.5 = 73.7% WR (the proven sweet spot)
- Yet SP-v015 contains:
  - BTCUSDT SHORT (copy_hl): R:R = 0.8x
  - ETHUSDT SHORT (clone): R:R = 0.4x — **should be HARD BLOCKED**

**The 1.5-3.0 winner filter is NOT catching R:R < 1.0 picks**

**Immediate Fix:**
```python
# In forward_validator.py - Enforce R:R >= 1.0 for ALL sources
RR_GATE_MIN = 1.0  # Was 1.5, but at minimum enforce 1.0

def apply_rr_gate(pick):
    """Hard block ANY pick with R:R < 1.0 regardless of source"""
    rr = pick.get('risk_reward', 0)
    
    # NO EXCEPTIONS for copy_trader picks
    if rr < RR_GATE_MIN:
        print(f"[RR_GATE] BLOCK {pick['symbol']} — R:R {rr:.2f} < {RR_GATE_MIN}")
        return False  # HARD BLOCK
    
    # Optimal zone bonus
    if 2.0 <= rr <= 2.5:
        pick['elite_score'] += 5  # Sweet spot bonus
    
    return True
```

---

### 6. SP-v001 is the ONLY Resolved Batch — "64% Median WR" is Premature

**The Problem:**
- SMARTPICKS.MD claims 64% median WR across 14 active batches
- Only **SP-v001** is fully resolved: **0% WR, -8.10% avg PnL**
- All other "WR" figures are based on **snapshot PnL** at 20-min intervals — NOT final outcomes

**Example:** GRIFFAINUSDT was +1.32% at 6.7h snapshot → hit SL at -8.10% by hour 22.9

**Immediate Fix:**
```python
# In smart_picks_tracker.py - Label correctly
def compute_batch_stats(batch):
    if batch.resolved:
        return {
            'wr': batch.final_wr,
            'avg_pnl': batch.final_avg_pnl,
            'label': 'RESOLVED'  # Real WR
        }
    else:
        return {
            'wr': batch.snapshot_wr,  # Current unrealized
            'avg_pnl': batch.snapshot_pnl,
            'label': 'UNREALIZED_SNAPSHOT'  # NOT "WR" — may reverse!
        }

# In dashboard — display clearly
# ❌ "64% Median WR" 
# ✅ "64% Unrealized Snapshot (0% Resolved WR)"
```

---

## 🟡 HIGH PRIORITY FIXES (This Week)

### 7. Kill the "Death Zone" Blind Spot

**Current:** UTC 13:00-16:00 soft penalty (-10). Claims 11-21% WR during these hours.

**Problem:** UTC 13-16 is London afternoon + NY morning — the **highest volume, most liquid window**. Your low WR is likely small-sample overfitting, not a structural edge.

**Fix:**
```python
# Replace time-based penalty with volume-based
VOLUME_PENALTY_THRESHOLD = 0.30  # 30th percentile of 30-day average

def volume_penalty(symbol):
    vol_4h = get_volume(symbol, '4h')
    vol_30d_avg = get_volume_ma(symbol, '4h', 30)
    vol_percentile = vol_4h / vol_30d_avg
    
    if vol_percentile < VOLUME_PENALTY_THRESHOLD:
        return -10  # Thin books = stop hunts
    elif vol_percentile > 2.0:
        return +5   # High volume = good liquidity
    return 0
```

---

### 8. Delete These Components (Dead Weight)

Per Kimi audit and live data, these components add no value:

| Component | Why Delete | Replacement |
|-----------|-----------|-------------|
| Session Bonus | No edge in time-of-day | Volume percentile |
| Monte Carlo | Disabled, dead code | Delete entirely |
| Meta Label | Same as broken ML | Delete |
| Hindsight Winner | Survivorship bias | Real-time pattern detection |
| Skyrocket Potential | Unvalidated | On-chain velocity |
| Death Zone (time) | Wrong hours | Volume threshold |
| Confluence Penalty | Herding works in crypto | Correlation filter |

---

### 9. Position Sizing is Missing (Fatal)

**Current:** 10-11 "Smart Picks" with implicit equal weight

**Problem:** Volatility ignorance. In a 64% WR system with 2:1 R:R, optimal Kelly is ~28% per pick.

**Fix:**
```python
def kelly_size(elite_score, strategy_wr, recent_volatility, correlation_to_portfolio):
    """Fractional Kelly with vol scaling and correlation penalty"""
    
    # Base Kelly
    avg_win = get_strategy_avg_win(strategy)
    avg_loss = get_strategy_avg_loss(strategy)
    edge = (strategy_wr * avg_win) - ((1 - strategy_wr) * avg_loss)
    kelly_pct = edge / avg_win if avg_win > 0 else 0
    
    # Fractional (conservative)
    half_kelly = kelly_pct * 0.5
    
    # Volatility scaling
    vol_scalar = TARGET_VOL / recent_volatility  # Reduce size in high vol
    
    # Correlation penalty (diversification)
    corr_penalty = 0.5 if correlation_to_portfolio > 0.7 else 1.0
    
    final_size = half_kelly * vol_scalar * corr_penalty
    return min(final_size, 0.10)  # Hard cap 10% per pick
```

---

## 🟢 WORLD-CLASS UPGRADES (Month 1)

### 10. Regime Detection: From Lagging to Leading

**Current:** 30-minute refresh with momentum confirmation (RSI, SMA, ADX) — all lagging

**World-Class Fix:**
```python
def microstructure_regime():
    """Update every 10 seconds via WebSocket"""
    
    # Leading indicators (not lagging)
    funding_velocity = (current_funding - funding_6h_ago) / 6  # Acceleration > level
    perp_premium = (perp_price - spot_price) / spot_price  # Arbitrage pressure
    book_pressure = (bid_vol_1pct - ask_vol_1pct) / (bid_vol_1pct + ask_vol_1pct)
    liq_clusters = get_liquidation_levels(symbol)
    distance_to_liq = abs(price - nearest_cluster) / price
    
    # Predict regime 5-15 minutes ahead of price movement
    regime_score = (
        funding_velocity * 0.3 +
        perp_premium * 0.25 +
        book_pressure * 0.25 +
        (1 / distance_to_liq) * 0.2  # Closer to liq = more volatile
    )
    
    return regime_score
```

---

### 11. The One-Page World-Class System

```
INPUT:      WebSocket (10s updates)
REGIME:     Microstructure ensemble (funding + premium + book pressure)
SIGNALS:    5 uncorrelated strategies max
FILTER:     Expected value > threshold (not score-based)
SIZE:       Fractional Kelly with vol scaling
TRACK:      Resolved batch equity curve
KILL:       Auto-kill if 20-trade resolved WR < 40%
```

**Complexity:** 5 files, not 100+. Speed: Sub-second, not 20-minute cron.

---

## 📊 Performance Targets

| Metric | Current | World-Class Target |
|--------|---------|-------------------|
| Signal-to-noise | 572 → 11 (2%) | 50 → 10 (20%) |
| Out-of-sample Sharpe | 2.95 (inflated) | >1.5 (conservative) |
| Max drawdown | Unknown | <15% monthly |
| Regime detection latency | 30 minutes | <2 minutes |
| ML AUC | 0.51 (broken) | >0.65 |
| Win rate by regime | 64% (biased to bear) | >55% in ALL regimes |
| Score-PnL correlation | r=0.05 | r>0.30 |

---

## ✅ IMMEDIATE ACTION CHECKLIST

### Today:
- [ ] Disable session bonus, death zone time filter, confluence penalty
- [ ] Add SYMBOL_EXCLUDE_LIST with FETUSDT, RENDERUSDT
- [ ] Fix R:R filter to hard-block < 1.0 for ALL sources
- [ ] Label batch WR as "unrealized snapshot" vs "resolved"

### This Week:
- [ ] Wire technical_features.py into scanner (fix feature population)
- [ ] Retrain ML with MFE/MAE labels (not TP/SL hits)
- [ ] Implement Kelly sizing with vol scaling
- [ ] Audit score_booster.py boosts vs live WR data
- [ ] Require min 50 closed trades for forward validation (not 4)

### Month 1:
- [ ] Deploy WebSocket regime detector (10s updates)
- [ ] Add cross-sectional ranking features
- [ ] Implement conformal prediction for uncertainty
- [ ] Build portfolio optimizer with correlation caps

---

## Summary

Your system is **over-engineered on scoring** and **under-engineered on speed, correlation, and edge detection**. Strip out 80% of the complexity, focus on:

1. **Microstructure regime detection** (speed matters)
2. **Uncorrelated signal generation** (5 strategies max)
3. **Kelly sizing** (risk management)
4. **Feature population** (ML needs real data)

**The 64% "median WR" is a mirage.** Only resolved batch (SP-v001) had 0% WR. Fix the fundamentals before claiming profitability.

---

*Document generated: March 24, 2026*  
*Next review: After 10 resolved Smart Picks batches*
