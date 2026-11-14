# Fix spec — TIME_EXPIRED / spot-flicker zero-PnL artifacts ("P/L stuck at 0%")

> **2026-11-14 peer cross-check correction.** Peer `reports/zero_pnl_data_pipeline_audit_2026-06-05.md`
> found the root cause is NOT spot-flicker: 100% of 28,218 zero rows are `status=EXPIRED`,
> `resolution_method=TIME_EXPIRED`, produced by the `backfill_widened_*` / `backfill_updated_*`
> resolvers (81.2% / 96.6% zero share). The time-expiry resolver writes pnl=0 instead of computing
> close-vs-entry. See §Root-cause-below. Newer resolvers (`backfill_2026-06-01`, `universal_v2`,
> `signflip_purge`) are clean (<10%).

## Problem (evidence)
- pf_registry counts: 28,719 closed rows → **3,872 (13.5%) dropped as "spot-flicker"**
  (|pnl_pct| < 0.0002, i.e. exit == entry to within a hair). June registry: 1,147/1,882 (61%).
- Live active picks: many OPEN rows with current_price=None for days (incubator BTCUSDT picks from
  2026-11-12 unresolved) — the resolver marks exit=entry instead of leaving them pending.
- This is the user-visible "0% PnL stuck" phenomenon.

## Proposed changes
1. **In the resolver** (audit_trail/universal_pick_resolver.py):
   - If the best available exit quote differs from entry by < flicker threshold, do NOT close the
     pick. Mark `status=RESOLVE_PENDING_PRICE` and retry on the next cycle with a better quote.
   - Only force-close with pnl=0 when the pick is past its max lifetime AND two independent
     quotes agree (record both quote sources on the row).
2. **Distinguish three zero-cases** downstream instead of one:
   - `FLAT_REAL` (quotes agree, pnl truly ~0),
   - `PRICE_UNAVAILABLE` (no quote — pending),
   - `SPOT_FLICKER` (single unstable quote).
   Aggregates should exclude PRICE_UNAVAILABLE and count SPOT_FLICKER separately.
3. **Display**: active-pick rows show `age` + `last_checked`; when current_price is None show
   "awaiting price" instead of a 0% P/L (frontend: template.html pick-card renderer).

## Acceptance test
- Spot-flicker drop count in ledger_filter_report.json < 2% of closed rows (from 13.5%).
- No OPEN pick older than 24h with current_price=None and no RESOLVE_PENDING_PRICE marker.
