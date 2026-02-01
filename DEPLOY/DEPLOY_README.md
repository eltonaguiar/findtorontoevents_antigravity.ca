# Deploy fix to findtorontoevents.ca (when FTP is broken)

This folder contains the **exact files** that fix the live error:
`js-proxy-v2.php?file=next/_next/static/chunks/a2ac3a6616d60872.js:19 Uncaught SyntaxError: Unexpected token '('`

The live server is still serving an old/broken chunk. Upload the contents of this folder to your **site root** (same folder as `index.html`).

---

## What to upload (and where)

| Local path (inside DEPLOY/) | Upload to (on server) |
|-----------------------------|------------------------|
| `js-proxy-v2.php` | **Site root** (next to index.html) |
| `next/_next/static/chunks/a2ac3a6616d60872.js` | **Site root** → `next/_next/static/chunks/` (create folders if missing) |
| `_next/static/chunks/a2ac3a6616d60872.js` | **Site root** → `_next/static/chunks/` (optional fallback) |
| `.htaccess` | **Site root** (only if you need to restore rewrite rules) |

Minimum required: **js-proxy-v2.php** + **next/_next/static/chunks/a2ac3a6616d60872.js**.

---

## When FTP is broken – other ways to deploy

### 1. cPanel File Manager (most hosts)
1. Log in to your hosting control panel (cPanel, Plesk, etc.).
2. Open **File Manager** → go to the site root (e.g. `public_html` or `www`).
3. **Upload** `js-proxy-v2.php` to the root (overwrite existing).
4. Go to `next/_next/static/chunks/` (create `next`, then `_next`, then `static`, then `chunks` if they don’t exist).
5. Upload `a2ac3a6616d60872.js` into `chunks/` (overwrite existing).
6. If the host has a “Clear cache” or “Purge cache” option, run it.

### 2. SSH / SFTP (if you have shell or SFTP access)
From your machine (in the folder that contains `DEPLOY`):

```bash
# SFTP – upload entire DEPLOY structure
sftp your-user@findtorontoevents.ca
cd public_html   # or your docroot
put -r DEPLOY/* .
quit
```

Or with **rsync** (replace `your-user` and path):

```bash
rsync -avz --relative DEPLOY/./js-proxy-v2.php DEPLOY/./next DEPLOY/./_next your-user@findtorontoevents.ca:public_html/
```

(Adjust `public_html` to your actual document root.)

### 3. Zip and extract on server
1. Zip the **contents** of `DEPLOY` (so that inside the zip you have `js-proxy-v2.php`, `next/`, `_next/`, `.htaccess`).
2. In cPanel File Manager, go to site root and **Upload** the zip.
3. Right‑click the zip → **Extract** (overwrite when asked).
4. Delete the zip after extraction.

### 4. Git (if the site is deployed from a repo)
If the server pulls from GitHub/GitLab:

1. Commit and push the fixed files from your repo (including `js-proxy-v2.php` and the chunk under `next/_next/static/chunks/`).
2. On the server, run `git pull` (or use the host’s “Deploy from Git” / “Pull” button).
3. Clear any server or CDN cache.

### 5. Host support
If you can’t get in at all, ask your host to:
- Replace the file at `next/_next/static/chunks/a2ac3a6616d60872.js` with your fixed version (you can send them the file from this DEPLOY folder).
- Replace `js-proxy-v2.php` in the site root with the version from this DEPLOY folder.

---

## After uploading

1. **Hard refresh** the site: https://findtorontoevents.ca/index.html (Ctrl+Shift+R or Cmd+Shift+R).
2. If the host has **caching** (e.g. LiteSpeed Cache, Cloudflare), purge cache for the site or at least for `*.js` and the proxy URL.
3. Check the browser console; the `Unexpected token '('` error should be gone.

---

## Why this fixes it

- **js-proxy-v2.php** – Serves the chunk from disk with no PHP notices/warnings in the output (so the response is pure JS).
- **a2ac3a6616d60872.js** – Fixed chunk (valid JS, no syntax error at line 19). The live server currently has an old/broken copy; replacing it with this file removes the error.
