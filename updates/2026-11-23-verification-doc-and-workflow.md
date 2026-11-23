# Verification doc + weekly regeneration workflow (2026-11-23)

## What was missing

The peer-claim verification report (`updates/2026-11-23-peer-claim-verification.md`) was
produced by hand: a human fetched refs, ran a dozen git/gh commands per claim, folded the
results into VERIFIED / NOT LANDED / PARTIALLY / UNVERIFIABLE, and wrote the table. Nothing
recorded which part of that was mechanical, nothing could re-run it, and the report's own
summary names the recurring defect: commits that existed only in a local clone were
described as landed. There was also no document saying how to reproduce the report, and no
scheduled refresh.

## What was added

- `docs/VERIFICATION.md` - the reproduction guide: the R1-R4 flow (R1 refs and R3 checks
  automated, R2 claim collection manual, R4 write-up and landing decision manual), local
  commands and every CLI flag (each checked against `--help`), exit codes, the verdict
  derivation rule, the absent-evidence trap, what the weekly workflow does and does not do,
  how to add a claim, and a provenance table.
- `.github/workflows/peer-claim-verification.yml` - Mondays 06:23 UTC plus
  `workflow_dispatch`. It runs `tools/verify_peer_claims.py` (no `--strict`), prints a
  summary with `::warning::` annotations for violations, and commits the regenerated
  report and JSON to `main` with `[skip ci]`, using the same guarded commit + 3-attempt
  rebase/push loop as `crypto-intraday-sim.yml`. No `push:` trigger.

## The defect this documents

My first derivation rule counted every check PASS as supporting evidence. For
B3/B4/B6/B7 the decisive checks were absence checks (`path_absent_from_main`), which PASS
precisely when the claimed path is MISSING from `origin/main` - so five absence PASSes were
scored as support and B3 came out PARTIALLY where the evidence said NOT LANDED.

Fix (commit `bcefb7dd5da`): every check in `claims/verification_claims.json` carries an
explicit polarity. `supports` means PASS is evidence FOR the claim; `refutes` means PASS is
evidence AGAINST it (absence checks are `refutes`). The engine folds each outcome through
its polarity into supporting/refuting counts, and the verdict follows from those counts
(0 refute + >=1 support = VERIFIED; >=1 refute + 0 support = NOT LANDED; both = PARTIALLY;
nothing executable = UNVERIFIABLE).

B7 was the last one to resolve: one claim mixed "the sha exists on a branch" with "the file
was restored to main", which is true-for-the-first and false-for-the-second. Commit
`a63729dac5a` split it into B7 (landing claim, NOT LANDED) and B7-context (existence, VERIFIED)
so the verdict stops conflating them.

## What the workflow can and cannot do

Can: re-check every claim whose evidence is a git object in this repository (ancestry,
origin-ref reachability, path presence/absence, author sets) and PR state when `gh` is
authorised, then publish the refreshed report.

Cannot: sweep the COMS bus. The broker is the LAN address `192.168.2.52:1883`, anonymous,
no TLS, and the job runs on a GitHub-hosted runner which cannot reach it - so collecting
new claims stays manual. It also does not re-derive edge research (no backtests or PnL),
does not decide landing or merging, and never edits `expected_verdict`.

## How it was verified

- `yaml.safe_load` on the new workflow: ok.
- `python3 tools/verify_peer_claims.py --help` - every documented flag exists.
- `pytest tests/test_edge_research_tally_consistency.py -q` - 24 before adding
  `docs/VERIFICATION.md`, 25 after (the new document's single canonical tally line is
  parametrised in), all passing.
- `pytest tests/test_verify_peer_claims.py -q` - 25 passed.
- `python3 tools/verify_peer_claims.py --strict` - exit 0.

## Post-merge run observation (first real dispatch)

The first real dispatch of the workflow (run `45114413921`) went **green** - every step
`success`, conclusion `success` - and committed a regenerated report to `main`. The report
was largely WRONG.

- Local, full clone, same commit range: `16 claims: 12 agree, 4 disagree (1 non-manual); strict violations: 0`.
- CI, same range: `16 claims: 6 agree, 10 disagree (5 non-manual); strict violations: 3`.

B12, B7-context, A1i, A1ii, A2 and B9 were inverted from their true verdicts, e.g.
`[B12] NOT LANDED ... (hand: VERIFIED)` and `[A1i] NOT LANDED ... FAIL supports
commit_on_any_origin_ref: 3a4f199132d does not resolve to a commit`.

Cause: the checkout step used `actions/checkout@v4` with `fetch-depth: 1`. A depth-1 clone
holds one commit and no other branch refs, so `git cat-file -e <sha>^{commit}` fails for
every sha that is not HEAD, `git branch -r --contains` finds nothing and `git merge-base
--is-ancestor` cannot work. The engine faithfully reported NOT LANDED for commits that had
genuinely landed. Because the workflow runs without `--strict`, it still exited 0.

Fix (this change):

1. `fetch-depth: 0` in the workflow - full history is required.
2. The engine now refuses to run in a shallow clone: `git rev-parse --is-shallow-repository`
   -> `true` is a FATAL error (exit 2) unless `--allow-shallow` is passed, and then every
   affected check and verdict is tagged `[SHALLOW CLONE - results unreliable]`.
3. The report header records `checked-out HEAD at report time`, the ref used for checks,
   and `shallow:` - captured just before writing, since a rebase can move the sha after
   checkout.
4. Regression tests build a real `git clone --depth 1` fixture and drive the CLI.

Before/after, same claims: 6 agree / 10 disagree / 5 non-manual / 3 violations (CI, shallow)
-> 12 agree / 4 disagree / 1 non-manual / 0 violations (full clone).

## Post-merge re-dispatch (run 45115464824): fetch-depth 0 alone times out

The first re-dispatch after merging the fix was **cancelled**: the `Checkout` step ran
`git fetch --prune --no-recurse-submodules origin +refs/heads/*:refs/remotes/origin/* +refs/tags/*:refs/tags/*`
for 10 minutes and hit the job's `timeout-minutes: 10`. Full history across every branch
and tag is large, so an unfiltered full checkout is not viable on a hosted runner.

The requirement is the commit graph, not every blob. The workflow now uses
`fetch-depth: 0` (all commits of all refs - a sha may land on a non-main origin ref),
`filter: blob:none` (commit graph and trees only; blobs are fetched on demand for the files
actually read), and a sparse checkout of `tools`, `claims`, `updates`, `reports`. The
commit step uses `git add --sparse` for the two generated files.

Locally this combination costs ~66 MB / ~12 s for the full commit graph of 340k commits,
versus a 25 GB working repository - the timeout was fetching blobs nobody reads.
