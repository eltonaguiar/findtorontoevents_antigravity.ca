# REALTIMECHALLENGE — buffy — 2026-11-22 03:58 EST

**Status: LIVE, positions open, first fills taken on real market data.**
Book: `$10,000` paper · Tag: `buffy` · State: `data/realtime_challenge/buffy.json`

This is the prototype of the live-verification challenge: can a mechanical rule
open AND close a position on live markets, in a short window, and come out ahead
after the costs a real account would pay? Every round is recorded whether it
wins or loses, because a challenge that only reports winners proves nothing.

## 1. Why this venue

Crypto spot because the market is open now. An equity sprint would have to wait
for an opening bell and then sit in a 6.5-hour session; the point of the
challenge is to test the *machinery* and the *rule* today, not to schedule
around a market calendar. Venue is Binance spot via its public endpoint —
no API key, no account, no order ever sent. Fills are simulated.

## 2. Frozen rules (registered before the first fill)

| item | value |
|---|---|
| universe | BTC, ETH, SOL, BNB, XRP, ADA, DOGE, LINK (USDT) |
| timeframe | 5-minute bars, 200-bar lookback |
| entry filter | `close > EMA20 > EMA60` **and** `40 <= RSI14 <= 72` **and** last 3 bars net positive |
| ranking | best 3-bar return among qualifying names |
| slots | 3, one name each, 1/3 of the book per slot |
| take-profit | **+0.60 %** |
| stop-loss | **−0.40 %** |
| time stop | **60 minutes**, measured from the fill |
| tie-break | if one bar touches both TP and SL, the **stop** is assumed to fill first |
| fees | 10 bps per side (Binance taker) |
| slippage | 2 bps per side |
| round-trip cost | **24 bps** |

Net of costs: a TP is `+0.36 %`, a stop is `−0.64 %`. The rule therefore needs
**> 64 % accuracy** to break even, which is deliberately demanding — a rule that
only looks good before costs should fail here, and I want it to fail visibly.

## 3. What actually happened

Scan at `2026-11-22T08:58:59Z` (03:58 EST):

| symbol | fill | TP | SL | time stop | outcome at last mark |
|---|---|---|---|---|---|
| ETHUSDT | 1687.257384 | 1697.04152 | 1680.17232 | 09:58:59Z | open, −0.035 % |
| BTCUSDT | 59803.668342 | 60150.46026 | 59552.54316 | 09:58:59Z | open, −0.082 % |

Only **2 of 3** slots filled: SOL, BNB, XRP, ADA, DOGE and LINK failed at least
one filter (typically RSI outside 40–72 or price below EMA20), so the rule abstained
rather than being forced to trade. That is the intended behaviour.

## 4. Success criteria

Two separate questions, deliberately not conflated:

1. **Machinery (this round).** Did the harness fetch live prices, size a position,
   set TP/SL, honour the tie-break, charge 24 bps and write an auditable ledger?
   — Verifiable from the state file; that part is already true.
2. **Edge (needs many rounds).** Does the rule make money net of costs across a
   population? A 2-trade window is noise: with TP `+0.36 %` and SL `−0.64 %` net,
   two winners prove nothing. **Round 1 cannot establish an edge and will not be
   reported as one.** It establishes that the experiment is running.

## 5. What would count as evidence

- ≥ 100 closed challenge trades in one rule/timeframe combination (`G8`).
- Mean net return per trade with a block-bootstrap CI-LB above zero — the same
  gate the backtests use, not a different, friendlier one.
- Split-half stability, and a benchmark leg (BTC buy-and-hold over the identical
  window) recorded for every trade.

## 6. Automation

`.github/workflows/realtime-challenge.yml` runs `cycle` every 15 minutes: mark
open positions against live prices, close anything that hit TP/SL/time, open new
slots if the rule qualifies, then commit the ledger with `[skip ci]`. Manual runs:

```
python3 tools/realtime_challenge.py cycle  --tag buffy
python3 tools/realtime_challenge.py status --tag buffy
python3 tools/realtime_challenge.py report --tag buffy
```

## 7. Honest limitations

- Paper only. No order-book impact, no partial fills, no funding paid on spot, no
  exchange downtime. A real account would see worse fills in fast markets.
- One 60-minute window, two names. Statistically meaningless as evidence of edge.
- The 5-minute/60-minute horizon is the *hardest* place to find an edge after
  24 bps of costs; a negative result here is the expected result, and the useful
  output is the machinery plus a cost-calibrated ledger.
- Peers running the same challenge should compare **cost assumptions** first: a
  rule that shows +0.3 %/trade on 4 bps round-trip and −0.2 % on 24 bps is not a
  disagreement about the market, it is a disagreement about fees.

## 8. Sprint round 1 — opened AND closed, on live data

Book `sprint1` (separate from `buffy` so the 60-minute rule above is untouched).
Opened `09:02:54Z`, flattened `09:13Z` with the labelled exit `SPRINT_CLOSE`.

| symbol | entry | exit | gross | net (after 24 bps) | P&L on $3,333 |
|---|---|---|---|---|---|
| BNBUSDT | 546.619302 | 546.100758 | −0.095 % | **−0.295 %** | −$9.83 |
| XRPUSDT | 0.92638524 | 0.925615 | −0.043 % | **−0.283 %** | −$9.44 |
| ETHUSDT | 1686.3372 | 1684.203092 | −0.087 % | **−0.327 %** | −$10.89 |

**Result: −$30.16 on $10,000 = −0.302 %. No profit.** All three closed red.

The decomposition is the useful part. Mean **gross** move was −0.075 %; mean
**net** was −0.302 %. So **0.24 of the 0.30 points of loss was the cost floor
itself** — roughly 80 % of the loss was fees and slippage, 20 % was the market
moving against the position. The rule picked direction close to a coin flip,
which is what a 5-bar EMA/RSI filter should be expected to do.

Why it cannot work at this horizon, in one line of arithmetic: a TP of +0.60 %
has to be reached before a 60-minute time stop, while the round-trip cost is
0.24 % — so the rule needs a **0.84 % favourable move** to bank 0.36 %, and the
typical 10-minute move on these majors is 0.1–0.2 %. The cost floor is larger
than the signal. This is a structural statement about 5-minute crypto scalping
with taker fees, not a bug in the harness.

What the round *did* prove: the machinery opens, marks, honours TP/SL/time, and
closes with an auditable ledger, and the realised costs match the stated model to
the basis point. That was the point of round 1.

The `buffy` book from §3 stays open under its frozen rule and will exit via
TP/SL/time; it is monitored by the workflow, not by hand.

## 9. Round 2 — both slots resolved at TARGET, on live data

The two slots left open in §3 were marked by `tools/realtime_challenge.py` at
`09:41Z` and `09:42Z` against live 5-minute Binance bars.

| symbol | entry | TP | exit | reason | net | P&L |
|---|---|---|---|---|---|---|
| BTCUSDT | 59803.668342 | 60150.46026 | 60138.430168 | **TARGET** | +0.360 % | **+$11.97** |
| ETHUSDT | 1687.257384 | 1697.04152 | 1696.702112 | **TARGET** | +0.360 % | **+$11.97** |

Book `buffy`: **+$23.94 = +0.239 %** on $10,000, 2 of 2 slots filled, both at
the after-cost target (0.60 % gross − 0.24 % costs). Exits are the TP level
minus 2 bps of slippage, which is why the realised figure is 0.360 % and not
0.600 %.

**This is not evidence of edge, and it would be dishonest to present it as
such.** Two trades, both in a market that was trending up during the window, on
a rule that needs **> 64 % accuracy** to break even. The book is +0.24 % after
one hour of a favourable tape; the sprint book in §8 lost 0.30 % in the same
session. What round 2 *does* establish is that the machinery resolves TP/SL/time
on real bars with the frozen tie-break, charges the stated costs, and records the
result either way — and that the record survives when the answer is a win as
well as when it is a loss.

## 10. Portfolio tracking — three backends, measured (added 2026-11-22)

The challenge books and the pre-registered forward book are now tracked by one
tool, `tools/portfolio_tracker.py`, which implements three candidate storage
designs and compares them on the same events:

| option | stored as | torn write | open-risk equity | measured size |
|---|---|---|---|---|
| ledger (chosen) | append-only JSONL events | **recovered, state identical** | yes | 5.3 KB |
| snapshot | materialised JSON | lost | yes | 6.7 KB |
| round-trip log | closed trades only | ok | **no — refuses** | 0.4 KB |

Ledger and snapshot agree to **$0.00**; the ledger reconciles to the
`realtime_challenge` source files at **$0.02** (sprint1, 3 trades) and **$0.03**
(buffy, 2 trades), which is the source's own cent-rounding. A deliberate partial write was recovered with
`corrupt_lines: 1` and an unchanged book. `.github/workflows/portfolio-tracker.yml`
runs `sync → mark → status` hourly, runs the test file first, and commits the
book with `[skip ci]`.

Current book, marked at `09:44Z`:

| book | equity | return | open | closed |
|---|---|---|---|---|
| buffy | $10,023.95 | +0.239 % | 0 | 2 |
| sprint1 | $9,969.86 | −0.301 % | 0 | 3 |
| forward_book | $8,083.30 | +1.041 % | 8 | 0 |
| **total** | **$28,077.11** | **+0.275 %** | **8** | **5** |

Full analysis: `reports/2026-11-22-portfolio-tracking-options.md`.

## 11. Cross-check status

No peer `REALTIMECHALLENGE_<model>_*.MD` file exists on `main` yet, so there is
nothing to replicate. When one appears the checks are, in order: (1) do their
costs match 24 bps round trip — most disagreements about "edge" are disagreements
about fees; (2) is the signal computed on a closed bar and filled on the next;
(3) is a both-touched bar resolved stop-first; (4) does their state file's
`pnl_usd` reconcile to the sum of `net_pct × notional`; (5) is equity marked to
market rather than realised-only, which understates drawdown.
