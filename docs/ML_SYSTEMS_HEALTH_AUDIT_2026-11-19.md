# ML Systems Health & Staleness Audit — 2026-11-19

**Audit date:** 2026-11-19  
**Evidence:** model training reports (`ml_gatekeeper/models/training_report.json`,
`ml_consensus/models/consensus_report.json`, `crypto_ml_edge/results/training_report.json`,
`mercury2/data/metrics_report.json`, `stabilization/forward_performance_report.json`,
`copy_trader_intel/data/pick_quality_report.json`) + live `at_pick_outcomes` queries on
`mysql.50webs.com`. No credentials exposed.

---

## 1. Executive verdict

| Question | Verdict |
|---|---|
| Are the ML systems healthy? | **Mixed.** Consensus + gatekeeper are fresh and statistically validated; Mercury2 and crypto-ML are stale/weak. |
| Can they produce winning picks? | **Yes, selectively.** The *ensemble/consensus* path has real, statistically significant edge. The *broader raw pipeline* is break-even. |
| Worth maintaining? | **Yes — but only the subset with proven lift.** Do NOT maintain the whole surface. |
| Modify slightly or redo? | **Modify slightly (not redo).** Keep the validated gatekeeper + consensus + top strategies; fix the stale/weak pieces. Do not rebuild from scratch. |

**Bottom line:** the ML layer is not broken — it is *under-deployed*. The
signal is real (gatekeeper holdout profit factor 2.83, consensus backtest WR
50.6% vs 41.9% single) but it is diluted by a large body of negative-EV
strategies and stale data feeds. The fix is curation + freshness, not a
rewrite.

---

## 2. Health & freshness per ML system

| System | Last trained / generated | Freshness | Health | Evidence |
|---|---|---|---|---|
| **Gatekeeper** (`ml_gatekeeper`) | 2026-11-19 03:58 | ✅ fresh (today) | ✅ **healthy, significant** | 12-fold walk-forward mean lift **10.44%** (95% CI 4.8–17.0), t=3.23, **p=0.008**; true-holdout passed WR 61% vs 52.2% baseline, **profit factor 2.826**; top features `strat_fwd_pf`, `ml_composite_score`, `elite_score`, `confidence` |
| **Consensus** (`ml_consensus`) | 2026-11-19 03:58 | ✅ fresh | ✅ **healthy** | backtest: consensus WR **50.6%** vs single 41.9%, cumulative PnL **+38.4** vs −677 (single); consensus 81 picks vs 3,203 single |
| **Mercury2** | 2026-11-19 04:49 | ✅ runs, 🚩 weak | ⚠️ **weak / questionable** | economic WR 40.1%, **hit-rate at top-3 = 0%**, top-5 = 0%, top-10 = 20%; quality flags `low_linear_ic`, `weak_top5_hit_rate`; IC pearson 0.039 / spearman 0.105 (near-zero) |
| **Crypto ML edge** (`crypto_ml_edge`) | 2026-02-25 | 🚩 **STALE ~9 mo** | ⚠️ stale (was passing at train time) | 10/10 models passed at 2026-02-25 (acc 0.52–0.77), but no fresh retrain; model drift unverified |
| **Walk-forward / forward validation** (`stabilization/forward_performance_report`) | 2026-03-02 | 🚩 **STALE ~8.5 mo** | ⚠️ stale | overall WR 35.4%, sum PnL **−300**; theory confirmed (graveyard EV −0.58 vs keep EV +0.31) but data old |
| **Copy-trader pick quality** | 2026-11-19 05:19 | ✅ fresh | ✅ operational (filtering gate) | 94.6% pass rate, avg confidence 0.664, avg R:R 2.78; flags inverted TP/SL on 5 picks |

---

## 3. Ground-truth: actual resolved picks in the DB

From `at_pick_outcomes` (all-time, resolved WON/LOST):

### 3.1 Overall
- **Resolved:** 32,352 (WON 13,496 / LOST 18,856)
- **Win rate: 41.7%**
- **Avg PnL: +0.085%** → the *overall* pipeline is roughly **break-even**.

Not profitable as an undifferentiated pool — edge is concentrated.

### 3.2 By asset class
| Class | Trades | WR | Avg PnL |
|---|---|---|---|
| CRYPTO | 27,668 | 42.2% | +0.12% |
| FOREX | 2,789 | 39.7% | +0.33% |
| COMMODITY | 891 | 37.1% | −0.70% |
| EQUITY | 502 | 36.9% | −0.46% |
| MEME | 70 | 30.0% | −3.04% |
| PENNYSTOCK | 4 | 0.0% | −13.21% |

**CRYPTO + FOREX carry the only positive EV.** Commodities/equity/meme/penny are net losers.

### 3.3 By strategy (the real edge)
| Strategy | Trades | WR | Avg PnL |
|---|---|---|---|
| Multi-Timeframe Trend Alignment | 394 | **87.1%** | **+2.79%** |
| Price Acceleration Detector | 234 | **77.4%** | **+2.25%** |
| non_crypto_consensus | 226 | **53.1%** | +0.27% |
| VerifiedStochRsiStrategy | 233 | 49.8% | +0.74% |
| Bollinger Squeeze Breakout | 745 | 46.7% | +0.57% |
| luxalgo_confluence | 5,512 | 47.8% | +0.18% |
| claude_ml_moderate_mut | 1,072 | 43.2% | +0.30% |
| CCI Reversal Scout | 257 | 44.4% | +0.44% |
| MeanReversionBB | 225 | 48.4% | +0.42% |
| Crypto RSI Scout | 601 | **8.5%** | **−1.54%** |
| Extreme Fear Contrarian Buy | 516 | 14.7% | −1.19% |
| rapid_rsi_filter_mut | 302 | 17.9% | −0.79% |
| gainer_compression_relaxed_mut | 275 | 19.3% | −0.48% |
| futures_momentum | 695 | 38.1% | −0.67% |
| battleground_ml_relaxed_mut | 524 | 30.7% | −0.19% |

**Clear positive-EV core:** Multi-Timeframe Trend Alignment, Price Acceleration,
non-crypto-consensus, VerifiedStochRsi, Bollinger Squeeze, CCI Reversal,
MeanReversionBB, luxalgo_confluence, claude_ml_moderate.
**Clear destruction:** Crypto RSI Scout, Extreme Fear Contrarian, rapid_rsi_filter,
gainer_compression, futures_momentum, all meme/penny.

---

## 4. Why the ML signal is real but diluted

1. **The gatekeeper works.** Statistically significant lift (p=0.008), positive
   holdout PF. This is the strongest evidence in the build.
2. **The consensus works.** Backtest shows the *agreement subset* wins at 50.6%
   WR with +38 cumulative PnL — the only net-positive aggregate in the build.
3. **But it is applied to a broad, mostly negative pool.** Only ~9–15 of ~95
   router strategies show real edge; the rest drag the aggregate to break-even.
4. **Stale data feeds cap improvement.** crypto-ML (Feb) and walk-forward (Mar)
   are months old; the feature store hasn't refreshed since Feb. The systems
   are being asked to score on stale inputs.

---

## 5. Recommendation (verdict)

**Do NOT redo or abandon. Do NOT keep everything — curate + refresh.**

| Action | Priority | Rationale |
|---|---|---|
| **Keep & lean on** gatekeeper + consensus + the ~9 positive-EV strategies | High | Proven lift; gatekeeper p=0.008, consensus +38 PnL |
| **Gate the output harder** — run the gatekeeper on every pick, reject low-confidence passes | High | Holdout PF 2.83 only applies to "passed" picks; enforce it |
| **Retrain crypto-ML** (fresh since Feb) and refresh walk-forward | High | Both are the stalest inputs feeding the pipeline |
| **Ban / suppress** negative-EV strategies (Crypto RSI Scout, Extreme Fear, rapid_rsi, gainer_compression, meme, penny) | Medium | 5+ strategies net −1%..−13% per trade |
| **Fix Mercury2** (IC near zero, top-3 hit rate 0%) or demote it | Medium | Currently adds noise, not edge |
| **Reconcile symbol/asset-class naming** (A.2/A.4 of spec) | Medium | 211 forex picks have no computable alpha |
| **Repopulate the DB model registry** (`ml_model_registry`, `ml_models`) | Low | Today models are JSON/file-backed; versioning gaps |
| **Rewrite from scratch** | ✗ Not advised | Would discard the only validated edge (gatekeeper/consensus) |

**Net:** the ML systems are worth maintaining **conditionally** — keep the
validated gatekeeper + consensus + curated strategy core, refresh the stale
training, and hard-gate selection. A full rewrite is unnecessary and would
throw away the best evidence in the repo.

---

## 6. Source files

- `ml_gatekeeper/models/training_report.json` (2026-11-19 03:58)
- `ml_consensus/models/consensus_report.json` (2026-11-19 03:58)
- `crypto_ml_edge/results/training_report.json` (2026-02-25)
- `mercury2/data/metrics_report.json` (2026-11-19 04:49)
- `stabilization/forward_performance_report.json` (2026-03-02)
- `copy_trader_intel/data/pick_quality_report.json` (2026-11-19 05:19)
- Live `at_pick_outcomes` from `ejaguiar1_stocks` on `mysql.50webs.com`
