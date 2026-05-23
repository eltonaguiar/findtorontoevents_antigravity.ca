# Open PR Review + Attachment Synthesis (2026-05-03)

## Scope

This note captures:

1. Feedback posted as comments on all currently open PRs.
2. Cross-check findings from the attachment bundle:
   - `config_revised.yaml`
   - `EVIDENCE_REPORT_2026_05_02.md`
   - `GOAL_ASSESSMENT_2026_05_02.md`
   - `HEDGE_FUND_AUDIT_REPORT_2026_05_02.md`
   - `INTEGRATION_TESTING_PLAN.md`
   - `plan.md`
   - `pr_597_review.json`
   - `pr_608_review.json`
   - `PR_615_review.json`
   - `pr_665_review.json`
   - `pr_669_review.json`
   - `pr_676_diff.txt`
   - `pr_676_review.json`
   - `PR_ACTION_PLAN.md`
   - `pr644_review.json`
   - `run_audit.py`

## PR Comment Actions Completed

Posted suggestion comments on all 15 open PRs:

- #703
- #700
- #699
- #681
- #676
- #668
- #661
- #660
- #658
- #655
- #644
- #625
- #615
- #608
- #597

## Consolidated Review Outcomes

### Merge-ready / near merge-ready

- **#669**: Additive and low-risk. Good test coverage and fallback behavior. Minor cleanup only.
- **#676**: Data-quality cleanup is focused and symmetrical. Minor metadata sanity check recommended.
- **#608**: Test PR is safe/gated. Needs rebase and optional test-isolation cleanup.

### Request changes / hold

- **#597**: Scope bundling across unrelated streams + stale frontend regression risk. Split and rebase required.
- **#615**: Regressions present (`__builtins__.print` pattern, stale branch failures) and unsafe circuit-breaker reset handling.
- **#644**: Scope mismatch in PR narrative, no automated tests for new gate modules, and thresholds built on low sample counts.
- **#665**: Good shadow-gate design, but bundled removal of walkforward payload is risky and needs explicit coordination/recovery path.

### High-risk broad PRs needing decomposition

- **#681 / #658 / #655 / #661 / #660 / #699 / #700 / #703 / #668 / #625**:
  - Require tighter scope discipline, clearer operator toggles, and stronger test gates for behavioral changes.
  - Multiple PRs mix docs/artifacts with production logic; recommend split before merge for safer rollback.

## Attachment-Specific Technical Notes

1. **`run_audit.py` portability issue**:
   - Default output path uses `/tmp/audit_output.json`, which is not safe in this Windows workspace.
   - Use repo-relative output path by default for cross-platform execution.

2. **Config + plan alignment issue**:
   - `config_revised.yaml` and planning docs include strong operational assumptions (thresholds, gating) that should be protected by automated schema + behavior tests in CI.

3. **Evidence quality**:
   - The evidence docs are detailed and useful for triage.
   - Some proposed hard thresholds still rely on thin sample windows; rollout should remain warn-first with explicit promotion criteria.

4. **Gate enforcement caution**:
   - Any new hard gate relying on upstream flags (for example `forward_validated`) should include fallback logic or explicit upstream readiness checks to avoid starving valid picks.

## Priority Follow-up Checklist

1. Rebase stale branches before further review cycles (#608, #615, #597, and any PR with known merge conflict status).
2. Split mixed-scope PRs into deployable units (logic vs docs/artifacts).
3. Add/expand tests for any new gate or CI-enforcement module before merge.
4. Keep new enforcement in `warn` mode until sample sizes and realized metrics are stable.
5. Fix cross-platform path defaults (`/tmp`) in scripts intended for this workspace.

## Final Recommendation

The current queue has a few clean wins, but most risk is in broad PRs that combine multiple workstreams. Merging should prioritize:

1. Small, reversible, well-tested changes.
2. Rebased branches with green tests.
3. Explicit rollout toggles and rollback criteria for any gate/risk-control behavior change.
