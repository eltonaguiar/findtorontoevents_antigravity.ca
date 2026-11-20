# Correction: the dashboard cron is 3-hourly, and a 0-that-min lag is luck

**Date:** 2026-11-20T07:31Z
**Area:** documentation for `.github/workflows/audit-dashboard.yml` (no behaviour change)
**Base:** `origin/main` @ `48fd154df20`

## What was wrong

Two merged docs -- `updates/2026-11-20-audit-publish-stall-and-sleeve-gate-wiring.md` (PR #985)
and `updates/2026-11-20-single-publisher-audit3-ledger.md` (PR #994) -- described the dashboard
producer as "hourly `:10`, ~35 min job". I asserted that; I had not read the cron.

The actual trigger on main is **`cron: '10 */3 * * *'`** -- every 3 hours at :10. The 6-hourly
counterpart is `audit3-ledger.yml` at `23 */6`. Both read from the merged blob, not inferred
from run timestamps.

The workflow comment I added in #994 repeated the same error ("full 6-hour cycle behind").

## Why it does not change the fix

The defect was structural -- two workflows publishing one artifact and racing on it -- which is
independent of cadence. What cadence changes is the *rate* of stale overwrites: at most **two**
per fresh 6-hourly ledger, not the six implied by "hourly".

## A second, more interesting correction

At 07:10Z today the two URLs were **byte-identical**, `/audit/data/audit3_ledger.json` and
`/audit3/audit3_ledger.json`, both `633,608 B`, both `generated_at 2026-11-20T06:37:23Z`,
sha `812f035ef0`. That looks like the fix working. It is not: my merge landed at 07:29Z, after
that ledger was generated.

The real reason is `git pull --no-rebase --no-recurse-submodules -X ours --no-edit origin main`
inside the dashboard's own commit step. When that pull lands *after* the ledger commit, the
dashboard republishes identical bytes and the lag reads 0.0 min. When it lands before, it
republishes an older ledger -- the 222.6 min case measured earlier today.

So the lag is **not** a constant offset, it is a race: 0.0 min when the pull is lucky, hours
when it is not. A parity gate that only passes on lucky runs is the actual problem, and
single-publishing removes the race rather than tuning its odds.

## What changed here

Documentation only, plus one workflow comment:

| File | Change |
|---|---|
| `updates/2026-11-20-audit-publish-stall-and-sleeve-gate-wiring.md` | "hourly `:10`" -> "`10 */3`, every 3 hours"; table row and title corrected; correction section appended |
| `updates/2026-11-20-single-publisher-audit3-ledger.md` | same cadence correction, "six stale writes" removed; §7 correction appended |
| `.github/workflows/audit-dashboard.yml` | comment "full 6-hour cycle behind" -> "up to a full 3-hour cycle behind"; **no executable change** |

No code path, threshold, or deploy behaviour is touched. `git diff` on the workflow is comment
lines only.

## Verification

- `grep` for the stale phrases across all three files returns nothing.
- Workflow YAML still parses (`jobs = ['generate-and-deploy']`).
- Diff for the workflow is confined to the comment block; `for df in _jsons:` logic and the
  `_PUBLISHED_ELSEWHERE` skip are unchanged.

## Limitations

1. The 222.6 min figure was measured once, on one cycle; I have not characterised the lag
   distribution across many cycles, and with the race removed there is no population left to
   measure.
2. Corrections are appended, not substituted, so the original wrong sentences are still visible
   in §1 of both docs. That is deliberate -- a silent edit would hide that I asserted something
   I had not checked.
