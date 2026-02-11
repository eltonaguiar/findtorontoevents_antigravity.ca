#!/usr/bin/env python3
"""
Deploy full mirror of findtorontoevents.ca to tdotevent.ca via FTP_TLS.

Stages all site files into a temp directory with domain replacements
(findtorontoevents.ca -> tdotevent.ca) then uploads via FTP_TLS.

Same databases, same hosting account, different domain.

Uses Windows user environment variables:
  FTP_SERVER  - FTP hostname
  FTP_USER    - FTP username
  FTP_PASS    - FTP password

Run from project root:
  python tools/deploy_to_tdotevent.py
"""
import os
import sys
import time
import tempfile
import shutil
from ftplib import FTP_TLS, error_perm
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE = _SCRIPT_DIR.parent

# ─── FTP Config ───────────────────────────────────────────────
FTP_SERVER = os.environ.get('FTP_SERVER', '').strip()
FTP_USER = os.environ.get('FTP_USER', '').strip()
FTP_PASS = os.environ.get('FTP_PASS', '').strip()
REMOTE_ROOT = 'tdotevent.ca'

# ─── Domain Replacements (order: most specific first) ────────
REPLACEMENTS = [
    ('www.findtorontoevents.ca', 'www.tdotevent.ca'),
    ('www.FindTorontoEvents.ca', 'www.tdotevent.ca'),
    ('support@findtorontoevents.ca', 'support@tdotevent.ca'),
    ('contact@findtorontoevents.ca', 'contact@tdotevent.ca'),
    ('FindTorontoEvents.ca', 'TdotEvent.ca'),
    ('findtorontoevents.ca', 'tdotevent.ca'),
    ('FindTorontoEvents', 'TdotEvent'),
]

# GitHub raw URL must NOT be replaced (events.json fallback)
GITHUB_RAW_MARKER = 'raw.githubusercontent.com/eltonaguiar/findtorontoevents.ca'
GITHUB_PLACEHOLDER = '___GITHUB_RAW_PRESERVE___'

# Text file extensions eligible for domain replacement
TEXT_EXTENSIONS = {
    '.html', '.htm', '.js', '.css', '.json', '.php',
    '.txt', '.md', '.xml', '.ics', '.svg',
}

# OAuth files: skip domain replacement (auth routes through main site)
OAUTH_SKIP_FILES = {
    'google_auth.php', 'google_callback.php',
    'discord_config.php', 'discord_callback.php', 'discord_auth.php',
}

# ─── Directory Manifest ──────────────────────────────────────
# (source_relative_path, remote_relative_path)
DIRS_TO_DEPLOY = [
    ('next/_next', 'next/_next'),
    ('_next', '_next'),
    ('favcreators/docs', 'fc'),
    ('favcreators/public/api', 'fc/api'),
    ('api', 'api'),
    ('news', 'news'),
    ('deals', 'deals'),
    ('updates', 'updates'),
    ('weather', 'weather'),
    ('vr', 'vr'),
    ('stats', 'stats'),
    ('live-monitor', 'live-monitor'),
    ('findstocks', 'findstocks'),
    ('investments', 'investments'),
    ('MOVIESHOWS', 'MOVIESHOWS'),
    ('TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS2', 'movieshows2'),
    ('TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3', 'MOVIESHOWS3'),
    ('CONTACTLENSES', 'CONTACTLENSES'),
    ('daily-feed', 'daily-feed'),
    ('gotjob', 'gotjob'),
    ('WINDOWSFIXER', 'WINDOWSFIXER'),
    ('MENTALHEALTHRESOURCES', 'MENTALHEALTHRESOURCES'),
    ('2xko', '2xko'),
    ('findcryptopairs', 'findcryptopairs'),
    ('findforex2', 'findforex2'),
    ('findmutualfunds', 'findmutualfunds'),
    ('findmutualfunds2', 'findmutualfunds2'),
    ('data', 'data'),
    ('images', 'images'),
    ('alpha_engine', 'alpha_engine'),
    ('affiliates', 'affiliates'),
    ('luxcal', 'luxcal'),
    ('404', '404'),
    ('TORONTOEVENTS_ANTIGRAVITY/build/blog', 'blog'),
    ('TORONTOEVENTS_ANTIGRAVITY/_next', '_next'),
    ('TORONTOEVENTS_ANTIGRAVITY/next/_next', 'next/_next'),
    ('goldmine_cursor', 'goldmine_cursor'),
    ('FIGHTGAME', 'FIGHTGAME'),
]

# Single root files
FILES_TO_DEPLOY = [
    ('index.html', 'index.html'),
    ('.htaccess', '.htaccess'),
    ('events.json', 'events.json'),
    ('events.json', 'next/events.json'),
    ('last_update.json', 'last_update.json'),
    ('favicon.ico', 'favicon.ico'),
    ('ai-assistant.js', 'ai-assistant.js'),
    ('sitemap.xml', 'sitemap.xml'),
    ('robots.txt', 'robots.txt'),
    ('theme-switcher.js', 'theme-switcher.js'),
    ('theme-registry.js', 'theme-registry.js'),
    ('theme-animations.js', 'theme-animations.js'),
    ('blog_styles_common.css', 'blog_styles_common.css'),
    ('blog_template_base.js', 'blog_template_base.js'),
]

# Root-level blog HTML files (blog200-249, blog300-349) → /blog/
ROOT_BLOG_FILES = []
import glob as _glob
for _p in _glob.glob(str(WORKSPACE / 'blog*.html')):
    _name = os.path.basename(_p)
    ROOT_BLOG_FILES.append((_name, 'blog/' + _name))

# Directories to skip during walk (anywhere in tree)
SKIP_DIR_NAMES = {
    'node_modules', '.git', 'tests', 'test-results', 'screenshots',
    '__pycache__', '.cursor', '.vscode', '.vs', '.idea',
    'src',  # Skip source dirs inside favcreators/docs (only built output)
}

# File patterns to skip
SKIP_FILE_SUFFIXES = {'.log', '.zip', '.sql', '.bak', '.spec.ts', '.pyc'}
SKIP_FILE_NAMES = {'nul', '.gitignore', '.gitkeep', 'package-lock.json'}


# ─── Domain Replacement ──────────────────────────────────────

def replace_domains(content):
    """Replace findtorontoevents.ca -> tdotevent.ca, preserving GitHub raw URLs."""
    # Protect GitHub raw URL from replacement
    content = content.replace(GITHUB_RAW_MARKER, GITHUB_PLACEHOLDER)
    # Apply all replacements
    for old, new in REPLACEMENTS:
        content = content.replace(old, new)
    # Restore GitHub raw URL
    content = content.replace(GITHUB_PLACEHOLDER, GITHUB_RAW_MARKER)
    return content


def should_skip_file(file_path):
    """Check if a file should be skipped."""
    name = file_path.name
    suffix = file_path.suffix.lower()
    if name in SKIP_FILE_NAMES:
        return True
    if suffix in SKIP_FILE_SUFFIXES:
        return True
    return False


def process_file(src_path, dst_path, do_replacement=True):
    """Copy file to staging, optionally replacing domain references."""
    dst_path.parent.mkdir(parents=True, exist_ok=True)

    if should_skip_file(src_path):
        return False

    # Check if this is an OAuth file that should skip replacement
    skip_replace = src_path.name in OAUTH_SKIP_FILES

    if do_replacement and not skip_replace and src_path.suffix.lower() in TEXT_EXTENSIONS:
        try:
            content = src_path.read_text(encoding='utf-8', errors='replace')
            content = replace_domains(content)
            dst_path.write_text(content, encoding='utf-8')
            return True
        except Exception:
            # Fall through to binary copy
            pass

    shutil.copy2(src_path, dst_path)
    return True


# ─── og:image Injection ──────────────────────────────────────

OG_IMAGE_TAGS = (
    '<meta property="og:image" content="https://tdotevent.ca/images/Toronto%20Events.jpg">'
    '<meta property="og:image:width" content="800">'
    '<meta property="og:image:height" content="600">'
    '<meta name="twitter:image" content="https://tdotevent.ca/images/Toronto%20Events.jpg">'
)


def inject_og_image(index_path):
    """Inject og:image meta tags into the staged index.html for social media previews."""
    if not index_path.is_file():
        return
    content = index_path.read_text(encoding='utf-8', errors='replace')
    # Inject before closing </head> or after first <head> tag
    if '</head>' in content:
        content = content.replace('</head>', OG_IMAGE_TAGS + '</head>', 1)
    elif '<head>' in content:
        content = content.replace('<head>', '<head>' + OG_IMAGE_TAGS, 1)
    index_path.write_text(content, encoding='utf-8')
    print('  Injected og:image meta tags into index.html')


# ─── Staging ──────────────────────────────────────────────────

def prepare_staging(staging_dir):
    """Copy all site files into staging with domain replacements."""
    file_count = 0

    # Process directories
    for src_rel, dst_rel in DIRS_TO_DEPLOY:
        src_dir = WORKSPACE / src_rel
        if not src_dir.is_dir():
            print(f'  Skip dir {src_rel} (not found)')
            continue

        dir_count = 0
        for root, dirs, files in os.walk(src_dir):
            # Prune skipped directories
            dirs[:] = [d for d in dirs if d not in SKIP_DIR_NAMES]

            for name in files:
                src_path = Path(root) / name
                rel_path = src_path.relative_to(src_dir)
                dst_path = staging_dir / dst_rel / rel_path
                if process_file(src_path, dst_path):
                    dir_count += 1

        print(f'  {src_rel} -> {dst_rel}  ({dir_count} files)')
        file_count += dir_count

    # Process single root files
    for src_rel, dst_rel in FILES_TO_DEPLOY + ROOT_BLOG_FILES:
        src_path = WORKSPACE / src_rel
        if not src_path.is_file():
            if src_rel in dict(FILES_TO_DEPLOY):
                print(f'  Skip file {src_rel} (not found)')
            continue
        dst_path = staging_dir / dst_rel
        if process_file(src_path, dst_path):
            file_count += 1

    if ROOT_BLOG_FILES:
        print(f'  Root blog files -> blog/  ({len(ROOT_BLOG_FILES)} files)')

    # Inject og:image into index.html
    inject_og_image(staging_dir / 'index.html')

    return file_count


# ─── FTP Upload ──────────────────────────────────────────────

def ensure_remote_dir(ftp, path):
    """Create remote directory tree if needed."""
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


def upload_tree(ftp, local_dir, remote_base, total_files=0):
    """Upload entire directory tree to FTP with progress reporting."""
    uploaded = 0
    errors = 0

    # Collect all files first for progress tracking
    all_files = []
    for root, dirs, files in os.walk(local_dir):
        for name in files:
            all_files.append(Path(root) / name)

    total = len(all_files)
    start_time = time.time()

    for local_path in all_files:
        rel = local_path.relative_to(local_dir)
        remote_path = remote_base + '/' + str(rel).replace('\\', '/')
        remote_dir = '/'.join(remote_path.split('/')[:-1])
        remote_file = remote_path.split('/')[-1]

        try:
            ftp.cwd('/')
            ensure_remote_dir(ftp, remote_dir)
            ftp.cwd('/' + remote_dir)
            with open(local_path, 'rb') as f:
                ftp.storbinary('STOR ' + remote_file, f)
            uploaded += 1

            # Progress every 50 files
            if uploaded % 50 == 0:
                elapsed = time.time() - start_time
                rate = uploaded / elapsed if elapsed > 0 else 0
                remaining = (total - uploaded) / rate if rate > 0 else 0
                print(f'  Progress: {uploaded}/{total} files '
                      f'({uploaded*100//total}%) '
                      f'~{int(remaining)}s remaining')

        except Exception as e:
            errors += 1
            if errors <= 20:
                print(f'  ERROR {remote_path}: {e}')
            elif errors == 21:
                print('  ... (suppressing further errors)')

            # Retry once on failure
            try:
                time.sleep(1)
                ftp.cwd('/')
                ensure_remote_dir(ftp, remote_dir)
                ftp.cwd('/' + remote_dir)
                with open(local_path, 'rb') as f:
                    ftp.storbinary('STOR ' + remote_file, f)
                uploaded += 1
                errors -= 1  # Successful retry
            except Exception:
                pass

    return uploaded, errors


# ─── Main ─────────────────────────────────────────────────────

def main():
    if not all([FTP_SERVER, FTP_USER, FTP_PASS]):
        print('ERROR: FTP credentials not found in environment variables.')
        print('Set FTP_SERVER, FTP_USER, FTP_PASS as Windows user environment variables.')
        sys.exit(1)

    print('=' * 60)
    print('  Deploy Full Mirror to tdotevent.ca')
    print('=' * 60)
    print()
    print(f'FTP Server: {FTP_SERVER}')
    print(f'Remote root: /{REMOTE_ROOT}/')
    print()
    print('Domain replacements:')
    for old, new in REPLACEMENTS:
        print(f'  {old} -> {new}')
    print()

    # Phase 1: Stage files with domain replacements
    print('Phase 1: Staging files with domain replacements...')
    print('-' * 40)

    with tempfile.TemporaryDirectory() as temp_dir:
        staging = Path(temp_dir)
        file_count = prepare_staging(staging)

        print()
        print(f'Staged {file_count} files for upload.')
        print()

        # Phase 2: Upload via FTP_TLS
        print('Phase 2: Uploading via FTP_TLS...')
        print('-' * 40)

        try:
            ftp = FTP_TLS(FTP_SERVER)
            ftp.login(FTP_USER, FTP_PASS)
            ftp.prot_p()
            ftp.set_pasv(True)
            print('Connected with TLS.')
            print()

            start = time.time()
            uploaded, errors = upload_tree(ftp, staging, REMOTE_ROOT, file_count)
            elapsed = time.time() - start

            ftp.quit()

            print()
            print('=' * 60)
            print(f'  Deploy complete! ({int(elapsed)}s)')
            print(f'  Uploaded: {uploaded} files')
            if errors:
                print(f'  Errors: {errors}')
            print('=' * 60)
            print()
            print('Your mirror site is live at: https://tdotevent.ca/')
            print()
            print('Verify these pages:')
            print('  https://tdotevent.ca/                        - Main events')
            print('  https://tdotevent.ca/fc/#/guest               - FavCreators')
            print('  https://tdotevent.ca/deals/                   - Deals & Freebies')
            print('  https://tdotevent.ca/news/                    - News Feed')
            print('  https://tdotevent.ca/findstocks/portfolio2/hub.html - Stocks Hub')
            print('  https://tdotevent.ca/live-monitor/live-monitor.html - Live Trading')
            print('  https://tdotevent.ca/weather/                 - Weather')
            print('  https://tdotevent.ca/vr/                      - VR Games')
            print('  https://tdotevent.ca/investments/              - Investments')
            print('  https://tdotevent.ca/WINDOWSFIXER/             - Windows Fixer')
            print('  https://tdotevent.ca/movieshows2/              - Film Vault')
            print('  https://tdotevent.ca/MOVIESHOWS3/              - Binge Mode')
            print('  https://tdotevent.ca/CONTACTLENSES/            - Contact Lenses')
            print('  https://tdotevent.ca/daily-feed/               - Daily Feed')
            print()

        except Exception as e:
            print(f'Deploy FAILED: {e}')
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == '__main__':
    main()
