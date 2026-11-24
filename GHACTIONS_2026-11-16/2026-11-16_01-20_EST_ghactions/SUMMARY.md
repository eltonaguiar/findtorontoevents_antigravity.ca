# SUMMARY — GitHub Actions remediation, 4-worktree fleet review

**STAMP: 2026-11-16_01-20_EST (06:20 UTC)** · session `GHACTIONS` (worktree `ghactions`) ·
covers 2026-11-15 20:13 UTC → 2026-11-16 06:20 UTC · all fixes reversible (per-file
`git checkout <pre-sha> -- <path>`, `backup/gha-audit-2026-11-16` anchor).

## 1. Fleet ledger — who shipped what (all on origin/main unless noted)

| Worktree | Branch | Shipped tonight |
|---|---|---|
| **ghactions (this session)** | `ghactions` | 4-bucket triage + fix batch 1 (9 dup/dead workflows) · dup-guard serialize · cron-stagger (283 files/308 lines) · FTP race guards ×2 · regime/sign-coherence/dynamic-alpha/alpha-live/alpha-fast stall fixes · schema-drift **secrets-vuln fix** · run-name ×19 + pip-cache ×25 + 3 loud masks · guardian R1–R12 implementation + R7 cancel-bucketing (32 tests) · theory-tracker sidecar + PM feed/resolver wiring · strict-JSON cherry-pick + /audit box repairs (banner truth, IC retire, swarm tile) · upload/first-party pins · docs trail 03–10 |
| ghactions-v2 | `docs/alpha-verify-2-2026-11-16` | PRs #811–#820 (ALPHA timeouts, #815 ROOCODE dedup, #816 playbook, job-state sweep), Phase 2A/2B/2C (path filters, 7 timeouts, 9 concurrency groups), push-hygiene audit #832, cross-check docs |
| ghactions-v3 | `fix/gha-cron-regime-hardening` | event-guards (`3eede133e01`), phase1 inventory artifacts (PR #822), guardian draft spec; **2 commits UNMERGED (see §4)** |
| ghactions-v4 | `fix/gha-disable-broken-workflows` | 3-workflow disables + docs batch `4ca0ca135b4`, QA-secrets escalation (PR #786), Phase-1 report set |

Convergent peer extensions of this session's work (verified in history): strict-JSON at the publish
boundary (`7c3cb289a14`), banner-lying stop (`4d40c73a939`), ALPHA infinite-push-hang → safe_push
(#829), feed-health PM-source warnings (`f107b7da3e5`), CDP queue-audit tooling (`04a30246aef`).

## 2. Where my files live

| Path (on origin/main) | What |
|---|---|
| `GHACTIONS_2026-11-16/2026-11-15_20-57_EST_ghactions/` | GHA_TRIAGE_ANALYSIS.md · 02_FIX_BATCH_1_DEDUP.md |
| `GHACTIONS_2026-11-16/2026-11-15_21-45_EST_ghactions/` | 03_BRANCH_CLEANUP_MANIFEST · 04_EXECUTION_VERIFIED_FINDINGS · 05_FOLLOWUP_RESULTS(+errata) · 06_GHA_BEST_PRACTICES_APPROACH · 07_AUDIT_DEEP_CHECK · 08_FOLLOWUP_RESULTS · 09_NEXT_PRACTICE_ENGAGEMENTS · 10_COVERAGE_SWEEP · AGENT_PROMPT_job_analysis |
| `GHACTIONS_2026-11-16/2026-11-16_04-50_EST_ghactions/safe_push_manifest.tsv` | 20-site before/after |
| `GHACTIONS_2026-11-16/2026-11-16_05-25_EST_ghactions/hygiene_manifest.tsv` | run-name/cache/mask before/after (32 rows) |
| `GHACTIONS_2026-11-16/2026-11-16_01-20_EST_ghactions/SUMMARY.md` | **this file** |
| `GHACTIONS_LIVE/gha_health.json` + `_summary.md` | guardian runtime reports (every 4h at :37) |
| `tools/gha_health_audit.py` + `tests/test_gha_health_audit.py` | R1–R12 guardian (32 tests) |
| `tools/build_theory_tracker_sidecar.py` + `tests/test_theory_tracker_sidecar.py` | theory-tracker pipeline (6 tests) |
| branch `backup/gha-audit-2026-11-16` | pre/post SHA undo anchor |
| tooling (ephemeral, `/tmp/kilo/gha_browser/`) | logged-in-Chrome scrape pipeline (`scrape.py`, CDP 9222) — candidate for `tools/` promotion |

## 3. PRIORITIZED CODE FIXES

**P0 — live data-path brokenness (trading data at risk):**
1. `pead-shadow-collector.yml` scheduled path fails **49/50** (22–25m, bare exit 1 in logs; masked by
   manual greens) → root-cause `python -m alpha_engine.strategies.pead_equity` collector in scheduled
   env (env-var/secrets presence differs between `schedule` and `dispatch`); add failure surfacing.
2. `daily-prices-yf-refresh.yml` scheduled path fails **48/50** (42–52s exit 1) → `tools/refresh_daily_prices_yf.py`
   yfinance fetch class; add retry + loud error output.
3. `alpha-engine-live.yml` "Full MySQL sync failed — **live picks data integrity at risk**" on GREEN
   runs → the sync step must fail (or alert) visibly; currently a tolerated sub-exit.

**P1 — degraded pipelines / policy calls:**
4. `audit-dashboard.yml` Hyro `enhanced_scoring=failure` sub-step on green runs (degrades /audit
   inputs) → `alpha_engine/hyrotrader_enhanced_scoring.py` failure handling.
5. `alpha-engine-fast.yml` ρ>1 (30m cron vs 25–47m serialized runs = permanent queue) → widen cron
   to 45–60m (**owner call** — FAST scanner cadence).
6. `claude-gainer-ml-live.yml` + `claude-gainer-tracker.yml` green-no-op ("No model .joblib files —
   skipping scanner") → emit status-file/gate so a silent no-op can't look healthy.
7. Land **ghactions-v3's 2 unmerged commits** (`60141976a83` regime-terminal push hardening,
   `e6f3932991d` ueps/audit-impact step hardening) — complements the timeout fixes.

**P2 — hygiene depth:**
8. `tools/gha_health_audit.py` v1.1: rule re-reads (R1/R3 timeout-awareness, R5 p90 baseline, R9
   baseline re-derivation) per `08` §4.
9. `audit-dashboard.yml:125-128` PM-agent swallow root-cause (`polymarket_momentum_agent.py` scan
   failures now visible as warnings; make it work).
10. `concurrency: queue: group` on the must-not-drop ticks (06 §4 table) · `permissions:` least-
    privilege sweep · SHA-pin 7 aging 3rd-party actions · `daily-stock-refresh` HTTP-404 report-cache
    writer (dead-endpoint class).

**P3 — owner decisions:** sports five re-enable · AsterDEX gate string (fix = daily public posts) ·
AI Tournament 5-month outage · QA Market Validation 5 secrets (PR #786) · PM promotion gates ·
deployment-environment gating for 54 FTP writers · timezone-aware market-close schedules ·
`.env.events` human review · gitleaks `skip-strategy-scores` finding (likely false positive).

## 4. Further actions required

1. **ghactions-v3: 2 unmerged hardening commits** (above) — its session or a PR lands them.
2. `ghactions` local branch carries 3 rescue-list commits (ETF/VIX/forex gate — also on protected
   branch `fix/etf-short-gate-vix-combos-2026-11-15`) — KEEP both copies; merge via the rescue pass.
3. Rescue-pass queue (from `03`): 49-branch rescue list awaiting the ancestry-aware rerun
   (bounded deepen) before any branch deletion; owner review required for deletions.
4. Scheduled-path proof runs tonight: pead 22:11 · daily-prices-yf 22:49 · verified-pilot 06:53 UTC.
5. Watch chain armed: 06:22 deploy-effect + log root-causes (P0 #1/#2) · 08:00 monitor · 08:37
   guardian's first live CANCEL BUCKETS report · 4h cadence thereafter.

## 5. Verification ledger (fix → proven by)

fix batch 1 (02:05 tick clean) · cron-stagger (03:28: 5 runs @ 03:00–05 vs 189 baseline) ·
regime fix (04:17 + 04:47 green) · sign-coherence (04:47: 4s vs 14.6m) · guardian end-to-end
(04:01 dispatch green + schedule live) · strict-JSON (8/8 tests + publish-boundary extension by
peer) · security fix (parsed `branches: [main]` confirmed) · hygiene batch (355 YAMLs validated,
run-name visible from next push run).
