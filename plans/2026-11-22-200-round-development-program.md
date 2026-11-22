# 2026-11-22 — 200-Round Development Program

**Purpose.** Turn the 12-asset-class audit (which reached **zero CANDIDATEs**) into a
disciplined, falsifiable program of 200 rounds: first *unblock the data*, then *test
mechanisms honestly*, then *prove cost survival, robustness, portfolio fit, paper
behaviour, monitoring, live pretend-trades, peer replication, and finally promotion
decisions*. This is a research program, **not** a promise of profit. The default
expected outcome is still mostly KILL; the program exists to make each KILL or
CANDIDATE defensible.

- **Author:** deepseek-flash (architect mode)
- **Created:** 2026-11-22T08:55Z (03:55 EST)
- **Governing standard:** [`PROOF_METHODOLOGY.md`](../docs/audit_review_2026-11-22/PROOF_METHODOLOGY.md)
- **Consolidated findings:** [`00_FINDINGS_2026-11-22.md`](../docs/edge_research/00_FINDINGS_2026-11-22.md)
- **Machine verdicts:** [`reports/per_class_edge_verdicts_20261122.json`](../reports/per_class_edge_verdicts_20261122.json)

---

## Verified starting facts (from RECON, 2026-11-22)

| # | Fact | Evidence |
|---|------|----------|
| F1 | **No `REALTIMECHALLENGE_*.MD` file exists anywhere in the repo** (case-insensitive full-tree search returned 0). This prototype is therefore the first such file. | repo-wide search, 0 hits |
| F2 | **A real live-quote path exists and is wired.** [`tools/realtime_challenge.py`](../tools/realtime_challenge.py:105) fetches live 5m bars from Binance spot mirrors (`api.binance.com`→`api1..api4`), cross-checks against KuCoin, requires **≥2 venues agreeing within 50bp**, resolves intrabar TP/SL **pessimistically** (stop first), and charges **10bp/side**. | [`tools/realtime_challenge.py`](../tools/realtime_challenge.py:104) |
| F3 | **A real single-quote fetcher for equities/crypto exists.** [`live_monitor/position_monitor.py`](../live_monitor/position_monitor.py:28) pulls live Binance ticker price (`.us` + global + mirror); [`tools/ai_tournament/price_tracker.py`](../tools/ai_tournament/price_tracker.py:126) routes crypto/equity/forex/commodity/bond with `yfinance`/AlphaVantage/exchangerate-api failover. | [`live_monitor/position_monitor.py`](../live_monitor/position_monitor.py:28), [`tools/ai_tournament/price_tracker.py`](../tools/ai_tournament/price_tracker.py:79) |
| F4 | **An open/close paper-trade ledger format exists.** [`paper_trading/data/closed_picks.json`](../paper_trading/data/closed_picks.json:1) fields: `id, symbol, direction, entry_price, current_price, tp, sl, strategy, strategy_name, portfolio_type, conviction_tier, position_size_usd, shares, entry_date, status, exit_price, exit_date, pnl_pct, pnl_usd, mfe, mae, confidence, reason`. Challenge ledger (JSONL) at [`reports/realtime_challenge/state.json`](../reports/realtime_challenge/state.json:1) with `rules / open / closed / skipped`. | [`paper_trading/data/closed_picks.json`](../paper_trading/data/closed_picks.json:1) |
| F5 | **Challenge engine state is empty today** (`open: []`, `closed: []`, `skipped: []`, run_id `20261122T085654Z`) — no trades placed yet. | [`reports/realtime_challenge/state.json`](../reports/realtime_challenge/state.json:24) |
| F6 | **Free/no-key APIs already wired:** Binance spot (`/api/v3/ticker/price`, `/klines`), Binance US, Binance futures (`fapi`), CoinGecko, KuCoin, Kraken, CryptoCompare, Yahoo Finance chart (`query1.finance.yahoo.com/v8/finance/chart`), Stooq. **Key-required (optional, env-gated):** AlphaVantage (`ALPHAVANTAGE_API_KEY`), Finnhub (`FINNHUB`/`token`), Polygon (`POLYGON_KEY`), TwelveData, OANDA, CoinGecko Pro (`x-cg-pro-api-key`). | [`alpha_engine/equity_price_failover.py`](../alpha_engine/equity_price_failover.py:670), [`tools/ai_tournament/price_tracker.py`](../tools/ai_tournament/price_tracker.py:126), [`data_fetcher_enhanced.py`](../data_fetcher_enhanced.py:41) |
| F7 | **FOREX and BOND are now READY (2026-11-22, Block 1 R1/R2); other target classes remain BLOCKED_DATA.** `data/forex_rate_cache/` holds 110 real pair CSVs (~2,022 dated rows each, Frankfurter/ECB rates 2018-12-31..2026-11-20), so FOREX (`≥100 files`) and BOND (`≥1 file`) pass; the Round 2 gap audit found 0 pairs with >5-business-day interior gaps. COMMODITY/FUTURES still need `data/commodity_price_cache` + `data/cftc_cot`; EQUITY needs vintage earnings + survivorship-free universe. | [`tools/class_data_readiness.py`](../tools/class_data_readiness.py:59), [`reports/block1_r02_fx_gap_audit.json`](../reports/block1_r02_fx_gap_audit.json) |
| F8 | **7 monitoring workflows already run on cron:** `outcome-resolver` (:47 hourly), `live_monitor`/`live-monitor-refresh` (:42 hourly), `portfolio-trackers` (:48 hourly), `crypto-intraday-sim` (:07/:37), `forward-tracking-v2` (:28 hourly), `ghcopilot-paper-monitor` (:20 hourly), `dashboard-pick-trader` (:38 hourly), `verified-pilot-daily` (06:53 daily). `tv-paper-tpsl-watchdog` every 15m. | `.github/workflows/*.yml` |
| F9 | **git state:** HEAD = `89ccdf0af55f70df7a202a63f460350d2b7af2c5` ("research(equity): full H-033 statistics - WEAK not CANDIDATE"). Working tree is heavily dirty (many ` M` and ` D` entries plus untracked workflows). | `git log --oneline -5`, `git status --short` (run 2026-11-22T09:02Z) |
| F10 | **`reports/forward_observations.jsonl` IS DIRTY** (` M reports/forward_observations.jsonl`) — modified by another actor (the pilot bridge / forward ingest). It must not be bundled into any commit that is not explicitly about it; only push branches where every changed file is yours. | `git status --short -- reports/forward_observations.jsonl` → ` M reports/forward_observations.jsonl` |

**Hard constraint that governs everything below:** cost, not signal, is the binding
constraint almost everywhere (ETF gross +0.76bps → net −9.24bps; Coinbase premium
gross +9.85 → net −20.15; Futures TSMOM gross +1.00 → net −9.00). Any round that
reports a gross edge without a net-of-2×-cost number is **incomplete**.

---

## Standing honesty rules (apply to every round)

1. **Never launder uncertainty into a confident number.** If n is small, print n next
   to the number. A CI that straddles zero is reported as straddling zero.
2. **Selection on the test statistic is a failure, not a win.** Choosing the
   symbol/parameter/period that gave the best result and then reporting that result as
   evidence inflates the false-positive rate. Every such choice must be counted in the
   trial count fed to DSR.
3. **`eff` measures score separation, not profit.** A high effect size with a net
   negative expectancy is a failed hypothesis, not a promising one.
4. **UNMEASURED is a legitimate outcome.** "I could not measure this" is honest and
   complete; "I measured it and it looked good when unverified" is neither. Prefer
   UNMEASURED over a fabricated number.
5. **A closed loss stays a loss.** No rolling a loser into a "longer-term hold", no
   re-basing entry prices after the fact.
6. **Zero completed trades in a live round scores ZERO, not neutral.**

---

## Block flow

```mermaid
flowchart TD
    B1[Block 1: Data acquisition and point-in-time reconstruction] --> B2[Block 2: Per-class mechanism testing]
    B2 --> B3[Block 3: Cost, capacity, slippage realism]
    B3 --> B4[Block 4: Robustness and multiplicity control]
    B4 --> B5[Block 5: Portfolio construction]
    B5 --> B6[Block 6: Paper trading on live data]
    B6 --> B7[Block 7: GHA monitoring infrastructure]
    B7 --> B8[Block 8: Live pretend challenge rounds]
    B8 --> B9[Block 9: Peer cross-check]
    B9 --> B10[Block 10: Synthesis and promotion decisions]
    B1 -. unblocked classes only .-> B2
    B3 -. cost survival under 60 percent kills .-> B10
    B4 -. DSR under 0.95 kills .-> B10
```

Serial by design: each block's gate must pass for a class before that class advances to
the next block. Classes that fail a block's gate are sent straight to Block 10 to be
published as KILL, and do not consume later rounds.

---

# Block 1 — Rounds 1–20: Data acquisition & point-in-time reconstruction

Priority order by number of classes unblocked: **(a) FX spot/forward series** (unblocks
FOREX, and BOND curve), **(b) futures continuous series** (unblocks FUTURES + COMMODITY),
**(c) CFTC COT history** (unblocks COMMODITY positioning), **(d) point-in-time earnings
consensus + estimate revision** (unblocks EQUITY PEAD), **(e) point-in-time index
membership** (unblocks survivorship-free EQUITY/ETF/INDEX). Gate per round = a **named
class flips from BLOCKED_DATA to READY** in `python3 tools/class_data_readiness.py --json`,
with the row/file count stated.

**Round 1** — *a) FX spot series (majors).*
- Hypothesis: A free daily FX source (Yahoo `EURUSD=X`-style or Frankfurter) can populate `data/forex_rate_cache/` with ≥100 dated files for G10 majors, matching what `class_data_readiness.py` requires for FOREX.
- Gate: `class_data_readiness.py` FOREX `fx rates` gap disappears (≥100 files); FOREX flips to READY.
- Stop condition: If no free source yields ≥100 dated, timestamped records for at least 6 G10 pairs within 3 fetch attempts, mark FOREX UNMEASURABLE and stop the FX sub-branch.
- Output: `data/forex_rate_cache/*.json` + append `docs/edge_research/block1_r01_fx_spot.md`.

**Round 2** — *a) FX spot continuity & gap audit.*
- Hypothesis: The Round-1 cache has no calendar gaps > 5 business days and no duplicate dates per pair.
- Gate: `python3 tools/class_data_readiness.py` still READY AND a gap-audit reports 0 pairs with >5-day interior gaps.
- Stop condition: If >20% of pairs show interior gaps that cannot be filled from a second source, downgrade FOREX back to BLOCKED_DATA.
- Output: `reports/block1_r02_fx_gap_audit.json`.

**Round 3** — *a) FX forward/interest-rate differential inputs.*
- Hypothesis: Short-rate series (policy rates or 1m forward points) needed for a carry signal can be assembled point-in-time for ≥6 currencies.
- Gate: ≥6 currencies with dated rate series covering the backtest window; recorded in readiness JSON as a FOREX sub-requirement passing.
- Stop condition: If only spot is available with no rate/forward input, restrict FOREX scope to trend-only and note carry is UNMEASURABLE.
- Output: `data/forex_rate_cache/rates_*.json` + note.

**Round 4** — *b) Futures continuous series (commodity + index).*
- Hypothesis: Continuous back-adjusted daily series for ≥10 futures (energy, metals, ag, equity index) can be assembled into `data/commodity_price_cache/`.
- Gate: `class_data_readiness.py` FUTURES `futures prices` requirement (≥20 files) satisfied; FUTURES flips READY.
- Stop condition: If <20 contracts obtainable free, restrict to the obtainable subset and label remaining futures UNMEASURABLE.
- Output: `data/commodity_price_cache/*.csv` + `docs/edge_research/block1_r04_futures_series.md`.

**Round 5** — *b) Roll-method documentation.*
- Hypothesis: A single documented back-adjustment/roll rule can be applied uniformly so no series mixes contract months arbitrarily.
- Gate: Every futures file carries a `roll_rule` metadata field; 100% coverage.
- Stop condition: If series cannot state their roll rule, they cannot support roll-yield tests → demote to price-only TSMOM.
- Output: `data/commodity_price_cache/_meta.json`.

**Round 6** — *c) CFTC COT history.*
- Hypothesis: CFTC Commitments of Traders historical CSV (free, public) can populate `data/cftc_cot/` with ≥100 weekly dated records per commodity.
- Gate: `class_data_readiness.py` COMMODITY `COT history` (≥100 files) satisfied; COMMODITY partly READY (pending futures prices from R4).
- Stop condition: If COT history is only current-snapshot, mark COMMODITY positioning UNMEASURABLE.
- Output: `data/cftc_cot/*.json`.

**Round 7** — *c) COT vintage discipline.*
- Hypothesis: Each COT record carries its true release date (Tuesday positions, Friday release) so tests cannot use pre-release data.
- Gate: 100% of COT rows have `release_date >= report_date`; a look-ahead lint passes.
- Stop condition: If release dates are unavailable, block COMMODITY positioning.
- Output: `reports/block1_r07_cot_vintage_lint.json`.

**Round 8** — *c) COMMODITY readiness flip.*
- Hypothesis: With R4 futures prices + R6/R7 COT, COMMODITY reaches full READY.
- Gate: `class_data_readiness.py` COMMODITY both requirements satisfied → READY.
- Stop condition: If either requirement still fails, COMMODITY stays BLOCKED_DATA and is not tested in Block 2.
- Output: readiness JSON snapshot.

**Round 9** — *d) Point-in-time earnings consensus.*
- Hypothesis: A point-in-time consensus EPS estimate (with `estimate_asof`) can be sourced for ≥100 S&P names, replacing the single non-vintage snapshot.
- Gate: `tools/class_data_readiness.py::_earnings_vintage_ok()` returns `True` for the sample (history rows all carry `estimate_asof`).
- Stop condition: If no free source provides vintage consensus, EQUITY PEAD is permanently UNMEASURABLE — stop the PEAD branch.
- Output: `data/earnings/<TICKER>/latest.json` with vintage fields + note.

**Round 10** — *d) Estimate-revision series.*
- Hypothesis: For ≥100 names a revision series (Δconsensus over time) can be built, enabling a revision-momentum test distinct from SUE.
- Gate: ≥100 names with ≥4 vintage estimates each in the cache.
- Stop condition: If <100 names qualify, restrict to SUE-only PEAD and record revision as UNMEASURABLE.
- Output: `data/earnings/revisions_index.json`.

**Round 11** — *e) Point-in-time index membership.*
- Hypothesis: Historical S&P 500 (and/or Russell) constituent changes can be sourced, giving a survivorship-free universe.
- Gate: `class_data_readiness.py` EQUITY `survivorship-free universe` gap clears.
- Stop condition: If only current constituents are obtainable (as today), EQUITY and ETF remain survivorship-biased; disclose and downgrade.
- Output: `data/universe/sp500_pit_membership.csv`.

**Round 12** — *e) Delisted-name price backfill.*
- Hypothesis: Delisted tickers from R11 can have their price history backfilled so they are not silently dropped.
- Gate: ≥90% of delisted names in R11 have usable price history.
- Stop condition: If <60% backfillable, survivorship correction is cosmetic → mark UNMEASURABLE.
- Output: `data/equity_quote_cache/*delisted*`.

**Round 13** — *EQUITY readiness flip.*
- Hypothesis: With R9/R11/R12, EQUITY reaches READY for PEAD.
- Gate: `class_data_readiness.py` EQUITY all three requirements satisfied → READY.
- Stop condition: If vintage earnings still missing, EQUITY stays BLOCKED_DATA for PEAD.
- Output: readiness JSON snapshot.

**Round 14** — *BOND curve readiness.*
- Hypothesis: A dated yield-curve series (2s10s etc.) can populate `data/forex_rate_cache/` (the path BOND currently points at) sufficiently for BOND.
- Gate: `class_data_readiness.py` BOND `rate curve` (≥1) passes → READY.
- Stop condition: If curve history is only current, BOND stays BLOCKED_DATA.
- Output: `data/forex_rate_cache/curve_*.json`.

**Round 15** — *CRYPTO funding archive expansion.*
- Hypothesis: Funding-rate history can be expanded from 5 symbols to ≥20 (`data/funding_rate_archive/`), meeting the CRYPTO readiness minimum.
- Gate: `class_data_readiness.py` CRYPTO `funding symbols` (≥20) passes → READY.
- Stop condition: If only 5 symbols are reachable, CRYPTO carry stays INSUFFICIENT_N.
- Output: `data/funding_rate_archive/*.json`.

**Round 16** — *INDEX denominator fix.*
- Hypothesis: The INDEX "denominator-leak" flagged in findings can be resolved with a clean alias mapping.
- Gate: INDEX no longer INSUFFICIENT_N due to denominator leak; audit script reports 0 leaks.
- Stop condition: If the leak is structural (INDEX is just an alias), record INDEX as a non-tradable alias and stop.
- Output: `reports/block1_r16_index_denominator_audit.json`.

**Round 17** — *PENNY_STOCK universe seed growth.*
- Hypothesis: A dated penny universe seed with ≥1 verified record and delisting awareness can be built.
- Gate: `class_data_readiness.py` PENNY_STOCK `universe seed` passes → READY.
- Stop condition: If no honest penny universe can be built (no PIT delisting data), keep NO_ROWS.
- Output: `data/penny_universe_seed.json` (dated).

**Round 18** — *MUTUAL_FUND structural verdict.*
- Hypothesis: MUTUAL_FUND is structurally unmeasurable on daily NAV (no intraday first-touch possible).
- Gate: A written determination that MUTUAL_FUND cannot meet intrabar-honest first-touch on 100%.
- Stop condition: N/A — this round only confirms the structural block; no data work continues.
- Output: `docs/edge_research/block1_r18_mutual_fund_structural.md`.

**Round 19** — *Readiness scoreboard freeze.*
- Hypothesis: After R1–R18, a stable readiness snapshot exists showing which classes moved from BLOCKED_DATA to READY.
- Gate: `python3 tools/class_data_readiness.py --json` output committed as the Block-1 baseline; delta table written.
- Stop condition: If fewer than 2 classes flipped to READY, escalate that the program's premise (data unblocks classes) is weak.
- Output: `reports/block1_r19_readiness_baseline.json`.

**Round 20** — *Block 1 exit gate.*
- Hypothesis: At least one class (ideally FOREX or FUTURES) is READY with stated row counts.
- Gate: ≥1 class READY with ≥ the minimum rows required, documented per class.
- Stop condition: If ZERO classes became READY, Block 2 has nothing to test — the program halts and publishes "data acquisition failed" rather than re-testing blocked classes.
- Output: `docs/edge_research/block1_exit.md`.

---

# Block 2 — Rounds 21–40: Per-class mechanism testing on newly unblocked data

One mechanism family per round. Gate = `python3 tools/class_backtest_sweep.py` class
verdict **plus** the H-033-style full statistics block (mean bps, median, 95% CI, 2×-cost
mean, both halves, WR, concentration). Stop = CI straddles zero at n ≥ 2000.

**Round 21** — FOREX carry (G10, rate-differential ranked).
- Hypothesis: G10 carry earns positive net expectancy after 2× cost.
- Gate: mean net bps > 0, 95% CI lower bound > 0, n ≥ 2000.
- Stop: CI straddles zero at n ≥ 2000.
- Output: `reports/block2_r21_forex_carry.json`.

**Round 22** — FOREX time-series momentum.
- Hypothesis: 12-1 FX TSMOM shows net-positive expectancy net of 2× cost.
- Gate: same full-stats block, CI-LB > 0.
- Stop: CI straddles zero at n ≥ 2000.
- Output: `reports/block2_r22_forex_tsmom.json`.

**Round 23** — FOREX carry + trend combo.
- Hypothesis: Combining carry and trend raises net Sharpe over either alone.
- Gate: combo net IR ≥ max(single arms) AND CI-LB > 0.
- Stop: combo underperforms both singles.
- Output: `reports/block2_r23_forex_combo.json`.

**Round 24** — COMMODITY roll yield / basis carry.
- Hypothesis: Positive-roll commodities (backwardation) outperform in net terms.
- Gate: full-stats block with CI-LB > 0 net of 2× cost.
- Stop: CI straddles zero at n ≥ 2000.
- Output: `reports/block2_r24_commodity_roll.json`.

**Round 25** — COMMODITY COT commercial positioning.
- Hypothesis: Commercial net-position extremes predict net-positive forward returns.
- Gate: full-stats block, CI-LB > 0 net of 2× cost.
- Stop: straddle at n ≥ 2000.
- Output: `reports/block2_r25_commodity_cot.json`.

**Round 26** — COMMODITY seasonal.
- Hypothesis: Documented seasonal spreads survive 2× cost.
- Gate: full-stats, CI-LB > 0.
- Stop: straddle.
- Output: `reports/block2_r26_commodity_seasonal.json`.

**Round 27** — FUTURES TSMOM on continuous series.
- Hypothesis: Diversified TSMOM on back-adjusted continuous series is net positive (retest of H-035 with cleaner data).
- Gate: full-stats, CI-LB > 0 net of 2× cost.
- Stop: straddle at n ≥ 2000 (H-035 previously net −9.00bps).
- Output: `reports/block2_r27_futures_tsmom.json`.

**Round 28** — FUTURES cross-sectional carry.
- Hypothesis: Cross-sectional futures carry is net positive.
- Gate: full-stats, CI-LB > 0.
- Stop: straddle.
- Output: `reports/block2_r28_futures_xsec_carry.json`.

**Round 29** — FUTURES basis-momentum.
- Hypothesis: Basis-momentum beats plain TSMOM net of cost.
- Gate: net IR ≥ TSMOM AND CI-LB > 0.
- Stop: fails to beat TSMOM.
- Output: `reports/block2_r29_futures_basis_momentum.json`.

**Round 30** — EQUITY PEAD on vintage consensus.
- Hypothesis: SUE-decile drift is net positive once vintage consensus replaces the look-ahead snapshot.
- Gate: full-stats, CI-LB > 0 net of 2× cost.
- Stop: straddle (PEAD was previously BLOCKED_DATA).
- Output: `reports/block2_r30_equity_pead.json`.

**Round 31** — EQUITY estimate-revision momentum.
- Hypothesis: Δconsensus revision predicts net-positive forward returns.
- Gate: full-stats, CI-LB > 0.
- Stop: straddle.
- Output: `reports/block2_r31_equity_revision.json`.

**Round 32** — EQUITY quality-minus-junk.
- Hypothesis: QMJ factor earns net-positive return net of cost.
- Gate: full-stats, CI-LB > 0.
- Stop: straddle.
- Output: `reports/block2_r32_equity_qmj.json`.

**Round 33** — EQUITY sector momentum (H-033 re-run with clean survivorship).
- Hypothesis: With survivorship-free universe, H-033 moves from WEAK to net-positive.
- Gate: full-stats; CI-LB > 0 (previously CI [−2.58,+5.38]).
- Stop: CI still straddles zero.
- Output: `reports/block2_r33_equity_sector_momentum.json`.

**Round 34** — BOND curve carry/roll.
- Hypothesis: 2s10s carry/roll earns net-positive expectancy.
- Gate: full-stats, CI-LB > 0.
- Stop: straddle.
- Output: `reports/block2_r34_bond_carry.json`.

**Round 35** — BOND slope momentum.
- Hypothesis: Curve-slope momentum is net positive (retest of H-008 with clean curve).
- Gate: full-stats, CI-LB > 0.
- Stop: straddle.
- Output: `reports/block2_r35_bond_slope_momentum.json`.

**Round 36** — CRYPTO funding carry (expanded archive).
- Hypothesis: With ≥20 symbols, delta-neutral funding carry survives 2× cost.
- Gate: full-stats, CI-LB > 0 net of 2× cost.
- Stop: cost survival < 60% of gross (H-012 precedent 5.05%).
- Output: `reports/block2_r36_crypto_funding_carry.json`.

**Round 37** — CRYPTO cross-exchange basis.
- Hypothesis: Spot-perp basis net of fees is positive.
- Gate: full-stats, CI-LB > 0.
- Stop: straddle.
- Output: `reports/block2_r37_crypto_basis.json`.

**Round 38** — ETF dual-momentum (retest).
- Hypothesis: ETF dual-momentum with clean prices is net positive.
- Gate: full-stats, CI-LB > 0 (ET-1 previously net −9.24bps).
- Stop: straddle.
- Output: `reports/block2_r38_etf_dual_momentum.json`.

**Round 39** — Multi-class survivor shortlist.
- Hypothesis: At least one mechanism family per READY class clears a CI-LB > 0 gate.
- Gate: A shortlist file naming every surviving mechanism with its full-stats block.
- Stop: If no mechanism survives, Block 3 has nothing to cost-test — publish KILL for all and halt.
- Output: `reports/block2_r39_survivor_shortlist.json`.

**Round 40** — Block 2 exit gate.
- Hypothesis: ≥1 mechanism has CI-LB > 0 net of 2× cost and advances to cost analysis.
- Gate: count of CI-LB>0 mechanisms ≥ 1, each with complete stats.
- Stop: zero survivors → all classes to Block 10 KILL.
- Output: `docs/edge_research/block2_exit.md`.

---

# Block 3 — Rounds 41–60: Cost, capacity, and slippage realism

Gate = gross edge must exceed measured round-trip cost by a stated multiple before any
further work. Stop = cost survival < 60% of gross after 3 attempts at cost modelling.

**Round 41** — Measure realized bid-ask spread per instrument (crypto from order book depth; equities from quote).
- Hypothesis: Measured spread differs from the 10bp assumption by more than 2×.
- Gate: a spread table per instrument with source and timestamp.
- Stop: if spread cannot be measured for >50% of the shortlist, use the conservative default and disclose.
- Output: `reports/block3_r41_spreads.json`.

**Round 42** — Commission/fee schedule per venue.
- Hypothesis: All-in round-trip fee is ≤ the modelled 20bp for the primary venue of each mechanism.
- Gate: fee table; the mechanism's gross must exceed total round-trip by ≥ 3×.
- Stop: if a mechanism's gross < 1.5× round-trip, flag it unfit.
- Output: `reports/block3_r42_fees.json`.

**Round 43** — Market-impact model for size.
- Hypothesis: Impact scales as a square-root function of size/ADV; at the paper account size impact is < 20% of spread.
- Gate: impact estimate at stated notional; document the size where impact = 50% of spread.
- Stop: if impact exceeds half the edge at $10k notional, the mechanism is capacity-constrained.
- Output: `reports/block3_r43_impact.json`.

**Round 44** — Slippage realism for taker fills.
- Hypothesis: Actual fills land within 1 spread half of the mid at paper sizes.
- Gate: measured slippage distribution across ≥ 30 simulated fills per mechanism.
- Stop: if median slippage > full spread, mark mechanism cost-unfit.
- Output: `reports/block3_r44_slippage.json`.

**Round 45** — Funding/financing carry cost for levered/FX positions.
- Hypothesis: Financing cost is ≤ 25% of the mechanism's gross edge.
- Gate: financing cost stated per mechanism as bps/year and bps per hold.
- Stop: if financing eliminates the edge, KILL.
- Output: `reports/block3_r45_financing.json`.

**Round 46** — Round-trip cost sensitivity 1×/2×/3×.
- Hypothesis: A mechanism survives at least the 2× cost multiple.
- Gate: net expectancy CI-LB > 0 at 2× cost.
- Stop: net CI-LB ≤ 0 at 2× cost.
- Output: `reports/block3_r46_cost_multiples.json`.

**Round 47** — Turnover vs. edge ratio.
- Hypothesis: Each mechanism's gross-edge-to-turnover ratio exceeds the cost-per-turnover.
- Gate: edge/turnover > cost/turnover for each mechanism.
- Stop: fails the ratio → KILL.
- Output: `reports/block3_r47_turnover_edge.json`.

**Round 48** — First cost-model attempt (spread-only).
- Hypothesis: Spread-only costing already leaves a positive net.
- Gate: net > 0 under spread-only cost.
- Stop: if even spread-only is negative, the mechanism cannot pay execution → KILL (attempt 1 of 3).
- Output: `reports/block3_r48_costmodel_v1.json`.

**Round 49** — Second cost-model attempt (spread + fee + slippage).
- Hypothesis: Full realistic cost still leaves a positive net.
- Gate: net > 0 under combined cost (attempt 2 of 3).
- Stop: negative → third attempt or KILL.
- Output: `reports/block3_r49_costmodel_v2.json`.

**Round 50** — Third cost-model attempt (add impact).
- Hypothesis: Even with impact, the mechanism's net CI-LB > 0.
- Gate: net CI-LB > 0 under all-in cost (attempt 3 of 3).
- Stop: **if cost survival < 60% of gross after this third attempt, KILL.**
- Output: `reports/block3_r50_costmodel_v3.json`.

**Round 51** — Capacity at $10k / $100k / $1M notional.
- Hypothesis: The mechanism remains net positive up to a stated capacity ceiling.
- Gate: capacity ceiling (notional where net edge → 0) documented.
- Stop: if the ceiling is below the paper account, note the strategy is unscalable but still paper-valid.
- Output: `reports/block3_r51_capacity.json`.

**Round 52** — Cost stress under stressed spreads (2× normal).
- Hypothesis: Net remains positive if spreads double.
- Gate: net > 0 at 2× measured spread.
- Stop: negative under stressed spread → flag as fragile.
- Output: `reports/block3_r52_stressed_spreads.json`.

**Round 53** — Latency assumption sensitivity.
- Hypothesis: A 1-bar execution delay does not flip the sign of net expectancy.
- Gate: sign of net unchanged under +1 bar delay.
- Stop: sign flips → mechanism is latency-fragile → KILL.
- Output: `reports/block3_r53_latency.json`.

**Round 54** — Borrow/financing for shorts.
- Hypothesis: Short-side financing does not erase the short leg's contribution.
- Gate: short-leg net > 0 after borrow cost.
- Stop: short leg net negative → disable shorts and retest long-only.
- Output: `reports/block3_r54_borrow.json`.

**Round 55** — Per-class cost survival summary.
- Hypothesis: Cost survival ≥ 60% of gross for surviving mechanisms.
- Gate: cost-survival table per mechanism.
- Stop: mechanisms below 60% → KILL.
- Output: `reports/block3_r55_cost_survival.json`.

**Round 56** — Fill-size distribution realism.
- Hypothesis: Splitting orders across a hold window does not materially worsen cost.
- Gate: cost under split fills within 10% of single fill.
- Stop: split fills materially worse → capacity-limited.
- Output: `reports/block3_r56_fill_sizes.json`.

**Round 57** — Weekend/gap cost (crypto 24/7 vs equity gaps).
- Hypothesis: Equity overnight gaps add unmodeled cost that crypto does not.
- Gate: gap-cost component quantified per class.
- Stop: gap cost alone exceeds edge for equity → KILL equity overnight strategies.
- Output: `reports/block3_r57_gap_cost.json`.

**Round 58** — Tax/friction note (non-binding, disclosed).
- Hypothesis: Nothing in the mechanism relies on a tax artifact.
- Gate: written determination per mechanism.
- Stop: if it relies on a tax artifact, it is not a real edge.
- Output: `docs/edge_research/block3_r58_tax_note.md`.

**Round 59** — Cost-adjusted shortlist.
- Hypothesis: ≥1 mechanism survives all-in 2× cost with CI-LB > 0 and survival ≥ 60%.
- Gate: cost-adjusted shortlist file.
- Stop: zero survivors → all to Block 10 KILL.
- Output: `reports/block3_r59_cost_adjusted_shortlist.json`.

**Round 60** — Block 3 exit gate.
- Hypothesis: At least one mechanism is cost-fit for robustness testing.
- Gate: ≥1 mechanism passes R46 + R50 + R55.
- Stop: none → KILL all and halt.
- Output: `docs/edge_research/block3_exit.md`.

---

# Block 4 — Rounds 61–80: Robustness / multiplicity control

Gate = DSR ≥ 0.95 **AND** survives a pre-declared parameter perturbation.

**Round 61** — Declare the trial count before testing (pre-registration).
- Hypothesis: The true search breadth (symbols × params × arms) can be stated as an integer N before any robustness result is seen.
- Gate: N logged and frozen in a registry before tests run.
- Stop: if N cannot be stated, DSR cannot be computed → mechanism cannot be promoted.
- Output: `reports/block4_r61_trial_count.json`.

**Round 62** — Sub-period split (first/second half).
- Hypothesis: Both halves show positive net expectancy.
- Gate: both-halves net > 0.
- Stop: one half negative → mechanism regime-dependent → flag.
- Output: `reports/block4_r62_halves.json`.

**Round 63** — Rolling-window stability.
- Hypothesis: ≥70% of rolling windows are net positive.
- Gate: share of positive windows ≥ 70%.
- Stop: < 50% positive → KILL.
- Output: `reports/block4_r63_rolling.json`.

**Round 64** — Instrument jackknife.
- Hypothesis: Dropping any single symbol does not flip sign.
- Gate: leave-one-out sign stable across all symbols.
- Stop: one symbol drives the result (>60% contribution) → concentration KILL.
- Output: `reports/block4_r64_jackknife.json`.

**Round 65** — Parameter sensitivity (pre-declared grid).
- Hypothesis: A ±20% perturbation of the key parameter keeps net CI-LB > 0.
- Gate: net CI-LB > 0 across the pre-declared grid.
- Stop: performance only at a knife-edge parameter → overfit → KILL.
- Output: `reports/block4_r65_param_grid.json`.

**Round 66** — Data-snoop / look-elsewhere adjustment.
- Hypothesis: After adjusting for the number of variants tried, at least one remains significant.
- Gate: adjusted p (Bonferroni/White) < 0.05 for the winner.
- Stop: none survives adjustment → KILL.
- Output: `reports/block4_r66_snoop_adj.json`.

**Round 67** — Deflated Sharpe Ratio with true N.
- Hypothesis: DSR ≥ 0.95 at the frozen trial count N.
- Gate: DSR ≥ 0.95.
- Stop: DSR < 0.95 → the edge is indistinguishable from best-of-N noise → KILL.
- Output: `reports/block4_r67_dsr.json`.

**Round 68** — Regime breakdown (bull/bear/highvol).
- Hypothesis: Net expectancy is non-negative in ≥2 of 3 regimes.
- Gate: ≥2 regimes net ≥ 0.
- Stop: positive only in one regime → strategy is a regime bet, not an edge.
- Output: `reports/block4_r68_regimes.json`.

**Round 69** — Survivorship re-check under PIT universe.
- Hypothesis: Result is unchanged when delisted names are included.
- Gate: net change from survivorship ≤ 20%.
- Stop: result collapses on delisted inclusion → survivorship artifact → KILL.
- Output: `reports/block4_r69_survivorship.json`.

**Round 70** — Cost-multiple robustness (2×/3× at the winner).
- Hypothesis: Net CI-LB > 0 persists at 3× cost.
- Gate: net CI-LB > 0 at 3× cost.
- Stop: fails at 3× → margin too thin → flag.
- Output: `reports/block4_r70_cost3x.json`.

**Round 71** — Alternative-exit robustness.
- Hypothesis: The edge is not an artifact of the specific TP/SL ratio.
- Gate: net CI-LB > 0 across ≥3 pre-declared exit schemes.
- Stop: positive only for one exit → exit-overfit → KILL.
- Output: `reports/block4_r71_exits.json`.

**Round 72** — Universe-size sensitivity.
- Hypothesis: Result holds at half and double the universe.
- Gate: net CI-LB > 0 at reduced and expanded universe.
- Stop: only works at the chosen universe size → fragility.
- Output: `reports/block4_r72_universe_size.json`.

**Round 73** — Correlation-to-benchmark leakage.
- Hypothesis: The edge is not merely beta to a benchmark.
- Gate: selection alpha CI-LB > 0 (benchmark-adjusted).
- Stop: beta-neutralizing the mechanism kills it → it is beta → KILL.
- Output: `reports/block4_r73_selection_alpha.json`.

**Round 74** — Bootstrap stability.
- Hypothesis: A stationary bootstrap CI-LB > 0.
- Gate: bootstrap CI-LB > 0 at 10k resamples.
- Stop: bootstrap CI straddles zero.
- Output: `reports/block4_r74_bootstrap.json`.

**Round 75** — Multiple-testing across classes.
- Hypothesis: The winning class still clears a family-wise threshold across all 12 classes.
- Gate: family-wise-corrected significance passes.
- Stop: fails family-wise correction → the "winner" is best-of-12 noise.
- Output: `reports/block4_r75_familywise.json`.

**Round 76** — Persistence prereq (first of two consecutive runs).
- Hypothesis: The result reproduces on a fresh run with identical inputs (run 1 of 2).
- Gate: identical sign and magnitude within 10% (run 1).
- Stop: run-to-run drift > 30% → nondeterministic → investigate.
- Output: `reports/block4_r76_run1.json`.

**Round 77** — Persistence (second consecutive run).
- Hypothesis: The result reproduces again (run 2 of 2), satisfying the PROVEN_T2 persistence item.
- Gate: run 2 matches run 1; persistence = PASS.
- Stop: fails persistence → cannot promote.
- Output: `reports/block4_r77_run2.json`.

**Round 78** — Concentration check (source/symbol).
- Hypothesis: No symbol > 60% and no source > 90% of P&L.
- Gate: concentration limits satisfied.
- Stop: breached → KILL or respecify.
- Output: `reports/block4_r78_concentration.json`.

**Round 79** — Robustness scorecard.
- Hypothesis: ≥1 mechanism passes every Block-4 gate.
- Gate: scorecard with all items green for at least one mechanism.
- Stop: none green → Block 5 empty.
- Output: `reports/block4_r79_robustness_scorecard.json`.

**Round 80** — Block 4 exit gate.
- Hypothesis: A robust, multiplicity-controlled survivor exists.
- Gate: DSR ≥ 0.95 AND perturbation survived AND concentration OK.
- Stop: none → publish KILL, halt Block 5.
- Output: `docs/edge_research/block4_exit.md`.

---

# Block 5 — Rounds 81–100: Portfolio construction

Gate = portfolio-level CI-LB > 0 net of 2× costs **AND** no single strategy > 40% of
portfolio variance.

**Round 81** — Correlation matrix of survivors.
- Hypothesis: Survivors are not >0.9 correlated (some diversification exists).
- Gate: correlation matrix; max pairwise < 0.9.
- Stop: all pairwise ≥ 0.9 → survivors are one bet → treat as one.
- Output: `reports/block5_r81_corr_matrix.json`.

**Round 82** — Equal-weight book.
- Hypothesis: An equal-weight combination is net CI-LB > 0.
- Gate: portfolio net CI-LB > 0 at 2× cost.
- Stop: combined book negative even when members positive → cost overlap → respecify.
- Output: `reports/block5_r82_equal_weight.json`.

**Round 83** — Risk-parity book.
- Hypothesis: Inverse-vol weighting improves portfolio CI-LB over equal weight.
- Gate: risk-parity CI-LB ≥ equal-weight CI-LB.
- Stop: worse → keep equal weight.
- Output: `reports/block5_r83_risk_parity.json`.

**Round 84** — Variance decomposition.
- Hypothesis: No single strategy contributes >40% of portfolio variance.
- Gate: max variance share ≤ 40%.
- Stop: one strategy > 40% → cap or drop it.
- Output: `reports/block5_r84_variance_decomp.json`.

**Round 85** — Sleeve caps.
- Hypothesis: Capping each sleeve at 40% leaves portfolio CI-LB > 0.
- Gate: capped book net CI-LB > 0.
- Stop: caps make the book unprofitable → too few uncorrelated sleeves.
- Output: `reports/block5_r85_caps.json`.

**Round 86** — Rebalance frequency study.
- Hypothesis: Monthly rebalance is net-positive after turnover cost.
- Gate: net > 0 at monthly; compare to quarterly.
- Stop: rebalance cost kills it → use longer horizon or KILL.
- Output: `reports/block5_r86_rebalance.json`.

**Round 87** — Drawdown profile.
- Hypothesis: Max drawdown is survivable (< 25%) at the paper account size.
- Gate: max DD < 25%.
- Stop: DD > 40% → position sizing must shrink or KILL.
- Output: `reports/block5_r87_drawdown.json`.

**Round 88** — Tail-risk (CVaR) check.
- Hypothesis: CVaR95 is within the stated risk budget.
- Gate: CVaR95 documented and within budget.
- Stop: tail loss exceeds budget → hedge or KILL.
- Output: `reports/block5_r88_cvar.json`.

**Round 89** — Benchmark comparison (portfolio vs 60/40 and vs SPY).
- Hypothesis: Portfolio net Sharpe > benchmark Sharpe.
- Gate: net Sharpe > benchmark.
- Stop: cannot beat buy-and-hold net of cost → no reason to run it.
- Output: `reports/block5_r89_benchmark.json`.

**Round 90** — Contribution attribution.
- Hypothesis: Portfolio return is explained by the survivors, not residual beta.
- Gate: selection alpha at portfolio level CI-LB > 0.
- Stop: portfolio return is beta → KILL.
- Output: `reports/block5_r90_attribution.json`.

**Round 91** — Leverage/vol targeting.
- Hypothesis: Vol-targeting to 10% annualized improves risk-adjusted return.
- Gate: vol-targeted net IR ≥ untargeted.
- Stop: worse → keep unlevered.
- Output: `reports/block5_r91_vol_target.json`.

**Round 92** — Liquidity-weighted caps.
- Hypothesis: Weighting by ADV-scaled capacity keeps impact < 20% of spread.
- Gate: impact check passes at capped weights.
- Stop: impact too high → downsize.
- Output: `reports/block5_r92_liquidity_caps.json`.

**Round 93** — Concentration stress (drop the top contributor).
- Hypothesis: Removing the best strategy keeps portfolio CI-LB > 0.
- Gate: ex-best net CI-LB > 0.
- Stop: portfolio depends on one strategy → not a book → respecify.
- Output: `reports/block5_r93_drop_best.json`.

**Round 94** — Cost overlay at portfolio level.
- Hypothesis: Portfolio net CI-LB > 0 after 2× cost across all sleeves.
- Gate: portfolio net CI-LB > 0 at 2× cost.
- Stop: negative → KILL the book.
- Output: `reports/block5_r94_portfolio_cost.json`.

**Round 95** — Cash/idle allocation.
- Hypothesis: Holding cash when no signal is better than forcing trades.
- Gate: cash-aware book ≥ always-invested book.
- Stop: forcing trades is better → signal-timing is weak.
- Output: `reports/block5_r95_cash.json`.

**Round 96** — Signal-overlap handling.
- Hypothesis: Overlapping signals across sleeves are de-duplicated so the book doesn't double-count one bet.
- Gate: overlap-adjusted exposure within limits.
- Stop: overlap > 50% → sleeves are the same bet.
- Output: `reports/block5_r96_overlap.json`.

**Round 97** — Book stability over time.
- Hypothesis: Weights do not swing pathologically month to month.
- Gate: max month-over-month weight change documented and bounded.
- Stop: unstable weights → add smoothing.
- Output: `reports/block5_r97_stability.json`.

**Round 98** — Full portfolio full-stats block.
- Hypothesis: The book has mean net bps > 0, CI-LB > 0, both halves positive.
- Gate: complete H-033-style stats block for the portfolio.
- Stop: any required sub-stat fails → respecify.
- Output: `reports/block5_r98_portfolio_stats.json`.

**Round 99** — Paper-account sizing plan.
- Hypothesis: A $10,000 paper account can hold the book without breaching per-name caps.
- Gate: a sizing sheet mapping weights → notional at $10k.
- Stop: cannot size at $10k without fractional lots → note minimum viable account.
- Output: `reports/block5_r99_sizing.json`.

**Round 100** — Block 5 exit gate.
- Hypothesis: The portfolio passes net CI-LB > 0 and variance-share ≤ 40%.
- Gate: both conditions satisfied.
- Stop: either fails → the book does not advance to paper trading.
- Output: `docs/edge_research/block5_exit.md`.

---

# Block 6 — Rounds 101–120: Paper trading on live data

Real quotes, recorded fills, both TP and SL pre-declared. Gate = n ≥ 30 resolved paper
trades with intrabar-honest first touch. The existing engine
[`tools/realtime_challenge.py`](../tools/realtime_challenge.py:5) is the intended driver
(`--open`/`--resolve`).

**Round 101** — Wire the live driver to the book.
- Hypothesis: `tools/realtime_challenge.py --open` can place paper opens for at least the crypto sleeve from live 5m bars.
- Gate: ≥1 paper open recorded with timestamped entry quote in `reports/realtime_challenge/state.json`.
- Stop: if live quotes cannot be fetched (network/geo-block) for a full session, mark paper UNMEASURABLE and stop.
- Output: `reports/realtime_challenge/state.json` (open populated).

**Round 102** — Pre-declare TP/SL per sleeve before entry.
- Hypothesis: Every open carries a TP and SL set before the fill, not after.
- Gate: 100% of opens have TP and SL in the record at open time.
- Stop: any open lacking pre-declared TP/SL → that trade is voided.
- Output: append `docs/edge_research/block6_r102_prereg.md`.

**Round 103** — Two-venue agreement enforcement.
- Hypothesis: All recorded entry prices pass the ≥2-venue 50bp agreement check.
- Gate: 100% of entries pass the agreement check.
- Stop: >20% fail → feed unreliable, pause paper.
- Output: `reports/block6_r103_venue_agreement.json`.

**Round 104** — Intrabar-pessimistic resolution.
- Hypothesis: Resolution assumes stop-first when a bar spans both TP and SL.
- Gate: 100% of resolutions use the pessimistic rule.
- Stop: any optimistic resolution → rescore all trades.
- Output: `reports/block6_r104_resolution_rule.json`.

**Round 105** — Fill realism (fees both legs).
- Hypothesis: Every paper trade charges fees on entry and exit (10bp/side).
- Gate: net P&L equals gross minus 2× fee on 100% of trades.
- Stop: any trade missing a leg fee → recompute.
- Output: `reports/block6_r105_fees_applied.json`.

**Round 106** — Hold-limit enforcement.
- Hypothesis: Trades exit at max-hold if neither TP nor SL is hit.
- Gate: 100% of trades close by TP/SL/hold.
- Stop: any open beyond max-hold → force-close and log.
- Output: `reports/block6_r106_hold_limit.json`.

**Round 107** — Accumulate to n ≥ 10 resolved.
- Hypothesis: 10 resolved trades can be gathered with honest first-touch.
- Gate: n_resolved ≥ 10.
- Stop: if n < 10 after a full week of sessions, extend or record insufficient cadence.
- Output: `reports/block6_r107_n10.json`.

**Round 108** — Accumulate to n ≥ 20.
- Gate: n_resolved ≥ 20. Stop: n stalls → cadence problem, report.
- Output: `reports/block6_r108_n20.json`.

**Round 109** — Accumulate to n ≥ 30.
- Gate: n_resolved ≥ 30 with intrabar-honest first touch on 100%.
- Stop: < 30 after reasonable time → paper result is INSUFFICIENT_N, not a pass.
- Output: `reports/block6_r109_n30.json`.

**Round 110** — Live net expectancy full-stats.
- Hypothesis: Live paper net expectancy CI-LB > 0.
- Gate: full-stats block on paper trades; CI-LB > 0.
- Stop: CI straddles zero at n ≥ 30 → no live confirmation.
- Output: `reports/block6_r110_live_stats.json`.

**Round 111** — Live vs backtest reconciliation.
- Hypothesis: Live paper mean is within 1 std err of backtest mean.
- Gate: |live − backtest| ≤ 1 SE.
- Stop: divergence > 2 SE → backtest overfit → investigate.
- Output: `reports/block6_r111_live_vs_bt.json`.

**Round 112** — Slippage measured on paper.
- Hypothesis: Paper slippage matches R44 assumptions.
- Gate: measured slippage ≤ assumed + 5bp.
- Stop: worse → re-cost.
- Output: `reports/block6_r112_paper_slippage.json`.

**Round 113** — Win-rate vs expectancy check.
- Hypothesis: Net expectancy is positive independent of a coin-flip win rate.
- Gate: net expectancy > 0 while WR may be ≤ 50%.
- Stop: positive only if WR > 50% but live WR < 50% → signal decaying.
- Output: `reports/block6_r113_wr_expectancy.json`.

**Round 114** — Per-symbol live concentration.
- Hypothesis: No symbol > 60% of live P&L.
- Gate: concentration limits pass on live.
- Stop: breached → reduce that symbol.
- Output: `reports/block6_r114_live_concentration.json`.

**Round 115** — Live halves.
- Hypothesis: Both halves of the paper period are net positive.
- Gate: both halves > 0.
- Stop: one half negative → live regime dependence.
- Output: `reports/block6_r115_live_halves.json`.

**Round 116** — Drawdown on paper.
- Hypothesis: Paper max DD < 25%.
- Gate: max DD < 25%.
- Stop: DD > 40% → sizing/halt.
- Output: `reports/block6_r116_paper_dd.json`.

**Round 117** — Reconciliation to real quotes (audit).
- Hypothesis: Every resolved paper trade price can be re-fetched from a real venue.
- Gate: 100% of trades reconcile to a stored real quote.
- Stop: any unverifiable trade → void it.
- Output: `reports/block6_r117_reconcile.json`.

**Round 118** — Ledger integrity (append-only).
- Hypothesis: The ledger is append-only and no closed row was mutated.
- Gate: hash-chain check passes.
- Stop: mutation detected → reset and re-run cleanly.
- Output: `reports/block6_r118_ledger_integrity.json`.

**Round 119** — Paper exit scorecard.
- Hypothesis: ≥1 sleeve reached n ≥ 30 with honest first-touch and CI-LB > 0.
- Gate: scorecard green for at least one sleeve.
- Stop: none green → Block 7/8 paper is INSUFFICIENT and cannot promote.
- Output: `reports/block6_r119_paper_scorecard.json`.

**Round 120** — Block 6 exit gate.
- Hypothesis: n ≥ 30, 100% honest first-touch, CI-LB > 0 for at least one sleeve.
- Gate: all three satisfied.
- Stop: fails → halt promotion path; publish INSUFFICIENT_N.
- Output: `docs/edge_research/block6_exit.md`.

---

# Block 7 — Rounds 121–140: GHA monitoring infrastructure

Scheduled TP/SL checking, ledger commit discipline, failure alerting. Gate = workflow
runs green for 7 consecutive days and every resolved trade reconciles to a real quote.

Existing: `tv-paper-tpsl-watchdog` (every 15m), `outcome-resolver` (:47), `crypto-intraday-sim` (:07/:37), `forward-tracking-v2` (:28).

**Round 121** — Add a challenge monitor workflow.
- Hypothesis: A scheduled worklow can run `tools/realtime_challenge.py --resolve` hourly.
- Gate: workflow file exists and runs green once.
- Stop: if secrets/network blocked in CI, document and run locally instead.
- Output: `.github/workflows/realtime-challenge-monitor.yml` (new, to be created in Code mode).

**Round 122** — Cron stagger to avoid contention.
- Hypothesis: Placing the monitor off the busy minute avoids queue cancellation.
- Gate: 3 consecutive runs complete without cancellation.
- Stop: cancellations persist → move minute.
- Output: workflow cron note.

**Round 123** — Ledger commit discipline (`[skip ci]`, own path).
- Hypothesis: Ledger commits touch only `reports/realtime_challenge/*` with `[skip ci]`.
- Gate: 3 commits verified path-scoped and `[skip ci]`.
- Stop: any commit touches unrelated files → fix allowlist.
- Output: commit audit note.

**Round 124** — TP/SL check each cron tick.
- Hypothesis: Each tick re-checks open positions against live quotes.
- Gate: 100% of open positions checked each tick.
- Stop: misses → bug in resolver.
- Output: `reports/block7_r124_tick_audit.json`.

**Round 125** — Failure alerting.
- Hypothesis: A failed run raises a visible alert (log/marker/issue).
- Gate: simulated failure produces an alert.
- Stop: silent failure → add loud-fail.
- Output: alerting config note.

**Round 126** — Stale-quote guard.
- Hypothesis: The monitor rejects quotes older than a threshold.
- Gate: stale-quote test rejects a 1-hour-old price.
- Stop: accepts stale → fix.
- Output: `reports/block7_r126_stale_guard.json`.

**Round 127** — Idempotent re-resolution.
- Hypothesis: Re-running resolution does not double-close a trade.
- Gate: idempotency test passes.
- Stop: double-close → fix.
- Output: `reports/block7_r127_idempotency.json`.

**Round 128** — Reconciliation each day.
- Hypothesis: Daily reconciliation matches ledger to real quotes for 100% of resolved trades.
- Gate: 100% reconcile on 1 day.
- Stop: any mismatch → investigate.
- Output: `reports/block7_r128_daily_reconcile.json`.

**Round 129** — 7-consecutive-day green run (day 1).
- Gate: green. Stop: red → fix before counting.
- Output: run link.

**Round 130** — Green day 2.
- Gate: green. Stop: red → reset counter.
- Output: run link.

**Round 131** — Green day 3. Gate green; Stop red resets. Output run link.

**Round 132** — Green day 4. Gate green; Stop red resets. Output run link.

**Round 133** — Green day 5. Gate green; Stop red resets. Output run link.

**Round 134** — Green day 6. Gate green; Stop red resets. Output run link.

**Round 135** — Green day 7 (gate satisfied).
- Gate: 7 consecutive green days AND every resolved trade reconciled.
- Stop: any red → counter resets.
- Output: `reports/block7_r135_seven_day_green.json`.

**Round 136** — Missed-tick detection.
- Hypothesis: The monitor detects its own missed schedules.
- Gate: a simulated gap is detected.
- Stop: silent gap → add gap detector.
- Output: `reports/block7_r136_gap_detect.json`.

**Round 137** — Multi-sleeve monitoring.
- Hypothesis: The monitor resolves all sleeves, not just crypto.
- Gate: equity/futures/forex positions resolve when quotes available; else UNMEASURED.
- Stop: silent skip → log explicit UNMEASURED.
- Output: `reports/block7_r137_multi_sleeve.json`.

**Round 138** — Cost accounting in monitor.
- Hypothesis: Monitor applies fees on every close.
- Gate: 100% of closes include fee deduction.
- Stop: missing fee → recompute.
- Output: `reports/block7_r138_costs.json`.

**Round 139** — Observability dashboard row.
- Hypothesis: A status row shows n, net CI, last-tick time.
- Gate: row renders with live values.
- Stop: stale row → fix.
- Output: dashboard snippet note.

**Round 140** — Block 7 exit gate.
- Hypothesis: Monitoring is reliable and honest.
- Gate: 7-day green + 100% reconciliation.
- Stop: fails → paper/trading rounds below cannot trust their own data.
- Output: `docs/edge_research/block7_exit.md`.

---

# Block 8 — Rounds 141–160: Live "pretend" challenge rounds

Repeated real-time open/close attempts on live markets, short holding windows,
technicals-driven. Each round records entry rationale, real quotes at entry and exit, and
the honest reason for profit or loss. **These are the rounds the `REALTIMECHALLENGE_*.MD`
files document.** Zero completed trades in a round scores ZERO, not neutral.

**Round 141** — First live pretend round (crypto only if equities closed).
- Hypothesis: A technical setup can be opened and closed within a short window on a live venue with real quotes.
- Gate: ≥1 completed open→close with entry & exit real quotes.
- Stop: market closed/no reachable quote → record ZERO and state why.
- Output: append `REALTIMECHALLENGE_deepseek-flash_20261122T0355_EST.MD` Round 141.

**Round 142** — Second round, different instrument.
- Hypothesis: Repeatability across instruments.
- Gate: ≥1 completed trade with honest note.
- Stop: zero trades → ZERO.
- Output: same MD.

**(Rounds 143–160 follow the identical four-field structure: one live open/close attempt
each, entry rationale + real entry/exit quotes + honest reason; gate = ≥1 completed
trade; stop = zero trades scores ZERO; output = a new row in the challenge MD.)** The
sequence alternates instruments within the verified-reachable set (crypto majors via
Binance; equities via yfinance only during market hours) and alternates technical setups
(breakout, pullback, mean-reversion, momentum) so no single setup is over-sampled without
being disclosed in the trial count.

**Round 160** — Block 8 exit gate.
- Hypothesis: Across rounds 141–160 there is an honest record of live pretend performance.
- Gate: a completed scoring table with net bps per round, zero-trade rounds scored ZERO.
- Stop: if no completed trades were possible (venues unreachable), record UNMEASURABLE and do not claim proof.
- Output: `docs/edge_research/block8_exit.md` + challenge MD scoring table.

---

# Block 9 — Rounds 161–180: Peer cross-check

Read peers' `REALTIMECHALLENGE_*.MD` files, re-run their claimed tests where data allows,
record agreement/disagreement per claim. Gate = every peer claim classified as
REPLICATED / NOT_REPLICATED / UNMEASURABLE.

**Round 161** — Discover peer challenge files.
- Hypothesis: Peer `REALTIMECHALLENGE_*.MD` files exist to cross-check.
- Gate: an inventory listing each peer file, model token, timestamp, 3-line rule summary.
- Stop: **if none exist (current recon found ZERO), record "no peer files found" and mark the entire block N/A.**
- Output: `reports/block9_r161_peer_inventory.json`.

**Round 162** — Extract peer claims.
- Gate: each claim listed. Stop: no claims → N/A. Output: `reports/block9_r162_claims.json`.

**Round 163** — Re-run peer claim 1 where data allows.
- Gate: claim classified REPLICATED / NOT_REPLICATED / UNMEASURABLE.
- Stop: data missing → UNMEASURABLE (legitimate).
- Output: `reports/block9_r163_claim1.json`.

**(Rounds 164–179)** — one peer claim per round, same four-field structure and gate;
output one classification file per claim.

**Round 180** — Block 9 exit gate.
- Hypothesis: Every peer claim is classified.
- Gate: 100% of discovered claims carry a classification (or the block is N/A because no peers exist).
- Stop: none unclassified.
- Output: `docs/edge_research/block9_exit.md`.

---

# Block 10 — Rounds 181–200: Synthesis and promotion decisions

One class at a time, run the full PROVEN_T2 checklist and publish CANDIDATE or KILL.
Gate = PROVEN_T2 items each individually satisfied; **no partial credit.**

PROVEN_T2 checklist (from background): n ≥ 100 forward rows; intrabar-honest first-touch
on 100%; net PF CI-LB > 1.0 OR IR ≥ 0.5; selection alpha CI-LB > 0; 2×-cost CI-LB > 0;
both halves positive; no symbol > 60%; no source > 90%; benchmark coverage ≥ 90%; DSR ≥
0.95 with true trial count; persists 2 consecutive runs; survivorship-free and
point-in-time.

**Round 181** — FOREX full checklist.
- Hypothesis: FOREX meets every PROVEN_T2 item or fails at least one.
- Gate: item-by-item PASS/FAIL list; CANDIDATE only if all PASS.
- Stop: any FAIL → publish KILL (no partial).
- Output: `reports/block10_r181_forex_verdict.json`.

**Round 182** — COMMODITY full checklist. Same structure. Output `reports/block10_r182_commodity_verdict.json`.

**Round 183** — FUTURES full checklist. Output `reports/block10_r183_futures_verdict.json`.

**Round 184** — EQUITY (PEAD) full checklist. Output `reports/block10_r184_equity_pead_verdict.json`.

**Round 185** — EQUITY (sector momentum) full checklist. Output `reports/block10_r185_equity_mom_verdict.json`.

**Round 186** — BOND full checklist. Output `reports/block10_r186_bond_verdict.json`.

**Round 187** — CRYPTO full checklist. Output `reports/block10_r187_crypto_verdict.json`.

**Round 188** — ETF full checklist. Output `reports/block10_r188_etf_verdict.json`.

**Round 189** — INDEX full checklist. Output `reports/block10_r189_index_verdict.json`.

**Round 190** — MEME full checklist. Output `reports/block10_r190_meme_verdict.json`.

**Round 191** — PENNY_STOCK full checklist (likely NO_ROWS). Output `reports/block10_r191_penny_verdict.json`.

**Round 192** — MUTUAL_FUND full checklist (structurally unmeasurable). Output `reports/block10_r192_mutualfund_verdict.json`.

**Round 193** — Any new class discovered in Blocks 1–9. Output `reports/block10_r193_other_verdict.json`.

**Round 194** — Consolidate verdicts via `tools/publish_class_verdict.py`.
- Hypothesis: Machine-published verdicts match this program's determinations.
- Gate: published JSON equals the round-by-round verdicts.
- Stop: mismatch → fix inputs, not the publisher.
- Output: `reports/per_class_edge_verdicts_20261122.json` (updated).

**Round 195** — Write the final findings doc.
- Gate: `docs/edge_research/00_FINDINGS_2026-11-22.md` updated with any CANDIDATE (or reaffirmed zero).
- Stop: if still zero CANDIDATE, state it plainly.
- Output: `docs/edge_research/00_FINDINGS_2026-11-22.md`.

**Round 196** — Honesty audit of every published number.
- Hypothesis: Every number has a source or is marked UNMEASURED.
- Gate: `tools/doc_source_lint.py` passes on the findings doc.
- Stop: unsourced number → mark UNMEASURED or cite.
- Output: lint report.

**Round 197** — Kill-list reconciliation.
- Gate: KILL classes match `tools/kill_list_reconcile.py` expectations.
- Stop: drift → reconcile.
- Output: `reports/block10_r197_kill_reconcile.json`.

**Round 198** — If any CANDIDATE exists: paper→live gating memo.
- Hypothesis: A CANDIDATE can be sized at $10k without breaching caps.
- Gate: sizing memo complete.
- Stop: none exist → mark N/A.
- Output: `docs/edge_research/block10_r198_candidate_memo.md`.

**Round 199** — Program retrospective.
- Hypothesis: The program's outcome is honestly summarizable in one page.
- Gate: retrospective written with pass/fail counts per block.
- Stop: n/a.
- Output: `docs/edge_research/block10_r199_retrospective.md`.

**Round 200** — Final publication.
- Hypothesis: The program ends with an honest verdict set and a clear next step.
- Gate: verdicts published, findings updated, honesty audit green.
- Stop: none — this round closes the program.
- Output: final `docs/edge_research/00_FINDINGS_2026-11-22.md` + `reports/per_class_edge_verdicts_20261122.json`.

---

## Round 1 and 2 are live now

The next agent should execute exactly these two rounds first, and nothing else:

**Round 1 — FX spot series acquisition.**
Run a free, no-key fetch of daily FX spot for G10 majors into `data/forex_rate_cache/`
(as JSON, one file per pair-date or per pair with dated rows), then run
`python3 tools/class_data_readiness.py --json` and confirm the FOREX `fx rates` gap
(requires ≥100 files) has cleared and FOREX reads `READY`. Cite the row/file count.
If no free source yields ≥100 dated records for ≥6 G10 pairs after 3 attempts, record
FOREX as UNMEASURABLE and stop the FX branch. Output: cache files +
`docs/edge_research/block1_r01_fx_spot.md`.

**Round 2 — FX spot continuity & gap audit.**
On the Round-1 cache, compute per-pair interior date gaps and duplicate dates. Gate:
readiness still READY AND 0 pairs with >5-business-day interior gaps. If >20% of pairs
have unfillable interior gaps, downgrade FOREX back to BLOCKED_DATA. Output:
`reports/block1_r02_fx_gap_audit.json`.

Both rounds are **data-acquisition only** — no backtesting, no new harness code, no
commits unless the operator asks.

---

## Change log

| When | Who | What |
|------|-----|------|
| 2026-11-22T08:55Z | deepseek-flash (architect) | Created this 200-round program from the 12-class audit recon. Rounds 1–2 designated live. |
