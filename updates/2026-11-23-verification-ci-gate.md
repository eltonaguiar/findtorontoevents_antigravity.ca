# Verification CI gate (2026-11-23)

## What was missing

The verification stack on `main` had tests but no gate that could block a merge:

- [`tools/verify_peer_claims.py`](../tools/verify_peer_claims.py) — deterministic peer-claim engine
- [`claims/verification_claims.json`](../claims/verification_claims.json) — 18 claims (17 active, 1 retired)
- [`tests/test_verify_peer_claims.py`](../tests/test_verify_peer_claims.py), [`tests/test_capacity_model.py`](../tests/test_capacity_model.py), [`tests/test_edge_research_tally_consistency.py`](../tests/test_edge_research_tally_consistency.py)
- [`.github/workflows/peer-claim-verification.yml`](../.github/workflows/peer-claim-verification.yml) — weekly cron + `workflow_dispatch` only, **no `pull_request` or `push` trigger**

PR #1097 (`a70bf659fd2`, containing `4f740be3a73` "first-class claim retirement") changed the
engine, the manifest and the tests. It merged with no gate. Evidence:

- Branch protection on `main` is **disabled** (`gh api .../branches/main/protection` → 404
  "Branch protection has been disabled on this repository"), so there are no required checks.
- The only workflow that runs `tests/` on PRs, [`ci-tests.yml`](../.github/workflows/ci-tests.yml),
  did run on PR #1097 and **failed** (`test (3.11)` and `test (3.12)`, run `45128193990`). The PR
  merged at `07:02:01Z`, seconds after the checks started and ~5 minutes before they finished.
  Its failure was unrelated drift (`tests/test_verify_peer_claims.py::test_remote_map_env_var`,
  which fails when `origin/main` is not fetched in the checkout), so even a blocking gate on
  `ci-tests.yml` would have been red for the wrong reason.

## What changed

Added [`.github/workflows/verification-tests.yml`](../.github/workflows/verification-tests.yml) —
a minimal, read-only gate:

- Triggers: `pull_request` → `main`, `push` → `main`, `workflow_dispatch`.
- `paths:` limited to what can affect these tests: `tools/verify_peer_claims.py`, `claims/**`,
  the three test files, `tools/capacity_model.py`, `docs/**` (the tally test recursively globs
  every markdown file under `docs/`), and the workflow file itself.
- `actions/checkout@v5` with `fetch-depth: 0` (the engine refuses shallow clones by default),
  `actions/setup-python@v6`, Python `3.11`.
- Runs exactly:
  `python3 -m pytest tests/test_verify_peer_claims.py tests/test_capacity_model.py tests/test_edge_research_tally_consistency.py -q`
- `permissions: contents: read`; `concurrency` keyed on `${{ github.ref }}` with
  `cancel-in-progress: true`; `timeout-minutes: 10`.

### Why a new workflow instead of extending `ci-tests.yml`

Rule: do not duplicate an existing gate. [`ci-tests.yml`](../.github/workflows/ci-tests.yml:44)
already runs `pytest tests/` on PRs with `tests/**` in its paths, so it already runs these three
suites. Extending it was the preferred option and was rejected for one concrete reason: this
gate must watch `docs/**` (the tally invariant lives there), and `ci-tests.yml`'s own comment
explains that adding broad globs re-triggers the full ~747-test suite on every commit and lets
the next push cancel it. A sub-minute, docs-aware gate cannot share that workflow's trigger
without either dropping `docs/**` (missing the tally invariant) or turning the heavy suite into
a queue hog again. The new gate is fast and scoped; `ci-tests.yml` remains the broad suite. They
are complementary, not duplicates.

### AGENTS.md registry

**No row added.** The path-registry table in `AGENTS.md` documents *pipeline dependencies*
(workflows that produce artifacts consumed downstream, on cron). This is a PR/push test gate
with no artifact output. Adding it would misrepresent the table's purpose.

## How verified

- Local: `python3 -m pytest tests/test_verify_peer_claims.py tests/test_capacity_model.py tests/test_edge_research_tally_consistency.py -q`
  → **80 passed in ~1.5s** on a full (non-shallow) clone.
- PR run on a clean tree → **success**.
- Probe commit adding a deliberately failing test → run **failure**, log names the probe.
- Probe reverted (no force-push) → run **success** again.
- Merged with `--merge --match-head-commit`; `git grep deliberately_broken_gate_probe origin/main` → no hits.

## What it would have caught

The three defects that were previously found by hand, late, after merging:

1. `fetch-depth: 1` clone inverting six verdicts while the job stayed green (fixed in `4be51510620`).
2. A polarity rule counting absence of evidence as support (fixed in `bcefb7dd5da`).
3. The claim-retirement change in PR #1097 itself, merged ungated.
