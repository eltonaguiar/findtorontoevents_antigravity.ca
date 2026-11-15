# 2026-11-15 — attach the benchmark leg at sync time

The forward ledger was scoring picks on **net return**, while the registration says the
endpoint is **excess vs the class benchmark**. `_endpoint()` labelled that swap honestly —
it never pretended to test `excess_pp` — but a labelled wrong statistic is still the wrong
statistic. `rs-breakout-scout` was registered with `endpoint: excess_pp`, a fixed sample of
152 windows and OF boundaries computed for that endpoint. Testing net return against those
boundaries would have decided a different question.

## What changed

`tools/forward_tracker.py sync` now computes the benchmark leg per pick as it appends:

| Field | Meaning |
|---|---|
| `excess_pp` | pick return − benchmark return, in percentage points |
| `bench_ret_pct` | benchmark return over the pick's own window |
| `bench_symbol` | `SPY` / `BTC-USD` from the file's own class map |
| `bench_window` | the two trading days actually used (`2026-02-02..2026-02-06`) |
| `bench_note` | why it is null, when it is |

Source is `audit_dashboard/data/benchmark_prices.json` — the same series the dashboard's
`vs Bench` column reads, so the always-on column and the forward ledger cannot disagree.
`--bench-file` overrides it; `--no-benchmark` restores the old behaviour explicitly.

Conventions are copied from `tools/pick_excess.py`, deliberately: entry is the last close
on/before the pick's **open** day, exit the last close on/before its **close** day. Reusing
the retrospective tool's windowing is what makes the forward test a test of the *same*
statistic the prior was measured on.

## Three refusals, because a default would be a lie

1. **Same-day window** → `window_collapsed_to_one_trading_day`, `excess_pp` null. Daily
   closes resolve both ends to one price, so the benchmark move is identically 0 and every
   intraday pick would collect a free positive excess. Null with a reason, never 0.
2. **Window starting before the series** → `outside_series:SPY`. The dashboard file starts
   2025-01-02; a pick opened in 2024 has no measurable beta, not a zero one.
3. **Class with no benchmark** → `no_benchmark_for_class:FOREX`. Not silently mapped to SPY.

`_endpoint()` still prefers `excess_pp` only when **every** row has one, and the verdict now
also carries `endpoint_missing_rows` and an `endpoint_note` naming the substituted statistic
and how many rows caused it. The sync summary prints `benchmarked N | no benchmark M` per
strategy, so coverage is visible at the point rows are created.

## Verification

`selftest` is **21/21** (8 rule cases, 8 OF checks, 5 new benchmark checks). The benchmark
checks pin the conventions rather than the plumbing: 100→110 over two SPY days is exactly
+10.00pp, a same-day window is refused, a pre-series window is refused, an unmapped class is
named, and BTC 50000→45000 reads −10.00pp.

An isolated end-to-end sync (temp state dir, real SPY series, 4 synthetic closed picks):

| Pick | ret | bench | excess | outcome |
|---|---:|---:|---:|---|
| AAA long 02-02 → 02-06 | +10.0000% | −0.6888pp | **+10.6888pp** | scored |
| BBB long same day | +3.0000% | — | null | `window_collapsed_to_one_trading_day` |
| EURUSD (FOREX) | +1.8182% | — | null | `no_benchmark_for_class:FOREX` |
| CCC short 04-01 → 04-10 | +11.1111% | +3.6964pp | **+7.4147pp** | scored |

Each scored row was then recomputed independently from the raw series with `bisect`, and the
stored `bench_window` endpoints were asserted against the days that lookup chose. A second
sync appended 0 rows (duplicate 4), so attaching the benchmark did not disturb idempotency.

Real payload unchanged: `vwap-reversion-scout` 0 / 29 before registration, `rs-breakout-scout`
0 / 45 before registration / 68 class mismatch — identical to before this change.

## Limits

- The committed benchmark file is a snapshot (`generated_utc 2026-11-15T02:42:12Z`). The CI
  job refreshes it to `/tmp` and never commits it, to avoid two workflows fighting over the
  same path — so a ledger row's excess is frozen at the closes available when it was synced.
  Re-scoring historical rows would require a re-sync, and nothing does that yet.
- **The ledger is still empty.** No forward `excess_pp` exists; this change means the first
  admitted pick will carry one. `rs-breakout-scout` remains 0/152.
- Sub-day picks are structurally unscorable from daily closes. `pick_excess.py` falls back to
  60m bars for those; the ledger deliberately does not, because an hourly bar fetched months
  later is not the bar that was available at decision time.
- Payload class can be blank; the strategy's registered class is used then. For
  `rs-breakout-scout` (`strict_class: true`) that combination is already skipped, so the
  fallback only ever applies to classes the payload itself declares.
