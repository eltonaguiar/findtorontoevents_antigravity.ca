# Expired zero-PnL rows are now published as FLAT instead of being dropped

**Date:** 2026-11-27 · **File:** `audit_trail/dashboard_generator.py` · **Status:** unit-verified, not yet exercised through a full dashboard build.

## What was broken

`collect_all_picks()` split closed rows into `real_closed` and `auto_expired` (pnl 0 plus a stale/time-exit
reason) and commented that the expired rows are *"kept in the payload for transparency"*. They were not:
`resolved_closed = _filter_valid_resolved_picks(closed)` rejects anything with `_auto_expired=True`, and
`_build_recent_closed_picks()` was called with `resolved_closed` only. So the rows vanished from
`picks.recent_closed`.

The live payload on 2026-11-27 proves the gap:

| field | value |
|---|---|
| `summary.auto_expired_excluded` | **9,420** |
| `summary.resolver_anomalies.expired_zero_pnl_rows` | **3,701** |
| `summary.zero_pnl_count` / `flat_count` | **138** (1.52 %) |
| CRYPTO slice: rows with `pnl_pct == 0` | **0** |

Nine thousand rows were closed by timeout with no outcome and the reader could not see a single one of them.
The `flat_count` tile (138) was counting only the zero-PnL rows that happened to survive the other filters,
which is why it looked like a rounding effect rather than a missing cohort.

## What changed

1. **New `_as_flat_expired_row(pick)`** — returns a copy with `status="FLAT"`, `exit_reason="EXPIRED"`,
   `pnl_pct=0.0`, `_flat=True`, `_auto_expired=True`.
2. **Published cohort** — `recent_closed` is now built from `resolved_closed + _flat_expired_rows`, where
   `_flat_expired_rows` is the most recent auto-expired rows, capped at **15 % of `MAX_CLOSED_PICKS`**
   (525 of 3,500) so FLAT rows can never crowd out real outcomes or the non-crypto reservations.
3. **New summary field `flat_published_rows`** — how many FLAT rows reached the payload, so the count is
   auditable instead of implied.

**What deliberately did *not* change:** `_is_valid_resolved_pick()` still rejects `_auto_expired` rows, so
win rate, profit factor, PnL totals, readiness and forward gates are computed exactly as before. A FLAT row
is visible in the ledger; it is not evidence of an edge and it does not enter the win/loss denominator.

## How it was verified

```bash
python3 -m py_compile audit_trail/dashboard_generator.py            # OK
python3 - <<'PY'   # module imported, helpers exercised directly
row = {"pnl_pct": 0, "status": "TIME_EXIT", "exit_reason": "time_exit", ...}
_is_auto_expired_pick(row)        -> True
_as_flat_expired_row(row)         -> status FLAT, exit_reason EXPIRED, pnl 0.0, _flat True
_is_valid_resolved_pick(flat)     -> False      # still excluded from WR/PF, as intended
row["status"]                     -> "TIME_EXIT"  # original dict not mutated
PY
```

`pytest` is not installed in the project venv (`No module named pytest`), so the suite was run with the
FREELLM venv instead: `~/freellm/.venv/bin/python -m pytest tests/test_audit_proven_gate_and_pnl_audit.py -q`
→ **14 passed**. The first end-to-end exercise is the next `audit-dashboard` cron run; check
`summary.flat_published_rows` and that `picks.recent_closed` now contains `status=FLAT` rows.

## Follow-ups

- Once the cohort is visible, decide whether FLAT belongs in the WR denominator (it currently does not) —
  that is a policy decision for the audit, not a bug fix.
- The 9,420 → 525 cap is a display budget, not a data limit; raise it if class-level FLAT counts are needed.
