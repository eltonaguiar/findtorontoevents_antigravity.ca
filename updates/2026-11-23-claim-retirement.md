# Claim retirement: a resolved claim is not a still-true claim

## The problem

Claim B11 recorded a real provenance gap: `tools/capacity_model.py:49` cites
`HURDLE_TBILL_APR = 0.0432`, but the file was absent from `origin/main`, so the line could not be
checked there. The manifest expressed that as two `path_absent_from_main` checks with `refutes`
polarity, and the engine reported B11 as `NOT LANDED`.

PR #1095 (merge `8e3cefd5ca0cf3efc94563e4e115f83543ebdfed`) added `tools/capacity_model.py` and
`tests/test_capacity_model.py` to main. The absence checks now FAIL, which under `refutes` polarity
is *supporting* evidence - so the engine flipped B11 to `VERIFIED (manual judgement required)` and
reported `16 agree, 1 disagree`. B11 was now asserting an ongoing defect that no longer existed.

## Why retirement, not deletion or rewriting

- **Deleting B11** would erase the record that the gap ever existed. The next reader could not tell
  whether the claim was resolved or simply never made.
- **Rewriting B11** to assert the opposite would silently change an evidentiary claim after the
  fact. That is precisely the failure mode this verification system exists to prevent.
- **Retirement** keeps the claim, keeps its original checks as the historical record, and stops it
  counting as evidence in either direction.

## What changed

Engine, [`tools/verify_peer_claims.py`](../tools/verify_peer_claims.py):

- A claim may declare `retired: true`, plus optional `retired_reason`, `superseded_by` and
  `retired_at`.
- `RETIRED` is part of the verdict vocabulary (`VERDICT_VOCAB`, `normalize_verdict`, report text,
  JSON).
- A retired claim's checks still run and their raw output is still printed. Its verdict is forced
  to `RETIRED` in [`run_claim()`](../tools/verify_peer_claims.py), it agrees with nothing, it is
  skipped by [`strict_violations()`](../tools/verify_peer_claims.py), and it is excluded from the
  agree/disagree counts in [`main()`](../tools/verify_peer_claims.py).
- The report keeps retired claims out of the main table and re-renders them in a trailing
  `## Retired claims` section with their reason, supersession and full check output.
- `retired: true` without a non-empty `retired_reason` is a manifest error: exit 2.
- The summary line now leads with `N active (...) , M retired (ids)`.

Manifest, [`claims/verification_claims.json`](../claims/verification_claims.json):

- B11 is retired, `superseded_by: B11-resolved`, `retired_at: 2026-11-23`, with its `checks`
  untouched.
- New active claim `B11-resolved` asserts the positive now-true proposition: both paths are on
  main and `8e3cefd5ca0c` is an ancestor of main, expected `VERIFIED`.

Tests, [`tests/test_verify_peer_claims.py`](../tests/test_verify_peer_claims.py): five new tests
(retired listed but excluded from tallies, retired never a strict violation, retirement requires a
reason, retired verdict is never a live verdict, `--help` exits 0), and the manifest-shape test now
exempts retired claims from the absence-polarity rule while keeping it for every active claim.

Docs, [`docs/VERIFICATION.md`](../docs/VERIFICATION.md): a `## Retiring a claim` section.

## How it was verified

In a fresh non-shallow clone of `origin/main` (`git rev-parse --is-shallow-repository` -> `false`),
with the review repo cloned alongside:

```
python3 tools/verify_peer_claims.py --remote-map '{"review": "/tmp/block42/review"}' --strict
```

Before:

```
[verify_peer_claims] 17 claims: 16 agree, 1 disagree (0 non-manual), 6 manual; strict violations: 0
```

After:

```
[verify_peer_claims] 18 claims: 17 active (17 agree, 0 disagree (0 non-manual), 5 manual), 1 retired (B11); strict violations: 0
```

Exit 0 in both cases. `B11` prints `RETIRED` with both of its checks still shown, and
`B11-resolved` prints `VERIFIED [supporting=3 refuting=0]`.

`python3 -m pytest tests/test_verify_peer_claims.py -q` -> `39 passed` (34 before, +5).
