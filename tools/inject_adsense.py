#!/usr/bin/env python3
"""
Inject Google AdSense code into all HTML files that don't already have it.

Usage:
    python tools/inject_adsense.py                            # scan tmp/fte_clone/
    python tools/inject_adsense.py --path path/to/dir         # scan specific directory
    python tools/inject_adsense.py --dry-run                  # preview without writing
    python tools/inject_adsense.py --pub-id ca-pub-XXXXXXXXX  # custom publisher ID

The script:
  1. Finds all .html files in the target directory tree
  2. Skips files that already contain the AdSense script tag
  3. Injects the <script> tag into <head> (after the last <meta> or before </head>)
  4. Reports what was injected and what was skipped
"""

import argparse
import os
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE = SCRIPT_DIR.parent

DEFAULT_PUB_ID = "ca-pub-7893721225790912"

ADSENSE_TAG_TEMPLATE = '<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={pub_id}" crossorigin="anonymous"></script>'

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".cursor", ".github",
    "TORONTOEVENTS_ANTIGRAVITY", "playwright-report", "test-results",
    "backups", "backup_feb12026_232pmEST",
}

SKIP_FILE_PATTERNS = {
    "server_index", "server-index", "tmp-remote", "temp_index",
    "tdot_index", "live_index", "local_index", "ftp_downloaded",
    "fresh_server", "index_formatted", "index_server_download",
    "page_content", "index.backup",
}


def should_skip_dir(name):
    return name.lower() in {s.lower() for s in SKIP_DIRS}


def should_skip_file(name):
    name_lower = name.lower()
    for pattern in SKIP_FILE_PATTERNS:
        if pattern in name_lower:
            return True
    return False


def has_adsense(content):
    return "googlesyndication" in content or "adsbygoogle" in content


def find_old_adsense(content, current_pub_id):
    """Find old/different AdSense publisher IDs."""
    old_pubs = []
    for match in re.finditer(r'ca-pub-(\d+)', content):
        full_id = match.group(0)
        if full_id != current_pub_id:
            old_pubs.append(full_id)
    return list(set(old_pubs))


def inject_adsense_tag(content, pub_id):
    """Inject AdSense <script> tag into <head> section of HTML content."""
    tag = ADSENSE_TAG_TEMPLATE.format(pub_id=pub_id)

    # Strategy 1: Insert after the last <meta> tag in <head>
    head_match = re.search(r'<head[^>]*>', content, re.IGNORECASE)
    if not head_match:
        return content, False

    head_end = re.search(r'</head>', content, re.IGNORECASE)
    if not head_end:
        return content, False

    head_section = content[head_match.end():head_end.start()]

    # Find the last <meta> tag position
    last_meta = None
    for m in re.finditer(r'<meta\s[^>]*/?>', head_section, re.IGNORECASE):
        last_meta = m

    if last_meta:
        insert_pos = head_match.end() + last_meta.end()
        # Detect indentation
        line_start = content.rfind('\n', 0, insert_pos)
        if line_start >= 0:
            line = content[line_start + 1:insert_pos]
            indent = re.match(r'^(\s*)', line)
            indent_str = indent.group(1) if indent else '  '
        else:
            indent_str = '  '
        content = content[:insert_pos] + '\n' + indent_str + tag + content[insert_pos:]
        return content, True

    # Strategy 2: Insert right after <head>
    insert_pos = head_match.end()
    content = content[:insert_pos] + '\n  ' + tag + content[insert_pos:]
    return content, True


def replace_old_adsense(content, old_pub_ids, new_pub_id):
    """Replace old AdSense publisher IDs with the new one."""
    for old_id in old_pub_ids:
        content = content.replace(old_id, new_pub_id)
    return content


def process_directory(target_dir, pub_id, dry_run=False):
    """Process all HTML files in a directory tree."""
    target = Path(target_dir)
    if not target.exists():
        print(f"ERROR: Directory not found: {target}")
        return

    injected = []
    replaced = []
    skipped = []
    already_has = []

    for root, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if not should_skip_dir(d)]

        for name in files:
            if not name.lower().endswith(('.html', '.htm')):
                continue
            if should_skip_file(name):
                continue

            filepath = Path(root) / name
            try:
                content = filepath.read_text(encoding='utf-8', errors='ignore')
            except Exception as e:
                print(f"  SKIP (read error): {filepath}: {e}")
                skipped.append(str(filepath))
                continue

            rel_path = filepath.relative_to(target)

            # Check for old/different publisher IDs
            old_pubs = find_old_adsense(content, pub_id)
            if old_pubs:
                content = replace_old_adsense(content, old_pubs, pub_id)
                replaced.append((str(rel_path), old_pubs))
                if not dry_run:
                    filepath.write_text(content, encoding='utf-8')
                    print(f"  REPLACED old pub IDs in: {rel_path} ({old_pubs} -> {pub_id})")
                else:
                    print(f"  WOULD REPLACE old pub IDs in: {rel_path} ({old_pubs} -> {pub_id})")

            # Check if already has current AdSense
            if has_adsense(content):
                already_has.append(str(rel_path))
                continue

            # Inject AdSense
            new_content, success = inject_adsense_tag(content, pub_id)
            if success:
                injected.append(str(rel_path))
                if not dry_run:
                    filepath.write_text(new_content, encoding='utf-8')
                    print(f"  INJECTED: {rel_path}")
                else:
                    print(f"  WOULD INJECT: {rel_path}")
            else:
                skipped.append(str(rel_path))
                print(f"  SKIP (no <head>): {rel_path}")

    print(f"\n{'=' * 60}")
    print(f"  AdSense Injection Summary")
    print(f"  Publisher ID: {pub_id}")
    print(f"  Target: {target}")
    print(f"  Dry run: {dry_run}")
    print(f"{'=' * 60}")
    print(f"  Already has AdSense: {len(already_has)}")
    print(f"  Injected:            {len(injected)}")
    print(f"  Old IDs replaced:    {len(replaced)}")
    print(f"  Skipped:             {len(skipped)}")
    print(f"  Total processed:     {len(already_has) + len(injected) + len(skipped)}")

    return {
        'injected': injected,
        'replaced': replaced,
        'already_has': already_has,
        'skipped': skipped,
    }


def main():
    parser = argparse.ArgumentParser(description="Inject Google AdSense into HTML files")
    parser.add_argument("--path", default=None,
                        help="Target directory (default: tmp/fte_clone/)")
    parser.add_argument("--pub-id", default=DEFAULT_PUB_ID,
                        help=f"AdSense publisher ID (default: {DEFAULT_PUB_ID})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without writing")
    args = parser.parse_args()

    target = Path(args.path) if args.path else WORKSPACE / "tmp" / "fte_clone"

    print(f"Scanning for HTML files missing AdSense...")
    print(f"  Target: {target}")
    print(f"  Publisher ID: {args.pub_id}")
    print(f"  Dry run: {args.dry_run}")
    print()

    process_directory(target, args.pub_id, args.dry_run)


if __name__ == "__main__":
    main()
