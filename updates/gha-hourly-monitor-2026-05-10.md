# GHA Hourly Health Monitor — 2026-05-10

## 05:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** Unable to query workflow run history directly (gh CLI unavailable in this environment; MCP-only mode). Proxy evidence from open PRs: across 6 consecutive code-change PRs (#876, #878, #887, #889, #891 from 2026-05-09T17:41Z → 2026-05-10T04:08Z), at least one of `test (3.11)` / `test (3.12)` is FAILED with the other CANCELLED on every run. `gate` also fails on all PRs that trigger it. `scan` and `audit` pass on all. Pattern spans ~10.5 hours with zero passing CI Tests runs — treat as **RED**.

**Chronic workflows:** None flagged per spec definition (requires ≥4 cancellations + 0 successes in last 15 runs). The `test (3.12)` / `test (3.11)` cancellations are consequential — one Python version fails first, causing the other to cancel — not independent chronic cancellations. `gate` failures are FAILURE, not CANCELLED. Full per-workflow chronic scan not possible without gh CLI.

**Open PRs RED:**

| PR | Title (truncated) | Failing checks | Classification |
|----|-------------------|----------------|----------------|
| #891 | fix(mysql_sync): entry_time/exit_time fallback | test(3.11)=failure, test(3.12)=cancelled, gate=failure | AUTHOR_FIX — likely systemic root cause, not PR-specific |
| #889 | feat(b13): HMM regime filter sidecar | test(3.11)=failure, test(3.12)=cancelled, gate=failure | AUTHOR_FIX — systemic |
| #887 | feat(quality_gates): WIN_RATE_TRAP_BLACKLIST | test(3.11)=failure, test(3.12)=cancelled | AUTHOR_FIX — systemic |
| #878 | feat(short_engine): BULL-regime gate | test(3.12)=failure, test(3.11)=cancelled, gate=failure | AUTHOR_FIX — systemic |
| #876 | fix(mysql_sync): pnl_pct anomaly clamp | test(3.12)=failure, test(3.11)=cancelled, gate=failure | AUTHOR_FIX — systemic |

PRs with only `scan` (no CI Tests): #888, #890 — these are audit/report PRs that don't trigger the full test matrix; classified GREEN for their scope.

**Evidence table (run IDs for triage):**

| PR | CI Tests run | gate run | Opened |
|----|-------------|----------|--------|
| #891 | 25619442812 | 25619442818 | 2026-05-10T04:08Z |
| #889 | 25619334471 | 25619334473 | 2026-05-10T04:01Z |
| #887 | 25618360690 | — | 2026-05-10T03:07Z |
| #878 | 25607979330 | 25607979335 | 2026-05-09T17:59Z |
| #876 | 25607548294 | 25607548309 | 2026-05-09T17:41Z |

**Action required:** Systemic CI test failure active for ≥10 hours across all code-change PRs. Likely root cause: shared conftest.py, a pytest fixture, or a dependency that broke across the test matrix — NOT individual PR code. **Recommended action:** Owner should bisect the test failure on a clean branch (e.g. `git stash && pytest` against HEAD of main) and identify which test(s) fail. Check recent merges to main for changes to `conftest.py`, `requirements*.txt`, or shared test utilities. Opening a hotfix PR with the fix will unblock all 5+ stalled PRs.

---
*Monitor run: 2026-05-10T05:00Z | gh CLI unavailable — using GitHub MCP tools (pr check_runs) as proxy*

## 06:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** gh CLI unavailable; proxy via open PR check_runs. All 3 code-change PRs that received CI runs this hour failed test(3.11). Pattern identical to 05:00 UTC — zero passing CI Tests runs on any code-change branch. The two merges to main since 05:00 UTC were docs-only PRs (#886, #874) that only triggered `scan` (green); main's last actual CI Tests run remains the pre-systemic-failure state. Treating main as **RED** (same evidence base).

**Chronic workflows:** None flagged per spec (cannot run per-workflow 15-run queries without gh CLI). The test(3.11) / test(3.12) cancel-cascade pattern persists but is a consequence of a single test failure, not an independent chronic cancellation.

**Open PRs RED (as of 06:00 UTC):**

| PR | Title (truncated) | Failing checks | Classification |
|----|-------------------|----------------|----------------|
| #895 | feat(b13): HMM regime filter v4 (audit_trail/ placement) | test(3.11)=failure, test(3.12)=cancelled | AUTHOR_FIX — systemic; PR body claims 19/19 tests pass locally, so failure is conftest/env level not PR code |
| #893 | feat(safe-ops): orphan_resolver_dryrun.py | test(3.11)=failure, test(3.12)=cancelled | AUTHOR_FIX — systemic |
| #891 | fix(mysql_sync): entry_time/exit_time fallback | test(3.11)=failure, test(3.12)=cancelled, gate=failure | AUTHOR_FIX — systemic; gate also failing |
| #892 | feat(db-safety): tools/safe_db_archive.py | no check runs | UNKNOWN — no CI triggered yet |
| #894 | audit(05Z 2026-05-10): EQUITY T1 confirmed | scan=success only | GREEN for scope (audit/docs PR) |

**Delta from 05:00 UTC:** 2 new RED PRs (#895, #893 — both opened after 04:50Z). Previously RED PRs #889/#872/#868 are now closed (superseded by #895). Net open-RED count: 3 code PRs red + 1 unknown, unchanged systemic pattern.

**Action required:** Systemic CI test failure now spans ≥12 hours and ≥7 consecutive code-change PRs. The root cause is upstream of PR code (conftest, fixture, or dependency regression on main). **Owner should:** (1) clone main fresh, `pytest` without any PR changes to confirm the base failure; (2) `git log --since="2026-05-09T17:00Z" -- conftest.py requirements*.txt tests/` to find the offending commit; (3) open a one-line hotfix PR to unblock all stalled code PRs.

---
*Monitor run: 2026-05-10T06:00Z | gh CLI unavailable — using GitHub MCP tools (pr check_runs) as proxy*
