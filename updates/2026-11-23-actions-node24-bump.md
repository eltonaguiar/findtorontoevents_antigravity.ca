# 2026-11-23 — Bump checkout / setup-python off the deprecated Node 20 runtime

## What was wrong

`peer-claim-verification.yml` ran green, but every run carried this annotation:

> Node.js 20 is deprecated. The following actions target Node.js 20 but are being
> forced to run on Node.js 24: actions/checkout@v4, actions/setup-python@v5.

GitHub currently forces those actions onto Node 24, so it is only a warning today.
Once the pinned majors stop working, the workflow breaks. Baseline (run
`45122121748`, on `60ff4b650`): 1 annotation, claims line
`16 claims: 15 agree, 1 disagree (0 non-manual), 7 manual; strict violations: 0`.

## Tag → runtime evidence (GitHub API, not guessed)

`gh api repos/<repo>/contents/action.yml?ref=<tag>`, field `runs.using`:

| Action | Tag | `runs.using` |
|---|---|---|
| actions/checkout | v4 | `node20` |
| actions/checkout | v5 | `node24` |
| actions/checkout | v6 | `node24` |
| actions/checkout | v7 (latest, v7.0.1) | `node24` |
| actions/setup-python | v4 | `node16` |
| actions/setup-python | v5 | `node20` |
| actions/setup-python | v6 | `node24` |
| actions/setup-python | v7 (latest, v7.1.0) | `node24` |

Both latest majors already use `node24`, so no residual warning is accepted.
Every input this workflow uses (`ref`, `fetch-depth`, `filter`, `sparse-checkout`,
`sparse-checkout-cone-mode`, `repository`, `path`, `token`, `python-version`)
still exists in the target majors. Release notes show no relevant breaking change:
checkout v5 is the node24 bump, v6 changed credential persistence, v7 blocks fork-PR
checkout (not used here); setup-python v6 is the node24 bump, v7 removed the
`pip-install` input (not used here).

## What was changed

Only `.github/workflows/peer-claim-verification.yml`:

- `actions/checkout@v4` → `@v5` (both occurrences: main repo + review repo)
- `actions/setup-python@v5` → `@v6`

Pinned to the lowest major that is on `node24`, not to latest: the workflow only
needs the node24 runtime, and the smallest jump has the smallest behaviour delta.

## What was deliberately left alone

Repo-wide inventory of occurrences: checkout@v6 241, setup-python@v6 249,
cache@v5 11, checkout@v4 14 (12 after this change), setup-python@v5 14 (13 after),
setup-node@v5 4, setup-node@v4 2.

The other 11 workflows still on checkout@v4 (and 12 on setup-python@v5) were NOT
mass-updated. Each bump is a behaviour change, and several of those workflows commit
to main on a schedule; changing them without dispatching each one is how a working
pipeline is broken silently. They should be bumped one PR at a time, each with its
own dispatch proof. No other workflow was trivially verifiable in this block, so
none was touched.

## Verification

- `yaml.safe_load(...)` → `yaml ok`
- `grep -n 'uses:'` → `checkout@v5` (42, 74), `setup-python@v6` (82)
- `pytest tests/test_verify_peer_claims.py -q` → 33 passed
- `pytest tests/test_edge_research_tally_consistency.py -q` → 25 passed

## Post-merge dispatch result

Filled in after merge: run id, per-step conclusions, `Node.js 20 is deprecated`
grep count (expected 0), and the claims line (expected unchanged).
