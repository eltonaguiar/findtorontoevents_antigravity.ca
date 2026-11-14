# TradingView Contest Winner Archetypes — Research Notes

**Date:** 2026-11-14
**Worktree:** hilarious-seer
**Source:** finpredict-v4/research/tradingview_contest_winner_research_2026-11-14.md

---

## Verified Top Performers (TradingView The Leap Leaderboards)

| Winner | Contest | Net Profit | Profitable Trades | Contestants |
|--------|---------|------------|-------------------|-------------|
| BenBernanke1 | Futures — Feb 2025 | +5,220.72% | 94% | 59,187 |
| yxiao8911 | Futures — Sep 2026 | +1,673.74% | 83% | 103,158 |
| Me-tis | Futures — Jul 2026 | +155.95% | 65% | 107,677 |
| Manishh_jain92 | Crypto — May 2026 | +271.78% | 77% | 39,363 |
| ICT_Hispanohablantes | Multi-asset — Apr 2025 | +308.07% | 52% | 36,965 |
| KingBob09 | Commodities — Oct 2026 | +45.58% | 43% | 25,189 |
| prodigy5284 | Stocks — Mar 2026 | +17.58% | 95% | 41,301 |

**Critical insight:** Two viable winner archetypes:
- **High-frequency, high-win-rate grinders** (83–95% WR, modest per-trade gains, massive sample)
- **Low-frequency, high-R:R snipers** (43–52% WR, huge outlier trades, tight risk control)

---

## Common Methodologies

### A. ICT / Smart Money Concepts (SMC)
- Liquidity sweeps, fair value gaps (FVG), order blocks, breaker structures
- Dominates retail futures contest space
- Gives precise entry models with defined invalidation levels (tight SL → high R:R)

### B. Momentum / EMA Confluence
- `MomentumEMA` is #1 strategy family among genuine closed winners (42 of 155 wins, 27.1%)
- Winners cluster on liquid crypto majors: BTC, ETH, SOL, LINK, NEAR, AVAX

### C. Contrarian / Fear-Greed Reversal
- `st_fear_greed_contrarian` produced BNBUSDT LONG +21.42% (206-day hold) and AVAXUSDT LONG +10.69%
- Regime-aware mean-reversion plays, not blind counter-trend

### D. Multi-Timeframe Alignment
- Strategies requiring 4+ timeframes aligned produce higher live win rates but fewer signals
- Contest winners trade 4H direction with 1H/15M precision entry, Daily as trend filter

---

## Timeframes

| Timeframe | Role | Usage by Winners |
|-----------|------|-----------------|
| Daily | Trend filter / regime | Directional bias only; rarely entry |
| 4H | Trade direction | Primary signal generation |
| 1H | Entry timing | Precision entries, especially crypto/futures |
| 15M / 5M | Scalping / confluence | Only when multi-TF alignment confirms |

Winners do NOT scalp 1M/3M. Noise-to-signal too high. They favor swing holds (4H–Daily) with 2–10% targets or high-probability intraday 1H setups.

---

## Risk Management

- **Paper contest winners use aggressive sizing** — 10–20% of equity per trade (no real drawdown consequence)
- **For real money:** Scale down to 1–3% per trade; our `prove_winners.py` gate uses max 2% risk per trade
- **Winners use technical-level SLs** — swing low/high, order block invalidation, FVG extreme (not fixed percentages)
- **Daily loss cap at −5%, monthly at −20%** (LuneFi audit)

---

## Handling Losing Streaks

- High-WR grinders: **3 losses in a row → stop for the session** (regime likely unfavorable)
- High-R:R snipers: **Fixed risk per trade, no scaling up after losses** (Martingale is #1 contest killer)

---

## Technical Indicators vs. Price Action vs. Quant

| Approach | Prevalence | Notes |
|----------|-----------|-------|
| Price Action (ICT/SMC) | Very High | Dominant among futures/forex winners |
| Technical Indicators | High | RSI < 35 at ideal entry, volume spike >2x, Bollinger squeeze before breakout |
| Quantitative / ML | Moderate | `multi_asset_copytrader` achieved 82.1% WR — highest win-rate source |
| Hybrid | Best performers | Quant signal + price-action confirmation |

From our reverse-engineer:
- Volume spike >2x before pump appears in majority of hourly winners
- RSI < 35 at entry is most common mean-reversion signature
- Bollinger squeeze (width < 0.04) precedes volatility-breakout winners

---

## Position Sizing — The Hidden Edge

- Paper contest winners max leverage on high-conviction setups because contest rewards absolute return, not Sharpe
- For real prediction system:
  - Kelly Criterion fractional sizing (0.25x–0.5x full Kelly) for proven edges
  - `crypto_ml_edge` pipeline uses volatility-based sizing (ATR-adjusted)
  - MetaLearner caps score multipliers at 1.5x and confidence at 0.99 to prevent tail-risk concentration

---

## Specialization by Pattern

| Pattern | Winner Example | Contest Type |
|---------|---------------|--------------|
| Trend Following / EMA Momentum | yxiao8911 (+1,673%) | Futures |
| Mean Reversion / Fear-Greed | Manishh_jain92 (+271%) | Crypto |
| Breakout / Volatility Expansion | Me-tis (+155%) | Futures |
| High-Frequency Grind | prodigy5284 (+17.58%, 95% WR) | Stocks |
| Low-WR, High-R:R Sniping | KingBob09 (+45.58%, 43% WR) | Commodities |

**No consistent winner is a generalist.** They pick ONE pattern, master it, and exploit it in the asset class where it works best.

---

## Red Flags — What NOT to Copy

1. **Repainting / Lookahead Bias** — Many 90%+ WR strategies cheat with `security(tickerid, 'D', close[1])` or `calc_on_every_tick=true`. Our `prove_winners.py` flags these as ONE-HIT WONDER — DEMOTED.
2. **Over-Leveraged Survivorship Bias** — Top of leaderboard dominated by traders who got lucky on 2–3 all-in bets. Median contestant using same approach blew up.
3. **Ignoring Costs** — Paper trading ignores slippage and commissions. Live results are 60–70% of backtests on average. Our validation pipeline deducts Binance fees + slippage before any Sharpe calculation.

---

## Actionable Recommendations for Our System

### Immediate (This Week)
1. Adopt the two-archetype model: separate pipelines for High-WR Grinders (70%+ WR, 1.5:1 R:R) and High-R:R Snipers (45–55% WR, 3:1+ R:R). Blend in ensemble.
2. Add missing proven-winner symbols: `AUDJPY=X`, `GBPJPY=X`, `BAT-USD`, `CRV-USD`, `ZECUSDT`, `WLD-USD`, `XTZ-USD`, `MINAUSDT`.
3. Time window targeting: schedule entry generation to capture 14:00Z / 21:00Z UTC resolution windows where 76 of 155 genuine winners closed.

### Medium-Term (Next Sprint)
4. Implement heterogeneous stacking: LightGBM + GRU-Attention + Ridge linear model predictions as meta-features.
5. Add prediction tail clipping: clip ensemble outputs to [2nd, 98th] percentile of training-set predictions.
6. Calibrate `crypto_ml_edge` pipeline with `CalibratedClassifierCV(method="isotonic", cv=3)`.

### Validation Hard Gates (Already Partially Implemented)
7. Enforce competition-grade gates:
   - DSR > 0.95
   - Cost-adjusted Sharpe > 0 after Binance fees + slippage
   - Regime coverage: 2022 bear market must appear in at least one test fold
   - 200+ trades across bull/bear/chop cycles before declaring a strategy "proven"
