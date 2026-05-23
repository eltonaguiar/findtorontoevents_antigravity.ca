#!/usr/bin/env python3
"""Deploy funds.html + dashboard_payload.json via FTPS"""
import os, sys, ssl
from ftplib import FTP_TLS

FTP_SERVER = 'ftps2.50webs.com'
FTP_USER = 'ejaguiar1'
FTP_PASS = os.getenv('FTP_PASS', '')

if not FTP_PASS:
    print("Error: FTP_PASS not set")
    sys.exit(1)

FILES = [
    ('audit_trail/data/dashboard_payload.json', '/findtorontoevents.ca/audit_dashboard/data/dashboard_payload.json'),
    ('audit_dashboard/funds.html', '/findtorontoevents.ca/audit_dashboard/funds.html'),
    ('audit_dashboard/funds.html', '/findtorontoevents.ca/audit/funds.html'),
]

print("=" * 60)
print("FUNDS PAGE + DATA DEPLOYMENT (FTPS)")
print("=" * 60)

try:
    print("Connecting to FTPS...")
    ftps = FTP_TLS(FTP_SERVER)
    ftps.login(FTP_USER, FTP_PASS)
    ftps.prot_p()
    print("Connected!")

    success = 0
    failed = 0

    for local_file, remote_path in FILES:
        print(f"Deploying: {os.path.basename(local_file)} -> {remote_path}")

        if not os.path.exists(local_file):
            print(f"  ERROR: Local file not found: {local_file}")
            failed += 1
            continue

        try:
            parts = remote_path.strip('/').split('/')
            filename = parts[-1]
            dirs = parts[:-1]

            ftps.cwd('/')
            for d in dirs:
                try:
                    ftps.mkd(d)
                except:
                    pass
                ftps.cwd(d)

            with open(local_file, 'rb') as f:
                ftps.storbinary(f'STOR {filename}', f)

            size = os.path.getsize(local_file)
            print(f"  SUCCESS ✓ ({size:,} bytes)")
            success += 1

        except Exception as e:
            print(f"  FAILED: {e}")
            failed += 1

    ftps.quit()

    print()
    print("=" * 60)
    print(f"SUMMARY: {success} success, {failed} failed")
    print("=" * 60)

    if failed == 0:
        print("\nAll files deployed!")
        print("\nTest URLs:")
        print("  https://findtorontoevents.ca/audit_dashboard/funds.html")
        print("  https://findtorontoevents.ca/audit_dashboard/data/dashboard_payload.json")
        sys.exit(0)
    else:
        sys.exit(1)

except Exception as e:
    print(f"\nERROR: {e}")
    sys.exit(1)
