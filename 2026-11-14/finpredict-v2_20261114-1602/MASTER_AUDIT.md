# MASTER AUDIT — findtorontoevents.ca/audit prediction system

**Audit date:** 2026-11-14
**Audit clock:** 2026-11-14T16:05Z (all ages computed against this clock unless stated)
**Auditor subtree:** `finpredict-v2` (7 parallel subagents, independent evidence extraction)
**Live targets:** `https://findtorontoevents.ca/audit` and `/audit/hyrotrader`
**Repo:** `github.com/eltonaguiar/findtorontoevents_antigravity.ca`
**Primary live payload:** `dashboard_data.json` / `dashboard_payload.json`, `generated_at = 2026-11-14T14:30:07Z`, captured ~1.6 h later at 16:03–16:05Z.
**Peer archives cross-referenced:** `finpredict` (2026-11-14T160004Z), `finpredict-v3` (2026-11-14T155500Z), `finpredict-v4` (`audits/2026-11-14/finpredict-v4_2026-11-14-1555/`), and the pasted `inspect-wt` transcript.

> **Reading rule:** every number below is traceable to a live file, an API response, or a named peer artifact. Items that could not be verified are marked `UNVERIFIED`. Nothing is estimated or invented.

---

## Executive scorecard

| # | Subtask | Verdict | One-line reason |
|---|---|---|---|
| 1 | GitHub Actions health | **FAIL** | 24 workflows failing in 24 h / 88 in 7 d; audit-dashboard cancels ~1/3 of runs and takes 80–104 min vs 30–35 documented |
| 2 | Active picks, all asset classes | **FAIL** | Only 20 curated rows; 19/20 PnL = 0; raw inventory is 4,148 rows, majority zombies/unpriced |
| 3 | Frozen data / dead fields | **FAIL** | Core payload fresh, but Edge/Track/FWD ≈ dead and 10+ sidecars are 79–245 days stale |
| 4 | Closed picks (recent realized) | **FAIL** | 42.2% WR, sum −469.5% on 3,500 rows; only 10 closes <24 h old |
| 5 | Verdict: real edge vs chance | **FAIL** | Fleet policy-clean PF 0.27, WR 42.2%, z = −23.6; 0/9 classes money-ready; 31/38–69/80 overfit |

**Bottom line:** the pipeline is real engineering, but the published performance is **not genuinely profitable and not statistically sound**. It is a multiple-testing + survivorship + stale-price artifact.

---

## 1. Actions health — **FAIL**

**PASS/FAIL:** **FAIL** — large surface, high failure and cancellation rates, and the dashboard pipeline itself is unstable.

### Evidence (GitHub API, captured 2026-11-14T16:03–16:08Z)

| Metric | Value |
|---|---:|
| Workflow files | **365** (361 active, 4 `disabled_manually`) |
| Ran in last 24 h | **269** |
| Ran in last 7 d | **309** |
| Never ran (all-time) | **20** |
| Stale >7 d | **36** |
| Zero runs in 7 d (never + stale) | **56** |
| Runs in 24 h | **4,109** → 3,747 success, **214 failure**, **82 cancelled**, 49 skipped, 17 running |
| Runs in 7 d | **28,187** → 26,112 success, **1,207 failure**, **642 cancelled**, 185 skipped, 41 running |
| Failing workflows | **24** in 24 h / **88** in 7 d |
| Last run failed | **25** workflows |
| Last run cancelled | **11** workflows |
| Cancelled with zero jobs executed | **15** in 24 h (all 82 checked) |

### Failure clusters (last 24 h)

| Workflow | Fail 24 h | Latest failing run | Failing step | Root error |
|---|---:|---|---|---|
| ALPHA ENGINE — Dynamic Runner | 47 | 43609547717 (15:19Z) | Run Alpha Engine | `KeyError: 'LONG'` after Binance HTTP 451, CoinMetrics 400/403, missing `xgboost` |
| ALPHA ENGINE FAST | 46 | 43608586741 (15:08Z) | Run Alpha Engine FAST | Same `KeyError: 'LONG'` |
| Sports endpoint smoke + Playwright | 24 | 43609430834 (15:18Z) | retrying | `UNVERIFIED` — attempt 3 in progress at snapshot |
| CI Tests | 15 | 43605861085 (14:37Z) | retrying | `UNVERIFIED` — attempts 4, `test(3.11)`/`test(3.12)` running |
| Market Beating System | 12 | 43603128044 (14:06Z) | retrying | `UNVERIFIED` — attempt 5 in progress |
| Signal Tracking & Validation | 11 | 43602685216 (14:01Z) | Install dependencies | pandas 2.1.4 source build under Python 3.14: `_PyLong_AsByteArray` expected 6 args, have 5 |

### Dashboard pipeline (`audit-dashboard.yml`)

- **7 d:** 106 success / **61 cancelled** / 168 runs.
- **24 h:** 13 success / **10 cancelled**.
- Five sampled successful jobs ran **79.6–104.2 min** (median **84.5 min**) against a documented 30–35 min and a 115-min timeout.
- 9 of the 24 h cancels were **zero-job queued runs** in the `dashboard-publish` group — the cancel cascade documented on 2026-05-19 is still active.
- Push contention: Live Spike exhausted 8/8 push attempts; H-002 PEAD 10/10; mirror timed out at 30 min.
- `fetch_prices.php` returns HTTP **404**.

### Reconciliation with peers

- `finpredict` (118-line audit): 365 workflows, **28 last-run failures**, 20 never run, 24 workflows >30 d stale. Compatible with the windowed counts above.
- `finpredict-v4`: same 365 workflows; adds "Alpha Engine last 10 runs = 9 cancelled + 1 failure" (its own window). `UNVERIFIED` independently; consistent with the 93 failed runs/24 h `KeyError` cluster.
- Root causes for the retrying runs in the table are `UNVERIFIED` because the runs were mid-retry when logs were requested.

---

## 2. Active Picks — **FAIL**

**PASS/FAIL:** **FAIL** — the visible "20 picks" are signal-fresh but price-frozen; the raw inventory is dominated by zombies.

### Populations you must keep separate

| Population | Rows | What it is |
|---|---:|---|
| `picks.active` | **20** | Curated panel shown on the page |
| `picks.active_raw` | **4,148** (3,851 unique IDs) | Full emitted inventory |
| `picks.recent_closed` | **3,500** | Closed-pick feed |
| `performance.by_asset_class` "active" | **158** | Internal inconsistency: 7.9× the curated panel |
| `concentration_summary.total_active` | 263 | Third count |
| `summary.total_active_picks` | 20 | Matches the panel |

### Per-asset-class status

| Asset class | Curated active | Raw OPEN | Frozen at 0% (current==entry or null) | Newest signal | Signal age | Class verdict |
|---|---:|---:|---:|---|---:|---|
| CRYPTO | 3 | 402 | 334 (**83%**) | 2026-11-14T13:54Z | ~2.0 h | **FAIL** — thin live minority; raw median 88.7 d |
| EQUITY | 2 | 94 | 40 (**43%**) | 2026-11-14T13:06Z | ~2.8 h | **FAIL** — 82 raw rows >30 d |
| ETF | 10 | 30 | 15 (**50%**) | 2026-11-14T12:53Z | ~3.0 h | **FAIL** — no mark-to-market |
| FOREX | 2 | 118 | 93 (**79%**) | 2026-11-14T14:24Z | ~1.5 h | **FAIL** — 158 raw rows >30 d |
| FUTURES | 1 | 3 | 3 (**100%**) | 2026-11-14T13:06Z | ~2.8 h | **FAIL** — 0 rows in `picks.recent_closed` (full history n=13 policy-clean; intrabar n=52); date-only seed |
| BOND | 0 | 15 | 9 (**60%**) | 2026-11-13T14:34Z | ~25 h | **FAIL** — newest closed 4.09 d |
| COMMODITY | 2 | 27 | 18 (**67%**) | 2026-11-14T14:24Z | ~1.5 h | **FAIL** — all 44 raw rows are futures `=F` |
| MUTUAL FUNDS | 0 | 0 | — | — | — | **NOT BUILT (production)** — untracked prototype files exist only in the main checkout, absent from `origin/main`; no live picks |
| SPORTS (non-canonical) | 2 | 2 | 2 (**100%**) | 2026-11-14T12:29Z | ~3.4 h | **FAIL** — 2 seed rows |

- **691 total OPEN rows.** Of these, **177 (25.6%)** carry a positive, entry-differing quote; **123 (17.8%)** also carry non-zero PnL; **29** are bit-exact `current == entry`; **485** have a null price. Use the 123 figure only for the strict "live mark" count; do not conflate it with 177.
- **277 of 571 non-crypto raw rows (48.5%) are `_auto_expired` / `expired_no_pnl` zombies.**
- **274 non-crypto rows are >30 d stale** (EQUITY 82, FOREX 158, COMMODITY 16, FUTURES 10, ETF 8).
- **FOREX timestamp defects are larger than first reported:** **105/277 FOREX rows already carry a date-only `entry_time`** (not 12; 12 is date-only `timestamp`), and 44 more are EST-stamped and unparseable by both timestamp parsers. All 3 OPEN `ES=F` rows carry date-only `entry_time`/`signal_time`.
- **FOREX "block" is not enforced:** the advertised PR #6 allowlist lives in `evaluate_non_crypto_candidate()` (`alpha_engine/non_crypto_policy.py:698-741`) with **0 call sites**; the live gate `passes_non_crypto_policy()` (`:1026-1040`) omits it. **0/277** audited FOREX rows pass the allowlist. Four retired strategies supply ~95/277 rows (not one).
- `active_raw` has **4,148 rows / 3,851 unique IDs**; BOND emits 15 rows for 5 instruments; FOREX has 67 duplicate `symbol+strategy+direction` groups.

### Per-class accuracy (honest / policy-clean, not curated)

| Class | n | WR | PF | Source |
|---|---:|---:|---:|---|
| CRYPTO | 21,988 | 42.35% | 0.2595 | `pf_registry.by_asset_class_policy_clean_net` |
| FOREX | 438 | 35.62% | 0.8339 | same |
| EQUITY | 461 | 42.95% | 0.7022 | same |
| COMMODITY | 14 | 14.29% | 0.1718 | same |
| FUTURES | 13 | 23.08% | 0.8567 | same |
| ETF | 15 | 73.33% | 1.8358 | same (n too small) |
| BOND | 1 | 0% | 0 | same (n=1) |

**No class meets the project's own Tier-2 charter (n≥100, WR≥50%, PF≥1.5).**

### External cross-reference (named sources)

Sources: Binance `api.binance.com/api/v3/ticker/price` and `/klines`; `open.er-api.com` for FX; Yahoo `query1.finance.yahoo.com` / Stooq for equities/ETFs/futures.

| Symbol / direction | Entry | Dashboard current | Dashboard PnL | Live quote (source) | True PnL | Verdict |
|---|---:|---:|---:|---:|---:|---|
| NEARUSDT SHORT | 3.324 | 3.233 | +2.74% | 3.197–3.222 (Binance) | +3.1% to +3.8% | **REAL, plausible** |
| XRPUSDT SHORT | 0.9842 | 0.9842 | 0.00% | 0.9698–0.9742 (Binance) | +1.0% to +1.5% | **FROZEN at entry** |
| BTCUSDT SHORT | 66,300 | 66,300 | 0.00% | 65,658–65,839 (Binance) | +0.7% to +1.0% | **FROZEN at entry** |
| USDCAD=X SHORT | 1.4269 | 1.4269 | −0.0% | 1.42603 (er-api) | +0.06% | **FROZEN at entry** |
| NZDUSD=X LONG | 0.552517 | 0.552517 | −0.0% | 0.55273 (er-api) | +0.04% | **FROZEN at entry** |

**NEARUSDT +3.16% is real.** `(3.324 − 3.22) / 3.324 ≈ 3.1%`; the dashboard's 2.74% is the same pick marked at 14:30Z (3.233). A ~3% move in NEAR is entirely plausible for a volatile altcoin. This is a real, ~2 h-stale quote — not wrong data.

**Everything else near 0% is stale, not flat.** For the 20 curated rows, `current_price == entry_price` exactly on 19 of them, so 0% is an arithmetic identity, not an observation. XRP/BTC actually moved +1.0–1.5% / +0.7–1.0% in favour of the SHORT; the dashboard never re-quoted.

---

## 3. Frozen data — **FAIL**

**PASS/FAIL:** **FAIL** — the core JSON is fresh, but most metric fields and at least 10 sidecars are dead.

### Payload freshness (live `data/*.json`, captured 16:03–16:05Z)

| Payload | Age | Verdict |
|---|---:|---|
| `dashboard_payload.json` / `dashboard_data.json` | 1.63 h | **FRESH** |
| `money_ready_verdict.json` | 1.65 h | FRESH |
| `pf_registry.json` | 1.64 h | FRESH |
| `anti_overfit_audit.json` | 1.77 h | FRESH |
| `summary_picks.json` | 1.63 h | FRESH (math broken) |
| `db_health.json` | 1.91 h | FRESH |
| `ma_strategy_leaderboard.json` | 1.72 h | FRESH |
| `audit_surface_truth.json` | **11.26 h** | **LATE** |
| `hyro_pick_performance.json` | **157.9 h (6.6 d)** | **STALE/DEAD** |
| `hyrotrader_picks.json` (`account_snapshot.last_session_date`) | **5,296 h (220.7 d)** | **DEAD** |
| `regime_report.json` | **3,896.9 h (162 d)** | **DEAD** |
| `strategy_ic_analysis.json` | **4,060.4 h (169 d)** | **DEAD** |
| `strong_signals.json` | **5,120.8 h (213 d)** | **DEAD** |
| `stock_forex_prices.json` | **5,211.9 h (217 d)** | **DEAD** |
| `pilot_forward_dashboard.json` | **3,877.6 h (161.6 d)** | **DEAD** |
| `strategy_admissibility.json` | **3,877.6 h (161.6 d)** | **DEAD** |
| `operator_review_today.json` | **1,901.7 h (79.2 d)** | **DEAD** |
| `claude/grok/kimi/mercury/ag_top_picks*.json` | ~**245 d** | **DEAD** |
| `strategy_tribunal_latest.json` | HTTP 404 | **MISSING** |

### Metric-field liveness (the user's Edge / Track / FWD WR / FWD N question)

| Field | Alive on 691 OPEN rows | Verdict |
|---|---:|---|
| `history_wr` / `history_trades` / `history_avg_pnl` | **0%** | DEAD |
| `profile_crypto_wr` | **0%** | DEAD |
| `strat_decay` | 0.1% | DEAD |
| `sym_track_wr` / `sym_track_total` | 2.7–3.6% | DEAD |
| `strat_fwd_pf` / `strat_csr` | 3.8% | DEAD |
| `forward_wr` | 8.7% | MOSTLY DEAD |
| `forward_trades` | 10.1% | MOSTLY DEAD |
| `strat_fwd_wr` / `strat_fwd_trades` | 6.9–8.5% | MOSTLY DEAD |
| `rsi` | 21.0% | PARTIAL |
| `current_price` | 29.8% | PARTIAL |
| `strat_sample_quality` | 26.5% | PARTIAL |

On the **visible 20-row panel**:
- **EDGE = 0/20 populated** (client-side `buildVerifiedEdgeIndex()` finds no matching `(strategy,symbol)` in `recent_closed`; 19/20 strategies have **n=0** closed trades).
- **Track = 2/20** (both 0%).
- **FWD WR = 2/20**.
- **FWD N = 20/20 but 90% are 0.**

So the columns are not "some dead fields" — they are structurally empty for the current active universe.

### Other frozen / broken data

- **`summary_picks.json` publishes impossible win rates** (wins ÷ resolved where wins/losses come from a larger overlapping population). **7 classes report WR >100%:** BOND 127.8%, COMMODITY 240.2%, EQUITY 162.4%, ETF 232.9%, FOREX 147.0%, FUTURES 363.9%, INDEX 1141.2%. **9 classes have `wins+losses > resolved`** (the 7 above plus CRYPTO 98.3% and MEME 40.8%). Root cause: `sync_summary_picks_json.py:63-65` + division at `:161`.
- **22,947 ghost rows** (`db_health.json`), top cohort DOGEUSDT LONG pnl 1.3226 n=3,569 distinct_entries=1.
- **3,377 `EXPIRED` rows** inside `active_raw` still counted as inventory.
- **85 zero/null entry rows**; **12 LOST-but-positive-PnL contradictions**; **248 duplicate-ID groups / 297 extra rows**; **56 IDs conflicting across `active_raw`/`recent_closed`**.
- **COMMODITY and FUTURES are administratively blocked:** `audit_trail/quality_gates.py:1724` sets `BLOCKED_ASSET_CLASSES = {"FOREX","COMMODITY","FUTURES","BOND"}`. A "live" commodity bucket is a display artifact, not an unblocked trading class.
- **COMMODITY generator uses crypto proxies:** `alpha_engine/commodity_signal_generator.py:231-238` maps RNDR/ARB to "silver" and `:250` maps XLM/DOT to "oil". Rows labelled COMMODITY may carry no commodity exposure.
- **AI Challenge crypto registry is stale:** `audit_dashboard/data/ai_challenge_antigravity_active_picks.json` has **9 OPEN rows, all `current_price=None`, `pnl_pct=0.0`, no timestamp fields** (age itself `UNVERIFIED`).
- **SQLite layer is independently stale:** peer ML audit `updates/2026-11-14-ML-AUDIT-childlike-airport.md` found `data/live_picks.db` **128/129 active picks ~172 days stale**, **8 PnL sign contradictions**, **15 PnL mismatches**, and `data/audit_trail.db` **9 audit tables with 0 rows**; `pick_history` is all `REGISTERED` (no exits). This is a separate store from the dashboard JSON.
- **Dashboard inflates CRYPTO PF ~5× vs raw DB:** v4 evidence reports dashboard CRYPTO PF **1.801** vs raw DB **0.371**, and Smart Picks PF **9.69** on 3 closed rows (91.7% one source). Peer-accepted, not independently re-derived here.
- **Fabricated flat-3% cohort:** `signal_validation` (117), `macd_rsi_confluence` (138), `meanreversionbb` (111), `macd_crossover`, `momentumema`, `bollinger_squeeze`, `gpx/gpm_gen*` → **286 trades, every win exactly +3.00%, zero losers** (peer `finpredict`; adopted by `finpredict-v3`).
- **127 "verified strategies" OPEN picks seeded 2026-11-12 12:15–12:19; 123 (96.9%) frozen** at PnL 0 / current==entry.
- **11 frozen closed FOREX phantoms** (EURUSD, USDCHF, USDJPY, AUDUSD, GBPUSD, NZDUSD, SOFI; March 2026; `exit UNKNOWN`; `exit_price == entry_price`).
- **HyroTrader page is a static template:** `hyrotrader_picks.json` has no timestamp, 7 `pending_entry` rows with null prices, `account_snapshot.last_session_date = 2026-04-08`, journal `trades: []`; two fetches give identical SHA-256.
- **Non-standard JSON:** `money_ready_verdict.json` contains `NaN`; `strategy_ic_analysis.json` contains `Infinity` → browser `JSON.parse` throws.
- **Dead tabs/panels:** Smart Picks empty (`total_scored: 0`, last batch 2026-11-11), Score Tracker is browser `localStorage` only, Regime 0/263 with data, Walkforward empty, ML Health 173 d, Permutations 12/13 zero-active.

---

## 4. Closed picks — **FAIL**

**PASS/FAIL:** **FAIL** — recent realized performance is negative and the closed feed is mostly months old.

### `picks.recent_closed` (3,500 rows, same live payload)

| Metric | Value |
|---|---:|
| Win rate | **42.2%** |
| Sum PnL | **−469.5%** |
| Mean PnL | **−0.134%** |
| Last 7 d | **34.6% WR, −381.3%** |
| Last 14 d (peer `finpredict-v3`) | **n=751, sum −333.2%** |

**Exit mix:** SL_HIT 1,451 · TP_HIT 884 · FORCE_CLOSED 622 · TIME_EXIT 516 · UNKNOWN 22 · EXPIRED 5.

### By class (recent closed feed)

| Class | WR | Sum PnL |
|---|---:|---:|
| CRYPTO | 40.2% | **−689.9%** |
| FOREX | 39.0% | −29.0% |
| BOND | 37.1% | −7.7% |
| COMMODITY | 42.9% | −4.2% |
| EQUITY | 47.0% | **+238.4%** |
| ETF | 44.3% | +22.9% |

**But EQUITY is not a robust edge:** three aggregators disagree — headline n=8 (75% WR, PF 8.86), `non_crypto_performance` n=759 (46.1%), `recent_closed` n=738 (47.0%); peer `finpredict-v3` reports full n=461 at ~43% / PF 0.70. The n=8 "edge" is meaningless.

### Closed-pick age (this is why "recent" is misleading)

| Class | n | Newest close | Median close age |
|---|---:|---|---:|
| CRYPTO | 1,966 | 3.2 h | **29.1 d** |
| EQUITY | 738 | 33.3 h | **120.1 d** |
| ETF | 567 | 26.0 h | **120.1 d** |
| FOREX | 187 | 38.0 h | **128.1 d** |
| BOND | 35 | 98.2 h | **135.1 d** |
| COMMODITY | 7 | 25.5 h | 4.9 d |

Only **10 of 3,500** closed rows are <24 h old. **2,221 are >30 d**, 1,132 >90 d, 582 >180 d.

### Independent surfaces agree on losses

- `money_ready_verdict`: **0/9 classes money-ready**; CRYPTO WR 35.87%, PF 0.92, expectancy −0.059.
- `audit_surface_truth`: "0/9 asset classes money-ready on policy-clean closed picks."
- `pf_registry` policy-clean: CRYPTO PF 0.2595, FOREX 0.8339, EQUITY 0.7022.
- `pilot_forward_dashboard`: 0/8 forward sleeves promotion-ready (161.6 d stale).
- MA walk-forward: 0 golden.

---

## 5. Verdict — **FAIL: artifact of multiple testing + survivorship, not a real edge**

**PASS/FAIL:** **FAIL** — not demonstrably profitable and not statistically sound.

### Search space actually scored

- **658 distinct strategies** in the live `pf_registry` (682 asset×strategy pairs; 2,218 strategy×symbol cells).
- Declared space: **361 strategy families** (`alpha_engine/config.py:1646`) + **84 baby meta-strategies** + **231 hand mutation variants** + 7 DNA operators ≈ **676 before genome search**.
- 365 workflows, 100+ source systems, ~4,300 open picks in backlog.

### Fleet truth (policy-clean, net of slippage)

| Metric | Value |
|---|---:|
| n (deduped, policy-clean) | **22,941** |
| Win rate | **42.21%** |
| Profit factor | **0.2657** |
| WR z vs 50% | **−23.60** (two-sided p ≈ 3.6×10⁻¹²³) |
| Median per-strategy PF | **0.052** (0.66 for n≥30) |
| Strategies with PF>1 | **94 / 658 (14.3%)** — below the ~329 expected under a coin flip |
| Strategies with n<10 | **512 / 658 (78%)** |

### Multiple-testing math (shown, not asserted)

- At **N = 658** tests and α = 0.05, expected false positives = **32.9**.
- Bonferroni α = 7.599×10⁻⁵, **z_crit = 3.788** (one-sided); Šidák ≈ 7.795×10⁻⁵.
- **21 strategies clear Bonferroni** — but **all 21 are the single-source, 90–100%-WR artifact cluster** (`single_source_pct = 1.00`, `top_source = file:mysql:at_pick_outcomes`), flagged `is_single_source_artifact = True` by the registry itself. That violates the independence assumption, so this is a data-generation artifact masquerading as 21 discoveries.
- BH-FDR at q=0.05 rejects for 22 of 76 strategies with n≥30 — again all in the same correlated cluster.

### PBO / DSR / Reality Check

- **PBO = 0.0 is degenerate, not evidence of edge:** 20×80 matrix, `n_folds=5` (10 splits, 8-obs OOS), rows built with `ORDER BY strategy` and no chronological alignment (`tools/anti_overfit_audit_sidecar.py:88-95,210-224`). CSCV needs a time-indexed T×S matrix; this has none. It also contradicts the same file's **69/80 OVERFIT_LIKELY** verdicts.
- **DSR uses `n_trials=80`** (`anti_overfit_audit_sidecar.py:184`) while the ledger has 658 strategies → under-corrects.
- **Reality Check never ran** (`arch` package missing).

### Per-class significance (two-sided, Bonferroni |z|_crit = 2.773)

| Class | n | WR | PF | z | Survives correction? |
|---|---:|---:|---:|---:|---|
| CRYPTO | 21,988 | 42.35% | 0.2595 | **−22.69** | **YES — significantly BELOW 50%** |
| FOREX | 438 | 35.62% | 0.8339 | **−6.02** | **YES — significantly BELOW 50%** |
| EQUITY | 461 | 42.95% | 0.7022 | **−3.03** | **YES — significantly BELOW 50%** |
| COMMODITY | 14 | 14.29% | 0.1718 | −2.67 | No |
| FUTURES | 13 | 23.08% | 0.8567 | −1.94 | No |
| ETF | 15 | 73.33% | 1.8358 | +1.81 | No (n too small) |
| BOND | 1 | 0% | 0 | n/a | No |

**No asset class survives correction with a positive edge.** Three survive with significantly negative WR.

### Survivorship

- **90,523 / 143,156 picks (63%) never resolve.**
- **16,126 → 7,914 (49%)** closed picks survive integrity gates; `integrity_excluded` 7,567; `auto_expired_excluded` 8,888.
- **22,947 constant-PnL ghost rows** removed from the canonical view.
- **1,777 known-killer rows** policy-excluded (7.2% of deduped).
- Headline stats are computed on survivors, so the true population is worse than displayed.

**Verdict:** the "winners" are fully explained by (a) ~33 expected false positives at N=658, (b) a correlated single-source resolver artifact, and (c) survivorship filtering. There is no independent, multiple-testing-robust, positive-edge strategy group.

---

## 6. Direct answers to the specific questions

| Question | Answer |
|---|---|
| Are the crypto and non-crypto stats real? | **Computed from real data, but not trustworthy as performance.** Crypto policy-clean PF 0.26 / WR 42.2%; non-crypto `active_raw` is 89% zero-PnL and 48.5% auto-expired. `summary_picks` WR>100% is arithmetically impossible. |
| Are "recent picks" per class actually recent? | **Signal timestamps: yes for the curated 20** (1.4–3.6 h). **Prices: no** — 19/20 are pinned at entry. **Raw inventory: mostly old** — crypto median 88.7 d, futures 97.7 d, 274 non-crypto rows >30 d. |
| FUTURES shows 1 active pick with no date? | **Not reproduced on the live Active Picks table** — it renders `Nov 14, 8:06 AM`. But the underlying `entry_time`/`signal_time` for `ES=F` is date-only `2026-11-14`, and 8 raw FUTURES `EXPIRED` rows are date-only. Panel-dependent; not a live priced position. |
| Bonds picks were 4 days ago? | **Confirmed for Closed Picks:** newest BOND close `2026-11-10T14:34:06Z` = **4.06–4.09 d**. BOND has **0 curated active**, 15 raw seeds ~25 h old with null prices. Effectively dead. |
| Crypto "1.9 h ago" — true? | **True as signal age:** newest crypto signal 13:53Z = **~2.18 h** at 16:03Z (~1.9 h when the user looked ~15:45Z). **False as price freshness:** XRP/BTC were not re-quoted at the 14:30Z build. |
| Everything except NEAR/XRP/USDCAD/NZDUSD/BTC shows ~0% — stale? | **Yes.** `current_price == entry_price` identically; it is an unquoted/stale-row artifact, not genuine flat performance. |
| Are Edge / Track / FWD WR / FWD N alive? | **Mostly dead.** EDGE 0/20, Track 2/20, FWD WR 2/20, FWD N 90% zero; underlying `forward_*` / `sym_track_*` / `strat_fwd_*` fields are 0–10% populated. |
| Is Kalshi MTF consensus real? | **Real code and real live API** (Kalshi trade-api v2, no key; 4 raw picks, 2 on the panel, newest 13:53Z, entries inside real Binance candles). **But 0 resolved outcomes**, absent from leaderboards, and still weighted in the `consensus` panel. Real data, unvalidated performance. |
| Is NEARUSDT 3.16% real and plausible? | **Yes.** Entry 3.324 → dashboard 3.233 = +2.74%; live Binance 3.197–3.222 = +3.1–3.8%. A ~3% altcoin move is normal. The quote is ~2 h stale, not wrong. |

---

## 7. Peer cross-reference (finpredict v1 / v2 / v3 / v4)

| Finding | `finpredict` (v1) | `finpredict-v3` | `finpredict-v4` | This audit (v2) | Reconciliation |
|---|---|---|---|---|---|
| Overall verdict | FAIL | FAIL | FAIL | FAIL | **AGREE** |
| Actions: 365 workflows | 365 | — | 365 | 365 | **AGREE** |
| Actions last-run failures | 28 | — | 28 | 25 last-run / 24 workflows in 24 h | **AGREE** (window differs) |
| 20 never-run workflows | yes | — | yes | yes | **AGREE** |
| Alpha Engine broken | yes | — | last 10 = 9 cancelled + 1 failure | 93 failed runs/24 h `KeyError:'LONG'` | **AGREE** |
| Curated active picks | 20 | 20 | **0 in INDEX, 20 in its own crypto deep-dive** | **20 live** | **v4 internally contradictory** — `INDEX.md`/`dashboard_data_report.md` read a stale repo snapshot; its own `crypto_deep_dive.md` and `forex_deep_dive.md` describe 20 active / live 14:30Z. Live fetch confirms 20. |
| `dashboard_data.json` age | 1.63 h | 1.63 h | **26 days repo copy; 1.63 h live in deep-dives** | **1.63 h live** | **v4 internally contradictory** — the repo copy is `2026-10-19T19:40:11Z`, the deployed HTTP payload is `2026-11-14T14:30:07Z`. v4's "empty shell" describes the repo snapshot, not the live page. |
| Raw inventory | 4,148 / 691 OPEN | zombie scan 3,577 CRYPTO | 4,310 | 4,148 | **AGREE** |
| Crypto raw median age | 89 d | 3,085 rows >7 d | — | 88.7 d | **AGREE** |
| NEAR real | yes, +2.74% → +3.07% | live quote | +2.74% → +3.46% | +2.74% → +3.1–3.8% | **AGREE** |
| XRP/BTC frozen | yes | yes | yes | yes | **AGREE** |
| BOND 4 d | yes (closed) | yes | ~1.9 d (different population) | yes (closed 4.09 d) | **AGREE on closed feed**; v4's 1.9 d is raw-seed age |
| FUTURES no date | not on live table; date-only seed | date-only seed | 0 live picks | not reproduced on table; date-only `entry_time` | **AGREE with nuance** |
| Metric fields dead | ~90% | FWD 48% populated, edge_ratio absent | all empty (due to 0 picks) | Edge 0/20, Track 2/20, FWD WR 2/20 | **AGREE** |
| `summary_picks` WR>100% | — | yes | yes | yes (7 named) | **AGREE** |
| Multiple testing | 361+285+mutation ⇒ ~260 lucky | 361+285 ⇒ ~260 | "100+ strategies" | 658 scored; 32.9 expected FP; 21 artifact cluster | **AGREE in direction**; v2 quantifies the live scored space |
| Survivorship | 16,126 → 7,914 (49%) | 49% | 4,220 TIME_EXIT, 6.2% resolved | 90,523/143,156 never resolve; 22,947 ghost | **AGREE** |
| 0/9 money-ready | yes | yes | yes | yes | **AGREE** |
| Kalshi real but unresolved | real code, frozen output | kalshi ~7 mo stale | code runs, silent failures | real live API, 4 picks, 0 resolved | **AGREE** |
| HyroTrader dead | yes | — | loading / 46 h stale | static template, 220.7 d account | **AGREE** |
| Mutual funds | unbuilt | — | — | NOT BUILT | **AGREE** |

### Corrections adopted from peers

- The pasted transcript's **"37 active picks"** is a **May 2** figure, not the current state (v3/G reconciliation). Current live: **20 curated / 4,148 raw / 263 concentration**.
- The transcript's **"61% spot-flicker dropped"** is not reproducible registry-wide; the registry rate is **2,188/28,460 = 7.7%**. The 1,147/1,882 cohort was a narrower June snapshot (v3).
- The transcript's **"last-14d −1.4%"** is superseded by live **n=751, −333.2%** (v3).
- The transcript's external quote checks were `UNVERIFIED` (sandbox blocked them). **This audit and v1 verified them** against Binance and er-api; XRP/BTC/USDCAD/NZDUSD are frozen, NEAR is real.
- `finpredict-v4`'s **"0 active picks / 26-day-old dashboard"** is **CONTRADICTED** by the live HTTP fetch and by v1. Its per-class counts (EQUITY 757, ETF 1,722, BOND 1,293) are **DB/backlog populations**, not the curated 20-row panel; do not compare them to `picks.active`.

---

## 8. Could not verify (explicit)

- **Root causes of runs still retrying** when logs were requested (Sports smoke, CI Tests, Market Beating) — `UNVERIFIED`.
- **Repo-wide warning census** (deprecation/annotation warnings across 365 workflows) — not exhaustively counted; `UNVERIFIED`.
- **FORCE_CLOSED / TIME_EXIT / FORCE_CLOSED_TOXIC** closures marked at fair market vs arbitrary exit — `UNVERIFIED`.
- **Real-money vs paper** distinction for active picks — `UNVERIFIED`.
- **Exact full-sample EQUITY PF** — three aggregators disagree (8.86 / positive-sum / 0.70); `UNVERIFIED`.
- **`summary_picks` provenance/consumers** — whether any tab consumes it beyond diagnostics; `UNVERIFIED` (root-cause code identified).
- **Browser visual rendering** — logic replicated in Python + Playwright DOM checks, not a full pixel/render audit; `UNVERIFIED` for visual-only states.
- **Mutual-fund performance** — no live picks exist; `NOT BUILT`, not a performance question.

---

## 9. Evidence inventory

| File | Contents |
|---|---|
| `sub/A_actions_health.md` + `sub/A_workflow_matrix.csv` | 365-workflow matrix, failure clusters, 19 failure logs |
| `sub/B_dashboard_freshness.md` | Payload freshness, tab inventory, metric liveness, frozen data |
| `sub/C_crypto.md` | Crypto per-symbol audit, Binance/Coinbase/CoinGecko cross-checks, zombies |
| `sub/D_non_crypto.md` | Per-class EQUITY/FOREX/ETF/BOND/FUTURES/COMMODITY/MF audit |
| `sub/E_statistical.md` + `raw/per_strategy_agg.csv` | Multiple-testing, PBO/DSR, per-class z, survivorship |
| `sub/F_sources.md` | Source authenticity matrix (Kalshi/Polymarket/copy-trader/Hyro) |
| `sub/G_peer_reconciliation.md` | Peer artifact inventory and claim reconciliation |
| `recommendations/**` | Per-class remediation plans, cross-cutting P0/P1, data contract, CI gates |
| `recommendations/peer_review/*.md` | Independent reviewer memos (4) with corrections applied in §10 |
| `raw/` | Live JSON snapshots, GitHub run JSON, workflow logs, per-symbol extracts |

---

## 10. Post-review corrections applied

Four independent reviewer subagents (crypto/commodity, equity/ETF/bond/MF, forex/futures/CI, overall) audited the archive and the peer outputs. Their memos are in `recommendations/peer_review/`. The following corrections were applied to this report:

| # | Correction | Old → New |
|---|---|---|
| 1 | Duplicate IDs | 218 groups / 55 cross-ledger → **248 groups / 297 extra rows / 56 cross-ledger** |
| 2 | "Quoted OPEN" | 123 ambiguous → **177 entry-differing quotes; 123 also non-zero PnL; 29 exact; 485 null** |
| 3 | `summary_picks` | "8/11" / "6 of 11" → **7 classes WR>100%; 9 with `wins+losses > resolved`** |
| 4 | FUTURES history | "0 closed ever" → **0 rows in `picks.recent_closed`; full history n=13 policy-clean; intrabar n=52** |
| 5 | FOREX date-only | "12" → **105/277 date-only `entry_time`** |
| 6 | FOREX block | "allowlist exists" → **allowlist has 0 call sites; 0/277 pass; 4 retired strategies emit ~95/277** |
| 7 | COMMODITY/FUTURES | New finding: both are in `BLOCKED_ASSET_CLASSES` (`quality_gates.py:1724`); COMMODITY generator uses crypto proxies |
| 8 | Mutual funds | "unbuilt" → **unbuilt in production / `origin/main`; untracked prototype exists in the main checkout** |
| 9 | v4 reconciliation | "uniformly contradicted" → **v4 is internally contradictory** (INDEX says 0 active/26 d; its own deep-dives say 20 active/14:30Z) |
| 10 | sqlite layer | Added ML-peer findings: `live_picks.db` 128/129 stale, 8 PnL sign bugs, empty `audit_trail.db` |

**Reviewer verdicts:** crypto/commodity **FAIL** (P0 can proceed; structural layer must be corrected), equity/ETF/bond/MF **FAIL** (4 corrections), forex/futures/CI **PASS conditional** (4 factual corrections), overall coherence **FAIL** (documentation conflicts, not the central conclusion). The central verdict — **FAIL / not demonstrably profitable** — survived every review.

**Do-not-apply peer fixes (reviewer vetoes):** `DELETE` ghost rows; `UPDATE TIME_EXIT → LOST, pnl_pct=0.0`; `EXPIRED_FORCE` mass rewrite; invert the ML confidence gate; unblock FUTURES without a real commodity/futures feed; add `MUTUAL_FUND` to canonical classes before a real emitter exists.

**Key URLs used:** `https://findtorontoevents.ca/audit/data/{dashboard_data,dashboard_payload,money_ready_verdict,pf_registry,anti_overfit_audit,audit_surface_truth,summary_picks,db_health,hyro_pick_performance,hyrotrader_picks,ma_strategy_leaderboard}.json`; `https://api.binance.com/api/v3/{ticker/price,klines}`; `https://open.er-api.com/v6/latest/USD`; `https://api.github.com/repos/eltonaguiar/findtorontoevents_antigravity.ca/actions/*`.

---

*Prepared for the next-stage review agent. No fabricated numbers; every figure is traceable to the archived evidence or a named peer artifact.*
