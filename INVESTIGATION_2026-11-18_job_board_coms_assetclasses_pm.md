# Investigation — Job Board Algorithm, COMS, /audit Asset Classes, Copy-Trader/Kalshi/Polymarket

**Date:** 2026-11-18 · **Author:** buffy (Freebuff) · **Repo:** `findtorontoevents_antigravity.ca` @ `main`
**Method:** read-only. Live HTTP pulls for `/audit`, `gh` API for BESTIEJOB run history, shallow clone of `eltonaguiar/bestiejob` at `/tmp/bj-inspect`, local artifact mtimes.
**No commits, no pushes, no workflow triggers.**

---

## 0. TL;DR — the five things that actually matter

| # | Finding | Severity |
|---|---------|----------|
| 1 | **BESTIEJOB "Job Source Truth Check" has been red for 15+ consecutive hourly runs** (11-17 13:21Z → 11-18 02:25Z). Cause: 13 paywall-aggregator rows in `README.md`, and *no gate prevents new ones from being merged back in.* | **P0** |
| 2 | **`/audit` reports two different performance ledgers per asset class that disagree in both n and sign** — EQUITY is `PF 10.16 / WR 66.7` on the headline and `PF 0.62 / WR 38.7` in the readiness gate. CRYPTO is n=5,031 vs n=22,379. | **P0** |
| 3 | **Kalshi pick verification reads a 7-month-old snapshot.** `data/kalshi_snapshots/` holds exactly one file (2026-04-26) although the Kalshi agent ran 36 events → 4 signals at 23:07Z. | **P0** |
| 4 | **`gap-channels` fails at "Commit and push" every 6h** — all 9 work steps succeed, then the push dies. ~9 min of harvested rows discarded each cycle. | P1 |
| 5 | **Zero asset classes are money-ready.** All 9 report `sizing_allowed: false`; only ETF clears PF ≥ 1.25 (1.65) and it has n=25. | P1 (honesty is working) |

---

## 1. Job posting algorithm (BESTIEJOB)

### 1.1 What the pipeline is

12 workflows in `eltonaguiar/bestiejob` (pushed 2026-11-18T02:18Z, still active):

| Workflow | Cadence | Role |
|---|---|---|
| `hourly-scan.yml` | hourly `:00` | `scripts/daily_job_scan.mjs` → drop 404/410/451 → merge |
| `fresh-ca-scan.yml` | 6h `:25` | today+yesterday CA sweep |
| `linkedin-sweep.yml` | — | LinkedIn guest API rounds |
| `gap-channels-daily.yml` | 6h `:40` | Workday / Phenom / Oracle / Job Bank / Workable |
| `agency-board-scan.yml` | — | agency portals |
| `truth-check.yml` | hourly `:17` | **the failing gate** |
| `board-invariants.yml`, `readme-guard.yml`, `inbox-guard.yml`, `pages.yml`, `scrape_jobs.yml`, `undated-recheck.yml` | mixed | guards + publish |

All writers serialise on `concurrency.group: bestiejob-main-write, cancel-in-progress: false`.

### 1.2 The ranking algorithm itself

`tools/build_site.py::match_score` (lines ~304-326) — this is the "posting algorithm" in the sense of ordering:

- `PROFILE` = list of `(regex, weight, label)` pairs matched against `title + location + note + company`.
- A hit scores `weight × 2` if it matches the **title**, else `weight × 1`.
- Location bonus: Toronto/Ontario/GTA/Mississauga/Markham/Brampton +12; Canada-or-remote +8; Quebec +4.
- `WEAK` title regex multiplies the whole score by **0.35**.
- Capped at 100, top-5 reasons kept, emitted into `public/jobs-data.json` as `match` + `reasons`.

Board-level filters that run *before* ranking:

- `jobs_merge_inbox.py`: `EXCL` regex drops sales/marketing **job functions** (carefully scoped so "Marketing Cloud Specialist" survives), `is_listing_url()` drops aggregator listing pages, requires absolute `YYYY-MM-DD` date + URL.
- `dedupe()` from `jobs_consolidate.py`.
- `--max-per-table 500` (default 150 silently evicts in-window rows).

### 1.3 Defects found

**D1 — truth-check red since 11-17 13:21Z (15 consecutive failures). P0.**
`tools/job_source_truth.py` exit rule (end of `main()`):

```python
return 1 if report["gated"] and args.check else 0
```

`--check` scans **README.md + FRESH_JOBS.md + jobs.json** and fails when *any* gated row exists in *any* of them. Current state:

- `README.md`: **13** gated dated rows (11 `www.jobleads.com`, 2 `www.theladders.com`), out of 7,921 dated rows.
- `jobs.json`: **11** gated rows (9 jobleads, 2 theladders).

The rows are old (2026-10-30 → 2026-11-04) and include real ServiceNow roles ("ServiceNow Developer (CONTRACT ROLE)", "ServiceNow CSM/OMT Architect"). They are *real postings behind a paywall* — exactly the case this gate exists for — so the gate is right and the board is wrong.

**D2 — no gated-domain gate at ingest. P0 (root cause of D1).**
`grep` across `tools/` and `scripts/`: only `build_site.py` imports `job_source_truth` (`domain_is_gated`, line 37) — and it merely **labels** the row `gated` and swaps in a cross-ref alternate; it never removes it. `jobs_merge_inbox.py` never imports it. `scripts/partner_sponsor_scan_verified.py` has an unrelated `MIRROR` regex.

⇒ Cleaning README once will go red again on the next inbox merge that carries a jobleads row. **Both halves are required.**

**D3 — `config/gated_domains.txt` is documented but does not exist. P1.**
`_extra_domains()` reads `config/gated_domains.txt` and silently no-ops when absent. `config/` holds `agency_boards.json` and `agency_portals.json` only. The blocklist is frozen at 4 hosts (jobleads.com, www.jobleads.com, theladders.com, www.theladders.com) with no data-driven extension path in use.

**D4 — dedupe is inbox-only, never board-wide. P1.**
`dedupe()` runs on merged inbox rows. Existing README rows are never re-deduped. In the "Other jobs" section: **4,992 rows, 27 exact `(date,title,url)` duplicate keys** — e.g. the PwC Brasil "IRM/GRC Technologies Senior Associate" LinkedIn row appears **3×**, plus 2× Adzuna duplicates. `readme_job_row_guard.py` checks row counts, so duplicates are invisible to CI.

**D5 — `gap-channels` fails at step 11 of 11, "Commit and push". P1.**
Run 44211439366: dedupe-index build, sweep, net-new report, submission validation, inbox merge, jobs.json parse guard, feed rebuild — **all success** — then `Commit and push: failure`. It shares `bestiejob-main-write` with hourly-scan and fresh-ca-scan, so the push is the casualty of a concurrent writer + rebase. ~9 min 17 s of harvest lost per 6h cycle. `gh run view --log` for that run now returns empty (logs expired), so the exact rejection text is not recoverable from history.

**D6 — dedupe hazard on query-stripped URLs. P1 (risk, not yet a live bug).**
84 rows share the prefix `https://instacart.careers/job/`, 49 `careers.toasttab.com/jobs`, 28 `jobs.elastic.co/jobs`. These are **distinct** Greenhouse postings distinguished only by `?gh_jid=…`. `gap-channels-daily.yml` normalises URLs by stripping `refId`/`trackingId` and lowercasing. Any future normaliser that strips the *whole* query string would collapse 84 live postings into 1 — and `build_site.py::jobs_json_rows()` exists specifically because a previous cap silently deleted 924 postings. Worth an explicit regression test before anyone "improves" URL normalisation.

### 1.4 What is healthy

- 7,921 dated rows, live feeds still updating (Hourly Job Scan success 02:16Z, 2m30s; Deploy Pages success 02:37Z).
- GitHub Pages deploy green every hour.
- The `--max-per-table 500` lesson is encoded in the skill and in `build_site.py` comments.
- `job_source_truth.py` is genuinely good code — cross-ref search links (Google Jobs/LinkedIn/Indeed/Adzuna) are built to route a human to the employer's real posting. It just isn't wired into the write path.

---

## 2. COMS

**Bus alive.** `COMS` at `~/.local/bin/COMS`; broker `192.168.2.52:1883` (gx10-c9b9, anonymous, no TLS); `COMS roster` returns retained registry entries; `COMS listen --agent buffy` binds cleanly to `inbox/gx10-c9b9/findtorontoevents_antigravity-ca/buffy`.

**Verbs available:** `register`, `send <topic> <message>`, `listen --agent <seat>`, `roster`, `guard`. There is **still no `check`/`--inbox` read verb** — this was already logged twice by prior seats (`GHACTIONS_2026-11-16/2026-11-16_16-10_EST_ghactions-v4/BACKLOG.md`, `.../2026-11-16_15-54_EST_ghactions-v4/FINAL_SUMMARY.md`) and remains true. `listen` is a blocking subscriber, so "did anything arrive while I was away?" is unanswerable without leaving a listener attached.

**Seats relevant to this investigation:**

| Seat | Worktree | State |
|---|---|---|
| `kilo` | `bestiejobharvest-v2` | methodology designed; **`todo: handoff to v3; await owner pick of which angles to build first`** |
| `kilo` | `bestiejobharvest-v3` | 4-angle batch methodology done; measured 7,903 dated rows, 0 dup URLs, 17 public-sector, 175 Workday — but that measurement says **0 duplicate URLs**, while README today has 27 exact dups in "Other". Their dedupe was URL-keyed; the dups are identical URLs, so the measurement and the board disagree and one of them is wrong. |
| `kilo-general` | `auditpage-v3` | idle; own P0 backlog **"(1) one canonical ledger per class, (2) IC-vs-calibration reconcile. Both need owner/design call first"** |
| `grok-4-7` | `auditpage-v4` | idle; dashboard deploy verified, main CI green |

**Ownership gap:** no seat claims the BESTIEJOB `truth-check` red streak or the `gap-channels` push failure. The bestiejob seats are parked awaiting an owner decision on *which sourcing angle to build*, not on fixing the two red gates. Those two are unowned and immediately actionable — that is where I'd contribute.

---

## 3. `findtorontoevents.ca/audit` — asset classes

Live `dashboard_data.json`: HTTP 200, 25.5 MB, `generated_at 2026-11-18T01:15:43Z` (~25 min old at read). Local `audit_dashboard/data/dashboard_data.json` is **stale (2026-10-23, 25.2 MB)** — the CI job generates then deploys, so the local copy is expected to lag; do not read it as the site's state. The page does surface asset-class data (74 `asset_class` references, 19 "Asset Class").

### 3.1 Headline ledger — `performance.by_asset_class`

| Class | Active | Closed | WR % | PF | Expectancy | PnL |
|---|---|---|---|---|---|---|
| CRYPTO | 84 | 5,031 | 40.3 | 0.91 | -0.13 | -652.15 |
| FOREX | 25 | 102 | 21.6 | 0.42 | -0.29 | -29.23 |
| EQUITY | 64 | 12 | 66.7 | **10.16** | +0.97 | +11.62 |
| ETF | 12 | 12 | 25.0 | 0.53 | -0.53 | -6.36 |
| COMMODITY | 4 | 11 | 9.1 | 0.06 | -2.55 | -28.06 |
| BOND | 8 | 3 | 33.3 | 0.06 | -0.74 | -2.21 |
| FUTURES | 2 | 0 | — | None | 0 | 0 |
| SPORTS | 1 | 0 | — | None | 0 | 0 |

### 3.2 Gate ledger — `readiness.by_class` (same payload, same timestamp)

| Class | n | PF | WR % | gate_state | sizing | sample_tier |
|---|---|---|---|---|---|---|
| CRYPTO | **22,379** | **0.26** | 41.6 | MONITORING | ❌ | SUB_T2 |
| EQUITY | **476** | **0.62** | **38.7** | MONITORING | ❌ | SUB_T2 |
| FOREX | 433 | 0.31 | 35.3 | **BLOCKED** | ❌ | SUB_T2 |
| ETF | 25 | **1.65** | 52.0 | MONITORING | ❌ | INSUFFICIENT_SAMPLE |
| COMMODITY | 23 | 0.53 | 21.7 | **BLOCKED** | ❌ | INSUFFICIENT_SAMPLE |
| BOND | 1 | 0.0 | 0.0 | **BLOCKED** | ❌ | INSUFFICIENT_SAMPLE |
| CHEAP_STOCKS | 1 | None | 100.0 | MONITORING | ❌ | INSUFFICIENT_SAMPLE |

### 3.3 The finding: two ledgers, one page

Same class, same JSON, same timestamp — irreconcilable numbers:

- **CRYPTO** closed 5,031 vs n 22,379 (4.4×).
- **EQUITY** closed 12 → WR 66.7 / PF **10.16** vs n 476 → WR 38.7 / PF **0.62**. Not a scale difference; the *sign of the conclusion* flips.
- **BOND** 3 closed vs n 1.
- **ETF** is the only class above the PF ≥ 1.25 bar in either ledger — and in the headline ledger ETF is 0.53.

This is exactly the P0 that `auditpage-v3/kilo` has parked for an owner design call ("one canonical ledger per class"). The data now quantifies it.

### 3.4 Why the headline numbers are fragile even taken alone

`performance.asset_class_concentration` supplies the honest labels:

- CRYPTO: `top_strategy luxalgo_confluence = 80.22%` of class share; top symbol NEARUSDT 8.99% of PnL. Tier OK only because the *symbol* is diversified, while the *strategy* is 80% of the class.
- EQUITY: `top_symbol AAPL = 54.01%`, `top_strategy vt_equity_two_day_rsi_reversal = 53.45%`. So "PF 10.16" is one strategy on one symbol across 12 trades.
- FOREX: top symbol EURUSDT 68.04%, top strategy 43.49%.

### 3.5 Other live defects

- **FUTURES fails the resolution gate**: 0 resolved / 2 open = 0.0% vs `gate_pct: 80`. It is the **only** class failing; every other class is ≥ 87.2%. MUTUAL_FUND is 0/0.
- **`performance.smart_gate_failure_histogram` is `{}`** — empty object, so whatever diagnostic renders from it draws nothing.
- **`picks_now.json` is 6.7 h stale** (`generated_at 2026-11-17T18:32:55Z`) against a 25-min-fresh dashboard: `n_scored 325`, `picks 29`, regime `RISK_OFF`.
- Summary honesty metrics look healthy: 8,117 headline closed unique, 97 mirror duplicates removed, 7,499 integrity-excluded, 133 zero-PnL, headline PnL explicitly labelled "rolling-100 compounded equal-weight (bounded) = -40.81" with `legacy_headline` called out.

---

## 4. Copy trader / Kalshi / Polymarket

### 4.1 Orchestrator (23:07:57Z, 115.4 s, every agent `error: null`)

| Agent | Result |
|---|---|
| whale_tracker | 6 traders → 3 signals |
| momentum_detector | 29 markets → 1 signal |
| **kalshi_agent** | **36 events → 4 signals** |
| consensus | 10 aggregated → 6 consensus, **1 high-conviction** |
| merged_to_pipeline | 5 |

### 4.2 Kalshi — healthy agent, dead snapshot store (P0)

- `alpha_engine/kalshi_signals.py` is fine: series_ticker-based fetch (the 0-event keyword bug is fixed), multi-timeframe, MTF consensus, trade-level derivation.
- **`data/kalshi_snapshots/` contains exactly one file: `20260426T025427Z.json`, mtime May 25.** Nothing written in ~7 months.
- `tools/kalshi_sports_fetch.py` writes `data/kalshi_snapshots/<UTC>.json`; `tools/verify_kalshi_picks.py` **reads that directory** (with a live-fetch fallback). So the verifier resolves picks against an April snapshot first.
- `prediction_market_agents/data/` otherwise updates on time (23:07Z): `whale_tracker.json` 24 kB, `pm_odds_history.jsonl` 6.8 MB, `pm_leadlag_report.json` 373 kB.

### 4.3 Polymarket — two live picks, three dead artifacts

- `copy_trader_intel/data/polymarket_picks.json`: **2 picks**, both `BTCUSDT` SHORT, both `copy_pm_cleancoinflip`, entry 64916.11, conf 0.95, trader CleanCoinFlip (rank 15, crypto WR 1.0, Bayes WR 0.9608). Fresh (23:47Z). Note: two SHORTs on the same symbol from the same trader — effectively one position counted twice.
- `polymarket_strategy_audit.json` (8.6 kB) and `whale_alerts.json` (166 B): **both May 25, 6 months stale.** Their writers exist (`polymarket_strategy_audit.py`, `polymarket_whale_tracker.py`) but neither is on a live schedule.
- `pm_macro_overlay_signals.json`: `pick_count 0, picks []` — the IDEA-H Fed-rate overlay produced nothing (requires Kalshi **and** Polymarket > 70% agreement on the same direction).

### 4.4 Copy trader — the non-crypto lane feeds the blocked classes (P1)

- `clone_active_picks.json`: **100 picks, 100% crypto.** The "multi-asset" clone lane is single-asset in practice.
- `non_crypto_consensus_picks.json`: **12 picks** — FOREX 6 (EURUSD 0.85, GBPUSD 0.75, AUDUSD 0.85 long), COMMODITY 2 (CL=F 0.75 long), BOND 2 (TLT 0.67, IEF 0.67 long), + 2 more.
- `pick_quality_report.json` (23:48Z): 54 non-crypto, 53 pass (**98.1%**), avg conf 0.706, avg R:R 2.21, **66.7% long**, 1 flagged — `cta_commodity_momentum_term::CL=F` for SL distance **10.2% > commodity max 10.0%**.
- Coverage split: forex 31, commodity 14, stocks 3, index 2, equity 2, bond 2.

**The structural tension:** those 12 picks land in FOREX (PF 0.31, BLOCKED), COMMODITY (PF 0.53, BLOCKED) and BOND (PF 0.0, BLOCKED). A 98.1% quality pass rate on picks routed into the three worst classes is quality-without-edge. Same for the 66.7%-long skew against a `RISK_OFF` regime.

---

## 5. Ranked next steps I can contribute

Ordered by (impact ÷ risk). All are single-repo, no owner decision required.

### P0

**S1 — Turn `truth-check` green and keep it green** (`eltonaguiar/bestiejob`)
1. Add `from job_source_truth import domain_is_gated` to `tools/jobs_merge_inbox.py` and drop gated rows in the same place `EXCL`/`is_listing_url` are applied, with a printed counter (so the drop is visible in CI, not silent).
2. Re-render/merge to purge the 13 existing README rows + 11 `jobs.json` rows — but **keep the role**, not the link: attach the `xref` cross-ref links so a human can still reach the employer's posting. The gate funds a cross-ref generator; use it.
3. Add `config/gated_domains.txt` with the 4 core hosts so the blocklist has the extension path it already documents.
4. Tighten the exit rule to distinguish "gated in README" (`--fail-on-readme`, already implemented but unused) from "gated in jobs.json" — right now a JSON-only occurrence fails the build too.

**S2 — Reconcile the two asset-class ledgers on `/audit`** (`findtorontoevents_antigravity.ca`)
Not a code fix until the owner picks canonical — but I can do the analysis that makes the decision cheap: name both sources (which query/table backs `performance.by_asset_class` vs `readiness.by_class`), show the row-count delta per class, and produce the one-page diff. That is the unblock for the parked `auditpage-v3` P0.

**S3 — Restore Kalshi snapshot persistence**
Wire `data/kalshi_snapshots/<UTC>.json` writes into the existing hourly PM run (`prediction_market_agents/orchestrator.py` already calls the Kalshi agent), so `verify_kalshi_picks.py` stops resolving against April data. Small, additive, testable.

### P1

**S4 — Fix `gap-channels` push failure.** Read the concurrency/rebase path in the push step; the pattern is the known `bestiejob-main-write` collision. Either retry-with-rebase or move the push to the hourly writer.
**S5 — Board-wide dedupe pass.** Run `dedupe()` across existing README sections, not just inbox rows; 27 exact dups in "Other" prove the current scope is too narrow.
**S6 — ETF is the only class above the PF bar.** n=25 vs the n≥30 T2 requirement; ~5 more resolutions clears it. Worth watching as the one real edge candidate — but check it isn't a single-symbol artifact the way EQUITY/AAPL is.
**S7 — `pm_macro_overlay` produces 0 picks.** Confirm whether the 70%/70% agreement gate is simply never satisfied in the current odds history, or whether the Kalshi side of the join is broken.

### P2

**S8 — Purge/refresh the three May-25 PM artifacts** (`polymarket_strategy_audit.json`, `whale_alerts.json`, `kalshi_snapshots/*`) or mark them retired so nothing reads them as current.
**S9 — `smart_gate_failure_histogram` is `{}`** — populate or remove from the payload so the UI stops drawing an empty diagnostic.
**S10 — `picks_now.json` 6.7 h vs dashboard 25 min** — check whether `picks_now` is on a different schedule or a different generator.
**S11 — Add the missing `COMS check`/`--inbox` read verb** to `AGENT_REGISTER_PROMPT.md` + the CLI. Third time this has been logged; it's the one COMS gap that costs every new seat a blocking listener.

---

## 6. Limitations of this investigation

- `gh run view --log` for the `gap-channels` failure (44211439366) returns empty — logs expired. D5's root cause is inferred from the concurrency design plus the step-level `failure` on "Commit and push" only, not from the error text.
- The two-ledger analysis names the *symptom* with exact numbers; I did not trace which SQL/table backs each, so S2's source attribution is still open.
- `bestiejobharvest-v3/kilo` reported "0 duplicate URLs" against a board where I count 27 exact duplicate rows. One of us is measuring a different artifact (their `/tmp` feed vs `README.md`); unresolved, and it matters before S5.
- No fix was applied. Everything above is read-only evidence.

---
**End of investigation.**
