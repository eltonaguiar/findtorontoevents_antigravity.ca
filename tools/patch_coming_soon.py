#!/usr/bin/env python3
"""Add 'Save Preference - Coming Soon' badge to all blog pages."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BADGE = '<span class="coming-soon-badge">Save Preference &#8212; Coming Soon</span>'

count = 0
for f in sorted(ROOT.glob("blog2[0-4][0-9].html")):
    html = f.read_text(encoding='utf-8')
    if 'coming-soon-badge' in html and BADGE in html:
        continue
    # Match: <span class="theme-label">Theme #NNN &mdash; Name</span>
    new_html = re.sub(
        r'(<span class="theme-label">Theme #\d+ &mdash; [^<]+)(</span>)',
        r'\1 ' + BADGE + r'\2',
        html
    )
    if new_html != html:
        f.write_text(new_html, encoding='utf-8')
        count += 1
        print(f"  Added badge to {f.name}")

print(f"\nPatched {count} files")
