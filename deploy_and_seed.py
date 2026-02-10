#!/usr/bin/env python3
"""Deploy findstocks2_global/index.html to FTP, then seed algorithms via setup_schema.php."""

import os
import sys
import json
from ftplib import FTP_TLS
import urllib.request
import ssl

# --- Step 1: Deploy via FTP ---
FTP_SERVER = "ftps2.50webs.com"
FTP_USER = "ejaguiar1"
FTP_PASS = "$a^FzN7BqKapSQMsZxD&^FeTJ"

LOCAL_FILE = r"e:\findtorontoevents_antigravity.ca\findstocks2_global\index.html"
REMOTE_DIR = "/findtorontoevents.ca/findstocks2_global"
REMOTE_FILE = REMOTE_DIR + "/index.html"

print("=" * 60)
print("STEP 1: Deploy findstocks2_global/index.html via FTP")
print("=" * 60)

try:
    ftp = FTP_TLS(FTP_SERVER)
    ftp.login(FTP_USER, FTP_PASS)
    ftp.prot_p()
    print(f"  Connected to {FTP_SERVER} as {FTP_USER}")

    # Ensure remote directory exists
    try:
        ftp.cwd(REMOTE_DIR)
        print(f"  Remote dir exists: {REMOTE_DIR}")
    except Exception:
        print(f"  Creating remote dir: {REMOTE_DIR}")
        ftp.mkd(REMOTE_DIR)
        ftp.cwd(REMOTE_DIR)

    # Upload the file
    file_size = os.path.getsize(LOCAL_FILE)
    print(f"  Uploading {LOCAL_FILE} ({file_size:,} bytes)...")
    with open(LOCAL_FILE, "rb") as f:
        ftp.storbinary("STOR index.html", f)

    # Verify upload by checking remote size
    remote_size = ftp.size("index.html")
    print(f"  Remote file size: {remote_size:,} bytes")

    if remote_size == file_size:
        print("  Upload VERIFIED - sizes match!")
    else:
        print(f"  WARNING: size mismatch (local={file_size}, remote={remote_size})")

    ftp.quit()
    print("  FTP connection closed.\n")

except Exception as e:
    print(f"  FTP ERROR: {e}", file=sys.stderr)
    sys.exit(1)

# --- Step 2: Hit setup_schema.php to seed algorithms ---
print("=" * 60)
print("STEP 2: Seed algorithms via setup_schema.php")
print("=" * 60)

SCHEMA_URL = "https://findtorontoevents.ca/findstocks/portfolio2/api/setup_schema.php"

try:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(SCHEMA_URL)
    req.add_header("User-Agent", "DeployScript/1.0")

    print(f"  Hitting: {SCHEMA_URL}")
    with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
        body = resp.read().decode("utf-8")
        status = resp.status

    print(f"  HTTP {status}")
    print(f"  Raw response: {body[:1000]}")

    # Parse JSON
    data = json.loads(body)

    # Try to find algorithm count in various possible response shapes
    algo_count = None
    if isinstance(data, dict):
        # Check common key names
        for key in ["algorithms_seeded", "algorithms", "seeded", "algo_count", "count"]:
            if key in data:
                algo_count = data[key]
                break
        # Check nested data
        if algo_count is None and "data" in data and isinstance(data["data"], dict):
            for key in ["algorithms_seeded", "algorithms", "seeded", "algo_count", "count"]:
                if key in data["data"]:
                    algo_count = data["data"][key]
                    break
        # Check for arrays that might contain algorithms
        if algo_count is None:
            for key, val in data.items():
                if "algo" in key.lower() and isinstance(val, list):
                    algo_count = len(val)
                    print(f"  Found list '{key}' with {algo_count} items")
                    break

    if algo_count is not None:
        print(f"\n  RESULT: {algo_count} algorithms were seeded.")
    else:
        print(f"\n  Full parsed response:")
        print(f"  {json.dumps(data, indent=2)}")

except json.JSONDecodeError:
    print(f"  Response was not valid JSON: {body[:500]}")
except Exception as e:
    print(f"  HTTP ERROR: {e}", file=sys.stderr)
    sys.exit(1)

print("\nDone!")
