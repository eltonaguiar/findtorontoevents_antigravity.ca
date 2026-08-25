# GHA Hourly Health Monitor — 2026-08-25

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress

**Chronic workflows:** none (cancellation pattern not detected in recent run sample; all non-CI workflows showing success)

**Open PRs RED:** Unable to retrieve individual PR check rollups in this run; given main CI Tests is itself broken (30+ consecutive failures), any PR depending on CI Tests is also blocked.

**Action required:** CRITICAL — operator must investigate and fix `CI Tests` on main. This is a persistent multi-day regression (not a flake).

---

### Detail

**Failure scope:** CI Tests (`ci-tests.yml`, workflow ID 282011873) has been failing on **every** run on `main` for at least **30 consecutive runs** across both Python 3.11 and 3.12 matrix jobs. The failure streak spans from run #2170 (2026-08-23T22:14 UTC) through run #2199 (2026-08-25T12:51 UTC) — approximately 38+ hours of continuous failure, each attempt retried 3–4 times.

**Failing step (latest run #2199, run ID 32845381755):**
- Job `test (3.12)` — step 8 `Run all tests (gating — known-drift quarantined)` → **failure**
- Job `test (3.11)` — step 8 `Run all tests (gating — known-drift quarantined)` → **failure**
- All other steps (checkout, pip install, JS guard, quarantine list, upload, coverage) succeed normally.

**Classification:** AUTHOR_FIX — not a flake. The failure is deterministic (3–4 retries all fail), affects both Python versions, and has persisted for 30+ runs over 38+ hours. This is a real test logic/assertion regression.

**Failing run URL:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/32845381755

**Earliest failure in current streak:** run #2170, 2026-08-23T22:14 UTC  
https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/32669989865

**Open PRs (9 open, CI status not individually fetched this run):**
- #667 feat/b5-forward-track-tool
- #666 fix/resolver B1 backfill price guard
- #665 audit/stalled-producer-detector
- #657 feat/contract-test cold-merge
- #600 feat/edge money-ready hunt
- #595 feat/validate non-crypto intrabar
- #581 feat/minimax next steps
- #564 docs/audit edge hunt action plan
- #562 feat/audit edge hunt session docs

All PRs running CI Tests against this broken main baseline will show red. The fix must land on main before PR CI is meaningful.

**In-progress workflows on main (13:05 UTC):** 10 operational workflows running normally (Rapid Fire NOW Scanner, Dashboard Pick Trader, Strategy Funnel Hourly Refresh, etc.) — these are data/trading workflows unrelated to CI Tests and are healthy.
