#!/usr/bin/env python3
'''
protocol_bootstrap.py -- Cross-PC protocol missing-file detector + optional auto-fetcher

Run this FIRST when joining the swarm if you hit ModuleNotFoundError or missing adapter errors.

Usage:
    python tools/protocol_bootstrap.py                    # diagnostics only
    python tools/protocol_bootstrap.py --fix              # auto-fetch missing files
    python tools/protocol_bootstrap.py --fix --runtime laptop   # auto-fetch + use laptop peer id
'''
from __future__ import annotations

import argparse
import json
import socket
import sys
import urllib.request
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]

PROTOCOL_FILES: Dict[str, List[str]] = {
    'cross_pc_protocol/': [
        '__init__.py',
        'client.py',
        'schema.py',
        'storage.py',
        'gateway.py',
        'reliability.py',
        'redis_bridge.py',
        'lan_discovery.py',
    ],
    'tools/adapters/': [
        'cursor_claude_adapter.py',
        'freebuff_adapter.py',
    ],
    'tools/': [
        'protocol_gateway.py',
        'protocol_inspect.py',
    ],
}

# ASCII-safe status symbols
OK_CHR   = ord('+')
FAIL_CHR = ord('X')
WARN_CHR = ord('!')


def _c(code: int, text: str = '') -> str:
    '''Return ANSI-coloured text. code=0 strips colour.'''
    prefix = '\u001b[%dm' % code if code else ''
    suffix = '\u001b[0m' if code else ''
    return prefix + text + suffix


def detect_gateway_ip() -> str:
    '''Find correct gateway IP: 127.0.0.1 on desktop, 192.168.2.32 on laptop.'''
    desktop_ip = '192.168.2.32'
    my_hostname = socket.gethostname().lower().replace(' ', '-')

    # Desktop hostnames on this network contain '081g9oh'
    if any(d in my_hostname for d in ('081g9oh', 'desktop')):
        return '127.0.0.1'

    try:
        resp = urllib.request.urlopen('http://127.0.0.1:8788/health', timeout=3)
        data = json.loads(resp.read())
        peers = list(data.get('peer_registry', {}).keys())
        # Own peer in local registry = we're on desktop
        if my_hostname in peers:
            return '127.0.0.1'
        # Desktop gateway always has 9+ peers (full swarm)
        if len(peers) >= 9:
            return '127.0.0.1'
    except Exception:
        pass

    return desktop_ip


def check_file_exists(path: Path) -> Dict:
    exists = path.exists()
    size = path.stat().st_size if exists else 0
    return {'exists': exists, 'size': size, 'empty': exists and size == 0}


def check_all_files() -> Dict[str, Dict]:
    results = {}
    for directory, filenames in PROTOCOL_FILES.items():
        for fname in filenames:
            rel = str(Path(directory) / fname)
            results[rel] = check_file_exists(REPO_ROOT / rel)
    return results


def check_imports() -> Dict[str, bool]:
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    results = {}
    for mod_name, attr_name in [
        ('cross_pc_protocol', None),
        ('cross_pc_protocol.client', 'ProtocolClient'),
        ('cross_pc_protocol.schema', 'new_envelope'),
        ('cross_pc_protocol.storage', 'EventStore'),
    ]:
        try:
            mod = __import__(mod_name, fromlist=[attr_name] if attr_name else [])
            if attr_name is None or hasattr(mod, attr_name):
                results[mod_name] = True
            else:
                results[mod_name] = 'MISSING_ATTR:' + attr_name
        except Exception as e:
            results[mod_name] = 'ERROR:' + type(e).__name__ + ':' + str(e)
    return results


def check_gateway(http_base: str) -> Dict:
    try:
        base = http_base.rstrip('/')
        url = base + '/health'
        req = urllib.request.Request(url, headers={'Accept': 'application/json'})
        resp = urllib.request.urlopen(req, timeout=5)
        data = json.loads(resp.read())
        peers = data.get('peer_registry', {})
        return {
            'ok': True,
            'peer_count': len(peers),
            'offline_queues': data.get('offline_queues', {}),
            'peers': list(peers.keys()),
        }
    except Exception as e:
        return {'ok': False, 'error': '%s: %s' % (type(e).__name__, e)}


def fetch_file(relative_path: str, dry_run: bool = False) -> bool:
    '''Fetch from GitHub raw and save locally. Returns True on success.'''
    url = 'https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/' + relative_path
    local = REPO_ROOT / relative_path

    if dry_run:
        print('  [dry-run] would fetch ' + url)
        print('  [dry-run] would save to ' + str(local))
        return True

    try:
        local.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read()
        local.write_bytes(content)
        print('  + %s (%d bytes)' % (relative_path, len(content)))
        return True
    except Exception as e:
        print('  X %s: %s' % (relative_path, e))
        return False


def auto_fix_missing(missing: List[str], dry_run: bool = False) -> int:
    '''Fetch missing files, validate with py_compile, revert bad downloads.'''
    success = 0
    for rel_path in missing:
        ok = fetch_file(rel_path, dry_run=dry_run)
        if ok and not dry_run:
            local = REPO_ROOT / rel_path
            try:
                import py_compile
                py_compile.compile(str(local), doraise=True)
            except Exception:
                print('    X %s is not valid Python -- reverting' % rel_path)
                try:
                    local.unlink()
                except Exception:
                    pass
                continue
        if ok:
            success += 1
    return success


def resolve_runtime(http_base: str) -> str:
    '''Infer peer runtime from hostname.'''
    h = socket.gethostname().lower().replace(' ', '-')
    if any(k in h for k in ('laptop', 'zerou', 'ubuntu', 'wsl', 'wslamd64')):
        return 'laptop'
    try:
        base = http_base.rstrip('/')
        url = base + '/health'
        resp = urllib.request.urlopen(url, timeout=3)
        peers = list(json.loads(resp.read()).get('peer_registry', {}).keys())
        if any('laptop' in p for p in peers):
            return 'laptop'
    except Exception:
        pass
    return 'hermes'


def print_report(file_results, import_results, gateway_result, gateway_ip, runtime, missing):
    sep = '=' * 60
    print()
    print(_c(1, sep))
    print(_c(1, '  CROSS-PC PROTOCOL BOOTSTRAP REPORT'))
    print(_c(1, sep))
    print()
    print('  Hostname : %s' % socket.gethostname())
    print('  Repo root: %s' % REPO_ROOT)
    print('  Gateway  : %s:8788' % gateway_ip)
    print('  Runtime  : %s' % runtime)
    print()

    # Gateway block
    print(_c(1, '  +-- Gateway'))
    if gateway_result['ok']:
        print('  |  + reachable -- %d peers registered' % gateway_result['peer_count'])
        oq = gateway_result.get('offline_queues', {})
        if oq:
            pending = sum(int(v) for v in oq.values() if str(v).isdigit())
            print('  |  ! offline queues: %s (%d pending)' % (json.dumps(oq), pending))
        print('  |  Peers: %s' % gateway_result['peers'])
    else:
        print('  |  X unreachable: %s' % gateway_result.get('error'))
        print('  |  ! Run gateway on desktop: python tools/protocol_gateway.py')
    print('  |')

    # Files block
    print(_c(1, '  +-- Protocol Files'))
    all_ok = True
    for directory, filenames in PROTOCOL_FILES.items():
        print('  |  %s' % _c(1, directory))
        for fname in filenames:
            rel = str(Path(directory) / fname)
            res = file_results.get(rel, {})
            if res.get('exists') and not res.get('empty'):
                sym = '+'
            elif res.get('exists') and res.get('empty'):
                sym = '! EMPTY'
                all_ok = False
            else:
                sym = 'X MISSING'
                all_ok = False
            print('  |     %s  %s' % (sym, rel))
    print('  |')

    # Imports block
    print(_c(1, '  +-- Python Imports'))
    for mod, status in import_results.items():
        if status is True:
            print('  |  + %s' % mod)
        else:
            print('  |  X %s: %s' % (mod, status))
            all_ok = False
    print('  |')

    # Summary
    print(_c(1, '  +-- Summary'))
    if all_ok and gateway_result['ok']:
        print('  + All files present, imports OK, gateway reachable.')
        print('  + Ready to send! Example command:')
        print()
        print('    cd %s && python tools/adapters/cursor_claude_adapter.py \\' % REPO_ROOT)
        print('      --runtime %s \\' % runtime)
        print('      --http-base http://%s:8788 \\' % gateway_ip)
        print('      send --topic WHATSUP \\')
        print('      --payload {\\\"text\\\":\\\"hello from %s\\\"} \\' % runtime)
        print('      --to all')
    else:
        if missing:
            print('  X %d file(s) missing or empty:' % len(missing))
            for p in missing:
                print('       - %s' % p)
            print()
            print('  ! Run with --fix to auto-fetch:')
            print('    python tools/protocol_bootstrap.py --fix --runtime %s' % runtime)
        if not gateway_result['ok']:
            print('  X Gateway unreachable -- is desktop gateway running?')
        if not all(v is True for v in import_results.values()):
            print('  X Import failures -- fix files first, then re-bootstrap.')

    print()
    print(_c(1, sep))


def main() -> int:
    ap = argparse.ArgumentParser(description='Cross-PC protocol bootstrap')
    ap.add_argument('--fix', action='store_true', help='Auto-fetch missing files from GitHub')
    ap.add_argument('--runtime', default='', help='Peer runtime (hermes, laptop, etc.)')
    ap.add_argument('--dry-run', action='store_true', help='Show what would be fetched')
    ap.add_argument('--gateway-ip', default='', help='Gateway IP (auto-detected if omitted)')
    args = ap.parse_args()

    gateway_ip = args.gateway_ip or detect_gateway_ip()
    http_base = 'http://%s:8788' % gateway_ip

    print('Bootstrap starting -- repo root: %s' % REPO_ROOT)
    print('Gateway: %s' % http_base)

    print()
    print('Checking gateway...')
    gw = check_gateway(http_base)
    print('  Gateway: %s (%s)' % ('OK' if gw['ok'] else 'DOWN', gateway_ip))

    print()
    print('Checking protocol files...')
    file_results = check_all_files()
    missing = [p for p, r in file_results.items() if not r['exists'] or r.get('empty')]
    ok_count = len(file_results) - len(missing)
    print('  %d/%d files OK' % (ok_count, len(file_results)))

    print()
    print('Checking Python imports...')
    import_results = check_imports()

    runtime = args.runtime or resolve_runtime(http_base)
    print('  Runtime auto-detected: %s' % runtime)

    print_report(file_results, import_results, gw, gateway_ip, runtime, missing)

    if args.fix and missing:
        print(_c(1, '\nFetching missing files from GitHub...\n'))
        if args.dry_run:
            print('[DRY RUN -- no files actually fetched]\n')
        success = auto_fix_missing(missing, dry_run=args.dry_run)
        print('\n  Fetched %d/%d file(s).' % (success, len(missing)))
        if success == len(missing) and not args.dry_run:
            print('\n  Re-running bootstrap to verify fix...\n')
            fr2 = check_all_files()
            ir2 = check_imports()
            gw2 = check_gateway(http_base)
            missing2 = [p for p, r in fr2.items() if not r['exists'] or r.get('empty')]
            print_report(fr2, ir2, gw2, gateway_ip, runtime, missing2)
        elif success < len(missing):
            print('\n  X Some files failed to fetch.')
            print('  Try fetching manually or re-clone the repo.')

    all_ok = gw['ok'] and all(v is True for v in import_results.values()) and not missing
    return 0 if all_ok else 1


if __name__ == '__main__':
    raise SystemExit(main())