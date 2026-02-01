# GitHub Actions Workflow Review

## Overview
Found **4 workflow files** in `.github/workflows/`:

1. **deploy-sftp.yml** - SFTP deployment workflow
2. **scrape-events.yml** - Event scraping (every 6 hours)
3. **scrape.yml** - Daily scraper refresh (4 AM UTC)
4. **scraper.yml** - Event scraping (every 6 hours)

---

## Detailed Analysis

### 1. `deploy-sftp.yml` ✅
**Purpose:** Deploy built site to SFTP server  
**Triggers:** Push to `main` branch, manual dispatch  
**Status:** ✅ **Properly configured**

**Features:**
- Uses Node.js 20
- Installs dependencies with `npm ci`
- Builds with `npm run build`
- Uses environment variables from GitHub Secrets:
  - `FTP_SERVER`
  - `FTP_USERNAME`
  - `FTP_PASSWORD`
  - `FTP_PATH1_EVENTS`
- Calls `scripts/deploy-sftp.ts` (uses env vars correctly)

**Notes:**
- ✅ Correctly uses secrets (no hardcoded credentials)
- ✅ Properly structured with emoji steps for readability

---

### 2. `scrape-events.yml` ✅
**Purpose:** Scrape events every 6 hours  
**Triggers:** Cron schedule (`0 */6 * * *`), manual dispatch  
**Status:** ✅ **Well-configured with verification**

**Features:**
- Runs scraper with `npm run scrape`
- **Verifies scraped data** (checks for `events.json`, validates event count)
- **Checks for changes** before committing
- Commits and pushes only if data changed
- Includes metadata verification
- 60-minute timeout to prevent hanging

**Notes:**
- ✅ Excellent error handling and verification
- ✅ Only commits when changes detected
- ✅ Includes helpful logging and status messages

---

### 3. `scrape.yml` ⚠️
**Purpose:** Daily scraper refresh at 4 AM UTC  
**Triggers:** Cron schedule (`0 4 * * *`), manual dispatch  
**Status:** ⚠️ **Needs review**

**Features:**
- Runs scraper with `npm run scrape`
- Commits changes with `[skip ci]` to avoid deployment loops
- **Also runs deployment** with `npm run deploy:sftp`

**Issues:**
- ⚠️ **No verification step** - doesn't check if scraping succeeded
- ⚠️ **No change detection** - always commits (even if no changes)
- ⚠️ **Deployment may fail** if `deploy:sftp` requires secrets that aren't set
- ⚠️ Uses `git config --global` instead of `--local` (minor)

**Recommendations:**
- Add verification step like `scrape-events.yml`
- Add change detection before committing
- Consider separating scraping and deployment into separate jobs

---

### 4. `scraper.yml` ⚠️
**Purpose:** Scrape events every 6 hours  
**Triggers:** Cron schedule (`0 */6 * * *`), manual dispatch  
**Status:** ⚠️ **Redundant with scrape-events.yml**

**Features:**
- Runs scraper with `npm run scrape`
- Commits and pushes changes
- Has `contents: write` permission (good)

**Issues:**
- ⚠️ **Duplicate of `scrape-events.yml`** - both run every 6 hours
- ⚠️ **No verification** - doesn't check if scraping succeeded
- ⚠️ **No change detection** - always commits (even if no changes)
- ⚠️ Commits entire `data/` folder instead of specific files

**Recommendations:**
- **Consider removing this workflow** since `scrape-events.yml` is more robust
- OR merge the best features from both workflows

---

## Overlap Analysis

### Duplicate Schedules:
- `scrape-events.yml` and `scraper.yml` both run **every 6 hours**
- This means scraping runs **twice every 6 hours** (4 times per day total)

### Recommendation:
- **Keep `scrape-events.yml`** (better verification and change detection)
- **Remove or disable `scraper.yml`** (redundant and less robust)

---

## Security Review

### ✅ Good Practices:
- `deploy-sftp.yml` uses GitHub Secrets correctly
- `deploy-sftp.ts` uses environment variables (not hardcoded)

### ⚠️ Security Concern:
- `scripts/deploy-simple.ts` has **hardcoded credentials** (lines 6-9)
  - This file should use environment variables instead
  - However, it's only called by `npm run deploy:sftp` which may not be used in workflows

---

## Required GitHub Secrets

For workflows to function, ensure these secrets are set in GitHub:

### For `deploy-sftp.yml`:
- `FTP_SERVER`
- `FTP_USERNAME`
- `FTP_PASSWORD`
- `FTP_PATH1_EVENTS`

### For scraping workflows:
- `GITHUB_TOKEN` (usually auto-provided, but explicitly used in some workflows)

---

## Recommendations

### High Priority:
1. **Remove or disable `scraper.yml`** - redundant with `scrape-events.yml`
2. **Improve `scrape.yml`** - add verification and change detection
3. **Fix `deploy-simple.ts`** - remove hardcoded credentials, use env vars

### Medium Priority:
4. **Consolidate workflows** - reduce duplication
5. **Add error notifications** - email/Slack on workflow failures
6. **Add workflow status badges** - for README visibility

### Low Priority:
7. **Standardize git config** - use `--local` instead of `--global`
8. **Add workflow descriptions** - document purpose in workflow files

---

## Workflow Summary Table

| Workflow | Schedule | Verification | Change Detection | Deployment |
|----------|----------|--------------|------------------|------------|
| `deploy-sftp.yml` | On push/manual | N/A | N/A | ✅ Yes |
| `scrape-events.yml` | Every 6h | ✅ Yes | ✅ Yes | ❌ No |
| `scrape.yml` | Daily 4 AM | ❌ No | ❌ No | ✅ Yes |
| `scraper.yml` | Every 6h | ❌ No | ❌ No | ❌ No |

---

## Next Steps

1. Review and decide which workflows to keep/remove
2. Set up required GitHub Secrets if not already done
3. Test workflows manually using `workflow_dispatch`
4. Monitor workflow runs for any issues
5. Consider adding notifications for failures

---

*Generated: 2026-01-26*
