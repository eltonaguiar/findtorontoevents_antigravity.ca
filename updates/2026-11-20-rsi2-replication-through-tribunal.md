# RSI(2) replicated through the audit pipeline — it is beta, not timing (2026-11-20)

## Why

H-2026-11-20-06. Every strategy tested in this repo has come back negative, so a
negative result proves nothing about the *pipeline* — a broken tribunal and a
strict one look identical when everything fails. RSI(2) mean reversion on equity
indices is documented since the 1990s, so it is the right calibration target: if
the pipeline cannot reproduce a known effect, it is not measuring what it claims.

## What was built

- `tools/rsi2_replication.py` — Wilder RSI, 5-day SMA, a bar-by-bar simulator
  emitting canonical rows, and a summary. Signal at the close of day *t*, entry
  at the **open of t+1**, exit on close above the 5-day MA / RSI(2) > 60 / 10-day
  cap. Network fetch is behind `--fetch` so tests never touch it.
- `tests/test_rsi2_replication.py` — 10 deterministic tests on synthetic bars.

## The one real bug

`wilder_rsi` seeded the average gain/loss and then looped with an `i > period`
guard, which skipped smoothing for the first post-seed delta and left a stale
value there. On a series like `[100,100,100,50,50,...]` the drop bar reported
RSI 100 and no trade ever fired. Fixed by computing the seed's own value at
index `period` and smoothing every subsequent delta unconditionally.

Two other failures were my tests' fault, not the code's: I asserted the first
defined RSI at index 2 for a 3-price series (the seed consumes 2 deltas, so
index 2 needs 3 prices — the assertion was fine but the input was too short),
and I guessed which bar would trigger the signal instead of asserting the
invariant "entry is some bar's open, never the trigger bar's close". Both
rewritten as invariants.

## Result (10y daily bars, yfinance)

| symbol | n | mean net | win rate | mean buy-hold | **selection alpha** |
|---|---|---|---|---|---|
| SPY | 115 | +0.25% | 74.8% | +0.38% | **−0.12%** |
| QQQ | 113 | +0.37% | 68.1% | +0.52% | **−0.15%** |
| BTC-USD | 191 | +0.61% | 72.8% | +0.19% | **+0.42%** |
| SOL-USD | 127 | +0.21% | 63.0% | +0.75% | **−0.53%** |

The headline is that SPY looks *good* on every metric a naive backtest reports —
positive mean, 74.8% win rate — while losing to buy-and-hold over the identical
holding windows. The whole positive mean is beta captured during an up decade.

The BTC control is the part that matters: it shows **more** selection alpha
(+0.42%) than either equity target, so the test does not isolate the
gap-structure mechanism it was supposed to. Both pre-registered failure
conditions fired — the control did not fail, and n was below the 200 minimum.

## Verdict

REFUTED as a timing-alpha claim. Not a powered proof of absence (n < 200), but a
refusal to credit absolute return as skill — which is exactly the error that
produces the inflated backtest numbers we keep finding elsewhere in the repo.

## Files

`tools/rsi2_replication.py`, `tests/test_rsi2_replication.py`,
`reports/rsi2_replication_2026-11-20.json`, registry entry H-2026-11-20-06.
