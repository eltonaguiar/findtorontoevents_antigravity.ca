# Fix: Audit Dashboard JS Errors + GHA Cancellation

**Date:** 2026-04-19
**Author:** Buffy (Codebuff Agent)
**Status:** Implemented, pending PR review

---

## Problem

Three JavaScript errors were found on the live audit dashboard at findtorontoevents.ca/audit/:

1. **`SyntaxError: Unexpected identifier 'Neal'`** — Unescaped single quote in "O'Neal" inside a single-quoted JS string literal broke parsing of the entire `<script>` block, causing all subsequent function definitions (including `init()`) to fail.
2. **`ReferenceError: el is not defined`** — Two `const el` variable declarations shadowed the `el()` helper function, causing variable confusion in the same scope.
3. **`ReferenceError: init is not defined`** — This was a **cascade effect** from error #1. When the O'Neal syntax error broke script parsing, no functions in that block were defined, so every subsequent call failed. Not a separate root cause.

Additionally, the **Copy Trader Forward Test** GitHub Actions workflow had `cancel-in-progress: true`, causing 100% cancellation of runs that were mid-push when a new run triggered.

## Fixes

### 1. O'Neal apostrophe escape (root cause of errors 1 & 3)

Replaced `O'Neal` with `O\u0027Neal` (unicode escape) in `audit_dashboard/template.html`. This prevents the single quote from breaking the JS string literal and allows the entire `<script>` block to parse correctly.

### 2. Variable shadowing fix (defensive improvement, not root cause)

Renamed two `const el` declarations that shadowed the `el()` helper function:
- `const el = document.getElementById('price-refresh-countdown')` → `const countdownEl`
- `const el = document.getElementById('perf-alerts-container')` → `const alertsEl`

Also fixed 6 accidentally corrupted `leverageLabel.innerHTML` references that were hit by an overly broad `el.innerHTML` → `alertsEl.innerHTML` replacement (now corrected back to `leverageLabel`).

### 3. setTimeout init() guard (defensive improvement)

Added `typeof init === "function"` guard to the `setTimeout(function() { init(); }, 0)` call. While the O'Neal fix is the real root cause, this guard prevents a similar cascade if any future syntax error breaks script parsing.

```js
// Before:
setTimeout(function() { init(); }, 0);

// After:
setTimeout(function() { if (typeof init === "function") init(); else console.warn("[Audit] init() not yet defined, deferring..."); }, 0);
```

### 4. GHA cancel-in-progress fix

Changed `cancel-in-progress: true` → `cancel-in-progress: false` in `.github/workflows/copy-trader-forward-test.yml`. Same pattern that caused 100% cancellation in the Consensus Outcome Tracker (PR #239).

## Verification

- Browser-use agent tested the live dashboard after fixes (will be verified on next CI deploy)
- `py_compile` syntax check passes on all modified Python files
- Code reviewer confirmed the O'Neal fix is the root cause; the other changes are defensive improvements

## Files Changed

| File | Change |
|------|--------|
| `audit_dashboard/template.html` | O'Neal unicode escape, countdownEl/alertsEl rename, init typeof guard |
| `.github/workflows/copy-trader-forward-test.yml` | cancel-in-progress: true → false |
