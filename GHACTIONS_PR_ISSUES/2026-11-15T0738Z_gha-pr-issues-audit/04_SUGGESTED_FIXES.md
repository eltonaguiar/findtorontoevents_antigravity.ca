# 04 — Suggested Fixes (copy-paste ready)

Ordered by value/effort. All commands assume `gh` is authenticated to
`eltonaguiar/findtorontoevents_antigravity.ca`.

---

## Fix 1 — Merge PR #713 (stops the backup-verify issue flood)

PR #713 is **MERGEABLE / CLEAN** and already implements the correct fix. Do not
hand-roll a second implementation.

```bash
gh pr merge 713 --squash --delete-branch
```

What it does (already coded):
- adds `Fetch dashboard_data.json from production` → `curl` the live
  `https://findtorontoevents.ca/audit/data/dashboard_data.json`;
- Query 1 warns + `SKIPPED` instead of `exit 1` when the file is absent;
- removes the gitignored path from `critical_files`;
- makes `Open failure issue` idempotent (`listForRepo` → comment on the open
  issue instead of `create`).

If #713 cannot be merged, the minimal local patch is:

```yaml
# .github/workflows/backup-verify.yml — in the python smoke block
DD = REPO / "audit_dashboard" / "data" / "dashboard_data.json"
if not DD.exists():
    # gitignored at .gitignore:218 → never in actions/checkout. Not a failure.
    print("::warning::dashboard_data.json not present (gitignored) — skipping proxy")
    results["trading_picks_count"] = "SKIPPED"
else:
    ...

# and REMOVE it from critical_files:
critical_files = [
    "alpha_engine/data/recent_exits.json",
    "alpha_engine/data/ml_health_status.json",
    "audit_dashboard/data/pcg5_log.json",
]
```

```javascript
// .github/workflows/backup-verify.yml — Open failure issue step
const open = await github.paginate(github.rest.issues.listForRepo, {
  owner: context.repo.owner, repo: context.repo.repo,
  state: 'open', labels: 'backup-verify',
});
const dup = open.find(i => i.title.startsWith('[backup-verify]'));
if (dup) {
  await github.rest.issues.createComment({
    owner: context.repo.owner, repo: context.repo.repo,
    issue_number: dup.number, body,
  });
  core.notice(`Reused existing open backup-verify issue #${dup.number}`);
} else {
  await github.rest.issues.create({
    owner: context.repo.owner, repo: context.repo.repo,
    title: `[backup-verify] Restore check FAILED — ${new Date().toISOString().slice(0,10)}`,
    body, labels: ['backup-verify','automated'],
  });
}
```

---

## Fix 2 — Merge PR #786 (QA keys + rebase + sports smoke)

```bash
gh pr merge 786 --squash --delete-branch
```

**Secret reality check (verified):** repo secrets include `FINNHUB`,
`FINNHUB_API_KEY`, `FMP_API_KEY`, `ALPHA_VANTAGE_API_KEY` → three working
adapters. `TIINGO_API_KEY` and `TWELVE_DATA_API_KEY` are **absent**, but they are
optional fallbacks, so QA should now pass. If QA still fails with
`ALL 7 sources failed`, add the two missing secrets; do **not** lower the gate.

Also apply the same `ubuntu-24.04` pin to the other two Playwright workflows
(PR #786 only fixes `sports-smoke-and-e2e.yml`):

```yaml
# .github/workflows/social-prediction-tracker.yml:18
-    runs-on: ${{ vars.ACTIONS_RUNNER_LABEL || 'ubuntu-latest' }}
+    runs-on: ${{ vars.ACTIONS_RUNNER_LABEL || 'ubuntu-24.04' }}

# .github/workflows/sports-betting-refresh.yml:27 and :659
-    runs-on: ${{ vars.ACTIONS_RUNNER_LABEL || 'ubuntu-latest' }}
+    runs-on: ${{ vars.ACTIONS_RUNNER_LABEL || 'ubuntu-24.04' }}
```

(`ACTIONS_RUNNER_LABEL` does not exist as a repo variable — confirmed via
`gh api .../actions/variables` — so the `||` fallback is always what runs.)

---

## Fix 3 — Stop the guardian retry loop (`scripts/actions_failure_guardian.py`)

The guardian re-runs **every** latest failure on main every 30 min with no cap
and no exclude list. Add both. See `06_PATCHES/guardian_exclude_and_retry_cap.patch`.

Summary of the change:

```python
# 1) find_unresolved_latest_failures(): carry run_attempt through
            "created_at": latest.get("created_at"),
            "run_attempt": latest.get("run_attempt", 1),   # <-- add

# 2) main(): read config
    excluded = {s.strip().lower()
                for s in os.getenv("FAILURE_GUARD_EXCLUDE", "").split(",") if s.strip()}
    max_attempt = int(os.getenv("FAILURE_GUARD_MAX_ATTEMPT", "3"))

# 3) main(): skip excluded + capped runs before rerun
    for row in unresolved:
        ...
        name = (row.get("workflow_name") or "").strip().lower()
        if name in excluded:
            row["rerun_message"] = "skipped (excluded)"
            continue
        if int(row.get("run_attempt") or 1) >= max_attempt:
            row["rerun_message"] = f"skipped (attempt {row.get('run_attempt')} >= cap {max_attempt})"
            continue
        ...existing age check...
```

And set the exclude list in `.github/workflows/actions-failure-guardian.yml`:

```yaml
      - name: Run failure guardian script
        env:
          GITHUB_TOKEN: ${{ secrets.GH_PAT || github.token }}
          GITHUB_REPOSITORY: ${{ github.repository }}
          FAILURE_GUARD_MAX_ATTEMPT: "3"
          FAILURE_GUARD_EXCLUDE: "Backup Restore Verification,Secret Rotation Reminder"
```

Result: no more infinite re-run → duplicate-issue loop, and a hard cap on retries.

---

## Fix 4 — Auto-close the bot issue on recovery

Add to `backup-verify.yml` after the success step:

```yaml
      - name: Close stale issue on success
        if: success()
        uses: actions/github-script@v8
        with:
          script: |
            const open = await github.paginate(github.rest.issues.listForRepo, {
              owner: context.repo.owner, repo: context.repo.repo,
              state: 'open', labels: 'backup-verify',
            });
            for (const i of open) {
              await github.rest.issues.createComment({
                owner: context.repo.owner, repo: context.repo.repo,
                issue_number: i.number,
                body: `✅ Backup verification passed at ${new Date().toISOString()} — closing.`,
              });
              await github.rest.issues.update({
                owner: context.repo.owner, repo: context.repo.repo,
                issue_number: i.number, state: 'closed',
              });
            }
```

Same idempotency pattern should be applied to
`secret-rotation-reminder.yml` (one pinned tracking issue, comment monthly).

---

## Fix 5 — Issue cleanup (run after Fix 1/2 are merged)

```bash
# Close the 43 stale backup-verify duplicates (safe AFTER #713 is merged)
gh issue list --state open --label backup-verify --limit 200 --json number \
  | jq -r '.[].number' | xargs -rn1 gh issue close --reason "not planned"

# Close superseded monthly secret-rotation reminders (keep #764)
for n in 695 685 675 668; do gh issue close "$n" --reason "not planned"; done
```

Keep **#748** open — it is the real FLAT_CLOSE / `exit_price=0.0` data bug.

---

## Fix 6 — Cron sprawl (the systemic fix)

Measured: **313 scheduled workflows, 236 that push to `main`, 83 firing every
minute.** Run `06_PATCHES/audit_workflow_sprawl.py` to regenerate, then:

1. **Disable duplicates/retired scanners** — move to `.disabled`:
   `edge-stability-daily.yml` *or* `edge-stability-refresh.yml` (same name).
2. **Stagger the `* * * * *` cluster** — spread 83 jobs across minutes
   (`7`, `17`, …) so they don't all hit the same runner-minutes and push race.
3. **Convert push-to-main publishers to a single serialized queue** (one
   `dashboard-publish` concurrency group already exists; extend it to the
   snapshot jobs) instead of 236 independent `git push` attempts.
4. **Prune zero-output scanners** — anything whose latest N runs are
   `cancelled`/empty. The guardian already computes a
   `chronic_cancel_workflows` list in `reports/actions_failure_guardian.json`;
   act on it.

---

## Fix 7 — Stop shipping code under `[skip ci]`

Real Python landed under `[skip ci]` in the last 48h (e.g. the forward-tracker
cost model `e527b290026`). At minimum, run `python -m py_compile` + the relevant
`tests/test_*.py` in a small non-blocking job before such commits, or drop
`[skip ci]` for non-data commits.

---

## Do NOT

- Do **not** lower QA tolerances or exit codes to make it green (PR #786 already
  correctly refuses to).
- Do **not** re-add a `push:` trigger to `audit-dashboard.yml` (AGENTS.md: the
  2026-05-19 cancel-cascade removal was deliberate).
- Do **not** hand-roll a second backup-verify fix — merge #713.
