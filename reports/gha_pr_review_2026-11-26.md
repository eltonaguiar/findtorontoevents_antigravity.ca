# Open PR review — eltonaguiar/findtorontoevents_antigravity.ca

**Date:** 2026-11-26
**Open PRs:** 7, all authored by `eltonaguiar`.
`mergeable` reported `UNKNOWN` for every PR (GitHub had not computed it at review time), so merge
readiness below is based on CI state and diff size, not on a mergeability verdict.

| PR | files | +/- | CI | branch | assessment |
|---|---|---|---|---|---|
| #1125 | 1 | +10/-0 | **none reported** | `fix/pages-artifact-wait` | tiny, plausible, but no checks ran — needs a trigger before merge |
| #1128 | 2 | +14/-2 | 6 success, 1 skipped | `fix/dna-generate-picks-timeout` | **ready** |
| #1150 | 1 | +6/-0 | 6 success, 1 skipped | `fix/cross-aggregator-audit-db-pass` | **ready** — one-line AUDIT_DB_PASS fix |
| #1151 | 26 | +197/-160 | 6 success, 1 skipped | `ci/2026-11-26-safe-push-sweep` | **ready** — routes 25 workflows through `safe_push.sh` |
| #1154 | 1 | +36/-1 | 6 success, 1 skipped | `fix/audit3-ftp-fallback` | **ready** |
| #1149 | 11 | +467/-5 | **none reported** | `fix/audit-dashboard-registry-tribunal-20261125` | audit-dashboard restore; no checks ran |
| #1116 | **1846** | **+894,530/-21,688** | **none reported** | `coverage-and-verdict-tooling-2026-11-24` | do not merge blind — half a million added lines, no CI signal |

## Notes

- #1116 is the only real risk: 1846 files and +894k lines with no checks reported. It should be split
  or at minimum have its diff classified before any merge decision.
  **RESOLVED 2026-11-26** — diff classified: 82% generated artifact (data caches, dashboard/ledger
  JSON, `_raw` snapshots), 9% markdown, 8.6% source (~53k lines of non-HTML code). See
  `updates/2026-11-26-pr1116-diff-audit.md`.
- #1125, #1149 and #1116 share a symptom: **no CI checks reported at all**, while the other four PRs
  each ran 6 checks. Either their `paths:` filters exclude every touched file, or their branch
  predates the current `pull_request` triggers. Worth checking that `push`/`pull_request` triggers
  actually fire for them — a PR with zero checks looks safe and is not.
  **RESOLVED 2026-11-26** — neither guess was right. `pull_request` workflows run on
  `refs/pull/<n>/merge`; all three are merge-conflicted, so no merge ref is built (1116, 1125) or it
  froze at an old base (1149, after commit `2911eb6ea1`). Zero PR checks = conflict signal, not a CI
  outage. See `updates/2026-11-26-pr-checks-missing-due-to-merge-conflicts.md`.
- The `masking-policy-lint` failure in run 45725163709 came from branch `ci/2026-11-25-gha-digest`
  (adding `gha-failure-digest.yml` as a silent masker), which is **no longer among the open PRs** —
  that failure is historical.

## Stale workflow registrations

`db-secret-scan.yml` and `mermaid-test-deploy.yml` are registered on GitHub as **active** workflows,
but neither file exists anywhere in `main`'s tree. They cannot run, yet they still appear in
`gh workflow list` and in any audit that trusts the registry. They need removing from the Actions
settings (or the files restoring, if they were deleted by accident).

**RESOLVED 2026-11-26** — neither was ever on `main` (`commits?path=` returns zero commits for both),
so nothing was deleted by accident. `db-secret-scan.yml` existed only on the now-deleted branch
`fix/md-action-items-2026-06-05` (2 runs, both failed) and is superseded by `db-password-leak-guard.yml`.
`mermaid-test-deploy.yml` exists only on scratch branch `wiring` (338 bytes, deploys `docs/mermaid_tests`,
which does not exist on `main`; 5 runs, all failed). Both **retired** (`disabled_manually`) via the
Actions API. See `updates/2026-11-26-stale-workflow-registrations-retired.md`.
