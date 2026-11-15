# Forward-Test Protocol — Fast Elimination vs Hold-Longer Decisions

**Date:** 2026-11-15 (AM)
**Purpose:** A lightweight, drop-in tracker to decide, from live paper trades, whether a strategy can be eliminated quickly or must be held longer.

---

## 1. The core decision rule (decide with ~30 trades, not 200)

The single most useful early signal is the **consistency of the edge** against the benchmark, not the raw win rate. A strategy that is *consistently slightly better* than buy-and-hold is held; one that is *inconsistently worse* is eliminated early.

| Track | At n=30 | At n=60 | Decision |
|-------|---------|---------|----------|
| **Hold / extend** | excess-vs-benchmark > 0 on ≥60% of closed trades | Sharpe ≥ 0.8, excess > 0, DD < 20% | Keep; extend holding if edge is in the tail |
| **Trim** | excess > 0 but < 50% of trades | Sharpe 0.4-0.8 | Halve size; keep paper |
| **Eliminate FAST** | excess < 0 on ≥55% of trades, OR >3 consecutive losses | Sharpe < 0.4 or DD > 20% | Kill now — do not wait for n=200 |

---

## 2. Holding-period decision

When a trade is profitable but the *exit* is early relative to the trend, extend. When a trade reaches its target quickly but the opportunity keeps going, the trend is intact — consider a trailing exit instead of a fixed target.

| Signal | Action |
|--------|--------|
| Trades hit TP fast but trend continues | Switch to trailing stop (e.g., 200-day MA or ATR trail) |
| Trades sit near breakeven for a long time | Time-exit (e.g., 30 days) — don't hold dead capital |
| Majority of winners are held < 5 days | Extend horizon (the edge is in later exits) |
| Majority of losers are held > 20 days | Cut losers faster (tighter stop) |

---

## 3. The tracking table (one row per closed trade)

Score each closed trade with a simple pass/fail vs the benchmark:

| Field | What to record |
|-------|----------------|
| strategy_id | which strategy/class |
| symbol | ticker |
| entry_date / exit_date | timestamps |
| entry / exit price | real fills |
| pnl_pct | net of costs |
| benchmark_pnl_pct | SPY (equity) / BTC-hold (crypto) / 60-40 (allocation) over same window |
| excess_pct | pnl_net - benchmark_pnl |
| hold_days | exit - entry |
| exit_reason | TP / SL / TIME_EXIT / TRAIL |

**Compute each Sunday:**
- `% of closed trades with excess > 0` → if < 45% at n=30, eliminate.
- `median excess` → if < 0 at n=30, eliminate.
- `max drawdown of equity curve` → if > 20% at n=60, eliminate.
- `Sharpe (weekly)` → if < 0.4 at n=60, eliminate.

---

## 4. A 30-second checklist to run weekly

1. Pull all closed trades since last week (paper ledger).
2. Mark each `excess` vs benchmark.
3. Update the table: n, %excess>0, median excess, maxDD, Sharpe.
4. Apply the decision rule above.
5. If "hold/extend" → keep; if "eliminate" → stop the strategy and log why.

---

## 5. Key principle

**Eliminate fast on inconsistency; hold longer only on demonstrated consistency.** Do not give a weak strategy 200 trades to prove it is bad. The benchmark-relative excess at n=30 is a strong early signal. Conversely, do not kill a *consistent* strategy just because the raw win rate is below 50% — a low win rate with positive excess and good R:R is a valid trend strategy.
