# Peer Progress Check — 2026-05-02

**Produced by:** Zero (operator watchdog session)  
**Generated:** 2026-05-02 ~01:30 UTC  
**Scope:** Five peer agents started ~2026-05-01T23:16Z (A/B/C) and ~2026-05-02T00:26/00:50Z (D/E)  
**Instruction:** Report only — do NOT merge or close anything.

---

## 1. PRs Opened During the Session Window

| PR | Title | State | Created (UTC) | CI |
|----|-------|-------|---------------|----|
| #601 | feat(audit): B17 — HC button audit + after-cost shadow gate | **OPEN** | 2026-05-01 23:37Z | not retrieved |
| #603 | test(events-homepage): restore React #418 allowlist | MERGED | 2026-05-01 23:44Z | — |
| #604 | fix(events-homepage): show actual JUNE date on Next Month cards | MERGED | 2026-05-01 23:55Z | — |
| #605 | Disable Alpha Suite Daily Refresh (PHP 404s) + Fix CI Tests | MERGED | 2026-05-02 00:08Z | ✅ all pass |
| #606 | Fix outcome_resolver + quality_gates for FOREX/COMMODITY | MERGED | 2026-05-02 00:18Z | n/a (tiny patch) |
| #607 | docs: tier performance audit + suggested fixes (Copilot, DRAFT) | **OPEN** | 2026-05-02 00:39Z | — |
| #608 | test(tradingagents): B26 — live smoke test gated on TRADINGAGENTS_LIVE | **OPEN** | 2026-05-02 00:40Z | not retrieved |
| #609 | fix: outcome_resolver retry loop + per-asset-class filter calibration | **OPEN** | 2026-05-02 00:44Z | ❌ FAILING |

PRs #603 and #604 are events-homepage fixes — outside the scope of any of the five target peers. They were from concurrent unrelated sessions.

---

## 2. Per-Peer Status

### Peer A — Freebuff (GH Actions failures + asset-class data gaps)

**Status: CRASHED after shipping.**

**Shipped artifact: PR #605 (MERGED ✅, CI green)**

Scope match is exact: PR #605 title = "Disable Alpha Suite Daily Refresh (PHP 404s) + Fix CI Tests". The PR covers:
- `alpha-suite-daily-refresh.yml`: curl retry/error handling added
- `TORONTOEVENTS_ANTIGRAVITY/index.html`: staleness filter added (fixes `test_events_staleness_filter`)
- `tests/test_quan_engine_concurrency_cap.py`: kill-list mocks added (fixes `test_quan_engine_concurrency_cap`)
- `tools/hc_parity_test.py`: tolerance threshold MAX_DIVERGENT=10
- `alpha_engine/isolated_signal_integrator.py`: asset class normalized to lowercase

Both pre-existing known CI failures (`test_events_staleness_filter`, `test_quan_engine_concurrency_cap`) are addressed. PR was merged and CI passed (test 3.11 ✅, test 3.12 ✅, scan ✅).

**Also likely contributed to PR #606 (MERGED):** 4-line surgical resolver fix — adds `asset_class` field to resolved picks and trusts WON/LOST when TP/SL unset (addresses FOREX FORCE_CLOSED mis-tagging). This is a valid, independent bug distinct from the Opus 4.7-documented v2 bugs.

---

### Peer B — opencode/Big Pickle (first session, same scope as A)

**Status: STUCK — no shipped artifact.**

No PR opened. Per description, blocked on PowerShell shim. The scope (GH Actions + CI fixes) was already covered by Peer A's PR #605 before B could push. There is nothing to close or review. If B attempts to push the same fixes now, that PR will be a **true duplicate** of #605 — reject on sight.

---

### Peer C — opencode/deepseek (branch `fix/alpha-suite-gha-404`)

**Status: CRASHED TWICE — no shipped artifact.**

Branch `fix/alpha-suite-gha-404` was **not found** across 250+ remote branches (5 pages of 50 checked). The branch was never pushed, or was pushed and subsequently deleted. Either way there is no open PR and nothing to close or review.

The reported pathology (Chinese SPAM characters in YAML line 35) would have injected junk bytes into a workflow file. If that branch had been pushed and a PR opened, the `scan` check would have flagged it (the scan job checks workflow YAML syntax). No downstream damage.

**No action required for Peer C.**

---

### Peer D — Big Pickle (performance edge audit, started ~2026-05-02T00:26Z)

**Status: ACTIVE — two open PRs.**

**Shipped artifacts:**
- **PR #601 (OPEN):** `feat(audit): B17 — HC button audit + after-cost shadow gate`  
  Branch `feat/b17-hc-after-cost-gate-2026-05-01`, session `session_01TVT13HfpY7KjipAGs22Q7N`.  
  +856 additions, 10 files changed. Adds `stamp_after_cost_fields()` in `dashboard_generator._normalize_pick()`, shadow HC gate `passes_hc_after_cost()` behind `HC_AFTER_COST_GATE_ENABLED=1` env flag, and an "Honest Read" toolbar popup.  
  **Wire-Up Rule:** ✅ (production `_normalize_pick()` path is the caller).  
  **Gate change rule:** ✅ (shadow flag present, 14-day shadow design documented).  
  **Blocker:** CI status not retrieved — needs check before merge.

- **PR #608 (OPEN):** `test(tradingagents): B26 — live smoke test gated on TRADINGAGENTS_LIVE_SMOKE=1`  
  Branch `feat/b26-tradingagents-smoke-2026-05-02`, session `session_01TNYXQiaiU9knUQEcHHwCig`.  
  Test-only PR. Unconditionally skipped in CI (no live flag in workflow env). Prerequisite B24 and B25 already merged. Wire-Up Rule: ✅ (test file only, no new integration module). Looks clean.

*(Note: PR #601 was created at 23:37Z which is before D's stated start of 00:26Z. Likely explanation: the operator's "20:26 ET" note is approximate, or D's session was already running. The session URL is unique to this PR and does not appear in any other PR.)*

---

### Peer E — Claude Opus 4.7 Kimi-review (resolver bug review, started ~2026-05-02T00:50Z)

**Status: ACTIVE — one open PR with CI failures.**

**Shipped artifact: PR #609 (OPEN, ❌ CI FAILING)**

Branch `fix/resolver-and-filters-2026-05-02`, created 00:44Z (6 minutes before E's stated start of 00:50Z — timing is approximate; attribution is either D or E). The PR directly addresses the five bugs identified in the Opus 4.7 review:

| Bug | Location | Addressed in #609? |
|-----|----------|--------------------|
| Empty `ohlc_window=[]` falls through to live-spot | line 608 | ✅ Yes — adds empty-list check with MAX_RESOLVE_RETRIES cap |
| RESOLVE_FAILED_BREAKEVEN infinite retry loop | lines 624-674 | ✅ Yes — adds MAX_RESOLVE_RETRIES=3, sets status="FLAT" on max-retry |
| yfinance no timeout | line 317 | ✅ Yes — adds `timeout=15` |
| Entry-day lookahead bias | lines 351-353 | ✅ Yes — excludes entry-day bar for intraday entries |
| Zombie TTL (no expiry on active non-crypto) | lines 1908-1917 | ❌ Not addressed |

**VALID work — not a re-application of v2.** PR #606 (already merged) touched different bugs (normalize_exit_reason, asset_class field). There is no overlap.

---

## 3. Duplicate Analysis

| PR pair | Verdict |
|---------|---------|
| #605 vs #606 | Not duplicates — different files, different bugs |
| #606 vs #609 (resolver PRs) | **Not duplicates** — #606 fixes quality_gates normalize_exit_reason and asset_class field; #609 fixes retry loop, empty-window, timeout, lookahead. Distinct bugs. |
| Any v2 re-application risk in #609? | **No** — #609 does not attempt to replace v2 resolver logic; it patches bugs within v2 |
| Peer A (#605) vs Peer B (no PR) | Potential future duplicate if B pushes now — reject on sight |

**No PRs to close on duplicate grounds.** Both resolver PRs target orthogonal bugs.

---

## 4. Rule Violations

### PR #609 — FOUR violations requiring fixes before merge

1. **hc_filter.js gate changes without 14-day shadow** (HIGH)  
   WR floor thresholds lowered live: `forwardWRMinPctCrypto` 70→55, `forwardWRMinPctEquity` 70→50, `forwardWRMinPctForex` 70→55, `forexRelaxedWRMinPct` 65→50. Per CLAUDE.md these are MEDIUM-risk gate changes requiring default-OFF env flag + 14-day shadow before flip. None of these changes are behind a flag — they go live on merge.  
   **Fix:** Move behind `HC_WR_FLOOR_CALIBRATION_ENABLED` env flag OR split to a separate PR with proper shadow design.

2. **FOREX_BANNED_SYMBOLS clearance without investigation doc** (MEDIUM)  
   `FOREX_BANNED_SYMBOLS = frozenset()` removes the ban on AUDUSD=X, CADJPY=X, EURJPY=X, EURUSD=X. The PR body argues the 0% WR was the resolver bug, not bad alpha — that may well be true, but per CLAUDE.md §7 ("Do not expand BLOCKED_SOURCE_SYSTEMS without STRATEGY_INVESTIGATION_BEFORE_KILL.md"), a gate removal requires the investigation doc. No such doc is referenced.  
   **Fix:** Either generate `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` for the FOREX ban or move the clearance to a follow-up PR after v2 data accumulates.

3. **CI failing — test(3.11) FAILURE + hc-parity FAILURE** (BLOCKER)  
   Both jobs failed on the PR's head commit. The test(3.11) failure is not the pre-existing staleness/concurrency failures (PR #605 fixed those). This is a new regression introduced by the PR's changes.  
   **Fix:** Investigate and fix the failing tests before merge.

4. **PR bundles 4 unrelated concerns** (LOW — quality)  
   Resolver bug fixes (#1–4 from the documented list) + HC filter gate calibration + FOREX ban removal + hf_quality_gates.json edit. Per "small, surgical changes" guidance these should be at minimum two PRs: (a) pure resolver bug fixes, (b) gate calibrations.

### PR #607 (Copilot DRAFT)

- **From Copilot SWE agent, not one of the five peers** — informational only.
- The "Direction=BUY vs LONG label-routing bug (P0)" is an important finding: 28.9% WR for BUY-tagged picks vs 54.9% WR for LONG-tagged (n=3909 vs 441). If correct, this is a production scoring bug worth triaging.
- The "cap confidence at ≤0.90" is already reflected by `confidenceMax: 0.90` in hc_filter.js — no new code needed there.
- Docs-only PR, no rule violations.

---

## 5. Current Main CI State

Main branch (after PRs #603–#606 merged):
- `test (3.11)` from PR #605 merge: ✅ passed
- `test (3.12)` from PR #605 merge: ✅ passed  
- `scan` from PR #605 merge: ✅ passed

Pre-existing failures per CLAUDE.md (`test_events_staleness_filter`, `test_quan_engine_concurrency_cap`) were **fixed by PR #605** — confirmed by CI passing on that PR.

PR #609 (branch, not yet merged) currently shows:
- `hc-parity`: ❌ FAILURE (00:44–00:46Z)
- `test (3.11)`: ❌ FAILURE (00:44–00:48Z)
- `test (3.12)`: cancelled
- `scan`: ✅ success
- `drift`: ✅ success

---

## 6. Operator Watchouts (Confirmed)

### CONFIRMED: Stale `PR_BODY.md` on disk
File `./PR_BODY.md` exists at repo root, dated **2026-04-25 06:31 UTC**. Content is "Policy v3 upgrade with 12 config-flagged features" — an old session artifact. **Must not be committed or pushed.** Add to `.gitignore` or delete.

### CONFIRMED: `hf_quality_gates.json` `enabled: false` — NOT a real blocker
The file has `"enabled": false` at the top level. PR #609 changes `min_elite_score` from 80 to 30 inside this file, but since the gate is disabled, this has zero production effect. Any PR claiming to "fix" the `hf_quality_gates.json` `enabled: false` field should be ignored.

### NOT YET VERIFIED: GH PAT `github_pat_11AJHZIL...`
Operator should rotate this PAT immediately if it appeared in peer session dumps/logs. No PAT was found in any PR body reviewed here, but the exposure may have been in local session output.

---

## 7. Recommendations (for operator review on wake)

| Action | Priority | Target |
|--------|----------|--------|
| Fix CI failures in PR #609 (test 3.11 + hc-parity) before any merge decision | P0 | Peer D/E |
| Split PR #609: pure resolver fixes (bugs #1–4) into PR A; gate calibrations into PR B behind shadow flag | P1 | Peer D/E |
| Add STRATEGY_INVESTIGATION_BEFORE_KILL.md before clearing FOREX_BANNED_SYMBOLS | P1 | Peer D/E |
| Review and merge PR #608 (B26 smoke test) — clean, test-only | P2 | Peer D |
| Review PR #601 (B17 HC after-cost gate) CI status; shadow design is correct | P2 | Peer D |
| Rotate GH PAT `github_pat_11AJHZIL...` | P0 | Operator |
| Delete or gitignore `./PR_BODY.md` | P1 | Operator |
| Address zombie TTL bug (lines 1908-1917) — not covered in any current PR | P2 | Next session |

---

## 8. Resolver PR Classification Summary

Per the CRITICAL CORRECTION in the watchout brief:

| PR | Type | Verdict |
|----|------|---------|
| #606 (MERGED) | Fixes quality_gates + asset_class field — different from the 5 documented bugs | **VALID**, already merged |
| #609 (OPEN) | Fixes documented bugs #1–4 (empty-ohlc, retry loop, timeout, lookahead) | **VALID follow-up, not duplicate** — needs CI fix + gate changes behind shadow flag before merge |

No PR attempts to re-apply v2 (the "DUPLICATE, close" case). Both resolver PRs address distinct bugs on top of an already-deployed v2 resolver.
