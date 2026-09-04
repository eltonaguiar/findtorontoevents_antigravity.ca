# GHA Hourly Health Monitor — 2026-09-04

## 13:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** CI Tests workflow (`.github/workflows/ci-tests.yml`) is path-gated (`alpha_engine/**`, `paper_trading/**`, `tests/**`, `requirements.txt`, `.github/workflows/ci-tests.yml`). All recent main commits are `[skip ci]` bot pushes — no CI-triggering code-path commits landed on main since the last confirmed CI run (pre-Sep-04). **Last confirmed run: unknown (no triggering commit in scope of this scan).** Treating CI Tests as NOT TRIGGERED — not RED, but unverified.

**Chronic workflows (cancellation methodology):** none — no workflow shows `cancelled` as latest conclusion with ≥4 cancels / 0 successes in 15 runs.

**Persistent-failure workflows (not cancellations — flagged separately):**

| Workflow | File | Last 15 completed | Pattern | Failure step |
|---|---|---|---|---|
| `Feed Health Check` | `feed-health.yml` | 15/15 FAILURE (runs 2072–2086, Sep 3–4) | Every run fails at step 5 "Run payload health check" (FTP-sourced dashboard payload). Latest failed run: #33868193155 (11:29Z) | `Run payload health check` — dashboard payload fetched via FTP likely stale/malformed |
| `robust-edge-miner` | `robust-edge-miner.yml` | 15/15 FAILURE (runs 137–151, Aug 28–Sep 4) | Each run retries 6–9 times before final failure; no success since ≥Aug 28 (oldest in 15-run window) | `mine` job fails — exact error unknown (run currently in_progress for retry attempt 2 of run #151) |

Both workflows are scheduled (not PR-triggered) and do not gate any PR merges. However the `Feed Health Check` failure suggests the FTP-hosted dashboard payload (`audit_dashboard/data/dashboard_data.json` or similar) may be stale or unreachable — this could indicate the `Unified Audit Dashboard` hourly workflow is also failing or producing bad output.

**Intermittent (not chronic):**
- `Missed Opportunity Analyzer Hourly Self-Improvement` (`missed-opportunity-scan.yml`): 7 success / 8 failure in last 15 runs (Sep 3–4); some runs pass on first attempt (1 minute), others time out to retry×3 before failing. Pattern suggests resource contention (GitHub-hosted runner queue saturation during peak hours).

**Open PRs RED:** No CI status data retrieved (statusCheckRollup not available in this scan; open PRs are #667, #666, #665, #657, #600, #595, #581, #564, #562). Most recent open PR is #667 (`feat(b5): forward-track cell selector`). CI Tests likely not triggered on any PR branch lacking path-matching files.

**Action required:**
- **Investigate `Feed Health Check`** — 15+ consecutive failures at "Run payload health check" step indicates the FTP-sourced audit dashboard payload is broken or unreachable. Check that `Unified Audit Dashboard` (`audit-dashboard.yml`) ran successfully recently and FTP upload landed. Run `python3 tools/deploy_audit_files.py --only audit_dashboard/data` to refresh if needed.
- **Investigate `robust-edge-miner`** — 15+ consecutive failures across 7+ days (each exhausting 6–9 retry attempts). The workflow has never succeeded in the 15-run window. This warrants a manual log inspection at https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/33824527304 (last completed failure, run 150, 8 attempts).
- **Monitor CI Tests** — next PR merge touching `alpha_engine/`, `tests/`, or `requirements.txt` will trigger CI; ensure it passes.
