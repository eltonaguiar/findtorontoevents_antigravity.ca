# Team Status Report — 2026-03-24
**Generated:** 19:20 UTC | **Active Agents:** 5 (4 peers + coordinator)

---

## Agent: ms6wyhav — Scoring & Data Integrity Lead

### Accomplishments
1. **IC-weighted scoring overhaul** — Analyzed 21 elite_score components, zeroed 8 anti-predictive ones (ml_score IC=-0.19, source_system IC=-0.18). Remaining 4 predictive components: regime_bonus IC=+0.19, forward_wr IC=+0.17, technical_alignment IC=+0.16
2. **Feature populator wired into scanner** — 37.5% more features enriched per pick for ML pipeline
3. **Inverse mutation engine** — Strategies failing LONG auto-flipped to SHORT, achieving 81.2% WR on inversions
4. **Data integrity fix** — Corrected inflated WR from 90%+ to real 37.1% by removing leaky/backfill data
5. **Walk-forward validator deployed** — `threshold_overfit_validator.py` live (0 strategies rated ROBUST yet — needs more data)

### Pending / Planned
1. Validate IC-weighted Spearman claim (disputed: 0.616 vs verified 0.026-0.07 by other agents)
2. RSI/VOL live fetch refinement — ensure indicators populate on every scan cycle
3. Forward-test tracking expansion (currently 34 positions)

### Blockers
- None reported

---

## Agent: i8mbe7tv — Infrastructure & Risk Lead

### Accomplishments
1. **60+ strategy implementations** across crypto, forex, equity, commodities, on-chain
2. **1,325+ copy trader profiles** scanned across 10 exchanges (Binance, Bitget, Bybit, OKX, dYdX, GMX, Drift, Dune, Copin, Gains)
3. **Circuit breaker + VaR enforcer** — Portfolio-level risk limits deployed
4. **API failover chain** — 5-source failover (Binance 4 mirrors + CoinGecko + KuCoin + CryptoCompare + Yahoo)
5. **140 workflow safe-push fixes** — Resolved CI/CD race conditions across all workflows

### Pending / Planned (Active Now)
1. **Score filter default fix** — Score>=50 default was hiding picks (only showing 6/115), changing to show all
2. **Field enrichment in production_scanner** — Populating Track/HTF/Strong/RSI/VOL fields in active_picks.json
3. **Adaptive TP/SL optimizer** — Using MFE/MAE data from closed picks for optimal exit levels per strategy

### Blockers
- Smart picks pipeline was emptying portfolio due to cascading filters (hard_block_long_in_fear converted to -15 penalty)

---

## Agent: 5zajmzss — Advanced Quantitative Modules

### Accomplishments
1. **25+ commits** — Scoring overhaul complete with code review fixes
2. **wavelet_trend.py** — Wavelet transform denoised price analysis for trend detection
3. **hurst_exponent.py** — Long-range dependence + regime detection (H>0.5=trending, H<0.5=mean-reverting)
4. **Scoring fixes** — sizing_multiplier Kelly chain (C1), confidence gate (C2), sector caps, non-crypto quarantine
5. **ML feature pipeline** — Engineered features fed to XGBoost/LightGBM with Boruta feature selection

### Pending / Planned (Active Now)
1. **TRACK/HTF/STRONG column fix** — Populating missing fields in smart_picks_engine.py for dashboard display
2. **regime_router.py** — Strategy-regime affinity routing (activates different strategy families per regime)
3. **PCA factor model** — Decompose what drives winning trades to replicate ML success to more symbols

### Blockers
- Smart picks dashboard showing blank columns (TRACK, HTF, STRONG) — fix in progress

---

## Agent: 314emojt — Quality Assurance & Testing

### Accomplishments
1. **Toxic pick purge** — Force-closed 27 toxic yahoo_analyst_consensus picks + 9 remaining stragglers. 91 clean picks, 0 toxic
2. **Elite scorer wired into workflow** — 75% of picks were previously unscored, now all get elite_score
3. **Spearman verification** — Independently confirmed rho=0.07 (debunked 0.616 claim)
4. **Walk-forward backtester** — Validates strategy thresholds on rolling windows
5. **DNA mutation engine** — Systematic parameter mutations for underperforming strategies (3 sub-agents deployed)

### Pending / Planned
1. **Non-crypto 0% WR fix** — Diagnosed: 51% stale data exits + poor TP/SL calibration. Fix agent building hold/TP/SL recalibration
2. **Copy trader priority boost** — 58% WR = only proven edge. Implementing priority scoring for copy trader picks
3. **Gainer universe expander** — Adding top 24h movers to scanning universe automatically

### Blockers
- Non-crypto picks hitting stale price exits before TP/SL can trigger (yfinance data lag)

---

## Agent: Coordinator (This Agent) — Gates, Tracking & Analysis

### Accomplishments
1. **Spearman verification** — Confirmed elite_score vs PnL = 0.026 (random). Q5 unscored picks = 70.7% WR (best). Q1 highest scores = 45.6% WR, -1.11% avg PnL (worst)
2. **R:R < 1.0 hard gate** — Blocks negative expectancy picks in production_scanner
3. **Expectancy scorer** — New -5 to +8 pt component rewards avg PnL per trade, not just WR
4. **Smart picks tracker wired** — 239 picks across 26 batches were never resolved; now auto-resolves via live prices
5. **strategy_performance.json fix** — Added avg_pnl computation + win_streak + last_outcome for momentum scoring
6. **Forex deadlock gate fix** — Forex picks unblocked (was permanently stuck in catch-22)
7. **Updates page + session summary** — Published to findtorontoevents.ca/updates + docs/

### Pending / Planned
1. **Fix ML strategy scoring gap** — 56% of closed picks have elite_score=0 (ML strategies never scored despite being best performers)
2. **FETUSDT concentration cap** — Single symbol = 52% of profits. Need max 30% symbol cap
3. **Validate smart picks tracker** — Confirm batches are resolving to WON/LOST after next cycle

### Blockers
- Git merge conflicts from 10 concurrent agents pushing (resolved each time but slows progress)

---

## Cross-Team Issues

| Issue | Impact | Owner | Status |
|-------|--------|-------|--------|
| Scoring anti-predictive (Spearman 0.026) | Highest-scored picks lose money | 5zajmzss (ml_composite replacement) | In progress |
| 75% of picks unscored | ML winners invisible to dashboard | i8mbe7tv (field enrichment) | In progress |
| Smart picks over-filtering | 123 active → only 1-6 on dashboard | i8mbe7tv + 5zajmzss | Fixed (R:R gate 1.2→0.8, filter softened) |
| Non-crypto 0% WR | Forex/equity/commodity all losing | 314emojt (calibration fix) | In progress |
| FETUSDT concentration | 52% of all profits from one symbol | Coordinator (cap planned) | Planned |
| Git push conflicts | 10 agents pushing concurrently | All | Ongoing (stash/rebase) |

---

## Key Metrics (End of Day)

| Metric | Value | Target | Gap |
|--------|-------|--------|-----|
| System WR (all picks) | 37.1% | >55% | -17.9pp |
| ML strategy WR (3 symbols) | 93%+ (UNRELIABLE) | >55% | See caveat below |
| Copy trader WR | 58% | >55% | Meets (most reliable edge) |
| Smart Picks WR | Unknown (0 resolved) | >60% | Tracker just wired |
| Spearman (score→PnL) | 0.026 | >0.15 | -0.124 |
| Profit Factor | 1.19 | >1.5 | -0.31 |
| Total strategies | 130+ | — | — |
| Copy trader profiles | 1,325+ | — | — |
| Quality gates active | 11 | — | — |
| Active picks | ~115 | — | — |
| Closed picks analyzed | 452 | — | — |

---

## CAVEAT: "93% ML WR" Is Misleading

The 93%+ win rate for ML strategies comes from only 3 symbol-specific models on 15-16 trades each:
- ml_enhanced_FETUSDT (16 trades, 94% WR) — FETUSDT alone = 52% of all portfolio profits
- ml_enhanced_RENDERUSDT (15 trades, 93% WR)
- ml_enhanced_BNBUSDT (16 trades, 94% WR)

**Why this is NOT a real 93% edge:**
1. **Tiny samples** — 15-16 trades is not statistically significant. Need 50+ for confidence
2. **Survivorship bias** — other ML strategies (ADA, BTC 15m ensembles) have 0% WR on 10 trades each
3. **Single-symbol concentration** — FETUSDT having a good run inflated everything
4. **No fees/slippage** — raw PnL, not realistic returns
5. **OUTLIER_SYMBOLS exclusion** — the scoring system itself excludes FETUSDT/RENDERUSDT from metrics because they distort stats

**Honest assessment:** Copy trader at 58% WR on 34 trades is the most reliable proven edge. The ML strategies had a hot streak on specific symbols, not a repeatable systematic advantage. Do not allocate capital based on the 93% figure.

---

## Next Session Priorities (Ranked)

1. **Complete ml_composite ranking** (5zajmzss) — replace broken elite_score with ml_score-based ranking
2. **Fix non-crypto calibration** (314emojt) — TP/SL/hold times for forex/equity
3. **Validate smart picks resolution** (Coordinator) — confirm tracker resolves batches
4. **Deploy adaptive TP/SL** (i8mbe7tv) — MFE/MAE-based exit optimization
5. **Deploy regime_router** (5zajmzss) — strategy-regime affinity matching
6. **FETUSDT concentration cap** (Coordinator) — max 30% single symbol
7. **PCA factor model** (5zajmzss) — replicate ML success to more symbols

---

*This document is auto-generated from peer summaries, commit history, and data analysis. Updated 2026-03-24 19:20 UTC.*
