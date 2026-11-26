# gha-queue-audit: the report step could never push (2026-11-26)

## What was broken

`.github/workflows/gha-queue-audit.yml` ran clean — audit ran, report written — and then
finished with 18 error lines while still concluding `success`:

```
fatal: unable to access 'https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/': The requested URL returned error: 403   (x15)
ERROR: All 5 push attempts failed                                                                                                  (x3)
```

The cause is in the workflow's own header: it declares

```yaml
permissions:
  contents: read
  actions: read
```

and its last step commits `reports/gha_queue_audit.json` and pushes it with
`.github/scripts/safe_push.sh`. `contents: read` gives the job token no write access, so the
push is a guaranteed 403 on every run. `safe_push.sh` then retries with exponential backoff
(5 attempts, 600s budget), which is where the ~6 minutes per run went (04:22:30 → 04:28:04 in
run log 45754724808). Nothing ever landed in the repo.

This is one of the 14 workflows the usage triage flagged for push-403 (`reports/GHA_USAGE_TRIAGE.md`),
and it is pure waste: 961 billed minutes across 62 runs, of which a large share was retry sleep.

## What changed

The report is a monitoring artifact — nothing in the codebase reads
`reports/gha_queue_audit.json` (only historical docs mention watching it). So instead of
granting `contents: write` and adding one more pusher to the already contended `main` branch
(236 workflows push there), the last step now uploads the report:

```yaml
      - name: Upload audit report
        if: always()
        uses: actions/upload-artifact@v6
        with:
          name: gha-queue-audit
          path: reports/gha_queue_audit.json
          retention-days: 30
          if-no-files-found: warn
```

`permissions:` is left at `contents: read` — with no push, that is now correct and minimal.

## How it was verified

Debug runs were executed on the idle self-hosted ARM64 runner rather than cloud, then the
workflow was switched back:

| Run | Runner | Result | Log |
|-----|--------|--------|-----|
| 45759735232 | `gx10-arm64-native` | success | 400 runs scanned, 0 push-403 lines, artifact `gha-queue-audit` 748 bytes |
| 45761441306 (re-run) | `gx10-arm64-native` | success | 400 runs scanned, 0 push-403 lines, artifact uploaded |

The report content was read straight off the runner workspace (not just the conclusion) and
is real data: `runs_scanned: 400`, `queued_stuck: 0`, `long_running: 0`,
`duration_stats: 0`, `failed_no_success: 5` on the first run and `4` on the re-run.

After the re-run validated, `runs-on` was restored to `ubuntu-latest` in the same branch, so
the merged diff contains **no self-hosted pin** — only the artifact step.

## Follow-up

`reports/gha_queue_audit.json` stops being refreshed in the repo; read the artifact instead
(`gh run download <run-id> -n gha-queue-audit`). If a dashboard needs it in-repo, replace this
with `permissions: contents: write` plus a `if: github.ref == 'refs/heads/main'` gate rather
than restoring an ungated push.
