#!/usr/bin/env python3
"""Check what HTML the server is actually serving"""
import requests

url = "https://findtorontoevents.ca/index3.html"
headers = {
    'Cache-Control': 'no-cache',
    'User-Agent': 'Mozilla/5.0'
}

r = requests.get(url, headers=headers)
content = r.text

print(f"Status: {r.status_code}")
print(f"Content length: {len(content)}")
print(f"\nHas /_next/static: {'/_next/static' in content}")
print(f"Has /next/_next/static: {'/next/_next/static' in content}")

# Find first script tag
import re
scripts = re.findall(r'<script[^>]*src=["\']([^"\']*)["\']', content)
if scripts:
    print(f"\nFirst 3 script src paths:")
    for s in scripts[:3]:
        print(f"  {s}")

# Check if there's any server-side modification
if '/_next/static' in content and '/next/_next/static' in content:
    print("\nWARNING: HTML contains BOTH path formats!")
elif '/next/_next/static' in content:
    print("\nERROR: Server HTML has wrong paths!")
elif '/_next/static' in content:
    print("\nOK: Server HTML has correct paths!")
