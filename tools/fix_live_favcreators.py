"""
Fix favcreators URL in the live JavaScript chunk file.
This script ensures all favcreators links use /favcreators/#/guest
"""
import re
import os

def fix_all_chunk_files():
    """Fix all a2ac chunk files in the repository"""
    # Find all a2ac chunk files
    chunk_files = []
    for root, dirs, files in os.walk('.'):
        if 'a2ac3a6616d60872.js' in files:
            chunk_files.append(os.path.join(root, 'a2ac3a6616d60872.js'))
    
    print(f"Found {len(chunk_files)} chunk files to check")
    
    for file_path in chunk_files:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='surrogateescape') as f:
                content = f.read()
            
            # Count occurrences
            wrong_matches = re.findall(r'href:"/favcreators/"', content)
            correct_matches = re.findall(r'href:"/favcreators/#/guest"', content)
            
            print(f"\n{file_path}:")
            print(f"  Wrong URL: {len(wrong_matches)}")
            print(f"  Correct URL: {len(correct_matches)}")
            
            # Fix wrong URLs
            if len(wrong_matches) > 0:
                content = content.replace('href:"/favcreators/"', 'href:"/favcreators/#/guest"')
                with open(file_path, 'w', encoding='utf-8', errors='surrogateescape') as f:
                    f.write(content)
                print(f"  ✅ Fixed {len(wrong_matches)} wrong URL(s)")
        except Exception as e:
            print(f"  ❌ Error processing {file_path}: {e}")

if __name__ == "__main__":
    fix_all_chunk_files()
