#!/usr/bin/env python3
"""
Full-sync FTP deploy: uploads ALL modified and new project files.

Maps local paths to remote FTP paths under /findtorontoevents.ca/.
Uses FTP_TLS for secure transfer.

Uses environment variables:
  FTP_SERVER  - FTP hostname
  FTP_USER    - FTP username
  FTP_PASS    - FTP password

Run from project root:
  python tools/deploy_full_sync.py
"""
import os
import sys
import time
from ftplib import FTP_TLS, error_perm
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE = _SCRIPT_DIR.parent
REMOTE_ROOT = 'findtorontoevents.ca'

# ─── FTP Credentials ─────────────────────────────────────────
_env_file = WORKSPACE / '.env'
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, _, v = line.partition('=')
            k, v = k.strip(), v.strip()
            if k and os.environ.get(k) in (None, ''):
                os.environ.setdefault(k, v)
    if 'FTP_SERVER' not in os.environ and os.environ.get('FTP_HOST'):
        os.environ['FTP_SERVER'] = os.environ['FTP_HOST']

FTP_SERVER = os.environ.get('FTP_SERVER', '').strip()
FTP_USER = os.environ.get('FTP_USER', '').strip()
FTP_PASS = os.environ.get('FTP_PASS', '').strip()

# ─── Skip Patterns ───────────────────────────────────────────
SKIP_PREFIXES = [
    '.github/', '.claude/', '.git/', '.vs/', '.vscode/', '.cursor/',
    'tools/', 'tests/', 'scripts/', 'server/', 'src/',
    'node_modules/', 'backups/', 'ContentCreation/', 'test-results/',
    'data/', 'favcreators/src/', 'favcreators/server/',
    'favcreators/tests/', 'favcreators/node_modules/',
]
SKIP_PATTERNS = [
    'temp_', 'tmp_', 'KIMI_', 'VISUAL_', 'MULTI_', 'SUPPLEMENTAL_',
    'NAV_MENU_BACKUP', '.backup', '.bak',
]
SKIP_FILES = {
    '.gitignore', '.env', '.env.local', '.env.events',
    'package.json', 'package-lock.json', 'tsconfig.json',
    'playwright.config.ts', 'playwright.config.js',
    'verify_templates.js', 'generate_blog_templates.js',
    'index6.html',  # dev scratch
    'important.txt',
}
SKIP_EXTENSIONS = {
    '.md', '.log', '.zip', '.jsonl', '.pyc', '.suo', '.sln',
    '.njsproj', '.ntvs_', '.sw', '.swp',
    '.spec.ts', '.spec.js', '.test.ts', '.test.js',
    '.py',  # Python scripts stay local
}

# ─── Path Mapping ────────────────────────────────────────────
def map_to_remote(rel_path):
    """Map a local relative path to its FTP remote path under REMOTE_ROOT."""
    r = rel_path.replace('\\', '/')

    # Blog build directory → /blog/
    if r.startswith('TORONTOEVENTS_ANTIGRAVITY/build/blog/'):
        return r.replace('TORONTOEVENTS_ANTIGRAVITY/build/blog/', 'blog/')

    # TORONTOEVENTS_ANTIGRAVITY/_next/ → /_next/
    if r.startswith('TORONTOEVENTS_ANTIGRAVITY/_next/'):
        return r.replace('TORONTOEVENTS_ANTIGRAVITY/', '')

    # TORONTOEVENTS_ANTIGRAVITY/next/ → /next/
    if r.startswith('TORONTOEVENTS_ANTIGRAVITY/next/'):
        return r.replace('TORONTOEVENTS_ANTIGRAVITY/', '')

    # TORONTOEVENTS_ANTIGRAVITY/index.html → /TORONTOEVENTS_ANTIGRAVITY/index.html
    if r.startswith('TORONTOEVENTS_ANTIGRAVITY/'):
        # Skip non-deployable TA files
        if any(r.endswith(ext) for ext in ('.js.backup', '.config.js')):
            return None
        if '/tests/' in r:
            return None
        return r

    # FavCreators docs → /fc/
    if r.startswith('favcreators/docs/'):
        return r.replace('favcreators/docs/', 'fc/')

    # FavCreators public API → /fc/api/
    if r.startswith('favcreators/public/api/'):
        return r.replace('favcreators/public/api/', 'fc/api/')

    # FavCreators public non-api → /fc/
    if r.startswith('favcreators/public/'):
        return r.replace('favcreators/public/', 'fc/')

    # Root blog200-249 and blog300-349 HTML files → /blog/
    if r.startswith('blog') and r.endswith('.html'):
        return 'blog/' + r

    # Direct-mapped directories
    direct_dirs = [
        'live-monitor/', 'deals/', 'news/', 'updates/', 'weather/',
        'vr/', 'WINDOWSFIXER/', 'goldmine_cursor/', 'MOVIESHOWS/',
        'findstocks/', 'findforex2/', 'findcryptopairs/', 'investments/',
        'FIGHTGAME/', 'stats/', '_next/', 'next/', 'api/', 'images/',
    ]
    for d in direct_dirs:
        if r.startswith(d):
            return r

    # Root-level files
    root_deploy_files = {
        'index.html', 'sitemap.xml', 'robots.txt', '.htaccess',
        'events.json', 'last_update.json', 'ai-assistant.js',
        'theme-switcher.js', 'theme-registry.js', 'theme-animations.js',
        'blog_styles_common.css', 'blog_template_base.js',
    }
    if r in root_deploy_files:
        return r

    return None


def should_skip(rel_path):
    """Return True if this file should NOT be deployed."""
    r = rel_path.replace('\\', '/')
    name = os.path.basename(r)

    if name in SKIP_FILES:
        return True

    for prefix in SKIP_PREFIXES:
        if r.startswith(prefix):
            return True

    for pat in SKIP_PATTERNS:
        if pat in name:
            return True

    _, ext = os.path.splitext(name)
    if ext in SKIP_EXTENSIONS:
        return True

    return False


# ─── FTP Helpers ─────────────────────────────────────────────
def ensure_dir(ftp, path):
    """Ensure remote directory exists, creating parents as needed."""
    parts = path.strip('/').split('/')
    current = ''
    for part in parts:
        if not part:
            continue
        current += '/' + part
        try:
            ftp.cwd(current)
        except error_perm:
            try:
                ftp.mkd(current)
                ftp.cwd(current)
            except Exception:
                pass


def upload_file(ftp, local_path, remote_path):
    """Upload a single file to FTP."""
    full_remote = '/' + REMOTE_ROOT + '/' + remote_path.lstrip('/')
    remote_dir = '/'.join(full_remote.split('/')[:-1])
    remote_name = full_remote.split('/')[-1]

    try:
        ftp.cwd('/')
        ensure_dir(ftp, remote_dir.lstrip('/'))
        ftp.cwd(remote_dir)
        with open(local_path, 'rb') as f:
            ftp.storbinary('STOR ' + remote_name, f)
        return True
    except Exception as e:
        print(f'  ERROR: {remote_path} -> {e}')
        return False


# ─── Main ────────────────────────────────────────────────────
def collect_files():
    """Collect all deployable files from the workspace."""
    files = []

    for root, dirs, filenames in os.walk(WORKSPACE):
        # Skip hidden/excluded dirs
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != 'node_modules'
                   and d != '__pycache__' and d != 'test-results' and d != 'backups'
                   and d != 'ContentCreation' and d != 'tmp' and d != 'temp']

        for name in filenames:
            local_path = Path(root) / name
            try:
                rel = str(local_path.relative_to(WORKSPACE)).replace('\\', '/')
            except ValueError:
                continue

            if should_skip(rel):
                continue

            remote = map_to_remote(rel)
            if remote:
                files.append((str(local_path), remote))

    return files


def main():
    if not all([FTP_SERVER, FTP_USER, FTP_PASS]):
        print('ERROR: Set FTP_SERVER, FTP_USER, FTP_PASS environment variables.')
        sys.exit(1)

    print('Collecting files to deploy...')
    files = collect_files()
    print(f'Found {len(files)} files to deploy.\n')

    if not files:
        print('No files to deploy.')
        return

    # Group by directory for display
    dirs = {}
    for local, remote in files:
        d = remote.split('/')[0] if '/' in remote else '(root)'
        dirs[d] = dirs.get(d, 0) + 1
    print('Breakdown by area:')
    for d in sorted(dirs.keys()):
        print(f'  {d}: {dirs[d]} files')
    print()

    try:
        print(f'Connecting to {FTP_SERVER}...')
        ftp = FTP_TLS(FTP_SERVER)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.prot_p()
        ftp.set_pasv(True)
        print('Connected via FTP_TLS.\n')

        uploaded = 0
        errors = 0
        start = time.time()

        for i, (local_path, remote_path) in enumerate(files, 1):
            if upload_file(ftp, local_path, remote_path):
                uploaded += 1
                if uploaded % 25 == 0 or i == len(files):
                    print(f'  [{i}/{len(files)}] {uploaded} uploaded...')
            else:
                errors += 1
                # Retry once after short pause
                time.sleep(0.5)
                try:
                    ftp.cwd('/')
                except Exception:
                    # Reconnect
                    try:
                        ftp.quit()
                    except Exception:
                        pass
                    ftp = FTP_TLS(FTP_SERVER)
                    ftp.login(FTP_USER, FTP_PASS)
                    ftp.prot_p()
                    ftp.set_pasv(True)
                    print('  (reconnected)')

                if upload_file(ftp, local_path, remote_path):
                    uploaded += 1
                    errors -= 1

        elapsed = time.time() - start
        print(f'\nDeploy complete: {uploaded} uploaded, {errors} errors ({int(elapsed)}s)')

        ftp.quit()

    except Exception as e:
        print(f'\nDeploy FAILED: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
