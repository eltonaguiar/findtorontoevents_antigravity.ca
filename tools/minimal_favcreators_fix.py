"""
Minimal fix: ONLY change favcreators URL, don't run full patch script
"""
import re
import os
from pathlib import Path

def minimal_fix():
    file_path = Path('next/_next/static/chunks/a2ac3a6616d60872.js')
    
    if not file_path.exists():
        print(f"ERROR: File not found: {file_path}")
        return False
    
    print(f"Reading {file_path}...")
    with open(file_path, 'r', encoding='utf-8', errors='surrogateescape') as f:
        content = f.read()
    
    print(f"File size: {len(content)} characters")
    
    # Check current state (correct URL on host is /fc/#/guest; /favcreators/ returns 500)
    wrong1 = len(re.findall(r'href:"/favcreators/"', content))
    wrong2 = len(re.findall(r'href:"/favcreators/#/guest"', content))
    correct = len(re.findall(r'href:"/fc/#/guest"', content))
    print(f"Before: Wrong (favcreators/): {wrong1}, Wrong (favcreators/#/guest): {wrong2}, Correct (/fc/#/guest): {correct}")
    
    if wrong1 or wrong2:
        content = content.replace('href:"/favcreators/#/guest"', 'href:"/fc/#/guest"')
        content = content.replace('href:"/favcreators/"', 'href:"/fc/#/guest"')
        with open(file_path, 'w', encoding='utf-8', errors='surrogateescape') as f:
            f.write(content)
        print(f"Fixed to /fc/#/guest")
    else:
        print("No wrong URLs found")
    
    wrong_after = len(re.findall(r'href:"/favcreators/"', content)) + len(re.findall(r'href:"/favcreators/#/guest"', content))
    correct_after = len(re.findall(r'href:"/fc/#/guest"', content))
    print(f"After: Wrong URLs: {wrong_after}, Correct URLs: {correct_after}")
    
    # Verify file is still valid JavaScript
    is_valid = (content.startswith('(globalThis') and 
                content.endswith('}]);') and 
                'Parse error' not in content and 
                'syntax error' not in content.lower())
    
    print(f"File is valid JavaScript: {is_valid}")
    
    return wrong_after == 0 and is_valid

if __name__ == "__main__":
    minimal_fix()
