# GitHub Actions fixes

## Verified inventory

There are 360 workflow YAML files. 161 have `concurrency`, 271 have `timeout-minutes`, and 39 have a `push` trigger. GitHub lists 365 workflow registrations; five have no matching file in the repository tree. The local `final_v3/00_common_themes/BUGS.md` claim that zero workflows have concurrency/timeouts is contradicted by the scan; use the counts above.

The latest checked `CI Tests` run (`43644095951`, 2026-11-14 21:40Z) failed both Python 3.11 and 3.12 jobs. The audit dashboard run list showed overlapping pending/in-progress/cancelled runs. These are point-in-time observations; inspect the run logs and current status before any remediation.

## P0

- [ ] **A1. Triage the current CI failure.** Inspect the two failed jobs and classify the cause before changing dependencies or interpreter versions.
  - **Accept:** root cause is linked to a minimal reproducer; same workflow passes on the fix commit.
- [ ] **A2. Prevent overlapping writers.** Add concurrency groups first to workflows that write the same output. Use `cancel-in-progress: false` for data publishers; only cancel superseded check-only runs where safe.
  - **Accept:** two simultaneous dispatches cannot race to publish the same file.
- [ ] **A3. Stop stale-success publication.** Add per-input freshness checks and fail a data job when source data exceeds its documented TTL. Missing/unquoted prices must not produce a success-shaped dashboard.
  - **Accept:** a deliberately stale fixture makes the producer fail before deploy/commit.
- [ ] **A4. Protect the audit dashboard's schedule.** Reconcile observed runtime against schedule frequency and concurrency. Keep the documented removal of its `push` trigger; do not re-add it without revisiting the cancel-cascade evidence.
  - **Accept:** no new dashboard run starts while the same output is still being published; a missed refresh is visible rather than silently cancelled.
- [ ] **A5. Run integrity checks before any generated-data commit.** Add conflict-marker, PnL-unit/provenance, denominator, and output-freshness checks to relevant writers.
  - **Accept:** invalid output fails before commit and does not replace the previous good artifact.

## P1

- [ ] **A6. Apply timeouts by measured runtime.** Set an explicit timeout on each long-running job from observed p95 plus a documented margin. Do not blanket-copy one timeout across all 360 workflows.
- [ ] **A7. Audit cron collisions by dependency and resource.** The 2026-11-14 peer report lists large schedule buckets; recompute current buckets, then spread only jobs competing for the same resources or publishing related artifacts.
- [ ] **A8. Reconcile 5 untracked workflow registrations.** The unmatched paths include two `.github/workflows` entries and three `dynamic/...` registrations. Determine whether each is deleted, platform-generated, or intentionally external before disabling anything.
- [ ] **A9. Map one producer per generated artifact.** Classify workflows as producer, consumer, report-only, or retired; disable duplicate writers only after confirming their consumers.
- [ ] **A10. Add explicit runtime/environment assertions.** If `setup-python` pins a version, assert `python --version` in the same job. Change `update-environment` or dependency pins only after reproducing the current failure.
- [ ] **A11. Make optional steps explicit.** Review `continue-on-error` individually; failing required validation should fail the job, while non-blocking diagnostics should be labeled as such.
- [ ] **A12. Keep action supply-chain and secret checks scoped.** Pin third-party actions using the repository's accepted policy, scan generated files for secrets, and scope credentials to the jobs that need them. Never print credential values in logs.

## P2

- [ ] **A13. Archive oversized logs/artifacts.** Rotate large generated logs rather than committing unbounded history.
- [ ] **A14. Add workflow inventory CI.** Compare repository files, registered workflows, schedule, concurrency, timeout, owners, and output destinations. Report drift before cleanup.
- [ ] **A15. Validate deployed assets.** For deploy workflows, run syntax checks and post-deploy smoke checks against known page/payload markers.

**Do not** bulk-add concurrency, move every cron, delete unmatched registrations, or re-enable a removed `push` trigger based on a report alone. Each has a distinct deployment and data-loss risk.

