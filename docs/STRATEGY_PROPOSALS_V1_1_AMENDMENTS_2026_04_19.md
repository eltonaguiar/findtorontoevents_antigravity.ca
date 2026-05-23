# Strategy Proposals v1.1 — Amendments After Peer Review

**Date:** 2026-04-19
**Base:** [STRATEGY_PROPOSALS_V1_2026_04_19.md](STRATEGY_PROPOSALS_V1_2026_04_19.md)
**Reviewers:** DeepSeek-v3.1:671b (Ollama cloud), Gemma3:27b (Ollama cloud)
**Status:** amendments adopted; base doc still authoritative for hypothesis content; this doc adds risk/cost/demotion refinements

Both reviewers strongly endorsed the framework. Both recommended APPROVE to proceed with S1 backtesting on the priority list. Specific refinements below.

## 1. Demotions — move to Anti-Goals

### BD-2 FOMC Policy Surprise — DEMOTED
**DeepSeek-v3.1 verdict:** *"NOT viable for the systematic framework. n too low. Edge exists in 5-10 minute window inaccessible without ultra-low-latency execution. By the time a retail system places a trade, the move is over."*

**Agree.** With only 8 FOMC meetings/year → n=40 over 5 years, statistical validation is impossible at retail scale even if edge exists. Move to Anti-Goals section of base doc.

## 2. Re-classification — ETF-1 Intermarket-Flow-Scout

**DeepSeek-v3.1 verdict:** *"The recent 85% WR is a massive red flag for overfitting. This strategy should be immediately paper-traded only until it passes full S1-S3 validation. Its current 'live' status is the exact problem v1.1 amendments were designed to solve."*

**Agree.** ETF-1 runs live in GHA today via `.github/workflows/backtest-and-deploy.yml`. It must be **immediately paper-flagged** until it passes S1-S3. Add to `alpha_engine/strategy_blocklist.py` as PAPER-ONLY pending validation.

## 3. Re-framing — EQ-2 Credit Spread as Regime Filter

**DeepSeek-v3.1 verdict:** *"Less a pure alpha signal and more of a regime filter. Most valuable as a risk-off signal that de-levers or hedges other long-only strategies in the ensemble, rather than as a standalone short signal."*

**Adopt.** Move EQ-2 from Tier 1 (Event/Alpha) to Tier 2 (Regime Gates) in the v1.1 multi-asset pyramid. Its role: annotate every active LONG pick with a `credit_regime` tag, and auto-demote picks emitted during credit-widening events. Lower validation bar since it's not an emitter.

## 4. Risk sizing per strategy (Gemma3 request)

Add to each strategy's hypothesis doc:

| Strategy | Initial risk/trade | Max concurrent | Max daily exposure |
|---|---|---|---|
| CR-1 Funding Reversion | 0.5% | 2 (one BTC, one ETH) | 1.0% |
| CR-2 Token Unlock | 0.5% | 3 | 1.5% |
| EQ-1 PEAD | 0.3% | 5 | 1.5% |
| EQ-2 Credit Regime | N/A — filter only | — | — |
| ETF-1 (paper-only) | 0% live | — | 0% |
| ETF-2 Sector Rotation | 0.4% | 3 (different sectors) | 1.2% |
| FX-1 Carry Unwind | 0.4% | 2 | 0.8% |
| FX-2 CB Divergence | 0.3% | 1 | 0.3% |
| COM-1 COT Commercial | 0.3% | 2 | 0.6% |
| BD-1 Yield Carry | 0.3% | 1 | 0.3% |

Total simultaneous max exposure: ~6% of account. Way below the 10% DD cap even if all stops trigger.

## 5. Transaction-cost estimates per asset class (Gemma3 request)

For S1 backtests, use these realistic costs:

| Asset class | Spread (bps) | Commission (bps) | Slippage (bps) | Total round-trip (bps) |
|---|---|---|---|---|
| Crypto perps (major) | 1-3 | 4-8 (funding + fee) | 3-5 | **15-30** |
| Crypto perps (alt) | 5-15 | 4-8 | 10-25 | **30-65** |
| US equities (mid-cap) | 3-8 | 0 (retail broker) | 5-15 | **15-45** |
| US ETFs (liquid) | 1-3 | 0 | 2-5 | **5-15** |
| FX majors | 0.5-1 pip = 5-10bps | 0 | 2-5 | **12-25** |
| Commodity futures | 1-2 ticks | $1-3/contract | 2-5 | **5-20** |
| Treasury ETFs | 1-2 | 0 | 2-3 | **5-8** |

Per DeepSeek-v3.1's CR-1 risk note: **crypto alts in liquidation cascades can hit 100-300bps slippage.** The S1 backtest must model this at 95th-percentile volatility.

## 6. Data-latency warnings (DS-v3.1 critical)

For each data source, document the lag explicitly:

| Data source | Nominal lag | Real-world lag for backtesting |
|---|---|---|
| Binance funding rate | Real-time / 8h cycle | ~5s live; **check historical for completeness** |
| FMP earnings | ~1 min post-release | Must verify timestamp is press-release time, not scrape time |
| CFTC COT report | **Tuesday 3:30pm ET with Tue prev-week data** | **4-5 day lag in backtest** — must only trade on Wed market open at earliest |
| HYG/LQD ETF | End-of-day | Real-time during session but spreads widen in stress |
| FRED yield data | End-of-day | 1-2 day publishing lag |
| ExchangeRate-API | 1-hour refresh | **Too slow for short-window FX backtests** — need better vendor for FX-1 |

**⚠️ COM-1 specific danger:** CFTC data-lag handling is THE critical implementation detail. Must only use data available at the time of the trade. Lookahead bias here has killed many academic-paper-inspired strategies in live.

## 7. Individual strategy gotchas (from DS-v3.1 section-by-section review)

### CR-1 Funding Rate — add liquidation cascade risk
DS-v3.1: *"A crowded short (high positive funding) can become even MORE crowded, leading to short squeeze moving AGAINST the signal violently before reversion."* Action: hard stop-loss at 1.5× entry-move-against, reduce position size if IV > 100% annualized.

### EQ-1 PEAD — FMP timestamp precision critical
*"What is the exact time of FMP's earnings announcement timestamp? Press release (good) vs scrape time (bad, lookahead)."* Action: validate timestamps against NYSE/Nasdaq official announcement schedules before any backtest.

### EQ-2 Credit Spread (now regime filter)
*"ETF prices can be influenced by factors other than pure bond values."* Action: cross-reference HYG/LQD with direct bond index data (LQD's net asset value vs price premium/discount).

### ETF-2 Sector Rotation
*"Universe definition must avoid lookahead bias."* Action: use SPDR's published ETF holdings as of historical date, not today's holdings.

### FX-1 Carry Unwind
*"Signal is rare — VIX spikes >30% in 5 days may only happen few times/year."* Accept inactivity as feature. Reminder: Wilson LB on n≤15 will fail Bonferroni correction → this strategy may structurally never reach S4 status. Flag as such in the hypothesis doc.

### COM-1 COT Commercial
*"Structural shifts break the pattern (2022 energy crisis example)."* Add regime override: if commodity spot is up >50% YTD (structural shortage signal), disable COT signal temporarily.

### BD-1 Yield Carry
*"Duration risk can overwhelm roll-down carry."* Action: S1 MUST backtest 2013 Taper Tantrum + 2022-2023 rising rates window; if WR drops below 40% in those windows, demote to regime-gated only.

## 8. Regulatory considerations (Gemma3 question)

For strategies involving shorting or restricted markets:
- **EQ-2 SHORT SPY**: fine via inverse ETF (SH) or put options; direct short OK at retail broker
- **FX-1 SHORT AUDJPY**: no regulatory issue for retail spot FX
- **COM-1 SHORT commodity futures**: requires futures broker (not typical equity broker); regulatory margin rules apply (CFTC Reg 1.17)
- **BD-1 TLT LONG**: no issue
- **BD-2 (demoted)**: N/A

No regulatory blocker for the 8 remaining strategies. All tradeable at Interactive Brokers / tastytrade / equivalent.

## 9. Bonferroni aggressiveness (Gemma3 question)

Gemma3 asked: *"Bonferroni correction in S2 seems aggressive — could lead to false negatives."*

**Intentional.** Per v1.1 §4 (4-AI peer review): Bonferroni is the correct correction for testing many (strategy × symbol × direction) combos against the null. The alternative (Benjamini-Hochberg FDR) is more permissive but riskier when the cost of a Type-I error is "deploy a losing strategy live." Keep Bonferroni. Accept the higher bar.

## 10. Updated priority list

Post-amendments:

| Rank | Strategy | Asset | Status change |
|---|---|---|---|
| 1 | **CR-1 Funding Reversion** | Crypto | No change — top priority |
| 2 | **EQ-1 PEAD small-cap** | Equities | No change |
| 3 | **COM-1 COT Commercial** | Commodities | ⚠️ Add data-latency enforcement |
| 4 | **EQ-2 Credit Spread** | Equities | ✏️ Reframed as regime filter (Tier 2) |
| 5 | **BD-1 Yield Curve Carry** | Bonds | ⚠️ Must pass 2013/2022 stress windows |
| 6 | **FX-1 Carry Unwind** | FX | Accept rarity — may never reach S4 n-threshold |
| 7 | **ETF-2 Sector Rotation Breadth** | ETFs | No change |
| 8 | **FX-2 CB Divergence** | FX | No change |
| — | **BD-2 FOMC Surprise** | Bonds | ❌ DEMOTED to Anti-Goals (n too low, latency-restricted) |
| — | **ETF-1 Intermarket-Flow** | ETFs | ❌ PAPER-FLAG NOW (existing live code unvalidated) |

## 11. Implementation order for CR-1 S1 backtest

DS-v3.1 said *"strongest candidate for prioritization"* + Gemma3 agreed. Go-ahead to start CR-1 S1 work now:

1. Verify `alpha_engine/funding_rate_scanner.py` is wired live — check last GHA run
2. Pull 2023-2025 BTC/ETH funding data from Binance (free)
3. Run S1 backtest with transaction costs per §5
4. S1 pass criteria: Sharpe > 1.0 on IS, 70/15/15 OOS drift < 10pp, positive avg PnL post-cost
5. If pass → graduate to S2 (walk-forward + Wilson LB Bonferroni)
6. If fail → archive, don't iterate parameters (overfitting trap)

Expected S1 completion: 1-2 days.

## 12. Immediate actions needed

- [ ] **Add ETF-1 Intermarket-Flow-Scout to `strategy_blocklist.py`** as PAPER-ONLY until it passes S1-S3
- [ ] **Remove BD-2 from strategy proposals** (move to Anti-Goals)
- [ ] **Update `docs/STRATEGY_PROPOSALS_V1_2026_04_19.md`** with the data-latency table + risk sizing
- [ ] **Verify `alpha_engine/funding_rate_scanner.py` status** before CR-1 work
- [ ] **Document FMP earnings timestamp convention** before EQ-1 S1

## 13. Consensus green light

Both external AIs explicitly recommended **APPROVE to proceed**. No blockers surfaced. This is the first time today a document has been green-lit by all peer reviewers on first pass. The event-driven and factor-rooted strategies with named academic backing are the right frontier.

Proceed with CR-1 S1 backtest work when you authorize.

---

## Review feedback — Cursor agent (2026-04-19)

1. **S0.5 data integrity:** Strong addition — require a **single checksum line** (row count + date range + vendor) in every S1 JSON artifact so CI can diff artifacts across runs ([STRATEGY_DISCOVERY_PROTOCOL.md](STRATEGY_DISCOVERY_PROTOCOL.md) aligns).
2. **Cost table vs discovery doc:** Keep numbers in sync between §5 here and [STRATEGY_DISCOVERY_PROTOCOL.md](STRATEGY_DISCOVERY_PROTOCOL.md) §5; if they diverge, label one “authoritative for S1” and link the other.
3. **ETF-1 paper-flag:** The checklist in §12 is right — add **owner + date closed** when the blocklist entry ships so the item does not linger open.
4. **Orthogonality:** v1.1 mandates dependency checks — name **`correlation_prune_strategies.py`** (or portfolio covariance cap) as the mechanical implementation for Tier 4 ensembles.
5. **Green light caveat:** “Approve to proceed” applies to **research execution**, not live routing — restate S-stage ceiling in one sentence for newcomers.
