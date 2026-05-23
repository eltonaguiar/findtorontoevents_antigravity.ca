# Quantitative Forensic Review — Antigravity Multi-Asset Prediction System

**Date:** 2026-04-11  
**Reviewer:** Senior Quantitative Portfolio Manager (systematic trading)  
**Scope:** Full code & architecture audit, statistical diagnostics, feature/model evaluation, TP/SL & position-sizing blueprint, operational roadmap  
**Dataset:** 3,500 closed picks, 82 active picks, 658 Python modules in `alpha_engine/`, 30+ JSON data sources

---

## 1. Executive Summary

### Key Findings

This is an ambitious multi-asset systematic trading platform with solid infrastructure (walk-forward validation, promotion gates, Kelly sizing, regime detection, ATR-based TP/SL) — but **six structural issues** are destroying alpha:

1. **SHORT trades are a catastrophic PnL leak.** Crypto SHORT: 35.4% WR, PF 0.57, -126% PnL. Equity SHORT: 0% WR. Yet the system has no hard direction gate.
2. **Score < 50 picks should never trade.** Score is a genuine alpha predictor (CRYPTO B-tier: 83.1% WR vs D-tier: 46.0%), but the system publishes D/F-tier picks.
3. **Hold duration mismanagement.** Crypto's sweet spot is 4-24h (62-72% WR), but 306 picks exit in ≤1h (37.9% WR). Forex loses in the 1h-3d zone but the system doesn't enforce duration gates.
4. **TP/SL calibration is asset-class blind.** Fixed 2.5× / 1.5× ATR multipliers are applied uniformly. Equity SL_HIT alone destroyed -830% PnL. The MFE/MAE analyzer uses synthetic data (estimated MFE/MAE, not tick-level) making its "adaptive" outputs unreliable.
5. **Strategy zoo is unculled.** 658 Python files, 30+ source systems, but `Value + Quality` (6.2% WR, -243% on equity), `enhanced_ml_A_xgboost` (30.9% WR, -69% on crypto), and `TRXUSDT` (6.2% WR, -76%) persist.
6. **Risk controls are partially bypassed.** `is_daily_blocked` returns `False` always (line patched). Circuit breaker uses 7-day rolling PnL, not high-water-mark drawdown.

### Top 3 Recommendations

| Priority | Action | Expected Impact |
|----------|--------|----------------|
| **P0** | Hard gate: `direction == 'LONG'` for crypto; `score >= 50` for all | +20-35pp WR, saves 700%+ PnL bleed |
| **P1** | Duration-based exit logic: close crypto <1h, close forex 1h-3d positions at breakeven | +15pp WR on affected trades |
| **P2** | Asset-class-specific TP/SL multipliers derived from MFE/MAE percentiles with real kline data | Reduces SL_HIT frequency, lifts PF by est. 0.3-0.5 |

---

## 2. Code & Architecture Audit

### 2.1 Critical Bugs

| Issue | Location | Severity | Fix |
|-------|----------|----------|-----|
| **Daily block bypassed** | `risk_controls.py` → `is_daily_blocked`: `return False  # Patched to bypass` | 🔴 Critical | Remove bypass. Wire to actual daily PnL tracking. |
| **Kelly shrinkage uses `n_trades=100` default** | `position_sizing.py` — `get_kelly_fraction` called without actual trade count | 🟡 Medium | Pass real `closed_picks` count from strategy metadata. |
| **DSR threshold inconsistency** | `promotion_gate.py`: `dsr_threshold = 1.64` compared to `compute_deflated_sharpe` which returns CDF probability in [0,1] | 🔴 Critical | Change `dsr_threshold` to 0.95 (probability), or change `compute_deflated_sharpe` to return z-stat. |
| **MFE/MAE is synthetic** | `mfe_mae_analyzer.py`: winners MFE estimated as `|pnl|*100 + atr * hold_days * 0.2` | 🟡 Medium | Integrate real high/low from klines. Synthetic estimates hide true stop-out dynamics. |
| **Drawdown not HWM-based** | `risk_controls.py` circuit breaker uses 7d sum of realized PnL + unrealized | 🟡 Medium | Implement proper high-water-mark drawdown tracking on equity curve. |
| **`ConfluenceEngine` not wired by default** | `scanner.py`: requires `ALPHA_CONFLUENCE=1` env var | 🟡 Medium | Enable by default or A/B test. Cross-family confluence is a strong alpha signal. |

### 2.2 Anti-Patterns

| Pattern | Where | Issue |
|---------|-------|-------|
| **God file** | `scanner.py` (~4400 lines), `dashboard_generator.py` (~12000 lines), `elite_scorer.py` (~2500 lines) | Unmaintainable. Split by concern. |
| **Magic numbers everywhere** | TP/SL multipliers, score floors, confidence thresholds hardcoded in 10+ files | Consolidate into `config/trading_params.yaml`. |
| **Duplicate TP/SL logic** | `tp_sl_filler.py`, `tp_sl_optimizer.py`, inline in strategies, `mfe_mae_analyzer.py` | Single source of truth for TP/SL computation. |
| **No type hints on data dicts** | Picks are `dict` everywhere, no dataclass/TypedDict | Use `@dataclass` for Pick, Signal, etc. |
| **658 strategy files** | Many are experimental/dead | Audit and archive. Active production set should be <50 files. |

### 2.3 Reproducibility

| Aspect | Status | Action |
|--------|--------|--------|
| Version control | ✅ Git | — |
| Environment management | ⚠️ `requirements.txt` without pinned versions for some deps | Pin all versions. Add `pyproject.toml`. |
| Data versioning | ❌ JSON files in git, no DVC/S3 | Introduce DVC or timestamp-versioned JSON artifacts. |
| Experiment tracking | ❌ No MLflow/W&B | Add MLflow for model experiments. |
| Config management | ❌ Hardcoded constants | Move to YAML/JSON config with schema validation. |

---

## 3. Statistical & Financial Diagnostics

### 3.1 Risk-Adjusted Metrics by Asset Class (from closed picks)

| Asset | Trades | WR | PF | Avg PnL | Total PnL | Avg Win | Avg Loss | Win/Loss Ratio | Edge? |
|-------|--------|-----|-----|---------|-----------|---------|----------|---------------|-------|
| CRYPTO | 2,129 | 52.8% | 1.80 | +0.54% | +1,156% | +2.31% | -1.44% | 1.60 | ✅ Real edge |
| FOREX | 546 | 43.6% | 2.00 | +0.39% | +211% | +1.77% | -0.68% | 2.60 | ⚠️ Outlier-driven |
| EQUITY | 576 | 37.3% | 0.70 | -0.72% | -413% | +4.55% | -3.85% | 1.18 | ❌ Net loser |
| COMMODITY | 211 | 43.1% | 1.08 | +0.03% | +7% | +0.97% | -0.68% | 1.43 | ⚠️ Breakeven |
| BOND | 8 | 50.0% | 25.90 | +0.62% | +5% | +1.29% | -0.05% | 25.80 | ✅ Tiny sample |
| ETF | 15 | 33.3% | 0.21 | -1.48% | -22% | +1.16% | -2.80% | 0.41 | ❌ No edge |
| FUTURES | 15 | 6.7% | 0.08 | -6.27% | -94% | +8.60% | -7.33% | 1.17 | ❌ Catastrophic |

### 3.2 Tail Risk

**Crypto**: Max single-trade loss -23.82%, max win +34.40%. The `STOP_LOSS` exit reason averages -10.76% (6 trades) — indicating some SL levels are far too wide.

**Equity**: Max loss -20.74%, SL_HIT average -5.19% across 160 trades. This is where the PnL hemorrhage lives.

**FUTURES**: Single outlier of -87.89% (likely leveraged). This should have been caught by the -15% circuit breaker, but the daily block is bypassed.

### 3.3 Overfitting Assessment

| Signal | Evidence |
|--------|----------|
| **Score genuinely predicts** | Monotonic WR increase across score tiers in CRYPTO, EQUITY, ETF. Not overfit — works out-of-sample. |
| **Direction bias is real** | LONG >> SHORT in crypto across all time windows, not just backtest. |
| **Some strategies are curve-fit** | `enhanced_ml_A_xgboost`: 152 trades, 30.9% WR suggests training-set overfit or feature leakage. |
| **MFE/MAE "adaptive" is circular** | Uses estimated MFE (derived from pnl + atr), then "optimizes" TP/SL from it. Needs real excursion data. |
| **Promotion gate deflated Sharpe has a bug** | `dsr_threshold = 1.64` compared to probability output. Strategies may pass that shouldn't. |

---

## 4. Feature & Model Evaluation

### 4.1 Feature Quality

**Strong features (validated by out-of-sample):**

| Feature | Evidence |
|---------|----------|
| `score` (composite) | Monotonic WR/PF relationship across all asset classes. Strongest single predictor. |
| `direction` | LONG massively outperforms SHORT on crypto. Structural edge. |
| `hold_duration` | 4-24h sweet spot in crypto. ≤1h and >3d decay. Actionable. |
| `entry_time` (UTC hour) | 12-16 UTC is best for crypto (+452% PnL). 20-00 UTC is worst. |
| `rr_ratio` | 2.0-3.0 is optimal for crypto (56.1% WR, PF 2.99). |

**Suspect features:**

| Feature | Issue |
|---------|-------|
| `lstm_direction_prob` | No real LSTM — numpy approximation. Rename or implement properly. |
| `orderbook_imbalance` | Default 0 when unavailable. Most picks use default. Feature is noise for non-crypto. |
| `vpin_toxicity` | Default 0.5. Same issue — sparse real data. |
| `funding_rate_raw` | Crypto-only. Non-crypto defaults to 0. Creates multicollinearity with asset_class indicator. |

**Missing features that would add alpha:**

| Feature | Rationale | Implementation |
|---------|-----------|----------------|
| **Cross-asset momentum** | Crypto correlates with equity risk-on/off | S&P500 5d return, VIX level, DXY change |
| **Intraday volatility structure** | Morning vs afternoon vol predicts TP probability | Garman-Klass vol by session |
| **Options-implied vol skew** | For equities, put skew predicts drawdown | IVR, 25-delta skew from CBOE |
| **Funding rate z-score** | Raw rate is noisy; z-score relative to 30d history is signal | Rolling z-score |
| **On-chain whale flow** | BTC exchange inflow/outflow | Glassnode/CryptoQuant API |

### 4.2 Model Redundancy

| Component | Alpha Contribution | Recommendation |
|-----------|-------------------|----------------|
| `st_fear_greed_contrarian` | **Dominant**: 86.1% WR, PF 15.11, +506% | **Amplify** — this is the system's best edge |
| XGBoost ranker (`ml_ranker.py`) | Moderate: ranks picks reasonably but 30.9% WR on `enhanced_ml_A_xgboost` shows training issues | Retrain with purged CV. Drop correlated features. |
| `elite_scorer` Method C | Composite score is genuinely predictive | Keep but audit weight decay curves |
| LSTM "features" | Questionable: not a real LSTM | Replace with proper temporal model or drop |
| PPO RL (`ppo_micro_strategy.py`) | No evidence of live alpha contribution | Deprecate unless validated in walk-forward |
| CNN patterns | Minimal contribution | Deprecate |

---

## 5. TP/SL & Position-Sizing Blueprint

### 5.1 Current TP/SL Problems

The system uses **TP = 2.5 × ATR, SL = 1.5 × ATR** uniformly. This is inadequate:

| Asset | ATR-Based SL | Actual Avg Loss | Problem |
|-------|-------------|----------------|---------|
| CRYPTO | 1.5 × 3% = 4.5% | -1.44% (winners avg), -2.10% (SL_HIT avg) | SL too wide for scalps, ok for swings |
| EQUITY | 1.5 × 2% = 3.0% | -5.19% (SL_HIT avg) | SL hits are 2× wider than ATR target — price gaps |
| FOREX | 1.5 × 0.5% = 0.75% | -0.68% (avg loss) | Roughly calibrated |

### 5.2 Proposed TP/SL Framework

**Principle:** TP/SL should be derived from empirical MFE/MAE percentiles on real kline data, not synthetic estimates, with regime and timeframe adjustments.

**Step 1: Empirical Calibration**

```python
def compute_optimal_tp_sl(closed_picks: list, kline_data: dict) -> dict:
    """Derive TP/SL from actual MFE/MAE using intrabar high/low data."""
    results = {}
    for asset_class in ['CRYPTO', 'EQUITY', 'FOREX', 'COMMODITY']:
        ac_picks = [p for p in closed_picks 
                    if p.get('asset_class', '').upper() == asset_class]
        mfe_pcts = []  # Maximum Favorable Excursion
        mae_pcts = []  # Maximum Adverse Excursion
        
        for p in ac_picks:
            sym = p['symbol']
            entry = p['entry_price']
            direction = p.get('direction', 'LONG')
            entry_ts = parse_ts(p['timestamp'])
            exit_ts = parse_ts(p.get('closed_at'))
            
            if sym not in kline_data or not entry_ts or not exit_ts:
                continue
            
            bars = kline_data[sym]  # DataFrame with OHLC
            trade_bars = bars[(bars.index >= entry_ts) & (bars.index <= exit_ts)]
            
            if direction == 'LONG':
                mfe = (trade_bars['high'].max() - entry) / entry * 100
                mae = (entry - trade_bars['low'].min()) / entry * 100
            else:
                mfe = (entry - trade_bars['low'].min()) / entry * 100
                mae = (trade_bars['high'].max() - entry) / entry * 100
            
            mfe_pcts.append(max(0, mfe))
            mae_pcts.append(max(0, mae))
        
        if len(mfe_pcts) >= 20:
            results[asset_class] = {
                'tp_pct': np.percentile(mfe_pcts, 50),  # Median MFE
                'sl_pct': np.percentile(mae_pcts, 75),  # P75 MAE
                'tp_aggressive': np.percentile(mfe_pcts, 25),  # Tighter TP
                'sl_tight': np.percentile(mae_pcts, 50),       # Tighter SL
            }
    return results
```

**Step 2: Regime Multipliers (refined from tp_sl_optimizer.py)**

```python
REGIME_TP_SL_MULTIPLIERS = {
    'CRYPTO': {
        'TRENDING_UP':   {'tp_mult': 1.30, 'sl_mult': 1.15},  # Let winners run
        'TRENDING_DOWN': {'tp_mult': 0.60, 'sl_mult': 0.75},  # Quick exits
        'CHOPPY':        {'tp_mult': 0.75, 'sl_mult': 0.90},  # Tight targets
        'HIGH_VOLATILITY': {'tp_mult': 1.10, 'sl_mult': 1.30}, # Wider SL
        'CRISIS':        {'tp_mult': 0.50, 'sl_mult': 0.60},  # Minimal risk
    },
    'EQUITY': {
        'TRENDING_UP':   {'tp_mult': 1.20, 'sl_mult': 1.00},
        'TRENDING_DOWN': {'tp_mult': 0.50, 'sl_mult': 0.70},  # Equity gaps
        'CHOPPY':        {'tp_mult': 0.80, 'sl_mult': 0.85},
    },
    'FOREX': {
        'TRENDING_UP':   {'tp_mult': 1.15, 'sl_mult': 1.05},
        'TRENDING_DOWN': {'tp_mult': 1.15, 'sl_mult': 1.05},  # FX is bilateral
        'CHOPPY':        {'tp_mult': 0.70, 'sl_mult': 0.90},
    },
}
```

**Step 3: Multi-Tier Stop-Loss Hierarchy**

```python
def compute_stop_hierarchy(entry_price, direction, atr, score, regime):
    """Three-tier stop system."""
    sl_base = atr * SL_MULTIPLIERS[asset_class]  # From empirical calibration
    
    # Tier 1: Hard stop (never moved)
    hard_stop = entry_price - sl_base if direction == 'LONG' else entry_price + sl_base
    
    # Tier 2: Trailing stop (activates after 1× ATR profit)
    trailing_activation = 1.0 * atr  # Activate when price moves 1 ATR favorable
    trailing_distance = 1.5 * atr    # Trail at 1.5 ATR from high
    
    # Tier 3: Time-based exit
    # If position hasn't hit TP in max_hold_hours, exit at market
    max_hold = {
        'CRYPTO': 24,     # Based on 4-24h sweet spot
        'EQUITY': 168,    # 7 days
        'FOREX': 1,       # Scalp mode: 1h; swing mode: 168h
        'COMMODITY': 1,   # Scalp only
    }
    
    return {
        'hard_stop': hard_stop,
        'trailing_activation_pct': trailing_activation / entry_price * 100,
        'trailing_distance_pct': trailing_distance / entry_price * 100,
        'max_hold_hours': max_hold[asset_class],
    }
```

### 5.3 Position Sizing Reform

**Current issue:** Kelly with default `n=100` ignores actual strategy sample size. Drawdown governor uses 5% steps — too coarse.

**Proposed: Volatility-Scaled Kelly with Continuous Drawdown Decay**

```python
def compute_position_size_v2(
    kelly_fraction: float,
    strategy_trades: int,
    current_drawdown_pct: float,
    current_vol: float,
    target_vol: float = 0.15,
    max_position_pct: float = 0.05,
) -> float:
    """
    Position size = Kelly × uncertainty_shrinkage × vol_target × drawdown_decay
    
    Key changes from current:
    1. Real trade count in Kelly shrinkage (not default 100)
    2. Continuous drawdown decay (not 5% steps)
    3. Vol targeting to normalize risk across asset classes
    """
    # Baker-McHale shrinkage with REAL trade count
    p_hat = kelly_fraction  # Assuming this is already Kelly-computed
    if strategy_trades > 0:
        sigma = (p_hat * (1 - p_hat) / strategy_trades) ** 0.5
        shrinkage = max(0, 1 - sigma**2 / max(p_hat * (1 - p_hat), 1e-6))
    else:
        shrinkage = 0.1  # Nearly zero for unvalidated
    
    # Continuous drawdown decay: exp(-lambda * dd)
    # At 5% DD: 0.78×, at 10%: 0.61×, at 15%: 0.47×, at 20%: 0.37×
    lambda_dd = 5.0
    dd_multiplier = math.exp(-lambda_dd * abs(current_drawdown_pct) / 100)
    
    # Vol targeting
    vol_ratio = target_vol / max(current_vol, 0.01)
    vol_mult = min(max(vol_ratio, 0.25), 2.0)
    
    raw_size = kelly_fraction * shrinkage * dd_multiplier * vol_mult
    return min(raw_size, max_position_pct)
```

### 5.4 Per-Asset-Class TP/SL Recommendations (from data)

| Asset | TP Multiplier | SL Multiplier | RR Target | Max Hold | Notes |
|-------|--------------|--------------|-----------|----------|-------|
| CRYPTO LONG | 2.0 × ATR | 1.2 × ATR | 1.67 | 24h | Sweet spot 4-24h. Kill <1h exits. |
| CRYPTO SHORT | **BLOCK** | — | — | — | 35.4% WR. No edge. |
| EQUITY | 3.0 × ATR | 1.5 × ATR | 2.00 | 7d | Wide TP for swing. Score≥50 only. |
| FOREX (scalp) | 0.8 × ATR | 0.5 × ATR | 1.60 | 1h | Quick in/out. |
| FOREX (swing) | 3.0 × ATR | 2.0 × ATR | 1.50 | 14d | Let carry work. |
| COMMODITY | 1.5 × ATR | 1.0 × ATR | 1.50 | 1h | 16-20 UTC only. |
| FUTURES | **BLOCK** | — | — | — | 6.7% WR. Kill the asset class. |
| ETF | **PAUSE** | — | — | — | 33.3% WR. Redesign needed. |

---

## 6. Operational Roadmap

### Phase 1 — Immediate (1-2 days of work)

| Action | File(s) | Impact |
|--------|---------|--------|
| Add `direction == 'LONG'` hard gate for crypto in scanner | `scanner.py` rank_and_filter | Saves 126% PnL |
| Add `score >= 50` gate for equity and ETF | `quality_gates.py` | Saves 564% PnL |
| Fix daily block bypass | `risk_controls.py` | Restores risk control |
| Fix DSR threshold (1.64 → 0.95) | `promotion_gate.py` | Correct promotion gate |
| Block FUTURES asset class | `scanner.py` or `risk_policy.json` | Saves 94% PnL |
| Blacklist TRXUSDT, JTOUSDT, SHIBUSDT | Config | Saves 117% PnL |
| Kill `Value + Quality` equity strategy | `strategies/quality_value.py` | Saves 243% PnL |
| Kill `enhanced_ml_A_xgboost` | ML config | Saves 69% PnL |

### Phase 2 — Short-term (1-2 weeks of work)

| Action | Impact |
|--------|--------|
| Implement asset-class-specific ATR multipliers for TP/SL | Reduces SL_HIT frequency |
| Add hold-duration time gate (crypto max 24h, forex bimodal) | +15pp WR |
| Wire `ConfluenceEngine` as default (remove env var gate) | Better signal quality |
| Implement real MFE/MAE from kline high/low data | Accurate TP/SL calibration |
| Add entry-time gate (crypto: penalize 20-00 UTC) | +10pp WR on filtered |
| Pass real trade count to Kelly shrinkage | Correct position sizing |
| Implement continuous drawdown decay | Smoother risk scaling |

### Phase 3 — Medium-term (weeks of work)

| Action | Impact |
|--------|--------|
| Implement trailing stop (ATR-based, activated at 1× ATR profit) | ATR trailing already shows 71.4% WR |
| Add cross-asset features (SPX, VIX, DXY) | Regime awareness |
| Integrate real orderbook/VPIN data or drop features | Reduce noise |
| Proper LSTM/transformer for temporal features | Replace numpy "LSTM" |
| Centralize all config in YAML with schema validation | Maintainability |
| Add MLflow experiment tracking | Reproducibility |
| Cull strategy zoo to <50 active strategies | Reduce complexity |
| Implement proper HWM drawdown tracking | Accurate risk measurement |

### Phase 4 — Strategic (ongoing)

| Action | Impact |
|--------|--------|
| Smart order routing / execution algos | Reduce slippage |
| Real-time model drift detection (PSI, KL divergence) | Early warning |
| Bayesian online learning for TP/SL adaptation | Continuous improvement |
| Multi-timeframe ensemble (1h + 4h + daily signals) | Diversified alpha |
| Correlation-based portfolio construction (risk parity) | Reduce drawdowns |

---

## Appendix A: Strategy Kill List

| Strategy | Asset | Trades | WR | PF | Total PnL | Action |
|----------|-------|--------|-----|-----|-----------|--------|
| Value + Quality | EQUITY | 48 | 6.2% | 0.14 | -243% | **KILL** |
| enhanced_ml_A_xgboost | CRYPTO | 152 | 30.9% | 0.67 | -69% | **KILL** |
| Earnings Drift | EQUITY | 19 | 15.8% | 0.30 | -57% | **KILL** |
| Dividend Aristocrats | EQUITY | 8 | 0.0% | 0.00 | -50% | **KILL** |
| claude_gainer_1h | CRYPTO | 15 | 46.7% | 0.25 | -50% | **KILL** |
| ML Ranker (equity) | EQUITY | 32 | 28.1% | 0.61 | -32% | **KILL** |
| Consecutive Beats | EQUITY | 39 | 25.6% | 0.54 | -72% | **KILL** |
| Breakout Momentum (forex) | FOREX | 26 | 30.8% | 0.27 | -18% | **KILL** |
| extreme_oversold_bounce (ETF) | ETF | 6 | 0.0% | 0.00 | -23% | **KILL** |
| crypto_kalman_trend_residual_reversion_v1 | CRYPTO | 11 | 9.1% | 0.03 | -5% | **KILL** |
| stochrsi_macd_combo | CRYPTO | 6 | 16.7% | 0.12 | -9% | **KILL** |

## Appendix B: Symbol Blacklist

| Symbol | Trades | WR | Total PnL | Reason |
|--------|--------|-----|-----------|--------|
| TRXUSDT | 48 | 6.2% | -76% | Persistent loser, 48 trades |
| JTOUSDT | 41 | 22.0% | -31% | Low WR, high volume |
| SHIBUSDT | 7 | 0.0% | -10% | Zero wins |
| ENAUSDT | 12 | 25.0% | -17% | Consistent loser |
| DYDXUSDT | 12 | 25.0% | -13% | Consistent loser |
| ESPUSDT | 10 | 20.0% | -9% | Low liquidity loser |

## Appendix C: Strategy Amplify List

| Strategy | Asset | Trades | WR | PF | Total PnL | Action |
|----------|-------|--------|-----|-----|-----------|--------|
| st_fear_greed_contrarian | CRYPTO | 238 | 86.1% | 15.11 | +506% | **MAX ALLOCATION** |
| st_multi_day_momentum | CRYPTO | 51 | 76.5% | 11.33 | +150% | Increase weight |
| st_obv_support_divergence | CRYPTO | 68 | 73.5% | 4.44 | +69% | Increase weight |
| stocks_rsi2_pullback | EQUITY | 9 | 88.9% | 5.14 | +13% | Scale up |
| rs-breakout-scout | EQUITY | 13 | 69.2% | 4.90 | +26% | Scale up |
| forex_rsi2_mean_reversion | FOREX | 326 | 48.2% | 3.69 | +35% | Core forex strategy |
| kimi_signal_tracking | CRYPTO | 11 | 81.8% | 7.22 | +46% | **UNBLOCK** |
| signal_validation | CRYPTO | 17 | 64.7% | 3.58 | +22% | **UNBLOCK** |

---

*This review is based on 3,500 closed picks and 658 source files. All WR/PF/PnL figures are from `dashboard_data.json` as of 2026-04-10T23:54 UTC. Code findings are from static analysis of the codebase at commit `main` 2026-04-11.*
