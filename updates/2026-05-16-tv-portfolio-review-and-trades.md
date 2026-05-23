# TradingView Portfolio Review + New Trades — 2026-05-16

**Generated:** 2026-05-16T22:46:00Z · **Operator:** claude-desktop (Claude Opus 4.7)
**TV:** Desktop 3.1.0.7818, CDP 9223 → 9222 forwarder (`tools/tv_cdp_proxy.py`)
**Market window:** Saturday — crypto open; equity / ETF / FOREX / futures closed (positions frozen).

## 1. Portfolio Review — all 13 paper books

Enumerated via the account dropdown. **Selector drift fixed:** TV 3.1.0.7818 moved the
account-row class from `div.middle-RDCgMoEQ.hasTitle-RDCgMoEQ` to
`div.middle-fY6nuScj.hasTitle-fY6nuScj`, and the dropdown opens only on a full
pointer-event sequence (`pointerdown`+`mousedown`+`mouseup`+`click`) — a bare
`.click()` no longer opens it. `tv-account-switch` skill needs updating.

| # | Portfolio | Open positions | Protected? |
|---|-----------|----------------|-----------|
| 0 | HIGHFWWRABV55_SCOREABOVE50_V3 | 0 | — |
| 1 | HIGHFWWRABV55_SCOREABOVE50_V2 | 2 — EURUSD, GBPUSD shorts | ✓ both |
| 2 | _MANUALBROKIE_CONV_TRUST6p4 | 0 | — |
| 3 | __VERIFIEDALPHA | 1 — AUDUSD short | ✓ |
| 4 | __MANUALBROKIE_STRONG_CONV | 0 → 1 (new RENDER short) | ✓ |
| 5 | TRUSTOURSCORE | 1 → 2 (new BTC long) | ✓ both |
| 6 | HYROTRADER | 2 — BNB, ETH longs | ✓ both |
| 7 | HIGHFWWRABV55_SCOREABOVE50 | 0 | — |
| 8 | HIGHFWWRABV55_SCOREABOVE50_V4 | 7 — equity/ETF longs | ✓ all 7 |
| 9 | zerounderscore | 2 — BAC, LLY longs | ✓ both |
| 10 | The Leap Crypto | skipped (retired account) | — |
| 11 | brokie | 1 — AVAX long | ✓ |
| 12 | theswarm | 7 — mixed L/S | ✓ all 7 |

**Result: 23 pre-existing positions across 8 books — every one carries TP + SL.
Zero unprotected violations. Zero inverted TP/SL.** The TP/SL discipline from the
prior sessions is holding.

### Notable positions

- **theswarm CRWD Long** +216.32 USD (+10.01%) — last 594.08 vs TP 601.00, ~1.2% from
  target. Strongest open winner. Let TP fire; optionally trail SL up to lock the gain.
- **HIGHFWWRABV55_SCOREABOVE50_V2** — EURUSD short +1.30% and GBPUSD short +1.64%, both
  with SL parked 1 pip above entry (breakeven lock) — risk-free runners.
- **zerounderscore LLY Long** +4.85%, SL 970.00 sits above entry 958.45 — a profit-locking
  trailing stop, valid (SL < last 1004.92). Not inverted.
- **theswarm TLT Long** −160.68 USD (−2.09%) — biggest open drawdown, still inside SL band.
- No position is near its stop. No close candidates this review. Equity/FOREX/futures
  books are frozen (weekend) — no action possible until Monday open regardless.

## 2. New Trades Placed (crypto — only open market)

Picks sourced from `alpha_engine/data/active_picks.json` (12 CRYPTO candidates).
Avoided BNB / ETH / AVAX — already concentrated across HYROTRADER / theswarm / brokie.

### Trade 1 — TRUSTOURSCORE · BTCUSDT Long

| Field | Value |
|-------|-------|
| Symbol / side | BINANCE:BTCUSDT · **Long** |
| Qty / entry | 0.057 BTC @ 78,224.71 |
| Take profit | 82,135.00 (+5.0%) |
| Stop loss | 76,268.00 (−2.5%) |
| R:R | 2.0 : 1 |
| Notional | $4,458 |

**Pick:** `prediction_market_consensus`, **confidence 0.778** — squarely in the 0.75–0.79
sweet spot (87.4% historical WR; 0.90+ is the overconfidence danger zone).
**Size justification:** 5% of the ~$90K TRUSTOURSCORE book. TRUSTOURSCORE charter is
5–10% (high-conviction only); sized at the floor because it is a single uncorrelated
crypto add to an equity-heavy book, and BTC carries the book's largest single-name
notional. TP/SL = TRUSTOURSCORE rule (2× ATR / 1× ATR, BTC ATR ≈ 2.5%).

### Trade 2 — __MANUALBROKIE_STRONG_CONV · RENDERUSDT Short

| Field | Value |
|-------|-------|
| Symbol / side | BINANCE:RENDERUSDT · **Short** |
| Qty / entry | 43 RENDER @ 1.832 |
| Take profit | 1.722 (−6.0%) |
| Stop loss | 1.905 (+4.0%) |
| R:R | 1.5 : 1 |
| Notional | $78.77 |

**Pick:** `inverse_ml_enhanced_RENDERUSDT_4h_D`, confidence 0.70. Price had already moved
3.7% in the short's favour since the pick's reference entry (1.903 → 1.832) — confirmed
downward momentum upgrades a sub-sweet-spot signal.
**Size justification:** 4% of the $1,987.14 __MANUALBROKIE_STRONG_CONV book. Downsized
from the 5–10% brokie default because confidence 0.70 is below the 0.75 sweet spot and
this is a single-strategy ML short. Adds a SHORT to balance the book's net-long crypto
exposure.

### Both trades — protection note

Both market orders filled **unprotected** — the TP/SL entered in the order ticket did
NOT carry onto the position (a known TV 3.1.0 behavior). Each was immediately fixed via
the inline Protect Position panel (P1 row-target → P2 toggles on → P3 `execCommand`
insertText → P4 Confirm → P5 verify). Final positions table confirms TP + SL populated
on both. **No position left unprotected at any point a scan would catch.**

## 3. Lessons / Follow-ups

1. **`tv-account-switch` skill is stale** — account-row class `RDCgMoEQ` → `fY6nuScj`,
   and the dropdown needs a pointer-event sequence, not `.click()`. Update the skill.
2. **Order-ticket TP/SL does not bind to the filled position** on TV 3.1.0.7818 — every
   market order must be followed by the Protect Position flow. `tv-paper-trade` Step 6
   already warns this; treat it as the rule, not the exception.
3. Portfolio hygiene is good — 23/23 prior positions protected. The repeated-violation
   pattern from earlier sessions is resolved.
