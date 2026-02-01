"""
Emergency restore: Get original chunk from server or use backup, apply minimal fix
"""
import os
import re
import urllib.request
from pathlib import Path

def emergency_fix():
    target = Path('next/_next/static/chunks/a2ac3a6616d60872.js')
    target.parent.mkdir(parents=True, exist_ok=True)
    
    # Try to get from a known good backup location
    backup_sources = [
        'next/static/chunks/a2ac3a6616d60872.js',
        '_next/static/chunks/a2ac3a6616d60872.js',
    ]
    
    content = None
    source_used = None
    
    for backup_path in backup_sources:
        backup = Path(backup_path)
        if backup.exists() and backup.stat().st_size > 39000:
            with open(backup, 'r', encoding='utf-8', errors='surrogateescape') as f:
                content = f.read()
            source_used = backup_path
            print(f"Using backup: {backup_path} ({len(content)} chars)")
            break
    
    if not content:
        print("ERROR: No valid backup found!")
        return False
    
    # Apply ONLY the favcreators URL fix - nothing else!
    wrong_before = len(re.findall(r'href:"/favcreators/"', content))
    if wrong_before > 0:
        print(f"Found {wrong_before} wrong URL(s), fixing...")
        content = content.replace('href:"/favcreators/"', 'href:"/favcreators/#/guest"')
    
    # Write to target
    with open(target, 'w', encoding='utf-8', errors='surrogateescape') as f:
        f.write(content)
    
    print(f"Restored and fixed: {target} ({len(content)} chars)")
    
    # Verify
    wrong_after = len(re.findall(r'href:"/favcreators/"', content))
    correct_after = len(re.findall(r'href:"/favcreators/#/guest"', content))
    print(f"Wrong URLs: {wrong_after}, Correct URLs: {correct_after}")
    
    return wrong_after == 0

if __name__ == "__main__":
    emergency_fix()
