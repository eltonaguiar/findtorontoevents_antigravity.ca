# peer_claude — resolver pnl_pct zero-clobber fix (2026-05-31)

## Linked finding

`reports/peer_blackbox_incidents-enhancements-pr_2026-05-31.md`
→ FINDING_OVERALL: exit-logic-divergence (1,394 rows; 581 attributed to
this code path per peer audit).

## Bug

`alpha_engine/outcome_resolver.py::resolve_single_pick()` contained a
breakeven-fallback branch (former lines 957-962) that, when the resolver
could not derive an OHLC-replay `effective_exit` for an already-closed
pick (status in CLOSED/EXPIRED/WON/LOST and entry > 0), unconditionally
overwrote:

```python
pick["exit_price"] = entry   # clobbers any previously recorded exit
pick["pnl_pct"]    = 0.0     # zeroes any previously computed pnl
```

The intent was a "no-data → breakeven force-close" rescue for picks the
resolver had never seen a real exit for. The defect: the guard
(`status in (...) and entry > 0`) did not check whether `exit_price` was
already recorded. Picks closed upstream by
`portfolio_tracker_{copytrader,20x,recommended}.py` with
`TIME_EXIT_MAX_HOLD` / `TIME_EXIT_PROFIT`, or by
`force_close_breached.py` / `production_scanner.py` with `STALE_NO_DATA`
and a genuine `exit_price`, were silently re-zeroed on every subsequent
resolver pass when the OHLC fallback could not re-prove them.

Resulting symptom: `pnl_pct == 0.0` with `exit_price != entry_price` —
the exact divergence pattern flagged in the peer black-box audit.

## Fix

Insert a preserve-exit branch BEFORE the breakeven clobber.

```python
if (status in ("CLOSED", "EXPIRED", "WON", "LOST")
        and entry > 0
        and exit_p > 0
        and abs(exit_p - entry) / entry > 0.00001):
    preserved_pnl = compute_pnl(entry, exit_p, direction)
    if abs(preserved_pnl) <= _pnl_sanity_cap_for(asset_class):
        pick["pnl_pct"] = round(preserved_pnl, 6)
        pick["resolved_by"] = "outcome_resolver_preserve_exit_price"
        pick["_resolver_preserved_exit_price"] = True
        pick["status"] = (
            "EXPIRED" if exit_reason.upper().startswith(
                ("EXPIRED","TIME_EXIT","MAX_HOLD","STALE_NO_DATA"))
            else classify_outcome(preserved_pnl, asset_class=asset_class))
        return pick
```

Rule: only zero `pnl_pct` when `exit_price` is `None`/`0`/missing OR
within float-tolerance (1e-5 relative) of `entry`. Otherwise recompute
from the recorded `exit_price` via `compute_pnl()`. PnL-sanity cap
preserved (rejects implausible >cap results without writing them).

## Tests

`tests/test_outcome_resolver_pnl_preserve.py` — 3 cases, all green:

1. `STALE_NO_DATA` with `exit_price == entry_price` → `pnl_pct = 0.0`
   (legitimate breakeven preserved).
2. `TIME_EXIT_MAX_HOLD` with `exit_price = 105`, `entry = 100`
   → `pnl_pct > 0`, `exit_price = 105` retained, `status = EXPIRED`
   (per v2.3 time-exit rule).
3. `TIME_EXIT_MAX_HOLD` with `exit_price = None` and retries exhausted
   → `pnl_pct = 0.0`, `exit_price = entry` (legitimate force-close
   breakeven; fix does NOT over-preserve).

```
$ python3 -m pytest tests/test_outcome_resolver_pnl_preserve.py -q
... 3 passed in 0.08s
```

## Backups

No DB writes in this PR. Pure code change in resolver + a new unit test
file. The fix takes effect on the NEXT resolver pass; previously
clobbered rows in `closed_picks.json` are not retroactively repaired by
this PR (would require a separate one-shot script with the
ejaguiar1_backups snapshot rule). Recommended follow-up: scan
secondary portfolio JSON files for rows with `pnl_pct == 0.0` AND
`exit_price` recorded != entry AND `_legacy_pnl_pct` != 0, then re-run
`resolve_single_pick` to repopulate `pnl_pct` via the new preserve
branch.

## Scope

- File: `alpha_engine/outcome_resolver.py` (lines ~957-995, additive
  branch above the existing breakeven block — no behavior change to
  the pre-existing path; new path only fires when exit_price is real).
- File: `tests/test_outcome_resolver_pnl_preserve.py` (new).
- No DB writes. No FTP deploy. No dashboard regeneration.

## Branch / PR

Branch: `fix/resolver-pnl-zero-on-stale-2026-05-31` (off `origin/main`).
No auto-merge.
