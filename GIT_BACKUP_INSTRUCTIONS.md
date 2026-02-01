# Backup branch and push to main (TORONTOEVENTS_ANTIGRAVITY)

Run these in a **clone** of [github.com/eltonaguiar/TORONTOEVENTS_ANTIGRAVITY](https://github.com/eltonaguiar/TORONTOEVENTS_ANTIGRAVITY). The `e:\findtorontoevents.ca` workspace is not a git repo, so these must be run from your Antigravity clone (e.g. on another drive or after cloning).

---

## 1. Clone (if you don’t have it yet)

```bash
git clone https://github.com/eltonaguiar/TORONTOEVENTS_ANTIGRAVITY.git
cd TORONTOEVENTS_ANTIGRAVITY
```

---

## 2. Create a backup branch

Create a branch from current `main` so you can restore if needed:

```bash
git fetch origin
git checkout main
git pull origin main
git branch backup-$(date +%Y%m%d)
git push origin backup-$(date +%Y%m%d)
```

On Windows PowerShell, use a fixed name or:

```powershell
git fetch origin
git checkout main
git pull origin main
git branch backup-20260131
git push origin backup-20260131
```

---

## 3. Upload “our project” to main

**Option A – You only want to push current Antigravity repo to main (no new files):**

```bash
git checkout main
# make any edits in the clone, then:
git add .
git commit -m "Update from findtorontoevents.ca session"
git push origin main
```

**Option B – You want to copy findtorontoevents.ca files (e.g. BREAK_FIX.MD, FIX_SUMMARY.md, index.html) into the Antigravity clone and then push:**

1. Copy the files you need from `e:\findtorontoevents.ca` into your `TORONTOEVENTS_ANTIGRAVITY` clone (e.g. put `BREAK_FIX.MD` and `FIX_SUMMARY.md` in the repo root).
2. In the clone:

   ```bash
   git checkout main
   git add .
   git status
   git commit -m "Add BREAK_FIX.MD and FIX_SUMMARY; sync from findtorontoevents.ca"
   git push origin main
   ```

---

## 4. Restore from backup (if needed)

```bash
git fetch origin
git checkout main
git reset --hard origin/backup-20260131
git push origin main --force
```

Use the actual backup branch name you created. **`--force` overwrites remote `main`;** use only when you intend to restore that state.
