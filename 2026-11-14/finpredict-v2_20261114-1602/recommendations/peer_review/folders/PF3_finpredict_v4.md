# PF3 — Peer Review of `finpredict-v4` Audit Folder

**Merge-readiness: FAIL** — the findings are valuable, but the archive is not merge-ready as-is: it is internally contradictory on the two headline populations, uses a 173-day-stale evidence file for its most-cited dashboard-vs-DB deltas, cites several non-existent files, and ships destructive SQL/policy reversals that must not reach an implementer.

- **Reviewer:** PF3
- **Review clock:** 2026-11-14T17:55Z (first read); live re-check 17:57Z; archive re-checked 18:00Z
- **Target:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/audits/2026-11-14/finpredict-v4_2026-11-14-1555/`
- **Our archive:** `.kilo/worktrees/finpredict-v2/2026-11-14/finpredict-v2_20261114-1602/`
- **Method:** read every v4 file; read our `MASTER_AUDIT.md`, `PEER_CROSSREF.md`, `recommendations/**`; verified v4 `file:line` refs against repo source; fetched the live `dashboard_data.json` once at 17:57Z to settle the active-count contradiction. **No repo source was modified.**
- **Note on mutation:** `INDEX.md` was rewritten during this review. At 17:55Z it was 10,788 B, headed `FINAL CONSOLIDATED`, and said “The live dashboard currently shows **0 active picks**”. At 17:58Z it became 15,594 B, headed `CORRECTED & INTEGRATED`, and now says “20 curated active picks”. This review assesses the current 15,594-B version and records the earlier text where it matters.

---

## 1. Inventory (21 files, 3 empty directories)

All mtimes are 2026-11-14 UTC. The folder is **untracked** in git (`git status --short` → `?? audits/2026-11-14/finpredict-v4_2026-11-14-1555/`), so it has no commit-level provenance.

| Path | mtime | Size (B) | Description |
|---|---:|---:|---|
| `INDEX.md` | 17:58 | 15,594 | Was 10,788 B / `FINAL CONSOLIDATED` at 16:20; now `CORRECTED & INTEGRATED` after peer-review round 2. |
| `actions_health_report.md` | 15:58 | 47,593 | 365-workflow inventory, 28 last-run failures, 39 repeat failures, full appendix. |
| `dashboard_data_report.md` | 15:58 | 11,538 | Per-class active/closed/backlog tables, dashboard-vs-raw-DB deltas, money-ready gates. |
| `dashboard_metrics_sources.md` | 16:05 | 11,615 | Field liveness, stale sidecars, Alpha Engine run history, source provenance, “0 active” claim. |
| `crypto_deep_dive.md` | 16:05 | 17,188 | 3 live crypto picks, Binance cross-check, forward-validation and trust audit. |
| `forex_deep_dive.md` | 16:05 | 13,831 | 2 live FOREX picks, er-api cross-check, PR #6 bypass, consensus inputs. |
| `noncrypto_deep_dive.md` | 16:05 | 14,168 | EQUITY/ETF/BOND/COMMODITY/FUTURES alive-vs-dead, ages, intrabar truth. |
| `market_crossref_report.md` | 15:58 | 10,614 | 19-pick sample vs Binance/Yahoo; zombie AI Challenge/tournament registry. |
| `evidence_money_ready_verdict.json` | 15:58 | 42,481 | Generated 14:29Z; per-class gates, top sleeves, gate-flag state. |
| `evidence_intrabar_truth.json` | 15:58 | 3,486 | Generated 14:25Z; intrabar n/WR/PF by class; n<100 = INSUFFICIENT_N. |
| `evidence_db_health.json` | 15:58 | 6,462 | Generated 14:13Z; 22,947 ghost rows, open bloat, PnL integrity, status standardization. |
| `evidence_pick_summary_stats.json` | 15:58 | 9,262 | **Generated 2026-05-25T05:46Z** (173 days old); dashboard-vs-raw comparisons. |
| `peer_review/2026-11-14-ML-AUDIT-childlike-airport.md` | 16:17 | 10,218 | SQLite `live_picks.db`, PnL sign bug, empty `audit_trail.db`, no mutual funds. |
| `peer_review/PEER_REVIEW_INTEGRATION.md` | 16:19 | 5,146 | Merges the ML peer into v4 priorities; flags three divergent data stores. |
| `proposed_fixes/overall/QUICK_WINS.md` | 16:19 | 17,959 | System-level 5 QW + 5 MF + 4 LF; **contains the DELETE/UPDATE/invert-ML fixes**. |
| `proposed_fixes/infra/QUICK_WINS.md` | 16:20 | 18,458 | Concurrency, silent failures, orphan merge, dedup, TIME_EXIT, 44-MB JSON. |
| `proposed_fixes/crypto/QUICK_WINS.md` | 16:17 | 12,376 | Frozen prices, PF inflation, zombie purge, forward validation, ML flip. |
| `proposed_fixes/forex/QUICK_WINS.md` | 16:17 | 13,088 | Blacklist/dedup/hard-disable enforcement, FX price resolver, forward lane. |
| `proposed_fixes/equity/QUICK_WINS.md` | 16:18 | 13,566 | EQUITY/ETF/BOND; **contains the `EXPIRED_FORCE` mass update**. |
| `proposed_fixes/commodity/QUICK_WINS.md` | 16:18 | 9,137 | COMMODITY/FUTURES; **contains the FUTURES unblock**. |
| `proposed_fixes/bond/` | — | — | **EMPTY** (folded into `equity/QUICK_WINS.md`). |
| `proposed_fixes/etf/` | — | — | **EMPTY** (folded into `equity/QUICK_WINS.md`). |
| `proposed_fixes/futures/` | — | — | **EMPTY** (folded into `commodity/QUICK_WINS.md`). |

**Inventory gap:** the brief describes `proposed_fixes/{bond,commodity,crypto,equity,etf,forex,futures,infra,overall}` as if nine file sets exist. Only six exist; three directories are empty. The INDEX repeats “six parallel subagents”, so this is a packaging limitation, not a hidden finding.

---

## 2. What each file actually says (short form)

- **Actions:** 365 workflows; 28 last-run failures; 39 with ≥3 bad runs in the last 5; 20 never run; 19 >90 days stale; Alpha Engine 9 cancelled + 1 failure in its last 10.
- **Dashboard data:** all nine classes fail or have insufficient n; 4,220/4,820 TIME_EXIT backlog; 22,947 ghost rows; `90,523` open `trading_picks` vs `21` DB-active.
- **Crypto:** 3 live picks, all SHORT; all `_backfilled`; 0 forward trades; XRP/BTC current price equals entry; NEAR understated by 0.72 pp.
- **FOREX:** 2 live picks; both `current_price ≈ entry_price`; `sym_dir_fwd_pf` 0.428/0.14; consensus fed by a “retired” strategy.
- **Non-crypto:** EQUITY/ETF/BOND backlogs 757/1,722/1,293; COMMODITY 4 picks all ~156 days old; FUTURES 0 live, one Oct-19 YM=F ghost.
- **Market cross-ref:** `picks_now.json` prices match live; AI Challenge/tournament “OPEN” rows are 5–8 months old with `pnl_pct=0.0`.
- **Peer ML:** 128/129 SQLite picks 172 days stale; 8 PnL sign contradictions; 15 calc mismatches; `audit_trail.db` 8-of-9 tables empty; no mutual-fund coverage.

---

## 3. Contradiction resolution (file + quote)

### 3.1 “0 active” vs “20 active” vs the live count

| Side | File:line | Verbatim quote | What it actually is |
|---|---|---|---|
| A (“0”) | `INDEX.md` (17:55Z version) §2 | “The live dashboard currently shows **0 active picks** because the Alpha Engine is dead.” | Wrong for the live site. The current 17:58Z INDEX retracts this at line 46. |
| A (“0”) | `dashboard_metrics_sources.md:13` | “**Active picks table** | **EMPTY (0 picks)** — CRITICAL” | Same error; contradicted 10 lines later by its own `generated_at` quote. |
| A (“0”) | `dashboard_metrics_sources.md:73` | code block: `n_active_picks: 0` | **The live payload has no `n_active_picks` key.** At 17:57Z the key was absent (`'n_active_picks' in payload == False`); `summary.total_active_picks` was `10`. Reading a missing key with a default of 0 produces this. |
| A (“0”) | `dashboard_metrics_sources.md:104,110,157,215` | “The dashboard shows 0 active picks total.” / “0 active picks on dashboard.” / “With 0 active picks, no filter can return results.” / “it shows 0 picks” | Cascading restatement of the same field error. |
| B (“20”) | `crypto_deep_dive.md:13` | “**Total Active Picks (all asset classes):** 20” | Correct for the live `dashboard_data.json` generated 14:30:07Z. |
| B (“20”) | `forex_deep_dive.md:19` | “The live `dashboard_data.json` (generated 2026-11-14T14:30:07Z) contains **20 total active picks** across all asset classes.” | Correct for that snapshot. |
| B (“20”) | `INDEX.md:46` (17:58Z) | “The live dashboard shows **20 curated active picks** (`dashboard_data.json` generated 2026-11-14T14:30Z).” | Post-hoc correction; accurate for 14:30Z. |

**Resolution:** `0` was never a live-site fact. It is a **repo-copy + wrong-field** artifact: `audit_dashboard/data/dashboard_data.json` in the repo is generated `2026-10-19T19:40:11Z` (mtime 2026-10-23) and contains 23 `picks.active`; the live URL is hourly-fresh. The live payload I fetched at **17:57Z** was `generated_at = 2026-11-14T16:15:51.726778+00:00`, `summary.total_active_picks = 10`, `picks.active` length **10**, classes `{CRYPTO:2, EQUITY:2, FOREX:2, FUTURES:1, ETF:1, COMMODITY:2}`. So the active count is a moving target: **20 at 14:30Z, 10 at 16:15Z, never 0**. The corrected INDEX still contradicts itself: line 46 says 20, but line 92 still says “ALL EMPTY (0 active picks)” and line 118 still says “freshly-painted empty shell.”

### 3.2 `dashboard_data.json`: 26 days old vs live/fresh

| File:line | Quote | Resolution |
|---|---|---|
| `INDEX.md:66` | “**Local `dashboard_data.json`** | **CRITICAL** | 26 days old (Oct 19) in repo. **LIVE site is fresh** (2026-11-14T14:30Z).” | Correct **only after** the 17:58Z rewrite. |
| `noncrypto_deep_dive.md:30` | “`dashboard_data.json` | **2026-10-19 19:40 UTC** | **~26 days (STALE)**” | True of the repo copy. |
| `noncrypto_deep_dive.md:32` | “The main `dashboard_data.json` (which drives the /audit HTML active-picks table) is **26 days old**.” | **False as a live claim**: the deployed copy is what drives `/audit`, and it was 1.4 h old at audit time. The 26-day file is the repo fallback. |
| `dashboard_metrics_sources.md:27` | “**Live `dashboard_data.json` generated_at:** `2026-11-14T14:30:07Z`” | Contradicts the same report’s “0 picks” conclusion. |
| Repo check | `generated_at = 2026-10-19T19:40:11.683221+00:00`, `picks.active = 23` | Confirms the repo copy is the 26-day artifact. |
| Live check (17:57Z) | `generated_at = 2026-11-14T16:15:51Z`, `picks.active = 10` | Confirms the live copy is fresh (but the count moved). |

**Resolution:** v4 conflated two different files with the same name. “26 days” = repo copy; “14:30Z / 20 picks” = deployed copy. Do not reuse either number without naming the surface and clock.

### 3.3 Class counts: 757 / 1,722 / 1,293 vs 767 / 1,730 / 1,313

| File:line | Quote | Surface |
|---|---|---|
| `noncrypto_deep_dive.md:39,101,159` | “**picks_now_live_pnl.json:** 757 open picks” / “1722 open picks” / “1293 open picks” | `picks_now_live_pnl.json` `by_class[].n`. |
| `dashboard_metrics_sources.md:183-186` | “BOND: 1,293” / “ETF: 1,722” / “EQUITY: 757” | Same file, repo snapshot. |
| `dashboard_data_report.md:28,31,32` | “BOND | 8 | 1,313” / “EQUITY | 5 | 767” / “ETF | 5 | 1,730” | Same file, **later live snapshot**; line 37 says “4,361 open picks.” |
| `dashboard_data_report.md:37,159` | “the **4,361 open picks**” / “**4,361 open picks** priced” | Different generation of the same tracker (repo copy has `n_open = 4,310`). |
| Repo check | `audit_dashboard/data/picks_now_live_pnl.json` generated `2026-11-12T18:57:19Z`, `n_open = 4,310`, `by_class = {BOND:1293, COMMODITY:4, EQUITY:757, ETF:1722, FOREX:534}` | The 757/1,722/1,293 set is real, but for the **Nov-12 backlog**. |

**Resolution:** These are **not** `picks.active` and not `picks.active_raw`. They are `picks_now_live_pnl.json` — a separate traditional-finance tracker (`source: picks_now_tracker (ejaguiar1_stocks)`) whose rows are a multi-month backlog. At v4’s 15:52Z audit the file was **~45 h old**; at 17:57Z it is **~53 h old**. v4’s own non-crypto report says the newest rows are 1.9–2.4 days old and the oldest 148–161 days. The 767/1,730/1,313 / 4,361 set is a later live snapshot of the same file; it is **UNVERIFIED** because that version is not in the repo. Neither set may be compared to the 20-row curated panel, and neither is a current position count.

### 3.4 `at_signal_outcomes`: 80 days vs 254 days

| File:line | Quote | Resolution |
|---|---|---|
| `dashboard_data_report.md:87,89` | “Staleness: **115,782 minutes (~80 days)**.” / “have not been refreshed for ~80 days.” | `db_freshness.json` was generated **2026-05-23T18:29Z**; at that moment last resolve `2026-03-04` was 80 days earlier. Correct **as of May 23**, not as of Nov 14. |
| `INDEX.md` (17:55Z) §3 | “Last resolved 2026-03-04 (**254 days stale**).” | Correct arithmetic from Mar 4 to Nov 14 (~255 d). |
| `INDEX.md:69` (17:58Z) | “Freshly computed today (2026-11-14). The ‘254 days’ claim was overstated.” | Plausible for the **derived** `evidence_intrabar_truth.json` (generated 14:25Z), but not evidence that `at_signal_outcomes` itself was refreshed. The freshness file still says `last_resolved_at = 2026-03-04 08:47:58`. |
| Repo check | `audit_dashboard/data/db_freshness.json`: `generated_at 2026-05-23T18:29:59Z`, `minutes_stale 115782.0`, `last_resolved_at 2026-03-04 08:47:58` | Both numbers derive from one stale file. Neither is a current measurement. |

**Resolution:** 80 d and 254 d are the same fact measured from two different “now” clocks. The derived intrabar JSON can be freshly computed **from stale rows**; those are not contradictory. Mark the true `MAX(resolved_at)` as **UNVERIFIED** until queried directly.

### 3.5 The most-cited dashboard-vs-DB deltas rest on a May-25 evidence file

`evidence_pick_summary_stats.json:2` says `"generated_at": "2026-05-25T05:46:20.818392Z"` — **173 days before the audit**. Line 4 says the dashboard source was `audit/data/dashboard_data.json (audit_dashboard/data/dashboard_data.json missing — fallback used)`. Therefore v4 §4 and the INDEX “Closed Picks” section — CRYPTO dashboard PF 1.80 vs raw 0.371, EQUITY PF 0.70 vs 5.56, FOREX PF 2.02 vs 0.108, FUTURES PF 0.582 vs 131.6 — are **May-2026 comparisons**, not 2026-11-14 comparisons. They may still be directionally right, but they are not current evidence. Our v2 accepted these numbers as peer-reported rather than re-deriving them; they must be re-derived from the live payload before any fix is prioritized on them.

### 3.6 Residual contradictions in the “corrected” INDEX

The 17:58Z rewrite fixed §2 but left:
- line 92: “edge, track, FWD WR%, FWD N, score, trust, confidence: **ALL EMPTY** (0 active picks)” — false; the live payload had 10–20 active rows and the emptiness is per-field, not zero rows.
- line 118: “the dashboard is currently a freshly-painted empty shell” — false for the live site.
- line 199: “**Safe alternatives** are documented in each per-class fix file under ‘SAFE’ headings” — **no `SAFE` heading exists anywhere under `proposed_fixes/`** (verified with `grep -rn 'SAFE' proposed_fixes/` → 0 hits). The destructive SQL remains in the fix files unchanged.
- §3 still lists `dashboard_data.json` as “26 days old” without the “local repo only” qualifier that was added in §2.

---

## 4. Unique findings vs our v2, and classification

Legend: **ADOPT** = take as-is with the stated guard; **MERGE** = take the intent, rewrite mechanics/refs; **REJECT** = do not implement; **ALREADY_COVERED** = v2 already has an equivalent, no action beyond cross-link.

| # | v4 item (file ref) | New vs v2? | Class | Reason / merge target |
|---:|---|---|---|---|
| 1 | Alpha Engine `cancel-in-progress: true` root cause (`infra/QUICK_WINS.md:14-30`) | Yes | **ADOPT** | Verified: `alpha-engine-live.yml:39` is `true`; `alpha-engine-fast.yml:13` and `audit-dashboard.yml:42` are already `false`. Safe config change. |
| 2 | Surface `\|\| non-fatal` masking (`infra/QUICK_WINS.md:34-48`) | Partial | **ADOPT** | Safe log-scan step. Correct v4’s “58 instances” to the actual **42** `non-fatal` occurrences in `alpha-engine-live.yml`. |
| 3 | Restart hourly-update pipeline (`infra/QUICK_WINS.md:52-67`) | Partial | **MERGE** | v2 has a sidecar-freshness manifest; add the specific `hourly_update_last_run.json` freshness assert. |
| 4 | Merge Copy Trader / Gainer orphans into dashboard (`infra/QUICK_WINS.md:71-88`) | Yes | **MERGE** | v2 notes the orphaning but has no merge step. Add `source_system` tag + dedup key before merge. |
| 5 | Ghost-row dedup dry-run / weekly cron (`infra/QUICK_WINS.md:92-108`) | Partial | **MERGE → reject apply** | Keep `dry_run=true`; replace DELETE with a quarantine table/view. v2 P0-9 already says “quarantine, never delete.” |
| 6 | TIME_EXIT backlog rescue (`infra/QUICK_WINS.md:116-135`; `overall/QUICK_WINS.md:127-137`) | Partial | **MERGE → reject SQL** | Intent is valid; v2 already has age-out. Use a resolved-price batch job that writes real `exit_price`/`pnl`; never `pnl=0.0`. |
| 7 | Intrabar bootstrap dispatch (`infra/QUICK_WINS.md:139-155`) | Partial | **ADOPT** | Existing `bootstrap_intrabar` input is real; run once, verify `MAX(resolved_at)`. |
| 8 | Refresh stale JSON sidecars (`infra/QUICK_WINS.md:159-184`) | Yes | **MERGE** | v2 P0-7 is the same goal; do not delete `db_freshness.json` (destroys evidence) — mark it superseded. |
| 9 | Make MySQL sync fail-loud (`infra/QUICK_WINS.md:188-203`) | Yes | **ADOPT** | `alpha-engine-live.yml:813-828` has `continue-on-error: true`; safe to make critical. |
| 10 | Stop committing 44-MB JSON (`infra/QUICK_WINS.md:211-229`) | Yes | **ADOPT (long-term)** | Real repo bloat; aligns with the 19-GB pack comment in `audit-dashboard.yml:78-92`. |
| 11 | Workflow circuit breaker (`infra/QUICK_WINS.md:258-275`) | Yes | **ADOPT (low priority)** | Safe after concurrency fix; otherwise masks a fixable problem. |
| 12 | Unified orphan merger (`infra/QUICK_WINS.md:279-299`) | Partial | **MERGE** | Fold into #4; do not build a second merger abstraction first. |
| 13 | `claude_gainer_st` EXPIRED→WON guard (`overall/QUICK_WINS.md:13-22`) | Partial | **MERGE** | The target `alpha_engine/claude_gainer_emitter.py` **does not exist**; the feed is `claude_gainer_ml/tracker/short_term_active.json` (`alpha_engine/isolated_signal_integrator.py:106`). Fix the label at ingest/resolver, not with a source-name special case. |
| 14 | DELETE 22,947 ghost rows (`overall/QUICK_WINS.md:26-36`) | No | **REJECT** | Irreversible, no backup, breaks audit trail; grouping can delete legitimate same-day rows. v2 P0-9 already covers quarantine. |
| 15 | Wire orphan BOND/ETF backtests (`overall/QUICK_WINS.md:40-50`) | Partial | **MERGE** | Both classes are in `BLOCKED_ASSET_CLASSES` (`audit_trail/quality_gates.py:1724`), so “live wiring” must first be a paper/shadow path. |
| 16 | Invert ML confidence filter (`overall/QUICK_WINS.md:54-63`) | No | **REJECT** | ML code is already sound (peer), and `ml_gatekeeper/gatekeeper.py:707-730,957-966` already has a CRYPTO inversion guard that **raises the floor to 70 / can disable CRYPTO**. Flipping the comparator is dangerous and redundant. |
| 17 | Frozen dashboard prices (`overall/QUICK_WINS.md:67-77`) | No | **ALREADY_COVERED** | v2 P0-5 quote-provenance contract. |
| 18 | Intrabar-first-touch resolution (`overall/QUICK_WINS.md:85-95`) | Partial | **MERGE** | v2 P1 has this. Do **not** switch `sizing_source` globally in one step; stage by class and prove parity. |
| 19 | Bonferroni/FDR enforcement (`overall/QUICK_WINS.md:99-109`) | Partial | **MERGE** | Wrong file: `bonferroni_threshold` lives in `alpha_engine/money_ready_verdict.py:1051`, not `alpha_engine/anti_overfit_gate.py` (that file has no Bonferroni code). |
| 20 | Repair Alpha Engine (`overall/QUICK_WINS.md:113-123`) | No | **ADOPT** | v2 P0-1/P0-3 already fix the `KeyError: 'LONG'` and Python-3.14 clusters. |
| 21 | TIME_EXIT mass update (`overall/QUICK_WINS.md:127-137`) | No | **REJECT SQL** | `pnl_pct=0.0` fabricates outcomes and contradicts v4’s own “honest accounting” claim. |
| 22 | FOREX PR #6 bypass (`overall/QUICK_WINS.md:141-151`) | Partial | **ALREADY_COVERED / MERGE** | v2 P0-12 is “make the block observable (shadow)”; keep that, then enforce. |
| 23 | SSOT dashboard (`overall/QUICK_WINS.md:159-169`) | No | **MERGE (long-term)** | v2 DATA_CONTRACT/ROADMAP covers the contract; the real-time API is a later phase. |
| 24 | Walk-forward OOS gating (`overall/QUICK_WINS.md:173-183`) | Partial | **ALREADY_COVERED / MERGE** | v2 P1 structural; add the purged-K-fold detail, not the arbitrary `wf_oos_ratio < 1.2` if it would flip existing gates. |
| 25 | Retire all but five workflows (`overall/QUICK_WINS.md:187-201`) | Yes | **REJECT** | Mass deletion of 360 workflows is not a quick win; it destroys provenance and breaks scheduled jobs with shared deps. Consolidate later behind a measured plan. |
| 26 | Random-entry benchmark (`overall/QUICK_WINS.md:205-215`) | No | **ALREADY_COVERED** | Repo already has `alpha_engine/benchmark_closed_ledger.py` + `tests/test_benchmark_closed_ledger.py` with same-asset nulls. |
| 27 | Crypto price fetcher (`crypto/QUICK_WINS.md:10-27`) | No | **ALREADY_COVERED** | v2 P0-5 / quote-status contract. |
| 28 | Crypto PF-inflation filter (`crypto/QUICK_WINS.md:31-47`) | Partial | **MERGE** | Add `COUNT(DISTINCT pick_id)` and source tags, but re-derive the 5× delta from current data first (see 3.5). |
| 29 | Crypto zombie purge (`crypto/QUICK_WINS.md:51-68`) | No | **MERGE → reject SQL** | Quarantine/`EXPIRED_QUARANTINE` + label; do not bulk-update live rows. |
| 30 | Crypto confidence flip (`crypto/QUICK_WINS.md:93-111`) | No | **REJECT** | Same reason as #16; `effective_conf = 1.0 - raw_conf` is a second unvalidated inversion. |
| 31 | Crypto sample-size gate (`crypto/QUICK_WINS.md:115-131`) | No | **ALREADY_COVERED** | v2 QUICK_WINS “n + Wilson CI” and INSUFFICIENT at `forward_trades==0`. |
| 32 | Crypto LF-3 contract tests (`crypto/QUICK_WINS.md:178-196`) | Partial | **ALREADY_COVERED / MERGE** | v2 `CI_GATES.md` + `acceptance_tests.md`; port the specific assertions. |
| 33 | EQUITY/ETF/BOND force-close (`equity/QUICK_WINS.md:23-38`) | No | **REJECT SQL / MERGE quarantine** | `EXPIRED_FORCE` mass status rewrite corrupts the closed ledger. v2 says age-out with documented `TIME_EXIT`, not silent force. |
| 34 | Demote ETF/BOND to WATCH (`equity/QUICK_WINS.md:62-77`) | Partial | **ADOPT / MERGE** | v2 already adds ETF to `WATCH_ONLY_CLASSES`; BOND is already there. Safe and consistent. |
| 35 | Kill all sub-20 strategies (`equity/QUICK_WINS.md:124-141`) | No | **REJECT as written** | n<20 is precisely the regime where you cannot conclude failure; it also kills incubator measurement. Use minimum-n **reporting** gates, not emission bans. |
| 36 | Graduate `MeanReversionBB` (`equity/QUICK_WINS.md:170-193`) | No | **REJECT as written** | Selecting the one surviving sub-strategy (n=200/PF 1.76 from a 2-day-old sidecar) is the exact survivorship pattern the audit condemns. Re-derive on the full ledger first. |
| 37 | Non-crypto walk-forward (`equity/QUICK_WINS.md:147-166`) | Yes | **MERGE** | Good long-term item; align thresholds with v2 P1, not a new set. |
| 38 | FOREX blacklist enforcement (`forex/QUICK_WINS.md:20-33`) | Partial | **ADOPT with correction** | The mechanism is right, but the premise is wrong: `forex_rsi2_mean_reversion` is **not** in `BLACKLISTED_STRATEGIES` (`alpha_engine/config.py:264-...`; it only appears in comments at `:727`, a category map at `:1952`, and a disabled mapping at `:2261`). Add it explicitly, then filter. |
| 39 | FOREX hard-disable enforcement (`forex/QUICK_WINS.md:36-50`) | Partial | **MERGE (shadow first)** | Note: repo default is now **off** (`alpha_engine/config.py:345`, default `"0"`), while the check lives at `audit_trail/quality_gates.py:8860`; the log’s cited line 7789 is stale. Read the GHA variable before claiming it is active. |
| 40 | FOREX consensus dedup (`forex/QUICK_WINS.md:54-65`) | Yes | **ADOPT** | Concrete and safe: dedup `(symbol,direction,strategy)` before voting in `copy_trader_intel/non_crypto_consensus.py:150-...`. |
| 41 | FOREX source swap (`forex/QUICK_WINS.md:91-103`) | Partial | **MERGE / defer** | Removing sources is a strategy change; stage behind a shadow lane and measure. |
| 42 | FOREX scraper branch removal (`forex/QUICK_WINS.md:147-160`) | Partial | **MERGE / defer** | Code deletion is high blast radius; gate the call first. |
| 43 | COMMODITY/FUTURES unblock (`commodity/QUICK_WINS.md:12-17`) | No | **REJECT** | Removing `FUTURES` from `audit_trail/quality_gates.py:1724` unblocks a class with 0 live picks, n=13 policy-clean, and a known `futures_momentum` kill. Paper lane first. |
| 44 | Commodity zombie force-expire (`commodity/QUICK_WINS.md:19-27`) | Partial | **MERGE quarantine** | Same as #33; close with reason, keep rows. |
| 45 | Wire commodity generator (`commodity/QUICK_WINS.md:29-34`) | Partial | **MERGE (after #46)** | Only after real futures data; otherwise it wires crypto proxies into COMMODITY. |
| 46 | Commodity real-futures data (`commodity/QUICK_WINS.md:53-57`) | No | **ADOPT** | Matches v2 finding: `commodity_signal_generator.py:231-238,250` uses RNDR/ARB as “silver” and XLM/DOT as “oil.” |
| 47 | Per-symbol daily cap (`commodity/QUICK_WINS.md:40-45`) | Yes | **ADOPT** | Safe emission throttle; prevents the 6.33× CT=F over-emission. |
| 48 | Futures freshness guard (`commodity/QUICK_WINS.md:47-51`) | Yes | **ADOPT** | Safe `index[-1]` staleness skip. |
| 49 | Futures paper track record (`commodity/QUICK_WINS.md:72-76`) | Partial | **ADOPT** | Correct alternative to unblocking. |
| 50 | Peer ML: refresh stale picks (`peer_review/...:145`) | No | **MERGE** | Re-price and quarantine; do not bulk-close 30–60 d rows as a quick win. |
| 51 | Peer ML: PnL sign fix (`peer_review/...:146`) | No | **ADOPT** | Add the single-source-of-truth formula + assertion; already in v2 §3. |
| 52 | Peer ML: backfill asset_class (`peer_review/...:147`) | No | **ADOPT** | Use `alpha_engine/asset_class.py`; already in v2. |
| 53 | Peer ML: add `MUTUAL_FUND` (`peer_review/...:148`) | No | **REJECT** | No emitter/NAV source; v2 recommendation is de-advertise + `NOT_BUILT`. |
| 54 | Peer ML: lifecycle events (`peer_review/...:149`) | No | **ADOPT** | `pick_history` only has REGISTERED; safe additive fix. |
| 55 | Peer ML: populate `audit_trail.db` (`peer_review/...:150`) | No | **ADOPT** | Safe additive; also exposes why the tables are empty. |
| 56 | Peer ML: empty consensus JSON (`peer_review/...:151`) | No | **ADOPT (investigate)** | No destructive change. |
| 57 | Peer ML: harmonize freshness (`peer_review/...:152`) | No | **ALREADY_COVERED** | v2 sidecar freshness manifest. |

### Net classification counts (primary label; 57 rows)

- **ADOPT (safe, do first):** 19 rows — concurrency, silent-failure surfacing, intrabar bootstrap, MySQL fail-loud, 44-MB JSON, circuit breaker, alpha repair, ETF/BOND watch demotion, FOREX blacklist + dedup, commodity real-feed / per-symbol cap / freshness guard / paper lane, peer PnL / asset-class / lifecycle / audit-DB fixes.
- **MERGE (rewrite mechanics):** 21 rows.
- **REJECT:** 9 rows — DELETE ghosts, TIME_EXIT SQL, invert ML, `EXPIRED_FORCE`, retire 364 workflows, unblock FUTURES, add MUTUAL_FUND, sub-20 strategy ban, `MeanReversionBB` graduation (as written). Two MERGE rows (#5 dedup, #33 equity purge) and #6/#29/#44 carry a “reject the SQL/apply, keep the intent” rider.
- **ALREADY_COVERED:** 8 rows — quote provenance, random-entry benchmark, sample-size gate, contract tests, forward validation, FILTER shadow, sidecar freshness, ML soundness.

---

## 5. Destructive / dangerous fix veto table

**No `git push --force`, `reset --hard`, or `git clean` instruction exists in v4** (verified `grep -rni 'force-push|push --force|reset --hard|git clean'` → no hits). The damaging items are data and policy changes.

| # | Fix (verbatim intent) | Exact location | Why veto | Safe alternative |
|---:|---|---|---|---|
| V1 | `DELETE FROM trading_picks WHERE asset_class='MEMECOIN' AND id NOT IN (...)` | `proposed_fixes/overall/QUICK_WINS.md:31` | Irreversible hard delete; destroys audit trail; same-day legitimate rows can share the group key; MySQL self-subquery deletion is error-prone. | Quarantine view/table; keep rows; publish `ghost_flag=true`. |
| V2 | Create `alpha_engine/ghost_row_cleanup.py` nightly cleanup | `overall/QUICK_WINS.md:32` | Automates deletion; no dry-run/backup. | Nightly **report** + quarantine; require manual apply. |
| V3 | Change ML gate to `conf <= threshold` | `overall/QUICK_WINS.md:58` | Inverts a production safety gate on an unproven data diagnosis; contradicts peer finding that ML code is sound; gatekeeper already has a CRYPTO inversion guard at `ml_gatekeeper/gatekeeper.py:707-730,957-966`. | Fix labels/data; keep monotonic calibration test; do not flip the comparator. |
| V4 | Route all `conf >= 0.85` into quarantine | `overall/QUICK_WINS.md:59` | `_ml_enhanced_quarantine_n` is a reported metric, not a routing API; mass quarantine can empty the feed. | Add a shadow cohort and measure before routing. |
| V5 | `UPDATE trading_picks SET status='LOST', exit_price=entry_price, pnl_pct=0.0 WHERE status='TIME_EXIT' ...` | `overall/QUICK_WINS.md:132` | Fabricates outcomes; writes a false 0% PnL for unresolved prices; directly contradicts the “honest accounting” goal. | Resolve with real exit prices; if no price, `exit_price=NULL, pnl_pct=NULL, exit_reason='TIME_EXIT_UNPRICED'`. |
| V6 | `UPDATE at_raw_picks SET status='EXPIRED_FORCE' WHERE ... age_days > 14 AND status='OPEN'` | `equity/QUICK_WINS.md:32` | Mass status rewrite; corrupts closed-ledger stats; no dry-run; kills legitimate longer-horizon picks. | Age-out job with documented `TIME_EXIT`, reason code, and reversible flag. |
| V7 | `UPDATE picks SET status='EXPIRED', exit_reason='audit_zombie_purge' ...` | `crypto/QUICK_WINS.md:54` | One-off bulk update on live data; no dry-run; `source='ai_challenge'` may not match the real column. | Quarantine by ID list after review; keep rows. |
| V8 | Auto-expire crypto >30 d with `forward_trades=0` | `crypto/QUICK_WINS.md:55` | Blanket age rule deletes legitimate low-frequency signals and masks the missing resolver. | Report-only; require manual batch approval. |
| V9 | Runtime flip `effective_conf = 1.0 - raw_conf` | `crypto/QUICK_WINS.md:97` | A second inversion layered on a suspected data bug; no validation; can invert a correct model. | Recalibrate on a held-out set; prove monotonicity. |
| V10 | Remove `"FUTURES"` from `BLOCKED_ASSET_CLASSES` | `commodity/QUICK_WINS.md:13` (`audit_trail/quality_gates.py:1724`) | Unblocks a class with 0 live picks, policy-clean n=13, and a killed `futures_momentum`; no feed guard in place. | 30-day paper lane; keep block until paper PF/WR/n pass. |
| V11 | Force-expire COMMODITY/FUTURES zombies with 30-d cap | `commodity/QUICK_WINS.md:19-27` | Same as V6/V7; mass close without per-row price resolution. | Quarantine + reason code. |
| V12 | Retire all but 5 workflows | `overall/QUICK_WINS.md:187-201` | Mass deletion of 360 workflows; breaks cross-workflow deps; irreversible in practice. | Measure per-workflow value; retire in small batches with owners. |
| V13 | Add `MUTUAL_FUND` class to schema/strategies | `peer_review/2026-11-14-ML-AUDIT-childlike-airport.md:148` | No emitter, no NAV source, no picks; pollutes canonical classes and dashboards. | De-advertise; `NOT_BUILT` label until a real source exists. |
| V14 | Blacklist every ETF/BOND strategy with `n<20`; allow only `MeanReversionBB` | `equity/QUICK_WINS.md:128-129` | n<20 is not evidence of failure; concentrating on one selected sleeve is survivorship bias; blocks incubator learning. | Gate **reporting** at n<20; keep emission measurable. |
| V15 | Graduate `MeanReversionBB` to a standalone EQUITY scanner | `equity/QUICK_WINS.md:170-193` | One selected sub-strategy from a stale sidecar; v2 shows EQUITY aggregators disagree (8 / 759 / 738 / 461) and policy-clean PF 0.70. | Re-derive on the full ledger; require n≥100 + PF≥1.5 + benchmark beat. |
| V16 | Replace contrarian FOREX sources by removing loader paths | `forex/QUICK_WINS.md:97` | Strategy/alpha change disguised as a “quick win”; no shadow measurement. | Feature-flag a shadow lane and compare. |
| V17 | Delete `db_freshness.json` | `infra/QUICK_WINS.md:178` | Deletes evidence of a 175-day outage; the replacement does not exist yet. | Mark superseded; keep file; add `artifact_freshness.json`. |

**Note on V1/V5/V6/V7:** the corrected INDEX’s own veto table names these as “DO NOT APPLY,” which confirms the fix files are stale. The master review must treat the INDEX veto list as authoritative over the per-class files until the files are rewritten.

---

## 6. Citation spot-check (15 refs, ≥6 required)

| # | v4 reference | Verified? | Repo evidence | Drift |
|---:|---|---|---|---|
| C1 | `audit_trail/quality_gates.py:1724` = `BLOCKED_ASSET_CLASSES` | **PASS** | `1724:BLOCKED_ASSET_CLASSES: set = {"FOREX", "COMMODITY", "FUTURES", "BOND"}` | None. |
| C2 | `copy_trader_intel/non_crypto_consensus.py:~303` = `_apply_quality_gate` | **PASS** | `303: gated_picks, dropped = _apply_quality_gate(...)`; function starts `94`; `consensus_vote` at `150`. | v4 says “after ~303”; exact call is 303. Fine. |
| C3 | `alpha_engine/config.py:~264` = `BLACKLISTED_STRATEGIES` | **PASS (file)** | `264:BLACKLISTED_STRATEGIES = [` | **Content drift:** `forex_rsi2_mean_reversion` is **not** in the list; it appears only at `:727` (comment), `:1952` (category map), `:2261` (disabled mapping). v4’s premise that it is already blacklisted is false. |
| C4 | `alpha_engine/commodity_signal_generator.py:231-238,250` = crypto proxies | **PASS** | `231-235`: RNDRUSDT/ARBUSDT “silver-like proxies”; `250`: XLMUSDT/DOTUSDT WTI proxies. | v4 said 231-238; actual block ends ~235. Minor. |
| C5 | `audit_trail/universal_pick_resolver.py:1301-1338` = TIME_EXIT fallback | **PASS** | Lines 1301-1338 are the no-price TIME_EXIT block; writes `exit_price=None`, `pnl_pct=None` (not 0). | None. |
| C6 | `.github/workflows/alpha-engine-live.yml:812-828` = Full MySQL sync, `continue-on-error: true` | **PASS** | Step starts ~813; `continue-on-error: true` at 817; error/warn logic at 823-831. | Minor range drift. |
| C7 | `.github/workflows/alpha-engine-live.yml` has “58 instances” of non-fatal | **FAIL** | `grep -c 'non-fatal'` = **42**. | 16 too high. |
| C8 | `alpha_engine/claude_gainer_emitter.py` | **FAIL (missing)** | File does not exist. Actual feed: `claude_gainer_ml/tracker/short_term_active.json`, mapped in `alpha_engine/isolated_signal_integrator.py:106`. | Wrong target file. |
| C9 | `alpha_engine/non_crypto_consensus.py` (`overall/QUICK_WINS.md:145-147`) | **FAIL (missing)** | Actual file is `copy_trader_intel/non_crypto_consensus.py`; the forex file uses the correct path. | Internal path inconsistency. |
| C10 | `alpha_engine/anti_overfit_gate.py` for `bonferroni_threshold` | **FAIL (wrong file)** | The gate has no Bonferroni code; `bonferroni_threshold` is produced in `alpha_engine/money_ready_verdict.py:1051`. | Wrong module. |
| C11 | `copy_trader_intel/multi_asset_copytrader_scraper.py:2472` calls `scan_forex_rsi2_mean_reversion` | **PASS** | Call at ~2472; function at `:480-524`. | None material. |
| C12 | `alpha_engine/smart_picks_engine.py:~518` includes `non_crypto_consensus` in FOREX allowlist | **PASS** | `518: "non_crypto_consensus",` inside the FOREX allowlist; also `forex_rsi2_mean_reversion` at `515`. | None. |
| C13 | `alpha_engine/money_ready_verdict.py` `_ml_enhanced_quarantine_n` | **PASS (field)** | Present in the JSON output (`523` for CRYPTO). | It is a metric, not a routing API; v4’s proposed “route into it” is not implemented. |
| C14 | `FOREX_HARD_DISABLE` “exists in `quality_gates.py`”, default active | **PARTIAL / FAIL** | Check is at `quality_gates.py:8860`; config default is now `"0"` at `alpha_engine/config.py:345`; the log’s `line: 7789` is stale. | Must read the GHA variable before claiming it is ON. |
| C15 | `alpha_engine/ghost_row_cleanup.py`, `intrabar_replay.py`, `non_crypto_walkforward.py`, `tools/resolve_time_exit_backlog.py`, `tools/stale_artifact_refresher.py` | **FAIL (create-if-absent)** | None exist. | v4 explicitly says “create”; safe only as new modules, not as edits. |

**Drift summary:** 8 PASS, 2 PASS-with-correction, 5 FAIL (missing/wrong file), 1 FAIL (count). The operational refs (blocks, resolver, concurrency, scraper) are solid; the per-fix file refs are materially worse.

---

## 7. UNVERIFIED (do not turn these into assertions)

1. **The 4,361-row `picks_now_live_pnl` snapshot** in `dashboard_data_report.md:37,159` — not present in the repo (repo has 4,310, generated Nov 12 18:57Z). Could be the live 15:48Z version; cannot verify.
2. **True `MAX(resolved_at)` in `at_signal_outcomes`** — `db_freshness.json` says 2026-03-04 but is 175 days old; the derived intrabar JSON was generated today. Query the table directly.
3. **Whether the May-25 dashboard-vs-raw deltas still hold on 2026-11-14** — the evidence file is stale; re-derive before using the 5× PF / EQUITY-inversion / FUTURES-PF claims.
4. **`n_active_picks` at 14:30Z** — the 16:15Z payload has no such key; only `summary.total_active_picks`. The 14:30 payload is no longer served; the “0” may be a default-value artifact.
5. **Exact live count at 15:52Z** — 20 is corroborated by v4’s two deep-dives and our own v2, but the 17:57Z fetch shows 10 for the 16:15Z build; the dashboard is a moving target.
6. **`FOREX_HARD_DISABLE` effective state in production** — repo default is “0”; the GHA variable/log claims “1.” Read the variable.
7. **Whether `evidence_intrabar_truth.json` is a fresh table scan or a recomputation over stale rows** — generated today, but source freshness is unproven.
8. **`MeanReversionBB` n=200/PF 1.76** — from a 2-day-old `strategy_perf_by_class` sidecar; not re-derived on the full ledger.
9. **`Kalshi/Polymarket` real-time status** — v4 itself lists this as unverified.
10. **`inspect-wt` / Windows `E:\` peer artifacts** — not present on this Linux host, not on `origin` (our v2 verified this).

---

## 8. Instructions to the master-review agent

### 8.1 Adopt (safe, integrate first)

1. **Alpha Engine concurrency:** change `alpha-engine-live.yml:39` `cancel-in-progress: true` → `false`; mirror the proven `alpha-engine-fast.yml:13` / `audit-dashboard.yml:42` settings. This is a one-line, reversible CI fix.
2. **Fail-loud critical sync:** make `alpha-engine-live.yml` Full MySQL sync (`~813-828`) `continue-on-error: false` after adding 3× retry; make the audit-dashboard build emit `::error` on missing critical sidecars.
3. **FOREX consensus hygiene:** dedup `(symbol,direction,strategy)` in `copy_trader_intel/non_crypto_consensus.py:150-...`; add an explicit `forex_rsi2_mean_reversion` blacklist entry (it is **not** currently there); add the `FOREX_HARD_DISABLE` check to consensus as a **shadow** gate first.
4. **COMMODITY provenance:** replace RNDR/ARB/XLM/DOT proxies in `alpha_engine/commodity_signal_generator.py:231-250` with real `GC=F/SI=F/CL=F` data; add the 2-trading-day staleness skip; add the 1-pick/`(symbol,strategy,direction)`/day cap. Do **not** wire the generator to live until the feed is real.
5. **Peer SQLite fixes:** add the PnL single-source formula + assertion; backfill `asset_class` via `alpha_engine/asset_class.py`; emit CLOSED/EXIT events into `pick_history`; populate `audit_trail.db`. All additive and reversible.

### 8.2 Merge (take intent, rewrite mechanics)

1. **Quote-provenance / frozen PnL:** merge v4 crypto QW-1 + forex MF-1 + overall QW-5 into our P0-5 contract (`LIVE`/`LAST_CLOSE`/`STALE`/`UNQUOTED`/`PLACEHOLDER`; `null` never `0.00%`).
2. **Sidecar freshness:** merge v4 infra QW-3/MF-3 into our P0-7 manifest; do **not** delete `db_freshness.json`.
3. **Orphan merge:** merge v4 infra QW-4/LF-4 into one merge step with `source_system` tagging and the economic dedup key; do not build two mergers.
4. **TIME_EXIT / zombie cleanup:** merge the intent into our age-out policy; replace every bulk UPDATE with quarantine + real price resolution + reason code.
5. **Multiple-testing / PF parity:** merge v4 overall MF-2 + crypto QW-2, but correct the target to `alpha_engine/money_ready_verdict.py:1051` and re-derive the 5× delta from current data before setting thresholds.
6. **Intrabar-first-touch:** merge v4 overall MF-1 into our P1; stage by class; do not globally switch `sizing_source` in one release.
7. **FOREX/COMMODITY futures lanes:** merge v4 commodity 3.2 + forex LF-1 into paper-only lanes; keep the class blocks until n/PF/WR pass.
8. **`claude_gainer_st` labeling:** merge the intent into the ingest/resolver label fix (`EXPIRED` → `LOST` only with a real reason); correct the target to `claude_gainer_ml/tracker/short_term_active.json` + `isolated_signal_integrator.py:106`.

### 8.3 Veto (do not ship)

1. **All hard deletes** — V1/V2 (`overall/QUICK_WINS.md:31-32`), V5 (`infra` dry-run apply), V13 (`db_freshness` deletion). Quarantine/tag instead.
2. **All fabricated-status rewrites** — V5 `TIME_EXIT→LOST pnl=0` (`overall:132`), V6 `EXPIRED_FORCE` (`equity:32`), V7/V8 crypto zombie updates (`crypto:54-55`), V11 commodity force-expire.
3. **All ML inversions** — V3 (`overall:58`) and V9 (`crypto:97`); the gate is already inverted-guarded, and the peer ML audit says the code is sound.
4. **Policy reversals without evidence** — V10 unblock FUTURES (`commodity:13`), V13 add `MUTUAL_FUND` (`peer:148`), V12 retire 364 workflows (`overall:191`).
5. **Survivorship promotions** — V14 sub-20 bans and V15 `MeanReversionBB` graduation as written; re-derive first.

### 8.4 What to cite from v4 (and what not to)

- **Safe to cite:** the concurrency root cause, `|| non-fatal` masking (correct count to 42), SQLite peer findings (already in our v2), commodity proxy lines, the `BLOCKED_ASSET_CLASSES` line, the FOREX allowlist/consensus paths.
- **Do not cite without re-derivation:** the 5× PF, EQUITY filter inversion, FUTURES PF 131.6, the 4,361 backlog, the 0-active claim, the 254-day intrabar claim, the “FUTURES 2–8 signals/week” projection.
- **Do not cite at all:** `alpha_engine/claude_gainer_emitter.py`, `alpha_engine/non_crypto_consensus.py`, `alpha_engine/anti_overfit_gate.py` for Bonferroni, or the “SAFE headings” claim.

---

## 9. Bottom line

**FAIL for merge-readiness**, with a usable core:

- The v4 **operational** findings are good: concurrency, silent-failure masking, orphaned pipelines, SQLite peer bugs, commodity proxy provenance, and the `BLOCKED_ASSET_CLASSES` fact are all real and mostly verified.
- The v4 **performance** story is unreliable as written: its headline “0 active / 26-day dashboard” is a repo-vs-live + wrong-field artifact; its class counts are a 45–53-hour-old backlog, not active positions; its dashboard-vs-DB deltas use a **173-day-old** evidence JSON; and its “254-day” claim is a clock mix-up.
- The v4 **fix set** cannot go to an implementer unchanged: it contains hard DELETEs, fabricated PnL/status rewrites, ML inversions, an unguarded FUTURES unblock, a mutual-fund class with no feed, and 364-workflow deletion — all of which the corrected INDEX itself now vetoes, while the fix files still contain them and no “SAFE” headings exist.

**Master-review recommendation:** take the 19 ADOPT rows and the 21 MERGE intents; reject the 9 REJECT rows; re-derive the performance deltas before using them; and treat the current INDEX veto table as authoritative over the stale per-class fix files. With those changes, v4 becomes a useful supporting archive rather than a second, conflicting source of truth.

---

*PF3, 2026-11-14. Evidence: v4 archive as listed; live `https://findtorontoevents.ca/audit/data/dashboard_data.json` fetched 2026-11-14T17:57Z; repo source files cited above. No repo source modified.*
