# Smart Picks System -- Comprehensive Methodology & Live Data

**Generated:** 2026-03-23 16:10 EST (21:10 UTC) | **BTC:** $70,968 | **Fear & Greed:** 8 (Extreme Fear) | **Regime:** NEUTRAL | **Strategies:** 120+

---

## 1. Methodology Deep-Dive

### Full Pipeline Flow

```
                   +--------------------------------+
                   | KILL SWITCH CHECK              |
                   | kill_switch.py                 |
                   | - Drawdown spike (2x 95th pct) |
                   | - SL hit rate >60% of last 10  |
                   | - Win rate collapse (<25% R20) |
                   | - 5+ consecutive losses        |
                   | Severity: warning / critical / |
                   |   emergency (halts all entries) |
                   +----------------+---------------+
                                    |
                         if not killed
                                    |
                                    v
                        +--------------------------+
                        |   RAW SIGNAL GENERATION  |
                        |   120+ Strategy Files    |
                        +-----------+--------------+
                                    |
             +------+------+-------+-------+------+------+
             |      |      |       |       |      |      |
             v      v      v       v       v      v      v
          Crypto  Forex  Equity  Commod  On-Ch  Quant  Special
          75 stg  11stg  14stg   8 stg   6 stg  8+stg  (below)
             |      |      |       |       |      |      |
             |      |      |       |       |      |      |
             v      v      v       v       v      v      v
          +--------------------------------------------+
          | Special modules:                           |
          | - Alligator (4 variants: std/scalp/swing/  |
          |   daily -- Bill Williams)                   |
          | - Polymarket prediction market signals      |
          | - Statistical strategies (10 RenTech-style) |
          | - TTM Squeeze (standard + triple)           |
          | - COT Positioning (CFTC data)               |
          | - Cyclical/seasonal momentum                |
          +--------------------------------------------+
                                    |
                    generates signals for all symbols
                                    |
                                    v
                   +--------------------------------+
                   | GLOBAL TP/SL SANITY CHECK      |
                   | scanner.py (post-generation)    |
                   | Caps per asset class:           |
                   |   crypto/meme: 15%/8%           |
                   |   forex:       1%/0.5%          |
                   |   equity:      5%/3%            |
                   |   commodity:   5%/3%            |
                   |   etf:         4%/2.5%          |
                   |   bond/index:  3%/2%            |
                   |   penny:       8%/5%            |
                   +----------------+---------------+
                                    |
                                    v
                   +--------------------------------+
                   | FORWARD VALIDATOR              |
                   | forward_validator.py           |
                   | - Fetches live prices (yfinance)|
                   | - Tracks MFE/MAE               |
                   | - Checks TP/SL/trailing/expiry  |
                   | - Closes triggered picks        |
                   | - Computes per-strategy stats   |
                   | - Applies Winner Filter Gate    |
                   | - Annotates forward gate status  |
                   +----------------+---------------+
                                    |
                    active_picks.json (OPEN picks)
                    closed_picks.json (resolved)
                                    |
                                    v
                   +--------------------------------+
                   | UNIVERSAL PRICE ENRICHER       |
                   | universal_price_enricher.py     |
                   | - Binance batch (crypto ~80%)   |
                   | - yfinance fallback (stocks,    |
                   |   forex, commodities, ETFs)     |
                   | - Fills current_price for ALL   |
                   |   picks (was 175/191 missing)   |
                   | - Updates pnl_pct, checks TP/SL |
                   +----------------+---------------+
                                    |
                                    v
                   +--------------------------------+
                   | ELITE SCORER                   |
                   | elite_scorer.py                |
                   | 21 component scoring (0-100)   |
                   | Produces elite_score per pick  |
                   +----------------+---------------+
                                    |
                                    v
                   +--------------------------------+
                   | SCORE BOOSTER                  |
                   | score_booster.py               |
                   | - Family-based boosts (+15-45) |
                   | - Opposing-pick penalty (-20%) |
                   | - Age-decay penalty (-5 to -20)|
                   | - Low WR system penalty (-10)  |
                   | - Symbol dedup penalty (-20)   |
                   +----------------+---------------+
                                    |
                   dashboard_payload.json (scored)
                                    |
                                    v
            +----------------------------------------------+
            | SMART PICKS ENGINE                           |
            | smart_picks_engine.py                        |
            |                                              |
            | Inputs:                                      |
            |   1. alpha_engine/data/active_picks.json     |
            |   2. copy_trader_intel/data/active_picks.json|
            |   3. audit_trail/data/dashboard_payload.json |
            |   4. alpha_engine/data/hmm_regime_state.json |
            |   5. Live prices (Binance 6 mirrors +        |
            |      CoinGecko + KuCoin + CryptoCompare)     |
            |   6. Fear & Greed Index API                  |
            |   7. Real-time BTC 1h candles (regime check) |
            |                                              |
            | Process:                                     |
            |   - Dedup by (symbol, strategy, direction)   |
            |   - Filter: status=OPEN only                 |
            |   - Filter: age < 48h (168h for copy/whale)  |
            |   - Filter: TP remaining >= 10%              |
            |   - Filter: R:R >= 1.2 (risk/reward gate)    |
            |   - Score each pick 0-100 (5 dimensions)     |
            |   - Filter: meme LONG in bear excluded       |
            |   - Filter: wrong direction + score<70       |
            |   - Sort by smart_score descending           |
            |   - Classify into 3 tiers                    |
            |   - Top 3-4 per tier                         |
            |                                              |
            | Output: smart_picks.json (10-11 top picks)   |
            +----------------------+-----------------------+
                                   |
                                   v
            +----------------------------------------------+
            | SMART PICKS TRACKER                          |
            | smart_picks_tracker.py                       |
            |                                              |
            | - Creates versioned batches (SP-vNNN)        |
            | - Fingerprints picks to detect changes       |
            | - Snapshots PnL every 20 minutes             |
            | - Resolves batches after 24 hours            |
            | - Computes final WR, avg PnL, profit factor  |
            |                                              |
            | Output: smart_picks_history.json (max 50)    |
            +----------------------------------------------+
                                   |
                                   v
            +----------------------------------------------+
            | EQUITY TRACKER                               |
            | equity_tracker.py                            |
            |                                              |
            | - Records portfolio equity snapshots         |
            | - Tracks drawdown percentage                 |
            | - Runs after each scan cycle                 |
            +----------------------------------------------+
                                   |
                                   v
            +----------------------------------------------+
            | MULTI-TIMEFRAME GATE (being built)           |
            | mtf_gate.py                                  |
            |                                              |
            | - Checks 1H / 4H / 1D trend alignment       |
            | - EMA-9 vs EMA-20, Price vs SMA-50, MACD    |
            | - 3/3 agree: +10, 2/3: +5, 1/3: -10,       |
            |   0/3: -25 (optionally reject)              |
            | - Expected WR boost: 42% -> 55-62%           |
            | - Not yet wired into scanner pipeline        |
            +----------------------------------------------+
```

### Upstream: Elite Scorer -- Exact Formula (21 Components)

The `elite_scorer.py` computes a composite quality score for each pick across 21 components. Raw score is normalized to 0-100 via `final_score = raw_score * 100 / 90`.

| # | Component | Range | Weight Logic |
|---|-----------|-------|-------------|
| 1 | **ML Replacement Score** | 0-18 pts | Confidence >=0.80: +8, >=0.70: +6, >=0.60: +3, >=0.50: +2. Kelly >=0.35: +5, >=0.20: +3, >=0.10: +2. Strategy reputation WR >=0.65: +5, >=0.55: +3, >=0.45: +2. Capped at 18. |
| 2 | **Forward-Validated WR** | 0-30 pts | 10+ trades & WR>55%: up to 30 (scaled). 5+ trades & WR>45%: up to 22. 3+ trades & WR>40%: up to 12. Unvalidated: 5 baseline. Profit factor >=2.0 gets 15% boost. |
| 3 | **Source System Tier** | 0-20 pts | Tier 1 (alpha_engine, super_signals): 20. Tier 2 (battleground, baby_strats): 12-15. Tier 3 (kimi, luxalgo): 5-8. Copy traders: 5-10. Unknown: 3. Known losers: 0. |
| 4 | **Confluence Penalty** | -3 to 0 pts | 3+ systems agreeing: -3 (herding). 2 systems: -2. Solo: 0. ANTI-PREDICTIVE per audit (34% WR). |
| 5 | **Position Performance** | 0-10 pts | +100% PnL: 10, +50%: 9, +20%: 8, +5%: 7, 0%: 5, -5%: 3, -20%: 1, worse: 0. TP progress >80%: +3, >50%: +2, >25%: +1. |
| 6 | **Regime Bonus** | -30 to +15 pts | Ranging regime: +15 (92.3% WR). LONG in bull: +5. SHORT in bear: +15. SELL in bull: -30 (30.1% WR). Direction-aware, uses HMM regime data. |
| 7 | **Session Bonus** | 0-5 pts | Asia session (00-08 UTC): +5 (74% WR). London (08-16): +2. New York: 0. Crypto only. |
| 8 | **Age Freshness** | -5 to +5 pts | <1h: +5, <4h: +3, <12h: +1, <24h: 0, <48h: -3, >48h: -5. Swing/position immune from penalties. |
| 9 | **Risk:Reward** | 0-5 pts | R:R 2.0-2.5: 5 (sweet spot, 73.7% WR). 1.5-2.0: 3. 2.5-3.0: 2. 1.0-1.5: 1. 3.0+: 1 (TP rarely reached). |
| 10 | **Monte Carlo** | 0 pts | DISABLED. Anti-predictive (10% WR, -1.95% avg PnL per audit). Always 0. |
| 11 | **Leverage Safety** | 0-8 pts | Stop 1.5-3%: +10. Stop 1-1.5%: +6. Stop 3-4%: +4. ML conf >=0.80: +6. Forward validated (10+ trades, 60%+ WR): +4. Capped at 8. |
| 12 | **Volume Confirmation** | -20 to +5 pts | Vol ratio >=5.0: -20 (extreme spike penalty). 3.0-5.0: +2. 1.5-3.0: +5 (best zone). 1.0-1.5: +3. |
| 13 | **Signal Quality** | -5 to +10 pts | Pattern predicted WR >=0.65: +5, <=0.30: -5. Entry zone >=70: +3, <30: -3. Net edge >=20bps: +2. |
| 14 | **Meta Label** | -5 to +3 pts | P(profitable) from meta-labeler. >0.7: +3. <0.3: -5. |
| 15 | **Hindsight Winner** | 0-3 pts | Symbol in winner_patterns.json as frequently winning: +3. |
| 16 | **Skyrocket Potential** | 0-5 pts | Symbol flagged by skyrocket_detector with prob >=0.65: +5. |
| 17 | **Proven Strategy Bonus** | 0-10 pts | Academically-backed OOS strategies (Keltner compression 75% WR: +10, RSI5 momentum: +8, etc). Active copy trader families: +6-8. |
| 18 | **Strategy Track Record** | -5 to +20 pts | 5+ closed picks, WR>55%: +20. WR>45%: +10. WR<25% on 20+: -5. WR<35% on 10+: -4. (Doubled per Method 4 backtest.) |
| 19 | **Copy Trader Edge** | -6 to +12 pts | Our tracked clone/highscore history bonus. Consensus count 5+: +6, 4: +4, 3: +2. Variation forward test overlay. |
| 20 | **Risk Warning Penalty** | -3 to 0 pts | Symbols flagged in config (low liquidity, micro-cap): -3. |
| 21 | **Technical Alignment** | -25 to +5 pts | 2/3+ timeframes agree with direction: +5. 0/3 agree: -25. 1/3: -15. |

**Score Caps:**
- Super-signal cap: unproven "super" strategies capped at 52 (normalized)
- Regime + misalignment cap: adverse regime + technical misalignment = max 65
- Copy trader confidence deflated to 0.60 max (prevents gaming ML component)
- All scores clamped to 0-100

**Grade Thresholds:** S (90+), A (75+), B (55+), C (40+), D (25+), F (<25)

### Upstream: Score Booster -- Post-Processing Adjustments

After the dashboard generator runs, `score_booster.py` applies evidence-based adjustments:

| Adjustment | Logic |
|-----------|-------|
| **Family Boosts** (+15-45) | copy_trader_consensus: +45 (72% known WR). copy_trader_clones: +40 (55% WR). copy_trader_intel: +35 (65% WR). copy_trader_highscore: +35 (70% WR). kimi_signal_tracking: +35 (57% WR). rapid_fire: +20 (55% WR). binance_smart_money: +15 (46% WR). Only applied to picks with score <70. Scaled by live/closed WR. |
| **Opposing-Pick Penalty** (-20%) | Same symbol with both LONG and SHORT = contradiction. All picks for that symbol get -20% score. |
| **Age-Decay Penalty** (-5 to -20) | 4-12h: -5. 12-24h: -10. 24-48h: -15. >48h: -20. |
| **Low WR System Penalty** (-10) | Picks from systems with poor forward WR or in WEAK_SYSTEMS set. |
| **Symbol Dedup Penalty** (-20) | Multiple picks on same symbol+direction: only best-scored kept, rest -20. |
| **Consensus Lessons** (-6 to +8) | Evidence from copytrader_lessons.json: realized trader-history stats, mutation backtests. |
| **Score Cap** (100 max) | Safety net. |

### Forward Validator -- Gate Requirements

The `forward_validator.py` applies these gates before a pick becomes "active":

| Gate | Requirement | Consequence |
|------|------------|-------------|
| **Forward Gate** | Min 4 closed trades with WR >= 45% | Annotated as "validated" or "insufficient_data" / "low_wr". Not hard-blocked. |
| **Winner Filter: Asset Class** | Must be crypto or meme | Equity (35.7% WR), forex (31.4% WR) blocked |
| **Winner Filter: Confidence** | 0.55-0.75 range | Below 0.55 = noise. Above 0.75 = overfit (49% WR) |
| **Winner Filter: R:R Ratio** | 1.5-3.0 range | Below 1.5 = bad risk. Above 3.0 = unreachable TP (29.7% WR) |
| **Winner Filter: Banned Systems** | Not in banned list | rapid_fire, stocks_competition, mercury2_fast, penny_momentum, etc. |
| **Winner Filter: Death Zone** | UTC 13:00-16:00 | Soft penalty: -10 score (11-21% WR during these hours) |
| **Core Whitelist Kill List** | Strategy not in kill_list | Hard block for eliminated strategies |
| **VPIN Detector** | Volume-synchronized PIN check | High VPIN = toxic flow warning |
| **Cooldown Gate** | Consecutive loss check | Skip if recent losses exceed threshold |
| **Deflated Sharpe** | Adjusted for multiple testing | Strategies with inflated Sharpe penalized |
| **White's Reality Check** | Multiple hypothesis testing | Adjusted p-value > 0.05 = data-snooped |
| **GARCH Volatility** | Conditional volatility forecast | Adjusts SL/TP for current vol regime |
| **SL Calibrator** | ATR-based SL/TP calibration | Adjusts stops to market conditions |

### Smart Picks Engine -- 5-Dimension Scoring (0-100)

This is the FINAL scoring layer that selects the actual "Smart Picks" from all scored active picks.

| Dimension | Max Pts (Crypto) | Max Pts (Non-Crypto) | Scoring Logic |
|-----------|-----------------|---------------------|---------------|
| **1. Direction/Regime Match** | 40 | 20 | LONG in bull OR SHORT in bear = full points. Neutral = half. Opposing = 0. Real-time regime from BTC 1h candles (4h avg vs 8h avg, >1% change). |
| **2. Elite/Quality Score** | 20 | 30 | `min(elite_score, 100) / 100 * max_pts`. Non-crypto gets higher quality weight since crypto regime is irrelevant for forex/equity. |
| **3. Freshness** | 15 | 15 | <1h: 15, <4h: 12, <12h: 8, <24h: 4, >24h: 0. |
| **4. TP Remaining Upside** | 15 | 15 | >70% to TP: 15, 50-70%: 10, 30-50%: 5, <30%: 0. Pick near TP (<10%) filtered out entirely. |
| **5. Currently Winning** | 10 | 10 | PnL > 0: 10. PnL = 0: 5. PnL < 0: 0. Momentum confirmation. |

### What Makes a Pick "Smart" vs Just "Active"

The system has ~572 active picks at any time. Only 10-11 become "Smart Picks" per batch. The selection process:

1. **Only OPEN picks** -- TP_HIT, SL_HIT, CLOSED are excluded
2. **Must have live price** -- no price = excluded (151 picks excluded this cycle)
3. **Must be fresh** -- >48h old excluded (44 excluded), copy/whale trades get 168h grace
4. **Must have upside** -- TP remaining <10% excluded (16 excluded)
5. **Must have favorable R:R** -- R:R < 1.2 excluded (unfavorable risk/reward)
6. **Must not oppose regime** -- wrong direction + score<70 excluded (197 excluded this cycle)
7. **No meme LONGs in bear** -- DOGE, SHIB, PEPE, etc. can't go LONG in bear regime
8. **Scored and ranked** -- remaining picks scored 0-100, sorted descending
9. **3-tier classification** -- SCALP (<2h age or forex), SWING (default), POSITION (>24h age or macro)
10. **Top 3-4 per tier** -- max 4 SCALP, 4 SWING, 3 POSITION = up to 11 picks per batch

This cycle: 572 active picks --> 84 scored --> 11 Smart Picks selected.

---

## 2. Current Active Smart Picks (SP-v015)

**Batch:** SP-v015 | **Generated:** 2026-03-23 16:10 EST | **Regime:** NEUTRAL | **F&G:** 8 | **BTC:** $70,880

### SCALP Tier (4 picks)

| Symbol | Dir | Score | Entry | TP | SL | Live | PnL% | R:R | Strategy | Age | Reason |
|--------|-----|-------|-------|----|----|------|-------|-----|----------|-----|--------|
| BNBUSDT | SHORT | 84 | 638.84 | 619.67 | 648.42 | 640.08 | -0.19% | 2.2x | cg_whale_divergence | 1.5h | Direction matches BEAR +40, Quality 87 +17, Fresh +12, 103% upside +15 |
| SIRENUSDT | SHORT | 83 | 2.301 | 2.175 | 2.370 | N/A | -7.31% | 2.97x | binance_smart_money | 1.6h | Direction matches BEAR +40, Quality 78 +16, Fresh +12, 233% upside +15 |
| BTCUSDT | SHORT | 80 | 70,932 | 70,328 | 71,348 | 70,968 | -0.05% | 1.18x | keltner_compression_v1 | 0.3h | Direction matches BEAR +40, Fresh +15, 91% upside +15, Winning +10 |
| AVAXUSDT | LONG | 70 | 9.501 | 10.014 | 9.216 | 9.55 | 0.52% | 1.46x | binance_smart_money | 1.6h | Quality 64 +13, Fresh +12, 92% upside +15, Winning +10 |

### SWING Tier (4 picks)

| Symbol | Dir | Score | Entry | TP | SL | Live | PnL% | R:R | Strategy | Age | Reason |
|--------|-----|-------|-------|----|----|------|-------|-----|----------|-----|--------|
| BTCUSDT | SHORT | 77 | 71,440 | 69,297 | 72,869 | 70,968 | 0.66% | 0.8x | copy_hl_lb_None | 2.8h | Direction matches BEAR +40, Fresh +12, 74% upside +15, Winning +10 |
| LINKUSDT | SHORT | 77 | 9.191 | 8.915 | 9.374 | 9.15 | 0.45% | 1.05x | ct_consensus_linkusdt_short | 3.0h | Direction matches BEAR +40, Fresh +12, 85% upside +15, Winning +10 |
| XRPUSDT | LONG | 77 | 1.437 | 1.480 | 1.408 | 1.439 | 0.12% | 1.48x | ct_consensus_xrpusdt_long | 3.0h | Direction matches BULL +40, Fresh +12, 100% upside +15, Winning +10 |
| LTCUSDT | SHORT | 77 | 56.017 | 54.336 | 57.137 | 55.80 | 0.39% | 1.05x | ct_consensus_ltcusdt_short | 3.0h | Direction matches BEAR +40, Fresh +12, 85% upside +15, Winning +10 |

### POSITION Tier (3 picks)

| Symbol | Dir | Score | Entry | TP | SL | Live | PnL% | R:R | Strategy | Age | Reason |
|--------|-----|-------|-------|----|----|------|-------|-----|----------|-----|--------|
| ETHUSDT | SHORT | 76 | 2,169 | 2,139 | 2,207 | 2,160 | 0.38% | 0.4x | clone_hl_copy_lb_None | 105.3h | Direction matches BEAR +40, Quality 80 +16, 65% upside +10, Winning +10 |
| RENDERUSDT | SHORT | 75 | 1.654 | 1.646 | 1.671 | 1.694 | -2.42% | 2.59x | clone_hl_copy_lb_None | 105.3h | Direction matches BEAR +40, Quality 100 +20, 495% upside +15 |
| RENDERUSDT | SHORT | 72 | 1.653 | 1.646 | 1.670 | 1.694 | -2.48% | 2.44x | clone_hl_copy_whale_433roi | 105.3h | Direction matches BEAR +40, Quality 85 +17, 564% upside +15 |

**Exclusion Summary (this cycle):** wrong_direction: 197, no_price: 151, too_stale: 44, near_tp: 16, meme_long_bear: 0

---

## 3. Closed/Resolved Smart Picks Batches

Only 1 batch has been fully resolved (system launched Mar 22, 2026).

### SP-v001 (RESOLVED)

| Field | Value |
|-------|-------|
| Version | SP-v001 (Mar 22, 9:50 AM EST) |
| Regime | BEAR |
| F&G | 10 |
| BTC at Open | N/A |
| Picks | 1 |
| Duration | 24.1 hours |
| Final WR | 0.0% |
| Final Avg PnL | -8.10% |
| Profit Factor | 0.0 |
| TP Hits | 0 |
| SL Hits | 1 |

| Symbol | Dir | Score | Entry | TP | SL | Final PnL | Strategy | Result |
|--------|-----|-------|-------|----|----|-----------|----------|--------|
| GRIFFAINUSDT | SHORT | 77 | 0.008715 | 0.008279 | 0.008933 | -8.10% | hl_funding_fade | SL_HIT (LOST) |

**Note:** This was the very first batch with only 1 pick. The pick was profitable (+1.32%) at the 6.7h snapshot but reversed and hit SL by hour 22.9.

### Active Batches Summary (SP-v002 through SP-v015)

| Batch | Picks | Latest WR | Avg PnL | TP Hits | SL Hits | Age | Key Symbols |
|-------|-------|-----------|---------|---------|---------|-----|-------------|
| SP-v002 | 11 | 7/11 (64%) | -0.36% | 0 | 1 | 7.5h | XRPUSDT(x4 LONG), ENAUSDT(x2 SHORT), LTCUSDT, JTOUSDT, TONUSDT, NEARUSDT, BTCUSDT |
| SP-v003 | 11 | 7/11 (64%) | +0.70% | 1 | 0 | 7.0h | BTCUSDT(x3 SHORT), XRPUSDT(x2 LONG), ENAUSDT, ETHUSDT, SOLUSDT, ZECUSDT, LTCUSDT, GMXUSDT |
| SP-v004 | 11 | 10/11 (91%) | +1.32% | 2 | 0 | 6.5h | BTCUSDT(x2), STXUSDT, XRPUSDT(x2), DOTUSDT, ENAUSDT(x2), LTCUSDT, LINKUSDT, AAVEUSDT |
| SP-v005 | 11 | 9/11 (82%) | +1.28% | 1 | 0 | 6.3h | BTCUSDT(x2), ETHUSDT, FETUSDT, DOTUSDT, ENAUSDT(x2), XRPUSDT, LTCUSDT, LINKUSDT, AAVEUSDT |
| SP-v006 | 11 | 8/11 (73%) | +1.01% | 1 | 0 | 5.8h | XRPUSDT, ETHUSDT, BTCUSDT, STXUSDT, DOTUSDT, NEARUSDT, ENAUSDT(x2), LTCUSDT, LINKUSDT, AAVEUSDT |
| SP-v007 | 11 | 5/11 (45%) | -0.19% | 0 | 1 | 5.5h | FETUSDT, ETHUSDT, BTCUSDT(x3), STXUSDT, ASTERUSDT, NEARUSDT, LTCUSDT, FILUSDT |
| SP-v008 | 7 | 5/7 (71%) | +0.30% | 0 | 0 | 3.6h | BTCUSDT, PENGUUSDT, ETHUSDT(x2), LTCUSDT, RUNEUSDT, BANANAUSDT |
| SP-v009 | 11 | 4/11 (36%) | -0.71% | 0 | 1 | 3.4h | XRPUSDT(x3), BTCUSDT, STXUSDT, PENGUUSDT, ETHUSDT, FETUSDT, LTCUSDT, ZROUSDT, LINKUSDT |
| SP-v010 | 11 | 7/11 (64%) | -0.03% | 0 | 1 | 3.2h | XRPUSDT, BTCUSDT, AVAXUSDT(x2), PENGUUSDT, STXUSDT, ETHUSDT, NEARUSDT, LTCUSDT, WLFIUSDT, RUNEUSDT |
| SP-v011 | 11 | 7/11 (64%) | -0.57% | 0 | 2 | 2.7h | BTCUSDT, APTUSDT, XRPUSDT, DOGEUSDT, SUIUSDT(x2), STXUSDT, ETHUSDT, LTCUSDT, WLFIUSDT, TRXUSDT |
| SP-v012 | 9 | 5/9 (56%) | -0.08% | 0 | 1 | 1.7h | BTCUSDT(x2), XRPUSDT, XMRUSDT, SUIUSDT(x2), STXUSDT, NEARUSDT, UUSDT |
| SP-v013 | 8 | 5/8 (63%) | -0.10% | 0 | 1 | 1.3h | XRPUSDT, XMRUSDT, BTCUSDT(x2), SUIUSDT, STXUSDT, ETHUSDT, NEARUSDT |
| SP-v014 | 9 | 6/9 (67%) | +0.01% | 0 | 1 | 1.0h | XRPUSDT(x2), XMRUSDT, BTCUSDT(x2), LINKUSDT, SUIUSDT, STXUSDT, UUSDT |
| SP-v015 | 11 | 8/11 (73%) | +8.97% | 1 | 2 | 0.0h | BNBUSDT, SIRENUSDT, BTCUSDT(x2), AVAXUSDT, LINKUSDT, XRPUSDT, LTCUSDT, ETHUSDT, RENDERUSDT(x2) |

---

## 4. Top 20 Picks by Score (All Active Picks)

Scores from dashboard_payload.json (elite_score after booster), with live Binance prices as of 2026-03-23 21:10 UTC.

| Rank | Score | Grade | Symbol | Dir | Entry | Live | PnL% | Strategy | Source System |
|------|-------|-------|--------|-----|-------|------|-------|----------|---------------|
| 1 | 96 | S | CT=F | SHORT | 67.16 | N/A | 0.00% | cot_positioning | alpha_engine |
| 2 | 91 | A | SPXUSDT | SHORT | 0.3188 | N/A | 0.00% | ct_consensus_spxusdt_short | copy_trader_consensus |
| 3 | 91 | A | MONUSDT | SHORT | 0.02268 | N/A | 0.00% | ct_consensus_monusdt_short | copy_trader_consensus |
| 4 | 90 | S | BAC | LONG | 47.71 | N/A | -0.40% | strong consensus | super_signals |
| 5 | 89 | A | XPLUSDT | SHORT | 0.1023 | 0.0963 | +5.86% | copy_hl_x35767_113M | copy_trader_intel |
| 6 | 86 | A | COST | LONG | 965.73 | N/A | 0.00% | stocks_rsi2_pullback | alpha_engine |
| 7 | 86 | A | PFE | LONG | 26.77 | N/A | 0.00% | stocks_rsi2_pullback | alpha_engine |
| 8 | 86 | A | PUMPUSDT | SHORT | 0.001968 | 0.001833 | +6.86% | copy_hl_x35767_113M | copy_trader_intel |
| 9 | 86 | A | XMRUSDT | SHORT | 118.70 | 118.70 | 0.00% | copy_hl_x35767_113M | copy_trader_intel |
| 10 | 83 | A | JNJ | LONG | 235.42 | N/A | 0.00% | stocks_rsi2_pullback | alpha_engine |
| 11 | 80 | S | GBPJPY=X | SHORT | 212.73 | N/A | 0.00% | forex_rsi2_mean_reversion | alpha_engine |
| 12 | 80 | B | INJUSDT | LONG | 3.087 | 3.096 | +0.28% | ct_consensus_injusdt_long | copy_trader_consensus |
| 13 | 80 | B | WLFIUSDT | LONG | 0.0940 | 0.1039 | +10.52% | ct_consensus_wlfiusdt_long | copy_trader_consensus |
| 14 | 79 | A | KC=F | LONG | 306.90 | N/A | 0.00% | cot_positioning | alpha_engine |
| 15 | 78 | A | NG=F | SHORT | 2.885 | N/A | 0.00% | cta_tsmom_blend | alpha_engine |
| 16 | 78 | A | TLT | SHORT | 86.39 | N/A | 0.00% | cta_tsmom_blend | alpha_engine |
| 17 | 78 | A | EURGBP=X | LONG | 0.8647 | N/A | 0.00% | myfxbook_retail_contrarian | alpha_engine |
| 18 | 77 | B | AAVEUSDT | SHORT | 112.33 | 110.39 | +1.72% | ct_consensus_aaveusdt_short | copy_trader_consensus |
| 19 | 77 | B | PENGUUSDT | SHORT | 0.007257 | 0.007059 | +2.73% | ct_consensus_penguusdt_short | copy_trader_consensus |
| 20 | 77 | B | SYRUPUSDT | SHORT | 0.2495 | 0.2355 | +5.61% | ct_consensus_syrupusdt_short | copy_trader_consensus |

**Note:** Many top-scored picks (CT=F, BAC, COST, PFE, JNJ, GBPJPY=X, KC=F, NG=F, TLT, EURGBP=X) are non-crypto assets without live Binance prices. Their PnL cannot be computed in real-time from this system.

---

## 5. Bottom 20 Picks by Score (All Active Picks)

All bottom picks score 0 and come from the `rapid_fire` source system.

| Rank | Score | Grade | Symbol | Dir | Entry | Live | PnL% | Strategy | Source System |
|------|-------|-------|--------|-----|-------|------|-------|----------|---------------|
| 553 | 0 | D | ETHUSDT | LONG | 2,156.01 | 2,160.28 | +0.20% | macd_rsi_confluence | rapid_fire |
| 554 | 0 | D | TAOUSDT | LONG | 270.00 | 288.80 | +6.96% | macd_rsi_confluence | rapid_fire |
| 555 | 0 | F | LINKUSDT | LONG | 9.11 | 9.15 | +0.44% | macd_rsi_confluence | rapid_fire |
| 556 | 0 | D | SUIUSDT | LONG | 0.9621 | 0.9571 | -0.52% | macd_rsi_confluence | rapid_fire |
| 557 | 0 | F | DOGEUSDT | SHORT | 0.09416 | 0.09506 | -0.96% | macd_crossover | rapid_fire |
| 558 | 0 | F | LINKUSDT | SHORT | 9.13 | 9.15 | -0.22% | macd_crossover | rapid_fire |
| 559 | 0 | D | WIFUSDT | LONG | 0.181 | 0.189 | +4.42% | volume_spike_breakout | rapid_fire |
| 560 | 0 | D | PEPEUSDT | LONG | 0.00000343 | 0.0000035 | +2.04% | macd_rsi_confluence | rapid_fire |
| 561 | 0 | D | WIFUSDT | LONG | 0.181 | 0.189 | +4.42% | macd_crossover | rapid_fire |
| 562 | 0 | D | TONUSDT | SHORT | 1.263 | 1.311 | -3.80% | rsi_overbought | rapid_fire |
| 563 | 0 | F | ANKRUSDT | LONG | 0.00574 | 0.00527 | -8.19% | macd_rsi_confluence | rapid_fire |
| 564 | 0 | F | ANKRUSDT | LONG | 0.00574 | 0.00527 | -8.19% | macd_crossover | rapid_fire |
| 565 | 0 | D | PEPEUSDT | LONG | 0.00000346 | 0.0000035 | +1.16% | volume_spike_breakout | rapid_fire |
| 566 | 0 | D | UUSDT | LONG | 1.0003 | 1.0002 | -0.01% | macd_crossover | rapid_fire |
| 567 | 0 | F | PIXELUSDT | LONG | 0.01011 | 0.00925 | -8.51% | macd_crossover | rapid_fire |
| 568 | 0 | F | LINKUSDT | LONG | 9.15 | 9.15 | 0.00% | volume_spike_breakout | rapid_fire |
| 569 | 0 | F | LINKUSDT | LONG | 9.15 | 9.15 | 0.00% | macd_crossover | rapid_fire |
| 570 | 0 | F | DOGEUSDT | SHORT | 0.0947 | 0.09506 | -0.38% | rsi_overbought | rapid_fire |
| 571 | 0 | F | ZROUSDT | SHORT | 2.033 | 2.215 | -8.95% | rsi_overbought | rapid_fire |
| 572 | 0 | F | ETHUSDT | SHORT | 2,145.55 | 2,160.28 | -0.69% | rsi_overbought | rapid_fire |

**Note:** All bottom picks are from `rapid_fire` system (macd_crossover, macd_rsi_confluence, rsi_overbought, volume_spike_breakout). This system is in the banned list and gets -10 low WR penalty plus -20 age decay plus -20 dedup penalty, driving scores to 0. Interestingly, some of these zero-score picks are actually profitable (TAOUSDT +6.96%, WIFUSDT +4.42%) -- the score correctly identifies the system as unreliable even when individual picks occasionally win.

---

## 6. Performance Analysis

### Overall System Stats (from dashboard_payload.json)

| Metric | Value |
|--------|-------|
| Total Active Picks | 572 |
| Total Closed Picks | 11,342 |
| Total Resolved | 11,169 |
| Overall Win Rate | 41.9% |
| Total PnL | +2,951.33% |
| Profit Factor | 1.19 |
| Avg Win | +4.04% |
| Avg Loss | -2.46% |
| Expectancy | +0.26% per trade |
| Net Sharpe (annual) | 2.95 |
| Sortino (annual) | 18.85 |
| Calmar Ratio | 11.34 |

### Smart Picks WR vs Overall WR

| Metric | Smart Picks (all active batches) | Overall System |
|--------|--------------------------------|----------------|
| Win Rate | ~64% (median across 14 active batches) | 41.9% |
| Avg PnL | Variable (+8.97% to -0.71% across batches) | +0.26% |
| Best Batch | SP-v004: 91% WR, +1.32% avg PnL, 2 TP hits | -- |
| Worst Active | SP-v009: 36% WR, -0.71% avg PnL, 1 SL hit | -- |
| Only Resolved | SP-v001: 0% WR, -8.10% (1 pick, SL hit) | -- |

**Key Finding:** Smart Picks achieve approximately 64% median WR compared to the system's overall 41.9% WR. The 5-dimension scoring effectively filters quality signals, particularly through regime alignment (the heaviest component at 40 pts).

### Score-to-PnL Correlation

From the dashboard payload data:
- **Top-scored picks (score 77-96):** Mix of crypto and non-crypto. Crypto picks with live prices showing +1.72% to +10.52% PnL.
- **Bottom-scored picks (score 0):** All from rapid_fire system. Avg PnL approximately -1.2% with high variance (-8.95% to +6.96%).
- **Concentration warning:** 153.6% of total system PnL comes from FETUSDT trades alone. Removing FETUSDT drops overall PnL from +2,951% to -1,582%.

### Best/Worst Performing Strategies Within Smart Picks

**Recurring top strategies in Smart Picks:**
1. `copy_hl_whale_24.5M` -- Appears in 8/15 batches, consistently scored 85
2. `copy_hl_NMTD_25M` -- Appears in 3/15 batches, scored 83-85
3. `copy_hl_whale_20.7M` -- Appears in 4/15 batches, scored 83
4. `ct_consensus_*` -- Consensus picks appear in later batches, scored 77
5. `luxalgo_confluence` -- Appears in 10/15 batches, scored 67-77

**Weakest strategies that still made Smart Picks:**
1. `macd_crossover` -- Scored 60-69, usually lowest-tier
2. `rsi_overbought` -- Scored 68-77, mixed results
3. `incubator_gainer*` -- Scored 57-70, newer strategies

### Direction Breakdown

Across all 15 Smart Picks batches:

| Direction | Picks | Approx % | Dominant Regime |
|-----------|-------|----------|-----------------|
| SHORT | ~110 | ~75% | BEAR (batches 1-14 were in bear/neutral regime) |
| LONG | ~37 | ~25% | Mostly XRPUSDT and AVAXUSDT counter-trend plays |

**Note:** The heavy SHORT bias is correct for the current bear market (F&G = 8, Extreme Fear). The regime alignment dimension (40 pts) naturally selects SHORT picks in bear markets. The few LONGs that make it through have strong quality scores compensating for the regime mismatch.

---

## Data Sources & Signal Generation

Signals feeding into Smart Picks originate from these strategy files (120+ total strategies):

| Strategy Category | File(s) | Strategies | Asset |
|-------------------|---------|------------|-------|
| Core crypto | `real_time_scanner.py`, `crypto_strategies.py` | 33 core | Crypto |
| On-chain (original) | `onchain_strategies.py` | 10 | Crypto |
| On-chain macro | `onchain_macro_strategies.py` | 6 (MVRV, SOPR, NVT, SSR, DXY inverse, yield curve) | Crypto/Macro |
| Quant (original) | `quant_strategies.py` | 4 (TSMOM, pairs, momentum blend, OI divergence) | Crypto |
| Quant research (statistical) | `statistical_strategies.py` | 10 (multi-sigma, O-U, variance ratio, Hurst, BB-KC squeeze, autocorrelation, volume profile, half-life, CVD, multi-factor composite) | Multi |
| TTM Squeeze | `ttm_squeeze.py` | 2 (standard + triple compression) | Multi |
| Alligator | `alligator_strategies.py` | 4 (standard 4h, scalp 1h, swing 4h, daily 1d) | Crypto |
| Event-driven | `event_strategies.py` | 8 | Crypto |
| Advanced | `advanced_strategies.py` | 8 | Crypto |
| Community/spike | various | 12 | Crypto |
| Polymarket | `polymarket_signals.py` | Prediction market probability signals | Crypto |
| COT Positioning | `cot_positioning.py` | CFTC commitment of traders data | Commodities/Forex |
| Cyclical/seasonal | `cyclical_strategies.py`, `cyclic_momentum_strategy.py` | Seasonal and cycle-based | Multi |
| Forex | `forex_strategies.py` | 11 | Forex |
| Equity | `equity_strategies.py` | 14 | Equity |
| Commodities | `commodities_strategies.py` | 8 (seasonal, macro, mean-reversion, spread, momentum, divergence) | Commodities |
| TradingView | `tradingview_strategies*.py` | 14 Pine Script | Multi |
| Copy trader | `copy_trader_intel/` | Whale/clone/consensus scrapers | Crypto |
| Incubator | `incubator/` | Permutation engine | Crypto |
| Rapid fire | `rapid_fire/` | macd_crossover, rsi_overbought, volume_spike | Crypto |
| Battleground | `battleground/` | Aggregated signals | Multi |

**Strategy count breakdown:** ~75 crypto core + 8 quant research + 6 on-chain/macro + 4 alligator + polymarket + 2 TTM squeeze + 11 forex + 14 equity + 8 commodities + COT + cyclical + copy traders + TradingView = **120+ strategies**

---

## File Paths

| File | Purpose |
|------|---------|
| `alpha_engine/smart_picks_engine.py` | 5-dimension scoring engine (runs every 20 min) |
| `alpha_engine/smart_picks_tracker.py` | Batch versioning and PnL tracking |
| `alpha_engine/elite_scorer.py` | 15-component elite score (0-100 normalized) |
| `alpha_engine/score_booster.py` | Post-processing boosts/penalties |
| `alpha_engine/forward_validator.py` | Forward validation loop with gates |
| `alpha_engine/data/smart_picks.json` | Current batch output |
| `alpha_engine/data/smart_picks_history.json` | All tracked batches (max 50) |
| `alpha_engine/data/hmm_regime.json` | HMM regime detector output |
| `alpha_engine/data/active_picks.json` | All open picks from all strategies |
| `alpha_engine/data/strategy_performance.json` | Per-strategy closed-pick stats |
| `audit_trail/data/dashboard_payload.json` | Aggregated dashboard data |
| `.github/workflows/smart-picks-tracker.yml` | GitHub Actions workflow (*/20 cron) |
| `audit_dashboard/template.html` | Dashboard with Smart Picks tab |
| `alpha_engine/regime_flip_detector.py` | Momentum-confirmed regime detector |
| `alpha_engine/kill_switch.py` | Auto kill switch (drawdown/SL rate/WR/consecutive loss monitoring) |
| `alpha_engine/universal_price_enricher.py` | Fills prices for all asset classes (Binance + yfinance) |
| `alpha_engine/equity_tracker.py` | Portfolio equity curve snapshots after each scan |
| `alpha_engine/mtf_gate.py` | Multi-timeframe confirmation gate (1H/4H/1D -- being wired in) |
| `alpha_engine/onchain_macro_strategies.py` | MVRV, SOPR, NVT, SSR, DXY inverse, yield curve (6 strategies) |
| `alpha_engine/alligator_strategies.py` | Bill Williams Alligator (4 variants: std/scalp/swing/daily) |
| `alpha_engine/polymarket_signals.py` | Polymarket prediction market probability signals |
| `alpha_engine/commodities_strategies.py` | 8 commodity strategies (seasonal, macro, spread, momentum) |
| `alpha_engine/statistical_strategies.py` | 10 RenTech-inspired statistical strategies (Wave 7) |
| `alpha_engine/ttm_squeeze.py` | TTM Squeeze breakout (standard + triple compression) |
| `alpha_engine/cot_positioning.py` | CFTC Commitment of Traders positioning signals |
| `alpha_engine/cyclical_strategies.py` | Seasonal/cyclical momentum strategies |
| `alpha_engine/data/regime_report.json` | Current regime state + momentum data |
| `alpha_engine/data/kill_switch_status.json` | Kill switch current state and severity |
| `alpha_engine/data/polymarket_signals.json` | Polymarket prediction market signal output |
| `alpha_engine/data/optimal_tp_sl.json` | Data-driven TP/SL recommendations |
| `alpha_engine/data/strategy_kill_list.json` | 391 killed strategies |
| `alpha_engine/data/strategy_tiers.json` | PROVEN/ACTIVE/PROBATION/KILL tiers |
| `alpha_engine/feedback_loop.py` | Logistic regression win predictor |
| `alpha_engine/check_active_picks.py` | Recurring quality analysis (30-min cron) |

---

## 7. Data Refresh Frequencies & Latency

Understanding refresh cadence is critical for pick quality. Stale data = bad picks.

| Data Source | Refresh Frequency | Latency Risk | Impact on Picks |
|---|---|---|---|
| **Binance OHLCV** | Real-time via API | <1s | Entry/exit prices accurate |
| **Dashboard payload** (dashboard_payload.json) | Every 30 min (CI workflow) | Up to 30 min stale | Scores may lag market moves |
| **Smart Picks batch** (smart_picks.json) | Every 20 min (*/20 cron) | Up to 20 min stale | Pick selection may miss fast moves |
| **Regime detection** (regime_report.json) | Every 30 min (audit-dashboard workflow) | Up to 30 min stale | **CRITICAL: Regime flips during gap cause wrong-direction picks** |
| **Copy trader data** (copy_trader_intel/) | Every 15 min (copy-trader-intelligence workflow) | Up to 15 min | Trader positions may close before we see them |
| **HMM regime** (hmm_regime.json) | Every scan cycle (~30 min) | Up to 30 min | Transition probabilities update slowly |
| **ML model scores** | Per-pick at generation time | N/A | Champion model currently awaiting retrain (39 features) |
| **Fear & Greed Index** | 2-hour cache (alternative.me) | Up to 2h stale | Acceptable for slow-moving sentiment |
| **CryptoPanic news** | 24-hour cache (API limit: 100/month) | Up to 24h stale | News sentiment very delayed |
| **Strategy performance** | Updated on each trade close | Real-time | Accurate for proven/probation status |

### Known Latency Issues That Cause Bad Picks

1. **Regime Fakeout (CRITICAL):** If BTC rallies +4% (regime = BULLISH) then reverses -2% within a 30-min gap, picks generated during the gap are wrong-direction. **Mitigation:** Momentum-confirmed regime detector (RSI + ADX + SMA slope) catches most fakeouts. Hysteresis requires 2 consecutive confirmations.

2. **Copy Trader Position Staleness:** A whale closes their position, but our 15-min scan hasn't detected it yet. We generate a pick mirroring a position that no longer exists. **Mitigation:** Age-decay in score_booster penalizes older picks.

3. **ML Champion Incompatibility:** When the ML model's feature set changes, it cannot score picks until retrained. All picks fall back to heuristic scoring (AUC 0.51 = random). **Current status: Awaiting retrain with 39 clean features.**

4. **Dashboard Payload Staleness:** The 30-min refresh means closed picks may still appear as "active" for up to 30 minutes. TP/SL hits are not reflected in real-time.

---

## 8. Regime Detection Methodology

### Primary: Momentum-Confirmed Detector (`regime_flip_detector.py`)

Uses BTC 24h change + 4H candle momentum confirmation:

| Indicator | Source | Threshold |
|---|---|---|
| BTC 24h % change | Binance ticker/24hr | >+2% = bullish signal, <-2% = bearish signal |
| RSI (14-period, 4H) | Binance 4H klines (30 bars) | >50 confirms bullish, <50 confirms bearish |
| SMA slope (5 vs 20) | 4H closes | Positive = uptrend, negative = downtrend |
| ADX (14-period) | 4H candles | >20 = trend has conviction, <15 = no trend |
| ATR % | 4H candles | Volatility measure for position sizing |
| Drawdown from 6-bar high | 4H closes | Detects reversals within trends |

### 7 Regime States

| State | Condition | Position Bias |
|---|---|---|
| **BULLISH** | 24h > +2% AND RSI > 50 AND (slope > 0 OR RSI > 55) | Strong LONG bias |
| **BEARISH** | 24h < -2% AND RSI < 50 AND (slope < 0 OR RSI < 45) | Strong SHORT bias |
| **CHOPPY** | -2% < 24h < +2%, no clear momentum | Reduce all positions, favor mean-reversion |
| **WEAKENING_BULL** | 24h > +2% BUT RSI < 48 OR slope < -0.1% (fakeout!) | Caution on LONGs, allow hedging SHORTs |
| **WEAKENING_BEAR** | 24h < -2% BUT RSI > 52 OR slope > +0.1% | Caution on SHORTs, recovery possible |
| **LEANING_BULL** | -2% < 24h < +2% BUT RSI > 60 AND slope > 0.2% | Mild LONG preference |
| **LEANING_BEAR** | -2% < 24h < +2% BUT RSI < 40 AND slope < -0.2% | Mild SHORT preference |

### Hysteresis Rules
- **confirm_bars = 2:** Regime must be confirmed for 2 consecutive checks before flipping
- **min_dwell = 3:** Once flipped, regime cannot flip again for 3 checks (prevents oscillation)

### Secondary: HMM Regime (`hmm_regime.py`)
- 3-state Hidden Markov Model (BULL/BEAR/CHOP) on BTC daily returns
- Provides transition probabilities (e.g., P(BULL→BEAR) = 0.15)
- Used as supplementary signal, not primary

### Impact on Smart Picks
- Regime match is **40% of Smart Pick score** (crypto) or 20% (non-crypto)
- WEAKENING_BULL: LONGs get -10% penalty, SHORTs get +0% (no bonus, no penalty)
- BULLISH: LONGs get +40%, SHORTs get -35%
- BEARISH: SHORTs get +40%, LONGs get -35%

---

## 9. Non-Crypto Assets in Smart Picks

Previously, Smart Picks only selected crypto picks. Non-crypto assets (forex, equity, commodity, bond, ETF) are now included with adjusted scoring and tier assignments.

### Why Non-Crypto Was Excluded Before

The forward validator's Winner Filter originally hard-blocked non-crypto assets because their historical WR was low (equity 35.7%, forex 31.4%). However, these poor results were caused by two issues:
1. **No live prices** -- 175 of 191 non-crypto picks showed "---" on the dashboard because only Binance-listed symbols got price updates.
2. **Regime mismatch** -- crypto regime (BTC-based) was being applied at full weight (40%) to forex and equity picks, penalizing picks that had nothing to do with BTC direction.

### How Non-Crypto Scoring Works Now

The `smart_picks_engine.py` detects non-crypto picks via category field or `=` in symbol (e.g., `GBPJPY=X`, `CT=F`) and applies adjusted weights:

| Dimension | Crypto Max Pts | Non-Crypto Max Pts | Rationale |
|-----------|---------------|-------------------|-----------|
| Direction/Regime Match | 40 | 20 | Crypto regime (BTC-based) is less relevant for forex/equity |
| Elite/Quality Score | 20 | 30 | Strategy track record matters more without reliable regime data |
| Freshness | 15 | 15 | Same for all assets |
| TP Remaining Upside | 15 | 15 | Same for all assets |
| Currently Winning | 10 | 10 | Same for all assets |

### Non-Crypto Tier Assignments

Instead of purely age-based tiers, non-crypto picks get category-based tier defaults:

| Asset Class | Default Tier | Typical Hold | TP Range |
|------------|-------------|-------------|----------|
| Forex (`forex`, `fx`, or `=` in symbol) | SCALP | 1-4h | < 1% |
| Equity / Commodity | SWING | 4-48h | 1-5% |
| Bond / Macro | POSITION | 2-7d | > 1% |

### Universal Price Enricher

The `universal_price_enricher.py` module runs after the scanner to fill prices for all non-crypto picks:
1. **Binance batch endpoint** -- covers ~80% of crypto symbols in one API call
2. **yfinance fallback** -- fetches stocks, forex pairs, commodities, ETFs
3. Updates `current_price`, `last_checked`, `pnl_pct`, and checks TP/SL hits

This runs as part of the GitHub Actions workflow (`alpha-engine-live.yml`) after the main scan.

Non-crypto picks that still lack a live price after enrichment are excluded from Smart Picks (`no_price` filter).

---

## 10. Global TP/SL Sanity Check (Asset Class Caps)

After signal generation, `scanner.py` enforces maximum TP/SL percentages per asset class. This prevents unrealistic targets (e.g., 30-172% TP on equities from analyst targets, commodity-scale ATR multipliers on ETFs).

| Asset Class | Max TP % | Max SL % | Notes |
|------------|---------|---------|-------|
| `crypto` / `meme` | 15.0% | 8.0% | Standard crypto volatility range |
| `forex` | 1.0% | 0.5% | Tight for low-volatility FX pairs |
| `equity` / `stocks` / `stock` | 5.0% | 3.0% | Standard equity swing range |
| `commodity` / `futures` | 5.0% | 3.0% | Commodity futures range |
| `penny` | 8.0% | 5.0% | Higher caps for penny stocks |
| `etf` | 4.0% | 2.5% | Tighter than individual equities |
| `bond` / `index` | 3.0% | 2.0% | Most conservative |
| **Default** (unclassified) | 5.0% | 3.0% | Fallback for unknown categories |

Any pick whose TP or SL exceeds these caps has its targets clamped to the maximum. This is applied globally before the forward validator processes picks.

---

## 11. Technical Indicators Used Across Strategies

### In Elite Scorer (upstream quality)
| Indicator | Usage | Weight in Score |
|---|---|---|
| RSI (14) | Overbought/oversold detection | Via pattern_predictor (+5/-5 pts) |
| MACD (12,26,9) | Trend direction | Via momentum alignment (-8 pts if misaligned) |
| SMA 5/20 | Short-term momentum | Momentum gate (-8 if signal vs SMA disagree) |
| SMA 50/200 | Daily trend | Daily trend bonus (+5/-5 pts) |
| ATR | Volatility-adjusted sizing | Leverage safety component (up to 10 pts) |
| VPIN | Order flow toxicity | HARD gate: blocks if VPIN > 0.55 |
| Bollinger Bands | Volatility squeeze | bbkc_squeeze_strategy.py |
| Keltner Channels | Volatility reference | Combined with BB for squeeze detection |
| EMA 9/20 | Trend alignment | CBC Flip strategy (MapleStax) |
| VWAP | Session fair value | CBC Flip + Smart Picks engine |
| ADX | Trend strength | Regime detector, BB-KC squeeze filter |

### In Copy Trader Intelligence
| Signal | Source | How Used |
|---|---|---|
| Whale positions | OKX, Hyperliquid, Bybit leaderboards | Direct position mirroring |
| Consensus (2+ traders same direction) | Cross-exchange aggregation | Confidence boost (+0.05 per additional trader) |
| Trader win rate | Historical trade analysis | Trusted trader filtering (>55% WR required) |
| Funding rate | Binance perpetuals | Funding rate arbitrage strategy |

### In TSMOM Strategy (new)
| Indicator | Usage |
|---|---|
| N-day return (14d default) | Momentum signal |
| 30-day realized volatility | Position sizing (vol-scaled) |
| BTC 50-day SMA | Regime gate (above = long, below = cash) |
| ATR (14) | TP/SL calculation (TP=2x ATR, SL=1x ATR) |

---

## 12. What Makes a "Smart Pick" vs a "Regular Pick"

| Attribute | Regular Pick | Smart Pick |
|---|---|---|
| **Source** | Any of 120+ strategy files | Filtered from regular picks by smart_picks_engine.py |
| **Scoring** | Elite score (0-123 pts) + score booster | Additional 5-dimension scoring on top of elite score |
| **Regime alignment** | Soft penalty only (-10 to -35%) | **40% of Smart Pick score** — hard filter |
| **Minimum quality** | Must pass 13 forward validator gates | Must ALSO pass: confidence >= 0.50, not from banned system, not in death zone (losing >10%), valid TP/SL with R:R >= 1.2, TP within asset-class cap |
| **Freshness** | No requirement | **15% of score** — newer picks preferred |
| **Currently winning** | No bonus | **10% of score** — picks already in profit boosted |
| **TP upside** | No requirement | **15% of score** — picks with room to run preferred |
| **Tier system** | None | SCALP (<4h), SWING (4-48h), POSITION (>48h) |
| **Batch tracking** | Individual | Grouped into versioned batches (SP-v001, etc.) with PnL snapshots |
| **Resolution** | TP/SL hit or expiry | Batch resolves after 24h with aggregate WR/PnL |

### The Smart Pick Score Formula:
```
# Crypto picks:
smart_score = (
    regime_match * 0.40 +      # Does direction match current regime?
    elite_quality * 0.20 +     # Normalized elite score (0-100)
    freshness * 0.15 +         # Age decay (newer = better)
    tp_upside * 0.15 +         # Distance to TP as % of range
    currently_winning * 0.10   # Is unrealized PnL positive?
) * 100

# Non-crypto picks (forex, equity, commodity, bond):
smart_score = (
    regime_match * 0.20 +      # Reduced -- crypto regime less relevant
    elite_quality * 0.30 +     # Increased -- track record matters more
    freshness * 0.15 +         # Same
    tp_upside * 0.15 +         # Same
    currently_winning * 0.10   # Same
) * 100
```

### Banned Systems (cannot generate Smart Picks):
Systems with historically poor performance are excluded from Smart Pick candidacy regardless of individual pick score.

---

## 13. Known Issues & Improvement Roadmap

### Current Issues (as of Mar 23, 2026)
1. **ML Champion awaiting retrain** — scoring falls back to heuristic (AUC 0.51 = random)
2. **Score-PnL correlation r=0.05** — scores barely predict outcomes
3. **Multi-Agree consensus is NEGATIVE signal** — 18.1% WR vs 35% solo (feedback loop finding)
4. **391 strategies killed** but kill list may not be fully enforced until next CI cycle
5. **FETUSDT concentration** — 149% of total PnL from one symbol
6. **SL too tight** — 1.5% default is in crypto shakeout zone (optimal: 2.0-2.1%)
7. **MTF gate not yet wired in** — `mtf_gate.py` exists and is tested but not connected to the scanner pipeline yet (expected WR boost: 42% to 55-62%)

### Improvements Deployed This Session
1. Momentum-confirmed regime detector (catches fakeouts)
2. Strategy killer (391 dead strategies removed)
3. TSMOM vol-scaled momentum (Sharpe 1.12-2.17 academic)
4. BB-KC Squeeze breakout (waits for volatility explosion)
5. MapleStax CBC Flip (VWAP + EMA state machine)
6. TP/SL optimizer (data-driven from 2,481 trades)
7. Feedback loop (logistic regression, identifies scoring miscalibration)
8. Regime ensemble (different signal weights per market state)
9. Per-symbol dedup (-20 score for duplicates)
10. Low WR System penalty (-10 for known weak systems)
11. Kill switch (auto-halts signal generation on drawdown spikes, SL rate >60%, WR collapse, 5+ consecutive losses)
12. Non-crypto Smart Picks (forex, equity, commodity now scored with adjusted weights)
13. Global TP/SL sanity check (asset-class caps prevent unrealistic targets)
14. Universal price enricher (fills prices for non-crypto via yfinance)
15. Equity tracker (records portfolio snapshots after each scan)
16. On-chain macro strategies (MVRV, SOPR, NVT, SSR, DXY, yield curve)
17. Alligator strategies (4 Bill Williams variants: standard, scalp, swing, daily)
18. Polymarket prediction market signals
19. Commodities strategies (8 strategies across precious metals, energy, agriculture)
20. Statistical strategies (10 RenTech-inspired: O-U process, variance ratio, Hurst, multi-factor composite)
21. TTM Squeeze (standard + triple compression breakout)
22. R:R >= 1.2 gate in Smart Picks (blocks unfavorable risk/reward picks)

---

*Document version: 2.0 | Last updated: Mar 23, 2026*
*For questions, see the ML Blueprint at `docs/ML_BLUEPRINT_2026-03-16.md` for the full technical specification.*
