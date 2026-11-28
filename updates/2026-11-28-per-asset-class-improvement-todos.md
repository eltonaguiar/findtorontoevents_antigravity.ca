# Per-asset-class improvement todos — 2026-11-28

Generated after the wrong-side-stop sweep (`updates/2026-11-28-historical-wrong-side-stop-sweep.md`).
Every number below is a measured gate detail from
`python3 tools/asset_class_audit_checks.py --skip-backtests` run at
2026-11-28T04:05Z (JSON: `/tmp/audit_post_sweep.json`, 15/51 gates passing) or
the session's per-class edge table. Bars: `null_pnl_share ≤ 55%`,
`null_closed_at_share ≤ 55%`, `duplicate_share ≤ 10%`, `open_share ≤ 60%`,
`bad_side_stops = 0`, `weekend_closes = 0`, `unlabelled_zero_pnl = 0`.

`bad_side_stops` is **0 in every class** after the sweep. The failures below are
the remaining ones, ordered by how much they distort the class's headline
numbers.

---

## CRYPTO — 21,421 resolved, WR 51.0%, PF 1.22, −0.143% net of 0.25% costs

- [ ] `duplicate_share` 14.7% (6,464 extra rows in 3,667 groups) — the largest
      honest sample in the estate is 15% inflated; dedupe by
      `(symbol, created_at, direction)` at ingest, then re-measure WR/PF.
- [ ] `unlabelled_zero_pnl` 705 rows with `pnl = 0` and a non-flat status —
      these score as neither win nor loss; classify as `EXPIRED`/`FLAT`.
- [ ] `weekend_closes` 2,770 rows closed Sat/Sun — crypto is 24/7 so a weekend
      close is legal here, unlike every other class; either widen the gate for
      CRYPTO or prove the resolver's timestamps are not offset.
- [ ] Turn the −0.143% net into a candidate: at 0.25% costs the class needs
      PF ≥ 1.31 merely to break even. Re-price the cost model or narrow the
      symbol set to the majors before spending more on signal work.

## EQUITY — 884 resolved, WR 54.4%, PF 1.33, **+0.169% net** of 0.03% (only class surviving costs)

- [ ] `duplicate_share` 71.2% (10,363 extra rows in 985 groups) — the class with
      the only post-cost edge is the most duplicated one in the DB; this is the
      single highest-leverage fix in the estate.
- [ ] `open_share` 73.3% (10,666 still OPEN) and `null_closed_at_share` 73.7% —
      the same rows: a pick that never resolves cannot contribute an edge, and
      the resolution rate bounds every statistic quoted for the class.
- [ ] `unlabelled_zero_pnl` 830 rows — same treatment as CRYPTO.
- [ ] `weekend_closes` 188 rows closed Sat/Sun — impossible for a listed
      equity; trace the resolver's date handling before the class is trusted.
- [ ] Guard the +0.169%: add a per-class cost assertion to the audit so a
      change in the cost model cannot silently erase the one positive class.

## FOREX — PF ≈ 1.00, −0.002% net

- [ ] `null_pnl_share` 64.8% (41,871 of 64,664) — the largest null block in the
      estate; more than half the class cannot be scored at all.
- [ ] `duplicate_share` 63.2% (40,882 extra rows in 12,966 groups) — the
      denominator is largely duplicates *of rows that also lack a PnL*, so the
      real sample size is unknown until both are fixed.
- [ ] `open_share` 72.3% / `null_closed_at_share` 72.4% — same rows again.
- [ ] `weekend_closes` 776 — FX closes Friday 22:00 UTC; a weekend close is
      proof of a timestamp bug, not a market event.
- [ ] Restore the 2,667 `USD-JPY`/`USD-CHF`-shaped rows that the backfill used
      to call unclassifiable: `tools/backfill_unknown_category.py` now applies
      the sync's ISO-pair rule, so `--table trading_picks --apply` labels them
      FOREX instead of reporting them.
- [ ] Do not fund signal research on this class until `null_pnl_share` < 55%.

## ETF — 3,527 rows, null PnL 84.3%

- [ ] `null_pnl_share` 84.3% (2,973 of 3,527) and `open_share` 86.5% — the
      class is effectively unmeasured; any ETF WR/PF in a report is built on
      ~540 rows.
- [ ] `unlabelled_zero_pnl` 65 and `weekend_closes` 19 — small, same causes.
- [ ] `duplicate_share` 17.1% (604 extra in 444 groups) — one emitter writes
      the same ETF pick repeatedly; find it via
      `source_system` before the resolver spends another cycle on it.
- [ ] Decide the ETF universe: the 26 rows backfilled to ETF on 2026-11-28 were
      `etf_all_strategies` rows whose emitter set no class at all — the emitter,
      not the label layer, is the bug.

## BOND — 1,818 rows, +0.005% net

- [ ] `null_pnl_share` 79.3% (1,441 of 1,818), `open_share` 86.3%,
      `null_closed_at_share` 86.6% — the class quotes a positive edge from 377
      scored rows; that is not an edge, it is noise.
- [ ] `duplicate_share` 47.2% (859 extra in 181 groups) — 181 groups for 377
      scored rows means the "sample" is a handful of instruments repeated.
- [ ] Freeze new BOND emission until the resolution rate rises; a bond pick
      that never closes is a data-row, not a trade.
- [ ] Add a duration/maturity field check before any BOND cost model is
      attempted (currently no cost model exists for the class).

## COMMODITY — 20,412 rows, no cost model

- [ ] `null_pnl_share` 60.9% (12,437 of 20,412), `open_share` 63.3%,
      `null_closed_at_share` 63.3%.
- [ ] `duplicate_share` 45.2% (9,225 extra in 3,019 groups) — second-largest
      duplicate block after FOREX.
- [ ] `unlabelled_zero_pnl` 451 rows.
- [ ] `weekend_closes` 339 — futures/spot metals do trade Sunday evening; check
      whether those rows are Sunday-open mislabelled as closes before muting the
      gate.
- [ ] Build the cost model before quoting any COMMODITY edge: the class has
      none, so every "profitable" number in a report is gross.

## FUTURES — 973 rows, cleanest data in the estate (4/7 gates pass)

- [ ] `unlabelled_zero_pnl` 10 rows and `weekend_closes` 17 rows — both small
      enough to fix by hand this week; this is the class to use as the
      reference implementation for the others.
- [ ] Build the cost model (none exists) and measure PF on the 465 closed rows
      before adding any new futures strategy.
- [ ] Use FUTURES' gate profile as the regression fixture: if a change makes
      FUTURES fail, the change is wrong.

## INDEX / PREDICTION_MARKET / PENNY_STOCK / MEMECOIN — thin

- [ ] INDEX and PENNY_STOCK have no rows in the DB: either emit them or remove
      them from the canonical enum so `detect_asset_class` and the dashboards
      stop advertising classes that cannot appear.
- [ ] PREDICTION_MARKET: 4 rows prepared per sync, all from
      `pm_macro_expansion`/`polymarket_bts_consensus`; too thin for a WR/PF
      claim — track coverage (markets scraped vs picks emitted), not win rate.
- [ ] MEMECOIN: WR far below breakeven (last measured −0.507% net); the 4 rows
      with `stop_loss = 0` were cleaned today, but the class needs a design
      decision (paper-only, or drop) rather than more signal tuning.

---

## Cross-cutting (not per class)

- [x] **`label_drift` cleared** (2026-11-28T05:20Z). The `meme=1` was not a
      live emitter: it was one stale row, `hoffman_keltner_expansion::PEPE-USD::2026-09-26`
      from `alpha_engine_fast`, written before the sync chokepoint learned
      `meme → MEMECOIN` (2026-11-28). Relabelled to `MEMECOIN` with backup
      `ejaguiar1_backups.trading_picks_label_fix_meme_20261128T052055Z` and a
      `relabel_category` ledger row. The gate is PASS with no drift.
- [x] **`bad_side_stops` PASS in all seven classes** (CRYPTO/EQUITY/FOREX/ETF/
      BOND/COMMODITY/FUTURES). The `at_raw_picks` half of the sweep NULLed
      6,968 bracket fields, 2,481 of them from `incubator_gainer` writing a
      LONG-shaped bracket on SHORT rows. See
      `updates/2026-11-28-at-tables-bracket-sweep-and-regrowth.md`.
- [!] **Every bracket repair regrows until PR #1240 merges.** The
      `ON DUPLICATE KEY UPDATE … stop_loss = VALUES(stop_loss)` in
      `alpha_engine/mysql_trading_sync.py` rewrites the bad brackets from source
      JSON on every sync, and `_validate_bracket_geometry` exists only on the PR
      branch (0 occurrences on `origin/main`, 2 on the branch). 48 cleaned rows
      were restored within the hour at 04:59Z. Merging the PR is the only
      durable fix; until then, re-run the sweep after each sync rather than
      treating a new failure as a new defect.
- [x] **`empty_category` 67 → 0 and `label_drift` PASS** (2026-11-28T08:07Z).
      Two evidence rules cleared the pair the classifier cannot read — peer
      label (`JTO-USD2`, four CRYPTO siblings) and equity price universe
      (`BRK-B`, 1,367 rows in `equity_daily_ohlcv`) — and alias repair cleared
      14 lowercase forks (13 `prediction_market`, 1 `meme`). Backups
      `…trading_picks_label_fill_20261128T080640Z` (67 rows) and `…080758Z`
      (14 rows).
- [!] **Both labels regrow until PR #1240 merges.** 65 of the 67 were already
      repaired at 04:06Z and rewritten as `''` at 04:59/05:59/06:59Z, an hour
      apart, by `category = VALUES(category)`. `origin/main` also still has
      `_CATEGORY_KNOWN_PASSTHROUGH = {"meme", "index", "unknown"}`, which is
      why the `meme` row returned at 07:59Z. The branch guards the column and
      normalizes the aliases. Re-run
      `python3 tools/backfill_unknown_category.py --table trading_picks --apply`
      (idempotent) until then.
- [x] **`detect_asset_class` left alone.** A ticker-suffix rule was the first
      idea for `BRK-B`/`JTO-USD2`; two database-proof rules in the backfill tool
      solve the same rows without teaching the classifier a new guess. Revisit
      only if such symbols start arriving in volume.
- [x] **Sports betting removed from `ejaguiar1_stocks`** (2026-11-28T08:06Z).
      Scrapped for now: 17 tables / 22,061 rows dropped after a verified
      snapshot, and five workflow crons (the refresh writer plus four readers)
      disabled. Table count 469 → 453. No gate ever read those tables. See
      `updates/2026-11-28-empty-category-cleared-and-sports-db-scrapped.md`.
- [ ] The PHP live-monitor sports endpoints (`live-monitor/api/sports_*.php`)
      are still deployed on FTP and will error against the dropped tables — a
      deploy-side removal, not a repo change.
- [ ] Wire `tools/asset_class_audit_checks.py` into a nightly job so a gate that
      passes today cannot silently fail tomorrow without a card being raised.

---

**Provenance.** Gate counts: `tools/asset_class_audit_checks.py --skip-backtests`
(2026-11-28T04:05Z, 154,379-row `ejaguiar1_stocks.trading_picks`). Edge numbers:
session per-class table (EDGE = n ≥ 100, Wilson-95% low > 50%, PF ≥ 1.20; costs
0.03% equity, 0.25% crypto, 0.002% forex as measured this session). Duplicate
definitions: `duplicate_share` = extra rows inside identical
`(symbol, direction, created_at)` groups, as implemented in the gate.
