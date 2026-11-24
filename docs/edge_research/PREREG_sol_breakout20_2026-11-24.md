# Pre-registration: SOLUSDT breakout 20-bar, daily, 1-bar hold

**Registered:** 2026-11-24 · **Status:** awaiting forward data · **Not tradeable**

## Why this exists

It is the only cell of 66 measured that survived a check designed to kill it. Pooled
statistics made three candidates look alike; walk-forward separated them:

| cell | folds positive | most recent fold | verdict |
|---|---|---|---|
| SOLUSDT/breakout/1d | 3/3 | **+122.74 bp** | CONSISTENT_SIGN |
| SOLUSDT/donchian/1d | 1/2 | −77.16 bp | NOT_ROBUST |
| BTCUSDT/bb_meanrev/1d | 2/3 | −17.82 bp | NOT_ROBUST (monotonic decay 152→54→−18) |

The other two died for reasons the pooled test could not see: donchian was carried by a single
regime, and bb_meanrev's edge decayed to negative in the most recent fold.

## The frozen specification

Deviating from any line below invalidates the test. This is the point of pre-registering.

- **Symbol:** SOLUSDT
- **Signal:** `close > max(close, previous 20 bars)` — evaluated on the daily close
- **Entry:** next bar's open. **Exit:** open 1 bar later. Non-overlapping.
- **Cost:** 26 bp round-turn, charged once per trade
- **Metric:** mean net bp per trade
- **Data:** Binance daily klines, same source as `tools/measure_cell.py`

## What counts as a pass

All three, not any one:

1. n ≥ 30 forward trades
2. 95% bootstrap CI on net bp per trade **excludes zero from below**
3. DSR > 0.95 at a trial count of **1** — this cell is pre-registered, so it is no longer one
   of 1000 tries. That is the entire benefit of registering it, and it must not be squandered by
   also testing nine variants.

## Baseline for comparison

The in-sample result that generated this registration, recorded so it cannot be quietly revised:

- n = 62 trades, gross +97.90 bp, **net +71.90 bp** after 26bp
- 95% CI [−29.01, +184.28] — contains zero
- permutation p = 0.013, **DSR = 0.0045**

Every fold CI also contained zero (n = 20–23 per fold). So the prior probability that this is
real is low, and the forward test is expected to fail. Registering it anyway is the point: a
pre-registered failure is information, an unregistered success is noise.

## What would kill it

- Net mean ≤ 0 over ≥ 30 forward trades
- Any fold in a forward walk-forward with negative net
- Realised cost materially above 26bp (the edge is ~72bp, so cost could plausibly eat it)
- A regime shift in SOL that the 20-bar breakout cannot distinguish

## Honest statement

Nothing here is a finding, an edge, or advice. It is one hypothesis with a written specification and
a written failure condition, which is the minimum required before forward data can mean anything.

---

## CORRECTION 2026-11-24: the GitHub cron does NOT fire

`.github/workflows/sol-breakout-forward.yml` was added on the branch
`research/cells-copilot-2026-11-24`. **GitHub only runs `schedule:` triggers from the
DEFAULT branch.** Verified: `gh workflow run sol-breakout-forward.yml` returns
`HTTP 404: Not Found` — the workflow is not even registered with Actions, because it has
never existed on `main`.

So the earlier claim that "the only open thread is now running on its own" was **wrong**.
The forward clock has never advanced automatically, and would not have.

### Two ways to actually fix it

1. **Move the workflow to `main`.** This is the correct fix and the only one that gives a
   real daily cron. It requires a merge to `main`, which this session is not permitted to
   do unilaterally. A PR containing ONLY this workflow file is the minimal path.
2. **Run it locally** via `tmux`/`nohup` on this host, or a user crontab entry. Works
   today, dies on reboot, and depends on this machine staying up.

### Status

- Workflow file: correct and locally validated (YAML parses, 6 steps, script dry-runs).
- Registration with Actions: **not possible from a feature branch**.
- Forward clock: still **0/30**, advanced only when run by hand.
