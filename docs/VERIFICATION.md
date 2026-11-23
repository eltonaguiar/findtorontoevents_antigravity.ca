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

When claims point at a second repository (the review repo), map it in so `review/main` resolves:

```sh
python3 tools/verify_peer_claims.py --strict \
  --remote-map '{"review": "/path/to/review_clone"}'
```

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

### Exit codes

| code | meaning |
|------|---------|
| 0 | ran to completion. Disagreements are still reported, but they only fail the run under `--strict` |
| 1 | `--strict` was given and there were violations (`tools/verify_peer_claims.py:802-803`) |
| 2 | usage or environment error: bad `--remote-map`, not a git repository, unresolvable `--ref`, missing or invalid claims file, invalid manifest, or an unwritable report path |

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

`.github/workflows/peer-claim-verification.yml` runs Mondays at 06:23 UTC
(`'23 6 * * 1'`) and on `workflow_dispatch`. It checks out `main`, runs
`tools/verify_peer_claims.py` without `--strict`, prints a summary (raising
`::warning::` annotations for violations instead of failing), and commits the two
generated files back to `main` with a `[skip ci]` message.

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
| `--strict` semantics | `[SRC: tools/verify_peer_claims.py:66-71]` |
| exit 1 only under `--strict` with violations | `[SRC: tools/verify_peer_claims.py:802-803]` |
| `--out` must not live under `docs/` | `[SRC: tools/verify_peer_claims.py:683]` |
| B3 verdict and evidence | `[SRC: updates/2026-11-23-peer-claim-verification.md:51]` |
| local-only commits were described as landed | `[SRC: updates/2026-11-23-peer-claim-verification.md:67]` |
| COMS broker is a LAN address, anonymous, no TLS | `[SRC: INVESTIGATION_2026-11-18_job_board_coms_assetclasses_pm.md:99]` |
| settled tally | `[SRC: docs/edge_research/28_PROGRAMME_STATUS_INDEX_2026-11-23.md:7]` |
| do not re-derive the verdicts | `[SRC: docs/edge_research/28_PROGRAMME_STATUS_INDEX_2026-11-23.md:163]` |
| settled triple and discovery in the tally test | `[SRC: tests/test_edge_research_tally_consistency.py:134-149]` |
| workflow idioms (cron, concurrency, commit guard, retry loop) | `[SRC: .github/workflows/crypto-intraday-sim.yml:17-91]` |

For the workflow's cron, concurrency group and steps, `.github/workflows/peer-claim-verification.yml` is the source of truth.
