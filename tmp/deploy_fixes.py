import os, ftplib, traceback, sys

def ensure_dir(ftp, path):
    ftp.cwd('/')
    for part in path.split('/'):
        if not part: continue
        try: ftp.cwd(part)
        except:
            try: ftp.mkd(part)
            except: pass
            ftp.cwd(part)

def upload(ftp, local_path, remote_path):
    parts = remote_path.split('/')
    d = '/'.join(parts[:-1])
    if d: ensure_dir(ftp, d)
    ftp.cwd('/')
    if d: ftp.cwd(d)
    with open(local_path, 'rb') as f:
        ftp.storbinary('STOR ' + parts[-1], f)
    sz = os.path.getsize(local_path)
    print(f'  OK {remote_path} ({sz} bytes)', flush=True)

pwd = os.getenv('FTP_PASS', '')
root = r'e:\findtorontoevents_antigravity.ca'

files_to_deploy = []

# JS files
for jsf in ['dashboard.js', 'data-mode-switcher.js', 'data-loader.js', 'audit-trail.js', 'charts.js']:
    files_to_deploy.append((
        os.path.join(root, 'riseoftheclaw', 'js', jsf),
        'findtorontoevents.ca/riseoftheclaw/js/' + jsf
    ))

# HTML
files_to_deploy.append((os.path.join(root, 'riseoftheclaw.html'), 'findtorontoevents.ca/riseoftheclaw.html'))

# CSS
files_to_deploy.append((os.path.join(root, 'riseoftheclaw', 'css', 'dashboard.css'), 'findtorontoevents.ca/riseoftheclaw/css/dashboard.css'))

# Data
for df in ['live_competition.json', 'active_picks.json', 'algorithms.json']:
    local = os.path.join(root, 'riseoftheclaw', 'data', df)
    if os.path.exists(local):
        files_to_deploy.append((local, 'findtorontoevents.ca/riseoftheclaw/data/' + df))

# Audit dashboard
files_to_deploy.append((os.path.join(root, 'audit_dashboard', 'index.html'), 'findtorontoevents.ca/audit_dashboard/index.html'))

try:
    print('Connecting to 50webs (ftps2.50webs.com)...', flush=True)
    ftp = ftplib.FTP('ftps2.50webs.com', timeout=60)
    ftp.login('ejaguiar1', pwd)
    print('Connected!', flush=True)

    ok = 0
    fail = 0
    for local, remote in files_to_deploy:
        try:
            upload(ftp, local, remote)
            ok += 1
        except Exception as e:
            print(f'  FAIL {remote}: {e}', flush=True)
            fail += 1

    ftp.quit()
    print(f'DONE - 50webs: {ok} OK, {fail} failed', flush=True)
except Exception as e:
    traceback.print_exc()
    print(f'ERROR: {e}', flush=True)
    sys.exit(1)
