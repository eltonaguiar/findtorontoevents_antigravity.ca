# GitHub Actions census without the REST API

**Date:** 2026-11-25 · **Tool:** `tools/gha_web_census.py` (new) · No workflow behaviour changed.

## Why

The account's GitHub REST quota (5,000/h, shared by every agent using the token) ran dry twice
today, once mid-census: `API rate limit exceeded for user ID 38769710`. A census costs ~110 REST
calls, and several agents polling it is what empties the bucket.

GitHub server-renders each Actions page with the same JSON the UI consumes:

```html
<script type="application/json" data-target="react-app.embeddedData">{...}</script>
```

A plain HTTPS GET of that page costs **no REST quota** and carries the same fields the API returns
for a run: `workflowName`, `workflowFilePath`, `state.status`, `state.conclusion`,
`createdAt.timestamp`, `id`.

## Usage

```
python3 tools/gha_web_census.py                       # recent-runs census
python3 tools/gha_web_census.py --pages 20            # 25 runs per page
python3 tools/gha_web_census.py --dormant             # every workflow's last run
python3 tools/gha_web_census.py --watch qa-market-validation hub-sync deploy-riseoftheclaw
```

Writes `reports/gha_web_census_latest.json`. Exit 1 if no run could be read.

## How dormancy is answered without the API

Neither obvious page works: `/actions?page=N` exposes only 50 workflows, and `/actions/workflows`
embeds no payload at all (the first implementation read there and silently reported
`dormant=0 of 0`). The tool reads `payload.codeViewTreeRoute.tree.items` from
`/tree/main/.github/workflows` — **382 workflow files** — and then fetches a workflow page only for
files it has not already seen running in the window.

## Two bugs in my own tool, both caught by cross-checking

1. **Uppercase conclusions.** `FAIL_C` held `{"FAILURE","TIMED_OUT"}` while `norm()` lowercases, so
   no failure ever matched: every report said *"0 failures with no later success"* beside a MIX line
   counting failures. Fixed, with a comment tying the set to `norm()`.
2. **Unreadable pages counted as "never registered".** A throttled fetch returned `[]`, the same as a
   workflow that genuinely never ran, and a throttled scan reported 145 such workflows. Now `None`
   (unreadable) and `[]` (no runs) are distinct, and unreadable pages are excluded from dormancy
   rather than inflating it.

Both were found by comparing numbers printed in the same output, not by the tool passing.

## Throttling: HTML is rate-limited too

~1,000 page fetches at 12 workers got the tool soft-blocked: `/actions` returned 1 page instead of
14 and the tree page returned nothing, so a census silently degraded to a 25-run window. GitHub then
sent `Retry-After: 300`. The tool now paces every request (`MIN_INTERVAL = 0.5 s`, one global lock),
honours `Retry-After` capped at 20 s, retries 429/403/5xx, and — most importantly — **says when it
is reporting a partial window** instead of quietly narrowing it.

## Result: clean run at 22:54 UTC (290 requests, 0 throttles, 0 REST calls)

- Window: **150 runs**, `22:22:03Z → 22:53:50Z`.
- Mix: success 109, cancelled 5, failure 3, in_progress 31, skipped 1, queued 1.
- Failures: `Deploy Rise of the Claw Dashboard` 22:37 (`45714838451`), `masking-policy-lint` 22:42
  (`45715565680`), `validation-gates.yml` 22:44 (`45715804546`).
- **Failures with no later success: 2** — `validation-gates.yml` (22:44, 1 of 2 runs failed, no
  success in window) and `Deploy Rise of the Claw Dashboard` (22:37, last success 22:22).
- Dormancy: **61 of 382** workflow files have not run in >24 h; 21 have never run; 0 pages
  unreadable. Longest gaps: `pick-flow-snapshot-fast.yml` (4,441 h ≈ 185 d),
  `strategy-performance-no-regression.yml` (4,371 h), `ai-tournament-pipeline.yml` (4,186 h),
  `ai-leaderboard-refresh.yml` (4,172 h), `battleground-mass-backtest-part2.yml` (4,143 h).

Watched workflows in the same window: `qa-market-validation` succeeded at 22:16 after seven failures
(see `updates/2026-11-25-gha-workflow-patches-applied.md` for why that green is a market-close
artefact); `hub-sync` and `live_tracker` succeeded on every hourly run; `deploy-riseoftheclaw`
alternated success/failure — 22:22 success, 22:37 failure — the intermittent pattern of the
artifact-visibility race.

## Limits

- Run logs and step-level detail are **not** in the HTML. This answers *what* failed, *when*, and
  whether it later recovered — not *why*. Confirming a cause still needs `gh run view --log-failed`
  or the web UI.
- It scrapes a page shape GitHub may change. If `embeddedData` disappears the tool exits 1 with
  "could not read any run" rather than reporting an empty result.
- Anonymous only: no token is sent, so it sees what a logged-out visitor sees.
- Dormancy counts workflow *files*. The REST API's 198 is the number *registered* with Actions;
  382 is how many `.yml` files exist. Both are true of different denominators.
