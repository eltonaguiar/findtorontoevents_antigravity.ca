# FOREX — quant audit todo board (phase 3 of the per-asset-class programme)

Measured 2026-11-27 against the live payload (generated 2026-11-27T17:36Z), the live tribunal ledger (12:35Z) and
`trading_picks` (`category='FOREX'`). Payload slice n=236; **DB 64,650 rows** — the largest class in the database and the
worst in the ledger: **KILL, net −0.142 %/trade, PF 0.60, n=295**.

Legend: `[x]` passing · `[!]` **failing** · `[ ]` not yet checked.

## Phase 0 — Feeds & provenance

- [x] DB reachable; FOREX `last_close` 2026-11-26T09:59Z (a day behind — FX trades ~24/5, so this is stale by roughly one session).
- [!] **The AUDJPY forward clock is blocked on a dead price feed since 2026-02-09** (review site: 34 closed rows, needs 48 to
      reach the DSR 0.95 gate). The strongest statistical case in the estate is unmeasurable — fix the feed or retire the claim.
- [!] **776 DB closes fall on a Saturday or Sunday** (6 in the payload slice). Spot FX closes Friday ~22:00 UTC and reopens
      Sunday ~22:00 UTC; a Saturday close cannot exist. Either the timestamp is UTC-vs-broker-time, or the bar source is wrong.
- [ ] Record the quote source per row (broker feed vs `=X` proxy vs mid). `EURUSD=X` is an indicative mid, not a tradeable
      price — every PnL computed from it overstates fill quality.

## Phase 1 — Row-level integrity (the "unreasonable data" pass)

- [x] Payload slice: null PnL 0, `|pnl| > 50` 0, range −2.3 % … +3.8 % (plausible for unlevered FX).
- [!] **39 of 236 payload rows (16.5 %) and 2,993 DB rows have `pnl_pct = 0`.** In FX a zero is almost always an unresolved
      row, not a flat trade; publish them as FLAT/EXPIRED, not as closed.
- [!] **8 rows in the slice have the stop on the wrong side** (LONG stop ≥ entry or SHORT stop ≤ entry).
- [!] **Inverted brackets exist: 29 rows carry TP −3.0 % / SL −2.0 %** (both negative) and 114 carry +1.5 % / −1.0 %. A
      negative take-profit on a LONG is a guaranteed-loss bracket; there is no validation anywhere that rejects it.
- [!] **Stops essentially never resolve in the DB: SL_HIT 33 vs TP_HIT 1,342 (a 0.8 % stop-out rate)**, while the payload
      slice shows SL_HIT 133 / TP_HIT 56. The DB resolver ignores or mis-detects stops on FX; the payload slice is the more
      believable of the two and still fails.
- [!] **DB: 41,853 null PnL of 64,650 (64.7 %) and 46,781 null `closed_at` (72.4 %)**; `status='OPEN'` is 46,729 (72.3 %).
- [!] **Holding period p50 = 3,530 h (~147 days)**, p90 6,230 h — this is not `london-breakout-scout` or
      `forex-rsi-ema-scout` behaviour; the names promise intraday and the rows deliver half a year.
- [!] `unknown` is the 4th-largest strategy by row count (28 in the slice) — unnamed emitters cannot be audited or killed.
- [ ] Verify no row was opened while the market was shut (Friday 22:00 → Sunday 22:00 UTC).

## Phase 2 — FOREX-specific cost model (the part that decides the class)

- [ ] **Swap/carry must be charged**: every position held >1 day pays or earns rollover on both legs. A 147-day median hold
      means carry dominates the PnL, and today it is not modelled at all.
- [ ] Spread by session: London/NY overlap tight, Asia/rollover wide. `london-breakout-scout` (64 of 236 rows) needs the
      22:00–07:00 spread, not a 24h average.
- [ ] **News-time slippage**: NFP/CPI/rate decisions widen EURUSD to 10–30 pips. Add an event-window stress bucket.
- [ ] Commission/lot minimum: at a $1,000 book, 0.01-lot minimums and $2–7 round-turn commissions are a large fraction of
      any edge — model at that size, not at institutional notional.
- [!] `after_cost_net_per_trade` is null on sampled rows: the −0.142 % is gross of spread.

## Phase 3 — Signal & statistics

- [!] Killed cells (audit3): **Breakout Momentum** LONG (n=37, WR 40.5 %, PF 0.40), **forex_zscore_200d_fade** LONG
      (n=36, WR 5.6 %), **MeanReversionBB SHORT** (n=29, WR 0 %), **AUDUSD** LONG (n=22, WR 22.7 %).
- [!] `forex_zscore_200d_fade` is still the 3rd-largest emitter in the DB (12,171 rows) **after** being killed in the tribunal.
      A kill must stop the emitter, not just grey the card.
- [ ] Reproduce the polyglot claim that FOREX WR 57.8 % coexists with PF 0.85 (tight-TP / wide-SL asymmetry) on the current
      payload; if it holds, stop quoting WR for FX entirely and quote PF.
- [!] Power: `required_n` = **227** at the observed effect; n=295 exists, yet the CI is entirely below zero — so this class is
      not underpowered, it is negative. Say that plainly.
- [ ] Session-of-day split (Asia/London/NY/overlap) with per-session spread cost.

## Phase 4 — Forward gate & ops

- [ ] Only pre-registered pods with ≥100 post-registration rows may display a rate. FOREX has none, and the AUDJPY pod cannot
      accrue until the feed is repaired.
- [ ] Add a bracket validator that rejects TP ≤ 0 on a LONG, SL ≥ entry on a LONG, and any TP/SL on the wrong side — before
      the row is stored, not after.
- [ ] Kill-switch: enforce emitter shutdown on KILL (see `forex_zscore_200d_fade`).

## Re-run

```bash
python3 - <<'PY'
import json, collections, datetime as dt
d = json.load(open('/tmp/dd_live.json'))
C = [p for p in d['picks']['recent_closed'] if (p.get('asset_class') or '').upper() == 'FOREX']
print("n", len(C), "zeros", sum(1 for p in C if p.get('pnl_pct') == 0))
print(collections.Counter(p['exit_reason'] for p in C).most_common())
print("inverted brackets", sum(1 for p in C if p.get('direction') == 'LONG'
      and p.get('entry_price') and p.get('take_profit') and p['take_profit'] <= p['entry_price']))
PY
```

_Judge-side note: unlike CRYPTO (killed on a negative CI) and EQUITY (unmeasurable power), FOREX is killed **and** emitting
at industrial scale — 64,650 rows. It is the single largest source of noise in the estate._
