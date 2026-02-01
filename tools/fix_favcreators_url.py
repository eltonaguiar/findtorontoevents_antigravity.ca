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
        
        # Count occurrences (correct URL on host is /fc/#/guest; /favcreators/ returns 500)
        wrong1 = re.findall(r'href:"/favcreators/"', content)
        wrong2 = re.findall(r'href:"/favcreators/#/guest"', content)
        correct_matches = re.findall(r'href:"/fc/#/guest"', content)
        print(f"  Wrong (href:\"/favcreators/\"): {len(wrong1)}")
        print(f"  Wrong (href:\"/favcreators/#/guest\"): {len(wrong2)}")
        print(f"  Correct (href:\"/fc/#/guest\"): {len(correct_matches)}")
        
        # Fix wrong URLs to /fc/#/guest
        if wrong1 or wrong2:
            content = content.replace('href:"/favcreators/#/guest"', 'href:"/fc/#/guest"')
            content = content.replace('href:"/favcreators/"', 'href:"/fc/#/guest"')
            with open(file_path, 'w', encoding='utf-8', errors='surrogateescape') as f:
                f.write(content)
            print(f"  ✅ Fixed wrong URL(s) to /fc/#/guest")
        else:
            print(f"  OK: No wrong URLs found")

if __name__ == "__main__":
    fix_favcreators_urls()
