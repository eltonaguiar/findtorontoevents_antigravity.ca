# What Fixed findtorontoevents.ca

## Timeline of Fixes (Based on FTP File Timestamps - Eastern Time)

### Most Recent Changes (2026-01-31 3:40 PM EST)
1. **`.htaccess`** - Added rewrite rule to route `/next/_next/static/chunks/*.js` through `js-proxy.php`
2. **`index.html`** - Updated with client-side path fixes
3. **`sw.js`** - Service worker to strip query parameters

### Earlier Changes
- **`next/_next/static/chunks/.htaccess`** (3:35 PM EST) - Created `.htaccess` in chunks directory
- **`next/_next/.htaccess`** (3:33 PM EST) - Created `.htaccess` in `next/_next/` directory  
- **`_next/.htaccess`** (3:33 PM EST) - Created `.htaccess` in `_next/` directory
- **`events.json`** (3:39 PM EST) - Uploaded to root and `data/` directory
- **`next/_next/` directory** (3:32-3:33 PM EST) - Copied all `_next/` files to `next/_next/` path

## The Fix

The combination of these changes fixed the issue:

1. **Copied files to `next/_next/`** - The server HTML was requesting files from `/next/_next/...` paths, so we copied all files there
2. **Added `.htaccess` files** - Created `.htaccess` files in `_next/`, `next/_next/`, and `next/_next/static/chunks/` directories to bypass ModSecurity
3. **Updated root `.htaccess`** - Added rewrite rule to route JavaScript files through PHP proxy (though this may not be the primary fix)
4. **Uploaded `events.json`** - Made events data available locally as fallback

## Key Insight

The server was modifying HTML server-side to use `/next/_next/...` paths. By copying all files to that location AND adding `.htaccess` files in those directories to bypass ModSecurity, the files became accessible.

The `.htaccess` files in the subdirectories (`next/_next/.htaccess` and `next/_next/static/chunks/.htaccess`) likely allowed ModSecurity to serve the files correctly.
