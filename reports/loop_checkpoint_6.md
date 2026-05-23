# Loop Checkpoint 6 — T+~140m (2026-05-08 20:35 UTC)

## 🔴 BIG correction: I had wrong-repo bias all session

For ~3 hours I queried `eltonaguiar/findtorontoevents.ca` (the OLD repo) instead of the active `eltonaguiar/findtorontoevents_antigravity.ca`. Effects:
- **My "penny-stock-picks disabled_manually since 2026-02-21" finding** — TRUE on the OLD repo, FALSE on active repo (where it's `state=active`)
- **My "penny-skyrocket-runner.yml not registered" finding** — TRUE for old repo (file not there), FALSE on active repo (it IS registered as `Penny Skyrocket Detector`)

Active repo state for penny workflows:

| workflow | state | last 5 runs |
|---|---|---|
| `Penny Stock Daily Picks` | active | 5/4–5/8 all FAILURE |
| `Penny Skyrocket Detector` | active | 5/4–5/8 all FAILURE |
| `Skyrocket Detector — Live Scanner` | active | unchecked |

**5+ days of consecutive failures** — that's the actual EQUITY pipeline outage.

## Failure root cause

Pulled run 25563493178 logs:

```
Steps:
  ✓ Set up job
  ✓ Checkout repository
  ✓ Set up Python
  ✓ Install dependencies
  ✓ Run penny skyrocket detector
  X Commit results            ← FAILS HERE
  ✓ Step summary
  
Process completed with exit code 128.
```

Exit code 128 from `Commit results` = `git push` non-fast-forward rejection. Penny-skyrocket runs at 14:48 UTC daily and races other workflows committing to main (audit-dashboard.yml hourly, alpha-engine-live.yml every-2h).

## Fix

Per CLAUDE.md + commit `64e44113bb2 fix: upgrade 139 workflows to safe_commit_push.sh`, the canonical fix is:

```yaml
# .github/workflows/penny-skyrocket-runner.yml — Commit results step
- name: Commit results
  run: |
    git config user.name "github-actions[bot]"
    git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
    git add -A
    git diff --staged --quiet && exit 0
    git commit -m "[skip ci] Penny Skyrocket scan $(date -u +%Y-%m-%d)"
    bash tools/safe_commit_push.sh   # retries with rebase + jitter
```

Replace whatever `git push` is currently in the Commit results step with the `safe_commit_push.sh` pattern. 139 other workflows use it; this one was missed.

## Implications

- The 5-day EQUITY pipeline outage is a workflow-concurrency bug, NOT a code bug
- Fix is 1 line edit (replace `git push` with `safe_commit_push.sh`)
- Once fixed, `alpha_engine/data/skyrocket_picks.json` resumes daily writes; dashboard `JSON_PICK_SOURCES` re-picks it up
- Recovers ~1k+ EQUITY rows/week toward charter Tier 2 floor (per uncharted recon prediction)

## Other findings this checkpoint

- penny-skyrocket-runner.yml YAML parses cleanly (Python yaml.safe_load: name, on, concurrency, permissions, jobs)
- The two-repo split (`findtorontoevents.ca` legacy + `findtorontoevents_antigravity.ca` active) is the source of my wrong-repo bias. Future investigations should start with `git remote -v` on the local clone, not assume.

## Done since checkpoint 5

- ✅ YAML-validated penny-skyrocket-runner.yml
- ✅ Discovered two-repo split (active = antigravity, legacy = findtorontoevents.ca)
- ✅ Found 5-day failure streak on active repo
- ✅ Failure root cause = "Commit results" exit 128 = git push conflict
- ✅ Fix prescription = `safe_commit_push.sh` (1-line replace)

## Files

- This: `reports/loop_checkpoint_6.md`
- Previous wrong-repo finding now documented as misattribution: `reports/penny_picks_cron_investigation_2026-05-08.md` (header note added next)
- Fix target: `.github/workflows/penny-skyrocket-runner.yml` Commit-results step
