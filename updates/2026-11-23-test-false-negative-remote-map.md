# test_remote_map_env_var failed for environmental reasons, not because the code was wrong

## The defect

`tests/test_verify_peer_claims.py::test_remote_map_env_var` failed with `assert 2 == 0` at
[`tests/test_verify_peer_claims.py:188`](../tests/test_verify_peer_claims.py) in **run 45128193990**
(`CI Tests`, PR #1097, branch `verify/claim-retirement`), in both the 3.11 and 3.12 jobs. The captured
stderr in that run was:

```
[verify_peer_claims] ERROR: cannot resolve origin/main in /home/runner/work/findtorontoevents_antigravity.ca/findtorontoevents_antigravity.ca (fetch it first: git fetch origin --prune)
```

The PR merged anyway (merge commit `a70bf659fd247e02abe48d344aaba7317561e5c8`).

## Diagnosis: the exact exit-2 condition

`vpc.main()` defaults `--ref` to `origin/main` (SRC: `tools/verify_peer_claims.py:824`) and
resolves that ref **against the host checkout** before doing anything else
(SRC: `tools/verify_peer_claims.py:880`). When the ref does not resolve it prints the ERROR above
and returns `2` (SRC: `tools/verify_peer_claims.py:884`) - deliberately, because an unresolvable
top-level ref makes every downstream check meaningless.

The test never passed `--ref`, so it inherited that default. In a PR checkout `origin/main` is not
resolvable: the `CI Tests` workflow checks out depth-1 without fetching `origin/main` (only the
separate `verification-tests.yml` gate does that fetch). The condition is therefore exactly: **the
host checkout has no `refs/remotes/origin/main`, and the test calls `main()` without `--ref`.**
Nothing about `--remote-map` was wrong - the test died before the map was ever consulted.

Reproduced locally in a clone with `origin/main` deleted:

```
$ git update-ref -d refs/remotes/origin/main
$ python3 -m pytest tests/test_verify_peer_claims.py::test_remote_map_env_var -q
E       assert 2 == 0
[verify_peer_claims] ERROR: cannot resolve origin/main in /tmp/b44_hostile (fetch it first: git fetch origin --prune)
1 failed in 0.19s
```

The same test passes in a clone where `origin/main` exists (39 passed).

## Ref-dependent tests swept

- `tests/test_verify_peer_claims.py`: only **two** tests ever call `main()`. `test_remote_map_env_var`
  (fragile, fixed here) and the `_run_main` helper (already hermetic - it pins `--ref HEAD`,
  SRC: `tests/test_verify_peer_claims.py:556-559`). Every other test calls `run_claim()` directly
  against fixture repos that assign their own `origin/*` refs via `git update-ref`
  (SRC: `tests/test_verify_peer_claims.py:40,69,124,314,417`) - self-owned, not host-dependent.
- `tests/test_capacity_model.py`, `tests/test_edge_research_tally_consistency.py`: no reference to
  `origin`, any remote ref, or `vpc.main`. Hermetic.

## The fix and why self-owned beats a skip

The test's subject is the **per-check** remote-map wiring: a check whose `ref` is `review/main` must
resolve through the map to the review repo. The top-level `--ref` is incidental to that. So the test
now pins `--ref HEAD` (always resolvable), and instead of the old shallow assertions it reads the
`--json` payload and asserts:

- the check's `status` is `PASS` (with its detail on failure),
- the check's resolved `ref` is `review/main` (i.e. it went through the map, not a fallback),
- the claim's normalized `computed_verdict` is `VERIFIED`.

The verdict is compared with `vpc.normalize_verdict`, not by exact string: the gate's checkout is
depth-1 by design, `--allow-shallow` is passed, and the engine then appends
`[SHALLOW CLONE - results unreliable]` to every affected verdict
(SRC: `tools/verify_peer_claims.py:125`). That suffix is an environment fact, not this test's
subject; normalizing still separates `VERIFIED` from `UNVERIFIABLE`, which is what a broken remote
map produces.

This is the preferred shape from the brief's option (a): the test's preconditions are owned by the
test, so it cannot be perturbed by the checkout it runs in. A `skipif` was rejected because it would
silently lose coverage in exactly the environment (PR checkouts) where the gate runs.

It also turned out the **old assertions were hollow**: with the remote map deliberately discarded,
the old test still passed in a healthy checkout (an unresolvable per-check ref yields `SKIP`, and
`strict_violations` exempts `SKIP`, so `rc == 0` and the claim id still appears in the report). The
new assertions are what make the RED proof actually red.

The engine was **not** changed: exit 2 on an unresolvable top-level ref is correct behaviour.

## Proofs

1. **GREEN in a hostile environment** - clone with `origin/main` deleted:
   `39 passed in 1.11s` (whole file, including the fixed test).
2. **RED for the right reason** - sabotaged `main()` to parse the remote map then discard it
   (`extras = {}`):
   ```
   >       assert check["status"] == vpc.STATUS_PASS, check["detail"]
   E       AssertionError: cannot resolve review/main in this clone
   E       assert 'SKIP' == 'PASS'
   1 failed in 0.15s
   ```
   Under the same sabotage the old assertions passed (39 passed) - proof they were hollow.
   The engine was reverted afterwards (`git diff --stat tools/verify_peer_claims.py` empty).
3. **Full suite** - `python3 -m pytest tests/test_verify_peer_claims.py tests/test_capacity_model.py tests/test_edge_research_tally_consistency.py -q`
   -> `80 passed in 1.33s`.
4. **CI** - the `Verification Tests` gate on PR #1099 (a real PR checkout - the environment that
   exposed the original bug). The first attempt on the PR was red for a *different* environmental
   reason: the exact-string verdict assertion did not allow for the shallow marker (see above); it
   was corrected and the gate re-run. Final run id and conclusion are recorded in the PR.

Also verified in a **shallow** hostile checkout (depth-1 clone, `origin/main` absent - the gate's
environment shape): 39 passed; and with the remote map sabotaged the test fails with
`assert 'SKIP' == 'PASS'`.

## Scope

Only `tests/test_verify_peer_claims.py` and this note (plus the session-lessons entry). No workflow
change, no engine change, no other tests.
