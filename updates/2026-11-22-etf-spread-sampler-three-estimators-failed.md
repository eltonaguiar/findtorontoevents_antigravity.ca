# ETF effective spread — three estimators failed, so it is now a sampler (2026-11-22)

Reproducer: `python3 tools/etf_spread_sampler.py [--record] [--series]`
Workflow: `.github/workflows/etf-spread-series.yml` — every 30 min, 13:05–19:35 UTC, Mon–Fri
Outputs: `reports/etf_spread/etf_spread_series.jsonl`

---

## Why this is the decisive number

The breakout family is the **only** strategy in this programme with a real gross
edge: **+22.43 bp/trade at t = +7.32** (`tools/execution_sensitivity.py`, todo 5).
Breakeven sits between **20 and 24 bp round trip**. So the entire question of
whether that family is investable reduces to one unmeasured quantity: **the
realised ETF round-trip spread.**

| measured spread | consequence |
|---|---|
| < 18 bp RT | nets +4 to +18 bp/trade → worth re-registering as a **new** hypothesis |
| 18–24 bp RT | marginal |
| > 24 bp RT | stays REFUTED |

Note the killed OUTSIDE-1 test specified 24 bp and fired correctly. **That kill
stands.** This measurement can only justify *re-registration*, never resurrection.

## Three estimators, three failures

| estimator | result | why |
|---|---|---|
| Corwin-Schultz | **0.00 on all 1,248 SPY pairs** | degenerate on liquid names |
| Roll | 34.76 bp | `2·√(−autocov)` scales with return volatility, not spread |
| Abdi-Ranaldo (2017) | **~100,000 bp on SPY** | my implementation was wrong |

The Abdi-Ranaldo attempt is the instructive one. I wrote it from recollection of
the algebra, ran it, and the **control check caught it immediately** — the tool
refused to emit and printed:

```
ESTIMATOR FAILS ITS CONTROL -> BROKEN.
It cannot recover the spread on SPY/QQQ/GLD, the three most liquid ETFs on earth.
Emitting a strategy-universe number from it would be fabricating precision.
```

I then tried to confirm the exact formula from a source I trusted and could not.
**So I deleted the implementation rather than tune variants until one produced a
plausible number.** Tuning an estimator until it agrees with the answer you
expect is fitting to the prior, not measuring. `tools/etf_spread_abdi_ranaldo.py`
no longer exists.

That control is the most valuable thing this block produced: a spread estimator
that cannot recover SPY's spread is worthless on anything else, and the check
that says so costs ten lines.

## What replaced it

A **live NBBO sampler** on SPY / QQQ / GLD — IEX top-of-book via the existing
Tiingo key. Every number it emits is an observed quote, not an inference.

Current run (2026-11-22, Saturday):

```
requested 3, quoted OK 0
SPY   —  —  BLOCKED  null/stale quote (market closed?)
QQQ   —  —  BLOCKED  null/stale quote (market closed?)
GLD   —  —  BLOCKED  null/stale quote (market closed?)

BLOCKED: no live quote. IEX returns null bid/ask outside regular trading hours...
Recording nothing is the correct outcome -- a zero or a previous close would be
a fabricated spread.
```

So: **UNMEASURED today, and the tool says so instead of emitting a number.**

## How it accrues

| | |
|---|---|
| workflow | `.github/workflows/etf-spread-series.yml` |
| cron | `35,05 13-19 * * 1-5` → inside 09:30–15:55 America/New_York |
| samples/day | up to 14 per ticker |
| min gap | 20 min per ticker, enforced in code (a retry storm cannot inflate n) |
| commits | `[skip ci]`, own concurrency group, no push trigger |

`--series` reports median / p75 / p95 / min and the verdict band. **n < 10 reads
"not established"** — the deciding parameter is the tail, and a single snapshot
cannot have one.

## Why the job stays green when blocked

"No quote today" is a real market state, not a CI failure. Failing on it would
train everyone to ignore the workflow, which is how the dead `consult_multi`
presets survived for six months (todo 46). The tool returns non-zero when a human
runs it interactively, but the workflow downgrades that to a notice.

## Labels

| item | label |
|---|---|
| ETF effective spread | **UNMEASURED** — sampler live, zero samples (market closed) |
| Breakout family net edge | **UNDETERMINED** — gross +22.43 bp known, cost unknown |
| Corwin-Schultz / Roll / my AR | **REFUTED as instruments** — recorded, not retried |
