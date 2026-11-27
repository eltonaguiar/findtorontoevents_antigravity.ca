# CRYPTO — quant audit todo board (phase 1 of the per-asset-class programme)

Measured 2026-11-27 against the **live** payload (`https://findtorontoevents.ca/audit/data/dashboard_data.json`,
generated 2026-11-27T17:36Z, 27.4 MB) and the **live** tribunal ledger
(`https://findtorontoevents.ca/audit3/audit3_ledger.json`, generated 2026-11-27T12:35Z, 722,829 B).
Page slice used for row-level checks: `picks.recent_closed`, CRYPTO n=1,835 (the payload caps this
list at 3,500 rows across all classes — it is not the full 8,398-row ledger).

Legend: `[x]` checked and passing · `[!]` checked and **failing** · `[ ]` not yet checked.

## Phase 0 — Feeds, provenance, freshness (do this first; every number downstream depends on it)

- [x] Live dashboard payload is fresh: `generated_at` 17:36Z, `data_freshness.age_hours` 0.7, `stale_warning` false.
- [!] **Repo copy is 134.4 h stale** (`audit_dashboard/data/dashboard_data.json`, 2026-11-22T04:00Z). Anyone reading the
      repo instead of the site is auditing a week-old book. Either refresh it in CI or delete it and point to the URL.
- [!] `payload_lag_seconds` = 8,459 s (2.35 h) despite a 0.7 h payload age — the lag field and the age field disagree,
      so one of them is measured from the wrong clock. Reconcile before quoting either.
- [!] `https://findtorontoevents.ca/audit/data/forward_observations.json` → **404**, yet audit3's forward gate reads
      `reports/forward_observations.jsonl` and audit2's page says `reports/` is not web-served. Publish a hosted copy so
      the gate is reproducible from outside the runner.
- [!] `/audit3/data/audit3_ledger.json` → 404; only `/audit3/audit3_ledger.json` and `/audit/data/audit3_ledger.json` (200,
      identical 722,829 B) resolve. Pick one canonical path and redirect the others.
- [x] Database is alive and reachable directly: MySQL 8.4.7 at `mysql.50webs.com` / `ejaguiar1_stocks`, 465 tables;
      `trading_picks` has **154,166 rows**, CRYPTO 43,838 of them, latest `closed_at` 2026-11-27T17:43Z (fresh).
- [!] **The database is mostly unresolved**: `trading_picks.status` = OPEN **100,475** (65%), TIME_EXIT 33,650, TP_HIT 7,374,
      LOST 6,061, SL_HIT 4,023, EXPIRED 2,530, ACTIVE 53. That is the ghost-row mass the review site warned about, and it is
      still there, not a legacy artifact.
- [!] **Class labels are case-inconsistent in the DB**: `CRYPTO`, `FOREX`, `COMMODITY`, `ETF`, `FUTURES` are upper-case but
      `equity` (14,474) and `bond` (1,798) are lower-case, plus `index`, `meme`, `MEMECOIN`, `prediction_market`, and 2,641
      rows with an **empty** category. Any `group by category` silently splits classes. Normalise to one enum.
- [!] **Status enum mismatch**: the DB has no `WON` status at all (wins are `TP_HIT`/`TIME_EXIT`), while the dashboard payload
      uses `WON`/`LOST`. Two different notions of "won" are being reported side by side.
- [!] Same DB health file reports **22,947 ghost rows** across 10 cohorts (10 MEMECOIN/meta_strategy) — a non-zero count is
      defined as a failure in that file's own contract, so the health page is failing its own check and saying "ok".
- [ ] Add a CI assert: every public feed age < 2 h, every documented path returns 200, ghost-row count == 0. Fail the build,
      do not just paint a tile amber.

## Phase 1 — Row-level integrity (the "unreasonable data" pass)

- [x] `pnl_pct` null/non-numeric in the crypto slice: **0**.
- [!] **But the DB itself is mostly null PnL**: `trading_picks` CRYPTO has **15,879 null `pnl_pct` of 43,838 (36.2%)**,
      1,002 `pnl_pct = 0` (2.3%), **21,220 rows with null `closed_at` (48%)**, and 231 rows missing a TP or SL. FOREX is worse:
      41,853 null PnL of 64,650 and 46,781 null `closed_at`. The dashboard slice is the clean 4% of the table — every
      headline computed off it is a selection, not the book.
- [!] 27 rows are resolved (`WON`/`LOST`) with `pnl_pct = 0`, and 93 rows carry a closed status with `closed_at` NULL.
- [x] **FIXED 2026-11-27** (`updates/2026-11-27-flat-rows-published.md`): auto-expired rows are now published
      as `status=FLAT` / `exit_reason=EXPIRED` (capped at 15% of the closed list) and counted in
      `summary.flat_published_rows`; they stay out of WR/PF by design.
- [!] `pnl_pct == 0` in the crypto slice: **0**, which is not good news — the summary says `zero_pnl_count` **138**
      (`zero_pnl_share_pct` 1.52) and `resolver_anomalies.expired_zero_pnl_rows` **3,701**. The zeros exist and are being
      filtered *out of the view*, so a reader sees a cleaner book than the resolver produced. **Publish FLAT rows** with
      `exit_reason=EXPIRED` instead of excluding them, and keep them in the denominator as a separate column.
- [x] Missing `entry_price` / `take_profit` / `stop_loss` / `exit_price` / `closed_at` / `entry_time` in the slice: 0 each.
- [!] Ledger-wide that is not true: the review site records **39,508 resolved rows with no entry/TP/SL**. Those rows cannot be
      re-derived and must be quarantined, not counted.
- [!] **Stops on the wrong side: 18 LONG with stop ≥ entry, 13 SHORT with stop ≤ entry** (31 rows, 1.7% of crypto). These are
      guaranteed-loss or guaranteed-win rows; quarantine and re-derive from bars.
- [!] **`closed_rows_missing_closed_at`: 1,342** (live). A row with no close time cannot enter any time-based statistic.
- [!] **`stale_exit_beyond_planned_stop`: 46** and **`clamped_loss_rows`: 23** — exits printed after the stop should have filled.
      Re-resolve intrabar with SL-wins-ties, then compare.
- [x] Duplicate rows on `(symbol, direction, entry_price)`: **55 extra rows / 52 groups (3.0%)**; duplicate `id`s: 0.
- [!] **Duplicate inflation is the headline defect**: the review site measured 67,022 resolved rows collapsing to 2,864 unique
      picks (95.7% duplicates). In this slice it is only 3.0%, so the dedupe key used here is *weaker* than the one used there.
      Adopt the strict key (symbol + direction + entry + opened bar) and publish the dedupe rate per strategy.
- [!] **Exit mix is not a bracket book**: SL_HIT 767, **FORCE_CLOSED 548 (29.9%)**, TP_HIT 386, TIME_EXIT 127, UNKNOWN 7.
      Three in ten crypto closes are forced, and forced exits carry no cost model. Break FORCE_CLOSED out by reason.
- [!] **Fixed bracket, not vol-scaled**: the modal `(TP%, SL%)` is **2.5 / 1.5** (364 rows) with 6.0/5.0 next (73). A constant
      bracket across BTC and a micro-cap is a sizing bug; replace with ATR- or realized-vol-scaled brackets.
- [!] **Horizon mismatch**: median `age_hours` is **584 h (~24 d)**, p10 90 h — but the strategy names say `scalp`,
      `-scout`, `rapid_fire`. Either the labels or the holding period is wrong; both feed the WR by strategy.
- [!] **Direction gate leak**: 495 of 1,835 crypto rows (27%) are SHORT while the Smart Picks page states "crypto shorts
      blocked (15.3% WR live)". Find the path that bypasses the gate.
- [ ] Coverage check: for each crypto row, assert `exit_price` lies between the bar's low/high on `closed_at` (needs bars).
- [ ] Assert sign consistency: `WON` ⇒ `pnl_pct > 0`, `LOST` ⇒ `pnl_pct < 0` (the DB health file claims 0 contradictions;
      prove it per row, per class).
- [ ] Assert `entry_time <= closed_at` and `0 < age_hours < 20000` on 100% of rows.

## Phase 2 — Universe & survivorship

- [ ] Count symbols with < 20 rows; those WRs are noise and should not be ranked.
- [!] One symbol carries both **+500%** and **−99%** closed rows (`HYPEUSDT`, `copy_hl_lb_none`, and `-99.0` clamp rows across
      HYPE/TRX/BNB/mercury2). +500 and −99 are clamp artifacts, not PnL. Add a `pnl_clamped` boolean and exclude clamped rows
      from every rate, or quote the unclamped distribution.
- [ ] Delisting / rug check: crypto has no survivorship filter at all — list symbols that stopped emitting mid-window and
      check whether they are disproportionately the losers.
- [ ] Concentration: BTCUSDT is 12.9% of total crypto PnL; top-3 symbols must be reported alongside every class number.

## Phase 3 — Signal & labelling

- [ ] Reproduce the ML calibration inversion on the live payload (crypto `conf ≥ 0.90` → 14.4% WR vs `0.50–0.60` → 60.3%):
      if it still holds, the confidence field is anti-predictive and must be dropped from sizing.
- [ ] Intrabar replay of the S/A score bands (documented: 23–24% of "wins" flip to SL-first; S-tier 8/8 → 0% true WR).
- [ ] Label audit for `claude_gainer_st` EXPIRED→WON mislabels (the review measured the raw-DB equivalent at WR 33%).
- [ ] Recompute every strategy's WR on unique picks only and publish the delta vs the raw-row WR.

## Phase 4 — Cost & execution

- [ ] Cost of record is **9.92 bp/trade** for crypto in audit3 and the 2× stress gate fails on every class. Re-derive with
      live funding, taker fees, and square-root impact at realistic size for a $1,000 book.
- [ ] Funding/borrow is not modelled on the 27% SHORT book; a perp short pays funding — add it or drop the shorts.
- [ ] Check the `after_cost_net_per_trade` field: it is `null` on sampled rows, so "net" headlines may be gross.

## Phase 5 — Statistics (the gates)

- [ ] Dedupe → compute net expectancy with a block bootstrap CI → DSR with `n_trials` (audit3 used 658) → PBO via CSCV.
- [ ] Power: CRYPTO `required_n` = **1,674** trades at the observed effect size; publish it next to every win rate so nobody
      sizes on n=37.
- [ ] Regime split (TRENDING_UP/DOWN/RANGING observed 3/18/12 trades — far too thin; widen the window before claiming
      regime conditioning).

## Phase 6 — Forward gate (the only promotion path)

- [!] `POD-CRYPTO-VWAP-REVERSION` has **n_forward = 2** against a `min_n` of 100, and is registered as `observe` — it can never
      promote. Decide: promote it to `pre_registered` or retire it.
- [ ] Host the forward ledger (Phase 0) so `n_forward` is auditable by anyone.
- [ ] Enforce: no cell may display a WR without `n` and `required_n` in the same tile.

## Phase 7 — Ops

- [ ] Resolver freshness SLA: `last_alpha_scan` vs `last_dashboard_build` gap must be < 1 h (currently 44 min — OK, keep it).
- [ ] Kill-switch dry run: replay the last 30 days and confirm KILL verdicts fire before a strategy bleeds > 10%.
- [ ] Publish a one-page "what we would actually buy" that names only cells passing Phase 5 + 6 — today that set is empty.

## How to re-run these checks

```bash
# live payload + ledger
curl -s https://findtorontoevents.ca/audit/data/dashboard_data.json -o /tmp/dd.json
curl -s https://findtorontoevents.ca/audit3/audit3_ledger.json -o /tmp/a3.json

python3 - <<'PY'
import json, collections
d = json.load(open('/tmp/dd.json'))
C = [p for p in d['picks']['recent_closed'] if p.get('asset_class') == 'CRYPTO']
print("n", len(C), "| zero pnl", sum(1 for p in C if p.get('pnl_pct') == 0))
print("bad stops", sum(1 for p in C if p.get('stop_loss') and p.get('entry_price')
      and ((p['direction'] == 'LONG' and p['stop_loss'] >= p['entry_price'])
        or (p['direction'] == 'SHORT' and p['stop_loss'] <= p['entry_price']))))
print("exits", collections.Counter(p.get('exit_reason') for p in C).most_common())
PY
```

_Every number above was read from the payloads named at the top; none is estimated. Where a figure is chain-of-custody
uncertain, it is marked with the source that reports it (review site vs ledger vs db_health.json)._
