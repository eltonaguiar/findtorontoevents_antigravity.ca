# EQUITY — quant audit todo board (phase 2 of the per-asset-class programme)

Measured 2026-11-27 against the live payload (`/audit/data/dashboard_data.json`, generated 2026-11-27T17:36Z),
the live tribunal ledger (`/audit3/audit3_ledger.json`, 12:35Z) and `trading_picks` (`category='equity'`, MySQL 8.4.7).
Payload slice: EQUITY n=785 of the capped 3,500-row `recent_closed` list; DB: **14,474 rows**.

Legend: `[x]` passing · `[!]` **failing** · `[ ]` not yet checked.

## Phase 0 — Feeds, universe, provenance

- [x] Payload fresh (0.7 h), DB reachable, equity `last_close` 2026-11-27T00:00Z (daily cadence, acceptable).
- [!] **Universe is 38 symbols in the payload / 157 in the DB, and it is mega-cap only** — AMD 86 rows, AAPL 85, AMZN 68,
      JPM 63, GOOGL 57, XOM 51. A mega-cap-only universe is the textbook survivor-conditioned sample: gate 1 of the review's
      17-gate protocol is explicitly still red for this reason.
- [ ] Confirm no delisted name can ever appear: check whether any symbol in `trading_picks` is absent from the live listing
      file. Zero delisted names in the history is the defect, not a convenience.
- [!] **177 closes land on a Saturday or Sunday** in the DB (19 in the payload slice, 2.4%). US equity markets are shut; those
      timestamps are wrong, and any DTW/hourly statistic built on them is wrong too.

## Phase 1 — Row-level integrity (the "unreasonable data" pass)

- [x] Payload slice: `pnl_pct` null 0, `|pnl| > 50` 0, max +23.5 %, min −30.2 %.
- [!] **One resolved row with `pnl_pct = 0` in the slice, 3,633 in the DB (25.1% of all equity rows) and 27 with a closed
      status but NULL `closed_at`.** A quarter of the equity book carries a zero PnL — that is not "flat", that is unresolved
      data wearing a number.
- [!] **DB: 6,248 null PnL of 14,474 (43.2%) and 10,716 null `closed_at` (74%).** Only ~26% of the equity table is closed.
- [!] `status = OPEN` 10,653 of 14,474 (73.6%) — the ghost-row mass again.
- [!] **Stops almost never fire: SL_HIT 99 vs TP_HIT 458 (a 4.6:1 win-to-stop ratio).** In the payload the split is
      SL_HIT 338 / TP_HIT 213. Two different books: the DB resolver barely registers stops, the payload slice is stop-heavy.
      Reconcile before any WR is quoted.
- [!] **One bracket for everything: 771 of 785 rows (98.2%) use TP +8% / SL −5%** regardless of symbol volatility. Not
      vol-scaled, and the fixed R:R of 1.6 is what the WR is really measuring.
- [!] **Holding period contradicts the labels**: `age_hours` p50 = 3,027 h (~126 days), p90 = 5,788 h (~241 days), while
      strategies are named `-scout`, `vol-contraction-scout`, `adx-trend-scout`. Daily-bar swing is fine; calling it a scout is not.
- [!] **Direction skew 776 LONG / 9 SHORT (1.1%)** — in a book with `regime_*_bear` strategies. Either shorts are blocked or
      they never fire; either way the long side is unhedged and the WR is a beta artifact in disguise.
- [!] 3 duplicate `(symbol, direction, entry)` rows in the slice; 275 DB rows missing a TP or SL leg.
- [ ] **Corporate actions**: run every entry/exit against split- and dividend-adjusted bars. An unadjusted 4:1 split reads as
      −75 %. None of the fields (`sector`, `volatility_atr`) proves the prices are adjusted.
- [ ] **Look-ahead on earnings**: `earnings drift` / `consecutive beats` strategies must enter at the *next session open* after
      the announcement. Verify by checking whether any entry timestamp falls inside the announcement bar.
- [ ] **Short side only**: locate/borrow cost and hard-to-borrow names are not modelled anywhere in `trading_picks`.

## Phase 2 — Cost & execution

- [ ] Charge commission + half-spread + square-root impact per symbol ADV (the review found two repo constants 5× apart,
      5.0 vs 25.0 bp — pick one and record it).
- [ ] Sub-$5 names: spread dominates. Confirm no penny/micro-cap row is quoted without a liquidity flag
      (`volatility_atr` exists; ADV does not).
- [ ] Model the after-hours fills: a 16:05 signal filled at the 16:00 print is not tradeable.
- [!] `after_cost_net_per_trade` is null on sampled rows, so the "net" equity headline (+0.085 %/trade) may be gross.

## Phase 3 — Signal & statistics

- [ ] Reproduce the documented `stocks_rsi2_pullback` reversal: 62.9 % WR on raw rows → **33.9 % after dedupe** (n=140).
- [ ] `smart_money_accumulation` is 3,764 of 14,474 DB rows (26%) — publish its single-source share before any class number.
- [ ] Dedupe → net expectancy → block-bootstrap CI → DSR with the true trial count → PBO.
- [!] Power: **`required_n` = 35,533** for EQUITY at the observed effect (+0.085 %, CI −0.53/+0.70). Nothing can pass this
      window; say so in the tile instead of showing a WR.
- [ ] Sector concentration: `sector` exists on every row — compute Herfindahl per strategy and publish.

## Phase 4 — Forward gate & ops

- [ ] Only cells with ≥100 forward rows post-registration may display a rate. Today: zero equity cells qualify.
- [ ] Fix the DB/payload divergence (SL_HIT 99 vs 338) — one of the two resolvers is wrong about stops.
- [ ] Alert when `status='OPEN'` share rises above 60 % (it is 73.6 %).

## Re-run

```bash
python3 - <<'PY'
import json, collections
d = json.load(open('/tmp/dd_live.json'))
C = [p for p in d['picks']['recent_closed'] if (p.get('asset_class') or '').upper() == 'EQUITY']
print(len(C), collections.Counter(p['exit_reason'] for p in C))
print("zeros", sum(1 for p in C if p.get('pnl_pct') == 0),
      "weekend closes", sum(1 for p in C if p.get('closed_at') and p['closed_at'][:10] and
      __import__('datetime').datetime.fromisoformat(p['closed_at'].replace('Z','+00:00')).weekday() >= 5))
PY
```

_Judge-side note: the review site's own equity verdict is WEAK with an unmeasurable effect, and its #4 ranking line
("everything else — 69 picks, 10 classes: NO") applies to this class too._
