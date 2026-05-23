# DeepSeek consult — CI fix review (20260425T062441Z)

Model: deepseek-chat. Tokens: {'prompt_tokens': 573, 'completion_tokens': 308, 'total_tokens': 881, 'prompt_tokens_details': {'cached_tokens': 0}, 'prompt_cache_hit_tokens': 0, 'prompt_cache_miss_tokens': 573}.

## Prompt

You are reviewing a CI/CD fix for a Python/GitHub-Actions repo. Be terse, only flag actual problems.

CONTEXT
A scheduled workflow `audit-dashboard.yml` failed run 24923115839: 10 push retries all failed identically with `error: Your local changes to the following files would be overwritten by merge: alpha_engine/data/strategy_performance.json`. That file is written by sibling workflow `alpha-engine-live.yml`, not by audit-dashboard. The retry loop kept the same dirty working tree on every attempt.

THE FIX (applied to two files, same pattern):

```bash
# Before the existing for-loop that does `git pull --no-rebase -X ours --no-edit origin main` then `git push`:
git stash push -m "audit-dashboard: park out-of-scope changes before merge" 2>&1 || true
push_ok=false
for i in 1 2 3 4 5 6 7 8 9 10; do
    git pull --no-rebase --no-recurse-submodules -X ours --no-edit origin main || {
        git merge --abort 2>&1 || true
        # ... backoff
        continue
    }
    # ... conflict-marker check, then push, break on success
done
```

Key choices:
1. Stash WITHOUT `-u` (untracked files don't trigger "would be overwritten by merge").
2. Stash is intentionally NOT popped — those out-of-scope files belong to other workflows' commit steps, and the runner is ephemeral so the orphaned stash entry is harmless.
3. `git merge --abort 2>&1 || true` is left in place because it can legitimately emit "no merge to abort" if pull failed at the working-tree check — that's not actionable.

QUESTIONS
1. Is there any failure mode this fix misses that would still cause the 10-retry-fail pattern?
2. Could `git stash` itself fail in a way that leaves a worse state than before? (e.g. partial stash on a corrupted index)
3. The runner-is-ephemeral argument for not popping the stash — is that sound? Could anything in the post-push steps (FTP deploy, artifact upload) need those parked files?
4. Sibling workflow `multi-asset-scanner.yml` uses `git add -A` before the same retry loop — should I treat that as already-protected (since `-A` stages everything) or also add a stash?
5. Anything else worth flagging?

Reply in <= 250 words. Number your answers.


## Response

1. Yes: if the conflicting file is **untracked** (not in git history), `git stash` without `-u` won't touch it, and the merge will still fail. Verify `strategy_performance.json` is tracked. Also, if the file is **ignored** (`.gitignore`), stash won't help—need `--include-ignored` or manual cleanup.

2. Yes: a corrupted index or a stash failure mid-write could leave the working tree in a partially-stashed state. `git stash push` is generally safe, but adding `git stash drop` after success (or `git stash pop` with conflict handling) would be safer. The `|| true` masks real failures.

3. Sound for ephemeral runners. Post-push steps (FTP, artifacts) typically read from the working tree, not stash. If they need those files, they'll be missing—but that's the existing behavior (they were never committed). Acceptable.

4. `git add -A` stages everything, so the merge won't see local changes as "would be overwritten." It's already protected. No stash needed.

5. The retry loop still has a race: if the sibling workflow pushes between your stash and pull, the merge may still fail (non-fast-forward). The `-X ours` helps but doesn't guarantee success. Consider `git fetch && git reset --hard origin/main` instead of pull for a fully clean slate.
