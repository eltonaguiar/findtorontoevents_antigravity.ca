# GHA Hourly Health Monitor — 2026-05-16

## 05:00 UTC

**Verdict:** DEGRADED _(improved from RED — see notes)_

**Main CI Tests (last meaningful runs):**
| Run | Branch | test(3.11) | test(3.12) | Source |
|---|---|---|---|---|
| PR #1094 merged (01:52Z) | feat/m051-pick-candidate-gen | FAILURE ❌ | CANCELLED ❌ | last merge to main |
| PR #1097 unmerged (04:52–05:01Z) | fix/trading-picks-indexes (based on main post-#1094) | SUCCESS ✅ | SUCCESS ✅ | most recent CI run |

> **Interpretation:** The systemic `test (3.11)` failure that caused RED verdicts since ≥2026-05-15 06:00Z appears **resolved**. PR #1097's branch — based on main SHA `f69332d2f18165ae7789b71595a9ea6c8b85f59b` (after #1094 merge) — passed both matrix jobs cleanly. However, PR #1094 was merged WITH CI Tests failing (governance concern), and no clean CI Tests run has landed on main itself. Calling DEGRADED, not GREEN, until a passing CI run on a merged-to-main PR is confirmed.

**Chronic workflows:**

| Workflow | Recent runs | Successes | Last success | Verdict |
|---|---|---|---|---|
| Gitleaks secret scan | 5 cancelled (PRs #1094, #1096, #1097, #1098, #1099) | 0 | Unknown (>48h) | **CHRONIC** ⚠️ |

> `Gitleaks secret scan` meets all chronic-flag criteria: latest=cancelled, ≥4 cancels in last 15 visible runs, 0 successes, no success within last 48h. Likely a billing/seat limit issue with the Gitleaks GitHub App, or the workflow timeout is too short for the repo's size. This does not block CI Tests but leaves the secret-scan coverage gap undetected.

**Secondary:** One `scan` job from run [25953192139](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/25953192139) FAILED on PR #1097. A second `scan` run (25953192635) on the same PR SUCCEEDED. Two workflows both named "scan" are racing — the failure is likely a path-specific check (possibly `hc-parity.yml` or `quant-auditor-fast-pr.yml`). Since PR #1097 was not merged, this does not affect main.

**Open PRs RED:** none — 0 open PRs as of 05:06 UTC.

> PRs #1026, #1027, #1037 (which were RED and open in yesterday's report) are now closed/not present. PRs #1096–#1099 were all closed without merging.

**Action required:**
1. **Author/operator:** Investigate why PR #1094 was merged despite CI Tests failing — the governance check (`gate` job?) may not be blocking merges when CI fails. Consider adding a branch protection rule requiring `CI Tests` to pass before merge.
2. **Operator:** Diagnose `Gitleaks secret scan` chronic cancellations — check the Gitleaks app's billing status or increase the workflow timeout in `.github/workflows/secret-scan.yml` (or whichever workflow drives it).
3. **Monitor (next hour):** If a code-touching PR is opened or merged, confirm CI Tests pass to promote verdict to GREEN.

---
_Status changed from RED (2026-05-15 06:00Z) → DEGRADED (2026-05-16 05:00Z). Commit triggered._

## 06:00 UTC

**Verdict:** DEGRADED _(unchanged from 05:00Z)_

**Main CI Tests (last meaningful runs):**
| PR | Merged | test(3.11) | test(3.12) | Notes |
|---|---|---|---|---|
| #1094 feat/m051-pick-candidate-gen | 01:52Z | FAILURE ❌ | CANCELLED ❌ | Most recent code PR to main |
| #1090 fix/audit P0/P1 banner | 00:57Z | FAILURE ❌ | CANCELLED ❌ | |
| #1088 fix/ci walkforward-gate diff-aware | 00:31Z | FAILURE ❌ | CANCELLED ❌ | |

> PR #1097 (the branch that passed CI Tests cleanly at 05:00Z analysis) is no longer open or present in recent merged PRs — it appears closed without merging. No code-touching PR has landed on main with a passing CI Tests run. The DEGRADED verdict stands; cannot promote to GREEN until a code-touching PR passes CI Tests and merges.

> Main branch commits since 05:31Z are all `[skip ci]` bot commits (ML tracker, Hermes Agent docs, Conviction Picks). No CI Tests triggered on main directly.

**Chronic workflows:**

| Workflow | Evidence | Verdict |
|---|---|---|
| Gitleaks secret scan | Cancelled on every PR sampled: #1100, #1094, #1090 (and #1096–#1099 per 05:00Z report). 0 successes in 8+ runs sampled. | **CHRONIC** ⚠️ (unchanged) |

**Open PRs RED:** none with CI Tests failure

> PR #1100 (audit/hourly-05z — auto-generated audit tracking PR): no CI Tests check runs triggered (docs/reports-only branch). Checks present: Gitleaks=cancelled, Grep-for-passwords=success, scan=success. Not actionable.

**Action required:**
1. **Author/operator (carry-over from 05:00Z):** A code-touching PR needs to open against current main and pass CI Tests to confirm the suite is green — without this confirmation main's CI status remains ambiguous. Target: any of the in-flight feature branches.
2. **Operator (carry-over):** Diagnose and fix `Gitleaks secret scan` chronic cancellations — 0 successes across 8+ consecutive runs is a sustained secret-scan coverage gap.
3. **No new escalations this hour.**

---
_Verdict unchanged DEGRADED. No commit (Step 5: only commit on verdict change)._

## 07:00 UTC

**Verdict:** RED _(escalated from DEGRADED — systemic CI Tests failure confirmed across all 5 most recent merged PRs)_

**Main CI Tests (last 5 code-PR runs):**
| PR | Merged | test(3.11) | test(3.12) | Notes |
|---|---|---|---|---|
| #1094 feat/m051-pick-candidate-gen | 01:52Z | FAILURE ❌ | CANCELLED | Most recent merge |
| #1093 feat/ai-leaderboard-research-proposers | 01:42Z | FAILURE ❌ | CANCELLED | Verified this hour |
| #1092 feat/m051-multi-model-vote | 01:21Z | CANCELLED | FAILURE ❌ | Matrix order reversed — still failing |
| #1090 fix/audit P0/P1 banner | 00:57Z | FAILURE ❌ | CANCELLED | From 06:00Z data |
| #1088 fix/walkforward-gate-diff-aware | 00:31Z | FAILURE ❌ | CANCELLED | From 06:00Z data |

> **5/5 most recent CI Tests runs = FAILURE.** Verdict escalated from DEGRADED to RED per protocol. PR #1084 body claimed "systemic test(3.11) failure resolved" but CI Tests failed on every subsequent merged PR (#1088 through #1094). The failure is matrix-wide: on PR #1092 the roles inverted (3.12 failed, 3.11 cancelled) confirming this is not a Python-version-specific issue. No code PR has passed CI Tests and merged to main since at least 2026-05-15T22:44Z (~8+ hours). Open PRs #1100 and #1101 are docs-only audit branches with no CI Tests check runs — they do not affect this verdict.

**Chronic workflows:**

| Workflow | Evidence | Verdict |
|---|---|---|
| Gitleaks secret scan | Cancelled on PRs #1092, #1093, #1094, #1100, #1101 (5+ consecutive). 0 successes visible. | **CHRONIC** ⚠️ (unchanged) |

**Open PRs RED:** none — both open PRs (#1100, #1101) are docs-only; no CI Tests triggered.

**Action required:**
1. **URGENT — Author/operator:** CI Tests has failed on every code PR merged to main for 8+ hours. Root cause unconfirmed (PR #1084 fix did not hold). Steps: (a) pull CI logs from failing run [25949603984](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/25949603984) (PR #1094 test 3.11 job) to identify the specific failing test; (b) open a fix PR; (c) confirm CI Tests passes before merging. **Do not merge code PRs until CI Tests is green.**
2. **Operator (carry-over):** Diagnose and fix `Gitleaks secret scan` chronic cancellations — 0 successes across 10+ consecutive runs is an unacceptable secret-scan gap.
3. **Governance (carry-over):** Enable branch protection rule requiring CI Tests to pass before merge — multiple code PRs have merged with failing CI today.

---
_Status changed from DEGRADED (06:00Z) → RED (07:00Z). Commit triggered._
