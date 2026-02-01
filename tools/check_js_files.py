"""
Check what's actually being served for JavaScript files
"""
import urllib.request
import os

js_files = [
    '43a0077a15b1a098.js',
    '806bdb8e4a6a9b95.js',
    '628f1cf8c6948755.js',
    'a2ac3a6616d60872.js',
    'ff1a16fafef87110.js',
    'dde2c8e6322d1671.js',
    'turbopack-03e217c852f3e99c.js',
    'f1a9dd578dc871d3.js',
    '7c4eddd014120b50.js',
    'afe53b3593ec888c.js',
    '1bbf7aa8dcc742fe.js',
]

base_url = 'https://findtorontoevents.ca/next/_next/static/chunks/'

for js_file in js_files:
    url = base_url + js_file
    try:
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode('utf-8', errors='ignore')
            if content.startswith('<'):
                print(f"ERROR: {js_file}: Returns HTML (first 200 chars):")
                print(f"   {content[:200]}")
            elif content.startswith('(globalThis') or content.startswith('!function'):
                print(f"OK: {js_file}: Valid JavaScript ({len(content)} chars)")
            else:
                print(f"WARN: {js_file}: Unknown content ({len(content)} chars, starts with: {content[:50]})")
    except Exception as e:
        print(f"ERROR: {js_file}: Error - {e}")
