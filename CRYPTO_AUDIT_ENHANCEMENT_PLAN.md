# Crypto/Forex Audit Page Enhancement Plan
## findtorontoevents.ca/audit — High-Quality Picks Implementation

**Date:** March 26, 2026  
**Status:** Draft — Awaiting Review  
**Priority:** P0 (Critical for User Trust)

---

## Executive Summary

The audit dashboard currently shows mixed-quality picks due to:
1. **Polluted data sources** — Raw copy-trader signals, HFT market makers, and stale prediction market rows
2. **Inconsistent quality gates** — Different filtering logic for Active Picks vs Smart Picks
3. **Artifact drift** — Multiple workflows overwrite dashboard data independently

**Goal:** When users filter to "Crypto" → "Active Picks" or click "Smart Picks", they see ONLY high-quality, vetted picks with proven edge.

---

## Current State (From TODO Analysis)

### Problems Identified

| Issue | Impact | Source File |
|-------|--------|-------------|
| HFT traders contaminate copy-trader pipeline | 31% WR, -91% PnL | `copy_trader_intel/main.py` |
| PM signals have entry_price=0 (not tradeable) | Signal-only rows in Active Picks | `prediction_market_agents/orchestrator.py` |
| 4 different WR formulas across codebase | Inconsistent quality metrics | `template.html`, `portfolio_manager.py`, etc. |
| 2,900+ isolated picks not feeding dashboard | Missing quality signals | Various orphan sources |
| ML 15m models anti-predictive | 47% WR, -1.72% PnL | `ml_crypto_predictor/` |
| Stale picks >24h not cleaned | Zombie positions accumulate | `force_close_breached.py` |
| Smart WR conflates history + snapshot | Misleading KPI | `smart_picks_history.json` |

### What Was Recently Fixed
- ✅ SL gap-through bug (5-11x loss amplification fixed)
- ✅ Copy trader HFT filter (4h min hold, stale cleanup)
- ✅ Forex TP calibration (0.8% → 0.3%)
- ✅ PM pipeline unblocked (consensus threshold lowered)
- ✅ ML symbol expansion (4 → 13 symbols)
- ✅ Kill list prefix bug fixed
- ✅ Scoring overhaul (r=-0.001 → r=+0.33 correlation)

---

## Proposed Enhancement: "Quality Gates" System

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    QUALITY GATES PIPELINE                        │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 1: SOURCE VETTING (At Generation)                        │
│  ├── PERMANENTLY_KILLED strategies blocked at scanner           │
│  ├── HFT filter on copy-trader (median_hold > 4h)               │
│  ├── Fake ML scores rejected (ml_score ≠ confidence)            │
│  └── Entry price validation (entry > 0 for tradeable picks)     │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 2: ACTIVE PICKS FILTER (Dashboard Display)               │
│  ├── Status = OPEN (no SL_HIT/TP_HIT/EXPIRED)                   │
│  ├── Entry price > 0 (tradeable, not signal-only)               │
│  ├── Age < 72h for crypto, < 240h for non-crypto                │
│  ├── Source tier ≥ WATCH (no EXPERIMENTAL sources)              │
│  └── Score ≥ 55 (elite_score floor)                             │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 3: SMART PICKS FILTER (Premium Quality)                  │
│  ├── All Active Picks criteria PLUS:                            │
│  ├── Score ≥ 65 (top quartile)                                  │
│  ├── Confidence 0.60-0.70 sweet spot (87% WR band)              │
│  ├── R:R ≥ 1.5 (risk-adjusted)                                  │
│  ├── ML score populated (not null/zero)                         │
│  ├── Strategy tier: TOP_TIER or PROVEN only                     │
│  └── Direction consensus: ≥2 independent sources agree          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Data Hygiene (P0 — This Week)

#### 1.1 Active Picks Cleanup
**File:** `audit_trail/dashboard_generator.py`

Add strict filtering at payload generation:

```python
# New function to add to dashboard_generator.py
def _passes_active_picks_gate(pick: dict) -> bool:
    """
    Quality gate for Active Picks display.
    Returns True only for tradeable, vetted picks.
    """
    # Must be genuinely open
    status = str(pick.get("status", "")).upper()
    if status not in {"", "OPEN", "ACTIVE", "PENDING"}:
        return False
    
    # Must have tradeable entry price
    entry = _float(pick.get("entry_price", 0))
    if entry <= 0:
        return False  # Signal-only, not tradeable
    
    # Must have TP/SL defined
    tp = _float(pick.get("take_profit", 0))
    sl = _float(pick.get("stop_loss", 0))
    if tp <= 0 or sl <= 0:
        return False
    
    # Age check (prevent stale zombies)
    created = pick.get("created_at") or pick.get("timestamp")
    if created:
        age_hours = _calculate_age_hours(created)
        asset_class = pick.get("asset_class", "CRYPTO").upper()
        max_age = 240 if asset_class in {"FOREX", "EQUITY", "COMMODITY"} else 72
        if age_hours > max_age:
            return False
    
    # Source tier check
    source = pick.get("source_system", "")
    if _get_source_tier(source) == "EXPERIMENTAL":
        return False
    
    return True
```

#### 1.2 Smart Picks Premium Filter
**File:** `alpha_engine/smart_picks_engine.py` (or create new)

```python
def _passes_smart_picks_gate(pick: dict) -> bool:
    """
    Premium quality gate for Smart Picks.
    Only top-quartile picks pass.
    """
    # Must pass active picks gate first
    if not _passes_active_picks_gate(pick):
        return False
    
    # Score floor (top quartile)
    score = pick.get("elite_score") or pick.get("score", 0)
    if score < 65:
        return False
    
    # Confidence sweet spot (data shows 0.60-0.70 = 87% WR)
    conf = pick.get("confidence", 0)
    if conf < 0.58:  # QUALITY_GATE_MIN_CONFIDENCE
        return False
    
    # R:R check
    entry = pick.get("entry_price", 0)
    tp = pick.get("take_profit", 0)
    sl = pick.get("stop_loss", 0)
    if entry > 0 and tp > 0 and sl > 0:
        rr = abs(tp - entry) / abs(entry - sl) if entry != sl else 0
        if rr < 1.5:
            return False
    
    # ML score must be populated (not trading blind)
    ml_score = pick.get("ml_score")
    if ml_score is None or ml_score == 0:
        return False
    
    # Strategy tier check
    strategy = pick.get("strategy", "")
    if strategy in LOW_CONFIDENCE_STRATEGIES:
        return False
    
    # For crypto: require multiple source confirmation
    asset_class = pick.get("asset_class", "CRYPTO").upper()
    if asset_class == "CRYPTO":
        source_systems = pick.get("source_systems", [])
        if len(source_systems) < 2:
            # Single source picks need extra validation
            if pick.get("forward_wr", 0) < 0.60:
                return False
    
    return True
```

#### 1.3 Kill Specific Polluters
**File:** Update `alpha_engine/auto_tuner.py`

Add to `PERMANENTLY_KILLED`:
- `binance_smart_money` — NOT copy trading, just sentiment aggregate
- `hl_funding_fade` — 0/11 = 0% WR
- All `*_15m_*` ML models — 47% WR, anti-predictive

### Phase 2: UI/UX Enhancements (P1 — Next Week)

#### 2.1 Smart Picks Tab Redesign
**File:** `audit_dashboard/template.html`

Add visual quality indicators:

```html
<!-- Smart Picks Badge System -->
<span class="quality-badge tier-top">⭐ TOP TIER</span>
<span class="quality-badge confidence-sweet">🎯 87% Zone</span>
<span class="quality-badge ml-validated">🤖 ML Validated</span>
<span class="quality-badge multi-source">🤝 Consensus</span>
<span class="quality-badge inverse-edge">🔄 Inverse Proven</span>

<!-- Tooltip explaining why this pick is "Smart" -->
<div class="smart-pick-rationale">
  <strong>Why this pick is Smart:</strong>
  <ul>
    <li>✅ Elite Score 72 (top 15%)</li>
    <li>✅ Confidence 0.65 (sweet spot)</li>
    <li>✅ ML Score 0.71 (high signal)</li>
    <li>✅ 3 independent sources agree</li>
    <li>✅ Forward WR 81% (16 trades)</li>
  </ul>
</div>
```

#### 2.2 Quality Filter Controls

Add filter pills to the filter bar:

```html
<div class="quality-filters">
  <button class="filter-pill active" data-filter="all">All Active</button>
  <button class="filter-pill" data-filter="smart">⭐ Smart Picks</button>
  <button class="filter-pill" data-filter="ml">🤖 ML Only</button>
  <button class="filter-pill" data-filter="consensus">🤝 Consensus</button>
  <button class="filter-pill" data-filter="inverse">🔄 Inverse Edge</button>
</div>
```

#### 2.3 Empty State Messaging

When filters return no picks, show helpful context:

```html
<div class="empty-state">
  <h3>🔍 No Smart Picks Currently Available</h3>
  <p>This is actually GOOD — we only show picks that meet our strict quality criteria.</p>
  <ul>
    <li>Current market regime may be uncertain (FGI: <span id="fgi-value">11</span>)</li>
    <li>We need ≥2 independent sources to agree for Smart Picks</li>
    <li>Try "All Active" to see all vetted picks, or check back in 30 min</li>
  </ul>
  <p class="tip">💡 Tip: Smart Picks average 72% WR vs 35% for all picks</p>
</div>
```

### Phase 3: Smart Picks Engine Improvements (P2 — Ongoing)

#### 3.1 Real-Time Quality Scoring
**File:** `alpha_engine/smart_picks_engine.py`

Implement dynamic scoring based on:

```python
SMART_PICKS_WEIGHTS = {
    # Core predictive factors (from decile test results)
    'ml_score': 0.30,           # r=+0.33 Spearman
    'confidence_sweet_spot': 0.25,  # 0.60-0.70 band = 87% WR
    'forward_wr': 0.20,         # Track record matters
    'rr_ratio': 0.15,           # R:R ≥1.5 = 68% WR
    'source_consensus': 0.10,   # Multi-source agreement
}

def calculate_smart_score(pick: dict) -> float:
    """Calculate 0-100 Smart Score for ranking."""
    score = 0
    
    # ML Score component (0-30 pts)
    ml = pick.get('ml_score', 0)
    score += min(ml * 30, 30)
    
    # Confidence sweet spot (0-25 pts)
    conf = pick.get('confidence', 0)
    if 0.60 <= conf <= 0.70:
        score += 25
    elif 0.55 <= conf < 0.60:
        score += 15
    elif 0.70 < conf <= 0.80:
        score += 10
    else:
        score += max(0, 25 - abs(conf - 0.65) * 50)
    
    # Forward WR component (0-20 pts)
    fwd = pick.get('forward_wr', 0)
    score += min(fwd * 20, 20)
    
    # R:R component (0-15 pts)
    entry = pick.get('entry_price', 0)
    tp = pick.get('take_profit', 0)
    sl = pick.get('stop_loss', 0)
    if entry and tp and sl:
        rr = abs(tp - entry) / abs(entry - sl) if entry != sl else 0
        score += min(rr * 10, 15)
    
    # Consensus bonus (0-10 pts)
    sources = pick.get('source_systems', [])
    score += min(len(sources) * 3, 10)
    
    return round(score, 1)
```

#### 3.2 Inverse Strategy Prioritization

From TODO analysis, inverse strategies show 78% avg WR:

```python
INVERSE_STRATEGIES = {
    'st_multi_day_momentum': 84.3,
    'claude_gainer_1h': 78.7,
    'luxalgo_confluence': 69.9,
    'crypto_rsi_whaleconfirmed_v1': 81.8,
    'atr_regime_rsi': 74.1,
    'winner_pattern_precursor': 77.2,
}

def get_inverse_boost(strategy: str) -> float:
    """Boost score for proven inverse strategies."""
    return 1.2 if strategy in INVERSE_STRATEGIES else 1.0
```

---

## Specific File Changes Required

### 1. `audit_trail/dashboard_generator.py`

**Add:**
- `_passes_active_picks_gate()` function
- Filter active picks through gate before adding to payload
- Add `smart_picks` array to payload (premium-filtered)

**Lines to modify:** ~150-200 (in pick aggregation section)

### 2. `alpha_engine/smart_picks_engine.py`

**Modify:**
- `score_pick()` to use new weighting
- `select_smart_picks()` to apply Smart Picks gate
- Add `calculate_smart_score()` function

### 3. `audit_dashboard/template.html`

**Add:**
- Quality filter pills UI
- Smart Picks badge system
- Empty state component
- Tooltips explaining quality criteria

**Modify:**
- Active picks table rendering
- Filter bar to include quality filters

### 4. `alpha_engine/auto_tuner.py`

**Add to PERMANENTLY_KILLED:**
```python
PERMANENTLY_KILLED = [
    'binance_smart_money',      # NOT copy trading
    'hl_funding_fade',          # 0% WR
    'cta_tsmom_blend',          # 22% WR
    'yahoo_analyst_consensus',  # 0% WR
    'winner_pattern_precursor', # 5% WR
    # ... existing entries
]
```

---

## Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Active Picks (Crypto) Quality Score | ~45 | ≥70 | Avg elite_score of displayed picks |
| Smart Picks WR | ~54% | ≥70% | Forward-tested over 50 trades |
| Smart Picks % of Portfolio | N/A | 20-30% | # Smart / # Total Active |
| 0% WR Strategies in Active | 35% | 0% | Count of PERMANENTLY_KILLED in active |
| Signal-only rows (entry=0) | ~5% | 0% | Rows with entry_price=0 or TP=0/SL=0 |
| User "Why Smart?" tooltip CTR | N/A | >30% | Click rate on rationale tooltips |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Too few Smart Picks (empty state) | Keep "All Active" as default; Smart as opt-in filter |
| Over-fitting to historical data | Use walk-forward validation for score weights |
| Strategy decay (what worked stops working) | Auto-deprecate strategies with 10+ losing streak |
| User confusion about filtering | Clear tooltips; "Why am I seeing this?" explanations |
| Data pipeline latency | Show "Last Updated" timestamp; cache freshness indicator |

---

## Implementation Checklist

### Week 1: Foundation
- [ ] Implement `_passes_active_picks_gate()` in dashboard_generator.py
- [ ] Add PERMANENTLY_KILLED strategies to auto_tuner.py
- [ ] Deploy and monitor Active Picks count/quality
- [ ] Fix any broken data sources

### Week 2: Smart Picks
- [ ] Implement Smart Picks scoring engine
- [ ] Add Smart Picks filter to template.html
- [ ] Create quality badge UI components
- [ ] Deploy Smart Picks tab

### Week 3: Polish
- [ ] Add empty state messaging
- [ ] Implement rationale tooltips
- [ ] A/B test Smart vs All Active performance
- [ ] Monitor user engagement metrics

### Week 4: Optimize
- [ ] Tune scoring weights based on forward performance
- [ ] Add inverse strategy prioritization
- [ ] Implement ML feature population fixes
- [ ] Document quality criteria publicly

---

## Appendix: Quality Criteria Reference

### Active Picks Minimum Criteria
1. **Tradeable** — Has entry_price > 0, TP > 0, SL > 0
2. **Live** — Status is OPEN/ACTIVE (not resolved)
3. **Fresh** — Age < 72h (crypto) or < 240h (non-crypto)
4. **Vetted Source** — Source tier ≥ WATCH (not EXPERIMENTAL)
5. **Not Killed** — Strategy not in PERMANENTLY_KILLED

### Smart Picks Additional Criteria
1. **Elite Score** ≥ 65 (top quartile)
2. **Confidence** 0.58-0.80 (sweet spot, not overconfident)
3. **R:R** ≥ 1.5 (positive expectancy)
4. **ML Score** populated and > 0.5
5. **Strategy Tier** TOP_TIER or PROVEN
6. **Multi-Source** ≥ 2 independent sources (for crypto)

---

*This plan addresses all major issues identified in TODO1-5 and CHATWITHIT.MD while maintaining operational continuity.*
