# GHA Hourly Health Monitor — 2026-08-20

## 13:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** N/A — no workflow named "CI Tests" exists in this repository (404 on name lookup; repo has 362 total workflows, none match the exact name). No push-triggered test suite found by that name.

**Chronic workflows (fail-loud pattern — NOT cancellations):**
- `robust-edge-miner` — 15/15 last runs are `failure`, conclusion from step "Alert if a ROBUST candidate appeared (fail-LOUD = good news, review now)". The actual mining step (step 5) and artifact upload (step 6) both succeed. This is an **intentional fail-loud signal** designed to force attention when a robust edge candidate is detected. However, 15 consecutive triggers across 10+ days (runs 107–121, since 2026-08-06) may indicate the alert threshold is always satisfied — possible misconfiguration or the scanner is genuinely producing candidates every run. No cancellations observed; this fails, not cancels.

**Open PRs RED:** Unable to assess per-PR CI status — no "CI Tests" check name to filter on, and `statusCheckRollup` was not fetched. 9 open PRs exist (#562, #564, #581, #595, #600, #657, #665, #666, #667).

**Action required:**
- Review `robust-edge-miner` alert threshold — 15/15 consecutive fail-loud alerts across 10+ days may mean the threshold is too loose (always triggers) rather than detecting genuine edge candidates. Examine the uploaded scan artifacts to confirm. Run: `gh run list --workflow robust-edge-miner.yml --limit 1` then download the artifact to inspect.
- Clarify whether a "CI Tests" workflow was renamed or retired. No push-gated test workflow was found under that name; PRs may be merging without a required test gate.
