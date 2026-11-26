# GHA full workflow sweep — 2026-11-26

## What prompted this

`gh pr view` on #1158 confirmed the merge landed (`cd92eb85eacb`, 2026-11-26T02:11Z),
so the next step was the deferred Mercury 2 retrain. Dispatching it once showed a
green run that committed nothing, which only became visible by checking the model
directory — so the whole workflow registry was swept instead of one workflow.

## Scope of the sweep

| | |
|---|---|
| workflows registered | 386 |
| active | 377 |
| dispatched via `workflow_dispatch` | 365 |
| completed | 350 |
| success | 338 |
| failure | 9 |
| cancelled | 2 |
| skipped | 1 |

Seven workflows could not be dispatched at all:

- `_dynamic-runner-template.yml` — template, intentionally no trigger
- `db-password-leak-guard.yml`, `gha-scan-job.yml`, `masking-policy-lint.yml`,
  `no-stale-db-passwords.yml`, `quant-auditor-fast-pr.yml`,
  `strategy-performance-no-regression.yml` — `pull_request`-only, so they never
  run on a dispatch. The first five are the PR gate checks seen on #1158.
- `resolver-step5-6-backfill.yml`, `resolver-step7-apply.yml` — require a
  `confirm` input. **Not dispatched on purpose** (they write to the DB).
- `pages-build-deployment` — GitHub-managed, not file-based.

## Defects found

### 1. Mercury 2 retrain reported success while committing nothing (fixed)

Run `45742936345` concluded `success`. `mercury2/models/` does not exist on
`main` (API 404), and the next scanner run died with
`ensemble_conservative.joblib not found`.

The commit step ended with:

```bash
for i in 1 2 3; do
  bash .github/scripts/safe_push.sh && break
  echo "Push attempt $i failed, retrying in ${i}0s..."
  sleep ${i}0
  git rebase --abort 2>/dev/null || true
  git pull --rebase origin main || true
done
```

Two independent bugs:

- **The loop swallows the failure.** `safe_push.sh` does `exit 1` correctly, but
  the loop's last command is `git pull --rebase ... || true`, so the step exits 0.
  The job is green with the models still on the runner's disk.
- **Retries are poisoned by the previous attempt.** After a rejected push the tree
  is mid-merge on `ml_battleground/retrain_trigger.json`; every later attempt
  fails with `Pulling is not possible because you have unmerged files`, so
  attempts 4–5 could never succeed.

Fix (`mercury2-retrain.yml`, same shape in `mercury2-scan.yml`): count a
successful push, and on each failure abort the stuck rebase/merge, `git fetch`,
`git reset --soft origin/main` (keeps the work tree, re-parents the commit onto
the current tip) and re-commit before retrying. After five failures the step
prints `::error::` and `exit 1`, so a lost commit can never be reported green.

### 2. `verification-tests` fetch rejected as non-fast-forward (fixed)

```
git fetch --no-tags --depth=1 origin main:refs/remotes/origin/main
! [rejected] main -> origin/main (non-fast-forward)
```

`actions/checkout` already creates a shallow `refs/remotes/origin/main` at the
merge commit, so an un-forced refspec update fails whenever main has moved.
Fixed with `+main:refs/remotes/origin/main`.

### 3. Remaining failures — real, not caused by the sweep

| workflow | cause |
|---|---|
| `anti-overfit-gate` | By design: every strategy fails DSR ≥ 0.95. Correct verdict, permanently red. |
| `Clear Channel Command` | Bot lacks *Manage Messages* in `#freshpicks` (deleted 0/100). Permission fix, not code. |
| `DB Sync: findtorontoevents.ca ↔ torontoevent.net` | `_db_export_tmp.php` returns 404 on the host — the export endpoint is not deployed. |
| `Kimi Fetch Movies/TV (Manual)` | `https://findtorontoevents.ca` returned HTTP 500 while `torontoevent.net` verified fine (added 2, total 8149). |
| `Index All Creator Content` | `curl` exit 56 on `/fc/api/index_all_creators.php`; the endpoint answers normally when called directly, so this is transient/reset, not a broken deploy. |
| `Deploy FC API Hotfix (3 domains)` | FTP connect to GoDaddy: `TimeoutError [Errno 110]` — host unreachable from the runner. |
| `forward observations ingest` | `POD-EQUITY-BREAKOUT` has 0 forward rows 7.1 d after pre-registration (grace 7.0 d) — the emitter never landed. Watchdog working. |
| `WSL Runner Manager` | Targets WSL distro `UbuntuRecovered`, which no longer exists: `WSL_E_DISTRO_NOT_FOUND`. |
| `fx-cost-overlap` | `git push` rejected (`fetch first`) — push race against ~360 concurrent jobs. Measure itself was fine (1 commit, 322 insertions) before the push. |

Two runs were `cancelled` (`Refresh Movies Databases`, `Fetch New Movies & TV Shows`)
— both hit the 10 m concurrency/queue ceiling while the sweep saturated the runners.

## Systemic risk not fixed here

**235 workflows call `safe_push.sh`**, and many wrap it in the same
`for i in 1 2 3` loop that discards its exit status. Any of them can therefore
report green with nothing on `main`. The two Mercury 2 workflows are fixed
because they were the ones under investigation; the rest need the same
`pushed=0 ... if [ "$pushed" -ne 1 ]; then exit 1; fi` treatment. This is a
follow-up, not something to mass-edit in one commit.

## Verification

- All three patched files parse: `yaml.safe_load` OK
  (`mercury2-retrain.yml` 5 steps, `mercury2-scan.yml` 8, `verification-tests.yml` 5).
- The retrain fix is proven end-to-end only by a run that commits
  `mercury2/models/`; that re-dispatch is recorded in
  `updates/2026-11-26-mercury2-retrain-artifacts.md`.

Sweep scripts: `tmp/gha/dispatch_all.py`, `tmp/gha/sweep_status.py`,
`tmp/gha/patch_wf.py` (scratch, gitignored).
