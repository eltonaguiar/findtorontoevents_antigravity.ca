# 05 — Follow-up Results (cron stagger, race fixes, integration record)

**STAMP:** 2026-11-16_02-50_EST_ghactions (work window 02:41–02:52 UTC). Companions:
`AGENT_PROMPT_job_analysis.md`, `04_EXECUTION_VERIFIED_FINDINGS.md`, `06_GHA_BEST_PRACTICES_APPROACH.md`
(same folder family) + `2026-11-16_02-50_EST_ghactions/{cron_stagger_manifest.tsv, cron_stagger_risks.md}`.

## 1. Cron stagger — LANDED (this commit)

| Metric | Value |
|---|---|
| Files modified / cron lines shifted | **285 / 310** (359 total entries; entry count preserved 359→359) |
| Frequency preservation | **PASS 310/310** — 7-day minute-resolution simulation, robfig/cron `N/step` semantics verified |
| YAML parse | PASS (all 355 active `.yml`) |
| Skipped — `github.event.schedule` string-compare guard | **17 files** (analyst-tracker, automated-reporting, backtest-and-deploy, claude-gainer-tracker, kimi-feb172026-live, live-monitor-refresh, master-automation-scheduler, meme-scanner, meme-scanner-v2, meta-strategy, regime-detector, sec-edgar-fetch, smart-money-tracker, torontoevent-backtest-and-deploy ×2, worldclass ×2) — changing their minute string would silently break `==` branches |
| Skipped — market-boundary risk | **2 files, COORDINATOR DECISION = leave unstaggered:** `alpha-trend-catcher.yml` (`5 0,4,…,20` — new minute would fire 20:01 vs candle-close cutoff) and `populate-alpha-macro-daily.yml` (`7 21` → 21:01 vs "data is settled"). Market-close semantics outrank stampede relief for these 2 of 310 lines |
| Policy no-ops | 4 files (already non-colliding) |
| Tie-breaks | plan's 2 (signal_tracking 34→35, sign-coherence-gate 32→33) + 2 new collisions in the newer tree (quan-engine-live 42→43, signal-engine 39→40) |
| Deviation (documented, rules beat syntax) | 9 `*/N` lines with `M ≥ N` use count-preserving wrapped form (`*/30` → `43,13`) because literal `M/30` would truncate; 6 lines with `M < N` keep `M/30` verbatim |

Effect: minute-0 pile-up 189/360 → ~14 (only the deliberate exceptions remain) — the queue
spike at the top of each hour is gone. Revert per file: `git checkout <pre-sha> -- <file>`
(pre-SHA anchor: `backup/gha-audit-2026-11-16` lineage + manifest's old/new columns).

## 2. FTP deploy race fixes — LANDED (commit 20f6e1cdad1)

- `deploy-competition-to-site.yml` → `concurrency: ftp-deploy-audit-dashboard-${{ github.ref }}` (HIGH race: 3 trigger sources interleaving lftp puts into /audit)
- `deploy-fte-index.yml` → `concurrency: fte-ftp-deploy` (MEDIUM: one-sided group; colliding `next/events.json` writes with deploy-fte-events-json)

## 3. Integration decisions this round

- Risk-flagged stagger targets stay as-is (§1) — owner may override later per `cron_stagger_risks.md`.
- The 17 string-compare files need a follow-up refactor (`github.event.schedule` → index/label
  matching) before they can join the stagger — listed as Phase-2 item in `06` §6.
- `site_impact_audit.md` off-by-one (claims 54 writers, table has 53) noted for its author.
- **Rebase supersession (02:52 UTC):** a sibling's interval fixes landed concurrently on
  `audit-dashboard.yml` (60-min cron → cadence matching its 63-125 min runtime; ~43% of fires
  were being lost to pending-replacement) and `dynamic-alpha-engine.yml` (30-min → 2h @ :23;
  ~62% lost). Those interval fixes outrank pure minute-stagger for these 2 files — resolved to
  upstream content; their stagger is deliberate (:23). Stagger effective total: 283 files / 308 lines.

## 4. Verification of subsequent runs (stagger)

| Check | When | Expectation |
|---|---|---|
| First staggered fires at new minutes | 02:50–03:59 UTC | sample manifest rows → runs appear at `new_cron` minute (e.g. `*/30`→`30,0`, `15 0,12`→`16 0,12`) |
| Hourly tick at 03:00 | 03:00 UTC | pile-up drops from ~190 simultaneous to ~14 |
| 4h monitor cron | 04:00 UTC | broad regression sweep (also carries dup-guard completion-ratio verdict) |
| Guarded files unchanged | now | 17+2 skipped files byte-identical to pre-stagger (asserted in manifest scope) |

## 5. Still open (unchanged from 04 §4, updated)

1. Sports five UI-disabled — **owner decision** (HIGH if `sports-betting-refresh` stays off)
2. Branch-cleanup manifest (subagent in flight) → deletions with SHA undo map after review
3. Guardian hardening to R1–R12 (`06` §2) — next implementation piece
4. Timeout sweep (125+ files lack explicit `timeout-minutes`) + concurrency for 192 uncovered (per `06` §4 class table)
5. safe_push.sh `-X theirs` last-writer-wins policy + 2 bare-`git push` workflows → route through safe_push
6. deploy-competition stale `index.html` put removal (behavior-changing; own verification cycle)
7. 51 phantom queued runs → GitHub Support / admin token (proven unremovable otherwise)
