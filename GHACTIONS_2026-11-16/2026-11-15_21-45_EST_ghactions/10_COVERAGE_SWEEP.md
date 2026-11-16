# 10 — Coverage Sweep (4-axis swarm: main×jobs, main×states, non-main×7d, all×run-state)

**STAMP:** 2026-11-15_21-45_EST_ghactions · sweeps 05:24–05:37 UTC. Method: logged-in Chrome (CDP 9222)
primary + REST supplement. All sweeps read-only; fixes applied by coordinator after each report.
Failures with a later success treated as "assumed fixed/intermittent" per owner directive (one line).

## Coverage matrix (no blind spots)

| Axis | Window | Agent | Coverage |
|---|---|---|---|
| MAIN × critical-active × per-job | 24h | A1 | 61 workflows (53 core + 8 extensions), ~3,050 runs, 60 run-detail dives |
| MAIN × runtime-states × stalls | 48h | A2 | 11 in-progress + queues + 31 job-level stall probes + runner census |
| NON-MAIN × branch activity | 7d | A3 | 43-branch complete queries, 548 branch runs, 15 branch-registered files, 10 run-detail dives |
| ALL × run-state × warnings | 24h | A4 | full state census (~5,700 runs), 25 green-run annotation samples, 20 cancel-bucket classifications |

## Headline: 0 BROKEN. 61/61 critical workflows green-latest. 0 timed_out / neutral / action_required.

**DEGRADED ×5 (the real remaining problems):**
| Workflow | Evidence | Status |
|---|---|---|
| pead-shadow-collector | **49/50 SCHEDULED runs fail** (22–25m, bare exit 1 in logs) — masked by manual greens | **top open item** — log root-cause queued to 06:22 wakeup |
| daily-prices-yf-refresh | **48/50 SCHEDULED runs fail** (42–52s, bare exit 1) — same masked-by-manual pattern | same — likely yfinance fetch class |
| dynamic-alpha-engine | 24 f/c/24h (5m→15m→**30m commit-cap fix landed this round**) | fixed-pending-scheduled-run |
| alpha-engine-live | **"Full MySQL sync failed — live picks data integrity at risk"** errors on GREEN runs + silent data-gap warnings | open — owner-visible data integrity risk |
| audit-dashboard | Hyro `enhanced_scoring=failure` sub-step on green runs (degrades /audit inputs) + stale-deploy banner check warns | open (Hyro side) |

**STALLED-BEHAVIOR ×1:** alpha-engine-fast — 30-min cron vs 25–47m serialized runs = the ρ>1
replacement class (permanent queue). Job cap raised 40→60m this round (stops chronic kills); the
queue itself needs interval widening (owner call — it's the FAST scanner's cadence).

## Fixes landed from this sweep round (all validated, per-file reverts)

1. 🔒 **`schema-drift-watchdog.yml` secrets vulnerability** (A3): unfiltered `push:` + `secrets.DB_STOCKS_PASSWORD`
   = any branch push ran pushed-commit code with the prod DB password (executed 2× from a feature
   branch). Now `branches: [main]`.
2. **3 stall classes** (A2): dynamic-alpha `Commit results` 15→30m (killed at new cap 04:33 — the
   #813 5→15 bump proved insufficient), alpha-engine-live commit capped 30m (32.6m stall), alpha-fast
   job 40→60m (runtime drift).
3. **First-party pin stragglers → v6** (A4/A1 deprecation delta): 2 files on `checkout@v4` /
   `setup-python@v5` (Node20-onto-24 warnings). `gitleaks-action@v2` Node24 warning = upstream's.
4. Earlier round already-verified: sign-coherence commit step now 4s (was a 9-day 14.6m nightly
   stall), regime-terminal 33s/33s/4s.

## Key state findings (A4, new taxonomy in production)

- Census: 5,386 success / 80 failure (74 assumed-fixed; 6 = retired disable-commit artifacts) /
  244 cancelled / 18 skipped / 0 timed_out.
- **Cancels bucket perfectly**: 10 timeout-shaped / 4 eviction / 5 stack-kill / 0 pr-close / **1 external**
  (= benign human cancel-and-retry). The R7 era of "external mass-cancel" is fully dissolved.
- All 18 skips = healthy `conclusion == 'success'` deploy gates correctly not deploying failed upstreams.
- 3 new loud masks: 0 sightings yet (workflows haven't run since landing) — first sightings at their
  next crons (alpha-daily-picks Mon 22:14, academic-strategies 13:00, ml-gatekeeper-train 19:16).
- Green-with-errors: 3 workflows / 5 errors; green-with-warnings: 8 / 22 (incl. claude-gainer
  no-models green-no-op ×2, db-freshness exit-2 tolerated, daily-stock "HTTP 404" = dead-endpoint class).

## Non-main findings (A3)

- 548 branch runs/7d: 395 S / 27 F / 126 C (23% = branch-copy noise: 96 pre-fix dup-guard cancels
  = rebase-lag tax, self-healing) / **0 skipped**. Branch-registered: 3 BROKEN (mermaid — fails
  closed at `git exit 128` publishing to live gh-pages from `wiring`; the 2 retired-by-disable),
  11 INERT, merged-to-main 5.
- Latent dangers (die with branch cleanup): `winner-hunt-replay.yml` (3 branches: `contents: write`
  + `git push origin main` via `workflow_dispatch --ref`), old-branch emitters holding prod creds.
- gitleaks hit (2 matches in a data file) = **likely false positive** (date-shaped score keys;
  rule `skip-strategy-scores`) — owner confirms.
- Premise corrections: `feat/finpredict-final-v001` deleted; `alpha-engine-bond` inert everywhere;
  pr/145 has zero workflows.

## Open items (updated)

1. **pead + daily-prices-yf scheduled-path root causes** (49/50 + 48/50 fail) — log-level dig queued.
2. alpha-engine-live MySQL sync integrity errors (owner-visible).
3. audit-dashboard Hyro sub-step failure.
4. alpha-engine-fast interval-vs-runtime (owner call).
5. 3 "verified-by-manual-green, scheduled path untested": pead 22:11, daily-prices-yf 22:49,
   verified-pilot 06:53 — all due today; their outcomes ARE the next-run proofs.
6. Owner decisions unchanged (sports five, AsterDEX, AI Tournament, QA secrets, PM gates, deploy-env).

Watchers: 06:22 deploy-effect + log root-cause · 08:00 monitor · 08:37 guardian CANCEL BUCKETS.
Model babysitting: 4/4 agents completed clean — no swaps needed (ladder stood ready throughout).
