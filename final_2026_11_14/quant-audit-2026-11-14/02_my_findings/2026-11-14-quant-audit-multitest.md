# Quant Audit — findtorontoevents.ca/audit + /audit/hyrotrader

**Audit date:** 2026-11-14 (Saturday), ~18:00Z
**Repo:** eltonaguiar/findtorontoevents_antigravity.ca @ `f6a4f476293` (branch `wiring`)
**Worktree:** `.worktrees/quant-audit-2026-11-14` (branch `audit/quant-multitest-2026-11-14`)

## Data sources used (all named, all timestamped)

| Source | What | Retrieved |
|---|---|---|
| `https://findtorontoevents.ca/audit/data/dashboard_data.json` | Primary audit payload, 24,954,459 bytes, `Last-Modified: Sat, 14 Nov 2026 16:23:48 GMT` | 18:00:21Z |
| `https://findtorontoevents.ca/audit/data/picks_now_live_pnl.json` | Live open-pick mark-to-market, `generated_at 2026-11-14T17:56:33Z` | 18:01Z |
| `https://findtorontoevents.ca/audit/hyrotrader/` (301 → trailing slash) | HyroTrader page, 92,985 bytes | 18:05Z |
| `https://findtorontoevents.ca/audit/data/hyrotrader_picks.json` / `_journal.json` / `hyro_quan_bridge.json` / `hyro_pick_performance.json` | Hyro page backing data | 18:06Z |
| GitHub REST `/actions/workflows` (365) + `/actions/workflows/{id}/runs?per_page=1` (365 calls) + `/actions/runs` (1,500) | Workflow inventory, last run per workflow, recent run outcomes | 18:00–18:04Z |
| Binance `api.binance.com/api/v3/ticker/price` | Crypto spot reference | 18:03Z |
| Frankfurter `api.frankfurter.app/latest` (ECB reference rates, date 2026-11-13) | FX reference | 18:03Z |
| CNBC quote service / Nasdaq API | Equity + ETF last sale | 18:04Z |

**Not used / not available:** MySQL databases (no credentials exercised in this audit), login-gated pages, GitHub warning-level annotations (run-level `/annotations` returns 404 for this repo; failure logs inspected instead).

---

## 1. Actions health — **FAIL**

365 workflows exist: **361 active, 4 disabled manually**. Last-run status per workflow (one API call per workflow, not inferred from a run window):

| Last-run conclusion | Count |
|---|---|
| success | 292 |
| failure | 30 |
| cancelled | 11 |
| no conclusion (in progress/queued) | 11 |
| skipped | 1 |
| **never run** | **20** |
| **total** | **365** |

**Staleness of last run:** 269 ≤1d · 40 1–7d · 12 7–30d · 5 30–90d · **19 >90d**.

**Recent-window failures:** 1,500 runs spanning 2026-11-14T09:01Z → 18:00Z → **77 failures (5.1%)**, 10 in progress at snapshot.

**Repeat offenders (failures in ~9h):** ALPHA ENGINE – Dynamic Runner 17 · ALPHA ENGINE FAST 17 · Sports endpoint smoke + Playwright 9 · CI Tests 7 · Market Beating System 4 · Signal Tracking 4.

**Concrete errors (from failed-run logs, not inferred):**
- `ALPHA ENGINE – Dynamic Runner` (run 43620447658, 17:19Z): `KeyError: 'LONG'` at `alpha_engine/scanner.py:2942` → `_forex_by_sym[s["symbol"]][sig_type].append(s)`. Crashes **hourly**; this is the main pick generator.
- `CI Tests` (run 43623195606, 17:49Z): `ValueError: Invalid frequency: ME` / `KeyError: 'ME'` in `tests/test_combined_book_sleeves.py` (pandas freq alias). Both Python 3.11 and 3.12 shards red.
- `Sports endpoint smoke + Playwright` (run 43620352180): fails at step **Install Playwright (chromium only)** — infrastructure, not product logic.

**30 workflows whose most recent run failed** (age of that run): DB Freshness Check 175.0d · MySQL Q-001 174.4d · ML Gatekeeper A/B Bootstrap 171.6d · DB Secret Scan 162.5d · Backup Restore Verification 30.5d · Algorithm Competition Refresh 6.3d (×2, incl. torontoevent mirror) · Stale Branch Cleanup 5.5d · Weekly score quartile spread 5.2d · HC Evaluator Parity 5.1d · Mermaid Test Deploy 1.7d · H-002 PEAD Collector 0.8d · Daily Prices yfinance Refresh 0.8d · Daily Price Refresh 0.7d · Verified pilot daily 0.5d · Mirror site 0.2d · robust-edge-miner 0.2d · 13 trading-bot/dispatch workflows 0.0–0.1d · Sports smoke 0.0d · Missed Opportunity Analyzer 0.0d · **CI Tests 0.0d**.

**20 active workflows that have never run:** Dynamic Runner Template, Battleground Mass Backtest, Clear Channel Command, Closed Picks Command, DB Credentials Test, Deploy FC API Hotfix, Deploy fc/api/.env, Deploy MOVIESHOWS3 Hotfix, Deploy Strategy Bundle, Fast Stocks Competition, Fix Ghost Cards, Meme Coin Scanner, MySQL Dedup Fix, REAL 2-HOUR CHALLENGE, **Resolver Step 5-6 Backfill**, **Resolver Step 7 active_picks_sync APPLY**, RL Agent PPO, Test Fast Variants, **Won PNL Contradiction Backfill**, WSL Runner Manager.

**Prediction-critical workflows that are disabled or ancient:** Forex Agent (disabled, last 164d) · Forex Smart Picks Scanner (disabled, last 163.8d) · AI Tournament Pipeline (disabled, 163.2d) · Pick Flow Snapshot Fast (173.8d) · Deploy Alpha Engine Dashboard (171.2d) · POC Picks Checkpoint (116.9d).

**Verdict:** FAIL. The two most important generation/resolution workflows (Alpha Engine dynamic runner, Resolver Step 5-7) are respectively crash-looping hourly and never executed. CI is red on both Python shards. The "warnings" requirement is **partially unverified**: GitHub annotation retrieval 404s; only failure-level logs were inspectable.

---

## 2. Active picks — **FAIL**

### 2.1 What the dashboard displays

`picks.active` contains **10 rows, all status OPEN**. There is no mutual-fund class anywhere in the payload (classes present: CRYPTO, EQUITY, FOREX, COMMODITY, FUTURES, ETF, BOND, SPORTS, PENNY_STOCK, MEME). **Mutual funds: NOT COVERED.**

Payload `generated_at 2026-11-14T16:15:51.726778+00:00`; self-reported `payload_lag_seconds: 3732.7` (62 min). Served file modified 16:23:48Z. Audit at 18:00Z.

| Class | Symbol | Dir | Entry | Current (displayed) | TP | SL | P/L % | Age h | Strategy | Source |
|---|---|---|---|---|---|---|---|---|---|---|
| CRYPTO | XRPUSDT | SHORT | 0.9635 | 0.9635 | 0.94065 | 0.97719 | 0.00 | 0.6 | kalshi_mtf_consensus | pm_kalshi_signals |
| CRYPTO | NEARUSDT | SHORT | 3.324 | 3.133 | 2.7106 | 3.6307 | +5.75 | 3.1 | tsmom_volscaled | tsmom_strategy |
| EQUITY | ADBE | LONG | 243.0800 | 243.08 | 262.5264 | 230.9260 | −0.00 | 3.5 | magic_formula_x_piotroski_x_acquirers | ueps |
| EQUITY | SNDL | LONG | 1.37 | 1.37 | 1.4796 | 1.3015 | 0.00 | 1.2 | regime_terminal | regime_terminal |
| FOREX | USDCAD=X | SHORT | 1.4269 | 1.4269 | 1.417913 | 1.434035 | −0.00 | 0.1 | non_crypto_consensus | non_crypto_consensus |
| FOREX | NZDUSD=X | LONG | 0.552517 | 0.552517 | 0.556937 | 0.549754 | −0.00 | 0.1 | non_crypto_consensus | non_crypto_consensus |
| COMMODITY | PA=F | SHORT | 1006.0 | 1006.0 | 975.82 | 1026.12 | 0.00 | 0.1 | commodity_carry_momo_double_sort | commodity_carry_momo |
| COMMODITY | SB=F | LONG | 18.41 | 18.41 | 18.9623 | 18.0418 | −0.00 | 0.1 | commodity_carry_momo_double_sort | commodity_carry_momo |
| FUTURES | ES=F | LONG | 7583.0 | 7583.0 | 8039.6429 | 7354.6786 | 0.00 | 1.2 | futures_connors_rsi2 | multi_asset_copytrader |
| ETF | XLF | LONG | 58.52 | 58.68 | 61.446 | 56.7644 | +0.27 | 46.1 | adx-trend-scout | kimi_riseoftheclaw |

### 2.2 Cross-reference against public market data

| Symbol | Dashboard current | Public reference | Source | Implied P/L | Match? |
|---|---|---|---|---|---|
| XRPUSDT | 0.9635 | **0.9585** | Binance ticker, 18:03Z | **+0.52%** | ✗ displayed 0.00 |
| NEARUSDT | 3.133 | **3.125** | Binance ticker, 18:03Z | **+5.99%** | ≈ (5.75 shown) |
| ADBE | 243.08 | **243.08** (Nov 13 close, +4.54) | CNBC / Nasdaq | 0.00% | ✓ |
| SNDL | 1.37 | **1.37** (Nov 13 close, −0.02) | CNBC | 0.00% | ✓ |
| XLF | 58.68 | **58.68** (Nov 13 close, +0.47) | CNBC | 0.00% | ✓ |
| USDCAD=X | 1.4269 | **1.4258** (ECB, 2026-11-13) | Frankfurter | +0.08% (short) | ≈ |
| NZDUSD=X | 0.552517 | **0.55322** (1/1.8076) | Frankfurter | +0.13% (long) | ≈ |
| ES=F | 7583.0 | — | — | — | **UNVERIFIED** |
| PA=F | 1006.0 | — | — | — | **UNVERIFIED** |
| SB=F | 18.41 | — | — | — | **UNVERIFIED** |

Futures could not be verified: Yahoo `query1/query2 /v8/finance/chart` returned HTTP 429 on every attempt; CNBC returned `last: None` for `@ES.21/@ES.26/@ESZ26/ES=F`; Stooq is JS-gated. **I am marking futures prices unverified rather than guessing.**

**Important mitigating fact:** 2026-11-14 is a **Saturday**. Six of the eight zero-P/L picks are US equities/FX/index futures whose reference price is Friday's close, so 0.00% is expected, not frozen. The two exceptions are genuine defects: **XRPUSDT shows 0.00% against a +0.52% live move** (current_price copied at entry for a 24/7 asset), and **XLF's "current" 58.68 is Friday's close while it is 46.1h old**.

### 2.3 Field completeness — "every field"

The 10 picks expose **189 distinct fields**. **60 are null/empty on all 10**, including:
`after_cost_net_per_trade`, `is_ac_survivor`, `wilson_lb_wr`, `history_wr`, `history_wr_bayes`, `history_avg_pnl`, `history_basis`, `history_trades`, `history_bonus`, `_metaWinProb`, `_metaGrade`, `forward_validated`, `exit_price`, `exit_reason`, `resolved_at`, `closed_at`, `safety_score`, `safety_reason`, `confluence_score`, `precursor_score`, `source_count`, `source_strategies`, `source_systems` (PM), `consensus_count`, `conviction_tier`, `hf_conviction_tier`, `beta_score`, `beta_breakdown`, `beta_qualified`, `leverage_factors`, `leverage_warning`, `ml_features_at_entry`, `volume`, `notes`, `paper_trade`, `strong`, `trader_label`, `strategy_top_symbol`, `strategy_top_symbol_pnl_pct`, `strategy_distinct_symbols`, `strategy_concentration_warning`, `strategy_concentration_penalty`.

**57 further fields are populated on fewer than 5 of 10 picks**, including `forward_wr`/`forward_trades` (2/10), `strat_fwd_pf` (2/10), `wf_oos_wr`/`wf_p_value`/`wf_verdict` (2/10), `pnl_pct` (2/10 non-zero), `has_conflict` (2/10), `regime` (1/10).

**Consequence:** the "accuracy" columns the dashboard advertises (forward WR, walk-forward p, after-cost net, Wilson lower bound) are **not populated for the live ledger**. There is nothing to audit per-pick.

### 2.4 Per-class accuracy (what is actually measurable)

`asset_class_summary.forwardWR` = **0.0** for CRYPTO, EQUITY, FOREX, COMMODITY, BOND; 0.059 FUTURES; 0.435 ETF. `thresholdPass=false` for 6 of 7 classes; BOND "passes" only because `activeCount=0` (vacuous pass).

Dashboard `performance` block (longer history, different denominator than `recent_closed`):

| Class | Active | Closed | Wins | Losses | WR % | Avg win % | Avg loss % | PF | Expectancy % |
|---|---|---|---|---|---|---|---|---|---|
| CRYPTO | 52 | 4,939 | 2,008 | 2,931 | 40.7 | 3.24 | 2.41 | 0.92 | −0.11 |
| EQUITY | 58 | 8 | 6 | 2 | 75.0 | 1.75 | 0.59 | 8.86 | +1.17 |
| FOREX | 13 | 82 | 30 | 52 | 36.6 | 0.86 | 1.03 | 0.48 | −0.34 |
| BOND | 3 | 3 | 1 | 2 | 33.3 | 0.13 | 1.17 | 0.06 | −0.74 |
| ETF | 15 | 8 | 3 | 5 | 37.5 | 2.37 | 1.87 | 0.76 | −0.28 |
| FUTURES | 1 | 0 | 0 | 0 | — | — | — | null | 0 |
| SPORTS | 1 | 0 | 0 | 0 | — | — | — | null | 0 |

**EQUITY's 75% / PF 8.86 is n=8** — statistically meaningless. Every class with a usable sample is below PF 1.0.

### 2.5 Stale entries flagged

`picks.active_raw` = **4,164 rows**:

| Status | n |
|---|---|
| EXPIRED | **3,378** |
| OPEN | 703 |
| SL_HIT | 57 |
| TP_HIT | 26 |

- **83 picks that already hit TP or SL are still sitting in the "active" feed.**
- 703 OPEN: 427 ≤1d, 275 1–7d, 1 7–30d; **583 have `pnl_pct` exactly 0.0**; **514 have `current_price` null/0**.
- 3,378 EXPIRED: **`closed_at` is empty on 100%**, P/L 0, `exit_reason` = `STALE (auto-expired >5764h)` / `>6011h` / `>3036h` … i.e. dead timestamps, never resolved.
- Max age in the active feed: **5,764.4 hours ≈ 240 days**.

### 2.6 The live ledger disagrees with the display by ~436×

`picks_now_live_pnl.json` (17:56:33Z):

- **`n_open` = 4,361**, `n_priced` = 3,900, **avg P/L −1.90%**, 1,460 positive vs **2,401 negative**, 461 with no price.
- By class: BOND 1,313 (1,249 priced, **−1.67%**, 316 pos / **914 neg**) · EQUITY 767 (648 priced, **−7.08%**, 142 pos / **501 neg**) · ETF 1,730 (1,527 priced, −0.68%) · FOREX 547 (476 priced, +0.64%) · COMMODITY 4 (0 priced) · **CRYPTO: absent**.
- 500 rows have `pnl_pct` exactly 0.0; 461 have no `current_price`; one `price_source` (`yfinance`) for all 3,900.
- Duplicate emission: EQUITY top symbols appear **139–140 times each** (PLTR, GOOGL, TTWO, NFLX, MU).
- BOND "class" is dominated by **preferred/high-yield/bond ETFs** (PFXF, PFFA, TFI, PFF, PZA, PFFD, LQD, VTEB, MUB, HYD, IEF, SCHP), all `direction: STRONG_BUY` — a mislabeled ETF book, not a bond book.
- Several rows show `current_price` identical to `entry_price` (WIP 36.99, GNMA 42.10, VTIP 48.51, PFFA 18.01, IGOV 39.58), consistent with prices not refreshed on those rows.

**Reading:** the public dashboard shows **10** active picks; the live tracker it publishes shows **4,361** open, averaging **−1.9%** with 62% of priced positions underwater. Those are not compatible descriptions of the same book.

**Verdict:** FAIL — active-pick accuracy is not auditable (60/189 fields empty, forward WR 0.0), 83 resolved picks remain in the active feed, 3,378 dead-timestamp rows, no mutual-fund coverage, and a 436× discrepancy between displayed and tracked open positions.

---

## 3. Frozen data — **FAIL**

### 3.1 Core payload is fresh
`last_dashboard_build 2026-11-14T16:20:31Z`, `last_alpha_scan 2026-11-14T15:39:17Z`, `age_hours 0.7`, `stale_warning false`. Hourly rebuild works.

### 3.2 P/L stuck at 0% / dead timestamps

| Symptom | Count | Evidence |
|---|---|---|
| `active_raw` rows with `pnl_pct == 0.0` | **3,856 / 4,164 (92.6%)** | 3,273 EXPIRED + 583 OPEN |
| OPEN picks with `current_price` null | **514** | never marked to market |
| EXPIRED with `closed_at` empty | **3,378 (100%)** | exit_reason "STALE (auto-expired >Nh)" |
| `picks_now` open rows with `pnl_pct == 0.0` | 500 | tracker, 17:56Z |
| `picks_now` rows with no price | 461 | tracker |
| Recent closed picks with P/L exactly 0 | 11 | negligible |

### 3.3 Fields that never update

**Empty containers in the live payload:** `macro_context`, `ta_baseline`, `bundles`, `audit_events`, `filter_events`, `picks.smart_picks` (**[]**), and `smart_picks_by_asset` is `[]` for all 7 classes, while `smart_picks_snapshot_summary` reports 53 picks / 64.2% WR. A summary exists with **zero underlying picks**.

**Stale sub-payloads:**

| Artifact | Timestamp | Age |
|---|---|---|
| `walkforward.by_class` | `2026-04-15T17:19:00Z`, `{}` | **213 days**, empty |
| `hyrotrader_picks.account_snapshot` | `last_session_date 2026-04-08`, `trading_days_logged: 0`, equity 4,929.34 / −70.66 | **220 days** |
| `hyrotrader_journal.json` | `trades: []`; page renders "No journal trades logged yet." | never |
| `hyro_pick_performance.json` | `2026-11-08T02:14:09Z` | 6 days (while `hyro_quan_bridge` is 17:51Z today) |

**Contradictory/frozen status fields:**
- `sidecar_promotion_status`: 3 strategies `status: "PROMOTED"` with **`n: 0, wr: 0.0, pf: 0.0`** — promoted with zero trades.
- `tier2_proven_strategies.signal_validation`: `n 73`, WR 8.2%, PF 0.12, `last_signal_at 2026-06-08`, `is_stale true`, `status dead` — still carded as "proven".
- `backtest_vs_forward`: **111 / 255 rows have `fwd_trades = 0` and `fwd_wr = null`**, yet **11 are labelled `SURVIVOR`**. Example: `connors_rsi2` bt_wr 68.8, bt_sharpe 1.78, **fwd_trades 0**, verdict SURVIVOR.
- `systems`: 126 total — **47 empty, 38 dead, 1 stale**, 30 active, 7 monitoring, 3 BLOCKED. **86 of 126 (68%) are not producing.**
- `performance_alerts` includes `DATA_STALE: wf_audit_signals hasn't produced a pick in 152h`.

**Verdict:** FAIL. The headline timestamp is current, but 92.6% of the active feed is 0% P/L, all 3,378 expired rows have empty `closed_at`, 60 active-pick fields are permanently empty, walkforward is 213 days stale, HyroTrader's account snapshot is 220 days old, and "PROMOTED"/"SURVIVOR" labels are attached to zero-trade entities.

---

## 4. Closed picks — **FAIL**

`picks.recent_closed` = 3,500 rows, `closed_at` 2026-02-21T07:08:50Z → 2026-11-14T15:39:18Z. Status: WON 1,459, LOST 2,030, CLOSED 11. Zero duplicate IDs.

### 4.1 Rolling realized performance

| Window | n | WON | LOST | WR % | Avg P/L % | Σ P/L % | PF |
|---|---|---|---|---|---|---|---|
| 1d | 125 | 34 | 91 | **27.2** | −1.129 | −141.1 | **0.441** |
| 7d | 412 | 146 | 266 | **35.4** | −0.355 | −146.4 | **0.782** |
| 30d | 1,323 | 515 | 808 | **38.9** | −0.335 | **−443.1** | **0.804** |
| 90d | 2,323 | 925 | 1,398 | 39.8 | −0.213 | −494.5 | 0.876 |
| 365d | 3,380 | 1,438 | 1,931 | 42.7 | −0.056 | −189.4 | 0.965 |

**Every window ≤365 days has negative expectancy.** The trend is deteriorating into the present (1d WR 27.2%), not improving.

### 4.2 Per class

| Class | All-time n | WR % | Avg P/L % | PF | 30d n | 30d WR % | 30d PF |
|---|---|---|---|---|---|---|---|
| CRYPTO | 1,966 | 39.4 | −0.360 | 0.801 | 1,078 | 38.3 | 0.803 |
| EQUITY | 738 | 47.1 | +0.323 | **1.154** | 104 | 42.3 | 0.842 |
| ETF | 567 | 44.1 | +0.040 | 1.036 | 83 | 37.3 | 0.698 |
| FOREX | 187 | 41.2 | −0.155 | 0.634 | 43 | 51.2 | **1.483** |
| BOND | 35 | 34.3 | −0.221 | 0.586 | 8 | 37.5 | 0.674 |
| COMMODITY | 7 | 28.6 | −0.598 | 0.604 | 7 | 28.6 | 0.604 |

Only EQUITY (all-time) and FOREX (30d, n=43) exceed PF 1.0; neither survives multiple-testing (§5).

### 4.3 By emitter

| source_system | n | WR % | Avg P/L % | PF |
|---|---|---|---|---|
| kimi_riseoftheclaw | 1,701 | 41.6 | −0.308 | 0.840 |
| luxalgo_filters | 1,271 | 43.0 | +0.185 | 1.131 |
| battleground | 122 | **56.6** | +0.226 | **1.756** |
| ml_bg_system_f | 90 | 22.2 | **−2.992** | 0.351 |
| alpha_engine | 85 | 38.8 | −0.082 | 0.926 |
| super_signals | 80 | 27.5 | +0.090 | 1.070 |
| multi_asset_copytrader | 39 | 53.8 | +0.162 | 1.696 |
| crypto_signal_engine | 30 | **3.3** | −0.966 | 0.184 |

**Two emitters produce 2,972 of 3,500 rows (84.9%).** Only **8 sources have n ≥ 20**; the other 106 strategies in the ledger cannot be evaluated.

### 4.4 Exit decomposition (shows where the money goes)

| Exit | n | Avg P/L % | Σ P/L % |
|---|---|---|---|
| TP_HIT | 881 | +4.016 | +3,538.2 |
| SL_HIT | 1,466 | −2.964 | **−4,345.1** |
| FORCE_CLOSED | 609 | +0.121 (median −1.986) | +73.7 |
| TIME_EXIT | 517 | +0.470 | +243.0 |
| UNKNOWN | 22 | −0.081 | −1.8 |

TP_HIT 4.02% vs SL_HIT −2.96% gives a nominal reward:risk of 1.36:1, but TP-vs-SL hit rate is 881/2,347 = **37.5%**, and the all-in PF is **0.80**. The system loses because it is stopped out substantially more often than it takes profit.

**Verdict:** FAIL — negative expectancy in every window, PF 0.44–0.97, and 85% of the sample comes from two emitters.

---

## 5. Verdict — **NOT profitable; the apparent edge is a multiple-testing / survivorship artifact**

### 5.1 Is anything statistically significant?

Global closed sample: **3,489 resolved, WR 41.8%** — one-sided binomial p against 50% = **1.00** (no evidence of an edge; the observed rate is *worse* than a coin flip).

Bonferroni threshold for 177 strategies (the dashboard's own `kill_switch.total_strategies`): **0.05 / 177 = 2.82e-4**.

| Emitter | n | WR % | p (one-sided) | Bonferroni |
|---|---|---|---|---|
| battleground | 122 | 56.6 | 0.087 | ✗ |
| multi_asset_copytrader | 39 | 53.8 | 0.375 | ✗ |
| luxalgo_filters | 1,271 | 43.0 | 1.00 | ✗ |
| kimi_riseoftheclaw | 1,701 | 41.6 | 1.00 | ✗ |
| alpha_engine | 85 | 38.8 | 0.985 | ✗ |
| super_signals | 80 | 27.5 | 1.00 | ✗ |
| ml_bg_system_f | 90 | 22.2 | 1.00 | ✗ |
| crypto_signal_engine | 30 | 3.3 | 1.00 | ✗ |

**Zero emitters survive Bonferroni. Zero even reach uncorrected p<0.05.** The best candidate (battleground, PF 1.756) carries p=0.087 on n=122 — short of the uncorrected 0.05 bar and 300× short of the corrected one.

**Multiple-testing arithmetic:** with 177 strategy slots, if none had edge, the probability that at least one appears significant at α=0.05 is **1 − 0.95¹⁷⁷ ≈ 99.99%**. The dashboard's existence of "top performers" is therefore *expected under the null*. With only 8 testable sources, expected false positives at α=0.05 = 0.4 — and we observe exactly one p<0.10 candidate, which is the expected count.

### 5.2 Survivorship — five independent biases, all confirmed in the data

1. **Attrition bias:** 3,378 expired picks are excluded from WON/LOST and carry P/L 0. They are neither wins nor losses in the realized stats, while the 1,466 SL_HIT rows are counted. Since expiry is what happens to trades that hit neither TP nor SL, this systematically removes the "slow bleed" outcomes from the denominator. **Direction of bias: favorable to the dashboard. Not removable from published JSON alone (unverified magnitude).**
2. **Label survivorship:** 11 strategies are labelled `SURVIVOR` with **zero forward trades**; 3 sidecars are `PROMOTED` with **n=0**; `signal_validation` is carded as "proven" while `status: dead`, WR 8.2%, PF 0.12, last signal 2026-06-08. The "proven" tier is not a forward-tested tier.
3. **Right-censoring / truncation:** the dashboard publishes a 3,500-row `recent_closed` slice while its own `policy_clean_n` for CRYPTO alone is **21,386**. Recent windows are reported on a truncation of the full book.
4. **Pseudo-replication:** 997 rows sit in 414 duplicate `(symbol, direction, day, strategy)` groups (max 9 copies). The effective sample size is materially below the headline n, so every p-value above is *optimistic*.
5. **Emitter concentration:** 84.9% of outcomes from 2 emitters; 141 symbols, BTC/ETH/AVAX/DOT/STX dominating. This is not 177 independent experiments — it is a handful of correlated bets counted many times.

### 5.3 The system's own gates agree

`money_ready_verdicts` (published by the site itself):

| Class | n_resolved | WR % | PF | Expectancy | DSR ok | WR ok | PF ok | Bootstrap CI | MDD |
|---|---|---|---|---|---|---|---|---|---|
| CRYPTO | 3,705 | 35.87 | 0.920 | −0.0590 | ✗ | ✗ | ✗ | (−0.0506, −0.0448) | 1.0009 |
| EQUITY | 250 | 59.2 | 0.939 | +0.0082 | ✓ | ✓ | ✗ | (−0.0027, +0.0089) | 0.9999 |
| FOREX | 612 | 32.19 | 0.660 | −0.0022 | ✗ | ✗ | ✗ | (−0.0053, +0.0031) | 0.8212 |
| COMMODITY | 229 | 40.17 | 1.026 | −0.0040 | ✗ | ✓ | ✗ | n/a | 0.1975 |
| FUTURES | 52 | 42.31 | 1.094 | +0.0103 | ✗ | ✓ | ✗ | n/a | 0.1665 |
| ETF | 45 | 2.22 | 0.022 | — | n/a | ✗ | ✗ | n/a | n/a |
| MEME | 10 | 10.0 | 0.023 | −0.0658 | ✗ | ✗ | ✗ | n/a | 0.4936 |
| BOND | 1 | 0.0 | 0.0 | — | n/a | ✗ | ✗ | n/a | n/a |
| PENNY_STOCK | 1 | 0.0 | 0.0 | — | n/a | ✗ | ✗ | n/a | n/a |

- CRYPTO: **the 95% bootstrap CI on expectancy is entirely negative** (−0.0506 to −0.0448), MDD 1.0009 (**100.09%**), `pf_ok=false`, `dsr_ok=false`. `n_bonferroni_pass 21 / 83 tested`, but `_fdr_gate_enforce: false` — the correction is computed and then not enforced.
- EQUITY is the only class with `dsr_ok=true`, on **n=250** and **`bonferroni_pass = 0`** of 1 tested; `pf_ok=false`.
- `readiness.by_class`: **`sizing_allowed: false` for every single class** (CRYPTO MONITORING PF 0.26/WR 42.2; BOND/COMMODITY BLOCKED; all `sample_tier: BELOW_T2`).
- `kill_switch`: 177 strategies, 56 evaluated, **42 killed (75% kill rate)**; its own `impact` block reports `wr_lift_pp +6.16` but `pf_lift −0.0223` (baseline PF 0.0314 → post 0.0091; both values look unit-scaled) — the filter improves win rate while lowering profit factor, i.e. it removes small losers and leaves the tail risk.

### 5.4 Answer

**Not genuinely profitable, and not statistically sound.** On 3,489 resolved trades the system wins 41.8% and earns negative expectancy in every window from 1 day to 365 days (30d: PF 0.80, −443 cumulative percentage points). No emitter survives Bonferroni; none reaches uncorrected p<0.05. The handful of green cells are explained by the mechanics of running 177 strategies across 365 workflows: with that many trials, ~99.99% probability of at least one α=0.05 "winner" under the null, and every published green cell here sits on n≤250 with `bonferroni_pass = 0`.

The positive-looking numbers on the site come from four reproducible mechanisms, not from alpha:
1. **Denominator manipulation** — 3,378 expired rows excluded from win/loss.
2. **Zero-trade labels** — SURVIVOR/PROMOTED attached to n=0 or dead entities.
3. **Cherry-picked sub-cohorts** — e.g. EQUITY 75% WR / PF 8.86 on n=8.
4. **Display filtering** — 10 "active" picks vs 4,361 open in the site's own tracker at −1.9%.

**What would change this verdict** (all absent today): forward-tested (not backtest-only) samples with n≥100 per strategy, Bonferroni/FDR *enforced* at the promotion gate rather than computed, expired outcomes resolved and counted, after-cost net P&L populated per pick, and a single ledger whose open count matches between dashboard and tracker.

---

## Limitations — explicitly unverified

- **Futures prices (ES=F, PA=F, SB=F):** no public source reachable (Yahoo 429, CNBC empty, Stooq JS-gated). Marked unverified, not guessed.
- **Warning-level GitHub annotations:** run-level `/annotations` returns 404 for this repo; only failure logs and job step results were inspected. Counts of *warnings* are therefore not reported.
- **Intraday accuracy for equities/ETFs/FX:** audit ran on a Saturday; references are Friday 2026-11-13 closes. Only spot crypto allowed true live comparison.
- **MySQL source tables** (`ejaguiar1_stocks`, `ejaguiar1_backtests`) were not queried; every figure here comes from the published JSON endpoints and the GitHub API.
- **Magnitude of attrition bias** (whether the 3,378 expired picks would have been net winners or losers) cannot be determined from published data.
- **`picks_now` EQUITY −7.08% average** is reported as published; the cause (genuine drawdown vs split-adjusted entry mismatch) was not established.
- **Mutual funds:** no such asset class exists in any payload — not covered, not evaluated.

---

## Appendix A — All 365 workflows, last run

Generated from GitHub REST `/actions/workflows` + one `/runs?per_page=1` call per workflow at 2026-11-14 ~18:04Z. Sorted by staleness, worst first. "NEVER" = workflow exists with 0 runs in its entire history.


| # | Age (days) | Last run (UTC) | Conclusion | State | Workflow | Path |
|---|---|---|---|---|---|---|
| 1 | NEVER | NEVER | never run | active | Battleground Mass Backtest | `.github/workflows/battleground-mass-backtest.yml` |
| 2 | NEVER | NEVER | never run | active | Clear Channel Command | `.github/workflows/clear-channel-command.yml` |
| 3 | NEVER | NEVER | never run | active | Closed Picks Command | `.github/workflows/closed-picks-command.yml` |
| 4 | NEVER | NEVER | never run | active | DB Credentials Test | `.github/workflows/db-credentials-test.yml` |
| 5 | NEVER | NEVER | never run | active | Deploy FC API Hotfix (3 domains) | `.github/workflows/deploy-fc-api-hotfix.yml` |
| 6 | NEVER | NEVER | never run | active | Deploy MOVIESHOWS3 Hotfix | `.github/workflows/deploy-movieshows3-hotfix.yml` |
| 7 | NEVER | NEVER | never run | active | Deploy Strategy Bundle | `.github/workflows/deploy_bundle.yml` |
| 8 | NEVER | NEVER | never run | active | Deploy fc/api/.env to GoDaddy (torontoevent.net) | `.github/workflows/deploy-fc-api-env-godaddy.yml` |
| 9 | NEVER | NEVER | never run | active | Dynamic Runner Template | `.github/workflows/_dynamic-runner-template.yml` |
| 10 | NEVER | NEVER | never run | active | Fast Stocks Competition  High Frequency Scanner | `.github/workflows/fast-stocks-competition.yml` |
| 11 | NEVER | NEVER | never run | active | Fix Ghost Cards & Thumbnails  All Sites | `.github/workflows/fix-ghost-cards.yml` |
| 12 | NEVER | NEVER | never run | active | Meme Coin Scanner  Fixed with Monitoring | `.github/workflows/meme-scanner-fixed.yml` |
| 13 | NEVER | NEVER | never run | active | MySQL Dedup Fix | `.github/workflows/mysql_dedup_fix.yml` |
| 14 | NEVER | NEVER | never run | active | REAL 2-HOUR CHALLENGE - Live Market Data | `.github/workflows/real_2hour_challenge.yml` |
| 15 | NEVER | NEVER | never run | active | RL Agent (PPO) Train & Predict | `.github/workflows/rl-agent-ppo.yml` |
| 16 | NEVER | NEVER | never run | active | Resolver Step 5-6 — at_raw_picks Backfill | `.github/workflows/resolver-step5-6-backfill.yml` |
| 17 | NEVER | NEVER | never run | active | Resolver Step 7 — active_picks_sync APPLY | `.github/workflows/resolver-step7-apply.yml` |
| 18 | NEVER | NEVER | never run | active | Test Fast Variants | `.github/workflows/test-fast.yml` |
| 19 | NEVER | NEVER | never run | active | WSL Runner Manager | `.github/workflows/wsl-runner-manager.yml` |
| 20 | NEVER | NEVER | never run | active | Won PNL Contradiction Backfill | `.github/workflows/won-pnl-contradiction-backfill.yml` |
| 21 | 175.4 | 2026-05-23T07:22:58Z | success | active | Dependency Graph | `dynamic/dependabot/update-graph` |
| 22 | 175.0 | 2026-05-23T18:28:36Z | failure | active | DB Freshness Check (Legacy Manual) | `.github/workflows/db-freshness-check.yml` |
| 23 | 174.4 | 2026-05-24T08:48:30Z | failure | active | MySQL Q-001 — Create picks table + sync from JSON | `.github/workflows/mysql-q001-sync.yml` |
| 24 | 173.8 | 2026-05-24T21:50:32Z | success | active | Pick Flow Snapshot (Fast) | `.github/workflows/pick-flow-snapshot-fast.yml` |
| 25 | 172.9 | 2026-05-25T21:12:04Z | success | active | Copilot cloud agent | `dynamic/copilot-swe-agent/copilot` |
| 26 | 171.6 | 2026-05-27T03:50:50Z | failure | active | ML Gatekeeper A/B Bootstrap | `.github/workflows/ml-gatekeeper-ab-bootstrap.yml` |
| 27 | 171.2 | 2026-05-27T12:08:23Z | success | active | Deploy Alpha Engine Dashboard | `.github/workflows/deploy-alpha-dashboard.yml` |
| 28 | 171.2 | 2026-05-27T12:08:23Z | success | active | Deploy FriendTracker | `.github/workflows/deploy-friendtracker.yml` |
| 29 | 171.2 | 2026-05-27T12:08:23Z | success | active | Fix Battleground Deployment | `.github/workflows/fix-battleground.yml` |
| 30 | 170.9 | 2026-05-27T20:09:22Z | success | active | strategy_performance.json no-regression guard | `.github/workflows/strategy-performance-no-regression.yml` |
| 31 | 164.1 | 2026-06-03T14:30:17Z | success | active | [torontoevent.net] Deploy Live Monitor APIs | `.github/workflows/torontoevent-deploy-live-monitor.yml` |
| 32 | 164.0 | 2026-06-03T18:29:34Z | success | disabled_manually | Forex Agent | `.github/workflows/forex-agent.yml` |
| 33 | 163.8 | 2026-06-03T22:41:44Z | success | disabled_manually | Forex Smart Picks Scanner | `.github/workflows/forex-smart-picks.yml` |
| 34 | 163.2 | 2026-06-04T13:12:44Z | success | disabled_manually | AI Tournament Pipeline — Daily Picks + DB Ingest | `.github/workflows/ai-tournament-pipeline.yml` |
| 35 | 162.6 | 2026-06-05T02:38:12Z | success | active | AI Leaderboard Refresh | `.github/workflows/ai-leaderboard-refresh.yml` |
| 36 | 162.5 | 2026-06-05T06:57:28Z | failure | active | DB Secret Scan | `.github/workflows/db-secret-scan.yml` |
| 37 | 161.4 | 2026-06-06T07:32:55Z | success | active | Battleground Mass Backtest (Part 2 - Babies) | `.github/workflows/battleground-mass-backtest-part2.yml` |
| 38 | 154.7 | 2026-06-13T01:39:52Z | success | disabled_manually | Real-Time Battle Test - Eliminate Losers, Optimize Winners | `.github/workflows/battle_test.yml` |
| 39 | 116.9 | 2026-07-20T21:25:17Z | success | active | POC Picks Checkpoint (2-week reminder) | `.github/workflows/poc-picks-checkpoint.yml` |
| 40 | 44.4 | 2026-10-01T07:25:25Z | success | active | UEPS Value Resolver Quarterly | `.github/workflows/value_resolver_quarterly.yml` |
| 41 | 41.5 | 2026-10-04T04:52:51Z | success | active | Discord Token Selftest | `.github/workflows/discord-token-selftest.yml` |
| 42 | 34.5 | 2026-10-11T06:00:39Z | success | active | Fetch New Movies & TV Shows (Manual) | `.github/workflows/fetch-movies.yml` |
| 43 | 34.5 | 2026-10-11T06:30:29Z | success | active | Kimi Fetch Movies/TV (Manual) | `.github/workflows/kimi-fetch-movies.yml` |
| 44 | 30.5 | 2026-10-15T06:04:51Z | failure | active | Backup Restore Verification | `.github/workflows/backup-verify.yml` |
| 45 | 27.7 | 2026-10-18T01:47:05Z | success | active | Deploy FavCreators Frontend (/fc/) | `.github/workflows/deploy-fc-frontend.yml` |
| 46 | 25.6 | 2026-10-20T03:03:30Z | success | active | UEPS Smoke Tests | `.github/workflows/ueps_smoke_tests.yml` |
| 47 | 22.8 | 2026-10-22T23:24:32Z | success | active | Quant Auditor (fast PR check) | `.github/workflows/quant-auditor-fast-pr.yml` |
| 48 | 22.8 | 2026-10-22T23:24:32Z | success | active | walkforward-gate | `.github/workflows/walkforward-gate.yml` |
| 49 | 22.0 | 2026-10-23T17:26:23Z | success | active | DB Password Leak Guard | `.github/workflows/db-password-leak-guard.yml` |
| 50 | 22.0 | 2026-10-23T17:26:23Z | success | active | masking-policy-lint | `.github/workflows/masking-policy-lint.yml` |
| 51 | 13.6 | 2026-11-01T04:01:08Z | success | active | ML Monthly Full Retrain | `.github/workflows/ml-monthly-retrain.yml` |
| 52 | 13.5 | 2026-11-01T06:13:31Z | success | active | Monthly DNA Tournament | `.github/workflows/monthly-tournament.yml` |
| 53 | 13.5 | 2026-11-01T06:29:57Z | success | active | Beta Portfolio Refresh (monthly) | `.github/workflows/beta-portfolio-refresh.yml` |
| 54 | 13.5 | 2026-11-01T07:05:33Z | success | active | Monthly Confidence Calibrator Refit (M-060) | `.github/workflows/monthly-calibrator-refit.yml` |
| 55 | 13.4 | 2026-11-01T09:07:09Z | success | active | Secret Rotation Reminder | `.github/workflows/secret-rotation-reminder.yml` |
| 56 | 13.2 | 2026-11-01T14:01:39Z | success | active | H-103 Forward Logger | `.github/workflows/h103-forward-logger.yml` |
| 57 | 6.8 | 2026-11-07T23:01:09Z | success | active | AI Hedge Fund Simulation — Weekly Pick Resolution | `.github/workflows/simulation-picks-resolver.yml` |
| 58 | 6.7 | 2026-11-08T00:27:51Z | success | active | Weekly Strategy Scorecard | `.github/workflows/weekly-strategy-scorecard.yml` |
| 59 | 6.7 | 2026-11-08T02:16:14Z | success | active | Mercury 2  Weekly Retrain | `.github/workflows/mercury2-retrain.yml` |
| 60 | 6.6 | 2026-11-08T03:06:55Z | success | active | [RiseOfTheClaw] Weekly Backtest + Elimination | `.github/workflows/riseoftheclaw-weekly-backtest.yml` |
| 61 | 6.6 | 2026-11-08T03:10:32Z | success | active | Taste Profile Scanner | `.github/workflows/taste-profile-scan.yml` |
| 62 | 6.6 | 2026-11-08T04:08:25Z | success | active | bt_backtest_trades cross-DB sync (DRAFT) | `.github/workflows/bt-backtest-trades-sync.yml` |
| 63 | 6.5 | 2026-11-08T06:08:19Z | success | active | Strategy Genome Evolution | `.github/workflows/genome-evolution.yml` |
| 64 | 6.5 | 2026-11-08T06:14:18Z | success | active | Weekly Exhaustive Stock Simulation | `.github/workflows/weekly-stock-simulation.yml` |
| 65 | 6.4 | 2026-11-08T08:13:08Z | success | active | Walk-Forward Backtest (Weekly) | `.github/workflows/walk-forward-backtest.yml` |
| 66 | 6.3 | 2026-11-08T10:03:12Z | failure | active | Algorithm Competition Refresh | `.github/workflows/algorithm-competition-refresh.yml` |
| 67 | 6.3 | 2026-11-08T10:07:08Z | failure | active | [torontoevent.net] Algorithm Competition Refresh | `.github/workflows/torontoevent-algorithm-refresh.yml` |
| 68 | 5.5 | 2026-11-09T06:05:03Z | success | active | Feature Stability Check (Weekly) | `.github/workflows/feature-stability-check.yml` |
| 69 | 5.5 | 2026-11-09T06:09:52Z | success | active | Weekly Real-Money Filter | `.github/workflows/weekly-filter.yml` |
| 70 | 5.5 | 2026-11-09T06:13:52Z | success | active | Alpha Engine - Weekly Validation Suite | `.github/workflows/alpha-weekly-validation.yml` |
| 71 | 5.5 | 2026-11-09T06:15:52Z | cancelled | active | UEPS Value Screener Weekly | `.github/workflows/value_screener_weekly.yml` |
| 72 | 5.5 | 2026-11-09T06:18:24Z | success | active | H-004 — Inventory Surprise + Roll Yield Backtest (real EIA data) | `.github/workflows/h004-backtest.yml` |
| 73 | 5.5 | 2026-11-09T06:39:00Z | failure | active | Stale Branch Cleanup | `.github/workflows/stale-branch-cleanup.yml` |
| 74 | 5.5 | 2026-11-09T06:42:16Z | success | active | Mutation analysis report | `.github/workflows/mutation-analysis-report.yml` |
| 75 | 5.5 | 2026-11-09T06:45:58Z | success | active | Sports Forensics Weekly | `.github/workflows/sports-forensics-weekly.yml` |
| 76 | 5.3 | 2026-11-09T11:02:48Z | success | active | Insider Trades Refresh | `.github/workflows/insider-trades-refresh.yml` |
| 77 | 5.2 | 2026-11-09T14:08:33Z | success | active | Deals & Freebies  Verify & Refresh | `.github/workflows/deals-refresh.yml` |
| 78 | 5.2 | 2026-11-09T14:18:23Z | failure | active | Weekly score quartile spread | `.github/workflows/weekly_score_quartile_spread.yml` |
| 79 | 5.1 | 2026-11-09T15:09:53Z | failure | active | HC Evaluator Parity Test | `.github/workflows/hc-parity.yml` |
| 80 | 2.1 | 2026-11-12T15:11:12Z | success | active | 📺 News Video Health Check | `.github/workflows/news-video-healthcheck.yml` |
| 81 | 1.7 | 2026-11-13T00:07:30Z | failure | active | Mermaid Test Deploy | `.github/workflows/mermaid-test-deploy.yml` |
| 82 | 1.4 | 2026-11-13T07:24:16Z | success | active | Edge decay monitor | `.github/workflows/edge-decay-check.yml` |
| 83 | 1.3 | 2026-11-13T11:07:35Z | success | active | 🧠 Smart Money Intelligence | `.github/workflows/smart-money-tracker.yml` |
| 84 | 1.3 | 2026-11-13T11:30:29Z | success | active | World-Class Intelligence  Daily Pipeline | `.github/workflows/worldclass-intelligence.yml` |
| 85 | 1.2 | 2026-11-13T12:02:49Z | success | active | Penny Stock Daily Picks | `.github/workflows/penny-stock-picks.yml` |
| 86 | 1.2 | 2026-11-13T12:13:46Z | success | active | 2hour-challenge | `.github/workflows/2hour_challenge.yml` |
| 87 | 1.2 | 2026-11-13T13:07:17Z | success | active | SEC EDGAR  Insider Trades & 13F Holdings | `.github/workflows/sec-edgar-fetch.yml` |
| 88 | 1.2 | 2026-11-13T13:35:30Z | success | active | DXY State Update | `.github/workflows/dxy-state-update.yml` |
| 89 | 1.2 | 2026-11-13T14:05:51Z | success | active | ETF & Bond Scanner | `.github/workflows/etf-bond-scanner.yml` |
| 90 | 1.2 | 2026-11-13T14:06:39Z | success | active | UEPS Swing Screener Daily | `.github/workflows/swing_screener_daily.yml` |
| 91 | 1.2 | 2026-11-13T14:10:30Z | success | active | Strategy Kill Tribunal | `.github/workflows/strategy-tribunal.yml` |
| 92 | 1.2 | 2026-11-13T14:10:59Z | success | active | Pre-Spike Early Warning | `.github/workflows/pre-spike-scan.yml` |
| 93 | 1.2 | 2026-11-13T14:12:02Z | success | active | Growth Stock Screener Daily | `.github/workflows/growth-stock-screener-daily.yml` |
| 94 | 1.1 | 2026-11-13T14:33:36Z | success | active | Bond Agent | `.github/workflows/bond-agent.yml` |
| 95 | 1.1 | 2026-11-13T14:36:13Z | success | active | ETF Agent | `.github/workflows/etf-agent.yml` |
| 96 | 1.1 | 2026-11-13T14:48:38Z | success | active | Penny Skyrocket Detector | `.github/workflows/penny-skyrocket-runner.yml` |
| 97 | 0.9 | 2026-11-13T19:16:31Z | success | active | ML Gatekeeper Train A/B (Phase D) | `.github/workflows/ml-gatekeeper-train-ab.yml` |
| 98 | 0.9 | 2026-11-13T19:30:37Z | success | active | Top Gainers Spike Scanner | `.github/workflows/top-gainers-scan.yml` |
| 99 | 0.9 | 2026-11-13T19:31:30Z | success | active | Traditional Test Portfolios (5-8) | `.github/workflows/traditional-test-portfolios.yml` |
| 100 | 0.9 | 2026-11-13T19:32:53Z | success | active | Non-Crypto A/B Portfolio Tracker | `.github/workflows/non-crypto-ab-test.yml` |
| 101 | 0.9 | 2026-11-13T20:01:18Z | success | active | Commodities Agent | `.github/workflows/commodities-agent.yml` |
| 102 | 0.9 | 2026-11-13T20:34:05Z | success | active | Daily Regime Detection + Position Sizing | `.github/workflows/regime-detector.yml` |
| 103 | 0.9 | 2026-11-13T20:45:27Z | success | active | World-Class Algorithm Pipeline | `.github/workflows/worldclass-pipeline.yml` |
| 104 | 0.9 | 2026-11-13T21:03:11Z | success | active | Equities & Stocks Agent | `.github/workflows/equities-agent.yml` |
| 105 | 0.9 | 2026-11-13T21:10:21Z | success | active | Populate alpha_macro Daily | `.github/workflows/populate-alpha-macro-daily.yml` |
| 106 | 0.8 | 2026-11-13T21:38:56Z | success | active | Daily Stock Picks Generator (STOCKSUNIFY) | `.github/workflows/stocks-daily.yml` |
| 107 | 0.8 | 2026-11-13T21:40:49Z | success | active | STOCKSUNIFY Daily Stock Picks | `.github/workflows/stocks-daily-stocksunify.yml` |
| 108 | 0.8 | 2026-11-13T22:01:32Z | success | active | AI-Model Portfolios — Daily EOD | `.github/workflows/ai-model-portfolios-daily.yml` |
| 109 | 0.8 | 2026-11-13T22:03:29Z | success | active | Alpha Engine  Daily Picks | `.github/workflows/alpha-engine-daily-picks.yml` |
| 110 | 0.8 | 2026-11-13T22:03:33Z | success | active | Futures Agent | `.github/workflows/futures-agent.yml` |
| 111 | 0.8 | 2026-11-13T22:05:28Z | success | active | Daily Picks Snapshot  Crypto, Forex & Stocks | `.github/workflows/daily-picks-snapshot.yml` |
| 112 | 0.8 | 2026-11-13T22:32:00Z | failure | active | H-002 PEAD Shadow Collector | `.github/workflows/pead-shadow-collector.yml` |
| 113 | 0.8 | 2026-11-13T22:32:28Z | success | active | ALPHA ENGINE - Equity 52wk High Breakout Scanner | `.github/workflows/alpha-equity-breakout.yml` |
| 114 | 0.8 | 2026-11-13T22:34:31Z | success | active | Daily Stock Data Refresh | `.github/workflows/daily-stock-refresh.yml` |
| 115 | 0.8 | 2026-11-13T22:40:47Z | failure | active | Daily Prices yfinance Refresh | `.github/workflows/daily-prices-yf-refresh.yml` |
| 116 | 0.8 | 2026-11-13T23:01:04Z | success | active | Daily Miracle DayTrades Scan | `.github/workflows/daily-miracle-scan.yml` |
| 117 | 0.8 | 2026-11-13T23:03:48Z | success | active | AI Tournament Price Tracker | `.github/workflows/ai-tournament-price-tracker.yml` |
| 118 | 0.8 | 2026-11-13T23:08:00Z | success | active | Track Quick Pick Portfolios | `.github/workflows/track-quick-picks.yml` |
| 119 | 0.8 | 2026-11-13T23:40:03Z | success | active | macd_rsi_m048 Shadow Generator | `.github/workflows/macd-rsi-m048-shadow-daily.yml` |
| 120 | 0.7 | 2026-11-14T00:05:09Z | success | active | Daily Runs | `.github/workflows/daily_runs.yml` |
| 121 | 0.7 | 2026-11-14T00:10:14Z | success | active | Statistical Rigor Validation - Thousands of Signals | `.github/workflows/statistical_validation.yml` |
| 122 | 0.7 | 2026-11-14T00:43:03Z | success | active | Edge stability refresh | `.github/workflows/edge-stability-refresh.yml` |
| 123 | 0.7 | 2026-11-14T00:44:15Z | success | active | Funding-Rate Archive Collector | `.github/workflows/funding-rate-collector.yml` |
| 124 | 0.7 | 2026-11-14T01:38:40Z | success | active | Edge stability refresh | `.github/workflows/edge-stability-daily.yml` |
| 125 | 0.7 | 2026-11-14T02:03:31Z | success | active | Cross-DB Consistency Guardian (M-005) | `.github/workflows/cross-db-consistency.yml` |
| 126 | 0.7 | 2026-11-14T02:05:57Z | failure | active | Daily Price Refresh | `.github/workflows/daily-price-refresh.yml` |
| 127 | 0.7 | 2026-11-14T02:07:53Z | success | active | Overnight Mutations | `.github/workflows/overnight-mutations.yml` |
| 128 | 0.7 | 2026-11-14T02:09:54Z | success | active | Refresh Creator Updates | `.github/workflows/refresh-creator-updates.yml` |
| 129 | 0.6 | 2026-11-14T02:34:26Z | success | active | Hierarchical Bayesian Edge Update | `.github/workflows/hierarchical-bayes.yml` |
| 130 | 0.6 | 2026-11-14T03:05:08Z | success | active | Schema Drift Audit | `.github/workflows/schema-drift-audit.yml` |
| 131 | 0.6 | 2026-11-14T03:06:30Z | success | active | Index All Creator Content | `.github/workflows/index-creator-content.yml` |
| 132 | 0.6 | 2026-11-14T03:08:08Z | success | active | Prune strategy_performance.json (30d) | `.github/workflows/prune-strategy-performance.yml` |
| 133 | 0.6 | 2026-11-14T03:08:47Z | cancelled | active | Swarm Pick Review (resolve + weekly + patterns + tournament promotion) | `.github/workflows/swarm-pick-review.yml` |
| 134 | 0.6 | 2026-11-14T03:33:00Z | success | active | Optimize Score Thresholds | `.github/workflows/optimize-score-thresholds.yml` |
| 135 | 0.6 | 2026-11-14T04:01:28Z | success | active | FINDTORONTOEVENTS.CA Database Backups | `.github/workflows/db-backup-email.yml` |
| 136 | 0.6 | 2026-11-14T04:03:02Z | cancelled | active | Blacklist Reconciler (cross-check vs live systems) | `.github/workflows/blacklist-reconciler.yml` |
| 137 | 0.6 | 2026-11-14T04:05:36Z | success | active | Pick Funnel — nightly | `.github/workflows/pick-funnel-nightly.yml` |
| 138 | 0.6 | 2026-11-14T04:06:50Z | success | active | Scrape events | `.github/workflows/scrape-events.yml` |
| 139 | 0.6 | 2026-11-14T04:07:22Z | success | active | swarm-janitor | `.github/workflows/swarm-janitor.yml` |
| 140 | 0.6 | 2026-11-14T04:09:09Z | cancelled | active | Secret Scan (M-043) | `.github/workflows/secret-scan.yml` |
| 141 | 0.6 | 2026-11-14T04:09:10Z | success | active | Backfill OHLCV Features | `.github/workflows/backfill-features.yml` |
| 142 | 0.6 | 2026-11-14T04:09:40Z | success | active | ML Battleground Daily Retrain | `.github/workflows/ml-battleground-retrain.yml` |
| 143 | 0.6 | 2026-11-14T04:09:48Z | success | active | MySQL Stale OPEN Picks Resolver | `.github/workflows/mysql-stale-picks-resolver.yml` |
| 144 | 0.6 | 2026-11-14T04:11:24Z | cancelled | active | Sign-Coherence Gate | `.github/workflows/sign-coherence-gate.yml` |
| 145 | 0.6 | 2026-11-14T04:12:31Z | success | active | Deploy findtorontoevents.ca core site | `.github/workflows/deploy-fte-index.yml` |
| 146 | 0.6 | 2026-11-14T04:12:31Z | success | active | Deploy findtorontoevents.ca next/events.json | `.github/workflows/deploy-fte-events-json.yml` |
| 147 | 0.6 | 2026-11-14T04:32:31Z | success | active | AI Leaderboard Freshness (daily FTP + data rebuild) | `.github/workflows/ai-leaderboard-freshness.yml` |
| 148 | 0.6 | 2026-11-14T04:33:06Z | success | active | Incidents + Enhancements — Nightly Page Render | `.github/workflows/incidents-enhancements-nightly.yml` |
| 149 | 0.5 | 2026-11-14T05:03:36Z | success | active | DNA Mutation Cycle | `.github/workflows/dna-mutation-cycle.yml` |
| 150 | 0.5 | 2026-11-14T05:07:15Z | success | active | Gate Config Emit | `.github/workflows/gate-config-emit.yml` |
| 151 | 0.5 | 2026-11-14T05:34:36Z | success | active | A/B Analysis + Zero-PnL Audit | `.github/workflows/ab_analysis.yml` |
| 152 | 0.5 | 2026-11-14T05:34:40Z | success | active | GHA stale workflows audit | `.github/workflows/gha-stale-workflows-audit.yml` |
| 153 | 0.5 | 2026-11-14T05:34:57Z | success | active | Mutation Lifecycle Runner | `.github/workflows/mutation-lifecycle-runner.yml` |
| 154 | 0.5 | 2026-11-14T05:42:58Z | success | active | Hyro Quan Bridge Regen | `.github/workflows/hyro-bridge-regen.yml` |
| 155 | 0.5 | 2026-11-14T06:05:06Z | success | active | DB Sync: findtorontoevents.ca  torontoevent.net | `.github/workflows/db-sync-to-mirror.yml` |
| 156 | 0.5 | 2026-11-14T06:06:15Z | success | active | Cross-DB Strategy Consistency Audit | `.github/workflows/cross-db-audit.yml` |
| 157 | 0.5 | 2026-11-14T06:10:25Z | success | active | Research Orchestrator (weekly) | `.github/workflows/research-orchestrator.yml` |
| 158 | 0.5 | 2026-11-14T06:11:20Z | success | active | Decile Separation Test | `.github/workflows/decile-separation-test.yml` |
| 159 | 0.5 | 2026-11-14T06:17:28Z | success | active | SPY 20d Return Refresh | `.github/workflows/spy-data-refresh.yml` |
| 160 | 0.5 | 2026-11-14T06:17:33Z | success | active | Incubator Pipeline  Strategy Graduation | `.github/workflows/incubator-pipeline.yml` |
| 161 | 0.5 | 2026-11-14T06:22:49Z | success | active | Money-Ready Verdict Snapshot | `.github/workflows/money-ready-snapshot.yml` |
| 162 | 0.5 | 2026-11-14T06:24:27Z | failure | active | Verified pilot daily | `.github/workflows/verified-pilot-daily.yml` |
| 163 | 0.5 | 2026-11-14T06:25:04Z | success | active | Quant Auditor (deep nightly) | `.github/workflows/quant-auditor-deep-nightly.yml` |
| 164 | 0.5 | 2026-11-14T06:38:15Z | success | active | Validate HF by asset class | `.github/workflows/validate-hf-asset-class.yml` |
| 165 | 0.5 | 2026-11-14T07:00:41Z | success | active | Refresh Movies Databases (50webs + GoDaddy) | `.github/workflows/fetch-movies-v3.yml` |
| 166 | 0.5 | 2026-11-14T07:03:08Z | cancelled | active | rsi5070 Forward-Test Snapshot (Daily) | `.github/workflows/rsi5070-forward-snapshot.yml` |
| 167 | 0.5 | 2026-11-14T07:04:23Z | success | active | Goldmine Tracker - Archive & Maintain | `.github/workflows/goldmine-tracker.yml` |
| 168 | 0.5 | 2026-11-14T07:05:45Z | success | active | [torontoevent.net] Goldmine Tracker - Archive & Maintain | `.github/workflows/torontoevent-goldmine-tracker.yml` |
| 169 | 0.5 | 2026-11-14T07:08:51Z | success | active | Benchmark Comparison  Daily | `.github/workflows/benchmark-comparison.yml` |
| 170 | 0.5 | 2026-11-14T07:11:02Z | cancelled | active | Operator Review — Manual Candidates daily snapshot | `.github/workflows/operator-review-today.yml` |
| 171 | 0.4 | 2026-11-14T07:34:22Z | success | active | Daily Per-Class Scrutiny Engine | `.github/workflows/daily-scrutiny-engine.yml` |
| 172 | 0.4 | 2026-11-14T07:41:38Z | success | active | Audit Frontend Manifest | `.github/workflows/audit-frontend-manifest.yml` |
| 173 | 0.4 | 2026-11-14T08:03:16Z | success | active | Strategy Health Report | `.github/workflows/strategy-health-report.yml` |
| 174 | 0.4 | 2026-11-14T08:04:38Z | success | active | Auto-Shutdown Source Monitor | `.github/workflows/auto-shutdown-monitor.yml` |
| 175 | 0.4 | 2026-11-14T08:09:23Z | success | active | Automated Reporting | `.github/workflows/automated-reporting.yml` |
| 176 | 0.4 | 2026-11-14T08:12:32Z | success | active | DB Sync: Bi-directional User Data | `.github/workflows/db-sync-bidirectional.yml` |
| 177 | 0.4 | 2026-11-14T09:15:35Z | success | active | Schema Drift Watchdog | `.github/workflows/schema-drift-watchdog.yml` |
| 178 | 0.4 | 2026-11-14T09:34:21Z | success | active | Auto-Retire — Daily Bleeder Check | `.github/workflows/auto-retire-daily.yml` |
| 179 | 0.2 | 2026-11-14T12:00:52Z | success | active | Social Media Algo Trader Investigation | `.github/workflows/social_investigation.yml` |
| 180 | 0.2 | 2026-11-14T12:03:01Z | success | active | Refresh Top Movies Data | `.github/workflows/refresh-top-movies.yml` |
| 181 | 0.2 | 2026-11-14T12:03:40Z | success | active | Picks NOW Refresh | `.github/workflows/picks-now-refresh.yml` |
| 182 | 0.2 | 2026-11-14T12:03:51Z | success | active | Deploy MOVIESHOWS2 + MOVIESHOWS3 (All 3 Domains) | `.github/workflows/deploy-movieshows-all.yml` |
| 183 | 0.2 | 2026-11-14T12:05:00Z | success | active | FRED Macro Refresh | `.github/workflows/fred-macro-refresh.yml` |
| 184 | 0.2 | 2026-11-14T12:05:04Z | success | active | Crypto Winner Scanner  Auto Scan | `.github/workflows/crypto-winner-scan.yml` |
| 185 | 0.2 | 2026-11-14T12:06:12Z | success | active | Data Pipeline Reliability Test | `.github/workflows/data-pipeline-test.yml` |
| 186 | 0.2 | 2026-11-14T12:06:36Z | success | active | Buy Now Analysis & Tracking | `.github/workflows/buy-now-analysis.yml` |
| 187 | 0.2 | 2026-11-14T12:07:02Z | success | active | Audit Impact Tracker | `.github/workflows/audit-impact-tracker.yml` |
| 188 | 0.2 | 2026-11-14T12:08:14Z | success | active | CFTC COT Refresh | `.github/workflows/cftc-cot-refresh.yml` |
| 189 | 0.2 | 2026-11-14T12:09:32Z | success | active | Forward-Test New Strategies Tracker | `.github/workflows/forward-test-new-strategies.yml` |
| 190 | 0.2 | 2026-11-14T12:09:38Z | success | active | Honest Kill Switch | `.github/workflows/honest-kill-switch.yml` |
| 191 | 0.2 | 2026-11-14T12:10:05Z | success | active | ML Feedback Loop | `.github/workflows/ml-feedback-loop.yml` |
| 192 | 0.2 | 2026-11-14T12:11:02Z | failure | active | Mirror: findtorontoevents.ca  torontoevent.net | `.github/workflows/mirror-site.yml` |
| 193 | 0.2 | 2026-11-14T12:12:45Z | success | active | gha-summary-report | `.github/workflows/gha-summary-report.yml` |
| 194 | 0.2 | 2026-11-14T12:14:59Z | success | active | ML Model Auto-Training | `.github/workflows/ml-model-autotraining.yml` |
| 195 | 0.2 | 2026-11-14T12:16:26Z | (none) | active | Discord Bot  Persistent | `.github/workflows/discord-bot.yml` |
| 196 | 0.2 | 2026-11-14T12:16:43Z | success | active | ALPHA ENGINE - ETF Emitter | `.github/workflows/alpha-engine-etf.yml` |
| 197 | 0.2 | 2026-11-14T12:18:50Z | success | active | Cross-Asset Correlation Monitor | `.github/workflows/correlation-monitor.yml` |
| 198 | 0.2 | 2026-11-14T12:20:21Z | success | active | ALPHA ENGINE - Adaptive Trust Tuner | `.github/workflows/adaptive-trust-tuner.yml` |
| 199 | 0.2 | 2026-11-14T12:26:25Z | success | active | ML Feedback Retrain  Learn from Closed Trades | `.github/workflows/ml-feedback-retrain.yml` |
| 200 | 0.2 | 2026-11-14T12:43:13Z | failure | active | robust-edge-miner | `.github/workflows/robust-edge-miner.yml` |
| 201 | 0.2 | 2026-11-14T13:00:49Z | cancelled | active | Academic Strategies Daily | `.github/workflows/academic-strategies-daily.yml` |
| 202 | 0.2 | 2026-11-14T13:05:56Z | success | active | ML Model Staleness Watchdog | `.github/workflows/ml-staleness-watchdog.yml` |
| 203 | 0.2 | 2026-11-14T13:10:49Z | cancelled | active | STOCKSUNIFY2 daily-stocks pull | `.github/workflows/stocksunify2-pull.yml` |
| 204 | 0.2 | 2026-11-14T13:19:07Z | success | active | Pick Data Quality Gate | `.github/workflows/pick-data-quality-gate.yml` |
| 205 | 0.2 | 2026-11-14T13:31:14Z | success | active | paper-pilot-daily | `.github/workflows/paper-pilot-daily.yml` |
| 206 | 0.2 | 2026-11-14T13:35:03Z | success | active | Asset Class Freshness Watchdog | `.github/workflows/asset-class-freshness-watchdog.yml` |
| 207 | 0.2 | 2026-11-14T13:37:50Z | success | active | Hyro daily (filter + backtest) | `.github/workflows/hyro-daily.yml` |
| 208 | 0.2 | 2026-11-14T13:44:10Z | success | active | Strategy Perf By Class Rebuild | `.github/workflows/strategy-perf-by-class-rebuild.yml` |
| 209 | 0.2 | 2026-11-14T14:07:41Z | success | active | Sports Prediction Market Sync | `.github/workflows/sports-prediction-market-sync.yml` |
| 210 | 0.1 | 2026-11-14T15:03:51Z | success | active | Mutation Lab  Strategy Evolution Pipeline | `.github/workflows/mutation-lab.yml` |
| 211 | 0.1 | 2026-11-14T15:04:45Z | success | active | Sports Betting  Odds Refresh & Auto-Settle | `.github/workflows/sports-betting-refresh.yml` |
| 212 | 0.1 | 2026-11-14T16:00:37Z | success | active | [torontoevent.net] Run Backtests & Deploy Dashboards (ROOCODE) | `.github/workflows/torontoevent-backtest-and-deploy-ROOCODE.yml` |
| 213 | 0.1 | 2026-11-14T16:00:41Z | success | active | MOMENTUM SCALP SCANNER - Dynamic Universe Expansion | `.github/workflows/momentum-scanner.yml` |
| 214 | 0.1 | 2026-11-14T16:01:06Z | failure | active | Autonomous Trading Bot - Runs Automatically Every 4 Hours | `.github/workflows/autonomous_trading.yml` |
| 215 | 0.1 | 2026-11-14T16:01:33Z | failure | active | Signal Tracking & Validation - Beat the Market | `.github/workflows/signal_tracking.yml` |
| 216 | 0.1 | 2026-11-14T16:02:48Z | failure | active | Self-Optimizing Trading Bot - Auto-Validates & Tweaks | `.github/workflows/self_optimizing_trading.yml` |
| 217 | 0.1 | 2026-11-14T16:02:55Z | success | active | TradingView Strategy Scanner | `.github/workflows/tv-strategy-scanner.yml` |
| 218 | 0.1 | 2026-11-14T16:02:56Z | success | active | Proven Strategies Scanner | `.github/workflows/proven-strategies-scanner.yml` |
| 219 | 0.1 | 2026-11-14T16:03:05Z | failure | active | Crypto Picks Dispatch | `.github/workflows/picks_dispatch.yml` |
| 220 | 0.1 | 2026-11-14T16:03:06Z | success | active | Check Streamer Live Status | `.github/workflows/check-streamer-status.yml` |
| 221 | 0.1 | 2026-11-14T16:04:39Z | success | active | Strategy Health Monitor | `.github/workflows/strategy-health-monitor.yml` |
| 222 | 0.1 | 2026-11-14T16:04:56Z | failure | active | Live Trading Bot | `.github/workflows/live_trading.yml` |
| 223 | 0.1 | 2026-11-14T16:05:37Z | success | active | KIMI Goldmine Data Collection | `.github/workflows/kimi-goldmine-collector.yml` |
| 224 | 0.1 | 2026-11-14T16:05:40Z | success | active | KIMI_FEB172026 - Live Trading System | `.github/workflows/kimi-feb172026-live.yml` |
| 225 | 0.1 | 2026-11-14T16:06:19Z | success | active | Daily Feed Summary | `.github/workflows/daily-feed-summary.yml` |
| 226 | 0.1 | 2026-11-14T16:06:20Z | success | active | [torontoevent.net] Run Backtests & Deploy Dashboards | `.github/workflows/torontoevent-backtest-and-deploy.yml` |
| 227 | 0.1 | 2026-11-14T16:06:22Z | success | active | Discord Channel Heartbeat | `.github/workflows/discord-heartbeat.yml` |
| 228 | 0.1 | 2026-11-14T16:06:32Z | failure | active | Live Trading Bot - Canada Edition | `.github/workflows/live_trading_canada.yml` |
| 229 | 0.1 | 2026-11-14T16:06:37Z | failure | active | Live Trading Bot - Canada Edition (FREE Data) | `.github/workflows/live_trading_canada_free.yml` |
| 230 | 0.1 | 2026-11-14T16:06:42Z | failure | active | Forward Test - Strategy Validation | `.github/workflows/forward_test.yml` |
| 231 | 0.1 | 2026-11-14T16:07:11Z | success | active | Parquet Data Ingestion | `.github/workflows/parquet-ingest.yml` |
| 232 | 0.1 | 2026-11-14T16:07:19Z | failure | active | Market Beating System - Crypto & Forex Priority | `.github/workflows/market_beating.yml` |
| 233 | 0.1 | 2026-11-14T16:08:30Z | success | active | Backfill Missing Audit Trail Sources | `.github/workflows/backfill.yml` |
| 234 | 0.1 | 2026-11-14T16:08:36Z | success | active | Forward Signal Scanner | `.github/workflows/forward-signal-scanner.yml` |
| 235 | 0.1 | 2026-11-14T16:09:15Z | success | active | What Worked Active Picks Insights | `.github/workflows/what-worked-insights.yml` |
| 236 | 0.1 | 2026-11-14T16:10:03Z | success | active | Run Backtests & Deploy Dashboards | `.github/workflows/backtest-and-deploy.yml` |
| 237 | 0.1 | 2026-11-14T16:10:15Z | failure | active | ALPHA ENGINE - Live Autonomous Scanner | `.github/workflows/alpha-engine-live.yml` |
| 238 | 0.1 | 2026-11-14T16:10:47Z | success | active | FC-CRYPTO PRO Top Actionable Picks | `.github/workflows/fc-crypto-pro.yml` |
| 239 | 0.1 | 2026-11-14T16:10:51Z | success | active | Spike Scanner | `.github/workflows/spike-scanner.yml` |
| 240 | 0.1 | 2026-11-14T16:11:08Z | success | active | System Health Check | `.github/workflows/system-health-check.yml` |
| 241 | 0.1 | 2026-11-14T16:12:25Z | success | active | ALPHA ENGINE - Trend Catcher (4H Adaptive) | `.github/workflows/alpha-trend-catcher.yml` |
| 242 | 0.1 | 2026-11-14T16:12:25Z | success | active | Sidecar Status Markdown Update | `.github/workflows/sidecar-status-update.yml` |
| 243 | 0.1 | 2026-11-14T16:14:52Z | (none) | active | DNA Strategy Pipeline | `.github/workflows/dna_strategy_pipeline.yml` |
| 244 | 0.1 | 2026-11-14T16:15:47Z | success | active | Crypto Test Portfolios | `.github/workflows/crypto-test-portfolios.yml` |
| 245 | 0.1 | 2026-11-14T16:17:14Z | success | active | Prediction Market Agents | `.github/workflows/prediction-market-agents.yml` |
| 246 | 0.1 | 2026-11-14T16:17:20Z | success | active | Strategy Forward Tester | `.github/workflows/strategy-forward-tester.yml` |
| 247 | 0.1 | 2026-11-14T16:18:40Z | success | active | Deploy Vetted Master-Picks | `.github/workflows/deploy-vetted-picks.yml` |
| 248 | 0.1 | 2026-11-14T16:18:53Z | success | active | ALPHA ENGINE - Incubator Strategies | `.github/workflows/incubator-strategies.yml` |
| 249 | 0.1 | 2026-11-14T16:18:57Z | success | active | Rapid Validation Engine | `.github/workflows/rapid-validation-CLAUDECODE_Feb152026.yml` |
| 250 | 0.1 | 2026-11-14T16:19:22Z | success | active | Claude Code Gainer ML Tracker | `.github/workflows/claude-gainer-tracker.yml` |
| 251 | 0.1 | 2026-11-14T16:19:22Z | success | active | UEPS Pick Runner | `.github/workflows/ueps-pick-runner.yml` |
| 252 | 0.1 | 2026-11-14T16:20:47Z | success | active | Enhanced ML Crypto Train & Predict | `.github/workflows/enhanced-ml-crypto.yml` |
| 253 | 0.1 | 2026-11-14T16:22:50Z | success | active | Audit Drift Telemetry | `.github/workflows/audit-drift-telemetry.yml` |
| 254 | 0.1 | 2026-11-14T16:22:50Z | success | active | Money-Ready Registry Gate | `.github/workflows/money-ready-registry-gate.yml` |
| 255 | 0.1 | 2026-11-14T16:23:04Z | success | active | crypto-ohlcv refresh | `.github/workflows/crypto-ohlcv-refresh.yml` |
| 256 | 0.1 | 2026-11-14T16:24:17Z | success | active | Daily Top-Picks Filter | `.github/workflows/daily-top-picks-filter.yml` |
| 257 | 0.1 | 2026-11-14T16:26:31Z | success | active | ML Strategy Reviver Bridge & Standalone | `.github/workflows/ml-strategy-reviver.yml` |
| 258 | 0.1 | 2026-11-14T16:28:54Z | success | active | Feature Signals — Non-LLM Emitters | `.github/workflows/feature-signals-hourly.yml` |
| 259 | 0.1 | 2026-11-14T16:29:30Z | success | active | LIVE SPIKE TRADING - Autonomous Crypto Monitor | `.github/workflows/live_spike_trading.yml` |
| 260 | 0.1 | 2026-11-14T16:29:43Z | success | active | ALPHA  Verify Predictions | `.github/workflows/alpha-verify-predictions.yml` |
| 261 | 0.1 | 2026-11-14T16:30:34Z | success | active | Master-Picks Health Score | `.github/workflows/master-picks-health.yml` |
| 262 | 0.1 | 2026-11-14T16:31:07Z | success | active | Social Media Prediction Tracker | `.github/workflows/social-prediction-tracker.yml` |
| 263 | 0.1 | 2026-11-14T16:31:25Z | success | active | ML Forward Test 1745 Models | `.github/workflows/ml-forward-test.yml` |
| 264 | 0.1 | 2026-11-14T16:39:48Z | success | active | Continuous Improvement Monitor | `.github/workflows/continuous-improvement-monitor.yml` |
| 265 | 0.1 | 2026-11-14T16:39:55Z | success | active | Dynamic Universe Scanner | `.github/workflows/dynamic-universe.yml` |
| 266 | 0.1 | 2026-11-14T16:43:06Z | success | active | Copy Trader Portfolio Tracker | `.github/workflows/copytrader-tracker.yml` |
| 267 | 0.0 | 2026-11-14T16:48:55Z | success | active | CRYPTO SMART PICKS - Portfolio A/B/C/D Scanner | `.github/workflows/crypto-smart-picks.yml` |
| 268 | 0.0 | 2026-11-14T16:55:53Z | success | active | ALPHA ENGINE - Universe Expander | `.github/workflows/universe-expander.yml` |
| 269 | 0.0 | 2026-11-14T17:01:12Z | success | active | Forward Trade Tracking v2 | `.github/workflows/forward-tracking-v2.yml` |
| 270 | 0.0 | 2026-11-14T17:03:00Z | success | active | Analyst Tracker  Top 20 Crypto Analysts | `.github/workflows/analyst-tracker.yml` |
| 271 | 0.0 | 2026-11-14T17:03:04Z | success | active | DARWIN ENGINE - DNA Evolution Pipeline | `.github/workflows/darwin-evolution.yml` |
| 272 | 0.0 | 2026-11-14T17:03:11Z | success | active | Send Accountability Reminders | `.github/workflows/send-accountability-reminders.yml` |
| 273 | 0.0 | 2026-11-14T17:04:49Z | success | active | Master Automation Scheduler | `.github/workflows/master-automation-scheduler.yml` |
| 274 | 0.0 | 2026-11-14T17:04:58Z | success | active | Contested Pick Checker (Claude vs Antigravity) | `.github/workflows/contested-pick-checker.yml` |
| 275 | 0.0 | 2026-11-14T17:06:53Z | success | active | Specialized Scanners - Rocket, Short Engine, TSMOM | `.github/workflows/specialized-scanners.yml` |
| 276 | 0.0 | 2026-11-14T17:08:00Z | success | active | ANTIGRAVITY ML  Hourly Discord Status + Picks (DISABLED) | `.github/workflows/discord_status.yml` |
| 277 | 0.0 | 2026-11-14T17:08:47Z | success | active | Crypto Gainer ML Live Tracker | `.github/workflows/crypto-ml-tracker.yml` |
| 278 | 0.0 | 2026-11-14T17:09:14Z | success | active | VOLATILE ALT SCANNER Hyperliquid High-Vol Alts | `.github/workflows/volatile-alt-scanner.yml` |
| 279 | 0.0 | 2026-11-14T17:09:24Z | success | active | Coinglass DNA Scanner | `.github/workflows/coinglass-scanner.yml` |
| 280 | 0.0 | 2026-11-14T17:09:57Z | success | active | Hindsight Learner  Hourly Winner Analysis | `.github/workflows/hindsight-learner.yml` |
| 281 | 0.0 | 2026-11-14T17:10:01Z | success | active | Hourly Master Picks to Discord | `.github/workflows/hourly-master-picks.yml` |
| 282 | 0.0 | 2026-11-14T17:10:22Z | success | active | Low-Score Winner Tracker | `.github/workflows/low-score-tracker.yml` |
| 283 | 0.0 | 2026-11-14T17:10:28Z | success | active | AsterDEX Paper Trading | `.github/workflows/asterdex-paper-trading.yml` |
| 284 | 0.0 | 2026-11-14T17:11:59Z | success | active | Quick Guess ML Agent | `.github/workflows/quick-guess-ml.yml` |
| 285 | 0.0 | 2026-11-14T17:12:36Z | success | active | Breakout Arena  3 Approaches | `.github/workflows/breakout-arena.yml` |
| 286 | 0.0 | 2026-11-14T17:14:14Z | (none) | active | Unified Audit Dashboard | `.github/workflows/audit-dashboard.yml` |
| 287 | 0.0 | 2026-11-14T17:15:22Z | success | active | EMA Retracement Mean Reversion Scanner | `.github/workflows/ema-retracement-scan.yml` |
| 288 | 0.0 | 2026-11-14T17:17:08Z | success | active | Deploy Battleground to FTP | `.github/workflows/deploy-battleground-ftp.yml` |
| 289 | 0.0 | 2026-11-14T17:17:18Z | success | active | Signal Quality Monitor | `.github/workflows/signal-quality-monitor.yml` |
| 290 | 0.0 | 2026-11-14T17:18:02Z | success | active | Portfolio Trackers (Real Money + Theory) | `.github/workflows/portfolio-trackers.yml` |
| 291 | 0.0 | 2026-11-14T17:18:10Z | failure | active | Sports endpoint smoke + Playwright | `.github/workflows/sports-smoke-and-e2e.yml` |
| 292 | 0.0 | 2026-11-14T17:19:08Z | cancelled | active | Outcome Resolver  Validate Unresolved Picks | `.github/workflows/outcome-resolver.yml` |
| 293 | 0.0 | 2026-11-14T17:19:09Z | success | active | Signal Integrator - Isolated Source Aggregator | `.github/workflows/signal-integrator.yml` |
| 294 | 0.0 | 2026-11-14T17:19:17Z | success | active | Baby Strat Real Forward Monitor | `.github/workflows/baby-strat-forward-paper.yml` |
| 295 | 0.0 | 2026-11-14T17:21:00Z | success | active | Copy Trader Forward Test | `.github/workflows/copy-trader-forward-test.yml` |
| 296 | 0.0 | 2026-11-14T17:21:12Z | success | active | Meta-Strategy Permutation Engine | `.github/workflows/meta-strategy.yml` |
| 297 | 0.0 | 2026-11-14T17:21:16Z | success | active | Audit Hourly Update | `.github/workflows/audit-hourly-update.yml` |
| 298 | 0.0 | 2026-11-14T17:22:05Z | success | active | [torontoevent.net] Deploy Competition to Live Site | `.github/workflows/torontoevent-deploy-competition.yml` |
| 299 | 0.0 | 2026-11-14T17:22:20Z | failure | active | Missed Opportunity Analyzer Hourly Self-Improvement | `.github/workflows/missed-opportunity-scan.yml` |
| 300 | 0.0 | 2026-11-14T17:22:32Z | success | active | [torontoevent.net] Rapid Validation Engine | `.github/workflows/torontoevent-rapid-validation.yml` |
| 301 | 0.0 | 2026-11-14T17:24:34Z | success | active | Test Portfolios  Hourly Strategy Validation | `.github/workflows/test-portfolios.yml` |
| 302 | 0.0 | 2026-11-14T17:24:54Z | success | active | Hub Data Sync | `.github/workflows/hub-sync.yml` |
| 303 | 0.0 | 2026-11-14T17:26:40Z | success | active | Live Picks Tracker | `.github/workflows/live_tracker.yml` |
| 304 | 0.0 | 2026-11-14T17:27:32Z | success | active | pages-build-deployment | `dynamic/pages/pages-build-deployment` |
| 305 | 0.0 | 2026-11-14T17:28:15Z | success | active | Feed Health Check | `.github/workflows/feed-health.yml` |
| 306 | 0.0 | 2026-11-14T17:28:44Z | success | active | LuxAlgo Signal Generator | `.github/workflows/luxalgo-signals.yml` |
| 307 | 0.0 | 2026-11-14T17:30:35Z | success | active | Recommended Portfolio Generator | `.github/workflows/recommended-portfolio.yml` |
| 308 | 0.0 | 2026-11-14T17:31:30Z | success | active | Regime Terminal  HMM Live Scanner | `.github/workflows/regime-terminal.yml` |
| 309 | 0.0 | 2026-11-14T17:32:34Z | success | active | Deploy Rise of the Claw Dashboard | `.github/workflows/deploy-riseoftheclaw.yml` |
| 310 | 0.0 | 2026-11-14T17:32:50Z | success | active | [torontoevent.net] Deploy Rise of the Claw | `.github/workflows/torontoevent-deploy-riseoftheclaw.yml` |
| 311 | 0.0 | 2026-11-14T17:32:57Z | success | active | actions-failure-guardian | `.github/workflows/actions-failure-guardian.yml` |
| 312 | 0.0 | 2026-11-14T17:32:59Z | success | active | Multi-Asset Copytrader Scanner v2  Forex/Futures/Stocks/Commodities | `.github/workflows/multi-asset-scanner.yml` |
| 313 | 0.0 | 2026-11-14T17:33:26Z | success | active | Consensus Outcome Tracker | `.github/workflows/consensus-outcome-tracker.yml` |
| 314 | 0.0 | 2026-11-14T17:34:02Z | success | active | QUAN ENGINE - Live Autonomous Scanner | `.github/workflows/quan-engine-live.yml` |
| 315 | 0.0 | 2026-11-14T17:34:23Z | success | active | Claude's Test - Portfolio Manager | `.github/workflows/claudes-test-portfolios.yml` |
| 316 | 0.0 | 2026-11-14T17:34:52Z | success | active | MySQL Trading Picks Sync | `.github/workflows/mysql-trading-sync.yml` |
| 317 | 0.0 | 2026-11-14T17:35:02Z | (none) | active | ALPHA ENGINE FAST Tighter TP/SL, Shorter Holds | `.github/workflows/alpha-engine-fast.yml` |
| 318 | 0.0 | 2026-11-14T17:35:08Z | success | active | MOMENTUM CATCHER - Real-time Pump Detector | `.github/workflows/momentum-catcher.yml` |
| 319 | 0.0 | 2026-11-14T17:35:10Z | success | active | OBI Hourly Snapshot | `.github/workflows/obi-snapshot.yml` |
| 320 | 0.0 | 2026-11-14T17:36:01Z | success | active | Skyrocket Detector  Live Scanner | `.github/workflows/skyrocket-detector.yml` |
| 321 | 0.0 | 2026-11-14T17:36:05Z | success | active | ALPHA ENGINE - Quant Stack (KAMA + ATR + Regime) | `.github/workflows/alpha-quant-stack.yml` |
| 322 | 0.0 | 2026-11-14T17:38:18Z | success | active | Mercury 2  Signal Scanner | `.github/workflows/mercury2-scan.yml` |
| 323 | 0.0 | 2026-11-14T17:38:30Z | success | active | MOMENTUM TRACKER - Real-Time Gainer Scanner | `.github/workflows/momentum-tracker.yml` |
| 324 | 0.0 | 2026-11-14T17:40:07Z | success | active | GHCOPILOT prospective paper monitor | `.github/workflows/ghcopilot-paper-monitor.yml` |
| 325 | 0.0 | 2026-11-14T17:40:38Z | success | active | Claude Gainer Short-Term Predictor | `.github/workflows/claude-gainer-short-term.yml` |
| 326 | 0.0 | 2026-11-14T17:41:21Z | success | active | Cross-System Signal Aggregator | `.github/workflows/cross-aggregator.yml` |
| 327 | 0.0 | 2026-11-14T17:42:30Z | success | active | ALPHA ENGINE Gainer Capture (15min) | `.github/workflows/alpha-gainer-capture.yml` |
| 328 | 0.0 | 2026-11-14T17:44:31Z | success | active | Polymarket Prediction Market Signals (Multi-Asset) | `.github/workflows/polymarket-signals.yml` |
| 329 | 0.0 | 2026-11-14T17:46:01Z | success | active | Live Trading Monitor  Auto Refresh | `.github/workflows/live-monitor-refresh.yml` |
| 330 | 0.0 | 2026-11-14T17:46:40Z | success | active | Mega Mutation Live Tracker | `.github/workflows/mega-mutation-tracker.yml` |
| 331 | 0.0 | 2026-11-14T17:46:44Z | cancelled | active | Strategy Funnel Hourly Refresh | `.github/workflows/strategy-funnel-hourly.yml` |
| 332 | 0.0 | 2026-11-14T17:47:01Z | success | active | Dashboard Pick Trader | `.github/workflows/dashboard-pick-trader.yml` |
| 333 | 0.0 | 2026-11-14T17:47:53Z | success | active | Prediction Quality Tracker | `.github/workflows/prediction-quality-tracker.yml` |
| 334 | 0.0 | 2026-11-14T17:47:55Z | success | active | Rapid Fire - NOW Scanner | `.github/workflows/now-scanner.yml` |
| 335 | 0.0 | 2026-11-14T17:48:23Z | success | active | Sustained Gainer Confluence Scanner | `.github/workflows/sustained-gainer-scan.yml` |
| 336 | 0.0 | 2026-11-14T17:48:36Z | success | active | Claude Gainer ML  Live Scanner | `.github/workflows/claude-gainer-ml-live.yml` |
| 337 | 0.0 | 2026-11-14T17:48:40Z | success | active | Winner Pattern Precursor Scanner | `.github/workflows/winner-pattern-scanner.yml` |
| 338 | 0.0 | 2026-11-14T17:48:41Z | success | active | Sports data snapshots | `.github/workflows/sports-data-snapshots.yml` |
| 339 | 0.0 | 2026-11-14T17:49:07Z | (none) | active | ALPHA ENGINE - Dynamic Runner (Cloud or Local) | `.github/workflows/dynamic-alpha-engine.yml` |
| 340 | 0.0 | 2026-11-14T17:49:28Z | success | active | ML Battleground System F (Claws of Doom) | `.github/workflows/ml-battleground-f.yml` |
| 341 | 0.0 | 2026-11-14T17:49:36Z | (none) | active | Branch Large File Duplicate Guard | `.github/workflows/branch-large-file-dup-guard.yml` |
| 342 | 0.0 | 2026-11-14T17:49:36Z | failure | active | CI Tests | `.github/workflows/ci-tests.yml` |
| 343 | 0.0 | 2026-11-14T17:50:42Z | success | active | Deploy FindCryptoPairs to FTP | `.github/workflows/deploy-findcryptopairs-ftp.yml` |
| 344 | 0.0 | 2026-11-14T17:51:05Z | success | active | Picks-Now Live PnL (hourly) | `.github/workflows/picks-now-live-pnl.yml` |
| 345 | 0.0 | 2026-11-14T17:51:26Z | success | active | Signal Recorder | `.github/workflows/signal-recorder.yml` |
| 346 | 0.0 | 2026-11-14T17:53:35Z | (none) | active | Copy Trader Intelligence  Scrape + Analyze + Track | `.github/workflows/copy-trader-intelligence.yml` |
| 347 | 0.0 | 2026-11-14T17:56:37Z | success | active | Smart Picks Tracker | `.github/workflows/smart-picks-tracker.yml` |
| 348 | 0.0 | 2026-11-14T17:56:46Z | skipped | active | Pine Script Generator | `.github/workflows/pine-generator.yml` |
| 349 | 0.0 | 2026-11-14T17:57:03Z | success | active | Conviction Picks Ultra-Selective Discord Alert | `.github/workflows/conviction-picks.yml` |
| 350 | 0.0 | 2026-11-14T17:58:01Z | success | active | Deploy Competition to Live Site | `.github/workflows/deploy-competition-to-site.yml` |
| 351 | -0.0 | 2026-11-14T18:00:26Z | success | active | [torontoevent.net] Spike Scanner | `.github/workflows/torontoevent-spike-scanner.yml` |
| 352 | -0.0 | 2026-11-14T18:00:29Z | success | active | TV Paper TP/SL Watchdog | `.github/workflows/tv-paper-tpsl-watchdog.yml` |
| 353 | -0.0 | 2026-11-14T18:00:44Z | success | active | Hoffman IRB Strategy Tracker | `.github/workflows/hoffman-tracker.yml` |
| 354 | -0.0 | 2026-11-14T18:00:44Z | success | active | Meme Coin Scanner Auto Scan & Resolve | `.github/workflows/meme-scanner.yml` |
| 355 | -0.0 | 2026-11-14T18:00:46Z | success | active | ML System Health Monitor | `.github/workflows/ml-health-monitor.yml` |
| 356 | -0.0 | 2026-11-14T18:00:49Z | (none) | active | Crypto Signal Engine | `.github/workflows/signal-engine.yml` |
| 357 | -0.0 | 2026-11-14T18:00:59Z | success | active | Pick Monitor & Price Validator (30min) | `.github/workflows/pick-monitor-30min.yml` |
| 358 | -0.0 | 2026-11-14T18:01:00Z | success | active | Swarm State Sync | `.github/workflows/swarm-sync-v2.yml` |
| 359 | -0.0 | 2026-11-14T18:01:03Z | success | active | Meme Coin Scanner v2  Fixed & Monitored | `.github/workflows/meme-scanner-v2.yml` |
| 360 | -0.0 | 2026-11-14T18:01:05Z | (none) | active | DNA Genome Daily Pipeline | `.github/workflows/genome-daily-pipeline.yml` |
| 361 | -0.0 | 2026-11-14T18:01:06Z | (none) | active | Gainer Predictor Scanner | `.github/workflows/gainer-predictor.yml` |
| 362 | -0.0 | 2026-11-14T18:01:06Z | (none) | active | Update Creator News | `.github/workflows/update-creator-news.yml` |
| 363 | -0.0 | 2026-11-14T18:01:15Z | success | active | DB Freshness Guardian | `.github/workflows/db-freshness-guardian.yml` |
| 364 | -0.0 | 2026-11-14T18:01:48Z | success | active | Conflict Marker Check | `.github/workflows/conflict-marker-check.yml` |
| 365 | -0.0 | 2026-11-14T18:01:48Z | success | active | No stale DB passwords | `.github/workflows/no-stale-db-passwords.yml` |

**Counts:** 20 never run · 30 last-run failed · 19 last run >90d ago · 365 total.
