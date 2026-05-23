# GHA Hourly Health Monitor — 2026-05-02

## 08:00 UTC

**Verdict:** GREEN

**Main CI Tests (last 5 observable runs):** 5 success, 0 failure, 0 in_progress

> Note: `gh` CLI unavailable in this environment; CI status inferred from PR check runs.
> All 4 recent commits to main carry `[skip ci]` (bot commits: signal-recorder, System-F-Claws,
> dashboard-pick-trader, mega-mutation-tracker) — CI Tests not triggered on those.
> Most recent code PR with full test run: PR #665 (08:08–08:14Z) — 5/5 pass.
> Most recent merged code PR: #659 (07:30–07:35Z) — 4/4 pass.

**CI check runs observed (code PRs, today 2026-05-02):**

| PR | Branch | test(3.11) | test(3.12) | validate | scan | hc-parity | drift | verdict |
|----|--------|-----------|-----------|---------|------|-----------|-------|---------|
| #665 (open) | feat/b17-hc-after-cost-gate | ✅ | ✅ | ✅ | ✅ | ✅ | — | PASS |
| #659 (merged 07:36Z) | docs/hedge-fund-master-synthesis | ✅ | ✅ | — | ✅ | — | ✅ | PASS |
| #647 (open) | fix/risk-controls-none-date | — | — | — | ✅ | — | — | scan-only |
| #615 (open, HELD) | scanner-fixes-2026-05-01 | ❌ cancelled | ❌ failure | — | ✅ | — | — | FAIL |
| #597 (open) | investigate/usdchf-concentration | ❌ failure | ❌ cancelled | — | ✅ | — | — | FAIL |
| #664 (open) | audit-credibility-supplements | (no checks recorded) | — | — | — | — | — | UNKNOWN |

**Chronic workflows:** none detected

> Per-workflow history scan (15-run window) requires `gh run list --workflow` which is unavailable.
> Based on observable check-run data: all workflows (test, scan, validate, hc-parity, drift) show
> success on the most recent triggers. No pattern of 4+ consecutive cancellations observed.

**Open PRs RED:**

- **#615** — `fix: resolve 5 scanner blockers (circuit breaker, stdout crashes, earnings dict bug)`
  - `test (3.12)`: failure | `test (3.11)`: cancelled (run at 06:13–06:18Z)
  - Classification: **AUTHOR_FIX** — PR is explicitly HELD per broadcast PR #625: "10 test failures + risky CB reset, do not merge." Failure is pre-existing.
  - Action: author should fix 10 failing tests and address CB reset risk before merging.

- **#597** — `P0 fixes + USDCHF investigation: rapid_fire pair-block, pick revalidator`
  - `test (3.11)`: failure | `test (3.12)`: cancelled (run at 06:14–06:18Z, two separate run IDs)
  - Classification: **AUTHOR_FIX** — bundled multi-purpose PR; test failures on both Python versions. Pre-existing.
  - Action: author should isolate failing tests and fix before merging.

**Action required:** author should fix test failures in #615 and #597 before merging. No new regressions detected on main; these are pre-existing failures on open/held PRs.

---

## 09:00 UTC

**Verdict:** GREEN

**Main CI Tests (last 5 observable runs):** 5 success, 0 failure, 0 in_progress

> Note: `gh` CLI unavailable; CI status inferred from PR check runs. Main branch head
> (`07cd906`) is a [skip ci] bot commit ("Mutation Lab evolution"). CI Tests not triggered
> directly on main. Most recent code PR with full test run: PR #669 (opened 08:34Z) — 4/4 pass.
> Most recently merged PR: #672 (docs only, scan ✅). No main-branch regressions detected.

**CI check runs observed (code PRs, today 2026-05-02):**

| PR | Branch | test(3.11) | test(3.12) | validate | scan | hc-parity | drift | verdict |
|----|--------|-----------|-----------|---------|------|-----------|-------|---------|
| #669 (open) | feat/b2-ac-timeframe-grid | ✅ | ✅ | — | ✅ | — | ✅ | PASS |
| #665 (open) | feat/b17-hc-after-cost-gate | ✅ | ✅ | ✅ | ✅ | ✅ | — | PASS |
| #664 (open) | audit-credibility-supplements | ❌ failure | cancelled | — | ✅ | — | ✅ | FAIL |
| #661 (open) | infrastructure-modules-2026-05-02 | ❌ failure | cancelled | — | ✅ | — | — | FAIL |
| #660 (open) | emergency-gate-fixes | — | — | — | ✅ | — | — | scan-only (config-only PR) |
| #615 (open, HELD) | scanner-fixes-2026-05-01 | cancelled | ❌ failure | — | ✅ | — | — | FAIL |
| #597 (open) | investigate/usdchf-concentration | ❌ failure | cancelled | — | ✅ | — | — | FAIL |

**Chronic workflows:** none detected

> Cascade cancellations (test 3.12 cancelled when test 3.11 fast-fails in the same run) are visible
> on PRs #664, #661, #615, #597 but these are intra-run fail-fast artifacts, NOT standalone
> workflow chronic cancellations. No pattern of 4+ independent cancellations with 0 successes
> observed on any single workflow. Chronic-cancellation threshold not met.

**Open PRs RED:**

- **#664** — `Audit credibility supplements: 7 sidecar modules + 1 wired calibrator (68 tests)`
  - `test (3.11)`: failure | `test (3.12)`: cancelled (run 09:01–09:05Z) — NEW since 08:00 run
  - Classification: **AUTHOR_FIX** — real test failure (likely import or assertion error in one of the 7 new modules). 68-test suite introduced; one test job is failing on Python 3.11.
  - Action: author should investigate `test (3.11)` failure log and fix the broken test(s).

- **#661** — `Infrastructure v2.0 — Track Calculator, PSR/DSR Validation, Decay Tracker`
  - `test (3.11)`: failure | `test (3.12)`: cancelled (run 07:36–07:39Z) — NEW since 08:00 run
  - Classification: **AUTHOR_FIX** — noted in peer review (PR #671 body) as having a "fatal ImportError" in `statistical_rigor.py`. Needs deduplication fix (duplicate file) per REQUEST_CHANGES.
  - Action: author should fix ImportError and remove duplicate `statistical_rigor.py`.

- **#615** — `fix: resolve 5 scanner blockers (circuit breaker, stdout crashes, earnings dict bug)`
  - `test (3.12)`: failure | `test (3.11)`: cancelled (run 06:13–06:18Z) — pre-existing from 08:00 run
  - Classification: **AUTHOR_FIX** — explicitly HELD per broadcast PR #625: "10 test failures + risky CB reset, do not merge."
  - Action: author should fix 10 failing tests and address CB reset risk before merging.

- **#597** — `P0 fixes + USDCHF investigation: rapid_fire pair-block, pick revalidator`
  - `test (3.11)`: failure | `test (3.12)`: cancelled (two run IDs, 06:14Z) — pre-existing from 08:00 run
  - Classification: **AUTHOR_FIX** — bundled multi-purpose PR with test failures on both Python versions.
  - Action: author should isolate failing tests and fix before merging.

**Action required:** authors of #664 and #661 should investigate and fix newly-detected test failures. #615 and #597 failures are pre-existing. PRs #669 and #665 are CI-green and merge-ready. No action needed on main branch.

---

## 10:00 UTC

**Verdict:** GREEN

**Main CI Tests (last 5 observable runs):** 5 success, 0 failure, 0 in_progress

> Note: `gh` CLI unavailable; CI status inferred from PR check runs. Main branch HEAD
> (`cf359a54`) is a [skip ci] bot commit ("Auto-update prediction quality metrics 2026-05-02 10:08Z").
> CI Tests not triggered directly on main. Most recently merged code PRs: #670 (fix/audit-dashboard
> template, 08:48Z — HTML-only change, no Python tests), #647 (fix/risk-controls, 08:46Z, scan ✅).
> Most recent PR with full Python test run: PR #669 (open, 08:34Z) — 4/4 pass. No main regressions.

**CI check runs observed (code PRs, today 2026-05-02):**

| PR | Branch | test(3.11) | test(3.12) | validate | scan | hc-parity | drift | verdict |
|----|--------|-----------|-----------|---------|------|-----------|-------|---------|
| #669 (open) | feat/b2-ac-timeframe-grid | ✅ | ✅ | — | ✅ | — | ✅ | PASS |
| #665 (open) | feat/b17-hc-after-cost-gate | ✅ | ✅ | ✅ | ✅ | ✅ | — | PASS |
| #664 (open) | audit-credibility-supplements | ✅ *(recovered)* | ✅ *(recovered)* | — | ✅ | — | — | PASS ✅ |
| #661 (open) | infrastructure-modules-2026-05-02 | ❌ failure | cancelled | — | ✅ | — | — | FAIL |
| #660 (open) | emergency-gate-fixes | — | — | — | ✅ | — | — | scan-only |
| #658 (open) | hedge-fund-enhancement | — | — | — | ✅ | — | — | scan-only |
| #608 (open) | feat/b26-tradingagents-smoke | ❌ failure | cancelled | — | ✅ | — | ✅ | FAIL |
| #615 (open, HELD) | scanner-fixes-2026-05-01 | cancelled | ❌ failure | — | ✅ | — | — | FAIL |
| #597 (open) | investigate/usdchf-concentration | ❌ failure | cancelled | — | ✅ | — | — | FAIL |

**Delta from 09:00 UTC:**
- PR #664 **recovered GREEN** — new test run at 09:36Z shows 3/3 pass (author pushed fix between 09:00–09:36Z).
- PR #608 **newly observed RED** — `test(3.11)` failure at 06:13Z; pre-existing, not checked in prior hourly runs.
- PRs #661, #615, #597 remain RED; no new activity on those branches.

**Chronic workflows:** none

> Per-workflow gh CLI query unavailable. Cascade cancellations visible on PRs #661, #608, #615, #597
> are intra-run fail-fast artifacts (test 3.12 cancelled when test 3.11 fast-fails), not standalone
> chronic cancellations. Chronic threshold (0 successes + ≥4 cancels in 15-run window) not met
> for any individual workflow based on available data.

**Open PRs RED:**

- **#661** — `Infrastructure v2.0 — Track Calculator, PSR/DSR Validation, Decay Tracker`
  - `test (3.11)`: failure | `test (3.12)`: cancelled (run 07:36–07:39Z) — pre-existing from 09:00 report
  - Classification: **AUTHOR_FIX** — known ImportError in `statistical_rigor.py`; fix: resolve duplicate file and ImportError.
  - Action: author should fix ImportError and deduplicate `statistical_rigor.py`.

- **#608** — `test(tradingagents): B26 — live smoke test gated on TRADINGAGENTS_LIVE_SMOKE=1`
  - `test (3.11)`: failure | `test (3.12)`: cancelled (run 06:13–06:17Z) — pre-existing (first observation in this monitor)
  - Classification: **AUTHOR_FIX** — failure timestamp matches the ~06:13Z batch that also hit #615 and #597; may be a common transient or a real assertion error. Scan and drift checks pass.
  - Action: author should rerun CI or investigate `test(3.11)` failure log.

- **#615** — `fix: resolve 5 scanner blockers (circuit breaker, stdout crashes, earnings dict bug)`
  - `test (3.12)`: failure | `test (3.11)`: cancelled (run 06:13–06:18Z) — pre-existing, HELD
  - Classification: **AUTHOR_FIX** — HELD per broadcast PR #625; 10 test failures + risky CB reset.
  - Action: author should fix failing tests and address CB reset risk before merging.

- **#597** — `P0 fixes + USDCHF investigation: rapid_fire pair-block, pick revalidator`
  - `test (3.11)`: failure | `test (3.12)`: cancelled (two run IDs, 06:14Z) — pre-existing
  - Classification: **AUTHOR_FIX** — bundled multi-purpose PR; test failures on both Python versions.
  - Action: author should isolate and fix failing tests.

**Notable positive:** PR #664 (`audit-credibility-supplements`, 68 tests) recovered to GREEN since the 09:00 UTC report — author pushed a fix and all tests now pass at 09:36Z.

**Action required:** authors of #661 and #608 should investigate and fix test failures. #615 and #597 are pre-existing held PRs. PRs #669 and #665 are CI-green and merge-ready. No action required on main branch.

---

## 11:00 UTC

**Verdict:** GREEN

**Main CI Tests (last 5 observable runs):** 5 success, 0 failure, 1 in_progress

> Note: `gh` CLI unavailable; CI status inferred from PR check runs. Main branch HEAD is a
> [skip ci] bot commit ("Update QuantumFusion performance report", 11:21Z). CI Tests not triggered
> directly on main. Most recent code PR with full test run: PR #673 (opened 10:35Z) — 3/3 pass.
> PR #664 has a new commit pushed at ~11:20Z with CI in_progress (was GREEN at 10:00Z check).

**CI check runs observed (code PRs, 2026-05-02):**

| PR | Branch | test(3.11) | test(3.12) | scan | other | verdict |
|----|--------|-----------|-----------|------|-------|---------|
| #673 (open, new) | feat/b14-slippage-stress | ✅ (10:41Z) | ✅ (10:39Z) | ✅ | — | PASS |
| #669 (open) | feat/b2-ac-timeframe-grid | ✅ | ✅ | ✅ | drift ✅ | PASS |
| #665 (open) | feat/b17-hc-after-cost-gate | ✅ | ✅ | ✅ | validate ✅, hc-parity ✅ | PASS |
| #664 (open) | audit-credibility-supplements | 🔄 in_progress | 🔄 in_progress | 🔄 in_progress | — | PENDING |
| #661 (open) | infrastructure-modules-2026-05-02 | ❌ failure | cancelled | ✅ | — | FAIL |
| #608 (open) | feat/b26-tradingagents-smoke | ❌ failure | cancelled | ✅ | drift ✅ | FAIL |
| #615 (open, HELD) | scanner-fixes-2026-05-01 | cancelled | ❌ failure | ✅ | — | FAIL |
| #597 (open) | investigate/usdchf-concentration | ❌ failure | cancelled | ✅ | — | FAIL |

**Delta from 10:00 UTC:**
- **PR #673 opened** (10:35Z) — B14 slippage stress test, 31 tests; all 3 CI checks pass ✅
- **PR #664** new commit pushed at ~11:20Z; new CI run in_progress. Previously recovered GREEN at ~09:36Z; new push does not indicate regression, just further iteration.
- **PR #668** (Copilot draft, feature flags): no CI check runs (draft PRs may be excluded).
- All pre-existing failures on #661, #608, #615, #597 are unchanged.

**Chronic workflows:** none

> Per-workflow gh CLI query unavailable. Cascade cancellations on #661, #608, #615, #597 are
> intra-run fail-fast artifacts (test 3.12 cancelled when test 3.11 fast-fails in same run).
> Chronic-cancellation threshold (0 successes + ≥4 cancels in last 15 per-workflow runs) not met
> for any individual workflow based on available data.

**Open PRs RED:**

- **#661** — `Infrastructure v2.0 — Track Calculator, PSR/DSR Validation, Decay Tracker`
  - `test (3.11)`: failure | `test (3.12)`: cancelled (run 07:36–07:39Z) — pre-existing
  - Classification: **AUTHOR_FIX** — known fatal ImportError in `statistical_rigor.py`; duplicate file issue noted in REQUEST_CHANGES review.
  - Action: author should fix ImportError, deduplicate `statistical_rigor.py`, re-push.

- **#608** — `test(tradingagents): B26 — live smoke test gated on TRADINGAGENTS_LIVE_SMOKE=1`
  - `test (3.11)`: failure | `test (3.12)`: cancelled (run 06:13–06:17Z) — pre-existing
  - Classification: **AUTHOR_FIX** — failure first observed at 06:13Z batch; same batch that hit #615 and #597 (could be shared transient or real assertion failure). No re-push since.
  - Action: author should investigate `test(3.11)` log and re-push or request rerun.

- **#615** — `fix: resolve 5 scanner blockers (circuit breaker, stdout crashes, earnings dict bug)`
  - `test (3.12)`: failure | `test (3.11)`: cancelled (run 06:13–06:18Z) — pre-existing, HELD
  - Classification: **AUTHOR_FIX** — HELD per broadcast PR #625: "10 test failures + risky CB reset, do not merge."
  - Action: author should fix 10 failing tests and address CB reset risk.

- **#597** — `P0 fixes + USDCHF investigation: rapid_fire pair-block, pick revalidator`
  - `test (3.11)`: failure | `test (3.12)`: cancelled (06:14Z, two runs) — pre-existing
  - Classification: **AUTHOR_FIX** — bundled multi-purpose PR; test failures on both Python versions.
  - Action: author should isolate and fix failing tests before merging.

**Action required:** authors of #661 and #608 should investigate and fix test failures. #615 and #597 are pre-existing held PRs. PRs #673, #669, and #665 are CI-green and merge-ready. Monitor PR #664 CI result (in_progress at time of scan). No action required on main branch.

---

## 12:00 UTC

**Verdict:** GREEN

**Main CI Tests (last 5 observable runs):** 5 success, 0 failure, 0 in_progress

> Note: `gh` CLI unavailable; CI status inferred from PR check runs. Main branch HEAD is a
> [skip ci] bot commit ("Cross-system aggregation 2026-05-02 12:01 UTC"). CI Tests not triggered
> directly on main. Most recent code PR with full test run: PR #664 (11:52–11:58Z) — 3/3 pass.
> PR #673 (10:36–10:41Z) — 3/3 pass. No main-branch regressions detected.

**CI check runs observed (code PRs, 2026-05-02):**

| PR | Branch | test(3.11) | test(3.12) | scan | other | verdict |
|----|--------|-----------|-----------|------|-------|---------|
| #673 (open) | feat/b14-slippage-stress | ✅ (10:41Z) | ✅ (10:39Z) | ✅ | — | PASS |
| #669 (open) | feat/b2-ac-timeframe-grid | ✅ | ✅ | ✅ | drift ✅ | PASS |
| #665 (open) | feat/b17-hc-after-cost-gate | ✅ | ✅ | ✅ | validate ✅, hc-parity ✅ | PASS |
| #664 (open) | audit-credibility-supplements | ✅ (11:58Z) | ✅ (11:58Z) | ✅ | — | PASS ✅ recovered |
| #661 (open) | infrastructure-modules-2026-05-02 | ❌ failure | cancelled | ✅ | — | FAIL |
| #608 (open) | feat/b26-tradingagents-smoke | ❌ failure | cancelled | ✅ | drift ✅ | FAIL |
| #615 (open, HELD) | scanner-fixes-2026-05-01 | cancelled | ❌ failure | ✅ | — | FAIL |
| #597 (open) | investigate/usdchf-concentration | ❌ failure | cancelled | ✅ | — | FAIL |

**Delta from 11:00 UTC:**
- **PR #664** resolved PENDING → GREEN: new test run at 11:52Z passes all 3 checks ✅. No longer "monitor pending."
- **PRs #661, #608, #615, #597** unchanged — no new pushes, failures pre-existing.
- No new PRs opened or merged between 11:00–12:00 UTC (main HEAD unchanged from prior [skip ci] bot run).

**Chronic workflows:** none

> Per-workflow gh CLI query unavailable. Cascade cancellations on #661, #608, #615, #597 are
> intra-run fail-fast artifacts. Chronic-cancellation threshold (0 successes + ≥4 cancels in last
> 15 per-workflow runs) not met for any individual workflow based on available data.

**Open PRs RED:**

- **#661** — `Infrastructure v2.0 — Track Calculator, PSR/DSR Validation, Decay Tracker`
  - `test (3.11)`: failure | `test (3.12)`: cancelled (run 07:36–07:39Z) — pre-existing, no new push
  - Classification: **AUTHOR_FIX** — known fatal ImportError in `statistical_rigor.py`; duplicate file issue per REQUEST_CHANGES review.
  - Action: author should fix ImportError, deduplicate `statistical_rigor.py`, re-push.

- **#608** — `test(tradingagents): B26 — live smoke test gated on TRADINGAGENTS_LIVE_SMOKE=1`
  - `test (3.11)`: failure | `test (3.12)`: cancelled (run 06:13–06:17Z) — pre-existing, no new push
  - Classification: **AUTHOR_FIX** — failure first observed at 06:13Z; same batch as #615 and #597. No activity since.
  - Action: author should investigate `test(3.11)` log and re-push or request CI rerun.

- **#615** — `fix: resolve 5 scanner blockers (circuit breaker, stdout crashes, earnings dict bug)`
  - `test (3.12)`: failure | `test (3.11)`: cancelled (run 06:13–06:18Z) — pre-existing, HELD
  - Classification: **AUTHOR_FIX** — HELD per broadcast PR #625: "10 test failures + risky CB reset, do not merge."
  - Action: author should fix 10 failing tests and address CB reset risk.

- **#597** — `P0 fixes + USDCHF investigation: rapid_fire pair-block, pick revalidator`
  - `test (3.11)`: failure | `test (3.12)`: cancelled (06:14Z, two runs) — pre-existing, no new push
  - Classification: **AUTHOR_FIX** — bundled multi-purpose PR; test failures on both Python versions.
  - Action: author should isolate and fix failing tests before merging.

**Action required:** authors of #661 and #608 should investigate and fix test failures. #615 and #597 are pre-existing held PRs. PRs #673, #669, #665, and #664 are CI-green and merge-ready. No action required on main branch.

---

## 13:00 UTC

**Verdict:** GREEN

**Main CI Tests (last 5 observable runs):** 5 success, 0 failure, 0 in_progress

> Note: `gh` CLI unavailable; CI status inferred from PR check runs. Main branch HEAD is a
> [skip ci] bot commit ("Signal recorder update 2026-05-02 13:15 UTC"). CI Tests not triggered
> directly on main. Most recently merged code PR: #672 (docs-only, 08:58Z). Most recent code
> PR with full Python test run: PR #674 (12:52–12:57Z) — 3/3 pass. No main-branch regressions.

**CI check runs observed (code PRs, 2026-05-02):**

| PR | Branch | test(3.11) | test(3.12) | scan | other | verdict |
|----|--------|-----------|-----------|------|-------|---------|
| #675 (open, docs) | docs/tpl-verified-sitc-waf | — | — | ✅ (13:06Z) | — | scan-only |
| #674 (open, NEW) | fix/b11-etf-production-emitters | ✅ (12:52Z) | ✅ (12:52Z) | ✅ (12:54Z) | — | PASS ✅ |
| #673 (open) | feat/b14-slippage-stress | ✅ | ✅ | ✅ | — | PASS |
| #669 (open) | feat/b2-ac-timeframe-grid | ✅ | ✅ | ✅ | drift ✅ | PASS |
| #665 (open) | feat/b17-hc-after-cost-gate | ✅ | ✅ | ✅ | validate ✅, hc-parity ✅ | PASS |
| #664 (open) | audit-credibility-supplements | ✅ (13:00Z) | ✅ (13:00Z) | ✅ | — | PASS ✅ |
| #661 (open) | infrastructure-modules-2026-05-02 | ❌ failure | cancelled | ✅ | — | FAIL |
| #615 (open, HELD) | scanner-fixes-2026-05-01 | cancelled | ❌ failure | ✅ | — | FAIL |
| #608 (open) | feat/b26-tradingagents-smoke | ❌ failure | cancelled | ✅ | drift ✅ | FAIL |
| #597 (open) | investigate/usdchf-concentration | ❌ failure | cancelled | ✅ | — | FAIL |

**Delta from 12:00 UTC:**
- **PR #674 opened** (12:52Z) — B11 ETF production emitter wiring fix; all 3 CI checks pass ✅. New merge candidate.
- **PR #664** fresh run at 13:00Z (author iteration) — still GREEN ✅. No regression.
- **PR #675** (docs-only, TPL/SITC verification) — scan-only pass; no Python tests triggered (docs change).
- **PRs #661, #615, #608, #597** — no new pushes; all failures unchanged and pre-existing.

**Chronic workflows:** none

> Per-workflow `gh run list --workflow` unavailable. Cascade cancellations on #661, #608, #615,
> #597 are intra-run fail-fast artifacts (test 3.12 cancelled when test 3.11 fast-fails in same
> run). Chronic-cancellation threshold (latest=cancelled + ≥4 cancels + 0 successes in 15-run
> window) not met for any individual workflow based on available data.

**Open PRs RED:**

- **#661** — `Infrastructure v2.0 — Track Calculator, PSR/DSR Validation, Decay Tracker`
  - `test (3.11)`: failure | `test (3.12)`: cancelled (run 07:36–07:39Z) — pre-existing, no new push
  - Classification: **AUTHOR_FIX** — known fatal ImportError in `statistical_rigor.py`; duplicate file per REQUEST_CHANGES.
  - Action: author should fix ImportError, deduplicate `statistical_rigor.py`, re-push.

- **#608** — `test(tradingagents): B26 — live smoke test gated on TRADINGAGENTS_LIVE_SMOKE=1`
  - `test (3.11)`: failure | `test (3.12)`: cancelled (run 06:13–06:17Z) — pre-existing, no new push
  - Classification: **AUTHOR_FIX** — no activity since initial 06:13Z failure run; same batch as #615/#597.
  - Action: author should investigate `test(3.11)` log and re-push or request CI rerun.

- **#615** — `fix: resolve 5 scanner blockers (circuit breaker, stdout crashes, earnings dict bug)`
  - `test (3.12)`: failure | `test (3.11)`: cancelled (run 06:13–06:18Z) — pre-existing, HELD
  - Classification: **AUTHOR_FIX** — HELD per broadcast PR #625: "10 test failures + risky CB reset, do not merge."
  - Action: author should fix 10 failing tests and address CB reset risk.

- **#597** — `P0 fixes + USDCHF investigation: rapid_fire pair-block, pick revalidator`
  - `test (3.11)`: failure | `test (3.12)`: cancelled (06:14Z, two runs) — pre-existing, no new push
  - Classification: **AUTHOR_FIX** — bundled multi-purpose PR; test failures on both Python versions.
  - Action: author should isolate and fix failing tests before merging.

**Action required:** authors of #661 and #608 should investigate and fix test failures. #615 and #597 are pre-existing held PRs. PRs #674, #673, #669, #665, and #664 are CI-green and merge-ready. No action required on main branch.
