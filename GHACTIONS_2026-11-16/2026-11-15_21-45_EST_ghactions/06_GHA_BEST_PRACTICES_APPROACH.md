# 06 — GitHub Actions Best-Practice Approach (researched + repo-calibrated)

**STAMP:** 2026-11-15_21-45_EST_ghactions. Sources: official GitHub workflow-syntax reference
(fetched 2026-11-16), plus measured evidence from this repo's 2026-11-16 audit (see
`GHA_TRIAGE_ANALYSIS.md`, `02_FIX_BATCH_1_DEDUP.md`, `04_EXECUTION_VERIFIED_FINDINGS.md`, the
`21-00-33_EST` 8-file audit set). Where generic advice conflicts with measured evidence here,
evidence wins — those corrections are marked ⚠.

---

## 1. Verified platform semantics (the rules the design rests on)

| Fact (official docs) | Design consequence |
|---|---|
| `schedule` runs **only the latest commit on the default branch**; min interval 5 min | Branch copies of schedule-only workflows cost nothing (verified empirically: 159 stale branches, 0 wasted runs). Don't "fix" them for cost. |
| `workflow_dispatch` only receives events when the file is on the **default branch** | Manual tools on branches are unreachable; dispatch-only = quiet by design (not stale). |
| `workflow_run` fires the **default branch's** copy of the consumer | Deploy-chain fixes land immediately on push to main (used for the 2026-11-16 FTP race fix). |
| `github.event.schedule` is the **cron string literal** (docs example matches `!= '30 5 * * 1,3'`) | ⚠ Any cron-minute stagger MUST grep for `github.event.schedule == '…'` string comparisons first — changing the minute string silently breaks those branches. |
| `concurrency`: ≤1 **running** per group; new pending **replaces** older pending (`queue: single` default); `queue: group` lets multiple pendings wait; `cancel-in-progress: true` kills the running one | The full toolkit: serialize (`false`), supersede-pending (default), keep-every-tick (`queue: group`), or newest-wins (`true`) — chosen per job class (§4). |
| Path/branch-filtered + skipped workflows leave required checks **"Pending"** (docs) | Never leave a required check on a filter-skippable workflow. |
| Path-filter diff limits: >1,000 commits in a push ⇒ workflow **always runs**; >3,000-file diffs can **miss** matches | Big bot pushes defeat `paths:` silently — don't rely on filters as the only guard. |
| Default `timeout-minutes` = 360; hard per-job cap 6h (observed live: dup-guard runs "cancelled after ~6h") | Every job gets an explicit timeout (§4 ladder). |
| Reusable workflows (`workflow_call`) with `secrets`/`inputs` maps | The consolidation vehicle for the scanner family (§5). |
| (Plan-dependent) concurrent-job caps apply per plan/runner pool | With ~4k runs/day of cron pile-ups, **concurrency slots — not dollars (public repo) — are the binding constraint**. Queue hygiene = latency for everything else. |

## 2. Detection rules → automation spec (harden `actions-failure-guardian.yml` into this)

Each rule is computable from browser scrape (`/actions?query=…` + per-workflow history) with
zero API, or from run-listings in a scheduled guardian. Emit a committed
`GHACTIONS_LIVE/health.json` + MD summary; alert via the existing guardian's issue pattern.

| Rule | Definition (sequence-context) | Threshold / notes |
|---|---|---|
| **R1 failed-no-success** | latest completed run failed AND no later success same workflow+branch | Immediate report row. "Never passed in life" + dormant ⇒ prune row instead |
| **R2 monitor-next-run** | R1 candidate WITH a live cadence (cron/push) | Auto-watch the next 2 occurrences; if green ⇒ reclassify FLAPPING; if missing ⇒ escalate (scheduler dead) |
| **R3 flapping** | ≥5 failures in last 15 runs but latest green | Report failing STEP name (run page annotations), split infra-flake vs bug |
| **R4 phantom queue** | status=queued, age > 24h, 0 materialized jobs | Uncancelable (409/403/UI-fail — all four paths proven dead) ⇒ batch list for GitHub Support. Watch batch count for growth |
| **R5 runner hog** | in_progress > 2× workflow p90, or > 2h | Known designed hog: Discord Bot–Persistent (24/7). Report, don't kill |
| **R6 cancel churn** | ≥50% cancelled in last 15 AND cancels follow own tick spacing | Concurrency cancel-loop (measured: dup-guard 0/15 completed; dynamic-runner 80%) |
| **R7 external mass-cancel** | cancels at IDENTICAL timestamps across unrelated workflows | Different class — don't "fix" configs; find the cancelling actor |
| **R8 perpetual skip** | job `if:` always false (e.g. `wsl-direct`), or run conclusion=skipped >80% for a live trigger | Dead code / broken filter |
| **R9 stale-by-cadence** | no run in >30d (daily), >60d (weekly), >90d (monthly); workflow_dispatch-only is EXEMPT | Trigger-aware (docs semantics above) |
| **R10 non-main duplicate** | branch-only workflow file with a `push:` trigger that matches its branch | The only real per-push waste class (measured: mermaid-test-deploy on `wiring`) |
| **R11 fan-in amplification** | `workflow_run` consumers per upstream (deploy chains) | Report runs/day per chain (measured: deploy-competition ← 8 upstreams ≈ 160/day) |
| **R12 no-consumer output** | workflow writes file/FTP artifact with zero repo consumers | Latent-trap class (measured ×3: `db_freshness.json`, `daily_top_picks_filter.json`, `alpha_engine/output/latest_picks.json`) |

## 3. ⚠ Corrections to generic advice for THIS repo

1. **`cancel-in-progress: true` everywhere is wrong here.** For long scanners (21 min–3 h)
   with trigger interval < runtime it is a 100% cancel-loop (dup-guard measured 0/15
   completions). Decision table in §4.
2. **`on: {}` disable is not the house style.** This repo renames to `.yml.disabled` —
   keeps git history auditable (the UI-disabled state is INVISIBLE to git — the 5 sports
   workflows were silently off with no tree trail; browser-verified 02:45 UTC).
3. **Deleting runs to purge the UI is blocked here** (REST delete 403) — skip that step;
   phantom runs go to GitHub Support.
4. **Stale-branch cleanup needs a lost-work gate:** 49 branches carry unmerged work
   (incl. provably lost June tools). Gate: protected set + `git cherry`-equivalent zero-unique
   test + SHA undo map + `backup/` anchor branch (main SHAs churn via bot rebase races).
5. **"Free minutes" is a red herring (public repo)** — the real caps are concurrency slots
   and the 6h job cap. Optimize queue shape (§4), not dollars.
6. **Never `git add .github/workflows/` from a stale checkout** — measured hazard: would
   resurrect 9 deleted workflows + revert live timeout fixes (`push_chain_impact.md`).

## 4. Queue-shape playbook (the fix patterns)

**Concurrency — choose by runtime/interval ratio ρ = runtime ÷ trigger interval:**

| Class | ρ | Setting | Example here |
|---|---|---|---|
| Superseding scanner (new data wins) | ≈1 | `cancel-in-progress: true`, group `${{ github.workflow }}-${{ github.ref }}` | gainer scanners, price ticks |
| Long scan, each run must finish | >0.5 | `cancel-in-progress: false` (serialize; default `queue: single` keeps ≤1 pending) | dup-guard (fixed 2026-11-16: 0/15 → completions) |
| Must-not-drop data tick | any | `concurrency` + `queue: group` (docs' newer property — ticks wait instead of being replaced) | price/DB refreshers, settle jobs |
| Deploy/writer to shared paths | any | serialize + ONE owner per remote file (the FTP race fix: `ftp-deploy-audit-dashboard-*`, `fte-ftp-deploy`) | deploy-competition, fte pair |
| Designed 24/7 singleton | ∞ | no group + `run-name` sentinel; report via R5 | Discord Bot–Persistent |

**Timeout ladder:** fast checks 10m · scanners 15–30m · heavy backtests 60m · dashboard
generator 115m (its own documented value). Nothing without `timeout-minutes`.

**Cron stampede:** 189/360 crons at `:00`. Deterministic stagger `crc32(filename) % 60` with
per-group tie-breaks is designed in `cron_stagger_plan.md` (execution in flight 2026-11-16) —
with the `github.event.schedule` string-comparison guard from §1.

**Path filters:** add to push/PR workflows, but (a) never leave required checks filter-skippable
(Pending-trap), (b) don't trust filters on >1k-commit bot pushes.

**Perpetual skips:** delete dead `if:` jobs; fix-or-remove always-skipped fallbacks; for
`workflow_run` deploy chains add `if: conclusion == 'success'` + path-change guards (debounce
the 8-upstream fan-in).

## 5. Structural consolidation (Phase 4 — after hygiene)

1. **Reusable workflow extraction** (highest duplication): FTP-deploy block (54 writers share
   ~3 patterns), auto-commit+`safe_push.sh` block (20+ emitters — and route the 2 bare-`git push`
   laggards through `safe_push.sh`, which itself needs `-X theirs`→neutral rebase policy review:
   it silently last-writer-wins same-file conflicts), scanner skeleton (checkout→pip→scan→commit).
2. **Scanner families** (5 live-trading bots, 6 ML-battleground, 3 meme, 3 gainer, 4 data-refresh)
   → merge per `02_FIX_BATCH_1_DEDUP.md` verdicts (merge-first survivors named).
3. **Guardian**: evolve `actions-failure-guardian.yml` (existing 30-min, retrying, self-serialized)
   to emit R1–R12 — it already owns the failure-watch pattern; add queue-depth + no-success
   semantics + the browser-driven cross-check when API-limited.
4. **Archive ladder** for everything disabled: observe ≥2 cadence cycles → rename `.retired` →
   delete at the next cleanup window (with the undo-map discipline).

## 6. Phased status (the generic plan mapped onto reality)

| Phase | Generic plan | Status here (2026-11-16) |
|---|---|---|
| 1 Inventory & classify | build report | **DONE** — 4-bucket audit, 367 workflows, family dedup, branch sweep, per-file /audit verdicts (53 rows) — all on main under `GHACTIONS_2026-11-16/` |
| 2 Hygiene | concurrency+timeouts, disable dead, path filters, stale-branch dry-run | **PARTIAL** — 9 dup/dead removed; dup-guard serialized; 2 FTP races guarded; sibling disables landed (mysql-q001, ml-gatekeeper, secret-scan). REMAINING: timeout sweep (125+ files lack explicit values), safe_push routing ×2, concurrency for remaining 192 uncovered files per §4 table, cron-stagger landing |
| 3 Queue/skip monitoring | guardian hardening | **SPEC'D** (§2 R1–R12) — ready to implement in `actions-failure-guardian.yml`; interim coverage via session crons (4h monitor + weekly deep review) |
| 4 Structural cleanup | consolidate + archive | **SPEC'D** (§5) — pending Phase 2 completion; branch cleanup gated on the 49-branch rescue manifest |
