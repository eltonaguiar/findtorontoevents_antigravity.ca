import re
import os

def fix_favcreators_urls():
    """Fix all favcreators URLs in chunk files"""
    chunk_files = [
        'next/_next/static/chunks/a2ac3a6616d60872.js',
        '_next/static/chunks/a2ac3a6616d60872.js',
        'next/static/chunks/a2ac3a6616d60872.js',
    ]
    
    for file_path in chunk_files:
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            continue
            
        print(f"\nProcessing: {file_path}")
        with open(file_path, 'r', encoding='utf-8', errors='surrogateescape') as f:
            content = f.read()
        
        # Count occurrences
        wrong_matches = re.findall(r'href:"/favcreators/"', content)
        correct_matches = re.findall(r'href:"/favcreators/#/guest"', content)
        print(f"  Wrong URL (href:\"/favcreators/\"): {len(wrong_matches)}")
        print(f"  Correct URL (href:\"/favcreators/#/guest\"): {len(correct_matches)}")
        
        # Fix wrong URLs
        if len(wrong_matches) > 0:
            content = content.replace('href:"/favcreators/"', 'href:"/favcreators/#/guest"')
            with open(file_path, 'w', encoding='utf-8', errors='surrogateescape') as f:
                f.write(content)
            print(f"  ✅ Fixed {len(wrong_matches)} wrong URL(s)")
        else:
            print(f"  OK: No wrong URLs found")

if __name__ == "__main__":
    fix_favcreators_urls()
