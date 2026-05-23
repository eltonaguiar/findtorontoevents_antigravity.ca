# MySQL Environment Setup

This guide covers required credentials for all MySQL sync scripts in this repo
(`tools/cross_db_consistency.py`, `tools/db_freshness_check.py`, and any future
sync/audit scripts).  Run `python tools/env_check.py` before any sync to confirm
all required variables are resolved.

---

## 1. Required Secrets

| Secret Name       | Database    | Required? | Notes                                      |
|-------------------|-------------|-----------|--------------------------------------------|
| `DB_PASS_STOCKS`  | Stocks DB   | Preferred | Takes precedence over `MYSQL_PASSWORD`     |
| `DB_PASS_BACKTESTS` | Backtests DB | Preferred | Takes precedence over `MYSQL_PASSWORD`   |
| `MYSQL_PASSWORD`  | Both DBs    | Fallback  | Used when per-DB secret is absent          |
| `AUDIT_DB_PASS`   | Stocks DB   | Fallback  | Last-resort fallback for stocks DB only    |
| `MYSQL_HOST`      | Both DBs    | Optional  | Defaults to `mysql.50webs.com` if not set  |

### Setting in GitHub Secrets (Actions)

1. Go to **Settings → Secrets and variables → Actions** in your GitHub repo.
2. Click **New repository secret** for each secret listed above.
3. Reference them in workflow YAML:

```yaml
env:
  DB_PASS_STOCKS:    ${{ secrets.DB_PASS_STOCKS }}
  DB_PASS_BACKTESTS: ${{ secrets.DB_PASS_BACKTESTS }}
  MYSQL_PASSWORD:    ${{ secrets.MYSQL_PASSWORD }}
  MYSQL_HOST:        ${{ secrets.MYSQL_HOST }}
```

---

## 2. Windows Local Setup (PowerShell)

Set variables for the current session only (lost on terminal close):

```powershell
$env:DB_PASS_STOCKS    = "your_stocks_password_here"
$env:DB_PASS_BACKTESTS = "your_backtests_password_here"
$env:MYSQL_HOST        = "mysql.50webs.com"
```

To persist across sessions (user-level, survives reboots):

```powershell
[System.Environment]::SetEnvironmentVariable("DB_PASS_STOCKS",    "your_stocks_password_here",    "User")
[System.Environment]::SetEnvironmentVariable("DB_PASS_BACKTESTS", "your_backtests_password_here", "User")
[System.Environment]::SetEnvironmentVariable("MYSQL_HOST",        "mysql.50webs.com",             "User")
```

Verify after setting:

```powershell
python tools/env_check.py
```

Expected output when all vars are set:

```
[env_check] Stocks DB credential: resolved via DB_PASS_STOCKS
[env_check] Backtests DB credential: resolved via DB_PASS_BACKTESTS
[env_check] MySQL host: mysql.50webs.com
[env_check] All required env vars present.
```

---

## 3. Credential Fallback Chain

`env_check.py` (and all sync scripts) resolve passwords in this priority order:

### Stocks DB password

```
DB_PASS_STOCKS  →  MYSQL_PASSWORD  →  AUDIT_DB_PASS
```

### Backtests DB password

```
DB_PASS_BACKTESTS  →  MYSQL_PASSWORD
```

### MySQL host

```
MYSQL_HOST  →  "mysql.50webs.com"  (hard-coded default)
```

Using per-DB secrets (`DB_PASS_STOCKS` / `DB_PASS_BACKTESTS`) is strongly preferred
because they allow independent rotation and limit blast radius if one credential leaks.

---

## 4. Troubleshooting

### `env_check` exits 1 — "password missing"

- Confirm the env var is exported in the current shell, not just defined in a child
  process or `.env` file that was never sourced.
- On Windows, close and reopen the terminal after setting User-level vars via
  `SetEnvironmentVariable`.
- In GitHub Actions, confirm the secret name matches exactly (case-sensitive) and the
  workflow step includes the `env:` block shown in §1.

### `Access denied for user` from MySQL connector

- The password resolved by `env_check` is correct for the OS env, but the DB user /
  password combination is wrong on the server side.
- Verify with: `mysql -h mysql.50webs.com -u <user> -p` (enter password manually).
- Contact 50webs hosting panel to reset the DB user password, then rotate the secret.

### `Can't connect to MySQL server` / timeout

- `MYSQL_HOST` may be wrong. The 50webs shared-host value is `mysql.50webs.com`.
- Check that your IP / GitHub Actions egress IP is allowed in the 50webs "Remote MySQL"
  panel (cPanel → Remote MySQL → add `%` for GitHub-hosted runners if needed).

### Two DBs share `MYSQL_PASSWORD` but one password changed

- Set the changed DB's dedicated secret (`DB_PASS_STOCKS` or `DB_PASS_BACKTESTS`)
  so the fallback to `MYSQL_PASSWORD` is bypassed for that DB only.

---

## 5. Security Note

**NEVER commit passwords to this repo.**

- Use `.gitignore` to exclude any `.env` files.
- Store all credentials as GitHub Secrets or Windows User-level environment variables
  (never System-level on shared machines).

**ROTATE IMMEDIATELY:** The password `stocks123` was committed in plain text in
PR #1086 and is now in git history. Any account using this password should be
considered compromised.

Steps to rotate:

1. Log into the 50webs cPanel.
2. Navigate to **MySQL Databases → Change Password** for the affected DB user.
3. Update `DB_PASS_STOCKS` (and `MYSQL_PASSWORD` if it was set to the same value)
   in GitHub Secrets and your local environment.
4. Run `python tools/env_check.py` to confirm the new credential resolves.
5. Run a quick connectivity smoke test against the DB to confirm the new password works
   before triggering any scheduled sync job.

To scrub the exposed value from git history, use `git filter-repo` or open a
GitHub support ticket — but note that anyone who cloned the repo before the scrub
may still have the old value locally.
