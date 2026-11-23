# Verification: reproducing the peer-claim report

How the peer-claim verification report (`updates/2026-11-23-peer-claim-verification.md`)
is produced and re-produced: it checks claims peers, other agents and I made about work
"landing" here, where the recurring failure was a commit that existed only in a local
clone, or on an unmerged branch, being described as landed. Existence checks cannot
catch that, reachability checks can. The deterministic half is now a script,
`tools/verify_peer_claims.py`, driven by `claims/verification_claims.json`; the
judgement half is still human.

## The four-step flow

| step | what it does | who does it |
|------|--------------|-------------|
| R1 | establish refs (`origin/main` sha + UTC time) | AUTOMATED |
| R2 | collect claims into the manifest | MANUAL |
| R3 | verify each claim against refs | AUTOMATED |
| R4 | attribution, write-up, landing decision | MANUAL (author counting is automated) |

### R1 - establish refs (AUTOMATED)

- Consumes: the `origin` remote.
- Does: `git fetch origin --prune`, then records the `origin/main` sha and the UTC
  time. The hand report recorded `origin/main = 2af4cf54953...` at
  `2026-11-23T03:52` UTC (`updates/2026-11-23-peer-claim-verification.md:8-10`).
- Produces: the reference point every later check runs against.
- Who: the weekly workflow's checkout step, and any human running the engine after a fetch.

### R2 - collect claims (MANUAL)

- Consumes: COMS notes, PRs, branch tips, documents - whatever peers said.
- Does: reduces each statement to `(id, group, claimant, summary, checks[])` and
  decides which claims exist at all.
- Produces: entries in `claims/verification_claims.json`.
- Who: a human or agent. The COMS bus is LAN-only (see "The weekly workflow"), and
  deciding which claims are worth recording is a judgement, not a mechanical step.

### R3 - verify each claim against refs (AUTOMATED)

- Consumes: the manifest plus a git clone with the relevant refs.
- Does: `git cat-file`, `git merge-base --is-ancestor`, `git ls-tree <ref> -- <path>`,
  `git branch -r --contains` (via `for-each-ref`), `gh pr view --json state`, and
  `git log --format=%ae`. The check kinds are listed at
  `tools/verify_peer_claims.py:44-59`.
- Produces: `updates/peer-claim-verification-latest.md`, plus the `--json-out` JSON.
- Who: `tools/verify_peer_claims.py`.

### R4 - attribution, write-up, landing decision (MANUAL, narrowly automated)

- Consumes: R3's output.
- Does: attributes commits to authors, judges ownership (the facts can hold while the
  branch is still "NOT MINE"), resolves PARTIALLY-vs-NOT-LANDED boundary calls, and
  decides whether to merge.
- Who: a human. The author-set count is automated (the `author_set` check); the
  ownership and boundary judgements are not.

## Running the engine locally

From a clone that has the refs you care about:

```sh
git fetch origin --prune
python3 tools/verify_peer_claims.py --strict
```

When claims point at a second repository (the review repo
`eltonaguiar/antigravity_review_Nov192026`), map it in so `review/main` resolves:

```sh
git clone https://github.com/eltonaguiar/antigravity_review_Nov192026 /tmp/review_probe
python3 tools/verify_peer_claims.py --strict \
  --remote-map '{"review": "/tmp/review_probe"}'
```

The mapped path may be a normal (non-bare) checkout: the engine runs
`git -C <path> merge-base --is-ancestor ...` / `git -C <path> ls-tree ...` inside it,
so an ordinary clone directory is all `review/main` needs. Without the mapping,
every check on `review/main` SKIPs and those claims read UNVERIFIABLE (never FAIL).
The weekly workflow gets the same effect from a second checkout into `.review`
(see "The weekly workflow" below).

### Flags

Every flag below was checked against `python3 tools/verify_peer_claims.py --help`.

| flag | default | what it does |
|------|---------|--------------|
| `--claims` | `claims/verification_claims.json` | manifest to read; relative paths resolve against the repo root |
| `--ref` | `origin/main` | the git ref every check runs against unless the check sets its own |
| `--out` | `updates/peer-claim-verification-latest.md` | markdown report path; the help says it must NOT live under `docs/` |
| `--repo` | origin remote's slug | `owner/name` for `gh pr view` lookups |
| `--json` | off | also emit machine-readable results to `--json-out` (passing `--json` without `--json-out` is an error) |
| `--json-out` | none | path for the JSON results; written whenever it is given |
| `--remote-map` | none | JSON object `{remote name: local git path}` so a check's `ref` can be e.g. `review/main`; env fallback `VERIFY_EXTRA_REMOTES` |
| `--strict` | off | exit non-zero on a non-manual verdict disagreement or an unexpected check FAIL |
| `--allow-dirty-ref` | off | silence the warning about uncommitted changes in the working tree |
| `--allow-shallow` | off | run in a shallow clone anyway. By default a shallow clone is a FATAL error (exit 2); this flag downgrades it to a warning and appends `[SHALLOW CLONE - results unreliable]` to every check and verdict that depends on the object graph |

### Exit codes

| code | meaning |
|------|---------|
| 0 | ran to completion. Disagreements are still reported, but they only fail the run under `--strict` |
| 1 | `--strict` was given and there were violations |
| 2 | usage or environment error: bad `--remote-map`, not a git repository, **a shallow clone without `--allow-shallow`**, unresolvable `--ref`, missing or invalid claims file, invalid manifest, or an unwritable report path |

### Shallow clones invert verdicts

A depth-1 clone (`actions/checkout` with `fetch-depth: 1`) contains one commit and
no other branch refs. `git cat-file -e <sha>^{commit}` then fails for every sha that
is not HEAD, `git branch -r --contains` finds nothing, and
`git merge-base --is-ancestor` cannot work - so **landed commits are reported as NOT
LANDED**. The engine therefore checks `git rev-parse --is-shallow-repository` at
startup and refuses to run in a shallow clone unless `--allow-shallow` is passed
(`tools/verify_peer_claims.py:66-76`). If the probe itself fails (very old git), it
warns and proceeds instead of crashing.

### Report header provenance

The markdown header records, so the artefact is auditable on its own:

- `checked-out HEAD at report time: <sha>` - captured immediately before the report
  is written, because a rebase or a concurrent push can move `origin/main` after
  checkout, so the sha seen at run start may describe a tree the report is not
  sitting on. It is the checked-out HEAD, not the merge commit the report will
  eventually land as - that cannot be known at write time.
- `ref used for checks: <ref> (<sha>)` - the ref and its resolved tip that every
  check read.
- `shallow: true|false` - the clone state the run saw; `true` also adds a warning
  line naming the unreliable-result marker.

## Interpreting the output

### Verdict vocabulary and derivation rule

The vocabulary is fixed: VERIFIED / NOT LANDED / PARTIALLY / UNVERIFIABLE
(`tools/verify_peer_claims.py:31`). Each check has a polarity
(`tools/verify_peer_claims.py:17`; definition in `claims/verification_claims.json:5`):

- `supports`: PASS is evidence FOR the claim, FAIL is evidence AGAINST it (default).
- `refutes`: PASS is evidence AGAINST the claim, FAIL is evidence FOR it.

After dropping SKIPped checks and folding each outcome through its polarity:

| supporting | refuting | verdict |
|------------|----------|---------|
| none executable | - | UNVERIFIABLE |
| >= 1 | 0 | VERIFIED |
| 0 | >= 1 | NOT LANDED |
| >= 1 | >= 1 | PARTIALLY |

A SKIP never decides on its own: an unresolvable ref makes a check SKIP, never FAIL
(`tools/verify_peer_claims.py:64`). A `manual` claim's verdict is reported with a
" (manual judgement required)" suffix but never blocks `--strict`
(`tools/verify_peer_claims.py:41-42`).

A claim that bundles two propositions - here a landing fact and a citation-integrity
fact - must be split into one claim per proposition rather than averaged into a
single PARTIALLY, as B7 (split into `B7` and `B7-context`) and B5 (split into `B5`
and `B5-typo`) both demonstrate.

### The absent-evidence trap

An "absent" observation must count as REFUTING evidence, not supporting. The original
derivation counted every PASS as support, so "these files landed" plus an absence
check that PASSed because the files were missing scored PARTIALLY - even though every
piece of evidence said NOT LANDED.

B3 is the worked example: `c0d48e28968` supposedly added five named paths, yet
`git merge-base --is-ancestor c0d48e28968 origin/main` -> rc=1, the commit sits on no
`refs/remotes/origin/*` ref, and all five paths are ABSENT from `origin/main`. That is
supporting=0, refuting=7 -> NOT LANDED, the hand report's verdict
(`updates/2026-11-23-peer-claim-verification.md:51`). Counting the five absence PASSes
as support would have given PARTIALLY. The report names this defect class itself: a
local `git cat-file` success is not evidence of landing
(`updates/2026-11-23-peer-claim-verification.md:67`).

## The weekly workflow

`.github/workflows/peer-claim-verification.yml` runs Mondays at 06:31 UTC
(`'31 6 * * 1'`) and on `workflow_dispatch`. It checks out `main` with
`fetch-depth: 0` - full history is REQUIRED, because ancestry, branch-containment
and object-existence checks all need objects and refs outside HEAD, and a depth-1
clone silently inverts VERIFIED claims into NOT LANDED. `filter: blob:none` and a
sparse checkout (`tools`, `claims`, `updates`, `reports`) keep it inside the job's
10-minute timeout: the commit graph is what the checks need, not every blob.

A second `actions/checkout@v4` step checks out the review repo
(`eltonaguiar/antigravity_review_Nov192026`, public) into `.review` with
`fetch-depth: 0` - a plain full checkout, since it is a small docs repo - and the
verification step is passed
`--remote-map '{"review": "${{ github.workspace }}/.review"}'`. That is what makes
B1/B2/B5/B10 resolvable in CI; without it their `review/main` checks SKIP and the
claims read UNVERIFIABLE. It runs `tools/verify_peer_claims.py` without `--strict`,
prints a summary (raising `::warning::` annotations for violations instead of
failing), and commits the two generated files back to `main` with a `[skip ci]`
message.

What it does NOT do:

- No COMS sweep. The broker is `192.168.2.52:1883`, a LAN address, anonymous and
  without TLS (`INVESTIGATION_2026-11-18_job_board_coms_assetclasses_pm.md:99`); a
  GitHub-hosted runner cannot reach it, so a claim only ever broadcast on COMS is
  neither confirmed nor refuted. `pr_state` checks likewise SKIP when `gh` is missing.
- No re-derivation of edge research: no backtests, PnL, win rates or pick quality.
- No landing or merge decision, and no change to any `expected_verdict`.

A workflow PASS therefore means only one thing: the cited objects are still reachable
from the named ref. It does not mean the work is correct, complete or profitable.

## Adding a claim

Append an entry to `claims` in `claims/verification_claims.json`:

```json
{
  "id": "B13", "group": "B", "claimant": "peer / other agent",
  "summary": "one sentence of what was claimed",
  "checks": [
    {"kind": "commit_ancestor_of_main", "sha": "<sha>", "polarity": "supports"},
    {"kind": "path_absent_from_main", "path": "<path>", "polarity": "refutes"}
  ],
  "manual": false, "expected_verdict": "VERIFIED"
}
```

Rules:

- Polarity: `supports` for evidence that the thing exists where claimed; `refutes`
  for absence checks (`path_absent_from_main`, `commit_absent`,
  `commit_not_reachable`). A PASS on an absence check is evidence AGAINST a landed claim.
- Prefer `commit_not_reachable` over `commit_absent` for "exists but not landed":
  `commit_absent` is clone-local and a shallow clone can make it PASS spuriously
  (`tools/verify_peer_claims.py:48-52`).
- Set `manual: true` with a `manual_reason` when the decision is ownership, a
  PARTIALLY boundary call, or no executable check exists.
- Do NOT edit `expected_verdict` to make a run go green. That is exactly how the
  original errors happened: a verdict was adjusted to match the happy story instead
  of the evidence. Record the disagreement instead.

## The tally constraint

`tests/test_edge_research_tally_consistency.py` discovers every markdown file under
`docs/` that states an edge-research tally and requires the settled triple, except on
lines marked historical (`tests/test_edge_research_tally_consistency.py:134-149`,
`:170`). This document keeps that tally consistent and quotes it exactly once:

TALLY: 0 INVESTABLE / 11 NOT_INVESTABLE / 3 UNKNOWN (14 rows)

That is the settled tally for the 14-row programme. Re-verifying *landing* says nothing
about *edge*, so it cannot change these verdicts; the programme index says not to
re-derive them because they are settled (`docs/edge_research/28_PROGRAMME_STATUS_INDEX_2026-11-23.md:163`).

## Provenance

| statement | source |
|-----------|--------|
| reachability, not existence, is the point; verdict vocabulary and derivation rule | `[SRC: tools/verify_peer_claims.py:1-42]` |
| polarity definition | `[SRC: claims/verification_claims.json:5]` |
| check kinds | `[SRC: tools/verify_peer_claims.py:44-59]` |
| SKIP on unresolvable ref | `[SRC: tools/verify_peer_claims.py:64]` |
| `--strict` semantics | `[SRC: tools/verify_peer_claims.py:78-83]` |
| exit 1 only under `--strict` with violations | `[SRC: tools/verify_peer_claims.py:891-892]` |
| `--out` must not live under `docs/` | `[SRC: tools/verify_peer_claims.py:740]` |
| shallow-clone guard (fatal by default, `--allow-shallow` opt-out) | `[SRC: tools/verify_peer_claims.py:66-76]` |
| shallow detection helper | `[SRC: tools/verify_peer_claims.py:119-140]` |
| shallow-sensitive check kinds | `[SRC: tools/verify_peer_claims.py:492-497]` |
| HEAD-at-report-time + `shallow:` header fields | `[SRC: tools/verify_peer_claims.py:628-633]` |
| B3 verdict and evidence | `[SRC: updates/2026-11-23-peer-claim-verification.md:51]` |
| local-only commits were described as landed | `[SRC: updates/2026-11-23-peer-claim-verification.md:67]` |
| COMS broker is a LAN address, anonymous, no TLS | `[SRC: INVESTIGATION_2026-11-18_job_board_coms_assetclasses_pm.md:99]` |
| settled tally | `[SRC: docs/edge_research/28_PROGRAMME_STATUS_INDEX_2026-11-23.md:7]` |
| do not re-derive the verdicts | `[SRC: docs/edge_research/28_PROGRAMME_STATUS_INDEX_2026-11-23.md:163]` |
| settled triple and discovery in the tally test | `[SRC: tests/test_edge_research_tally_consistency.py:134-149]` |
| workflow idioms (cron, concurrency, commit guard, retry loop) | `[SRC: .github/workflows/crypto-intraday-sim.yml:17-91]` |
| review-repo checkout into `.review` and the `--remote-map` it feeds | `[SRC: .github/workflows/peer-claim-verification.yml:69-78]` |
| mapped remote resolved with `git -C <path>` | `[SRC: tools/verify_peer_claims.py:139-150]` |

For the workflow's cron, concurrency group and steps, `.github/workflows/peer-claim-verification.yml` is the source of truth.
