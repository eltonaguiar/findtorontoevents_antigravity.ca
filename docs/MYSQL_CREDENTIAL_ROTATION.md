# MySQL Credential Rotation — P0 Action Required

## Issue
The `ejaguiar1_stocks` MySQL password (`stocks123`) appears in git history and
in repository worktree files. While it was intentionally set via commit
`b6ae06e8a4` ("bulk password fix"), having it in version control is a security
risk.

**Flagged by:** Peer inbox (claude-elton2026 prior session, 2026-05-16T21:00Z)
**Severity:** P0 — credential in git history is permanently accessible

## Current State
- `DB_PASS_STOCKS` env var on this desktop ends in `23` (matches `stocks123`)
- Files currently containing `stocks123`:
  - `.claude/worktrees/` (local only, not in main branch)
  - `docs/MYSQL_ENV_SETUP.md`
- Password was set in commit `b6ae06e8a4` (2026-05-15)

## Rotation Steps (Operator Manual Action)

### 1. Generate new password
```bash
python -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(24)))"
```

### 2. Update MySQL on 50webs
```sql
ALTER USER 'ejaguiar1_stocks'@'%' IDENTIFIED BY '<new_password>';
FLUSH PRIVILEGES;
```

### 3. Update environment variables on all machines
- Desktop: Update in System Properties → Environment Variables
- GitHub Actions: Update `STOCKS_DB_PASSWORD` secret in repo Settings → Secrets
- Any other agents with `DB_PASS_STOCKS` set

### 4. After rotation, remove hardcoded passwords from docs
```bash
grep -r "stocks123" --include="*.md" --include="*.py" -l
# Edit each file to use ${DB_PASS_STOCKS} env var reference
```

### 5. Verify rotation
```bash
python -c "import mysql.connector; conn = mysql.connector.connect(host='...', user='ejaguiar1_stocks', password='<new>', database='ejaguiar1_stocks'); print('OK')"
```

## Files to Update After Rotation
- `docs/MYSQL_ENV_SETUP.md` — replace literal password with `${DB_PASS_STOCKS}`
- Any CI/CD pipeline configs
- This file (update status below)

## Status
- [ ] New password generated
- [ ] MySQL password updated on 50webs
- [ ] Environment variables updated on desktop
- [ ] GitHub Actions secrets updated
- [ ] Hardcoded references removed from docs
- [ ] Rotation verified
