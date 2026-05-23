# Fix: Forward Test Daily `KeyError: 'ticker'`

**Date:** 2026-04-16  
**Author:** Codebuff (Buffy)  
**Affected workflows:** Forward Test Daily, [torontoevent.net] Forward Test Daily  
**Root cause:** `STOCKS/competition/forward_test.py` line 466 used direct bracket access `p['ticker']` which threw `KeyError` when a pick dict lacked the `ticker` key  

## Problem

Both Forward Test Daily workflows failed with (traceback line numbers are from the failing revision, not necessarily current `main`):
```
KeyError: 'ticker'
  File "STOCKS/competition/forward_test.py", line 425, in cmd_resolve
    tickers_needed = list(set(p['ticker'] for p in open_picks))
```

The `_normalize_open_pick_for_resolve()` function and the MISSING_TICKER handler both use `.get('ticker')` (safe access), but the `tickers_needed` list comprehension and the resolve loop used direct `p['ticker']` / `pick['ticker']` access (unsafe). If any pick has `status='OPEN'` but no `ticker` key, the code crashes before reaching the safe handlers.

## Fix

Two changes in `STOCKS/competition/forward_test.py`:

1. **Line ~466** — `tickers_needed` list comprehension:
   ```python
   # Before:
   tickers_needed = list(set(p['ticker'] for p in open_picks))
   # After:
   tickers_needed = list(set(p.get('ticker', '') for p in open_picks if p.get('ticker')))
   ```
   Added `.get()` access and `if p.get('ticker')` filter to skip picks without a ticker (empty strings passed to `yf.download()` would cause silent failures).

2. **Line ~489** — resolve loop ticker extraction:
   ```python
   # Before:
   ticker = pick['ticker']
   # After:
   ticker = pick.get('ticker', '')
   ```
   Safe fallback; if empty string, the `if ticker not in close_df.columns` check skips it naturally.

## Verification

- `py_compile.compile('STOCKS/competition/forward_test.py', doraise=True)` → SYNTAX OK  
- Other `p['status']` accesses in this path assume `status` is present on pick dicts created by this module; the failure mode here was specifically missing `ticker`.

## Cascading impact

- **Feed Health Check** was failing because the audit-dashboard pipeline wasn't completing (stale payload 21h > 12h threshold). The threshold was already relaxed to 30h in commit `3ce49b01`. Once the audit-dashboard pipeline succeeds, the Feed Health Check should recover.
