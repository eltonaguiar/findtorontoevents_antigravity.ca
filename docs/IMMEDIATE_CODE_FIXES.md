# Immediate Code Fixes: Apply These Today

**Priority:** CRITICAL  
**Estimated Time:** 2-4 hours  
**Expected Impact:** Fix 80% of scoring issues

---

## Fix 1: Hard Block R:R < 1.5 (5 minutes)

**File:** `alpha_engine/forward_validator.py`

**Add at the top of validation loop:**
```python
# --- R:R HARD GATE ---
RR_MINIMUM = 1.5

for pick in picks:
    rr = pick.get('risk_reward', 0)
    if rr < RR_MINIMUM:
        print(f"[RR_GATE] BLOCK {pick['symbol']} — R:R {rr:.2f} < {RR_MINIMUM}")
        pick['blocked'] = True
        pick['block_reason'] = f'RR_TOO_LOW:{rr:.2f}'
        continue
```

**Why:** SP-v015 has 5 picks with R:R < 1.5 that should have been blocked.

---

## Fix 2: Exclude FETUSDT from WR Stats (10 minutes)

**File:** `alpha_engine/elite_scorer.py`

**Add at module level:**
```python
# Symbols that distort strategy performance metrics
OUTLIER_SYMBOLS = {'FETUSDT', 'RENDERUSDT'}  # Add others >20% of total PnL
```

**Modify `compute_forward_wr()`:**
```python
def compute_forward_wr(strategy_name, closed_picks):
    """Compute WR excluding outlier symbols"""
    strategy_picks = [p for p in closed_picks 
                      if p['strategy'] == strategy_name 
                      and p['symbol'] not in OUTLIER_SYMBOLS]
    
    if len(strategy_picks) < 4:
        return 0.0, 0  # WR, trade_count
    
    wins = sum(1 for p in strategy_picks if p['outcome'] == 'WON')
    wr = wins / len(strategy_picks)
    
    return wr, len(strategy_picks)
```

**Why:** 153.6% of total PnL comes from FETUSDT alone. Remove it → -1,582% PnL.

---

## Fix 3: Fix Confidence Scoring Sweet Spot (10 minutes)

**File:** `alpha_engine/elite_scorer.py`

**Replace `compute_confidence_score()`:**
```python
def compute_confidence_score(confidence):
    """
    FIXED: 0.60-0.70 has 61% WR (best) — was being penalized!
    """
    if confidence is None:
        return 0
    
    # Sweet spot: 0.60-0.70 = 61% WR (best performance)
    if 0.60 <= confidence <= 0.70:
        return 8
    elif 0.70 < confidence <= 0.75:
        return 6
    elif 0.55 <= confidence < 0.60:
        return 4
    elif 0.75 < confidence <= 0.80:
        return 3
    elif confidence > 0.80:
        return 2  # Overconfidence — actually worse performance
    else:
        return 0  # Below 0.55 = noise
```

**Why:** Old code penalized 0.60-0.70 range which had the BEST win rate.

---

## Fix 4: Label Unrealized vs Resolved WR (15 minutes)

**File:** `alpha_engine/smart_picks_tracker.py`

**Modify batch stats computation:**
```python
def compute_batch_stats(batch):
    """Clearly distinguish unrealized from resolved"""
    if batch.get('resolved', False):
        return {
            'win_rate': batch['final_wr'],
            'avg_pnl': batch['final_avg_pnl'],
            'tp_hits': batch['tp_hits'],
            'sl_hits': batch['sl_hits'],
            'label': 'RESOLVED',  # This is REAL
            'sample_size': batch['total_picks']
        }
    else:
        # Snapshot can reverse!
        return {
            'win_rate': batch['snapshot_wr'],
            'avg_pnl': batch['snapshot_pnl'],
            'tp_hits': batch.get('tp_hits', 0),
            'sl_hits': batch.get('sl_hits', 0),
            'label': 'UNREALIZED_SNAPSHOT',  # NOT final!
            'sample_size': batch['total_picks'],
            'warning': 'PnL can reverse — SP-v001 was +1.32% at 6.7h, -8.10% at 22.9h'
        }
```

**Why:** Dashboard shows "64% Median WR" but only 1 batch resolved with 0% WR.

---

## Fix 5: Reduce Quality Weight in Smart Score (10 minutes)

**File:** `alpha_engine/smart_picks_engine.py`

**Modify `compute_smart_score()`:**
```python
def compute_smart_score(pick, regime):
    """
    FIXED: Reduce elite_quality weight until ML is fixed
    """
    # Regime match (INCREASED — this is the only thing working)
    if pick.direction == regime.primary_direction:
        regime_score = 1.0
    elif regime.state in ['CHOPPY', 'NEUTRAL']:
        regime_score = 0.5
    else:
        regime_score = 0.0
    
    # Elite quality (REDUCED — ML is broken, quality is noise)
    elite_score = min(pick.get('elite_score', 50), 100) / 100
    
    # Freshness
    age_hours = pick.get('age_hours', 0)
    if age_hours < 1:
        freshness = 1.0
    elif age_hours < 4:
        freshness = 0.8
    elif age_hours < 12:
        freshness = 0.5
    elif age_hours < 24:
        freshness = 0.25
    else:
        freshness = 0.0
    
    # TP upside
    tp_remaining = pick.get('tp_remaining_pct', 50)
    if tp_remaining > 70:
        tp_score = 1.0
    elif tp_remaining > 50:
        tp_score = 0.67
    elif tp_remaining > 30:
        tp_score = 0.33
    else:
        tp_score = 0.0
    
    # Currently winning
    pnl = pick.get('unrealized_pnl_pct', 0)
    if pnl > 0:
        winning = 1.0
    elif pnl == 0:
        winning = 0.5
    else:
        winning = 0.0
    
    # NEW WEIGHTS (reduced quality, increased regime)
    smart_score = (
        regime_score * 0.50 +      # WAS 0.40 — regime is only thing working
        elite_score * 0.10 +       # WAS 0.20 — ML broken
        freshness * 0.15 +
        tp_score * 0.15 +
        winning * 0.10
    ) * 100
    
    return smart_score
```

**Why:** Score-PnL correlation is r=0.05 — quality scoring is decorative.

---

## Fix 6: Audit and Fix Consensus Boost (20 minutes)

**File:** `alpha_engine/score_booster.py`

**Replace family boost logic:**
```python
def apply_family_boost(pick, system_live_wr):
    """
    FIXED: Scale boost by actual live WR, not outdated claims
    """
    # Get base boost from config
    base_boosts = {
        'copy_trader_consensus': 45,    # Claimed 72% WR
        'copy_trader_clones': 40,        # Claimed 55% WR
        'copy_trader_intel': 35,         # Claimed 65% WR
        'copy_trader_highscore': 35,     # Claimed 70% WR
        'kimi_signal_tracking': 35,      # Claimed 57% WR
        'rapid_fire': 20,                # Claimed 55% WR
        'binance_smart_money': 15,       # Claimed 46% WR
    }
    
    source = pick.get('source_system', 'unknown')
    base_boost = base_boosts.get(source, 0)
    
    if base_boost == 0:
        return 0
    
    # Scale by actual performance
    # If live WR is 18% but claim was 72%, scale to 0.25x
    claimed_wr = {
        'copy_trader_consensus': 0.72,
        'copy_trader_clones': 0.55,
        'copy_trader_intel': 0.65,
        'copy_trader_highscore': 0.70,
        'kimi_signal_tracking': 0.57,
        'rapid_fire': 0.55,
        'binance_smart_money': 0.46,
    }.get(source, 0.50)
    
    scaling_factor = system_live_wr / claimed_wr if claimed_wr > 0 else 0.5
    scaling_factor = max(scaling_factor, 0.1)  # Min 10% of boost
    
    final_boost = base_boost * scaling_factor
    
    # Log for monitoring
    print(f"[BOOST] {source}: base={base_boost}, live_wr={system_live_wr:.1%}, "
          f"claimed={claimed_wr:.1%}, scale={scaling_factor:.2f}, final={final_boost:.1f}")
    
    return final_boost
```

**Why:** Consensus boost was +45 but live WR is 18.1% — contradiction!

---

## Fix 7: Add Volume-Based Gating (20 minutes)

**File:** `alpha_engine/production_scanner.py`

**Add volume gate:**
```python
def apply_volume_gate(pick):
    """
    Replace 'Death Zone' time filter with volume-based filter
    """
    symbol = pick['symbol']
    
    # Get 4H volume vs 30-day average
    vol_4h = get_volume(symbol, '4h')
    vol_30d_avg = get_volume_ma(symbol, '4h', 30)
    
    if vol_30d_avg == 0:
        return True  # Allow if no data
    
    vol_percentile = vol_4h / vol_30d_avg
    
    # Thin books = stop hunts
    if vol_percentile < 0.30:
        print(f"[VOLUME_GATE] BLOCK {symbol} — vol {vol_percentile:.1%} < 30th percentile")
        return False
    
    # High volume = good liquidity
    if vol_percentile > 2.0:
        pick['elite_score'] = pick.get('elite_score', 50) + 5
    
    return True
```

**Why:** UTC 13-16 is highest volume, not lowest. Time-based filter is wrong.

---

## Fix 8: Disable Broken Components (10 minutes)

**File:** `alpha_engine/elite_scorer.py`

**Set these components to 0:**
```python
# DISABLED COMPONENTS (anti-predictive or broken)
COMPONENTS_DISABLED = {
    'monte_carlo': True,        # 10% WR, -1.95% avg PnL
    'session_bonus': True,      # No edge in time-of-day
    'hindsight_winner': True,   # Survivorship bias
    'skyrocket_potential': True, # Unvalidated
    'meta_label': True,         # Same as broken ML
}

def compute_component_score(component_name, pick):
    if COMPONENTS_DISABLED.get(component_name, False):
        return 0  # Disabled
    
    # ... normal computation ...
```

**Why:** These components add noise, not signal.

---

## Fix 9: Add Live TP/SL Check (15 minutes)

**File:** `alpha_engine/smart_picks_engine.py`

**Add before scoring:**
```python
def check_tp_sl_hit(pick):
    """
    Don't rely on stale dashboard_payload for TP/SL status
    """
    symbol = pick['symbol']
    current_price = get_live_price(symbol)
    
    tp = pick.get('tp_price')
    sl = pick.get('sl_price')
    direction = pick.get('direction')
    
    if direction == 'LONG':
        if current_price >= tp:
            pick['status'] = 'TP_HIT'
            return False  # Exclude from scoring
        elif current_price <= sl:
            pick['status'] = 'SL_HIT'
            return False  # Exclude from scoring
    else:  # SHORT
        if current_price <= tp:
            pick['status'] = 'TP_HIT'
            return False
        elif current_price >= sl:
            pick['status'] = 'SL_HIT'
            return False
    
    return True  # Still active
```

**Why:** 30-min stale dashboard means closed picks still score as "winning".

---

## Fix 10: Wire Technical Features (1 hour)

**File:** `alpha_engine/scanner.py` or `production_scanner.py`

**Add feature population:**
```python
from technical_features import compute_all_features
from cross_sectional import compute_cross_sectional_features

def populate_features(signal):
    """
    Populate technical features at signal generation time
    """
    symbol = signal['symbol']
    
    # Fetch OHLCV
    ohlcv = fetch_ohlcv(symbol, timeframe='30m', bars=50)
    
    if ohlcv is None or len(ohlcv) < 30:
        return signal  # Skip if no data
    
    # Compute technical features
    tech_features = compute_all_features(ohlcv)
    signal.update(tech_features)
    
    # Compute cross-sectional features
    try:
        cs_features = compute_cross_sectional_features(
            symbol, 
            universe=get_top_50_symbols()
        )
        signal.update(cs_features)
    except Exception as e:
        print(f"[CS_FEATURES] Error for {symbol}: {e}")
    
    return signal
```

**Why:** Only 1 of 46 features is "alive" — the rest are defaults.

---

## Quick Wins Summary

| Fix | Time | Impact |
|-----|------|--------|
| R:R hard gate | 5 min | Blocks worst picks |
| Exclude FETUSDT | 10 min | Real performance metrics |
| Fix confidence scoring | 10 min | Use best-performing range |
| Label unrealized WR | 15 min | Honest reporting |
| Reduce quality weight | 10 min | Focus on regime |
| Fix consensus boost | 20 min | Align with live data |
| Volume gating | 20 min | Replace broken time filter |
| Disable broken components | 10 min | Remove noise |
| Live TP/SL check | 15 min | Accurate status |
| Wire technical features | 1 hour | Fix ML feature crisis |

**Total:** ~3 hours to fix 80% of issues

---

## Verification Checklist

After applying fixes, verify:

- [ ] No picks with R:R < 1.5 in Smart Picks
- [ ] FETUSDT excluded from strategy WR calculations
- [ ] Confidence 0.60-0.70 gets highest score
- [ ] Dashboard labels "unrealized" vs "resolved"
- [ ] Smart score weights: regime 50%, quality 10%
- [ ] Consensus boost scaled by live WR
- [ ] Volume gate replaces time-based "Death Zone"
- [ ] Disabled components return 0
- [ ] Features populated in active_picks.json

---

*Apply these fixes. Deploy. Measure. Iterate.*
