# M2-residual: scheduled London/NY-overlap FOREX cost measurement (2026-11-22)

## What was missing

FOREX cost had been measured **once**, at the Sunday 22:00Z weekly reopen
([`reports/cost_measurement_forex/FOREX_COST_20261122.md`](../reports/cost_measurement_forex/FOREX_COST_20261122.md)).
That is a real book but a thin one - frozen pairs, wide spreads, high variance - so it
is an **upper bound**, and it cannot close FX mean-reversion. The representative
number (a weekday London/NY-overlap session) was owed, but it only existed if a human
happened to re-run the probe on a weekday. It never happened. This item makes it
self-completing.

## What was scheduled

[`.github/workflows/fx-cost-overlap.yml`](../.github/workflows/fx-cost-overlap.yml):

- **Cron, weekdays only, inside 13:00-16:00 UTC**: six runs across the window
  (`:48`/`:56` at 13h, `:52`/`:57` at 14h, `:54`/`:58` at 15h, all `* * 1-5`).
  Several runs, not one, so a single flaky API call cannot produce a null result.
- **Why the overlap**: 13:00-16:00 UTC is when the London and New York sessions are
  both open - the deepest, tightest FX liquidity of the day, i.e. the session whose
  spread a G10 strategy would actually trade in. GitHub cron is UTC, and this window
  is fixed in UTC year-round, so DST does not move it the way it moves a local-time
  schedule.
- **Secret**: `TIINGO_API_KEY`, the existing repository secret (already used by
  `etf-spread-series.yml`, `stocks-daily.yml`, `qa-market-validation.yml`,
  `etf-bond-scanner.yml`). No key is hardcoded and none is in the YAML body.
- **Concurrency**: its own group `fx-cost-overlap`, `cancel-in-progress: false`.
- **Read-only**: the only write is the artifact commit. No MySQL, no trading, no order
  path. `permissions: contents: write` covers the commit and nothing else.
- **Commit**: `chore(fx-cost): overlap spread sample [skip ci]` - the `[skip ci]` is
  mandatory (this repo has been burned by an unguarded commit loop).
- **`workflow_dispatch`** for manual runs.

## The sampler

[`tools/fx_cost_sampler.py`](../tools/fx_cost_sampler.py) was **extended** (one
implementation, two modes) rather than duplicated. The legacy mode is unchanged; the
new `--overlap` mode:

1. gates on the session (`in-window iff weekday AND 13:00 <= UTC hour < 16:00`);
2. polls until every pair has `n >= 30` plausible quotes;
3. per pair records min / p25 / median / p75 / max / mean / sd / IQR, the count of
   **distinct spread values** and **distinct mids**, the longest run of an unchanged
   quote-or-spread, and the median vendor quote age;
4. assigns each pair a verdict, **first match wins**, with the rule recorded verbatim:
   `NO_QUOTE -> INSUFFICIENT_N -> FROZEN -> WIDE -> REPRESENTATIVE`;
5. aggregates a decision cost = median of per-pair medians over the REPRESENTATIVE
   pairs (the all-pairs basis, because the traded universe is 55 crosses);
6. chains the FX mean-reversion re-run to that cost;
7. writes `FOREX_COST_<YYYYMMDD>_overlap.{json,md}`.

### How a FROZEN pair is caught

A pair that returns one price for dozens of polls is **frozen, not tight** - it is
never reported as a 0-sd bargain. It is `FROZEN` if any of:

- distinct spread values `< max(3, 10% of n)`, or
- longest run of identical bid/ask/spread `>= 10`, or
- median vendor quote age `> 300 s`.

A pair is `WIDE` (unstable) if its median spread `> 8 bp` or its `IQR/median > 0.50`.
Only a pair that is none of these is `REPRESENTATIVE`. The `--self-test` mode pins
these rules with fixtures: a single-price series, a low-distinct series, a series
with a jittering mid but a frozen spread, a wide/unstable series, a healthy one, and
the empty and short cases.

## The auto-promote guard

The job can write exactly one of:

`NOT_INVESTABLE`, `HUMAN_REVIEW_REQUIRED`, `BLOCKED_NO_REPRESENTATIVE_SESSION`,
`UNCHANGED_UNKNOWN`.

**`INVESTABLE` is not in the allowlist.** The rule: if measured cost > break-even
(break-even derived from the re-run, not hardcoded) the verdict is `NOT_INVESTABLE`;
otherwise it is `HUMAN_REVIEW_REQUIRED` - even when the window-clustered CI excludes
zero. It is enforced in `guard_verdict()`, which is called before every write, and it
raises on any verdict outside the allowlist (including `INVESTABLE` and the research
states `CANDIDATE`/`WEAK`). A machine that can promote a strategy to investable is a
machine that can launder a bug into a position.

## What happens on a blocked run

If the run is off-session, on a suspected holiday, API-unreachable, or every pair
comes back FROZEN/WIDE/NO_QUOTE, the artifact says
`BLOCKED_NO_REPRESENTATIVE_SESSION` with the diagnostics (session label and reason,
per-pair verdicts and rules), and **no verdict changes**. Additional guards:

- a fixed-date holiday is **labelled** (the market may still be open; the label never
  suppresses sampling);
- a blocked run **never overwrites** an existing `MEASURED_REPRESENTATIVE` artifact -
  it writes to `..._overlap_blocked_<HHMM>.json` instead, so a good weekday number
  cannot be clobbered by a 03:00 Christmas run;
- the workflow step does not fail on a blocked session (it is a real state, not a
  failure), so the job stays green and the artifact records why.

## Numbers recorded this session (2026-11-22, Sunday)

The market was closed, so no overlap measurement exists yet. What was verified:

- **Chained re-run at the Sunday upper bound (7.533 bp)**: FX mean-reversion net
  **-3.2292 bp**, window-clustered CI95 **[−10.852, +4.553]** - **still includes
  zero**. Break-even re-derived from the run: **4.3038 bp** (drift 0.0000).
- **At the documented break-even**: net 0.0038 bp, clustered CI [−7.62, +7.79] -
  includes zero.
- **At 1 bp**: net +3.30 bp, clustered CI [−4.32, +11.09] - includes zero.

So even a cost far below the Sunday upper bound does not close FX mean-reversion: the
window-clustered CI includes zero at every cost tested. The representative cost is
necessary but, on this evidence, not sufficient.

## Tally

**Unchanged: 0 INVESTABLE / 8 NOT_INVESTABLE / 6 UNKNOWN.** FX mean-reversion stays
`UNKNOWN`. Nothing auto-promoted; no verdict moved.

## Verified

- `py_compile` on every touched Python file: **PASS**.
- GHA quality framework (Q1-Q10) on the new workflow: **score 100/100, no blocking
  (P0/P1) findings**. The only hits are repo-level advisory (P2) cron-minute
  collisions, which are unavoidable (40 workflows already share `:00`); `--check`
  exits 1 both with and without this workflow, i.e. the pre-existing baseline is
  unchanged.
- Dry run while the market is closed: emits `BLOCKED_NO_REPRESENTATIVE_SESSION`
  (`OFF_SESSION_WEEKEND`), exit 0, writes no bogus number.
- `--self-test`: 7/7 fixtures pass.
- End-to-end with an injected representative book: `MEASURED_REPRESENTATIVE`, then a
  blocked run wrote a separate `_blocked_` file and left the measured artifact
  intact.
