# Plan review: fix the non-crypto forward-resolution pipeline

## Root cause (confirmed by investigation)
`at_raw_picks` (MySQL) rows are INSERTed as status=OPEN / pnl_pct=NULL. The ONLY
code that resolves them — `alpha_engine/active_picks_sync.py::apply_transition()`
— runs DRY-RUN only: the workflow `.github/workflows/audit-dashboard.yml:382-406`
invokes it without `--apply` and without `ACTIVE_PICKS_SYNC_APPLY=1`, and only
for `--asset-class CRYPTO` and `EQUITY` (never FOREX/COMMODITY/BOND/ETF/FUTURES).
PR #2 (wire the writer) and PR #3 (integrate into workflow) were never shipped.
Result: non-crypto resolution = 0%.

## Proposed staged fix
1. Verify `at_raw_picks` symbol format per class — bare (`EURUSD`,`GC`) vs Yahoo
   (`EURUSD=X`,`GC=F`). If bare, add a `_to_yahoo_symbol()` normalizer in
   `active_picks_sync.fetch_live_prices` before `yf.Tickers(...)`.
2. Extend `audit-dashboard.yml` to invoke `active_picks_sync` for ALL asset
   classes (still dry-run) — inspect non-crypto verdicts.
3. Flip the writer on: add `--apply` + `ACTIVE_PICKS_SYNC_APPLY=1`; place the
   step before the resolver step so closures feed downstream same-cycle.
4. Verify: `SELECT asset_class, COUNT(*), SUM(status<>'OPEN')` shows non-crypto
   resolved > 0; check `no_price_available` count.

## Questions for the swarm
1. Is flipping a production-MySQL writer on inside an hourly workflow safe, or
   should it run shadow/dry-run for N cycles first and diff the proposed
   transitions before any write?
2. What guardrails before enabling writes: a per-cycle max-rows cap? a backup of
   `at_raw_picks` first? a status-transition whitelist (only OPEN->WON/LOST,
   never reopen)?
3. Risk of double-resolution: if a crypto row was already INSERTed terminal,
   could `active_picks_sync` wrongly re-transition it? How to make
   `apply_transition` idempotent.
4. yfinance batch-fetch silent-empty on wrong symbol format — best way to fail
   loud instead of marking everything `no_price`.
5. Sequencing — should the writer step run before or after the JSON resolvers?
6. Anything in this plan that is wrong or dangerous?
