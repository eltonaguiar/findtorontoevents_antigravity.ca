# Peer Status & Roadmap — 2026-03-24 04:30 UTC

## Active Peers & Current Work

| Peer ID | Task | Status |
|---------|------|--------|
| **fcc1gex2** | Researching top broker-verified forex systems (Myfxbook/ForexFactory), implementing `proven_forex_strategies.py` | In progress |
| **8lhtfz7w** | Building 4 traditional asset test portfolio trackers (Portfolios 5-8) at `alpha_engine/traditional_test_portfolios.py` + GH Actions workflow | In progress |
| **vm1ur9f9** | Orchestrator: 24 new strategies deployed, TP/SL caps centralized, non-crypto in smart picks, cron monitoring | Active |
| **i4f158ku** | (No summary set) | Active |
| **This instance** | Forex deadlock gate fix, cycle_metrics_runner.py, institutional metrics wiring, peer coordination | Active |

---

## Completed Work (This Session)

### 1. Forex Deadlock Gate Fix (DEPLOYED)
**Commit:** `5f708ab30d` — on main, deployed via GH Actions

**Problem:** Gate 3 in `production_scanner.py` blocked ALL forex picks when < 10 closed trades existed. This created a catch-22: forex couldn't accumulate data because the gate blocked all picks, and the gate wouldn't open because there weren't enough trades.

**Fix:**
- Removed `"forex"` from `kill_categories` in `core_whitelist.json`
- Removed 7 non-london-breakout forex strategies from kill_list (london_breakout stays killed — 0/7 proven loser)
- Changed Gate 3 logic: insufficient data now PASSES forex through (was: blocked)
- Only blocks forex if 10+ trades show WR < 30% (data-driven, proven bad)

**Impact:** Forex strategies can now generate picks and accumulate forward-test data. Coordinates with peer fcc1gex2's new `proven_forex_strategies.py` and Grok's `non_crypto_agent/`.

### 2. Cycle Metrics Runner (NEW — `alpha_engine/cycle_metrics_runner.py`)
Orchestrates 4 institutional-grade modules after each alpha engine scan:

| Module | What It Computes | Output |
|--------|-----------------|--------|
| `institutional_metrics.py` | Sortino, Calmar, realistic Sharpe (0.1% fees), IC | `data/institutional_metrics.json` |
| `drawdown_tracker.py` | Max DD per strategy + portfolio, recovery time, streaks | `data/drawdown_report.json` |
| `threshold_overfit_validator.py` | Walk-forward validation, overfit risk (0-100) | `data/walk_forward_report.json` |
| `institutional_scorecard.py` | 250-point hedge fund signal scorecard | `data/institutional_scorecard.json` |

**Alert thresholds (auto-checked each cycle):**
- Portfolio DD > -30% = CRITICAL
- Loss streak >= 12 = WARNING
- System WR < 35% = WARNING
- IC negative = CRITICAL (scoring anti-predictive)
- Scorecard grade D or F = WARNING

**Wired into:** `alpha-engine-live.yml` — runs after Strategy Consensus Matrix, before Audit Trail push. Non-fatal (continue-on-error).

### 3. Pylance OOM Fix (`pyrightconfig.json`)
- Workspace had 16,500+ .py files (mostly in .venv, .venv312, incubator)
- Pylance hit 2.86 GB RAM and crashed with heap OOM
- Created config excluding non-essential dirs from analysis

---

## System Performance Summary (Current State)

| Metric | Value | Target | Gap |
|--------|-------|--------|-----|
| Win Rate (overall) | 41.9% | >55% | -13.1pp |
| Win Rate (Smart Picks) | ~64% | >60% | Above target |
| Profit Factor | 1.26 (crypto) | >1.5 | -0.24 |
| Score-PnL Correlation | r=0.043 | >0.15 | Near-random |
| Max Drawdown | -302.62% | <20% | Unacceptable |
| Scorecard Grade | C (~120/250) | B+ (175+) | -55 pts |

### By Asset Class
| Category | WR | PF | Status |
|----------|-----|-----|--------|
| Crypto | 42.8% | 1.26 | **PROVEN EDGE** — keep optimizing |
| Forex | 33.9% | 0.53 | **PROBATION** — gate fixed, data accumulating |
| Equity | 31.8% | 0.63 | **PROBATION** — macro gate active |

---

## Strong Signals Blueprint (Key Findings)

These data-backed findings should guide ALL strategy development:

1. **Regime alignment is the #1 factor** — LONG in bull = 64% WR. Wrong direction = ~25% WR regardless of score.
2. **R:R 2.0-2.5 = 73.7% WR** — Hard filter anything below 1.5.
3. **Confidence 0.60-0.70 = 61% WR (BEST)** — System currently penalizes this range. Fix needed.
4. **Leverage safety = best single predictor** — Tight stops (1.5-3%) + high ML confidence = 67% WR, +1.21% avg P&L.
5. **Strategy track record weight should double** — From 10 to 20 pts in elite scorer.

### Expected Impact of Strong Signal Filter
572 picks -> ~40 strong signals (7% pass rate) -> **65-70% WR, PF 1.8-2.2**

---

## Roadmap & Coordination Needed

### Immediate (This Week)

| Task | Owner | Dependency | Priority |
|------|-------|------------|----------|
| R:R >= 1.5 hard gate in production_scanner | Any peer | None | HIGH |
| Fix confidence scoring (0.60-0.70 = best) | Any peer | None | HIGH |
| Wire drawdown_tracker into strategy gating | Any peer | drawdown_tracker.py exists | HIGH |
| Proven forex strategies (Myfxbook-verified) | fcc1gex2 | Forex gate fix (DONE) | HIGH |
| Traditional asset portfolio trackers | 8lhtfz7w | None | MEDIUM |
| Score-PnL correlation fix (r=0.043 -> >0.15) | vm1ur9f9 or any | ML retrain needed | HIGH |

### Next Week

| Task | Notes |
|------|-------|
| Regime match weight 0.40 -> 0.50 | Strongest predictor, increase influence |
| Strategy track record weight -> 20 pts | Backtest-validated improvement |
| Half-Kelly position sizing in production | kelly_position_sizer.py exists, needs wiring |
| FETUSDT concentration filter | 153.6% of total P&L from single symbol |
| Consensus scoring fix | Anti-predictive at 34.8% WR but gets +45 boost |

### Month 1-2

| Task | Notes |
|------|-------|
| HMM/Bayesian regime detection | Replace simple threshold-based regime |
| Portfolio correlation monitoring | Max 0.7 correlation between positions |
| Stress testing framework | Flash crash, gap, liquidity scenarios |
| Multi-manager pod structure | Isolate trend, mean-reversion, on-chain, copy, event |
| Investor-grade reporting dashboard | Real-time metrics visualization |

---

## Coordination Rules for All Peers

1. **ALWAYS pull before push:** `git stash && git pull --rebase origin main && git stash pop`
2. **Never run generators locally** — use `py_compile` for syntax checks only
3. **API failover chain mandatory** — 3+ endpoints (Binance mirrors -> CoinGecko -> KuCoin -> CryptoCompare)
4. **Mutate before kill** — Try DNA mutation/inverse/symbol rotation before killing any strategy
5. **Edit `audit_dashboard/template.html`**, NOT `index.html`
6. **Forex is NOT killed** — Gate fixed 2026-03-24. New forex strategies welcome.
7. **Non-crypto picks** should go through `non_crypto_quality_gate.py` (probation until 50+ trades @ 40%+ WR)

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `alpha_engine/production_scanner.py` | Main scan + quality gates |
| `alpha_engine/cycle_metrics_runner.py` | NEW — Post-cycle institutional metrics |
| `alpha_engine/data/core_whitelist.json` | Strategy lifecycle (core/incubator/kill) |
| `alpha_engine/data/cycle_metrics_summary.json` | NEW — Per-cycle alert summary |
| `alpha_engine/non_crypto_quality_gate.py` | Forex/equity probation system |
| `alpha_engine/strong_signals.py` | Strong signal filter implementation |
| `docs/STRONG_SIGNALS_BLUEPRINT.md` | Data-backed scoring improvements |
| `docs/SYSTEM_AUDIT_COMPREHENSIVE.md` | Full institutional audit |
| `.github/workflows/alpha-engine-live.yml` | Main scan workflow (now includes metrics) |

---

---

## Agent Status Dump — 2026-03-24 04:50 UTC

### BREAKTHROUGH: Score-PnL Spearman 0.003 -> 0.616 (peer 6vdhbhhx)
Scoring system is now predictive. 4 anti-predictive components zeroed. 405 strategies killed. This is the single biggest improvement to date.

### Active Peers (6 total)

| Peer | Task | Key Achievement |
|------|------|-----------------|
| bzcx9ofh | Data validation tests (Node.js) | 5 new test sections for closed/active picks |
| i40lezdb | Orchestrator — 55+ algos, 8 quant deployed | Kalman, Bayesian, GARCH, Cointegration live |
| 6vdhbhhx | IC-weighted selector + score caps | Spearman 0.003->0.616 BREAKTHROUGH |
| 9j3sckm2 | (no summary) | Needs assignment |
| gp9np3vp | Reviewing Gemini's non-crypto fix | Conflict resolution |
| This instance | Quality gates, forex fix, monitoring, copy trader analysis | Toxic symbol gate, cycle metrics |

### Copy Trader Analysis (NEW — data audit of closed picks)

**Best source systems by WR:**

| Source | WR | W/L | PnL | Priority |
|--------|-----|-----|------|----------|
| copy_trader_intel | 73.9% | 17/23 | +38.5% | HIGHEST |
| cta_replicator | 72.7% | 8/11 | -4.7% | HIGH |
| copy_trader_binance | 52.6% | 10/19 | +24.6% | MEDIUM |

**Best individual traders:**

| Trader | WR | W/L | Avg PnL | Symbols |
|--------|----|-----|---------|---------|
| copy_hl_NMTD_25M | 81.2% | 13/16 | +2.95% | ETH, FARTCOIN, MON, CRV, AAVE |
| copy_hl_whale_123M_87roi | 100% | 4/4 | +2.95% | SOL, XRP |
| copy_hl_whale_24.5M | 0% | 0/1 | -2.10% | TIA (too small) |

**Action items for copy trader improvement:**
1. INCREASE weight for copy_trader_intel and cta_replicator picks in elite_scorer
2. Track NMTD_25M and whale_123M picks with higher priority
3. Expand Hyperliquid whale scanning (best source of alpha)
4. Reduce weight for multi_asset_copytrader (30% WR) and yahoo_analysts (0%)

### Symbol Concentration Risk

| Symbol | PnL Share | WR | Action |
|--------|-----------|-----|--------|
| FETUSDT | 100.1% | 84% | Protect — ensure strategies keep generating FET picks |
| RENDERUSDT | 40.9% | 95% | Protect — highest WR symbol |
| BNBUSDT | 13.1% | 79% | Healthy — keep as core |
| BTCUSDT | -15.5% | 6% | GATED — requires conf>=0.85 + ml>=0.70 |
| ADAUSDT | -19.3% | 12% | GATED — same toxic symbol gate |

### Data Corrections (Blueprint was wrong)

| Claim | Blueprint Said | Actual Data | Status |
|-------|---------------|-------------|--------|
| Confidence sweet spot | 0.60-0.70 = 61% WR | 0.80+ = 68.4% WR (BEST) | Current scoring CORRECT |
| R:R sweet spot | 2.0-2.5 = 73.7% WR | R:R<1.0 = 87.5% (best small sample) | Already recalibrated |
| Consensus | Boosts picks | 34.8% WR, anti-predictive | Already flipped to penalty |

### Unclaimed Work / Available Tasks

| Task | Impact | Effort | Notes |
|------|--------|--------|-------|
| Boost copy_trader_intel weight in elite_scorer | HIGH | LOW | 73.9% WR source, currently equal weight |
| Cointegration pairs scanner (171 symbols) | HIGH | MED | New algo deployed, needs pick generator |
| Portfolio correlation monitor | MED | MED | Max 0.7 corr between positions |
| HMM regime detection upgrade | MED | HIGH | Replace threshold-based regime |
| Stress testing framework | MED | HIGH | Flash crash, gap scenarios |
| Live paper ramp (0.5% capital on 85+ scores) | HIGH | MED | Scoring now predictive (Spearman 0.616) |

### Next 24h Focus (Integration > Expansion)
1. Prune 47 algos to top 12 by OOS Sharpe > 1.0
2. Ensemble top algos into unified pick scoring
3. Boost copy trader source weighting (73.9% WR source)
4. Forward-test the Spearman 0.616 scoring in live picks
5. Begin micro-live ramp if forward WR > 55% sustained

*Last updated: 2026-03-24 04:50 UTC*
