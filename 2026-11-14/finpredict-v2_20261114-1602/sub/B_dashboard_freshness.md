# Subagent B — Dashboard freshness & metric-liveness audit

**FAIL** — "dashboard freshness + metric liveness".
The core build pipeline is genuinely fresh (1.6–1.8 h old at audit time), but the metrics it serves are largely dead, frozen, or internally inconsistent: EDGE/Track/FWD columns are empty or zero on 18–20 of 20 active picks, 19/20 active picks carry `pnl_pct == 0`, Smart Picks is empty, Performance-tab active counts are 7.9× the real count, and 8 of 11 classes in `summary_picks.json` report impossible win rates >100%.

Audit window: **2026-11-14T16:03Z – 16:08Z** (all ages below computed at **16:08:12Z** unless stated).
Targets: `https://findtorontoevents.ca/audit/` (HTTP 200, 1,432,405 B), `https://findtorontoevents.ca/audit/hyrotrader/` (HTTP 200, 92,985 B).
Raw evidence archive: `2026-11-14/finpredict-v2_20261114-1602/raw/` (see §10).

---

## 1. Freshness table (payload timestamps, age vs 16:08:12Z)

Verdict bands: FRESH <2 h · LATE 2–24 h · STALE >24 h · DEAD >7 d · MISSING.

| Payload | HTTP | Bytes | Timestamp field | Value (UTC) | Age | Verdict |
|---|---|---|---|---|---|---|
| `dashboard_payload.json` | 200 | 34,385,688 | `generated_at` | 2026-11-14T14:30:07 | **1.63 h** | FRESH |
| `dashboard_data.json` | 200 | 25,099,200 | `generated_at` | 2026-11-14T14:30:07 | **1.63 h** | FRESH |
| `money_ready_verdict.json` | 200 | 42,481 | `generated_at` | 2026-11-14T14:29:00 | **1.65 h** | FRESH |
| `pf_registry.json` | 200 | 15,178,278 | `generated_utc` | 2026-11-14T14:30:05 | **1.64 h** | FRESH |
| `anti_overfit_audit.json` | 200 | 27,973 | `generated_at` | 2026-11-14T14:22:00 | **1.77 h** | FRESH |
| `summary_picks.json` | 200 | 2,736 | `generated_at` | 2026-11-14T14:30:06 | **1.63 h** | FRESH (but broken math — §7) |
| `db_health.json` | 200 | 6,462 | `generated_at` | 2026-11-14T14:13:42 | **1.91 h** | FRESH |
| `ma_strategy_leaderboard.json` | 200 | 61,919 | `generated_at` | 2026-11-14T14:25:04 | **1.72 h** | FRESH |
| `ueps_picks.json` | 200 | 97,684 | `generated_at` | 2026-11-14T12:44:52 | **3.39 h** | LATE (by policy) |
| `hyro_quan_bridge.json` | 200 | 53,864 | `generated_at` | 2026-11-14T14:22:55 | **1.75 h** | FRESH |
| `claudes_test_dashboard.json` | 200 | 717,996 | `generated_at` | 2026-11-14T15:36:01Z | **0.54 h** | FRESH |
| `hyro_ml_pick_rankings.json` | 200 | 39,981 | `generated_at` | 2026-11-14T14:23:55 | **1.74 h** | FRESH |
| `stock_prices.json` | 200 | 1,224 | `updated_at` | 2026-11-14T14:13:38 | **1.91 h** | FRESH |
| `cot_paper_pilot_status.json` | 200 | 2,119 | `generated_at` | 2026-11-14T14:22:12 | **1.77 h** | FRESH |
| `crypto_rsi5070_us_forward_status.json` | 200 | 1,387 | `generated_at` | 2026-11-14T14:30:02 | **1.64 h** | FRESH |
| `top_n_rank_backtest.json` | 200 | 2,224 | `generated_at` | 2026-11-14T14:22:13 | **1.77 h** | FRESH |
| `audit_surface_truth.json` | 200 | 10,239 | `generated_at` | **2026-11-14T04:52:51** | **11.26 h** | **LATE** |
| `hyro_pick_performance.json` | 200 | 62,294 | `generated_at` | **2026-11-08T02:14:09** | **157.90 h (6.6 d)** | **STALE/DEAD** |
| `hyrotrader_picks.json` | 200 | 11,543 | `account_snapshot.last_session_date` | **2026-04-08** | **5,296 h (220.7 d)** | **DEAD** |
| `regime_report.json` | 200 | 556 | `momentum_last_updated` | **2026-06-05T07:15** | **3,896.9 h (162 d)** | **DEAD** |
| `strategy_ic_analysis.json` | 200 | 42,632 | `generated_at` | **2026-05-29T11:45** | **4,060.4 h (169 d)** | **DEAD** |
| `strong_signals.json` | 200 | 105,108 | `generated_at` | **2026-04-15T07:19** | **5,120.8 h (213 d)** | **DEAD** |
| `stock_forex_prices.json` | 200 | 519 | `updated_at` | **2026-04-11T12:16** | **5,211.9 h (217 d)** | **DEAD** |
| `pilot_forward_dashboard.json` | 200 | 12,321 | `timestamp` | **2026-06-06T02:30** | **3,877.6 h (161.6 d)** | **DEAD** |
| `strategy_admissibility.json` | 200 | 31,542 | `generated_at` | **2026-06-06T02:30** | **3,877.6 h (161.6 d)** | **DEAD** |
| `operator_review_today.json` | 200 | 6,117 | `generated_at` | **2026-08-27T10:25** | **1,901.7 h (79.2 d)** | **DEAD** |
| `claude_top_picks.json` (+phase2) | 200 | 17,723 / 3,235 | `generated_at` | **2026-03-14T06:00** | **5,889.6 h (245 d)** | **DEAD** |
| `grok_top_picks*.json` | 200 | 1,686 / 2,549 | `timestamp` | **2026-03-14** | **5,886.6–5,892.4 h** | **DEAD** |
| `kimi_top_picks*.json` | 200 | 2,828 / 2,609 | `generated_at` | **2026-03-14** | **5,886.6–5,890.1 h** | **DEAD** |
| `mercury_top_picks*.json` | 200 | 1,865 / 2,849 | `timestamp` | **2026-03-14** | **5,886.6–5,890.1 h** | **DEAD** |
| `ag_top_picks*.json` | 200 | 2,055 / 5,292 | `timestamp` | **2026-03-14** | **5,874.8–5,890.1 h** | **DEAD** |
| `hyro_live_strategies.json` | 200 | 5,700 | — none — | — | n/a | **no timestamp (static config)** |
| `hyrotrader_journal.json` | 200 | 222 | — none — | `trades: []` | n/a | **empty** |
| `active_picks.json` (at `/audit/data/`) | **404** | 992 | — | Apache 404 page | — | MISSING (not actually fetched by page; link only) |
| `hmm_regime.json` / `correlation_report.json` at `/audit/data/` | **404** | 992 | — | page fetches these from `raw.githubusercontent.com` instead | — | not a page break |
| `strategy_tribunal_latest.json` at `/audit/data/` | **404** | 992 | — | page fetches `./data/strategy_tribunal_latest.json` | — | **REAL broken panel** |

Server delivery lag (HTTP `last-modified`): all `/audit/data/*` files were written to the web root **14:37:51–14:38:53Z**, i.e. ~8 min after `generated_at`. Hence "generated 14:30, served 14:38". The page shell itself was rebuilt at **15:58:28Z** (last-modified), so the HTML is 10 min old at audit time.

---

## 2. Tab inventory → backing data → freshness

Top-level buttons found in `page_audit.html` (15; the UEPS long-term/swing/closed buttons are sub-tabs inside `tab-ueps`):

| # | Tab | Backing data | Freshness / status |
|---|---|---|---|
| 1 | Overview | `dashboard_data.json` → summary/systems/readiness/data_freshness | FRESH 1.63 h; but embedded sub-panels dead (§3) |
| 2 | ⭐ Active Picks | `picks.active` (20 rows) | FRESH (all 20 < 4 h) but metrics frozen (§5–6) |
| 3 | Verified Alpha | `verified_alpha` | 2 active, 1 source (`pm_kalshi_signals`); `audited.covered_active_picks = 0`, all audited WR fields `null` → **audited half DEAD** |
| 4 | 🧠 Smart Picks | `smart_picks_feed`, `smart_picks_by_asset`, `smartPicksByAsset` | **EMPTY**: `total_scored: 0`, all 7 asset lists `[]`; snapshot's last batch `2026-11-11T07:57` (~3.4 d) → DEAD |
| 5 | 📈 US Equity Picks (UEPS) | `ueps_picks.json` 3.39 h + server-rendered snapshot in HTML | LATE/FRESH-ish; sub-tabs Long-Term Value / Swing Plays / Closed Holds |
| 6 | Closed Picks | `picks.recent_closed` (3,500) | **STALE**: only 10 rows closed <24 h; median close age 29.1 d (CRYPTO) → 135 d (BOND) |
| 7 | Dashboards | static link list | n/a (navigation only) |
| 8 | Strat. Leaderboard | `leaderboard` (1,004) | fwd_wr 71 % populated (ALIVE); `bt_wr` 3 % populated, `bt_trades` 97 % zero, `decay` 1/1004 → **BT/decay columns DEAD** |
| 9 | Permutations | `cross_system_permutations` (13), `cross_strategy_permutations` (15) | **MOSTLY EMPTY**: 12/13 system perms have 0 active; all pair/triple perms 0 active AND 0 closed (only `solo_alpha` has 25 active) |
| 10 | Performance | `performance.by_asset_class` | **INCONSISTENT**: reports 158 active vs 20 actual; 5,008 closed vs 16,126 (§6) |
| 11 | Score Tracker | **browser `localStorage` only** (`getSnapshots()`, 10-min throttle) | **EMPTY for any new visitor** ("0 snapshots stored (none)"); not shared server data |
| 12 | ML Health | `ml_health` | **DEAD**: Claude Gainer ML `updated_at 2026-05-25` (173 d); ML Crypto Predictor `disabled`, no date |
| 13 | Links | static | n/a |
| 14 | Claude Top Picks (`tab-claudetoppicks`) | `data/claude_top_picks.json` | **DEAD 245 d** |
| 15 | Research / Systems / BT-vs-FWD / Bundles / Warnings / Audit / AI-Battle / Portfolios / Closet containers | various | Portfolios ← `claudes_test_dashboard.json` 0.54 h FRESH; Bundles `[]`; Audit `audit_events: []`, `filter_events: []`; BT-vs-FWD `decay` 0/255; Warnings 5 alerts |

Dead/empty sub-panels inside the FRESH Overview payload:
- `bundles: []`, `audit_events: []`, `filter_events: []`, `macro_context: {}`, `ta_baseline: {}`, `walkforward.by_class: {}` (`generated_at 2026-04-15`, 213 d).
- `extreme_conviction.total: 0`; `shadow_probation.enabled: false`, `shadow_picks: []`.
- `regime_validation.active_regime_composition = {total: 263, with_regime_data: 0, aligned: 0, misaligned: 0, neutral: 0}` → **regime layer 100 % empty**.
- `ml_health` 173 d.
- `strategy_tribunal_latest.json` fetch is a hard **404** → the "strategy tribunal" `<details>` panel always falls back to its error text.

---

## 3. Per-asset-class age table

Age computed from each row's `timestamp`/`signal_time` vs 16:08Z.

### `picks.active` (the 20 rows the Active Picks tab renders)

| Class | n | Newest | Oldest | Median | pnl==0 | null price | no date |
|---|---|---|---|---|---|---|---|
| ETF | 10 | 3.78 h | 3.78 h | 3.78 h | 10 | 0 | 0 |
| CRYPTO | 3 | 2.18 h | 2.91 h | 2.18 h | 2 | 0 | 0 |
| EQUITY | 2 | 2.99 h | 3.33 h | 3.16 h | 2 | 0 | 0 |
| FOREX | 2 | 1.67 h | 1.67 h | 1.67 h | 2 | 0 | 0 |
| COMMODITY | 2 | 1.71 h | 1.71 h | 1.71 h | 2 | 0 | 0 |
| FUTURES | 1 | 2.97 h | 2.97 h | 2.97 h | 1 | 0 | 0 |

**19/20 active picks have `pnl_pct` exactly 0.0** (all values: `0.0 ×19`, `2.74 ×1`). 7/20 have `current_price` bit-identical to `entry_price`; the other 13 differ only in the last float digits (pnl < 0.0001 %). Only NEARUSDT is actually marked to market. So the active panel is timestamp-fresh but **price/PnL-frozen**.

### `picks.active_raw` (4,148 rows; the raw feed kept in the payload)

| Class | n | Newest | Oldest | Median | Median (d) | pnl==0 | null price | unresolved* |
|---|---|---|---|---|---|---|---|---|
| CRYPTO | 3,577 | 1.7 h | **6,421.7 h** | **2,128.1 h** | **88.7 d** | 3,322 | 3,170 | 3,502 |
| FOREX | 277 | 1.7 h | 6,415.4 h | 26.0 h | 1.1 d | 273 | 242 | 276 |
| EQUITY | 182 | 3.0 h | 5,416.0 h | 25.5 h | 1.1 d | 142 | 110 | 179 |
| COMMODITY | 44 | 1.7 h | 4,056.0 h | 3.3 h | 0.1 d | 39 | 32 | 43 |
| ETF | 38 | 3.2 h | 5,416.0 h | 14.7 h | 0.6 d | 32 | 11 | 38 |
| BOND | 15 | 25.5 h | 26.4 h | 26.0 h | 1.1 d | 9 | 9 | 15 |
| FUTURES | 13 | 3.0 h | 5,416.0 h | **2,344.1 h** | **97.7 d** | 13 | 8 | 13 |
| SPORTS | 2 | 3.6 h | 3.6 h | 3.6 h | 0.2 d | 2 | 2 | 2 |

\* unresolved = status `OPEN`/`EXPIRED`/empty. Status split for `active_raw`: **EXPIRED 3,377 · OPEN 691 · SL_HIT 55 · TP_HIT 25**. The 2,838 "zombies" (age > 30 d & pnl == 0) are all EXPIRED rows that were never resolved and were never pruned.

Filtering to `status == OPEN` only, every class is genuinely recent: 668 dated OPEN rows, max age 10.0 d, **0 rows > 30 d** (CRYPTO 400 open, median 30.8 h; FOREX 118 / 3.0 h; EQUITY 74 / 3.4 h; ETF 30 / 3.8 h; COMMODITY 27 / 3.0 h; BOND 15 / 26 h; FUTURES 3 / 3.0 h). The staleness is therefore **dead rows left in the feed**, not stale open positions.

### `picks.recent_closed` (3,500 rows)

| Class | n | Newest | Oldest | Median | Median (d) |
|---|---|---|---|---|---|
| CRYPTO | 1,966 | 3.2 h | 6,475.7 h | 699.4 h | **29.1 d** |
| EQUITY | 738 | 33.3 h | 6,433.3 h | 2,882.6 h | **120.1 d** |
| ETF | 567 | 26.0 h | 6,433.3 h | 2,882.6 h | **120.1 d** |
| FOREX | 187 | 38.0 h | 6,475.7 h | 3,074.6 h | **128.1 d** |
| BOND | 35 | 98.2 h | 6,432.3 h | 3,241.4 h | **135.1 d** |
| COMMODITY | 7 | 25.5 h | 253.3 h | 117.3 h | 4.9 d |

Only **10** closed rows are <24 h old, **281** <7 d, **1,162** <30 d, **2,221 >30 d**, 1,132 >90 d, 582 >180 d. This is the feed that EDGE badges and leaderboard stats are computed from (`buildVerifiedEdgeIndex()` iterates `D.picks.recent_closed`), so every derived "edge" statistic is dominated by months-old closes.

---

## 4. The user's three claims — tested

| Claim | Measured | Verdict |
|---|---|---|
| "FUTURES shows 1 active pick with no date" | `picks.active` FUTURES = **1** row: `ES=F`, `timestamp 2026-11-14T13:06:02Z`, `age_hours 1.4`, `entry_time "2026-11-14"` (date-only). The Active Picks table's Time cell renders `p.timestamp` via `toEST(v)`, and `opened` (modal table) also maps to `p.timestamp`. | **NOT REPRODUCED.** The row has a timestamp. `entry_time` is date-only, and 8 FUTURES `EXPIRED` rows in `active_raw` have date-only `timestamp` (`2026-08-07` … `2026-08-12`) — those are the only "no time" FUTURES rows. Origin of the observation is `UNVERIFIED` (may be a different panel/browser state). |
| "BOND newest ~4 days old" | **Confirmed for the Closed Picks tab**: newest `recent_closed` BOND = `closed_at 2026-11-10T14:34:06Z`, **97.5 h = 4.06 d** (35 rows, median 135 d). But `active_raw` BOND rows are 25.5–26.4 h old, and BOND has **0** rows in `picks.active` / `activeCount 0`. | **MATCHES the Closed Holds/Closed Picks view.** Not true for the active feed. |
| "CRYPTO 1.9 h ago" | CRYPTO in `picks.active`: newest `XRPUSDT 2026-11-14T13:53:28Z` = **2.18 h** at 16:03Z; BTCUSDT same timestamp; NEARUSDT 2.91 h. `active_raw` CRYPTO newest 1.7 h. If viewed ~15:45Z the age was ~1.9 h. | **APPROXIMATELY CONSISTENT** (2.2 h at audit time). Note Smart Picks' own `generated_at` is 12:57:02Z (3.2 h). |

Additional observation the claims point at: `asset_class_summary.BOND = {activeCount: 0, smartCount: 0, avgScore: 0.0, forwardWR: 0.0, thresholdPass: **true**}` → the quality strip renders BOND as a green **PASS** with zero picks (vacuous-threshold bug). FUTURES renders `activeCount 1, forwardWR 0.059 (5.9 %), thresholdPass false`.

---

## 5. Metric liveness (what the "Edge / Track / FWD WR / FWD N" columns actually contain)

The Active Picks table columns are defined as `verified_edge` (EDGE), `_ic_track` (Track), `strat_fwd_wr` (FWD WR), `strat_fwd_trades` (FWD N), `timestamp` (Time), `age_hours` (Age). Both EDGE and Track are **computed client-side**; EDGE from `picks.recent_closed`, Track from `sym_track_*` → `strat_fwd_wr` fallback.

### 5a. `picks.active` (n=20) — field presence

| Field (column) | non-null | non-zero | distinct | min | max | % equal to mode | Liveness |
|---|---|---|---|---|---|---|---|
| `verified_edge` (EDGE) | 0/20 | 0 | 0 | — | — | — | **FROZEN/ABSENT field** |
| EDGE recomputed (JS logic) | **0/20 non-null tier** | — | — | — | — | — | **DEAD — every pick shows blank EDGE** |
| `_ic_track` (Track raw field) | 0/20 | 0 | 0 | — | — | — | absent; computed fallback used |
| Track recomputed (`_effectiveTrackWrPick`) | 2/20 (both 0 %) | 0 | 1 | 0 | 0 | 90 % | **DEAD — 18/20 "—", 2/20 "0 %"** |
| `sym_track_wr` | 0/20 | 0 | 0 | — | — | — | **FROZEN (all null)** |
| `sym_track_total` | 20/20 | **0** | 1 | 0 | 0 | **100 %** | **FROZEN at 0** |
| `strat_fwd_wr` (FWD WR) | **2/20 (10 %)** | 1 | 2 | 0.0 | 12.5 | 50 % | **PARTIALLY_DEAD** |
| `strat_fwd_trades` (FWD N) | 20/20 | 2 | 3 | 0 | 9 | **90 % zero** | **PARTIALLY_DEAD** |
| `forward_wr` | 20/20 | 1 | 3 | 0.0 | 5.9 | **95 % zero** | **PARTIALLY_DEAD** |
| `forward_trades` | 20/20 | 2 | 3 | 0 | 376 | 90 % zero | **PARTIALLY_DEAD** (376 belongs to ES=F only) |
| `sym_dir_fwd_wr` | 11/20 | 7 | 7 | 0 | 51.7 | 36 % | ALIVE but sparse |
| `sym_dir_fwd_n` | 20/20 | 11 | 12 | 0 | 82 | 45 % zero | ALIVE but sparse |
| `pnl_pct` | 20/20 | **1** | 3 | 0 | 2.74 | **95 % zero** | **FROZEN (19/20 = 0.0)** |
| `current_price` | 20/20 | 20 | 20 | 0.5525 | 66,300 | 5 % | present but **7/20 == entry_price**, other 13 differ <1e-4 |
| `entry_price` | 20/20 | 20 | 20 | 0.5525 | 66,300 | 5 % | ALIVE |
| `confidence` | 20/20 | 20 | 16 | 0.55 | 0.9991 | 15 % | ALIVE |
| `score` | 20/20 | 20 | 16 | 12 | 100 | 20 % | ALIVE |
| `elite_score` | 20/20 | 20 | 14 | 19 | 62 | 10 % | ALIVE |
| `ml_score` | 16/20 | 16 | 10 | 0.85 | 61.0 | 25 % | PARTIALLY (20 % null) |
| `edge` (field named exactly `edge`) | 0 | — | — | — | — | — | **does not exist anywhere in payload** |

EDGE replication detail: `buildVerifiedEdgeIndex()` over the 3,500 `recent_closed` rows yields **20 GOLDEN combos, 2 VERIFIED strategies, 6 strategies passing `stratOverallOk`, 409 track combos, 96 track strategies**. **None** of the 20 active picks' `(strategy, symbol)` pairs matches any of them; 19 of the 20 strategies have **n=0** closed trades in `recent_closed` (the 20th, `etf_faber_tactical`, has n=1). Therefore EDGE is blank for 20/20.

### 5b. `picks.active_raw` (n=4,148) — same fields

| Field | non-null | non-zero | distinct | min | max | mode share | Liveness |
|---|---|---|---|---|---|---|---|
| `strat_fwd_wr` | 89 (2 %) | 77 | 20 | 0 | 100 | 17 % | **PARTIALLY_DEAD (98 % null)** |
| `strat_fwd_trades` | 263 (6 %) | 89 | 20 | 0 | 3,887 | 66 % | **PARTIALLY_DEAD** |
| `forward_wr` | 445 (11 %) | 159 | 37 | 0 | 100 | 64 % | PARTIALLY_DEAD |
| `forward_trades` | 445 (11 %) | 154 | 34 | 0 | 4,434 | 65 % | PARTIALLY_DEAD |
| `sym_track_wr` | 45 (1 %) | 37 | 25 | 0 | 100 | 18 % | DEAD-feed |
| `sym_track_total` | 263 (6 %) | 45 | 24 | 0 | 294 | 83 % | DEAD-feed |
| `sym_dir_fwd_wr` | 195 (5 %) | 148 | 71 | 0 | 100 | 24 % | sparse |
| `sym_dir_fwd_n` | 263 (6 %) | 195 | 60 | 0 | 139 | 26 % | sparse |
| `pnl_pct` | 4,148 (100 %) | **316** | 245 | -99.88 | 146.42 | **92 % = 0.0** | **FROZEN** |
| `current_price` | **564 (14 %)** | 564 | 355 | 4.37e-06 | 67,202 | 2 % | **86 % MISSING** |
| `entry_price` | 4,148 | 4,063 | 2,003 | 0.0 | 86,450 | 2 % | ALIVE but 85 rows ≤ 0 |
| `confidence` | 4,148 | 3,739 | 412 | 0 | 1.0 | 56 % | ALIVE-ish |
| `score` | 446 (11 %) | 385 | 82 | 0 | 100 | 14 % | 89 % MISSING |
| `elite_score` | 283 (7 %) | 283 | 62 | 19 | 100 | 7 % | 93 % MISSING |
| `ml_score` | 226 (5 %) | 226 | 59 | 0.512 | 0.868 | 14 % | 95 % MISSING |

### 5c. `leaderboard` (n=1,004) and `systems` (n=126)

| Field | non-null | non-zero | distinct | mode share | Liveness |
|---|---|---|---|---|---|
| `leaderboard.fwd_wr` | 714 (71 %) | 500 | 163 | 30 % | **ALIVE** |
| `leaderboard.fwd_trades` | 1,004 | 720 | 131 | 28 % | **ALIVE** |
| `leaderboard.fwd_pf` | 465 (46 %) | 259 | 110 | 44 % | PARTIAL |
| `leaderboard.fwd_wins/losses` | 1,004 | 500 / 602 | 81 / 101 | 50 % / 40 % | PARTIAL |
| `leaderboard.bt_wr` | **28 (3 %)** | 28 | 28 | 4 % | **DEAD (97 % null)** |
| `leaderboard.bt_trades` | 1,004 | 29 | 30 | **97 % zero** | **FROZEN at 0** |
| `leaderboard.bt_pf` | 28 (3 %) | 28 | 27 | 7 % | **DEAD** |
| `leaderboard.decay` | **1 (0.1 %)** | 1 | 1 | 100 % | **DEAD** (single value -56.3) |
| `systems.win_rate` | 126 | 32 | 29 | **75 % zero** | **FROZEN** |
| `systems.profit_factor` | 35 (28 %) | 30 | 29 | 14 % | PARTIAL |
| `systems.closed_picks` | 126 | 56 | 43 | 56 % zero | PARTIAL |
| `backtest_vs_forward.bt_wr` | 28/255 | — | — | — | **DEAD (89 % null)** |
| `backtest_vs_forward.decay` | **0/255** | — | — | — | **DEAD** |

**Bottom line for "edge / Track / FWD WR / FWD N":** on the panel the user is looking at, **EDGE = 0/20 populated, Track = 2/20 (both 0 %), FWD WR = 2/20, FWD N = 20/20 but 90 % are 0.** These are not merely "some checks" — they are structurally empty for the current active universe because the active strategies have no closed history and `sym_track` is never populated for them. Only NEARUSDT/ES=F have any forward data.

---

## 6. Frozen / inconsistent-data evidence (exact rows & fields)

1. **Active PnL frozen**: all 20 `picks.active[].pnl_pct` = `0.0` except NEARUSDT (`2.74`). 7 rows have `current_price === entry_price` exactly (e.g. `BTCUSDT 66300.0 == 66300.0`, `XLE 64.96 == 64.96`).
2. **Price overlay dead**: `stock_prices.json` has 61 symbols (fresh 1.91 h) but only **1/2 active EQUITY** and **2/10 active ETF** symbols are present; FUTURES/COMMODITY/FOREX/Crypto pairs are absent → those rows cannot be marked.
3. **Performance tab counts inconsistent**: `performance.by_asset_class` active = `{CRYPTO:58, EQUITY:58, FOREX:20, FUTURES:1, BOND:3, ETF:15, SPORTS:1, COMMODITY:2}` = **158**, but `picks.active` has **20** and `summary.total_active_picks` = 20. Per-class deltas: CRYPTO 58 vs 3, EQUITY 58 vs 2, ETF 15 vs 10, BOND 3 vs 0. Closed sum 5,008 vs `summary.total_closed_picks` 16,126.
4. **Regime layer empty**: `regime_validation.active_regime_composition.with_regime_data = 0` of 263; `alignment_uplift` all 0/0 with `uplift_pp: null`; `regime` in `smart_picks_feed` is `NEUTRAL` only.
5. **Walk-forward empty**: `walkforward.by_class = {}` with `generated_at 2026-04-15` (213 d old).
6. **ML health**: `Claude Gainer ML` `updated_at 2026-05-25` (173 d) while `status: active`; `ML Crypto Predictor` `updated_at: ""`, `status: disabled`.
7. **Smart Picks dead**: `smart_picks_feed.total_scored = 0`, `crypto_scored = 0`, `non_crypto_scored = 0`, all pick arrays `[]`; `excluded_reasons` sum ≈ 190 candidates rejected; snapshot `last_batches[*].generated_at` newest = `2026-11-11T07:57` (3.4 d).
8. **Permutations degenerate**: all 6 pair/triple permutations have 0 active AND 0 closed; `solo_claude` 0/0, `solo_crypto_ml` 0/8; only `solo_alpha` has 25 active.
9. **`summary_picks.json` win-rate math is impossible** (file is 1.63 h fresh): `win_rate_pct` = BOND **127.8**, COMMODITY **240.2**, CRYPTO 98.3, EQUITY **162.4**, ETF **232.9**, FOREX **147.0**, FUTURES **363.9**, INDEX **1141.2**, because `wins + losses` exceeds `resolved` for those classes (e.g. INDEX 445 vs resolved 17; FUTURES 579 vs 61). Formula is `wins/(wins+losses)`-style while `resolved` counts a different cohort.
10. **`money_ready_verdict.json` (1.65 h fresh) has impossible/undefined risk stats** for CRYPTO: `mdd = 1.0009` (100.09 % — impossible drawdown >100 %), `cvar_95 = -96.0981`, `dsr_score = 0.0` alongside `n_ok: true`, `spa_p = 0.0` (exact zero p-value). Its `top_sleeves` list claims `WR 97.96 % / PF 120.0` and `WR 97.18 % / PF 56.7` — implausible sleeve stats.
11. **Non-standard JSON**: `money_ready_verdict.json` contains 2 `NaN` literals (`"dsr_score": NaN`) and `strategy_ic_analysis.json` contains 1 `Infinity` (`"pf": Infinity`). Browser `JSON.parse()` / `fetch().json()` **throws** on these tokens — those two payloads cannot be consumed by the page's own JS path.
12. **`audit_surface_truth.json` is 11.26 h old** although re-served at 14:37Z; the banner (`audit_surface_truth_banner.js`) prints `generated 2026-11-14T04:52:51Z` and headline "0/9 asset classes money-ready". Content is coherent with `money_ready_verdict` (0 money-ready) but not rebuilt with the 14:30 pipeline.
13. **`operator_review_today.json` is 79 d old** (generated 2026-08-27) yet `dashboard_enhancements.js` fetches it with `cache:'no-cache'` on every load.
14. **`pilot_forward_dashboard.json`** — the trust-hierarchy's #2 source — is 161.6 d old, and `strategy_admissibility.json` 161.6 d.
15. **`BOND.thresholdPass: true` with activeCount 0 / avgScore 0** in `asset_class_summary` → vacuous pass in the asset-quality strip.
16. **`tier2_proven_strategies`**: `signal_validation` reports `last_signal_at 2026-06-08`, `is_stale: true`, `status: dead`, while its `recent_picks[].closed_at` are `2026-11-14T13:55Z` — internal contradiction between the aggregate "last signal" and its own recent picks.
17. **`hyrotrader` page displays the April 8 snapshot as current**: it renders `account_snapshot` (`hyro_phase_label`, `equity_usdt 4929.34`, `cumulative_pnl_usdt -70.66`) with no date shown; `last_session_date` is not referenced in the page (string absent), so the 220-day staleness is invisible to the viewer. It does warn about `trading_days_logged=0` vs journal.
18. **`picks.recent_closed` and `picks.active_raw` carry 3377 `EXPIRED` rows with pnl 0**, i.e. the raw feed is append-only and never pruned. `db_health.json` independently reports `total_ghost_rows: 22947` (10 cohorts), with the top cohort `DOGEUSDT LONG pnl 1.3226 n=3569 distinct_entries=1` — classic duplicate/zombie rows.

---

## 7. Quantification

| Metric | Count |
|---|---|
| Total active picks shown (`picks.active`) | **20** |
| Total raw active rows retained (`picks.active_raw`) | 4,148 |
| Raw rows status OPEN | 691 (668 dated) |
| Raw rows status EXPIRED (never resolved) | **3,377** |
| Zombies (age > 30 d **and** `pnl_pct == 0.0`) in `active_raw` | **2,838** |
| `active_raw` rows with `pnl_pct == 0.0` | **3,832 / 4,148 (92 %)** |
| `active` rows with `pnl_pct == 0.0` | **19 / 20 (95 %)** |
| `recent_closed` rows with `pnl_pct == 0.0` | 11 / 3,500 (0.3 %) |
| `active_raw` `entry_price <= 0` | **85** |
| `active_raw` `current_price` null | **3,584 / 4,148 (86 %)** |
| `active_raw` `current_price < 0` | 0 |
| `active` current==entry (no mark) | 7 / 20 |
| `recent_closed` closed < 24 h | 10 / 3,500 (0.3 %) |
| `summary.total_closed_picks` vs `valid_closed_picks` | 16,126 vs 7,914 |
| `summary.zero_pnl_count` / `flat_count` | 66 / 66 (vs 3,832 zeros in active_raw — contradictory) |
| DB ghost rows (`db_health.json`) | **22,947** |
| Classes with impossible WR > 100 % (`summary_picks`) | **8 / 11** |
| Strategies audited OVERFIT_LIKELY (`anti_overfit_audit`) | **69 / 80** (6 EDGE_LIKELY_REAL, 5 UNDETERMINED) |
| `anti_overfit_audit.portfolio_diagnostics.reality_check` | **ERRORED** — `requires the 'arch' package` |

---

## 8. HyroTrader page — static template check

- `hyrotrader_picks.json` has **no `generated_at` / `updated_at` / timestamp field at all**. Only timestamps are `account_snapshot.last_session_date = "2026-04-08"` and `challenge.time_limit = "unlimited"`.
- Content is a **static template**: 7 picks, all `status: "pending_entry"`, all `entry_price/stop_loss/take_profit/pnl_pct = null`, all `opened_at/closed_at = null`, only `symbol_hint` (e.g. `BTCUSDT`, `label "Bitcoin — CCI Divergence"`, `confidence_pct 92`, `backtest_stats "+$1125 PnL, PF 2.15, 52% WR"`). Zero rows have a real `symbol`.
- `hyrotrader_journal.json` (222 B): `trades: []`, `daily_summary: []`.
- Two identical fetches 2 s apart returned the **same SHA-256** (`3deff64a…c43f`) and the HTTP headers show `last-modified 14:38:09Z`; the file is only re-copied by the hourly deploy, never regenerated.
- Live sub-feeds on the same page: `hyro_ml_pick_rankings.json` **1.74 h** (FRESH), `hyro_quan_bridge.json` **1.75 h** (FRESH), `hyro_live_strategies.json` no timestamp (static config), `hyro_pick_performance.json` **6.6 d STALE** (`total_signals 87`, 30-day lookback, 15 pending).
- Conclusion: **HyroTrader `picks`/journal/account blocks are a hand-maintained static template last substantively updated 2026-04-08 (220.7 d)**. The page's "Table 1 … generated server-side by GitHub Actions (hourly)" claim applies only to the QuanEngine bridge table, not to the picks/journal/account panel.

---

## 9. Exact URLs and commands

Page shell + assets:
```
curl -sS -L -o page_audit.html       https://findtorontoevents.ca/audit/
curl -sS -L -o page_hyrotrader.html  https://findtorontoevents.ca/audit/hyrotrader/
curl -sS -L -o js_enh.js             https://findtorontoevents.ca/audit/dashboard_enhancements.js
curl -sS -L -o js_banner.js          https://findtorontoevents.ca/audit/audit_surface_truth_banner.js
curl -sS -L -o js_post.js            https://findtorontoevents.ca/audit/ai_postmortem_helper.js
```
Data payloads (all `/audit/data/`): `dashboard_data.json`, `dashboard_payload.json`, `money_ready_verdict.json`, `pf_registry.json`, `anti_overfit_audit.json`, `audit_surface_truth.json`, `summary_picks.json`, `db_health.json`, `hyro_pick_performance.json`, `hyrotrader_picks.json`, `ma_strategy_leaderboard.json`, `pilot_forward_dashboard.json`, `ueps_picks.json`, `strong_signals.json`, `strategy_ic_analysis.json`, `stock_prices.json`, `regime_report.json`, `crypto_rsi5070_us_forward_status.json`, `claude_top_picks.json`(+phase2), `grok_top_picks.json`(+phase2), `kimi_top_3_live_picks.json`, `kimi_top_picks_phase2.json`, `mercury_top_picks.json`(+phase2), `ag_top_picks.json`(+phase2), `hyro_quan_bridge.json`, `cot_paper_pilot_status.json`, `claudes_test_dashboard.json`, `operator_review_today.json`, `top_n_rank_backtest.json`, `strategy_admissibility.json`, `hyro_live_strategies.json`, `hyro_ml_pick_rankings.json`, `hyrotrader_journal.json`.

Analysis snippets used (no file was `cat`ed; large JSON parsed with `orjson`/`json`):
```bash
# freshness
python3 - <<'PY'
import json,datetime as dt
now=dt.datetime.now(dt.timezone.utc)
o=json.load(open('dashboard_payload.json'))
d=dt.datetime.fromisoformat(o['generated_at'])
print((now-d).total_seconds()/3600)
PY

# per-class ages / zombies
python3 - <<'PY'
import orjson,statistics as st,datetime as dt
from collections import defaultdict
o=orjson.loads(open('dashboard_payload.json','rb').read())
now=dt.datetime.now(dt.timezone.utc)
# iterate picks.active / active_raw / recent_closed, parse timestamp,
# bucket by asset_class, count pnl_pct==0, current_price None, status
PY

# strict JSON-parse / NaN scan
python3 - <<'PY'
import glob,re,json
for p in glob.glob('*.json'):
    data=open(p,'rb').read()
    if data[:1] not in (b'{',b'['): continue
    try: json.loads(data)
    except Exception as e: print(p,e)
    print(p,len(re.findall(rb'(?<![\w"])-?(?:NaN|Infinity)(?![\w"])',data)))
PY
```
HTTP headers / static evidence:
```bash
curl -sSI https://findtorontoevents.ca/audit/data/hyrotrader_picks.json
curl -sS  https://findtorontoevents.ca/audit/data/hyrotrader_picks.json | sha256sum   # run twice
```
Key page code locations (in `raw/page_audit.html`):
- `buildVerifiedEdgeIndex()` @ ~380,460 — EDGE tiers from `picks.recent_closed`; thresholds GOLDEN combo n≥5/WR≥60/PF≥2.0 + strategy n≥30/WR≥50/PF≥1.3; VERIFIED strat n≥30/WR≥55/PF≥1.5.
- `getVerifiedTier(p)` @ ~387,075 — returns `null` when strategy/combo absent.
- `_effectiveTrackWrPick(p)` @ ~685,444 — Track fallback chain `sym_dir_fwd_*` → `sym_track_*` → `strat_fwd_wr`.
- `_picksTableInner()` @ ~690,337 — Time cell = `toEST(p.timestamp)`; Age cell = `p.age_hours`.
- `getSnapshots()` / `takeSnapshot()` @ ~1,383,048 — Score Tracker uses `localStorage` only, 10-min throttle.
- `renderAssetClassQuality()` — renders `thresholdPass` as green PASS regardless of `activeCount`.

---

## 10. Archive

Raw downloads: `2026-11-14/finpredict-v2_20261114-1602/raw/` — this subagent wrote 49 files (12 primary payloads + 23 page-referenced payloads + 3 hyrotrader feeds + 3 enhancement payloads + 3 JS assets + 5 page HTML fetches). The shared directory also contains peer/subagent files (`A_*`, `c_*`/`C_*`, `D_*`, `E_*`, `G_*`, `*.json.json`, `live_data_*`).
This report: `2026-11-14/finpredict-v2_20261114-1602/sub/B_dashboard_freshness.md`.

(Note: `raw/` also contains `A_*`, `C_*`/`c_*`, `D_*`, `E_*`, `G_*`, `*.json.json`, `live_data_*.json`, `symbol_stats.json` that this subagent did not create — they appear to be from concurrent peer/tool runs; none were used as evidence here.)

---

## UNVERIFIED markers

- `UNVERIFIED:` Browser-executed rendering. EDGE/Track blankness was established by replicating `buildVerifiedEdgeIndex()`/`getVerifiedTier()`/`_effectiveTrackWrPick()` in Python over the same payload, not by running the page in a headless browser. The conclusion is data-certain (0/20 qualifying stats) but the exact pixels were not observed.
- `UNVERIFIED:` Origin of the user's "FUTURES active pick with no date" observation. The only dated data contradicts it; may come from a different panel, a stale cached page, or a browser where the column preference hides `timestamp`.
- `UNVERIFIED:` Whether `strategy_tribunal_latest.json` 404 is newly broken or has been broken since the last deploy; only the current 404 was verified.
- `UNVERIFIED:` Server-side generator source for `performance.by_asset_class.active` (58/58/20/…) — the discrepancy with `picks.active` is certain, the code path that produces the inflated counts was not traced (repo source untouched per instructions).
- `UNVERIFIED:` Whether `summary_picks.json` is consumed by any live tab; it is present in `/audit/data/` and fresh, but no `fetch()` reference to it was found in `page_audit.html`/`dashboard_enhancements.js`.
- `UNVERIFIED:` The `hmm_regime.json` / `correlation_report.json` `/audit/data/` 404s are not page breaks because the page fetches those from `raw.githubusercontent.com`; the GitHub-side copies were not fetched/validated in this pass.
