# Score Calibration Audit — 2026-04-06

**Dataset:** 3,500 closed picks from `dashboard_data.json`. All correlations Pearson r.

## 1. Score Decile Analysis (350 picks each)

| Decile | Score Range | WR | Avg PnL | Cum PnL | PF |
|--------|------------|-----|---------|---------|-----|
| D1 | 9-12 | 40.6% | -0.05% | -17 | 0.94 |
| D2 | 12-16 | 33.4% | -0.35% | -121 | 0.68 |
| D3 | 16-20 | 30.3% | -1.17% | -408 | 0.46 |
| D4 | 20-28 | **54.9%** | +0.48% | +168 | 1.47 |
| D5 | 28-30 | **55.7%** | +0.51% | +180 | 1.59 |
| D6 | 30-35 | 43.1% | +0.07% | +26 | 1.12 |
| D7 | 35-40 | 35.7% | -0.27% | -96 | 0.63 |
| D8 | 40-48 | 52.0% | +0.42% | +146 | 1.67 |
| D9 | 48-56 | 55.1% | +0.44% | +156 | 1.87 |
| D10 | 56-100 | 57.4% | +0.48% | +168 | 1.75 |

**4 inversions out of 9.** Not monotonic. D6-D7 (score 30-40) is a dead zone where WR drops to 35-43% despite mid-range scores. elite_score r=+0.10 vs ml_composite_score r=+0.22 — elite_score is half as predictive as its ML counterpart.

## 2. Component Correlation Ranking (n=3,500)

| Component | r | Verdict |
|-----------|---|---------|
| forward_wr | **+0.242** | Best predictor |
| leverage_safety | +0.133 | Strong signal |
| source_system | +0.080 | Moderate signal |
| market_cap_tier | +0.056 | Weak signal |
| age_freshness | +0.035 | Weak signal |
| ml_score | -0.012 | Noise |
| technical_alignment | -0.014 | Noise (penalty hitting winners) |
| **regime_bonus** | **-0.115** | **Anti-predictive** |

**15 components are pure noise** (r=0.000): volume, signal_quality, confluence, session_bonus, risk_reward, volatility_predictability, strategy_momentum, time_of_day, monte_carlo, proven_strategy_bonus, etc.

## 3. Over-Scored (score>=60, lost >2%): n=30
- 83% were SHORTs (25/30). Sources: luxalgo_filters (10), rapid_fire (9), alpha_engine (6).
- Avg confidence=0.60 (below sweet spot). Pattern: regime_bonus inflated score on counter-trend SHORTs.

## 4. Under-Scored (score<30, won >2%): n=277
- Sources: claude_gainer_st (79), stocks_competition (43), kimi_riseoftheclaw (40).
- Score killed by: technical_alignment avg=-7.1, low forward_wr avg=11.2, low regime_bonus avg=3.2.
- Best missed: CTSIUSDT LONG score=12 pnl=+25%, OPEN LONG score=17 pnl=+22.6%.

## 5. Key Signal Brackets

| Signal | Bracket | n | WR |
|--------|---------|---|-----|
| trust | 0-2 | 2,365 | 37.4% |
| trust | 5-6 | 870 | **68.3%** |
| trust | 7-8 | 31 | **71.0%** |
| confidence | 0.70-0.79 | 968 | **57.0%** |
| confidence | 0.90-1.00 | 85 | 47.1% |
| fwd_wr | 50-65 | 792 | **69.7%** |
| fwd_wr | 0-20 | 353 | 13.9% |

## 6. Penalty Audit
- **Heavy penalty (score<20):** n=988, WR=36.5% — working correctly.
- **Heavy bonus (score>80):** n=27, WR=48.1% — **FAILING.** Should be 60%+ but barely above baseline.
- **Battleground:** avgScore=58.4 but WR=30.6% (n=36). Massively over-scored.

## 7. Proposed Fixes

### Weight Changes
| Component | Current Weight | Proposed | Evidence |
|-----------|---------------|----------|----------|
| forward_wr | 0-40 pts | 0-55 pts (+37%) | r=+0.242, best predictor |
| regime_bonus | 0-20 pts | 0-5 pts (-75%) | r=-0.115, anti-predictive; high_bonus WR=33.2% vs no_bonus WR=50.2% |
| source_system | 0-10 pts (halved) | 0-15 pts | r=+0.080; claude_gainer_st 63.2% WR crushed by low source_system score |
| leverage_safety | 0-5 pts (halved) | 0-10 pts (restore) | r=+0.133, 2nd best predictor |
| ml_score | 0-9 pts | 0-4 pts (-55%) | r=-0.012, noise |

### Penalties to Remove/Reduce
1. **regime_bonus** — not a penalty per se but awarding +20 pts to regime-aligned picks that lose 50.2% vs 33.2% WR. Cap at 5 pts max.
2. **technical_alignment** heavy penalty — picks with heavy_penalty (n=680) have WR=50.7%, BETTER than neutral (42.0%). The -30 pt penalty is destroying winners.
3. **battleground source tier** — avgScore=58.4 (top 15%) despite 30.6% WR (bottom 15%). Source tier for battleground must drop.

### New Signals to Add
1. **trust_score gate at 5** — trust>=5 delivers 68-71% WR (n=901) vs 37.4% (n=2,365). A hard gate or +15 bonus for trust>=5 would be the single biggest improvement.
2. **confidence sweet-spot bonus** — conf 0.70-0.79 = 57% WR. Conf 0.90+ = 47% WR. Add -5 penalty for overconfidence (conf>0.85).
3. **Direction-regime alignment** — LONGs: 47.2% WR, SHORTs: 31.4% WR overall, but SHORTs dominated in SHORT regimes (71% WR on 2026-04-05). Real-time regime tag must gate direction.
