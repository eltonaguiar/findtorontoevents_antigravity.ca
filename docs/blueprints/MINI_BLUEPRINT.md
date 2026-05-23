# MINI BLUEPRINT — Trading Systems Status
## Feb 26, 2026 21:00 UTC | F&G=11 (Extreme Fear) | BTC ~$67,400

**Hub:** https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/hub/

## SCORECARD

| System | Active | Closed | WR | P&L | Status |
|--------|--------|--------|-----|-----|--------|
| Mercury 2 | 10 | 25 | 40% | +23% | LONG-only, regressed from 94% |
| Claws of Doom | 3 | 2 | 100% | +12.8% | Expanded to 10 symbols |
| Alpha Engine | 30 | 141 | 34.8% | -$5,751 | Overhauled: 11 dead killed |
| Crypto ML Edge | 2 | 6 | 0% | -8.5% | Retraining (LightGBM) |
| KIMI v11.0 | — | — | — | — | 81 algos, every 15min |
| Battleground A | 0 | 3 | 0% | Neg | Dormant (all SL losses) |
| Battleground B-E | 0 | 0 | n/a | — | Fixed, awaiting picks |
| Breakout Arena | 0 | 0 | n/a | — | Dormant |

**13 systems total** | 22 GitHub Actions workflows | Scans every 5-30 min

## WHAT WORKS

1. **F&G contrarian entry** — Mercury 2 + Claws buy during retail panic (F&G<20)
2. **ATR trailing stops** — Lock BE at +1x ATR, trail after; prevents giveback
3. **XGBoost ensemble** — 3 models (conservative/aggressive/balanced) averaged
4. **Time exits** — Force-close after 24h prevents slow bleeds
5. **Multi-timeframe trend filter** — Daily 50-MA + MACD alignment (+142% Sharpe)
6. **Tiered TP exits** — 1.5R/3R partials + runner captures extended moves
7. **Cross-system consensus** — Sharpe-weighted aggregation across systems

## WHAT FAILS

1. **PANIC_SELL shorts** — Battleground A shorted during bounces → 0% WR
2. **ICT/SMC in fear** — FVG, BOS fail when F&G<20 (Alpha Engine drag)
3. **Models near coin-flip** — Mercury prob 0.487, edge is regime filters not ML
4. **On-chain lag** — MVRV, NVT too slow for volatile crypto
5. **Mercury regression** — WR dropped 100%→40% after 25 trades (LONG-only)

## TOP STRATEGIES (Alpha Engine, min 2 trades)

| Strategy | WR | Record | Direction |
|----------|-----|--------|-----------|
| community_london_breakout_v2_forex | 100% | 2/2 | SELL-only |
| multi_sigma_reversal | 100% | 3/3 | SELL-only (3x boost) |
| spike_macd_divergence | 100% | 3/3 | BUY-only (2x boost) |
| autocorrelation_exploiter | 83% | 5/6 | SELL-only (4x boost) |
| hurst_regime_adaptive | 83% | 5/6 | BUY-only (4x boost) |

## FIXES APPLIED (Feb 26)

### Round 1 — Performance Overhaul
- Alpha: killed 11 dead strategies (0% WR), direction restrictions, SL widened 1.5x→2.25x ATR
- Proven strategy boost: top 7 get 2-4x confidence multiplier
- ML patience: 12+ picks before evaluation (was 8)

### Round 2 — System Fixes
- Health gate: `min()` → `max()` for confidence (was killing signals when ml_score=0.5)
- Claws of Doom: 3→10 symbols + smart_round() for sub-$1 coins
- KIMI table: removed 7 phantom header columns
- System C: "MODEL TRAINED" → "HEURISTIC MODE" (honest labeling)
- Mercury 2: added SHORT explanation note (risk engine blocks shorts in oversold)

### Round 3 — Data Quality (17 files)
- Added `direction` + `timestamp` fields to Alpha picks
- Fixed PEPE/SUI CoinGecko ID leaks, added runtime sanitizer
- KIMI dedup + entryPrice aliases for aggregator
- Mercury TP/SL sanity guard (SL clamped min 1% from entry)
- All Discord: EST timezone, W/L counts, no scientific notation

### Round 4 — KIMI Research (10 implementations)
- 4 new microstructure strategies (OBI, options skew, Coinbase premium, perp basis)
- Meta-labeler gate on all 6 ML scanners (Lopez de Prado)
- Regime-strategy router (blocks shorts in panic, longs in euphoria)
- DSR hard gate (blocks systems with no statistical edge)
- StandardScaler leakage fix in 4 training files
- Fractional differentiation (d=0.4) for stationarity
- Universe swap: LTC/BCH/DOT → NEAR/RENDER/TAO

## KEY ARCHITECTURE

```
Scrapers → JSON data → GitHub Actions (5-30 min) → Dashboards + Discord
                                    ↓
                          Cross-Aggregator (5 min)
                          Sharpe-weighted consensus
                          Regime router + DSR gate
```

**Health Gate** (shared by Battleground A-E):
- SAFE → trade freely | CAUTION → 50% size | WARNING → 25% size
- PANIC + F&G≤15 → BUY conf≥0.50 at 50%, SELL conf≥0.58 at 35%

**Quality Gates** (system-wide):
- Meta-labeler: filters 70-90% bad trades (heuristic→RF at 50+ trades)
- DSR gate: blocks systems with p-value > 0.05
- Regime router: no shorts in panic, no longs in euphoria

## DASHBOARDS

| System | URL |
|--------|-----|
| Hub | [hub/](https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/hub/) |
| Alpha | [alpha/](https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/alpha/) |
| Mercury 2 | [mercury2/](https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/mercury2/) |
| KIMI | [riseoftheclaw.html](https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/riseoftheclaw.html) |
| Battleground | [battleground/](https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/battleground/) |
| Claws of Doom | [CLAWSOFDOOM](https://eltonaguiar.github.io/CLAWSOFDOOM/) |
| Monitor | [monitor/](https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/monitor/) |
| Edge | [edge/](https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/edge/) |

## HONEST ASSESSMENT

**The edge is NOT from ML predictions** (models are coin-flip quality). The edge comes from:
1. Regime filters (only trade in extreme fear/greed)
2. Risk management (ATR stops, time exits, position sizing)
3. Strategy selection (proven strategies get boosted)

**Next priorities:** Mercury 2 retrain, correlation management (max 4 crypto LONGs), walk-forward validation, expand features beyond price/volume.

## ROUND 5 — External Review Integration (Feb 26, late)

### Sources: Deep research feedback + Llama 3.1 8B assessment

**Key insight from both reviews:** The edge is NOT ML — it's regime filters + risk management + strategy selection. Both reviews independently confirmed this. ML models are coin-flip quality (prob ~0.487). Stop trying to make ML the edge; instead double down on what works.

### What's already done (confirmed by review):
- [x] Multi-indicator regime router (F&G + EMA20/50 + ADX) — `cross_aggregation/regime_router.py`
- [x] Kelly-fraction position sizing (half-Kelly) — `mercury2/risk_engine.py`
- [x] Dynamic ATR stops with vol scaling — Mercury 2 config (2.0x ATR)
- [x] Walk-forward CV — `crypto_ml_edge/validation.py`
- [x] Meta-labeler gate — all 6 ML scanners
- [x] Regime-strategy router — blocks shorts in panic, longs in euphoria

### New items to implement (from review gaps):

| # | Item | Expected WR lift | Priority | Status |
|---|------|------------------|----------|--------|
| 1 | **RSI into regime router** — Add RSI-14 as 4th signal to `regime_router.py` (F&G+EMA+ADX+RSI) | +1-2% | HIGH | TODO |
| 2 | **Correlation guard** — Max 4 concurrent crypto LONGs; rolling 60d pairwise corr ≤0.3 | +1-2% | HIGH | TODO |
| 3 | **Holding-period sweep** — Walk-forward test exit horizons (2h/4h/8h/12h/24h) per strategy class | +1-3% | MED | TODO |
| 4 | **Model-drift alarm** — Auto-retrain trigger when WR drops >5% for 2 consecutive weeks | +0.5-1% | MED | TODO |
| 5 | **Feature gaps** — Add `hour_of_day`, `volatility_cluster` (ATR50/ATR10), `volume_at_price` to ML features | +2-5% | MED | TODO |
| 6 | **Shadow A/B testing** — 5-10% capital canary for new model versions before full rollout | +0.5-1% | LOW | TODO |
| 7 | **Execution slippage buffer** — Add 0.5-1% slippage to all backtests for realistic fills | +0.5-1% | LOW | TODO |

### 30-Day Roadmap (from review)

| Week | Focus | Success Metric |
|------|-------|----------------|
| 1-2 | RSI in regime router + correlation guard | WR ↑ ≥3% vs baseline |
| 3-4 | Feature engineering + holding-period sweep | Validation WR ≥55%, stable across folds |
| 5-6 | Model-drift alarm + shadow A/B test | Auto-retrain fires correctly; shadow WR ≥55% |
| 7-8 | Execution hygiene + slippage buffer | Backtest-to-live gap ≤2% |

### Win-Rate Lift Estimates (ranked)

| Rank | Action | Expected Lift |
|------|--------|---------------|
| 1 | Regime router upgrade (add RSI) | +1-2% |
| 2 | ML feature overhaul (time/vol/VAP) | +2-5% |
| 3 | Correlation pruning (max 4 LONGs) | +1-2% |
| 4 | Holding-period optimization | +1-3% |
| 5 | Dynamic risk tuning | +1-2% |
| 6 | Execution slippage reduction | +0.5-1% |
| **Total potential** | | **+6-15%** |

### Llama 3.1 Assessment Summary
> "The edge in this trading system is primarily due to risk management and strategy selection, rather than ML predictions. Continue to improve ML models but prioritize regime filters, risk management refinement, and strategy selection. The meta-labeler approach for filtering bad trades is sound."

---

## ROUND 6 — Sharpe-Booster Integration (Feb 26, late)

### Source: Back-tested Sharpe optimizations compatible with live constraints

**Constraint validation:** All items below work within our live setup (F&G regime filter, 15-min GitHub Actions, max 4 concurrent crypto longs, ATR risk engine, min 50 trades for meta-labeler RF).

### Top 10 Sharpe Boosters (ranked by impact)

| # | Booster | Sharpe Δ | Effort | Status |
|---|---------|----------|--------|--------|
| 1 | **Regime-specific strategy map** — Route by F&G: Fear→mean-reversion LONGs only, Greed→momentum SHORTs only | +0.45 | MED | TODO |
| 2 | **Partial exit engine** — 50% at 1.5R, 25% at 3R, runner with BE+0.5ATR trail | +0.41 | LOW | PARTIAL (tiered TP exists, runner trail needs tuning) |
| 3 | **Walk-forward lite** — 1000d train/90d test, step 30d, retrain when 60d Sharpe<0.3 | +0.37 | MED | TODO |
| 4 | **Correlation cap basket** — Greedy-select by Sharpe until pairwise ρ<0.65 (within 4-long limit) | +0.33 | LOW | TODO |
| 5 | **Meta-labeler RF upgrade** — RF with 4 features (ATR, vol-of-vol, F&G, hour) at 50+ trades | +0.31 | LOW | TODO (heuristic→RF swap ready) |
| 6 | **Vol-adjusted TP/SL** — TP=0.4·ATR20+0.6·swing, SL=1.25·ATR20 | +0.29 | LOW | TODO |
| 7 | **Vol-of-vol filter** — Skip when 24h σ-of-σ > 75th pctile of 90 days | +0.27 | LOW | TODO |
| 8 | **Intraday seasonality** — Entries only 01:00-11:00 UTC (London+NY) | +0.24* | LOW | TODO |
| 9 | **Dynamic sizing k/(σ·√τ)** — Max 0.5% portfolio heat per trade | +0.22* | LOW | PARTIAL (vol_targeted_risk exists, needs τ term) |
| 10 | **Embedded carry filter** — Require funding rate <-25bps for longs, >+25bps for shorts | +0.55** | LOW | TODO |

*Mercury 2 specific. **Claws of Doom specific (WR 62→74%).

### Quick-Win Implementation Order (3 items → Sharpe >1.3)

1. **Vol-of-vol filter** — 1-line gate, zero new deps, +0.27 Sharpe
2. **Intraday seasonality overlay** — 1-line gate, +0.24 Sharpe (Mercury 2: 0.81→1.24)
3. **Correlation cap basket** — ~20 lines, +0.33 Sharpe, -19% portfolio vol

### Back-Test Results Summary

| Metric | Before | After (top 3) |
|--------|--------|---------------|
| Portfolio Sharpe | ~0.9 | >1.3 |
| Max Drawdown | -28% | -17% |
| Tail Ratio | 1.9 | 1.3 |
| Trade Frequency | 100% | -38% (quality > quantity) |

---

## ROUND 7 — Full-Heart Playbook Integration (Feb 26, late)

### Source: Structured end-to-end review with code sketches + 8-week roadmap

**Analysis:** ~70% of this feedback overlaps with Rounds 5-6 (vol-of-vol, intraday gate, correlation cap, RSI router, feature engineering, holding-period sweep, model-drift, shadow A/B). Below are the **genuinely new items** not yet captured.

### New Items (not in Rounds 5-6)

| # | Item | Sharpe Δ | Priority | Status |
|---|------|----------|----------|--------|
| 1 | **Ensemble Sharpe weighting** — Weight cross-system consensus by per-system 60d rolling Sharpe (not equal weight) | +0.3-0.6 | HIGH | TODO |
| 2 | **4-regime map** — Replace binary panic/greed with 4 regimes: Fear-MeanRev, Fear-Momentum, Greed-Momentum, Greed-MeanRev; assign strategy-specific 2-4x boosts per regime | +0.4-0.8 | HIGH | TODO |
| 3 | **Cross-asset risk budgeting** — Cap crypto at 30% of equity; treat rest as separate risk bucket; within crypto use correlation cap at ≤0.5% per trade | +0.3-0.5 | MED | TODO |
| 4 | **Signal staleness guard** — Discard any signal older than 45 min (GitHub Actions latency protection) | +0.1 | LOW | TODO |
| 5 | **Discord monitoring alerts** — Fire on: (a) 2+ consecutive losses, (b) rolling Sharpe dip <0.5, (c) correlation breach >0.65 | +0.1 | LOW | TODO |
| 6 | **MVRV z-score feature** — Z-score MVRV over 180d rolling (not raw) for ML scanners | +0.1-0.2 | MED | TODO |
| 7 | **Feature importance pruning** — Auto-drop features contributing <1% to model; prevents overfitting | +0.1 | LOW | TODO |
| 8 | **Pre-live checklist** — Formalized gate: UTC timestamps, no dupes, 0.75% slippage, 0.04% commission, walk-forward integrity, risk budget audit | — | HIGH | TODO |

### Updated 8-Week Roadmap (consolidated from all reviews)

| Week | Focus | Deliverable | Sharpe Target |
|------|-------|-------------|---------------|
| 1-2 | Vol-of-vol filter + intraday gate + correlation cap | Updated `risk_engine.py`, monitoring dashboard | ≥1.3 |
| 3-4 | RSI in regime router + 4-regime map + feature engineering | New `regime_router.py` v2 + `ml_features.py` | ≥1.5 |
| 5-6 | Ensemble Sharpe weighting + holding-period sweep | Per-strategy horizon JSON + `aggregator_weighted.py` | ≥1.5 |
| 7-8 | Model-drift alarm + shadow A/B + cross-asset risk budget | Auto-retrain script + `shadow_test/`, Discord alerts | Stable ≥1.3 |

### Pre-Live Checklist (from review)

- [ ] All timestamps UTC, no duplicate rows, missing values handled
- [ ] Backtests include 0.75% slippage + 0.04% taker commission
- [ ] Walk-forward: no look-ahead leakage, train ends before first test bar
- [ ] Risk budget: ≤2% equity per trade, ≤30% equity in crypto overall
- [ ] Signal-to-trade latency: discard signals >45 min old
- [ ] Discord alerts: consecutive losses, Sharpe dip, correlation breach

### Key Takeaway (3rd independent confirmation)
> "The real Sharpe lift comes from filtering — doing less but doing it better. By tightening regime filters, controlling correlation, and aligning trade horizons with each strategy's natural time-scale, you'll see a clean increase in risk-adjusted returns without having to chase a perfect ML model."

---

## ROUND 8 — Google Studio (Gemini) Feedback (Feb 26, late)

### Source: Google AI Studio analysis of the SUPER DETAILED BLUEPRINT

**Analysis:** ~80% overlaps with Rounds 5-7 (F&G gating, strategy pruning, ATR stops, WR-weighted consensus, feature enrichment, temporal filtering all already captured). Below are the genuinely new items.

### New Items (not in Rounds 5-7)

| # | Item | Impact | Priority | Status |
|---|------|--------|----------|--------|
| 1 | **Trail-to-breakeven ALL systems** — Mercury 2's "lock BE at +1 ATR" works. Propagate to Alpha Engine, KIMI, Battleground. Converts near-misses → scratch trades → instant WR boost | HIGH | HIGH | TODO |
| 2 | **Consensus threshold gate** — Require WR-weighted consensus score ≥0.70 before execution (currently no minimum). Fewer trades, higher quality | MED | HIGH | TODO |
| 3 | **Liquidation heat feature** — Price gravitates toward liquidation clusters. Add as ML feature from exchange liquidation data | MED | MED | TODO |
| 4 | **Open interest delta** — Distinguishes new money entering vs short squeeze. Add as ML feature from Binance OI endpoint | MED | MED | TODO |
| 5 | **Automated strategy retirement** — Any strategy <40% WR over 15 closed picks → auto-move to paper-only. Extend beyond Alpha Engine to all systems | MED | HIGH | TODO |

### Convergent Findings Across All 4 Reviews

All 4 independent reviews (Deep Research, Llama 3.1, Sharpe-booster research, Google Studio) agree:

| Finding | Confirmed by |
|---------|-------------|
| Edge is regime filters + risk mgmt, NOT ML | All 4 |
| F&G < 15 short-circuit is highest-impact single change | All 4 |
| Correlation management is critical (max 4 LONGs) | 3/4 |
| Feature set needs enrichment beyond price/volume | 3/4 |
| Strategy pruning / kill switch is essential | 3/4 |
| Trail-to-breakeven should be system-wide | 2/4 (new) |
| Consensus threshold needed | 2/4 (new) |

### Master TODO (deduplicated across all rounds)

**HIGH priority (Week 1-2):**
- [x] Vol-of-vol filter (1-line gate, +0.27 Sharpe) — **DONE Round 9**
- [x] Intraday seasonality (01-20 UTC, +0.24 Sharpe) — **DONE Round 9**
- [ ] Correlation cap basket (ρ<0.65, +0.33 Sharpe)
- [ ] Trail-to-breakeven in Alpha Engine + KIMI (instant WR boost)
- [ ] Consensus threshold ≥0.70 in cross-aggregator
- [ ] Auto-retire strategies <40% WR @ 15 picks (all systems)

**MED priority (Week 3-4):**
- [x] RSI-14 into regime router (4th signal) — **DONE Round 9**
- [ ] 4-regime map (Fear-MR, Fear-Mom, Greed-Mom, Greed-MR)
- [ ] Feature engineering: hour_of_day, vol_cluster, OI delta, liquidation heat
- [ ] Ensemble Sharpe weighting (60d rolling per-system)
- [ ] Holding-period sweep per strategy class

**LOW priority (Week 5-8):**
- [ ] Model-drift alarm (WR drop >5% for 2 weeks → retrain)
- [ ] Shadow A/B testing (5-10% capital canary)
- [ ] Cross-asset risk budget (30% crypto cap)
- [x] Signal staleness guard (>45 min → discard) — **DONE Round 9**
- [ ] Execution slippage buffer (0.75% in all backtests)
- [ ] Pre-live checklist enforcement
- [x] Embedded carry filter (funding rate alignment, +0.55 Sharpe) — **DONE Round 9**

---

## ROUND 9 — Sharpe Booster Implementation (Feb 27, 2026)

### 5 Quick-Win Sharpe Boosters Implemented

| # | Booster | Target | File(s) Changed |
|---|---------|--------|----------------|
| 1 | **Vol-of-vol filter** — Block entries when 24h ATR volatility > 75th pctl of 90d. Exception: extreme fear (F&G<15) | +0.27 Sharpe | `mercury2/risk_engine.py` (Guard 10), `mercury2/scanner.py`, `mercury2/config.py` |
| 2 | **Intraday seasonality gate** — Only enter 01:00-20:00 UTC (London open through NY close) | +0.24 Sharpe | `mercury2/risk_engine.py` (Guard 11), `mercury2/config.py` |
| 3 | **Embedded carry filter** — LONGs blocked when funding > +25bps (longs paying), SHORTs blocked when funding < -25bps (shorts paying). Exception: extreme fear | +0.55 Sharpe | `mercury2/risk_engine.py` (Guard 12) |
| 4 | **RSI-14 in regime router** — 4th signal: blocks shorts when RSI oversold, blocks longs when RSI OB + euphoria, enables pullback buys (RSI OS in uptrend) | +1-2% WR | `cross_aggregation/regime_router.py` v2, `aggregator.py` |
| 5 | **Signal staleness guard** — Discards signals >45 min old from consensus (GitHub Actions latency protection) | +0.1 Sharpe | `cross_aggregation/aggregator.py` |

### Mercury 2 v1.4.0 — 12 Risk Guards
Guards 1-9 (existing) + Guard 10 (vol-of-vol) + Guard 11 (seasonality) + Guard 12 (carry filter)

### Regime Router v2.0 — 4-Signal Architecture
F&G index + EMA20/50 crossover + ADX(14) + **RSI-14** (new)

### Round 9b — FC-PRO Integration Audit (Feb 27, 2026)
Verified `!fc-pro` command picks up Round 9 features. Found and fixed 3 gaps:

| Gap | Fix |
|-----|-----|
| RSI-14 not passed to `should_generate_signal()` — defaulted to `None`/50.0, missing momentum exhaustion detection | Now passes `regime.get("rsi_14")` |
| No signal staleness guard — FC-PRO loads picks from JSON directly, bypassing aggregator | Added >45 min age discard in `collect_actionable_picks()` |
| Non-crypto picks could leak through (forex/equity from Alpha Engine) | Added crypto-only filter (`_is_crypto_symbol()` gate) |

*Full details: [BLUEPRINT_ANALYSIS_v3.md](../BLUEPRINT_ANALYSIS_v3.md) | [SIMPLE_BLUEPRINT](2026-02-25_0818EST_SIMPLE_BLUEPRINT.md)*

---

## ROUND 10 — Silent Workflow Failures Fixed + Social Tracker Revived (Feb 27, 2026)

### Critical Discovery: 9 Workflows Silently Losing All Data

Every workflow that commits data back to the repo was hitting **403 Permission Denied** on `git push`, but because all used `git push || true`, the error was silently swallowed and runs reported "success".

| Workflow | Schedule | Data Lost |
|---|---|---|
| `social-prediction-tracker.yml` | Every 2h | Reddit + TradingView predictions |
| `analyst-tracker.yml` (2 jobs) | Every 4h / 15min | 20 analyst picks + price validation |
| `antigravity-claudeopus.yml` | Hourly | Live picks + Discord data |
| `claude-gainer-ml-live.yml` | Every 30min | ML scanner results |
| `live_trading.yml` | Every 4h | Trading bot results |
| `live_trading_canada.yml` | Every 4h | Canada edition results |
| `live_trading_canada_free.yml` | Every 4h | Free data edition results |
| `obi-snapshot.yml` | Hourly | Order book imbalance snapshots |
| `penny-stock-picks.yml` | Weekdays 12:00 UTC | Penny stock picks + tracking |

### Root Cause & Fix
- **Cause:** Missing `permissions: contents: write` + default `GITHUB_TOKEN` lacks push rights
- **Fix:** Added `permissions: contents: write` + `token: ${{ secrets.GH_PAT || github.token }}` to all 9 workflows

### Social Prediction Tracker — Fully Revived
- **crawl4ai → scrapling:** Replaced heavy Playwright-based crawler with lightweight TLS-fingerprinted HTTP (scrapling Fetcher + requests fallback)
- **Files rewritten:** `tradingview_scraper.py`, `analyst_scraper.py` (async → sync)
- **requirements.txt:** Removed `crawl4ai>=0.4.0`, `tradingview-scraper>=0.4.20`, added `scrapling>=0.2.0`
- **Deploy:** Social tracker dashboards added to GitHub Pages (`predictions/dashboard/`, `predictions/analysts/`)
