"""
Restore the chunk file from backup and apply ONLY the favcreators URL fix
"""
import os
import re
import shutil
from pathlib import Path

def restore_and_fix():
    # Find the most recent backup
    backup_dir = Path('backups')
    backups = []
    
    if backup_dir.exists():
        for backup_file in backup_dir.rglob('a2ac3a6616d60872.js'):
            if backup_file.stat().st_size > 39000:  # Valid size
                backups.append((backup_file, backup_file.stat().st_mtime))
    
    if not backups:
        print("No valid backups found. Using current file.")
        source = Path('next/_next/static/chunks/a2ac3a6616d60872.js')
    else:
        # Get most recent backup
        backups.sort(key=lambda x: x[1], reverse=True)
        source = backups[0][0]
        print(f"Using backup: {source} ({source.stat().st_size} bytes)")
    
    # Target file
    target = Path('next/_next/static/chunks/a2ac3a6616d60872.js')
    target.parent.mkdir(parents=True, exist_ok=True)
    
    # Copy backup to target
    shutil.copy2(source, target)
    print(f"Restored to: {target}")
    
    # Read the file
    with open(target, 'r', encoding='utf-8', errors='surrogateescape') as f:
        content = f.read()
    
    print(f"File size: {len(content)} characters")
    
    # Apply ONLY the favcreators URL fix (no other modifications)
    wrong_count = len(re.findall(r'href:"/favcreators/"', content))
    correct_count = len(re.findall(r'href:"/favcreators/#/guest"', content))
    
    print(f"Before fix: Wrong URLs: {wrong_count}, Correct URLs: {correct_count}")
    
    if wrong_count > 0:
        content = content.replace('href:"/favcreators/"', 'href:"/favcreators/#/guest"')
        with open(target, 'w', encoding='utf-8', errors='surrogateescape') as f:
            f.write(content)
        print(f"Fixed {wrong_count} wrong URL(s)")
    else:
        print("No wrong URLs found - file is already correct")
    
    # Verify
    with open(target, 'r', encoding='utf-8', errors='surrogateescape') as f:
        content = f.read()
    
    wrong_after = len(re.findall(r'href:"/favcreators/"', content))
    correct_after = len(re.findall(r'href:"/favcreators/#/guest"', content))
    
    print(f"After fix: Wrong URLs: {wrong_after}, Correct URLs: {correct_after}")
    
    if wrong_after == 0 and correct_after > 0:
        print("SUCCESS: File is fixed and ready to deploy")
        return True
    else:
        print("WARNING: File may not be correctly fixed")
        return False

if __name__ == "__main__":
    restore_and_fix()
