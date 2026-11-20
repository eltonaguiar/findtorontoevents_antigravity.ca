# The anti-overfit DSR gate has never passed since it was added

## What happened

Two consecutive audit-dashboard runs failed after deploying, at the same step:

```
44791570972  18:18Z  Anti-overfit GATE (blocking -- DSR must clear 0.95)  exit 2
44818503516  21:14Z  Anti-overfit GATE (blocking -- DSR must clear 0.95)  exit 2
ANTI-OVERFIT GATE: FAIL -- 74/80 strategies below DSR 0.95 (6/80 scored, 7.5%)
```

## It is not a data problem

* The payload is the healthy one: 80 rows, 6 PUBLISHABLE / 74 PROBATION.
* The step was introduced by **#1017** ("Make the anti-overfit audit able to fail").
* The last green run (15:16Z) does not contain the step at all -- its steps go
  straight from `Deploy to all 3 FTP sites` to `Verify URLs`. Nothing started
  failing; a new blocking gate arrived.
* Reproduced locally on a clean `origin/main` checkout: exit 2, identical message.

## Why it fails every single run

`gate_failures()` returns every strategy whose DSR falls below the floor, and with
`--gate` any non-empty result returns 2. The floor is 0.95 and the population's
steady state is 6 of 80 above it, so the gate reports "74 of 80 unproven" -- which is
the system's actual, long-standing state -- and exits non-zero. The step can only
pass if essentially every strategy clears 0.95, which this repo is nowhere near.

## Why that is worth fixing anyway

* The hourly job can never be green, so a genuine infrastructure failure looks
  exactly like the expected verdict. There is no signal left in the colour.
* It masks the two blocking hybrid gates added in #1031: they run earlier in the
  same job, and their pass is invisible in the run's overall status.
* Someone will eventually "fix" the red by deleting the gate, losing the finding.

## What I did not change

Not the floor, not the blocking behaviour. 6/80 clearing 0.95 is a real statement
about strategy quality; quietly turning the job green would hide it. This is a
policy call, recorded here with the evidence.

## Options

| option | behaviour | cost |
|---|---|---|
| (a) leave red | standing "not money-ready" alarm | no green runs, ever |
| (b) block on regression | fail only when the publishable count drops vs the previous audit; keep printing the absolute number | needs a small baseline read |
| (c) block on the rate | fail when the pass rate falls, or when it is below a low floor it used to clear | needs the same baseline |

Recommendation: **(b)**. The artifact already carries the absolute number
(`dsr_pass_rate`), so the log loses nothing, and the job's colour regains meaning:
red would then mean *something got worse*.

## How verified

* Run step lists: 15:16Z has no DSR step; 18:18Z and 21:14Z fail on it.
* Local reproduction on clean `origin/main`: `python3
  tools/anti_overfit_audit_sidecar.py --check-only --gate --dsr-threshold 0.95`
  exits 2 with the same 74/80 line.
* Payload census: 80 rows, 6 PUBLISHABLE / 74 PROBATION, labels consistent.
* The hybrid gates upstream were re-run against the 21:14Z job's own refresh commit
  (`8d8ffa8f`, 42 artifacts): 0 hybridised -- so they are not implicated.
