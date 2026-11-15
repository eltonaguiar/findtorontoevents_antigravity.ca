# Forward Test — what is on the clock, and what would kill it

**Registered:** 2026-11-15 · **Tool:** [`tools/forward_tracker.py`](../../tools/forward_tracker.py) · **Plan:** [`state/forward_test/plan.json`](../../state/forward_test/plan.json)

A backtest cannot promote a rule and neither can five retrospective re-reads of the same ledger. This
file records, **before any forward trade exists**, which rules are being watched, what verdict rule
applies to each, and the number that was true when the clock started. The rules live in code and are
pre-registered: changing them after seeing results turns the test into another trial.

---

## 1. On the clock

| Strategy | Class | Median hold | Fires / yr | Clock starts | Prior (see §2) |
|---|---|---:|---:|---|---|
| FABER10_SPY | ETF | ~8 months | 1.5 | 2026-11-15 | 33 trades, DSR 0.99, halves drawdown |
| BTC_TREND200 | CRYPTO | ~4.5 months | 2.7 | 2026-11-15 | 30 trades, DSR 0.84 |
| **vwap-reversion-scout** | **EQUITY** | **~6 days** | **~48** | **2026-11-15** | **28 picks, 25 windows, +1.96pp, t 1.99** |

Killed in backtest and **not** consuming forward months: `RSI2_SPY`, `DUALMOM_2`, `DUALMOM_3`,
`SIXTY_FORTY`. A rule that already failed on 2004–2026 evidence does not earn a forward slot.

---

## 2. `vwap-reversion-scout` — the rule being added and why

**Rule.** Long when all of: close is more than **2% below its 20-day rolling VWAP** (typical price
weighted by volume), **RSI(14) < 40**, the close sits in the **upper 45% of the day's range**, and
volume is at least **0.8×** its 20-day average. Exit on take-profit, stop-loss, or a **168-hour
(7-day) time stop**. Source: `KIMI_RISEOFTHECLAW/live_scanner.py::signal_vwap_reversion`, applied to
18 liquid US names.

**Why this one and not another.** It was the only rule in the live ledger with a positive excess on a
meaningful number of independent windows:

| | Value |
|---|---:|
| Closed picks in ledger | 28 |
| Independent windows | 25 |
| Mean excess vs SPY | **+1.96pp** |
| Excess win rate | **60.7%** |
| Clustered t | **1.99** |
| Median hold | 145 hours |
| Exit reasons | TP / SL / 168h time stop |

**The honest caveat, stated before the result exists:** t = **1.99** does not clear 2.0, and 25
windows is a small sample. This is a *prior*, not evidence. It is registered because it is the one
candidate that has earned a forward clock — not because it has been shown to work.

---

## 3. Pre-registered verdict rules

`hold_type: long` selects the **slow clock**, because the median hold is over 5 days. Fast rules that
fire often enough to reach n=20 inside a quarter use the fast clock; killing a slow rule for being slow
would be a bug, not a verdict.

| Condition | Verdict |
|---|---|
| 180 days elapsed, n ≥ 8, PF < 1.00 | **KILL** |
| 365 days elapsed, n ≥ 20, PF < 1.05 | **KILL** |
| Breaker: n ≥ 10, PF < 0.75 (any time) | **KILL** — 10 trades at PF 0.75 is evidence, not noise |
| 365 days elapsed, n < 20 | **HOLD-LONGER** (clock extends once, to 730 days) |
| 60 days elapsed, n = 0 | **BROKEN** — the rule is not firing (a different bug) |
| 365 days, n ≥ 20, PF ≥ 1.15, boot5(PF) > 1.00 | **PROMOTE** — still needs capital-committee sign-off |

Promotion is deliberately hard: at a true per-trade Sharpe of 0.20, separating edge from luck needs
about **155 closed trades**. A rule firing ~48×/yr reaches that in roughly three years. Anything
promoted earlier is being promoted on narrative.

---

## 4. How a trade enters the ledger

One line per **closed** trade, never edited. Two entry paths:

```bash
# (a) automatic: append picks that closed after registration
python3 tools/forward_tracker.py sync --dry-run   # preview (writes nothing)
python3 tools/forward_tracker.py sync             # append newly-closed picks

# (b) manual
python3 tools/forward_tracker.py log \
  --strategy vwap-reversion-scout --symbol QQQ --side long \
  --entry 604.12 --exit 611.40 --qty 1 --fees 0.72 \
  --opened 2026-11-16 --closed 2026-11-20 \
  --thesis "3.1% below 20d VWAP, RSI 34, close in upper range"

python3 tools/forward_tracker.py status      # verdict per strategy
python3 tools/forward_tracker.py selftest    # 8/8 rule cases
```

**Sync cannot backfill, by construction.** A pick is admitted only if it closed on or after the
strategy's registered `start` (2026-11-15). At registration the ledger is empty and `sync` reports
`would append 0 | closed before registration 29` — the 29 picks that produced the prior are excluded
because excluding them is the only thing that makes this a forward test. Idempotent by pick id plus a
`strategy|symbol|side|opened|closed` composite, so re-runs cannot double-count.

Synced rows carry `source: dashboard_sync`, the pick id, and an explicit `cost_model: none` — the
dashboard payload has no fee field, so **forward PF from synced rows is gross** while the backtest
assumed 6 bps/side. Read the eventual verdict with that gap in mind.

---

## 5. What this does not do

- It does not allocate capital. `PROMOTE` is a gate, not an order.
- It does not measure beta exposure. A rule can pass on PF while simply being a leveraged long SPY;
  the excess column in [`EXCESS_RETURNS.md`](EXCESS_RETURNS.md) is what catches that.
- It cannot see a rule that stops firing for a market reason rather than a code reason — after 60 days
  with zero trades the verdict is `BROKEN`, which sends you to the scanner, not to a conclusion.
