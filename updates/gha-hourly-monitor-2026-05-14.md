# GHA Hourly Health Monitor — 2026-05-14

## 04:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** Direct workflow run history unavailable (`gh` CLI absent; GitHub MCP has no runs-list endpoint). Proxy evidence via PR check runs: PR #993 (last merged to main, 2026-05-14T04:14Z) had `test (3.12)=failure`, `gate=failure`, `test (3.11)=cancelled` on its branch head before merge. `scan` and `audit` passed. Main was merged into while CI Tests was failing — treat as RED.

**Chronic workflows:** Full per-workflow history scan (Step 2) cannot run without `gh` CLI or workflow-runs API. Observed pattern across 4 PRs (#993 merged, #1004 open, #1003 open, #995 open): `gate` + `test (3.11)` + `test (3.12)` failing in tandem — consistent with a systemic import or assertion breakage rather than infra flakes. No cancellation-only pattern flagged (failures are real test failures, not infra timeouts).

**Open PRs RED:**
- **#1004** `fix/cot-ledger-atomic-write-and-direction-key-2026-05-14` — `test (3.11)=failure`, `gate=failure`, `test (3.12)=cancelled` → **AUTHOR_FIX** (test logic / assertion failure; atomic-write + direction-key changes likely broke existing test expectations)
- **#1003** `feat/equity-rsi2-overbought-short-2026-05-14` — `test (3.11)=failure`, `gate=failure`, `test (3.12)=cancelled` → **AUTHOR_FIX** (new strategy registration may have broken strategy-list or gate tests)
- **#995** `fix/etf-sector-momentum-tlt-hyg-2026-05-14` — `test (3.11)=failure`, `gate=failure`, `test (3.12)=cancelled` → **AUTHOR_FIX** (ETF+BOND union change may affect symbol-count assertions)
- **#1007** `feat/deep-dive-verify-2026-05-14` — all 5 checks `in_progress` (opened 04:09Z, still running — no verdict yet)

**Open PRs GREEN / partial:**
- #1006: scan=success (CI Tests not yet triggered on this head)
- #1005: audit=success, scan=success (CI Tests not yet triggered on this head)
- #1002: audit=success, scan=success (CI Tests not yet triggered on this head)
- #994: scan=success (CI Tests not yet triggered on this head)
- #996: scan=success (CI Tests not yet triggered on this head)

**Action required:**
1. Authors of #1004, #1003, #995 must fix test failures before merge.
2. Main branch was merged while CI Tests was RED (PR #993 had `test (3.12)=failure` + `gate=failure` pre-merge). Post-merge main CI state should be verified once a run completes.
3. Do not merge additional PRs to main until CI Tests on main returns GREEN.

**Methodology note:** `gh` CLI absent; Step 1 (workflow run history) and Step 2 (per-workflow chronic-cancel scan) executed via GitHub MCP `get_check_runs` on PR heads as proxy. Findings are conservative — real run counts may differ.

---

## 05:00 UTC

**Verdict:** RED

**Main CI Tests (last 5 proxied from merged PR heads):** 5 PRs merged to main between 04:53Z–04:58Z. CI Tests results at merge time:
- PR #1002 (04:53Z): `test (3.11)=failure`, `test (3.12)=cancelled`, `gate` not triggered — **FAILING**
- PR #1004 (04:55Z): `test (3.11)=failure`, `gate=failure`, `test (3.12)=cancelled` — **FAILING**
- PR #1005 (04:54Z): `scan=success`, `audit=success`, `drift=success` — no CI Tests (docs-only PR, OK)
- PR #1003 (04:57Z): `test (3.11)=failure`, `gate=failure`, `test (3.12)=cancelled` — **FAILING**
- PR #1006 (04:58Z): `scan=success` — no CI Tests (docs-only PR, OK)

Summary: 3 of 3 code PRs merged with failing CI Tests. Main remains RED from previous hour.

**Chronic workflows:** No new chronic-cancellation pattern detected. The persistent `test (3.12)=cancelled` is a matrix cascade from `test (3.11)` failing first — not an independent cancellation pattern. Root cause: `CRYPTO_HIGH_CONF_GUARD_ENABLED` gate (added 2026-05-14) rejects CRYPTO picks with confidence > 0.85; test fixture `_base_pick()` uses `confidence=0.88`. The gate + both matrix jobs fail in lockstep across every PR that touches `alpha_engine/`. Consistent with a single real assertion failure, not infra flakes or chronic cancellations.

**Open PRs:**
- **#1011** `fix/test-confidence-guard-2026-05-14` — `test (3.11)=in_progress`, `test (3.12)=in_progress`, `scan=success` → **PENDING** (this is the targeted fix: lowers `_base_pick()` fixture confidence 0.88→0.75; if CI passes, merge unblocks main)
- **#1012** `fix/live-picks-tracker-datetime-unbound-2026-05-14` — `scan=in_progress` → **PENDING** (P0 fix for hourly live-picks crash since 03:17Z; CI Tests not yet triggered)

**Action required:**
1. **Priority:** Merge PR #1011 once `test (3.11)` + `test (3.12)` complete — this is the only active fix for the systemic test failure causing main RED.
2. PR #1012 (live-picks UnboundLocalError) is a production incident fix — should be merged promptly after CI passes; it is independent of the test-fixture issue.
3. No additional code PRs should be merged to main until #1011 lands and main turns GREEN.

**Verdict change from 04:00 UTC:** None (RED → RED). No commit pushed (no-churn rule).

**Methodology note:** `gh` CLI absent. All CI data sourced from GitHub MCP `get_check_runs` on PR heads. Workflow run history (Step 2 canonical scan) not available; chronic-cancel determination based on check-run pattern analysis across 10+ PRs observed this session.

---

## 06:00 UTC

**Verdict:** GREEN

**Main CI Tests (last 5 proxied from PR check runs):** Systemic `CRYPTO_HIGH_CONF_GUARD` test failure resolved by PR #1011 (merged 05:09Z). Check runs on PR #1011 head:
- `test (3.11)` = **success** (completed 05:07:33Z)
- `test (3.12)` = **success** (completed 05:13:59Z)
- `scan` = **success** (completed 05:05:37Z)

All three matrix jobs passing. No failing CI Tests runs in the current window. Zero open PRs at time of scan.

**Chronic workflows:** No chronic-cancellation patterns detected. All 50+ commits to main since 05:00Z carry `[skip ci]` (bot automation); CI Tests only triggers on PR branches. No per-workflow pattern meeting CHRONIC threshold (latest=cancelled + ≥4 cancels/15 runs + 0 successes) observed.

**Open PRs RED:** none — 0 open PRs at time of scan.

**Action required:** none. Main CI GREEN; P0 live-picks `UnboundLocalError` crash (since 03:17Z) resolved by PR #1012 merged 05:10Z. No blocking failures.

**Verdict change from 05:00 UTC:** RED → GREEN. Committing this section.

**Methodology note:** `gh` CLI absent. CI data sourced from GitHub MCP `get_check_runs` on PR heads. Doc-only PRs #1013 and #1014 (merged 05:30Z) had no CI Tests triggered — expected for non-code changes.
