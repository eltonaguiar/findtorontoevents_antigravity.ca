# Code Review: Latest Commits + Uncommitted Changes — 2026-04-19

**Reviewer:** Buffy (AI Code Review)
**Scope:** Commits `56fcc73`..`3a9d8d1` + uncommitted changes in 6 files + 2 new files

---

## 🔴 Critical Bugs (3)

### 1. `funding_rate_scanner.py` — Missing `import time` (Runtime `NameError`)
The new code uses `int(time.time() * 1000)` to synthesize the `fundingTime` field, but the file only imports from `datetime`, not `time`. This will crash with a `NameError` whenever the shared failover path succeeds.

**Fix:** Add `import time` to the file's top-level imports.

### 2. `macd_crossover_strategy.py` — `ZeroDivisionError` in R:R calculation
```python
rr = (tp - price) / (price - sl)  # BUY
rr = (price - tp) / (sl - price)  # SELL
```
If `atr_val == 0` (flat/new crypto listings), then `tp == price == sl`, causing `ZeroDivisionError`. There is no guard for `atr_val == 0` or `price == sl`.

**Fix:** Add `if atr_val <= 0: continue` before the R:R calculation, or wrap in a try/except.

### 3. `crypto_data_failover.py` — 451/403 geo-block check is dead code
```python
with urllib.request.urlopen(req, timeout=timeout) as resp:
    code = resp.getcode()
    if code in (451, 403):  # ← UNREACHABLE: 4xx/5xx raise HTTPError
```
HTTP 451/403 raise `urllib.error.HTTPError` and are caught by the `except` block below, returning `None`. The docstring says "no retry" for geo-blocks, but geo-blocked responses **will trip the circuit breaker** as regular failures — 3 geo-blocks → breaker opens → 5 min cooldown → retry → geo-blocked again → loop.

**Fix:** In the `except urllib.error.HTTPError` handler, check `exc.code in (451, 403)` and return a sentinel or skip `record_failure()` so geo-blocks don't consume circuit breaker budget.

---

## 🟡 Design / Architecture Concerns (4)

### 4. Triple duplicate import pattern across 3 files
`funding_rate_scanner.py`, `winner_reverse_engineer.py`, and `data_fetcher.py` each have identical dual `try/except ImportError` blocks importing from `crypto_data_failover`. If the module path changes, all three must be updated independently.

**Recommendation:** Create a single `alpha_engine/failover_imports.py` that re-exports the functions and sets the `_HAS_SHARED_FAILOVER` flag once.

### 5. `data_fetcher.py` — `sys.path.insert(0, ...)` side effect
```python
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
```
This mutates the global import path at module load time, potentially shadowing other packages. The other two consumers use `alpha_engine.`-prefixed imports instead.

**Recommendation:** Use the same `alpha_engine.`-prefixed import pattern as the other two files, or use the proposed `failover_imports.py`.

### 6. Synthesized `fundingTime` is inaccurate
In `funding_rate_scanner.py`, the shared failover path sets `"fundingTime": int(time.time() * 1000)` — this is the **current wall-clock time**, not the actual funding settlement time. Downstream code using `fundingTime` to predict the next funding event will be misled.

**Recommendation:** If possible, propagate the actual funding timestamp from the failover source; or document that this field is approximate when `_source == "shared_failover"`.

### 7. `data_fetcher.py._ohlcv_shared` pads klines with zeros
Padding non-Binance kline rows to 12 columns with `0` means `quote_volume`, `trade_count`, `taker_base_vol`, `taker_quote_vol` are always zero. Downstream volume analysis could produce incorrect results silently.

**Recommendation:** Document that these fields are unavailable from non-Binance sources, or use `None`/`"NaN"` instead of `0` so downstream code can distinguish "missing" from "zero volume."

---

## 🟡 Circuit Breaker Subtlety

### 8. Half-open state doesn't "fail fast"
When a breaker exits cooldown and the next attempt fails (half-open), `record_failure` finds `now - first_ts > FAILURE_WINDOW_SECONDS` and resets the counter to 1. This means it takes **3 more consecutive failures** to re-trip the breaker instead of failing fast on 1. Not broken, but less protective than typical circuit breaker patterns.

**Recommendation:** In `record_failure`, if the source was recently open (e.g., `open_until_ts` just expired), immediately re-open the breaker on the first failure.

---

## 🟡 Test Coverage Gaps

| Gap | Priority |
|-----|----------|
| No test for `_http_get_json` 451/403 geo-block handling (broken as noted in Bug #3) | High |
| **No tests for `macd_crossover_strategy.py` at all** | High |
| No tests for integration points (`_HAS_SHARED_FAILOVER` flag paths in the 3 consumer files) | Medium |
| No test for `_coingecko_throttle` rate-limiting behavior | Low |
| No test for `fetch_funding_rate` with Bybit as the succeeding source | Low |

---

## ✅ Committed Changes — All Look Correct

| Commit | Change | Verdict |
|--------|--------|---------|
| `56fcc73` | `production_scanner.py` gate0c fix: `rr_ratio == 0` now correctly rejected | ✅ Correct — `is not None` + `< 0.6` evaluates to `True` for 0 |
| `3a9d8d1` | `institutional_metrics.py` adds `main()` wrapper | ✅ Correct fix for `ImportError` |
| `3a9d8d1` | `quick-guess-ml.yml` sets `cancel-in-progress: false` | ✅ Correct — prevents chronic CI cancellation |
| Auto/data commits | Trading cycles, signal tracking, market beating | ✅ Data/log updates only, no code issues |

---

## 🟢 Minor / Style

- `macd_crossover_strategy.py` imports `from config import CRYPTO_SYMBOLS` and `from indicators import macd, rsi, atr, sma, volume_ratio` without `try/except` — inconsistent with the project's defensive import pattern used everywhere else for `alpha_engine` submodules.
- `_smart_round` in `macd_crossover_strategy.py` is defined locally but looks like it could be a shared utility (similar rounding helpers likely exist elsewhere in the codebase).

---

## Summary

| Severity | Count | Action Required |
|----------|-------|-----------------|
| 🔴 Critical | 3 | Must fix before next production run |
| 🟡 Design | 4 + 1 | Should fix; technical debt accumulating |
| 🟡 Test gaps | 5 | Should add, especially MACD strategy |
| 🟢 Minor | 2 | Nice to have |
| ✅ Correct | 4 commits | No action needed |
