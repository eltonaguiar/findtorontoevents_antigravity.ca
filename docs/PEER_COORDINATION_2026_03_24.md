# Peer Coordination & System Status — 2026-03-24

## Active Peers (as of 10:19 UTC)

| Peer ID | Summary | Key Deploys |
|---------|---------|-------------|
| ms6wyhav | IC-weighted scoring, data integrity fix | Spearman 0.616 (disputed), feature populator |
| i8mbe7tv | Marathon session — 60+ strategies, 1325 copy traders, circuit breaker | Claims real WR=37%, Spearman 0.003-0.14 |
| 5zajmzss | 25+ commits, scoring overhaul, code review fixes | wavelet_trend.py, hurst_exponent.py, sector caps |
| 314emojt | Toxic pick cleanup, elite_scorer workflow fix | 91 clean picks, 0 toxic, yahoo purge |

## Critical Data Analysis (Closed Picks — 452 trades)

### The Real Picture: ML Strategies Are the Profit Engine

The old narrative "copy trading is the only winner" is **WRONG**. Here's what the data actually says:

| Group | Trades | WR | Avg PnL/Trade | Total PnL | Verdict |
|-------|--------|-----|---------------|-----------|---------|
| ML-enhanced (top 3) | 47 | 93.6% | +0.195 | +8.83 | **PROFIT ENGINE** |
| Copy trading | 34 | 64.7% | +0.014 | +0.47 | Stable but small |
| Technical (EMA, etc.) | ~50 | 55% | +0.011 | +0.52 | Modest |
| Losers (volume_spike, winner_pattern) | 125 | 24% | -0.004 | -0.46 | **DRAG** |
| Broken ML (ADA, BTC 15m ensembles) | 20 | 0% | -0.101 | -2.02 | **DISASTER** |

### Top 5 Money Makers

1. **ml_enhanced_FETUSDT** — 93.75% WR, +6.08 PnL (52% of all profits!)
2. **ml_enhanced_RENDERUSDT** — 93.33% WR, +1.73 PnL
3. **ml_enhanced_BNBUSDT** — 93.75% WR, +1.03 PnL
4. **copy_hl_NMTD_25M** — 81.25% WR, +0.32 PnL
5. **binance_smart_money** — 55% WR, +0.30 PnL

### Concentration Risk

FETUSDT alone = 52% of total portfolio PnL. This is dangerous — one symbol regime change wipes half our profits.

## VERIFIED: Scoring is Near-Random (Spearman = 0.026)

**Independent test on 181 scored closed picks (WON/LOST with elite_score + pnl_pct):**

| Metric | Value | Meaning |
|--------|-------|---------|
| Spearman rho | 0.0264 | Near zero — score doesn't predict rank |
| Pearson r | -0.0814 | Slightly ANTI-predictive |
| Mean elite_score | 29.4 | Range 6-91 |
| Mean PnL | -0.90% | Overall negative (system losing on scored picks) |

**Score Quintile Breakdown:**

| Quintile | Score Range | WR | Avg PnL | Verdict |
|----------|-----------|-----|---------|---------|
| Q1 (lowest) | 6-12 | 25.0% | -0.57% | Bad |
| Q2 | 12-24 | 13.9% | -1.11% | Worst WR |
| Q3 | 25-30 | 36.1% | +0.11% | **Best PnL** |
| Q4 | 31-41 | 36.1% | -0.07% | Decent |
| Q5 (highest) | 41-91 | 51.4% | -2.83% | Best WR, **WORST PnL** |

**Conclusion:** Higher scores correlate with slightly better WR but MUCH worse PnL. The scoring system rewards picks that win small but lose big. This is the #1 systemic issue to fix.

**Root Cause Hypothesis:** Score weights reward confidence/consensus (which correlate with popular-but-crowded trades) instead of R:R ratio and strategy track record (which correlate with actual profitability).

**ms6wyhav's Spearman 0.616:** Confirmed wrong. Likely computed on biased subset or with leaky features.

## Deployed Today (2026-03-24)

| Module | Deployer | Status |
|--------|----------|--------|
| Forex deadlock gate fix | This agent | LIVE — forex picks now flow |
| IC-weighted scoring | ms6wyhav | LIVE (disputed effectiveness) |
| wavelet_trend.py | 5zajmzss | LIVE (syntax verified) |
| hurst_exponent.py | 5zajmzss | LIVE (syntax verified) |
| normalize_confidence elif fix | 5zajmzss | LIVE |
| sizing_multiplier Kelly fix | 5zajmzss | LIVE |
| elite_scorer in workflow | 314emojt | LIVE |
| Toxic pick force-close | 314emojt | LIVE (91 clean, 0 toxic) |
| cycle_metrics_runner.py | Previously deployed | WIRED at workflow line 339 |
| circuit_breaker.py | i8mbe7tv | DEPLOYED (not yet wired to scanner gating) |

## Unclaimed High-Impact Tasks

### Priority 1: Validate Scoring Effectiveness
- Run independent Spearman test: `elite_score` vs actual `pnl_pct` on closed_picks
- If r < 0.05, scoring overhaul is priority #1
- If r > 0.10, continue refining existing approach

### Priority 2: Reduce FETUSDT Concentration
- Cap any single symbol at 30% of total active picks
- Diversify ML strategies to other high-liquidity pairs (SOL, DOGE, XRP)

### Priority 3: Kill Dead Weight (User says DO NOT KILL — mutate first)
- winner_pattern_precursor: 20% WR on 75 trades → try inverse/mutation
- volume_spike_backfill: 30% WR on 50 trades → try parameter mutation
- Broken ML (ADA, BTC 15m ensembles): 0% WR → retrain or reassign symbols

### Priority 4: Expand Winners
- ML-enhanced approach works (93%+ WR) — apply to more symbols
- copy_hl_NMTD_25M works (81% WR) — find similar traders on Bitget/Bybit
- binance_smart_money works (55% WR) — increase allocation

### Priority 5: Wire Remaining Modules
- circuit_breaker → production_scanner loss-streak gating
- hold_duration_optimizer → forward_validator time-based exits
- wavelet_trend + hurst_exponent → elite_scorer feature inputs

## Future Plans by Peer

| Peer | Planned Next |
|------|-------------|
| ms6wyhav | Building institutional trust metrics, 10 cron jobs |
| i8mbe7tv | Gainer capture + confluence strategies + scoring pipeline fixes |
| 5zajmzss | PCA factor model, normalize_confidence elif fix |
| 314emojt | Monitoring next cycle for toxic creep-back |
| This agent | Validate Spearman, expand copy trader discovery, wire circuit breaker |

## Rules Reminder (From CLAUDE.md)

- **NEVER kill forex** — 3 agents working on forex improvements
- **Mutate before kill** — try DNA mutation/inverse/symbol rotation first
- **API failover** — always 3+ endpoint chain
- **Never run generators locally** — py_compile only
