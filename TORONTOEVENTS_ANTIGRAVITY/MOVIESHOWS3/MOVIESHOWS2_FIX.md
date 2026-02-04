# MOVIESHOWS2 Redirect Issue - FIXED ✅

## Issue Reported
`/findtorontoevents.ca/movieshows2` was redirecting to a capital name (`/MOVIESHOWS2`) which doesn't exist, resulting in 404 errors.

## Root Cause
When I added case-insensitive redirect rules for MOVIESHOWS3, I mistakenly also added the same redirect pattern for MOVIESHOWS2:

```apache
# INCORRECT - This was breaking MOVIESHOWS2
RewriteCond %{REQUEST_URI} ^/movieshows2(/.*)?$ [NC]
RewriteCond %{REQUEST_URI} !^/MOVIESHOWS2(/.*)?$
RewriteRule ^movieshows2(/.*)?$ /MOVIESHOWS2$1 [R=301,L]
```

**The problem:** MOVIESHOWS2 directory is actually named `movieshows2` (lowercase) on the server, not `MOVIESHOWS2` (uppercase). The redirect was trying to send users to a non-existent uppercase directory.

## Solution
Removed the MOVIESHOWS2 redirect rules from the root `.htaccess` file, keeping only the MOVIESHOWS3 redirect (which was the original request):

```apache
# CORRECT - Only redirect MOVIESHOWS3
RewriteCond %{REQUEST_URI} ^/movieshows3(/.*)?$ [NC]
RewriteCond %{REQUEST_URI} !^/MOVIESHOWS3(/.*)?$
RewriteRule ^movieshows3(/.*)?$ /MOVIESHOWS3$1 [R=301,L]
```

## Key Differences
- **MOVIESHOWS2:** Directory is lowercase (`movieshows2`) - no redirect needed
- **MOVIESHOWS3:** Directory is uppercase (`MOVIESHOWS3`) - redirect needed for lowercase URLs

## Deployment
- **File Modified:** `server_htaccess` (root `.htaccess`)
- **Deployed:** Successfully uploaded to `/findtorontoevents.ca/.htaccess`
- **Status:** ✅ LIVE

## Testing Results
✅ `https://findtorontoevents.ca/movieshows2/?t=456` - **Working** (with cache-buster)  
⚠️ `https://findtorontoevents.ca/movieshows2/` - **Cached redirect** (will clear in 24-48 hours)

## Browser Cache Note
Users who visited `/movieshows2/` before the fix may still see the 404 error due to cached 301 redirects. Solutions:
1. **Wait:** Cache will expire in 24-48 hours
2. **Clear browser cache:** Force refresh with Ctrl+Shift+R or clear browsing data
3. **Use cache-buster:** Add `?t=123` to the URL temporarily

## Verification
The browser test confirmed:
- MOVIESHOWS2 loads correctly with cache-busting parameter
- Page content displays properly (Avatar: Fire and Ash, etc.)
- No redirect errors when cache is bypassed
- The actual directory name is `movieshows2` (lowercase)

## Apology
Sorry for the confusion! I should have verified the actual directory names on the server before adding redirect rules for MOVIESHOWS2. The fix is now deployed and working correctly.
