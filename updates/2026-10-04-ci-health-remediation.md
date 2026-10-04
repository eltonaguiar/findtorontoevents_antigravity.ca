# CI health remediation — 2026-10-04

Ran the `check-gh-actions` skill against `main`, then extended the scan to
**in-flight/stalled** runs (the skill only inspects *completed* runs — which is
why the worst problem, a multi-day silent outage, had been invisible).

Five distinct problems found; all fixed. Final state: the only remaining
"stale failure" on `main` is `robust-edge-miner`, which is a **by-design
fail-loud alert**, not a bug.

## 1. `CI Tests` red on `main` — quarantine-list comment lines (PR #707)

`PR #702` added explanatory `#` comments into the `known_drift_tests.txt`
heredoc. The gating step turned **every** line into `--deselect=<line>`, so a
comment became `--deselect=# 2026-10-04: ...` which word-split into a stray
pytest path arg:

```
ERROR: file or directory not found: 2026-10-04:
```

**Fix:** filter comment/blank lines before prefixing (both the gating
`DESELECTS` and the non-blocking `DRIFT` run). Verified: 0 stray tokens; YAML
parses; pytest accepts the 70 deselect args; `test (3.11)`/`test (3.12)` pass on
the PR.

## 2. `lint-masking` failed on *every* PR (PR #703)

`beta-portfolio-refresh.yml` (added 2026-10-04) used `continue-on-error: true`
with no `::warning`, and wasn't in the masking baseline — so
`scripts/lint_workflow_masking.py --fail-on-new` failed on every PR. Fix keeps
`continue-on-error` but emits a `::warning` so the failure is visible.

## 3. `Branch Large File Duplicate Guard` — run pileup (PR #705 + manual)

`on: push` for all non-main branches with **no `concurrency`**; the scan fetches
every branch ref and walks each tree, so a single run takes 2–3h. Observed 11
runs `in_progress` at once. **Actions:** cancelled 14 hung runs to free runners;
added a global `concurrency` group with `cancel-in-progress: true`.
*Root cause (slow scan: partial `blob:none` clone + `git ls-tree -l` lazy-fetch)
is a known follow-up — the concurrency change bounds the blast radius.*

## 4. `deploy-riseoftheclaw` — 5-day silent outage (PR #706 + manual)

```
total=200  success=5  cancelled=193   (2026-09-29T11:37 -> 2026-10-04T04:07)
```

All 5 successes were clustered **before** the failure. Root cause: a **zombie**
run `36580338652` entered the concurrency group at `2026-09-29T14:07:55Z` and
never started (`status=queued`). With `cancel-in-progress: false` and GitHub
never expiring queued runs, that single run held the group for 5 days.
**Actions:** cancelled the zombie (next run started within minutes — first start
in 5 days) and set `cancel-in-progress: true` so the group self-heals.
Confirmed: `deploy-riseoftheclaw` is `completed/success` again.

## 5. `scan-new-additions` failed on *every* PR (PR #709)

`db-password-leak-guard.yml` used `fetch-depth: 0` — a full clone of this
~193k-commit repo (all branches+tags) — which exceeded the 5-minute job timeout
and surfaced as a CANCELLED failure on every PR, unrelated to content. It only
diffs `base..head`, so it now shallow-fetches just those two commits.
Verified: shallow fetch + `git diff` + grep logic run clean; the check passes.

## Verification

- `CI Tests` on `main` → `completed/success` (head `7bd81768`).
- Stale-failure scan on `main` → only `robust-edge-miner` (by-design).
- `deploy-riseoftheclaw` → `completed/success`.
- dup-guard in-flight count → 1 (was 11).

## Note / residual exposure

**111 workflows** use `cancel-in-progress: false`, so any of them can be starved
by a zombie queued run the same way `deploy-riseoftheclaw` was. Not changed here
(too broad to flip blindly); flagged for follow-up.
