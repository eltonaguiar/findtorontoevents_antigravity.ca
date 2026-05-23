# Score Validation Deep Dive

Generated: 2026-03-24 23:57 UTC

## Scope

Validated local score/performance stats against the current workspace artifacts:

- `alpha_engine/data/closed_picks.json`
- `alpha_engine/data/active_picks.json`
- `alpha_engine/data/low_score_tracking.json`
- `alpha_engine/data/dynamic_universe.json`
- `alpha_engine/data/universe_expansion.json`
- `alpha_engine/data/coverage_metrics.json`
- `alpha_engine/data/performance_snapshot.json`
- `alpha_engine/elite_scorer.py`
- `alpha_engine/forex_smart_picks.py`

Latest external price checks used:

- Binance live price + 24h ticker endpoints:
  - `https://api.binance.com/api/v3/ticker/price`
  - `https://api.binance.com/api/v3/ticker/24hr`
- Yahoo Finance quotes:
  - `https://finance.yahoo.com/quote/GOOGL/`
  - `https://finance.yahoo.com/quote/AUDUSD%3DX/`
  - `https://finance.yahoo.com/quote/HG%3DF/`

## Executive Verdict

1. `elite_score` is not fake, but it is not the strongest predictor in the current data. It still separates crypto winners from losers, but `ml_score` and raw `confidence` are stronger on the resolved sample.
2. Cross-asset validation is weak. Crypto has enough sample to say something. Forex/equity/futures/commodity do not.
3. Current live conviction outside crypto is poor. The best currently-open non-crypto picks are all still F-grade.
4. Crypto universe coverage is good today. Forex universe coverage is not.
5. The biggest miss is score under-ranking, not crypto symbol discovery. Latest low-score tracking still shows a large pile of strong performers that the score stack did not respect.

## 1. What The Local Data Actually Says

### 1.1 Closed-pick ground truth

- `closed_picks.json` total rows: `502`
- Resolved rows (`WON` or `LOST`): `351`
- Resolved winners: `168`
- Resolved losers: `183`
- Resolved win rate: `47.9%`

Resolved sample by asset class:

| Asset class | Resolved picks | Elite-scored |
| --- | ---: | ---: |
| CRYPTO | 322 | 143 |
| FOREX | 8 | 8 |
| EQUITY | 8 | 8 |
| FUTURES | 7 | 7 |
| COMMODITY | 5 | 5 |
| ON-CHAIN | 1 | 1 |

Takeaway: only crypto has enough sample for a real validation.

### 1.2 Score-vs-performance validation

Overall resolved sample:

| Field | N | Corr with PnL | Corr with win/loss | Top-bottom WR spread | Top-bottom avg PnL spread |
| --- | ---: | ---: | ---: | ---: | ---: |
| `elite_score` | 172 | `+0.141` | `+0.174` | `+23.3 pts` | `+1.07 pts` |
| `confidence` | 351 | `+0.262` | `+0.197` | `+33.3 pts` | `+11.18 pts` |
| `ml_score` | 259 | `+0.337` | `+0.304` | `+37.5 pts` | `+15.60 pts` |

Crypto-only resolved sample:

| Field | N | Corr with PnL | Corr with win/loss | Bottom quartile | Top quartile |
| --- | ---: | ---: | ---: | --- | --- |
| `elite_score` | 143 | `+0.141` | `+0.219` | `25.7% WR`, `-0.4% avg PnL` | `52.6% WR`, `+0.8% avg PnL` |
| `confidence` | 322 | `+0.270` | `+0.217` | `40.0% WR`, `-2.0% avg PnL` | `76.8% WR`, `+9.9% avg PnL` |
| `ml_score` | 230 | `+0.344` | `+0.346` | `36.8% WR`, `-3.6% avg PnL` | `78.0% WR`, `+12.2% avg PnL` |

### 1.3 What this means for `elite_scorer.py`

`alpha_engine/elite_scorer.py` currently says ML/confidence-style inputs were anti-predictive and were zeroed out.

Current resolved data does **not** support zeroing them globally:

- `ml_score` is the strongest current performer on both PnL correlation and win/loss separation.
- `confidence` also beats `elite_score`.
- `elite_score` still helps, but it looks more like a weaker secondary ranker than the primary one.

Important caveat:

- This is based on current stored pick history, not the exact IC training slice used in `elite_scorer.py`.
- On the smaller intersection where all three fields exist on the same rows (`N=80` overall, `N=51` crypto), `elite_score` stays positive but still does not clearly dominate raw `confidence` / `ml_score`.

## 2. Current Top-Score Picks By Asset Class

Mark-to-market was recomputed from entry vs latest external price. I did not trust cached `pnl_pct` for active picks because the active file mixes percentage and decimal conventions.

| Asset class | Top current pick | Score | Entry | Latest checked price | Mark-to-market |
| --- | --- | ---: | ---: | ---: | ---: |
| CRYPTO | `FETUSDT` | 61 | 0.2333 | 0.2419 | `+3.94%` |
| FOREX | `AUDUSD=X` | 15 | 0.699428 | 0.699726 | `+0.04%` |
| EQUITY | `GOOGL` | 17 | 290.44 | 290.44 | `0.00%` |
| COMMODITY | `HG=F` | 10 | 5.5275 | 5.5385 | `+0.20%` |

Key read:

- Crypto currently has the only live pick that looks like a real high-score winner.
- Forex/equity/commodity do not currently have strong scored ideas. Their "top" picks are still F-grade or near-F-grade.

## 3. Low-Score Picks That Still Performed

### 3.1 Current open low-score crypto picks already working

`elite_score < 35`, latest external mark-to-market:

| Symbol | Score | Strategy | Current PnL |
| --- | ---: | --- | ---: |
| `APTUSDT` | 27 | `emergency_gainer_capture` | `+5.84%` |
| `ZROUSDT` | 30 | `emergency_gainer_capture` | `+4.12%` |
| `STGUSDT` | 26 | `emergency_gainer_capture` | `+3.08%` |
| `币安人生USDT` | 28 | `emergency_gainer_capture` | `+0.39%` |
| `BTCUSDT` | 26 | `polymarket_prediction` | `+0.24%` |

### 3.2 Resolved low-score winners

Using resolved `WON` picks with `elite_score < 30`:

| Symbol | Score | Strategy | Realized PnL |
| --- | ---: | --- | ---: |
| `COSUSDT` | 18 | `winner_pattern_precursor` | `+5.96%` |
| `XPLUSDT` | 26 | `winner_pattern_precursor` | `+5.95%` |
| `ANKRUSDT` | 14 | `winner_pattern_precursor` | `+5.95%` |
| `ETHFIUSDT` | 11 | `winner_pattern_precursor` | `+5.95%` |
| `DEGOUSDT` | 11 | `winner_pattern_precursor` | `+5.95%` |
| `JTOUSDT` | 24 | `emergency_gainer_capture` | `+4.95%` |
| `ONTUSDT` | 21 | `emergency_gainer_capture` | `+4.95%` |

### 3.3 Low-score tracking says the miss is still large

Latest snapshot in `alpha_engine/data/low_score_tracking.json`:

- Timestamp: `2026-03-24T23:23:54.435760+00:00`
- Active picks monitored: `538`
- Low-score winners: `178`
- Missed PnL (mark-to-market aggregate): `+471.45%`

Worst under-ranked families in the latest snapshot:

| Family | Low-score winners | Aggregate PnL | Average score |
| --- | ---: | ---: | ---: |
| `rapid_fire` | 65 | `+234.53%` | 3.0 |
| `copy_trader_clones` | 36 | `+97.66%` | 9.1 |
| `kimi_signal_tracking` | 27 | `+46.37%` | 4.7 |
| `goldmine_stocks` | 13 | `+46.12%` | 9.3 |
| `copy_trader_intel` | 21 | `+27.46%` | 11.4 |

Largest current low-score winners in that snapshot:

| Symbol | Score | Family | PnL |
| --- | ---: | --- | ---: |
| `KITEUSDT` | 0 | `rapid_fire` | `+17.56%` |
| `TAOUSDT` | 0 | `rapid_fire` | `+15.47%` |
| `ETHUSDT` | 0 | `kimi_signal_tracking` / aggregated | `+10.13%` |
| `LAUSDT` | 3 | `rapid_fire` | `+10.04%` |
| `SLB` | 11 | `goldmine_stocks` | `+7.64%` |

That is too much missed value to dismiss as noise.

## 4. High-Score Picks That Still Failed

Resolved losers with `elite_score >= 50`:

| Symbol | Score | Strategy | Loss |
| --- | ---: | --- | ---: |
| `AAVEUSDT` | 91 | `copy_hl_NMTD_25M` | `-2.10%` |
| `JCTUSDT` | 88 | `binance_smart_money` | `-3.10%` |
| `REZUSDT` | 68 | `hl_funding_fade` | `-2.59%` |
| `DOTUSDT` | 67 | `cg_taker_aggression` | `-1.60%` |
| `SKYUSDT` | 57 | `copy_hl_NMTD_25M` | `-2.10%` |

Conclusion:

- High score does help on crypto.
- High score is still very far from "safe".
- The current score stack has both false negatives and false positives.

## 5. Universe Coverage Check

### 5.1 Crypto universe

`dynamic_universe.json` was updated at `2026-03-24T23:11:33Z` and currently tracks `171` unique symbols.

Against live Binance 24h data, the top liquid USDT gainers today were:

`ONTUSDT`, `CUSDT`, `HUMAUSDT`, `DUSKUSDT`, `TAOUSDT`, `BATUSDT`, `KITEUSDT`, `GASUSDT`, `FETUSDT`, `ZECUSDT`, `VIRTUALUSDT`, `POLYXUSDT`, `APTUSDT`, `XLMUSDT`, `RENDERUSDT`

Result:

- All of those were already covered by the current merged crypto universe.
- So today’s crypto miss is **not** "we failed to scan the top movers."
- Today’s crypto miss is much more about bad ranking than missing symbols.

Crypto universe issues that still matter:

- `PENGUUSDT` is the highest positive mover I found outside the merged universe, but only at `+1.37%` on the same scan.
- `STGUSDT` and `WLFIUSDT` are live active crypto picks even though they are **not** in the merged universe. That means the universe and the pick generators are out of sync.

### 5.2 Forex universe

`alpha_engine/forex_smart_picks.py` only scans 10 pairs:

- `EURUSD=X`
- `GBPUSD=X`
- `USDJPY=X`
- `AUDUSD=X`
- `USDCAD=X`
- `NZDUSD=X`
- `USDCHF=X`
- `EURJPY=X`
- `GBPJPY=X`
- `AUDJPY=X`

Broader daily FX movers I checked that are **not** in that universe:

| Pair | Latest 1-day move |
| --- | ---: |
| `GBPCAD=X` | `+0.978%` |
| `EURCAD=X` | `+0.813%` |
| `GBPAUD=X` | `+0.793%` |
| `CADJPY=X` | `-0.671%` |
| `GBPCHF=X` | `+0.651%` |
| `EURAUD=X` | `+0.624%` |
| `EURCHF=X` | `+0.494%` |

Conclusion:

- Forex coverage is currently too narrow.
- We are covering majors, but missing many of the strongest cross-pair movers.

## 6. Data Quality Problems Found During Validation

### 6.1 `active_picks.json` mixes PnL units

Examples in the same file:

- `FETUSDT` has `pnl_pct = 4.2006`
- `JTOUSDT` has `pnl_pct = 0.049475`

Those do not use the same scale.

For this report, active-pick PnL was recomputed from `entry_price` to external latest price instead of trusting the stored field.

### 6.2 `performance_snapshot.json` does not match `closed_picks.json`

`performance_snapshot.json` summary says:

- `won = 163`
- `lost = 183`
- `win_rate = 44.9%`

But `closed_picks.json` currently contains:

- `168` resolved winners
- `183` resolved losers
- `47.9%` resolved win rate

So the summary snapshot is stale or built from a different subset.

### 6.3 Current feature coverage is weak

`coverage_metrics.json` says the current batch has:

- `12` total picks
- system coverage only `34.83%`
- `9` low-coverage picks
- `0` high-coverage picks

That helps explain why the current non-crypto book is mostly low-grade noise.

## 7. Bottom Line

If the claim is:

> "Our score stack is working across crypto, forex, and other asset classes, and the top scores are reliably the best picks."

Then the answer is:

- **Crypto:** partially true, but overstated. `elite_score` has signal, yet it is weaker than `ml_score` / `confidence`, and it still misses too many real winners.
- **Forex / equity / commodity:** not proven. The sample is tiny and the live book has no strong non-crypto conviction.
- **Universe coverage:** crypto is mostly fine today; forex is not.

## 8. Recommended Fixes

1. Re-run IC / correlation analysis by **asset class** and **strategy family** before continuing to zero `ml_score` globally.
2. Split scoring into separate models for:
   - crypto momentum/gainers
   - copy-trader / clone families
   - forex majors
   - equity/ETF swing picks
3. Expand forex universe beyond the current 10-pair major set.
4. Hard-fix the `active_picks.json` PnL unit inconsistency.
5. Reconcile `performance_snapshot.json` with `closed_picks.json` so dashboard stats stop drifting.
6. Treat `rapid_fire`, `copy_trader_clones`, `goldmine_stocks`, and `copy_trader_intel` as priority under-scored families. The latest low-score tracking already proves that.

## 9. External Benchmarks

These are the most directly relevant public benchmarks I found for comparing this stack:

- [Man Group 2025 results](https://www.man.com/results-for-the-financial-year-ended-31-december-2025) on `2026-02-26`: `AUM $227.6B`, `relative investment performance 1.3%`, `net inflows $28.7B`.
- [Man AHL Crypto managed long-only](https://www.man.com/ahl-crypto-managed-long-only-programme): systematic crypto mandate with a `30%` volatility target.
- [Two Sigma overview](https://www.twosigma.com/about-us/): scientific systematic trading platform; useful as a process benchmark even though it does not publish a clean daily PnL scoreboard.
- [Numerai Series C update](https://blog.numer.ai/numerai-raises-30m-series-c-at-500m-valuation/) on `2025-11-20`: 2024 meta model `25.45%` net return with one down month, AUM grew from `~$60M` to `$550M`.
- [Numerai Monthly](https://blog.numer.ai/numerai-monthly-numercon-agents-staking-risk-1m-nmr-buyback/) checked `2026-03-24`: the crawl was date-inconsistent, so I did not use it for date-sensitive claims; the usable point is that Numerai Crypto has an active tournament and a public crypto leaderboard.
- [WorldQuant IQC 2026](https://www.worldquant.com/brain/iqc/): public alpha-generation benchmark with 2026 dates, no fee to participate, and explicit alpha scoring on historical market data.
- [Kalshi Research launch](https://news.kalshi.com/p/kalshi-launches-research-arm-prediction-markets) on `2025-12-22`: Kalshi claims inflation forecasts beat Wall Street by `40%`, matched/beat on `85%` of inflation prints one week out, and had `50% lower MAE` in shock regimes.
- [Metaculus FutureEval](https://www.metaculus.com/futureeval/) checked `2026-03-24`: current leaderboard shows `Pro Forecasters 22.38` vs `Community 19.54` and updates daily.
- [Metaculus API launch](https://www.metaculus.com/notebooks/15141/officially-launching-the-metaculus-api/) on `2023-04-25`, with API updates on `2026-03-09`.
- [Kalshi public API docs](https://docs.kalshi.com/getting_started/quick_start_market_data) and [historical data docs](https://docs.kalshi.com/getting_started/historical_data): live and historical market data are publicly queryable.
- [Manifold docs](https://docs.manifold.markets/): API docs plus data dumps and licensing.
- Polymarket leaderboard tools that are live but third-party, not official:
  - [Polymarket Analytics](https://polymarketanalytics.com/traders) checked `2026-03-24`: updates every 5 minutes and tracks `1M+` traders by PnL / win rate.
  - [PolyMonit](https://polymonit.com/leaderboard/) checked `2026-03-24`: publishes monthly leaderboards; its March 2026 page shows a top wallet at `+$487K` and February at `+$392K`.

Interpretation:

- The strongest public benchmarks are not raw "top trader" screenshots. They are repeatable scoring systems with historical calibration and clear update cadence.
- For this repo, the most useful outside comparables are Kalshi research, Metaculus FutureEval, Numerai Crypto, and Polymarket whale analytics.

## 10. Root-Cause Deep Dive

### 10.1 The production gate stack is collapsing the book

I replayed the current `alpha_engine/data/active_picks.json` through `production_scanner.apply_quality_gates()` against the current `closed_picks.json`.

- Active picks checked: `68`
- Passed quality gates: `2`
- Rejected: `66`
- The only passers were:
  - `FETUSDT` via `ml_enhanced_FETUSDT_1d_B_lightgbm`
  - `RENDERUSDT` via `ml_enhanced_RENDERUSDT_1h_D_ensemble_stack`

Largest reject buckets:

- `16` -> `SHORT blocked: ALL SHORTS DISABLED`
- `10` -> `conf < 0.55`
- `14` combined -> algorithmic probation confidence failures
- `8` combined -> unvalidated strategy + low-confidence failures
- `5` -> extreme `vol_ratio > 5.0`
- `1` -> toxic-symbol gate on `BTCUSDT`

This is not a normal selection layer. It is a near-total choke point.

Concrete false negatives from the live file:

- `APTUSDT`, `ZROUSDT`, and `STGUSDT` were already positive mark-to-market in Section 3, but each was still rejected as `[ALGO PROBATION] conf < 0.80`.
- Multiple `polymarket_prediction` SHORT signals with `confidence` around `0.935-0.95` were rejected by the emergency global short block.

### 10.2 Smart Picks has a second hard choke after production gating

Current `alpha_engine/data/smart_picks.json` snapshot:

- Generated: `2026-03-24T21:59:09.398106+00:00`
- `total_scored = 8`
- `crypto_scored = 8`
- `non_crypto_scored = 0`
- Final published picks: `6`

Current exclusion counts in that file:

- `near_tp = 159`
- `no_price = 121`
- `too_stale = 76`
- `low_validated_score = 48`
- `banned_system = 26`
- `mtf_not_aligned = 7`

This matters because Smart Picks is supposed to be the refined final layer, but it is currently operating on a starved candidate set.

### 10.3 The repo is mixing incompatible score philosophies

The pipeline is not acting like one coherent model:

- `smart_picks_engine.py` and `production_scanner.py` rank with `ml_score` / `confidence` / forward WR.
- `elite_scorer.py`, `data_coverage_enforcer.py`, and `score_booster.py` still cap, deflate, or zero many sparse/public/copy-trader families.
- `smart_picks_engine.py` then hard-rejects `validated_score < 30`.

The result is stacked vetoes:

1. upstream source/trust penalties
2. score zeroing or caps
3. quality gates
4. tier gates
5. portfolio cap / copy-trader quota

That explains why the live system can "have the data" and still fail to convert it into accepted picks.

### 10.4 `score_booster.py` is zeroing candidates, not just demoting them

This is one of the strongest structural problems.

- Same-symbol long/short conflicts: weaker side is set to `score = 0`
- Symbol hard cap: after 3 picks on a symbol, excess picks are set to `score = 0`
- Lower-ranked duplicates also take hard penalties before Smart Picks ever ranks them

That is too destructive for discovery-mode families like:

- `copy_trader_consensus`
- `copy_trader_intel`
- `polymarket_prediction`
- clone families

For these families, the right control is usually ranking demotion or position-size decay, not zeroing.

### 10.5 Public trader "win rates" are probably overstated upstream

`copy_trader_intel/data/qualified_traders.json` currently contains:

- `42` traders total
- `11` traders with `100%` win rate, `>=100` trades, and `0` recorded losses
- `14` traders with `>=95%` win rate

That is not plausible as direct copy-trading ground truth.

The local forward-reality layer is much more normal. `alpha_engine/data/top_trader_analysis.json` on `341` closed picks shows:

- `whale_20.7M`: `57.2%` WR on `152` picks
- `NMTD_25M`: `53.1%` WR on `96` picks
- `whale_123M_87roi`: `60.0%` WR on `5` picks
- `whale_58M_287roi`: `83.3%` WR on `6` picks

That strongly suggests the public trader files are measuring something different from our copied entries, or the fill/accounting layer is biased.

Another red flag: `copy_trader_intel/copytrader_source_harvester.py` includes fallback research rows with combinations like:

- `89.5%` WR with `70.6%` max drawdown
- `100%` WR with `83.4%` max drawdown
- `92.9%` WR with `93.2%` max drawdown

Those are leaderboard mirages, not portfolio-quality signals.

### 10.6 Prediction-market integration is thinner than it looks

The local code comment in `alpha_engine/polymarket_signals.py` says there is no documented public leaderboard API.

That is now outdated.

Official Polymarket docs say the public Data API includes:

- user positions
- closed positions
- activity
- holder data
- open interest
- leaderboards

I also queried the live official endpoint directly on `2026-03-24`:

- `https://data-api.polymarket.com/v1/leaderboard`

Top 5 returned PnL values of roughly:

- `+$1.98M`
- `+$210.6K`
- `+$187.8K`
- `+$171.0K`
- `+$159.3K`

So the missing piece is not access. The missing piece is that these sources are not wired into the same local stats/gate path that the rest of the engine reads.

Related problem:

- `strategy_performance.json` currently has no `polymarket_prediction` entries
- it also has no `ct_consensus_*` entries

That means those families arrive with weak coverage and often fail lookup-driven gates by construction.

## 11. What Actually Does Not Add Up

The contradiction is real, but it is explainable:

- We do have a lot of public/copy/prediction-market data.
- We also have multiple layers that suppress sparse, short, conflicting, low-coverage, or under-scored families before they can compound enough local evidence.
- At the same time, some upstream trader stats are likely overstating edge because trader-level fill history is not the same thing as our copied entry timing, copied exit timing, TP/SL mapping, or filtered execution.

So these two things can both be true:

1. some outside public signals are genuinely informative
2. the current pipeline still turns them into a mediocre realized book

That is why the current problem looks like a gate/calibration failure more than a pure signal-discovery failure.

## 12. Exception Candidates

These are the highest-confidence candidates for controlled exceptions, not blind global loosening:

1. `emergency_gainer_capture`
   - Current evidence: tiny resolved sample, but current live false negatives are obvious.
   - Proposed exception: bypass algorithmic probation when the symbol is a top liquid 24h gainer and `confidence >= 0.65`.

2. `polymarket_prediction`
   - Current evidence: official public leaderboard/position data exists, but the family is under-integrated locally.
   - Proposed exception: allow a separate prediction-market lane; do not force it through the blanket short ban when market confidence and liquidity are high.

3. `copy_trader_consensus` and verified `copy_hl_*`
   - Current evidence: local low-score tracking still shows meaningful missed upside from copy-trader families.
   - Proposed exception: bypass `validated_score < 30` and some sparse-coverage penalties when local copied outcomes are already positive.

4. Non-crypto `multi_asset_copytrader`
   - Current evidence: the system is learning almost nothing because Smart Picks currently scores `0` non-crypto picks.
   - Proposed exception: move non-crypto into a capped learning lane instead of forcing it through the same crypto-oriented quarantine.

## 13. A/B/C/D Forward Test Design

The repo already has a forward-test runner in `alpha_engine/ab_test_portfolios.py`, but current state is not mature enough to answer the big question yet.

As of `2026-03-24`:

- `A/B/C/D/E/F/H`: `0` closed trades
- `G` control: `1` closed trade

There is also a broader but fragmented experiment layer:

- `alpha_engine/forward_test_portfolios.py`
- `alpha_engine/ab_test_portfolios.py`
- `alpha_engine/clone_ab_tester.py`
- `ml_battleground/abc_forward_test/scanner.py`
- `paper_trading/portfolio_manager.py`
- `paper_trading/permutation_portfolio_manager.py`

So the framework exists, but the evidence base is still effectively empty.

Important credibility gaps from that stack:

- `forward_test_portfolios.py` coerces anything not explicitly `FOREX` or `EQUITY` into `CRYPTO`, so futures and commodity picks can leak into crypto buckets.
- The same stack does not properly mark non-crypto to market yet, so forex/equity/futures portfolio stats are not trustworthy.
- Samples are still tiny across the forward-test files, so any current leaderboard is directional only.
- There is no single canonical experiment scoreboard, so results are split across incompatible state/history files.

Recommended experiment lanes:

### A. Control

- Current production stack unchanged
- This is the baseline

### B. Public/Copy Exception Lane

- Keep current sizing and risk
- Relax:
  - algorithmic probation for verified public/copy families
  - `validated_score < 30` hard reject
  - blanket short ban for prediction-market signals with high liquidity/confidence

### C. Soft-Gate Lane

- Replace score zeroing with rank demotion / size haircut
- Keep R:R and catastrophic-risk guards
- Do not hard-kill same-symbol weaker side; just shrink it

### D. Non-Crypto Learning Lane

- Expand forex universe
- require live price enrichment
- cap capital small
- learn from outcomes instead of suppressing the asset class to zero

All four lanes should track:

- win rate
- avg PnL
- profit factor
- max drawdown
- accepted-pick count
- rejected-shadow-book performance
- missed-winner rate
- per-family attribution

## 14. Backtesting / Replay Requirements

Backtesting modules already exist in the repo:

- `alpha_engine/walk_forward_backtester.py`
- `alpha_engine/unified_backtest.py`
- `alpha_engine/validation/purged_cv.py`
- `copy_trader_intel/copytrader_quality_backtest.py`
- `copy_trader_intel/consensus_backtester.py`

But the missing component is a proper rejected-picks replay lane.

Also missing: one canonical experiment registry that ties together:

- forward-test portfolio runs
- A/B/C portfolio variants
- clone experiments
- walk-forward/backtest results
- realized forward outcomes

Without that join key, backtest-vs-forward comparisons stay anecdotal.

Highest-value addition:

- write every rejected pick to a shadow log with:
  - timestamp
  - symbol
  - family
  - direction
  - score fields
  - exact reject reason
  - later mark-to-market / realized outcome

Without that, we can see low-score winners in aggregate, but we still cannot cleanly measure gate cost by rule.

## 15. Highest-Confidence Fix Order

1. Add a rejected-picks shadow portfolio and outcome tracker.
2. Replace score zeroing with demotion / size cuts in `score_booster.py`.
3. Relax `validated_score < 30` for trusted public/copy/prediction-market families.
4. Add explicit exception lanes for `polymarket_prediction`, `copy_trader_consensus`, and verified copy-trader families.
5. Expand forex coverage and wire live price enrichment for non-crypto.
6. Stop treating trader-level `100%` WR snapshots as execution truth until reconciled against copied outcomes.

If I reduce this to one sentence:

The biggest current problem is not lack of signal. It is that the repo trusts some external stats too much at ingestion time, distrusts those same families too much at admission time, and learns too little in the middle because the gates are blocking the feedback loop.

## 16. Audited Quant-System Cross-Check

This section re-checks the report from a stricter crypto/forex quant-audit perspective.

The standard here is not "is the conclusion plausible?" It is:

- can the reported statistic be independently reproduced?
- is the source provenance clear?
- is the result net of realistic execution effects?
- is the validation method appropriate for the asset class and sample size?
- would an internal model validation or external audit team accept the evidence chain?

### 16.1 What holds up under an audited quant lens

These parts of the report are still strong:

1. Data reconciliation failures are real and material.
   - `active_picks.json` mixes PnL units.
   - `performance_snapshot.json` does not reconcile to `closed_picks.json`.
   - Those are audit-grade control failures, not cosmetic issues.

2. The crypto/non-crypto sample-size distinction is correct.
   - Crypto has enough resolved picks to analyze directionally.
   - Forex/equity/futures/commodity do not.
   - So crypto-only conclusions are much more defensible than cross-asset conclusions.

3. The ranking conclusion is directionally valid.
   - On the current resolved sample, `ml_score` and `confidence` are stronger than `elite_score`.
   - That means a blanket "zero ML/confidence globally" stance is not supported by current stored outcomes.

4. The gate replay is a valid operational red flag.
   - Replaying `apply_quality_gates()` and seeing only `2/68` active picks survive is enough to treat the admission layer as a likely choke point.
   - But that is still an operational diagnosis, not yet a full causal proof of lost alpha.

### 16.2 What would fail audit sign-off today

If this repo were reviewed like an institutional quant stack, these claims would still fail or need stronger evidence:

1. Any broad cross-asset claim that the score stack "works across crypto, forex, and other asset classes."
   - The non-crypto resolved samples are too small.
   - This would be rejected as underpowered.

2. Any claim that low-score winners alone prove a production ranking failure.
   - The current low-score tracker is useful.
   - But audit-grade sign-off would require frozen timestamps, realized-vs-MTM separation, and cost-adjusted outcome attribution.

3. Any strong statement that the gates are definitively the root cause.
   - Current evidence makes that the leading hypothesis.
   - But institutional sign-off would require controlled replay:
     - same frozen input snapshot
     - same timestamps
     - same prices
     - alternative thresholds
     - side-by-side accepted vs rejected outcomes

4. Any use of the current public trader stats as execution truth.
   - `qualified_traders.json` contains too many `95-100%` WR rows with very large trade counts and zero losses.
   - That is not acceptable as copied-trade ground truth without provenance and reconciliation.

### 16.3 Provenance would fail review in several copy-trader feeds

This is one of the most important audit findings.

Multiple scrapers explicitly fall back to seed or research traders when live endpoints fail:

- `copy_trader_intel/bybit_scraper.py`: "Leaderboard returned no data, using seed traders"
- `copy_trader_intel/bitget_scraper.py`: "Using seed traders from research data"
- `copy_trader_intel/hyperliquid_scraper.py`: "Leaderboard API unavailable -- using seed wallets only"

That means some "live trader quality" inputs are not purely live leaderboard data.

From an audited-system perspective, that is only acceptable if every downstream row is tagged with immutable provenance such as:

- `api`
- `web`
- `seed`
- `research`
- `resolved_from_seed`

Without that, the score stack is partially training or gating on mixed provenance while presenting it as one class of evidence.

### 16.4 Forward-test credibility is not audit-ready yet

The experiment stack has useful machinery, but it is not yet audit-ready.

Main failures:

1. Asset-class leakage.
   - `alpha_engine/forward_test_portfolios.py` maps anything not explicitly `FOREX` or `EQUITY` into `CRYPTO`.
   - That means futures and commodities can contaminate crypto portfolio statistics.

2. Non-crypto mark-to-market is incomplete.
   - `forward_test_portfolios.fetch_price()` returns `None` for non-crypto.
   - Exit logic then falls back to last known or entry price.
   - So non-crypto forward-test PnL is not trustworthy.

3. Execution realism is inconsistent across stacks.
   - `paper_trading/portfolio_manager.py` applies a `0.7%` round-trip transaction cost for crypto.
   - The main Alpha Engine forward/A-B layers do not apply a consistent matching cost model.
   - That makes stack-to-stack comparisons non-comparable.

4. Closed-trade counts are still tiny in the active A/B layer.
   - So current forward-test leaderboards are informative for direction only, not final ranking decisions.

### 16.5 What the repo already has that is audit-positive

To be fair, the repo does contain several building blocks that align with real quant validation standards:

- `alpha_engine/model_audit_log.py`
  - data hashes
  - training-run logging
  - rollback mechanism

- `alpha_engine/validation/purged_cv.py`
  - purge and embargo logic
  - explicitly designed to reduce time-series leakage

- `alpha_engine/audit_sync.py`
  - consolidated database sync and portfolio snapshot infrastructure

- `paper_trading/portfolio_manager.py`
  - position sizing
  - transaction-cost handling
  - portfolio-level drawdown accounting

These are good signs.

The problem is not absence of audit concepts.
The problem is that these controls are fragmented and are not the same path currently being used to justify the main score/gate conclusions.

### 16.6 External standards that matter for the next pass

The following official/current references are the right benchmark for the next validation pass:

- Federal Reserve SR 11-7 model risk management:
  - https://www.federalreserve.gov/supervisionreg/srletters/sr1107.htm
- NIST AI RMF and TEVV/playbook:
  - https://www.nist.gov/itl/ai-risk-management-framework
  - https://www.nist.gov/itl/ai-risk-management-framework/nist-ai-rmf-playbook
- SEC Marketing Compliance FAQ:
  - https://www.sec.gov/rules-regulations/staff-guidance/division-investment-management-frequently-asked-questions/marketing-compliance-frequently-asked-questions
- Kalshi official market-data and historical-data docs:
  - https://docs.kalshi.com/getting_started/quick_start_market_data
  - https://docs.kalshi.com/getting_started/historical_data
- Polymarket official API docs:
  - https://docs.polymarket.com/api-reference/introduction
- OANDA official FX data resources:
  - https://www.oanda.com/foreign-exchange-data-services/en/historical-currency-converter/
  - https://www.oanda.com/foreign-exchange-data-services/en/exchange-rates-api/
- FX Global Code update:
  - https://www.globalfxc.org/press-p250124/
- BIS Project Rio:
  - https://www.bis.org/publ/othp104.htm

Interpretation:

- Official prediction-market data access now exists and is documented.
- Official FX data and market-conduct references also exist.
- So the system no longer has a good excuse for mixing informal screenshots, seed fallbacks, and partially marked non-crypto data in one performance narrative.

### 16.7 Audit-ready next-step checklist

If this is to become audit-grade for crypto/forex, the next pass should require all of the following:

1. Freeze a daily snapshot bundle with hashes.
   - inputs
   - prices
   - scores
   - gate outputs
   - config values

2. Split every performance table into:
   - realized closed PnL
   - live mark-to-market PnL
   - hypothetical / backtest PnL

3. Add immutable provenance tags to every trader and pick source.
   - especially `api` vs `seed` vs `research`

4. Add a rejected-picks shadow book.
   - exact reject reason
   - later realized or MTM outcome
   - rule-level missed-alpha attribution

5. Use one canonical cost model across forward-test stacks.
   - fees
   - slippage
   - spread assumptions
   - asset-class-specific transaction costs

6. Separate crypto and forex validation completely.
   - different universes
   - different execution assumptions
   - different thresholds
   - different performance sign-off criteria

7. Require controlled gate A/B/C replay before changing policy.
   - current policy
   - exception policy
   - soft-gate policy
   - non-crypto learning lane

### 16.8 Audited-quant verdict

From an audited quant crypto/forex perspective:

- the report’s data-quality concerns are valid
- the gate-choke diagnosis is plausible
- the crypto-only ranking conclusion is directionally credible
- the public-trader provenance is weaker than it should be
- the forward-test layer is not yet strong enough to certify causal claims

So the right institutional conclusion is:

The current report is a strong internal diagnostic, but not yet an audit-grade proof. It correctly identifies where the system is likely failing, but the next step must be frozen-snapshot replay, provenance tagging, consistent execution-cost treatment, and separate crypto/forex validation before policy changes are treated as validated.
