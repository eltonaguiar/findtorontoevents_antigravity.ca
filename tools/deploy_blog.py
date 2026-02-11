#!/usr/bin/env python3
"""
Deploy the blog directory to both findtorontoevents.ca and tdotevent.ca via FTP_TLS.

Uploads blog/ from TORONTOEVENTS_ANTIGRAVITY/build/blog/ to:
  - findtorontoevents.ca/blog/
  - tdotevent.ca/blog/ (with domain replacement)

Uses Windows user environment variables:
  FTP_SERVER  - FTP hostname
  FTP_USER    - FTP username
  FTP_PASS    - FTP password

Run from project root:
  python tools/deploy_blog.py
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

BLOG_SOURCE = WORKSPACE / 'TORONTOEVENTS_ANTIGRAVITY' / 'build' / 'blog'

FTP_SERVER = os.environ.get('FTP_SERVER', '').strip()
FTP_USER = os.environ.get('FTP_USER', '').strip()
FTP_PASS = os.environ.get('FTP_PASS', '').strip()

SITES = [
    {
        'name': 'findtorontoevents.ca',
        'remote_root': 'findtorontoevents.ca/blog',
        'replacements': [],
    },
    {
        'name': 'tdotevent.ca',
        'remote_root': 'tdotevent.ca/blog',
        'replacements': [
            ('www.findtorontoevents.ca', 'www.tdotevent.ca'),
            ('support@findtorontoevents.ca', 'support@tdotevent.ca'),
            ('FindTorontoEvents.ca', 'TdotEvent.ca'),
            ('findtorontoevents.ca', 'tdotevent.ca'),
            ('FindTorontoEvents', 'TdotEvent'),
        ],
    },
]

TEXT_EXTENSIONS = {'.html', '.htm', '.js', '.css', '.json', '.xml', '.txt'}


def replace_domains(content, replacements):
    for old, new in replacements:
        content = content.replace(old, new)
    return content


def ensure_remote_dir(ftp, path):
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


def upload_blog(ftp, source_dir, remote_root, replacements):
    uploaded = 0
    errors = 0

    all_files = list(source_dir.rglob('*'))
    all_files = [f for f in all_files if f.is_file()]

    for local_path in all_files:
        rel = local_path.relative_to(source_dir)
        remote_path = remote_root + '/' + str(rel).replace('\\', '/')
        remote_dir = '/'.join(remote_path.split('/')[:-1])
        remote_file = remote_path.split('/')[-1]

        try:
            ftp.cwd('/')
            ensure_remote_dir(ftp, remote_dir)
            ftp.cwd('/' + remote_dir)

            if replacements and local_path.suffix.lower() in TEXT_EXTENSIONS:
                content = local_path.read_text(encoding='utf-8', errors='replace')
                content = replace_domains(content, replacements)
                tmp = source_dir.parent / ('_tmp_' + local_path.name)
                tmp.write_text(content, encoding='utf-8')
                with open(tmp, 'rb') as f:
                    ftp.storbinary('STOR ' + remote_file, f)
                tmp.unlink()
            else:
                with open(local_path, 'rb') as f:
                    ftp.storbinary('STOR ' + remote_file, f)

            uploaded += 1
            print(f'  [{uploaded}/{len(all_files)}] {rel}')

        except Exception as e:
            errors += 1
            print(f'  ERROR {remote_path}: {e}')

            try:
                time.sleep(1)
                ftp.cwd('/')
                ensure_remote_dir(ftp, remote_dir)
                ftp.cwd('/' + remote_dir)
                with open(local_path, 'rb') as f:
                    ftp.storbinary('STOR ' + remote_file, f)
                uploaded += 1
                errors -= 1
            except Exception:
                pass

    return uploaded, errors


def main():
    if not all([FTP_SERVER, FTP_USER, FTP_PASS]):
        print('ERROR: FTP credentials not found.')
        print('Set FTP_SERVER, FTP_USER, FTP_PASS as Windows user environment variables.')
        sys.exit(1)

    if not BLOG_SOURCE.is_dir():
        print(f'ERROR: Blog source not found: {BLOG_SOURCE}')
        sys.exit(1)

    blog_files = list(BLOG_SOURCE.rglob('*'))
    blog_files = [f for f in blog_files if f.is_file()]
    print(f'Found {len(blog_files)} blog files to deploy.')
    print()

    try:
        ftp = FTP_TLS(FTP_SERVER)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.prot_p()
        ftp.set_pasv(True)
        print('Connected via FTP_TLS.')
        print()

        for site in SITES:
            print('=' * 50)
            print(f'  Deploying to {site["name"]}')
            print('=' * 50)

            start = time.time()
            uploaded, errors = upload_blog(
                ftp, BLOG_SOURCE, site['remote_root'], site['replacements']
            )
            elapsed = time.time() - start

            print()
            print(f'  Done: {uploaded} files uploaded, {errors} errors ({int(elapsed)}s)')
            print()

        ftp.quit()

        print('=' * 50)
        print('  Blog deployed to both sites!')
        print('=' * 50)
        print()
        print('Verify:')
        print('  https://findtorontoevents.ca/blog/')
        print('  https://tdotevent.ca/blog/')
        print()

    except Exception as e:
        print(f'Deploy FAILED: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
