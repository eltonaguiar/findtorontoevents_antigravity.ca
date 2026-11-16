# Revert Runbook — GitHub Actions Workflow Changes (2026-11-16)

Owner: @fix-manager
Base for all facts: `origin/main` as of 02:17Z (sha at time of analysis: `b016a61f9a2…`; main advances continuously — re-fetch before relying on any branch delta), local HEAD `89bbb6a2212`.
Scope: how to reverse every workflow change the swarm is about to push, plus the recovery commands for changes already landed on `main`.

> [!IMPORTANT]
> **Read §0 before staging anything.** This working tree is a *stale fork of workflows*. Committing the `.github/workflows/` directory wholesale would revert a live production fix **and** resurrect 9 deleted files. Stage only `GHACTIONS_2026-11-16/**` docs, file by file.

---

## 0. Push-safety facts (verified locally)

| Fact | Value |
|---|---|
| Local `HEAD` | `89bbb6a2212` (branch `main`) |
| `origin/main` | as of 02:17Z (sha at time of analysis: `b016a61f9a2…`; main advances continuously — re-fetch before relying on any branch delta) |
| Commits ahead / behind (`HEAD...origin/main`) | **88367 ahead, 15 behind** (`git rev-list --left-right --count HEAD...origin/main` → `88367  15`; left = ahead, right = behind) |
| Workflow files on `origin/main` | **373** |
| Workflow files in local HEAD | **382** |
| Delta `HEAD...origin/main` for `.github/workflows/` | **12 rows**: 9 deleted + 1 modified + 2 renamed |

The 12-row delta (`git diff --name-status HEAD origin/main -- .github/workflows/`), read as "origin/main vs HEAD":

```
D  .github/workflows/cross-db-consistency.yml
D  .github/workflows/daily-price-refresh.yml.disabled
D  .github/workflows/db-freshness-check.yml
M  .github/workflows/dynamic-alpha-engine.yml
D  .github/workflows/live_trading_canada_free.yml
D  .github/workflows/meme-scanner-fixed.yml
D  .github/workflows/ml-battleground-d.yml.retired
D  .github/workflows/ml-battleground-e.yml.retired
D  .github/workflows/ml-battleground-ensemble.yml.retired
D  .github/workflows/ml-battleground-monitor.yml.retired
R085 .github/workflows/ml-gatekeeper-ab-bootstrap.yml -> .github/workflows/ml-gatekeeper-ab-bootstrap.yml.disabled
R078 .github/workflows/mysql-q001-sync.yml -> .github/workflows/mysql-q001-sync.yml.disabled
```

> [!NOTE]
> Count convention: state the delta as **12 rows = 9 `D` + 1 `M` + 2 `R`**. Counting a rename "twice" (D + A) gives 14, but that double-counts paths and should not be used. The `ls-tree` counts (382 − 373 = 9) are a *different population* — they include `.disabled`/`.retired`/non-YAML entries and omit renames — so they neither confirm nor contradict the 12 diff rows.

Reading of the classes:

- **`M dynamic-alpha-engine.yml` — the only live-fix regression.** `origin/main` line 115 is `timeout-minutes: 90` with a comment explaining that 60 caused every scanner cycle to be killed at the job timeout before it could push (perpetual re-run churn). Local HEAD line 112 is `timeout-minutes: 60`. A naive push re-introduces the churn. Blob SHAs on the two *sides* differ and prove the regression: main `d2ec26fef7183ad3bfb900bb29dccf15db3a6031`, HEAD `c2dce7bb2d41a4f0f725698b9dd31b380bf6b540`.
- **9 × `A` — resurrection of deliberate deletions.** Moving `HEAD → origin/main`, these 9 read as `D` on main and are still present in local HEAD, so a wholesale stage puts them **back on main**. These 9 files were removed by `c2393512637` *("remove 9 duplicate/dead workflows (true-dup family audit)")*. That commit is **NOT** an ancestor of `origin/main` (verified: `git merge-base --is-ancestor c2393512637 origin/main` → false); it lives on `origin/fix/disable-dead-workflows-2026-11-16`. Note `origin/main` already lacks these 9, and the local tree still has them.
- **2 × `R` — no-op in intent.** Moving `HEAD → origin/main`, these read as reverse-renames, not `R`: `ml-gatekeeper-ab-bootstrap.yml` and `mysql-q001-sync.yml` were renamed `.yml → .yml.disabled` on main by `3d1aa94ba5e`. Local HEAD still has the pre-rename names, so a wholesale stage renames them *back* on main. (Note: 3d1aa94ba5e is **not** an ancestor of `origin/main`; it lives on another branch.)

**Rule:** never `git add .github/workflows/`. Commit docs only:

```bash
git add GHACTIONS_2026-11-16/2026-11-16_02-07_EST_ghactions/<file>
git commit -m "docs(ghactions): <what>"
```

If a workflow edit is genuinely required, build it as a patch against **main's blob**, not the local file:

```bash
git show origin/main:.github/workflows/<name>.yml > /tmp/<name>.yml
# edit /tmp/<name>.yml
cp /tmp/<name>.yml .github/workflows/<name>.yml
git diff origin/main -- .github/workflows/<name>.yml   # must show ONLY the intended hunk
```

---

## 0a. Verbatim commands (coordinator-mandated)

These three commands must appear exactly as written in any revert workflow:

1. Restore the 90-minute timeout ("get out of the churn jail free"):
   ```bash
   git checkout origin/main -- .github/workflows/dynamic-alpha-engine.yml
   ```
   > [!NOTE]
   > This was originally issued as `git checkout 4645d08eee4 -- …`. That SHA is a **local-only commit** (`git fetch origin 4645d08eee4` → `couldn't find remote ref`) and **not** an ancestor of `origin/main`, so the pinned form is unrunnable on any other clone. Use `origin/main`, which resolves to the same blob `d2ec26fef7183ad3bfb900bb29dccf15db3a6031` and is the only portable source. (`2a8421d197e`, an ancestor of `origin/main`, also holds `90` and works as a pinned fallback.)

2. Revert a docs-only commit (safe; touches only `GHACTIONS_*` paths):
   ```bash
   git revert <our-sha>
   ```

3. Restore one of the 9 files deleted by `c2393512637` (rollback of a cleanup, not a bugfix):
   ```bash
   git checkout c2393512637^ -- .github/workflows/<name>
   ```
   (`c2393512637` must be fetched first — see §4.)

---

## 0b. Verify the revert worked (coordinator-mandated checklist)

All three must pass before calling a revert done:

```bash
git fetch origin && git checkout main && git pull --ff-only
BASE=origin/main

# (a) tree is clean against base — must print 0
git diff origin/main -- .github/workflows/ | grep -c '^[+-]'

# (b) the timeout regression is gone — must print a line containing 90
grep -n "timeout-minutes" .github/workflows/dynamic-alpha-engine.yml   # expect 115:...90 and 177:...5

# (c) file count matches base — both numbers must be equal
git ls-tree -r --name-only $BASE -- .github/workflows | wc -l
git ls-tree -r --name-only HEAD  -- .github/workflows | wc -l
```

Expected: (a) `0`, (b) `90` present at the job level, (c) `373 == 373` at time of writing.

Additional spot checks (expect no output):

```bash
# the 9 dedup deletions are still deleted
for f in cross-db-consistency.yml daily-price-refresh.yml.disabled db-freshness-check.yml \
         live_trading_canada_free.yml meme-scanner-fixed.yml ml-battleground-d.yml.retired \
         ml-battleground-e.yml.retired ml-battleground-ensemble.yml.retired \
         ml-battleground-monitor.yml.retired; do
   git cat-file -e "$BASE:.github/workflows/$f" 2>/dev/null && echo "BACK ON MAIN: $f"
done

# the disabled pair is still disabled (expect .disabled names only)
git ls-tree -r --name-only $BASE -- .github/workflows | grep -E 'gatekeeper-ab-bootstrap|mysql-q001-sync'
```

---

## 1. Revert a docs-only commit we just pushed

Safe, because it touches only `GHACTIONS_2026-11-16/**`.

```bash
git fetch origin
git checkout main && git pull --ff-only
git revert --no-edit <our-sha>
git push origin main
```

Preview without committing: `git revert --no-commit <our-sha>` then `git diff --cached` then `git revert --abort` to bail.

---

## 2. Restore the 90-minute timeout on `dynamic-alpha-engine.yml` ("get out of the churn jail free")

If a push (ours or anyone's) has put `60` back on `main`:

```bash
git fetch origin
git checkout main && git pull --ff-only
git checkout origin/main -- .github/workflows/dynamic-alpha-engine.yml   # restores main's blob as-is
grep -n "timeout-minutes: 90" .github/workflows/dynamic-alpha-engine.yml # must hit line 115
git commit -m "fix(ci): restore 90m timeout on dynamic-alpha-engine (revert regression)"
git push origin main
```

Or, if `main` itself is wrong and the good value must be pulled from a commit rather than from main, use an ancestor of main (`2a8421d197e`, which still holds `90`):

```bash
git checkout 2a8421d197e -- .github/workflows/dynamic-alpha-engine.yml
grep -n "timeout-minutes: 90" .github/workflows/dynamic-alpha-engine.yml # must hit line 115
```

**Verified blob:** `git rev-parse origin/main:.github/workflows/dynamic-alpha-engine.yml` → `d2ec26fef7183ad3bfb900bb29dccf15db3a6031` (the same blob `2a8421d197e` carries). `origin/main` is the only *portable* source — prefer it. (The older pinned `4645d08eee4` resolves to the same blob but is **local-only** and not an ancestor of `origin/main`, so it is not usable elsewhere and is no longer referenced as a command.)

> [!WARNING]
> Never restore this file from a stale local branch or from the local working tree. Local HEAD carries `60`.

---

## 3. Re-enable a workflow that main has disabled

Disabling on main was done by renaming `.yml → .yml.disabled` (or `.yml.retired` for the ml-battleground family). To re-enable, rename it **back** — but only after fixing the reason it was disabled.

```bash
git fetch origin
git checkout main && git pull --ff-only
git mv .github/workflows/<name>.yml.disabled .github/workflows/<name>.yml
# edit the file: fix whatever made it fail (dead endpoint, stale action version, bad path)
git commit -m "ci: re-enable <name> after fixing <root cause>"
git push origin main
```

Currently disabled on `origin/main`, with reason:

| File | Disabled by | Reason |
|---|---|---|
| `daily-price-refresh.yml.disabled` | `2159ba9614f` (PR #793) | `fetch_prices.php` is dead HTTP 404; prices frozen since 2026-04-29. Superseded by `daily-prices-yf-refresh.yml`. |
| `ml-gatekeeper-ab-bootstrap.yml.disabled` | `3d1aa94ba5e` | "rename broken workflows to .disabled to stop spurious failures" |
| `mysql-q001-sync.yml.disabled` | `3d1aa94ba5e` | same |

> [!CAUTION]
> Do **not** re-enable `daily-price-refresh.yml`. Its only data source is a 404 and `daily-prices-yf-refresh.yml` already covers the business need. Re-enabling produces a job that hard-fails by design (`HTTP != 200 → exit 1`) and duplicates/conflicts with the yf refresh.

---

## 4. Restore one of the 9 files deleted by `c2393512637`

These were deleted **deliberately** (true-dup family audit). Restoring is a rollback of a cleanup, not a bugfix — say so in the commit message.

**Precondition:** `c2393512637` is reachable **only** on `origin/fix/disable-dead-workflows-2026-11-16` — it is not an ancestor of `main`. So `c2393512637^` only resolves if you fetch that branch first; on a `main`-only clone the command below fails with `unknown revision`. Fetch it explicitly (this is read-only, it does not check anything out):

```bash
git fetch origin fix/disable-dead-workflows-2026-11-16
```

Then:

```bash
git fetch origin
git checkout main && git pull --ff-only
git checkout c2393512637^ -- .github/workflows/<name>       # e.g. db-freshness-check.yml
git commit -m "revert(ci): restore <name> (rollback of dedup cleanup c2393512637)"
git push origin main
```

The 9 files: `cross-db-consistency.yml`, `daily-price-refresh.yml.disabled`, `db-freshness-check.yml`, `live_trading_canada_free.yml`, `meme-scanner-fixed.yml`, `ml-battleground-d.yml.retired`, `ml-battleground-e.yml.retired`, `ml-battleground-ensemble.yml.retired`, `ml-battleground-monitor.yml.retired`.

---

## 5. Restore a deleted file from an arbitrary SHA (general recipe)

```bash
git log --all --oneline --diff-filter=D -- .github/workflows/<name>   # find the deleting commit
git show <delete-sha>^:.github/workflows/<name> > .github/workflows/<name>   # recover last content
git show <any-sha>:.github/workflows/<name> > .github/workflows/<name>       # or from a chosen SHA
```

Before committing a recovered workflow, diff it against main and check: trigger cron, `concurrency.group`, action versions (`actions/checkout`, `setup-python`), and `PYTHONPATH`/`sys.path` handling.

---

## 6. Verification checklist (run after any revert)

The authoritative checklist is **§0b** — (a) diff against `origin/main` is empty, (b) `timeout-minutes: 90` at line 115, (c) HEAD's workflow count equals `origin/main`'s (373).

Extra check specific to a **docs-only** revert (where `.github/workflows/` must not appear at all):

```bash
git show --stat --oneline HEAD            # must list only GHACTIONS_2026-11-16/... paths
git diff --name-only origin/main~1..origin/main -- .github/workflows/ | wc -l   # must be 0
```

After the push, confirm the reversal took on the remote:

```bash
git fetch origin && git diff --stat origin/main~1..origin/main -- .github/workflows
```

---

## 7. Ordering rules

1. Revert the **most recent** offending commit first; if several, revert newest → oldest or a single `git revert --no-edit A B C`.
2. Never `git push --force` to `main`. Revert commits are append-only and are the only sanctioned way to undo.
3. If a revert conflicts, resolve on a branch, open a PR, and land via merge — do not hand-edit `main` in a dirty tree.
4. Any workflow-restoring revert needs the revert reason written into the commit body, including the original delete/disable SHA.
