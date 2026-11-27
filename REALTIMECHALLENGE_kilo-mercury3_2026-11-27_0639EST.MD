# REAL-TIME CHALLENGE — Prototype & Setup Log

**Agent:** kilo-mercury3 (Inception ULTRA_PAID_MERCURY_3)
**Seat:** `inbox/gx10-c9b9/auditreviews-v3/kilo-mercury3` (COMS registry)
**Created:** 2026-11-27 06:39 EST (11:39 UTC)
**Status:** Prototype defined; engine verified live; hypothesis pre-registered; 0 trades opened yet.

---

## 0. TL;DR of what this round is

The challenge: **open and close a paper position on LIVE market data and come out ahead in a short timeframe**, on real, current prices. This file is the pre-registration discipline (signal rules + costs fixed BEFORE any further live bar is used to choose them) plus the log of what I actually stood up. It is the Kilo/Mercury-3 entry in the fleetwide 200-round programme; peers (deepseek-flash, GitHub Copilot) have already filed theirs — I cross-check those and build on them rather than repeat them.

---

## 1. Findings that shape this prototype (from the review I just did)

Before touching any strategy I reviewed the estate's own methodology and the peer challenge results, because they dictate what is worth trying:

1. **Fees are the killer, not signal.** Peer backtest of the A1/A2 crypto arms on live bars: gross **+28.22%** over 1,254 trades, fees **250.80%**, net **−222.58%**, permutation p=0.000. Fees ≈ **889% of gross edge**. Even at the most favourable 4bp round-trip maker schedule, edge = 56% of cost → fails the 3.0× cost gate by 5.4×; per-trade edge +2.2bp vs ~12bp required.
2. **The only net-positive cell in 6,619 trades** was `S7_ORB_EQ` (equities open-range breakout, 4bp, n=161, t=+0.89) — directional, not yet proven, but equities was the venue that paid.
3. **Cost floors make most classes unmeasurable with current data** (`reports/2026-11-22-cost-floor-and-power.md`): EQUITY floor 614bp (30.7×), CRYPTO 667bp, ETF 165bp, FUTURES 18bp, INDEX 73bp. BOND/COMMODITY/FOREX/PENNY sit below floor. MDE to detect a tradable 1.92bp/day effect: EQUITY 207yr, CRYPTO 633yr. **Conclusion: the binding constraint is cost + data resolution, not signal supply.**
4. **Doctrine (audit2):** public daily OHLCV is arbitraged; remaining edges are risk premia and microstructure/flow. "Volatility scaling is free alpha" (~+0.3 Sharpe). Edge should be expressed with symmetric, vol-scaled, time-based exits, sized by vol targeting — "the expression of every trade changes the statistics more than the signal does."
5. **Estate scoring is broken** (0 PROVEN across the tribunal; ML calibration inverted; EXPIRED→WON mislabels inflate WR). Do NOT inherit the estate's composite score as an entry signal. Use clean, pre-registered rules only.

**Design consequence:** the profitable path is *not* more intraday crypto scalps. It is (a) lower-turnover, higher-conviction expressions, (b) cost that actually clears the gate (maker/limit fills, or low-cost venues), (c) symmetric time-based/vol-scaled exits, and (d) equities during US session where the one paying cell lived.

---

## 2. The prototype (pre-registered — fixed before more live bars are observed)

### Arm inventory (all pre-registered; any change = new hypothesis run)

| Arm | Class | Signal | Exit | Cost model | Why |
|---|---|---|---|---|---|
| C1 | Crypto (30 USDT pairs, 5m) | A1 Donchian-20 breakout close + A2 RSI(14)<30 dip (long-only) | TP 2.0×ATR(14), SL 1.0×ATR(14), max hold 24 bars | 10bp/side taker (peer baseline) | The published baseline; I run it to have a controlled comparator |
| C2 | Crypto, same pairs | **Vol-scaled symmetric time-based exit** — same long entries, but exit on time stop (N bars) at 1× ATR target, no fixed SL (intrabar pessimistic) | time-based, vol-targeted size | 10bp/side taker | Tests the "expression of exit changes the statistics" doctrine on the same signals |
| E1 | **US equities (S&P/SPY constituents + liquid names), 5m/15m** | Open-Range Breakout (ORB), 30-min range, long/short | symmetric, time-based; SL/TP in ATR terms | 4bp round-trip (best measured) | The one paying cell in the estate (S7_ORB_EQ) |
| X1 | Cross-venue basis (crypto) | same symbol traded on Binance vs KuCoin, arbitrage the >50bp divergence | book both legs | 4bp round-trip maker | Only runs when venue divergence actually appears; pre-registered, not hunted |

### Hard rules (from the estate's honest run + my additions)
- Real timestamped quotes only; no invented/interpolated fills. Two independent venues must agree within 50bp for crypto.
- Intrabar tie → pessimistic: if a bar's range covers both SL and TP, assume **SL fills first**.
- ≤ $200 notional per position on a fixed $10k paper book (2%); ≤3 concurrent; no rolling forward of losses.
- Scored on net-of-cost bps. Zero completed trades = **ZERO**, never neutral.
- Session clock enforced: equities only when the US cash market is open (this is the main reason the fleet's Sunday run omitted equities).

### What makes this different from the peer runs
1. **An equities arm** (E1) — peers ran crypto-only because it was Sunday; today is Friday (US session open), and equities is the only venue that produced a net-positive cell in the estate's 6,619-trade sweep.
2. **An exit-expression test** (C2) — directly isolates whether symmetric time-based vol-scaled exits rescue marginal crypto signals, per the audit2 doctrine.
3. **A cost-aware comparator** — C1 baseline vs C2 (same signals, different exit) makes the cost-vs-edge interaction measurable rather than asserted.

---

## 3. What I actually set up (verified)

- **Engine confirmed present and live:** `tools/realtime_challenge.py` (25.3KB). CLI: `--open / --resolve / --backtest / --status`.
- **Live status probe ran:** `--status` at 11:39Z returned `crypto=true, equity=false, futures=true, forex=true` (Fri, weekday session; equity gated to US market hours). `open=0 closed=0`.
- **State/ledger:** `reports/realtime_challenge/state.json` + `trades.jsonl` (append-only).
- **COMS registration done:** seat `kilo-mercury3` registered on `gx10-c9b9/auditreviews-v3` at 2026-11-27T11:39:24Z; bus round-trip verified (received `mentions/all` and a `notes/#` index of 426 notes).
- **Cross-check of peers:** read `REALTIMECHALLENGE_deepseek-flash_20261122T0355_EST.MD` and `REALTIMECHALLENGE_GitHubCopilot_2026-11-22_0359_EST.MD` — both are crypto-only 5m A1/A2, both opened **0 live positions** (signal drought, not data failure), and Copilot's backtest proved the fee-wall. My E1/C2/X1 arms are the delta.

## 4. Next actions (execution plan)
1. Run `tools/realtime_challenge.py --open` during the Friday US session so E1 (equities ORB) can actually fire — the venue the weekend peers could not open.
2. Add the C2 exit-variant as a separate hypothesis run (new arm, same entries, time-based exit), and X1 basis scanner.
3. Maintain this file as the living setup log; update the tracker + COMS note with each completed round.
4. Score net-of-cost only; report the 3.0× cost-gate result per arm.

---
**Not investment advice. Paper only, $200 notional, zero real capital.**
