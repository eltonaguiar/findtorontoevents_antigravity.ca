# FavCreators 500 on findtorontoevents.ca

## Fix applied (path /fc/)

We deployed FavCreators under **/fc/** instead of /favcreators/ so the host no longer returns 500. Use:

- **https://findtorontoevents.ca/fc/#/guest**
- **https://findtorontoevents.ca/findevents/fc/#/guest**

Main site nav links were updated to `/fc/#/guest`. Admin login (admin/admin) works at the same paths (api at /fc/api/login.php).

---

## What we saw (before fix)

- **https://findtorontoevents.ca/favcreators/#/guest** → 500 Internal Server Error  
- **https://findtorontoevents.ca/favcreators/docs/** → 500  
- **https://findtorontoevents.ca/findevents/favcreators/** → 500  
- **https://findtorontoevents.ca/findevents/favcreators/docs/index.html** → 500  

So **any** request that hits a URL path containing `favcreators` returns 500, including a direct request to a static file. The main site works: **https://findtorontoevents.ca/** and **https://findtorontoevents.ca/findevents/** return 200.

## What’s deployed

- FavCreators is deployed to:
  - `findtorontoevents.ca/favcreators/docs/` and `findtorontoevents.ca/favcreators/`
  - `findevents/favcreators/docs/` and `findevents/favcreators/`
- Root `.htaccess` (in repo) rewrites `/favcreators/` → `favcreators/docs/index.html` (used when the request is under the same base as that .htaccess).
- `favcreators/docs/.htaccess` sets `DirectoryIndex index.html` (and is deployed into both `favcreators/` and `favcreators/docs/`).

So the 500 is **not** from “served by docs vs not docs” or missing files; it happens for every `favcreators` path we tried.

## Likely cause

Something at **host/server level** is handling paths that contain `favcreators` (e.g. a global rule or handler for that folder name) and that handler is failing, producing 500. That could be:

- A server-wide or vhost `.htaccess` / mod_rewrite rule for `favcreators`
- A PHP or other handler bound to that path
- A security or “application” rule (e.g. ModSecurity or similar) for that directory name

## What to do

1. **Check server error logs**  
   Look at the Apache/PHP error log for the time of a request to  
   `https://findtorontoevents.ca/favcreators/` or  
   `https://findtorontoevents.ca/findevents/favcreators/docs/index.html`.  
   The log entry will show the real error (e.g. missing PHP extension, bad include, wrong path).

2. **Try a different path name**  
   If the host only treats the name `favcreators` specially, using another path can confirm that:
   - In `tools/deploy_to_ftp.py`, you could temporarily deploy the same app to a path like  
     `findtorontoevents.ca/fc/` (and `findevents/fc/`) and test  
     `https://findtorontoevents.ca/fc/#/guest` and  
     `https://findtorontoevents.ca/findevents/fc/#/guest`.  
   - The built app uses base `/favcreators/` for assets; for a different path you’d need a build with that base (e.g. `/fc/`) or the links from the main site would need to point to the new URL.

3. **Ask the host (50webs)**  
   Request that they:
   - Check why any request under a path containing `favcreators` returns 500.
   - Remove or fix the rule/handler for that path so static files (e.g. `index.html`, JS, CSS) under `favcreators` are served normally.

## Verify remote (main site)

Remote verification for the **main** site is passing:

```bash
npm run verify:remote
# Fallback: node tools/verify_remote_site_fallback.js
# Result: 3/3 checks (index, chunk, events.json) at https://findtorontoevents.ca
```

So the Toronto Events side is fine; only FavCreators paths are affected by the 500.
