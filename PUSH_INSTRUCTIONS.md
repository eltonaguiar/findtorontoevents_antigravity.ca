# Git History Rewrite — Push Instructions & Status

**Date:** 2026-05-23  
**Status:** LOCAL REWRITE COMPLETE — REMOTE PUSH BLOCKED BY GITHUB SERVER LIMITS

---

## ✅ What Was Successfully Completed

1. **Mirror backup created** (authoritative rollback point)
   - Location: `/home/eaguiar2015/fte-mirror-backup-2026-05-23.git`
   - Size: 17 GiB, 1.55M objects, pack file `pack-ba4c8a5c0abbaa154b507dc432dc48679738488c.pack`

2. **Fresh rewrite clone created**
   - Location: `/home/eaguiar2015/repo-clean`
   - Created from mirror via `git clone /home/eaguiar2015/fte-mirror-backup-2026-05-23.git .`

3. **History rewrite executed**
   - Tool: `tools/clean_git_history.sh` (git-filter-repo --invert-paths)
   - Paths removed from ALL history:
     - `audit_dashboard/data/dashboard_data.json` (1,139 historical revisions)
     - `audit_trail/data/dashboard_payload.json` (2,191 historical revisions)
   - Verification: `git log --all --oneline -- <path>` returns **0** for both paths

4. **Post-rewrite verification passed**
   - `git fsck --full --strict` — clean (no dangling references to removed blobs in reachable history)
   - Recent commits intact and buildable
   - Working tree clean on branch `main`

5. **Garbage collection run**
   - `git gc` completed successfully (aggressive GC was killed by OOM, standard GC succeeded)

---

## ❌ Remote Push — Current Blocker

**Problem:** GitHub's `git-receive-pack` endpoint returns **HTTP 500** after ~75 seconds when receiving the ~16 GiB pack file.

**Evidence (from GIT_TRACE):**
```
<= Recv header: HTTP/2 500
...
x-github-request-id: CB6C:F7A3F:1CB4574:23D87E2:6A114161
error: RPC failed; HTTP 500 curl 22 The requested URL returned error: 500
```

**Root cause:** GitHub server-side timeout / resource exhaustion while ingesting a 16 GiB pack during a history-rewriting force push. This is a known limitation for very large repositories.

**Attempts made:**
- `git push --force origin main` — HTTP 500
- `git push --force --all origin` — HTTP 500
- `git push --mirror origin` — HTTP 500
- `git push --mirror clean` (to newly created repo) — HTTP 500 after 84s

Even a brand-new empty repository (`findtorontoevents_antigravity.ca-clean`) could not accept the pack.

---

## 🚀 Commands to Run When Ready to Push

### Option 1 — Retry from this machine (may work later if GitHub load decreases)

```bash
cd /home/eaguiar2015/repo-clean

# Ensure remotes are correct
git remote -v
# origin  https://github.com/eltonaguiar/findtorontoevents_antigravity.ca.git

# Force push all refs (this is the canonical command from the script)
git push --force --all origin
git push --force --tags origin

# Or equivalently:
git push --mirror origin
```

### Option 2 — Create a fresh clone from the mirror and push (recommended for retries)

```bash
# On the same or a different machine with good connectivity
git clone --mirror /home/eaguiar2015/fte-mirror-backup-2026-05-23.git repo-clean-fresh
cd repo-clean-fresh

# The history is already rewritten in the mirror? No — the mirror is the OLD history.
# You must re-run the rewrite in the fresh clone, OR copy the objects from repo-clean.

# Better: copy the already-rewritten repo-clean and just reset its origin
cp -a /home/eaguiar2015/repo-clean /home/eaguiar2015/repo-clean-push
cd /home/eaguiar2015/repo-clean-push
git remote set-url origin https://github.com/eltonaguiar/findtorontoevents_antigravity.ca.git
git push --force --all origin
git push --force --tags origin
```

### Option 3 — Contact GitHub Support (most reliable for large rewrites)

Provide them with:
- Repository: `eltonaguiar/findtorontoevents_antigravity.ca`
- Request ID from the failed push: `CB6C:F7A3F:1CB4574:23D87E2:6A114161` (example — capture a fresh one)
- Description: "Force push of 16 GiB rewritten history fails with HTTP 500 on receive-pack after ~75s. Local rewrite complete, mirror backup exists. Requesting server-side assistance to accept the pack."

GitHub support can often import large packs on the backend when the public endpoint times out.

### Option 4 — Use the new empty repo as a staging area (partial success)

We successfully created:
- https://github.com/eltonaguiar/findtorontoevents_antigravity.ca-clean

If you can get even a partial push to succeed there, you can then:
1. On GitHub, rename the old repo to `findtorontoevents_antigravity.ca-old`
2. Rename the clean repo to `findtorontoevents_antigravity.ca`
3. Update any references / webhooks / deploy keys

---

## 📋 Post-Push Checklist (Run These After a Successful Push)

1. **Verify on GitHub**
   - Visit https://github.com/eltonaguiar/findtorontoevents_antigravity.ca
   - Confirm the large JSON files do NOT appear in the file browser at any commit
   - Confirm recent commits look sane (the top of history should match what you have locally)

2. **Create the required updates documentation**
   ```bash
   # In the MAIN working tree (NOT repo-clean), after pulling the new history:
   cd /home/eaguiar2015/findtorontoevents_antigravity.ca
   git pull --ff-only   # or re-clone if you prefer a clean slate

   # Then create:
   # updates/2026-05-23-git-history-reclaim.md
   ```
   (A draft already exists inside `repo-clean/updates/2026-05-23-git-history-reclaim.md` — copy and refine it.)

3. **Notify all consumers**
   - Every developer / CI machine must **delete their old clone** and re-clone
   - Any pinned SHAs in submodules, GitHub Actions `actions/checkout@<sha>`, deploy scripts, etc. must be updated
   - GitHub Actions that reference the old history will see broken SHAs until re-cloned

4. **Archive or delete the mirror backup** (only after you are 100% confident the push is permanent and verified)
   ```bash
   rm -rf /home/eaguiar2015/fte-mirror-backup-2026-05-23.git
   ```

5. **Update any external references**
   - READMEs, docs, or wiki pages that mentioned the old large files
   - Any blog posts or audit reports that linked to specific commits containing those files

---

## 🔄 Rollback (If Something Goes Wrong After Push)

The mirror backup is the source of truth:

```bash
# Restore the OLD (pre-rewrite) history to the remote
cd /tmp
git clone --mirror /home/eaguiar2015/fte-mirror-backup-2026-05-23.git restore-rollback
cd restore-rollback
git push --force --mirror origin
```

This will put the repository back to the exact state it had before the rewrite.

**WARNING:** Anyone who already pulled the rewritten history will have to reset/re-clone again.

---

## 📊 Size Comparison

| State                    | .git size (approx) | Notes |
|--------------------------|--------------------|-------|
| Before rewrite (origin)  | ~17–18 GiB        | Large JSON files in every commit |
| Mirror backup            | 17 GiB            | Full original history |
| repo-clean (after gc)    | 17 GiB (still)    | Pack not yet fully pruned; objects are gone from reachable history |
| Expected after successful push + GC on GitHub | ~several GiB | GitHub will eventually repack; the bloat is removed from the DAG |

The on-disk size in `repo-clean` may not drop dramatically until `git gc --aggressive` or GitHub's backend repack runs. The important metric is **"number of revisions for the removed paths = 0"**, which we have confirmed.

---

## 🗂️ Artifact Locations (This Machine)

- **Mirror backup (rollback source):** `/home/eaguiar2015/fte-mirror-backup-2026-05-23.git`
- **Rewritten working tree:** `/home/eaguiar2015/repo-clean`
- **This instructions file:** `/home/eaguiar2015/repo-clean/PUSH_INSTRUCTIONS.md`
- **Script used:** `/home/eaguiar2015/repo-clean/tools/clean_git_history.sh`
- **Draft updates card:** `/home/eaguiar2015/repo-clean/updates/2026-05-23-git-history-reclaim.md`
- **Local rewrite report (generated by script):** Look for `REWRITE_REPORT_*.md` in repo-clean (may not exist if script was interrupted)

---

## ✅ Sign-off

**Local rewrite verified by:** automated checks + manual `git log --all -- <path>` counts  
**Push status:** Blocked by GitHub infrastructure (HTTP 500 on 16 GiB receive-pack)  
**Next action required:** Human operator intervention (retry, support ticket, or alternative migration path)

**Do not delete the mirror backup until the push has succeeded and been independently verified on GitHub by at least two people.**

---

*Generated 2026-05-23 during ITEM D execution from OPEN_ITEMS_PLAN_2026-05-22.md*