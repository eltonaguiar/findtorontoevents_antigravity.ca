# Forward-test protocol: kill fast, or hold longer?

Two questions this answers:
1. **Can I eliminate a strategy quickly?** Often yes — and usually in the backtest, not the forward test.
2. **If not, how long must I hold before the verdict is honest?** That depends on how often the strategy
   trades, not on how the P&L feels.

**Tooling:** `tools/forward_tracker.py` (ledger + verdicts). **Rules are pre-registered** — changing them
after seeing results is a new trial, and it must be recorded as one.

---

## Stage 0 — kill in the backtest (costs nothing, takes an afternoon)

Run `tools/sim_path_forward.py`. Anything that fails these is **dead before it trades**:

| Gate | Kill if |
|---|---|
| Beats its own matched-exposure benchmark | excess ≤ 0 over full sample **and** OOS |
| Survives doubled costs | turns negative or falls below benchmark at 2× cost |
| OOS does not collapse | OOS excess < 0 when IS excess > 0 (regime overfit) |
| DSR | < 0.95 at the declared trial count |

Applied to the 8 pre-registered rules, **5 died here**: RSI2_SPY, DUALMOM_2, DUALMOM_3, SIXTY_FORTY,
BH_SPY-as-alpha. Only **FABER10_SPY** (risk reduction) and **BTC_TREND200** (promising, unproven) advance.

> **This is the most important sentence in the protocol:** most strategies should never reach a forward
> test. Every one you forward-test costs months of calendar time and attention. Backtest is cheap.

## Stage 1 — forward test only the survivors

| Strategy | Class | Hold type | Trades/yr (backtest) | Clock |
|---|---|---|---|---|
| FABER10_SPY | ETF | long | ~1.5 switches | **calendar** (180/365/730d) |
| BTC_TREND200 | CRYPTO | long | ~2.7 swings | **calendar** (180/365/730d) |

Both are *slow*: they cannot reach a trade-count threshold in a reasonable time (1.5/yr → 20 trades takes
13 years). Killing them on trade count would kill them for being slow, not for being wrong. So they are
judged on **calendar + breaker**, never on "we don't have 20 trades yet".

## The decision table

**FAST** (hold < 5 days *and* ≥ 25 trades/yr — can reach n=20 inside a quarter):
```
n ≥ 20 and (PF < 1.00 or Wilson_lower(WR) < 0.40)      -> KILL
n ≥ 30 and PF ≥ 1.15 and bootstrap_5%(PF) > 1.05       -> PROMOTE
otherwise                                               -> CONTINUE
```

**SLOW** (everything else):
```
180d, n ≥ 8,  PF < 1.00                                -> KILL
365d, n ≥ 20, PF < 1.05                                -> KILL
365d, n ≥ 20, PF ≥ 1.15 and boot5(PF) > 1.00           -> PROMOTE
365d, n < 20                                           -> HOLD-LONGER (extend to 730d, do not kill)
730d, n < 20, PF < 1.00                                -> KILL
60d, n = 0                                             -> BROKEN (strategy is not firing — a bug, not a loss)
```

**BREAKER — the fast exit for slow strategies** (this is how you eliminate a slow strategy early without
waiting a year): `n ≥ 10 and PF < 0.75` → **KILL**. Ten trades at PF < 0.75 is not noise; it is evidence.

## How to log a trade (10 seconds)

```bash
python3 tools/forward_tracker.py log \
  --strategy FABER10_SPY --symbol SPY --entry 512.40 --exit 540.10 --qty 10 \
  --fees 3.20 --opened 2026-11-02 --closed 2027-01-04 --thesis "month-end above 10M SMA"
```

Then, any time — this is the whole ritual:

```bash
python3 tools/forward_tracker.py status
```

```
strategy          n  days     WR     PF   PF5%  avgHold  verdict      note
FABER10_SPY      11   400  63.6%   1.42   0.71      71d  HOLD-LONGER  400d but n=11<20, avg_hold=71d
BTC_TREND200      8   400  62.5%   1.18   0.62      95d  CONTINUE     180d checkpoint passed, n=8
```

Writes `state/forward_test/status.json` for the dashboard. Run it weekly; it takes under a minute.

## How many trades before a verdict is honest?

n = ((1.645 + 0.842) / SR_per_trade)²  (one-sided 5%, 80% power)

| Real per-trade Sharpe | Closed trades needed |
|---|---|
| 0.40 | 39 |
| 0.30 | 69 |
| 0.20 | 155 |
| 0.15 | 275 |
| 0.10 | 619 |

**Consequence:** a modest edge is unprovable in a quarter. That is why `PROMOTE` is strict and
`CONTINUE` is the default — and why the cheap kills happen in Stage 0, not here.

## Rules of the ledger

1. **Log every closed trade**, including the losers and the ones closed by stop. A ledger with only
   winners is a marketing document.
2. **One strategy id per rule.** Changing a parameter creates a new id (e.g. `FABER10_SPY_v2`); the old
   one keeps its history and its verdict.
3. **Never reset a ledger** to escape a `KILL`. Start a new id instead, and count it as a new trial.
4. **Hold type is set before the first trade**, from the backtest's observed hold, never after seeing P&L.
5. **`PROMOTE` is not "go live".** It means "passes on forward data; take it to sizing review", where
   Kelly, ruin and the 10-gate bar still apply.

## What would change my mind

- FABER: two consecutive whipsaw years where the overlay exits and SPY rallies > 15% within 3 months →
  the DD benefit is decaying; demote to no-overlay.
- BTC_TREND200: 3 consecutive signal flips with < 5% follow-through → trend signal is noise; kill.
- Either: realised max drawdown > 1.3 × backtested max DD (FABER −28%, BTC −83%) → breaker, kill now,
  regardless of trade count.
