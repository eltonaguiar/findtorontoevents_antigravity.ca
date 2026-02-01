#!/usr/bin/env python3
"""
Fix local development by removing PHP proxy references from index.html
This creates a local-dev version of index.html that works with the Python HTTP server
"""

import re
import shutil
from pathlib import Path

# Paths
source_file = Path(r'e:\findtorontoevents_antigravity.ca\index.html')
backup_file = Path(r'e:\findtorontoevents_antigravity.ca\index.html.with_proxy_backup')
output_file = source_file  # We'll overwrite the original

# Read the file
with open(source_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Create backup
shutil.copy2(source_file, backup_file)
print(f"✓ Created backup: {backup_file}")

# Replace all js-proxy-v2.php references with direct paths
# Pattern: /js-proxy-v2.php?file=next/_next/static/chunks/FILENAME.js
# Replace with: /next/_next/static/chunks/FILENAME.js

original_content = content
content = re.sub(
    r'/js-proxy-v2\.php\?file=(next/_next/static/chunks/[^"\']+)',
    r'/\1',
    content
)

# Also update the function that generates proxy URLs (line 17)
content = re.sub(
    r'return "/js-proxy-v2\.php\?file=next/_next/static/chunks/" \+ file;',
    r'return "/next/_next/static/chunks/" + file;',
    content
)

# Count changes
changes = len(re.findall(r'js-proxy-v2\.php', original_content))
remaining = len(re.findall(r'js-proxy-v2\.php', content))

print(f"\n✓ Removed {changes - remaining} js-proxy references")
if remaining > 0:
    print(f"⚠ Warning: {remaining} js-proxy references still remain")

# Write the updated file
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"✓ Updated: {output_file}")
print(f"\nNow the local server should work correctly!")
print(f"To restore the proxy version, copy back from: {backup_file}")
