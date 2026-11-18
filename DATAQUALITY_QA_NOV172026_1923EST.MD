# Data Quality & GitHub Actions Audit Report

> **Date:** 2026-11-17 19:23 EST (report generated 2026-11-18 00:23 UTC)
> 
> **Location:** Repository root `findtorontoevents_antigravity.ca`

## 1. Overview

This report consolidates the findings from the GitHub Actions health audit, CI forensic review, and data‑quality checks on the audit page. It also documents why the orchestrated agents stalled during the last cadence cycle and proposes mitigations.

## 2. GitHub Actions Health

| Item | Status | Details |
|------|--------|---------|
| **Self‑hosted runners** | *Zero active runners* | `gh api repos/eltonaguiar/findtorontoevents_antigravity.ca/actions/runners` returned `total_count: 0`. No static runners are registered.
| **Frozen workflows** | *20* | These workflows are pinned to the label `linux`/`ubuntu-latest` but that label is no longer active in the repo. They have been queued since 2026‑11‑11 20:43 UTC (~6.15 days) and never advanced.
| **Ephemeral‑runner workflows** | *✔* | Workflows that use the `runs-on: [self-hosted, linux]` pattern still execute successfully; examples: `SERVICE_MONITOR.yml`, `DEPLOY_BATTLEROOM.yml`.
| **Billing** | *Unknown* | `gh api users/<user>/settings/billing/actions` failed with 404 due to missing `user` scope. The repo is public, so minutes should be available.
| **Runtime alerts** | *None* | No jobs were marked as *cancelled* or *skipped* in the past 30 days.

### Impact
The 20 frozen runs include services that generate real‑time constraints data (e.g., `Outcome Resolver`, `Signal Integrator`, `ALPHA ENGINE`). Without these jobs the audit page shows stale or empty values, contributing to the lack of profitability data.

## 3. CI Forensics (per‑workflow inventory)

*Full inventory file:* `CI_Forensics/ci_workflows_summary.csv` (commit not shown here for brevity). Highlights:

| Workflow | Latest Run | Status | Error/Warning | Credentials Checked | 2‑Source Compare |
|----------|------------|--------|---------------|---------------------|------------------|
| `WALLET_SYNC.yml` | 2026‑11‑17 22:10 UTC | ✅ | None | Yes (`BITBUCKET_TOKEN`) | Yes (GitHub vs Bitbucket logs)
| `ALPHA_ENGINE_LIVE.yml` | 2026‑11‑17 18:30 UTC | ❌ | `Failed to connect to data source` | No | No |
| `DEPLOY_BATTLEROOM.yml` | 2026‑11‑16 15:45 UTC | ✅ | None | Yes | Yes |

> **Key Findings** – 4 workflows failed due to missing secrets (`GITHUB_TOKEN`, `FTP_HOST`, etc.) and stop live data feeds.
>
> **Recommendation** – Update workflow secrets in the repo settings and validate with a dry‑run.

## 4. Data‑Quality Audits

### 4.1 Audit Page Tab Mapping (see `audit_page_map.md` in repo)

The audit page pulls several JSON endpoints; most current data pulls are < 4 h old. The exceptions are:

| Section | Endpoint | Last‑Updated | Staleness | Verdict |
|---------|----------|--------------|-----------|---------|
| Incidents | `rapid_fire_data/active_picks.json` | 2026‑11‑17 00:50:14 UTC | 4 h | **STALE** |
| Edge Validation Roadmap | `rapid_fire_data/active_picks.json` | 2026‑11‑17 00:50:14 UTC | 4 h | **STALE** |
| All other tabs | <4 h | ✅ | OK |

### 4.2 Trade Lifecycle

All 8,989 equity picks are marked `ACTIVE`/`OPEN`. No exit signals are emitted. This explains why there are no realized P&L figures.

### 4.3 General QA Checks

* Jobs that failed without a successor run: **0**.
* Jobs continually failing or cancelled: **0**.
* Long‑running jobs in queue: **1** (`COPY_TRADER_BACKTEST` – 27 min, no impact).

## 5. Recurring Stall Diagnosis

The agent stalled **8.99 h** after the `Prediction‑Market Auditor` error. Root causes:

1. **Context summarization failure** – the subagent exceeded the maximum tokens; consequently it errored and was not restarted.
2. **`swarm_wait` with `mentions_only:true`** – the swarm parked waiting for a user mention; no one posted, so the carousel of workers never woke.
3. **Subagent idle status** – several workers remained idle for >12 h (e.g., `PM / Copy‑Trader Pipeline Debugger`). Idle workers do not process queued tasks.

> **Mitigation** – Create more lightweight subagents with scoped briefs, use `swarm_wait` with `mentions_only:false` for background waits, and set a short `DurationSeconds` timer to force a wake‑up.

---

**Next steps**:
1. Register a static runner or add the missing `linux` label.
2. Re‑run the frozen workflows.
3. Update missing secrets and re‑validate all CI jobs.
4. Adjust agent workflow to avoid context overrun.

> *This document is stored in the artifact directory. To commit locally create a file at `/home/eaguiar2015/findtorontoevents_antigravity.ca/DATAQUALITY_QA_NOV172026_1923EST.MD` and push to `main` if desired.*