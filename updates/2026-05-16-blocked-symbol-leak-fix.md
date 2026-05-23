# Blocked Symbol Leak Fix (P0)

## What Was Leaking

13 blocked symbols were appearing in `active_picks.json` despite being on the `BLOCKED_SYMBOLS` list in `audit_trail/quality_gates.py`. These are symbols with known data-quality issues (delisted, redenomination, bad feeds) or pattern-mined drain symbols with catastrophic win-rates.

## Root Cause

`production_scanner.py` correctly filters blocked symbols before emitting picks, but **11 other files write directly to `active_picks.json` without going through that filter**. The canonical `save_active_picks()` in `alpha_engine/forward_validator.py` is used by multiple callers, and it had no `BLOCKED_SYMBOLS` defense.

Additionally, `_ueps_long_horizon_bypass_active()` in `audit_trail/quality_gates.py` was bypassing **all** blocked symbols for UEPS POSITION picks, when it should only bypass the 5 data-quality blocks (delisted / redenomination symbols that genuinely don't affect a 3-year horizon).

## Fix

Three changes, all minimal and surgical:

### 1. `audit_trail/quality_gates.py` — kill-switch + UEPS restriction

**a. Kill-switch in `passes_active_gate()`**
Added `UNIVERSAL_BLOCKED_SYMBOLS_GATE_DISABLED` env var around the existing blocked-symbol check. Default is ON (`0`); operators can set `=1` to bypass in an emergency without touching code.

```python
if os.environ.get("UNIVERSAL_BLOCKED_SYMBOLS_GATE_DISABLED", "0") != "1":
    if symbol.upper() in BLOCKED_SYMBOLS and not _ueps_long_horizon_bypass_active(pick):
        ...
```

**b. Restrict `_ueps_long_horizon_bypass_active()`**
Introduced `_DATA_QUALITY_BLOCKS = frozenset({"MATICUSDT", "UUSDT", "XMR", "XMRUSDT", "KATUSDT"})` and added an explicit check inside `_ueps_long_horizon_bypass_active()`: if the symbol is NOT in `_DATA_QUALITY_BLOCKS`, the bypass returns `False`. This prevents pattern-mined drain symbols (e.g. `ENAUSDT`, `IMXUSDT`, `ADBE`) from slipping through via the UEPS path.

### 2. `alpha_engine/forward_validator.py` — defense-in-depth filter in `save_active_picks()`

Added a `BLOCKED_SYMBOLS` filter immediately after the whitelist kill-list filter. It:
- Imports `BLOCKED_SYMBOLS` from `audit_trail.quality_gates`
- Filters out any pick whose symbol is in the blocked set
- Logs how many were removed (`[BLOCKED_SYMBOLS] Filtered N blocked picks before save`)
- Is wrapped in `try/except Exception` so a missing import never crashes the save (fail-open)

This protects the canonical save path for all callers, including the 10+ emitters that bypass `production_scanner`.

### 3. Documentation

This file (`updates/2026-05-16-blocked-symbol-leak-fix.md`) documents the leak, root cause, and fix per AGENTS.md rules.

## Verification

After the fix is deployed, run:

```bash
python -c "
import json
from audit_trail.quality_gates import BLOCKED_SYMBOLS
with open('data/active_picks.json') as f:
    picks = json.load(f)
leaked = [p['symbol'] for p in picks if p.get('symbol','').upper() in BLOCKED_SYMBOLS]
print(f'Leaked blocked symbols: {leaked}')
assert not leaked, f'Found blocked symbols in active_picks.json: {leaked}'
print('OK — no blocked symbols in active_picks.json')
"
```

Repeat for any other `active_picks.json` variants (e.g. `audit_dashboard/data/active_picks.json`).
