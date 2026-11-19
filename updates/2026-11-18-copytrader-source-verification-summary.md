# Copytrader Source Verification — 2026-11-18

Status: **verification complete, no source is money-ready.**
Tool: `copy_trader_intel/source_truth_verifier.py` (`probe`, `backtest`, `github`, `registry`).

## What was asked

Find free, verified copytrader / public-trade sources across asset classes, prove
they carry no future/lookahead bias (timestamps checked in UTC), backtest them
honestly, discover GitHub repos publishing picks (including `eltonaguiar`), and
integrate only what survives into the pipeline + `/audit` dashboard.

## Headline result

**0 of 9 asset classes are money-ready.** Two sources are usable for monitoring
only; one is a data artifact and must never be sized on.

| Asset class | Money-ready source | Why |
|---|---|---|
| CRYPTO | none | OKX survives OOS but is leaderboard-selected; Hyperliquid decays |
| FOREX | none | only Treasury yields as macro input, no trade PnL |
| EQUITY | none | ARK / SEC Form 4 are flow data, not trade PnL |
| COMMODITY | none | CFTC COT is positioning, no trade PnL |
| FUTURES | none | same as commodity |
| ETF | none | ARK only |
| MEME | none | Dexscreener is discovery only |
| PENNY_STOCK | none | no source found |
| BOND | none | Treasury yields only |

## Probe verdicts (`data/source_truth_report.json`)

All 8 reachable sources are timestamp-**CLEAN** — no future timestamps, no
synthetic duplicate blobs, no entry-after-exit. The earlier draft of this file
claimed OKX/Hyperliquid/Polymarket were REJECTed for missing timestamps; that
was wrong and has been corrected.

| Source | Verdict | n | WR | Wilson LB | PF | Integrity |
|---|---|---|---|---|---|---|
| `okx_copytrading` | WATCH | 69 | 52.17% | 40.59% | 4.90 | CLEAN |
| `hyperliquid_whales` | WATCH | 2884 | 42.61% | 40.82% | 1.26 | CLEAN |
| `polymarket_v2` | REJECT_ARTIFACT | 927 | 99.14% | 98.31% | inf | CLEAN |
| `cftc_cot` | DATA_OK_NO_TRADE_PNL | — | — | — | — | CLEAN |
| `ark_daily_trades` | DATA_OK_NO_TRADE_PNL | — | — | — | — | CLEAN |
| `sec_form4_insider` | DATA_OK_NO_TRADE_PNL | — | — | — | — | CLEAN |
| `treasury_yields` | DATA_OK_NO_TRADE_PNL | — | — | — | — | CLEAN |
| `dexscreener_meme` | DATA_OK_NO_TRADE_PNL | — | — | — | — | CLEAN |
| `myfxbook_outlook` | UNREACHABLE | — | — | — | — | auth required |

## The OKX artifact (why raw numbers were misleading)

OKX `public-subposition-history` returns **ticket-level** records — one round
trip is split across several partial scale-out tickets. Counting tickets inflates
win rate.

Added `aggregate_round_trips()` to collapse tickets by position. Effect:

| Trader | Ticket WR | Collapsed WR | OKX's own `winRatio` |
|---|---|---|---|
| CchrisBbtc | 74.3% | 50.0% | 0.5222 |
| Adored-PoW | 75.0% | 50.0% | 0.5778 |
| all leaders | 73.0% | 52.2% | ~52% |

Raw WR 73% → collapsed 52%, matching OKX's reported `winRatio`. `apply_artifact_guards()`
now rejects zero-loss series and impossible profit factors, and `verdict_for()` caps
leaderboard-selected sources at WATCH (selection bias).

## Backtest (`data/source_truth_backtest.json`)

60/40 temporal split, FIFO round trips.

| Source | IS WR | OOS WR | IS PF | OOS PF | Verdict |
|---|---|---|---|---|---|
| `okx_copytrading` | 53.33% | 51.61% | 12.74 | 2.08 | SURVIVES_OOS |
| `hyperliquid_whales` | 51.86% | 45.62% | 2.02 | 0.74 | DECAYS |
| `polymarket_v2` | 100% | 97.84% | inf | 927.63 | ARTIFACT_NOT_BACKTESTABLE |

- **OKX** holds WR across the split (53.3 → 51.6) but the OOS sample is n=31 and
  the PF collapse (12.7 → 2.1) is mostly one large winner. Treat as WATCH.
- **Hyperliquid** genuinely decays: OOS expectancy is **negative** (−0.229) and
  PF falls below 1. Do not size on it.
- **Polymarket** is not a backtest at all — the data-api leaderboard endpoint only
  surfaces closed **winners**, so there are effectively no realised losses.
  `IMPOSSIBLE_PF_1686` guard fires. Never size on this.

## GitHub discovery (`data/copytrader_github_repos.json`)

- 19 queries across crypto, forex, commodity/COT, penny, value, ETF/ARK, bond,
  futures, prediction markets, ML prediction, quant backtest, earnings momentum.
- **104 candidate repos, 0 usable** — none publish a machine-readable pick file
  with parseable timestamps at any probed path.
- **82 `eltonaguiar` repos scanned, 0 with published pick JSON.** The org
  publishes code and dashboards, not timestamped pick artifacts.
- Scanner now runs concurrently (16–24 workers); full pass completes in well
  under the previous timeout.

## Accepted registry (`data/copytrader_verified_sources.json`)

7 sources accepted, all capped at WATCH / DATA_OK (none TRUSTED):

`okx_copytrading`+`hyperliquid_whales` (CRYPTO, FUTURES),
`cftc_cot` (COMMODITY, FUTURES, INDEX, BOND),
`ark_daily_trades` (EQUITY, ETF), `sec_form4_insider` (EQUITY, PENNY_STOCK),
`treasury_yields` (FOREX, BOND), `dexscreener_meme` (MEME).

## Fixes made this session

1. Per-source `stale_tolerance_days`, `date_granularity`, censored entry/exit
   pairs, and Polymarket resolution-date handling — removed 6 false FLAGs.
2. `aggregate_round_trips()` — OKX ticket inflation corrected.
3. `apply_artifact_guards()` + `selection` cap — artifact and selection bias
   now blocked at the verdict layer.
4. Polymarket backtest labelled `ARTIFACT_NOT_BACKTESTABLE` instead of
   `SURVIVES_OOS`.
5. `_json_safe()` — backtest artifact no longer emits `Infinity` (invalid strict
   JSON that would break JS consumers).
6. Concurrent GitHub scanning (`ThreadPoolExecutor`) — removed the timeout.

## Next steps

1. Wire the 7 accepted sources into `audit_trail/dashboard_generator.py`
   `JSON_PICK_SOURCES` as monitoring-only entries (WATCH, never sized).
2. Add a live emitter so OKX/Hyperliquid refresh their sidecars on a schedule.
3. Keep the `REJECT_ARTIFACT` and `DECAYS` sources out of any sizing path.
4. Re-probe monthly; a WATCH can be promoted only with n≥100 and clean OOS.
