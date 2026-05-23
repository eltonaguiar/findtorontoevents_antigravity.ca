# Quant Swarm Round 1 — D.E. Shaw Lens (2026-05-12)

**Persona:** senior D.E. Shaw quant. Event-driven, earnings drift, M&A
arb, alt-data, news/sentiment. Caveman terse.

**Truth:** 55,510 trades, raw WR 11.13%, PF 0.46, Sharpe -2.34. 69%
zero-PnL ghosts. Filtered view (resolver v2): CRYPTO PF 1.36, COMMODITY
PF 2.08. Week 1 rescue shipped (db5bcfa0f04, dd8e8282537, c778f8f1696).

---

## 1. Per-asset-class — keep / kill / rebuild (D.E. Shaw lens)

| Class | Verdict | Shaw reason |
|---|---|---|
| COMMODITY | **KEEP** + scale | CT=F DSR 1.0 = CFTC COT alt-data signal. This is our edge. Shaw runs this playbook on softs daily. |
| EQUITY | **REBUILD** around PEAD | n=814, PF 2.18 with low WR = right-tail event payoff. Earnings drift is Shaw bread and butter. |
| ETF | **KEEP** thin | Sector rotation + NAV-arb is Shaw alt-data territory. Bump n. |
| BOND | **REBUILD** on FRED | Cochrane-Piazzesi forward-rate factor + curve carry. Shaw fixed-income desk territory. |
| FOREX | **KILL LONG, KEEP SHORT** | SHORT-axis 57% vs LONG 21% = retail-flow contrarian signal. IG/Myfxbook IS the alt-data. |
| CRYPTO | **REBUILD** narrow | Funding rate + perp basis is the only honest signal; kill sentiment ensembles. |
| FUTURES | **REBUILD** on COT | CT=F → GC=F transfer. Pure event-driven (COT release Friday 15:30 ET). |
| MEMECOIN / PENNY | **KILL** | No alt-data moat; pure microstructure noise. |

---

## 2. Hidden-insight queries (Shaw asks these on Day 1)

1. **Low-score-high-PnL outliers.** Query `picks.recent_closed` where
   `smart_score < 40` AND `realized_pnl_pct > 5`. Shaw thesis: scoring
   model is anti-correlated to truth in a subspace (confidence inversion
   per `feedback_long_source_bias.md`). Cross-tab vs source × side ×
   hour-of-day. Already partial evidence: ml_gatekeeper inversion gate
   (c778f8f1696).
2. **High-score-low-PnL traps.** `smart_score > 75` AND realized < 0.
   Map to source-system. Hypothesis: `crypto_soc_*`, `kimi_signal_tracking`,
   `quan_engine` LONG = three named draggers. Confirm cohort.
3. **Dormant strategies w/ positive backtest.** `algorithm_performance.csv`
   rows w/ n_picks < 50 in last 30d AND backtest PF > 1.5. Shaw: "edge
   that doesn't trade is edge wasted." Suspect: cot_paper_pilot pre-promo,
   PEAD-flavored equity strats never wired.
4. **Time-of-day × side anomaly.** 22 UTC = 61.2% WR (memory:
   project_clean_data_symbol_wr). Earnings post-close 21:00 UTC. Likely
   PEAD signal leaking into crypto noise. Test.
5. **Calendar-effect dormant.** Pre-CPI, pre-FOMC, pre-NFP windows —
   query realized PnL in T-2h / T+2h slices. Shaw runs macro-calendar
   regime gates always.

---

## 3. New event-driven strategies — first to test per class

| Class | Strategy | Alt-data source |
|---|---|---|
| EQUITY | **PEAD (post-earnings announcement drift)** — buy SUE > 2σ, hold 60d | Estimize crowdsourced consensus, Quandl Sharadar SF1 earnings actuals, Benzinga news API |
| EQUITY | **Insider cluster buys** | SEC Form 4 EDGAR feed, OpenInsider scrape |
| EQUITY | **Short-interest squeeze gate** | FINRA twice-monthly SI, Ortex / S3 if budget |
| ETF | **Creation/redemption imbalance** | NYSE ARCA daily basket file + iNAV vs market price |
| BOND | **Cochrane-Piazzesi single-factor** | FRED CMT yields (now unblocked, SKIP_FRED env) |
| BOND | **TIPS-Treasury arb (Fleckenstein)** | FRED DFII series + nominal CMT |
| COMMODITY | **COT commercials net position Δ** | CFTC Commitments of Traders Friday release |
| COMMODITY | **Backwardation slope** | CME term-structure |
| FOREX | **Retail contrarian (SHORT-only)** | Myfxbook + IG client positioning (already wired, SHORT axis only) |
| FOREX | **Carry × DXY-beta** | OANDA forward swap points |
| CRYPTO | **Funding rate extremes** | Coinglass aggregated funding, Hyperliquid HLP basis |
| CRYPTO | **Stablecoin float Δ** | Glassnode / on-chain — flow into USDT/USDC = risk-on signal |
| FUTURES | **COT for GC/SI/HG** | same CFTC release; CT=F template ports directly |

---

## 4. ML reality + Shaw re-engineering

**Current ML:** accuracy 32.6%, Brier 0.374, precision 11.52%, recall
84.38%. Predicts WIN almost always = class-imbalance artifact. Stale.
Hard-fail watchdog now mtime-gated (db5bcfa0f04).

**Shaw rebuild:**
- Stop predicting WIN/LOSS. **Predict residualized 5d alpha** after
  removing market beta + sector + size + value (Fama-French 5).
- Feature stack: (a) earnings surprise z-score, (b) revision momentum
  (IBES Δ), (c) news-flow polarity (Ravenpack / RoBERTa-finance), (d)
  insider net-buy 30d, (e) options skew Δ, (f) short-interest %float.
- **Calibrated probabilities** (isotonic regression on holdout), Brier
  target < 0.20.
- **Purged k-fold CV + embargo** (López de Prado). CPCV already
  integrated, not wired — wire it.
- **Meta-labeling** (López AFML Ch.3): primary model picks side,
  secondary sizes. Solves the low-precision / high-recall pathology.

---

## 5. THE ONE THING — Day 1

**Ship PEAD (post-earnings-announcement drift) on EQUITY top-100 by
liquidity, long-only, 60-day hold, SUE > 2σ entry, alt-data = Estimize +
Quandl SF1.**

Why this and not anything else:
- EQUITY already PF 2.18, low-WR / right-tail = exactly the shape PEAD
  produces (Bernard-Thomas 1989 → Ke-Ramalingegowda 2005).
- We have the universe (CRSP-style expansion already on roadmap).
- Zero new infrastructure: SUE = (actual - consensus) / σ; both sides
  exist in free Quandl SF1 + Estimize API.
- Independent of all current draggers (`kimi_*`, `crypto_soc_*`,
  `quan_engine` LONG) — no contamination risk.
- 30-day shadow → real money on a class we already trust the PF on.

Everything else (CRYPTO funding, FOREX SHORT-only, BOND Cochrane-Piazzesi)
is Day 2-7. PEAD on Day 1.

---

## NFA

Research surface only. No real-money sizing without 10-step López de
Prado AFML pipeline clear + 30d shadow. Per CLAUDE.md Goal #1.
