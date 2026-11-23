# T3 root cause: the runner never had `tools/` on disk

**Date:** 2026-11-23
**File changed:** `.github/workflows/alpha-engine-fast.yml`
**Prior finding:** `updates/2026-11-23-t3-live-emit-did-not-happen.md`

---

## The cause, proven rather than guessed

The previous note recorded two imports failing with "No module named …" and refused to
guess why, because both modules demonstrably exist in git. The answer was in the checkout
step:

```yaml
sparse-checkout: |
  .github
  alpha_engine
  shared
```

**Three directories. `tools/` and `audit_trail/` are not among them.** The runner's
filesystem therefore never contained them, so at runtime:

- `from provenance_ledger import emit` → **No module named 'provenance_ledger'**
  (`tools/provenance_ledger.py`, 1,705 tracked files live under `tools/`)
- `from audit_trail.quality_gates import enforce_sizing_override` → **No module named
  'audit_trail'** (125 tracked files live under `audit_trail/`)

One cause, two symptoms. And note that `PYTHONPATH: ${{ github.workspace }}` was **already
correct** — the path was on the module search path, the files simply were not on disk.
That is why every local reproduction succeeded: locally, `tools/` is present.

This also means the SHADOW sizing-override guard has been silently inert in CI for as
long as the sparse list has looked like this — a second, unreported degradation of the
same origin.

## Why a green job hid it

The emit is wrapped in `except Exception: print(f"… skipped (non-fatal): {err}")`. A
missing directory therefore produced an informational line and exit code 0. The one
mechanism built to guarantee falsifiability was switched off, and the job said success.

## The three fixes

1. **Sparse checkout:** added `tools`, `audit_trail`, and `reports/provenance`.
   Declared paths went from **3 → 6**.
2. **Stage the ledger:** the commit step now runs
   `git add -f reports/provenance/picks_provenance.jsonl`. Previously only two JSON files
   were staged, so even a successful emit died in the runner's ephemeral filesystem.
3. **Fail loudly:** the scanner output is now teed to `$RUNNER_TEMP/scan.log`, and a new
   step **"Provenance must not be silently skipped"** fails the job with `::error::` if
   `[PROVENANCE] skipped` appears.

A zero-pick cycle is **not** a failure of this guard — `emit_picks([])` legitimately writes
nothing. Only an actual *skip* (import error, exception) fails. The distinction matters:
failing on zero picks would make the job flaky for a reason unrelated to provenance.

## Verification performed here

| Check | Result |
|---|---|
| Workflow YAML parses | OK — 7 steps, in order |
| Sparse-checkout paths | `.github alpha_engine shared tools audit_trail reports/provenance` |
| Guard step placement | after the scan, before the commit |
| `safe_push.sh` carries the commit | `git push origin HEAD:main` — pushes HEAD, not an allowlist |

## What is NOT verified, and must not be claimed

**The fix has not been exercised in CI.** I cannot run a GitHub Actions job from here, so
the honest status is: cause proven, fix applied, YAML valid, end-to-end behaviour
**unverified**. T3 stays OPEN until a real run produces `picks_provenance.jsonl` on `main`
with `n_records > 0` and `provenance-verify.yml` reports the chain intact.

Claiming otherwise is precisely the mistake that produced this ticket: code that looks
right, tested locally, in a step whose success was never checked.

## Remaining exposure

Even with all three fixes, a **zero-pick cycle** writes no ledger rows. The log showed
`T4 HALT: clearing all 0 active picks` and `0 signals`, so T3's acceptance may need an
observation window rather than a single run. That decision is recorded in the fix list of
the prior note and is not resolved here.

Zero capital sanctioned. Not investment advice.
