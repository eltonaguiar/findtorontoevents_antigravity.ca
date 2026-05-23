# TradingView Portfolio Management — 2026-05-17

**Generated:** 2026-05-17T00:07:48Z · **Operator:** claude-desktop (Claude Opus 4.7)
**Follow-up to:** `updates/2026-05-16-tv-portfolio-review-and-trades.md`
**Market window:** Sat 23:xx–Sun 00:xx UTC — crypto open; equity/ETF/FOREX/futures closed
(FOREX opens Sun ~21:00 UTC). Limit orders used for closed equity markets.

## Actions taken

### 1. Locked profit on winners — SL tightened (works while market closed; modify-order, no fill)

| Book | Symbol | Entry | Last | Old SL | New SL | Locked |
|------|--------|-------|------|--------|--------|--------|
| theswarm | CRWD | 540.00 | 594.08 | 519.00 | **575.00** | +6.5% |
| zerounderscore | LLY | 958.45 | 1,004.92 | 970.00 | **990.00** | +3.3% |
| HIGHFWWRABV55_SCOREABOVE50_V4 | KMI | 32.29 | 33.63 | 29.90 | **32.80** | +1.6% |
| HIGHFWWRABV55_SCOREABOVE50_V4 | KO | 78.12 | 80.82 | 76.51 | **79.50** | +1.8% |

All 4 verified post-modify. TP levels untouched. EURUSD/GBPUSD shorts on
HIGHF_V2 already sit at breakeven SL — left as-is (risk-free runners).

### 2. New crypto trade — OPUSDT Long (live market)

| Field | Value |
|-------|-------|
| Book | _MANUALBROKIE_CONV_TRUST6p4 ($100,205 balance) |
| Side / qty / entry | Long · 22,600 OP @ 0.1330 |
| Take profit / Stop loss | 0.1463 (+10%) / 0.1264 (−5%) |
| R:R | 2.0 : 1 |
| Notional | $3,006 (3% of book) |
| Pick | `ml_enhanced_OPUSDT_4h_D_ensemble_stack`, conf 0.69; live price = pick entry 0.134 (fresh) |

Filled unprotected (TV 3.1.0 order-ticket TP/SL does not bind) → fixed
immediately via Protect Position. Verified: TP 0.1463 / SL 0.1264 populated.

### 3. Equity limit order — PFE (closed-market, rests until Monday open)

| Field | Value |
|-------|-------|
| Book | _MANUALBROKIE_CONV_TRUST6p4 |
| Order | Buy LIMIT 120 PFE @ 24.85 |
| Take profit / Stop loss | 29.50 / 23.80 |
| Last close | 25.32 → limit is 1.85% below (buy-the-dip) |
| Notional if filled | $2,982 (3% of book) |
| Pick | swarm_picks.json — PFE Long, target 29.5 / stop 23.8 |

Placement returned `Placed: Buy 120 PFE @ 24.85 LIMIT`. **Verification gap:**
the working-order could not be re-read — the account-manager Orders tab was
not reachable via DOM selectors this session (only `Paper.positions-table` is
exposed; the Orders tab strip eluded enumeration). Confirm the resting order
on the Orders tab at next TV session.

### 4. Crypto "close losers" — assessed, NOT closed (deliberate)

Open crypto positions and their state:

| Position | Book | PnL | Distance to SL |
|----------|------|-----|----------------|
| BNB Long | HYROTRADER | −2.29% | 2.6% above SL |
| ETH Long | HYROTRADER | −1.77% | 3.2% above SL |
| BNB Long | theswarm | −0.88% | within band |
| AVAX Long | brokie | −2.72% | 2.4% above SL |
| BTC Long | TRUSTOURSCORE | ~0% | new (2026-05-16) |
| RENDER Short | __MANUALBROKIE_STRONG_CONV | −0.11% | new |

**None closed.** Each is a small drawdown inside its SL band with a valid
stop — a working trade, not a stop-out loser. Manually closing a −2% position
the strategy did not signal to exit just realizes loss early and discards the
TP/SL discipline. Stops will resolve them. Re-evaluate if any approaches SL.

## Net session result

- 4 winners' stops trailed up — locked profit, zero downside added.
- 1 new live crypto trade (OP), protected.
- 1 equity limit order resting for Monday (PFE).
- 0 working trades force-closed — correct discipline over churn.
- Earlier same-cycle: BTC long + RENDER short placed + protected
  (`updates/2026-05-16-tv-portfolio-review-and-trades.md`).

## Follow-ups

1. **`tv-portfolio-extract` / account-manager Orders tab** — DOM selectors for
   the bottom-panel tab strip (Positions / Orders / Order history / Balance /
   Journal) are stale on TV 3.1.0.7818. Only `Paper.positions-table` resolves.
   Working/limit orders cannot be verified until this is fixed.
2. Monday open: confirm PFE limit fill; reassess equity/FOREX books for adds
   once those markets reopen (FOREX Sun ~21:00 UTC, equity Mon 14:30 UTC).
