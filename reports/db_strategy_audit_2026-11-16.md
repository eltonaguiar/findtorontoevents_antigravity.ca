# Database and strategy audit — 2026-11-16

Read-only audit of `ejaguiar1_backtests` and `ejaguiar1_stocks` through `tools/db_env.py`.
No row, index or schema was modified. Every figure regenerates from `reports/db_audit_2026-11-16.json`.

## 1. Headline findings

1. **The backtest archive is mostly open positions, not results.** Of 32,676,918 rows, 29,254,138 (89.5%) are `OPEN`; only 3,422,780 (10.5%) are resolved. Any query that ignores `status` measures the open book, not performance.
2. **Resolved coverage is almost entirely crypto.** CRYPTO supplies 2,341,679 resolved priced rows and MEMECOIN 109,517; EQUITY, FOREX, FUTURES and ETF supply 4,416, 6,795, 5,520 and 1,104.
3. **Those four small subsets are broken, not bad strategies.** They resolve at 0.0-0.7% WR with a zero total — a sign/price convention failure in their imports, not evidence the classes lack edge.
4. **The crypto archive is negative after cleaning:** 2,341,679 rows, 41.6% WR, PF 0.68. The live ledger says the opposite (50.9% WR, PF 3.07) — a contradiction that points at entry pricing, not strategy quality.
5. **The live ledger is inflated by outliers and missing geometry.** 16,170 of 50,838 rows (31.8%) lack a TP or SL, 206 have TP on the wrong side and 476 have SL on the wrong side. COMMODITY reports PF 6,690 on n=510 and `alpha_engine` PF 176 with a +1,017,931% total — both from a handful of |PnL|>100% rows.
6. **Copytraders are not investable on current evidence:** 50 resolved, 22.0% WR, PF 0.33.
7. **Kalshi and Polymarket have zero resolved rows.** No WR, PF or sizing claim is defensible until contracts settle.

**Verdict: no asset class is capital-ready today.** CRYPTO and MEMECOIN have the sample size; EQUITY, FOREX, FUTURES, ETF and COMMODITY do not have trustworthy arithmetic. The fix is integrity work, not new strategies.

## 2. Data integrity

### Backtest archive

| Class | rows | NULL PnL (open) | priced+resolved | bad entry | TP NULL | SL NULL |
| --- | --- | --- | --- | --- | --- | --- |
| CRYPTO | 19,669,046 | 16,401,717 | 2,341,679 | 8,634,742 | 10,251,775 | 10,251,061 |
| EQUITY | 4,118,978 | 4,113,249 | 4,416 | 151,978 | 1,831,308 | 1,831,288 |
| MEMECOIN | 2,431,649 | 2,279,184 | 109,517 | 1,418,217 | 1,418,003 | 1,417,923 |
| FOREX | 2,317,710 | 2,305,722 | 6,795 | 251,802 | 988,414 | 988,414 |
| FUTURES | 2,309,325 | 2,303,805 | 5,520 | 60 | 60 | 60 |
| ETF | 1,010,924 | 1,009,820 | 1,104 | 110,151 | 505,008 | 505,008 |
| PENNY_STOCK | 819,286 | 816,698 | 1,918 | 6,820 | 535,862 | 535,792 |

Status mix: OPEN=29,254,138, closed=1,495,232, LOST=1,104,881, WON=788,348, expired=33,630, WIN=265.
10,573,770 rows have a non-positive entry price and 15,530,430 have no take-profit, so entry/exit geometry cannot be validated for most of the archive.

### Live ledger (`at_signal_outcomes`, n=50,838)

- 16,170 rows (31.8%) missing TP **or** SL
- 206 TP on the wrong side of entry, 476 SL on the wrong side
- Outcome mix: SL_HIT=23,974, TP_HIT=16,028, WON=6,542, LOST=3,914, EXPIRED=332, OPEN=38
- Repo memory already flags `entry_price` as ~29% clean here; this audit is consistent with that and adds the geometry counts.

## 3. Backtest performance (resolved only: priced entry+exit, |PnL| <= 20)

| Class | rows | resolved n | WR | PF | sum PnL % |
| --- | --- | --- | --- | --- | --- |
| CRYPTO | 19,669,046 | 2,341,679 | 41.6% | 0.68 | 3,300 |
| MEMECOIN | 2,431,649 | 109,517 | 37.0% | 0.89 | 8,241 |
| FOREX | 2,317,710 | 6,795 | 0.7% | 0.01 | 0 |
| FUTURES | 2,309,325 | 5,520 | 0.0% | None | 0 |
| EQUITY | 4,118,978 | 4,416 | 0.0% | None | 0 |
| PENNY_STOCK | 819,286 | 1,918 | 34.5% | 0.28 | 0 |
| ETF | 1,010,924 | 1,104 | 0.0% | None | 0 |

Only CRYPTO and MEMECOIN have enough resolved rows to rank; the other rows should be read as "import broken".

### Candidate strategies (n >= 100, after the filter)

| PF | resolved n | WR | sum PnL % | Class | Strategy |
| --- | --- | --- | --- | --- | --- |
| 6.72 | 1,595 | 80.0% | 6,892 | CRYPTO | corr_vwap_reversion |
| 4.97 | 104 | 69.2% | 204 | CRYPTO | multi_period_rsi_confluence_sol |
| 3.09 | 131 | 75.6% | 313 | CRYPTO | keltner_compression_expansion_eth_v1 |
| 2.85 | 141 | 85.1% | 257 | CRYPTO | drawdown_recovery_rsi |
| 2.77 | 3,129 | 72.4% | 8,168 | MEMECOIN | quan_engine |
| 2.7 | 1,102 | 50.0% | 1,734 | MEMECOIN | signal_recorder |
| 2.68 | 390 | 84.6% | 498 | MEMECOIN | justin_breakout_volume_v2 |
| 2.33 | 124 | 60.5% | 96 | CRYPTO | multi_period_rsi_confluence_xrp |
| 2.24 | 168 | 71.4% | 220 | CRYPTO | multi_period_rsi_confluence |
| 1.98 | 440 | 47.7% | 389 | MEMECOIN | justin_trend_follow_v2 |
| 1.86 | 234 | 62.8% | 199 | CRYPTO | crypto_rsi_whaleconfirmed_v1 |
| 1.54 | 147 | 56.5% | 44 | CRYPTO | crypto_kalman_trend_residual_reversion_v1 |

These are **re-validation candidates**, not promotions. A PF above ~5 on one symbol/interval is usually cost-free or look-ahead; the archive has no commission or slippage columns, so every PF here is gross.

### Worst resolved strategies

| PF | resolved n | WR | Class | Strategy |
| --- | --- | --- | --- | --- |
| 0.05 | 876 | 7.1% | CRYPTO | opposite_day |
| 0.16 | 531,652 | 33.0% | CRYPTO | quan_engine |
| 0.17 | 891 | 49.6% | CRYPTO | coinglass_strategies |
| 0.29 | 1,336 | 49.5% | PENNY_STOCK | KIMI_signal_tracker |
| 0.45 | 2,871 | 33.3% | CRYPTO | irb_hoffman |
| 0.54 | 1,986 | 33.3% | CRYPTO | crypto-bb-squeeze-scout |
| 0.61 | 241 | 38.6% | CRYPTO | ensemble |
| 0.75 | 22,051 | 30.0% | CRYPTO | signal_recorder |

## 4. Live ledger by class and source

| Class | n | WR | PF | sum PnL % | |PnL|>20 |
| --- | --- | --- | --- | --- | --- |
| CRYPTO | 21,171 | 50.9% | 3.07 | 20,708 | 20 |
| FOREX | 1,998 | 48.5% | 1.99 | 88 | 0 |
| EQUITY | 730 | 53.8% | 1.33 | 163 | 6 |
| COMMODITY | 510 | 28.4% | 6690.03 | 999,968 | 2 |
| ETF | 192 | 40.1% | 1.11 | 10 | 1 |
| (blank) | 184 | 42.4% | 2.0 | 33 | 0 |
| FUTURES | 137 | 59.1% | 6.86 | 6 | 0 |
| MEMECOIN | 129 | 42.6% | 0.51 | -66 | 0 |
| BOND | 78 | 21.8% | 1.02 | 0 | 0 |
| UNKNOWN | 24 | 79.2% | 27.18 | 1 | 0 |

| Source | n | WR | PF | sum PnL % | |PnL|>20 |
| --- | --- | --- | --- | --- | --- |
| battleground | 14,027 | 56.9% | 1.77 | 3,207 | 0 |
| alpha_engine | 10,388 | 42.2% | 176.19 | 1,017,931 | 24 |
| mercury2 | 466 | 40.3% | 1.43 | 198 | 2 |
| multi_asset_copytrader | 50 | 22.0% | 0.33 | 0 | 0 |
| crypto_signal_engine | 46 | 10.9% | 0.28 | -38 | 0 |
| kimi_riseoftheclaw | 44 | 36.4% | 0.46 | -70 | 1 |

`trading_picks`: 52,335 resolved, 46.7% WR, PF 1.06, 196 rows beyond +/-20%.

## 5. Copytraders, Kalshi and Polymarket

**Copytraders** — 50 resolved:

| Strategy | n | WR | PF |
| --- | --- | --- | --- |
| vix_reversal | 15 | 26.7% | 0.12 |
| ema_stack_momentum | 10 | 20.0% | 1.32 |
| extreme_oversold_bounce | 8 | 50.0% | 1.03 |
| connors_rsi2 | 5 | 20.0% | 0.22 |
| hyperopt_connors_rsi2 | 4 | 0.0% | 0.0 |
| macd_divergence | 3 | 0.0% | 0.0 |
| bb_mean_reversion_forex | 3 | 0.0% | 0.0 |
| mean_reversion_bollinger | 2 | 0.0% | 0.0 |

**Kalshi** — 0 resolved. **Polymarket** — 0 resolved.

The dashboard's 27 PM rows are open and spot-derived. The contract resolver added on 2026-11-16 is the only path that makes this cohort measurable; 30 settled contracts is the minimum before quoting a WR.

## 6. Against financial-industry practice

| Practice | Industry norm | Current state | Gap |
| --- | --- | --- | --- |
| PnL derivation | direction-aware, from fills, with fees and slippage | stored `pnl_pct` trusted; four class imports sign-broken; no cost columns | **P0** |
| Open vs closed separation | only closed rows in performance stats | 89.5% of archive is OPEN; ad-hoc filters elsewhere | **P0** |
| Outlier handling | winsorize/quarantine, report raw + trimmed | raw PF (COMMODITY 6,690) | **P0** |
| Sample-size discipline | n>=100 + OOS before a class verdict | claims on n=50 (copytraders), n=0 (PM) | **P0** |
| Multiple testing | PBO / deflated Sharpe across the strategy set | validator exists, not applied to the archive | P1 |
| Walk-forward | purged, embargoed CV | aggregate results only | P1 |
| Transaction costs | commission, spread, slippage per class | absent | P1 |
| Benchmarking | vs buy-and-hold / class benchmark | absent | P2 |
| Risk sizing | fractional Kelly, vol targeting, DD caps | fixed sizing | P2 |
| Data contracts | uniqueness, freshness, schema CI | no unique key on (strategy,symbol,entry_time) | P1 |

## 7. Ranked improvements

1. **Separate OPEN from resolved everywhere (P0, ~2 h).** Persist a `resolved` flag and make every performance view filter on it. Largest single source of wrong numbers in the archive.
2. **PnL integrity auditor (P0, ~1 day).** Recompute PnL from entry/exit and direction, store `pnl_source`, quarantine mismatches. Confirms whether the 0.0-0.7% rows are sign-flipped and whether live CRYPTO (PF 3.07) or archive CRYPTO (PF 0.68) is right.
3. **Winsorize and dual-report (P0, ~2 h).** Exclude |PnL|>20%, publish raw and trimmed PF/WR, show the excluded count.
4. **Sample-size ladder (P0, ~2 h).** No sizing below n=100; n<30 labelled "insufficient". Retires copytrader and PM claims.
5. **Repair the four class imports (P1, ~1 day).** EQUITY, FOREX, FUTURES and ETF have 1.1k-6.8k resolved rows that are unusable; fix the price/sign convention and re-import.
6. **Cost model (P1, ~1 day).** Commission/slippage columns per class; subtract before ranking.
7. **Uniqueness + dedup (P1, ~4 h).** Unique key on (strategy, symbol, entry_time, source_table).
8. **OOS / PBO re-rank (P1, ~1 day).** Apply the anti-overfit validator to the archive; publish surviving pairs only.
9. **Retire losing cohorts (P1, ~1 h).** `multi_asset_copytrader` (22%/0.33), `crypto_signal_engine` (10.9%/0.28), `kimi_riseoftheclaw` (36.4%/0.46).
10. **Weekly DB audit job (P2, ~4 h).** Schedule this report; alert on open share, TP/SL null share, wrong-side geometry, outlier count.

## 8. Limits

- The archive scan was chunked by primary key (2M blocks, halving on server timeouts); single-pass aggregates over 32.7M rows exceeded the server limit.
- Percentages are unweighted across strategies; no shrinkage applied.
- Live `outcome` vs `pnl_pct` disagreements are counted, not corrected.
- No DB mutation was attempted; every figure is reproducible from the JSON.
