# FOREX cost - London/NY overlap measurement (20261125)

**Status: `BLOCKED_NO_REPRESENTATIVE_SESSION`** - block reason `NO_TIINGO_API_KEY` - generated 2026-11-25T13:50:36.533610+00:00

- **Endpoint:** `https://api.tiingo.com/tiingo/fx/top` via [`tools/fx_cost_sampler.py`](../../tools/fx_cost_sampler.py)
- **Session check:** weekday Wednesday 13:xx UTC inside 13:00-16:00 UTC -> `LONDON_NY_OVERLAP` (in-window: True)
- **Sampling:** 0 polls, 20.0s apart, target n>=30 plausible quotes per pair
- **Commission:** `COMMISSION_UNKNOWN` - Tiingo top-of-book exposes bid/ask only; a retail commission cannot be determined from this feed and is NOT assumed zero. Round-trip cost here is SPREAD ONLY.
- **Strategy verdict:** `BLOCKED_NO_REPRESENTATIVE_SESSION` - no representative session -> no verdict move
- **Verdict moves by this tool:** none by default - a blocked run changes no verdict; a measured run may write NOT_INVESTABLE or HUMAN_REVIEW_REQUIRED, never INVESTABLE, and never edits the programme tally

## Rules (verbatim, so the judgement is auditable)

- **session_window:** in-window iff weekday(Mon-Fri) AND 13:00 <= UTC hour < 16:00. GitHub cron is UTC; the window is fixed in UTC year-round.
- **min_samples:** a pair needs n >= 30 plausible quotes to be judged
- **no_quote:** n_plausible == 0
- **insufficient_n:** 0 < n_plausible < 30
- **frozen:** distinct spread values < max(3, 10% of n) OR longest run of identical bid/ask >= 10 OR median vendor quote age > 300s. A pair that returns one price for dozens of polls is frozen, not tight - it is never reported as a 0-sd bargain.
- **wide:** median full spread > 8.0 bp OR IQR/median > 0.5 (unstable book)
- **verdict_order:** NO_QUOTE -> INSUFFICIENT_N -> FROZEN -> WIDE -> REPRESENTATIVE (first match wins)
- **decision_cost:** median of the per-pair medians over the REPRESENTATIVE pairs of the probe universe (the traded universe is 55 crosses, so the all-pairs median is the honest basis); the USD-major median-of-medians is reported alongside
- **strategy_verdict:** NOT_INVESTABLE iff measured decision cost > break-even (derived from the re-run, not hardcoded); otherwise HUMAN_REVIEW_REQUIRED. The allowlist is ['NOT_INVESTABLE', 'HUMAN_REVIEW_REQUIRED', 'BLOCKED_NO_REPRESENTATIVE_SESSION', 'UNCHANGED_UNKNOWN'] - INVESTABLE is unreachable by construction.

## Per-pair (full spread = round trip, bp of mid)

| pair | n | min | p25 | median | p75 | max | mean | sd | distinct spreads | distinct mids | max identical run | median quote age s | verdict | rule |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| eurusd | 0 | - | - | - | - | - | - | - | 0 | 0 | 0 | - | **NO_QUOTE** | n_plausible == 0 |
| gbpusd | 0 | - | - | - | - | - | - | - | 0 | 0 | 0 | - | **NO_QUOTE** | n_plausible == 0 |
| usdjpy | 0 | - | - | - | - | - | - | - | 0 | 0 | 0 | - | **NO_QUOTE** | n_plausible == 0 |
| audusd | 0 | - | - | - | - | - | - | - | 0 | 0 | 0 | - | **NO_QUOTE** | n_plausible == 0 |
| usdcad | 0 | - | - | - | - | - | - | - | 0 | 0 | 0 | - | **NO_QUOTE** | n_plausible == 0 |
| usdchf | 0 | - | - | - | - | - | - | - | 0 | 0 | 0 | - | **NO_QUOTE** | n_plausible == 0 |
| eurgbp | 0 | - | - | - | - | - | - | - | 0 | 0 | 0 | - | **NO_QUOTE** | n_plausible == 0 |
| eurjpy | 0 | - | - | - | - | - | - | - | 0 | 0 | 0 | - | **NO_QUOTE** | n_plausible == 0 |

## Aggregate

- verdict counts: `{'NO_QUOTE': 8}`
- representative pairs: 0 / 8
- **decision cost:** None bp
- USD-major median-of-medians: None bp
- all representative pairs: median None bp, mean None bp, range None bp
- all pairs median-of-medians: None bp

## Chained FX mean-reversion re-run

- not run: `ABSENT`

## Strategy decision

- **verdict written: `BLOCKED_NO_REPRESENTATIVE_SESSION`**
- rule: no representative session -> no verdict move
- guard: allowlist ['NOT_INVESTABLE', 'HUMAN_REVIEW_REQUIRED', 'BLOCKED_NO_REPRESENTATIVE_SESSION', 'UNCHANGED_UNKNOWN'] enforced in `tools/fx_cost_sampler.py::guard_verdict (called before every write)`; INVESTABLE reachable: **False** - a machine that can promote a strategy to investable is a machine that can launder a bug into a position

## Programme state

- 0 INVESTABLE / 8 NOT_INVESTABLE / 6 UNKNOWN
- FX mean-reversion remains UNKNOWN until a representative weekday cost exists AND the window-clustered CI excludes zero
- none by default - a blocked run changes no verdict; a measured run may write NOT_INVESTABLE or HUMAN_REVIEW_REQUIRED, never INVESTABLE, and never edits the programme tally

## Provenance

- raw samples: `(none - dry run)`
- does not overwrite: reports/cost_measurement_forex/FOREX_COST_20261122.json, reports/cost_measurement_forex/FOREX_COST_20261122.md, reports/cost_measurement_forex/fx_top_of_book_samples.json, reports/cost_measurement_forex/fx_top_of_book_samples_window2.json
- kept previous artifact: no
