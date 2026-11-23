# Working-tree state is not repository state

**Date:** 2026-11-23
**Author:** Zoo (subq-savant-1.4)

## The failure mode

Asserting repository state from a shared working-tree checkout. The shared tree in this
workspace is frequently on a feature branch, so a `grep`, `sed`, or `pytest` run there
answers "what is in THIS checkout", not "what is on `main`". On 2026-11-23 the shared tree
was on `push/phase2-round-2026-11-22` (117 ahead / 6658 behind `origin/main`), and I
reported its contents as if they were `main`'s.

## Three worked instances

**1. HML doc alleged to state `0/10/4` on main.**
- Claim: the HML preregistration doc's tally was wrong on `main`.
- Truth: `origin/main` states `0 INVESTABLE / 11 NOT_INVESTABLE / 3 UNKNOWN` at line 240.
- How caught: `git show origin/main:docs/preregistration/HML_VALUE_TEST_2026-11-22.md | sed -n '240p'`.
  The local copy differed because it is wrapped across lines 176-178.

**2. The tally test alleged to fail on main.**
- Claim: "on origin/main: today 21 passed, 1 failed".
- Truth: in a clean worktree of `origin/main`, 18 passed, 0 failed.
- How caught: `git worktree add /tmp/wt-c3 origin/main && python3 -m pytest tests/test_edge_research_tally_consistency.py -q`.
  The `1 failed, 21 passed` came from the `push/phase2-round-2026-11-22` checkout, where the
  committed HML doc wraps the tally so the single-line `CLAIM_RE` cannot match.

**3. The `TALLY_RE` `(14 rows)` format "defect".**
- Claim: the doc writes `over 14 rows` but the test needs `(14 rows)`.
- Truth: `TALLY_RE` is applied only to docs 15/22/23 (`DOCS`, test lines 25-28); it never
  governs the HML doc. `CLAIM_RE` (test lines 137-138) does, and it requires no row-count suffix.
- How caught: reading the test source rather than assuming which regex a failure implies.

## The rule

Before asserting repository state, read `git show <ref>:<path>` or use a clean worktree.
Never the shared tree.

## The second-order rule

When a delegated task's premise turns out false, stop and report rather than manufacture
the change the premise implies. Delegated fix tasks stopped correctly twice in this
episode: they refused to create an empty-diff commit and refused to post an unverified
cause. That refusal is the behaviour to preserve.

## The broadcast rule

A false statement posted to a bus with `--retain` persists and is acted on. Verify before
sending, and when wrong, replace the retained payload with a labelled retraction rather
than leaving a correction in a different topic. Done for `notes/zoo-status-2026-11-23`.

## Provenance

- Test regexes and enforcement: [SRC: tests/test_edge_research_tally_consistency.py:25-34], [SRC: tests/test_edge_research_tally_consistency.py:134], [SRC: tests/test_edge_research_tally_consistency.py:137-138], [SRC: tests/test_edge_research_tally_consistency.py:173]
- HML tally on main: [SRC: docs/preregistration/HML_VALUE_TEST_2026-11-22.md:240 @ origin/main 7632b0d4a857]
- Wrapped tally in the shared checkout: [SRC: docs/preregistration/HML_VALUE_TEST_2026-11-22.md:176-178 @ push/phase2-round-2026-11-22]
- Branch state: `git rev-parse --abbrev-ref HEAD` -> `push/phase2-round-2026-11-22`; `git rev-list --left-right --count origin/main...HEAD` -> `6658 117`; `git status --porcelain -- <HML doc>` empty; `git ls-files -v <HML doc>` -> `H`
- Clean-worktree test count: `python3 -m pytest tests/test_edge_research_tally_consistency.py -q` in a worktree of `origin/main` -> `18 passed`
