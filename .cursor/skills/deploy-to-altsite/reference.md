# Deploy to Alternative Site — Technical Reference

## Architecture

The deployment pipeline has three phases:

```
[1. Stage]  →  [2. Upload]  →  [3. Verify]
   Copy all        FTP to         HTTP check
   files to        /target/       all pages
   temp dir        on server      return 200
   + rewrite                      + zero leaked
   domain refs                    domain refs
```

## File: `tools/deploy_to_altsite.py`

### Key Constants

| Constant | Purpose |
|----------|---------|
| `SOURCE_DOMAIN` | Domain to replace (`findtorontoevents.ca`) |
| `REWRITABLE_EXTENSIONS` | File suffixes that get text rewriting |
| `SKIP_PATTERNS` | Dirs/files excluded from staging |
| `WINDOWS_RESERVED` | Filenames that crash on Windows (nul, con, etc.) |
| `DEPLOY_COMPONENTS` | Master list of what gets deployed and where |

### DEPLOY_COMPONENTS Format

```python
# (local_path_relative_to_workspace, remote_path_relative_to_ftp_root, description)
("index.html",           "",             "Main site index"),       # file → root
("next/_next",           "next/_next",   "Next.js chunks"),        # dir → dir
("favcreators/docs",     "fc",           "FavCreators app"),       # dir → renamed dir
```

- **File entries**: source file is staged into `staging_dir/remote_path/filename`
- **Directory entries**: entire tree is walked and staged recursively
- **Order matters**: components are staged in listed order (last write wins on conflicts)

### Domain Rewriting Logic

`_rewrite_content(content, source, target)` applies these replacements in order:

1. `https://www.{source}` → `https://www.{target}`
2. `http://www.{source}` → `http://www.{target}`
3. `https://{source}` → `https://{target}`
4. `http://{source}` → `http://{target}`
5. `'{source}'` → `'{target}'` (JS string literals)
6. `"{source}"` → `"{target}"` (JS/JSON string literals)
7. `{source}` → `{target}` (catch-all for display text, comments, etc.)

The catch-all (#7) runs last so protocol-prefixed URLs aren't double-rewritten.

### What Gets Skipped

**Directories:**
- `.git`, `node_modules`, `__pycache__`, `.cursor`, `.github`
- `TORONTOEVENTS_ANTIGRAVITY`, `MOVIESHOWS*`, `DEPLOY`
- `favcreators_source`, `tests`, `playwright-report`, `test-results`

**Files:**
- `.env`, `package-lock.json`, `playwright.config.ts`
- Windows reserved names: `nul`, `con`, `prn`, `aux`, `com1`-`com9`, `lpt1`-`lpt9`

### FTP Upload Functions

| Function | Purpose |
|----------|---------|
| `_ensure_dir(ftp, path)` | Create remote dirs recursively |
| `_upload_tree(ftp, local, remote)` | Upload entire directory tree |
| `_upload_file(ftp, local, remote)` | Upload single file |
| `deploy_staged(ftp, staging, base)` | Deploy full staging dir to FTP |

## Remote Path Structure

After deployment, the FTP tree looks like:

```
/tdotevent.ca/
├── index.html              # Main events page
├── .htaccess               # Apache rewrite rules
├── events.json             # Events data
├── last_update.json        # Last update timestamp
├── next/
│   ├── events.json         # Events data (alternate location)
│   └── _next/
│       └── static/
│           └── chunks/     # Next.js JS chunks (70+ files)
├── _next/
│   └── static/
│       └── chunks/         # Alt Next.js chunks (57+ files)
├── fc/
│   ├── index.html          # FavCreators SPA
│   ├── assets/             # FavCreators CSS/JS bundles
│   ├── avatars/            # Creator avatars
│   └── api/                # PHP API (135+ files)
│       ├── config.php
│       ├── get_me.php
│       ├── discord_*.php
│       └── events_*.php
├── api/
│   ├── .htaccess
│   ├── google_auth.php
│   ├── google_callback.php
│   └── auth_db_config.php
├── stats/
│   └── index.html          # Stats dashboard
├── vr/
│   ├── index.html          # VR hub
│   ├── mobile-index.html
│   ├── events/index.html   # VR events zone
│   ├── movies.html         # VR movies zone
│   ├── creators.html       # VR creators zone
│   ├── stocks-zone.html    # VR stocks zone
│   ├── weather-zone.html   # VR weather zone
│   └── *.js                # VR scripts (50+ files)
└── findstocks/
    └── index.html          # FindStocks app
```

## Files That Contain Domain References

These files had `findtorontoevents.ca` references that get rewritten:

### HTML (critical)
- `index.html` — Schema.org, fcApi URLs, sign-in links, branding
- `findstocks/index.html` — branding text
- `vr/index.html`, `vr/events/index.html`, `vr/creators.html` — API URLs, links
- `vr/movies.html`, `vr/movies-tiktok.html` — IS_LIVE hostname check

### PHP (critical for API functionality)
- `favcreators/public/api/discord_*.php` — Discord bot response URLs (50+ refs)
- `favcreators/public/api/discord_unlink.php` — CORS header
- `favcreators/docs/api/discord_*.php` — Same as above (docs copy)
- `api/google_auth.php`, `api/google_callback.php` — OAuth redirect URLs

### JavaScript
- `vr/quick-wins-set7.js` — Share text
- `vr/quick-wins-substantial-set10.js` — iframe src
- `vr/server/start-servers.js` — Console banner text

### Data/Config
- `.htaccess` — Comment text (functional rules use relative paths)
- `stats/index.html` — mailto link
- `vr/server/package.json`, `vr/server/README.md` — metadata text

## Adding a New Sub-Application

When adding a new sub-app (e.g. `/newapp/`):

1. **Create the app** in the workspace (e.g. `newapp/` directory)
2. **Add to DEPLOY_COMPONENTS** in `tools/deploy_to_altsite.py`:
   ```python
   ("newapp",               "newapp",       "New App"),
   ```
3. **If the app has separate API files**, add those too:
   ```python
   ("newapp/api",           "newapp/api",   "New App API"),
   ```
4. **If it uses a new file extension**, add to REWRITABLE_EXTENSIONS
5. **Run deploy**: `python tools/deploy_to_altsite.py`
6. **Verify**: check `https://tdotevent.ca/newapp/` returns 200

The domain rewriting is automatic — any `findtorontoevents.ca` references in the new app's files will be replaced with the target domain.

## Database Considerations

The alternative site shares the same database as the main site (same hosting account). This means:
- FavCreators users, creators, events are shared
- Stats data is shared
- No separate database setup is needed

If you need separate databases for the alt site, you would need to:
1. Create new database credentials on the host
2. Update `fc/api/config.php` and `api/auth_db_config.php` in the staged files
3. Run setup endpoints: `https://tdotevent.ca/fc/api/ensure_tables.php`
