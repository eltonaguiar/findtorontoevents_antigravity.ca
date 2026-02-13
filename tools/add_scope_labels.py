#!/usr/bin/env python3
"""
Add scope_labels.js script tag to all HTML pages that have stock-nav.js
but don't yet have scope_labels.js.
"""
import os
import glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NAV_TAG = '<script src="/findstocks/portfolio2/stock-nav.js"></script>'
SCOPE_TAG = '<script src="/live-monitor/api/scope_labels.js"></script>'

# Find all HTML files recursively
patterns = [
    os.path.join(ROOT, 'live-monitor', '*.html'),
    os.path.join(ROOT, 'findstocks', 'portfolio2', '*.html'),
    os.path.join(ROOT, 'findstocks', '*.html'),
    os.path.join(ROOT, 'findcryptopairs', '*.html'),
    os.path.join(ROOT, 'findforex2', 'portfolio', '*.html'),
    os.path.join(ROOT, 'findforex2', 'portfolio', 'stats', '*.html'),
    os.path.join(ROOT, 'findmutualfunds2', 'portfolio2', '*.html'),
    os.path.join(ROOT, 'findcryptopairs', 'portfolio', '*.html'),
    os.path.join(ROOT, 'findcryptopairs', 'portfolio', 'stats', '*.html'),
    os.path.join(ROOT, 'findstocks2_global', '*.html'),
]

updated = 0
skipped = 0
no_nav = 0

for pattern in patterns:
    for filepath in glob.glob(pattern):
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        if NAV_TAG not in content:
            no_nav += 1
            continue

        if SCOPE_TAG in content:
            skipped += 1
            continue

        # Add scope_labels.js right after stock-nav.js
        new_content = content.replace(
            NAV_TAG,
            NAV_TAG + '\n' + SCOPE_TAG
        )

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)

        rel = os.path.relpath(filepath, ROOT)
        print("  UPDATED: %s" % rel)
        updated += 1

print("")
print("Done: %d updated, %d already had it, %d no nav tag" % (updated, skipped, no_nav))
