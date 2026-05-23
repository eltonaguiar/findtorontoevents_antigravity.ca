"""
sync_first_time_setup.py -- Automated first-time setup for bi-directional database sync.

Deploys sync scripts to both sites, creates infrastructure tables, runs initial
reconciliation, deploys permanent sync_log.php, verifies health, and cleans up.

Requires environment variables:
  FTP_SERVER, FTP_USER, FTP_PASS               -- 50webs FTP (findtorontoevents.ca)
  FTPGODADDYHOST_TE_DOTNET, FTPGODADDYUSER, FTPGODADDYPASS  -- GoDaddy FTP (torontoevent.net)

Usage:
  python tools/sync_first_time_setup.py                    # Full setup
  python tools/sync_first_time_setup.py --dry-run          # Dry run (no actual DB changes)
  python tools/sync_first_time_setup.py --step ensure      # Only run ensure_sync_tables
  python tools/sync_first_time_setup.py --step reconcile   # Only run initial reconciliation
  python tools/sync_first_time_setup.py --step verify      # Only run sync_status check
  python tools/sync_first_time_setup.py --step cleanup     # Only clean up _sync_tmp
"""

import os
import sys
import json
import ftplib
import glob
import secrets
import time
import ssl
import tempfile
import shutil

try:
    from urllib.request import Request, urlopen
    from urllib.error import URLError, HTTPError
except ImportError:
    from urllib2 import Request, urlopen, URLError, HTTPError

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
SYNC_SRC_DIR = os.path.join(PROJECT_ROOT, 'scripts', 'sync')
SYNC_LOG_SRC = os.path.join(PROJECT_ROOT, 'favcreators', 'docs', 'api', 'sync_log.php')

SYNC_TMP_DIR = '_sync_tmp'
RESULTS_FILE = os.path.join(PROJECT_ROOT, 'tmp', 'sync_setup_results.json')
FC_ENV_FILE = os.path.join(PROJECT_ROOT, 'favcreators', 'docs', 'api', '.env')

DATABASES = ['ejaguiar1_favcreators', 'ejaguiar1_tvmoviestrailers']


def _read_env_file(path):
    """Parse a .env file into a dict (handles quoted values)."""
    result = {}
    if not os.path.exists(path):
        return result
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                continue
            key, val = line.split('=', 1)
            key = key.strip()
            val = val.strip()
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            elif val.startswith("'") and val.endswith("'"):
                val = val[1:-1]
            result[key] = val
    return result


def _load_db_password():
    """Load the MySQL password for findtorontoevents.ca from the .env file."""
    env = _read_env_file(FC_ENV_FILE)
    pw = env.get('MYSQL_PASSWORD', '')
    if not pw:
        log_error(f'Could not read MYSQL_PASSWORD from {FC_ENV_FILE}')
        sys.exit(1)
    return pw


def _build_sites():
    """Build site configurations with DB credentials read from .env."""
    fc_db_pass = _load_db_password()
    return {
        'findtorontoevents.ca': {
            'ftp_host_env': 'FTP_SERVER',
            'ftp_user_env': 'FTP_USER',
            'ftp_pass_env': 'FTP_PASS',
            'ftp_remote_base': '/findtorontoevents.ca',
            'base_url': 'https://findtorontoevents.ca',
            'db_user': 'ejaguiar1_favcreators',
            'db_pass': fc_db_pass,
            'db_cred_map': {
                'ejaguiar1_favcreators': ('ejaguiar1_favcreators', fc_db_pass),
                'ejaguiar1_tvmoviestrailers': ('ejaguiar1_tvmoviestrailers', 'tvmoviestrailers'),
            },
            'use_tls': True,
        },
        'torontoevent.net': {
            'ftp_host_env': 'FTPGODADDYHOST_TE_DOTNET',
            'ftp_user_env': 'FTPGODADDYUSER',
            'ftp_pass_env': 'FTPGODADDYPASS',
            'ftp_remote_base': '',
            'base_url': 'https://torontoevent.net',
            'db_user': 'admin',
            'db_pass': fc_db_pass,
            'db_cred_map': {},
        },
    }


SITES = None  # initialized in main()


def log(msg):
    print(f'[sync-setup] {msg}')


def log_error(msg):
    print(f'[sync-setup] ERROR: {msg}', file=sys.stderr)


def get_env(name):
    val = os.environ.get(name, '')
    if not val:
        log_error(f'Missing environment variable: {name}')
        sys.exit(1)
    return val


def generate_token():
    return secrets.token_hex(16)


def prepare_scripts(site_name, site_cfg, token, tmp_dir):
    """Read sync PHP scripts, inject credentials, write to tmp_dir."""
    db_user = site_cfg['db_user']
    db_pass = site_cfg['db_pass']

    resolved_map = dict(site_cfg.get('db_cred_map', {}))

    cred_map_parts = []
    for dbname, (u, p) in resolved_map.items():
        u_esc = u.replace("'", "\\'")
        p_esc = p.replace("'", "\\'")
        cred_map_parts.append(f"'{dbname}' => array('{u_esc}', '{p_esc}')")
    cred_map_php = 'array(' + ', '.join(cred_map_parts) + ')' if cred_map_parts else 'array()'

    prepared = []
    for php_file in glob.glob(os.path.join(SYNC_SRC_DIR, '*.php')):
        with open(php_file, 'r', encoding='utf-8') as f:
            content = f.read()

        content = content.replace('SYNC_TOKEN_PLACEHOLDER', token)
        content = content.replace('DB_USER_PLACEHOLDER', db_user)
        content = content.replace('DB_PASS_PLACEHOLDER', db_pass)
        content = content.replace('array(); // SYNC_DB_CRED_MAP', cred_map_php + '; // SYNC_DB_CRED_MAP')

        basename = os.path.basename(php_file)
        out_path = os.path.join(tmp_dir, basename)
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(content)
        prepared.append(basename)

    log(f'  Prepared {len(prepared)} scripts for {site_name}')
    return prepared


def ftp_connect(site_cfg):
    """Connect to FTP server, return the connection."""
    host = get_env(site_cfg['ftp_host_env'])
    user = get_env(site_cfg['ftp_user_env'])
    pw = get_env(site_cfg['ftp_pass_env'])

    if site_cfg.get('use_tls'):
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


def ftp_ensure_dir(ftp, path):
    """Create directory if it doesn't exist."""
    try:
        ftp.mkd(path)
    except ftplib.error_perm:
        pass


def ftp_upload_dir(site_name, site_cfg, local_dir, remote_subdir):
    """Upload all PHP files from local_dir to remote_subdir on the FTP server."""
    ftp = ftp_connect(site_cfg)
    base = site_cfg['ftp_remote_base']

    try:
        if base:
            ftp.cwd(base)

        ftp_ensure_dir(ftp, remote_subdir)
        ftp.cwd(remote_subdir)

        uploaded = 0
        for fname in os.listdir(local_dir):
            if not fname.endswith('.php'):
                continue
            filepath = os.path.join(local_dir, fname)
            with open(filepath, 'rb') as f:
                ftp.storbinary(f'STOR {fname}', f)
            uploaded += 1

        log(f'  Uploaded {uploaded} files to {site_name}/{remote_subdir}/')
    finally:
        try:
            ftp.quit()
        except Exception:
            ftp.close()


def ftp_upload_file(site_name, site_cfg, local_path, remote_path):
    """Upload a single file to a specific remote path."""
    ftp = ftp_connect(site_cfg)
    base = site_cfg['ftp_remote_base']

    try:
        if base:
            ftp.cwd(base)

        remote_dir = '/'.join(remote_path.split('/')[:-1])
        if remote_dir:
            parts = remote_dir.split('/')
            for i in range(len(parts)):
                subpath = '/'.join(parts[:i+1])
                ftp_ensure_dir(ftp, subpath)

        with open(local_path, 'rb') as f:
            ftp.storbinary(f'STOR {remote_path}', f)

        log(f'  Uploaded {os.path.basename(local_path)} to {site_name}/{remote_path}')
    finally:
        try:
            ftp.quit()
        except Exception:
            ftp.close()


def ftp_cleanup(site_name, site_cfg, remote_subdir):
    """Remove the temp sync directory from the remote server."""
    ftp = ftp_connect(site_cfg)
    base = site_cfg['ftp_remote_base']

    try:
        if base:
            ftp.cwd(base)

        try:
            ftp.cwd(remote_subdir)
            files = ftp.nlst()
            for f in files:
                if f in ('.', '..'):
                    continue
                try:
                    ftp.delete(f)
                except ftplib.error_perm:
                    pass
            ftp.cwd('..')
            ftp.rmd(remote_subdir)
            log(f'  Cleaned up {site_name}/{remote_subdir}/')
        except ftplib.error_perm:
            log(f'  Cleanup: {remote_subdir}/ not found or already removed on {site_name}')
    finally:
        try:
            ftp.quit()
        except Exception:
            ftp.close()


def http_get(url, timeout=120):
    """GET request, return parsed JSON."""
    req = Request(url)
    req.add_header('User-Agent', 'SyncSetup/1.0')
    try:
        resp = urlopen(req, timeout=timeout)
        raw = resp.read().decode('utf-8')
        return json.loads(raw)
    except HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        log_error(f'HTTP {e.code} from {url}: {body[:500]}')
        return {'error': f'HTTP {e.code}', 'body': body[:500]}
    except URLError as e:
        log_error(f'URL error for {url}: {e}')
        return {'error': str(e)}
    except Exception as e:
        log_error(f'Request failed for {url}: {e}')
        return {'error': str(e)}


def http_post_json(url, data, timeout=120):
    """POST JSON data, return parsed JSON."""
    payload = json.dumps(data).encode('utf-8')
    req = Request(url, data=payload)
    req.add_header('Content-Type', 'application/json')
    req.add_header('User-Agent', 'SyncSetup/1.0')
    try:
        resp = urlopen(req, timeout=timeout)
        raw = resp.read().decode('utf-8')
        return json.loads(raw)
    except HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        log_error(f'HTTP {e.code} from {url}: {body[:500]}')
        return {'error': f'HTTP {e.code}', 'body': body[:500]}
    except URLError as e:
        log_error(f'URL error for {url}: {e}')
        return {'error': str(e)}
    except Exception as e:
        log_error(f'Request failed for {url}: {e}')
        return {'error': str(e)}


def step_deploy(token, dry_run=False):
    """Deploy sync scripts to both sites."""
    log('=== Step 1: Deploy sync scripts ===')
    results = {}

    for site_name, site_cfg in SITES.items():
        log(f'Deploying to {site_name}...')
        tmp_dir = tempfile.mkdtemp(prefix=f'sync_{site_name}_')
        try:
            prepare_scripts(site_name, site_cfg, token, tmp_dir)
            if not dry_run:
                ftp_upload_dir(site_name, site_cfg, tmp_dir, SYNC_TMP_DIR)
                results[site_name] = 'deployed'
            else:
                log(f'  [DRY RUN] Would deploy to {site_name}/{SYNC_TMP_DIR}/')
                results[site_name] = 'dry_run'
        except Exception as e:
            log_error(f'Deploy to {site_name} failed: {e}')
            results[site_name] = f'error: {e}'
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    return results


def step_ensure_tables(token, dry_run=False):
    """Call ensure_sync_tables on both sites."""
    log('=== Step 2: Ensure sync tables ===')
    dry_param = '1' if dry_run else '0'
    results = {}

    for site_name, site_cfg in SITES.items():
        url = f"{site_cfg['base_url']}/{SYNC_TMP_DIR}/ensure_sync_tables.php?token={token}&db=ALL&dry_run={dry_param}"
        log(f'Calling ensure_sync_tables on {site_name}...')

        for attempt in range(3):
            data = http_get(url)
            if 'error' not in data or data.get('status') == 'ok':
                break
            log(f'  Attempt {attempt+1} failed, retrying in 5s...')
            time.sleep(5)

        results[site_name] = data
        if data.get('status') == 'ok':
            for r in data.get('results', []):
                db = r.get('database', '?')
                actions = r.get('actions', [])
                errors = r.get('errors', [])
                counts = r.get('row_counts', {})
                log(f'  {db}: {len(actions)} actions, {len(errors)} errors')
                for a in actions:
                    log(f'    {a}')
                for e in errors:
                    log_error(f'    {e}')
                if counts:
                    log(f'    Row counts: {json.dumps(counts)}')
        else:
            log_error(f'  ensure_sync_tables failed on {site_name}: {json.dumps(data)[:300]}')

    return results


def step_reconcile(token, dry_run=False):
    """Run initial reconciliation between the two sites."""
    log('=== Step 3: Initial reconciliation ===')
    results = {}

    site_a_name = 'findtorontoevents.ca'
    site_b_name = 'torontoevent.net'
    site_a = SITES[site_a_name]
    site_b = SITES[site_b_name]

    for dbname in DATABASES:
        log(f'Reconciling {dbname}...')
        db_result = {'database': dbname}

        log(f'  Exporting from {site_a_name}...')
        export_a_url = f"{site_a['base_url']}/{SYNC_TMP_DIR}/db_sync_initial_reconcile.php?token={token}&db={dbname}&mode=export"
        export_a = http_get(export_a_url, timeout=180)

        if 'error' in export_a and export_a.get('status') != 'ok':
            log_error(f'  Export from {site_a_name} failed: {json.dumps(export_a)[:300]}')
            db_result['export_a'] = export_a
            results[dbname] = db_result
            continue

        data_a = export_a.get('data', {})
        log(f'  Exported {sum(len(v) for v in data_a.values())} rows across {len(data_a)} tables from {site_a_name}')

        log(f'  Exporting from {site_b_name}...')
        export_b_url = f"{site_b['base_url']}/{SYNC_TMP_DIR}/db_sync_initial_reconcile.php?token={token}&db={dbname}&mode=export"
        export_b = http_get(export_b_url, timeout=180)

        if 'error' in export_b and export_b.get('status') != 'ok':
            log_error(f'  Export from {site_b_name} failed: {json.dumps(export_b)[:300]}')
            db_result['export_b'] = export_b
            results[dbname] = db_result
            continue

        data_b = export_b.get('data', {})
        log(f'  Exported {sum(len(v) for v in data_b.values())} rows across {len(data_b)} tables from {site_b_name}')

        log(f'  Reconciling {site_a_name} data INTO {site_b_name} (dry_run={dry_run})...')
        reconcile_b = http_post_json(
            f"{site_b['base_url']}/{SYNC_TMP_DIR}/db_sync_initial_reconcile.php",
            {
                'token': token,
                'db': dbname,
                'mode': 'reconcile',
                'remote_site': site_a_name,
                'remote_data': data_a,
                'dry_run': dry_run,
            },
            timeout=180,
        )
        db_result['reconcile_on_b'] = reconcile_b
        _log_reconcile_result(site_b_name, reconcile_b)

        log(f'  Reconciling {site_b_name} data INTO {site_a_name} (dry_run={dry_run})...')
        reconcile_a = http_post_json(
            f"{site_a['base_url']}/{SYNC_TMP_DIR}/db_sync_initial_reconcile.php",
            {
                'token': token,
                'db': dbname,
                'mode': 'reconcile',
                'remote_site': site_b_name,
                'remote_data': data_b,
                'dry_run': dry_run,
            },
            timeout=180,
        )
        db_result['reconcile_on_a'] = reconcile_a
        _log_reconcile_result(site_a_name, reconcile_a)

        results[dbname] = db_result

    return results


def _log_reconcile_result(site_name, data):
    """Pretty-print reconciliation results."""
    if data.get('status') in ('ok', 'partial'):
        report = data.get('report', {})
        matched = report.get('matched_users', [])
        local_only = report.get('local_only_users', [])
        remote_only = report.get('remote_only_users', [])
        actions = report.get('actions_taken', [])
        errors = report.get('errors', [])
        tables = report.get('table_reports', [])

        log(f'    Users: {len(matched)} matched, {len(local_only)} local-only, {len(remote_only)} remote-only')
        for t in tables:
            log(f'    {t["table"]}: inserted={t.get("inserted",0)}, merged={t.get("merged",0)}, skipped={t.get("skipped",0)}')
        for a in actions:
            log(f'    Action: {a}')
        for e in errors:
            log_error(f'    {e}')
    else:
        log_error(f'    Reconcile on {site_name} failed: {json.dumps(data)[:300]}')


def step_deploy_sync_log(dry_run=False):
    """Deploy sync_log.php permanently to both sites."""
    log('=== Step 4: Deploy sync_log.php permanently ===')
    results = {}

    if not os.path.exists(SYNC_LOG_SRC):
        log_error(f'sync_log.php not found at {SYNC_LOG_SRC}')
        return {'error': 'file not found'}

    remote_path = 'fc/api/sync_log.php'

    for site_name, site_cfg in SITES.items():
        log(f'Deploying sync_log.php to {site_name}/{remote_path}...')
        if not dry_run:
            try:
                ftp_upload_file(site_name, site_cfg, SYNC_LOG_SRC, remote_path)
                results[site_name] = 'deployed'
            except Exception as e:
                log_error(f'  Failed: {e}')
                results[site_name] = f'error: {e}'
        else:
            log(f'  [DRY RUN] Would deploy to {site_name}/{remote_path}')
            results[site_name] = 'dry_run'

    return results


def step_verify(token):
    """Call sync_status on both sites to verify."""
    log('=== Step 5: Verify sync status ===')
    results = {}

    for site_name, site_cfg in SITES.items():
        url = f"{site_cfg['base_url']}/{SYNC_TMP_DIR}/sync_status.php?token={token}&db=ALL"
        log(f'Checking status on {site_name}...')
        data = http_get(url)
        results[site_name] = data

        if data.get('status') == 'ok':
            for r in data.get('results', []):
                db = r.get('database', '?')
                log(f'  {db} on {r.get("site", "?")}:')
                log(f'    Changelog: {r.get("changelog_total", 0)} total, {r.get("changelog_unsynced", 0)} unsynced')
                log(f'    Conflicts: {r.get("unresolved_conflicts", 0)} unresolved / {r.get("total_conflicts", 0)} total')
                counts = r.get('row_counts', {})
                if counts:
                    log(f'    Row counts: {json.dumps(counts)}')
        else:
            log_error(f'  Status check failed on {site_name}: {json.dumps(data)[:300]}')

    return results


def step_cleanup():
    """Clean up _sync_tmp/ on both sites."""
    log('=== Step 6: Cleanup ===')
    results = {}

    for site_name, site_cfg in SITES.items():
        log(f'Cleaning up {site_name}/{SYNC_TMP_DIR}/...')
        try:
            ftp_cleanup(site_name, site_cfg, SYNC_TMP_DIR)
            results[site_name] = 'cleaned'
        except Exception as e:
            log_error(f'  Cleanup failed on {site_name}: {e}')
            results[site_name] = f'error: {e}'

    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Bi-directional sync first-time setup')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode (no actual DB changes)')
    parser.add_argument('--step', choices=['deploy', 'ensure', 'reconcile', 'deploy-sync-log', 'verify', 'cleanup', 'all'], default='all')
    parser.add_argument('--token', help='Use a specific token instead of generating one')
    args = parser.parse_args()

    global SITES
    SITES = _build_sites()

    dry_run = args.dry_run
    token = args.token or generate_token()

    log(f'Sync token: {token}')
    log(f'Dry run: {dry_run}')
    log(f'Step: {args.step}')
    log('')

    all_results = {
        'token': token,
        'dry_run': dry_run,
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    }

    steps_to_run = []
    if args.step == 'all':
        steps_to_run = ['deploy', 'ensure', 'reconcile', 'deploy-sync-log', 'verify', 'cleanup']
    else:
        if args.step in ('ensure', 'reconcile', 'verify'):
            steps_to_run = ['deploy', args.step, 'cleanup']
        else:
            steps_to_run = [args.step]

    try:
        if 'deploy' in steps_to_run:
            all_results['deploy'] = step_deploy(token, dry_run=False)

        if 'ensure' in steps_to_run:
            all_results['ensure_tables'] = step_ensure_tables(token, dry_run)

        if 'reconcile' in steps_to_run:
            if dry_run:
                log('Running reconciliation in DRY RUN first...')
                all_results['reconcile_dry'] = step_reconcile(token, dry_run=True)
                log('')
                log('Dry run complete. Running for real...')
            all_results['reconcile'] = step_reconcile(token, dry_run=False)

        if 'deploy-sync-log' in steps_to_run:
            all_results['deploy_sync_log'] = step_deploy_sync_log(dry_run)

        if 'verify' in steps_to_run:
            all_results['verify'] = step_verify(token)

    finally:
        if 'cleanup' in steps_to_run:
            all_results['cleanup'] = step_cleanup()

    os.makedirs(os.path.dirname(RESULTS_FILE), exist_ok=True)
    with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, default=str)
    log(f'\nResults saved to {RESULTS_FILE}')

    errors = []
    for key, val in all_results.items():
        if isinstance(val, dict):
            for k2, v2 in val.items():
                if isinstance(v2, dict) and 'error' in v2:
                    errors.append(f'{key}.{k2}: {v2["error"]}')
                elif isinstance(v2, str) and v2.startswith('error:'):
                    errors.append(f'{key}.{k2}: {v2}')

    if errors:
        log(f'\n{len(errors)} error(s) encountered:')
        for e in errors:
            log(f'  - {e}')
        return 1

    log('\nSetup completed successfully!')
    return 0


if __name__ == '__main__':
    sys.exit(main())
