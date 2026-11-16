# Prompt — Full GitHub Actions Job Analysis & Fix Pass

Give this prompt to any agent working this repo's Actions. It encodes every hard-won
gotcha from the 2026-11-16 swarm audit (see `GHACTIONS_2026-11-16/` for the evidence trail).

---

You are auditing and fixing GitHub Actions for `eltonaguiar/findtorontoevents_antigravity.ca`
(~370 workflow files on main, ~4,000 runs/day, 88% cron). Work in this order.

## 0. Environment gotchas (read first — each cost this audit real time)

1. **The local clone is shallow + blob-filtered.** `git merge-base`, `git log --grep`,
   `git cherry`, and `git merge-base --is-ancestor` return EMPTY/FAIL below the graft line
   (~15 visible commits on `origin/main`). Absence of a commit in `git log` is NOT evidence
   it isn't on main. Run `git fetch --unshallow origin` in background first, or restrict all
   claims to tree-content comparisons (`git diff origin/main <branch> -- <path>`).
2. **`origin/main` advances every ~60 s (bot commits).** Re-fetch before acting on any SHA.
   Never `git add .github/workflows/` wholesale from a stale checkout — it resurrects deleted
   workflows and reverts live fixes (see `push_chain_impact.md`). Stage file-by-file.
3. **REST API is rate-limited to near-zero at peak.** Prefer the browser pipeline:
   persistent logged-in Chrome (`DISPLAY=:0 google-chrome --remote-debugging-port=9222
   --user-data-dir=$HOME/.cache/gha-scrape-profile …`) + Playwright `connect_over_cdp`;
   scrape `/actions?query=…` pages. `python3 /tmp/kilo/gha_browser/scrape.py` has ready
   commands (`runs "is:queued"`, `wf-history <file>`, `run-detail <id>`).
4. **GitHub run-search date semantics:** `created:>2026-11-15` means strictly AFTER the end
   of that day (Nov 16 only). Use `created:>=DATE` to include the day.
5. **`on: push` workflows execute the pushed REF's copy of the YAML**, not main's. Fixes to
   push-triggered workflows only reach branches as they rebase onto main.
6. **`schedule:` fires only from the default branch.** Schedule-only workflow copies on
   feature branches cost ZERO runtime. Don't "fix" them for run-cost reasons.

## 1. Analysis — classify every workflow, sequence context not failure lists

Pull per-workflow run history (≥15 runs deep; browser `wf-history`) and assign ONE bucket:

- **BROKEN** — latest completed run failed AND no success after it. Severity scales with
  cadence (hourly broken 3h = 3 missed cycles). "Never passed in its life" + dormant ⇒
  prune candidate, not an incident.
- **RECOVERED/FLAPPING** — any success after the last failure. NOT an issue; report count
  only. Flapper = ≥5 fails in last 15 runs: name the failing STEP (run-detail page), split
  infra-flake (playwright/pip installs) vs real bug.
- **QUEUE HOGS** — (a) phantom `queued` runs: age > 1 day with ZERO materialized jobs; they
  are UNCANCELLABLE (REST cancel `409`, REST delete `403`, UI cancel fails) — report batches
  by timestamp, escalation is GitHub Support/admin token. (b) runner hogs: `in_progress` > 2h
  (Discord Bot – Persistent is a designed 24/7 occupier — flag, don't "fix"). (c) cancel
  churn: ≥50% cancelled/15 = concurrency cancel-loop (e.g. dup-guard was 0/15 completed);
  distinguish from external mass-cancels (identical timestamps ACROSS workflows).
- **STALE/SKIPPED** — read `on:` first: `workflow_dispatch`-only quiet = BY DESIGN. Daily
  silent 30d+/weekly 60d+/monthly 90d+ = dead trigger. Jobs permanently `skipped` inside
  green runs (e.g. `wsl-direct` in dynamic-alpha-engine) = dead code. `if: false` jobs =
  workflow does nothing, ever.

Also sweep: `is:skipped`, `is:waiting`, `is:action_required`, `is:neutral`, `is:timed_out`;
`workflow_run` fan-in chains (one upstream completion spawns deploys — `deploy-competition-to-site`
← 8 upstreams ≈ 160 runs/day); cron-minute histogram (189/360 fire at `:00` — see
`cron_stagger_plan.md` for the deterministic crc32 stagger plan).

## 2. Downstream gate (MANDATORY before any workflow change)

For each output a workflow writes (files, DB rows, FTP paths, commits), `git grep` the
consumers: `audit_dashboard/`, `audit_trail/`, `tools/deploy_audit_files.py` (explicit
per-file deploy list — no globs), `TORONTOEVENTS_ANTIGRAVITY/`, `live-monitor/`. Record
per-file verdict "does /audit depend on it". Known traps:
- `audit_dashboard/data/db_freshness.json` has NO page consumer but is a latent trap: only
  the deleted legacy workflow ever committed it; the hourly guardian only writes artifacts.
- `/audit` DROPS sports by user directive (`_applyGlobalSportsFilter`); sports feeds
  `/live-monitor/sports-betting.html` instead.
- 5 sports workflows are `disabled_manually` (GitHub UI state — invisible to git, leaves no
  tree audit trail): sports-betting-refresh (auto-settle freeze = HIGH), sports-data-snapshots
  (silent devig degradation), sports-prediction-market-sync, sports-forensics-weekly,
  sports-smoke-and-e2e. Check UI state via browser before assuming crons run.

## 3. Fix rules

- Prefer **rename to `.yml.disabled`** over delete (reversible, matches repo pattern) unless
  the file is a proven true-duplicate (same script + same outputs — e.g. the 9-file batch in
  `02_FIX_BATCH_1_DEDUP.md`).
- `cancel-in-progress: true` + trigger interval < runtime = cancel-loop; serialize
  (`cancel-in-progress: false`, one group) rather than per-ref groups for repo-wide scans.
- Document EVERY change in `GHACTIONS_<date>/<date-time_EST>_<worktree>/NN_*.md`: what was
  broken, exact diff, downstream verdict, revert commands (`git checkout <pre-sha> -- <path>`),
  and the SHA undo map. Keep a `backup/` branch with pre-change SHAs (main SHAs churn via
  bot rebase races).

## 4. Verify subsequent runs (non-negotiable)

After each fix, watch the NEXT scheduled/triggered run (browser `wf-history`) and record
conclusion in the fix doc. Fixes to push-triggered workflows verify per-branch. Keep a 4h
monitoring cron; escalate only regressions.

## 5. Output format

1. BROKEN NOW (≤10 rows, action required) 2. FLAPPING (watch list + failing steps)
3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in) 4. STALE/SKIPPED/PRUNE
(trigger-aware verdicts) 5. "NOT an issue" suppressed count (so readers can tell green from
filtered noise) 6. Downstream verdicts 7. Fix + revert + verification table.
