# Why PRs #1116, #1125 and #1149 show no CI checks while others run six

**Date:** 2026-11-26
**Repo:** `eltonaguiar/findtorontoevents_antigravity.ca`

## Question

Seven PRs were open at audit time. #1128, #1150, #1151 and #1154 each had six or
more green checks; #1116, #1125 and #1149 appeared to have none.

## Answer: they are merge-conflicted, and `pull_request` workflows run on the merge ref

`pull_request`-triggered workflows do **not** run on the head commit. They run on
the synthetic merge commit `refs/pull/<n>/merge`, which GitHub builds from
`base` + `head`. If that merge cannot be built (conflict), the ref is not created
or stops being refreshed, and **no `pull_request` workflow runs at all** — no
failure, no queued run, nothing to display.

### Measured state

```
git ls-remote origin 'refs/pull/1116/*' ...
12b0e523a0  refs/pull/1116/head        <- head only, NO /merge
2ebd6e1436  refs/pull/1125/head        <- head only, NO /merge
370c35092a  refs/pull/1128/head
374948c653  refs/pull/1128/merge
6542e7382e  refs/pull/1149/head
356ab6ee18  refs/pull/1149/merge       <- present but STALE
554d519b16  refs/pull/1154/head
513090a030  refs/pull/1154/merge
```

`mergeable_state` for each PR:

| PR | mergeable_state | base | PR-triggered runs |
|---|---|---|---|
| #1116 | `dirty` (conflict) | 2fefbf9f2b | **0** |
| #1125 | `dirty` | 5d95b95c79 | **0** |
| #1149 | `dirty` | dd37b112b2 | 7 per wave, up to 00:34 only |
| #1128 | `dirty` (transient) | 5d95b95c79 | 6 |
| #1150 | `clean` | 5b48f33486 | 8 |
| #1154 | `clean` | 2db521a338 | 9 |

`mergeable_state=dirty` is GitHub's "has merge conflicts" state. It is not
`behind` (merely stale base) — `behind` PRs still run.

### Per-PR detail

**#1125** — one commit, one changed file (+10/−0). Its only run is
`workflow_dispatch` on `deploy-riseoftheclaw.yml`, i.e. a manual trigger, unrelated
to the PR. No merge ref → no PR gate.

**#1116** — 193 commits, 1846 files. Its only run is `push`
(`validation-gates.yml`), because `push` triggers do not need a merge ref. The
`pull_request` gates never fired.

**#1149** — this is the subtle one. It *did* run checks, three waves, all green:

```
00:31:50Z  2255ba2710  masking-policy-lint, Tribunal Runtime Gate,
                       Conflict Marker Check, No stale DB passwords,
                       DB Password Leak Guard, Secret Scan (M-043)
00:34:19Z  2911eb6ea1  same six + CI Tests   (all success)
```

Then three more commits landed (00:53:26, 00:57:00, 01:18:08) and produced **zero
runs**. The merge ref explains it — its parents are:

```
356ab6ee18 ^1 = 8b50604019   (old base)
          ^2 = 2911eb6ea1   (last checked commit)
```

while the PR's current base is `dd37b112b2`. The merge ref froze at the old base
after `2911eb6ea1`, so GitHub stopped building merge commits for the new pushes.
The PR page shows the *latest* commit `6542e7382e`, which has no checks attached —
hence "no CI checks at all".

**#1128 / #1150 / #1151 / #1154** — merge refs present and current, so the six
small gates fired normally.

## What the six are

The baseline gate set every healthy PR gets (all `pull_request`-triggered):

| check name | workflow | trigger |
|---|---|---|
| `lint-masking` | `masking-policy-lint.yml` | PR, paths: `.github/workflows/**`, `.github/masking_manifest.yaml`, `scripts/lint_workflow_masking.py` |
| `Tribunal Runtime Gate` | `tribunal-runtime-gate.yml` | PR |
| `scan` | `conflict-marker-check.yml` | PR, push to main, dispatch |
| `Grep for stale hardcoded DB passwords` | `no-stale-db-passwords.yml` | PR + push to main |
| `scan-new-additions` | `db-password-leak-guard.yml` | PR, paths: `**.py`, `**.sh`, `**.yml`, `**.yaml` |
| `Gitleaks PR diff scan` | `secret-scan.yml` | PR to main + cron + dispatch |

`CI Tests` and `ledger` are additional, not part of the baseline six.

## Consequences / fixes

1. **Nothing is broken in CI.** No workflow is skipping these PRs; GitHub never had
   a merge commit to attach them to. The PRs must resolve their conflicts first.
2. **#1116 cannot merge as-is** — 193 commits, 1846 files, conflicted. See
   `updates/2026-11-26-pr1116-diff-audit.md`: 82% of its diff is generated data.
   It should be split into a code PR and a data/artifacts PR rather than rebased.
3. **#1125** is a 1-file fix that conflicts — rebase onto current `main` and the six
   gates will appear immediately.
4. **#1149** just needs a rebase of the last three doc commits; its six gates were
   already green on `2911eb6ea1`.
5. Future audits should read `mergeable_state` **before** concluding a PR has no CI.
   A zero-run PR is a conflict signal, not a CI outage signal.

## Verification notes

- Run lists came from `/actions/runs?event=pull_request` filtered on
  `.pull_requests[].number`, not from a 500-run window (this repo's 500-run window
  is under 2 hours, so it cannot be used to judge history).
- `/commits/<sha>/check-runs` for the *head* sha returns 0 for all three PRs, which
  is exactly what the UI shows; the earlier `pull_request` runs are attached to
  earlier shas.
