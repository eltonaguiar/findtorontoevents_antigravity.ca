# 48h Change Review and Remediation (2026-05-02)

## Scope
- Reviewed `main` branch changes from the last 48 hours.
- Prioritized substantive runtime logic changes over high-frequency bot/data churn.
- Implemented targeted remediations for risks with direct production impact.

## Methodology
1. **Window evidence collection**
   - Enumerated 48h `main` commits and changed files.
   - Grouped churn by directory and file to isolate generated artifacts from logic edits.
2. **Risk-focused review**
   - Inspected high-impact diffs in resolver/gating/homepage hydration paths.
   - Classified issues by runtime blast radius (batch stalls, silent CI masking, policy mismatch).
3. **Minimal, warranted fixes**
   - Applied smallest safe code deltas to close each proven gap.
   - Added regression tests where behavior previously lacked an executable guard.
4. **Proof-first verification**
   - Ran targeted pytest/Playwright commands.
   - Recorded pass/fail evidence and environment blockers.

## 48h Evidence Snapshot
- Commits in window: ~3.7k (`git log main --since="48 hours ago"`).
- Unique files touched: ~1.1k.
- Churn dominated by generated data artifacts (e.g., `alpha_engine/data/*.json`, prediction-market sync outputs), not hand-authored logic.
- Substantive risk files identified:
  - `alpha_engine/outcome_resolver.py`
  - `audit_trail/quality_gates.py`
  - `TORONTOEVENTS_ANTIGRAVITY/index.html`
  - `tests/test_outcome_resolver_v21_bugfixes.py`
  - `tests/test_quality_gates.py`

## Findings, Fixes, and Justification

### 1) Resolver timeout path could still stall batch execution
**Risk:** `future.result(timeout=...)` inside `ThreadPoolExecutor` context still risks blocking on context-manager shutdown after timeout.  
**Why warranted:** A timeout guard that can still block defeats the anti-stall objective for outcome resolution batches.  
**Fix applied:**
- Reworked `_fetch_yfinance_ohlc_window()` in `alpha_engine/outcome_resolver.py`:
  - explicit executor lifecycle,
  - `future.cancel()` on timeout,
  - non-blocking `shutdown(wait=False, cancel_futures=True)` on timeout/error,
  - normal blocking shutdown only on completed-success path.
**Proof:**
- Added regression test `test_bug1d_timeout_returns_quickly_when_history_hangs` in `tests/test_outcome_resolver_v21_bugfixes.py`.
- Command:
  - `python -m pytest tests/test_outcome_resolver_v21_bugfixes.py -k "bug1d" -vv`
- Result:
  - `3 passed, 7 deselected`
  - New timeout-hang test passes in ~1.5s with a forced 4s fake `history()` call.

### 2) Pair exception carve-out policy and implementation diverged
**Risk:** Carve-out behavior contradicted its own contract:
- active gate bypassed hard blocks (too broad),
- smart gate failed to bypass some declared floors (too narrow/inconsistent).
**Why warranted:** Inconsistent gating semantics make model governance non-deterministic and invalidate written policy assumptions.
**Fix applied:**
- `audit_trail/quality_gates.py` updated so carve-out semantics are explicit and consistent:
  - **Does bypass:** score floors, R:R floor, forward-WR floors.
  - **Does not bypass:** hard blocklists and catastrophic gates.
- Removed active-gate early `return True` before hard-block checks.
- Applied carve-out conditionals to documented floor checks in active/smart paths.
- Added/updated B19 tests in `tests/test_quality_gates.py`:
  - hard blocks remain non-bypassable,
  - documented floors are bypassed when carve-out is active.
**Proof:**
- Command:
  - `python -m pytest tests/test_quality_gates.py -k "b19_carve_out" -q`
- Result:
  - `7 passed, 47 deselected`

### 3) Hydration masking remained vulnerable to pre-hydration timer injections
**Risk:** Static promo injector still had unconditional `window.load` timer chain (`100/500/1000/2000ms`) that can race hydration and reintroduce React #418 mismatch conditions.
**Why warranted:** The timer chain directly undermines hydration-safe gating (`__whenReactHydrated__`) and weakens CI signal reliability.
**Fix applied:**
- `TORONTOEVENTS_ANTIGRAVITY/index.html`:
  - removed unconditional load-time reinjection timer chain,
  - introduced `_runWhenHydrated(cb)` wrapper that:
    - uses `window.__whenReactHydrated__` when available,
    - waits briefly for helper declaration if script order differs,
    - only uses conservative load-settled fallback if helper never appears.
**Proof / current limitation:**
- Attempted strict hydration test:
  - `npx playwright test --config=playwright.next-month.config.ts tests/events_next_month_filter.spec.ts --project="Desktop Chrome" -g "React #418 hydration mismatch"`
- Local environment result:
  - test timed out waiting for homepage hydration path (`__eventInNextMonth__` readiness path did not complete in local setup).
- This is an execution-environment limitation for local homepage hydration validation, not a compile/lint failure in modified code.

## Verification Commands Executed
- `python -m pytest tests/test_outcome_resolver_v21_bugfixes.py -k "bug1d" -vv`
- `python -m pytest tests/test_quality_gates.py -k "b19_carve_out" -q`
- `npx playwright test --config=playwright.next-month.config.ts tests/events_next_month_filter.spec.ts --project="Desktop Chrome" -g "React #418 hydration mismatch"` (environment-limited timeout)
- Lint diagnostics on edited files via IDE lints: no new lint errors.

## Residual Risk and Follow-ups
- Hydration regression needs a deterministic runtime lane (prefer remote verification target or local bundle parity) to fully close #418 validation loop.
- Given the volume of 48h bot commits, periodic differential review should continue to focus on hand-authored logic paths and policy-bearing modules.

## Files Changed in This Remediation
- `alpha_engine/outcome_resolver.py`
- `audit_trail/quality_gates.py`
- `tests/test_outcome_resolver_v21_bugfixes.py`
- `tests/test_quality_gates.py`
- `TORONTOEVENTS_ANTIGRAVITY/index.html`
