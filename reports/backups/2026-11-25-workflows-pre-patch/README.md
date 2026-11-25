# Pre-patch backups — .github/workflows (2026-11-25)

Verbatim copies of the four workflow files **as they were on `origin/main` @ `d8a96e6ac60`**,
taken immediately before the patchset in `plans/2026-11-25-gha-publisher-and-hub-sync-patchset.md`
was applied on branch `fix/gha-pages-hub-sync-and-qa-cron`.

| file | backup |
|---|---|
| `.github/workflows/live_tracker.yml` | `live_tracker.yml.bak` |
| `.github/workflows/deploy-riseoftheclaw.yml` | `deploy-riseoftheclaw.yml.bak` |
| `.github/workflows/hub-sync.yml` | `hub-sync.yml.bak` |
| `.github/workflows/qa-market-validation.yml` | `qa-market-validation.yml.bak` |

Restore one file:

```bash
git show d8a96e6ac60:.github/workflows/live_tracker.yml > .github/workflows/live_tracker.yml
```

`tools/qa_ledger.py` has no .bak here: its pre-patch content is commit `547a00db1bb`
(`git show 547a00db1bb:tools/qa_ledger.py`), and the ledger change never touched the
deployed site, only the gate.
