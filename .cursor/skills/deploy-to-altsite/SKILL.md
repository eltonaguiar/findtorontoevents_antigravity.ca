---
name: deploy-to-altsite
description: Deploy the full site to an alternative domain (e.g. tdotevent.ca) via FTP with automatic path rewriting so the alt site is fully independent. Stages all components, rewrites hardcoded domain references, uploads via FTP, and verifies.
---

# Deploy to Alternative Site

Use this skill when the user asks to **deploy to tdotevent.ca**, **deploy to the alternative site**, **mirror the site to another domain**, **sync changes to the alt site**, or **update tdotevent.ca**.

## Overview

This skill deploys the entire findtorontoevents.ca project to an alternative FTP path (default: `/tdotevent.ca/`) with automatic domain rewriting so the alternative site is **fully independent** — no references leak back to the source domain.

**What gets deployed** (all components):
- Main site: `index.html`, `.htaccess`, `events.json`, `last_update.json`
- Next.js chunks: `next/_next/`, `_next/`
- FavCreators app: `favcreators/docs/` → `fc/`
- FavCreators API: `favcreators/public/api/` → `fc/api/`
- Events API: `api/events/` → `fc/events-api/`
- Auth API: `api/google_auth.php`, `api/google_callback.php`, `api/auth_db_config.php`
- Stats dashboard: `stats/`
- VR experience: `vr/`
- FindStocks: `findstocks/`

**What gets rewritten** in all text-based files (.html, .php, .js, .css, .json, .md, etc.):
- `https://findtorontoevents.ca` → `https://<target>`
- `https://www.findtorontoevents.ca` → `https://www.<target>`
- `hostname === 'findtorontoevents.ca'` → `hostname === '<target>'`
- Display text and branding references

## 1. Prerequisites

### FTP Credentials

The script reads from **Windows environment variables** (or `.env` file):

| Variable       | Description              | Required |
|----------------|--------------------------|----------|
| `FTP_SERVER`   | FTP hostname             | Yes      |
| `FTP_PASS`     | FTP password             | Yes      |
| `FTP_USER`     | FTP username             | Yes (from .env or env) |

The FTP remote path is **not** `FTP_REMOTE_PATH` — it is derived from the target domain name. For `tdotevent.ca`, the FTP path is `/tdotevent.ca/`.

If credentials are missing, remind the user:
```powershell
$env:FTP_SERVER = "ftps2.50webs.com"
$env:FTP_USER = "your_user"
$env:FTP_PASS = "your_password"
```

## 2. Deploy Command

### Default (tdotevent.ca)

```bash
python tools/deploy_to_altsite.py
```

### With explicit target

```bash
python tools/deploy_to_altsite.py --target tdotevent.ca
```

### Dry run (stage files but don't upload)

```bash
python tools/deploy_to_altsite.py --dry-run --keep-staging
```

### Custom FTP path

```bash
python tools/deploy_to_altsite.py --target example.ca --ftp-path example.ca
```

## 3. Workflow

1. **Run the deploy script** — it handles everything automatically:
   - Creates a temporary staging directory
   - Copies all deployable components
   - Rewrites `findtorontoevents.ca` → target domain in all text files
   - Skips non-deployable dirs (node_modules, .git, tests, TORONTOEVENTS_ANTIGRAVITY, etc.)
   - Skips Windows-reserved filenames (nul, con, prn, etc.)
   - Uploads the entire staged tree to `/<target>/` on FTP
   - Cleans up the staging directory

2. **Verify the deployment** — after deploy, check all key pages:

```python
import urllib.request
urls = [
    "https://tdotevent.ca/",
    "https://tdotevent.ca/events.json",
    "https://tdotevent.ca/fc/",
    "https://tdotevent.ca/stats/",
    "https://tdotevent.ca/vr/",
    "https://tdotevent.ca/findstocks/",
]
for url in urls:
    try:
        resp = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=15)
        print(f"  {url} -> {resp.getcode()} ({len(resp.read()):,} bytes)")
    except Exception as e:
        print(f"  {url} -> ERROR: {e}")
```

3. **Check for leaked references** — verify no `findtorontoevents.ca` references remain:

```python
import urllib.request
html = urllib.request.urlopen(
    urllib.request.Request("https://tdotevent.ca/", headers={"User-Agent": "Mozilla/5.0"}), timeout=15
).read().decode("utf-8", errors="ignore")
old_count = html.count("findtorontoevents.ca")
new_count = html.count("tdotevent.ca")
print(f"Old refs: {old_count}, New refs: {new_count}")
assert old_count == 0, f"LEAKED: {old_count} old domain references found!"
```

## 4. Adding New Components

When new functionality is added to the project, update `DEPLOY_COMPONENTS` in `tools/deploy_to_altsite.py`:

```python
DEPLOY_COMPONENTS = [
    # Existing components...
    
    # Add new component:
    # (local_relative_path, remote_relative_path, description)
    ("new-app",              "new-app",      "New App Name"),
    ("new-app/api",          "new-app/api",  "New App API"),
]
```

**Rules for new components:**
- Files: use `("path/to/file.ext", "remote/dir", "Description")` — file goes into remote dir
- Directories: use `("path/to/dir", "remote/dir", "Description")` — entire tree is uploaded
- All text files are automatically rewritten (domain refs replaced)
- Binary files (images, fonts) are copied as-is
- The script automatically creates remote directories as needed

### Adding new file types for rewriting

If a new file extension should have domain references rewritten, add it to `REWRITABLE_EXTENSIONS`:

```python
REWRITABLE_EXTENSIONS = {
    ".html", ".htm", ".php", ".js", ... ".newext",
}
```

## 5. Troubleshooting

| Issue | Solution |
|-------|----------|
| `WinError 87: The parameter is incorrect` | A file has a Windows-reserved name (nul, con, prn). Already handled by WINDOWS_RESERVED skip list. |
| `553 Can't open that file: Is a directory` | FTP server has a directory where a file is expected. Non-critical; the file's parent dir contents still upload. |
| Domain references leaked | Check if the file extension is in REWRITABLE_EXTENSIONS. Add it if missing. |
| FTP credentials missing | Set `FTP_SERVER`, `FTP_USER`, `FTP_PASS` in environment or `.env` file. |
| New component not deploying | Add it to DEPLOY_COMPONENTS in `tools/deploy_to_altsite.py`. |

## 6. Script Location and CLI Reference

- **Script:** `tools/deploy_to_altsite.py`
- **Default target:** `tdotevent.ca`
- **Default FTP path:** `/<target>/` (e.g. `/tdotevent.ca/`)

```
python tools/deploy_to_altsite.py [OPTIONS]

Options:
  --target DOMAIN    Target domain (default: tdotevent.ca)
  --source DOMAIN    Source domain to replace (default: findtorontoevents.ca)
  --ftp-path PATH    FTP remote path (default: same as target)
  --dry-run          Stage files but don't upload
  --keep-staging     Keep staging directory after deploy
```

## 7. Checklist

- [ ] FTP credentials set (`FTP_SERVER`, `FTP_USER`, `FTP_PASS`)
- [ ] Run: `python tools/deploy_to_altsite.py`
- [ ] All components staged and uploaded (check output for errors)
- [ ] Verify key pages return 200 (main, events.json, fc, stats, vr, findstocks)
- [ ] Verify zero leaked `findtorontoevents.ca` references in served HTML
- [ ] If new components were added: update DEPLOY_COMPONENTS list first
