# Database and strategy audit — 2026-11-16

Read-only audit of `ejaguiar1_backtests` and `ejaguiar1_stocks` via `tools/db_env.py`.
No rows were modified, no schema was changed. Numbers regenerate from
`reports/db_audit_2026-11-16.json`.

## 1. Headline findings

1. **The backtest archive cannot support per-class verdicts yet.** It holds
   32,676,918 trades, but FOREX resolves at 0.4% WR with PF 0.0 and FUTURES/ETF at
   0% WR with zero total. Those are price/sign convention breaks, not strategy
   results. Only 2,470,949 rows (7.6%) survive a
   price-and-outlier sanity filter.
2. **The live ledger's PF is inflated by a handful of outliers.** COMMODITY shows
   PF 6,690 on n=510 and `alpha_engine` shows PF 176 with a total of +1,017,931%,
   both driven by a few |PnL|>100% rows. The same ledger is credible only after
   winsorizing.
3. **Copytraders are not investable on current evidence.** 50 resolved trades,
   22.0% WR, PF 0.33 — and the best strategy inside the cohort (`vix_reversal`,
   n=15) is 26.7% WR / PF 0.12.
4. **Kalshi and Polymarket have zero resolved rows** in the live outcomes table.
   No WR, no PF, no sizing is defensible.
5. **The classes with usable samples are CRYPTO, EQUITY, FOREX and ETF**, in that
   order; MEMECOIN is thin and COMMODITY is contaminated.

## 2. Data integrity (the actual gating issue)

### Backtest archive

| Class | rows | bad entry | TP NULL | SL NULL | |PnL|>100 | status≠PnL |
|---|---|---|---|---|---|---|
| CRYPTO | 19,669,046 | 8,634,742 | 10,251,775 | 10,251,061 | 312 | 0 |
| EQUITY | 4,118,978 | 151,978 | 1,831,308 | 1,831,288 | 0 | 0 |
| MEMECOIN | 2,431,649 | 1,418,217 | 1,418,003 | 1,417,923 | 0 | 0 |
| FOREX | 2,317,710 | 251,802 | 988,414 | 988,414 | 0 | 0 |
| FUTURES | 2,309,325 | 60 | 60 | 60 | 0 | 0 |
| ETF | 1,010,924 | 110,151 | 505,008 | 505,008 | 0 | 0 |
| PENNY_STOCK | 819,286 | 6,820 | 535,862 | 535,792 | 0 | 0 |

Archive totals: 10,573,770 rows with a non-positive entry price,
15,530,430 with no take-profit, 312 with |PnL| > 100%, and
0 where the stored outcome contradicts the stored PnL.

### Live ledger (`at_signal_outcomes`, n=50,838)

- 16,170 rows (31.8%) have a missing TP **or** SL
- 206 rows have TP on the wrong side of entry, 476 have SL on the wrong side
- 1 rows have no usable entry price
- Outcome mix: SL_HIT=23,974, TP_HIT=16,028, WON=6,542, LOST=3,914, EXPIRED=332, OPEN=38

## 3. Backtest archive, cleaned

Filter: `entry_price>0 AND exit_price>0 AND |pnl_pct|<=20`. `n` is the filtered count.

| Class | rows | clean n | WR | PF | sum PnL % |
| --- | --- | --- | --- | --- | --- |
| CRYPTO | 19,669,046 | 2,341,679 | 41.6% | 0.68 | 3,299.8 |
| MEMECOIN | 2,431,649 | 109,517 | 37.0% | 0.89 | 8,241.1 |
| FOREX | 2,317,710 | 6,795 | 0.7% | 0.01 | 0 |
| FUTURES | 2,309,325 | 5,520 | 0.0% | None | 0 |
| EQUITY | 4,118,978 | 4,416 | 0.0% | None | 0 |
| PENNY_STOCK | 819,286 | 1,918 | 34.5% | 0.28 | 0 |
| ETF | 1,010,924 | 1,104 | 0.0% | None | 0 |

### Strongest strategies after the filter (n ≥ 100)

| PF | n | WR | sum PnL % | Class | Strategy |
| --- | --- | --- | --- | --- | --- |
| 6.72 | 1,595 | 80.0% | 6,892.0 | CRYPTO | corr_vwap_reversion |
| 4.97 | 104 | 69.2% | 204.0 | CRYPTO | multi_period_rsi_confluence_sol |
| 3.09 | 131 | 75.6% | 313.3 | CRYPTO | keltner_compression_expansion_eth_v1 |
| 2.85 | 141 | 85.1% | 257.4 | CRYPTO | drawdown_recovery_rsi |
| 2.77 | 3,129 | 72.4% | 8,168.5 | MEMECOIN | quan_engine |
| 2.7 | 1,102 | 50.0% | 1,733.7 | MEMECOIN | signal_recorder |
| 2.68 | 390 | 84.6% | 498.0 | MEMECOIN | justin_breakout_volume_v2 |
| 2.33 | 124 | 60.5% | 95.8 | CRYPTO | multi_period_rsi_confluence_xrp |
| 2.24 | 168 | 71.4% | 220.0 | CRYPTO | multi_period_rsi_confluence |
| 1.98 | 440 | 47.7% | 388.9 | MEMECOIN | justin_trend_follow_v2 |
| 1.86 | 234 | 62.8% | 198.6 | CRYPTO | crypto_rsi_whaleconfirmed_v1 |
| 1.54 | 147 | 56.5% | 44.2 | CRYPTO | crypto_kalman_trend_residual_reversion_v1 |

### Weakest (n ≥ 100)

| PF | n | WR | sum PnL % | Class | Strategy |
| --- | --- | --- | --- | --- | --- |
| 0.05 | 876 | 7.1% | -4,370.7 | CRYPTO | opposite_day |
| 0.16 | 531,652 | 33.0% | -2,983,504.7 | CRYPTO | quan_engine |
| 0.17 | 891 | 49.6% | -3,426.1 | CRYPTO | coinglass_strategies |
| 0.29 | 1,336 | 49.5% | -5,043.7 | PENNY_STOCK | KIMI_signal_tracker |
| 0.45 | 2,871 | 33.3% | -2,290.4 | CRYPTO | irb_hoffman |
| 0.54 | 1,986 | 33.3% | -3,097.2 | CRYPTO | crypto-bb-squeeze-scout |
| 0.61 | 241 | 38.6% | -201.2 | CRYPTO | ensemble |
| 0.75 | 22,051 | 30.0% | -11,158.4 | CRYPTO | signal_recorder |

Read these as **candidates for re-validation**, not promotions. A PF above ~5
on a single symbol/interval is a look-ahead or cost-free artefact until proven
otherwise, and the archive has no commission or slippage columns.

## 4. Live ledger by class and source

| Class | n | WR | PF | sum PnL % | |PnL|>20 rows |
| --- | --- | --- | --- | --- | --- |
| CRYPTO | 21,171 | 50.9% | 3.07 | 20,708.1 | 20 |
| FOREX | 1,998 | 48.5% | 1.99 | 88.5 | 0 |
| EQUITY | 730 | 53.8% | 1.33 | 163.3 | 6 |
| COMMODITY | 510 | 28.4% | 6690.03 | 999,968.4 | 2 |
| ETF | 192 | 40.1% | 1.11 | 9.7 | 1 |
|  | 184 | 42.4% | 2.0 | 33.4 | 0 |
| FUTURES | 137 | 59.1% | 6.86 | 5.6 | 0 |
| MEMECOIN | 129 | 42.6% | 0.51 | -65.5 | 0 |
| BOND | 78 | 21.8% | 1.02 | 0.1 | 0 |
| UNKNOWN | 24 | 79.2% | 27.18 | 1.1 | 0 |

| Source | n | WR | PF | sum PnL % | |PnL|>20 rows |
| --- | --- | --- | --- | --- | --- |
| battleground | 14,027 | 56.9% | 1.77 | 3,206.8 | 0 |
| alpha_engine | 10,388 | 42.2% | 176.19 | 1,017,931.4 | 24 |
| mercury2 | 466 | 40.3% | 1.43 | 198.0 | 2 |
| multi_asset_copytrader | 50 | 22.0% | 0.33 | -0.2 | 0 |
| crypto_signal_engine | 46 | 10.9% | 0.28 | -38.3 | 0 |
| kimi_riseoftheclaw | 44 | 36.4% | 0.46 | -70.3 | 1 |

`trading_picks`: 52,335 resolved, 46.7% WR, PF 1.06,
196 rows beyond ±20%. Status mix: OPEN=92,302, TIME_EXIT=33,635, TP_HIT=7,110, LOST=5,640, SL_HIT=3,892.

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

Zero resolved rows is the finding. The dashboard's 27 PM rows are spot-derived
and open; the contract resolver added on 2026-11-16 is the only path that will
make this cohort measurable, and it needs ≥30 settled contracts before any
WR/PF claim.

## 6. Against financial-industry practice

| Practice | Industry norm | Current state | Gap |
|---|---|---|---|
| PnL derivation | recomputed from fills, direction-aware, fees+slippage | stored `pnl_pct` trusted; FOREX/FUTURES/ETF sign-broken; no cost columns | **P0** |
| Outlier handling | winsorize / quarantine, report raw and trimmed | raw means; PF 6,690 from a few rows | **P0** |
| Sample-size discipline | n≥100 and OOS before a class verdict | verdicts on n=50 (copytraders), n=0 (PM) | **P0** |
| Multiple testing | PBO / deflated Sharpe across the strategy set | validator exists, not applied to the 342 backtest pairs | P1 |
| Walk-forward | purged, embargoed CV | aggregate backtests only; no OOS split recorded | P1 |
| Transaction costs | commissions, spread, slippage per asset class | absent from the archive | P1 |
| Benchmarking | compare vs buy-and-hold and class benchmark | no benchmark column | P2 |
| Risk sizing | fractional Kelly / vol targeting, drawdown caps | fixed sizing; `max_drawdown` only in run aggregates | P2 |
| Data contracts | uniqueness, freshness, schema checks in CI | no unique key on (strategy,symbol,entry_time) | P1 |
| Attribution | per-class/source/strategy with shrinkage | per-source tables exist, no shrinkage | P2 |

## 7. Ranked improvements

1. **PnL integrity auditor (P0, ~1 day).** Recompute PnL from entry/exit and
   direction for every ledger; store `pnl_source` and quarantine mismatches.
   Until this exists, class verdicts rest on broken arithmetic.
2. **Winsorize and report both views (P0, ~2 h).** Cap or exclude |PnL|>20%,
   publish raw and trimmed PF/WR, and count the excluded rows on the dashboard.
3. **Sample-size ladder (P0, ~2 h).** No sizing below n=100; label n<30 as
   "insufficient". This alone retires the copytrader and PM claims.
4. **Cost model (P1, ~1 day).** Add commission/slippage columns to
   `bt_backtest_trades` and subtract per-class spreads before ranking.
5. **Uniqueness + dedup (P1, ~4 h).** Add a unique key on
   (strategy, symbol, entry_time, source_table) after a dedup pass.
6. **OOS / PBO on the 342 pairs (P1, ~1 day).** Re-rank the archive with the
   existing anti-overfit validator and publish surviving pairs only.
7. **Retire losing cohorts (P1, ~1 h).** `multi_asset_copytrader` (22%/0.33),
   `crypto_signal_engine` (10.9%/0.28), `kimi_riseoftheclaw` (36.4%/0.46).
8. **Weekly DB audit job (P2, ~4 h).** Schedule this report, alert on
   integrity drift (TP/SL null share, wrong-side geometry, outlier count).

## 8. Limits

- `bt_backtest_trades` is 32,676,918 rows; the scan was chunked by primary key
  (2M blocks, halving on server timeouts) because single-pass aggregates exceeded
  the server's query limit.
- Percentages are unweighted across strategies; no shrinkage applied.
- The live ledger's build/outcome semantics (`outcome` vs `pnl_pct`) were read as
  stored; a row where the two disagree is counted, not corrected.
- No DB mutation was attempted, so every finding above is reversible by
  re-running the audit.
