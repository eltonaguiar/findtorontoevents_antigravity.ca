# AGENTS.md - Project Instructions for AI Assistants

**Project:** Find Toronto Events (findtorontoevents.ca)  
**Last Updated:** February 15, 2026

---

## 🚨 CRITICAL RULES - READ FIRST

### RULE #1: All Updates Must Be Tracked in GitHub First

**BEFORE** making any changes to the remote website, you MUST:

1. Create/modify files in the **local working directory**
2. **Commit to GitHub** with descriptive message
3. **Push to origin/main**
4. **Verify commit on GitHub.com**
5. Then and only then, deploy to server

**NEVER** upload files directly to the server without GitHub tracking.

---

### RULE #2: No Direct Server Edits

**FORBIDDEN:**
- Editing files directly on the server
- Using FTP to upload without GitHub commit
- Using hosting panel file manager for changes
- Making "quick fixes" on production

**REQUIRED:**
- All edits happen in local working directory
- All changes committed to GitHub
- Deployment happens from GitHub to server

---

### RULE #3: Verify Before Deploy

Use this checklist before any deployment:

```bash
# 1. Check git status - should show clean or only intended changes
git status

# 2. Check recent commits
git log --oneline -3

# 3. Commit if needed
git add <files>
git commit -m "type: description"
git push origin main

# 4. Verify on GitHub
curl -s https://api.github.com/repos/ejaguilar1/findtorontoevents_antigravity.ca/commits/main | head -20
```

---

## 📋 Project Structure

### Key Directories:
```
/findstocks/          - Stock market data and API
/findcryptopairs/     - Crypto trading signals
/favcreators/         - Streamer/creator tools
/findtorontoevents/   - Main events functionality
/.github/workflows/   - All automation workflows
/tools/               - Utility scripts
/updates/             - Progress tracking pages
```

### Critical Files:
```
AGENTS.md             - This file
DEPLOYMENT_POLICY.md  - Full deployment rules
README.md             - Project documentation
.env                  - Environment variables (NEVER commit secrets)
```

---

## 🔄 Standard Workflows

### Database Updates:
1. Edit schema file locally
2. Commit to GitHub
3. Run setup via GitHub Actions OR
4. Deploy then run setup endpoint

### API Changes:
1. Edit PHP files locally
2. Test locally if possible
3. Commit to GitHub
4. Deploy to server
5. Test API endpoint

### Workflow Changes:
1. Edit `.github/workflows/*.yml`
2. Validate YAML syntax
3. Commit to GitHub
4. Test via GitHub Actions tab

### HTML/CSS/JS Changes:
1. Edit files locally
2. Commit to GitHub
3. Deploy to server
4. Verify in browser

---

## ⚠️ ModSecurity Warning

The hosting provider (50webs.com) has ModSecurity enabled which blocks many automated requests.

### GitHub Actions are often blocked (403 errors)
### Workaround:
- Use manual deployment from local
- Or whitelist GitHub Actions IPs (ask hosting provider)
- Or use alternative hosting for API endpoints

---

## 🗄️ Database Information

### 8 Databases:
1. `ejaguiar1_stocks` - Stock market data
2. `ejaguiar1_memecoin` - Crypto signals
3. `ejaguiar1_sportsbet` - Sports betting data (HAS DATA)
4. `ejaguiar1_events` - Toronto events
5. `ejaguiar1_tvmoviestrailers` - Movie/TV data
6. `ejaguiar1_favcreators` - Creator platform data
7. `ejaguiar1_deals` - Deals/coupons
8. `ejaguiar1_news` - News aggregator

### Connection Pattern:
```php
$db = new mysqli('mysql.50webs.com', 'username', 'password', 'dbname');
if ($db->connect_error) { die("Connection failed"); }
```

---

## 📝 Commit Message Format

```
<type>: <subject>

[optional body]
```

Types:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `style:` - Formatting
- `refactor:` - Code restructuring
- `test:` - Tests
- `chore:` - Maintenance

Example:
```bash
git commit -m "fix: Correct sportsbet database row count"
git commit -m "feat: Add database health monitor for all 8 DBs"
```

---

## 🆘 Emergency Contacts

### Hosting:
- Provider: 50webs.com
- Control Panel: cpanel.50webs.com

### GitHub:
- Repository: ejaguilar1/findtorontoevents_antigravity.ca
- Actions: Check status at github.com -> Actions tab

---

## ✅ Agent Self-Check

Before completing any task, ask yourself:

1. [ ] Are all changes committed to GitHub?
2. [ ] Did I push to origin/main?
3. [ ] Can I see the commit on GitHub.com?
4. [ ] Did I document what I did?
5. [ ] Are there any sensitive files that shouldn't be committed?

If NO to any question, fix it before finishing.

---

## 🎯 Project Goals

1. **Reliability** - All code tracked in version control
2. **Transparency** - All changes documented
3. **Recoverability** - Can restore from GitHub at any time
4. **Scalability** - Proper workflows enable team growth

---

**Remember:** GitHub is the source of truth. The server is just a deployment target.

**When in doubt: Commit to GitHub first!**
