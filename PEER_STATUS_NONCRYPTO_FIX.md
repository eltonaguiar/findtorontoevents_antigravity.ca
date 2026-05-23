# Non-Crypto Dashboard Fix — Peer Status

**Session:** 2026-04-04 ~16:00 UTC
**Author:** Claude (main repo peer)

## User-Reported Bug

> "Magnifying glass for ETFs doesn't work!"
> Section: `findtorontoevents.ca/audit/` → "Non-Crypto Performance" panel

When user clicks the magnifying glass button on the **ETFs** card (and **Futures**
card), the drill-down modal opens but shows "No closed trades (0)" and
"No active picks (0)" — despite the card showing "Active: 5, Closed: 4, WR: 75%".

## Root Cause

**Two bugs compound:**

### Bug 1: Per-category crowding in closed picks reservation
- `_build_recent_closed_picks()` reserves 200 slots for non-crypto picks
- Reservation iterates picks by timestamp desc, includes first 200 non-crypto hits
- FOREX (377) + EQUITY (284) + COMMODITY (155) = 816 picks — they fill the 200
  slot reservation before smaller categories are reached
- Result: **0 ETF, 0 FUTURES, 0 BOND** in the capped payload
- Card stats use full server-side `non_crypto_performance` from `resolved_closed`
- Drill-down uses capped `D.picks.recent_closed` → mismatch

### Bug 2: Active picks gate runs AFTER non_crypto_performance computed
- Line 10042: `compute_non_crypto_performance(final_active_picks, resolved_closed)`
- Line 10376-10384: `passes_active_gate` filters active picks (276 → 130)
- Non-crypto picks drop from 101 → 11 (EQUITY: 73→6, FOREX: 14→2, etc.)
- Card shows pre-gate numbers; drill-down uses post-gate → mismatch

## Fixes Applied

### Fix 1: Per-category quota in `_build_recent_closed_picks`
File: `audit_trail/dashboard_generator.py` lines 3921-3987

Balanced reservation algorithm:
1. Bucket non-crypto picks by normalized asset class (FOREX, EQUITY, STOCK,
   COMMODITY, FUTURES, ETF, BOND)
2. Give each category a base quota of `floor(nc_reserved_slots / 7) = 28` slots,
   or fewer if the category has fewer picks
3. Distribute remaining slots (~99 with current data) round-robin to
   categories that have capacity to hold more, weighted by capacity
4. Fill reservation per quota in timestamp desc order per bucket

Result with current live data (377 FOREX, 284 EQUITY, 155 COMMODITY, 8 BOND, 5 FUTURES, 4 ETF):
- Quotas: `FOREX=61, EQUITY=61, COMMODITY=61, BOND=8, FUTURES=5, ETF=4, STOCK=0`
- **All 4 ETF picks, 5 FUTURES picks, 8 BOND picks preserved**

### Fix 2: Recompute `non_crypto_performance` post-gate
File: `audit_trail/dashboard_generator.py` lines 10400-10403

After the post-score quality gate removes low-quality picks, recompute the
card statistics from the final published picks so card numbers match what
the drill-down can display:
```python
payload["summary"]["non_crypto_performance"] = compute_non_crypto_performance(
    payload["picks"]["active"], payload["picks"]["recent_closed"]
)
```

## Testing

- **Unit tests:** `tmp_unit_test.py` — 4 test cases all pass
  - Live-data distribution: all small categories fully reserved
  - Edge case: fewer picks than quota
  - Large skewed distribution: 1 ETF among 5000 EQUITY — ETF preserved
  - Alias normalization (STOCKS→STOCK, FUTURE→FUTURES, FX→FOREX)
- **Playwright E2E:** `test_etf_magnifier.py` — confirmed all 5 magnifying
  glass buttons open modals; currently shows Futures/ETF empty (will verify
  after deploy)

## Peer Coordination Notes

- **Peer 9myf6f9p** is auditing the same dashboard. My changes only touch:
  - `audit_trail/dashboard_generator.py` (server-side payload builder)
  - NOT modifying `audit_dashboard/template.html` (preserved)
- **Peer 4j9sf0s4** is working on scoring/strategies — no conflict.
- If you see `data/dashboard_data.json` rebuild with ETF picks appearing
  in the recent_closed array, that's my fix taking effect after the
  audit-dashboard workflow regenerates.

## Files Changed

1. `audit_trail/dashboard_generator.py` — per-category reservation + recompute
2. `PEER_STATUS_NONCRYPTO_FIX.md` (this file)

Temp files (will be cleaned up before commit): `tmp_live_payload.json`,
`tmp_analyze.py`, `tmp_analyze2.py`, `tmp_active.py`, `tmp_test_fix.py`,
`tmp_unit_test.py`, `test_etf_magnifier.py`.

## Next Steps

1. Clean up temp files
2. Commit + push to main
3. Wait for audit-dashboard GH Actions workflow to regenerate payload
4. Re-run Playwright test to verify ETF/FUTURES drill-downs show data

---

## Second Fix (2026-04-04 ~17:30 UTC): outcome_resolver.py missing exit_price bug

### Bug
393 of 1200 closed picks (33%) in the audit dashboard payload have `exit_price=None`
despite `status="CLOSED"` and `exit_reason="CLOSED"`. Most are forex/commodity
copy-trader picks (AUDUSD=X, EURJPY=X, NZDUSD=X, USDCAD=X, GC=F, etc.).

### Root Cause (traced via Explore subagent)
Two-layer bug in `alpha_engine/outcome_resolver.py`:

**Layer 1: `is_unresolved()` lines 263-292** — Check order put `pnl_val != 0` early
exit before the exit_price check. Picks with `pnl_pct != 0 + exit_price=None` were
never detected.

**Layer 2: `resolve_single_pick()` line 378-380** — When yfinance forex price fetch
fails (returns None for `live_price`), `effective_exit` stays None and the function
silently returns the pick UNCHANGED, leaving `exit_price=None` permanently.

### Fix
1. `is_unresolved()`: Added explicit check — any pick with `status in (WON,LOST,CLOSED,EXPIRED)`
   AND `exit_price is None or <= 0` is ALWAYS unresolved. Catches all 393 cases.

2. `resolve_single_pick()`: When `effective_exit` cannot be determined, write a
   fallback: `exit_price=entry`, `pnl_pct=0`, `exit_reason="RESOLVE_FAILED_BREAKEVEN"`,
   `_resolve_retry_needed=True`. This eliminates the data-integrity violation
   (exit_price=None on CLOSED picks) while flagging the pick for re-resolution.

### Tests
`tmp_test_resolver.py` — 7/7 passing (null exit_price, non-zero pnl+null exit,
fallback breakeven, live_price still works, no entry_price, exit_price=0).

### Files Modified
- `alpha_engine/outcome_resolver.py` — `is_unresolved()` + `resolve_single_pick()`

---

## Kilo Audit Findings (full verification summary)

Verified against live payload `ts=2026-04-04T16:41Z` via `tmp_kilo_verify.py`:

| Bug | Status | Location |
|-----|--------|----------|
| Conflicting LONG+SHORT on 7 symbols | CONFIRMED, deferred (policy call) | quality_gates.py |
| 393 missing exit_price (33% of closed) | **FIXED** this session | outcome_resolver.py |
| 26 SHORT picks active | NOT A BUG (intentionally whitelisted) | — |
| 133/189 score=0 (70%) | CONFIRMED, BLOCKED by lock | dashboard_generator.py |
| STRONG field partial | CONFIRMED, BLOCKED by lock | dashboard_generator.py |
| 7 duplicate picks | CONFIRMED, BLOCKED by lock | dashboard_generator.py |
| 54 unparseable timestamps | CONFIRMED, BLOCKED by lock | dashboard_generator.py |
| Mercury drawdown 19702% | IDENTIFIED, BLOCKED by lock | dashboard_generator.py |

5 remaining fixes require `dashboard_generator.py` which is currently locked by
another agent.
