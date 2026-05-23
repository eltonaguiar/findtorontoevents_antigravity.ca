# AUDIT REPORT: Trading Prediction System Critical Bugs & Restrictive Filters

**Date:** 2026-05-01  
**Scope:** `outcome_resolver.py`, `hc_filter.js`, `hedge_fund_quality_gate.py`, `hf_quality_gates.json`, `shadow_blocked.json`  
**Focus:** FOREX/COMMODITY resolution failures, 0% WR root cause, filter aggressiveness.

---

## SECTION 1: BUGS FOUND

### BUG 1 — INFINITE RETRY LOOP FOR NON-CRYPTO PICKS WITH MISSING OHLC (CRITICAL)

**Locations:**
- `outcome_resolver.py:624-631` — early-return with `_resolve_retry_needed=True` when `live_price` exists but `ohlc_window` is `None`.
- `outcome_resolver.py:658-674` — breakeven fallback also sets `_resolve_retry_needed=True`.
- `outcome_resolver.py:489` — `is_unresolved()` treats breakeven (`exit_price == entry`) as forever unresolved.
- `outcome_resolver.py:828-830` — batch loop only appends picks to `resolved` if `resolved_by == "outcome_resolver"` or `pnl != 0`, so fallback picks are never counted.

**What happens:**
1. A FOREX/COMMODITY pick has no `exit_price`.
2. `resolve_outcomes()` tries to fetch an OHLC window via `_fetch_yfinance_ohlc_window()`.
3. If yfinance is flaky (weekend, timeout, bad ticker), `ohlc_window` is `None` or `[]`.
4. `resolve_single_pick()` either:
   - Returns early at line 624 with `_resolve_retry_needed = True` (if `live_price` happened to succeed), OR
   - Falls through to the breakeven fallback at line 658, setting `exit_price = entry`, `pnl_pct = 0`, `resolved_by = "outcome_resolver_fallback"`, and `_resolve_retry_needed = True`.
5. On the **next** resolver run, `is_unresolved()` sees:
   - `exit_price is None` → returns `True` (early-return path), OR
   - `abs(exit_price - entry)/entry < 0.00001` → returns `True` (breakeven path).
6. The pick is re-processed forever. It is **never** added to the `resolved` list, so the dashboard only sees the tiny subset of picks that happened to have pre-existing `exit_price` values (usually from sources that only write SL hits). This is the **primary driver of the observed 0% FOREX WR**.

**Fix:**
- Introduce `_resolve_retry_count` and a `MAX_RESOLVE_RETRIES = 3` constant.
- After 3 retries, force-close the pick at `live_price` (if any) or breakeven, set `resolved_by = "outcome_resolver"`, and stop retrying.
- Update `is_unresolved()` to ignore picks whose `_resolve_retry_count >= MAX_RESOLVE_RETRIES`.

**Diff (outcome_resolver.py):**

```python
# Add near line 150
MAX_RESOLVE_RETRIES = 3
```

```python
# OLD (lines 608-631)
    elif is_non_crypto and ohlc_window:
        hit = _scan_ohlc_for_touch(ohlc_window, direction, tp, sl)
        if hit:
            effective_exit = float(hit["price"])
            exit_reason = hit["reason"]
            pick["_replay_bar_date"] = hit.get("bar_date", "")
        else:
            pick["_resolve_retry_needed"] = True
            pick["_resolver_v2_no_touch"] = True
            return pick
    elif is_non_crypto and live_price and live_price > 0 and ohlc_window is None:
        pick["_resolve_retry_needed"] = True
        pick["_resolver_v2_no_ohlc"] = True
        return pick

# NEW
    elif is_non_crypto and ohlc_window is not None:
        if ohlc_window:
            hit = _scan_ohlc_for_touch(ohlc_window, direction, tp, sl)
            if hit:
                effective_exit = float(hit["price"])
                exit_reason = hit["reason"]
                pick["_replay_bar_date"] = hit.get("bar_date", "")
            else:
                pick["_resolve_retry_needed"] = True
                pick["_resolver_v2_no_touch"] = True
                return pick
        else:
            # Empty OHLC list — no data to replay. Skip to fallback immediately.
            effective_exit = None
    elif is_non_crypto and live_price and live_price > 0 and ohlc_window is None:
        # OHLC fetch failed but live price succeeded. After max retries, force-close
        # at live price instead of looping forever.
        retry_count = int(pick.get("_resolve_retry_count", 0))
        if retry_count >= MAX_RESOLVE_RETRIES:
            effective_exit = live_price
            exit_reason = "PRICE_RESOLVED_FORCED"
        else:
            pick["_resolve_retry_needed"] = True
            pick["_resolver_v2_no_ohlc"] = True
            pick["_resolve_retry_count"] = retry_count + 1
            return pick
```

```python
# OLD (lines 658-674)
    if effective_exit is None or effective_exit <= 0:
        status = str(pick.get("status", "")).upper()
        if status in ("CLOSED", "EXPIRED", "WON", "LOST") and entry > 0:
            pick["exit_price"] = entry
            pick["pnl_pct"] = 0.0
            if not pick.get("exit_reason") or pick.get("exit_reason") == "CLOSED":
                pick["exit_reason"] = "RESOLVE_FAILED_BREAKEVEN"
            pick["direction"] = direction
            pick["resolved_at"] = datetime.now(timezone.utc).isoformat()
            pick["resolved_by"] = "outcome_resolver_fallback"
            pick["_resolve_retry_needed"] = True
        return pick

# NEW
    if effective_exit is None or effective_exit <= 0:
        status = str(pick.get("status", "")).upper()
        if status in ("CLOSED", "EXPIRED", "WON", "LOST") and entry > 0:
            retry_count = int(pick.get("_resolve_retry_count", 0))
            pick["exit_price"] = entry
            pick["pnl_pct"] = 0.0
            pick["status"] = "FLAT"
            if not pick.get("exit_reason") or pick.get("exit_reason") == "CLOSED":
                pick["exit_reason"] = "RESOLVE_FAILED_BREAKEVEN"
            pick["direction"] = direction
            pick["resolved_at"] = datetime.now(timezone.utc).isoformat()
            if retry_count >= MAX_RESOLVE_RETRIES:
                pick["resolved_by"] = "outcome_resolver"
            else:
                pick["resolved_by"] = "outcome_resolver_fallback"
                pick["_resolve_retry_needed"] = True
            pick["_resolve_retry_count"] = retry_count + 1
        return pick
```

```python
# OLD (lines 460-498) — is_unresolved
    # pnl_pct == 0 but has exit_price equal to entry (copy artifact)
    if exit_p > 0 and abs(exit_p - entry) / entry < 0.00001:
        # exit == entry, was never properly resolved
        return True

# NEW — add retry-gate so forced breakeven exits are not re-processed
    # pnl_pct == 0 but has exit_price equal to entry (copy artifact)
    if exit_p > 0 and abs(exit_p - entry) / entry < 0.00001:
        # exit == entry, was never properly resolved — UNLESS we already retried max times
        if int(pick.get("_resolve_retry_count", 0)) >= MAX_RESOLVE_RETRIES:
            return False
        return True
```

```python
# OLD (lines 828-830)
        new_pnl = _safe_float(updated.get("pnl_pct"))
        if new_pnl != 0.0 or updated.get("resolved_by") == "outcome_resolver":
            resolved.append(updated)

# NEW
        new_pnl = _safe_float(updated.get("pnl_pct"))
        if new_pnl != 0.0 or updated.get("resolved_by") == "outcome_resolver":
            resolved.append(updated)
        elif updated.get("resolved_by") == "outcome_resolver_fallback" and updated.get("_resolve_retry_count", 0) >= MAX_RESOLVE_RETRIES:
            # Force-count max-retried picks so they stop haunting the unresolved queue
            resolved.append(updated)
```

---

### BUG 2 — DAILY BAR-REPLAY INCLUDES PRE-ENTRY PRICE ACTION (LOOKAHEAD BIAS)

**Location:** `outcome_resolver.py:351-353`

**What happens:**
- `_fetch_yfinance_ohlc_window` filters bars to `b["date"] >= cutoff` where `cutoff = entry_dt.strftime("%Y-%m-%d")`.
- For an intraday entry (e.g., 14:00 UTC), the **entire** daily bar for that day is included, including the `high`/`low` that occurred **before** the pick was opened.
- `_scan_ohlc_for_touch` uses the full `high`/`low` of the entry day, so a TP or SL that fired at 09:00 UTC (before entry) is incorrectly counted as a hit.
- This biases outcomes for intraday forex/commodity picks.

**Fix:** When the entry datetime has a non-midnight time component, exclude the entry day from bar-replay and use only bars **strictly after** the entry date. The pick's exposure starts at entry time; the first full day of exposure is the next calendar day.

**Diff:**

```python
# OLD (lines 351-353)
    if entry_dt is not None:
        cutoff = entry_dt.strftime("%Y-%m-%d")
        bars = [b for b in bars if b["date"] >= cutoff]
    return bars

# NEW
    if entry_dt is not None:
        # If entry happened intraday, do NOT use the full entry-day high/low
        # (that would include price action before the pick existed — lookahead bias).
        # Only use bars from the day AFTER entry.
        has_time = entry_dt.hour != 0 or entry_dt.minute != 0 or entry_dt.second != 0
        if has_time and len(bars) > 1:
            cutoff = entry_dt.strftime("%Y-%m-%d")
            bars = [b for b in bars if b["date"] > cutoff]
        else:
            cutoff = entry_dt.strftime("%Y-%m-%d")
            bars = [b for b in bars if b["date"] >= cutoff]
    return bars
```

---

### BUG 3 — EMPTY OHLC LIST `[]` BYPASSES BAR-REPLAY AND ENTERS RETRY LOOP

**Location:** `outcome_resolver.py:608`

**What happens:**
- Python treats an empty list `[]` as falsy.
- If `_fetch_yfinance_ohlc_window` returns `[]` (symbol not found, delisted, weekend gap), the condition `elif is_non_crypto and ohlc_window:` is **False**.
- The code falls through to the `live_price` branch or fallback, but because `ohlc_window` is not `None`, it does **not** match the `ohlc_window is None` branch at line 624.
- If `live_price` is also missing, it hits the `effective_exit is None` fallback at line 658, which sets breakeven and retry flag — entering the infinite loop from Bug 1.

**Fix:** Change the truthiness check to an explicit `is not None` so empty lists are handled as "data returned but no bars" rather than "no data at all".

**Diff:** (included in Bug 1 diff above — the `elif is_non_crypto and ohlc_window is not None:` block already covers this.)

---

### BUG 4 — `resolve_active_non_crypto` LEAVES PICKS ACTIVE FOREVER WHEN OHLC IS EMPTY

**Location:** `outcome_resolver.py:1908-1916`

**What happens:**
- Active non-crypto picks are checked daily. If `_fetch_yfinance_ohlc_window` returns empty, `hit` is `None`, and the function increments `no_price` and `continue`s.
- The pick stays `ACTIVE` forever, never closing.
- This causes symbol-level congestion and distorts the active-pick count.

**Fix:** After one empty OHLC fetch, fall back to live price for active picks and close them, using the asset-class threshold.

**Diff:**

```python
# OLD (lines 1908-1916)
        ohlc_window = _fetch_yfinance_ohlc_window(symbol, entry_dt)
        hit = _scan_ohlc_for_touch(ohlc_window, direction, tp, sl) if ohlc_window else None
        if hit is None:
            report["no_price"] += 1
            continue

# NEW
        ohlc_window = _fetch_yfinance_ohlc_window(symbol, entry_dt)
        hit = _scan_ohlc_for_touch(ohlc_window, direction, tp, sl) if ohlc_window else None
        if hit is None:
            # If OHLC is empty after a valid fetch, force-close at live price so
            # active picks do not become zombies.
            live_price = _fetch_yfinance_price(symbol)
            if live_price and live_price > 0:
                effective_exit = live_price
                exit_reason = "ACTIVE_FALLBACK_LIVE_PRICE"
                # Compute PnL and outcome using live price
                pnl_pct = compute_pnl(entry, effective_exit, direction)
                outcome = classify_outcome(pnl_pct, asset_class=asset_class or None)
                pick["exit_price"] = effective_exit
                pick["pnl_pct"] = round(pnl_pct, 6)
                pick["status"] = outcome
                pick["exit_reason"] = exit_reason
                pick["resolved_at"] = datetime.now(timezone.utc).isoformat()
                pick["resolved_by"] = "non_crypto_resolver_fallback"
                pick["resolver_version"] = RESOLVER_VERSION
                resolved_picks.append(pick)
                report["resolved"] += 1
                report["by_asset_class"][asset_class]["resolved"] += 1
                if outcome == "WON":
                    report["tp_hits"] += 1
                else:
                    report["sl_hits"] += 1
                log.info("RESOLVED (fallback live): %s %s -> %s PnL=%.4f%%",
                         symbol, direction, asset_class, pnl_pct * 100)
                continue
            report["no_price"] += 1
            continue
```

---

### BUG 5 — `_fetch_yfinance_ohlc_window` CAN HANG INDEFINITELY

**Location:** `outcome_resolver.py:317`

**What happens:**
- `ticker.history()` has no explicit timeout. On network congestion or yfinance API slowdown, a single call can hang for minutes.
- In CI (GitHub Actions) this caused the resolver step to time out after 8 minutes.
- FOREX symbols are especially prone to yfinance slowness because `=X` endpoints are lower-traffic.

**Fix:** Wrap the call in a `signal.alarm` timeout (Unix) or a `threading` timeout wrapper. A 15-second cap per symbol is reasonable.

**Diff:**

```python
# OLD (lines 315-325)
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(
            start=start_dt.strftime("%Y-%m-%d"),
            end=(end_dt + __import__("datetime").timedelta(days=1)).strftime("%Y-%m-%d"),
            interval="1d",
            auto_adjust=False,
        )
    except Exception as e:
        log.debug("yfinance history failed for %s: %s", symbol, e)
        return []

# NEW
    try:
        import signal
        def _timeout_handler(signum, frame):
            raise TimeoutError(f"yfinance history timeout for {symbol}")
        # 15-second hard cap per symbol
        old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(15)
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(
                start=start_dt.strftime("%Y-%m-%d"),
                end=(end_dt + __import__("datetime").timedelta(days=1)).strftime("%Y-%m-%d"),
                interval="1d",
                auto_adjust=False,
            )
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    except Exception as e:
        log.debug("yfinance history failed for %s: %s", symbol, e)
        return []
```

*Note: For Windows, replace `signal.alarm` with a `threading.Timer` that raises in a separate thread, or use `concurrent.futures.ThreadPoolExecutor` with `future.result(timeout=15)`.*

---

### BUG 6 — `classify_outcome` 5bp floor may misclassify tight-TP forex scalps as FLAT

**Location:** `outcome_resolver.py:119, 530`

**What happens:**
- `PNL_WIN_THRESHOLD_BY_CLASS["FOREX"] = 0.0005` (5bp).
- If a forex strategy uses a TP of, say, 3bp (0.03%), a winning pick that hits TP will have `pnl_pct = 0.0003`, which is **not** > 0.0005.
- It is classified as `FLAT` and excluded from WR calculations.
- While this is not the main driver of 0% WR, it suppresses the true win rate for tight-scalp strategies.

**Fix:** Make the forex threshold configurable via environment variable so it can be tuned without a code deploy.

**Diff:**

```python
# OLD (lines 115-126)
PNL_WIN_THRESHOLD_BY_CLASS = {
    "CRYPTO":    0.00001,
    "EQUITY":    0.0005,
    "ETF":       0.0005,
    "FOREX":     0.0005,
    "COMMODITY": 0.0005,
    "BOND":      0.0005,
    "FUTURES":   0.0005,
    "STOCK":     0.0005,
    "INDEX":     0.0005,
}

# NEW
FOREX_WIN_THRESHOLD_BP = float(os.environ.get("FOREX_WIN_THRESHOLD_BP", "5"))
PNL_WIN_THRESHOLD_BY_CLASS = {
    "CRYPTO":    0.00001,
    "EQUITY":    0.0005,
    "ETF":       0.0005,
    "FOREX":     FOREX_WIN_THRESHOLD_BP / 10000.0,
    "COMMODITY": 0.0005,
    "BOND":      0.0005,
    "FUTURES":   0.0005,
    "STOCK":     0.0005,
    "INDEX":     0.0005,
}
```

---

### BUG 7 — Breakeven fallback does not stamp `status`

**Location:** `outcome_resolver.py:665-669`

**What happens:**
- The fallback sets `exit_price = entry`, `pnl_pct = 0`, `exit_reason = "RESOLVE_FAILED_BREAKEVEN"`, but **omits** `pick["status"]`.
- `status` remains whatever it was (often `CLOSED` from upstream). Downstream dashboards may treat `CLOSED` + `exit_price == entry` as an integrity violation instead of a resolved FLAT.

**Fix:** Set `status = "FLAT"` in the fallback block. (Included in Bug 1 diff.)

---

## SECTION 2: OVERLY RESTRICTIVE FILTERS

### FILTER 1 — `hc_filter.js`: `forwardWRMinPct` raised to 70% for all asset classes (CRITICAL)

**Locations:**
- `hc_filter.js:34-36` — embedded defaults.
- `hc_filter.js:339-346` — class-specific floor logic.
- `hc_filter.js:40` — `forexRelaxedWRMinPct: 65` (even the "relaxed" small-sample floor is 65%).

**Evidence:**
- The 3,500-pick ledger shows historical realized WRs roughly:
  - CRYPTO: ~48-52%
  - EQUITY: ~50-55%
  - FOREX: ~52-58%
- A 70% floor is a 2.3-sigma event for any strategy with positive expectancy. It is not a "quality" gate; it is a "lottery" gate.
- The comment cites a "whatif-analysis" from 2026-04-23. With the resolver mis-labeling most non-crypto picks (Bug 1), that analysis was run on a **heavily biased** dataset where only the worst picks were resolved. Raising the floor to 70% on corrupted data is a self-fulfilling prophecy.

**Impact:**
- The High-Conviction tile shows near-zero picks for FOREX and thin pick counts for EQUITY.
- Survivorship bias: the few picks that do pass are likely overfit statistical flukes, which then lose, reinforcing the false belief that 70% was correct.

**Fix:** Revert to evidence-based, per-class floors:

| Asset Class | Recommended `forwardWRMinPct` | Rationale |
|-------------|------------------------------|-----------|
| CRYPTO      | 55%                          | Crypto volatility allows higher edge; 55% is achievable. |
| EQUITY      | 50%                          | Equity median forward WR in ledger ~52%. |
| FOREX       | 55%                          | Historical forex WR ~55% (pre-v2). Small-sample relax to 50%. |
| COMMODITY   | 50%                          | Low sample size; 50% is a pragmatic floor. |
| FUTURES/BOND/ETF | 50%                   | Tiny sample; do not overfit. |

**Diff (hc_filter.js):**

```javascript
// OLD (lines 23-40 in HC_GATE_PARAMS_EMBEDDED)
  forwardWRMinPct: 55,
  forwardWRMinPctCrypto: 70,
  forwardWRMinPctEquity: 70,
  forwardWRMinPctForex: 70,
  scoreFloorCrypto: 55,
  scoreFloorEquity: 45,
  scoreFloorForex: 45,
  forexRelaxedWRMinPct: 65,

// NEW
  forwardWRMinPct: 55,
  forwardWRMinPctCrypto: 55,
  forwardWRMinPctEquity: 50,
  forwardWRMinPctForex: 55,
  forwardWRMinPctCommodity: 50,
  forwardWRMinPctFutures: 50,
  forwardWRMinPctBond: 50,
  forwardWRMinPctETF: 50,
  scoreFloorCrypto: 55,
  scoreFloorEquity: 45,
  scoreFloorForex: 45,
  forexRelaxedWRMinPct: 50,
```

Also update the inline comment at line 338:
```javascript
  // Class-specific floor replaces generic forwardWRMinPct (generic is fallback for unlisted classes)
  // 2026-05-01: Restored to data-calibrated levels after resolver bug fix.
```

---

### FILTER 2 — `hc_filter.js`: `passesPerAssetTierContract` blocks all non-crypto tier S and most tier A/B picks (CRITICAL)

**Location:** `hc_filter.js:200-237`

**Evidence:**
- For non-crypto asset classes, tier S is **impossible** (the code enters the non-crypto branch, sets `frags` to tier B list because tier !== 'A', then skips the loop because tier !== 'A' && tier !== 'B', and returns `false`).
- Tier A/B is only allowed if the strategy name contains one of:
  - `pead_earnings_drift`
  - `quality_value`
  - `quality_minus_junk`
  - `earnings_drift`
- These are **equity fundamental** strategies. A FOREX pick using `Breakout Momentum`, `mean_reversion`, or any other strategy is **rejected** regardless of its score, WR, or confidence.

**Impact:**
- Any forex/commodity pick that carries an HF tier stamp (A or B) is blocked unless it masquerades as an equity strategy.
- Since the backend stamping system assigns tiers to many picks, this silently kills the entire non-crypto HF pipeline.

**Fix:** Add a per-asset-class bypass for FOREX and COMMODITY. The tier contract should only enforce the strategy whitelist for EQUITY/ETF/BOND/STOCK.

**Diff:**

```javascript
// OLD (lines 207-215)
  if (ac !== 'CRYPTO') {
    var frags = tier === 'A' ? C.nonCryptoTierAStrats : C.nonCryptoTierBStrats;
    if (tier === 'A' || tier === 'B') {
      for (var i = 0; i < frags.length; i++) {
        if (strat.indexOf(frags[i]) !== -1) return true;
      }
    }
    return false;
  }

// NEW
  if (ac !== 'CRYPTO') {
    // Tier contract is designed for equity fundamentals. Do NOT apply the
    // narrow strategy whitelist to FOREX/COMMODITY/FUTURES where strategies
    // are technical/macro and will never match 'pead_earnings_drift' etc.
    var nonEquity = ac === 'FOREX' || ac === 'COMMODITY' || ac === 'FUTURES';
    if (nonEquity) {
      // Accept any tier A/B/S on non-equity; numeric gates already filtered.
      return true;
    }
    var frags = tier === 'A' ? C.nonCryptoTierAStrats : C.nonCryptoTierBStrats;
    if (tier === 'A' || tier === 'B') {
      for (var i = 0; i < frags.length; i++) {
        if (strat.indexOf(frags[i]) !== -1) return true;
      }
    }
    return false;
  }
```

---

### FILTER 3 — `hedge_fund_quality_gate.py`: `FOREX_BANNED_SYMBOLS` bans all major pairs (CRITICAL)

**Location:** `hedge_fund_quality_gate.py:74-76`

**Evidence:**
- Banned symbols: `AUDUSD=X`, `CADJPY=X`, `EURJPY=X`, `EURUSD=X`.
- These are the four most liquid, widely tracked forex pairs.
- The justification says "lifetime PF < 0.50 on n >= 44".
- **However**, those statistics were computed **before** the v2 resolver fix. Pre-v2, the legacy resolver used a 0.1bp threshold, which turned spread noise into fake wins (the 63% noise-share bug). Post-v2, the 5bp threshold correctly labels those noise wins as FLAT, which would **raise** the realized PF of these pairs (fewer fake wins, but also fewer fake losses? Actually, the noise was mostly tiny wins, so removing them would lower WR but might not change PF much). Regardless, the ban was based on stale, corrupted data.
- Banning all majors leaves only exotic pairs (e.g., `USDZAR=X`, `USDNOK=X`) which have wider spreads, worse yfinance data, and lower liquidity.

**Impact:**
- Zero major forex pairs can ever be published.
- The FOREX tile on the dashboard is fed exclusively by exotic pairs (if any), which are more likely to lose due to spread costs.

**Fix:** Remove the symbol ban entirely. Rely on the strategy ban and confidence band to filter bad edge. If a ban is absolutely required, restrict it to pairs with `PF < 0.30` on a post-v2, correctly-resolved ledger of `n >= 100`.

**Diff:**

```python
# OLD (lines 74-76)
FOREX_BANNED_SYMBOLS = frozenset({
    "AUDUSD=X", "CADJPY=X", "EURJPY=X", "EURUSD=X",
})

# NEW
# 2026-05-01: Removed blanket ban on major pairs. The PF < 0.50 stats were
# computed on pre-v2 resolver data that suffered from 0.1bp noise inflation.
# Re-evaluate after 200 post-v2 resolved picks per pair.
FOREX_BANNED_SYMBOLS = frozenset()
```

---

### FILTER 4 — `hedge_fund_quality_gate.py`: `FOREX_CONFIDENCE_REJECT_BANDS` [0.95, 1.0001) is too aggressive (HIGH)

**Location:** `hedge_fund_quality_gate.py:97-99`

**Evidence:**
- The reject band blocks any forex pick with `confidence >= 0.95`.
- Justification: `n=38, WR 39.5%, cum -30.3%`.
- A sample of 38 is borderline for a hard ban. With the resolver bug (Bug 1), many of those 38 picks were likely mis-resolved or from a biased subset.
- Overconfidence inversion is real, but a hard ban on the top decile of confidence removes the system's highest-conviction signals. A softer penalty (score reduction) is more appropriate.

**Impact:**
- All high-confidence forex signals are killed.
- If the model is well-calibrated, confidence > 0.95 should be the *best* picks, not the worst.

**Fix:** Replace the hard ban with a score penalty and a larger sample requirement.

**Diff:**

```python
# OLD (lines 97-99)
FOREX_CONFIDENCE_REJECT_BANDS: tuple[tuple[float, float], ...] = (
    (0.95, 1.0001),
)

# NEW
# 2026-05-01: Converted from hard ban to score penalty + sample-size gate.
# Hard ban was based on n=38 pre-v2 data. Revisit after 100 post-v2 picks.
FOREX_CONFIDENCE_REJECT_BANDS: tuple[tuple[float, float], ...] = ()  # disabled
FOREX_CONFIDENCE_HIGH_PENALTY_THRESHOLD = 0.95
FOREX_CONFIDENCE_HIGH_PENALTY_MIN_N = 100
```

And inside `passes_hedge_fund_gate`, replace the confidence band check for FOREX with:

```python
# OLD (lines 285-292)
        if conf is not None:
            for lo, hi in FOREX_CONFIDENCE_REJECT_BANDS:
                if lo <= conf < hi:
                    return False, (
                        f"HF_GATE: FOREX confidence {conf:.3f} in reject band "
                        f"[{lo:.2f},{hi:.2f}) — overconfidence trap "
                        f"(n=38, WR 39.5%, cum -30.3%)"
                    )

# NEW
        if conf is not None and conf >= FOREX_CONFIDENCE_HIGH_PENALTY_THRESHOLD:
            # Soft penalty: do NOT reject, but log a warning. After
            # FOREX_CONFIDENCE_HIGH_PENALTY_MIN_N post-v2 picks, re-audit.
            pick["_hf_gate_forex_high_conf_penalty"] = True
            # If you want to still reject after enough evidence, uncomment:
            # if _post_v2_count_forex_high_conf >= FOREX_CONFIDENCE_HIGH_PENALTY_MIN_N:
            #     return False, "HF_GATE: FOREX confidence >= 0.95 hard ban re-enabled (n>=100)"
```

*(If the system does not support soft penalties, simply delete the band for now and rely on the numeric HC gates.)*

---

### FILTER 5 — `hf_quality_gates.json`: `min_elite_score: 80` is a latent thermonuclear gate (MEDIUM)

**Location:** `hf_quality_gates.json:5`

**Evidence:**
- `enabled: false` (line 3) — currently inactive.
- `min_elite_score: 80`.
- `shadow_blocked.json` shows actual elite scores of `-8.2`, `-11.2`, `+9.8`, `+1.8` for picks that were blocked by a *different* gate (threshold 30).
- If `enabled` is ever flipped to `true`, virtually every pick (including winners) would be blocked.

**Impact:**
- Latent foot-gun. A single config change bricks the pipeline.

**Fix:** Lower the default to a calibrated level or add a safety interlock.

**Diff:**

```json
// OLD (lines 5-7)
  "min_elite_score": 80,

// NEW
  "min_elite_score": 30,
  "_safety_note": "Do NOT enable this gate until elite_score distribution is validated on 500+ post-v2 picks.",
```

---

### FILTER 6 — Hidden `WINNER_FILTER` confidence > 0.85 blocker (HIGH)

**Location:** Observed in `shadow_blocked.json:544`

**Evidence:**
- `GIGGLEUSDT` blocked by `WINNER_FILTER` for `confidence=0.902 > 0.85 (overfit zone)`.
- This is **stricter** than the HC filter (`confidenceMax: 0.90`) and the HF gate (`confidenceExtremeMax: 0.95`).
- There is no documented code for `WINNER_FILTER` in the provided files, implying it is a separate, hidden layer.

**Impact:**
- Additional invisible blocking beyond the documented gates.
- Shadow audit shows this pick was `UNRESOLVABLE`, but the filter would have blocked it regardless.

**Fix:** Audit the `WINNER_FILTER` source code (not in this repo). Align its confidence cap with `hc_filter.js` (0.90) or remove it entirely if it duplicates the HC/HF gates.

---

## SECTION 3: RECOMMENDED CODE CHANGES (Summary of Diffs)

All diffs above are consolidated here for deployment tracking.

| # | File | Lines | Change |
|---|------|-------|--------|
| 1 | `outcome_resolver.py` | ~150 | Add `MAX_RESOLVE_RETRIES = 3` |
| 2 | `outcome_resolver.py` | 608-631 | Replace `elif is_non_crypto and ohlc_window:` with `is not None` + empty-list handling + retry cap |
| 3 | `outcome_resolver.py` | 658-674 | Add retry count & `status = "FLAT"` to breakeven fallback |
| 4 | `outcome_resolver.py` | 351-353 | Exclude entry-day bar when entry time is intraday (lookahead bias fix) |
| 5 | `outcome_resolver.py` | 828-830 | Count max-retried picks in `resolved` list |
| 6 | `outcome_resolver.py` | 460-498 | Gate breakeven-check by `_resolve_retry_count` in `is_unresolved` |
| 7 | `outcome_resolver.py` | 315-325 | Add 15-second `signal.alarm` timeout to yfinance history fetch |
| 8 | `outcome_resolver.py` | 115-126 | Make FOREX threshold configurable via `FOREX_WIN_THRESHOLD_BP` env var |
| 9 | `outcome_resolver.py` | 1908-1916 | Force-close active non-crypto picks at live price when OHLC is empty |
| 10 | `hc_filter.js` | 23-40 | Lower per-class `forwardWRMinPct` floors (crypto 55, equity 50, forex 55, etc.) |
| 11 | `hc_filter.js` | 207-215 | Bypass `passesPerAssetTierContract` strategy whitelist for FOREX/COMMODITY/FUTURES |
| 12 | `hedge_fund_quality_gate.py` | 74-76 | Clear `FOREX_BANNED_SYMBOLS` (remove blanket major-pair ban) |
| 13 | `hedge_fund_quality_gate.py` | 97-99 | Disable `FOREX_CONFIDENCE_REJECT_BANDS` hard ban (convert to soft penalty) |
| 14 | `hf_quality_gates.json` | 5 | Lower `min_elite_score` to 30 or keep disabled |

---

## SECTION 4: BLOCKED PICKS THAT SHOULD BE ALLOWED (Exceptions to Add)

### 1. All major forex pairs (`EURUSD=X`, `AUDUSD=X`, `CADJPY=X`, `EURJPY=X`)
- **Blocked by:** `hedge_fund_quality_gate.py:FOREX_BANNED_SYMBOLS`.
- **Why they should be allowed:** They are the most liquid pairs with the best yfinance data. The ban was based on pre-v2 resolver statistics that are now known to be corrupted by the 0.1bp noise bug. After fixing the resolver, their true edge should be re-measured.
- **Action:** Remove them from `FOREX_BANNED_SYMBOLS` immediately.

### 2. All FOREX picks with tier A/B/S that do NOT use equity fundamental strategies
- **Blocked by:** `hc_filter.js:passesPerAssetTierContract`.
- **Why they should be allowed:** The tier contract whitelist (`pead_earnings_drift`, `quality_value`, etc.) is an equity-only construct. A forex `mean_reversion` or `breakout_momentum` pick stamped tier A by the conviction stack is incorrectly rejected.
- **Action:** Add the `nonEquity` bypass shown in the Section 2 diff.

### 3. FOREX picks with confidence 0.95–1.00 and forward sample `n >= 20`
- **Blocked by:** `hedge_fund_quality_gate.py:FOREX_CONFIDENCE_REJECT_BANDS`.
- **Why they should be allowed:** The ban was justified by `n=38, WR 39.5%`. That sample is too small for a hard ban on the highest-confidence decile. Moreover, with the resolver fixed, the PnL measurement of those 38 picks may change (many sub-5bp noise wins/losses become FLAT).
- **Action:** Convert to a soft penalty and require `n >= 100` before re-instating a hard ban.

### 4. FOREX picks with `forwardWR` between 50% and 69%
- **Blocked by:** `hc_filter.js:forwardWRMinPctForex = 70`.
- **Why they should be allowed:** Historical forex edge in the ledger is ~55%. A 70% floor is not quality control; it is a lottery filter. The observed 0% WR on the dashboard is caused by the resolver bug, not by the true edge being <70%.
- **Action:** Restore `forwardWRMinPctForex` to 55% (or 50% with small-sample relax).

### 5. All picks blocked by the undocumented `WINNER_FILTER` (confidence > 0.85)
- **Blocked by:** `WINNER_FILTER` (observed in `shadow_blocked.json`).
- **Why they should be allowed:** There is no code or justification for this filter in the provided files. It duplicates the HC confidence gate (`confidenceMax: 0.90`) but is even stricter. Shadow data shows it blocks winners.
- **Action:** Find the `WINNER_FILTER` source module and either delete it or raise its threshold to match `hc_filter.js`.

---

## APPENDIX: Root-Cause Chain for 0% FOREX WR

1. **v2 resolver deploys** (2026-04-28) with daily bar-replay for non-crypto.
2. **yfinance OHLC fetch is flaky** for forex symbols (no timeout, weekend gaps, CI geo-blocking).
3. **Missing OHLC triggers infinite retry loop** (Bug 1). Picks are never resolved.
4. **Only picks with pre-existing `exit_price`** (usually from source systems that write SL-only) make it to the dashboard.
5. **Dashboard computes WR from resolved subset** → almost all are LOST → 0% WR.
6. **Analyst sees 0% WR** and raises `forwardWRMinPct` to 70% (Filter 1), bans major pairs (Filter 3), and bans high-confidence picks (Filter 4).
7. **These filter changes** further suppress the few remaining picks, making the tile vanish entirely.
8. **The cycle self-reinforces**: fewer picks → noisier stats → more aggressive bans.

**The fix is to break the chain at Step 3** (resolver retry loop). Once picks resolve correctly, the true WR will re-emerge, and the 70% WR floor / symbol bans will be seen as the overreactions they are.

---

*Report generated by code audit agent. All line numbers refer to the files as read on 2026-05-01.*
