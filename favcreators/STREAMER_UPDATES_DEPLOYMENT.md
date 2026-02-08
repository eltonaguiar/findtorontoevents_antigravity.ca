# Streamer Updates Feature - Deployment Guide

## Overview
This document provides step-by-step instructions for deploying the Streamer Updates feature to production.

## Prerequisites
- FTP access to `ftps2.50webs.com`
- Database access to `mysql.50webs.com` (ejaguiar1_favcreators)
- Python 3.x installed (for FTP upload script)

## Deployment Steps

### 1. Database Setup

**Execute the database migration script remotely:**

1. Upload `docs/api/setup_streamer_updates_tables.php` to FTP
2. Navigate to: `https://findtorontoevents.ca/fc/api/setup_streamer_updates_tables.php`
3. Verify JSON response shows `SUCCESS` for both tables:
   ```json
   {
     "status": "success",
     "results": {
       "streamer_content": "SUCCESS",
       "user_content_preferences": "SUCCESS"
     }
   }
   ```

### 2. Upload Backend Files

**Files to upload to `/fc/api/`:**
- `setup_streamer_updates_tables.php`
- `streamer_updates_api.php`
- `streamer_updates_preferences.php`
- `fetch_youtube_content.php`

**Upload command:**
```powershell
cd E:\findtorontoevents_antigravity.ca\favcreators
python upload_to_ftp.py
```

### 3. Build and Deploy Frontend

**Build the React app:**
```powershell
cd E:\findtorontoevents_antigravity.ca\favcreators
npm run build
```

**Deploy to FTP:**
```powershell
python upload_to_ftp.py
```

### 4. Verification

**Test the deployed feature:**

1. **Database Tables:**
   - Navigate to: `https://findtorontoevents.ca/fc/api/setup_streamer_updates_tables.php`
   - Verify both tables exist

2. **API Endpoint:**
   - Navigate to: `https://findtorontoevents.ca/fc/api/streamer_updates_api.php?user_id=0`
   - Verify JSON response with `items` array

3. **Frontend Page:**
   - Navigate to: `https://findtorontoevents.ca/fc/#/updates`
   - Verify page loads without JavaScript errors
   - Test platform filters
   - Test refresh button

### 5. Run Tests

**Execute comprehensive test suite:**
```powershell
cd E:\findtorontoevents_antigravity.ca\favcreators
.\tests\run-all-streamer-updates-tests.ps1
```

**Expected output:**
- Playwright: 100+ tests
- Puppeteer: 100+ tests (when implemented)
- Node.js: 100+ tests (when implemented)

### 6. Monitor for Errors

**Check for errors in first 24 hours:**
- Browser console errors
- API response errors
- Database connection issues
- Performance issues

## Rollback Plan

If issues are encountered:

1. **Remove routes from `main.tsx`**
2. **Rebuild and redeploy frontend**
3. **Optionally drop database tables:**
   ```sql
   DROP TABLE IF EXISTS streamer_content;
   DROP TABLE IF EXISTS user_content_preferences;
   ```

## Post-Deployment Tasks

- [ ] Gather user feedback
- [ ] Monitor API performance
- [ ] Implement remaining platform fetchers (TikTok, Twitter, Instagram)
- [x] Add automated content refresh cron job (GitHub Actions workflow)
- [ ] Implement push notifications (future enhancement)

### Automated Content Refresh

The system now includes a GitHub Actions workflow that automatically refreshes creator content daily:

**Workflow:** `.github/workflows/refresh-creator-updates.yml`
- Runs daily at 2 AM UTC (9 PM EST / 10 PM EDT)
- Fetches fresh content for all creators in the database
- Supports YouTube, Twitch, Kick, TikTok, Instagram, Twitter platforms
- Can be manually triggered via GitHub Actions UI

**Backend Script:** `favcreators/public/api/refresh_all_creators.php`
- Aggregates all creators from user lists
- Calls platform-specific fetchers for each creator
- Saves updates to `creator_status_updates` table
- Includes dry-run mode for testing: `?dry_run=1`
- Can limit scope for testing: `?limit=5`

**Manual Trigger:**
1. Go to GitHub repository → Actions tab
2. Select "Refresh Creator Updates" workflow
3. Click "Run workflow" button
4. View logs to see refresh results


## Support

For issues or questions, refer to:
- Implementation Plan: `implementation_plan.md`
- Test Results: `tests/streamer-updates-playwright.spec.ts`
