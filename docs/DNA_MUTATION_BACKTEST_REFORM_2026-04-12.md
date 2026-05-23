# DNA Mutation, Backtesting & Universe Reform — 2026-04-12

> **Objective:** Fix the backtest-to-live drift problem through better backtesting methods, symbol universe expansion, and DNA mutations for failing strategies.

---

## Executive Summary

The system has 27 strategies with <40% WR on 10+ trades, collectively losing **-770%** PnL. The DNA mutation infrastructure exists (`dna_mutation_engine.py`, `genome/`, `incubator/`) but is barely used — only 99 mutated picks out of 3,500 total (2.8%). The existing mutations that DO run are mostly profitable. The symbol universe is concentrated: 31% of crypto trades are on 5 symbols, and `TRXUSDT` alone accounts for -86% PnL from `enhanced_ml_A_xgboost`.

**Three reforms needed:**
1. **Backtest differently** — regime-conditional, shorter windows, purged CV, out-of-sample decay test
2. **Expand universe** — add high-volume symbols being missed, symbol-lock profitable edges
3. **Deploy mutations at scale** — inverse the top 10 losers, symbol-restrict strategies, TP/SL mutations

---

## 1. Backtesting Reform

### Problem: Current backtesting doesn't predict live performance

Walk-forward validation: **0/5 strategies pass anti-overfit**. ML-enhanced strategies show -13 to -33pp WR drift from backtest to live. The 60-day training window captures one regime that's stale by trade time.

### Fix A: Regime-Conditional Backtesting

**Instead of training on 60 days of all data, train only on data from matching regime.**

The `regime_detector.py` already classifies markets into TRENDING_UP, TRENDING_DOWN, CHOPPY, HIGH_VOLATILITY, CRISIS. Use this to filter training data:

```python
def regime_conditional_backtest(strategy, symbol, current_regime):
    """Only backtest on historical periods where regime matches current."""
    all_bars = load_ohlcv(symbol, days=365)
    
    # Classify regime for each 14-day window
    regime_labels = []
    for i in range(len(all_bars) - 14):
        window = all_bars[i:i+14]
        regime = detect_regime(window)  # Uses existing regime_detector
        regime_labels.append(regime)
    
    # Filter: only keep bars where regime matches current
    matching_bars = [bar for bar, regime in zip(all_bars, regime_labels)
                     if regime == current_regime]
    
    if len(matching_bars) < 100:  # Not enough data
        return None
    
    return run_backtest(strategy, matching_bars)
```

**Expected impact:** Strategies that work in TRENDING_UP but fail in CHOPPY will only be activated during TRENDING_UP regimes, eliminating regime-mismatch losses.

### Fix B: Shorter Walk-Forward Windows

Current: 60-day train / 30-day test / 15-day step.  
**Proposed for crypto:** 14-day train / 7-day test / 3-day step.

Crypto regimes change every 2-4 weeks. A 60-day window spans 2+ regime changes, diluting signal.

### Fix C: Purged Cross-Validation with Embargo

The `purged_cv.py` exists but isn't wired into the promotion pipeline. Use it:

```python
# In promotion_gate.py, add:
from validation.purged_cv import PurgedKFoldCV

def validate_strategy_purged(strategy, data, n_splits=5, embargo_pct=0.01):
    """Walk-forward CV with purged samples to prevent leakage."""
    cv = PurgedKFoldCV(n_splits=n_splits, embargo_pct=embargo_pct)
    oos_results = []
    for train_idx, test_idx in cv.split(data):
        train, test = data.iloc[train_idx], data.iloc[test_idx]
        model = strategy.fit(train)
        predictions = model.predict(test)
        oos_results.append(evaluate(predictions, test))
    return aggregate_oos_results(oos_results)
```

### Fix D: Out-of-Sample Decay Test

Before promoting any strategy, require it to show stable or improving OOS performance across sequential test windows:

```python
def oos_decay_test(strategy, data, n_windows=4, window_days=7):
    """Reject if OOS WR decays across sequential windows."""
    window_results = []
    for i in range(n_windows):
        start = len(data) - (n_windows - i) * window_days
        end = start + window_days
        window = data.iloc[start:end]
        wr = backtest_wr(strategy, window)
        window_results.append(wr)
    
    # Reject if monotonically declining
    declines = sum(1 for i in range(1, len(window_results))
                   if window_results[i] < window_results[i-1])
    
    if declines >= n_windows - 1:  # All declining
        return False, "OOS WR monotonically declining"
    
    # Reject if last window is >10pp below first
    if window_results[-1] < window_results[0] - 10:
        return False, f"OOS decay: {window_results[0]:.1f}% → {window_results[-1]:.1f}%"
    
    return True, "Stable OOS performance"
```

---

## 2. Symbol Universe Reform

### Current state: concentrated and missing edges

| Asset | Symbols | Concentration | Problem |
|-------|---------|---------------|---------|
| CRYPTO | 120 | Top 5 = 31% of trades | BTCUSDT alone = 13.1% of all crypto trades |
| EQUITY | 74 | Top 5 = 22% | XOM/CVX winning but NIO/TSLA/NVDA losing |
| FOREX | 27 | Top 5 = 42% | Reasonable for forex |
| COMMODITY | 11 | Top 5 = 94% | Nearly entire universe in top 5 |

### Fix A: Symbol-Lock Profitable Edges

Some strategies work brilliantly on specific symbols but terribly on others. Create symbol-locked variants:

**`enhanced_ml_A_xgboost` — massive symbol divergence:**

| Symbol | Trades | WR | PnL | Action |
|--------|--------|-----|-----|--------|
| SEIUSDT | 10 | **90%** | +25% | **LOCK — only trade this** |
| TIAUSDT | 12 | **75%** | +21% | LOCK |
| ETCUSDT | 8 | **88%** | +19% | LOCK |
| TRXUSDT | 43 | **0%** | **-86%** | **BLACKLIST** |
| JTOUSDT | 30 | **0%** | **-60%** | BLACKLIST |
| ARBUSDT | 12 | 17% | -14% | BLACKLIST |

**Creating the mutation:**
```python
# In dna_mutation_engine.py or strategy_mutations.py
SYMBOL_LOCK_MUTATIONS = {
    'enhanced_ml_A_xgboost': {
        'allow': ['SEIUSDT', 'TIAUSDT', 'ETCUSDT', 'WLDUSDT'],
        'block': ['TRXUSDT', 'JTOUSDT', 'ARBUSDT', 'ALGOUSDT', 'FILUSDT'],
        'reason': 'Symbol-specific edge: 90% WR on SEI vs 0% on TRX'
    },
    'st_rsi_momentum_confluence': {
        'allow': ['APTUSDT', 'ETHUSDT', 'SOLUSDT', 'ATOMUSDT'],
        'block': ['DOTUSDT', 'OPUSDT', 'ADAUSDT'],
        'reason': 'DOTUSDT 15% WR vs APTUSDT 73% WR'
    },
    'luxalgo_confluence': {
        'allow': ['DOTUSDT', 'JUPUSDT', 'AVAXUSDT', 'STXUSDT', 'XRPUSDT'],
        'block': ['ARBUSDT', 'ENAUSDT'],
        'reason': 'ARBUSDT 25% WR vs DOTUSDT 78% WR'
    },
    'st_bb_squeeze_expansion': {
        'block': ['TRXUSDT', 'LTCUSDT'],  # 20% and 25% WR
        'reason': 'Only BTCUSDT at 50% WR, rest losing'
    },
}
```

### Fix B: Expand Crypto Universe with Emerging Alts

Current universe has 120 symbols but many high-volume coins with clean price action are missing. The `universe_expander.py` exists — run it to discover:

- Layer-2 tokens with growing volume (OP, ARB already in — add STRK, MANTA, BLAST)
- AI narrative coins (FET, RENDER already in — verify AGIX, OCEAN coverage)
- RWA tokens (ONDO showing 0% WR on 8 trades — investigate or remove)
- DeFi blue chips (AAVE, UNI already in — add CRV, MKR if missing)

### Fix C: Equity Universe — Kill Losers, Add Value Winners

XOM (64.9% WR, +50%) and CVX (72.4% WR, +51%) are the clear equity winners. They're oil/energy. Meanwhile, NIO (-15.5%), TSLA (-21.1%), NVDA (-10.9%) are growth/momentum names that are failing.

**Proposal:** Split equity into sub-universes:
- **VALUE_ENERGY:** XOM, CVX, COP, etc. — strategies tuned for these
- **GROWTH_TECH:** TSLA, NVDA, etc. — pause until strategies improve
- **SMALL_CAP:** SPCE, CLOV — high vol, keep only if score ≥ 60

---

## 3. DNA Mutations at Scale

### Current mutation deployment: 99/3,500 = 2.8% of picks

The mutations that ARE running perform well:

| Mutation | Trades | WR | Total PnL |
|----------|--------|-----|-----------|
| claude_ml_moderate_mut | 30 | 60% | +26% |
| battleground_ml_relaxed_mut | 8 | 100% | +19% |
| battleground_vwap_1h_mut | 9 | 78% | +15% |
| battleground_rsi_no_regime_mut | 6 | 83% | +11% |
| inverse_ml_enhanced_ADA | 5 | 80% | +9% |

**The `_mut` strategies average 56% WR and are net profitable.** We need 10× more of them.

### Inverse Mutations — Top 10 Candidates

Every strategy below 40% WR is an inverse mutation candidate. Simple logic: if a strategy is a **consistent loser**, its inverse (flip direction, swap TP/SL) should be a **consistent winner**, minus transaction costs.

| Strategy | Trades | Orig WR | Inverse WR | Inverse PnL | Priority |
|----------|--------|---------|-----------|-------------|----------|
| **Value + Quality** | 48 | 6.2% | **93.8%** | **+243%** | **P0** |
| **enhanced_ml_A_xgboost** | 189 | 28.0% | **72.0%** | **+113%** | **P0** |
| **Consecutive Beats** | 39 | 25.6% | **74.4%** | **+72%** | P1 |
| **Earnings Drift** | 19 | 15.8% | **84.2%** | **+57%** | P1 |
| **ML Ranker** | 44 | 31.8% | **68.2%** | **+33%** | P1 |
| call-surge-scout | 12 | 16.7% | 83.3% | +25% | P2 |
| st_bb_squeeze_expansion | 52 | 28.8% | 71.2% | +26% | P2 |
| hh-hl-scout | 11 | 27.3% | 72.7% | +26% | P2 |
| community_london_breakout_v2_forex | 16 | 0.0% | **100.0%** | +8% | P2 |
| extreme_oversold_bounce | 14 | 14.3% | 85.7% | +15% | P2 |

**Caveat:** Inverse PnL is a theoretical max. Real inverse will be lower due to:
- Spread/slippage (~0.1-0.3% per trade)
- TP/SL geometry may not be symmetric
- Regime changes may break the anti-correlation

**Recommended approach:** Don't blindly inverse. Instead:
1. Paper-trade the inverse for 2 weeks (50+ trades)
2. Require inverse WR ≥ 55% on paper before going live
3. Apply tighter TP/SL on inverse (0.8× original distances)

### TP/SL Mutations

For strategies with decent WR (40-50%) but negative PnL, the problem is TP/SL geometry, not direction. Mutate the stops:

```python
TP_SL_MUTATIONS = {
    'tighter_60pct': {'tp_mult': 0.6, 'sl_mult': 0.6},  # Quick scalp exits
    'tight_tp_wide_sl': {'tp_mult': 0.7, 'sl_mult': 1.2},  # More room to be right
    'asymmetric_3to1': {'tp_mult': 1.5, 'sl_mult': 0.5},  # High RR
    'atr_trailing': {'use_trailing': True, 'trail_atr_mult': 1.5},
}
```

**Best candidates for TP/SL mutation (40-50% WR, negative avg PnL):**

| Strategy | WR | Avg PnL | Problem | Mutation |
|----------|-----|---------|---------|----------|
| volume_spike_breakout | 39% | +0.01% | WR decaying, exits too late | tighter_60pct |
| st_rsi_momentum_confluence (DOTUSDT) | 15% | -1.5% | Symbol-specific failure | Symbol-lock to winning syms |
| extreme_fear | 35% | -1.14% | Wrong timing | regime_gate (only in actual fear regime) |
| Short-Term Reversal | 38% | +0.19% | Barely positive, could flip | asymmetric_3to1 |

### Hybrid/Crossover Mutations

Combine the best elements of winning strategies with the signal generation of losing ones:

```python
CROSSOVER_MUTATIONS = [
    {
        'parent_strategy': 'enhanced_ml_A_xgboost',  # Losing: 28% WR
        'donor_strategy': 'st_fear_greed_contrarian',  # Winning: 81% WR
        'inherit': ['entry_timing', 'regime_filter'],  # Take regime awareness from donor
        'keep': ['ml_signal'],  # Keep ML signal from parent
        'name': 'xgboost_fear_greed_hybrid'
    },
    {
        'parent_strategy': 'st_bb_squeeze_expansion',  # Losing: 29% WR
        'donor_strategy': 'MeanReversionBB',  # Winning: 83% WR
        'inherit': ['tp_sl_levels', 'hold_duration'],
        'keep': ['entry_signal'],
        'name': 'bb_squeeze_meanrev_hybrid'
    },
]
```

---

## 4. Implementation Roadmap

### Phase 1 — Immediate symbol and strategy fixes (no code changes needed)

| # | Action | File | Impact |
|---|--------|------|--------|
| 1 | Add TRXUSDT and JTOUSDT to `BLOCKED_SYMBOLS` | `config.py` or symbol blocklist | Saves -146% PnL from xgboost alone |
| 2 | Symbol-lock `enhanced_ml_A_xgboost` to winning symbols only | `strategy_mutations.py` | Converts -113% loser to est. +65% winner |
| 3 | Symbol-lock `st_rsi_momentum_confluence` away from DOTUSDT | `strategy_mutations.py` | Saves -31% from DOTUSDT |
| 4 | Symbol-lock `luxalgo_confluence` away from ARBUSDT/ENAUSDT | `strategy_mutations.py` | Saves -31% |
| 5 | Symbol-lock `st_bb_squeeze_expansion` away from TRXUSDT | `strategy_mutations.py` | Saves -13% |

### Phase 2 — Deploy inverse mutations (1-2 days)

| # | Action | Expected Gain |
|---|--------|---------------|
| 6 | Inverse `Value + Quality` → paper trade 2 weeks | +243% (theoretical max) |
| 7 | Inverse `enhanced_ml_A_xgboost` (symbol-locked to TRXUSDT/JTOUSDT) | +146% |
| 8 | Inverse `Consecutive Beats` | +72% |
| 9 | Inverse `Earnings Drift` | +57% |
| 10 | Inverse `community_london_breakout_v2_forex` (0% WR → flip) | +8% |

### Phase 3 — Backtest infrastructure reform (1 week)

| # | Action |
|---|--------|
| 11 | Implement regime-conditional backtesting |
| 12 | Shorten walk-forward to 14d/7d/3d for crypto |
| 13 | Wire purged CV into promotion gate |
| 14 | Add OOS decay test as promotion requirement |
| 15 | Require 100+ forward trades before promotion (up from 10) |

### Phase 4 — Universe expansion (ongoing)

| # | Action |
|---|--------|
| 16 | Run `universe_expander.py` to discover missing high-volume symbols |
| 17 | Split equity universe into VALUE_ENERGY vs GROWTH_TECH |
| 18 | Add sub-universe routing: strategy X only trades universe Y |
| 19 | Dynamic universe rotation based on 30-day momentum + volume |

---

## 5. Summary: What Changes

| Area | Current | Proposed |
|------|---------|----------|
| **Backtesting** | 60d window, all regimes | 14d regime-conditional, purged CV, decay test |
| **Promotion gate** | 10 trades, 50% WR | 100 trades, stable OOS, decay-tested |
| **Mutations** | 99/3,500 picks (2.8%) | Target 30%+ picks through mutations |
| **Inverse** | 5 inverse variants running | 10+ inverse mutations of top losers |
| **Symbol universe** | 120 crypto (concentrated) | Symbol-locked per strategy, expanded to 150+ |
| **Symbol blocks** | None per-strategy | TRXUSDT/JTOUSDT blocked from xgboost; DOTUSDT from RSI confluence |
| **Strategy count** | 658 files, many dead | Cull to <100 active, rest archived |

---

*Generated 2026-04-12 from analysis of 3,500 closed picks, 658 strategy files, walk-forward results, forward test state, and DNA mutation registry.*
