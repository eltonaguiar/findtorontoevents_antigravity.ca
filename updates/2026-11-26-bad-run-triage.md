# 2026-11-26 — Bad-run triage: 7,000 runs in 7 days reduced to 118 unresolved

Source: Hermes (Hermes One desktop agent, seat `elton2026/hermes-agent/hermes-laptop`),
triaged 2026-11-26 against `eltonaguiar/findtorontoevents_antigravity.ca`.
Companion COMS note: `notes/hermes-one-badruns-triage-20261126`.

## What was wrong

The Actions query that lists every non-success conclusion
(`is:cancelled is:action_required is:failure is:neutral is:queued is:skipped is:stale
is:timed_out is:awaiting`) returns thousands of rows and is unreadable as a work list.
There was no documented rule for deciding which of those rows are real defects and which
are already-superseded noise, so red rows accumulated in the UI with nobody triaging them.

## Method

Query is feed-based and was re-checked live at write time. The filter rule
("if the same workflow on the same branch succeeded later, the failure is void") did most
of the work:

| stage | count |
|---|---|
| runs since 2026-11-19 | ~7,000 |
| non-success runs | 678 |
| voided — same workflow + branch succeeded later | 436 |
| **genuinely unresolved** | **118** |

## Branch question — answered definitively

- **gh-pages carries zero workflow files.** Nothing there can fail and nothing there needs
  transitioning to main. (API returns 404 for `.github/workflows` on `gh-pages`.)
- **97 of 100** distinct workflows in the unresolved set exist on **main**.
- Only **3 files exist solely on a branch**, all one-shot ops tooling:
  - `ops-install-gx10-pubkey` (failed 3×)
  - `ops-laptop-ssh-setup`
  - `ops-laptop-ssh-tunnel`
- The laptop pair is moot — that runner was decommissioned. `ops-install-gx10-pubkey` is the
  only porting candidate, and only if it is still the documented way to add keys.

## The 118, split

| bucket | count |
|---|---|
| real, on main | 12 |
| stalled | 2 |
| normal churn | 18 |
| branch noise where main is green | 71 |
| same as main | 5 |
| branch-only | 10 |

**63 of the 118 come from a single branch, `verify/self-hosted-routing`** — that morning's
routing-verification dispatches. Main's copies of the same workflows succeeded later, so
these are test artifacts, not defects. Removing the branch removes half the alarming rows.

## Real fixes, in order

Each row names the failing step or error, not a guess.

| fix | why |
|---|---|
| Delete `rl-agent-ppo.yml`, `deploy_bundle.yml`; retire `pine-generator` | `if: false` since March / `AttributeError: 'list' object has no attribute 'values'` / downstream skip — three workflows that only ever report bad |
| Serialise Pages deploys repo-wide | `deploy-riseoftheclaw` fails with 400 `due to in progress deployment`; two sibling workflows race for the same Pages site, so it is a concurrency problem, not a code bug |
| Delete branch `verify/self-hosted-routing` | 63 of 118 rows were that branch's routing-verification dispatches; deleted 2026-11-26 (see Outcome) |
| Decide `2hour_challenge` vs `real_2hour_challenge` | 5 straight cancels, killed at 30 min, no log; the `real_` twin succeeds |
| Fix or mute `sign-coherence-gate` | daily cron, red 2 days, nobody reads it |
| Dispatch `gha-quality-framework` once | last result came from the copy the bot deleted; restored 2026-11-26T20:24Z and never run since |

## Stalled at time of triage

- `discord-bot` — pending 3h, no runner ever picked it up. Cancel it so the next cron queues.
- `branch-large-file-dup-guard` — `in_progress` >1h with 39/40 runs cancelled and zero
  successes; a repo-wide lint that has never once completed.

## Not diagnosed — stated as a limit, not a finding

No downloadable log exists for these runs, so the failing step is verified and the cause is not:
`forward-observations-ingest`, `verification-tests`, `clear-channel-command`.

## Outcome (2026-11-26, same day)

Two of the six fixes were actioned after this triage:

**Branch `verify/self-hosted-routing` deleted.** Before deleting, its 12 ahead commits were

checked against main (it was 7,271 commits behind):

- `battleground/incubator/strategies/*.py` relative-import fix — **identical on main**, nothing lost.
- `.github/scripts/safe_push.sh` — main is **newer**: main carries the mass-delete guard added

  after commit `808f812f` deleted 807 paths; the branch version predates it.
- 22 workflow files — the only unique delta was hardcoded `runs-on: [self-hosted, gx10]`,

  which main replaces with `${{ vars.ACTIONS_RUNNER_LABEL || 'ubuntu-latest' }}`. That routing

  experiment was the point of the branch, and it is what produced the 63 false-red rows.

The remaining ahead commits were bot noise (`realtime-challenge: cycle`, `provenance: chain`).

No open PR pointed at the branch. Deleted head: `624e5c27ff04b4f09e9cf7fe72658bf25c44639e` —

restorable with `git push origin 624e5c27:refs/heads/verify/self-hosted-routing` while the

object is still reachable. Branch count 315 → 314.

**Pages concurrency fix opened as PR #1233.** `deploy-riseoftheclaw.yml` and

`deploy-bestiejob-page.yml` were the only two workflow files on main using Pages, and each had

its own concurrency group, so both could enter `actions/deploy-pages` at once and the loser got

`400 ... due to in progress deployment`. Both now use the shared group `github-pages`; each

file's `cancel-in-progress` is deliberately unchanged (see the PR body for why `riseoftheclaw`

must keep `true` — a queued run that never starts starves the group forever).

## State of this work

Triage plus those two actions. No workflow or run was modified outside PR #1233.
