# 🚀 Deployment Quick Reference

**Golden Rule:** GitHub FIRST, then deploy to server.

---

## Quick Check (Before ANY Deployment)

```bash
# 1. Check status
git status

# 2. If clean, deploy
# If not clean, commit first:
git add .
git commit -m "type: description"
git push origin main
```

---

## The 5-Step Process

```
┌─────────────────────────────────────────────────────────────┐
│  1️⃣  Edit Locally     →  Work in E:\findtorontoevents...   │
│  2️⃣  Commit          →  git commit -m "feat: add X"         │
│  3️⃣  Push            →  git push origin main               │
│  4️⃣  Verify          →  Check github.com/commits           │
│  5️⃣  Deploy          →  Upload to server                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Commit Message Cheat Sheet

| Type | Use When | Example |
|------|----------|---------|
| `feat:` | Adding feature | `feat: Add stocks API` |
| `fix:` | Fixing bug | `fix: Correct login error` |
| `docs:` | Documentation | `docs: Update README` |
| `style:` | Formatting | `style: Fix indentation` |
| `refactor:` | Restructure | `refactor: Simplify API` |
| `chore:` | Maintenance | `chore: Update deps` |
| `HOTFIX:` | Emergency* | `HOTFIX: Fix crash` |

*Hotfixes must be committed to GitHub immediately after!

---

## 🚫 NEVER DO THIS

```bash
# ❌ DON'T: Upload without committing
ftp upload file.php

# ❌ DON'T: Edit on server
nano /public_html/file.php

# ❌ DON'T: Quick fix on production
echo "fix" >> file.php

# ❌ DON'T: Deploy from uncommitted changes
# (This is the most common mistake!)
```

---

## ✅ ALWAYS DO THIS

```bash
# ✓ DO: Commit first
git add file.php
git commit -m "fix: Correct database query"
git push origin main

# ✓ DO: Verify on GitHub
open https://github.com/ejaguilar1/findtorontoevents_antigravity.ca/commits/main

# ✓ DO: Then deploy
# (via FTP, GitHub Actions, etc.)
```

---

## Emergency Hotfix Procedure

**ONLY if site is down:**

1. Fix on server (emergency only!)
2. Immediately commit:
```bash
git pull  # Get latest
git add <fixed-files>
git commit -m "HOTFIX: [description] - emergency server fix"
git push origin main
```
3. Document the incident

---

## Pre-Deploy Check Script

### Linux/Mac:
```bash
./tools/pre-deploy-check.sh
```

### Windows:
```powershell
.\tools\pre-deploy-check.ps1
```

---

## What Files to Track

### ✅ ALWAYS Commit:
- `.php` files
- `.html` files
- `.js` files
- `.css` files
- `.json` configs
- `.yml` workflows
- `.sql` schemas
- `.md` docs

### ❌ NEVER Commit:
- `node_modules/`
- `.env` (with secrets)
- `temp_*.json`
- `*.log` files
- Cache files

---

## Deployment Methods

### Method 1: GitHub Actions (Preferred)
- Push triggers automatic deployment
- Requires workflow configuration

### Method 2: Manual FTP
- Commit first
- Then upload via FTP client

### Method 3: Git Pull on Server
- Requires git on server
- SSH to server and `git pull`

---

## Verification Checklist

Before saying "Done":

- [ ] Files committed to GitHub?
- [ ] Commit message descriptive?
- [ ] Pushed to origin/main?
- [ ] Visible on GitHub.com?
- [ ] Deployed to server?
- [ ] Tested on live site?

---

## Common Mistakes

| Mistake | Why It's Bad | Solution |
|---------|--------------|----------|
| Direct server edit | Not tracked, lost on next deploy | Edit locally first |
| Forgetting to push | Commit only local, not on GitHub | `git push origin main` |
| Vague commit msg | Can't understand history | Use `type: description` format |
| Committing secrets | Security risk | Use .gitignore, check before commit |
| Deploying uncommitted | Code not tracked | Run pre-deploy-check script |

---

## Need Help?

1. Read: `DEPLOYMENT_POLICY.md`
2. Read: `AGENTS.md`
3. Run: `tools/pre-deploy-check.sh`
4. Check recent commits for examples: `git log --oneline -10`

---

**Remember:**
> GitHub is the source of truth.  
> The server is just a deployment target.  
> When in doubt: **Commit to GitHub first!**
