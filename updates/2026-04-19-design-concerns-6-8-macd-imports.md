# Design Concern Fixes: #6, #8, MACD Imports — 2026-04-19

**Author:** Buffy (AI Code Review)  
**Branch:** `fix/design-concerns-6-8-macd-imports`  
**Scope:** Remaining design concerns from 2026-04-19 code review (items #6, #8, and minor MACD import fix)

---

## What Changed

Three fixes addressing design concerns identified in the 2026-04-19 code review that were not included in the earlier critical bugfix commits.

---

## 🟡 Design #6: Synthesized `fundingTime` was inaccurate

**Before:** `funding_rate_scanner.py` used `int(time.time() * 1000)` as `fundingTime` when the shared failover path succeeded. This is the **current wall-clock time**, not the actual funding settlement time (which settles every 8h at 00:00, 08:00, 16:00 UTC). Downstream code using `fundingTime` to predict the next funding event was misled.

**Fix:**
- Added `fetch_funding_entry(symbol)` to `crypto_data_failover.py` — returns `{fundingRate, fundingTime, source}` instead of just the decimal rate
- `fundingTime` is now the **8h-aligned settlement boundary** (most recent 00:00/08:00/16:00 UTC) via `_estimate_funding_time_ms()`, not wall-clock time
- Updated `failover_imports.py` to re-export `fetch_funding_entry`
- Updated `funding_rate_scanner.py` to use `fetch_funding_entry` instead of `fetch_funding_rate`

**Files modified:**
| File | Change |
|------|--------|
| `alpha_engine/crypto_data_failover.py` | Added `fetch_funding_entry()` + `_estimate_funding_time_ms()` |
| `alpha_engine/failover_imports.py` | Added `fetch_funding_entry` to re-exports |
| `alpha_engine/funding_rate_scanner.py` | Switched from `fetch_funding_rate` to `fetch_funding_entry` |

**Benefits:**
- `fundingTime` now accurately reflects the 8h-aligned settlement schedule
- Downstream prediction of next funding event works correctly
- Eliminates `int(time.time() * 1000)` approximation that could be up to 8h off

**Future enhancement:** Propagate the actual `fundingTime` from Binance's `/fapi/v1/fundingRate` response instead of approximating (noted by code reviewer).

---

## 🟡 Design #8: Half-open circuit breaker didn't fail-fast

**Before:** When a breaker exited cooldown (half-open state) and the next attempt failed, `record_failure` reset the failure counter to 1 (because `now - first_failure_ts > FAILURE_WINDOW_SECONDS`). This meant it took **3 more consecutive failures** to re-trip the breaker instead of 1, wasting HTTP round-trips on a source already known to be unreliable.

**Fix:** Modified `record_failure()` to detect `0 < open_until_ts <= now` (breaker cooldown just expired) and immediately set `count = fail_threshold`, re-opening the breaker on the **first** failure after cooldown.

No new state fields needed — uses the existing `open_until_ts` entry. Backward-compatible with existing `failover_circuit.json` files.

**Files modified:**
| File | Change |
|------|--------|
| `alpha_engine/crypto_data_failover.py` | Modified `record_failure()` with half-open fail-fast logic |

**Benefits:**
- Unreliable sources are re-blocked immediately after a failed half-open probe
- Saves 3 HTTP round-trips per breaker cycle on permanently-down sources
- On GHA runners where Binance is permanently geo-blocked, prevents 3 wasted Binance calls every 5 minutes

---

## 🟢 Minor: MACD strategy bare imports inconsistent with project pattern

**Before:** `macd_crossover_strategy.py` imported `from config import CRYPTO_SYMBOLS` and `from indicators import macd, rsi, atr, sma, volume_ratio` without try/except — inconsistent with the defensive import pattern used everywhere else in `alpha_engine`.

**Fix:**
- Wrapped imports in `try/except ImportError`
- Added `_HAS_INDICATORS` flag (matching `_HAS_SHARED_FAILOVER` pattern)
- Added early return `if not _HAS_INDICATORS: return []` in `macd_crossover()`

**Files modified:**
| File | Change |
|------|--------|
| `alpha_engine/macd_crossover_strategy.py` | Defensive imports + `_HAS_INDICATORS` guard |

**Benefits:**
- Consistent with project-wide defensive import pattern
- Prevents `ImportError` crash when indicators module unavailable
- Graceful degradation: returns empty signal list instead of crashing

---

## Tests Added

9 new tests in `tests/test_crypto_data_failover.py`:

| Class | Tests | Coverage |
|-------|-------|----------|
| `TestHalfOpenFailFast` | 4 | Half-open re-opens on 1st failure; cold start still needs 3; success resets; full cooldown duration |
| `TestFetchFundingEntry` | 5 | Returns dict with rate+time+source; 8h-aligned; not wall-clock; all-fail returns None; helper unit test |

**Total test count:** 63 (was 47 before this PR, 27 before earlier bugfixes)

---

## Validation

- All 5 modified Python files pass `py_compile` syntax check
- All 63 tests in `tests/test_crypto_data_failover.py` pass
- Code reviewer confirmed correctness (noted future enhancement for propagating actual Binance `fundingTime`)

---

## Not Yet Addressed (future PR)

- Propagate actual `fundingTime` from Binance's `/fapi/v1/fundingRate` response instead of approximating with 8h boundary
- Add integration test for `funding_rate_scanner.py` confirming 8h-aligned times through the scanner's synthesize path
