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
- [ ] Add automated content refresh cron job
- [ ] Implement push notifications (future enhancement)

## Support

For issues or questions, refer to:
- Implementation Plan: `implementation_plan.md`
- Test Results: `tests/streamer-updates-playwright.spec.ts`
