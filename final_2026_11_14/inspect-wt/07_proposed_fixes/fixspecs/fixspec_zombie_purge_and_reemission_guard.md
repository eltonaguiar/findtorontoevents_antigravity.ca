# Fix spec — Zombie purge + re-emission guard

## Problem (evidence)
- `live_dashboard_payload.json` `.picks.active_raw` (Nov 14): 4,148 rows, **3,272 (79%) are
  status=EXPIRED with pnl_pct=0.0 and current_price=None** — never resolved, never purged.
- `inverse_mutations` (`inverse_luxalgo_confluence`) alone: 2,262 rows — BTCUSDT/XRPUSDT/NEARUSDT
  re-emitted daily since 2026-07-13 with identical entry prices for days at a stretch.
- Median crypto age in active_raw: 2,128h (89 days); oldest 6,421h (267 days).
- Zombie rows pollute every per-class stat surface and make "active picks" untrustworthy.

## Root cause hypotheses (verify in code before implementing)
1. `inverse_mutations` emitter re-issues a mutation pick every cycle without checking whether the
   prior pick for the same (strategy, symbol, direction) was resolved.
2. The resolver (audit_trail/universal_pick_resolver.py) gives up on rows whose symbol price feed
   breaks (e.g. BTC entry 0.3322 garbage rows) and leaves them EXPIRED-forever.
3. dashboard_generator.py loads active picks from files (e.g. alpha_engine/data/active_picks.json)
   without a max-age filter — nothing prunes stale rows from the feed.

## Proposed changes
1. **Emission guard** in the mutation emitter (alpha_engine side):
   ```python
   # before emitting a new mutation pick, skip if an unresolved pick exists with same
   # (strategy, symbol, direction) — or if >N unresolved picks for same symbol exist
   ```
2. **Generator-side hygiene filter** in audit_trail/dashboard_generator.py `_normalize_pick`
   (or the loader that builds `.picks.active_raw`):
   - Drop rows with `status in (EXPIRED, CLOSED, TP_HIT, SL_HIT)` from active arrays entirely —
     they belong in recent_closed, not active_raw.
   - Max-age gate: active picks older than `MAX_ACTIVE_AGE_H` (propose 168h = 7d; keep
     FUTURES/BOND daily cadence in mind) get demoted to a separate `stale_unresolved` key and
     excluded from all stat surfaces, with a count surfaced in `data_freshness`.
3. **One-time purge migration** (DB + JSON): re-resolve or archive all EXPIRED pnl-0 rows with
   entry_date < 30d. Keep them out of aggregates via the existing policy filters.
4. **Metric**: add `zombie_active_count` and `zombie_pct` to `.data_freshness` so the dashboard
   can display feed health.

## Acceptance test
- active_raw EXPIRED-with-pnl-0 count == 0 after deploy.
- Crypto active_raw median age < 48h.
- `evidence_live_audit.json` active_raw_by_class.CRYPTO.n drops from 3,577 to the genuinely-open count.
