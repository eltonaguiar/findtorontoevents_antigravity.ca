# Git History Reclaim - 2026-05-23

## Summary

**LOCAL REWRITE COMPLETE** — Large JSON payload files removed from git history to reclaim ~18 GiB of disk space.

**REMOTE PUSH STATUS:** Blocked by GitHub server limits (HTTP 500 on receive-pack for 16 GiB pack). See `PUSH_INSTRUCTIONS.md` for retry commands and mitigation options.

### Files Removed from All History

- `audit_dashboard/data/dashboard_data.json` — 1,139 historical revisions purged
- `audit_trail/data/dashboard_payload.json` — 2,191 historical revisions purged

## Process Completed Locally

1. Created full mirror backup (`/home/eaguiar2015/fte-mirror-backup-2026-05-23.git`)
2. Created fresh rewrite clone from mirror (`/home/eaguiar2015/repo-clean`)
3. Executed `bash tools/clean_git_history.sh` (git-filter-repo --invert-paths --force)
4. Verified zero remaining revisions for target paths across `--all`
5. Ran `git fsck --full --strict` — clean
6. Ran `git gc` — completed
7. Confirmed working tree on `main` is sane and buildable

## Push Blocker (GitHub Infrastructure)

Multiple force-push attempts (`--force --all`, `--mirror`, to both original and a newly-created staging repo) all failed with:

```
error: RPC failed; HTTP 500 curl 22 The requested URL returned error: 500
send-pack: unexpected disconnect while reading sideband packet
```

Trace shows GitHub returning HTTP 500 after ~75 seconds while ingesting the 16 GiB pack. This is a known server-side limitation for very large history rewrites.

**Request ID from one failure:** `CB6C:F7A3F:1CB4574:23D87E2:6A114161` (capture a fresh one on retry)

## Current Artifacts

- **Mirror backup (rollback source of truth):** `/home/eaguiar2015/fte-mirror-backup-2026-05-23.git`
- **Rewritten clone (ready to push):** `/home/eaguiar2015/repo-clean`
- **Detailed push instructions & status:** `PUSH_INSTRUCTIONS.md` (in repo-clean root)
- **Draft updates card (this file):** `updates/2026-05-23-git-history-reclaim.md`

## Next Steps (Human Operator)

See `PUSH_INSTRUCTIONS.md` for the full decision tree:

1. **Retry the push** from this or another well-connected machine during off-peak hours
2. **Contact GitHub Support** and reference the repository + request ID; they can often ingest large packs on the backend
3. **Alternative migration:** Use the newly-created empty repo `findtorontoevents_antigravity.ca-clean` as a staging target, then swap names on GitHub after a successful push
4. **After any successful push:**
   - Verify the large files are absent from the GitHub web UI at every commit
   - Have all consumers delete old clones and re-clone
   - Update any pinned SHAs in CI, submodules, deploy scripts
   - Archive or delete the mirror backup only after independent verification

## Rollback

If the push must be undone:

```bash
cd /tmp
git clone --mirror /home/eaguiar2015/fte-mirror-backup-2026-05-23.git restore
cd restore
git push --force --mirror origin
```

This restores the exact pre-rewrite state to the remote.

## References

- Implements **ITEM D** from `reports/OPEN_ITEMS_PLAN_2026-05-22.md`
- Safety script: `tools/clean_git_history.sh`
- Mirror creation + verification commands captured in session logs
- AGENTS.md / CLAUDE.md destructive operation rules followed (mirror first, explicit confirmation, post-rewrite verification, no auto-push)

**Do not consider this item complete until the rewritten history is live on the canonical `origin` remote and independently verified by at least one other person.**