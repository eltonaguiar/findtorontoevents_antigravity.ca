# Code Review Bugfixes — 2026-04-19

**Reviewer:** Buffy (AI Code Review)
**Scope:** Fixes for 3 critical bugs + 4 design concerns from code review of latest commits + uncommitted changes.

---

## 🔴 Critical Bugs Fixed (3)

### 1. `macd_crossover_strategy.py` — ZeroDivisionError in R:R calculation
**Before:** `rr = (tp - price) / (price - sl)` crashes when `atr_val == 0` (flat market) causing `price == sl`.
**Fix:** Added two guards:
- `if atr_val <= 0: continue` — skip flat/no-range markets
- `if denom == 0: continue` — skip zero-risk entries (price == sl)

### 2. `crypto_data_failover.py` — 451/403 geo-block check was dead code
**Before:** `if code in (451, 403)` inside `urlopen` success path — unreachable because HTTP 4xx/5xx raises `HTTPError`.
**Fix:**
- Moved check into `except urllib.error.HTTPError` handler where it belongs
- Returns `_GEO_BLOCKED` sentinel instead of `None` so callers can distinguish "source is geo-blocked" from "source is down"
- Added `if data is _GEO_BLOCKED: return _GEO_BLOCKED` propagation in all 12 per-source fetchers
- `_try_source` now checks `if result is _GEO_BLOCKED` and skips `record_failure()` — geo-blocks no longer consume circuit-breaker budget

### 3. `crypto_data_failover.py` — Geo-blocked responses were tripping circuit breakers
**Root cause:** Per-source fetchers swallowed `_GEO_BLOCKED` by returning `None` when `isinstance(data, list)` failed, losing the sentinel before `_try_source` could see it.
**Fix:** All 12 fetchers now propagate `_GEO_BLOCKED` through to `_try_source` which skips breaker recording.

---

## 🟡 Design Concerns Fixed (4)

### 4. Triple duplicate import pattern across 3 files
**Before:** `funding_rate_scanner.py`, `winner_reverse_engineer.py`, `data_fetcher.py` each had identical dual try/except blocks.
**Fix:** Created `alpha_engine/failover_imports.py` — single centralized import point. All 3 consumers now import from it.

### 5. `data_fetcher.py` — `sys.path.insert(0, ...)` side effect
**Before:** Mutated global import path at module load time, potentially shadowing other packages.
**Fix:** Removed `sys.path.insert` — now uses `from alpha_engine.failover_imports import ...` which works without path manipulation.

### 6. `data_fetcher.py._ohlcv_shared` — zero-padding type mismatch
**Before:** Padded kline rows with integer `0`, but Binance schema uses strings.
**Fix:** Changed padding to string `"0"` for consistency.

### 7. `audit-dashboard.yml` — pathspec errors for missing files
**Before:** `git add "$f" 2>&1 || true` printed noisy pathspec errors for files like `funding_rate_picks.json` that don't exist every run.
**Fix:** Added `[ -f "$f" ] || continue` guard before `git add`.

---

## 🟢 Already Fixed / Verified

- `funding_rate_scanner.py` already has `import time` — Bug #1 from original review was already resolved.

---

## Files Modified

| File | Change |
|------|--------|
| `alpha_engine/macd_crossover_strategy.py` | Added `atr_val <= 0` and `denom == 0` guards |
| `alpha_engine/crypto_data_failover.py` | Fixed 451/403 handling + `_GEO_BLOCKED` sentinel + propagation in 12 fetchers |
| `alpha_engine/failover_imports.py` | **NEW** — centralized import module |
| `alpha_engine/funding_rate_scanner.py` | Updated to use `failover_imports.py` |
| `alpha_engine/winner_reverse_engineer.py` | Updated to use `failover_imports.py` |
| `crypto_signal_engine/data_fetcher.py` | Updated to use `failover_imports.py`, removed `sys.path.insert` |
| `.github/workflows/audit-dashboard.yml` | Added file-existence guard before `git add` |

---

## Validation

- All 6 modified Python files pass `py_compile` syntax check
- All 27 tests in `tests/test_crypto_data_failover.py` pass
- Code reviewer confirmed `_GEO_BLOCKED` sentinel propagation is correct and complete
