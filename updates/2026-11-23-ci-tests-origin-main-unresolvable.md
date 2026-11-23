# CI failed on every PR because `origin/main` was unresolvable, not because of a defect

**Date:** 2026-11-23
**Branch:** `copilot/hub-audit-2026-11-23`
**PR:** #1096

## What was broken

`ci-tests.yml` reported:

```
tests/test_verify_peer_claims.py::test_remote_map_env_var FAILED
  assert rc == 0
  E  assert 2 == 0
[verify_peer_claims] ERROR: cannot resolve origin/main in <checkout>
        (fetch it first: git fetch origin --prune)
```

`tools/verify_peer_claims.py` resolves refs with
`git rev-parse --verify --quiet '<ref>^{commit}'`, defaulting to `origin/main`.
`actions/checkout` uses the default `fetch-depth: 1`, which fetches **only the PR
merge ref**. There is therefore no local `origin/main`, the tool exits `2`, and the
test that asserts `rc == 0` fails.

## Why it is not this PR's fault

- The test and the tool **do not exist on this branch** — they live only on `main`
  and arrive through the PR merge checkout:
  `git cat-file -e HEAD:tests/test_verify_peer_claims.py` → absent;
  `git cat-file -e origin/main:tests/test_verify_peer_claims.py` → present.
- This branch never modified either file.
- `.github/workflows/ci-tests.yml` was **identical to `origin/main`** before this
  change (`git diff origin/main -- .../ci-tests.yml` was empty), and `main`'s
  version has no fetch step either.
- Measured across other branches — **5 of the last 8** `ci-tests.yml`
  pull-request runs failed, on entirely unrelated branches:
  `verify/claim-retirement`, `fix/peer-claim-b5-split-2026-11-23`,
  `fix/peer-claim-verification-shallow-clone-2026-11-23`,
  `pr/h201-pit-universe-2026-11-23`.
- On `main` itself the same workflow **succeeds** (last five push runs:
  success ×5), because there `origin/main` exists.

So it is a PR-only latent bug that fails every pull request.

## What changed

One step added after `Checkout` in `.github/workflows/ci-tests.yml`:

```yaml
      - name: Make origin/main resolvable for ref-based checks
        run: |
          set -euo pipefail
          git fetch --no-tags --depth=1 origin +refs/heads/main:refs/remotes/origin/main
          git rev-parse --verify --quiet 'origin/main^{commit}' >/dev/null
          echo "origin/main resolves at $(git rev-parse --short 'origin/main^{commit}')"
```

`depth=1` is deliberate: the tool only needs the ref to *resolve*. Its own
docstring states that a `fetch-depth: 1` clone can make object-graph checks pass,
and it already downgrades those to warnings under `--allow-shallow`. Fetching full
history for a 47k-file repo on every PR would be wasteful for no extra signal.

The step also asserts the ref resolves after fetching, so a future change to
`actions/checkout` behaviour fails loudly at the fetch step instead of surfacing as
a confusing test failure.

## How it was verified

Diagnosis is from the failing run's own log
(`gh run view 45130227084 --log-failed`), not inference. The fix is verified by
the PR run going green — see the run linked on PR #1096.

## Note

This is the second workflow defect found in this PR that was masked as a code
failure; the first was the `php52` gate calling `python3 -m pytest` without ever
installing pytest (`updates/2026-11-23-php52-gate-missing-pytest.md`). Both had the
same shape: a required check that was red for a dependency/setup reason, which
reads like a regression in whatever the check is named after.
