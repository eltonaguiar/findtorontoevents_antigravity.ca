# TradingView Prediction Contest Winner Research — Actionable Summary

**Date:** 2026-11-14  
**Sources:** TradingView The Leap official leaderboard (2024–2026), LuneFi backtested strategy audit, Forex Factory repainting-exposure thread, repo internal winner-reverse-engineer + prove-winners pipelines.

---

## 1. What the Winners Actually Look Like (Real Data)

From TradingView’s official *The Leap* paper-trading leaderboards, here are verified top performers:

| Winner | Contest | Net Profit | Profitable Trades | Contestants |
|--------|---------|------------|-------------------|-------------|
| **BenBernanke1** | Futures — Feb 2025 | **+5,220.72%** | 94% | 59,187 |
| **yxiao8911** | Futures — Sep 2026 | **+1,673.74%** | 83% | 103,158 |
| **Me-tis** | Futures — Jul 2026 | **+155.95%** | 65% | 107,677 |
| **Manishh_jain92** | Crypto — May 2026 | **+271.78%** | 77% | 39,363 |
| **ICT_Hispanohablantes** | Multi-asset — Apr 2025 | **+308.07%** | 52% | 36,965 |
| **KingBob09** | Commodities — Oct 2026 | **+45.58%** | **43%** | 25,189 |
| **prodigy5284** | Stocks — Mar 2026 | **+17.58%** | **95%** | 41,301 |

**Critical insight:** There are **two viable winner archetypes**:
- **High-frequency, high-win-rate grinders** (e.g., 83–95% WR, modest per-trade gains, massive sample size).
- **Low-frequency, high-R:R snipers** (e.g., 43–52% WR, huge outlier trades, tight risk control).

Trying to be mediocre on both dimensions is how most contestants lose.

---

## 2. Common Strategies / Methodologies

### A. ICT / Smart Money Concepts (SMC)
- **JoshTrades_ICT** (Futures winner, +124%) explicitly uses ICT methodology — Telegram channel references liquidity sweeps, fair value gaps (FVG), order blocks, and breaker structures.
- SMC dominates the retail futures contest space because it gives precise entry models with defined invalidation levels (tight SL → high R:R).

### B. Momentum / EMA Confluence
- Our own reverse-engineered winner data shows **MomentumEMA** is the #1 strategy family among genuine closed winners (42 of 155 wins, 27.1% share).
- Winners cluster on liquid crypto majors: BTC, ETH, SOL, LINK, NEAR, AVAX.

### C. Contrarian / Fear-Greed Reversal
- `st_fear_greed_contrarian` produced the single biggest genuine win in our panel: **BNBUSDT LONG +21.42%** (206-day hold) and **AVAXUSDT LONG +10.69%**.
- These are regime-aware mean-reversion plays, not blind counter-trend entries.

### D. Multi-Timeframe Alignment
- LuneFi’s backtest audit shows strategies that require **4+ timeframes aligned** (e.g., Weekly > Daily > 4H > 30M all above 21 EMA) produce higher live win rates — but fewer signals.
- Contest winners often trade **4H direction with 1H/15M precision entry**, using Daily as a trend filter.

---

## 3. Timeframes Winners Focus On

| Timeframe | Role | Usage by Winners |
|-----------|------|-----------------|
| **Daily** | Trend filter / regime | Directional bias only; rarely entry |
| **4H** | Trade direction | Primary signal generation |
| **1H** | Entry timing | Precision entries, especially for crypto/futures |
| **15M / 5M** | Scalping / confluence | Only when multi-TF alignment confirms |

**Key pattern:** Winners do NOT scalp 1M/3M in contests. The noise-to-signal ratio is too high over a 1–4 week contest window. They favor **swing holds (4H–Daily) with 2–10% targets** or **high-probability intraday 1H setups**.

---

## 4. Risk Management Rules

### Position Sizing
- **Paper contest winners use aggressive sizing** — 10–20% of equity per trade is common because there is no real drawdown consequence.
- **For real-money application:** Scale down to 1–3% per trade. Our `prove_winners.py` gate uses **max 2% risk per trade** as the retail-viable threshold.

### Stop Loss Discipline
- Winners use **technical-level SLs** (swing low/high, order block invalidation, FVG extreme) — not fixed percentages.
- Our winner-reverse-engineer shows the ideal SL is typically the **maximum adverse excursion (MAE)** after entry, not an arbitrary ATR multiple.

### Daily / Weekly Loss Caps
- LuneFi audit: sustainable strategies cap **daily loss at –5%**, **monthly at –20%**.
- Contest winners who blow up usually violate this — the leaderboard is filled with traders who went all-in once and either won big or dropped to page 50.

---

## 5. Handling Losing Streaks

**Evidence from winner profiles:**
- **BenBernanke1** (94% WR) and **prodigy5284** (95% WR) have extremely high precision — they likely sit out choppy sessions rather than trade through them.
- **KingBob09** (43% WR, Commodities winner) accepted a sub-50% win rate and let outliers carry the P&L. Losing streaks are irrelevant if individual losses are capped and individual wins are asymmetric.

**Actionable rule:**
- High-WR grinders: **3 losses in a row → stop for the session** (regime is likely unfavorable).
- High-R:R snipers: **Fixed risk per trade, no scaling up after losses** (Martingale is the #1 contest killer).

---

## 6. Technical Indicators vs. Price Action vs. Quant

| Approach | Prevalence | Notes |
|----------|-----------|-------|
| **Price Action (ICT/SMC)** | Very High | Dominant among futures/forex winners; liquidity sweeps + FVG retests |
| **Technical Indicators** | High | RSI < 35 at ideal entry, volume spike >2x, Bollinger squeeze before breakout |
| **Quantitative / ML** | Moderate | Our `multi_asset_copytrader` achieved **82.1% WR** — the highest win-rate source in the window |
| **Hybrid** | Best performers | Quant signal + price-action confirmation (e.g., ML filter + SMC entry) |

**From our own reverse-engineer:**
- **Volume spike >2x before pump** appears in the majority of hourly winners.
- **RSI < 35 at entry** is the most common mean-reversion signature.
- **Bollinger squeeze (width < 0.04)** precedes volatility-breakout winners.

---

## 7. Position Sizing — The Hidden Edge

- **Paper contest winners are NOT position-sizing like real traders.** They max leverage on high-conviction setups because the contest rewards absolute return, not Sharpe.
- **For a real prediction system:**
  - Use **Kelly Criterion fractional sizing** (0.25×–0.5× full Kelly) for proven edges.
  - Our `crypto_ml_edge` pipeline uses **volatility-based sizing** (ATR-adjusted).
  - The `MetaLearner` caps score multipliers at 1.5× and confidence at 0.99 to prevent tail-risk concentration.

---

## 8. Specialization by Pattern

| Pattern | Winner Example | Contest Type |
|---------|---------------|--------------|
| **Trend Following / EMA Momentum** | yxiao8911 (+1,673%) | Futures |
| **Mean Reversion / Fear-Greed** | Manishh_jain92 (+271%) | Crypto |
| **Breakout / Volatility Expansion** | Me-tis (+155%) | Futures |
| **High-Frequency Grind** | prodigy5284 (+17.58%, 95% WR) | Stocks |
| **Low-WR, High-R:R Sniping** | KingBob09 (+45.58%, 43% WR) | Commodities |

**No consistent winner is a generalist.** They pick ONE pattern, master it, and exploit it in the asset class where it works best.

---

## 9. Red Flags — What NOT to Copy from Contest Leaderboards

1. **Repainting / Lookahead Bias** — Forex Factory exposed that many 90%+ WR strategies on TradingView cheat with `security(tickerid, 'D', close[1])` (peeks at daily close before the day ends) or `calc_on_every_tick=true`. Our `prove_winners.py` flags these as **ONE-HIT WONDER — DEMOTED**.
2. **Over-Leveraged Survivorship Bias** — The top of any contest leaderboard is dominated by traders who got lucky on 2–3 all-in bets. The median contestant using the same approach blew up.
3. **Ignoring Costs** — Paper trading ignores slippage and commissions. LuneFi audit shows live results are **60–70% of backtests** on average. Our validation pipeline deducts Binance fees + slippage before any Sharpe calculation.

---

## 10. Actionable Recommendations for Our Prediction System

### Immediate (This Week)
1. **Adopt the two-archetype model:** Run separate pipelines for **High-WR Grinders** (target 70%+ WR, 1.5:1 R:R) and **High-R:R Snipers** (target 45–55% WR, 3:1+ R:R). Blend them in the ensemble.
2. **Add the missing proven-winner symbols** from our reverse-engineer: `AUDJPY=X`, `GBPJPY=X`, `BAT-USD`, `CRV-USD`, `ZECUSDT`, `WLD-USD`, `XTZ-USD`, `MINAUSDT`.
3. **Time window targeting:** Schedule entry generation to capture the **14:00Z / 21:00Z UTC** resolution windows where 76 of 155 genuine winners closed.

### Medium-Term (Next Sprint)
4. **Implement heterogeneous stacking** (from researcher_021): Stack LightGBM + GRU-Attention + Ridge linear model predictions as meta-features. The components exist in `ml_battleground/` but are not wired together.
5. **Add prediction tail clipping:** Clip ensemble outputs to [2nd, 98th] percentile of training-set predictions to reduce variance from outlier predictions.
6. **Calibrate the `crypto_ml_edge` pipeline:** It currently outputs raw LightGBM probabilities. Add `CalibratedClassifierCV(method="isotonic", cv=3)` — the pattern already exists in `claude_gainer_ml/train_model.py`.

### Validation Hard Gates (Already Partially Implemented)
7. **Enforce the competition-grade gates we already have:**
   - **DSR > 0.95** (Deflated Sharpe Ratio)
   - **Cost-adjusted Sharpe > 0** after Binance fees + slippage
   - **Regime coverage:** 2022 bear market must appear in at least one test fold
   - **200+ trades** across bull/bear/chop cycles before declaring a strategy "proven"

---

## Sources

- TradingView The Leap Official Leaderboard: https://www.tradingview.com/the-leap/ (accessed 2026-11-14)
- LuneFi — Top Backtested TradingView Strategies 2026: https://lunefi.com/blog/top-backtested-tradingview-strategies-2026-win-rates-stats
- Forex Factory — All the >90% winning rate strategies on TradingView: https://www.forexfactory.com/thread/1273346
- Internal: `researcher_021_competition_winners.md`, `winner_reverse_engineer.py`, `prove_winners.py`, `reports/2026-10-22-top10-winners-reverse-engineered.md`
