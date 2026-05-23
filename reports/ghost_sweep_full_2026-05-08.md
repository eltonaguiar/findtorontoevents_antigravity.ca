# Full Ghost-Pattern Sweep — `ejaguiar1_stocks` MySQL DB

**Date:** 2026-05-08
**Scope:** all 322 tables in `ejaguiar1_stocks` @ `mysql.50webs.com` + sports DB `lm_arena_bets`
**Method:** read-only SELECT pattern-mining (`tools/ghost_sweep_2026_05_08.py` + `..._deep.py`); freebuff direct-pymysql connection pattern (no pool, fresh conn per table, 60s read_timeout). 46 tables had > 100 rows AND a PnL-like column or were on the explicit probe list. Sweep ran in 90 s wall.
**Skipped (already known):** `bt_backtest_trades` 5 cohorts, `at_raw_picks` quan_engine MATIC, `goldmine_cursor_predictions`, `meme_signals`. Re-detected for sanity; not re-flagged.

Raw outputs: `reports/_ghost_sweep_candidates.json`, `_ghost_sweep_raw.json`, `_ghost_sweep_log.txt`, `_ghost_sweep_deep_log.txt`.

---

## TL;DR — Top 5 NEW ghost patterns

| # | Table | Pattern | Rows polluted | Confidence |
|---|---|---|---|---|
| **1** | `rapid_signals` | Replay/CSV import — every strategy × pair gets identical entry_price at identical second timestamps; bimodal WR (0.6 % / 5 % vs 92 % / 99 %) | **35,352 / 35,352 (100 %)** | HIGH |
| **2** | `lm_signals` | 95 % of rows have `pnl_pct = 0.0000` — resolver never wrote real PnL | **31,996 / 33,732 (94.9 %)** | HIGH |
| **3** | `at_discord_notifications` | 100 % of `pnl_pct` is NULL — ever-unresolved | **40,242 / 40,242 (100 %)** | HIGH |
| **4** | `trading_picks` | 80 % NULL `pnl_pct`; 2,834 rows with NULL `created_at`; 9 single-second batch clusters covering 1,420 rows | **51,639 + 1,420 (54k of 64k)** | HIGH |
| **5** | `at_consensus_picks` | F4 time-travel: 8 cohorts (SPY/QQQ/ETHUSDT/BTCUSDT/SOLUSDT/TLT/XRPUSDT) where N>50 picks share 1 entry_price, 1 TP, identical pnl_pct, but distinct generated_at and a tiny set of closed_at | **1,181 / 9,218 (12.8 %)** | HIGH |

Plus 4 medium-priority follow-ons (daytrader_sim_*, alpha_engine MATIC twin, batch-clusters in trading_picks, at_signal_outcomes scope).

---

## Detailed findings

### 1. `rapid_signals` — synthetic / batch-replay (HIGH)
- **Real rows:** 35,352. Status = `closed` for all rows; 17,730 `win` / 17,622 `loss`.
- **Smoking gun A (timestamp clusters):**
  ```
  2026-02-27 14:43:26  n=3684  distinct_strategies=6  distinct_pairs=3
  2026-02-27 15:01:28  n=3129
  2026-02-28 20:33:59  n=2444
  ```
  Cluster decomposition shows that 6 strategies × CVX@185.00 LONG appear 559×6 times at the exact same second, 6 strategies × COIN@172.70 LONG appear 727×6 times, etc. Real-time scanners do not produce that pattern; it is a CSV/batch import where the same scan was multiplied across strategies.
- **Smoking gun B (bimodal WR):**
  ```
  rs-breakout-scout       n=1600 WR=97.1%
  donchian-stock-breakout n=959  WR=99.1%
  quality-minus-junk      n=2314 WR=92.3%
  crypto-fear-reversal    n=2059 WR=91.6%
  vs.
  betting-against-beta    n=2154 WR=0.6%
  options-flow-scout      n=1822 WR=5.2%
  call-surge-scout        n=1123 WR=5.4%
  meme-velocity           n=989  WR=19.2%
  ```
  Real strategies regress to 35-60 %. Polar 0-99 % WR over n>1000 = label-leakage / synthetic.
- **Sample (verbatim id=1..5):** all 5 are `quality-minus-junk` / `quality-momentum-scout` for `XOM` long with identical timestamp `2026-02-19 14:49:46` — different signal_ids, identical content.
- **Pollutes:** any "rapid_signals" tile or per-strategy WR aggregate on `/audit`; `rapid_signals` is referenced in feedback_rapid_signals_5237_mislabel and is now confirmed worse than mislabel — it is a fully synthetic table.

### 2. `lm_signals` — resolver dead, 95 % pnl=0.0000 (HIGH)
- **Real rows:** 33,732 (none NULL).
- 31,996 rows have `ROUND(pnl_pct, 4) = 0.0000`. Distinct pnl_pct count over the rest = 1,046 plausible values.
- Because lm_signals has `algorithm_name`, `signal_type`, `entry_price`, `exit_price`, `exit_reason`, `target_tp_pct`, `target_sl_pct` — the *infrastructure* is there. The resolver clearly never wrote into this table for the bulk of rows, OR the entry_price equals exit_price (mirror of the `daytrader_sim_trades` failure mode).
- **Pollutes:** any `algorithm_name` ranking from lm_signals will show a near-constant 0 % return for 30k of 33k rows.

### 3. `at_discord_notifications` — never resolved (HIGH)
- **Real rows:** 40,242. `pnl_pct IS NULL` for 100 % of them. 22,856 distinct `created_at` so the rows are real (not duplicated in time), they're just never closed.
- **Pollutes:** any aggregate that joins discord notifications to picks or treats notification rows as "fired and resolved" trades. Should be excluded from any closed-trade analysis.

### 4. `trading_picks` — 80 % unresolved + batch clusters (HIGH)
- **Real rows:** 64,283. 51,639 (80.3 %) have `pnl_pct IS NULL`.
- 2,834 rows have `created_at IS NULL` — likely mass-imported batch with no source timestamp.
- 9 distinct second-resolution timestamps each carry 100-207 rows (1,420 rows total). Notable cluster `2026-04-18 19:02:59` — 161 rows, 161 distinct symbols, 1 strategy, 1 source: a single strategy fired on 161 symbols at the same instant. Plausible scanner output but worth flagging as suspect.
- Status mix is real-looking (`OPEN/active/LOST/WON/EXPIRED/SL_HIT/TP_HIT`), but only 12,644 (19.7 %) of rows have a `pnl_pct`.
- **Pollutes:** dashboard `trading_picks` source_system aggregates — denominator includes 51k unresolved rows, dragging WR appear-low.

### 5. `at_consensus_picks` — F4 time-travel cohort (HIGH)
- **Real rows:** 11,453 (9,218 with non-null pnl_pct).
- 8 cohorts where same-symbol/same-direction has > 50 picks all sharing one entry_price + one take_profit + identical rounded pnl_pct, with distinct `generated_at` (287 distinct ts) but tiny number of distinct `closed_at` (56) and distinct `exit_price` (6):
  ```
  symbol  dir   pnl_pct    n    distinct_entry  distinct_TP
  SPY    LONG  -1.3358   287    1               1
  QQQ    LONG   0.0000   283    2               2
  ETHUSDT LONG  1.8748   187    1               1
  BTCUSDT LONG  6.3688   111    1               1
  SOLUSDT LONG -0.6186   105    2               2
  TLT    LONG  -0.6464    78    1               1
  XRPUSDT LONG  1.4493    70    1               1
  SOLUSDT LONG -4.7968    60    2               2
  ```
- **Diagnosis:** 287 separate "consensus generations" of an SPY LONG, each entered at the same anchor price ($671.01), all later resolved against the same handful of historical bars. This is the **F4 time-travel** pattern previously suspected: the consensus pipeline rebuilds picks from a window-anchored backfill, then closes them at the live `exit_price` of whichever close-bar happened to be hit. `pnl_pct=-1.3358` is locked because it is `(661.535 - 671.01) / 671.01`.
- 1,181 of 9,218 non-null-pnl rows (12.8 %) live inside these cohorts.
- **Pollutes:** `/audit` consensus-tier WR + ETF/EQUITY breakdowns for SPY, QQQ, TLT and CRYPTO breakdowns for BTC/ETH/SOL/XRP. SPY WR is being dragged by the same -1.3358 % loss being counted 287 times.

---

## Other notable findings (medium / low priority)

### `at_raw_picks` — NEW alpha_engine MATIC twin
- 440 rows of `source_system='alpha_engine'`, `symbol='MATICUSDT'`, `direction='LONG'`, identical `entry_price=0.37940000`, identical `take_profit=0.38505714`, identical `stop_loss=0.37657143`, all `pnl_pct=-15.0000`, all `status='CLOSED'`. This is the **same fingerprint** as the known 1,085-row `quan_engine` MATIC -15 cohort but under a different source_system label. Treat as the same defective generator wired through two pipelines. Net at_raw_picks MATIC ghost size: **1,525 rows** (1,085 quan_engine + 440 alpha_engine), confirms the existing memory note `1525/1537 MATIC rows are quan_engine-style ghosts`.

### `daytrader_sim_trades` (n=838) + `daytrader_sim_days` (n=176) — broken sim
- 100 % of `daytrader_sim_trades.pnl = 0.00`, every row has `exit_price = entry_price`.
- 100 % of `daytrader_sim_days.return_pct = 0.0000`. `total_pnl = 0.00`, `wins = 0`, `losses = 5` for every day. The sim records "5 losses" but PnL is 0 — sim path is half-implemented.
- Confidence: HIGH for "the sim never executed", LOW priority for `/audit` because volumes are tiny and these tables aren't surfaced in the live dashboard.

### `at_signal_outcomes` (n=121)
- Sweep flagged `distinct_pnl=1` but follow-up shows it's actually 30+ distinct values; flag was due to one-row groups falling under > 100 threshold incorrectly. **False positive — clean.** Real distribution: -18 to +3 across 49 LOSS / 13 WIN / 38 OPEN / 13 EXPIRED. Source `kimi_signal_tracker`. NOT a ghost.

### `cw_winners` (n=346), `miracle_picks2` (n=249), `miracle_picks3` (n=644), `daytrader_sim_*`
- These tables hold an `outcome` text column (`won/lost/winner/loser/win/loss/...`) and the sweep mistakenly tried to detect constant `outcome` clustering. They have real `pnl_pct`/`outcome_pct` columns (cw_winners has `pnl_pct double`, miracle has `outcome_pct decimal`). Their distributions are reasonable. **False-positive cluster.** Not flagged as ghosts.
  - cw_winners verdict mix: 186 LEAN_BUY / 151 BUY / 9 STRONG_BUY → outcome 100 win / 163 loss / ~80 partials. Plausible.
  - miracle_picks3 outcome: 344 lost / 258 won / 42 pending. Plausible.

### `gm_sec_13f_holdings` (n=2,084) + `gm_unified_picks` (n=1,846)
- Each shows large single-second clusters (1,040 rows at one ts on 13f_holdings; 363+339+254 on unified_picks). For 13F filings this is **expected** (one filing dump = one timestamp), so HIGH false-positive risk. Not a ghost — flagged for awareness only.

### `simulation_grid` (n=6,000)
- Earlier Kimi note "100 % LONG, 0 SHORT": confirmed. All rows `direction='LONG'`. PnL distribution looks varied (`profit_factor`, `total_return_pct`, `win_rate` all populated and varying). **Direction-bias bug only**, not ghost data.

### `alpha_picks` (n=5,043) and `stock_picks` (n=7,239)
- Schemas confirm Kimi #3: **no exit-tracking columns** (no `exit_price`, no `pnl_pct`, no `outcome`, no `closed_at`). These are pick-issuance tables only. They cannot pollute closed-trade aggregates because they have no closed-trade rows. **Not ghost data**, but a separate gap: there is no resolver that joins alpha_picks/stock_picks to outcomes.

### `fxp_pair_picks` (n=1,184) and `cr_pair_picks` (n=952)
- Same as alpha_picks/stock_picks — no outcome columns at all. Pick-issuance only. **Not ghost data**, gap-by-design.

### `lm_arena_bets` (sports DB, n=344)
- 100 % `status='pending'`, all 344 rows. The DB has `actual_away_score`, `actual_home_score`, `pnl`, `result`, `settled_at` columns but they are never written. Confirms user's hunch — sports arena pipeline never settles bets.
- Confidence: HIGH that pipeline is broken; MEDIUM impact since it's surfaced on `findtorontoevents.ca` sports tab.

---

## Tables explicitly checked + cleared

`gm_sec_insider_trades` (no pnl col), `gm_failure_alerts` (no pnl col), `gm_system_health` (status table), `gm_news_sentiment` (no pnl col), `crypto_assets`/`crypto_exchange_netflow`/`KIMI_GOLDMINE_SOURCES` (n<25), all 12 zero-row crypto_* + KIMI_GOLDMINE_* tables, `ua_predictions` (n=355, no pattern), `mf2_backtest_trades` (n=450, no pattern), `at_local_picks` (n=2,103, no pattern), `at_permutation_picks` (n=1,514, no pattern), `lm_trades` (n=200, no pattern), `lm_sports_daily_picks` (n=222, no pattern), `challenge_200_trades` (n=620, no pattern), `stock_picks`, `alpha_picks`, `fxp_pair_picks`, `cr_pair_picks` (no outcome cols, pick-issuance only).

Tables not eligible (row count < 100 AND not on explicit probe list): not enumerated; sweep tool would re-include them if any subsequently grew.

---

## Recommended actions

1. **Quarantine `rapid_signals` entirely** until provenance is clear. The bimodal WR + same-second cross-strategy duplication says this is fixture data, not live signals.
2. **Add `lm_signals.pnl_pct = 0` filter** at every aggregation site, OR rebuild the resolver. Right now any `algorithm_name` slice of lm_signals reports near-zero return.
3. **Exclude `at_discord_notifications` from closed-trade aggregates.** It is a notification log, not a trade record. If any audit query reads it as a trade source, fix that query.
4. **`at_consensus_picks` F4 fix** — collapse the 287 SPY-LONG-(-1.3358) rows into one realized trade (or one per closed_at distinct value, capped at 6). Same for the 7 other cohorts. Net effect: 1,181 polluted rows → ~50 real rows.
5. **`trading_picks` resolver coverage** — 80 % NULL pnl_pct is the real story; figure out whether the 51,639 NULL rows are still-open (legitimate `OPEN/active`) or stuck-unresolved (`LOST/WON/EXPIRED` with no pnl_pct).
6. **Extend `at_raw_picks` MATIC kill** to source_system=`alpha_engine` as well as `quan_engine`. Existing kill rule presumably matches only one source.
7. **`lm_arena_bets` settlement pipeline** — confirm the cron that sets `status=settled` is alive.

---

## Limits and caveats

- Row counts come from `COUNT(*)` per table, not the stale `information_schema.TABLE_ROWS`. Real counts diverged from approx by up to 5× (rapid_signals 11k approx → 35k real; trading_picks 24k approx → 64k real; at_consensus_picks 5k approx → 11k real).
- "Constant pnl cohort" detection requires `pnl_pct` numeric column AND `entry_price` to be present; tables with text-only outcome columns are surfaced as `fixed_bracket` false-positives in raw output but are filtered out in the analysis above.
- Sweep used `> 100` as the cohort size threshold per the user spec. Tightening to 50 would surface ~3 extra small cohorts in `at_consensus_picks` (already partially captured) and a few cohorts in `at_local_picks`. Not chased here.
- Time budget per table held below 60 s; no timeouts triggered.
