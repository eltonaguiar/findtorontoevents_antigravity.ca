# A PR gate that runs the tribunal for real

**Date:** 2026-11-20
**Area:** `.github/workflows/tribunal-runtime-gate.yml` (new)
**Base:** `origin/main`

## 1. The failure this prevents

`hotfix/required-n-power` was recommended for merge on the strength of two checks that
cannot see a contract mismatch:

- `py_compile` proves the file is valid Python, nothing more.
- `--help` exits **inside `argparse`**, before `main()` builds a report.

The first real invocation died with
`TypeError: build_report() got an unexpected keyword argument 'require_alpha'` — a
producer/consumer skew that both "checks" rated green. `tools/assert_tribunal_runs.py` was
written for exactly this, but nothing ran it automatically, so the tool existed without
being a gate.

## 2. What this adds

A `pull_request` job (`runs-for-real`, `timeout-minutes: 20`) that:

1. checks out the PR, Python 3.11;
2. fetches a real closed-pick payload — `dashboard_data.json` is gitignored (34MB), so a
   clean checkout has no input at all;
3. runs `tools/assert_tribunal_runs.py --picks … --require-sleeves`, which performs a
   real ledger build and asserts the report carries `schema`, `generated_at`, `summary`,
   `coverage`, `denylist_hits`, `n_rows >= 100`, a `sleeves` list, and no rankable sleeve
   above PF 25.

`--require-sleeves` is deliberate: a branch that silently dropped the sleeve list would
pass a bare "does it run" check while removing the contract main now depends on.

## 3. Fail closed, never skip

If the payload cannot be fetched after 3 attempts on the live URL and 3 on the fallback,
the job **fails**. A skipped gate reads as a passed gate in the PR checklist, which is the
same false comfort this tool exists to remove. `assert_tribunal_runs.py` exits 2 (not 0)
when it has no input, and that is respected rather than swallowed.

## 4. Verification (measured, not asserted)

- Real local run on `origin/main` with the live 25.8MB payload:
  `help exit=0 / real run exit=0 / schema=audit3.v1 n_rows=3500 / denylist_hits available
  n=68 / verdict_churn=yes / sleeves count=10 rankable=0 flagged=10 / verdict: PASS` in
  **10 s**.
- Workflow YAML parses; `jobs = ['runs-for-real']`, 3 steps, `pull_request` trigger
  present.
- Payload sanity: the live document is 25,777,877 bytes with a `picks` dict, so the
  tribunal's `('picks','recent_closed') -> ('picks',)` path is reachable.
- **Self-test:** the gate runs on its own PR. That run is the evidence that it works in
  CI and not only on this machine.

## 5. Limitations, stated

1. **Network dependency.** The job needs the public site to serve the payload. Six
   attempts with backoff are used, but a prolonged outage blocks PRs — deliberately, since
   the alternative is a green check on an unrun gate.
2. **26MB download per PR run.** `cancel-in-progress` on the same ref limits waste on
   storm pushes, but this is heavier than a pure unit test.
3. **Scope is the tribunal only.** It says nothing about whether a pick is profitable, and
   nothing about `/audit2`, which remains outside `assert_surface_parity.py`.
4. **Not a required check until branch protection says so.** Adding the workflow does not
   by itself block a merge on repos where only owners merge; the "Approve" button is
   blocked only once this check is marked required in settings.
