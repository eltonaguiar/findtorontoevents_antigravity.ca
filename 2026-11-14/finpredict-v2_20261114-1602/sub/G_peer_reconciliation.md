# Subagent G — Peer-Work Reconciliation (2026-11-14)

**Scope:** find and reconcile every prediction-system audit artifact produced on 2026-11-14 by peer agents, compare the peer transcript's claims to newer peer evidence and to the repo's own data/code, and identify what is missing before the master review.
**Mode:** research only; no repo files modified (this report is the only write).
**Audit as-of:** 2026-11-14T16:03Z (all ages recomputed to this instant unless stated).
**Primary data payload:** `/tmp/kilo/audit_data/dashboard_data.json` — 25 MB, `generated_at = 2026-11-14T14:30:07Z`, SHA `1b2c98e` (used by all three peers).
**Caution:** the repo copy `/home/eaguiar2015/findtorontoevents_antigravity.ca/audit_dashboard/data/dashboard_data.json` is **Oct 23 01:49** (stale). Do **not** verify live claims against it.

---

## VERDICT: **PASS** (peer artifacts are available and reconcilable)

Three independent peer audit subtrees produced artifacts today, and their headline numbers are mutually consistent on the verdict (not money-ready; data pipeline broken). Two specific transcript figures ("61% spot-flicker", "37 active in June") are **NOT** supported by any artifact found on disk, and the peer transcript file itself is **NOT FOUND**.

**PASS/FAIL breakdown**
- **PASS** — peer audit outputs exist for `finpredict`, `finpredict-v3`, `finpredict-v4`/`wt-audit-prediction-system`, all timestamped 2026-11-14 15:44–16:05Z.
- **PASS** — core numeric claims (Actions failures, per-class ages, raw-feed median age, BOND 98h, NEAR ±8.75%/−12.03%, XRP entry 0.0) reproduced independently from the shared payload / GitHub-API report.
- **FAIL (artifact missing)** — the pasted transcript (`chat_transcript_2026-11-14.md`, claimed Windows path) has no copy on this Linux host.
- **FAIL (unsupported figures)** — 61% spot-flicker and "37 active in June" are not reproducible from any 2026-11-14 artifact; both appear to be stale/cohort-specific numbers.

---

## 1. Artifact inventory (today's peer work only)

| # | Path | mtime (UTC) | What it is | Provenance / commit |
|---|------|-------------|------------|---------------------|
| 1 | `/home/eaguiar2015/findtorontoevents_antigravity.ca/.kilo/worktrees/finpredict/2026-11-14/finpredict/2026-11-14T160004Z/README.md` | 16:02 | Merged session summary; cross-references inspect-wt, v3, v4-era findings | Branch `finpredict` (worktree `tortoiseshell-beam`), commits `b4bc50c` + `4f24b23` |
| 2 | `.../finpredict/.../updates/2026-11-14-prediction-system-audit.md` | 16:02 | **Most complete single audit doc** (178 lines): Actions, per-class actives, frozen data, metric liveness, live-price cross-check, closed picks, multiple-testing | same branch (committed) |
| 3 | `/home/eaguiar2015/findtorontoevents_antigravity.ca/.kilo/worktrees/finpredict-v3/2026-11-14/finpredict-v3/2026-11-14T155500Z/README.md` | 16:01 | Data-hygiene session summary + peer reconciliation | Branch `archive/2026-11-14-finpredict-v3`, commits `b83eee`/`a061648` |
| 4 | `.../finpredict-v3/.../updates/2026-11-14-prediction-data-hygiene.md` | 16:01 | Defect evidence + per-class remediation plan (target files/lines) | same branch (committed) |
| 5 | `.../finpredict-v3/.../tools/pi_data_hygiene.py` | 16:01 | **Runnable, additive/read-only** guardian: STALE_CRYPTO_PRICE, FROZEN_CLOSED_PHANTOM, DATE_ONLY_SEED, NULL_PRICE, PLACEHOLDER_ENTRY, ACTIVE_RAW zombie scan | same branch |
| 6 | `.../finpredict-v3/.../tests/test_pi_data_hygiene.py` | 16:01 | 11 unit/integration tests (README says 11 passed; the updates doc says 12 — minor inconsistency) | same branch |
| 7 | `/home/eaguiar2015/findtorontoevents_antigravity.ca/audits/2026-11-14/finpredict-v4_2026-11-14-1555/INDEX.md` | 16:00 | v4 master index + executive verdict | Main worktree `audits/`; **no commit found in today's reflog/log** → treat as uncommitted |
| 8 | `.../finpredict-v4_.../actions_health_report.md` | 15:58 | **GitHub-API-verified** workflow health: 365 workflows, 28 failing last run, 39 with ≥3/5 failures, 20 never run | uncommitted; source `/home/eaguiar2015/wt-audit-prediction-system/audit_output/` |
| 9 | `.../dashboard_data_report.md` | 15:58 | Per-class active table, intrabar truth, DB-vs-dashboard divergences, 14-day raw-DB cohort | uncommitted |
| 10 | `.../market_crossref_report.md` | 15:58 | 19 picks vs Binance + Yahoo live quotes; June AI-challenge staleness (+143% NEAR) | uncommitted |
| 11 | `.../crypto_deep_dive.md` | 16:05 (source 15:59) | 3 live crypto picks vs Binance; proves `age_hours` is build-relative; PnL understatement | uncommitted |
| 12 | `.../noncrypto_deep_dive.md` | 16:05 (source 16:01) | EQUITY/ETF/BOND/COMMODITY/FUTURES alive-vs-dead; **June-snapshot based** | uncommitted |
| 13 | `.../forex_deep_dive.md` | 16:05 (source 16:02) | Forex verification + PR #6 block check | uncommitted |
| 14 | `.../dashboard_metrics_sources.md` | 16:05 (source 16:00) | Metric provenance, kalshi/polymarket/copy-trader/alpha-engine pipeline audit; claims live table = 0 picks | uncommitted |
| 15 | `.../evidence_money_ready_verdict.json` | 15:58 | Per-class money-ready gates (all FAIL/INSUFFICIENT) | uncommitted |
| 16 | `.../evidence_intrabar_truth.json` | 15:58 | Honest intrabar-true per-class performance | uncommitted |
| 17 | `.../evidence_pick_summary_stats.json` | 15:58 | 14d/48h stats; dashboard-vs-raw-DB divergence | uncommitted |
| 18 | `.../evidence_db_health.json` | 15:58 | 22,947 ghost rows | uncommitted |
| 19 | `/home/eaguiar2015/wt-audit-prediction-system/audit_output/{crypto,forex,noncrypto}_deep_dive.md`, `dashboard_metrics_sources.md` | 15:59–16:02 | Source copies of #11–14 (duplicate set) | Branch `audit-prediction-system-20261114-154529`, HEAD `7c80a16`; **audit outputs uncommitted** |
| 20 | `/tmp/kilo/audit_summary.txt` | 15:48 | Raw `summary` block (126 systems, 16,126 closed, WR 41.8, PF 0.94, Sharpe −1.31) | Scratch evidence (not a repo artifact) |
| 21 | `/tmp/kilo/audit_data/*.json` | 15:44–15:51 | Downloaded live payload + sidecars (`dashboard_data.json` 25 MB, `money_ready_verdict.json`, `strong_signals.json`, `stock_forex_prices.json`, etc.) | Scratch evidence |
| 22 | `/home/eaguiar2015/findtorontoevents_antigravity.ca/.kilo/worktrees/spice-hyena/` | 09:48 | Branch `review-branches-and-salesforce-guides` (renamed from `spice-hyena`); no 2026-11-14 audit output | Not an audit artifact today |
| 23 | `/home/eaguiar2015/findtorontoevents_antigravity.ca/.kilo/worktrees/finpredict-v4/` | 15:44 | June-snapshot code+data tree used by v4 subagents (`audit_dashboard/data/pf_registry.json` generated 2026-11-12) | Branch `finpredict-v4`, HEAD `1d9354a`, no new commit |

### Named files that do **not** exist as today's peer artifacts
| Name searched | Result |
|---|---|
| `chat_transcript_2026-11-14.md` / `.MD` | **NOT FOUND** anywhere under `/home/eaguiar2015` or `/tmp/kilo` (grep for `chat_transcript_2026-11-14`, `2128h`, `2,128h` found none) |
| `wt-audit-prediction-system/chat_transcript.MD` | Exists, but is an **unrelated 2026-05-15 transcript** (28 lines, daily_ideas commits); same file at repo root dated May 25 |
| `MARKET_BEATING_REPORT.md`, `STATISTICALLY_VALID_WINNERS_ANALYSIS.MD`, `NONCRYPTO_PF_TRUST_INVESTIGATION*`, `summary_*.md` | Only **June-snapshot copies** (mtime 15:45, content dated Apr–May 2026). No 2026-11-14-authored versions. |
| `2026-11-14*` folders in `wt-audit-prediction-system` / `finpredict-v4` / `spice-hyena` | **NOT FOUND**. Only `finpredict/2026-11-14/…`, `finpredict-v3/2026-11-14/…`, and `audits/2026-11-14/…` exist. |

---

## 2. Claim reconciliation

Status key: **AGREES** = reproduced; **PARTIAL** = directionally right, exact figure differs; **SUPERSEDED** = was true for an older cohort/window, replaced by newer evidence; **CONTRADICTS** = evidence disagrees; **NOT FOUND** = no artifact to test.

| # | Peer-transcript claim | Status | Evidence (file:line or command result) |
|---|---|---|---|
| 1 | Actions failures | **AGREES** | v4 `actions_health_report.md:15-24` — 365 workflows, 361 active, **28 failed their last run**, 20 never run. `:49-50` — **39 workflows with ≥3/5 failures/cancellations**. finpredict `2026-11-14-prediction-system-audit.md:15` independently reports 28 failure / 11 cancelled / 295 success. Peer's named examples confirmed: `Daily Prices yfinance` last run `failure` 2026-11-13 (`actions_health_report.md:228`), `Daily Price Refresh` failure (`:26`), `ALPHA ENGINE FAST` 4/5 failures (`:57`). |
| 2 | Active picks **37 in June** | **CONTRADICTS / SUPERSEDED** | No June artifact says 37. The **37-active** figure is from a **May 2** payload: `wt-audit-prediction-system/reports/kimi_swarm_2026_05_02_v3/HEDGE_FUND_AUDIT_REPORT_2026_05_02.md:5` ("n=3500 closed, 37 active, generated 2026-05-02T23:02Z"); also `docs/AUDIT_ADDITIONAL_FIXES_2026_04_20.md:3`. Live 14:30 payload: `.picks.active` = **20**, `.picks.active_raw` = **4,148**, `summary.concentration_summary.total_active` = **263**. Separate tracker `picks_now_live_pnl.json` = **4,310 open** (v4 `dashboard_metrics_sources.md:181`). |
| 3 | Frozen data **61% spot-flicker** | **CONTRADICTS (as system-wide) / NOT FOUND (as 1,147/1,882)** | No artifact contains `1,147` or `1,882` as a flicker pair. June/current `pf_registry.json` (`generated_utc 2026-11-12T18:18:49Z`) says `closed_rows 28,460`, `dropped_spot_flicker 2,188` = **7.7%** (`jq .counts`). Current `recent_closed` has **12/3,500 exit_price==entry (0.34%)**. The 61% may be a narrow June 14-day cohort, but that cohort is **not on disk**; do not state it as a system number. |
| 4 | Closed last-14d P/L **−1.4%** | **SUPERSEDED** | The −1.4% is the June 191-trade cohort adopted in finpredict `…audit.md:164`. Live payload last-14d (closed_at ≥ 2026-11-01): **n=751, sum −333.2%, mean −0.44%**; last-7d (≥ 11-07): CRYPTO −330.9, FOREX −1.28, BOND −3.38, COMMODITY −6.52, EQUITY +67.8, ETF +25.2. The current window is ~240× worse than −1.4%; don't merge the stale figure as current. |
| 5 | Per-class ages COMMODITY 1.5h / CRYPTO 2.0h / FUTURES 2.8h | **AGREES (within as-of skew)** | Payload `signal_time`: COMMODITY 14:22:03 → **1.7h**; CRYPTO newest 13:53:28 (v4 `crypto_deep_dive.md:150-151`) → **2.2h** (displayed NEAR 13:10:05 → 2.9h); FUTURES `ES=F` stored as bare `"2026-11-14"` with `age_hours 1.4` at 14:30 build → **~2.9h** at 16:03. Every figure is 0.1–0.4h higher than the peer's because the peer used ~15:50. Same pattern for EQUITY 3.3h / ETF 3.8h / FOREX 1.7h. |
| 6 | `.picks.active_raw` CRYPTO median age **2,128h (89d)** | **AGREES** | Recomputed over all parseable CRYPTO raw rows (n=3,535 of 3,577): **median 2,152.1h = 89.7d**; p25 880h; max 6,421.7h (267.6d); **3,085 rows >7d** — exactly the v3 README count. The 24h delta vs 2,128h is the as-of difference. |
| 7 | BOND newest closed **98h** | **AGREES** | Newest BOND row in `recent_closed`: `TLT … closed_at 2026-11-10T14:37:34Z` → **~97.5h** at 16:07Z; n=35 BOND closed rows. Separately, BOND `active_raw` = 15 rows, all OPEN, **9 null current_price** (v3 `…data-hygiene.md:56-57`). |
| 8 | NEARUSDT **+8.75% TP_HIT** and **−12.03% SL_HIT** | **AGREES (exactly)** | `.picks.active_raw`: `NEARUSDT SHORT entry 3.543 → 3.233, TP_HIT, source inverse_mutations` = (3.543−3.233)/3.543 = **8.749%**; `NEARUSDT LONG entry 3.675 → 3.233, SL_HIT` = (3.675−3.233)/3.675 = **−12.027%**, dated 2026-11-13. Caveat: these are **resolved rows still sitting in `active_raw`** — an inventory defect in itself. They are **not** in `recent_closed` (whose 3.543 rows are different LONG trades at +5.14%/+3.70%). |
| 9 | XRPUSDT **entry 0.0** | **AGREES** | `.picks.active_raw`: `XRPUSDT SHORT entry 0.0, current_price null, status OPEN, signal_time 2026-11-14, source prediction_market_consensus`; identical 0.0 rows for `SOLUSDT` and `DOGEUSDT` from the same source. Note a **second PM feed disagrees**: `pm_kalshi_signals` XRPUSDT = 0.9842 with current 0.9842 (frozen), so "Kalshi" itself did not emit 0.0 — `prediction_market_consensus` did. |
| 10 | Kalshi etc. (stale snapshot / dead PM feeds) | **PARTIAL** | Payload has 4 `pm_kalshi_signals` rows (XRP/DOGE/BTC/SOL), **all current_price == entry_price** → frozen (finpredict `…audit.md:92`). But the claimed "on-disk kalshi snapshot ~7 months stale" is **NOT FOUND**: no `*kalshi*.json`, `*polymarket*.json`, or `*prediction_market*.json` exists in either `audit_dashboard/data/` tree. v4 `dashboard_metrics_sources.md:101-105` verifies code + silent `|| echo` failure handling but not a 7-month file. |
| 11 | Verdict "not profitable / multiple-testing artifact" | **AGREES (3 independent peers)** | Payload summary: 126 systems, 16,126 closed, valid 7,914, WR 41.8, PF 0.94, expectancy −0.11, Sharpe −1.31 annual, compounded EW −99%, 30d DD 31.2%. v4 `evidence_money_ready_verdict.json` = 0/9 classes pass; finpredict `…audit.md:147-154` gives the multiple-testing/survivorship math. |
| 12 | Actions "Unified Audit Dashboard cancelled 3× with 0 jobs" | **SUPERSEDED** | True for the June observation, not now: v4 `actions_health_report.md:172` shows `Unified Audit Dashboard` run **in_progress** at 2026-11-14T15:14Z. Don't present the 3× cancel as current. |
| 13 | "ALPHA ENGINE FAST 2 failures in last 4" | **PARTIAL (worse now)** | v4 `:57` shows **4 failures / 5 last runs**, last run 15:35Z. |
| 14 | External market quotes UNVERIFIED (peer sandbox blocked) | **GAP CLOSED by peers** | finpredict verified 5 rows via Binance + Frankfurter (`…audit.md:107-119`); v4 crypto_deep_dive verified 3 rows via Binance at 15:52:38Z (`:125-129`); v4 market_crossref verified 19 picks via Binance + Yahoo (`:21-43`). Equity marks remain Yahoo "Friday close", not a paid feed — residual gap. |

---

## 3. Peer gaps and whether newer work closed them

| Gap | Closed today? | Evidence / residual risk |
|---|---|---|
| Transcript copy (`chat_transcript_2026-11-14.md`) | **NO** | Not on disk. All transcript claims here are reconstructed from the task brief + peers quoting it (finpredict §10 and v3 "Peer cross-validation"). If the master review needs verbatim quotes, the user must re-supply the file. |
| Root cause of workflow failures (per-step logs) | **NO** | v4 verified *counts* and named failing steps (Install dependencies, Run Alpha Engine, FTP download) via the API, but not the log text. finpredict `…audit.md:171` also marks logs UNVERIFIED (admin required). |
| Kalshi/Polymarket snapshot staleness | **NO** | No kalshi/polymarket JSON in either data tree; only source code and payload rows. |
| 61% spot-flicker cohort | **NO** | The 1,147/1,882 pair does not exist in any artifact; registry-wide flicker is 7.7%. |
| "37 active in June" | **NO** | Only May 2 evidence exists. Current live counts differ by surface (see claim 2). |
| External quotes for live picks | **YES** | Binance + Frankfurter (finpredict) and Binance + Yahoo (v4). Crypto/forex verified to the cent; equities only Friday close. |
| Active-pick count reconciliation | **NO — now worse** | Five different "active" numbers coexist: 20 (curated `.picks.active`), 4,148 (`active_raw`), 263 (`concentration_summary.total_active`), 4,310 (`picks_now_live_pnl` n_open), and **0** (v4 `dashboard_metrics_sources.md:13,73` says the live table was empty at 15:53). The master review must name the surface before quoting a count. |
| Per-class recency for non-crypto | **NO — peers disagree** | v4 noncrypto (June snapshot) says COMMODITY newest ~156 days / DEAD, FUTURES 0 live, EQUITY ~2.4 days. The live 14:30 payload has COMMODITY signals at 14:22 today, EQUITY at 12:44–13:05, FUTURES 3 OPEN placeholders. v4's verdicts describe the June dataset, not the live payload. |
| Intra-peer contradiction on "live table empty" | **NO** | v4 `dashboard_metrics_sources.md` says 0 active picks / 0 closed; v4's own `dashboard_data_report.md:26-37` lists 25 top-25 picks and 4,361 open in `picks_now_live_pnl`. finpredict sees 20 curated actives in the same payload. Likely different surfaces/endpoints; unresolved. |

---

## 4. Recommended merges for the master review

1. **Backbone:** adopt `/home/eaguiar2015/findtorontoevents_antigravity.ca/.kilo/worktrees/finpredict/2026-11-14/finpredict/2026-11-14T160004Z/updates/2026-11-14-prediction-system-audit.md` — it is the only peer doc that already cross-references all other peers and separates verified from attributed claims.
2. **Replace §1 Actions with v4 evidence:** merge `audits/2026-11-14/finpredict-v4_2026-11-14-1555/actions_health_report.md` (GitHub-API counts: 28 failing, 39 flaky, 20 never-run) as the primary; keep finpredict's named-step list as commentary.
3. **Replace §2/§4 recency mechanics with v4 `crypto_deep_dive.md`:** its `age_hours`-relative-to-`generated_at` proof explains why "1.9h ago" is signal age and why the peer's 2.0h/2.8h ages are build-relative.
4. **Adopt v3 as the only runnable deliverable:** `finpredict-v3/2026-11-14/finpredict-v3/2026-11-14T155500Z/tools/pi_data_hygiene.py` + tests + per-class remediation targets. It reproduces the defects and is CI-gateable (exit 1).
5. **Label, do not merge, v4 noncrypto verdicts:** `noncrypto_deep_dive.md` is June-snapshot evidence (COMMODITY "dead since June", FUTURES "0 live"). Merge as "June baseline", not as today's state — the live payload contradicts it.
6. **Merge v4 `market_crossref_report.md` only for the June AI-challenge cohort:** its NEAR entry 1.326 → 3.224 (+143%) is a different pick from the live NEAR (entry 3.324/3.543). Present them as two cohorts; do not average or conflate.
7. **Do NOT merge without qualification:** "37 active in June", "61% spot-flicker", "last-14d −1.4%". Replace with: 20 curated / 4,148 raw / 263 concentration; registry flicker 7.7%; live 14d sum −333.2%.
8. **Deduplicate:** the 4 deep dives exist twice (wt-audit `audit_output/` + `audits/`). Use `audits/2026-11-14/finpredict-v4_2026-11-14-1555/` as canonical; note it is currently **uncommitted**.
9. **Commit hygiene:** finpredict and v3 archives are on branches with commits; the v4 archive and `wt-audit-prediction-system/audit_output/` have no matching commit in today's reflog. The master review should commit them on a clean branch (per the repo's archive convention) before citing paths.

---

## 5. Evidence appendix (reproducible commands)

All were run read-only against the shared payload; `now = 1794672400` (approx 16:06Z) in the jq filters.

| Check | Command (abridged) | Result |
|---|---|---|
| Section sizes | `jq '(.picks.active|length),(.picks.active_raw|length),(.picks.recent_closed|length)'` | 20 / 4148 / 3500 |
| CRYPTO raw median age | `jq '[.picks.active_raw[]|select(.asset_class=="CRYPTO")|…]|sort|…'` | n=3535, median 2152.1h (89.7d), >7d = 3085, max 6421.7h |
| BOND newest closed | `jq '.picks.recent_closed|map(select(.asset_class=="BOND"))|sort_by(.closed_at)|.[-1]'` | TLT `2026-11-10T14:37:34Z`, SL_HIT, −1.099% |
| NEAR extremes | `jq '.picks.active_raw[]|select(.symbol|test("NEAR"))|select(.entry_price==3.543 or .entry_price==3.675)'` | SHORT 3.543→3.233 TP_HIT (+8.75%); LONG 3.675→3.233 SL_HIT (−12.03%) |
| Zero-entry PM rows | `jq '.picks.active_raw[]|select(.entry_price==0)'` | XRP/DOGE/SOL entry 0.0, current null, source `prediction_market_consensus`; plus BTC/ETH/AVAX 0.0 from genetic_programmer/mape_evolver/genome |
| Kalshi frozen | `jq '.picks.active_raw[]|select(.source_system|test("kalshi"))'` | 4 rows, all `current==entry` |
| 14d closed | `jq '[.picks.recent_closed[]|select(.closed_at[0:10]>="2026-11-01")|.pnl_pct]'` | n=751, sum −333.196, mean −0.4437 |
| Summary | `head -40 /tmp/kilo/audit_summary.txt` | 126 systems, 16,126 closed, 7,914 valid, WR 41.8, PF 0.94, Sharpe −1.31, EW −99.0 |
| Sidecar freshness | `jq '.generated_at' hyro_pick_performance.json`; `jq '.updated_at' stock_forex_prices.json` | hyro 2026-11-08T02:14Z (**~158h**); stock_forex 2026-04-11 (**217d**); strong_signals 2026-04-15 (**213d**) |
| Registry flicker | `jq '.counts' …/finpredict-v4/audit_dashboard/data/pf_registry.json` | closed 28,460; spot-flicker dropped 2,188 (7.7%) |
| "37 active" origin | grep `37 active` in wt-audit repo | `reports/kimi_swarm_2026_05_02_v3/...:5` — generated **2026-05-02T23:02Z** |

---

### Bottom line for the master review
Peer-artifact availability is **PASS**: three independent audits exist, agree on the negative verdict, and collectively close the external-price gap. The transcript's **quantitative core is confirmed** (Actions failures, raw-feed ages, BOND 98h, NEAR ±8.75/−12.03, XRP 0.0). Three numbers in circulation must be dropped or relabelled: **37 active (May, not June)**, **61% spot-flicker (registry is 7.7%)**, and **−1.4% 14-day P/L (live is −333% sum)**. The unresolved issue is definitional: five different "active pick" counts and an intra-v4 contradiction between "empty live table" and "25 top-25 picks".
