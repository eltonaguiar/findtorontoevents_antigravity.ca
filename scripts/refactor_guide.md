# Refactor Guide — Migrate to Canonical `asset_class.py`

**Date:** 2026-04-10  
**Module:** `alpha_engine/asset_class.py`  
**Goal:** Replace all duplicated asset-class normalization logic with the single canonical module.

---

## Step 0: Verify New Module

Before migrating, confirm `alpha_engine/asset_class.py` exists and tests pass:

```bash
cd /path/to/repo
python -m pytest tests/test_asset_class.py -v
```

---

## Step 1: Migrate `smart_picks_engine.py`

**File:** `alpha_engine/smart_picks_engine.py`

### 1a. Add import (top of file, ~line 20)

```python
from alpha_engine.asset_class import (
    normalize_asset_class,
    is_crypto,
    is_non_crypto,
    asset_class_from_symbol,
    normalize_symbol,
    FOREX_CODES,
    ETF_SYMBOLS,
    EQUITY_SYMBOLS,
    CRYPTO_SOURCE_HINTS,
    CRYPTO_STRATEGY_HINTS,
)
```

### 1b. Remove local constant definitions (~lines 118–143)

**DELETE** these blocks entirely:
- `FOREX_CODES = { ... }` (~line 118)
- `ETF_SYMBOLS = { ... }` (~line 123)
- `EQUITY_SYMBOLS = { ... }` (~line 128)
- `CRYPTO_SOURCE_HINTS = ( ... )` (~line 139)
- `CRYPTO_STRATEGY_HINTS = ( ... )` (~line 143)

### 1c. Remove `_normalized_asset_class()` function (~lines 230–265)

**DELETE** the entire function. Replace all call sites:

| Old Code | New Code |
|---|---|
| `_normalized_asset_class(pick)` | `normalize_asset_class(pick)` |
| `asset_class = _normalized_asset_class(pick)` | `asset_class = normalize_asset_class(pick)` |

Call sites to update:
- `score_pick()`: ~line where `asset_class = _normalized_asset_class(pick)` is used
- `_non_crypto_policy_block_reason()`: where `asset_class = _normalized_asset_class(source_pick)`
- Any other internal references

### 1d. Remove `_is_non_crypto()` function (~line 274)

**DELETE** the function. Replace call sites:

| Old Code | New Code |
|---|---|
| `_is_non_crypto(pick)` | `is_non_crypto(pick)` |

### 1e. Update `NON_CRYPTO_POLICY` keys

The policy dict uses `"equity"`, `"forex"`, `"etf"`, `"bond"`, `"futures"` as keys. The canonical module returns exactly these strings, so no key changes needed. Verify by running tests.

### 1f. Verify downstream consumers

- `score_pick()` returns `asset_class.upper()` — keep this (it's output formatting, not logic)
- The `non_crypto` local variable in `score_pick`: replace `_is_non_crypto(pick)` → `is_non_crypto(pick)`

---

## Step 2: Migrate `conviction_stack.py`

**File:** `alpha_engine/conviction_stack.py`

### 2a. Add import (top of file)

```python
from alpha_engine.asset_class import (
    normalize_asset_class,
    is_crypto,
    normalize_symbol,
)
```

### 2b. Replace `_norm_sym()` (~line 86)

**DELETE** the function. Replace all call sites:

| Old Code | New Code |
|---|---|
| `_norm_sym(s)` | `normalize_symbol(s)` |

Call sites in this file:
- `fear_greed_loser_symbol_reject()` — the `sym = (...)` block
- `classify_hf_conviction_tier()` — `sym = _norm_sym(...)` 
- Tier symbol set construction: `frozenset(_norm_sym(x) for x in ...)`

**IMPORTANT:** `normalize_symbol` also strips `=X` and `=F` suffixes (unlike the old `_norm_sym`). This is safe for the conviction tier use case since tier symbols are crypto (USDT-suffixed) and would never have `=X`/`=F`.

### 2c. Replace `_is_crypto_pick()` (~line 268)

**DELETE** the function. Replace call sites:

| Old Code | New Code |
|---|---|
| `_is_crypto_pick(pick, sym)` | `is_crypto(pick)` |

Note: `is_crypto()` is more comprehensive (checks source hints, strategy hints, symbol suffixes, category mapping). This is **strictly better** — the old version missed crypto picks with `category="meme"` or strategy-hint-only signals.

**Call site:** `classify_hf_conviction_tier()` — `is_crypto = _is_crypto_pick(pick, sym)` → `is_crypto_pick = is_crypto(pick)`

Rename the local variable to avoid shadowing the imported function name:
```python
pick_is_crypto = is_crypto(pick)
```

### 2d. Replace inline `ac_norm` in `audit_smart_gate_institutional_fail()` (~line 302)

**Old code:**
```python
ac = str(pick.get("asset_class") or pick.get("category") or "CRYPTO").lower()
ac_norm = "crypto" if ac == "crypto" else "other"
```

**New code:**
```python
ac_norm = normalize_asset_class(pick)
```

This gives full granularity (`forex`, `equity`, `etf`, `bond`, `futures`) instead of the binary `crypto`/`other`. The `institutional_filter_reason()` function already accepts any asset class string, so this is backward-compatible.

---

## Step 3: Check & Migrate Other Files

Search the repo for duplicated patterns:

```bash
# Find all files referencing asset class normalization
grep -rn "_normalized_asset_class\|_is_crypto_pick\|_is_non_crypto\|_norm_sym" alpha_engine/ --include="*.py"

# Find local FOREX_CODES/ETF_SYMBOLS/EQUITY_SYMBOLS definitions
grep -rn "^FOREX_CODES\|^ETF_SYMBOLS\|^EQUITY_SYMBOLS\|^CRYPTO_SOURCE_HINTS\|^CRYPTO_STRATEGY_HINTS" alpha_engine/ --include="*.py"

# Find inline crypto detection patterns
grep -rn 'endswith.*USDT\|endswith.*USDC\|asset_class.*==.*crypto' alpha_engine/ --include="*.py"
```

### Likely files to update:

| File | Pattern | Action |
|---|---|---|
| `quality_gates.py` | May inline-check `asset_class == "crypto"` | Import `is_crypto` |
| `non_crypto_policy.py` | References asset class strings | Verify strings match canonical returns |
| `equity_factor_model.py` | Checks for equity class | Import `normalize_asset_class` |
| `ensemble_gate.py` | Crypto-only guard | Import `is_crypto` |
| `htf_confirmation.py` | Crypto-only guard | Import `is_crypto` |
| `gainer_interceptor.py` | May filter by asset class | Import `normalize_asset_class` |
| `copy_trader_bridge.py` | May tag picks with asset class | Import `normalize_asset_class` |

### Migration pattern for all files:

```python
# OLD (inline)
ac = (pick.get("asset_class") or pick.get("category") or "").lower()
if ac == "crypto":
    ...

# NEW (canonical)
from alpha_engine.asset_class import is_crypto
if is_crypto(pick):
    ...
```

---

## Step 4: Update Tests

1. **Run canonical tests:** `python -m pytest tests/test_asset_class.py -v`
2. **Run full suite:** `python -m pytest` (or whatever test runner is used)
3. **Check for test breakage** from changed behavior:
   - `_is_crypto_pick` now catches `category="meme"` picks → previously missed
   - `_norm_sym` now strips `=X`/`=F` → harmless for crypto tier symbols
   - `audit_smart_gate_institutional_fail` now returns granular asset class → verify `institutional_filter_reason` handles all classes

---

## Step 5: Add Deprecation Shims (Optional, for gradual rollout)

If you can't migrate everything at once, add thin wrappers in the original files:

```python
# smart_picks_engine.py — temporary shim
import warnings
from alpha_engine.asset_class import normalize_asset_class as _normalized_asset_class

def _is_non_crypto(pick):
    warnings.warn("_is_non_crypto is deprecated, use is_non_crypto from asset_class", DeprecationWarning)
    from alpha_engine.asset_class import is_non_crypto
    return is_non_crypto(pick)
```

Remove shims after full migration.

---

## Step 6: Verify & Clean Up

1. Delete all duplicated code from original files
2. Remove unused imports
3. Run linter: `ruff check alpha_engine/` or `flake8 alpha_engine/`
4. Run type checker if applicable: `mypy alpha_engine/`
5. Run full test suite
6. Commit with message: `refactor: consolidate asset-class normalization into canonical asset_class.py`

---

## Rollback Plan

If issues arise:
1. Revert the commit
2. The old functions remain untouched in git history
3. File an issue documenting the specific regression for targeted fix
