# Fix: live_picks_tracker.py UnboundLocalError on datetime

**Date:** 2026-05-14  
**File:** `ml_crypto_predictor/enhanced_models/live_picks_tracker.py`  
**Workflow affected:** ANTIGRAVITY-CLAUDEOPUS Live Picks & Discord (was failing every hourly run)

## What Was Broken

The `update_active_picks()` function raised:

```
UnboundLocalError: cannot access local variable 'datetime' where it is not associated with a value
```

at line 529:

```python
now = datetime.now(timezone.utc)
```

## Root Cause

A status-shard rotation block added on 2026-05-14 contained:

```python
if newly_closed:
    try:
        import gzip
        from collections import defaultdict
        from datetime import datetime, timezone  # ← PROBLEM
```

In Python, any `from X import Y` or `Y = ...` inside a function body makes `Y` a **local variable for the entire function scope** — including lines *before* the import. Since `datetime` was assigned locally at line 638, Python raised `UnboundLocalError` when line 529 tried to use it.

`datetime` was already imported at module level (line 21), so the inner import was redundant.

## Fix

Removed the redundant `from datetime import datetime, timezone` from the `if newly_closed:` block. The module-level import covers the whole file.

## Verification

```bash
python -c "import py_compile; py_compile.compile('ml_crypto_predictor/enhanced_models/live_picks_tracker.py', doraise=True)"
# OK
```

The workflow `ANTIGRAVITY-CLAUDEOPUS Live Picks & Discord` should resume normal hourly operation after this is merged.
