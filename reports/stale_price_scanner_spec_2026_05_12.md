# Stale-Price Detection Integration Spec (Fix #3 / xiao mi mimo)

## Executive Summary
**Objective:** Integrate `has_deterministic_loss_pattern()` feed hygiene check into `alpha_engine/scanner.py` pick-emission loop to prevent next-MATIC-style ghost trading (660+ rows of 0%-WR trades from stale rebrand price).

**Status:** Ready to implement. All dependencies verified.

---

## File Locations & Exports

### Feed Hygiene Module (`alpha_engine/feed_hygiene.py`)
✓ **exists** — verified at `E:\findtorontoevents_antigravity.ca\alpha_engine\feed_hygiene.py`

**Exported functions:**
- `has_deterministic_loss_pattern(symbol: str, recent_prices: list[float], threshold_stdev: float=0.01) → bool` — line 122
  - Returns `True` if feed is stale (stdev/mean < 1%)
  - Used to detect flat-price feeds (e.g., MATICUSDT stuck at 0.3794)
- `sanitize_active_picks()` — already imported at scanner.py:60
- `is_valid_active_pick()` — line 152 (downstream use only)

**Constants:**
- `_DEAD_SYMBOLS` frozenset — lines 103-119
  - Includes: `LUNAUSDT`, `USTUSDT`, `FTTUSDT`, `SRMUSDT`, `MATICUSDT`, `MATICUSD`
  - Used as hard-block; stale-price detector is soft-block

---

## Scanner Architecture

### Main Pick-Opening Loop
**Function:** `open_new_picks(signals: list[dict], db: SQLiteStore, market_data: dict | None, context: dict | None)` 
- **Location:** line 3504
- **Signal iteration:** line 3526 (`for signal in signals`)
- **Pick emission:** line 3660 (`db.open_pick(pick_dict)`)

### Data Availability: OHLCV (YES ✓)
Parameter `market_data: dict[str, pd.DataFrame]` passed at line 3505:
- **Current usage:** lines 3650-3657 (slippage/execution gap tracking)
- **Structure:** `market_data[symbol]` returns pd.DataFrame with columns `["Open", "High", "Low", "Close", "Volume"]`
- **Example:**
  ```python
  _mdf = market_data[signal["symbol"]]  # line 3651
  if _mdf is not None and not _mdf.empty and "Close" in _mdf.columns:
      market_price_at_signal = float(_mdf["Close"].iloc[-1])
  ```

### Recent Prices Construction
Extract last N close prices from available OHLCV:
```python
recent_closes = market_data[symbol]["Close"].iloc[-10:].tolist()  # last 10 bars
```

---

## Insertion Spec

### Location 1: Import Statement
**File:** `alpha_engine/scanner.py` — **line 60**

**Before:**
```python
try:
    from alpha_engine.feed_hygiene import sanitize_active_picks
except ImportError:
    sanitize_active_picks = lambda picks, label="": picks
```

**After:**
```python
try:
    from alpha_engine.feed_hygiene import sanitize_active_picks, has_deterministic_loss_pattern
except ImportError:
    sanitize_active_picks = lambda picks, label="": picks
    def has_deterministic_loss_pattern(_symbol, _prices, _thresh=0.01):
        return False  # fallback: allow all signals
```

---

### Location 2: Emission Gate (Stale-Price Check)
**File:** `alpha_engine/scanner.py` — **after line 3657, before line 3659**

**Insertion (20 lines):**
```python
        # Stale-price detection gate: reject symbols with deterministic loss pattern
        # (MATIC rebrand class incident prevention per Fix #3 + DEFINITIVE_FIX_PLAN:168-186)
        # Prevents emission of picks on feeds stuck at old rebrand price (e.g., MATICUSDT→POLUSDT)
        try:
            if market_data and signal["symbol"] in market_data:
                _price_df = market_data[signal["symbol"]]
                if _price_df is not None and not _price_df.empty and "Close" in _price_df.columns:
                    recent_closes = _price_df["Close"].iloc[-10:].tolist()  # last 10 bars
                    if has_deterministic_loss_pattern(signal["symbol"], recent_closes):
                        logger.warning(
                            "[stale_price_gate] Rejecting %s — deterministic loss pattern detected (stdev/mean < 1%% → stale feed)",
                            signal["symbol"]
                        )
                        continue  # Skip to next signal; do NOT emit pick
        except Exception as e:
            logger.debug("stale_price_gate exception on %s: %s", signal.get("symbol"), e)
            pass  # Fallthrough on malformed data; gate is soft-block
```

**Code context (lines 3650-3670):**
```python
3650        if market_data and signal["symbol"] in market_data:
3651            _mdf = market_data[signal["symbol"]]
3652            if _mdf is not None and not _mdf.empty and "Close" in _mdf.columns:
3653                market_price_at_signal = float(_mdf["Close"].iloc[-1])
3654                if market_price_at_signal > 0 and entry_price > 0:
3655                    slippage_pct = round(
3656                        abs(entry_price - market_price_at_signal) / market_price_at_signal * 100, 4
3657                    )
3658
3659        # Open pick with cost-adjusted TP and risk-based allocation
3660        pick_id = db.open_pick({
```

→ **NEW CODE GOES BETWEEN 3657-3659**

---

## Validation Checklist

- [x] `feed_hygiene.py` exists and exports `has_deterministic_loss_pattern`
- [x] Function signature matches usage: `has_deterministic_loss_pattern(symbol, recent_prices, threshold_stdev=0.01) → bool`
- [x] Scanner has `market_data: dict[str, pd.DataFrame]` available at emission point
- [x] OHLCV structure confirmed: `market_data[symbol]["Close"].iloc[-N:].tolist()` works
- [x] `sanitize_active_picks` already imported (import statement half-wired)
- [x] Insertion point identified: line 3657-3659 (after slippage calc, before pick.open)
- [x] Exception handling follows existing scanner patterns (try/except fallthrough)
- [x] No new external dependencies required

---

## Test Case (Synthetic MATICUSDT)
1. Feed stale OHLCV with Close = [0.3794, 0.3794, 0.3794, ..., 0.3794] (10 bars)
2. Scanner processes signal for MATICUSDT with entry_price=0.3794
3. `has_deterministic_loss_pattern("MATICUSDT", [0.3794]*10)` → `True` (stdev/mean ≈ 0)
4. Gate logs warning, skips signal (continues to next)
5. No pick emitted → no ghost trade

---

## Risk Mitigation
- **Fallback import:** If feed_hygiene unavailable, returns `False` (allows all signals)
- **Soft block:** Exception handling allows malformed data to pass through
- **Threshold tuning:** Default 1% stdev/mean threshold catches 100%-flat feeds; configurable via `threshold_stdev` param if false positives emerge
- **Scope:** Only blocks signal BEFORE `db.open_pick()` — no database corruption
- **Logs:** All rejections logged with symbol + reason for audit trail

---

## References
- **DEFINITIVE_FIX_PLAN 2026-05-12, lines 168-186**
- **Project Memory:** `project_confidence_rho_matic_artifact.md` (660 MATIC 0%-WR ghost rows)
- **Historical Context:** `docs/ANALYSIS_TRADING_FORENSIC_2026_04_18.md` (889 MATICUSDT deterministic losses)
