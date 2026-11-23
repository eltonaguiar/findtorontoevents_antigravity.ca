# 2026-11-23 — Session lessons

Each error below is recorded in the AGENTS.md spirit of "when you make a mistake, document it so
future-you doesn't repeat it". Flat, factual, and each one ends with a rule that can be acted on.

## 1. Read the shared working tree as repository state

Four times I asserted what the repository contained by looking at the shared working tree. That
tree sits on `push/phase2-round-2026-11-22`, **6,841 commits behind `origin/main`** as of this
session, with untracked files that look exactly like repository content.

**Rule: use `git show <ref>:<path>` or a clean `/tmp` worktree; never assert repo state from the
working tree.**

## 2. Invented a `(14 rows)` format defect in the HML pre-registration

I claimed [`docs/preregistration/HML_VALUE_TEST_2026-11-22.md`](docs/preregistration/HML_VALUE_TEST_2026-11-22.md)
had a malformed tally because it lacked the `(14 rows)` suffix. It has no `TALLY:` line at all
(`grep -c "TALLY:"` = 0); it writes the claim as `0 INVESTABLE / 11 NOT_INVESTABLE / 3 UNKNOWN over
14 rows` at `:240` [SRC: `docs/preregistration/HML_VALUE_TEST_2026-11-22.md:240`]. `TALLY_RE`
applies only to docs 15/22/23; HML is discovered by `CLAIM_RE`, which takes no row suffix
[SRC: `tests/test_edge_research_tally_consistency.py:137-138`].

**Rule: before asserting a test's mechanism, read the test.**

## 3. Broadcast a false "the tally test fails on main" claim to COMS

I posted that the tally test fails on main. It passes (22 passed on the pre-merge tip
`6b2e65f`). I retracted by replacing the retained payload on the same topic.

**Rule: retained topics are last-writer-wins; a correction must replace the payload, not be
posted on a different topic beside it.**

## 4. Recommended an unnecessary pilot auto-closer

I proposed building a component to close paper-pilot positions. The pilot already self-closes:
exits are evaluated every tick through `exit_check()`
[SRC: `verified_strategies/paper_pilot/crypto_intraday_sim.py:261`], including TIME exits at
`max_hold_bars` at `:292`.

**Rule: verify a mechanism does not already exist before proposing to build it.**

## 5. Carried stale figures

I quoted pilot `n_closed = 0` when the committed state records 5 closed trades (3 + 0 + 2 across
slots) [SRC: `verified_strategies/paper_pilot/crypto_intraday_sim_state.json`], and I quoted the
ledger as 430 when the audit3 ledger's `forward_gate.n_rows` is 449 [SRC: `audit_dashboard/data/audit3_ledger.json`]
(430 is H-119's own `n_forward`, a narrower scope).

**Rule: re-read the source at the moment you quote it; a figure from an earlier block is a guess.**

## 6. Described the cost figures as "Corwin-Schultz estimates"

They are 1-minute bar-range **upper bounds**
[SRC: `tools/equity_cost_measure.py:224`, `:240`, `:602`]; Corwin-Schultz is a separate, unusable
field in the same artifact (`:147`, `:172`, `:606`). Corrected at
[`updates/2026-11-23-cost-estimator-description-correction.md`](updates/2026-11-23-cost-estimator-description-correction.md).

**Rule: name the estimator by what the code computes, not by what it resembles.**

## 7. Left deliverables on branches while criticising exactly that pattern

Four times (docs 24/25/26, the K1 corrections, doc 27, the FX pre-flight) I wrote work into a
branch and moved on, while my own analysis criticised unmerged work.

**Rule: after any research commit, merge to main in the same block, or state explicitly that it
is unmerged and why.**

## 8. Understated the pilot's requirement threefold

I told the user and the bus that the pilot needs 20 closes. It needs **60** closes
(20 per slot × 3 slots) — `MIN_N_BEFORE_JUDGMENT = 20` at `:54`, counted per slot at `:301`/`:324`
[SRC: `verified_strategies/paper_pilot/crypto_intraday_sim.py:54`].

**Rule: when a threshold is defined per unit, multiply by the number of units before quoting it.**

---

## The pattern the eight share

Every one of them is a number or a state asserted from memory instead of re-read from its source at
the moment it was used — the working tree instead of the ref, the remembered format instead of the
test, the imagined gap instead of the code, the earlier block's figure instead of the file.

## Three rules for future sessions

1. Re-read the exact source line immediately before quoting any figure; never carry one forward.
2. Read the test or the code before claiming what it does or does not check.
3. Merge a deliverable to main in the same block you finish it, or say out loud that it is unmerged.
