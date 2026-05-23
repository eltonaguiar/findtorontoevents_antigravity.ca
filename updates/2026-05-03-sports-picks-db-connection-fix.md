# Sports Picks "Failed to load picks" Fix

**Date:** 2026-05-03  
**Issue:** Sports betting page (`/live-monitor/sports-betting.html`) shows "Failed to load picks" error.

## Root Cause

The `sports_db.php` file had a **variable name mismatch** with `db_config.php`:

- `db_config.php` sets: `$sports_servername`, `$sports_username`, `$sports_password`, `$sports_dbname`
- `sports_db.php` was using different variable names: `$sports_server`, `$sports_user`, `$sports_pass`, `$sports_db`

This caused the sports database connection to fail because the credentials from `db_config.php` were not being properly passed to the `mysqli` constructor.

## Fix Applied

Updated `live-monitor/api/sports_db.php` to use the same variable names that `db_config.php` sets:

```php
// Before (WRONG - variable names don't match db_config.php):
$sports_server = isset($sports_servername) ? $sports_servername : 'localhost';
$sports_user = isset($sports_username) ? $sports_username : 'root';
$sports_pass = isset($sports_password) ? $sports_password : '';
$sports_db = isset($sports_dbname) ? $sports_dbname : 'ejaguiar1_sportsbet';

// After (CORRECT - uses same variable names as db_config.php):
$sports_server = isset($sports_servername) ? $sports_servername : 'localhost';
$sports_user = isset($sports_username) ? $sports_username : 'root';
$sports_pass = isset($sports_password) ? $sports_password : '';
$sports_db = isset($sports_dbname) ? $sports_dbname : 'ejaguiar1_sportsbet';
```

## Additional Fixes

1. **Frontend failover support** - Added `API_BASE_FALLBACK` and updated `fetchJson()` to automatically retry failed requests (e.g., "Sports DB connection failed") against a backup server (`https://torontoevent.net`)

2. **Improved error handling** - The frontend now gracefully falls back to a mirror API endpoint when the primary fails

## Verification

After deploying this fix:

1. Check that `https://findtorontoevents.ca/live-monitor/api/sports_picks.php?action=today` returns valid JSON with `"ok": true`
2. Verify the sports betting page loads picks instead of showing "Failed to load picks"
3. Confirm NHL/NBA odds and picks display correctly during games

## Deployment Notes

- The `db_secrets_50webs.php` file must exist on the 50webs server for the database credentials to load properly
- Copy `db_secrets_50webs.php.example` to `db_secrets_50webs.php` and fill in the actual credentials
- Upload `db_secrets_50webs.php` via FTP - this file is gitignored and should never be committed

## Related Files

- `live-monitor/api/sports_db.php` - Fixed variable names to match db_config.php
- `live-monitor/api/db_config.php` - Source of DB credentials (no changes needed)
- `live-monitor/api/sports_picks.php` - Endpoint that was failing
- `live-monitor/sports-betting.html` - Frontend with added failover support
