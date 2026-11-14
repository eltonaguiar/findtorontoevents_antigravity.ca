# Remote GitHub State — 2026-11-14

**Repo:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca · **Default:** `main`
(branch protection disabled) · **Visibility:** public

## Branches touched on 2026-11-14

| Branch | Head subject | Files vs `main` | Status |
|---|---|---|---|
| `main` | `5995106897a final: organize consolidated audit/peer-review/master-plan/research deliverable under final_2026_11_14/finpredict` | — | 20+ `[skip ci]` bot commits per hour |
| `audit/live-audit-2026-11-14` | `cc0226bdaf0 audit(deepAI): PROFITABLE_APPROACH_v1 …` | 75 files under `2026-11-14/` | **unmergeable** — based on `f54efb3b4ac` (2026-06-06), 23,488 files apart |
| `fix/audit-p0-truth` | `d1c1db68280 fix(audit): P0 truth fixes` | 4 files, +34/−7 | **superseded** — equivalent P0 fixes already on `main` via `9765801d4e3` |
| `wiring` | `ccebced7c8c feat: add money-ready screener with honest findings (0/166 cells pass)` | — | **not merged** |
| `docs/scratch-hippodraco-audit-2026-11-14` | quick-wins bundle | 12 files, +708 | reviewed, advisory |
| `swarmmethodquality-v2` / `-v4` | swarm method quality findings | — | analysis only |
| `bestiejobs-v3`, `salesforceagain-v3` | job-hunting | — | out of scope |

## Pull requests

- **33 open.** Oldest meaningful: #595 (2026-06-13), #600 (2026-06-13), #657/#665/#666/#667 (Jun 24),
  #700–#720 (Oct 3–13), #735–#751 (Oct 18–22), #756–#766 (Oct 22 – Nov 2).
- **2 merged today:** #767 (my quant audit) and #768 (my remediation plan + edge-search results).
  Both squash-merged from clean single-purpose branches; verified present on `main` via the contents
  API (75,664 B and 12,150/8,122 B).
- No open PR carries a 2026-11-14 audit deliverable. **Today's audit round lives entirely in
  branches and untracked folders, not in reviewable PRs** — which is why peer work had to be read
  off branch trees rather than diffs.

## What the remote state says about the system

1. **`main` is a machine state, not a codebase.** Its recent history is almost entirely
   `github-actions[bot] … [skip ci]` commits at ~20/hour (gainer scans, meme scanner, DARWIN engine,
   QuanEngine, coinglass, sidecar refresh, "Auto: Self-optimized trading cycle"). A 33-PR backlog on
   a branch that turns over this fast means review throughput is effectively zero: PRs #595–#667 are
   five months stale and cannot be safely merged without a rebase against 20 commits/hour of data churn.
2. **The two P0-fix branches disagree with each other.** `fix/audit-p0-truth` (branch) and
   `9765801d4e3` (on `main`) both claim the FX `KeyError: 'LONG'` guard and the `summary_picks`
   WR clamp. One of them is redundant. Verify which is live before touching `alpha_engine/scanner.py`
   — I confirmed the branch is **not** an ancestor of `main`, and its diff is only +34/−7, so nothing
   is lost by closing it, but nothing is gained by merging it either.
3. **`wiring`'s headline is itself an audit result:** "money-ready screener … 0/166 cells pass",
   matching the sibling opencode deliverable in this folder. Two independent implementations, same
   zero. That is corroboration, and it is sitting unmerged.

## Hygiene recommendations

| Action | Rationale |
|---|---|
| Close or rebase #595–#667 with a note | 5 months stale, conflicted by design against a high-churn `main` |
| Close `fix/audit-p0-truth` as superseded | Duplicate of `9765801d4e3`; keeps the P0 ledger single-sourced |
| Land `wiring`'s screener as a read-only tool | 0/166 is the most useful number produced today; it should be reachable, not stranded |
| Require audit deliverables as PRs | Branch-only archives are invisible to review and rot within a day |
| Stop `[skip ci]` data commits from outnumbering code commits | 20:1 ratio makes `git log` useless for forensics |

## Verification method

`gh pr list --state open` (33), `gh pr list --state merged --limit 20`, `git for-each-ref
--sort=-committerdate refs/remotes/origin`, `git merge-base --is-ancestor`, `git diff --stat
origin/main origin/<branch>`, `git ls-tree -r --name-only origin/<branch>`, and
`gh api repos/.../contents/<path>?ref=main` for the two delivered documents.
