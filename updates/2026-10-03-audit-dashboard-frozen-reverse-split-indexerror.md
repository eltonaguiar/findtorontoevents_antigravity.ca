# /audit dashboard frozen since 2026-08-30 — reverse-split annotation IndexError

**Date:** 2026-10-03
**Scope:** `audit_trail/dashboard_generator.py` → `_annotate_reverse_split_pick()`
**Status:** fixed, verified locally on a clean branch off `origin/main`

## Symptom

`https://findtorontoevents.ca/audit` showed effectively **no active picks** — the
live payload reported `summary.total_active_picks = 1` and only a single
`orphan_emitter_forex_futures` USDCAD pick in the Active Picks table.

Every GitHub Actions run of
[`Unified Audit Dashboard`](../../.github/workflows/audit-dashboard.yml)
(`audit-dashboard.yml`) was failing, and the live data files were **frozen**:

| Live artifact | `generated_at` | `total_active_picks` |
|---|---|---|
| `/audit/data/dashboard_data.json` | `2026-08-30T18:31:49Z` | 1 |
| `/audit/data/dashboard_payload.json` | `2026-08-30T18:31:49Z` | 1 |

Last successful workflow run was `2026-08-30T21:18Z` (run `33336055545`). Every
run after that failed on the step **“Generate dashboard payload and build HTML”**,
so the `Commit updated data` step was skipped and the deploy re-pushed the stale
payload — the site has been serving the 2026-08-30 snapshot for weeks.

## Root cause

The failing step produced this traceback:

```
File ".../audit_trail/dashboard_generator.py", line 18535, in <module>
File ".../audit_trail/dashboard_generator.py", line 15642, in generate
File ".../audit_trail/dashboard_generator.py", line 6990, in _build_recent_closed_picks
File ".../audit_trail/dashboard_generator.py", line 80, in _annotate_reverse_split_pick
IndexError: list index out of range
```

`_annotate_reverse_split_pick()` treated the registry value as a single
`(ratio, date)` pair:

```python
info = get_reverse_split_info(sym)   # -> list[tuple[str, str]] | None
if info:
    out["reverse_split_ratio"] = info[0]
    out["reverse_split_date"]  = info[1]   # <-- IndexError
```

But `get_reverse_split_info()` (`audit_trail/reverse_split_symbols.py`) returns a
**list of `(ratio, date)` tuples, newest first**. For any symbol with exactly one
split — `LODE`, `KULR`, `GSAT`, `GE` — `info[1]` is out of range and raises.
For multi-split symbols (`FFIE`, `WKHS`, `HOLO`) it did not raise but wrote whole
tuples into the `ratio` / `date` fields.

Because `_annotate_reverse_split_pick` is called from inside
`_build_recent_closed_picks` and `picks.active` construction, **one reverse-split
symbol inside the closed-pick set is enough to crash the entire dashboard
generation**. The regression was introduced by commit `2dbc0153ad`
(2026-06-04, “audit: reverse-split badges… #523”); it only started biting once a
`LODE/G…` pick actually landed in `recent_closed`, which happened after
2026-08-30.

### Reproduction

```
$ python3 -c "from audit_trail.reverse_split_symbols import get_reverse_split_info as g; \
  print(g('LODE')[1])"
IndexError: list index out of range
```

## Fix

`audit_trail/dashboard_generator.py` — index into the newest tuple and guard the
shape so a registry change can never take the build down again:

```python
    info = get_reverse_split_info(sym)
    if info:
        newest = info[0]
        if isinstance(newest, (list, tuple)):
            out["reverse_split_ratio"] = newest[0] if len(newest) > 0 else None
            out["reverse_split_date"]  = newest[1] if len(newest) > 1 else None
        else:  # registry shape changed — never crash the build over a badge
            out["reverse_split_ratio"] = newest
```

The front-end only consumes `reverse_split_affected` and `reverse_split_note`
(see `audit_dashboard/template.html`), so the informational `ratio` / `date`
fields being restored to scalars is safe.

## Verification

- `tests/test_reverse_split_annotate.py` (new, 12 cases) — **fails on the old
  code with the exact production `IndexError: list index out of range` at
  `dashboard_generator.py:80`, passes on the fix.** Verified both directions
  (`git stash` the fix → 9 failed; restore → 12 passed).
- Function-level check: `LODE/KULR/GSAT/GE` return scalars, no raise;
  `FFIE/WKHS/HOLO` return the newest split’s scalars; non-split symbols pass
  through untouched.
- `py_compile` clean.

## Follow-up (not fixed here — needs live-data investigation)

In the frozen 2026-08-30 payload the published active book collapsed to **1 pick
while `picks.active_raw` held 698 `OPEN` rows (~697 looking valid: non-empty
strategy, non-BANNED trust, median age 7.4h)**. The kill-list gate accounts for
only 175 of them and a `score >= 20` floor would still keep 247, so neither
explains the collapse on its own — the remaining suspects are the
`universal_resolved_picks` identity filter, the exact-duplicate dedup, and
`passes_active_gate` score floors. That needs the live input files and cannot be
reproduced from the committed snapshot. Fixing the crash above is what lets the
dashboard regenerate **at all**; the published count should be re-checked on the
first fresh build after this lands.
