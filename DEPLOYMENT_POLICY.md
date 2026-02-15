# Deployment Policy - Find Toronto Events

**Version:** 1.0  
**Date:** February 15, 2026  
**Applies to:** All website updates, database changes, and file deployments

---

## 🚨 MANDATORY RULE

### ALL remote website updates MUST be first tracked in GitHub

**No exceptions.** Any file uploaded directly to the server without being committed to GitHub first is a policy violation.

---

## ✅ Required Workflow

### Step 1: Local Development
```
Working Directory (local)
    ↓
Edit files, test changes
```

### Step 2: GitHub Commit (REQUIRED)
```
git add <files>
git commit -m "descriptive message"
git push origin main
```

### Step 3: Verify on GitHub
- Check commit appears in repository
- Verify files are correct
- Review changes in GitHub interface

### Step 4: Deploy to Server
```
Deploy from GitHub to server
(FTP, GitHub Actions, or manual deploy)
```

### Step 5: Verify Deployment
- Test on live site
- Confirm changes applied correctly

---

## ❌ Forbidden Actions

### NEVER do these:

1. **Direct FTP uploads without GitHub commit**
   ```bash
   # DON'T DO THIS
   ftp upload file.html  # Without committing first
   ```

2. **Edit files directly on server**
   ```bash
   # DON'T DO THIS
   vim /public_html/file.php  # Edit on server
   ```

3. **Use hosting panel file manager for edits**
   ```bash
   # DON'T DO THIS
   Use cPanel/Plesk file manager to edit
   ```

4. **Upload via deployment tools without GitHub tracking**
   ```bash
   # DON'T DO THIS
   Deploy from local directly to server
   ```

---

## 📋 Deployment Checklist

Before any deployment, verify:

- [ ] Changes committed to GitHub
- [ ] Commit message is descriptive
- [ ] Files pushed to origin/main
- [ ] Commit visible on GitHub.com
- [ ] No sensitive data in files (passwords, keys)
- [ ] Backup created (if major change)
- [ ] Deployment method documented

---

## 🔄 Emergency Procedures

### If you MUST hotfix directly on server:

1. **Make the emergency change** (only if site is down)
2. **Immediately commit to GitHub**:
   ```bash
   git pull  # Get any recent changes
   git add <hotfix-files>
   git commit -m "HOTFIX: [description] - emergency server fix"
   git push origin main
   ```
3. **Document in emergency log**
4. **Review at next team meeting**

---

## 📝 Commit Message Standards

### Format:
```
<type>: <subject>

<body> (optional)
```

### Types:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation only
- `style:` - Formatting, missing semi colons, etc
- `refactor:` - Code change that neither fixes a bug nor adds a feature
- `test:` - Adding tests
- `chore:` - Maintenance tasks

### Examples:
```bash
git commit -m "feat: Add new database schema for stocks"
git commit -m "fix: Correct sportsbet database status in reports"
git commit -m "docs: Update deployment policy"
git commit -m "HOTFIX: Fix critical login bug - deployed directly to server"
```

---

## 🏗️ Branching Strategy

### Main Branches:
- `main` - Production code (DEPLOYABLE)
- `develop` - Integration branch (optional)

### Feature Branches:
```bash
git checkout -b feature/database-fixes
git commit -m "feat: Add schema setup endpoints"
git push origin feature/database-fixes
# Create Pull Request
# Merge to main
# Deploy from main
```

---

## 📁 Files to ALWAYS Track in GitHub

### Critical Files:
- All `.php` files
- All `.html` files
- All `.js` files
- All `.css` files
- All `.json` configuration
- All `.yml` workflow files
- All `.sql` schema files
- All `.md` documentation

### Never Track:
- `node_modules/`
- `.env` files with secrets
- Temporary files (`temp_*.json`)
- Log files (`*.log`)
- Cache files

---

## 🔍 Verification Commands

### Before Deployment:
```bash
# Check what will be deployed
git log --oneline -5

# Check status
git status

# Check diff
git diff

# Verify files are committed
git ls-files | grep <filename>
```

### After Deployment:
```bash
# Verify server file matches GitHub
md5sum local_file.php
md5sum remote_file.php  # Should match
```

---

## ⚠️ Consequences of Violations

### First Offense:
- Warning and retraining
- Document incident

### Repeat Offenses:
- Loss of direct server access
- All deployments through CI/CD only
- Code review required for all changes

---

## 📚 Related Documents

- `README.md` - Project overview
- `AGENTS.md` - Agent-specific instructions
- `DATABASE_FIXES_PROGRESS_REPORT.md` - Database work tracking
- `.github/workflows/` - All deployment workflows

---

## 🙋 Questions?

If unsure about deployment procedures:
1. Check this policy document
2. Review recent commits for examples
3. Ask in team chat
4. When in doubt, commit to GitHub first!

---

**Policy Adopted:** February 15, 2026  
**Last Updated:** February 15, 2026  
**Next Review:** March 15, 2026
