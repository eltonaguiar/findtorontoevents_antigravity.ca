# Peer claim verification — 2026-11-23

Read-only verification of claims made by peers, by other agents, and by me. Every claim was
checked against real git refs (`git ls-remote`, `git cat-file`, `git rev-parse`,
`git merge-base --is-ancestor`, `git ls-tree`, `git log`) after `git fetch origin --prune`.
**The shared working tree was not used as evidence.**

Reference points at check time (UTC 2026-11-23T03:52):

- main repo `origin/main` = `2af4cf54953df84e354c5e075c27bc071f6a1de4` (fetch advanced it from `ec5f5e69c81`)
- review repo `origin/main` = `0a422436eb3276f9ad926705e04d55605d8e020f` (advanced from `10c2c68`)

Verdicts: **VERIFIED** / **NOT LANDED** / **PARTIALLY** / **UNVERIFIABLE**.
"origin reachable" = the commit is an ancestor of `origin/main` or sits on some
`refs/remotes/origin/*` ref. A commit that exists only locally is **NOT LANDED** by definition.

## Group A — defects raised against me

| id | claim | verdict | decisive evidence | notes |
|----|-------|---------|--------------------|-------|
| A1 (i) | `final/ranked-list-2026-11-23` tip `3a4f199132d` does not contain `docs/edge_research/24_EXECUTION_PLAN_2026-11-23.md`; that file exists only at `086583427e1` on `origin/plan/execution-2026-11-23`, which is not an ancestor of `3a4f1991` | **VERIFIED (was true)** | `git ls-tree 3a4f1991 -- docs/edge_research/` returns 15/22/23/26 only, no 24; `git ls-tree 086583427e1 -- docs/edge_research/24_...md` → `ab7372bfc6c…`; `git merge-base --is-ancestor 086583427e1 3a4f1991; echo $?` → `1` | The peer's original claim held at the time: doc 24 was absent from the final tip and `086583427e1` was not an ancestor of `3a4f1991`. |
| A1 (ii) | underlying concern now resolved because doc 24 is on `origin/main` via PR #1072 (merge `f67840d1ebe`) | **VERIFIED — DEFECT CLOSED** | `git ls-tree origin/main -- docs/edge_research/24_...md` → `100644 blob ab7372bfc6c…` (identical blob to `086583427e1`); `git merge-base --is-ancestor f67840d1ebe origin/main; echo $?` → `0` | Doc 24 is on current `origin/main` with the same blob content as at `086583427e1`, and the PR #1072 merge commit is an ancestor of main. The defect is **CLOSED**. |
| A2 | local `zoo/p0-recovery-2026-11-20` = `3ef08017bf3`, `origin/zoo/p0-recovery-2026-11-20` = `efb90f657c9`, 16 unpushed commits incl. a "GROUNDBREAKING POD-EQUITY-BREAKOUT" result | **VERIFIED (facts), but NOT MINE** | `git rev-parse zoo/p0-recovery-2026-11-20` → `3ef08017bf3773ca…`; `…origin/zoo/p0-recovery-2026-11-20` → `efb90f657c9d531c…`; `git rev-list --count origin/zoo/… .. zoo/…` → `16`; `git merge-base` → `efb90f657c9` | The POD-EQUITY-BREAKOUT commit is `a2932f1611f` ("R5 - POD-EQUITY-BREAKOUT does not reproduce (GROUNDBREAKING)"). See author analysis below. |

### A2 author analysis (mandatory)

`git log --format="%an <%ae>" origin/zoo/p0-recovery-2026-11-20..zoo/p0-recovery-2026-11-20 | sort | uniq -c`:

```
16 github-actions[bot] <eaguiar2015@users.noreply.github.com>
```

**All 16 unpushed commits are authored by `github-actions[bot]`** (machine commits). None are
authored by me (Zoo) or by any human. The branch as a whole is a long-running bot aggregation
branch (its full history mixes ~dozens of bot identities). Under the repo rule "only push your own
changes", **this branch is NOT mine to push.** Recommendation: leave it alone; the decision about
what to do with it belongs to the user.

Staleness / overlap:

- `git rev-list --count zoo/p0-recovery-2026-11-20..origin/main` → **6884** (the local branch is ~6884 commits behind main).
- `git cherry origin/main zoo/p0-recovery-2026-11-20` → **27 `+` / 0 `-`**: none of the local branch's patches are already upstream by patch-id. The 27 (vs 16 unpushed) counts all commits since the merge-base with main.
- Spot-check: `tools/per_class_edge_harness.py` **is** on main (different blob, `b5990946…`); `tools/vol_target_vs_hold.py` and `mercury3/portfolio_tracker.py` are **absent** from main. So some content overlaps by another route, most does not.

## Group B — peer / other-agent "landed" claims

| id | claim | verdict | decisive evidence | notes |
|----|-------|---------|--------------------|-------|
| B1 | review repo `34_FINAL_PICKS_2026-11-23/KILOCODE_VSCODE/INVESTMENT_HUB_ASSESSMENT.md` at `f45f67e`; also `tools/validate_incubator.py` | **PARTIALLY** | `f45f67e` → commit `f45f67ee3871…`, ancestor of review main = yes; `git ls-tree f45f67e -- .../INVESTMENT_HUB_ASSESSMENT.md` → `81829658f26…`. `git ls-tree f45f67e -- tools/validate_incubator.py` → **ABSENT** (also absent at `origin/main`; `git log --all` finds no history for it) | First file VERIFIED; second file NOT LANDED anywhere in the review repo. |
| B2 | review main `74f0ff92a43f…`, range `3f1ab35..74f0ff9`, files `GITHUB_COPILOT_DEEPSEEK/copilot.md` and `picks.json` | **PARTIALLY** | `git ls-remote origin refs/heads/main` at check time → `0a422436eb32…` (main has ADVANCED past `74f0ff9`); `74f0ff92a43f…` is still an ANCESTOR of current main; `git rev-list --count 3f1ab35..74f0ff9` → `1` (single commit `74f0ff9`). At 74f0ff9 the files are at `34_FINAL_PICKS_2026-11-23/GITHUB_COPILOT_DEEPSEEK/{copilot.md,picks.json}`, NOT at repo root | Range and sha VERIFIED (as an ancestor, since main advanced); the named paths were wrong — they are nested under `34_FINAL_PICKS_2026-11-23/`. |
| B3 | main repo `c0d48e28968` adds `tools/edgar_pit_fundamentals.py`, `tests/test_edgar_pit_fundamentals.py`, `reports/pit_filing_lag.json`, `data/fundamentals_pit/*.json`, `updates/2026-11-23-edgar-pit-filing-lag-measured.md` (COMS note also said "LOCAL ONLY") | **NOT LANDED** | `c0d48e28968` → commit `c0d48e2896…`, but `git merge-base --is-ancestor c0d48e28968 origin/main` → NO; `git branch -r --contains c0d48e28968` → **NONE** (local only, on `push/phase2-round-2026-11-22`). All five named paths exist at the sha, but every one is **ABSENT from origin/main** (`data/fundamentals_pit/` = 0 entries on main) | The commit and its files exist only locally. The "LOCAL ONLY" note was accurate. This is **not landed**. |
| B4 | main repo `cd44a8cab33`, `378fdd23fad` for `tools/paired_bootstrap_vs_benchmark.py`, `alpha_engine/two_hurdle_gate.py` | **NOT LANDED** (on origin) | Both resolve to commits, but both are NOT ancestors of `origin/main` and `git branch -r --contains` → **NONE**. `tools/paired_bootstrap_vs_benchmark.py` and `alpha_engine/two_hurdle_gate.py` are both **ABSENT from origin/main** | `cd44a8cab33` has the bootstrap tool; `378fdd23fad` has both files. Local-only. |
| B5 | review repo `a3f6a6b`, `41a6e19`, `3f1ab35` landed on review main; one note says `41a6e19`, another `41e6e19` | **VERIFIED** (with typo correction) | `a3f6a6b` → `a3f6a6b2bf47…`, `41a6e19` → `41a6e19d56ff…`, `3f1ab35` → `3f1ab35db72f…`, all ancestor-of-main = yes. `git cat-file -t 41e6e19` → **ABSENT** | All three claimed shas are on review main. **`41e6e19` does not exist** — it is a typo; the real sha is `41a6e19`. |
| B6 | main repo `0266a3067ed`, `a766c5e06fd`, `487a165cb1b`; workflow `.github/workflows/etf-trend-forward-month-end.yml` on main; branch `pr/h201-pit-universe-2026-11-23` | **NOT LANDED** (commits + workflow) / **VERIFIED** (branch) | All three resolve to commits but are NOT ancestors of `origin/main`, `branch -r --contains` → **NONE**. `git ls-tree origin/main -- .github/workflows/etf-trend-forward-month-end.yml` → **ABSENT**. `git rev-parse origin/pr/h201-pit-universe-2026-11-23` → `a6ef37f2a5f3…` | The three commits and the workflow are local-only / not on main. The branch exists on origin. |
| B7 | `4daf025ed1d` was where `tools/vol_target_vs_hold.py` sat on an unmerged branch, and it was "restored to main" | **NOT LANDED** (the restore) / branch sha exists | `4daf025ed1d` → commit `4daf025ed1d…`, NOT ancestor of `origin/main`, but `git branch -r --contains` → `origin/research/commodity-tsmom-v3-2026-11-22`. `git ls-tree origin/main -- tools/vol_target_vs_hold.py` → **ABSENT** | The sha is on an unmerged research branch (matches "unmerged branch"), but the file is **not on main**, so "restored to main" is **false**. |
| B8 | `5093eb796f8` for pre-registration docs; `tools/per_class_edge_harness.py` and `tools/vol_target_vs_hold.py` on main | **PARTIALLY** | `5093eb796f8` → commit, NOT ancestor of `origin/main`, `branch -r --contains` → **NONE**. `per_class_edge_harness.py` on main → `b5990946f68…` **PRESENT**. `vol_target_vs_hold.py` on main → **ABSENT** | Harness VERIFIED on main; `5093eb796f8` and `vol_target_vs_hold.py` are NOT on origin. |
| B9 | PRs **#1067**, **#1068** claimed OPEN | **VERIFIED** | `gh pr view 1067 --json state` → `"state":"OPEN"`, mergeCommit null; `gh pr view 1068 --json state` → `"state":"OPEN"`, mergeCommit null | Both still OPEN, unmerged. |
| B10 | review repo `d18179d` for `35_TOP_GAINERS_HARVEST_2026-11-23/` | **VERIFIED** | `d18179d` → `d18179d7a6a2…`, ancestor of review main = yes; `git ls-tree d18179d -- 35_TOP_GAINERS_HARVEST_2026-11-23/` → e.g. `MANIFEST.md`; also present at `origin/main` | Folder exists both at the sha and at current main. |
| B11 | main repo `tools/capacity_model.py:49` contains `HURDLE_TBILL_APR = 0.0432` | **NOT LANDED** | `git cat-file -e origin/main:tools/capacity_model.py` → fails; the file is **ABSENT from origin/main**. Only exists at local `1c15c5d7d07` | The line cannot be verified on main because the file is not on main. Claim is unverifiable against `origin/main` and therefore NOT LANDED. |
| B12 | my claims: PR #1074 merge `692cdea41a6ff753eac68ba89aea936a4cc3a47e`, PR #1076 merge `69c5243c5bfdf768b7a795f0a8f6042b51f18748` | **VERIFIED** | `git cat-file -t` → commit for both; `git merge-base --is-ancestor <sha> origin/main; echo $?` → `0` for both. `gh pr view` → both `"state":"MERGED"` (merged 02:41Z / 03:11Z) | Both merge commits are ancestors of current `origin/main`. |

## Summary

- **A1**: the peer's original observation was correct, but the defect is **CLOSED** — doc 24 is on `origin/main` (same blob) via PR #1072 merge `f67840d1ebe`, an ancestor of main.
- **A2**: the sha/count facts hold (16 unpushed), but **all 16 commits are `github-actions[bot]`** — the branch is **not mine to push**.
- **Landed (verified)**: B5, B9, B10, B12. **Partially**: B1, B2, B8. **Not landed on origin**: B3, B4, B6 (commits+workflow), B7 (the "restored to main" part), B11.
- Common failure mode: commits that exist **locally only** (on `push/phase2-round-2026-11-22`) were described as "landed to github". A local `git cat-file` success is not evidence of landing; only reachability from an `origin/*` ref is.

## Scope statement

This task was read-only with respect to repository state and conclusions: **nothing was merged,
pushed, reset, rebased or deleted.** The only write is this report, committed to the unmerged
branch `research/peer-claim-verification-2026-11-23` and pushed by explicit refspec. No branches
(other than that new report branch) were modified.

## Recovery and re-verification addendum (2026-11-23T04:00Z)

This report was previously declared lost: a later task stated that the branch and the commit
`51c77c6ba8a25635884255481e35a6a41bfdc912` did not exist in any clone. **That premise was wrong.**
Re-checked just now:

- `git cat-file -t 51c77c6ba8a2` → `commit`
- `git branch -a --contains 51c77c6ba8a2` → `research/peer-claim-verification-2026-11-23`, `remotes/origin/research/peer-claim-verification-2026-11-23`
- `git ls-remote origin '*peer-claim*'` → `51c77c6ba8a25635884255481e35a6a41bfdc912  refs/heads/research/peer-claim-verification-2026-11-23`
- `git merge-base --is-ancestor 51c77c6ba8a2 origin/main; echo $?` → `1` (the branch is real but **not merged**)

So the report was **RECOVERED from the existing branch**, not regenerated. Every verdict above
was then independently re-run against live refs before merging:

- main `origin/main` = `e0dfa043cbf726c187d5a45d8164ce669b074998` at re-check time
- review `origin/main` = `21ddccf1f068aa3f614b1d65d02971f32879b031` at re-check time

Re-run results all match the table above, with one clarification: the A1 doc-24 blob on main is
`ab7372bfc6c` (identical to `086583427e1`), B12's two merge commits are both ancestors of
`origin/main`, and B9's PRs #1067/#1068 are still `OPEN` with `mergeCommit: null`. Review-repo
shas B1 `f45f67e`, B2 `74f0ff9`, B5 `a3f6a6b`/`41a6e19`/`3f1ab35`, B10 `d18179d` are all still
ancestors of review main; `41e6e19` still does not resolve to any object (typo for `41a6e19`).

## B11 consequence — provenance gap

`tools/capacity_model.py` is **absent from `origin/main`** (`git cat-file -e
origin/main:tools/capacity_model.py` → fatal; `git ls-tree origin/main -- tools/capacity_model.py`
→ empty). It exists only at local `1c15c5d7d07` (`git log --all --oneline -- tools/capacity_model.py`).
The same is true of its test, `tests/test_capacity_model.py`.

The HML value pre-registration cites that exact line as the source of its hurdle:
`docs/preregistration/HML_VALUE_TEST_2026-11-22.md:139` carries
`tools/capacity_model.py:HURDLE_TBILL_APR = 0.0432`. With the file absent from main, the
**4.32% hurdle cannot be reproduced from the repository.** The `[SRC: tools/capacity_model.py:49]`
marker points at a path a fresh clone does not contain.

This does **not** change the HML kill rule. The rule's binding test is **≤ 4.32%**
(`docs/preregistration/HML_VALUE_TEST_2026-11-22.md:143`), and the recorded verdict is KILL on
the gross signal (`:217`), so the conclusion stands. What is broken is the hurdle's
**provenance**: either `tools/capacity_model.py` must be restored to main, or the 4.32% must be
re-cited to a source that exists in the repository. Until then, every document that links to
`tools/capacity_model.py:49` (docs 18 and 24, the ETF-trend pre-registration) has a dead source
link.

## Landing note

A previous attempt to get this report to main **failed**: the report was left on an unmerged
research branch, and the sha `51c77c6ba8a2` was cited to the fleet as if it had landed. It had
not. This PR is the actual landing.
