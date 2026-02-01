# tdotevent.ca redirect fix

**Problem:** The site was redirecting to  
`https://tdotevent.ca/services/users/z50websp3/ejaguiar1/www/tdotevent.ca/index.html`  
instead of loading at `https://tdotevent.ca/`.

**Cause:** The `.htaccess` on the server likely had `RewriteBase` set to the **filesystem path**  
(e.g. `RewriteBase /services/users/z50websp3/ejaguiar1/www/tdotevent.ca/`) instead of `/`.  
That makes Apache treat that path as the URL base, so redirects point to the wrong URL.

**Fix:**

1. Upload the `.htaccess` file from this folder to the **document root** of tdotevent.ca  
   (the same folder that contains `index.html`).
2. If you already have an `.htaccess` there, open it and ensure:
   - `RewriteBase /`  (just a slash — not the full server path)
   - Remove any line like `RewriteBase /services/users/.../tdotevent.ca/`
3. Save and test: `https://tdotevent.ca/` should load the homepage, not redirect to the long path.

The correct `.htaccess` in this folder uses `RewriteBase /` and includes a safety rule that redirects any accidental `/services/users/` URLs back to the site root.
