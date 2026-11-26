# Three workflows whose gates could never fire: referencing a step id that doesn't exist

**Date:** 2026-11-25 · **Found by:** `actionlint 1.7.7 -shellcheck=` · **API calls:** 0

`actionlint` reports 8 native findings on `main`. Four were `concurrency: queue` (see the end of
this note); the other four were expressions referencing a step id that no step declares. In GitHub
Actions that is not a warning — the expression silently evaluates to an **empty string**, so the
`if:` is false forever and the step never runs.

## What was broken

**1. `signal-quality-monitor.yml` — the quality alert could never fire.**
`Alert on quality issues` is gated on

```yaml
if: steps.monitor-quality.outputs.has_alerts == 'true'
```

but the step that writes `has_alerts`, `alert_count`, `win_rate` and `expiration_rate` to
`$GITHUB_OUTPUT` is `Analyze signal quality trends`, which had **no `id:`**. `steps.monitor-quality`
was an empty object, `.outputs.has_alerts` was `''`, and `'' == 'true'` is false. Every run went
green while the Discord alert path was dead. Only one step id was missing, so the failure looked
exactly like "no alerts to report".

**2. `automated-reporting.yml` — the notification reported an empty signal count.**
The Discord step read `steps.generate-report.outputs.signals_count`; the step that writes
`signals_count` is `Generate report`, which had no `id:` (the file's only id was `report-type`).
`SIGNALS` was always empty in the notification body.

**3. `optimize-score-thresholds.yml` — threshold updates were never committed.**
The commit step was gated on

```yaml
if: ... && steps.validate-thresholds.outcome == 'success'
```

and no step has the id `validate-thresholds`. Empty expression → false → the step was skipped on
every run. The walk-forward optimiser and the dynamic threshold optimiser both ran, and their output
was thrown away at the commit step.

## What changed

| file | change |
|---|---|
| `signal-quality-monitor.yml` | `Analyze signal quality trends` gains `id: monitor-quality` |
| `automated-reporting.yml` | `Generate report` gains `id: generate-report` |
| `optimize-score-thresholds.yml` | `Run dynamic threshold optimizer` gains `id: threshold-optimizer`; the commit gate now references `steps.threshold-optimizer.outcome` |

Behaviour after the fix is what the authors originally intended: the alert step can now fire, the
notification carries a real count, and threshold results get committed. That means the next
`scheduled` run of `signal-quality-monitor.yml` may post to `DISCORD_QUALITY_ALERTS` for the first
time — intended, but worth knowing before it surprises anyone.

## Verification

`actionlint -shellcheck= .github/workflows/*.yml` → **8 findings before, 4 after**, and the 4 that
remain are all the `queue` key below. The three expression errors are gone and every file still
parses as YAML.

## The four `queue: max` findings are a linter false positive — deliberately not changed

`crypto-ohlcv-refresh.yml`, `daily-prices-yf-refresh.yml`, `db-freshness-guardian.yml` and
`stocks-daily.yml` all set

```yaml
concurrency:
  group: ...
  cancel-in-progress: false
  queue: max
```

`actionlint` calls `queue` "unexpected key … expected one of cancel-in-progress, group". If that
invalidated the file, the workflows could not run at all. They do run, and they succeed — checked
without the API through the workflow pages:

```
db-freshness-guardian   23:15, 22:16, 21:16, 20:16, 19:14, 18:18  all success (hourly)
stocks-daily            21:45 success, and the same slot on each prior day
crypto-ohlcv-refresh    every 4 h, all success
daily-prices-yf-refresh 08:36 daily, all success
```

So GitHub ignores the unknown key and the linter is ahead of (or behind) the platform. Removing
`queue: max` would be churn on four working hourly/daily jobs with nothing to gain, so it stays.
If GitHub ever starts rejecting it, these four will fail loudly and the fix is a one-line delete.

## Also fixed: `tools/gha_web_census.py --watch` crashed instead of reporting

Found while gathering the evidence above. Two bugs, both in the code path that reads a single
workflow page:

- The slug was interpolated as `f".github/workflows/{slug}.yml"`, so the documented usage
  `--watch stocks-daily.yml` requested **`stocks-daily.yml.yml`** → HTTP 404 → `None`.
- `workflow_last_runs()` then called `.sort()` on that `None` before storing it, raising
  `AttributeError: 'NoneType' object has no attribute 'sort'` and killing the whole run after the
  census had already been collected.

Now the extension is stripped (`.yml`/`.yaml` both accepted), comma-separated lists are split, and a
`None` from a 429/timeout is preserved so callers can report "unreadable" instead of crashing — which
is the behaviour the function's own docstring already promised.
