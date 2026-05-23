# Fix: ETF Emitter Mislabeling + Dead Code Wiring + PEAD Warning — 2026-05-16

## What Was Broken

### 1. ETF Emitter `source_system` Mislabeling (P1)
**File:** `tools/etf_sector_emitter.py`  
**Commit that introduced:** `87fe706a8c fix(etf): sector emitter was running 1/5 strategies + missing BOND_SYMBOLS`

After the fix to run all 5 ETF strategies, the output JSON still labeled `source_system: "etf_sector_rotation"` and `strategy: "all_etf_strategies"`. This is misleading because:
- `etf_sector_rotation` is only ONE of 5 strategies
- Downstream consumers filtering by `source_system` would misattribute picks
- Per-strategy performance tracking was corrupted

### 2. Dead Code: `is_gap_risk_equity()` Unused (P2)
**File:** `alpha_engine/config.py:647-650`  
**Commit that introduced:** `6bbc11dc65 feat(world-class): PCG-5 enforce mode + net-of-cost model + PEAD wire + large-cap/gap-risk split`

The helper function `is_gap_risk_equity()` was defined but never called. `score_booster.py` did a direct import of `GAP_RISK_EQUITY_SYMBOLS` and its own membership check, bypassing the helper entirely.

### 3. PEAD Strategy Silent Failure (P2)
**File:** `non_crypto_agent/main.py:375-383`  
**Commit that introduced:** `6bbc11dc65`

PEAD equity strategy was opt-in but when enabled (`PEAD_EQUITY_ENABLED=1`), it would silently receive an empty earnings list and emit 0 picks with no warning.

## What Changed

### Fix 1: ETF Emitter Labels
- Changed `source_system` from `"etf_sector_rotation"` → `"etf_all_strategies"`
- Changed `strategy` from `"all_etf_strategies"` → `"multi_strategy_aggregate"`
- Updated `_normalize_pick()` default `source_system` parameter to match

### Fix 2: Wire `is_gap_risk_equity()` Helper
- Changed `score_booster.py` to import and use `is_gap_risk_equity()` from config
- Replaced direct frozenset membership check with the helper function
- Makes the helper function useful and follows the intended API design

### Fix 3: PEAD Empty Data Warning
- Added warning log when `PEAD_EQUITY_ENABLED=1` but `earnings_events` is empty
- Tells operator exactly what's needed (wire an earnings data source)

## How Verified

- All 3 files pass `py_compile` syntax check
- `is_gap_risk_equity()` behavior is identical (same frozenset lookup, same `.upper()` normalization)
- ETF emitter change is purely metadata — pick-level `strategy` field already contained correct per-strategy names
- PEAD warning is only triggered when explicitly enabled AND no data — no false positives

## Why Not Fix Duplicate Commits

BUG-1 and BUG-2 from the 72h review (duplicate commits `8b73150f67`, `47b5f56272`/`bfa37b4dbe`, `f3a2655ff0`/`0b420aa1ab`) are documented in `updates/2026-05-16-opencode-72h-review-feedback.md` but NOT fixed here because:
- They are already pushed to `main`
- Fixing requires `git rebase -i` + `git push --force`
- Force push is dangerous per AGENTS.md ("NEVER run `git push --force` without asking")
- These are history-cosmetic issues, not runtime bugs
- Recommend operator handles via squash on next branch opportunity
