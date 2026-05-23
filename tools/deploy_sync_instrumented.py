#!/usr/bin/env python3
"""
Deploy sync-instrumented PHP API files to both sites (50webs + GoDaddy).

Uploads the 12 changed PHP endpoints (with sync_log_write instrumentation)
plus sync_log.php itself to:
  - findtorontoevents.ca (50webs) -> /findtorontoevents.ca/fc/api/
  - torontoevent.net (GoDaddy) -> /fc/api/

Environment variables required:
  FTP_SERVER, FTP_USER, FTP_PASS (50webs)
  FTPGODADDYHOST_TE_DOTNET, FTPGODADDYUSER, FTPGODADDYPASS (GoDaddy)
"""
import os
import sys
import ssl
import ftplib
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent

FILES_TO_DEPLOY = [
    'favcreators/docs/api/sync_log.php',
    'favcreators/docs/api/save_creators.php',
    'favcreators/docs/api/save_events.php',
    'favcreators/docs/api/save_note.php',
    'favcreators/docs/api/save_secondary_note.php',
    'favcreators/docs/api/save_link_list.php',
    'favcreators/docs/api/delete_link_list.php',
    'favcreators/docs/api/user_preferences.php',
    'favcreators/docs/api/google_callback.php',
    'favcreators/docs/api/guest_usage.php',
    'favcreators/docs/api/discord_unlink.php',
    'favcreators/docs/api/accountability/reminder_settings.php',
    'favcreators/docs/api/accountability/goal_followup_optout.php',
]

SITES = {
    'findtorontoevents.ca': {
        'host_env': 'FTP_SERVER',
        'user_env': 'FTP_USER',
        'pass_env': 'FTP_PASS',
        'remote_base': '/findtorontoevents.ca/fc/api',
        'use_tls': True,
    },
    'torontoevent.net': {
        'host_env': 'FTPGODADDYHOST_TE_DOTNET',
        'user_env': 'FTPGODADDYUSER',
        'pass_env': 'FTPGODADDYPASS',
        'remote_base': '/fc/api',
        'use_tls': False,
    },
}

LOCAL_API_DIR = 'favcreators/docs/api'


def ftp_connect(cfg):
    host = os.environ.get(cfg['host_env'], '')
    user = os.environ.get(cfg['user_env'], '')
    pw = os.environ.get(cfg['pass_env'], '')
    if not host or not user or not pw:
        raise RuntimeError(f"Missing FTP env vars: {cfg['host_env']}, {cfg['user_env']}, {cfg['pass_env']}")

    if cfg['use_tls']:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ftp = ftplib.FTP_TLS(context=ctx)
        ftp.connect(host, 21, timeout=30)
        ftp.login(user, pw)
        ftp.prot_p()
    else:
        ftp = ftplib.FTP()
        ftp.connect(host, 21, timeout=30)
        ftp.login(user, pw)
    return ftp


def ensure_dir(ftp, path):
    parts = [p for p in path.split('/') if p]
    ftp.cwd('/')
    for part in parts:
        try:
            ftp.cwd(part)
        except ftplib.error_perm:
            try:
                ftp.mkd(part)
                ftp.cwd(part)
            except Exception as e:
                print(f"    WARNING: mkd/cwd {part}: {e}")
                return False
    return True


def upload_file(ftp, local_path, remote_dir, remote_filename):
    ftp.cwd('/')
    if not ensure_dir(ftp, remote_dir):
        return False
    try:
        with open(local_path, 'rb') as f:
            ftp.storbinary(f'STOR {remote_filename}', f)
        return True
    except Exception as e:
        print(f"    ERROR uploading {remote_filename}: {e}")
        return False


def deploy_to_site(site_name, cfg):
    print(f"\n{'='*60}")
    print(f"Deploying to {site_name}")
    print(f"{'='*60}")

    ftp = ftp_connect(cfg)
    remote_base = cfg['remote_base']
    uploaded = 0
    failed = 0

    for rel_path in FILES_TO_DEPLOY:
        local_path = WORKSPACE / rel_path
        if not local_path.exists():
            print(f"  SKIP (not found): {rel_path}")
            failed += 1
            continue

        remote_rel = rel_path.replace(LOCAL_API_DIR + '/', '')
        remote_dir = remote_base
        if '/' in remote_rel:
            subdir = '/'.join(remote_rel.split('/')[:-1])
            remote_dir = f"{remote_base}/{subdir}"
        filename = remote_rel.split('/')[-1]

        ok = upload_file(ftp, local_path, remote_dir, filename)
        if ok:
            print(f"  OK: {remote_base}/{remote_rel}")
            uploaded += 1
        else:
            failed += 1

    try:
        ftp.quit()
    except Exception:
        pass

    print(f"\n  {site_name}: {uploaded} uploaded, {failed} failed")
    return failed == 0


def main():
    print("Sync-Instrumented PHP Deploy")
    print(f"Files to deploy: {len(FILES_TO_DEPLOY)}")

    all_ok = True
    for site_name, cfg in SITES.items():
        try:
            ok = deploy_to_site(site_name, cfg)
            if not ok:
                all_ok = False
        except Exception as e:
            print(f"\n  FAILED to deploy to {site_name}: {e}")
            all_ok = False

    print(f"\n{'='*60}")
    if all_ok:
        print("All deployments succeeded.")
    else:
        print("Some deployments had errors. Check output above.")
    return 0 if all_ok else 1


if __name__ == '__main__':
    sys.exit(main())
