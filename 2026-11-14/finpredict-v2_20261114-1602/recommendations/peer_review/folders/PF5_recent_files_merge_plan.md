# PF5 — Recent-File Sweep & Overall Merge Plan

**Agent:** PF5 (sweep + merge planner, read-only)
**Clock:** 2026-11-14T17:55Z (commands run 17:56–18:05Z)
**Repo root:** `/home/eaguiar2015/findtorontoevents_antigravity.ca` (user Windows `E:\findtorontoevents_antigravity.ca`)
**Our archive (ARCHIVE):** `.kilo/worktrees/finpredict-v2/2026-11-14/finpredict-v2_20261114-1602/`
**Source changes made by PF5:** none. Only this report was written.

---

## Status

| Gate | Result | Reason |
|---|---|---|
| **Coverage** | **FAIL** | 5 of 9 peer groups have material output that is not cited in our archive: v1 `master-plan/`+`quick-wins/`, v3 `ML_VALIDATION`+`QUICK_WINS`+`PEER_REVIEW_R2`, scratch-hippodraco, flaxen-hair, hilarious-seer. The ML-audit `proposed_fixes/` tree and v4 `proposed_fixes/` are also unmerged. |
| **Merge readiness** | **FAIL (conditional)** | Our archive itself is already published on `origin/main` (137 tracked files, byte-identical), but `origin/main` advanced to `7e8c7ac82da` and now carries a gatekeeper leakage fix (`d8c8dd25581`) that our `MASTER_AUDIT.md` does not mention; v3's P0-10 merge edit exists only in v3's worktree; GA1–GA4 are untracked outside ARCHIVE. |
| **Verdict integrity** | **PASS** | The central verdict (FAIL / not demonstrably profitable) is unchanged by every new file. No new peer file contradicts the headline numbers. |

---

## 1. Recent-file inventory (ROOT, modified since 2026-11-14T16:30Z)

Command:

```bash
cd /home/eaguiar2015/findtorontoevents_antigravity.ca
find . -newermt '2026-11-14 16:30' -type f \
  -not -path './.git/*' -not -path '*/node_modules/*' -not -path './.kilo/worktrees/*' \
  -printf '%TY-%Tm-%TdT%TH:%TM %10s %p\n' | sort
```

Result: **16 files**, 25.94 MB total.

| # | Path | mtime (UTC) | Size | Classification |
|---|---|---|---:|---|
| 1 | `bestiejob/README.BAK_2026-11-14T163323Z.md` | 16:33 | 43 KB | Generated job data |
| 2 | `bestiejob/README.BAK_2026-11-14T170457Z.md` | 17:04 | 43 KB | Generated job data |
| 3 | `reports/peer_inbox_hourly.log` | 17:05 | 181 KB | Generated log |
| 4 | `bestiejob/FRESH_JOBS.md` | 17:30 | 529 KB | Generated job data |
| 5 | `bestiejob/README.md` | 17:33 | 1.5 MB | Generated job data |
| 6 | `bestiejob/jobs.json` | 17:33 | 3.2 MB | Generated job data |
| 7 | `bestiejob/public/findjobs/jobs.json` | 17:33 | 3.2 MB | Generated job data |
| 8 | `bestiejob/public/gotjob/jobs.json` | 17:33 | 3.2 MB | Generated job data |
| 9 | `bestiejob/public/jobs.json` | 17:33 | 3.2 MB | Generated job data |
| 10 | `bestiejob/README.BAK_2026-11-14T173352Z.md` | 17:33 | 43 KB | Generated job data |
| 11 | `bestiejob/logs/cron_30min.log` | 17:33 | 634 KB | Generated log |
| 12 | `___HELL_HEALTH_OPENCODE.MD` | 17:45 | 1.0 MB | **Generated ops monitor log** (tracked; header says 2026-05-23, body appended with 2026-11-14 run failures) — unrelated to this audit |
| 13 | `.github/gh_monitor_state.json` | 17:45 | 10.2 MB | Generated state |
| 14 | `data/audit_trail.db-wal` | 17:52 | 0 B | Generated DB sidecar (writer process `UNVERIFIED`) |
| 15 | `data/audit_trail.db-shm` | 17:52 | 32 KB | Generated DB sidecar |
| 16 | `.kilo/agent-manager.json` | 17:55 | 4.9 KB | Agent Manager UI state |

**Audit/peer artifacts found in ROOT scope after 16:30: 0.** No unflagged peer output exists at ROOT level.

Two caveats that matter for coverage:

- Peer work is inside `.kilo/worktrees/*` (excluded by instruction): v3 wrote `2026-11-14T174500Z/ML_VALIDATION` and `2026-11-14T175100Z/PEER_REVIEW_R2` at 17:47–17:55; hilarious-seer wrote its stubs at 17:52; flaxen-hair wrote `quick_wins/` at 17:55–17:56. These are covered in §3.
- `___HELL_HEALTH_OPENCODE.MD` is byte-appended by an opencode monitor, not by an auditor; its 2026-11-14 entries are real GitHub run IDs but it is a monitor log, not an audit artifact.

---

## 2. inspect-wt / deepAI availability (re-checked)

**Result: still ABSENT on this host and on `origin`.** Exact commands and results:

```bash
# 1) Host-wide search (home dir, depth 5, excluding caches/node_modules/.git)
find /home/eaguiar2015 -maxdepth 5 \( -name .cache -o -name node_modules -o -name .git \) -prune \
  -o \( -name 'inspect-wt_20261114_1058' -o -name 'deepAI_proposed_fixes_20261114_1612' \
       -o -name 'inspect-wt*' -o -name 'deepAI*' \) -print
# -> no output (exit 0)

# 2) All registered worktrees (84 entries), search depth 3
for d in $(git worktree list --porcelain | awk '/^worktree /{print $2}'); do
  find "$d" -maxdepth 3 -type d \( -name 'inspect-wt*' -o -name 'deepAI*' -o -name '*live-audit*' \) \
    -not -path '*/.git/*'; done
# -> no output

# 3) ROOT itself
ls -d /home/eaguiar2015/findtorontoevents_antigravity.ca/2026-11-14
# -> No such file or directory (the dated archive exists only in worktrees / on branches)

# 4) Remote branches
git ls-remote --heads origin | grep -iE 'live-audit|inspect|deepai'
# -> no match; total remote heads = 195 (also no finpredict-v2/v3/finpredict/hilarious-seer branches)

# 5) origin/main dated tree
git ls-tree -r --name-only origin/main -- 2026-11-14 | grep -iE 'inspect-wt|deepAI|live-audit'
# -> only 2026-11-14/finpredict-v2_20261114-1602/recommendations/peer_review/inspect-wt_integration.md
#    (our own absence note), no inspect-wt/deepAI archive
```

`origin/main` moved during this task: `git log -1 origin/main` → **`7e8c7ac82da` 2026-11-14T17:55:17Z** “archive: round-2 peer review …”. The dated archive **is** on main (200 files under `2026-11-14/`: 25 v1 + 137 ours + 38 v3). The two Windows-only folders and branch `audit/live-audit-2026-11-14` remain unreachable from Linux/GitHub.

---

## 3. Coverage map

Abbreviations: **ARCHIVE** = our folder (above). “On main” = present under `origin/main:2026-11-14/…` unless stated.

| Group | Reviewed by us | Missing / not covered | What the master reviewer still needs |
|---|---|---|---|
| **v1 `finpredict`** (25 files, on main) | `PEER_CROSSREF.md` covers only `README.md` + `updates/2026-11-14-prediction-system-audit.md` | `master-plan/PLAN.md`, `master-plan/inputs/01–07`, `folder-review/{ml,v2,v3,v4}.md`, `quick-wins/**` (10 files), `peer-review/PEER_RECONCILIATION.md` | Adopt `PLAN.md` phase/veto structure; build one canonical fix registry (v3-R2 flags duplicate IDs); surface v1-unique evidence: frozen 127-pick seed, flat-3% cohort, EQUITY n=8 vs n=759/738 |
| **v3 `finpredict-v3`** (38 files, on main) | Only `2026-11-14T155500Z` hygiene audit is cited (`PEER_CROSSREF.md:12`) | `161500Z/QUICK_WINS/**`, `161700Z/PEER_REVIEW/**`, `174500Z/ML_VALIDATION/**`, `175100Z/PEER_REVIEW_R2/**` | Merge ML validation (leakage, horizon harness, fundamentals ranker), R2 consensus, and the P0-10 edit (§4 item 5) |
| **v4 `finpredict-v4`** (local only, **0 files on main**) | `PEER_CROSSREF.md` + `MASTER_AUDIT.md §7` cover `INDEX.md` and the 8 reports by claim | `proposed_fixes/{overall,infra,crypto,equity,forex,commodity}/QUICK_WINS.md`, `peer_review/PEER_REVIEW_INTEGRATION.md`; whole archive untracked | Re-verify: `evidence_pick_summary_stats.json` is 173 d stale; 3 conflicting FOREX PF (2.02/0.108/0.66); NEAR 1.326 pick is a different row (§5) |
| **ML `childlike-airport`** (local only) | Cited as `updates/2026-11-14-ML-AUDIT-childlike-airport.md` (2 findings in `MASTER_AUDIT.md §3`) | `updates/2026-11-14-ML-AUDIT-childlike-airport/proposed_fixes/{overall,crypto,stocks,bonds,mutual_funds,forex,etfs}/FIX_PROPOSED.md`; `deploy/` and `docs/strategy-audit-rounds/` context | Adopt DB-divergence backbone; **veto** destructive SQL + mutual-fund stub scanner; resolve asset_class schema contradiction (metadata vs column); no futures/commodity fix doc exists |
| **hilarious-seer** | **Not mentioned anywhere** (0 hits in ARCHIVE) | `audit_quickwins/2026-11-14-hilarious-seer/{overall,crypto,equity_others}/quickwins.md` (3 stubs, 9 lines) + `updates/2026-11-14-hilarious-seer-audit-summary.md`; untracked | Corroboration only — no evidence, no reproduction; adopt roster/402 hygiene + prune pointers, do not cite per-class numbers |
| **actions GA1–GA4** | **Ours, but outside ARCHIVE** (`actions_deepdive/`, untracked) | `GA1_unresolved_failures.md`, `GA2_stale_workflows.md`, `GA3_log_errors_warnings.md`, `GA4_jobs_scheduling.md`, `GA2_workflow_matrix.csv` (365 rows), `raw/`, `raw_ga2/`, `raw_ga4/` | Merge into ARCHIVE first (§4 items 1–4). These resolve our `MASTER_AUDIT §1/§7/§8` UNVERIFIED root causes |
| **ours `finpredict-v2`** | n/a | 3 gitignored `raw/*.log` files are local-only; `recommendations/peer_review/folders/` is empty except this file | Archive is already on main (137 tracked files, identical to local). Any further edits must be rebased on `origin/main` (our branch is 3,876 commits behind / 7 ahead) |
| **scratch-hippodraco** (extra, not in task list) | Only 2 incidental “scratch” mentions in ARCHIVE | `2026-11-14/scratch-hippodraco-quick-wins/**` (11 files: README + OVERALL + 8 class docs + PEER_REVIEW) | v3-R2 rates it **most implementation-ready**: adopt QW-ALL-1..9 as the execution checklist (verified `file:line`, effort, verify steps) |
| **flaxen-hair** (extra, not in task list) | **Not mentioned** (0 hits) | `updates/2026-11-14-flaxen-hair.md` (119 lines), `quick_wins/{01..08}/`, `quick_wins/shared/normalize_pnl_units.py`, `validate_pick_ids.py`; untracked | Independent PnL recomputation (93 closed rows) is the strongest unit-bug evidence; also `multi_asset` staleness + duplicate IDs + `ml_score==confidence` |

---

## 4. Ordered merge plan (source → target → change)

All targets are inside **ARCHIVE**. Do them in this order; 1–4 are the actions-deepdive items and carry the most new verified content.

| # | Priority | Source (exact) | Target in ARCHIVE | Change to make |
|---|---|---|---|---|
| 1 | **P0** | `.kilo/worktrees/finpredict-v2/actions_deepdive/{GA1_unresolved_failures.md,GA2_stale_workflows.md,GA3_log_errors_warnings.md,GA4_jobs_scheduling.md,GA2_workflow_matrix.csv}` | `actions_deepdive/` | Copy all five files verbatim. Add an `actions_deepdive/README.md` stating scope (main @ `be4f8960`, 17:50–17:57Z), no source changes, and raw-evidence subfolders (`raw/`, `raw_ga2/`, `raw_ga4/`, ~36 MB combined — decide whether to commit raw or keep the two CSV/JSON caches only). |
| 2 | **P0** | GA3 cluster table | `sub/A_actions_health.md` | Replace `UNVERIFIED` root causes with verified clusters: **A** `KeyError:'LONG'` at `alpha_engine/scanner.py:2942` (15/30 failures); **B** pandas source-build on Python 3.14 (`_PyLong_AsByteArray`, 7); **C** Playwright 1.58.2 vs `ubuntu26.04-x64` (5); **D** `ME` alias vs `pandas==2.1.4` (2); **E** 100.22 MB `wrong_guesses_log.json` rejected (1). Add the 6,628-line Binance-451 log-noise finding and 70 `continue-on-error: true` files. |
| 3 | **P0** | GA4 executive table | `sub/A_actions_health.md` + `MASTER_AUDIT.md §1` | Add scheduler facts: audit-dashboard 21/22 cancels had **0 jobs** (35% of last 60); job p50/p95 **97.2/111.6 min** vs 60-min cron; 310 scheduled workflows, 166 without `concurrency`, 91 push-to-main without it; 196 crons at `:00`; queue p50 signal/market/mirror/PEAD 91.4/118.5/174.0/221.2 min; PEAD 60/60 push-retry exhausted; mirror 60/60 fails in FTP download. Keep our 5-sample 84.5-min figure but label it a sample (§5 conflict C5). |
| 4 | **P0** | GA1 + GA2 summaries | `MASTER_AUDIT.md §7/§8` + `sub/G_peer_reconciliation.md` | GA1: 8 unresolved latest-run failures (all auto-retried, attempts 2–4), 0 chronic cancels, 12 runs mid-flight; guardian reported 14 at 17:33Z. GA2: 56/365 stale (20 never-run, 12 1–30 d, 5 30–90 d, 19 >90 d, 4 disabled-with-cron, 2 orphaned registrations); **critical path fresh** (`audit-dashboard` 17:14Z, `audit-hourly-update` 17:21Z, `db-freshness-guardian` 17:01Z, `cross-db-audit` 06:06Z, `pick-funnel-nightly` 04:05Z). This converts the blanket “Actions FAIL” into “hygiene FAIL / critical path PASS”. |
| 5 | **P0** | `.kilo/worktrees/finpredict-v3/2026-11-14/finpredict-v3/2026-11-14T174500Z/ML_VALIDATION/{README.md,results/*,tools/*}` | `sub/H_ml_validation.md` (new) | Add: target leakage in production gatekeeper (`ml_gatekeeper/gatekeeper.py:170-186`, indices 5/6/19/30) — **verify against main**: `_drop_leakage_enabled()` now returns `True` by default (commit `d8c8dd25581`); look-ahead in `claude_gainer_ml/train_model.py:685-711`; shuffle split in `scripts/sports_ml.py:47`; 0 rows with both `bt_trades>0` and `fwd_trades>0`; horizon harness **0/6 (n≥60) and 0/26 (n≥30)** groups pass; best: ETF rs-breakout n=78 WR 57.7% CI_lo 46.6%; CRYPTO `luxalgo_confluence` n=1,290 WR 42.9% CI_lo 40.3%. Update `MASTER_AUDIT §5/§8`: “ML code not audited” is no longer true. |
| 6 | **P0** | `.kilo/worktrees/finpredict-v3/2026-11-14/finpredict-v2_20261114-1602/recommendations/patch_plan/P0_QUICK_WINS.md` (v3-local copy, `P0-10`) | `recommendations/patch_plan/P0_QUICK_WINS.md` + `recommendations/QUICK_WINS.md` | Add **P0-10 “Merge ML fixes & validations”** verbatim (leak default ON + tests; 0/26 horizon; fundamental ranker no-edge top-quantile WR 0.479 CI [0.439,0.520]; 0 bt/fwd overlap). Update sequencing line to `P0-1 → P0-4 … then P0-9/P0-10`. Update the QUICK_WINS “Refresh/retire live_picks.db” bullet to include ML_VALIDATION (same text v3 already drafted). |
| 7 | **P1** | `.kilo/worktrees/finpredict-v3/2026-11-14/finpredict-v3/2026-11-14T175100Z/PEER_REVIEW_R2/**` (7 files + index) | `recommendations/peer_review/round2/` | Copy `00_INDEX.md` + 7 memos. Add to `PEER_CROSSREF.md`: “Round 2 (17:51Z): v2 chosen as reconciliation backbone; scratch QW-ALL-1..9 chosen as checklist; ML-audit red-lined; v4 stale evidence flagged; seer corroboration-only.” |
| 8 | **P1** | `.kilo/worktrees/flaxen-hair/updates/2026-11-14-flaxen-hair.md` + `quick_wins/**` + `quick_wins/shared/*.py` | `peers/flaxen-hair/` | Copy. Add to `sub/G_peer_reconciliation.md` inventory and to `MASTER_AUDIT §3`: PnL unit mix confirmed by recomputation (93 rows: 47 ratio, 32 percent, 14 off; same symbol/strategy rows differ by 100×), duplicate `id`s (`vix_reversal::SI=F::2026-03-11` repeated), `ml_score == confidence`, `meta_strategy.db` 5 empty tables, `coinglass.positions` max 2026-11-06. |
| 9 | **P1** | `.kilo/worktrees/scratch-hippodraco/2026-11-14/scratch-hippodraco-quick-wins/**` (11 files) | `peers/scratch-hippodraco/` | Copy. Adopt **QW-ALL-1..9** into `recommendations/patch_plan/P0_QUICK_WINS.md` as the execution checklist (freshness kill-switch `dashboard_generator.py:3187-3227`; `if abs(pnl)<0.10: pnl*=100` at `:8065-8072`; `audit_sync.py:595` drops TP_HIT/SL_HIT; clamp 999,999.9999; NULL-tombstone drain; artifact max-age stamps; intrabar-primary PF; CI contract tests; BOND minTrades honesty). |
| 10 | **P2** | `.kilo/worktrees/hilarious-seer/audit_quickwins/2026-11-14-hilarious-seer/**` + `updates/2026-11-14-hilarious-seer-audit-summary.md` | `peers/hilarious-seer/` | Copy, header “CORROBORATION ONLY — no evidence files, `db_fixes/` empty, per-class numbers not re-derived (0/26 horizon; 22k+ ghosts; frozen prices; inverted ML conf).” Adopt only roster/402 hygiene + prune/regime pointers. |
| 11 | **P2** | `updates/2026-11-14-ML-AUDIT-childlike-airport.md` + `updates/2026-11-14-ML-AUDIT-childlike-airport/proposed_fixes/**` | `peers/ml-childlike-airport/` | Copy. Attach the veto block from `PEER_REVIEW_ML_AUDIT.md`: no blanket UPDATE/row-move/`INSERT OR REPLACE`; no MF stub scanner; resolve `asset_class` schema (metadata vs column) before any SQL. Keep the 8 sign + 15 calc PnL rows as canonical test cases. |
| 12 | **P2** | `audits/2026-11-14/finpredict-v4_2026-11-14-1555/proposed_fixes/**` + `peer_review/PEER_REVIEW_INTEGRATION.md` | `peers/finpredict-v4/` | Copy. Label `evidence_pick_summary_stats.json` **(2026-05-25, 173 d stale — do not cite)**; carry the 3-layer divergence (SQLite 129 rows / MySQL 90,523 / JSON), FOREX block bypass via `non_crypto_consensus`, 5× crypto PF inflation as **peer claim, not re-derived**. |
| 13 | **P2** | `.kilo/worktrees/finpredict/2026-11-14/finpredict/2026-11-14T160004Z/master-plan/PLAN.md` + `inputs/01–07` + `quick-wins/**` | `recommendations/master_plan/` | Copy as the planning foundation. Add the two required fixes from R2: single canonical fix registry (one table with ID/class/file:line/proposers/effort/risk/phase) and a **decision gate** for the 4 open conflicts (quote enum, dedup key, FUTURES/COMMODITY end-state, `FOREX_HARD_DISABLE` default). Mark “new tests” as TODO until files exist. |
| 14 | **P2** | all of the above | `INDEX.md`, `PEER_CROSSREF.md`, `sub/G_peer_reconciliation.md`, `MASTER_AUDIT.md §7/§10` | Update deliverable table, agreement matrix, peer inventory, and post-review corrections (#11–#16: GA root causes, GA2 stale counts, GA4 scheduler, ML leakage/horizon, PnL unit bug, 5-group coverage). |

**Do not merge:** v4 “0 active / 26-day dashboard” conclusions (stale repo snapshot); hilarious-seer per-class claims as evidence; ML-audit destructive SQL; mutual-fund stub emission; any `pnl_pct=0` fabrication.

---

## 5. Conflict check vs our MASTER_AUDIT

| # | New claim (source) | Our verdict/number (ARCHIVE) | Assessment + evidence |
|---|---|---|---|
| C1 | NEARUSDT SHORT **entry 1.326**, live 3.224, **+143% discrepancy**, SL 1.37 breached (`audits/.../market_crossref_report.md`, quoted in `PEER_REVIEW_V4.md:53`) | Entry **3.324**, current 3.233, +2.74%; true +3.1–3.8% (`MASTER_AUDIT.md:134`, §6) | **Not the same pick.** `raw/representative_picks.json` and `raw/active_table.txt` contain 3.324; `raw/binance_price_NEARUSDT.json` = 3.19700. The 1.326/SL-1.37 row is an older (likely AI-challenge) pick absent from our 4,148-row snapshot → **UNVERIFIED provenance; do not overwrite our curated row.** |
| C2 | “EQUITY 757 picks **−5.22% PnL**” (`hilarious-seer/equity_others/quickwins.md`; v4 `noncrypto_deep_dive`) | EQUITY `recent_closed` n=738, WR 47.0%, sum **+238.4%**, median close age 120.1 d (`MASTER_AUDIT.md:242,252`) | **Different populations/periods** (DB/backlog vs 3,500-row closed feed). Merge only with an explicit population label; no change to the FAIL verdict. |
| C3 | “ML algorithms are **sound**” (ML audit, echoed by v4 integration) **vs** “target leakage in the production gatekeeper” (v3 `ML_VALIDATION/README.md:31`) | ARCHIVE does not audit ML code; §10 vetoes “invert the ML confidence gate” | **Correction needed:** leakage is real (`ml_gatekeeper/gatekeeper.py:170-186`, indices 5/6/19/30). Verified on `origin/main`: `_drop_leakage_enabled()` now masks those indices and **returns True by default** (commit `d8c8dd25581`). Replace “ML code sound” with “leak fixed by default on main; old leaky sleeve was the live emitter.” Our veto on inverting the filter stands (data/label bug, not model inversion). |
| C4 | “Actions **critical path PASS**” (GA2) | “Actions health **FAIL**” (`MASTER_AUDIT.md:19,29-31`) | **Scope nuance, not contradiction:** hygiene FAIL (56/365 stale, 20 never-run) while the five audit/critical schedules are fresh. Merge as “FAIL (hygiene) / PASS (critical path)” and add GA2’s timestamp evidence. |
| C5 | Audit-dashboard job **p50 97.2 / p95 111.6 min** (GA4) | 5 sampled successes 79.6–104.2 min, **median 84.5** (`MASTER_AUDIT.md:65`) | Method/sample difference (5 successes vs last-60 all-outcomes). Both show >60-min cron saturation. Keep ours as “sampled successful jobs”, add GA4 as “all-runs p50”; mark the delta `UNVERIFIED`. |
| C6 | v4 “0 active picks / dashboard 26 d old” (`INDEX.md`, `dashboard_data_report.md`) | 20 curated, payload `generated_at 2026-11-14T14:30:07Z`, 1.63 h at capture | Already adjudicated: v4 read a **stale repo snapshot**; its own `crypto_deep_dive.md`/`forex_deep_dive.md` say 20 active / live 14:30Z. No change; keep the `PEER_CROSSREF.md:50-59` explanation. |
| C7 | “PnL units mixed up to 100×” (flaxen-hair recompute; scratch ALL-2; childlike; hilarious) | ARCHIVE has **no PnL-unit finding** (0 hits for “unit” outside a test comment) | **Coverage gap, not contradiction.** Three-way corroborated; adopt as P0 (§4 items 8–9). This is the highest-value missing first fix. |
| C8 | “0/26 horizon groups pass; 0 backtest↔forward overlap” (v3 ML_VALIDATION) | “0/9 money-ready; no class passes Tier-2” (§5) | **Consistent and strengthening.** Add as the rigor gate; it does not change the verdict. |
| C9 | v3 R2: “v2 archive has no top-level README” (`PEER_REVIEW_V2.md:14`) | `INDEX.md` serves as the index | Cosmetic; optionally add a 10-line `README.md` pointer to `INDEX.md`. |

---

## 6. UNVERIFIED

- Contents of `2026-11-14/inspect-wt_20261114_1058/` and `2026-11-14/deepAI_proposed_fixes_20261114_1612/` — absent on host and GitHub; Windows-only claim.
- Whether GA1’s 8 flagged workflows resolved after 17:57Z (guardian had auto-retried all 8).
- Owner/writer of `data/audit_trail.db-wal` / `-shm` (changed 17:52Z; DB opens still appear empty per ML audit).
- Provenance of v4’s NEAR entry 1.326 / SL 1.37 pick (not in our `raw/` snapshot).
- flaxen-hair’s exact unit-mix counts — peer recomputation accepted at face value; not re-run by PF5.
- GA4 p50 97.2 min vs our 84.5-min sample (see C5).
- Which process appends to `___HELL_HEALTH_OPENCODE.MD` (tracked file, 1.0 MB, modified 17:45Z).
- Whether any of `origin/main`’s 3,876 commits beyond the archive change the audited behavior (out of PF5 scope).

---

## 7. Top 5 gaps (actions in order)

1. **GA1–GA4 are outside the archive.** They verify what our report calls `UNVERIFIED` (exact failure root causes + scheduler saturation). Copy §4 items 1–4 first.
2. **v3 ML_VALIDATION + R2 are unreviewed by our master report.** Missing 0/26 horizon pass, 0 backtest/forward overlap, and the gatekeeper leakage correction now live on main.
3. **5 peer groups unmerged:** v1 `master-plan`/`quick-wins`, scratch QW-ALL-1..9, flaxen-hair, hilarious-seer, ML `proposed_fixes` (+ v4 `proposed_fixes`). The master plan currently has no implementation checklist and no canonical fix registry.
4. **PnL-unit bug absent from our P0 list** despite three independent peers and a recomputation; it invalidates every cross-class PnL aggregate by up to 100×.
5. **Branch divergence:** the archive is already on `origin/main` (`7e8c7ac82da`, 137 files identical), but our worktree branch is 3,876 commits behind. Apply all merge edits on a fresh branch from `origin/main`, then re-run the three-way check; do not push from `finpredict-v2`.
