# PR4 — Overall Review: audit + recommendation coherence

**Review clock:** 2026-11-14T16:32Z
**Reviewer:** PR4 (overall consistency / master-plan input)
**Scope:** `finpredict-v2` archive `2026-11-14/finpredict-v2_20261114-1602/`, peer v1/v3/v4 archives, ML peer `updates/2026-11-14-ML-AUDIT-childlike-airport.md`, and every audit artifact modified after 2026-11-14T15:30Z.
**Constraint:** read-only review. No repo source was modified. This file is the only artifact written.

---

## PASS/FAIL — overall audit + recommendation coherence

**FAIL.**

The evidence base is strong and the negative verdict is reproducible: all independent audits land on **not money-ready / not demonstrably profitable**, and the core numbers in `MASTER_AUDIT.md` largely survive recomputation from `raw/dashboard_data.json`. However, the combined audit + recommendation package is **not internally consistent enough to implement as-is**:

- **At least 9 material numeric conflicts** (duplicate-ID counts, quoted-row definitions, `summary_picks` class counts, population labels, BOND age, `active_raw` count).
- **At least 6 contradictory fix mechanics** (`pnl_pct` null-vs-keep, dedup key, `summary_picks` denominator, canonical class field name, quote-status enum, `template.html` vs `index.html`).
- **4 destructive peer fixes** that violate this project's own "no deletion / no retro-edit" rules.
- **5 peer deliverables modified after 15:30Z are not referenced by our archive** (v1 quick-wins, v3 16:15/16:17 sets, v4 proposed fixes, ML proposed fixes, hilarious-seer).
- **2 peer fixes are affirmatively dangerous** (invert the ML confidence gate; unblock FUTURES).

This is a **documentation/coherence FAIL**, not a failure of the audit's central conclusion. The master plan should adopt the canonical resolutions in §4 before any implementation starts.

**What passes:** the five-part scorecard (Actions, active picks, frozen data, closed picks, statistical verdict) is FAIL in every sub-audit; v1/v2/v3/v4 agree on FAIL; no peer claims a real positive edge; 0/9 classes are money-ready in every surface. The headline conclusion is not in dispute.

---

## 1. Recently modified file inventory (since 2026-11-14T15:30Z)

Method: `find . -xdev -type f -newermt '2026-11-14 15:30:00'`, excluding `.git`, `node_modules`, `.kilo/worktrees`, `.worktrees`, and generated job/weather paths. Result: **43 files in the primary scan**. Peer worktrees were scanned separately because the task also requires auditing peer output.

### 1.1 Primary scan — 43 files

| Class | Count | Files / paths | Assessment |
|---|---:|---|---|
| **Peer audit output (v4)** | 20 | `audits/2026-11-14/finpredict-v4_2026-11-14-1555/`: `INDEX.md`, `actions_health_report.md`, `dashboard_data_report.md`, `dashboard_metrics_sources.md`, `market_crossref_report.md`, `crypto_deep_dive.md`, `forex_deep_dive.md`, `noncrypto_deep_dive.md`, `evidence_{db_health,intrabar_truth,money_ready_verdict,pick_summary_stats}.json`, `proposed_fixes/{crypto,forex,equity,commodity,infra,overall}/QUICK_WINS.md`, `peer_review/{2026-11-14-ML-AUDIT-childlike-airport.md,PEER_REVIEW_INTEGRATION.md}` | Peer output. Valuable raw-DB/evidence layer; several fixes are destructive and must not be applied verbatim. |
| **Peer audit output (ML)** | 8 | `updates/2026-11-14-ML-AUDIT-childlike-airport.md` + `updates/2026-11-14-ML-AUDIT-childlike-airport/proposed_fixes/{stocks,bonds,etfs,forex,crypto,mutual_funds,overall}/FIX_PROPOSED.md` | Peer output. Adds the SQLite `live_picks.db` / empty `audit_trail.db` layer. Conflicts with v4 on ML confidence and with our bond plan on mutual funds. |
| **Generated job data** | 8 | `bestiejob/FRESH_JOBS.md`, `bestiejob/jobs.json`, `bestiejob/public/{jobs.json,findjobs/jobs.json,gotjob/jobs.json}`, `bestiejob/README.md`, `bestiejob/README.BAK_2026-11-14T160754Z.md`, `bestiejob/README.BAK_2026-11-14T153352Z.md` | Generated job-board publication. Not audit evidence. Excluded from analysis. |
| **Generated logs / state** | 4 | `logs/vllm_8000.log`, `reports/peer_inbox_hourly.log`, `bestiejob/logs/cron_30min.log`, `.github/gh_monitor_state.json` | Generated telemetry. Not audit evidence. |
| **Unrelated repo change** | 2 | `tools/ai_menu.sh` (15:39), `___HELL_HEALTH_OPENCODE.MD` (16:30) | Not prediction-audit output. `___HELL_HEALTH_OPENCODE.MD` is a GitHub Actions health monitor document, not this audit. |
| **UI/recovery state** | 1 | `.kilo/agent-manager.json` (16:23) | Agent Manager persisted state. Not repo source; do not edit. |

No file under `audit_dashboard/data/` or `audit_trail/data/` was regenerated after 15:30Z. The repo copies remain stale (`audit_dashboard/data/dashboard_data.json` `generated_at = 2026-10-19T19:40:11Z`; `audit_trail/data/dashboard_payload.json` `generated_at = 2026-10-23T02:00:56Z`), while the live HTTP payload is `2026-11-14T14:30:07Z`. This is the root of the v4 "empty shell" conflict (§4, C2).

### 1.2 Peer files modified after 15:30Z but **not referenced by our archive**

Our archive only references: v1 `README.md` + `updates/2026-11-14-prediction-system-audit.md`; v3 `2026-11-14T155500Z`; v4 `INDEX.md` + 6 reports + 4 evidence JSON; ML single audit MD. The following are **new, material, and unreferenced**:

| Peer | Unreferenced files | Why it matters |
|---|---|---|
| **v1 `finpredict`** | `quick-wins/README.md`, `quick-wins/OVERALL.md`, `quick-wins/by-asset-class/{CRYPTO,FOREX,EQUITY,ETF,BOND,FUTURES,COMMODITY,MUTUAL_FUNDS}.md`, `peer-review/PEER_RECONCILIATION.md` | Adds unique or higher-priority fixes not first-class in ours: binomial CI/excluded-count disclosure (`QW-1`), `edge_ratio` reader/emitter mismatch (`QW-2`), `INSUFFICIENT` when `forward_trades==0` (`QW-3`), outlier clamp surfacing (`QW-5`), visibility-floor exposure (`QW-7`). |
| **v3 `finpredict-v3`** | `2026-11-14T161500Z/QUICK_WINS/**` (10 files) and `2026-11-14T161700Z/PEER_REVIEW/**` (10 files) | The 16:15 quick-wins are peer-reviewed at 16:17 and contain the only runnable hygiene guardian (`tools/pi_data_hygiene.py`). Our archive cited only the 15:55 audit. |
| **v4 `finpredict-v4`** | `proposed_fixes/{crypto,forex,equity,commodity,infra,overall}/QUICK_WINS.md` (6), `peer_review/{2026-11-14-ML-AUDIT-childlike-airport.md,PEER_REVIEW_INTEGRATION.md}` (2) | The proposed fixes contain the destructive SQL (`DELETE`, `UPDATE ... status='LOST', pnl_pct=0.0`) and the two dangerous policy reversals (invert ML gate, unblock FUTURES). They must be explicitly rejected in the master plan, not silently omitted. |
| **ML peer** | `updates/2026-11-14-ML-AUDIT-childlike-airport/proposed_fixes/*/FIX_PROPOSED.md` (7) | Adds the SQLite/`audit_trail.db` layer. Its mutual-fund recommendation is the opposite of ours. |
| **hilarious-seer** | `updates/2026-11-14-hilarious-seer-audit-summary.md`, `audit_quickwins/2026-11-14-hilarious-seer/{crypto,equity_others,overall}/quickwins.md` | Independent audit modified 16:06–16:15Z. Reaches FAIL and adds regime-layer and PnL-cross-reference findings. Not mentioned in `PEER_CROSSREF.md`. |
| **spice-hyena** | `forreviews_final/2026-11-14T03-25-00Z_spice-hyena/**` | Mostly Salesforce/review material, not a prediction-system audit. Cited by v3 as "review material"; not relevant to the master plan. |

Also present but not date-stamped as new content: `.kilo/worktrees/finpredict-v3/2026-11-14/finpredict/**` contains **copies** of v1/v3 files (mtime 16:07–16:20). `.kilo/worktrees/finpredict-v4/` is a checkout (all mtime 15:44), not a dated archive; v4's reports live in the main repo `audits/` tree. `deepAI`/`inspect-wt` remains unreviewable on this host.

### 1.3 Generated data explicitly excluded

Job board (`bestiejob/**`), logs (`logs/**`, `reports/**`, `bestiejob/logs/**`), GitHub monitor state, and weather/job feeds were not treated as audit evidence. No audit count in this review depends on them.

### 1.4 External v4 source worktree (outside repo root)

v4's source worktree `/home/eaguiar2015/wt-audit-prediction-system` (commit `7c80a160759`) contains `audit_output/` with 7 reports (15:52–16:02Z, byte-identical to the `audits/2026-11-14/finpredict-v4_2026-11-14-1555/` copies) and an untracked `chat_transcript.MD`. That transcript is a **2026-05-15** operations log, **not** the missing `chat_transcript_2026-11-14.md`; the user's claimed transcript remains unavailable. The external worktree is not part of the repo-root scan but is the provenance of the v4 archive.

---

## 2. Sub-audit PASS/FAIL agreement

### 2.1 Our sub-audits

| Sub-audit | Verdict | Scope |
|---|---|---|
| `sub/A_actions_health.md` | **FAIL** | 365 workflows; 24 failing/24h; 93 Alpha failures; Python 3.14 masquerade |
| `sub/B_dashboard_freshness.md` | **FAIL** | Core payload fresh 1.63h; metric fields and 10+ sidecars dead |
| `sub/C_crypto.md` | **FAIL** | 3,577 raw crypto rows, 86.7% EXPIRED, 92.9% zero PnL; NEAR real |
| `sub/D_non_crypto.md` | **FAIL** | Every non-crypto class fails pricing/staleness/status/class taxonomy |
| `sub/E_statistical.md` | **FAIL** | Policy-clean n=22,941, WR 42.21%, PF 0.2657, z=−23.60 |
| `sub/F_sources.md` | **FAIL** (partial authenticity) | Kalshi real; Polymarket wallet dead/410; copy-trader hidden; Hyro dead |
| `sub/G_peer_reconciliation.md` | **PASS** | Peer **artifact availability**, not system health |

**Agreement:** A–F all FAIL; G's PASS is a different question (were peer artifacts available and reconcilable?). No sub-audit supports a positive read. The four primary sub-audits (A–D) agree on FAIL.

### 2.2 Peer audits

| Audit | Overall verdict | Active-pick claim | Key caveat |
|---|---|---|---|
| v1 `finpredict` | FAIL | 20 curated / 4,148 raw | Uses live payload; headline 41.8% WR / PF 0.94 |
| v2 ours | FAIL | 20 curated / 4,148 raw / 691 OPEN | Policy-clean PF 0.2657; most precise root causes |
| v3 `finpredict-v3` | FAIL | 20 curated; per-class "ALIVE/STALE/DEAD" | "ALIVE" means feed alive, not performance pass |
| v4 `finpredict-v4` | FAIL | **0 active** (stale repo snapshot) | Reads `audit_dashboard/data/*` and `picks_now*`, not live HTTP |
| ML `childlike-airport` | FAIL | 129 SQLite active, 128 stale | Different data store (SQLite), not the dashboard |

**Agreement:** all five independent audits agree FAIL / not money-ready. The only "disagreement" is population and snapshot choice, not the verdict.

---

## 3. Master conflict table

Every row is resolved to one adopted value/interpretation. "Recomputed" means re-derived from `raw/dashboard_data.json` during this review with Python `json.load`; no value is estimated.

| # | Conflict | Evidence | Adopted resolution |
|---|---|---|---|
| **C1** | `G_peer_reconciliation` says **PASS** while the others say FAIL | `sub/G...:11` PASS is explicitly scoped to "peer artifacts are available and reconcilable" | Not a system verdict. **Adopt:** overall system = FAIL; G = PASS only for peer-artifact availability. Never quote G as an overall PASS. |
| **C2** | v4: **0 active picks, dashboard_data 26 days stale**; v1/v2/v3: **20 curated, 14:30Z fresh** | v4 `dashboard_data_report.md:4` reads `/home/eaguiar2015/wt-audit-prediction-system/audit_dashboard/data/`; repo copy verified `generated_at 2026-10-19T19:40:11Z`. Live HTTP `https://findtorontoevents.ca/audit/data/dashboard_data.json` = `2026-11-14T14:30:07Z`, 20 active. | **Adopt live HTTP:** 20 curated active, payload 1.63h old at capture. Treat repo JSON copies as stale build artifacts. v4's "empty shell" describes the repo snapshot, not the deployed page. |
| **C3** | v4 class counts **EQUITY 757 / ETF 1,722 / BOND 1,293 / COMMODITY 4 / FUTURES 0** vs curated **2 / 10 / 0 / 2 / 1** | v4 `noncrypto_deep_dive.md:39-41` is `picks_now_live_pnl.json`; curated counts are `picks.active` | **Adopt:** separate populations. Never compare v4's `picks_now` counts to curated or `active_raw`. Label every count with its surface. |
| **C4** | v4: COMMODITY **DEAD since June**, FUTURES **0 live**; ours: COMMODITY **27 OPEN** at 14:24Z, FUTURES **3 OPEN** at 13:06Z | v4 `noncrypto_deep_dive.md:17-18` uses June `picks_now`; `raw/dashboard_data.json` has 27 COMMODITY OPEN / 3 FUTURES OPEN | **Adopt live payload.** v4 noncrypto is a **June baseline**, not today's state. |
| **C5** | BOND newest **4.09d** vs **1.9d** vs **25.5h** | 4.09d = `recent_closed` newest close `2026-11-10T13:52:26Z` (D:268); 1.9d = `picks_now` Nov 12 cohort; 25.5h = `active_raw` seeds (D:266) | **Adopt all three, labelled:** closed feed 4.09d; raw active seeds 25.5h; 0 curated; `picks_now` 1.9d is a third population. |
| **C6** | FUTURES "no date": v1 says UI renders no date; v2 says not reproduced; v4 says 0 live | `picks.active` ES=F has `timestamp 2026-11-14T13:06:02Z` and renders `Nov 14, 8:06 AM` (B:§4); `entry_time`/`signal_time` are date-only `2026-11-14`; 8 EXPIRED futures rows are date-only | **Adopt v2 nuance:** the panel renders a time; the **underlying entry/signal timestamp is date-only** and must be rejected at ingest. v4 sees 0 because it uses `picks_now`, not `picks.active`. |
| **C7** | Headline performance: **41.8% WR / PF 0.94 / Sharpe −1.31 / EW −99%** vs **42.21% WR / PF 0.2657 / z −23.60** | 41.8/0.94 = summary on `valid_closed_picks` 7,914/16,126 (v1 §0); 42.21/0.2657 = policy-clean net registry n=22,941 (E §6.1) | **Adopt both, labelled.** Report `summary_valid_closed` and `policy_clean_net` side by side; never mix PF 0.94 with PF 0.27. Closed-feed `recent_closed` is a third cohort (42.2% WR, −469.5% sum). |
| **C8** | Multiple-testing N: **~260 lucky** vs **658 scored / 32.9 expected FP**; overfit **31/38** vs **69/80** | v1 uses 361 families + 285 baby + mutations; v2 uses 658 registry strategies; anti-overfit has a June 38-row run and a current 80-row run | **Adopt:** 658 scored strategies → 32.9 expected false positives at α=0.05; 21 "Bonferroni survivors" are the single-source cluster; report both PBO runs (`31/38` June, `69/80` current) with dates. |
| **C9** | CRYPTO z: **−7.1** (v1) vs **−22.69** (v2) | v1 cites the `inspect-wt` June snapshot; v2 recomputes policy-clean n=21,988 (E:302) | **Adopt −22.69** for the live policy-clean cohort; keep −7.1 only as a historical June comparison. |
| **C10** | Survivorship: **49%** vs **63%** vs **6.2%** | 49% = 7,914/16,126 integrity-passed closed; 63.2% = 90,523/143,156 open/never-resolved; 6.2% = 301/4,820 track-record symbol-days | **Adopt three distinct labels:** gate-pass rate 49%; open-pick non-resolution 63.2%; track-record resolution 6.2%. Do not use them interchangeably. |
| **C11** | `active_raw` **4,148** vs **4,310** vs **263** vs **20** | 4,148/3,851 IDs = `picks.active_raw`; 4,310 = `picks_now_live_pnl`; 263 = `concentration_summary.total_active`; 20 = `picks.active` | **Adopt 4,148 / 3,851** for dashboard `active_raw`; 691 OPEN; 20 curated. Quote the surface name with every count. |
| **C12** | Duplicate IDs **218** (MASTER §3, C:172) vs **248** (P0-8, DATA_CONTRACT); cross-ledger **55** vs **56** | Recomputed: **248** duplicate-ID groups, **297** extra rows (4,148−3,851); **56** IDs in both `active_raw` and `recent_closed` | **Adopt 248 / 297 / 56.** The 218 and 55 figures are stale and must be corrected in `MASTER_AUDIT.md`, `sub/C_crypto.md`, and crypto P0-4. |
| **C13** | "Quoted OPEN": **123** (MASTER bullet, v1) vs **175** (crypto P0) vs recomputed **177** | Recomputed: 691 OPEN; 177 have `current_price>0`, `entry_price>0`, and `abs(current−entry)≥1e-9`; of those, **123** also have non-zero `pnl_pct`. Exact `current==entry`: **29**, not 31. | **Adopt definitions:** `quoted_entry_differing = 177 (25.6%)`; `quoted_and_nonzero_pnl = 123 (17.8%)`; `exact = 29`; `null = 485`. Fix crypto P0's 175/31 and keep MASTER's 123 only with the non-zero-PnL definition. |
| **C14** | `summary_picks` "impossible WR": **6/11** (D top finding), **7** (P0-2), **8/11** (B, equity P0-4) | Recomputed from `raw/summary_picks.json`: **7** classes have WR>100% (BOND 127.8, COMMODITY 240.2, EQUITY 162.4, ETF 232.9, FOREX 147.0, FUTURES 363.9, INDEX 1141.2); **9** classes have `wins+losses > resolved` (add CRYPTO 98.3 and MEME 40.8) | **Adopt 7 >100%; 9 impossible denominator.** Correct B's "8/11", D's "6 of 11", and P0-2's "8 classes". |
| **C15** | Per-class verdict: v3 says EQUITY/ETF/FOREX/COMMODITY **ALIVE**; v2 D says **FAIL** | v3 "ALIVE" = emitter produces rows; D "FAIL" = pricing/status/taxonomy integrity | **Adopt two axes:** `FEED_ALIVE` (v3) and `PERFORMANCE/INTEGRITY = FAIL` (v2). A live feed is not a passing class. |
| **C16** | ML confidence: v4 says inverted and proposes **invert the gate**; ML peer says code is sound and the problem is **data** | v4 overall QW-4 / crypto MF-2; ML audit §5 says `ml_ranker_fixed.py` and `gatekeeper.py` are mathematically sound; v4's own peer integration §2 agrees it is a data bug | **Adopt ML peer:** do not invert the production gate. Fix labels/PnL/staleness first, then re-measure the confidence→WR curve. |
| **C17** | Credentials: ML peer says **no exposure**; P0-9 finds **3 tracked hardcoded Google API keys** and `dbpasses.txt` not ignored | ML peer only searched for `dbpasses.txt`; P0-9 names `STOCKSUNIFY/scripts/lib/stock-api-keys.ts`, `STOCKSUNIFY/STOCKSUNIFY2/...`, `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS2/scroll-fix.js` | **Adopt P0-9:** rotate the three keys, move to env/secrets, add `dbpasses.txt`/`*dbpasses*` to `.gitignore`. Do not print values. ML peer's "nothing to fix" is a scope gap. |
| **C18** | Mutual funds: ML peer proposes **add `MUTUAL_FUND` class + strategies + schema**; our bond plan says **de-advertise + NOT_BUILT, do not add** | No MF picks in any feed; `mutual_fund_ranker.py` exists only **untracked in the main checkout** (verified: not in worktree, not in `origin/main`); no page; NAV-only instrument cannot support intraday TP/SL | **Adopt de-advertise / NOT_BUILT.** Do not add `MUTUAL_FUND` to `CANONICAL_ASSET_CLASSES` or `_PER_ASSET_CLASSES`. A research-only NAV page is optional, with a coverage gate and no price/PnL fields. |
| **C19** | FUTURES policy: v4 commodity says **unblock FUTURES**; our plans say **keep frozen / do not unblock** | `quality_gates.py` blocklist and `money_ready_verdict` policy-frozen; FUTURES has 0 primary-feed closed rows and 3 weekend seeds | **Adopt keep frozen.** Do not remove from `BLOCKED_ASSET_CLASSES`; build a shadow promotion gate instead (bond P1-2 pattern). |
| **C20** | `summary_picks` formula description: B says "wins/(wins+losses)-style"; actual code is `wins/resolved` | `tools/sync_summary_picks_json.py:161` is `100*wins/resolved`; raw values confirm (BOND 92/72=127.8%) | **Adopt `wins/resolved`** as the defect description. The fix must use one terminal population, not a `wins/(wins+losses)` denominator. |
| **C21** | Mutual-fund ranker existence: D says it exists (23,931 B); bond doc says absent from worktree/`origin/main` | Verified: file exists in main checkout only, **untracked**; `git ls-files` empty; absent from `origin/main` and `finpredict-v2` worktree | **Adopt bond doc:** treat as an uncommitted prototype. Do not cite it as shipped or build production on it without review. |

---

## 4. Recommendation coherence and canonical fix ownership

### 4.1 Shared contracts the four per-class plans must obey

1. **Quote contract** — `quote_status`, `quote_source`, `quote_at`, `quote_age_minutes`, `pnl_status`. Defined in `recommendations/overall/DATA_CONTRACT.md` §2.2. Current enum in the contract (`QUOTED|UNQUOTED`) is **too narrow** for the per-class plans (`LIVE|LAST_CLOSE|STALE|UNQUOTED`). The contract must be amended to the five-value set before implementation.
2. **Timestamp contract** — `signal_at`, `entry_at`, `closed_at`, `quote_at`, `entry_at_precision`. Defined in `DATA_CONTRACT.md` §1.
3. **Class routing contract** — one canonical field `canonical_asset_class` + `asset_class_source` + `class_mismatch`/`class_mismatch_reason`. `canonical_asset_class` is the DATA_CONTRACT name; `class_canonical` is a second name and must be rejected.
4. **Dedup contract** — identity dedup (ID, for counts) and economic dedup (strategy+symbol+direction+UTC-day+entry-price tolerance, for display). Defined in `DATA_CONTRACT.md` §6 and `P0_QUICK_WINS.md` P0-8.
5. **Metric population contract** — every WR/PF carries `n`, `n_emitted`, `coverage_pct`, `population`, `single_source_pct`, `computed_at` (`DATA_CONTRACT.md` §7).
6. **Honesty labels** — `INSUFFICIENT_DATA`, `DATA_STALE`, `NOT_BUILT`, `UNQUOTED`, `LAST_CLOSE`, `SINGLE_SOURCE_ARTIFACT`.

### 4.2 Duplicated fixes — collapse to one owner

| Fix | Appears in | Canonical owner (single source of truth) | Action for other docs |
|---|---|---|---|
| `summary_picks` population | P0-2, crypto P0-6, equity P0-4, forex P1-7, bond QW-3 | **P0-2** → `tools/sync_summary_picks_json.py:63-65,149-164` | Replace each duplicate with a one-line reference to P0-2. Retire crypto's `wins/(wins+losses)` variant; it contradicts bond QW-3 and masks the cohort mismatch. |
| Quote provenance + `UNQUOTED` | P0-5, crypto P0-1/P0-2, equity P0-1/P0-3, forex P0-2, bond QW-7 | **DATA_CONTRACT §2.2** + **P0-5** final pass in `audit_trail/dashboard_generator.py:1618-1846`, `:17481-17485`, `:16953` | Per-class docs keep only class-specific behavior (`LAST_CLOSE` for futures, weekend close for ETF). Delete duplicate final-pass code. |
| Render contract | crypto P0-2, equity P0-2/P0-3, bond QW-1 | **`audit_dashboard/template.html`** (`:8889-8905`, `:9134-9145`, `:4946`), regenerated to `index.html` via `dashboard_generator.py:18582-18599` | Equity's `index.html:...` line references are invalid as edit targets; patch the template. |
| Timestamp rejection | forex P0-1; DATA_CONTRACT §1 | **forex P0-1** → `dashboard_generator.py:8136-8154`, `:8351-8352` | Keep one implementation; other classes do not re-implement `_entry_ts_keys`. |
| Class routing shadow audit | crypto P1-3, equity P0-6, forex P0-3/P1-1 | **`alpha_engine/asset_class.py`** + `dashboard_generator.py:3645-3680`; one shadow report | Standardize on `canonical_asset_class`; drop `class_canonical`. Do not enforce in P0. |
| Dedup | P0-8, crypto P0-4, forex P0-5/P1-4, bond QW-5 | **P0-8 + `DATA_CONTRACT.md` §6**; key `(strategy, symbol, direction, trade_date, round(entry,4))` from `tools/build_pf_registry.py:818-835` | Bond QW-5's `(asset_class, symbol, direction, strategy)` key is too coarse and would collapse legitimate re-entries; replace it with the canonical key + day/price window. Forex P0-5 exact-ID dedup remains a subset of the identity tier. |
| Vacuous PASS / `NOT_BUILT` | P0 rank 7, bond QW-1/QW-2, equity P1-6 | **bond QW-1/QW-2** → `dashboard_generator.py:6824-6826`, `template.html:4946`, `summary.unbuilt_asset_classes` | One implementation. Do not create a second `status` enum. |
| Sidecar freshness | P0-7, v1 QW-4, v3 GLOBAL #2, v4 MF-3 | **P0-7** → `sidecar_freshness_manifest.json` + `tools/assert_sidecar_freshness.py` | v1/v3/v4 items become references; do not add three manifests. |
| Open-pick backlog | P1-2, v4 MF-1/MF-4, v3 GLOBAL #5 | **P1-2** → bounded resolver batches / explicit `TIME_EXIT`/`EXPIRED_NO_DATA`/`VOID` | Delete v4's `UPDATE ... status='LOST', pnl_pct=0.0` approach; it fabricates outcomes. |
| FOREX policy wiring | forex P0-6/P1-2, v4 forex QW-1/QW-2, v4 overall MF-5 | **forex P0-6** → `alpha_engine/non_crypto_policy.py:1026-1040`, `copy_trader_intel/non_crypto_consensus.py:143-147` | v4's `alpha_engine/non_crypto_consensus.py` path is wrong; the live consensus module is `copy_trader_intel/non_crypto_consensus.py`. |
| Alpha Engine repair | P0-1, v4 overall MF-3 / infra QW-1 | **P0-1** → `alpha_engine/scanner.py:2937-2942` (log-proven `KeyError: 'LONG'`) | v4's `cancel-in-progress` theory is a secondary scheduler issue; do not replace the log-proven root cause with it. |
| ML confidence | v4 overall QW-4 / crypto MF-2; ML peer §5 | **No code owner yet**; ML peer audit is the authority | Do not invert the gate. Add a data-quality/label fix first, then re-measure. |
| Mutual funds | bond QW-2 vs ML peer P0/P1 | **bond QW-2** | Do not add `MUTUAL_FUND` to canonical classes. |

### 4.3 Contradictory fixes that must be retired (do not implement)

1. **`DELETE` ghost rows** (v4 overall QW-2, infra QW-5) — violates "no destructive cleanup". Quarantine/tag and archive.
2. **`UPDATE ... status='LOST', pnl_pct=0.0` for TIME_EXIT** (v4 overall MF-4) — fabricates outcomes and retro-edits history.
3. **`UPDATE at_raw_picks SET status='EXPIRED_FORCE'`** (v4 equity 1.1) — mass status rewrite; not allowed in P0.
4. **`UPDATE ... status='EXPIRED'` zombie purge** (v4 crypto QW-3) — same problem.
5. **Unblock FUTURES** (v4 commodity 1.1) — policy reversal without a promotion gate.
6. **Invert the ML confidence filter** (v4 overall QW-4, crypto MF-2) — contradicted by the ML code review; fix data first.
7. **`wins/(wins+losses)` denominator** (crypto P0-6, equity P0-4) — masks the cohort mismatch; bond QW-3 explicitly forbids it.
8. **Patch generated `audit_dashboard/index.html`** (equity P0-2/P0-3) — template is the source; `index.html` is generated.
9. **Add `MUTUAL_FUND` to canonical classes** (ML peer) — no data, no page, NAV-only; de-advertise instead.
10. **Delete `db_freshness.json` in P0** (v4 infra MF-3) — hide/label first; deletion is a P1 lifecycle decision.
11. **Bond dedup key without date/price** (bond QW-5) — collapses legitimate re-entries; use the canonical economic key.
12. **`class_canonical` field** (forex P0-3) — second canonical field; use `canonical_asset_class`.

---

## 5. Top-10 master-plan actions (next agent)

Ranked by (impact ÷ risk), with dependencies and explicit prohibitions. P0 = truth/reliability only; no strategy or resolver behavior changes.

| Rank | Action | Canonical target | Depends on | Must NOT do |
|---:|---|---|---|---|
| **1** | Guard the FX direction bucket (`KeyError: 'LONG'`) | `alpha_engine/scanner.py:2937-2942` | none | Do not change the 70% BUY/SELL majority rule; do not disable the Alpha workflows; do not treat `xgboost` as the fatal error (import is already guarded). |
| **2** | One-population `summary_picks` + assert/clamp | `tools/sync_summary_picks_json.py:63-65,149-164` | none | Do not divide by `wins+losses`; do not retro-edit historical values; do not leave `wins+losses > resolved` unasserted. |
| **3** | Fix Python 3.14 masquerade + add `xgboost` to FAST | `.github/workflows/signal_tracking.yml:35`, `.github/workflows/alpha-engine-fast.yml:35,40` | none | Do not bulk-edit all 197 `update-environment: false` files in P0; do not bump `pandas` before the interpreter guard passes. |
| **4** | Space the audit-dashboard cron + add a fresh-payload preflight | `.github/workflows/audit-dashboard.yml:5,41,42,55` | none | Do not re-enable the `push:` trigger; do not raise `timeout-minutes`; keep `cancel-in-progress: false`. |
| **5** | Quote-provenance Release A + `UNQUOTED`/`LAST_CLOSE` render | `DATA_CONTRACT.md` §2.2 + `dashboard_generator.py:1618-1846`, `:17481-17485`, `:16953`; `audit_dashboard/template.html:8889-8905`, `:9134-9145` | none (Release A additive) | Do not null `pnl_pct` in Release A (downstream may `float(None)`); do not backfill `current_price` from `entry_price`; do not patch generated `index.html`; do not claim a real mark without `quote_at`/`quote_source`. |
| **6** | Populate `sym_track_*` from the closed ledger | `dashboard_generator.py:14551`, `:1830-1832` | #5 (labels) | Do not pass the active slice; cap to 90 days; do not change EDGE/GOLDEN thresholds. |
| **7** | Identity dedup + quarantine EXPIRED (keep all rows) | `dashboard_generator.py` `_pick_dedup_key` + `:17481-17485`; `audit_dashboard/data/expired_archive/YYYY-MM.jsonl` | #4 (stable build) | Do not delete rows; do not use bond QW-5's coarse key; do not dedupe legitimate same-day re-entries at different entry prices. |
| **8** | Sidecar freshness manifest + hide-if-stale | P0-7; `audit_dashboard/data/sidecar_freshness_manifest.json`; `tools/assert_sidecar_freshness.py` | none | Do not delete sidecars in P0; do not display the 220.7-day HyroTrader snapshot as current; do not hide without a visible "stale, hidden" label. |
| **9** | Secret hygiene: rotate the 3 tracked keys, ignore `dbpasses.txt` | `STOCKSUNIFY/scripts/lib/stock-api-keys.ts`, `STOCKSUNIFY/STOCKSUNIFY2/scripts/lib/stock-api-keys.ts`, `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS2/scroll-fix.js`; `.gitignore` | operator coordination | Do not print or commit key values; do not read `~/dbpasses.txt`; do not rotate without coordinating live consumers. |
| **10** | Shadow class-routing audit + `NOT_BUILT` labels | `alpha_engine/asset_class.py`, `dashboard_generator.py:3645-3680`; `summary.unbuilt_asset_classes` | #5 (labels) | Do not enforce class moves in P0; do not add MUTUAL FUNDS to canonical classes; do not unblock FOREX/FUTURES/BOND; keep `COMMODITY_DISPLAY_BUCKET=1`. |

**Immediately after the top 10 (not in P0):** `patch_plan/P1-2` bounded open-pick resolution (90,523 unresolved), P1-1 write-time data contract, P1-6 honest statistics (time-indexed PBO/DSR, `n_trials=658`, Reality Check), `forex_futures.md` P1-2 policy wiring.

### 5.1 Sequencing constraints

- #1–#4 are independent and can ship in one batch; they do not touch data consumers.
- #5, #6, #7, #8, #10 share the same generator release; ship them behind flags in one build to avoid multiple published-number changes.
- #9 can run in parallel but needs operator approval.
- Do not start Phase 3 (strategy tuning) before #5–#7 and P1-2 are green: tuning on frozen 0.00% marks just fits noise.

### 5.2 Evidence required before any "profitable" claim

A claim of profitability is only allowed when **all** of the following are true for **at least one class**:

1. **Time-ordered ledger** with `entry_at`, `closed_at`, `exit_price`, `resolution_kind`; no date-only rows; no `ORDER BY strategy` pseudo-PBO.
2. **Population:** policy-clean, deduped, net of slippage/fees (`pnl_basis=NET`), with `n`, `n_emitted`, `coverage_pct` and a single-source flag.
3. **Sample:** Tier-2 minimum **n ≥ 100** (prefer n ≥ 200) for the class; n < 30 is `INSUFFICIENT`, not a win rate.
4. **Multiple testing:** PBO/DSR on a time-indexed T×S matrix with `n_trials ≥ 658`; Reality Check (`arch`) actually runs; the result survives a pre-registered Bonferroni/BH-FDR threshold.
5. **Independence:** `single_source_pct < 0.95` (hard reject at ≥0.95); ideally `< 0.40` top-source share.
6. **Out-of-sample:** ≥ 90 days of forward/paper accrual with no look-ahead; walk-forward OOS PF within 15–20% of IS; random-entry same-asset/direction null beaten at p < 0.05.
7. **Data integrity:** quote coverage ≥ 95% for crypto majors and ≥ 80% overall; no frozen `current_price == entry_price` displayed as 0.00%; no `summary_picks` WR > 100%; no duplicate IDs; no ghost cohorts.
8. **Survivorship:** resolved/emitted ratio published and > 60%; the 63.2% open backlog is resolved or explicitly bounded.
9. **Replication:** recomputed independently from MySQL + JSON (not from a dashboard aggregate), with the file hashes and clocks recorded.
10. **Real vs paper:** the real-money/paper distinction is resolved; fills, spreads, and financing are documented.

**Does not count as evidence:** `summary_picks` WR; the 3,500-row capped `recent_closed` feed; the 80-day-stale `at_signal_outcomes`; a single-source sleeve with n < 50; any number produced after a filter that was applied to active but not closed rows.

---

## 6. Completeness check — user questions still unanswered or partial

| Original question | Status | Where / gap |
|---|---|---|
| Are the crypto and non-crypto stats real? | **Partial** | `MASTER_AUDIT.md` §6: computed from real data but not trustworthy; policy-clean PF 0.26 / WR 42.2%. Still no class-level forward OOS; "real" is answered as "real inputs, invalid performance." |
| Are "recent picks" per class actually recent? | **Partial** | Signal ages are fresh (1.4–3.6h); prices are frozen; raw inventory median 88.7d. The raw-OPEN median (30.8h) vs all-raw median (88.7d) distinction needs to be stated every time. |
| FUTURES shows 1 active pick with no date? | **Answered with nuance** | Not reproduced on the live table (renders `Nov 14, 8:06 AM`); `entry_time`/`signal_time` are date-only. Origin of the user's observation is `UNVERIFIED`. |
| BOND picks were 4 days ago? | **Partial** | Confirmed for the closed feed (4.09d); `active_raw` seeds are 25.5h; 0 curated. If the user meant "active", the answer is different. |
| Crypto "1.9h ago" — true? | **Answered** | True as signal age; false as price freshness. |
| Everything except NEAR/XRP/USDCAD/NZDUSD/BTC ~0% — stale? | **Answered** | Yes: identity/stale artifact, not flat performance. FX has genuinely tiny moves, but the stored `current==entry` is still a copy. |
| Are Edge / Track / FWD WR / FWD N alive? | **Answered** | Structurally dead: EDGE 0/20, Track 2/20, FWD WR 2/20, FWD N 90% zero. |
| Is Kalshi MTF consensus real? | **Partial** | Real code + live API + real entries; **0 resolved outcomes** and already weighted in consensus. Performance is unvalidated. |
| Is NEARUSDT 3.16% real and plausible? | **Answered** | Yes; entry inside Binance range; ~3% move plausible; quote ~2h stale. |
| Mutual funds? | **Answered as absent / `NOT_BUILT`** | No live picks, no page; untracked prototype only. No performance possible. |
| Real-money vs paper for active picks | **Unanswered / `UNVERIFIED`** | `MASTER_AUDIT.md` §8. This is material to any "profit" claim. |
| Exact full-sample EQUITY PF | **Unanswered / `UNVERIFIED`** | Aggregators disagree: 8.86 / 0.70 / positive-sum / 46.1% / 47.0%. Do not "fix" n=8 until the producer is identified. |
| FORCE_CLOSED / TIME_EXIT fairness | **Unverified** | Whether exits are marked at fair market vs arbitrary. |
| `summary_picks` consumers | **Unverified** | Whether any tab consumes it beyond diagnostics. |
| Browser visual rendering | **Unverified** | Logic replicated in Python/Playwright DOM, not a pixel/render audit. |
| Root causes of CI runs still retrying | **Unverified** | Sports smoke, CI Tests, Market Beating were mid-retry when logs were pulled. |
| Repo-wide warning census | **Unverified** | Not exhaustively counted. |
| "Quick wins + proposed fix per asset class and overall" | **Answered in form, not yet coherent** | Delivered in `QUICK_WINS.md` + 4 per-class plans + `P0/P1`; this review found the mechanics conflicts that must be resolved first. |

---

## 7. UNVERIFIED

- **v4's "0 active / 26-day dashboard"** is verified as a **repo-copy** fact (`generated_at 2026-10-19T19:40:11Z`), not a live-deploy fact. Why the deployed site is fresher than the repo copy (separate build/deploy path?) is `UNVERIFIED`.
- **Which JSON file the deployed `/audit` page actually serves** (repo copy, FTP copy, or runtime build) is `UNVERIFIED`; the HTTP payload is fresh, but the deployment path was not traced.
- **Root cause of the 93 Alpha failures beyond the log-proven `KeyError: 'LONG'`** (Binance 451, CoinMetrics 400/403, `xgboost` warning) is partially verified; the interaction order is `UNVERIFIED`.
- **Exact `summary_picks` post-fix value** for each class — not predicted; the archived file only proves the old values are invalid.
- **Whether `summary_picks` is consumed by any live tab** — `UNVERIFIED`; the fix changes a published number.
- **Real-money vs paper** for active picks — `UNVERIFIED`.
- **Exact full-sample EQUITY PF** — three aggregators disagree; `UNVERIFIED`.
- **FORCE_CLOSED / TIME_EXIT / FORCE_CLOSED_TOXIC** exit fairness — `UNVERIFIED`.
- **Browser visual rendering** — `UNVERIFIED` beyond DOM/text assertions.
- **`data/live_picks.db` (SQLite) refresh path** — ML peer verified 128/129 rows 172 days stale; whether any consumer reads it in production was not traced.
- **`hilarious-seer` audit** — new peer output; its claims were not re-derived, only checked for verdict agreement.
- **`deepAI`/`inspect-wt` Windows archive and branch** — not on this Linux host; its `.patch` and per-class fixspecs are unreviewable here. The only file named `chat_transcript.MD` on this host is a **2026-05-15** log in `/home/eaguiar2015/wt-audit-prediction-system/`, not the claimed 2026-11-14 transcript.

---

## 8. Appendix — recomputations used in this review

Source: `raw/dashboard_data.json` (`generated_at 2026-11-14T14:30:07Z`), read with Python `json.load`. No sampling; full arrays.

```text
picks.active        20
picks.active_raw  4,148
picks.recent_closed 3,500
active_raw status: EXPIRED 3,377 | OPEN 691 | SL_HIT 55 | TP_HIT 25
unique IDs 3,851; duplicate-ID groups 248; extra rows 297
IDs in both active_raw and recent_closed: 56
OPEN price state: null 485 | exact current==entry 29 | entry-differing 177
OPEN with non-zero pnl and entry-differing: 123 (17.8%)
active panel: pnl==0 19/20; current==entry 7/20
raw: zero/null entry 85; null current 3,584; pnl==0 3,832
```

Per-class OPEN price state (frozen = null + exact):

```text
CRYPTO     402 open: quoted 68, exact 5,  null 329, frozen 334 (83.1%)
EQUITY      94 open: quoted 54, exact 14, null 26,  frozen 40  (42.6%)
ETF         30 open: quoted 15, exact 4,  null 11,  frozen 15  (50.0%)
FOREX      118 open: quoted 25, exact 3,  null 90,  frozen 93  (78.8%)
FUTURES      3 open: quoted 0,  exact 1,  null 2,   frozen 3   (100.0%)
BOND        15 open: quoted 6,  exact 0,  null 9,   frozen 9   (60.0%)
COMMODITY   27 open: quoted 9,  exact 2,  null 16,  frozen 18  (66.7%)
```

Per-class duplicate trade-key groups (symbol+strategy+direction) / extra rows:

```text
CRYPTO 271/2,908 | FOREX 67/198 | EQUITY 21/60 | ETF 3/3
FUTURES 2/7 | BOND 6/9 | COMMODITY 11/26
```

`summary_picks.json` (full file, 11 classes):

```text
WR > 100%: BOND 127.8, COMMODITY 240.2, EQUITY 162.4, ETF 232.9,
           FOREX 147.0, FUTURES 363.9, INDEX 1141.2  -> 7 classes
wins+losses > resolved: the 7 above + CRYPTO (24,008 vs 10,444)
                        + MEME (79 vs 76)              -> 9 classes
```

Repo-copy freshness (not live):

```text
audit_dashboard/data/dashboard_data.json      generated 2026-10-19T19:40:11Z
audit_trail/data/dashboard_payload.json       generated 2026-10-23T02:00:56Z
audit_dashboard/data/summary_picks.json       generated 2026-11-12T18:18:51Z
audit_dashboard/data/money_ready_verdict.json generated 2026-11-12T18:18:02Z
```

---

*Prepared for the master-plan agent. This review does not modify source and does not endorse any destructive or retroactive fix. All adopted numbers are either recomputed above or explicitly attributed to a named archive.*
