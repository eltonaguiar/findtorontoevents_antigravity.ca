# REALTIME CHALLENGE — deepseek-flash — 20261122T0355 EST

## Header

| Field | Value |
|---|---|
| **Model token** | `deepseek-flash` |
| **Created (UTC)** | 2026-11-22T08:55Z |
| **Created (EST)** | 2026-11-22T03:55 EST (UTC−5) |
| **Repo** | `/home/eaguiar2015/findtorontoevents_antigravity.ca` |
| **Commit at creation** | `89ccdf0af55f70df7a202a63f460350d2b7af2c5` — "research(equity): full H-033 statistics - WEAK not CANDIDATE" |
| **Author** | deepseek-flash (architect mode), via the 200-round program Round 141+ |

This file is the **first** `REALTIMECHALLENGE_*.MD` in the repository — a full-tree
search on 2026-11-22 found zero prior such files, so there is no peer prototype to
inherit rules from. The rules below are therefore declared fresh and are binding for this
file.

---

## Objective

Attempt to **open and close at least one paper position** in a short timeframe on **live
markets**, using **real timestamped quotes** and simple technicals, and report **honestly**
whether a profit was captured, how, or exactly why not. This file is a ledger of honest
attempts, not a marketing page. A round with no completed trade is recorded as ZERO, not
as "neutral" and never as a win.

---

## Rules (binding, numbered)

1. **Real quotes only.** Every entry and exit fill price must be a timestamped real market
   quote pulled from a live source in this repo. Invented, interpolated, or
   "approximately" prices are forbidden. If a venue is closed, the round is recorded as
   ZERO with the reason, not back-filled with a stale close.
2. **Both TP and SL declared before entry.** A position may not be opened without a
   pre-declared take-profit and stop-loss. TP and SL are written into the row at the
   moment of entry.
3. **Max position size.** Each position is ≤ **2% of a $10,000 notional paper account**
   (i.e. ≤ $200 notional per position). The paper account is fixed at **$10,000**. Size
   is stated on every row.
4. **Max concurrent positions.** ≤ **3** open at once.
5. **No rolling forward of a loss.** A closed loss stays a loss. It may not be re-labelled
   a "longer-term hold", re-based to a new entry, or excused after the fact.
6. **Scored on net-of-cost return, not win rate.** Each round is scored on **net bps**
   (gross move minus round-trip cost, assumed 10bp/side = 20bp round trip unless the
   venue schedule differs and is stated). A high win rate with negative net bps is a
   losing round.
7. **Zero completed trades = ZERO.** A round in which no trade is opened and closed is
   scored **ZERO**, not neutral. "Nothing happened" is not a pass.

---

## Instrument selection rationale (based on recon)

Instruments are restricted to those whose live quotes were **verified reachable in this
repo** during recon:

- **Crypto (verified, 24/7):** [`tools/realtime_challenge.py`](tools/realtime_challenge.py) pulls live 5m bars from
  Binance spot mirrors (`api.binance.com` → `api1..api4`) and cross-checks against KuCoin,
  requiring ≥2 venues agreeing within 50bp. Live single quotes are also available via
  [`live_monitor/position_monitor.py`](live_monitor/position_monitor.py) (Binance `.us` + global + mirror). → **Crypto is the
  primary instrument set: BTCUSDT, ETHUSDT, SOLUSDT, and other liquid majors.**
- **Equities / ETF / Forex / Commodity / Bond (conditional):** a live single-quote path
  exists via [`tools/ai_tournament/price_tracker.py`](tools/ai_tournament/price_tracker.py) (`yfinance` → AlphaVantage →
  exchangerate-api failover) and [`alpha_engine/equity_price_failover.py`](alpha_engine/equity_price_failover.py), **but** equity
  quotes are only meaningful during US market hours (approx 13:00–21:00 UTC weekdays).
  Outside those hours there is **no live equity quote** in this repo, so equity rounds are
  **restricted to market hours** and recorded as ZERO outside them.
- **This session's timestamp (03:55 EST / 08:55 UTC, weekend):** cash equity, FX and most
  futures venues are **closed**. Only **crypto** is live. Therefore the first live rounds
  must use crypto instruments; equity rounds are scheduled only for weekday market hours.

---

## Scoring table

| Round# | Entry UTC | Instrument | Direction | Entry px | TP | SL | Exit UTC | Exit px | Gross bps | Net bps | Outcome | Honest note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EXAMPLE | 2026-11-22T09:00Z | BTCUSDT | LONG | 0.00 | 0.00 | 0.00 | 2026-11-22T10:00Z | 0.00 | 0.0 | −20.0 | EXAMPLE — NOT A TRADE | Placeholder row showing column format and the 20bp round-trip cost. Do not count. |
| 141 | 2026-11-22T09:02:59Z | CRYPTO 30-sym scan (BTCUSDT, ETHUSDT, SOLUSDT +27) | LONG (engine rules are long-only) | — | — | — | — | — | 0.0 | 0.0 | NO_TRADE | No entry: on no supported symbol did A1 (5m close beyond the prior 20-bar Donchian high) or A2 (RSI14 < 30) fire across 3 scans at 09:02:59Z / 09:08:50Z / 09:14:49Z. Nearest to firing: BTCUSDT gap_to_break +119bp, RSI 63.1. Binance and KuCoin both reachable, so this is a signal drought, not a data failure. No position opened, `--resolve` said "no open positions". → scored ZERO per rule 7. |
| 141-c | 2026-11-22T09:14:49Z | BTCUSDT | n/a (no signal) | n/a | n/a | n/a | n/a | n/a | n/a | n/a | NO_SIGNAL | **Companion row (amendment A2) — NOT a trade and NOT a round; never count it in any statistic.** Closest non-signal candidate at the last poll: `gap_to_break` +112 to +119 bp across the 3 polls (A1 needed ≤ 0 bp, i.e. a 5m close above the prior 20-bar high), RSI14 63.1–64.x (A2 needed < 30). Distance to trigger ≈ 112–119 bp on the breakout leg, ≈ 33–34 RSI points on the oversold leg. |

The table starts **empty of real trades**. The single example row is explicitly
`EXAMPLE — NOT A TRADE` and must never be counted in any statistic.

---

## Prototype defect found by Round 141

Round 141 opened **zero** positions. Rule 7 scores that **ZERO**, and the ZERO is correct
bookkeeping. But the zero was produced by the prototype's trigger design, not by the market, so
this section records the defect and three rule amendments. **No engine change is made here:**
[`tools/realtime_challenge.py`](tools/realtime_challenge.py) is deliberately left unmodified in
this task; a later round decides whether to change it.

### 1. The flaw, stated plainly

The entry scan is a **rare-trigger** scan: a long is opened only when a symbol (A1) closes beyond
its prior **20-bar Donchian high**, or (A2) prints **RSI14 < 30**. Applied to a **30-symbol**
universe with a **120-minute maximum hold**, the arithmetic is unfavourable:

- **Rare trigger × short hold = mostly zero-signal rounds.** A 20-bar breakout or an RSI<30 dip
  on any single symbol is uncommon; requiring one *inside a 120-minute window* on a quiet
  Sunday makes it rarer still.
- **Measured (Round 141):** three scans in ~12 minutes (09:02:59Z, 09:08:50Z, 09:14:49Z), each
  after a new 5m bar, over all 30 symbols → **0 A1 setups, 0 A2 setups, 0 positions opened**.
- **Closest:** BTCUSDT, `gap_to_break` **+112 to +119 bp** (it needed ≤ 0 bp) and **RSI14 63–64**
  (it needed < 30).

The engine is therefore not broken — it is *selective*, and the challenge currently has no
mechanism that tells selectivity apart from absence of opportunity.

### 2. Why a zero round is not neutral

Scoring it ZERO is correct (rule 7: no completed trade = ZERO). Concluding **"no edge"** from it
would be wrong, because **nothing was tested**: no entry, no TP/SL resolution, no cost drag, no
exit was exercised. A zero round measures *the trigger rate* and only that. The challenge must
distinguish:

- **"no signal"** — the rules were evaluated and no setup existed (a fact about scarcity), from
- **"signal lost"** — a setup existed but was missed, mis-sized, rejected for data reasons, or
  the round failed operationally (a defect to fix).

Round 141 is the first kind. Until rounds record trigger statistics, the ledger cannot tell the
two apart.

### 3. Rule amendment A1 (binding from Round 142): every round records signal frequency

Every challenge round must additionally record **signal frequency**:

- **Setups per poll:** how many of the N scanned symbols produced a setup at each poll
  (`a1_count`, `a2_count`, their union), together with N.
- **Universe distribution:** `gap_to_break` (bp) and RSI14 for every scanned symbol, summarised at
  minimum as min / median / max, and ideally persisted in full.

A subsequent round with 0 setups then becomes **evidence about signal scarcity** (an observed
trigger rate ≈ 0/N over the polls), not a null result. Suggested per-poll record in a JSON
sidecar (e.g. `reports/realtime_challenge/freq_<run_id>.json`):

```json
{"poll_utc": "...", "symbols_scanned": 30, "setups": 0, "a1": 0, "a2": 0,
 "universe": [{"symbol": "BTCUSDT", "gap_to_break_bp": 112.0, "rsi14": 63.1}],
 "summary": {"gap_to_break_bp": {"min": 0, "median": 0, "max": 0},
             "rsi14": {"min": 0, "median": 0, "max": 0}}}
```

### 4. Rule amendment A2: a "closest non-signal candidate" row per round

For every round that opens nothing, the scoring table gains a **companion row**
(`Round#` written as `<n>-c`, outcome `NO_SIGNAL`) capturing the closest non-signal candidate:

| Field | Meaning |
|---|---|
| Symbol | the symbol nearest to firing |
| Metric | the condition it was nearest on (`gap_to_break` bp, RSI14, …) |
| Value | the measured value |
| Distance to trigger | how far that value was from firing the rule |

A zero round then still yields data (how quiet the universe was) instead of a bare 0. Round 141's
companion row is in the scoring table above (`141-c`).

### 5. Rule amendment A3: horizon mismatch is a design issue to TEST, not to change

The entry lookback and the maximum hold are nearly the same size:

- breakout lookback: **20 bars × 5m = 100 minutes**
- maximum hold: **24 bars × 5m = 120 minutes**

A 20-bar breakout entry is expected to sit near the *end* of the move that the 20-bar measurement
describes, while the position is held almost exactly as long as the lookback. A "failed" trade may
then be a lookback-length artefact rather than a bad signal.

**This is recorded as a design issue to test, not silently changed.** No engine constant is
modified in this task. A later round should compare, on the same archived quotes and with the cost
model fixed: lookback 20 / hold 24 (current), lookback 20 / hold 60, lookback 10 / hold 24, and
report net bps for each.

### Round 141 — what it did and did not establish

| | |
|---|---|
| **Established** | Both quote venues were **live and agreeing**: Binance **59745.16** vs KuCoin **59742.90** (≈ **3.8 bp** apart, far inside the 50 bp agreement gate). The engine ran to completion over all 30 symbols and opened 0 positions. At **09:02:59Z / 09:08:50Z / 09:14:49Z** no symbol satisfied A1 (20-bar Donchian breakout) or A2 (RSI14 < 30); `--resolve` reported "no open positions". |
| **NOT established** | Anything about the **profitability** of the strategy: no entry, no exit, no TP/SL resolution, no fill quality, no cost drag, no net bps. Round 141 says nothing about win rate, expectancy, or whether these rules would make money if they fired. It is neither a win nor evidence of no edge. |

---

## What was ACTUALLY set up

Stated plainly, so nothing is implied to exist that does not:

**Exists now (verified on disk):**
- [`tools/realtime_challenge.py`](tools/realtime_challenge.py) — live-quote paper engine: fetches live 5m bars, enforces
  ≥2-venue 50bp agreement, resolves intrabar TP/SL **pessimistically** (stop first),
  charges 10bp/side, holds max 24 bars (120 min). Modes `--open` and `--resolve`. **This is
  the driver this challenge is built on.**
- [`reports/realtime_challenge/state.json`](reports/realtime_challenge/state.json) — the ledger (currently `open: []`, `closed: []`,
  `skipped: []`, run_id `20261122T085654Z`). **No trades placed yet.**
- `reports/realtime_challenge/trades.jsonl` — append-only trade ledger path.
- [`live_monitor/position_monitor.py`](live_monitor/position_monitor.py) — live Binance single-quote fetcher (crypto).
- [`tools/ai_tournament/price_tracker.py`](tools/ai_tournament/price_tracker.py) — class-routed live quote fetcher (crypto/equity/
  forex/commodity/bond).
- [`paper_trading/data/closed_picks.json`](paper_trading/data/closed_picks.json) — the canonical closed-pick schema (fields:
  `id, symbol, direction, entry_price, current_price, tp, sl, strategy, strategy_name,
  portfolio_type, conviction_tier, position_size_usd, shares, entry_date, status,
  exit_price, exit_date, pnl_pct, pnl_usd, mfe, mae, confidence, reason`).

**Does NOT exist yet (must be built in Code mode):**
- ~~`tools/live_pretend_trader.py`~~ — **CORRECTION (2026-11-22T09:15Z): this wrapper is NOT needed.**
  [`tools/realtime_challenge.py`](tools/realtime_challenge.py) is the actual live-quote paper engine. Its real CLI
  (verified with `--help`) is `--open | --resolve | --backtest | --status`; it takes no
  symbol/TP/SL/size arguments because those are pre-registered constants in the file
  (`TP_ATR=2.0`, `SL_ATR=1.0`, `FEE_PER_SIDE=0.0010`, `MAX_HOLD_BARS=24`). Rows for this
  table are produced by running its `--open` / `--resolve` paths and transcribing the output.
- A scheduled GHA workflow for this specific challenge — **NOT YET BUILT** (the 200-round
  program's Block 7 defines it: `.github/workflows/realtime-challenge-monitor.yml`).
- Any equity-hours live-round automation — **NOT YET BUILT.**

No claim is made that a live round has run. **Completed live rounds so far: 0.**

---

## Update log

| When | Who | What |
|---|---|---|
| 2026-11-22T08:55Z (03:55 EST) | deepseek-flash (architect) | Created this challenge prototype. Established binding rules, instrument scope (crypto-first because equities/FX are closed and no live equity quote exists outside market hours), empty scoring table with a no-trade example row, and the "what was actually set up" honesty section. **Next planned:** build `tools/live_pretend_trader.py` (Code mode) on top of [`tools/realtime_challenge.py`](tools/realtime_challenge.py), then execute Round 141 as the first real crypto open→close using live Binance quotes. |
| 2026-11-22T09:15Z (04:15 EST) | subq-savant-1.4 (code) | **Round 141 executed → NO_TRADE.** Ran `--open` three times (09:02:59Z, 09:08:50Z, 09:14:49Z, ~6 min apart, each after a new 5m bar) over all 30 supported symbols: zero A1 breakout and zero A2 RSI-dip setups, so the engine opened 0 positions. `--resolve` then reported "no open positions". Binance + KuCoin were reachable throughout (BTC 59743.5 vs 59700 vs ~59700), so this is a genuine signal drought on a quiet Sunday, not a data outage. Scored ZERO per rule 7. Also corrected the setup section: `tools/realtime_challenge.py` is the real engine and `tools/live_pretend_trader.py` is not needed. |

---

## Peer cross-check placeholder

Recon on 2026-11-22 performed a full-tree search for `REALTIMECHALLENGE_*.MD` and found
**zero** peer files anywhere in the repository. Per the rules, this is recorded honestly
rather than fabricated:

| Peer file | Claimed mechanism | Replicated? | Notes |
|---|---|---|---|
| *(none found)* | — | UNMEASURABLE | No `REALTIMECHALLENGE_*.MD` peer file exists in the repo as of 2026-11-22T08:55Z. Full-tree search returned 0 hits. If peer files appear later, add one row each and classify REPLICATED / NOT_REPLICATED / UNMEASURABLE. |
