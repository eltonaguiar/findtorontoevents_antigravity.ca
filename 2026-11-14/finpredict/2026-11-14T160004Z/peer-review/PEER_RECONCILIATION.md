# Peer-Work Reconciliation (2026-11-14) — subtree `finpredict`

Review of all four sibling audits + the `inspect-wt` transcript agent, cross-referenced against the live payload and each other. As-of ~16:25Z. This updates my own `updates/2026-11-14-prediction-system-audit.md` (§10 corrected below).

## Peer artifact map

| Peer | Location | Contents | Commit status |
|---|---|---|---|
| `finpredict` (me) | `.kilo/worktrees/finpredict/2026-11-14/finpredict/…` | full audit + quick-wins | pushed to main (`40fea73312f`, `92720c6fdd9`) |
| `finpredict-v2` | `.kilo/worktrees/finpredict-v2/2026-11-14/finpredict-v2_20261114-1602/` | `sub/A..G` (incl. peer-reconciliation), `recommendations/patch_plan/P0_QUICK_WINS.md`, `recommendations/overall/DATA_CONTRACT.md`, `raw/` evidence | on disk (branch `finpredict-v2`) |
| `finpredict-v3` | `.kilo/worktrees/finpredict-v3/2026-11-14/finpredict-v3/…` | data-hygiene guardian (runnable) + remediation plan | pushed to main |
| `finpredict-v4` | `audits/2026-11-14/finpredict-v4_2026-11-14-1555/` (main repo `audits/`) | 7 deep-dives + 6 `proposed_fixes/*/QUICK_WINS.md` + peer_review of ML audit | **uncommitted** |
| `inspect-wt` | `.inspect-wt/` (June snapshot) + pasted transcript | 5-turn audit | n/a |
| `deepAI` (= `inspect-wt`, **Windows host**) | `E:\findtorontoevents_antigravity.ca\2026-11-14\{inspect-wt_20261114_1058, deepAI_proposed_fixes_20261114_1612}\` + worktree `.inspect-wt` | findings archive (summary.MD + 5 per-class summary MDs + chat_transcript) + proposed fixes (P0–P3 README, 8 `fixspecs/`, per-asset-class quick-wins, **a real `.patch`** for hyro-pick-perf freshness tripwire) | local branch `audit/live-audit-2026-11-14` (3 commits `fcac1d9017`, `5ef470dbb3`, `0cd7a1204e`) — **NOT pushed to origin** |

### deepAI / inspect-wt peer — UNREVIEWABLE from this host

The `deepAI` agent runs on the user's Windows machine (`E:\…`, `C:\Users\zerou\Desktop\…`). Its files and its branch `audit/live-audit-2026-11-14` are **not on this Linux host** (`/home/eaguiar2015/findtorontoevents_antigravity.ca/2026-11-14/inspect-wt_*` and `.inspect-wt/` do not exist; `git ls-remote origin` shows no `live-audit`/`deepai` branch). Its `chat_transcript_2026-11-14.md` is likewise absent (matches v2's and v4's "NOT FOUND" notes).

**To review it:** the deepAI agent must `git push` its branch (it says it is "safe to push for peer review whenever you say so") or sync the folders to this host. Once pushed, fetch and review: (1) `summary.MD` + 5 per-class summaries, (2) `deepAI_proposed_fixes_20261114_1612/README.md` (P0–P3), (3) the `fixspecs/` (8 cross-asset) and per-asset-class quick-wins, (4) `patches/0001-hyro-pick-perf-freshness-tripwire.patch` — which corroborates my hyro staleness finding (hyro_pick_performance.json 6.6d stale) and is the only peer to ship an actual code patch.

## Corrections to my own doc (adopted from peers)

Three figures I carried from the `inspect-wt` transcript are **superseded/stale** and are corrected here (also edited in `updates/…audit.md` §10):

1. **"61% spot-flicker (1,147/1,882)" → NOT reproducible.** Registry-wide flicker is **7.7%** (2,188 dropped / 28,460 closed, `pf_registry.json` generated 2026-11-12). The 1,147/1,882 pair is not on disk. Drop it.
2. **"June last-14d ≈ −1.4%" → superseded.** Live last-14d (`closed_at ≥ 2026-11-01`) is **n=751, sum −333.2%, mean −0.44%** — ~240× worse. The −1.4% is a stale June 191-trade cohort.
3. **"37 active in June" → actually May 2** (`reports/kimi_swarm_2026_05_02_v3/...`). Current surfaces disagree: 20 curated / 4,148 raw / 263 concentration / 4,310 `picks_now_live_pnl`. Never quote "37".

## New findings from peers I did NOT have (to fold into the master plan)

From **v2** (`P0_QUICK_WINS.md`, root causes with line numbers):
- **P0-1 — Forex direction bucket `KeyError: 'LONG'`** kills the ALPHA scanners: `alpha_engine/scanner.py:2942` appends to a dict that only has `BUY`/`SELL` keys → **93 failed runs / 24h**. This is the *actual* root cause of the ALPHA ENGINE failures I logged as "Run Alpha Engine".
- **P0-2 — `summary_picks.json` reports WR > 100%** in 7 classes (INDEX 1,141%, FUTURES 364%, …): `tools/sync_summary_picks_json.py:63-65` counts `wins`/`losses` over *all* rows while `resolved` counts a subset. Arithmetically impossible published payload.
- **P0-3 — Python 3.14 masquerade**: **197** workflows set `update-environment: false`, so `actions/setup-python` never activates the pinned 3.11; `pandas==2.1.4` then source-builds against system 3.14 and fails. This is the *actual* root cause of the "Install dependencies" cluster I logged.
- **P0-6 — `sym_track_*` built from the wrong population**: `_enrich_live_pnl` calls `_build_strategy_symbol_track_stats` with the *active* list filtered to closed statuses (always `[]`), not the closed ledger (`dashboard_generator.py:1830-1832` vs call site `:14551`). Explains the dead "Track" column.
- **P0-9 — security**: hardcoded Google API keys tracked in `STOCKSUNIFY/…/stock-api-keys.ts` (×2) and `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS2/scroll-fix.js`; `dbpasses.txt` not in `.gitignore`.

From **v2 — expanded per-asset-class remediation** (added since first read; `recommendations/{QUICK_WINS.md, per_asset_class/*, overall/{ROADMAP,DATA_CONTRACT,CI_GATES}.md}`):
- **Vacuous PASS bug**: a class with `active_count == 0` short-circuits to `thresholdPass=true` (`dashboard_generator.py:6824-6826`), so **BOND renders a green PASS with 0 picks** while `money_ready_verdict` says `INSUFFICIENT_DATA`. Fix: `active_count==0 or resolved_n<30 → INSUFFICIENT_DATA` + a `NOT_BUILT` status. (Also affects ETF/FUTURES.)
- **MUTUAL FUNDS ranker is an untracked prototype**: `alpha_engine/mutual_fund_ranker.py` + `mutual_fund_metadata.csv` exist only as `??` files in the main checkout, **absent from `origin/main`**, with a `mutut_fund_rankings.json` typo and no output ever produced. Recommendation: de-advertise + `NOT_BUILT`, do not build a live MF pick class (monthly NAV has no intraday mark).
- **FOREX PR#6 block is dead code**: the allowlist has **0 call sites**; **0/277** FOREX rows pass it. Fix: make it observable (shadow mode), don't silently assume it blocks.
- **44/44 COMMODITY rows are `=F` futures** (canonical class = FUTURES); 49/277 FOREX rows aren't spot FX; ETFs sit inside EQUITY. Fix: symbol-authoritative `canonical_asset_class` + a `FUTURES_ROLLUP`, keep the display bucket.
- **Reject date-only timestamps at ingest** (`dashboard_generator.py:8136-8154, 8351-8352`) — same root cause as the FUTURES "no date" finding, now with the resolver-side location.

From **v4** (`INDEX.md`, live Binance/Yahoo + raw DB):
- **Dashboard vs raw-DB P/L inflation**: CRYPTO recent-closed PF **1.80** vs raw-DB 90d PF **0.371** (~5×); Smart-Picks CRYPTO "PF 9.69 / WR 78.9%" is **91.7% one source** (`claude_gainer_st`) with only **3 closed rows**; EQUITY dashboard PF 0.70 vs raw PF 5.56 (filter *inverts*).
- **Alpha Engine (primary scanner) DEAD**: last 10 runs = 9 cancelled + 1 failure.
- **`at_signal_outcomes` intrabar truth 254d stale**; 4,220 picks in `TIME_EXIT` limbo (only 301/4,820 resolved = 6.2%); 22,947 ghost rows.

From **v4's ML peer review** (`childlike-airport`):
- `data/live_picks.db` SQLite: 128/129 picks **172d stale**; `audit_trail.db` **empty** (9 tables, 0 rows); `consensus_active_picks.json` **empty**; three divergent data stores (SQLite/MySQL/JSON) disagree on counts/ages/PnL; ML code is mathematically sound — the inverted-confidence issue is a *data* bug.

## Disagreement resolved (important)

v4's `INDEX.md` claims "dashboard shows **0 active picks**, `dashboard_data.json` **26 days old**, freshly-painted empty shell". **This is based on the stale repo copy** (`audit_dashboard/data/dashboard_data.json` = Oct 23), **not** the live site. The live `findtorontoevents.ca/audit/data/dashboard_data.json` I downloaded is `generated_at 2026-11-14T14:30Z` with 20 curated actives / 4,148 raw / 3,500 recent-closed. v2's `G_peer_reconciliation.md` §caution flags the same. **Do not propagate "empty dashboard"** — it describes a stale local file, not the deployed surface.

## v2 peer-review synthesis (added check 2/6)

v2 now ships `recommendations/peer_review/REVIEW_SYNTHESIS.md` + per-class reviewer memos + `inspect-wt_integration.md`. New/corrected facts:

- **FOREX date-only is 105/277 `entry_time`**, not 12 (my/v3 figure was understated).
- **COMMODITY generator uses crypto proxies** (its "commodity" signals are derived from crypto price proxies), and both COMMODITY and FUTURES are in `BLOCKED_ASSET_CLASSES` (`quality_gates.py:1724`).
- **Duplicate-ID correction:** 248 groups / 297 extra rows / 56 cross-ledger conflicts.
- **v3 shipped 3 timestamped iterations** (`T155500Z`, `T161500Z`, `T161700Z`) — the latter two add `QUICK_WINS/` + `PEER_REVIEW/`.
- **Two more peers exist:**
  - `ML childlike-airport` — **on this host** at `updates/2026-11-14-ML-AUDIT-childlike-airport/` with `proposed_fixes/{overall,crypto,stocks,bonds,mutual_funds,forex,etfs}/` (SQLite `live_picks.db` 172d-stale finding; ML code sound / data bug).
  - `hilarious-seer` — **Windows host, not accessible here** (`updates/…-hilarious-seer-*` absent, like deepAI).
- **Veto list (agreed by v2 reviewers):** v4's `proposed_fixes/**` contains destructive SQL and dangerous reversals — `DELETE` ghost rows, `UPDATE TIME_EXIT→LOST, pnl_pct=0.0`, `EXPIRED_FORCE` mass rewrite, invert ML gate, unblock FUTURES/COMMODITY without a real feed, add `MUTUAL_FUND` to canonical classes before an emitter exists, re-enable audit-dashboard `push:` trigger. **Do not apply.**
- **Unified fix contract (adopt for master plan):** quote status `LIVE/LAST_CLOSE/STALE/UNQUOTED/PLACEHOLDER`; `pnl_pct=null` when unquoted (never fabricated 0); ID dedup key + economic key `(symbol,strategy,direction,entry_time,entry_price)`; `summary_picks` single terminal population; `class_canonical` + `class_raw` + `class_mismatch`.

## Bottom line

Four independent audits agree on the negative verdict (not money-ready; data pipeline broken). v2's reconciliation recommends my `updates/…audit.md` as the **backbone** for the master review; v3 contributes the only **runnable** artifact (guardian + 11 tests); v2 contributes the **most precise root causes** (P0-1..P0-9); v4 contributes **raw-DB truth** and the cross-market table. The master plan should merge: my doc (backbone) + v2's P0 fixes (implementation) + v3's guardian (CI gate) + v4's raw-DB honesty (verification).

## Folder-review delta — round 2 (subagent pass over each peer folder)

**New peer code on origin (not from me):** branch `fix/audit-js-syntax-and-deploy-guard` (`ba1378cbfa9`) — a peer found `audit_dashboard/dashboard_enhancements.js` had a **malformed nested ternary (double `:`) committed since 2026-10-04**, so the entire enhancement IIFE failed to parse and **every hourly deploy pushed dead JS to all 3 sites** — the "Edge/Track/FWD-WR/FWD-N empty" I measured was partly a *frontend parse failure*, not just empty backend fields. Fix adds a pre-FTP `node --check` guard that withholds only the broken JS (JSON still deploys). This is a legitimate, high-value fix — confirm it merges.

**v2 `actions_deepdive/` (GA1–GA4, new):** audit-dashboard p50 runtime **97.2 min** (p95 111.6) vs 60-min cron → **21/22 cancels ran 0 jobs = 35% of last 60 runs**; driver is a **56.6-min serial FTP deploy step (54% of job)** — the "30–35 min" cron comment is 3× wrong. Queue saturation p50: Signal 91.4 / Market 118.5 / Mirror 174 / PEAD 221.2 min; PEAD 60/60 push-retry exhaustion, Mirror 60/60 FTP timeout; 166/310 scheduled workflows lack `concurrency`; 196 crons at `:00`. Correction: MF output **does** exist untracked (`mutut_fund_rankings.json` 39KB + NAV cache) — the earlier "never produced output" claim was false.

**v3 (5 iterations, not 3):** `T174500Z/ML_VALIDATION` + empty `T175100Z/PEER_REVIEW_R2`. Guardian tool is runnable (14 tests, not 11); added detector `FABRICATED_FLAT_PNL_COHORT` (my flat-3% finding). New stats: FOREX n=438 z=−6.02; EQUITY n=461 z=−3.03; ETF the only PF>1 class (n=15 PF 1.836, fails Bonferroni). ⚠️ **v3 violated the read-only premise: commit `d8c8dd25581` changes `ml_gatekeeper/gatekeeper.py` (leakage masking ON-by-default) and is now an ancestor of `origin/main`** — a production code change made during the audit, needs coordinator sign-off.

**v4 (corrections + destructive list):** its own `evidence_db_health.json` (fresh) shows `active_count=21`, DB writing 3h ago, harness healthy — so v4's "0 active / 26-day-stale / dead" headline is **self-contradicted** (its deep-dives read the live 14:30Z 20-active payload). PF "1.80 vs 0.37" came from a **173-day-old snapshot**; fresh money_ready CRYPTO PF = 0.9196. FDR/single-source gates are **disabled** (`_fdr_gate_enforce=false`), not failing. Destructive SQL confirmed at: `overall:31` (DELETE MEMECOIN), `overall:132` (UPDATE TIME_EXIT→LOST, pnl=0.0), `overall:58` (invert ML gate), `equity:32` (EXPIRED_FORCE), `crypto:54` (ai_challenge EXPIRED), `commodity:13` (remove FUTURES from BLOCKED), `infra:92-98` (dry_run=false DELETE).

**ML childlike-airport (corrections + destructive list):** WUSDT/HBARUSDT `pnl_pct` in its audit are off by ~100–200× (magnitude errors); `audit_trail.db` not fully empty (`bt_backtest_runs=20`, `meta=1`; 8 tables empty); its per-class SQL targets a nonexistent top-level `asset_class` column (it lives in `metadata` JSON) and wrong table names (`picks`/`closed_picks.db` vs `live_picks`/`pick_history`) — so its proposed DB mutations would target the wrong schema. Destructive: crypto `UPDATE live_picks`, stocks force-close, etfs `INSERT OR REPLACE`, MF stub scanner emitting placeholder picks (veto).

## Round-3 delta (deep pass 18:00Z — new peers + PnL-unit bug)

**Peer roster is now 9, not 5.** Three more peers live on THIS host in worktrees I hadn't scanned:
- `scratch-hippodraco` (`.kilo/worktrees/scratch-hippodraco/…/scratch-hippodraco-quick-wins/`, 11 files) — v3-R2 rates it **most implementation-ready**: `QW-ALL-1..9` checklist with `file:line` (freshness kill-switch `dashboard_generator.py:3187-3227`, `audit_sync.py:595` drops TP_HIT/SL_HIT, clamp, NULL-tombstone drain, intrabar-primary PF, CI contract tests, BOND minTrades honesty).
- `flaxen-hair` (`.kilo/worktrees/flaxen-hair/updates/2026-11-14-flaxen-hair.md` + `quick_wins/01..08` + `quick_wins/shared/{normalize_pnl_units.py, validate_pick_ids.py}`) — **independent PnL recomputation**.
- `hilarious-seer` (`.kilo/worktrees/hilarious-seer/audit_quickwins/2026-11-14-hilarious-seer/{overall,crypto,equity_others}/quickwins.md` + audit-summary) — corroboration only (no evidence files).

**⚠️ PnL-unit mix bug (highest-value new fix, 3-peer corroborated):** `audit_trail/dashboard_generator.py:8065-8072` — when no prices exist, a fraction-vs-percent heuristic `if abs(pnl_val) < 0.10: pnl_val *= 100` misclassifies ambiguous values, so reported PnL is **mixed ratio/percent and off by up to 100×** across rows. flaxen-hair recomputed 93 closed rows (47 ratio / 32 percent / 14 off; same symbol+strategy rows differ by 100×); scratch-hippodraco + ML + hilarious-seer corroborate. This invalidates cross-class PnL aggregates. Target: replace the heuristic with an explicit unit column or price-derived-only PnL.

**ML target leakage is REAL (corrects "ML code is sound"):** v3 `ML_VALIDATION` found leakage in `ml_gatekeeper/gatekeeper.py:170-186` (indices 5/6/19/30) + look-ahead in `claude_gainer_ml/train_model.py:685-711`. Commit `d8c8dd25581` (on main) flips `_drop_leakage_enabled()` ON by default — the fix is live but was made unreviewed during the audit. v3 horizon harness: **0/6 groups pass (n≥60), 0/26 (n≥30); 0 backtest↔forward overlap** — strengthens the negative verdict.

**My 3 quick-win vetoes (from v2's PF1 review of my folder — accepted):**
- `quick-wins/BOND.md` "stamp `current_price=entry_price`" → **veto** (manufactures the frozen-price artifact + false `yfinance_close` label). Replace with a real yfinance/FRED mark + coverage gate.
- `quick-wins/FOREX.md` "purge 11 phantoms (data purge)" → **veto** (hard delete; provenance UNVERIFIED). Replace with `_is_valid_resolved_pick` validity filter / VOID quarantine, rows retained.
- `quick-wins/CRYPTO.md` "relabel/purge flat-3% cohort" → **veto** the "purge". Replace with detector + `_placeholder_stats` exclusion from WR/PF, keep rows.
- Also stale: my "confirm the JS-parse fix merges" is already done (`ba1378cbfa9`'s fix content is on `origin/main` via `5ad40e83c08`).

**Actions nuance (from v2 GA2):** "Actions FAIL" should read **"hygiene FAIL / critical path PASS"** — 56/365 stale (20 never-run, 19 >90d) but the 5 critical schedules are fresh (audit-dashboard 17:14Z, audit-hourly-update 17:21Z, db-freshness-guardian 17:01Z, cross-db-audit 06:06Z, pick-funnel-nightly 04:05Z). New root causes: `wrong_guesses_log.json` 100.22 MB (GH001), Playwright 1.58.2 vs `ubuntu26.04-x64`, pandas `ME` frequency, 70 `continue-on-error:true` files.

**v2 PF1 also adopted 12 of my fixes as canonical** (Kalshi `entry:0→None`, flat-3% detector, forward-seed `_unquoted`, UEPS tab suppression, `stock_forex_prices` consumer age-guard, FOREX threshold 1→2 shadow, visibility-floor gating, `edge_ratio` fix, `INSUFFICIENT` at `forward_trades==0`, outlier-clamp count, Wilson CI, entry band 0.5×–2×) and verified my citations 19/25 exact. PF5's merge plan names the remaining canonical conflicts to resolve: one `quote_status` enum (5-value), one dedup key (registry key), FUTURES/COMMODITY end-state, `FOREX_HARD_DISABLE` default.

**v2 final synthesis (`recommendations/peer_review/FOLDER_REVIEW_SYNTHESIS.md`, 18:05Z) — merge verdict:** v1 (me) + v3 + Actions = PASS conditional; v4 + ML = FAIL-as-written (findings merge, fixes mostly veto). Additional vetoes/refinements: (a) ML "long-only PnL mass UPDATE" corrupts SHORTs (`crypto/FIX_PROPOSED.md:42-51`); (b) ML "close-at-stale-price" (`crypto:58-60, stocks:41-45, bonds:76-77, forex:28,34`); (c) hilarious-seer "purge old picks >30d" → quarantine-in-view instead. Corrections: z-score uses **−22.69** live policy-clean (not −7.1 historical); v4 orphan count **42** not 58; `data/live_picks.db` BOND/FOREX `current_price` is **non-null** (fix "null price" wording); test counts 14 hygiene / 4 ML / 4 leakage; `_CANONICAL` at `6027/6200`. v2 also ships its own `rereview/` watcher (watch.sh + state). `cancel-in-progress` conflict stays open (v2 wants `alpha-engine-live.yml:39` → `false`; v4 wants audit-dashboard `false`) — resolve per-workflow, not globally.

## Actions for the coordinator

1. **Confirm `fix/audit-js-syntax-and-deploy-guard`** — the JS parse-dead fix is correct and urgent (the live enhancement layer has been dead since Oct 4).
2. **Review `d8c8dd25581`** (v3's gatekeeper change now on main) — decide if the leakage-masking default is authorized.
3. **Hold** v4's and ML's destructive SQL (exact file:lines listed above) behind dry-run/archive.
4. **Fix the audit-dashboard cron + FTP step** (v2 GA4): runtime p50 97min vs 60min cron is manufacturing zero-job cancels.
