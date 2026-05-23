# Alpha Engine — Scoring Reference

## Elite Scorer (0-100 points)

7 components with detailed thresholds:

### 1. ML Score (0-25 pts)
- Points = ml_score x 25 (direct multiplier of 0-1 normalized confidence)

### 2. Forward Win Rate (0-25 pts)
- >=10 trades @ >55% WR: min(25, (WR - 0.40) x 100). PF >=2.0 bonus: x1.15
- >=5 trades @ >45% WR: min(18, (WR - 0.35) x 60). PF >=1.5 bonus: x1.1
- >=3 trades @ >40% WR: min(10, (WR - 0.30) x 40)
- >=1 trade: min(5, WR x 10)

### 3. Confluence (0-15 pts)
- 5+ strategies = 15pts; 4 = 14pts; 3 = 12pts; 2 = 8pts
- Convergence >=2 = 8pts; >=1 = 5pts; score > 1.0 = 3pts
- Type diversity bonus: 3+ types = +3pts; 2+ types = +1pt
- Type categories: TA, statistical, structural, regime, ML

### 4. Risk:Reward (0-10 pts)
- R:R >=3.0 = 10pts; >=2.0 = 7pts; >=1.5 = 4pts; >=1.0 = 2pts; <1.0 = 0pts

### 5. Monte Carlo (0-15 pts)
- PROVEN = 15pts; LIKELY_VALID = 10pts
- INCONCLUSIVE: p<0.3 = 5pts; else = 3pts. Sharpe >1.5 bonus: +2pts
- INSUFFICIENT_DATA: 5+ trades @ >50% WR = 3pts; 3+ trades = 1pt
- LIKELY_RANDOM = 0pts

### 6. Volume (0-5 pts)
- >2.0x = 5pts; >1.5x = 4pts; >1.2x = 3pts; >1.0x = 1pt; <=1.0x = 0pts
- Falls back to parsing "vol=X.Xx" from strategy reason text

### 7. Regime (0-5 pts)
- ACCUMULATION+BUY = 5pts; MARKUP+BUY = 4pts
- DISTRIBUTION+SELL = 3pts; MARKDOWN+SELL = 5pts
- Compatible legacy = 5pts; Minor mismatch = 2pts
- Forward validated bonus: +1pt

## Grade Scale

| Grade | Score Range |
|-------|------------|
| S     | 90+        |
| A     | 75+        |
| B     | 60+        |
| C     | 45+        |
| D     | 30+        |
| F     | <30        |

## ML Ranker (39 features)

### Core features
`strategy_encoded`, `category_encoded`, `confidence`, `rsi_at_entry`, `atr_at_entry`, `volume_ratio`, `risk_reward`, `hour_of_day`, `day_of_week`, `regime_encoded`, `entry_distance_sma`, `strategy_win_rate`, `strategy_sharpe`, `strategy_closed_picks`, `pnl_momentum`, `consecutive_losses`, `strategy_pnl_last10`, `bb_pct_b`, `spread_pct`, `wick_ratio`, `market_fear_greed`, `funding_rate`, `entry_distance_vwap`

### Phase 3-4 additions
`hour_of_day_cos`, `hour_of_day_sin`, `ema_position`, `orderbook_imbalance`, `cvd_divergence`, `vpin`, `ofi`, `galaxy_score`, `accel_10`, `ma_dist_20`, `bb_position`, `atr_ratio`, `parkinson_vol`, `trend_consistency_20`, `consecutive_direction`, `zscore_20`, `volume_trend`, `cci_20`

### Heuristic scoring (bootstrap)

Base score: **0.50**

| Condition | Adjustment |
|-----------|------------|
| conf > 0.5 | +(conf - 0.5) x 0.3 |
| R:R > 3 | +0.10 |
| RSI 30-55 | +0.05 |
| RSI > 75 | -0.10 |
| vol > 2x | +0.05 |
| WR > 60% | +0.08 |
| Sharpe > 1 | +0.05 |
| convergence | +0.03 per each |
| regime aligned | +0.08 |
| regime counter | -0.12 |

## Scanner Filters (applied before ML scoring)

1. **Falling knife**: >25% below 200d SMA → reject
2. **R:R gate**: < 1.5 → reject (HIGH_RR >= 2.0 → +10% boost)
3. **Regime penalty**: counter-regime → x0.70 ml_score
4. **Volume warning**: low vol breakout → x0.80 ml_score
5. **Repeat-loser cooldown**: 2+ SL in 72h → x0.50 ml_score
6. **MIN_ML_SCORE** = 0.50 filter
7. **Max 3 picks** per symbol

## Confluence Engine

### Synergy pairs (proven combos, 1.20x-1.35x)

| Pair | Multiplier |
|------|------------|
| variance_ratio + fear_greed | 1.35x |
| connors_rsi2 + rsi_macd | 1.30x |
| hash_ribbon + pentoshi_htf | 1.30x |
| onchain_composite + fear_greed | 1.30x |
| vix_spike + connors_rsi2 | 1.30x |

### Anti-synergy pairs (0.30x-0.60x)

| Pair | Multiplier |
|------|------------|
| smart_money_fvg + community_fvg | 0.30x |
| double_top + spike_volume | 0.40x |
| community_fvg + mvrv_proxy | 0.40x |

### Crypto convergence trap
- 3+ crypto strategies agreeing = 0.75x penalty (25% WR vs 52.9% solo)
- Forex 3+ = 1.25x bonus (100% WR historically)

## Key Files

- `alpha_engine/elite_scorer.py`
- `alpha_engine/scanner.py` (lines 1338-1740)
- `alpha_engine/ml_ranker.py`
- `alpha_engine/confluence_engine.py`
- `alpha_engine/forward_validator.py`
