# Crypto-Automation Discord Feedback - Action Plan
**Date:** March 3, 2026  
**Source:** Discord #crypto-automation channel analysis  
**Status:** Critical Issues Identified → Action Plan Created

---

## 🚨 Executive Summary

The Discord notifications reveal several **fundamental issues** preventing the crypto trading systems from achieving fund-grade performance:

| Metric | Current State | Fund-Grade Target | Gap |
|--------|---------------|-------------------|-----|
| Win Rate (Claws-of-Doom) | ~48% | >55% | -7% |
| Realized P&L | -1.2% (-$4.36) | Positive | Losing money |
| Max Unrealized Drawdown | -18% | <-15% | Risk too high |
| Signal Outcome Coverage | 55% | >90% | Missing data |
| Pipeline Reliability | 97-99% | 99.9% | 1-3% failures |
| Short Exposure | 0% | 20-40% | All-long bias |

---

## 🔍 Critical Issues Identified

### 1. Pipeline Instability (GitHub Actions)
**Problem:** 1-3% of 600 daily runs failing (DNA-pipeline, ML-battleground, AsterDEX)

**Root Causes:**
- Missing columns after config changes
- NaN values in feature matrix
- API rate limits / authentication failures
- No schema validation before training

**Impact:** 
- Stale models
- Missing data
- Break-in-pipeline risk

### 2. Regime Bias (All-Long, No Shorts)
**Problem:** Every 30-45 min: **exactly 4 LONG picks, 0 SHORT picks**

**Root Cause:** 
- Market reported as "Extreme-Fear (F&G=14)" + "TRENDING_DOWN"
- But signals still go LONG ("Fear-Contrarian" logic)
- No short-side filter implemented

**Impact:**
- Over-exposed to downside
- No hedge during bear markets
- Higher tail risk

### 3. Static Risk Parameters
**Problem:** All picks use flat 5% TP / 5% SL regardless of volatility

**Evidence:**
- Captain-Hook/Claude-Code: 5% TP/SL on low-cap tokens (BONK, ONDO, XDC)
- Confidence always "VERY HIGH" (static, not model-derived)
- No volatility scaling

**Impact:**
- Slippage > TP on thin-liquidity assets
- Risk-reward is tiny (1:1)
- Edge disappears after fees

### 4. Claws-of-Doom v3 Underperformance
**Problem:** 10 active picks, 29 closed (14W/15L), Realized P&L: -1.2%

**Issues:**
- Win-rate <50%
- Large unrealized drawdown swings (-18% → +3%)
- Static price ladders (orders placed once/hour, never adjust)
- Model not adapting to price moves

### 5. Poor Signal Tracking
**Problem:** Only 55% of signals have outcomes recorded

**Root Causes:**
- Many signals canceled by circuit-breaker
- Signals never hit TP/SL (static targets)
- Missing outcome tracking

**Impact:**
- Performance metrics biased upward
- Only "good" outcomes recorded
- Can't properly evaluate strategies

---

## ✅ Immediate Actions (Quick Wins - This Week)

### Action 1: Fix Pipeline Reliability
**File:** `.github/workflows/` + `scripts/health_check.py`

```python
# Add schema validation before training
def validate_schema(df: pd.DataFrame, required_cols: list) -> bool:
    missing = set(required_cols) - set(df.columns)
    if missing:
        logger.error(f"Missing columns: {missing}")
        return False
    if df[required_cols].isnull().sum().sum() > 0:
        logger.error("NaN values detected")
        return False
    return True
```

**Tasks:**
- [ ] Add `pandas_schema` validation to DNA-pipeline
- [ ] Implement exponential backoff for API calls (AsterDEX)
- [ ] Add circuit-breaker pause after 3 consecutive failures
- [ ] Create health-check endpoint `/health` with Grafana dashboard

**Success Metric:** Pipeline failures <0.1%

---

### Action 2: Add Duplicate Filter (Deduplication)
**File:** `scripts/send_top_picks_now.py`

Already partially implemented with `_filter_duplicates()` but needs tightening:

```python
# Tighten dedup cooldown from 4 hours to 5 minutes for volatile markets
DEDUP_COOLDOWN_MINUTES = 5  # was 240

# Add symbol+direction dedup (not just fingerprint)
def _signal_fingerprint(sig: dict) -> str:
    key = f"{sig.get('symbol')}|{sig.get('direction')}|{sig.get('entry_price')}"
    return hashlib.md5(key.encode()).hexdigest()
```

**Success Metric:** No duplicate symbols within 5-minute window

---

### Action 3: Make TP/SL Volatility-Scaled
**File:** `signal_aggregator/picks_router.py` + all signal generators

```python
def compute_dynamic_tp_sl(entry: float, atr: float, direction: str, 
                          rr_ratio: float = 1.5) -> tuple:
    """
    Compute TP/SL based on ATR (Average True Range).
    
    Args:
        entry: Entry price
        atr: 14-period ATR
        direction: "BUY" or "SELL"
        rr_ratio: Risk:Reward ratio (default 1.5)
    
    Returns:
        (tp_price, sl_price)
    """
    sl_distance = 1.5 * atr  # 1.5x ATR for stop
    tp_distance = sl_distance * rr_ratio  # TP = SL * R:R
    
    if direction == "BUY":
        sl = entry - sl_distance
        tp = entry + tp_distance
    else:
        sl = entry + sl_distance
        tp = entry - tp_distance
    
    return tp, sl
```

**Update:** All signal generators to use this instead of fixed percentages

**Success Metric:** TP/SL proportional to volatility (ATR-based)

---

### Action 4: Compute Confidence from Model + Regime
**File:** `signal_aggregator/picks_router.py`

```python
def compute_dynamic_confidence(
    model_proba: float,
    regime_probs: dict,
    current_regime: str
) -> float:
    """
    Compute confidence from model probability and regime alignment.
    
    Formula: conf = model_proba * regime_alignment_factor
    
    Regime alignment:
    - TREND + LONG: 1.0x (aligned)
    - TREND + SHORT: 1.0x (aligned)
    - RANGE + any: 0.8x (choppy, reduce confidence)
    - CRASH + LONG: 0.3x (counter-trend, very risky)
    """
    alignment_factors = {
        ("TREND", "BUY"): 1.0,
        ("TREND", "SELL"): 1.0,
        ("RANGE", "BUY"): 0.8,
        ("RANGE", "SELL"): 0.8,
        ("CRASH", "BUY"): 0.3,  # Dangerous!
        ("CRASH", "SELL"): 1.2,  # Good hedge
    }
    
    factor = alignment_factors.get((current_regime, direction), 0.5)
    confidence = model_proba * factor
    
    return min(confidence, 1.0)  # Cap at 1.0
```

**Success Metric:** Confidence varies with regime (no more static "VERY HIGH")

---

### Action 5: Add Kelly-Fraction Sizing
**File:** `signal_aggregator/picks_router.py` + Discord embed

```python
def kelly_fraction(p: float, edge: float, vol: float, cap: float = 0.02) -> float:
    """
    Calculate Kelly fraction for position sizing.
    
    Args:
        p: Model confidence (probability of win)
        edge: Expected return per trade (TP-entry)/entry
        vol: Forecasted volatility (annualized)
        cap: Max fraction of portfolio per trade (default 2%)
    
    Returns:
        Fraction of portfolio to allocate (0 to cap)
    """
    # Simple Kelly: f = (2p-1) * edge / vol^2
    f = (2 * p - 1) * edge / (vol ** 2)
    return max(min(f, cap), 0.0)  # Never negative, never exceed cap

# In Discord embed, add:
fields.append({
    'name': 'Position Size',
    'value': f"{size_frac:.1%} of portfolio (Kelly)",
    'inline': True
})
```

**Success Metric:** Position sizes proportional to edge/volatility

---

### Action 6: Attach Order Expiry
**File:** `scripts/send_top_picks_now.py` + execution layer

```python
# Add to signal dict
signal['expires_at'] = (datetime.now(timezone.utc) + 
                        timedelta(minutes=15)).isoformat()

# In execution layer, auto-cancel if not filled
def cancel_expired_orders():
    now = datetime.now(timezone.utc)
    for order in active_orders:
        if order['expires_at'] < now:
            cancel_order(order['id'])
```

**Success Metric:** No stale orders >15 minutes old

---

### Action 7: Add Short-Side Filter
**File:** `signal_aggregator/picks_router.py`

```python
def should_emit_short(
    confidence: float,
    regime: str,
    fear_greed_index: float
) -> bool:
    """
    Determine if a short signal should be emitted.
    
    Rules:
    1. Regime must be TRENDING_DOWN or CRASH
    2. Confidence < 0.30 (model predicts down move)
    3. Not in extreme fear (F&G < 10) - avoid short squeeze
    """
    if regime not in ["TRENDING_DOWN", "CRASH"]:
        return False
    
    if confidence > 0.30:  # Model thinks it goes up
        return False
    
    if fear_greed_index < 10:  # Extreme fear - potential reversal
        return False
    
    return True
```

**Success Metric:** Short signals appear (target: 20-40% of total)

---

### Action 8: Enforce Circuit Breaker Pre-Send
**File:** `scripts/send_top_picks_now.py` (already partially implemented)

Already has `_check_circuit_breaker_pre_send()` but needs to be more aggressive:

```python
def _check_circuit_breaker_pre_send():
    # ... existing code ...
    
    # NEW: Per-symbol VaR check
    for signal in signals:
        var = compute_var_1d(signal['symbol'])
        if var > 0.05:  # 5% of portfolio
            logger.warning(f"VaR too high for {signal['symbol']}: {var:.1%}")
            signal['blocked_by_var'] = True
    
    # NEW: Liquidity guard
    for signal in signals:
        depth = get_orderbook_depth(signal['symbol'])
        if depth < signal['size'] * portfolio_value:
            logger.warning(f"Insufficient liquidity for {signal['symbol']}")
            signal['blocked_by_liquidity'] = True
```

**Success Metric:** No signals sent when CB is RED/HALT or VaR exceeded

---

## 🎯 Medium-Term Actions (Next 2 Weeks)

### Action 9: Implement Full Risk Management Layer
**File:** `risk_management/enhanced_risk_engine.py` (new)

Components:
1. **Portfolio Circuit Breaker** (existing, enhance)
2. **Per-Symbol VaR Guard** (new)
3. **Liquidity Guard** (new)
4. **Dynamic Exposure Caps** based on F&G (new)

```python
class EnhancedRiskEngine:
    def __init__(self):
        self.circuit_breaker = PortfolioCircuitBreaker()
        self.var_limit = 0.05  # 5% per symbol
        self.liquidity_threshold = 0.02  # 2% of portfolio
    
    def check_signal(self, signal: dict, portfolio: dict) -> tuple:
        """
        Full risk check before sending signal.
        
        Returns:
            (allowed: bool, reason: str)
        """
        # 1. Circuit breaker
        cb_status = self.circuit_breaker.check(portfolio['equity_curve'])
        if cb_status.level in ["RED", "HALT"]:
            return False, f"Circuit breaker: {cb_status.level}"
        
        # 2. Per-symbol VaR
        var = self.compute_var_historical(signal['symbol'])
        if var > self.var_limit:
            return False, f"VaR {var:.1%} exceeds limit {self.var_limit:.1%}"
        
        # 3. Liquidity guard
        depth = self.get_orderbook_depth(signal['symbol'])
        needed = signal['size_frac'] * portfolio['value']
        if depth < needed:
            return False, f"Insufficient depth: ${depth:,.0f} < ${needed:,.0f}"
        
        # 4. Dynamic exposure cap based on F&G
        fg_index = self.get_fear_greed_index()
        if fg_index <= 10:  # Extreme fear
            max_exposure = 0.50  # 50% of normal
            current_exposure = portfolio['exposure']
            if current_exposure >= max_exposure:
                return False, f"Max exposure in extreme fear: {max_exposure:.0%}"
        
        return True, "PASS"
```

---

### Action 10: Walk-Forward Back-Testing
**File:** `scripts/evaluate_all.py` (enhance existing)

```python
def walk_forward_evaluation(
    start: datetime,
    end: datetime,
    train_window: int = 180,  # days
    test_window: int = 30     # days
):
    """
    Run walk-forward analysis with dynamic TP/SL and Kelly sizing.
    """
    results = []
    current = start
    
    while current + timedelta(days=train_window + test_window) <= end:
        train_end = current + timedelta(days=train_window)
        test_end = train_end + timedelta(days=test_window)
        
        # Train on [current, train_end)
        train_data = load_data(current, train_end)
        model = train_model(train_data)
        
        # Test on [train_end, test_end)
        test_data = load_data(train_end, test_end)
        signals = generate_signals(model, test_data)
        
        # Evaluate with new risk parameters
        stats = backtest_with_dynamic_tp_sl(signals, test_data)
        results.append(stats)
        
        current = train_end
    
    return pd.DataFrame(results)
```

**Success Metrics:**
- Sharpe ≥ 1.2 (annualized)
- Profit-factor ≥ 1.5
- Max-drawdown ≤ 15%
- Turnover ≤ 10% per day

---

### Action 11: Monte-Carlo Stress Testing
**File:** `ml_crypto_predictor/stress_test.py` (already exists, enhance)

Already implemented in previous commit - need to integrate:

```python
# Run stress test on all strategies
stress_results = run_stress_test(
    symbol="BTC-USD",
    start_price=30_000,
    n_paths=10_000,
    model=router.run_regime_trend_strategy
)

# Check 95th percentile
dd_95 = stress_results['max_dd'].quantile(0.95)
sharpe_median = stress_results['sharpe'].median()

assert dd_95 <= 0.15, f"95% DD too high: {dd_95:.1%}"
assert sharpe_median >= 1.2, f"Median Sharpe too low: {sharpe_median:.2f}"
```

---

## 📊 Success Metrics & Gates

### Fund-Grade Gate Criteria

| Metric | Threshold | Current | Status |
|--------|-----------|---------|--------|
| Sharpe (annualized) | ≥ 1.2 | ~0.8 | ❌ Fail |
| Profit-Factor | ≥ 1.5 | ~0.9 | ❌ Fail |
| Max Drawdown | ≤ 15% | -18% | ❌ Fail |
| Win Rate | ≥ 55% | 48% | ❌ Fail |
| Pipeline Uptime | ≥ 99.9% | 97-99% | ❌ Fail |
| Signal Outcome Coverage | ≥ 90% | 55% | ❌ Fail |
| Short Exposure | 20-40% | 0% | ❌ Fail |

**Target:** Meet all criteria on walk-forward AND live-paper before deploying real capital.

---

## 🚀 Implementation Priority

### Week 1 (Critical)
1. ✅ Fix pipeline failures (schema validation)
2. ✅ Tighten dedup cooldown (5 min)
3. ✅ Add volatility-scaled TP/SL
4. ✅ Add Kelly-fraction sizing
5. ✅ Add order expiry (15 min)

### Week 2 (High Priority)
6. ✅ Add short-side filter
7. ✅ Enhance circuit breaker (VaR, liquidity)
8. ✅ Dynamic confidence from model + regime
9. ✅ Run walk-forward back-test

### Week 3-4 (Medium Priority)
10. ✅ Monte-Carlo stress test
11. ✅ Live-paper deployment (30 days)
12. ✅ Dashboard & monitoring (Grafana)

---

## 📋 Code Changes Required

### Files to Modify:
1. `scripts/send_top_picks_now.py` - dedup, expiry, safety filters
2. `signal_aggregator/picks_router.py` - confidence, sizing, shorts
3. `risk_management/portfolio_circuit_breaker.py` - VaR, liquidity
4. All signal generators - dynamic TP/SL using ATR
5. `.github/workflows/` - schema validation, health checks

### New Files to Create:
1. `risk_management/enhanced_risk_engine.py` - unified risk layer
2. `scripts/health_check.py` - pipeline monitoring
3. `scripts/evaluate_all.py` - walk-forward testing (enhance)
4. `tests/test_risk_engine.py` - unit tests

---

## 📝 Notes

- **All changes must pass fund-grade gates before live deployment**
- **Start with paper trading for 30 days minimum**
- **Log every order, slippage, and fill-rate during paper trading**
- **Compare realized Sharpe to back-test (should be within ±10%)**

---

**Next Steps:**
1. Review this action plan
2. Prioritize quick wins (Week 1)
3. Implement changes incrementally
4. Run evaluation pipeline after each change
5. Report metrics back to Discord #crypto-automation
