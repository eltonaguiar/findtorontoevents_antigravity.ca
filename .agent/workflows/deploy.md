---
description: How to deploy the application and what to check
---

# Deployment Workflow

The site uses **FTP** to deploy files to 3 domains. All domains serve the same content.

## Domains

| Domain | FTP Host | FTP User | Site Root Path |
|--------|----------|----------|---------------|
| **findtorontoevents.ca** | `ftps2.50webs.com` | `ejaguiar1` | `/findtorontoevents.ca/` |
| **tdotevent.ca** | (same or similar) | (same) | May vary |
| **torontoevent.net** | `$TORONTOEVENT_FTP_HOST` (GoDaddy) | `$TORONTOEVENT_FTP_USER` | `/` (root) |

## FTP Credentials

- Password is stored in environment variable `FTP_PASS` (for 50webs/findtorontoevents.ca)
- For torontoevent.net: `TORONTOEVENT_FTP_HOST`, `TORONTOEVENT_FTP_USER`, `TORONTOEVENT_FTP_PASS`
- **Never hardcode passwords.** Always use `os.getenv('FTP_PASS', '')`

## How to Deploy Files

### Quick Deploy (single file or directory)
// turbo-all

1. Use Python's `ftplib` to upload files. Example pattern from `deploy_updates.py`:

```python
import os, ftplib
from pathlib import Path

ftp = ftplib.FTP('ftps2.50webs.com', timeout=60)
ftp.login('ejaguiar1', os.getenv('FTP_PASS', ''))

# Site root is /findtorontoevents.ca/
# Local path maps: e:\findtorontoevents_antigravity.ca\foo\bar.html → /findtorontoevents.ca/foo/bar.html

# Create remote dirs if needed
def ensure_dir(ftp, path):
    ftp.cwd('/')
    for part in path.split('/'):
        if not part: continue
        try: ftp.cwd(part)
        except:
            ftp.mkd(part)
            ftp.cwd(part)

# Upload a file
def upload(ftp, local_path, remote_path):
    parts = remote_path.split('/')
    d = '/'.join(parts[:-1])
    if d: ensure_dir(ftp, d)
    ftp.cwd('/')
    if d: ftp.cwd(d)
    with open(local_path, 'rb') as f:
        ftp.storbinary(f'STOR {parts[-1]}', f)
    print(f'  📤 {remote_path}')

# Example: deploy dashboard
upload(ftp, 'KIMI_RISEOFTHECLAW/dashboard_live.html', 
       'findtorontoevents.ca/KIMI_RISEOFTHECLAW/dashboard_live.html')

ftp.quit()
```

### Existing Deploy Scripts

- `deploy_updates.py` — Deploys `updates/index.html` to 50webs
- `deploy_kimis_claw_production.py` — Deploys KIMI Rise of the Claw
- `favcreators/upload_to_ftp.py` — Deploys FavCreators
- GitHub Actions workflows in `.github/workflows/torontoevent-deploy-*.yml`

### Path Mapping

Local workspace path → Remote FTP path:
```
e:\findtorontoevents_antigravity.ca\  →  /findtorontoevents.ca/
```

Example:
```
Local:  e:\findtorontoevents_antigravity.ca\updates\index.html
Remote: /findtorontoevents.ca/updates/index.html
URL:    https://findtorontoevents.ca/updates/index.html
```

## Post-Deploy Verification

After deploying, ALWAYS verify the URL is live using `read_url_content` or a browser subagent before providing links to the user. Check for `200` status code and expected content.

### MANDATORY: JavaScript Error Check

**After EVERY deployment of an HTML/JS file, you MUST:**

1. Use a browser subagent to navigate to the deployed URL with a fresh cache-busting `?v=` parameter
2. Execute `window.__errors = []; window.onerror = function(m,s,l,c,e) { window.__errors.push({msg:m,src:s,line:l}); }; setTimeout(() => JSON.stringify(window.__errors), 3000);` OR capture console logs
3. Check for **any JavaScript errors** in the console output
4. If errors are found:
   - **DO NOT** tell the user the deployment is complete
   - Fix the JavaScript error locally
   - Re-deploy and re-check
   - Only declare success when 0 JS errors are found
5. Additionally verify the page renders correctly by checking:
   - Key DOM elements exist (e.g., `document.querySelectorAll('.live-pick-card').length`)
   - No blank/empty sections where content should appear
   - Data loads successfully (check console for `[Funds] Loaded` or similar)

**Example verification JS to run in browser:**
```javascript
// Run this after page loads (wait 3-5 seconds)
const errors = performance.getEntriesByType('resource').filter(r => r.responseStatus >= 400);
const hasContent = document.querySelector('#live-picks-container')?.children.length > 0;
const consoleLogs = []; // captured via console log capture tool
JSON.stringify({ resourceErrors: errors.length, hasContent, consoleLogs });
```

This rule exists because silent FTP failures and JS syntax errors have caused deployments to appear successful while serving broken pages. NEVER skip this step.

## GoDaddy FTP (Alternative Deployment Path)

Some files also need deployment to the GoDaddy-hosted `findtorontoevents.ca` server:
- **Host:** `162.210.101.36` (resolved from findtorontoevents.ca)
- **User:** `findtoro`
- **Password:** `os.getenv('FTP_PASS')`
- **Paths:** `/public_html/audit_dashboard/` and `/public_html/audit/`

Both the 50webs and GoDaddy paths may serve the same content. Always check which one the user's browser is hitting.

## Important Notes

- 50webs may have **ModSecurity** that blocks some requests (412 errors) — use a browser to verify if `read_url_content` fails
- Files are served immediately after FTP upload (no CDN cache delay)
- The `KIMI_RISEOFTHECLAW/` directory may need to be created on first deploy
- **Always use the correct FTP host for the domain being deployed to**
