# Code Duplication Audit — Asset-Class Normalization

**Date:** 2026-04-10  
**Scope:** `alpha_engine/smart_picks_engine.py` + `alpha_engine/conviction_stack.py`  
**Issue:** Duplicated, inconsistent asset-class detection logic spread across two files with divergent behavior.

---

## 1. Inventory of Asset-Class Normalization Functions

### File A: `smart_picks_engine.py`

| Function/Constant | Line(s) | Purpose |
|---|---|---|
| `_normalized_asset_class(pick)` | ~230–265 | **Primary normalizer.** Returns one of: `crypto`, `forex`, `etf`, `bond`, `futures`, `equity`. Checks symbol suffixes (`=F`, `=X`), stablecoin endings, 6-char forex pair detection, ETF/EQUITY symbol sets, source/strategy hints, then category fallback. |
| `_is_non_crypto(pick)` | ~274 | Trivial wrapper: `_normalized_asset_class(pick) != "crypto"` |
| `FOREX_CODES` | ~118 | Set of 19 ISO currency codes (`EUR`, `GBP`, `USD`, `JPY`, …) |
| `ETF_SYMBOLS` | ~123 | Set of 20 known ETF ticker symbols (`SPY`, `QQQ`, `GLD`, …) |
| `EQUITY_SYMBOLS` | ~128 | Set of ~35 known equity tickers (`AAPL`, `MSFT`, `TSLA`, …) |
| `CRYPTO_SOURCE_HINTS` | ~139 | Tuple of source-system substrings indicating crypto (`binance`, `bybit`, `hyperliquid`, …) |
| `CRYPTO_STRATEGY_HINTS` | ~143 | Tuple of strategy-name substrings indicating crypto (`copy_hl_`, `funding`, `onchain`, …) |
| Inline `sym_no_suffix` logic | ~237 | Strips `=X`/`=F` suffixes and normalizes separators before checking stablecoins |

### File B: `conviction_stack.py`

| Function/Constant | Line(s) | Purpose |
|---|---|---|
| `_is_crypto_pick(pick, sym)` | ~268 | **Simplified crypto check.** Returns `True` if `asset_class` or `category` is literally `"CRYPTO"`, OR symbol ends with `USDT`/`USDC`. |
| `_norm_sym(symbol)` | ~86 | Symbol normalizer: uppercase + strip `-`, `/`, `_`. Duplicated from inline logic in smart_picks_engine. |
| Inline `ac_norm` in `audit_smart_gate_institutional_fail()` | ~302 | **Binary classifier:** `"crypto" if ac == "crypto" else "other"` — collapses ALL non-crypto into `"other"`. |

---

## 2. Logic Comparison & Behavioral Differences

### 2.1 `_normalized_asset_class` (smart_picks_engine) vs `_is_crypto_pick` (conviction_stack)

| Scenario | `_normalized_asset_class` | `_is_crypto_pick` |
|---|---|---|
| `{"symbol": "BTCUSDT", "category": "crypto"}` | `"crypto"` | `True` ✓ |
| `{"symbol": "EURUSD=X"}` | `"forex"` (suffix check) | `False` (no USDT/USDC suffix) |
| `{"symbol": "GC=F"}` | `"futures"` (suffix check) | `False` |
| `{"symbol": "SPY"}` | `"etf"` (symbol set lookup) | `False` |
| `{"symbol": "AAPL"}` | `"equity"` (symbol set lookup) | `False` |
| `{"symbol": "NEOUSDT", "source_system": "binance"}` | `"crypto"` | `True` ✓ |
| `{"symbol": "DOGEUSDT", "category": "meme"}` | `"crypto"` (category check) | `False` ⚠️ category is "meme" not "CRYPTO" |
| `{"symbol": "EURCAD", "category": "fx"}` | `"forex"` | `False` |
| `{"symbol": "UNKNOWNXYZ"}` | `"equity"` (default fallback) | `False` |
| `{"symbol": "", "category": "commodity"}` | `"futures"` | `False` ⚠️ |
| `{"symbol": "SOLUSDT", "source_system": "drift"}` | `"crypto"` (source hint) | `True` (USDT suffix) |
| `{"category": "penny"}` | `"equity"` | `False` |

**Key divergence:** `_is_crypto_pick` misses crypto picks where:
- Category is `"meme"` (not `"CRYPTO"`)
- Strategy contains crypto hints but symbol lacks USDT/USDC suffix
- Source system contains crypto hints but no stablecoin suffix

### 2.2 Non-Crypto Classification

| File | Logic | Granularity |
|---|---|---|
| `smart_picks_engine` | `_is_non_crypto(pick)` → `_normalized_asset_class(pick) != "crypto"` | **6 classes:** forex, equity, etf, bond, futures, commodity |
| `conviction_stack` | `ac_norm = "crypto" if ac == "crypto" else "other"` | **Binary:** crypto vs other |

The `conviction_stack` version loses all granularity. It cannot distinguish forex from equity from futures, which means `institutional_filter_reason()` in conviction_stack cannot apply asset-class-specific policies.

### 2.3 Symbol Normalization

| File | Code | Behavior |
|---|---|---|
| `smart_picks_engine` | `sym.upper().replace("-","").replace("_","").replace("/","")` + strip `=X`/`=F` suffixes | Full normalization with suffix awareness |
| `conviction_stack._norm_sym` | `(symbol or "").upper().replace("-","").replace("/","").replace("_","")` | Identical but **no suffix stripping** |

The `conviction_stack` version does NOT strip `=X` or `=F` suffixes, so `EURUSD=X` would NOT match any known set.

---

## 3. Inconsistency Flags

### 🔴 CRITICAL: STOCKS vs EQUITY vs STOCK

In `_normalized_asset_class`, the category fallback map is:
```python
if raw_cat in {"equity", "stock", "penny"}:
    return "equity"
```

The `NON_CRYPTO_POLICY` dict uses `"equity"` as its key. But:
- The `NON_CRYPTO_POLICY["equity"]["allowlist"]` references `"stocks_rsi2_pullback"` (note: `stocks_`, not `equity_`)
- The category field can arrive as `"stock"`, `"stocks"`, `"equity"`, or `"penny"` — all correctly mapped
- **However**, if any upstream code passes `"STOCKS"` (uppercase), it fails because `raw_cat` is lowered but the set only has `"stock"` not `"stocks"`

**Risk:** A pick with `category="STOCKS"` would fall through to the default `"equity"` fallback, which is correct by accident. But a pick with `category="STOCK"` correctly matches. The real danger is if someone adds `"stocks"` to the check without also handling it in `_is_crypto_pick`, creating a split-brain.

### 🔴 CRITICAL: COMMODITY vs FUTURES Mapping

In `_normalized_asset_class`:
```python
if raw_cat in {"commodity", "futures"}:
    return "futures"
```

This maps BOTH `"commodity"` AND `"futures"` categories to the single `"futures"` return value. But:
- `NON_CRYPTO_POLICY` has a `"futures"` key — no `"commodity"` key
- The function returns `"futures"` for `GC=F` (gold futures) via suffix check
- For `category="commodity"` with no `=F` suffix, it also returns `"futures"`

**Inconsistency:** There is no distinct `"commodity"` return value despite the task requirement to support one. Gold (GC=F) arrives as `"futures"` but might semantically be `"commodity"`. If `NON_CRYPTO_POLICY` ever needs commodity-specific rules different from futures, this breaks.

### 🟡 MODERATE: Default Fallback

- `_normalized_asset_class` returns `"equity"` as default (no match → equity)
- `_is_crypto_pick` returns `False` as default (no match → not crypto)
- `audit_smart_gate_institutional_fail` returns `"other"` as default

These are semantically different defaults. An unknown pick is classified as equity in one place and "other" (non-crypto, non-equity) in another.

### 🟡 MODERATE: Missing FOREX_SUFFIX_STRIPPING in conviction_stack

`_norm_sym` in conviction_stack does NOT strip `=X` or `=F` suffixes. If any pick arrives with `symbol="EURUSD=X"`, the conviction_stack's `_is_crypto_pick` would correctly return `False`, but other logic using `_norm_sym` might fail to match against known sets.

---

## 4. Code Duplication Hotspots

| Pattern | smart_picks_engine | conviction_stack | Duplication Type |
|---|---|---|---|
| Symbol normalization | Inline in `_normalized_asset_class` | `_norm_sym()` | Structural copy |
| Crypto detection | Full `_normalized_asset_class` → "crypto" | `_is_crypto_pick` | Partial reimplementation |
| Asset class from pick | `_normalized_asset_class(pick)` | `ac = (pick.get("asset_class") or pick.get("category") or "").lower()` | Partial reimplementation |
| `FOREX_CODES` set | Defined locally | Not defined (missing) | Missing |
| `ETF_SYMBOLS` set | Defined locally | Not defined (missing) | Missing |
| `EQUITY_SYMBOLS` set | Defined locally | Not defined (missing) | Missing |
| `CRYPTO_SOURCE_HINTS` | Defined locally | Not defined (missing) | Missing |

---

## 5. Recommendations

### Immediate Consolidation (P0)

1. **Create `alpha_engine/asset_class.py`** — single canonical module with:
   - `normalize_asset_class(pick) → str` — the full logic from `_normalized_asset_class`
   - `is_crypto(pick) → bool` — `normalize_asset_class(pick) == "crypto"`
   - `is_non_crypto(pick) → bool` — `not is_crypto(pick)`
   - `asset_class_from_symbol(symbol) → str` — symbol-only detection (no pick dict needed)
   - All constants: `FOREX_CODES`, `ETF_SYMBOLS`, `EQUITY_SYMBOLS`, `CRYPTO_SOURCE_HINTS`, `CRYPTO_STRATEGY_HINTS`

2. **Replace `_normalized_asset_class` in smart_picks_engine.py** with import from `asset_class.py`

3. **Replace `_is_crypto_pick` in conviction_stack.py** with `from alpha_engine.asset_class import is_crypto`

4. **Replace `_norm_sym` in conviction_stack.py** with the canonical symbol normalization from `asset_class.py`

5. **Replace inline `ac_norm` in `audit_smart_gate_institutional_fail`** with full `normalize_asset_class` call

### Medium-term (P1)

6. **Decide on "commodity" vs "futures"** — Either introduce `"commodity"` as a distinct return value (with separate policy), or document that `"futures"` covers both. Current mapping is lossy.

7. **Decide on default fallback** — Unknown/empty picks default to `"equity"`. Document this as intentional or change to `"unknown"`.

8. **Add `"stocks"` to category set** — Currently only `"stock"` (singular) is checked. Add `"stocks"` for safety.

### Testing (P0)

9. Add regression tests covering: USDT/USDC→crypto, `=X`→forex, `=F`→futures, known ETF/equity symbols, 6-char forex pairs, conflicting signals, missing fields.

---

## 6. Files That Import/Use Asset-Class Logic (Migration Scope)

| File | What It Uses | Migration Action |
|---|---|---|
| `smart_picks_engine.py` | `_normalized_asset_class`, `_is_non_crypto`, constants | Replace with `from alpha_engine.asset_class import …` |
| `conviction_stack.py` | `_is_crypto_pick`, `_norm_sym`, inline `ac_norm` | Replace with canonical imports |
| `quality_gates.py` (if exists) | Likely uses `_normalized_asset_class` indirectly | Check and migrate |
| `non_crypto_policy.py` | May reference asset class strings | Verify consistency |
| `equity_factor_model.py` | Checks for equity asset class | Verify string matches |
| `ensemble_gate.py` | Crypto-only guard | Migrate to `is_crypto()` |
| `htf_confirmation.py` | Crypto-only guard | Migrate to `is_crypto()` |
| `gainer_interceptor.py` | May filter by asset class | Check and migrate |
| Dashboard / audit_trail | Consumes `asset_class` field | Verify output format |
