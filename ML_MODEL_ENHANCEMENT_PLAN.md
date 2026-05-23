# 🔬 ML CRYPTO PREDICTOR — MODEL ENHANCEMENT PLAN
## Comprehensive Review & Upgrade Roadmap
**Date:** February 22, 2026  
**Model Version:** v2.0 (production_engine.py)  
**Current Forward Performance:** 18% WR (2W/9L), -$455 PnL  
**Backtest Performance:** 58.8% WR, Sharpe 1.34, PF 2.52  

---

## 📊 CURRENT MODEL AUDIT

### What We Have (production_engine.py)
| Component | Current Implementation | Assessment |
|-----------|----------------------|------------|
| **Models** | RF (200 trees) + GBT (200 trees), 0.4/0.6 weighted | ⚠️ No XGBoost, no LightGBM, no hyperparameter tuning |
| **Features** | 60+ features: EMAs, RSI, MACD, ATR, BB, Volume | ⚠️ All OHLCV-derived — no external data sources |
| **Walk-Forward** | 720-bar train / 120-bar test / 120-bar step | ✅ Good — prevents look-ahead bias |
| **TP/SL** | 3% TP / -1.5% SL / 48h max hold | ⚠️ Static — not adaptive per-pair or regime |
| **Regime Detection** | EMA50/EMA200 ratio + ADX | ⚠️ Basic — no HMM, no volatility regimes |
| **Confidence** | Fixed 0.60 threshold | ⚠️ No calibration, no Platt scaling |
| **Continuous Learning** | Retrains nightly on resolved picks | ✅ Good — but only performance data, not expanded training |
| **Feature Selection** | RF feature importance (top 15) | ⚠️ No SHAP, no alpha decay tracking |
| **Data Quality** | Basic NaN forward-fill | ❌ No outlier detection, no validation pipeline |
| **Position Sizing** | Max 8 positions, equal weight | ❌ No Kelly, no risk parity, no volatility-adjusted sizing |

### Why Backtest ≠ Forward (Root Causes)
1. **Overfitting to OHLCV patterns** — The model only sees price/volume. Real markets are driven by sentiment, on-chain flows, macro events, and correlations that OHLCV alone cannot capture.
2. **Static TP/SL** — 3% TP / -1.5% SL works well in backtest's moderate-volatility windows, but forward markets have different volatility regimes where these levels are wrong.
3. **No regime awareness** — The EMA50/200 crossover is too slow (200 bars = 8+ days lag). The model trades in choppy/bear regimes where it shouldn't.
4. **Train window too short** — 720 bars (30 days) is insufficient selection pressure. The model memorizes recent patterns that don't persist.
5. **No feature selection optimization** — All 60+ features are used with equal opportunity. Many are noisy, correlated, or stale.
6. **Fixed ensemble weights** — 0.4 RF + 0.6 GBT never changes. Some pairs favor RF, others GBT.

---

## 🚀 ENHANCEMENT PLAN (12 Upgrades, Prioritized)

### TIER 1: HIGH-IMPACT, MODERATE EFFORT (Implement This Week)
*These directly address the backtest-forward gap*

---

#### 🔧 Enhancement 1: VOLATILITY-BASED REGIME DETECTION
**Source:** Researcher 029 (Dr. Anna Petrova — Regime Detection Specialist), Researcher 010 (Dr. Michael Zhang — Alpha Decay)  
**Impact:** ★★★★★ | **Effort:** ★★☆☆☆ | **Priority:** IMMEDIATE

**Problem:** The current EMA50/200 regime indicator lags by 8+ days. The model enters trades in bear/choppy markets where the edge doesn't exist.

**Solution:** Implement a 3-state volatility-based regime classifier using free, readily available data:
```python
def classify_regime(close, high, low, volume):
    """
    Classify current market into 4 regimes using simple thresholds.
    Based on Researcher 029's finding: volatility-based regimes have 75% accuracy.
    """
    ret_30d = (close.iloc[-1] / close.iloc[-30] - 1) * 100 if len(close) >= 30 else 0
    vol_30d = close.pct_change().tail(30).std() * np.sqrt(24) * 100  # annualized hourly
    
    if vol_30d > 60:
        return 'HIGH_VOL'       # Don't trade — too chaotic
    elif ret_30d > 15:
        return 'BULL'           # Trade aggressively
    elif ret_30d < -15:
        return 'BEAR'           # Don't trade (long-only system)
    else:
        return 'SIDEWAYS'       # Trade with tighter SL
```

**Action Items:**
- [ ] Add `regime_current` as a feature in `build_production_features()`
- [ ] In `generate_live_picks()`, SKIP trades when regime == HIGH_VOL or BEAR
- [ ] Adjust TP/SL dynamically: BULL = wider TP, SIDEWAYS = tighter SL
- [ ] Track regime at pick creation time for later analysis

**Expected Impact:** Filter out 30-40% of losing trades that occur in unfavorable regimes.

---

#### 🔧 Enhancement 2: ADAPTIVE ATR-BASED TP/SL PER PAIR
**Source:** Researcher 009 (Market Microstructure), Alpha Engine `_atr_tp_sl()` function  
**Impact:** ★★★★★ | **Effort:** ★★☆☆☆ | **Priority:** IMMEDIATE

**Problem:** Static 3% TP / -1.5% SL doesn't account for the fact that BTC and SHIB have wildly different volatility profiles. A 3% move on BTC takes days; on a small-cap altcoin, it can happen in hours.

**Solution:** Replace static TP/SL with ATR-multiples:
```python
def adaptive_tpsl(close, high, low, regime='SIDEWAYS'):
    atr = compute_atr(high, low, close, period=14)
    current_atr = atr.iloc[-1]
    current_price = close.iloc[-1]
    atr_pct = current_atr / current_price
    
    # Regime-adjusted multipliers
    if regime == 'BULL':
        tp_mult, sl_mult = 3.0, 1.5    # Let winners run
    elif regime == 'SIDEWAYS':
        tp_mult, sl_mult = 2.0, 1.0    # Tighter targets
    else:
        tp_mult, sl_mult = 1.5, 0.75   # Very conservative
    
    tp_price = current_price + tp_mult * current_atr
    sl_price = current_price - sl_mult * current_atr
    return tp_price, sl_price
```

**Action Items:**
- [ ] Replace static `CONFIG['tp_pct']` and `CONFIG['sl_pct']` with adaptive per-pair values
- [ ] Store ATR in pick metadata for post-trade analysis
- [ ] Update `build_target_tpsl()` to use adaptive levels during backtest too (critical!)

**Expected Impact:** Better R:R per trade; fewer premature SL hits on volatile pairs, fewer time-expiry exits on calm pairs.

---

#### 🔧 Enhancement 3: ADD XGBOOST + LIGHTGBM + OPTUNA TUNING
**Source:** Researcher 011 (Dr. Priya Sharma — HPO Specialist), Multiple research sources  
**Impact:** ★★★★☆ | **Effort:** ★★★☆☆ | **Priority:** HIGH

**Problem:** Current RF + GBT with hardcoded hyperparameters. XGBoost typically outperforms both on tabular data. No hyperparameter optimization = leaving performance on the table.

**Solution:**
```python
import xgboost as xgb
import lightgbm as lgb
import optuna

def tune_xgboost(X_train, y_train, X_val, y_val, n_trials=50):
    """Optuna TPE search for XGBoost hyperparameters."""
    def objective(trial):
        params = {
            'max_depth': trial.suggest_int('max_depth', 4, 12),
            'n_estimators': trial.suggest_int('n_estimators', 100, 500),
            'learning_rate': trial.suggest_float('lr', 1e-3, 0.3, log=True),
            'subsample': trial.suggest_float('subsample', 0.6, 1.0),
            'colsample_bytree': trial.suggest_float('colsample', 0.6, 1.0),
            'min_child_weight': trial.suggest_int('min_child', 1, 10),
            'reg_alpha': trial.suggest_float('alpha', 1e-5, 10, log=True),
            'reg_lambda': trial.suggest_float('lambda', 1e-5, 10, log=True),
            'scale_pos_weight': (1 - y_train.mean()) / (y_train.mean() + 1e-10),
        }
        model = xgb.XGBClassifier(**params, random_state=42, eval_metric='logloss')
        model.fit(X_train, y_train, eval_set=[(X_val, y_val)], 
                  early_stopping_rounds=20, verbose=False)
        from sklearn.metrics import f1_score
        preds = model.predict(X_val)
        return f1_score(y_val, preds)
    
    study = optuna.create_study(direction='maximize')
    study.optimize(objective, n_trials=n_trials, show_progress_bar=True)
    return study.best_params
```

**Action Items:**
- [ ] Add `xgboost` and `lightgbm` to requirements.txt
- [ ] Run 50-trial Optuna TPE on each pair during nightly retrain (budget: ~15 min per pair)
- [ ] Save best params per pair in `production_models/`
- [ ] Expand ensemble to 4 models: RF + GBT + XGB + LGBM with learned weights

**Expected Impact:** 3-8% improvement in prediction accuracy based on Researcher 011's findings.

---

#### 🔧 Enhancement 4: SHAP-BASED FEATURE SELECTION
**Source:** Researcher 015 (Dr. Jennifer Liu — Explainable AI Specialist)  
**Impact:** ★★★★☆ | **Effort:** ★★☆☆☆ | **Priority:** HIGH

**Problem:** All 60+ features are used. Many are correlated (e.g., `rsi_7`, `rsi_14`, `rsi_21` move together). Noisy features reduce model accuracy.

**Solution:**
```python
import shap

def select_features_shap(model, X_train, top_k=30):
    """Select top K features using SHAP TreeExplainer."""
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_train[:500])  # sample for speed
    
    # Mean absolute SHAP value per feature
    importance = np.abs(shap_values).mean(axis=0)
    feature_importance = dict(zip(X_train.columns, importance))
    
    # Sort and select top K
    sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
    top_features = [f[0] for f in sorted_features[:top_k]]
    
    # Also check for redundant features (correlation > 0.8)
    corr_matrix = X_train[top_features].corr().abs()
    to_drop = set()
    for i in range(len(top_features)):
        for j in range(i+1, len(top_features)):
            if corr_matrix.iloc[i, j] > 0.8:
                # Drop the one with lower SHAP importance
                if feature_importance[top_features[i]] < feature_importance[top_features[j]]:
                    to_drop.add(top_features[i])
                else:
                    to_drop.add(top_features[j])
    
    return [f for f in top_features if f not in to_drop]
```

**Action Items:**
- [ ] Add `shap` to requirements.txt
- [ ] After training, compute SHAP values on validation set
- [ ] Select top 30 features, dropping correlated pairs
- [ ] Store selected features per pair (different pairs may need different features)
- [ ] Log SHAP drift monthly to detect concept drift

**Expected Impact:** Reduced noise → 2-5% accuracy improvement; also makes the model more interpretable for failure analysis.

---

### TIER 2: HIGH-IMPACT, HIGHER EFFORT (Implement This Month)
*These add new data sources and more sophisticated analysis*

---

#### 🔧 Enhancement 5: FEAR & GREED INDEX AS FEATURE
**Source:** Researcher 008 (Social Sentiment), Alpha Engine `crypto_fear_greed_contrarian()`  
**Impact:** ★★★★☆ | **Effort:** ★☆☆☆☆ | **Priority:** HIGH

**Problem:** Model only sees OHLCV. The Fear & Greed Index is free and has proven 58-68% directional accuracy as a contrarian indicator.

**Solution:** Add Free APIs to feature pipeline:
```python
def get_fear_greed():
    """Fetch Bitcoin Fear & Greed Index (free, no API key needed)."""
    import urllib.request, json
    url = "https://api.alternative.me/fng/?limit=30&format=json"
    try:
        data = json.loads(urllib.request.urlopen(url, timeout=10).read())
        values = [int(d['value']) for d in data['data']]
        return {
            'fg_current': values[0],               # 0-100 scale
            'fg_7d_avg': np.mean(values[:7]),
            'fg_30d_avg': np.mean(values[:30]),
            'fg_extreme_fear': int(values[0] < 25),  # Binary: extreme fear
            'fg_extreme_greed': int(values[0] > 75), # Binary: extreme greed
            'fg_divergence': int(values[0] < 30 and ret_30d > 0),  # Price up but fear
        }
    except: return {}
```

**Action Items:**
- [ ] Fetch F&G data at training time and inference time
- [ ] Add as 6 new features to feature matrix
- [ ] Ensure 24h lag in training to prevent look-ahead

**Expected Impact:** Adds macro-level market context that OHLCV alone can't capture.

---

#### 🔧 Enhancement 6: MULTI-TIMEFRAME FEATURES
**Source:** Strategy Comparison Matrix (§6.2), Researcher 029, Alpha Engine patterns  
**Impact:** ★★★★☆ | **Effort:** ★★★☆☆ | **Priority:** HIGH

**Problem:** Current model uses only 1h bars. Many successful strategies (FVG, Ichimoku, trend following) work best with multi-timeframe confirmation. The failure analysis found FVG entries fail when the 4h trend is against us.

**Solution:** Resample 1h data to 4h and daily, compute trend features at each:
```python
def build_multitimeframe_features(df_1h):
    """Build features from 1h, 4h, and daily timeframes."""
    feat = {}
    
    # 4h aggregation
    df_4h = df_1h.resample('4h', on='timestamp').agg({
        'open': 'first', 'high': 'max', 'low': 'min',
        'close': 'last', 'volume': 'sum'
    }).dropna()
    
    # Daily aggregation
    df_1d = df_1h.resample('1D', on='timestamp').agg({
        'open': 'first', 'high': 'max', 'low': 'min',
        'close': 'last', 'volume': 'sum'
    }).dropna()
    
    # 4h trend
    ema20_4h = df_4h['close'].ewm(span=20).mean()
    ema50_4h = df_4h['close'].ewm(span=50).mean()
    feat['htf_4h_trend'] = int(ema20_4h.iloc[-1] > ema50_4h.iloc[-1])
    feat['htf_4h_rsi'] = compute_rsi(df_4h['close'], 14).iloc[-1]
    
    # Daily trend
    ema20_d = df_1d['close'].ewm(span=20).mean()
    ema50_d = df_1d['close'].ewm(span=50).mean()
    feat['htf_daily_trend'] = int(ema20_d.iloc[-1] > ema50_d.iloc[-1])
    feat['htf_daily_rsi'] = compute_rsi(df_1d['close'], 14).iloc[-1]
    
    # Alignment score: how many timeframes agree on direction
    feat['htf_alignment'] = sum([
        feat['htf_4h_trend'], feat['htf_daily_trend'],
        int(df_1h['close'].iloc[-1] > df_1h['close'].ewm(span=50).mean().iloc[-1])
    ])  # 0-3 scale
    
    return feat
```

**Action Items:**
- [ ] Resample 1h data to 4h and 1D in `build_production_features()`
- [ ] Add 6-8 HTF features (trend direction, RSI, alignment score)
- [ ] CRITICAL: Use `htf_alignment >= 2` as a pre-filter for entry (all timeframes must agree)
- [ ] This directly fixes the FVG failure case identified in failure analysis

**Expected Impact:** Prevents 40-50% of counter-trend entries. This is the #1 fix recommended by failure analysis.

---

#### 🔧 Enhancement 7: PROBABILITY CALIBRATION (Platt Scaling)
**Source:** Researcher 011, sklearn documentation  
**Impact:** ★★★☆☆ | **Effort:** ★★☆☆☆ | **Priority:** MEDIUM

**Problem:** The model outputs raw probabilities that aren't well-calibrated. A "60% probability" doesn't mean it wins 60% of the time. This makes the confidence tiers unreliable.

**Solution:**
```python
from sklearn.calibration import CalibratedClassifierCV

# During training, wrap the model with Platt scaling
rf_calibrated = CalibratedClassifierCV(rf, method='sigmoid', cv=3)
rf_calibrated.fit(X_train_s, y_train)

gbt_calibrated = CalibratedClassifierCV(gbt, method='isotonic', cv=3)
gbt_calibrated.fit(X_train_s, y_train)
```

**Action Items:**
- [ ] Wrap RF and GBT with `CalibratedClassifierCV` during training
- [ ] Use `sigmoid` method for RF, `isotonic` for GBT
- [ ] Calibrate on a held-out portion of training data (not test!)
- [ ] Validate calibration with reliability diagrams

**Expected Impact:** More meaningful confidence scores → better trade selection → fewer false positives.

---

#### 🔧 Enhancement 8: PURGED K-FOLD CROSS-VALIDATION
**Source:** Researcher 011, López de Prado "Advances in Financial ML"  
**Impact:** ★★★★☆ | **Effort:** ★★★☆☆ | **Priority:** MEDIUM

**Problem:** Standard walk-forward can have leakage if training and test windows overlap in their look-ahead period (TP/SL requires looking 48 bars forward). If bar N is in training and bar N+48 is in the gap, there's leakage.

**Solution:**
```python
def purged_walk_forward(X, y, pnl, train_w, test_w, step, purge_bars=48):
    """Walk-forward with purge gap to prevent lookahead leakage."""
    for start in range(0, len(X) - train_w - test_w - purge_bars, step):
        train_end = start + train_w
        test_start = train_end + purge_bars  # PURGE GAP
        test_end = test_start + test_w
        
        X_train = X.iloc[start:train_end]
        y_train = y.iloc[start:train_end]
        X_test = X.iloc[test_start:test_end]
        y_test = y.iloc[test_start:test_end]
        
        yield X_train, y_train, X_test, y_test
```

**Action Items:**
- [ ] Add `purge_bars=48` gap between train and test
- [ ] Also add embargo: exclude last `purge_bars` of each training fold
- [ ] Re-run backtest with purged validation to get honest performance estimate

**Expected Impact:** More honest backtest results. May lower backtest WR from 58.8% to ~50-52%, but forward performance should converge closer.

---

### TIER 3: MEDIUM-IMPACT, HIGHER EFFORT (Implement Next Month)

---

#### 🔧 Enhancement 9: ON-CHAIN DATA INTEGRATION (Free Sources)
**Source:** Researcher 007 (Dr. Yuki Tanaka — On-Chain Analytics)  
**Impact:** ★★★☆☆ | **Effort:** ★★★★☆ | **Priority:** MEDIUM

**Problem:** Model has zero visibility into blockchain fundamentals. On-chain metrics like exchange netflows, active addresses, and MVRV have proven 58-60% directional accuracy.

**Free Data Sources:**
- CoinGecko API (free tier): market cap, volume, supply changes
- Blockchain.com API (free): BTC active addresses, hash rate
- Alternative.me: Fear & Greed Index (already in Enhancement 5)
- Mempool.space API (free): BTC mempool, fee estimates

**Action Items:**
- [ ] Integrate CoinGecko market data (market_cap, total_volume, supply changes)
- [ ] Add BTC-wide indicators as features for all pairs (BTC dominance, total market cap)
- [ ] Lag all on-chain features by 24h to prevent look-ahead bias
- [ ] Start simple: 5-8 on-chain features, validate impact before adding more

---

#### 🔧 Enhancement 10: CORRELATION GUARD (Anti-Concentration)
**Source:** Failure Analysis (identified as ❌ CANNOT SELF-FIX), Researcher 025 (Portfolio Optimization)  
**Impact:** ★★★☆☆ | **Effort:** ★★☆☆☆ | **Priority:** MEDIUM

**Problem:** Multiple strategies can generate picks on the same asset simultaneously. If BTC drops, 3 correlated BTC picks all lose together = triple the expected loss.

**Solution:**
```python
class CorrelationGuard:
    """Prevents concentration risk across strategies."""
    
    MAX_POSITIONS_PER_ASSET = 1
    COOLDOWN_AFTER_LOSS = 72  # hours
    MAX_CORRELATED_POSITIONS = 3  # max positions in correlated assets
    
    def __init__(self, active_picks, closed_picks):
        self.active = active_picks
        self.closed = closed_picks
        self.recent_losses = self._get_recent_losses()
    
    def can_enter(self, symbol, strategy):
        # Rule 1: Max 1 position per asset
        active_on_symbol = sum(1 for p in self.active if p['symbol'] == symbol)
        if active_on_symbol >= self.MAX_POSITIONS_PER_ASSET:
            return False, "MAX_POSITIONS_PER_ASSET exceeded"
        
        # Rule 2: Cooldown after loss
        for loss in self.recent_losses:
            if loss['symbol'] == symbol:
                hours_since = (datetime.utcnow() - loss['exit_time']).total_seconds() / 3600
                if hours_since < self.COOLDOWN_AFTER_LOSS:
                    return False, f"COOLDOWN: {symbol} lost {hours_since:.0f}h ago"
        
        return True, "OK"
```

**Action Items:**
- [ ] Build CorrelationGuard module
- [ ] Integrate into `generate_live_picks()` as a pre-filter
- [ ] Track "blocked picks" for later analysis (were they actually losers?)
- [ ] Add BTC-ETH correlation: if already long BTC, reduce ETH position size

---

#### 🔧 Enhancement 11: PER-STRATEGY MODEL EVALUATION
**Source:** Current performance data, Researcher 010 (Alpha Decay)  
**Impact:** ★★★☆☆ | **Effort:** ★★☆☆☆ | **Priority:** MEDIUM

**Problem:** Currently the model trains one ensemble per pair. But some strategies consistently fail (BTC_RSI_DIVERGENCE = 0W/3L) while others may have an edge. We treat all signals equally.

**Solution:** Track and weight strategies by forward performance:
```python
def compute_strategy_weights(closed_picks):
    """Weight strategies by their forward performance."""
    strategy_stats = {}
    for p in closed_picks:
        strat = p.get('strategy', 'unknown')
        if strat not in strategy_stats:
            strategy_stats[strat] = {'wins': 0, 'losses': 0, 'pnl': 0}
        if p['status'] == 'WON':
            strategy_stats[strat]['wins'] += 1
        else:
            strategy_stats[strat]['losses'] += 1
        strategy_stats[strat]['pnl'] += p.get('pnl_pct', 0)
    
    # Weight = win_rate if 10+ trades, else 0.5 (neutral)
    weights = {}
    for strat, stats in strategy_stats.items():
        total = stats['wins'] + stats['losses']
        if total >= 10:
            weights[strat] = stats['wins'] / total
        else:
            weights[strat] = 0.5  # insufficient data
    
    return weights
```

**Action Items:**
- [ ] Track strategy name in all picks
- [ ] After 10+ resolved picks per strategy, compute forward WR
- [ ] Suspend strategies with 0% WR after 10+ trades
- [ ] Weight ensemble predictions by strategy WR

---

#### 🔧 Enhancement 12: LONGER TRAINING WINDOWS + DATA AUGMENTATION
**Source:** Researcher 016 (Data Quality), Research findings on overfitting  
**Impact:** ★★★☆☆ | **Effort:** ★★☆☆☆ | **Priority:** LOW

**Problem:** 720 bars (30 days) training window is too short. The model memorizes recent noise. Need at least 3-6 months of data.

**Solution:**
```python
CONFIG = {
    'train_window_bars': 2160,   # 90 days (was 30 days)
    'test_window_bars': 240,     # 10 days (was 5 days)
    'step_bars': 240,            # slide every 10 days
}
```

Also add data augmentation:
- Add Gaussian noise (σ = 0.5 × ATR) to training data to reduce overfitting
- Oversample winning trades (currently rare class) using SMOTE
- Create synthetic "near-miss" samples (trades that almost hit TP)

**Action Items:**
- [ ] Increase training window to 2160 bars (90 days)
- [ ] Increase test window to 240 bars (10 days)
- [ ] Add `imblearn.over_sampling.SMOTE` for class balancing
- [ ] Experiment with noise augmentation on training features

---

## 📋 IMPLEMENTATION STATUS (Updated Feb 22, 2026 — v3.1)

| # | Enhancement | Impact | Effort | Status | Notes |
|---|------------|--------|--------|--------|-------|
| **1** | Volatility Regime Detection | ★★★★★ | ★★☆☆☆ | ✅ **v3.0** | 4-state: BULL/BEAR/SIDEWAYS/HIGH_VOL |
| **2** | Adaptive ATR TP/SL | ★★★★★ | ★★☆☆☆ | ✅ **v3.0** | Regime-adjusted ATR multiples (1.5-3.0× TP, 0.75-1.5× SL) |
| **3** | XGBoost Ensemble | ★★★★☆ | ★★★☆☆ | ✅ **v3.1** | 3-model: RF 25% + GBT 35% + XGB 40% (graceful fallback) |
| **4** | SHAP Feature Selection | ★★★★☆ | ★★☆☆☆ | ✅ **v3.1** | SHAP TreeExplainer top 20 features (fallback to RF importance) |
| **5** | Fear & Greed Index | ★★★★☆ | ★☆☆☆☆ | ✅ **v3.0** | 6 features from free API, injected at inference |
| **6** | Multi-Timeframe Features | ★★★★☆ | ★★★☆☆ | ✅ **v3.0** | 4h + daily trend/RSI + alignment score (0-3) |
| **7** | Probability Calibration | ★★★☆☆ | ★★☆☆☆ | ✅ **v3.1** | Platt (RF) + Isotonic (GBT) CalibratedClassifierCV |
| **8** | Purged Walk-Forward | ★★★★☆ | ★★★☆☆ | ✅ **v3.0** | 48-bar purge gap between train and test sets |
| **10** | Correlation Guard | ★★★☆☆ | ★★☆☆☆ | ✅ **v3.0** | Max 1 pos/asset + 72h cooldown after loss |
| **12** | Longer Train Windows | ★★★☆☆ | ★★☆☆☆ | ✅ **v3.0** | 90-day train (2160 bars) + 10-day test (240 bars) |
| **—** | Feature Correlation Cleanup | ★★★☆☆ | ★☆☆☆☆ | ✅ **v3.1** | Drops features with r>0.9 correlation |
| **9** | On-Chain Data (CoinGecko) | ★★★☆☆ | ★★★★☆ | ✅ **v3.1** | BTC dominance, market cap, per-coin metrics via API |
| **11** | Per-Strategy Evaluation | ★★★☆☆ | ★★☆☆☆ | ✅ **v3.1** | Per-pair forward WR tracking + auto-suspend at 0% after 5 trades |

### Metric Labeling (v3.0+)
All metrics in the JSON output and dashboard are now explicitly labeled:
- **`forward_*`** — Real performance from live resolved picks (e.g., `forward_win_rate`, `forward_total_pnl`)
- **`backtest_*`** — Historical validation metrics (e.g., `backtest_win_rate`, `backtest_profit_factor`)
- Each pick also carries `backtest_validation` metadata showing the pair's historical performance

---

## 📈 EXPECTED PERFORMANCE AFTER ALL ENHANCEMENTS

| Metric | Current | After Tier 1 | After Tier 2 | After All |
|--------|---------|-------------|-------------|-----------|
| **Forward WR** | 18% | 30-35% | 38-42% | 42-48% |
| **Profit Factor** | < 1.0 | 1.0-1.3 | 1.3-1.6 | 1.5-2.0 |
| **Backtest WR** | 58.8% | 52-55% | 50-53% | 48-52% |
| **BT-Forward Gap** | 40.8% | 17-25% | 8-15% | < 10% |
| **Monthly P&L** | -$455 | Breakeven | +$200-500 | +$500-1000 |

**Key Insight:** The goal is NOT to improve backtest WR. It's to REDUCE the gap between backtest and forward. A 48% backtest WR that holds at 45% forward is infinitely better than 58% backtest / 18% forward.

---

## 🔗 RESEARCHER REFERENCES USED

| Researcher | Topic | Key Contribution Used |
|------------|-------|-----------------------|
| #007 Dr. Tanaka | On-Chain Analytics | MVRV, NUPL, exchange netflow features |
| #008 Dr. Rodriguez | Social Sentiment | Sentiment divergence signal, F&G integration |
| #009 Dr. Petrov | Market Microstructure | Volume imbalance, bid-ask spread dynamics |
| #010 Dr. Zhang | Alpha Decay | Alpha half-life tracking, feature retirement |
| #011 Dr. Sharma | HPO | Optuna TPE, 100 trials, PurgedKFold |
| #012 Dr. Wu | Reinforcement Learning | PPO for portfolio allocation (future work) |
| #013 Dr. Andersson | Transformer Models | PatchTST architecture (future work) |
| #015 Dr. Liu | Explainable AI | SHAP TreeExplainer, drift monitoring |
| #016 Dr. O'Brien | Data Quality | MAD outlier filter, validation pipeline |
| #018 Dr. Garcia | Feature Store | Point-in-time joins, online/offline consistency |
| #025 Dr. Miller | Portfolio Optimization | Kelly criterion, correlation-aware sizing |
| #029 Dr. Petrova | Regime Detection | Volatility-based regimes (75% accuracy) |

---

*Document compiled from analysis of 30 researcher profiles, current production engine code review, web research on latest crypto ML improvements, and forward performance failure analysis.*
*All enhancements are designed to work within the existing GitHub Actions infrastructure (no GPU required).*
