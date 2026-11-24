#!/usr/bin/env python3
"""
Deploy the full site to an alternative domain via FTP with automatic path rewriting
and AdSense injection.

This script mirrors the entire site (main page, Next.js chunks, FavCreators, APIs,
Stats, VR, FindStocks) to an alternative FTP path, rewriting all hardcoded domain
references so the alternative site is fully independent.

AdSense Integration:
    - Automatically injects Google AdSense <script> tag into <head> of every HTML
      file that doesn't already have it
    - Replaces any old/different AdSense publisher IDs with the current one
    - Deploys adsense-integration.js to the site root

Usage:
    python tools/deploy_to_altsite.py --target torontoevent.net
    python tools/deploy_to_altsite.py --target tdotevent.ca
    python tools/deploy_to_altsite.py --dry-run --keep-staging
    python tools/deploy_to_altsite.py --target torontoevent.net --dry-run

Environment variables:
    FTP_SERVER  (or FTP_HOST) - FTP hostname
    FTP_USER    - FTP username
    FTP_PASS    - FTP password

The FTP_PATH for the alternative site is /<target_domain>/ (e.g. /torontoevent.net/).
"""

import argparse
import ftplib
import os
import re
import shutil
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE = _SCRIPT_DIR.parent

# The site content lives in tmp/fte_clone/ (full clone of the live site)
SITE_ROOT = WORKSPACE / "tmp" / "fte_clone"

SOURCE_DOMAIN = "findtorontoevents.ca"

# AdSense configuration
ADSENSE_PUB_ID = "ca-pub-7893721225790912"
ADSENSE_SCRIPT_TAG = '<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={}" crossorigin="anonymous"></script>'.format(ADSENSE_PUB_ID)

# Text-based file extensions that may contain domain references to rewrite
REWRITABLE_EXTENSIONS = {
    ".html", ".htm", ".php", ".js", ".jsx", ".ts", ".tsx", ".css",
    ".json", ".xml", ".svg", ".md", ".txt", ".yml", ".yaml",
    ".htaccess", ".env", ".example", ".map",
}

# Directories/files to skip entirely during staging
SKIP_PATTERNS = {
    ".git", "node_modules", "__pycache__", ".cursor", ".github",
    "TORONTOEVENTS_ANTIGRAVITY", "MOVIESHOWS", "MOVIESHOWS2", "MOVIESHOWS3",
    "DEPLOY", "favcreators_source", "tests", "playwright.config.ts",
    "playwright-report", "test-results", ".env",
    "package-lock.json", "backups", "backup_feb12026_232pmEST",
    # Temp/debug HTML files at root that shouldn't be deployed
    "server_index.html", "server_index_live.html", "server_index_check.html",
    "server-index-current.html", "tmp-remote-index.html", "temp_index.html",
    "tdot_index.html", "local_index.html", "live_index_full.html",
    "live_index.html", "ftp_downloaded_index.html", "fresh_server_check.html",
    "index_server_download.html", "index_formatted.html", "page_content.html",
    "index.backup-before-simple.html", "index2.html", "index3.html", "index4.html",
    "server_2xko_index.html", "server_windowsfixer_index.html",
}

# Reserved filenames on Windows that cannot be read/written
WINDOWS_RESERVED = {
    "con", "prn", "aux", "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
}

# Components and their local->remote mapping
# Format: (local_relative_path, remote_relative_path, description)
# Paths are relative to SITE_ROOT (tmp/fte_clone/)
DEPLOY_COMPONENTS = [
    # Main site
    ("index.html",                "",             "Main site index"),
    (".htaccess",                 "",             "Apache rewrite rules"),
    ("events.json",               "",             "Events data (root)"),
    ("events.json",               "next",         "Events data (next/)"),
    ("last_update.json",          "",             "Last update timestamp"),
    ("adsense-integration.js",    "",             "AdSense integration script"),
    # Next.js chunks
    ("next/_next",                "next/_next",   "Next.js static chunks"),
    ("_next",                     "_next",        "Alt Next.js static chunks"),
    # FavCreators (docs = built frontend)
    ("favcreators/docs",          "fc",           "FavCreators app"),
    # FavCreators API (PHP backend)
    ("favcreators/public/api",    "fc/api",       "FavCreators API"),
    # Events API
    ("api/events",                "fc/events-api", "Events API"),
    # Main API auth
    ("api/google_auth.php",       "api",          "Google OAuth (auth)"),
    ("api/google_callback.php",   "api",          "Google OAuth (callback)"),
    ("api/auth_db_config.php",    "api",          "Auth DB config"),
    ("api/.htaccess",             "api",          "API htaccess"),
    # Stats
    ("stats",                     "stats",        "Stats dashboard"),
    # VR pages
    ("vr",                        "vr",           "VR experience"),
    # FindStocks
    ("findstocks",                "findstocks",   "FindStocks app"),
    # Weather page
    ("weather",                   "weather",      "Weather page"),
    # Updates page
    ("updates",                   "updates",      "Updates page"),
    # Deals page
    ("deals",                     "deals",        "Deals page"),
    # WindowsFixer
    ("WINDOWSFIXER",              "WINDOWSFIXER", "WindowsFixer app"),
    # GotJob
    ("gotjob",                    "gotjob",       "GotJob app"),
    # Investments
    ("investments",               "investments",  "Investments dashboards"),
    # News
    ("news",                      "news",         "News page"),
    # Predictions
    ("predictions",               "predictions",  "Predictions dashboards"),
    # Live Monitor
    ("live-monitor",              "live-monitor",  "Live monitor dashboards"),
    # Daily Feed
    ("daily-feed",                "daily-feed",   "Daily feed page"),
    # Affiliates
    ("affiliates",                "affiliates",   "Affiliates page"),
    # FindForex
    ("findforex2",                "findforex2",   "FindForex app"),
    # FindMutualFunds
    ("findmutualfunds",           "findmutualfunds",  "FindMutualFunds app"),
    ("findmutualfunds2",          "findmutualfunds2", "FindMutualFunds2 app"),
    # FindCryptoPairs
    ("findcryptopairs",           "findcryptopairs",  "FindCryptoPairs app"),
]


# ---------------------------------------------------------------------------
# .env loader
# ---------------------------------------------------------------------------
def _load_env():
    """Load workspace .env for FTP credentials."""
    env_file = WORKSPACE / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip()
                if k and os.environ.get(k) in (None, ""):
                    os.environ.setdefault(k, v)
        if "FTP_SERVER" not in os.environ and os.environ.get("FTP_HOST"):
            os.environ.setdefault("FTP_SERVER", os.environ["FTP_HOST"])


def _env(key, fallback=""):
    return os.environ.get(key, fallback).strip()


# ---------------------------------------------------------------------------
# Path rewriting
# ---------------------------------------------------------------------------
def _rewrite_content(content, source, target):
    """Replace all domain references from source to target domain."""
    replacements = [
        # Full URLs with www
        (f"https://www.{source}", f"https://www.{target}"),
        (f"http://www.{source}", f"http://www.{target}"),
        # Full URLs without www
        (f"https://{source}", f"https://{target}"),
        (f"http://{source}", f"http://{target}"),
        # Hostname comparisons (JS): hostname === 'findtorontoevents.ca'
        (f"'{source}'", f"'{target}'"),
        (f'"{source}"', f'"{target}"'),
        # Display text / branding (only domain name, no protocol)
        (source, target),
    ]
    for old, new in replacements:
        content = content.replace(old, new)
    return content


def _is_rewritable(path):
    """Check if file should have domain references rewritten."""
    name = path.name.lower()
    suffix = path.suffix.lower()
    if name == ".htaccess":
        return True
    return suffix in REWRITABLE_EXTENSIONS


def _should_skip(name):
    """Check if a file or directory should be skipped."""
    if name in SKIP_PATTERNS:
        return True
    stem = Path(name).stem.lower()
    if stem in WINDOWS_RESERVED:
        return True
    return False


# ---------------------------------------------------------------------------
# AdSense injection
# ---------------------------------------------------------------------------
def _has_adsense(content):
    """Check if content already has AdSense."""
    return "googlesyndication" in content or "adsbygoogle" in content


def _find_old_adsense_pubs(content):
    """Find old/different AdSense publisher IDs."""
    old_pubs = set()
    for match in re.finditer(r'ca-pub-(\d+)', content):
        full_id = match.group(0)
        if full_id != ADSENSE_PUB_ID:
            old_pubs.add(full_id)
    return list(old_pubs)


def _inject_adsense(content):
    """Inject AdSense <script> tag into <head> of HTML content.
    
    Returns (modified_content, was_injected).
    Also replaces any old/different AdSense publisher IDs.
    """
    # First: replace any old publisher IDs
    old_pubs = _find_old_adsense_pubs(content)
    for old_id in old_pubs:
        content = content.replace(old_id, ADSENSE_PUB_ID)

    # If already has current AdSense, nothing more to do
    if _has_adsense(content):
        return content, False

    # Find <head> section
    head_match = re.search(r'<head[^>]*>', content, re.IGNORECASE)
    if not head_match:
        return content, False

    head_end = re.search(r'</head>', content, re.IGNORECASE)
    if not head_end:
        return content, False

    head_section = content[head_match.end():head_end.start()]

    # Find last <meta> tag position for nice placement
    last_meta = None
    for m in re.finditer(r'<meta\s[^>]*/?>', head_section, re.IGNORECASE):
        last_meta = m

    if last_meta:
        insert_pos = head_match.end() + last_meta.end()
        line_start = content.rfind('\n', 0, insert_pos)
        if line_start >= 0:
            line = content[line_start + 1:insert_pos]
            indent = re.match(r'^(\s*)', line)
            indent_str = indent.group(1) if indent else '  '
        else:
            indent_str = '  '
        content = content[:insert_pos] + '\n' + indent_str + ADSENSE_SCRIPT_TAG + content[insert_pos:]
        return content, True

    # Fallback: insert right after <head>
    insert_pos = head_match.end()
    content = content[:insert_pos] + '\n  ' + ADSENSE_SCRIPT_TAG + content[insert_pos:]
    return content, True


# ---------------------------------------------------------------------------
# Staging: copy files with rewriting + AdSense injection
# ---------------------------------------------------------------------------
def _stage_file(src, dst, source_domain, target_domain, inject_ads=True):
    """Copy a single file, rewriting text content and injecting AdSense if applicable."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if _is_rewritable(src):
        try:
            text = src.read_text(encoding="utf-8", errors="ignore")
            # Domain rewriting
            rewritten = _rewrite_content(text, source_domain, target_domain)
            # AdSense injection for HTML files
            if inject_ads and src.suffix.lower() in ('.html', '.htm'):
                rewritten, injected = _inject_adsense(rewritten)
                if injected:
                    print(f"    [AdSense] Injected into: {src.name}")
            dst.write_text(rewritten, encoding="utf-8")
            return
        except Exception:
            pass  # Fall through to binary copy
    # Binary copy (images, fonts, etc.)
    shutil.copy2(src, dst)


def _stage_tree(src_dir, dst_dir, source_domain, target_domain, inject_ads=True):
    """Recursively copy a directory tree with rewriting."""
    count = 0
    if not src_dir.is_dir():
        return 0
    for root, dirs, files in os.walk(src_dir):
        dirs[:] = [d for d in dirs if not _should_skip(d)]
        for name in files:
            if _should_skip(name):
                continue
            src_file = Path(root) / name
            rel = src_file.relative_to(src_dir)
            dst_file = dst_dir / rel
            _stage_file(src_file, dst_file, source_domain, target_domain, inject_ads)
            count += 1
    return count


def stage_site(staging_dir, source_domain, target_domain, site_root=None):
    """Stage all deployable components into staging_dir with rewritten paths.
    
    Returns a dict of component_name -> (staged_local_path, remote_relative_path)
    """
    root = site_root or SITE_ROOT
    manifest = {}

    # Also check workspace root for adsense-integration.js
    adsense_js_workspace = WORKSPACE / "adsense-integration.js"
    adsense_js_site = root / "adsense-integration.js"

    # If adsense-integration.js doesn't exist in site root, copy from workspace
    if not adsense_js_site.exists() and adsense_js_workspace.exists():
        shutil.copy2(adsense_js_workspace, adsense_js_site)
        print(f"  Copied adsense-integration.js to site root")

    for local_rel, remote_rel, desc in DEPLOY_COMPONENTS:
        src = root / local_rel.replace("/", os.sep)

        if not src.exists():
            print(f"  Skip {desc}: {local_rel} not found")
            continue

        if src.is_file():
            filename = src.name
            staged_path = staging_dir / remote_rel / filename if remote_rel else staging_dir / filename
            _stage_file(src, staged_path, source_domain, target_domain)
            manifest[desc] = (staged_path, f"{remote_rel}/{filename}" if remote_rel else filename)
            print(f"  Staged {desc}: {local_rel} -> {remote_rel or '(root)'}/{filename}")
        else:
            staged_path = staging_dir / remote_rel if remote_rel else staging_dir
            count = _stage_tree(src, staged_path, source_domain, target_domain)
            manifest[desc] = (staged_path, remote_rel)
            print(f"  Staged {desc}: {local_rel}/ -> {remote_rel}/ ({count} files)")

    return manifest


# ---------------------------------------------------------------------------
# FTP deployment
# ---------------------------------------------------------------------------
def _ensure_dir(ftp, remote_dir):
    """Ensure remote directory exists, creating parents as needed."""
    ftp.cwd("/")
    for part in remote_dir.split("/"):
        if not part:
            continue
        try:
            ftp.cwd(part)
        except ftplib.error_perm:
            try:
                ftp.mkd(part)
                ftp.cwd(part)
            except Exception as e:
                print(f"    Warning: mkd/cwd {part}: {e}")
                return False
    return True


def _upload_tree(ftp, local_dir, remote_base):
    """Upload a local directory tree to FTP."""
    if not local_dir.is_dir():
        return 0
    ftp.cwd("/")
    if not _ensure_dir(ftp, remote_base):
        return 0
    count = 0
    for root, dirs, files in os.walk(local_dir):
        for name in files:
            local_path = Path(root) / name
            rel = local_path.relative_to(local_dir)
            remote_path = remote_base + "/" + str(rel).replace("\\", "/")
            remote_parts = remote_path.split("/")
            remote_file = remote_parts[-1]
            remote_parent = "/".join(remote_parts[:-1])
            ftp.cwd("/")
            _ensure_dir(ftp, remote_parent)
            try:
                with open(local_path, "rb") as f:
                    ftp.storbinary(f"STOR {remote_file}", f)
                count += 1
            except Exception as e:
                print(f"    ERROR {remote_path}: {e}")
    return count


def deploy_staged(ftp, staging_dir, ftp_base):
    """Deploy the entire staged directory to FTP under ftp_base."""
    print(f"\nDeploying to FTP path: /{ftp_base}/")
    total = _upload_tree(ftp, staging_dir, ftp_base)
    print(f"\n  Total files uploaded: {total}")
    return total


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Deploy site to alternative domain via FTP")
    parser.add_argument("--target", default="torontoevent.net",
                        help="Target domain name (default: torontoevent.net)")
    parser.add_argument("--source", default=SOURCE_DOMAIN,
                        help=f"Source domain to replace (default: {SOURCE_DOMAIN})")
    parser.add_argument("--ftp-path", default=None,
                        help="FTP remote path (default: /<target>/)")
    parser.add_argument("--site-root", default=None,
                        help=f"Site content root (default: {SITE_ROOT})")
    parser.add_argument("--no-adsense", action="store_true",
                        help="Skip AdSense injection")
    parser.add_argument("--dry-run", action="store_true",
                        help="Stage files but don't upload")
    parser.add_argument("--keep-staging", action="store_true",
                        help="Don't delete staging directory after deploy")
    args = parser.parse_args()

    _load_env()

    target = args.target
    source = args.source
    ftp_path = args.ftp_path or target
    site_root = Path(args.site_root) if args.site_root else SITE_ROOT

    host = _env("FTP_SERVER") or _env("FTP_HOST")
    user = _env("FTP_USER")
    password = _env("FTP_PASS")

    if not args.dry_run and (not host or not user or not password):
        print("ERROR: Set FTP_SERVER (or FTP_HOST), FTP_USER, FTP_PASS in environment.")
        print("  Windows: $env:FTP_SERVER='...'; $env:FTP_USER='...'; $env:FTP_PASS='...'")
        print("  Or create a .env file in the project root.")
        raise SystemExit(1)

    if not site_root.exists():
        print(f"ERROR: Site root not found: {site_root}")
        print(f"  Ensure tmp/fte_clone/ exists with the site content.")
        raise SystemExit(1)

    print("=" * 70)
    print(f"  Alternative Site Deployment")
    print(f"  Source domain:  {source}")
    print(f"  Target domain:  {target}")
    print(f"  FTP path:       /{ftp_path}/")
    print(f"  FTP server:     {host or '(dry-run)'}")
    print(f"  Site root:      {site_root}")
    print(f"  AdSense inject: {'No' if args.no_adsense else 'Yes (ca-pub-7893721225790912)'}")
    print(f"  Dry run:        {args.dry_run}")
    print("=" * 70)
    print()

    # --- Stage ---
    staging_dir = Path(tempfile.mkdtemp(prefix="altsite_deploy_"))
    print(f"Staging directory: {staging_dir}")
    print()

    print("Staging files with path rewriting + AdSense injection...")
    try:
        manifest = stage_site(staging_dir, source, target, site_root)
    except Exception as e:
        print(f"\nStaging failed: {e}")
        shutil.rmtree(staging_dir, ignore_errors=True)
        raise SystemExit(1)

    # Count staged files
    staged_count = sum(1 for _ in staging_dir.rglob("*") if _.is_file())
    print(f"\nTotal staged files: {staged_count}")

    # --- Verify AdSense ---
    html_count = 0
    adsense_count = 0
    for html_file in staging_dir.rglob("*.html"):
        html_count += 1
        content = html_file.read_text(encoding="utf-8", errors="ignore")
        if "googlesyndication" in content or "adsbygoogle" in content:
            adsense_count += 1

    print(f"\nAdSense coverage: {adsense_count}/{html_count} HTML files have AdSense")
    if html_count > 0 and adsense_count < html_count:
        missing = html_count - adsense_count
        print(f"  WARNING: {missing} HTML files still missing AdSense (may not have <head>)")

    if args.dry_run:
        print(f"\nDry run complete. Staged files are in: {staging_dir}")
        if not args.keep_staging:
            print("(Use --keep-staging to inspect the staging directory)")
            shutil.rmtree(staging_dir, ignore_errors=True)
        return

    # --- Deploy ---
    print(f"\nConnecting to FTP: {host} ...")
    try:
        with ftplib.FTP(host, timeout=120) as ftp:
            ftp.login(user, password)
            print("Connected.\n")

            total = deploy_staged(ftp, staging_dir, ftp_path)

        print(f"\nDeploy complete! {total} files uploaded to /{ftp_path}/")
        print()
        print("Post-deploy verification:")
        print(f"  Main site:      https://{target}/")
        print(f"  Events:         https://{target}/events.json")
        print(f"  FavCreators:    https://{target}/fc/")
        print(f"  Stats:          https://{target}/stats/")
        print(f"  VR:             https://{target}/vr/")
        print(f"  FindStocks:     https://{target}/findstocks/")
        print()
        print("Setup endpoints (run once):")
        print(f"  Tables setup:   https://{target}/fc/events-api/setup_tables.php")
        print(f"  Events sync:    https://{target}/fc/events-api/sync_events.php")

    except Exception as e:
        print(f"\nDeploy failed: {e}")
        raise SystemExit(1)
    finally:
        if not args.keep_staging:
            shutil.rmtree(staging_dir, ignore_errors=True)
        else:
            print(f"\nStaging directory preserved: {staging_dir}")


if __name__ == "__main__":
    main()
