# GHA QA rule catalog (Q1-Q10)

Each rule is implemented in `tools/gha_quality_framework.py` and exercised by `--self-test`
(it must fire on a crafted bad workflow and stay silent on a crafted good one). Severity maps to
the gate in `GHA_QA_FRAMEWORK.md` Layer E.

## Q1 cron-stampede (P2, advisory)
Two or more workflows scheduled at the same cron minute. They contend for runners and the shared
REST API budget. Heuristic: the file does not say which share resources, so it is advisory.
Measured count: 60 groups [SRC: GHACTIONS_LIVE/gha_quality.md].

## Q2 unpinned-action (P1, blocking)
A third-party `uses:` that is not pinned to a 40-char commit SHA. First-party `actions/*` may use
a major tag (GitHub's documented convention). A mutable tag on someone else's action is a
supply-chain risk. Measured count: 10.

## Q3 write-all-default (P1, blocking)
A workflow that pushes to the repo but declares no `permissions:` block (so it inherits the repo
default, often write-all), or declares `write-all`. Least privilege is cheap here.
Measured count: 28.

## Q4 self-push-without-skip-ci (P2, advisory)
A commit/push step whose content has no `[skip ci]`. If the workflow also triggers on push, it
can loop. Advisory because the trigger may not be push. Measured count: 4.

## Q5 duplicate-producer (P0, blocking)
Two or more workflows write the same artifact path. This is the class of bug that let `/audit`
lag `/audit3`: two producers, one file, last writer wins. Measured count: 21 paths, including
`data/freshpicks_gate_state.json` (six producers) and `trading_results.json` (four).

## Q6 orphan-artifact (P2, advisory)
A JSON/markdown artifact written by some workflow that no workflow reads. Either dead output or a
renamed consumer. Advisory because a human may still consume it. Measured count: 166.

## Q7 silent-failure (P0, blocking)
A gate-shaped step (its label names a gate/check/test/verify and it is not a deploy/commit step)
that has `continue-on-error: true` or `|| true`. A gate that cannot fail is not a gate. Steps that
declare themselves optional / non-fatal / advisory / preview are excluded: they are honest, not
silent. Measured count: 40.

## Q8 missing-timeout (P1, blocking)
A job with no `timeout-minutes`. Hung jobs are what fill the queue with phantom runs.
Measured count: 4.

## Q9 secret-sprawl (P2, advisory)
One secret referenced by more than the fan-in bound (8) workflows. Widens blast radius. Advisory
because consolidation is an ownership decision. Measured count: 15.

## Q10 dead-schedule (P2, advisory)
From the trigger side: a malformed cron, an unusual minute, or (when the R1-R12 report is present)
a scheduled workflow whose last run is older than twice its interval. Extends R9, which looks at
runs, by starting from the `on: schedule` declaration. Measured count: 28.

## What the rules do not catch (red-team notes)

Recorded honestly, since the catalog is the claim:

- **A correct-looking YAML with a wrong path inside a script.** Q5/Q6 match artifact names, not
  shell resolution; `cd foo && python bar.py` is opaque.
- **A gate that is not named like a gate.** Q7 keys on the label; a step called "Do the thing"
  that runs a validator with `|| true` is missed.
- **Reusable workflows (`workflow_call`).** A caller's `uses: ./.github/workflows/x.yml` is
  inventoried as an action but its inputs are not followed into the callee.
- **Secrets passed via `secrets: inherit`.** Q9 sees no `secrets.NAME` reference there.
- **Composite actions** in `.github/actions/*` are not parsed, only referenced.
- **Environment-protection / required-reviewer misconfiguration.** Not visible in the file.
- **A cron that is "alive" but always failing.** That is R1's job; Q10 only sees staleness.

Each of these is a candidate for Q11+ with a fixture, not a claim that the framework is complete.
