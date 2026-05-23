#!/usr/bin/env python3
"""
Quick deploy: Upload ads.txt and updated index.html to torontoevent.net
for Google AdSense verification.

Rewrites findtorontoevents.ca -> torontoevent.net in the index.html during upload.
"""
import ftplib
import io
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE = SCRIPT_DIR.parent
SITE_ROOT = WORKSPACE / "tmp" / "fte_clone"

TARGET_DOMAIN = "torontoevent.net"
SOURCE_DOMAIN = "findtorontoevents.ca"
FTP_PATH = "torontoevent.net"


def load_env():
    env_file = WORKSPACE / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip()
                if k and not os.environ.get(k):
                    os.environ[k] = v
    if "FTP_SERVER" not in os.environ and os.environ.get("FTP_HOST"):
        os.environ["FTP_SERVER"] = os.environ["FTP_HOST"]


def rewrite(content):
    replacements = [
        ("https://www." + SOURCE_DOMAIN, "https://www." + TARGET_DOMAIN),
        ("http://www." + SOURCE_DOMAIN, "http://www." + TARGET_DOMAIN),
        ("https://" + SOURCE_DOMAIN, "https://" + TARGET_DOMAIN),
        ("http://" + SOURCE_DOMAIN, "http://" + TARGET_DOMAIN),
        ("'" + SOURCE_DOMAIN + "'", "'" + TARGET_DOMAIN + "'"),
        ('"' + SOURCE_DOMAIN + '"', '"' + TARGET_DOMAIN + '"'),
        (SOURCE_DOMAIN, TARGET_DOMAIN),
    ]
    for old, new in replacements:
        content = content.replace(old, new)
    return content


def upload_text(ftp, content, remote_name):
    data = content.encode("utf-8")
    ftp.storbinary("STOR " + remote_name, io.BytesIO(data))
    print(f"  Uploaded {remote_name} ({len(data):,} bytes)")


def main():
    load_env()
    host = os.environ.get("FTP_SERVER", "").strip()
    user = os.environ.get("FTP_USER", "").strip()
    pw = os.environ.get("FTP_PASS", "").strip()

    if not all([host, user, pw]):
        print("ERROR: FTP_SERVER, FTP_USER, FTP_PASS must be set")
        sys.exit(1)

    # Read files
    index_path = SITE_ROOT / "index.html"
    ads_path = SITE_ROOT / "ads.txt"
    adsense_js_path = SITE_ROOT / "adsense-integration.js"

    if not index_path.exists():
        index_path = WORKSPACE / "index6.html"

    print(f"Reading {index_path}...")
    index_html = index_path.read_text(encoding="utf-8", errors="ignore")
    index_html = rewrite(index_html)

    print(f"Reading {ads_path}...")
    ads_txt = ads_path.read_text(encoding="utf-8")

    adsense_js = ""
    if adsense_js_path.exists():
        adsense_js = adsense_js_path.read_text(encoding="utf-8", errors="ignore")

    # Verify AdSense is in <head> as direct tag
    head_end = index_html.lower().find("</head>")
    head_section = index_html[:head_end] if head_end > 0 else ""
    if 'src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js' in head_section:
        print("  OK: Direct AdSense <script> tag found in <head>")
    else:
        print("  WARNING: Direct AdSense <script> tag NOT in <head>!")

    if TARGET_DOMAIN in index_html:
        print(f"  OK: Domain rewritten to {TARGET_DOMAIN}")
    if SOURCE_DOMAIN in index_html:
        count = index_html.count(SOURCE_DOMAIN)
        print(f"  WARNING: {count} old domain references remain")

    # Upload
    print(f"\nConnecting to {host}...")
    ftp = ftplib.FTP(host, timeout=60)
    ftp.login(user, pw)
    print("Connected.")

    # Navigate to site root
    try:
        ftp.cwd("/" + FTP_PATH)
    except Exception:
        ftp.mkd("/" + FTP_PATH)
        ftp.cwd("/" + FTP_PATH)
    print(f"CWD: /{FTP_PATH}/")

    upload_text(ftp, ads_txt, "ads.txt")
    upload_text(ftp, index_html, "index.html")
    if adsense_js:
        upload_text(ftp, adsense_js, "adsense-integration.js")

    ftp.quit()
    print(f"\nDone! Verify:")
    print(f"  https://{TARGET_DOMAIN}/ads.txt")
    print(f"  https://{TARGET_DOMAIN}/ (view source, check <head> for AdSense)")


if __name__ == "__main__":
    main()
