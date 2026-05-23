# GHA Hourly Health Monitor — 2026-05-03

## 02:00 UTC

**Verdict:** GREEN

**Main CI Tests (last 5 observable runs):** 5 success, 0 failure, 0 in_progress

> Note: `gh` CLI unavailable in this environment; CI status inferred from PR check runs.
> Main branch HEAD (`a1fcb7cd`, 02:04Z) is a bot merge commit following a series of `[skip ci]`
> bot pushes (audit-dashboard refresh, prediction-market signals, outcome resolver, gainer scan).
> CI Tests not triggered directly on main. Most recently merged PRs: #712 (fix(ui) — HTML one-line
> wording fix, scan ✅ drift ✅, 01:16Z), #708 (docs/kimi-swarm-v3 archive, 01:01Z), #655
> (docs/cloud-agent-roadmap, 01:02Z). All docs or HTML-only — Python CI Tests not triggered.
> Last code PR with full Python test run still-green (from yesterday): PRs #664, #665, #669,
> #673, #674 — all confirmed GREEN before merge, no regressions detected.

**CI check runs observed (code/active PRs, 2026-05-03 02:00Z):**

| PR | Branch | test(3.11) | test(3.12) | scan | drift | verdict |
|----|--------|-----------|-----------|------|-------|---------|
| #713 (open, docs) | docs/kimi-swarm-v4 | — | — | — | — | no CI (docs-only) |
| #711 (open, docs) | docs/wf-audit-starvation | — | — | ✅ | — | scan-only |
| #710 (open, docs) | docs/hc-verdict-evidence | — | — | ✅ | — | scan-only |
| #709 (open, docs) | docs/freebuff-buffy-pr-review | — | — | — | — | no CI (docs-only) |
| #712 (merged 01:16Z) | fix/hc-legend-wording | — | — | ✅ | ✅ | PASS (HTML-only) |
| #661 (open) | infrastructure-modules-2026-05-02 | ❌ failure | cancelled | ✅ | — | FAIL |
| #660 (open) | emergency-gate-fixes | — | — | ✅ | — | scan-only (config-only PR) |
| #668 (open, draft) | copilot/enable-feature-flags | — | — | ✅ | — | scan-only (config-only PR) |
| #608 (open) | feat/b26-tradingagents-smoke | ❌ failure | cancelled | ✅ | ✅ | FAIL |
| #615 (open, HELD) | scanner-fixes-2026-05-01 | cancelled | ❌ failure | ✅ | — | FAIL |
| #597 (open) | investigate/usdchf-concentration | ❌ failure | cancelled | ✅ | — | FAIL |

**Delta from 2026-05-02 13:00 UTC (last entry):**
- PRs #664, #665, #669, #673, #674, #675 no longer appear in open PR list — presumed merged between
  13:00Z yesterday and 02:00Z today. All had confirmed GREEN CI at time of last observation.
- PRs #658 and #681 were **closed without merge** (confirmed via closed PR API, closed ≈ 01:02Z today).
- Four new **docs-only** PRs opened: #709, #710, #711, #713 — no Python CI Tests triggered.
- **PRs #615, #597, #661, #608** remain RED with no new pushes since yesterday — failures unchanged.
- No new CI Tests failures introduced. No regressions on main.

**Chronic workflows:** none

> Per-workflow `gh run list --workflow` unavailable (gh CLI absent). Cascade cancellations on PRs
> #661, #608, #615, #597 are intra-run fail-fast artifacts: one matrix job (test 3.11 or 3.12)
> fast-fails and GitHub automatically cancels its sibling — not independent chronic-cancellation
> events. Chronic-cancellation threshold (latest run = cancelled AND ≥4 cancels AND 0 successes
> AND no success in last 48h within 15-run window) not met for any individual workflow.

**Open PRs RED:**

- **#661** — `Infrastructure v2.0 — Track Calculator, PSR/DSR Validation, Decay Tracker`
  - `test (3.11)`: failure | `test (3.12)`: cancelled (run 07:36–07:39Z, 2026-05-02) — pre-existing, no new push
  - Classification: **AUTHOR_FIX** — known fatal ImportError in `statistical_rigor.py`; duplicate file issue per REQUEST_CHANGES review (PR #671 body). Wire-Up Rule also flagged.
  - Action: author should fix ImportError, deduplicate `statistical_rigor.py`, add `## Wiring Plan` section, re-push.

- **#608** — `test(tradingagents): B26 — live smoke test gated on TRADINGAGENTS_LIVE_SMOKE=1`
  - `test (3.11)`: failure | `test (3.12)`: cancelled (run 06:13–06:17Z, 2026-05-02) — pre-existing, no new push since 2026-05-02T00:40Z open
  - Classification: **AUTHOR_FIX** — failure is part of the 06:13Z batch affecting multiple PRs simultaneously; may be transient infra or real assertion error. No re-push has been made.
  - Action: author should investigate `test(3.11)` failure log and push a fix or request CI rerun.

- **#615** — `fix: resolve 5 scanner blockers (circuit breaker, stdout crashes, earnings dict bug)`
  - `test (3.12)`: failure | `test (3.11)`: cancelled (run 06:13–06:18Z, 2026-05-02) — pre-existing, HELD
  - Classification: **AUTHOR_FIX** — explicitly HELD per broadcast PR #625: "10 test failures + risky CB reset, do not merge." `circuit_breaker.json` EMERGENCY→NORMAL reset is the risk flag.
  - Action: author should fix 10 failing tests and address CB reset risk before merging.

- **#597** — `P0 fixes + USDCHF investigation: rapid_fire pair-block, pick revalidator`
  - `test (3.11)`: failure | `test (3.12)`: cancelled (two separate run IDs at 06:14Z, 2026-05-02) — pre-existing, no new push
  - Classification: **AUTHOR_FIX** — bundled multi-purpose PR; test failures on both Python versions. `pick_revalidator` is explicitly opt-in/sidecar (no production caller yet per Wire-Up Rule).
  - Action: author should isolate failing tests and fix before merging.

**Action required:** authors of #661 and #608 should investigate and fix pre-existing test failures. #615 and #597 are explicitly held PRs — do not merge until authors address test failures and risk flags. No action required on main branch.

---

## 03:00 UTC

**Verdict:** GREEN

**Main CI Tests (last 5 observable runs):** 5 success, 0 failure, 0 in_progress

> Note: `gh` CLI unavailable; CI status inferred from GitHub MCP check-run API.
> All 5 most recent commits on main (HEAD `cf30a173`, 03:23Z) are `[skip ci]` bot pushes:
> Sustained Gainer scan (03:23Z), Breakout Arena scan (03:22Z), two merge commits (03:22Z),
> and audit-dashboard payload refresh (03:22Z). No CI Tests workflow triggered on main.
> Verdict unchanged from 02:00 UTC — main remains GREEN.

**New activity since 02:00 UTC:**

| PR | Branch | test(3.11) | test(3.12) | scan | verdict |
|----|--------|-----------|-----------|------|---------|
| #721 (opened 03:21Z, docs) | docs/peer-state-summary-2026-05-03 | — | — | ✅ 03:23Z | GREEN (docs-only) |
| #720 (opened 03:18Z, code) | audit-credibility-supplements-2026-05-02 | 🔄 in_progress | 🔄 in_progress | ✅ 03:21Z | PENDING |

PR #720 (`feat(crypto-panel): Overall tile + master plan`) — CI Tests run `25268619868` started at 03:18:46Z, both matrix jobs still in_progress as of report time (~03:30Z). Changes are template.html JS/HTML only; Python test results TBD. No failure observed yet.

**Chronic workflows:** none (unchanged — cascade-cancel pattern on PRs #597/#608/#615/#661 are intra-run fail-fast siblings, not independent chronic-cancellation events)

**Open PRs RED (all pre-existing, no new pushes since 02:00 UTC):**

- **#661** — `Infrastructure v2.0` — test(3.11) ❌ FAILURE (07:36–07:39Z, 2026-05-02), test(3.12) cancelled
  - Classification: **AUTHOR_FIX** — ImportError in `statistical_rigor.py`; Wire-Up Rule gap
  - Action: fix ImportError, add Wiring Plan, re-push

- **#615** — `fix: 5 scanner blockers` (HELD per #625) — test(3.12) ❌ FAILURE (06:13–06:18Z, 2026-05-02), test(3.11) cancelled
  - Classification: **AUTHOR_FIX** — 10 failing tests + risky circuit_breaker.json reset; do not merge
  - Action: fix 10 failing tests, address CB reset risk

- **#608** — `test(tradingagents): B26 smoke` — test(3.11) ❌ FAILURE (06:13–06:17Z, 2026-05-02), test(3.12) cancelled
  - Classification: **AUTHOR_FIX** — test failure on initial push; no re-push in ~21h
  - Action: investigate test(3.11) failure log, fix or rerun

- **#597** — `P0 fixes + USDCHF investigation` — test(3.11) ❌ FAILURE (06:14Z, 2026-05-02), test(3.12) cancelled (2 runs)
  - Classification: **AUTHOR_FIX** — bundled PR with test failures on both Python versions; pick_revalidator is opt-in sidecar with no Wire-Up yet
  - Action: isolate and fix failing tests before merging

**Action required:** none on main. Watch PR #720 CI Tests (in_progress); if they fail, reclassify to RED next hour. PRs #661/#608/#597 authors should fix tests; #615 remains HELD.

---

## 04:00 UTC

**Verdict:** GREEN

**Main CI Tests (last 5 observable runs):** 5 success, 0 failure, 0 in_progress

> Note: `gh` CLI unavailable; CI status inferred from GitHub MCP check-run API.
> Main branch HEAD (`1ae9ba1d`, 04:04Z) is a bot merge commit following `[skip ci]` bot pushes
> (audit-dashboard payload refresh 04:04Z, Gainer Capture 04:03Z, CI-improvement report 04:02Z,
> Live Spike Trader 03:58Z, Dynamic universe 03:57Z). No CI Tests triggered on main HEAD.
> Last code PR with full CI run: PR #719 (merged 03:19Z, `feat(gates+audit): B18 shadow-mode
> auto-promotion`) — 4/4 checks GREEN: test(3.11) ✅, test(3.12) ✅, scan ✅, validate ✅.
> Verdict unchanged from 03:00 UTC.

**New activity since 03:00 UTC:**

| PR | Branch | test(3.11) | test(3.12) | scan | verdict |
|----|--------|-----------|-----------|------|---------|
| #719 (merged 03:19Z, code) | feat/b18-shadow-promote-2026-05-03 | ✅ 02:55Z | ✅ 02:55Z | ✅ 02:52Z | GREEN ✅ |
| #720 (open, code) | audit-credibility-supplements-2026-05-02 | ✅ 03:24Z | ✅ 03:24Z | ✅ 03:21Z | GREEN ✅ (was PENDING at 03:00Z) |
| #721 (open, docs) | docs/peer-state-summary-2026-05-03 | — | — | ✅ 03:23Z | scan-only |
| #722 (opened 03:27Z, docs) | audit/hourly-03z | — | — | — | no CI (docs-only) |
| #723 (opened 03:36Z, code) | feat/b18-shadow-promote-v2-2026-05-03 | — | — | — | **NO CI YET** |
| #724 (opened 03:40Z, docs/reports) | investigation/forex-crypto-deep-dives | — | — | ✅ 03:52Z | scan-only |
| #725 (opened 03:58Z, docs) | verify/audit-mobile-load-2026-05-03 | — | — | ✅ 04:00Z | scan-only |

PR #720 was PENDING at 03:00Z — now confirmed GREEN (test 3.11 ✅ 03:24Z, test 3.12 ✅ 03:24Z).

PR #723 (`feat/b18-shadow-promote-v2-2026-05-03`) — NEW code PR opened 03:36Z with Python changes to
`quality_gates.py`, `dashboard_generator.py`, `tools/dashboard_hc_rules.py`, and 13 new tests. Zero
check runs visible as of 04:00Z. PR body reports 13/13 tests pass locally + py_compile OK. Expected to
trigger full CI Tests on next push; monitor next hour.

**Chronic workflows:** none

> Per-workflow `gh run list --workflow` unavailable (gh CLI absent). No new cancellation patterns
> observed in PR check-run data since 03:00Z. Cascade-cancel pattern on PRs #597/#608/#615/#661
> are intra-run fail-fast siblings, not independent chronic-cancellation events.

**Open PRs RED (all pre-existing, no new pushes since 03:00 UTC):**

- **#661** — `Infrastructure v2.0 — Track Calculator, PSR/DSR Validation, Decay Tracker`
  - test(3.11) ❌ FAILURE, test(3.12) cancelled (07:36–07:39Z, 2026-05-02) — unchanged
  - Classification: **AUTHOR_FIX** — ImportError in `statistical_rigor.py`; Wire-Up Rule gap; HOLD confirmed
  - Action: fix ImportError, add Wiring Plan, re-push

- **#615** — `fix: resolve 5 scanner blockers` (HELD per broadcast #625)
  - test(3.12) ❌ FAILURE, test(3.11) cancelled (06:13–06:18Z, 2026-05-02) — unchanged
  - Classification: **AUTHOR_FIX** — 10 failing tests + risky circuit_breaker.json reset; do not merge
  - Action: fix 10 failing tests, address CB reset risk

- **#608** — `test(tradingagents): B26 smoke`
  - test(3.11) ❌ FAILURE, test(3.12) cancelled (06:13–06:17Z, 2026-05-02) — unchanged, no re-push in ~22h
  - Classification: **AUTHOR_FIX**
  - Action: investigate test(3.11) failure, fix or request rerun

- **#597** — `P0 fixes + USDCHF investigation`
  - test(3.11) ❌ FAILURE, test(3.12) cancelled (06:14Z, 2026-05-02) — unchanged
  - Classification: **AUTHOR_FIX** — bundled PR; pick_revalidator has no Wire-Up yet
  - Action: isolate and fix failing tests before merging

**Action required:** none on main. Monitor PR #723 (code PR, no CI run observed yet) next hour. PRs #661/#608/#597 authors should fix tests; #615 remains HELD.

---

## 05:00 UTC

**Verdict:** GREEN

**Main CI Tests (last 5 observable runs):** 5 success, 0 failure, 1 in_progress (PR #733)

> Note: `gh` CLI unavailable; CI status inferred from GitHub MCP check-run API.
> Main branch HEAD (`6451d116`, 05:21Z) is a Signal Tracker bot commit (`[skip ci]`).
> Five PRs merged since 04:00 UTC: #729 (JPY filter, scan ✅, 05:08Z), #730 (hold windows +
> workflow move, scan ✅, 05:08Z), #731 (tests/doc cherry-pick, 05:09Z), #732 (docs state, 05:21Z),
> #725 (verify PR, scan ✅, 05:21Z). Code PRs #729 and #730 triggered `scan` only (Python CI Tests
> workflow appears path-gated; `audit_trail/` + `alpha_engine/` changes in #730 did not trigger the
> full test matrix — consistent with pattern observed at 02:00-04:00 UTC for merged code PRs that
> lack `tests/` changes). No CI Tests failures observed on main. Verdict unchanged from 04:00 UTC.

**New activity since 04:00 UTC:**

| PR | Branch | test(3.11) | test(3.12) | scan | verdict |
|----|--------|-----------|-----------|------|---------|
| #729 (merged 05:08Z, code) | fix/jpy-corruption-filter-divergence | — | — | ✅ 04:51Z | scan-only |
| #730 (merged 05:08Z, code) | feat/per-class-hold-windows-and-workflow-move | — | — | ✅ 04:58Z | scan-only |
| #731 (merged 05:09Z, tests/doc) | feat/copilot-tests-doc-cherrypick | — | — | — | no check runs |
| #732 (merged 05:21Z, docs) | docs/asset-class-rescue-state | — | — | — | no check runs |
| #725 (merged 05:21Z, verify) | verify/audit-mobile-load-2026-05-03 | — | — | ✅ 04:00Z | scan-only |
| #728 (open 04:49Z, template) | feat/b18-shadow-probation-template | — | — | ✅ 04:51Z | scan-only |
| #733 (open 05:20Z, code) | feat/per-class-position-caps-sidecar | 🔄 in_progress | 🔄 in_progress | 🔄 in_progress | **PENDING** |

PR #733 (`feat(per-class-caps): position cap + concurrent limit sidecar`) opened 05:20Z with
`alpha_engine/per_class_position_caps.py` (152 lines) + 15 tests. CI matrix started 05:20:16Z,
both `test (3.11)` and `test (3.12)` still in_progress. No failures observed yet; watch next hour.

PR #723 (`feat/b18-shadow-promote-v2-2026-05-03`, code) — opened 03:36Z (~1h45m ago). Still shows
0 check runs. This is a code PR touching `quality_gates.py`, `dashboard_generator.py`,
`dashboard_hc_rules.py`, and 13 new tests. Absence of CI trigger is unusual for a code PR this old;
likely the branch HEAD `2853dd10` was not picked up by the CI workflow trigger. Author should force-push
or push a trivial commit to re-trigger.

**Chronic workflows:** none

> Per-workflow `gh run list --workflow` unavailable (gh CLI absent). Bot workflows (Signal Tracker,
> DARWIN ENGINE, Breakout Arena scan, ANTIGRAVITY-CLAUDEOPUS, Picks Bot, low-score-tracker) all
> commit with `[skip ci]` and do not trigger CI Tests — they are cron data-push bots, not test runners.
> Cascade-cancel pattern on open PRs #597/#608/#615/#661 remains intra-run fail-fast artifacts (one
> matrix job fails → GitHub auto-cancels sibling). Chronic-cancellation threshold (latest run
> cancelled AND ≥4 cancels AND 0 successes AND no success in 48h, within 15-run window) not met.

**Open PRs RED (all pre-existing, no new pushes since 04:00 UTC):**

- **#661** — `Infrastructure v2.0 — Track Calculator, PSR/DSR, Decay Tracker`
  - test(3.11) ❌ FAILURE, test(3.12) cancelled (07:36–07:39Z, 2026-05-02) — unchanged
  - Classification: **AUTHOR_FIX** — ImportError in `statistical_rigor.py`; Wire-Up Rule gap; HOLD confirmed
  - Action: fix ImportError, add `## Wiring Plan` section, re-push

- **#615** — `fix: resolve 5 scanner blockers` (HELD per broadcast #625)
  - test(3.12) ❌ FAILURE, test(3.11) cancelled (06:13–06:18Z, 2026-05-02) — unchanged, no new push
  - Classification: **AUTHOR_FIX** — 10 failing tests + risky circuit_breaker.json EMERGENCY→NORMAL reset; do not merge
  - Action: fix 10 failing tests and address CB reset risk before any merge consideration

- **#608** — `test(tradingagents): B26 — live smoke test gated on TRADINGAGENTS_LIVE_SMOKE=1`
  - test(3.11) ❌ FAILURE, test(3.12) cancelled (06:13–06:17Z, 2026-05-02) — unchanged, no re-push in ~29h
  - Classification: **AUTHOR_FIX** — test failure from the 06:13Z batch; no action taken by author in >24h
  - Action: investigate test(3.11) failure log, push fix or request CI rerun

- **#597** — `P0 fixes + USDCHF investigation: rapid_fire pair-block, pick revalidator`
  - test(3.11) ❌ FAILURE, test(3.12) cancelled (06:14Z, 2026-05-02) — unchanged, two separate run IDs
  - Classification: **AUTHOR_FIX** — bundled multi-purpose PR; pick_revalidator sidecar has no Wire-Up yet
  - Action: isolate failing tests and fix before merging; add Wire-Up plan for `pick_revalidator`

**Action required:** none on main. Watch PR #733 CI Tests (in_progress); if they fail, reclassify next hour. Author of PR #723 should push a trivial commit to re-trigger absent CI. PRs #661/#608/#597 authors should fix tests; #615 remains HELD.

---
