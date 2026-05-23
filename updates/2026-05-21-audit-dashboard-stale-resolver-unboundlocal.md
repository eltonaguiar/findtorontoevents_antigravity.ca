# Audit dashboard stale — `universal_pick_resolver` UnboundLocalError (2026-05-21)

## What was broken

The GitHub Actions step **Resolve active picks** (`python audit_trail/universal_pick_resolver.py`) failed with:

```text
UnboundLocalError: cannot access local variable 'pnl_pct' where it is not associated with a value
```

around line 1019 in `audit_trail/universal_pick_resolver.py`.

**Root cause:** Commit `9c6f8d3fc64` added the F-1 PnL outlier cap (`+/-100%`) on the JSON resolution path but left the cap and the entire `resolved = {...}` block **outside** the `if result:` guard. When `check_tp_sl()` returns `None` (price between TP and SL), `pnl_pct` is never assigned, yet the next lines reference it — Python raises `UnboundLocalError`.

The workflow uses `continue-on-error: false` for this step (since 2026-05-20), so the failure blocks the full **Unified Audit Dashboard** pipeline and leaves `/audit` stale.

## What changed

Indented the F-1 cap, `resolved` dict build, stats bump, log line, and `continue` **inside** `if result:` so they only run when TP/SL actually hit.

Before (broken on `origin/main`):

```python
if result:
    reason, exit_price, pnl_pct = result
# F-1 cap and resolved block here — runs even when result is None
if pnl_pct is not None:
    ...
```

After (fixed):

```python
if result:
    reason, exit_price, pnl_pct = result
    # F-1 cap and resolved block here
    pnl_pct_raw_json = pnl_pct
    pnl_pct = max(-100.0, min(100.0, float(pnl_pct)))
    ...
    continue
```

## Verification

- `python3 -c "import py_compile; py_compile.compile('audit_trail/universal_pick_resolver.py', doraise=True)"` — pass
- Smoke: `check_tp_sl()` no-hit path returns `None` without touching `pnl_pct` in `main()` loop logic (import + assert in one-liner)

## Deploy / recovery

After push to `main`, dispatch:

```bash
gh workflow run "Unified Audit Dashboard" --ref main
```

Expected: **Resolve active picks** completes; dashboard generator runs; `/audit` refreshes.
