# Checking GitHub Actions health without the REST API — what works, what doesn't

**Date:** 2026-11-25 · **Tools:** `tools/gha_web_census.py` (extended with `--health`), `actionlint`

Motivation: the shared 5,000/h REST quota ran dry twice in one session. Each check below was
actually run against `eltonaguiar/findtorontoevents_antigravity.ca` and the result recorded.

## What can be checked with zero API calls

| Question | How | Result |
|---|---|---|
| Did runs pass or fail, and when? | `/actions?page=N` embedded JSON (`react-app.embeddedData`) | ✅ conclusions + timestamps for 25 runs/page |
| Which workflow failed, and does it have a later success? | same payload, grouped by `workflowFilePath` | ✅ |
| How healthy is each workflow (rate, streak, flakiness)? | new `--health` | ✅ success %, failure count, current failure streak, outcome flips |
| What workflow files exist at all? | `/tree/main/.github/workflows` → `codeViewTreeRoute.tree.items` | ✅ all 382 |
| Has a workflow run recently? | one page per workflow, `/actions/workflows/<file>` | ✅ last run + conclusion |
| Is a scheduled workflow actually on time? | compare last-run age with the file's own `cron` | ✅ (see the dormancy triage doc) |
| Is the YAML valid? | `actionlint` over the checkout | ✅ 379 files, 8 findings |
| Is the page rendering as users see it? | Playwright/Chrome (see below) | ✅ but adds nothing for the list |

## What still needs the API

**Step-level detail and logs.** Verified three ways on failed run `45714838451`:

- raw HTML of `/actions/runs/<id>`: 0 occurrences of any step name ("Upload artifact", "Deploy to
  GitHub Pages", "Wait for …");
- raw HTML of the job page `/actions/runs/<id>/job/<job_id>` (job id `139558131979` is discoverable
  from the run HTML): also 0;
- a real headless Chromium rendering both pages (`wait_until=domcontentloaded` + 5 s): the rendered
  body contained none of the step names, and no step-like rows.

So the job/step list is loaded from an authenticated endpoint after page load. For *why* a run failed,
use `gh run view <id> --log-failed` — it is one call, and it is the only part worth spending quota on.
This is exactly how the `No module named pytest` cause was found.

## The browser (chrome-devtools / Playwright) route: honest verdict

A headless Chromium render of `/actions` returned the same 25 runs the embedded JSON already gives,
just as text and links, with no conclusions. It is a real fallback for when GitHub changes the JSON
shape, and a way to *see* the page, but it is slower, heavier, and strictly less data than parsing the
payload. For step logs it needs a logged-in profile, which this environment does not have.

## `--health` output at 23:2x UTC (400-run window)

```
validation-gates.yml              runs= 4 ok= 50.0% fails=1 streak=0 flips=2 last=success
Deploy Rise of the Claw Dashboard runs= 3 ok= 66.7% fails=1 streak=0 flips=2 last=success
Secret Scan (M-043)               runs=15 ok= 86.7% fails=1 streak=0 flips=2 last=success
masking-policy-lint               runs=14 ok= 92.9% fails=1 streak=0 flips=2 last=success
139 workflows had no failure in the window; 4 had at least one
```

`flips` counts success↔failure transitions, which is the cheapest flakiness signal available without
logs: a workflow that flips repeatedly with no code change is flaky, not broken.

## `actionlint` baseline (installed locally, no API)

379 `.yml` workflows on `main`: **8 findings in 7 files**.

- 4 × `unexpected key "queue" for "concurrency" section` (`signal-quality-monitor.yml` ×2,
  `stocks-daily.yml`, `optimize-score-thresholds.yml`, `db-freshness-guardian.yml`). Verify against
  current GitHub docs before changing these — if `concurrency.queue` is now supported, the finding is
  the linter being older than the platform, and "fixing" it would remove a working feature.
- 4 × undefined step id: `steps.monitor-quality`, `steps.validate-thresholds`, `steps.generate-report`
  referenced in `if:` conditions with no matching `id:`. These are genuine: the expression always
  evaluates empty, so the gate silently never runs.

The four workflows touched today (`qa-market-validation`, `deploy-riseoftheclaw`, `hub-sync`,
`live_tracker`) lint **clean**.

## Recommended loop for this repo

1. `actionlint .github/workflows/*.yml` before pushing (0 API calls, catches the silent-gate class).
2. `python3 tools/gha_web_census.py --health --dormant` to see state (0 API calls).
3. `gh run view <id> --log-failed` only for a run the census flagged — 1 call instead of ~110.
4. Never poll the API in a loop for status; the census already gives conclusions.
